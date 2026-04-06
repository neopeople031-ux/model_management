"""
Google Calendar API 단방향(Read) 연동 모듈

부커들의 Google Calendar 일정을 읽어와 시스템 내 모델과 매칭합니다.
"""
import os
from datetime import datetime, timedelta
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Google Calendar API 스코프 (읽기 전용)
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

TOKEN_PATH = "token.json"
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")


def get_calendar_service():
    """
    Google Calendar API 서비스 객체를 생성합니다.

    최초 1회 OAuth 인증 플로우를 수행하고, 이후에는 저장된 토큰을 재사용합니다.
    """
    creds = None

    # 기존 토큰 로드
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # 토큰 만료 시 갱신 또는 새 인증
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Google 자격증명 파일을 찾을 수 없습니다: {CREDENTIALS_PATH}\n"
                    "GCP 콘솔에서 OAuth 클라이언트 ID를 다운로드하세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # 토큰 저장
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def fetch_events(
    days_ahead: int = 30,
    days_past: int = 7,
    calendar_id: str = "primary",
) -> list[dict]:
    """
    Google Calendar에서 일정을 가져옵니다.

    Args:
        days_ahead: 앞으로 며칠의 일정을 가져올지
        days_past: 과거 며칠의 일정을 가져올지
        calendar_id: 캘린더 ID (기본: primary)

    Returns:
        일정 목록 (dict 리스트)
    """
    service = get_calendar_service()

    now = datetime.utcnow()
    time_min = (now - timedelta(days=days_past)).isoformat() + "Z"
    time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])

    return [
        {
            "google_event_id": event["id"],
            "title": event.get("summary", "제목 없음"),
            "description": event.get("description", ""),
            "start": event["start"].get("dateTime", event["start"].get("date")),
            "end": event["end"].get("dateTime", event["end"].get("date")),
            "location": event.get("location", ""),
        }
        for event in events
    ]


def parse_event_for_schedule(event: dict) -> dict | None:
    """
    Google Calendar 이벤트를 스케줄 데이터로 파싱합니다.

    이벤트 제목에서 모델명, 클라이언트명 등을 추출하는 간단한 파서입니다.
    향후 부커들의 작성 패턴에 맞게 고도화할 수 있습니다.

    Args:
        event: fetch_events에서 반환된 이벤트 dict

    Returns:
        스케줄 데이터 dict 또는 None (파싱 실패 시)
    """
    try:
        title = event.get("title", "")
        start = event.get("start", "")
        end = event.get("end", "")

        return {
            "google_event_id": event.get("google_event_id"),
            "title": title,
            "schedule_date": start[:10] if start else None,
            "start_time": start,
            "end_time": end,
        }
    except Exception:
        return None

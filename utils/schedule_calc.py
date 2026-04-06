"""
스케줄 시간 계산 모듈

PRD §6 비즈니스 로직 구현:
- 시간 반올림(Rounding) 규칙: 30분 이하 버림, 31분 이상 올림
- Half/Full/OT 자동 판별
"""
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class WorkTypeResult:
    """촬영 시간 계산 결과"""
    total_minutes: int       # 총 분 단위 시간
    rounded_hours: int       # 반올림 적용 후 시간
    work_type: str           # hours_only, half, half_plus, full, full_plus
    display: str             # 화면 표시용 문자열 (예: "Half + 2시간")
    display_en: str          # 영어 표시용


def round_hours(total_minutes: int) -> int:
    """
    30분 반올림 규칙 적용

    - 30분 이하: 버림 (Round Down)
    - 31분 이상: 올림 (Round Up)

    예: 270분(4시간 30분) → 4시간
    예: 271분(4시간 31분) → 5시간
    """
    hours = total_minutes // 60
    remaining_minutes = total_minutes % 60

    if remaining_minutes >= 31:
        return hours + 1
    return hours


def calculate_work_type(
    start_time: datetime,
    end_time: datetime,
) -> WorkTypeResult:
    """
    촬영 시작/종료 시간으로 Half/Full/OT를 판별합니다.

    판별 기준:
    - 1~4시간: 해당 시간 그대로 표기
    - 5시간(4h31m 도달 시): Half
    - 5시간 초과 ~ 9시간 미만: Half + 초과시간
    - 9시간(8h31m 도달 시): Full
    - 9시간 초과: Full + 초과시간

    Args:
        start_time: 촬영 시작 시간
        end_time: 촬영 종료 시간

    Returns:
        WorkTypeResult: 계산 결과
    """
    if end_time <= start_time:
        raise ValueError("종료 시간은 시작 시간보다 이후여야 합니다.")

    delta: timedelta = end_time - start_time
    total_minutes = int(delta.total_seconds() / 60)

    if total_minutes <= 0:
        raise ValueError("촬영 시간은 0보다 커야 합니다.")

    rounded = round_hours(total_minutes)

    # 최소 1시간
    if rounded < 1:
        rounded = 1

    # 판별 로직
    if rounded <= 4:
        return WorkTypeResult(
            total_minutes=total_minutes,
            rounded_hours=rounded,
            work_type="hours_only",
            display=f"{rounded}시간",
            display_en=f"{rounded}hr{'s' if rounded > 1 else ''}",
        )
    elif rounded == 5:
        return WorkTypeResult(
            total_minutes=total_minutes,
            rounded_hours=rounded,
            work_type="half",
            display="Half",
            display_en="Half",
        )
    elif rounded < 9:
        extra = rounded - 5
        return WorkTypeResult(
            total_minutes=total_minutes,
            rounded_hours=rounded,
            work_type="half_plus",
            display=f"Half + {extra}시간",
            display_en=f"Half + {extra}hr{'s' if extra > 1 else ''}",
        )
    elif rounded == 9:
        return WorkTypeResult(
            total_minutes=total_minutes,
            rounded_hours=rounded,
            work_type="full",
            display="Full",
            display_en="Full",
        )
    else:
        extra = rounded - 9
        return WorkTypeResult(
            total_minutes=total_minutes,
            rounded_hours=rounded,
            work_type="full_plus",
            display=f"Full + {extra}시간",
            display_en=f"Full + {extra}hr{'s' if extra > 1 else ''}",
        )

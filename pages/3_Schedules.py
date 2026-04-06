"""
📅 스케줄 관리 - Google Calendar 연동, Half/Full/OT 자동 판별
"""
import streamlit as st
from datetime import date, datetime, timedelta
from utils.auth import require_auth, get_current_user_id
from utils.i18n import t
from utils.supabase_client import get_supabase_client
from utils.schedule_calc import calculate_work_type


@require_auth(page_name="schedules")
def main():
    st.markdown(f"# {t('schedule.title')}")

    supabase = get_supabase_client()

    # ─── 상단 액션 바 ─────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        view_date = st.date_input("📅 날짜 선택", value=date.today())

    with col2:
        if st.button(f"➕ {t('schedule.add')}", use_container_width=True):
            st.session_state["show_schedule_form"] = True

    with col3:
        if st.button(f"🔄 {t('schedule.sync_calendar')}", use_container_width=True):
            _sync_google_calendar(supabase)

    st.divider()

    # ─── 스케줄 리스트 ────────────────────────────
    try:
        response = (
            supabase.table("schedules")
            .select("*, models(model_name, passport_name)")
            .eq("schedule_date", view_date.isoformat())
            .order("shoot_start_time")
            .execute()
        )
        schedules = response.data or []
    except Exception as e:
        st.error(f"스케줄 로드 실패: {e}")
        schedules = []

    # ─── 스케줄 등록 폼 ───────────────────────────
    if st.session_state.get("show_schedule_form"):
        _render_schedule_form(supabase, view_date)

    # ─── 오늘의 스케줄 표시 ───────────────────────
    st.markdown(f"### 📋 {view_date.isoformat()} 스케줄 ({len(schedules)}건)")

    if not schedules:
        st.info(t("common.no_data"))
        return

    for schedule in schedules:
        model_info = schedule.get("models", {}) or {}
        model_name = model_info.get("model_name", "미지정")

        with st.container():
            # 상태에 따른 아이콘
            status = schedule.get("status", "scheduled")
            status_emoji = {
                "scheduled": "📅",
                "in_progress": "🎬",
                "completed": "✅",
                "cancelled": "❌",
            }.get(status, "❓")

            col1, col2, col3, col4, col5 = st.columns([0.5, 2, 2, 2, 1.5])

            with col1:
                st.markdown(f"### {status_emoji}")

            with col2:
                st.markdown(f"**{schedule.get('title', '제목 없음')}**")
                st.caption(f"🧑 {model_name} · 🏢 {schedule.get('client_name', '-')}")

            with col3:
                hmu = schedule.get("hmu_start_time", "-")
                shoot_start = schedule.get("shoot_start_time", "-")
                shoot_end = schedule.get("shoot_end_time", "-")
                st.caption(f"HMU: {_format_time(hmu)}")
                st.caption(f"촬영: {_format_time(shoot_start)} ~ {_format_time(shoot_end)}")

            with col4:
                work_display = schedule.get("work_type_display", "-")
                earning = float(schedule.get("earning_usd", 0))
                st.write(f"⏱ **{work_display}**")
                st.write(f"💵 ${earning:,.0f}")

            with col5:
                if status == "scheduled":
                    if st.button("🎬 시작", key=f"start_{schedule['id']}"):
                        supabase.table("schedules").update({"status": "in_progress"}).eq("id", schedule["id"]).execute()
                        st.rerun()

                elif status == "in_progress":
                    if st.button(f"✅ {t('schedule.complete')}", key=f"complete_{schedule['id']}"):
                        st.session_state[f"completing_{schedule['id']}"] = True
                        st.rerun()

            # 촬영 완료 처리 폼
            if st.session_state.get(f"completing_{schedule['id']}"):
                _render_complete_form(supabase, schedule)

            st.divider()


def _render_schedule_form(supabase, default_date):
    """스케줄 등록 폼"""
    with st.expander(f"📝 {t('schedule.add')}", expanded=True):
        # 모델 목록 로드
        try:
            models_resp = supabase.table("models").select("id, model_name").eq("status", "active").execute()
            model_options = {m["model_name"]: m["id"] for m in (models_resp.data or [])}
        except Exception:
            model_options = {}

        with st.form("schedule_form"):
            col1, col2 = st.columns(2)

            with col1:
                title = st.text_input("촬영 제목")
                selected_model = st.selectbox("모델", options=list(model_options.keys()) if model_options else ["모델 없음"])
                client_name = st.text_input(t("schedule.client_name"))
                schedule_date = st.date_input(t("schedule.schedule_date"), value=default_date)

            with col2:
                hmu_start = st.time_input(t("schedule.hmu_start"), value=datetime(2025, 1, 1, 8, 0).time())
                shoot_start = st.time_input(t("schedule.shoot_start"), value=datetime(2025, 1, 1, 9, 0).time())
                shoot_end = st.time_input(t("schedule.shoot_end"), value=datetime(2025, 1, 1, 17, 0).time())
                earning = st.number_input(t("schedule.earning"), value=0.0, step=100.0)

            col_save, col_cancel = st.columns(2)
            with col_save:
                submitted = st.form_submit_button(t("common.save"), use_container_width=True)
            with col_cancel:
                if st.form_submit_button(t("common.cancel"), use_container_width=True):
                    st.session_state["show_schedule_form"] = False
                    st.rerun()

            if submitted and title:
                # 시간 계산
                base_date = datetime.combine(schedule_date, datetime.min.time())
                start_dt = datetime.combine(schedule_date, shoot_start)
                end_dt = datetime.combine(schedule_date, shoot_end)

                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)  # 자정 넘김 처리

                work_result = calculate_work_type(start_dt, end_dt)

                data = {
                    "title": title,
                    "model_id": model_options.get(selected_model) if selected_model != "모델 없음" else None,
                    "client_name": client_name,
                    "schedule_date": schedule_date.isoformat(),
                    "hmu_start_time": datetime.combine(schedule_date, hmu_start).isoformat(),
                    "shoot_start_time": start_dt.isoformat(),
                    "shoot_end_time": end_dt.isoformat(),
                    "total_hours": work_result.rounded_hours,
                    "work_type": work_result.work_type,
                    "work_type_display": work_result.display,
                    "earning_usd": earning,
                    "booker_id": get_current_user_id(),
                }

                try:
                    supabase.table("schedules").insert(data).execute()
                    st.success(f"✅ 스케줄 등록 완료 — {work_result.display}")
                    st.session_state["show_schedule_form"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")


def _render_complete_form(supabase, schedule):
    """촬영 완료 처리 폼 (시간/Earning 확정)"""
    with st.form(f"complete_form_{schedule['id']}"):
        st.markdown("#### ⏱ 촬영 완료 처리")
        col1, col2, col3 = st.columns(3)

        with col1:
            actual_start = st.time_input(
                "실제 촬영 시작",
                value=datetime.fromisoformat(schedule["shoot_start_time"]).time() if schedule.get("shoot_start_time") else datetime(2025, 1, 1, 9, 0).time(),
                key=f"actual_start_{schedule['id']}",
            )
        with col2:
            actual_end = st.time_input(
                "실제 촬영 종료",
                value=datetime.fromisoformat(schedule["shoot_end_time"]).time() if schedule.get("shoot_end_time") else datetime(2025, 1, 1, 17, 0).time(),
                key=f"actual_end_{schedule['id']}",
            )
        with col3:
            earning = st.number_input(
                t("schedule.earning"),
                value=float(schedule.get("earning_usd", 0)),
                step=100.0,
                key=f"earning_{schedule['id']}",
            )

        # 실시간 미리보기
        sched_date = date.fromisoformat(schedule["schedule_date"])
        start_dt = datetime.combine(sched_date, actual_start)
        end_dt = datetime.combine(sched_date, actual_end)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        work_result = calculate_work_type(start_dt, end_dt)
        st.info(f"📊 판별 결과: **{work_result.display}** ({work_result.rounded_hours}시간)")

        if st.form_submit_button(f"✅ {t('schedule.complete')}", use_container_width=True):
            update_data = {
                "shoot_start_time": start_dt.isoformat(),
                "shoot_end_time": end_dt.isoformat(),
                "total_hours": work_result.rounded_hours,
                "work_type": work_result.work_type,
                "work_type_display": work_result.display,
                "earning_usd": earning,
                "status": "completed",
            }

            try:
                supabase.table("schedules").update(update_data).eq("id", schedule["id"]).execute()
                st.success("✅ 촬영 완료 처리되었습니다!")
                st.session_state.pop(f"completing_{schedule['id']}", None)
                st.rerun()
            except Exception as e:
                st.error(f"업데이트 실패: {e}")


def _sync_google_calendar(supabase):
    """Google Calendar 동기화"""
    try:
        from utils.google_calendar import fetch_events, parse_event_for_schedule
        with st.spinner("📡 Google Calendar 동기화 중..."):
            events = fetch_events(days_ahead=30, days_past=7)
            synced = 0
            for event in events:
                parsed = parse_event_for_schedule(event)
                if parsed:
                    # 중복 확인
                    existing = (
                        supabase.table("schedules")
                        .select("id")
                        .eq("google_event_id", parsed["google_event_id"])
                        .execute()
                    )
                    if not existing.data:
                        supabase.table("schedules").insert(parsed).execute()
                        synced += 1

        st.success(f"✅ {synced}건의 새 일정을 동기화했습니다.")
    except FileNotFoundError as e:
        st.warning(f"⚠️ {e}")
    except Exception as e:
        st.error(f"동기화 실패: {e}")


def _format_time(dt_str):
    """ISO datetime 문자열을 HH:MM 형태로 변환"""
    if not dt_str or dt_str == "-":
        return "-"
    try:
        return datetime.fromisoformat(dt_str).strftime("%H:%M")
    except (ValueError, TypeError):
        return str(dt_str)


main()

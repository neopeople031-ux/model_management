"""
📊 대시보드 - 역할별 맞춤 위젯
"""
import streamlit as st
from utils.auth import require_auth, get_current_user_role, get_current_user_id
from utils.i18n import t
from utils.supabase_client import get_supabase_client


@require_auth(page_name="dashboard")
def main():
    st.markdown(f"# {t('dashboard.title')}")

    role = get_current_user_role()
    supabase = get_supabase_client()

    # ─── 공통 지표 ─────────────────────────────────
    try:
        models_data = supabase.table("models").select("id, status, visa_status, arrival_date, departure_date").execute()
        schedules_data = supabase.table("schedules").select("id, schedule_date, status, earning_usd").execute()
        settlements_data = supabase.table("settlements").select("id, approval_status, net_amount").execute()
    except Exception:
        models_data = type("", (), {"data": []})()
        schedules_data = type("", (), {"data": []})()
        settlements_data = type("", (), {"data": []})()

    all_models = models_data.data or []
    all_schedules = schedules_data.data or []
    all_settlements = settlements_data.data or []

    active_models = [m for m in all_models if m.get("status") == "active"]
    from datetime import date
    today = date.today().isoformat()
    today_schedules = [s for s in all_schedules if s.get("schedule_date") == today]
    pending_settlements = [s for s in all_settlements if s.get("approval_status") in ("submitted", "first_approved")]

    # ─── 상단 KPI 카드 ─────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(t("dashboard.total_models"), len(all_models))
    with col2:
        st.metric(t("dashboard.active_models"), len(active_models))
    with col3:
        st.metric(t("dashboard.today_schedules"), len(today_schedules))
    with col4:
        st.metric(t("dashboard.pending_settlements"), len(pending_settlements))

    st.divider()

    # ─── 역할별 위젯 ──────────────────────────────
    if role == "ceo":
        _render_ceo_widgets(all_models, all_schedules, all_settlements)
    elif role in ("booker", "team_lead"):
        _render_booker_widgets(all_models, all_schedules, today_schedules)
    elif role == "marketing":
        _render_marketing_widgets(all_models)
    elif role == "accounting":
        _render_accounting_widgets(all_settlements, pending_settlements)


def _render_ceo_widgets(models, schedules, settlements):
    """대표 전용 위젯"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📈 월간 매출 현황")
        completed = [s for s in schedules if s.get("status") == "completed"]
        total_earning = sum(float(s.get("earning_usd", 0)) for s in completed)
        st.metric("Total Earning (USD)", f"${total_earning:,.2f}")

        st.markdown("### 🌍 모델 상태 분포")
        from collections import Counter
        status_counts = Counter(m.get("status", "unknown") for m in models)
        for status, count in status_counts.most_common():
            status_label = t(f"model_status.{status}")
            st.write(f"- **{status_label}**: {count}명")

    with col2:
        st.markdown("### ⚠️ 비자 만료 임박")
        _render_visa_alerts(models)

        st.markdown("### ✈️ 입출국 예정")
        _render_arrival_departure(models)


def _render_booker_widgets(models, schedules, today_schedules):
    """부커/팀장 위젯"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📋 오늘의 촬영 스케줄")
        if today_schedules:
            for s in today_schedules:
                status_emoji = {"scheduled": "📅", "in_progress": "🎬", "completed": "✅"}.get(s.get("status"), "❓")
                st.write(f"{status_emoji} **{s.get('title', '제목 없음')}** — ${float(s.get('earning_usd', 0)):,.0f}")
        else:
            st.info("오늘 예정된 촬영이 없습니다.")

    with col2:
        st.markdown("### ⚠️ 비자 만료 임박")
        _render_visa_alerts(models)


def _render_marketing_widgets(models):
    """마케팅팀 위젯"""
    st.markdown("### 🎯 현재 활동 가능 모델")
    active = [m for m in models if m.get("status") == "active"]
    st.metric("활동 중 모델", f"{len(active)}명")

    st.markdown("### 🆕 최근 등록 모델")
    sorted_models = sorted(models, key=lambda m: m.get("created_at", ""), reverse=True)[:5] if models else []
    if sorted_models:
        for m in sorted_models:
            st.write(f"- **{m.get('model_name', '')}** ({m.get('nationality', '')})")
    else:
        st.info("등록된 모델이 없습니다.")


def _render_accounting_widgets(settlements, pending):
    """정산 담당 위젯"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📝 대기 중 정산")
        st.metric("대기 건수", len(pending))
        for s in pending:
            status_label = t(f"settlement.status.{s.get('approval_status', 'draft')}")
            st.write(f"- {status_label}: ${float(s.get('net_amount', 0)):,.2f}")

    with col2:
        st.markdown("### ✅ 확정 완료")
        confirmed = [s for s in settlements if s.get("approval_status") == "final_confirmed"]
        total = sum(float(s.get("net_amount", 0)) for s in confirmed)
        st.metric("이번 달 확정 금액", f"${total:,.2f}")


def _render_visa_alerts(models):
    """비자 만료 임박 경고"""
    from datetime import date, timedelta
    today = date.today()
    alerts = []

    for m in models:
        dep = m.get("departure_date")
        if dep:
            try:
                dep_date = date.fromisoformat(dep)
                days_left = (dep_date - today).days
                if 0 <= days_left <= 30:
                    alerts.append((m.get("model_name", ""), days_left))
            except (ValueError, TypeError):
                pass

    if alerts:
        alerts.sort(key=lambda x: x[1])
        for name, days in alerts:
            emoji = "🔴" if days <= 7 else "🟡"
            st.write(f"{emoji} **{name}** — D-{days}")
    else:
        st.success("비자 만료 임박 모델이 없습니다.")


def _render_arrival_departure(models):
    """입출국 예정 모델"""
    from datetime import date, timedelta
    today = date.today()

    upcoming_arrivals = []
    upcoming_departures = []

    for m in models:
        arr = m.get("arrival_date")
        dep = m.get("departure_date")
        name = m.get("model_name", "")

        if arr:
            try:
                arr_date = date.fromisoformat(arr)
                days = (arr_date - today).days
                if 0 <= days <= 14:
                    upcoming_arrivals.append((name, days))
            except (ValueError, TypeError):
                pass

        if dep:
            try:
                dep_date = date.fromisoformat(dep)
                days = (dep_date - today).days
                if 0 <= days <= 14:
                    upcoming_departures.append((name, days))
            except (ValueError, TypeError):
                pass

    if upcoming_arrivals:
        st.caption("🛬 입국 예정")
        for name, days in sorted(upcoming_arrivals, key=lambda x: x[1]):
            st.write(f"- **{name}** (D-{days})")

    if upcoming_departures:
        st.caption("🛫 출국 예정")
        for name, days in sorted(upcoming_departures, key=lambda x: x[1]):
            st.write(f"- **{name}** (D-{days})")

    if not upcoming_arrivals and not upcoming_departures:
        st.info("2주 내 입출국 예정 모델이 없습니다.")


main()

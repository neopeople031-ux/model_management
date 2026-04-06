"""
💰 정산 관리 - 3단계 승인 워크플로우, PDF 증빙 서류 생성
"""
import streamlit as st
from datetime import date
from decimal import Decimal
from utils.auth import require_auth, get_current_user_role, get_current_user_id
from utils.i18n import t
from utils.supabase_client import get_supabase_client
from utils.settlement_calc import calculate_settlement, SpendingItem, format_usd
from utils.pdf_generator import generate_receipt_pdf, generate_delegation_pdf


@require_auth(page_name="settlements")
def main():
    st.markdown(f"# {t('settlement.title')}")

    supabase = get_supabase_client()
    role = get_current_user_role()

    # ─── 상단 액션 바 ─────────────────────────────
    tab1, tab2 = st.tabs(["📋 정산 목록", "➕ 정산서 생성"])

    with tab1:
        _render_settlement_list(supabase, role)

    with tab2:
        if role in ("booker", "team_lead", "ceo"):
            _render_create_settlement(supabase)
        else:
            st.info("정산서 생성 권한이 없습니다. 부커 또는 팀장에게 요청하세요.")


def _render_settlement_list(supabase, role):
    """정산 목록 표시"""
    try:
        response = (
            supabase.table("settlements")
            .select("*, models(model_name, passport_name, mother_agency)")
            .order("created_at", desc=True)
            .execute()
        )
        settlements = response.data or []
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        settlements = []

    if not settlements:
        st.info(t("common.no_data"))
        return

    # 상태별 필터
    filter_status = st.selectbox(
        "상태 필터",
        ["전체", "draft", "submitted", "first_approved", "final_confirmed"],
        format_func=lambda x: t(f"settlement.status.{x}") if x != "전체" else "전체",
    )

    if filter_status != "전체":
        settlements = [s for s in settlements if s.get("approval_status") == filter_status]

    for settlement in settlements:
        model = settlement.get("models", {}) or {}
        model_name = model.get("model_name", "미지정")
        status = settlement.get("approval_status", "draft")

        status_colors = {
            "draft": "🔵",
            "submitted": "🟡",
            "first_approved": "🟠",
            "final_confirmed": "🟢",
        }

        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

            with col1:
                st.markdown(f"**{status_colors.get(status, '')} {model_name}**")
                st.caption(
                    f"{settlement.get('period_start', '')} ~ {settlement.get('period_end', '')} · "
                    f"{t(f'settlement.status.{status}')}"
                )

            with col2:
                earning = float(settlement.get("total_earning", 0))
                mac = float(settlement.get("mac_amount", 0))
                st.metric("Earning", f"${earning:,.2f}")
                st.caption(f"MAC: -${mac:,.2f}")

            with col3:
                spending = float(settlement.get("total_spending", 0))
                net = float(settlement.get("net_amount", 0))
                st.metric("Spending", f"-${spending:,.2f}")
                st.metric("Net", f"${net:,.2f}")

            with col4:
                # 역할에 따른 승인 버튼
                _render_approval_actions(supabase, settlement, role, model)

            st.divider()


def _render_approval_actions(supabase, settlement, role, model):
    """역할별 승인/반려 액션 버튼"""
    status = settlement.get("approval_status", "draft")
    sid = settlement["id"]
    user_id = get_current_user_id()

    # 1단계: 부커가 제출
    if status == "draft" and role in ("booker", "team_lead", "ceo"):
        if st.button(f"📤 {t('settlement.submit')}", key=f"submit_{sid}"):
            supabase.table("settlements").update({
                "approval_status": "submitted",
                "submitted_by": user_id,
                "submitted_at": "now()",
            }).eq("id", sid).execute()
            st.rerun()

    # 2단계: 팀장이 1차 승인
    elif status == "submitted" and role in ("team_lead", "ceo"):
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(f"✅ {t('settlement.approve_first')}", key=f"approve1_{sid}"):
                supabase.table("settlements").update({
                    "approval_status": "first_approved",
                    "first_approved_by": user_id,
                    "first_approved_at": "now()",
                }).eq("id", sid).execute()
                st.rerun()
        with col_b:
            if st.button(f"↩️ {t('settlement.reject')}", key=f"reject1_{sid}"):
                supabase.table("settlements").update({
                    "approval_status": "draft",
                }).eq("id", sid).execute()
                st.rerun()

    # 3단계: 정산 담당자 최종 확정
    elif status == "first_approved" and role in ("accounting", "ceo"):
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(f"🔒 {t('settlement.confirm_final')}", key=f"confirm_{sid}"):
                supabase.table("settlements").update({
                    "approval_status": "final_confirmed",
                    "final_confirmed_by": user_id,
                    "final_confirmed_at": "now()",
                }).eq("id", sid).execute()
                st.rerun()
        with col_b:
            if st.button(f"↩️ {t('settlement.reject')}", key=f"reject2_{sid}"):
                supabase.table("settlements").update({
                    "approval_status": "submitted",
                }).eq("id", sid).execute()
                st.rerun()

    # 확정 완료 - PDF 다운로드
    elif status == "final_confirmed":
        _render_pdf_downloads(settlement, model)


def _render_pdf_downloads(settlement, model):
    """PDF 다운로드 버튼"""
    # 영수증 PDF
    try:
        spending_resp = (
            get_supabase_client()
            .table("spending_items")
            .select("*")
            .eq("settlement_id", settlement["id"])
            .execute()
        )
        spending_items = spending_resp.data or []
    except Exception:
        spending_items = []

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button(f"📄 {t('settlement.download_receipt')}", key=f"receipt_{settlement['id']}"):
            pdf_bytes = generate_receipt_pdf(model, settlement, spending_items)
            st.download_button(
                "📥 영수증 다운로드",
                data=pdf_bytes,
                file_name=f"receipt_{model.get('model_name', 'unknown')}.pdf",
                mime="application/pdf",
                key=f"dl_receipt_{settlement['id']}",
            )

    with col_b:
        if st.button(f"📄 {t('settlement.download_delegation')}", key=f"delegation_{settlement['id']}"):
            pdf_bytes = generate_delegation_pdf(model, settlement)
            st.download_button(
                "📥 위임장 다운로드",
                data=pdf_bytes,
                file_name=f"delegation_{model.get('model_name', 'unknown')}.pdf",
                mime="application/pdf",
                key=f"dl_deleg_{settlement['id']}",
            )


def _render_create_settlement(supabase):
    """정산서 생성 폼"""
    st.markdown("### 📝 새 정산서 생성")

    # 모델 목록 로드
    try:
        models_resp = supabase.table("models").select("id, model_name, mac_rate").execute()
        model_options = {m["model_name"]: m for m in (models_resp.data or [])}
    except Exception:
        model_options = {}
        st.error("모델 데이터를 불러올 수 없습니다.")

    if not model_options:
        return

    with st.form("create_settlement"):
        selected_model_name = st.selectbox("모델 선택", list(model_options.keys()))
        selected_model = model_options.get(selected_model_name, {})

        col1, col2 = st.columns(2)
        with col1:
            period_start = st.date_input("정산 시작일", value=date.today().replace(day=1))
        with col2:
            period_end = st.date_input("정산 종료일", value=date.today())

        st.divider()

        # 완료된 스케줄 자동 조회
        st.markdown("#### 📊 Earning 내역")
        st.caption("정산 기간 내 완료된 촬영 건의 Earning을 자동 집계합니다.")

        st.divider()

        # Spending 수동 입력
        st.markdown("#### 💸 Spending 내역")
        spending_count = st.number_input("지출 항목 수", min_value=0, max_value=20, value=0, step=1)

        spending_items = []
        for i in range(int(spending_count)):
            scol1, scol2, scol3, scol4 = st.columns([2, 3, 2, 2])
            with scol1:
                cat = st.selectbox(
                    "분류", 
                    ["hospital", "sim_card", "transport", "accommodation", "food", "other"],
                    format_func=lambda x: t(f"spending.categories.{x}"),
                    key=f"spend_cat_{i}",
                )
            with scol2:
                desc = st.text_input("설명", key=f"spend_desc_{i}")
            with scol3:
                amt = st.number_input("금액(USD)", min_value=0.0, step=10.0, key=f"spend_amt_{i}")
            with scol4:
                spend_date = st.date_input("날짜", key=f"spend_date_{i}")
            spending_items.append({"category": cat, "description": desc, "amount": amt, "date": spend_date.isoformat()})

        if st.form_submit_button(t("common.save"), use_container_width=True):
            model_id = selected_model.get("id")
            mac_rate = float(selected_model.get("mac_rate", 0))

            # 자동 Earning 집계
            try:
                schedules_resp = (
                    supabase.table("schedules")
                    .select("earning_usd")
                    .eq("model_id", model_id)
                    .eq("status", "completed")
                    .gte("schedule_date", period_start.isoformat())
                    .lte("schedule_date", period_end.isoformat())
                    .execute()
                )
                earnings = [Decimal(str(s.get("earning_usd", 0))) for s in (schedules_resp.data or [])]
            except Exception:
                earnings = []

            # 정산 계산
            calc_spending = [
                SpendingItem(
                    category=s["category"],
                    description=s["description"],
                    amount=Decimal(str(s["amount"])),
                    date=s["date"],
                )
                for s in spending_items
                if s["amount"] > 0
            ]

            result = calculate_settlement(
                earning_amounts=earnings,
                mac_rate=Decimal(str(mac_rate)),
                spending_items=calc_spending,
            )

            # DB 저장
            try:
                settlement_data = {
                    "model_id": model_id,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "total_earning": float(result.total_earning),
                    "mac_rate": mac_rate,
                    "mac_amount": float(result.mac_amount),
                    "total_spending": float(result.total_spending),
                    "net_amount": float(result.net_amount),
                    "approval_status": "draft",
                    "submitted_by": get_current_user_id(),
                }
                settlement_resp = supabase.table("settlements").insert(settlement_data).execute()
                settlement_id = settlement_resp.data[0]["id"]

                # Spending 항목 저장
                for item in calc_spending:
                    supabase.table("spending_items").insert({
                        "settlement_id": settlement_id,
                        "category": item.category,
                        "description": item.description,
                        "amount": float(item.amount),
                        "date": item.date,
                    }).execute()

                st.success(
                    f"✅ 정산서가 생성되었습니다!\n\n"
                    f"- Earning: {format_usd(result.total_earning)}\n"
                    f"- MAC ({mac_rate}%): -{format_usd(result.mac_amount)}\n"
                    f"- Spending: -{format_usd(result.total_spending)}\n"
                    f"- **Net: {format_usd(result.net_amount)}**"
                )
            except Exception as e:
                st.error(f"정산서 저장 실패: {e}")


main()

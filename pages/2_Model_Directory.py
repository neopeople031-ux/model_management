"""
👤 모델 관리 - 통합 모델 DB, 검색/필터, 엑셀 추출
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.auth import require_auth, get_current_user_role
from utils.i18n import t, get_lang
from utils.supabase_client import get_supabase_client
from utils.excel_export import dataframe_to_excel, models_to_dataframe, generate_upload_template
from utils.excel_import import parse_excel, dataframe_to_db_records
@require_auth(page_name="model_directory")
def main():
    st.markdown(f"# {t('model.title')}")

    # 세션 초기화
    if "show_form" not in st.session_state:
        st.session_state.show_form = False
    if "show_upload" not in st.session_state:
        st.session_state.show_upload = False
    if "edit_model_id" not in st.session_state:
        st.session_state.edit_model_id = None

    supabase = get_supabase_client()

    # ─── 상단 액션 바 ─────────────────────────────
    col1, col2, col3, col4 = st.columns([4, 1, 1, 1])

    with col1:
        search_query = st.text_input(
            t("model.search"),
            placeholder="이름, 국적, 에이전시...",
            label_visibility="collapsed",
        )

    with col2:
        if st.button(f"➕ {t('model.register')}", use_container_width=True):
            st.session_state.show_form = True
            st.session_state.edit_model_id = None

    with col3:
        if st.button(f"📤 {t('model.upload_excel')}", use_container_width=True):
            st.session_state.show_upload = not st.session_state.show_upload

    with col4:
        # 엑셀 다운로드 (필터링된 데이터)
        excel_btn = st.button(f"📥 {t('model.export_excel')}", use_container_width=True)

    # ─── 필터 사이드바 ─────────────────────────────
    with st.expander(f"🔍 {t('model.filter')}", expanded=False):
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)

        with fcol1:
            filter_nationality = st.text_input(t("model.nationality"), key="filter_nat")
        with fcol2:
            filter_gender = st.selectbox(t("model.gender"), ["전체", "Male", "Female"], key="filter_gender")
        with fcol3:
            filter_status = st.selectbox(
                t("model.status"),
                ["전체", "pre_arrival", "active", "departed", "contract_ended"],
                format_func=lambda x: t(f"model_status.{x}") if x != "전체" else "전체",
                key="filter_status",
            )
        with fcol4:
            filter_visa = st.selectbox(
                t("model.visa_status"),
                ["전체", "pending", "applied", "approved", "expired"],
                format_func=lambda x: t(f"visa.{x}") if x != "전체" else "전체",
                key="filter_visa",
            )

    # ─── 데이터 로드 ──────────────────────────────
    try:
        query = supabase.table("models").select("*").order("created_at", desc=True)

        if search_query:
            query = query.or_(
                f"model_name.ilike.%{search_query}%,"
                f"passport_name.ilike.%{search_query}%,"
                f"nationality.ilike.%{search_query}%,"
                f"mother_agency.ilike.%{search_query}%"
            )

        if filter_nationality:
            query = query.ilike("nationality", f"%{filter_nationality}%")
        if filter_gender != "전체":
            query = query.eq("gender", filter_gender)
        if filter_status != "전체":
            query = query.eq("status", filter_status)
        if filter_visa != "전체":
            query = query.eq("visa_status", filter_visa)

        response = query.execute()
        models = response.data or []
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        models = []

    # ─── 엑셀 다운로드 처리 ────────────────────────
    if excel_btn and models:
        df = models_to_dataframe(models, lang=get_lang())
        excel_bytes, filename = dataframe_to_excel(df, sheet_name="Models", filename_prefix="models")
        st.download_button(
            label="📥 다운로드",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ─── 엑셀 대량 업로드 섹션 ──────────────────────
    if st.session_state.show_upload:
        _render_upload_section(supabase)

    # ─── 모델 등록/수정 폼 ────────────────────────
    if st.session_state.show_form:
        _render_model_form(supabase)

    # ─── 모델 리스트 ──────────────────────────────
    st.markdown(f"### 모델 목록 ({len(models)}건)")

    if not models:
        st.info(t("common.no_data"))
        return

    for model in models:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 1])

            with col1:
                if model.get("profile_photo_url"):
                    st.image(model["profile_photo_url"], width=60)
                else:
                    st.markdown("👤")

            with col2:
                st.markdown(f"**{model.get('model_name', '')}**")
                st.caption(f"{model.get('passport_name', '')} · {model.get('nationality', '')}")

            with col3:
                status = model.get("status", "")
                visa = model.get("visa_status", "")
                st.write(f"📌 {t(f'model_status.{status}')}")
                st.write(f"🛂 {t(f'visa.{visa}')}")

            with col4:
                st.caption(f"키: {model.get('height', '-')}cm")
                st.caption(f"에이전시: {model.get('mother_agency', '-')}")

            with col5:
                if st.button("✏️", key=f"edit_{model['id']}", use_container_width=True):
                    st.session_state.edit_model_id = model["id"]
                    st.session_state.show_form = True
                    st.rerun()

            st.divider()


def _render_model_form(supabase):
    """모델 등록/수정 폼 (개선 버전)"""
    editing = st.session_state.edit_model_id is not None
    title = t("model.edit") if editing else t("model.register")

    existing = {}
    if editing:
        try:
            resp = supabase.table("models").select("*").eq("id", st.session_state.edit_model_id).single().execute()
            existing = resp.data or {}
        except Exception:
            existing = {}

    # 기존 국적 목록 로드 (중복 제거)
    try:
        nat_resp = supabase.table("models").select("nationality").execute()
        existing_nationalities = sorted(set(
            r["nationality"] for r in (nat_resp.data or [])
            if r.get("nationality") and r["nationality"].strip()
        ))
    except Exception:
        existing_nationalities = []

    # 자주 사용하는 국적 기본 목록
    default_nationalities = [
        "US", "UK", "France", "Germany", "Italy", "Spain", "Brazil",
        "Russia", "Ukraine", "Netherlands", "Australia", "Japan",
        "South Korea", "China", "Thailand", "Philippines",
    ]
    all_nationalities = sorted(set(existing_nationalities + default_nationalities))

    with st.expander(f"📝 {title}", expanded=True):
        # ─── 사진 업로드 (폼 바깥) ────────────────
        st.markdown(f"**📷 {t('model.profile_photo')}**")
        if existing.get("profile_photo_url"):
            st.image(existing["profile_photo_url"], width=120)

        uploaded_photo = st.file_uploader(
            t("model.profile_photo"),
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
            key="model_photo_upload",
        )

        st.divider()

        # ─── 등록/수정 폼 ────────────────────────
        with st.form("model_form"):
            col1, col2 = st.columns(2)

            with col1:
                model_name = st.text_input(t("model.model_name"), value=existing.get("model_name", ""))
                passport_name = st.text_input(t("model.passport_name"), value=existing.get("passport_name", ""))
                dob = st.date_input(t("model.date_of_birth"),
                                    value=date.fromisoformat(existing["date_of_birth"]) if existing.get("date_of_birth") else date(2000, 1, 1))

                # 국적: 기존 목록에서 선택 또는 직접 입력
                nat_options = ["직접 입력"] + all_nationalities
                existing_nat = existing.get("nationality", "")
                if existing_nat and existing_nat in all_nationalities:
                    nat_default_idx = all_nationalities.index(existing_nat) + 1
                else:
                    nat_default_idx = 0

                nat_select = st.selectbox(
                    t("model.nationality"),
                    nat_options,
                    index=nat_default_idx,
                    key="nat_select",
                )
                if nat_select == "직접 입력":
                    nationality = st.text_input(
                        "국적 직접 입력",
                        value=existing_nat if existing_nat not in all_nationalities else "",
                        key="nat_manual",
                    )
                else:
                    nationality = nat_select

                gender = st.selectbox(t("model.gender"), ["Male", "Female"],
                                      index=0 if existing.get("gender", "Male") == "Male" else 1)
                mother_agency = st.text_input(t("model.mother_agency"), value=existing.get("mother_agency", ""))

            with col2:
                height = st.number_input(t("model.height"), value=float(existing.get("height", 170)), min_value=100.0, max_value=220.0, step=0.5)
                bust = st.number_input(f"{t('model.bust')} (inch)", value=float(existing.get("bust", 0)), step=0.5, format="%.1f")
                waist = st.number_input(f"{t('model.waist')} (inch)", value=float(existing.get("waist", 0)), step=0.5, format="%.1f")
                hips = st.number_input(f"{t('model.hips')} (inch)", value=float(existing.get("hips", 0)), step=0.5, format="%.1f")

                # 신발 사이즈: 체계 선택 + 값 입력
                shoe_col1, shoe_col2 = st.columns([1, 2])
                with shoe_col1:
                    # 기존 값에서 체계 파싱
                    existing_shoe = existing.get("shoe_size", "")
                    shoe_systems = ["US", "UK", "EU", "KR(mm)"]
                    default_system_idx = 0
                    for i, sys_name in enumerate(shoe_systems):
                        if existing_shoe.startswith(sys_name.split("(")[0]):
                            default_system_idx = i
                            break

                    shoe_system = st.selectbox(
                        "체계",
                        shoe_systems,
                        index=default_system_idx,
                        key="shoe_system",
                    )
                with shoe_col2:
                    # 기존 값에서 숫자만 추출
                    import re
                    shoe_num_match = re.search(r"[\d.]+", existing_shoe) if existing_shoe else None
                    shoe_val = shoe_num_match.group() if shoe_num_match else ""
                    shoe_value = st.text_input(
                        t("model.shoe_size"),
                        value=shoe_val,
                        placeholder="예: 250, 9, 42",
                        key="shoe_value",
                    )
                shoe_size = f"{shoe_system.split('(')[0]} {shoe_value}".strip() if shoe_value else ""

                guarantee = st.number_input(t("model.guarantee"), value=float(existing.get("guarantee_amount", 0)), step=100.0)

            st.divider()

            col3, col4 = st.columns(2)
            with col3:
                mac_rate = st.number_input(t("model.mac_rate"), value=float(existing.get("mac_rate", 20)), min_value=0.0, max_value=100.0)

                contract_start = st.date_input(t("model.contract_start"),
                                               value=date.fromisoformat(existing["contract_start"]) if existing.get("contract_start") else date.today())
                contract_end = st.date_input(t("model.contract_end"),
                                             value=date.fromisoformat(existing["contract_end"]) if existing.get("contract_end") else date.today(),
                                             min_value=contract_start)

                # 계약기간 자동 계산
                contract_days = (contract_end - contract_start).days
                if contract_days >= 0:
                    months = contract_days // 30
                    days = contract_days % 30
                    duration_text = f"📅 계약기간: **{months}개월 {days}일** ({contract_days}일)"
                    st.info(duration_text)
                else:
                    st.error("⚠️ 계약종료일이 시작일보다 빠릅니다.")

            with col4:
                visa_status = st.selectbox(
                    t("model.visa_status"),
                    ["pending", "applied", "approved", "expired"],
                    format_func=lambda x: t(f"visa.{x}"),
                    index=["pending", "applied", "approved", "expired"].index(existing.get("visa_status", "pending")),
                )
                arrival_date = st.date_input(t("model.arrival_date"),
                                             value=date.fromisoformat(existing["arrival_date"]) if existing.get("arrival_date") else None)
                departure_date = st.date_input(t("model.departure_date"),
                                               value=date.fromisoformat(existing["departure_date"]) if existing.get("departure_date") else None,
                                               min_value=arrival_date if arrival_date else None)

            notes = st.text_area(t("model.notes"), value=existing.get("notes", ""))

            col_save, col_cancel = st.columns(2)
            with col_save:
                submitted = st.form_submit_button(t("common.save"), use_container_width=True)
            with col_cancel:
                cancelled = st.form_submit_button(t("common.cancel"), use_container_width=True)

            if cancelled:
                st.session_state.show_form = False
                st.session_state.edit_model_id = None
                st.rerun()

            if submitted:
                # 추가 검증
                has_error = False
                if not model_name or not passport_name:
                    st.error("활동명과 여권명은 필수입니다.")
                    has_error = True
                if contract_end < contract_start:
                    st.error("계약종료일이 계약시작일보다 빠릅니다.")
                    has_error = True
                if arrival_date and departure_date and departure_date < arrival_date:
                    st.error("출국예정일이 입국예정일보다 빠릅니다.")
                    has_error = True

                if not has_error:
                    # 사진 업로드 처리
                    photo_url = existing.get("profile_photo_url")
                    if uploaded_photo is not None:
                        photo_url = _upload_profile_photo(supabase, uploaded_photo, model_name)

                    data = {
                        "model_name": model_name,
                        "passport_name": passport_name,
                        "date_of_birth": dob.isoformat(),
                        "nationality": nationality,
                        "gender": gender,
                        "height": height,
                        "bust": bust,
                        "waist": waist,
                        "hips": hips,
                        "shoe_size": shoe_size,
                        "mother_agency": mother_agency,
                        "guarantee_amount": guarantee,
                        "mac_rate": mac_rate,
                        "contract_start": contract_start.isoformat(),
                        "contract_end": contract_end.isoformat(),
                        "visa_status": visa_status,
                        "arrival_date": arrival_date.isoformat() if arrival_date else None,
                        "departure_date": departure_date.isoformat() if departure_date else None,
                        "notes": notes,
                    }

                    if photo_url:
                        data["profile_photo_url"] = photo_url

                    try:
                        if editing:
                            supabase.table("models").update(data).eq("id", st.session_state.edit_model_id).execute()
                            st.success("✅ 모델 정보가 수정되었습니다.")
                        else:
                            supabase.table("models").insert(data).execute()
                            st.success("✅ 모델이 등록되었습니다.")

                        st.session_state.show_form = False
                        st.session_state.edit_model_id = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"저장 실패: {e}")


def _upload_profile_photo(supabase, uploaded_file, model_name: str) -> str | None:
    """프로필 사진을 Supabase Storage에 업로드합니다."""
    import uuid

    try:
        ext = uploaded_file.name.split(".")[-1].lower()
        filename = f"models/{uuid.uuid4().hex[:12]}_{model_name.replace(' ', '_')}.{ext}"
        file_bytes = uploaded_file.getvalue()

        # Storage 업로드
        supabase.storage.from_("model-photos").upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": uploaded_file.type},
        )

        # Public URL 생성
        result = supabase.storage.from_("model-photos").get_public_url(filename)
        return result
    except Exception as e:
        st.warning(f"사진 업로드 실패: {e}. 모델 정보는 저장됩니다.")
        return None


def _render_upload_section(supabase):
    """엑셀 대량 업로드 섹션"""
    with st.expander(f"📤 {t('model.upload_section')}", expanded=True):
        # 템플릿 다운로드
        tmpl_col1, tmpl_col2 = st.columns([3, 1])
        with tmpl_col1:
            st.markdown(f"**1️⃣ {t('model.download_template')}** - 양식에 맞는 엑셀 파일을 먼저 다운로드하세요.")
        with tmpl_col2:
            tmpl_bytes, tmpl_name = generate_upload_template(lang=get_lang())
            st.download_button(
                label=f"📥 {t('model.download_template')}",
                data=tmpl_bytes,
                file_name=tmpl_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        st.divider()

        # 파일 업로드
        st.markdown(f"**2️⃣ {t('model.upload_excel')}** - 데이터를 채운 엑셀 파일을 업로드하세요.")
        uploaded_file = st.file_uploader(
            t("model.upload_excel"),
            type=["xlsx"],
            label_visibility="collapsed",
            key="excel_upload_file",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            df, errors = parse_excel(file_bytes)

            # 에러 표시
            if errors:
                st.warning(t("model.upload_error", count=len(errors)))
                with st.expander("⚠️ 오류 상세", expanded=False):
                    for err in errors:
                        if err["row"] > 0:
                            st.markdown(f"- **행 {err['row']}** · `{err['field']}`: {err['message']}")
                        else:
                            st.error(err["message"])

            # 미리보기
            if not df.empty:
                st.markdown(f"**3️⃣ {t('model.upload_preview')}** ({len(df)}건)")
                st.dataframe(df, use_container_width=True, height=300)

                # 에러 없는 행만 등록 가능
                error_rows = {e["row"] for e in errors if e["row"] > 0}
                valid_count = len(df) - len(error_rows)

                if valid_count > 0:
                    st.info(f"✅ 등록 가능: **{valid_count}건** / 총 {len(df)}건")

                    if st.button(
                        f"📤 {t('model.bulk_register')} ({valid_count}건)",
                        type="primary",
                        use_container_width=True,
                    ):
                        # 에러 행 제외
                        valid_df = df.drop(
                            [idx for idx in df.index if (idx + 2) in error_rows],
                            errors="ignore",
                        )
                        records = dataframe_to_db_records(valid_df)

                        if records:
                            try:
                                supabase.table("models").insert(records).execute()
                                st.success(t("model.upload_success", count=len(records)))
                                st.session_state.show_upload = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"등록 실패: {e}")
                        else:
                            st.error("유효한 데이터가 없습니다.")
                else:
                    st.error("등록 가능한 유효 데이터가 없습니다. 오류를 수정 후 다시 업로드하세요.")


main()

"""
인증 및 권한 관리 모듈

Google OAuth (PKCE flow) + 이메일/비밀번호 로그인 지원
"""
import streamlit as st
from functools import wraps
from utils.supabase_client import get_supabase_client

# 역할 정의
ROLES = {
    "ceo": "대표",
    "team_lead": "팀장",
    "booker": "부커",
    "marketing": "마케팅",
    "accounting": "정산담당",
}

# 사용자 승인 상태
APPROVAL_STATUS = {
    "pending": "승인 대기",
    "approved": "승인 완료",
    "rejected": "거절",
}

# 페이지별 접근 권한 설정
PAGE_PERMISSIONS = {
    "dashboard": ["ceo", "team_lead", "booker", "marketing", "accounting"],
    "model_directory": ["ceo", "team_lead", "booker", "marketing", "accounting"],
    "schedules": ["ceo", "team_lead", "booker"],
    "settlements": ["ceo", "team_lead", "booker", "accounting"],
    "admin": ["ceo"],
}


def init_session_state():
    """세션 상태 초기화"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "user_approved" not in st.session_state:
        st.session_state.user_approved = False


def login_with_google():
    """
    Supabase의 Google OAuth를 통한 로그인 (PKCE flow)

    PKCE flow를 사용하면 토큰이 URL query parameter로 전달되어
    Streamlit에서도 처리할 수 있습니다.
    """
    supabase = get_supabase_client()

    try:
        import os
        redirect_url = os.environ.get("SITE_URL", "http://localhost:8501")
        
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url,
                "query_params": {
                    "access_type": "offline",
                    "prompt": "consent",
                },
            },
        })

        if response and response.url:
            st.markdown(
                f'<a href="{response.url}" target="_self" '
                f'style="display:inline-block;padding:12px 24px;background:#000;'
                f'color:#fff;text-decoration:none;border-radius:8px;font-weight:600;'
                f'width:100%;text-align:center;">'
                f'🔐 Google 계정으로 로그인</a>',
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.error(f"Google 로그인 초기화 실패: {e}")


def login_with_email(email: str, password: str) -> bool:
    """이메일/비밀번호 로그인"""
    supabase = get_supabase_client()

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })

        if response and response.user:
            st.session_state.authenticated = True
            st.session_state.user = response.user

            user_data = _get_or_create_user(response.user)
            if user_data:
                st.session_state.user_role = user_data.get("role", "booker")
                st.session_state.user_name = user_data.get("name", response.user.email)
                st.session_state.user_approved = user_data.get("approval_status") == "approved"
            return True
    except Exception as e:
        error_msg = str(e)
        if "Invalid login" in error_msg or "invalid" in error_msg.lower():
            st.error("이메일 또는 비밀번호가 올바르지 않습니다.")
        elif "Email not confirmed" in error_msg:
            st.error("이메일 확인이 필요합니다. 이메일을 확인해 주세요.")
        else:
            st.error(f"로그인 실패: {e}")
    return False


def signup_with_email(email: str, password: str, name: str) -> bool:
    """이메일/비밀번호 회원가입"""
    supabase = get_supabase_client()

    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"full_name": name},
            },
        })

        if response and response.user:
            st.success("✅ 회원가입 완료! 이메일 확인 후 로그인하세요.")
            st.info("📧 인증 이메일을 확인해 주세요. (스팸함도 확인)")
            return True
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            st.error("이미 등록된 이메일입니다.")
        else:
            st.error(f"회원가입 실패: {e}")
    return False


def handle_auth_callback() -> bool:
    """
    OAuth 콜백 처리

    Google OAuth 완료 후 URL에 전달된 파라미터로 세션을 확인합니다.
    """
    supabase = get_supabase_client()

    # PKCE flow: query param에서 code 확인
    query_params = st.query_params
    code = query_params.get("code")

    if code:
        try:
            response = supabase.auth.exchange_code_for_session({"auth_code": code})
            if response and response.user:
                st.session_state.authenticated = True
                st.session_state.user = response.user

                user_data = _get_or_create_user(response.user)
                if user_data:
                    st.session_state.user_role = user_data.get("role", "booker")
                    st.session_state.user_name = user_data.get("name", response.user.email)
                    st.session_state.user_approved = user_data.get("approval_status") == "approved"

                # URL에서 code 파라미터 제거
                st.query_params.clear()
                return True
        except Exception as e:
            st.error(f"인증 콜백 처리 실패: {e}")
            st.query_params.clear()
            return False

    # 기존 세션 확인
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state.authenticated = True
            st.session_state.user = session.user

            user_data = _get_or_create_user(session.user)
            if user_data:
                st.session_state.user_role = user_data.get("role", "booker")
                st.session_state.user_name = user_data.get("name", session.user.email)
                st.session_state.user_approved = user_data.get("approval_status") == "approved"
                return True
    except Exception:
        pass

    return False


def _get_or_create_user(auth_user) -> dict | None:
    """
    users 테이블에서 사용자 조회, 없으면 pending 상태로 생성
    """
    supabase = get_supabase_client()

    try:
        response = (
            supabase.table("users")
            .select("*")
            .eq("id", auth_user.id)
            .execute()
        )

        if response.data:
            return response.data[0]

        # 신규 사용자: pending 상태로 자동 등록
        user_meta = auth_user.user_metadata or {}
        new_user = {
            "id": auth_user.id,
            "email": auth_user.email,
            "name": user_meta.get("full_name", user_meta.get("name", auth_user.email)),
            "role": "booker",
            "approval_status": "pending",
            "avatar_url": user_meta.get("avatar_url", ""),
        }

        insert_resp = supabase.table("users").insert(new_user).execute()
        return insert_resp.data[0] if insert_resp.data else new_user

    except Exception as e:
        st.error(f"사용자 정보 처리 실패: {e}")
        return None


def logout():
    """로그아웃 처리"""
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except Exception:
        pass

    for key in ["authenticated", "user", "user_role", "user_name", "user_approved"]:
        st.session_state.pop(key, None)
    st.rerun()


def get_current_user_role() -> str | None:
    """현재 사용자의 역할 반환"""
    return st.session_state.get("user_role")


def get_current_user_id() -> str | None:
    """현재 사용자의 ID 반환"""
    user = st.session_state.get("user")
    return user.id if user else None


def is_approved() -> bool:
    """현재 사용자가 관리자 승인을 받았는지 확인"""
    return st.session_state.get("user_approved", False)


def has_permission(page: str) -> bool:
    """현재 사용자가 해당 페이지에 접근 가능한지 확인"""
    if not is_approved():
        return False
    role = get_current_user_role()
    if not role:
        return False
    allowed_roles = PAGE_PERMISSIONS.get(page, [])
    return role in allowed_roles


def require_auth(page_name: str = None):
    """인증, 승인, 권한 확인 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            init_session_state()

            # 1. 인증 확인
            if not st.session_state.authenticated:
                show_login_page()
                st.stop()

            # 2. 관리자 승인 확인
            if not is_approved():
                show_pending_approval_page()
                st.stop()

            # 3. 페이지 권한 확인
            if page_name and not has_permission(page_name):
                st.error("🚫 이 페이지에 대한 접근 권한이 없습니다.")
                st.stop()

            return func(*args, **kwargs)
        return wrapper
    return decorator


def show_login_page():
    """로그인 페이지 - Google OAuth + 이메일/비밀번호"""
    # 먼저 기존 세션 확인
    if handle_auth_callback():
        st.rerun()
        return

    st.markdown("## 🔐 로그인")
    st.markdown("Model Management System에 접속하려면 로그인하세요.")
    st.markdown("")

    tab1, tab2, tab3 = st.tabs(["📧 이메일 로그인", "📝 회원가입", "🔐 Google 로그인"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("이메일", placeholder="name@company.com")
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", use_container_width=True)

            if submitted and email and password:
                if login_with_email(email, password):
                    st.rerun()

    with tab2:
        with st.form("signup_form"):
            s_name = st.text_input("이름", placeholder="홍길동")
            s_email = st.text_input("이메일", placeholder="name@company.com", key="signup_email")
            s_password = st.text_input("비밀번호 (6자 이상)", type="password", key="signup_pw")
            s_submitted = st.form_submit_button("회원가입", use_container_width=True)

            if s_submitted and s_email and s_password and s_name:
                if len(s_password) < 6:
                    st.error("비밀번호는 6자 이상이어야 합니다.")
                else:
                    signup_with_email(s_email, s_password, s_name)

    with tab3:
        st.markdown("")
        login_with_google()

    st.markdown("")
    st.caption("최초 로그인 시 관리자 승인이 필요합니다.")


def show_pending_approval_page():
    """관리자 승인 대기 화면"""
    st.markdown("## ⏳ 승인 대기 중")
    st.info(
        "가입이 완료되었습니다! 관리자가 계정을 승인하면 시스템을 이용할 수 있습니다.\n\n"
        "승인이 완료되면 페이지를 새로고침하세요."
    )

    user = st.session_state.get("user")
    if user:
        st.caption(f"📧 {user.email}")

    if st.button("🔄 새로고침", use_container_width=True):
        if handle_auth_callback():
            st.rerun()

    st.divider()

    if st.button("🚪 로그아웃", use_container_width=True):
        logout()


# ─── 관리자 기능 ──────────────────────────────────

def render_admin_panel():
    """관리자 전용: 사용자 승인/역할 관리 패널"""
    role = get_current_user_role()
    if role != "ceo":
        st.error("관리자 권한이 필요합니다.")
        return

    st.markdown("### 👥 사용자 관리")
    supabase = get_supabase_client()

    try:
        response = supabase.table("users").select("*").order("created_at", desc=True).execute()
        users = response.data or []
    except Exception as e:
        st.error(f"사용자 목록 로드 실패: {e}")
        return

    # 승인 대기 사용자
    pending_users = [u for u in users if u.get("approval_status") == "pending"]
    if pending_users:
        st.warning(f"⏳ 승인 대기 중인 사용자: {len(pending_users)}명")
        for user in pending_users:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                st.write(f"**{user.get('name', '')}**")
                st.caption(user.get("email", ""))
            with col2:
                new_role = st.selectbox(
                    "역할",
                    list(ROLES.keys()),
                    format_func=lambda x: ROLES[x],
                    key=f"role_{user['id']}",
                )
            with col3:
                if st.button("✅ 승인", key=f"approve_{user['id']}"):
                    supabase.table("users").update({
                        "approval_status": "approved",
                        "role": new_role,
                    }).eq("id", user["id"]).execute()
                    st.rerun()
            with col4:
                if st.button("❌ 거절", key=f"reject_{user['id']}"):
                    supabase.table("users").update({
                        "approval_status": "rejected",
                    }).eq("id", user["id"]).execute()
                    st.rerun()
        st.divider()

    # 전체 사용자 목록
    st.markdown("#### 전체 사용자")
    approved_users = [u for u in users if u.get("approval_status") == "approved"]
    for user in approved_users:
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            st.write(f"**{user.get('name', '')}** ({user.get('email', '')})")
        with col2:
            current_role = user.get("role", "booker")
            new_role = st.selectbox(
                "역할 변경",
                list(ROLES.keys()),
                format_func=lambda x: ROLES[x],
                index=list(ROLES.keys()).index(current_role) if current_role in ROLES else 0,
                key=f"change_role_{user['id']}",
                label_visibility="collapsed",
            )
            if new_role != current_role:
                if st.button("저장", key=f"save_role_{user['id']}"):
                    supabase.table("users").update({"role": new_role}).eq("id", user["id"]).execute()
                    st.toast(f"{user.get('name')}의 역할이 {ROLES[new_role]}(으)로 변경되었습니다.")
                    st.rerun()
        with col3:
            st.caption(ROLES.get(user.get("role", ""), ""))

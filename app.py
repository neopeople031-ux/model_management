"""
Model Management System - 메인 진입점
외국인 모델 통합 관리 시스템
"""
import streamlit as st
from utils.auth import init_session_state, logout, get_current_user_role, ROLES
from utils.i18n import t, render_lang_toggle, get_lang

# 페이지 설정
st.set_page_config(
    page_title="Model Management System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 커스텀 CSS
st.markdown("""
<style>
    /* 무채색 테마 강화 */
    .stApp {
        font-family: 'Inter', 'Pretendard', -apple-system, sans-serif;
    }

    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #FAFAFA;
        border-right: 1px solid #E5E5E5;
    }

    /* 버튼 스타일 */
    .stButton > button {
        background-color: #000000;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        background-color: #333333;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    /* 카드 스타일 */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E5E5E5;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
        transition: all 0.2s ease;
    }

    .metric-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }

    /* 헤더 스타일 */
    h1 {
        color: #1A1A1A;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    h2, h3 {
        color: #333333;
        font-weight: 600;
    }

    /* 데이터프레임 스타일 */
    .stDataFrame {
        border: 1px solid #E5E5E5;
        border-radius: 8px;
    }

    /* 상태 배지 */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .status-active { background: #E8F5E9; color: #2E7D32; }
    .status-pending { background: #FFF3E0; color: #E65100; }
    .status-completed { background: #E3F2FD; color: #1565C0; }
    .status-expired { background: #FFEBEE; color: #C62828; }

    /* 로고 영역 */
    .logo-container {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 1px solid #E5E5E5;
        margin-bottom: 1rem;
    }

    .logo-text {
        font-size: 1.3rem;
        font-weight: 700;
        color: #000000;
        letter-spacing: -0.03em;
    }

    .logo-subtitle {
        font-size: 0.7rem;
        color: #888888;
        text-transform: uppercase;
        letter-spacing: 0.15em;
    }
</style>
""", unsafe_allow_html=True)


def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        # 로고
        st.markdown("""
        <div class="logo-container">
            <div class="logo-text">🎯 MODEL MGMT</div>
            <div class="logo-subtitle">Management System</div>
        </div>
        """, unsafe_allow_html=True)

        # 언어 토글
        render_lang_toggle()

        st.divider()

        # 사용자 정보
        role = get_current_user_role()
        user_name = st.session_state.get("user_name", "사용자")
        role_display = t(f"roles.{role}") if role else ""

        st.markdown(f"**{user_name}**")
        st.caption(role_display)

        st.divider()

        # 로그아웃
        if st.button(t("auth.logout"), use_container_width=True):
            logout()


def render_home():
    """홈 화면 렌더링"""
    user_name = st.session_state.get("user_name", "")

    st.markdown(f"# {t('app.welcome', name=user_name)}")
    st.markdown(f"### {t('app.subtitle')}")

    st.divider()

    # 퀵 네비게이션 카드
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3 style="margin:0; font-size:2rem;">👤</h3>
            <p style="margin:0.5rem 0 0; font-weight:600;">모델 관리</p>
            <p style="margin:0; color:#888; font-size:0.8rem;">프로필 등록 & 검색</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3 style="margin:0; font-size:2rem;">📅</h3>
            <p style="margin:0.5rem 0 0; font-weight:600;">스케줄</p>
            <p style="margin:0; color:#888; font-size:0.8rem;">캘린더 연동 관리</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3 style="margin:0; font-size:2rem;">💰</h3>
            <p style="margin:0.5rem 0 0; font-weight:600;">정산</p>
            <p style="margin:0; color:#888; font-size:0.8rem;">3단계 승인 워크플로우</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3 style="margin:0; font-size:2rem;">📊</h3>
            <p style="margin:0.5rem 0 0; font-weight:600;">대시보드</p>
            <p style="margin:0; color:#888; font-size:0.8rem;">실시간 현황</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    st.info(
        "👈 왼쪽 사이드바에서 원하는 메뉴로 이동하세요. "
        "각 페이지는 역할에 따라 접근 권한이 다르게 적용됩니다."
    )


def main():
    """메인 실행 함수"""
    init_session_state()

    if not st.session_state.authenticated:
        # 먼저 OAuth 콜백 확인
        from utils.auth import handle_auth_callback
        if handle_auth_callback():
            st.rerun()
            return

        # 로그인 페이지 (센터 정렬)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align:center; padding:2rem 0;">
                <div style="font-size:3rem;">🎯</div>
                <h1 style="margin:0.5rem 0;">Model Management</h1>
                <p style="color:#888;">외국인 모델 통합 관리 시스템</p>
            </div>
            """, unsafe_allow_html=True)

            from utils.auth import login_with_google
            login_with_google()

            st.markdown("")
            st.caption("최초 로그인 시 관리자 승인이 필요합니다.")
        return

    # 승인 확인
    from utils.auth import is_approved, show_pending_approval_page
    if not is_approved():
        show_pending_approval_page()
        return

    # 인증 + 승인된 사용자 - 사이드바 & 홈
    render_sidebar()
    render_home()


if __name__ == "__main__":
    main()

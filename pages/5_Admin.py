"""
⚙️ 관리자 패널 - 사용자 승인 및 역할 관리
"""
import streamlit as st
from utils.auth import require_auth, render_admin_panel

st.set_page_config(page_title="관리자 패널", page_icon="⚙️", layout="wide")


@require_auth(page_name="admin")
def main():
    st.markdown("# ⚙️ 관리자 패널")
    render_admin_panel()


main()

"""
Supabase 클라이언트 싱글턴 모듈
"""
import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


@st.cache_resource
def get_supabase_client() -> Client:
    """Supabase 클라이언트를 생성하고 캐싱합니다."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        st.error("⚠️ Supabase 환경변수가 설정되지 않았습니다. `.env` 파일을 확인하세요.")
        st.stop()

    return create_client(url, key)


def get_supabase_admin_client() -> Client:
    """서비스 역할 키를 사용하는 관리자 클라이언트 (RLS 우회)"""
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not service_key:
        st.error("⚠️ Supabase 서비스 키가 설정되지 않았습니다.")
        st.stop()

    return create_client(url, service_key)

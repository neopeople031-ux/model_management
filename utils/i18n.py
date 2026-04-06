"""
다국어(한국어/영어) 지원 모듈
"""
import json
import os
import streamlit as st

_translations: dict[str, dict] = {}

LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locales")


def _load_translations():
    """번역 파일을 로드합니다."""
    global _translations
    if _translations:
        return

    for lang in ["ko", "en"]:
        filepath = os.path.join(LOCALES_DIR, f"{lang}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)
        else:
            _translations[lang] = {}


def get_lang() -> str:
    """현재 선택된 언어 코드를 반환합니다."""
    return st.session_state.get("lang", "ko")


def set_lang(lang: str):
    """언어를 설정합니다."""
    st.session_state["lang"] = lang


def t(key: str, **kwargs) -> str:
    """
    번역된 문자열을 반환합니다.

    사용법:
        t("dashboard.title")
        t("model.count", count=10)
    """
    _load_translations()
    lang = get_lang()
    translations = _translations.get(lang, {})

    # 점(.) 표기법으로 중첩 키 접근
    keys = key.split(".")
    value = translations
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            value = None
            break

    if value is None:
        # 폴백: 키 자체를 반환
        return key

    # 문자열 포매팅
    if kwargs and isinstance(value, str):
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError):
            return value

    return value


def render_lang_toggle():
    """사이드바에 언어 전환 토글을 렌더링합니다."""
    current_lang = get_lang()
    lang_options = {"ko": "🇰🇷 한국어", "en": "🇺🇸 English"}

    selected = st.sidebar.radio(
        "Language",
        options=list(lang_options.keys()),
        format_func=lambda x: lang_options[x],
        index=0 if current_lang == "ko" else 1,
        horizontal=True,
        label_visibility="collapsed",
    )

    if selected != current_lang:
        set_lang(selected)
        st.rerun()

"""محتوى الشريط الجانبي: شعار Maznexa (عبر st.logo)، اسم النظام، ومبدّل اللغة (منقول
من أعلى المحتوى الرئيسي). قائمة الصفحات نفسها تُعرض تلقائيًا بواسطة st.navigation —
لا حاجة لبنائها يدويًا هنا، وتمييز الصفحة النشطة يتم عبر CSS بـ theme.py."""
from pathlib import Path

import streamlit as st

from src.translations import t

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo_header.png"
ICON_PATH = ASSETS_DIR / "logo.png"


def render_sidebar_chrome(lang: str) -> None:
    if LOGO_PATH.exists():
        st.logo(str(LOGO_PATH), icon_image=str(ICON_PATH) if ICON_PATH.exists() else str(LOGO_PATH))

    with st.sidebar:
        st.markdown(
            f'<p style="font-weight:800;font-size:1.05rem;color:var(--text-primary);'
            f'margin:6px 0 0 0;">{t("header_title", lang)}</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr style="border-color:var(--border);margin:10px 0 16px 0;">', unsafe_allow_html=True)

        st.selectbox(
            t("lang_toggle_label", lang),
            options=["ar", "en"],
            format_func=lambda x: "AR" if x == "ar" else "EN",
            key="lang",
            label_visibility="collapsed",
        )

"""
واجهة Streamlit — الغلاف الرفيع لنظام تحديد العملاء الأوفلاين (Maznexa Brand).
لا يحتوي أي منطق معالجة/مطابقة/تطبيع جديد؛ الصفحتان الفعليتان (لوحة التحكم / رفع
ملف الأوفلاين) وكل مكوّنات الواجهة موزّعة على حزمة src/ui — هذا الملف فقط:
إعداد الصفحة، حقن التصميم الموحّد، شريط جانبي، وتوجيه Streamlit Navigation.
"""
from pathlib import Path

import streamlit as st

from src.translations import t
from src.ui import theme
from src.ui.dashboard_page import dashboard_page
from src.ui.sidebar import render_sidebar_chrome
from src.ui.upload_page import upload_page

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

if "lang" not in st.session_state:
    st.session_state.lang = "ar"

lang = st.session_state.lang

st.set_page_config(
    page_title=t("page_title", lang),
    page_icon=str(ASSETS_DIR / "logo.png") if (ASSETS_DIR / "logo.png").exists() else "📊",
    layout="wide",
)

theme.inject_theme(lang)
render_sidebar_chrome(lang)

pg = st.navigation(
    [
        st.Page(dashboard_page, title=t("dashboard_title", lang), icon="📊", default=True),
        st.Page(upload_page, title=t("upload_title", lang), icon="📤"),
    ]
)
pg.run()

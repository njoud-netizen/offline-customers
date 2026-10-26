"""شريط علوي داخل المحتوى: عنوان الصفحة + وصف صغير + آخر تحديث + زر تحديث اختياري.
وتذييل الصفحة المشترك."""
from typing import Callable, Optional

import streamlit as st

from src.translations import t


def render_page_header(
    title: str,
    subtitle: str,
    lang: str,
    last_updated: str | None = None,
    on_refresh: Optional[Callable[[], None]] = None,
    eyebrow: str | None = None,
) -> None:
    with st.container(key="maz_page_header"):
        col_text, col_meta = st.columns([3, 1])
        with col_text:
            if eyebrow:
                st.markdown(f'<div class="maz-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
            st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)
            st.markdown(f'<div class="maz-page-subtitle">{subtitle}</div>', unsafe_allow_html=True)
        with col_meta:
            if last_updated:
                st.markdown(
                    f'<div class="maz-page-meta">{t("dashboard_last_updated_label", lang)}: {last_updated}</div>',
                    unsafe_allow_html=True,
                )
            if on_refresh is not None:
                if st.button(t("dashboard_refresh_button", lang), use_container_width=True):
                    on_refresh()
                    st.rerun()


def render_results_header(
    eyebrow: str,
    title: str,
    subtitle: str,
    download_label: str,
    download_data: bytes,
    download_filename: str,
    download_mime: str,
) -> None:
    """عنوان صفحة النتائج (بعد المعالجة) — بدون بطاقة/حدود (خلفية الصفحة مباشرة)، مع زر
    تحميل CSV بالجهة المقابلة للعنوان. يستبدل render_page_header بصريًا لحالة النتائج فقط
    (يُرسم داخل نفس st.empty() placeholder، فيحل محل هيدر الرفع الافتراضي)."""
    with st.container(key="maz_results_header"):
        col_text, col_action = st.columns([3, 1])
        with col_text:
            st.markdown(f'<div class="maz-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
            st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)
            st.markdown(f'<div class="maz-page-subtitle">{subtitle}</div>', unsafe_allow_html=True)
        with col_action:
            st.download_button(
                download_label,
                data=download_data,
                file_name=download_filename,
                mime=download_mime,
                icon=":material/download:",
                use_container_width=True,
            )


def render_footer(lang: str) -> None:
    st.markdown(f'<div class="maz-footer">{t("footer_text", lang)}</div>', unsafe_allow_html=True)

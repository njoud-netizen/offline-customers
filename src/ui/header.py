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
    lang: str,
    download_label: str,
    build_download_data: Callable[[str], bytes],
    download_filename: str,
    download_mime: str,
) -> str:
    """عنوان صفحة النتائج (بعد المعالجة) — بدون بطاقة/حدود (خلفية الصفحة مباشرة). يسار
    الهيدر: بحث برقم الجوال + زر تحميل CSV. فلتر الشركة انتقل لقسم "أبرز المؤشرات" (multiselect
    مستقل هناك) فما بقي هنا غير هذين العنصرين. يرجع phone_search للاستخدام المباشر بحساب
    الفلترة بنفس التشغيلة. build_download_data(phone_search) -> bytes: يُستدعى هنا بعد معرفة
    قيمة البحث (من نفس الاستدعاء) لحساب بيانات CSV *قبل* رسم زر التحميل."""
    with st.container(key="maz_results_header"):
        col_text, col_action = st.columns([1.6, 1.4])
        with col_text:
            st.markdown(f'<div class="maz-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
            st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)
            st.markdown(f'<div class="maz-page-subtitle">{subtitle}</div>', unsafe_allow_html=True)
        with col_action:
            col_search, col_csv = st.columns([1.6, 1])
            with col_search:
                phone_search = st.text_input(
                    t("inbound_header_search_label", lang),
                    placeholder=t("inbound_header_search_placeholder", lang),
                    key="inbound_header_phone_search",
                    label_visibility="collapsed",
                )
            with col_csv:
                st.download_button(
                    download_label,
                    data=build_download_data(phone_search),
                    file_name=download_filename,
                    mime=download_mime,
                    icon=":material/download:",
                    use_container_width=True,
                )
    return phone_search


def render_footer(lang: str) -> None:
    st.markdown(f'<div class="maz-footer">{t("footer_text", lang)}</div>', unsafe_allow_html=True)

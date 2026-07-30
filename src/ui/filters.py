"""شريط فلاتر لوحة التحكم — كل فلتر يُطبَّق فورًا (Live) بدون زر "تطبيق": نطاق تاريخ +
أزرار اختيار سريع للفترات الشائعة + فلتر شركة (Dropdown حقيقي) + فلتر سنة. لا يوجد
Apply/Form — أي تغيير بأي فلتر يُعيد حساب البطاقات/الرسوم فورًا لأن قيمة كل ودجت
تُقرأ مباشرة (مربوطة بمفتاح session_state)، وليست محجوزة خلف تأكيد منفصل.
عند أول تحميل للصفحة: القيم الافتراضية = كل الشركات + كامل النطاق الزمني المتاح، أي
تُعرض كل البيانات مباشرة بدون أي فلترة مسبقة."""
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src.translations import t

DATE_KEY = "df_filter_date_range"
BRAND_KEY = "df_filter_brands"
YEAR_KEY = "df_filter_year"
BRAND_EDIT_MODE_KEY = "df_filter_brand_edit_mode"

_QUICK_RANGE_KEYS = ["today", "yesterday", "last_7", "last_30", "this_month"]


@dataclass
class DashboardFilters:
    brands: list[str]
    start_date: date
    end_date: date
    year: int | None = None


def _quick_range(kind: str, min_date: date, max_date: date) -> tuple[date, date]:
    today = date.today()
    if kind == "today":
        start, end = today, today
    elif kind == "yesterday":
        start = end = today - timedelta(days=1)
    elif kind == "last_7":
        start, end = today - timedelta(days=6), today
    elif kind == "last_30":
        start, end = today - timedelta(days=29), today
    elif kind == "this_month":
        start, end = today.replace(day=1), today
    else:
        return min_date, max_date
    # تقييد ضمن حدود البيانات الفعلية المتاحة حتى لا يفشل date_input بقيمة خارج النطاق
    start = max(start, min_date)
    end = min(end, max_date)
    if start > end:
        start = end = max_date
    return start, end


def render_filters_bar(df: pd.DataFrame, brand_dictionary: dict, lang: str) -> DashboardFilters:
    known_brands = sorted(brand_dictionary.keys())
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    years = sorted(int(y) for y in df["date"].dt.year.dropna().unique())
    all_label = t("filter_all_option", lang)

    # تُهيَّأ مرة واحدة فقط بأول تحميل: كل الشركات + كامل النطاق الزمني — أي البيانات
    # كاملة تُعرض فورًا بدون أي فلترة مسبقة يحتاجها المستخدم.
    if DATE_KEY not in st.session_state:
        st.session_state[DATE_KEY] = (min_date, max_date)
    if BRAND_KEY not in st.session_state:
        st.session_state[BRAND_KEY] = known_brands
    if YEAR_KEY not in st.session_state:
        st.session_state[YEAR_KEY] = all_label
    if BRAND_EDIT_MODE_KEY not in st.session_state:
        st.session_state[BRAND_EDIT_MODE_KEY] = False

    st.markdown('<div class="maz-card">', unsafe_allow_html=True)
    st.markdown(f'<p class="maz-card-title">{t("filters_card_title", lang)}</p>', unsafe_allow_html=True)

    st.markdown(f'<p class="maz-card-subtitle" style="margin-bottom:6px;">{t("quick_range_label", lang)}</p>', unsafe_allow_html=True)
    quick_cols = st.columns(len(_QUICK_RANGE_KEYS) + 1)
    for col, kind in zip(quick_cols, _QUICK_RANGE_KEYS):
        with col:
            if st.button(t(f"quick_range_{kind}", lang), key=f"quick_{kind}", use_container_width=True):
                st.session_state[DATE_KEY] = _quick_range(kind, min_date, max_date)
                st.rerun()

    col_date, col_brand, col_year, col_reset = st.columns([1.5, 1.6, 0.7, 0.6])

    # مهم: نتعامل مع زر "إعادة ضبط" ونُغيّر session_state هنا أولًا (بترتيب التنفيذ
    # بالكود)، قبل إنشاء أي ودجت مربوط بنفس المفاتيح أدناه — Streamlit يمنع تعديل
    # session_state لمفتاح ودجت بعد إنشاء ذلك الودجت بنفس التشغيلة. ترتيب التنفيذ هذا
    # لا يغيّر مكان ظهور العمود بصريًا (يبقى بأقصى العمود كما هو معرّف بـ st.columns).
    with col_reset:
        st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
        if st.button(t("filter_reset_button", lang), use_container_width=True):
            st.session_state[DATE_KEY] = (min_date, max_date)
            st.session_state[BRAND_KEY] = known_brands
            st.session_state[YEAR_KEY] = all_label
            st.session_state[BRAND_EDIT_MODE_KEY] = False
            st.rerun()

    with col_date:
        date_range_widget = st.date_input(
            t("filter_date_range_label", lang), min_value=min_date, max_value=max_date, key=DATE_KEY,
        )
    with col_brand:
        current_brands = st.session_state.get(BRAND_KEY, known_brands)
        is_all_selected = set(current_brands) == set(known_brands)
        # عرض مضغوط "كل الشركات" (بدون Chips فردية) فقط حين تكون كل الشركات مختارة
        # ولم يطلب المستخدم التعديل صراحةً — أي تضييق فعلي للاختيار يعيد إظهار Chips
        # الفردية تلقائيًا (عبر الشرط أدناه) دون أي تغيير بمنطق الفلترة نفسه.
        if is_all_selected and not st.session_state[BRAND_EDIT_MODE_KEY]:
            st.markdown(f'<div class="maz-compact-filter-label">{t("filter_brand_label", lang)}</div>', unsafe_allow_html=True)
            box_col, edit_col = st.columns([2.4, 1])
            with box_col:
                st.markdown(
                    f'<div class="maz-compact-filter-box">🏢 {t("filter_all_option", lang)}</div>',
                    unsafe_allow_html=True,
                )
            with edit_col:
                if st.button(t("filter_brand_edit_button", lang), key="brand_edit_btn", use_container_width=True):
                    st.session_state[BRAND_EDIT_MODE_KEY] = True
                    st.rerun()
            brands_widget = known_brands
        else:
            brands_widget = st.multiselect(
                t("filter_brand_label", lang), options=known_brands, key=BRAND_KEY,
            )
            st.session_state[BRAND_EDIT_MODE_KEY] = set(brands_widget) != set(known_brands)
    with col_year:
        year_options = [all_label] + years
        year_widget = st.selectbox(t("filter_year_label", lang), options=year_options, key=YEAR_KEY)

    st.markdown("</div>", unsafe_allow_html=True)

    if isinstance(date_range_widget, tuple) and len(date_range_widget) == 2:
        start_date, end_date = date_range_widget
    else:
        start_date, end_date = min_date, max_date
    year_value = None if year_widget == all_label else int(year_widget)

    return DashboardFilters(brands=brands_widget, start_date=start_date, end_date=end_date, year=year_value)


def apply_filters(df: pd.DataFrame, filters: DashboardFilters) -> pd.DataFrame:
    """قيود AND صريحة ومستقلة — لا تخفيف تلقائي صامت عند نتيجة فارغة."""
    d = df.dropna(subset=["date"])
    mask = d["company_name"].isin(filters.brands)
    mask &= (d["date"].dt.date >= filters.start_date) & (d["date"].dt.date <= filters.end_date)
    if filters.year is not None:
        mask &= d["date"].dt.year == filters.year
    return d[mask]

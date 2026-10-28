"""جدول العملاء الأوفلاين الاحترافي — يستبدل جدول HTML المخصص السابق بـ st.dataframe
(Sticky header + فرز أصلي)، مع بحث نصي، فلاتر (براند/تاريخ/موظف)، فرز صريح، وTرقيم صفحات
يدوي. لا يُغيّر أي عمود أو قيمة قادمة من pipeline_result.offline_rows — تصميم/تنظيم فقط."""
import pandas as pd
import streamlit as st

from src.translations import t, translate_offline_columns

from .empty_state import render_empty_state

PAGE_SIZE_OPTIONS = [10, 25, 50, 100]

# الأعمدة المعروضة بالجدول وبنفس الترتيب — باقي الأعمدة تبقى للفلاتر/البحث وملفات Excel فقط
DISPLAY_COLUMNS = [
    "اسم العميل", "رقم الجوال", "تاريخ التواصل بشيت المزروع", "سبب التواصل (Details)", "مبلغ الفاتورة الإجمالي",
]
DISPLAY_LABELS_AR = {
    "تاريخ التواصل بشيت المزروع": "تاريخ تواصله",
    "سبب التواصل (Details)": "السبب",
}


def _display_labels(columns, lang: str) -> list[str]:
    if lang == "ar":
        return [DISPLAY_LABELS_AR.get(c, c) for c in columns]
    return translate_offline_columns(columns, lang)


def render_offline_table(df_offline: pd.DataFrame, lang: str) -> None:
    if df_offline.empty:
        render_empty_state(t("warning_no_offline", lang))
        return

    df = df_offline.copy()
    df["_invoice_date_parsed"] = pd.to_datetime(df["تاريخ الفاتورة"], errors="coerce")

    raw_cols = [c for c in DISPLAY_COLUMNS if c in df_offline.columns]
    translated_cols = _display_labels(raw_cols, lang)
    col_map = dict(zip(translated_cols, raw_cols))

    col_search, col_sort, col_order = st.columns([2, 1, 1])
    with col_search:
        search_term = st.text_input(t("search_label", lang))
    with col_sort:
        sort_column_display = st.selectbox(t("sort_by_label", lang), options=translated_cols)
    with col_order:
        sort_desc = st.selectbox(
            t("sort_direction_label", lang), options=[t("sort_asc", lang), t("sort_desc", lang)]
        ) == t("sort_desc", lang)

    col_brand, col_agent, col_date = st.columns(3)
    with col_brand:
        brand_options = sorted(df["Brand"].dropna().unique().tolist())
        brand_filter = st.multiselect(t("table_filter_brand", lang), options=brand_options, default=brand_options)
    with col_agent:
        agent_options = sorted(df["اسم الموظفة (Agent)"].dropna().unique().tolist())
        agent_filter = st.multiselect(t("table_filter_agent", lang), options=agent_options, default=agent_options)
    with col_date:
        valid_dates = df["_invoice_date_parsed"].dropna()
        date_filter = None
        if not valid_dates.empty:
            min_d, max_d = valid_dates.min().date(), valid_dates.max().date()
            date_filter = st.date_input(t("table_filter_date", lang), value=(min_d, max_d), min_value=min_d, max_value=max_d)

    mask = df["Brand"].isin(brand_filter) & df["اسم الموظفة (Agent)"].isin(agent_filter)
    if isinstance(date_filter, tuple) and len(date_filter) == 2:
        start_d, end_d = date_filter
        mask &= df["_invoice_date_parsed"].isna() | (
            (df["_invoice_date_parsed"].dt.date >= start_d) & (df["_invoice_date_parsed"].dt.date <= end_d)
        )
    df_filtered = df[mask].drop(columns=["_invoice_date_parsed"])

    if search_term:
        text_mask = df_filtered.apply(lambda col: col.astype(str).str.contains(search_term, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[text_mask]

    if df_filtered.empty:
        render_empty_state(t("empty_no_data_matches_filters", lang))
        return

    sort_column = col_map[sort_column_display]
    df_sorted = df_filtered.sort_values(by=sort_column, ascending=not sort_desc)

    nav_size, nav_prev, nav_caption, nav_next, nav_export = st.columns([1.2, 0.7, 1.4, 0.7, 1])
    with nav_size:
        page_size = st.selectbox(t("table_page_size_label", lang), options=PAGE_SIZE_OPTIONS, index=1, key="offline_table_page_size")

    total_rows = len(df_sorted)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    if "offline_table_page" not in st.session_state:
        st.session_state["offline_table_page"] = 0
    st.session_state["offline_table_page"] = min(st.session_state["offline_table_page"], total_pages - 1)

    with nav_prev:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button(t("table_prev_page", lang), disabled=st.session_state["offline_table_page"] <= 0, use_container_width=True):
            st.session_state["offline_table_page"] -= 1
    with nav_next:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button(t("table_next_page", lang), disabled=st.session_state["offline_table_page"] >= total_pages - 1, use_container_width=True):
            st.session_state["offline_table_page"] += 1
    with nav_caption:
        st.markdown(
            f'<div style="text-align:center;color:var(--text-secondary);padding-top:34px;">'
            f'{t("table_page_caption", lang).format(current=st.session_state["offline_table_page"] + 1, total=total_pages)}'
            f"</div>",
            unsafe_allow_html=True,
        )
    with nav_export:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        csv_bytes = df_sorted.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            t("table_export_button", lang), data=csv_bytes, file_name="offline_customers_filtered.csv",
            mime="text/csv", use_container_width=True,
        )

    start_idx = st.session_state["offline_table_page"] * page_size
    end_idx = start_idx + page_size
    page_df = df_sorted.iloc[start_idx:end_idx][raw_cols].copy()
    page_df.columns = translated_cols

    phone_col, total_col = _display_labels(["رقم الجوال", "مبلغ الفاتورة الإجمالي"], lang)
    column_config = {
        phone_col: st.column_config.TextColumn(),
        total_col: st.column_config.NumberColumn(format="%.2f"),
    }
    st.dataframe(page_df, use_container_width=True, hide_index=True, column_config=column_config)

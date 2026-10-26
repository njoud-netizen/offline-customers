"""جدول HTML مخصّص لنتائج صفحة Inbound Call — ترويسة ثابتة، تلوين صفوف متبادل، شارات ملوّنة،
فلاتر (بحث بالرقم/تاريخ/حالة/تفاصيل)، دمج أرقام مكررة اختياري، إخفاء أعمدة فاضية تلقائيًا،
ترقيم صفحات (25/صفحة)، وتصدير CSV للعرض المفلتر بالقيم الخام.

مقسوم لدالتين عمدًا: render_filter_bar() ثم render_table_body() — لأن بطاقات KPI/المؤشرات
بصفحة Inbound Call يجب تتفاعل مع نفس الفلاتر (مطلوب صراحة)، لكنها تظهر بصريًا *قبل* الجدول.
Streamlit يُصيّر بالتسلسل من أعلى لأسفل بمرة واحدة فلا يمكن لودجت يظهر لاحقًا يُغذّي محتوى
أعلاه بنفس التشغيلة — الحل: الفلاتر تُصيَّر أولًا (تعيد DataFrame مفلتر)، تُستخدم لحساب
KPI/المؤشرات، ثم جدول الإخراج النهائي يُصيَّر بعدها بنفس البيانات المفلترة.

لا علاقة لهذا الملف بـ inbound_pipeline.py — يقرأ فقط قائمة dict الجاهزة (result.rows) ويعرضها،
بدون أي تعديل على البيانات المصدرية أو منطق الاستخراج."""
import html
import re
from datetime import date as _date

import pandas as pd
import streamlit as st

from src.translations import t

from .badges import details_badge_html, repeat_badge_html, status_badge_html
from .empty_state import render_empty_state
from .phone_format import format_phone_display

PAGE_SIZE = 25
_DISPLAY_COLS = ["Date", "Number", "Inbound calls/out bound calls", "Call Status", "Details"]
_SESSION_PAGE_KEY = "inbound_table_page"
_SESSION_SHOW_ALL_COLS_KEY = "inbound_table_show_all_cols"


def _digits_only(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def _col_label(col: str, lang: str) -> str:
    return {
        "Date": t("inbound_table_col_date", lang),
        "Number": t("inbound_table_col_number", lang),
        "Inbound calls/out bound calls": t("inbound_table_col_type", lang),
        "Call Status": t("inbound_table_col_status", lang),
        "Details": t("inbound_table_col_details", lang),
        "call_count": t("inbound_table_col_count", lang),
    }.get(col, col)


def render_filter_bar(rows: list[dict], lang: str) -> tuple[pd.DataFrame, bool]:
    """يرجع (filtered_df, group_enabled). filtered_df دائمًا قبل أي تجميع — نفس الصفوف
    بشكلها الأصلي بعد الفلترة فقط، تُستخدم لحساب KPI/المؤشرات وللجدول معًا."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df, False

    df["_date_parsed"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

    with st.container(key="maz_card_inbound_filters"):
        col_search, col_date, col_status, col_details, col_group = st.columns([1.4, 1.3, 1.1, 1.3, 1])
        with col_search:
            search_term = st.text_input(t("inbound_table_search_label", lang), key="inbound_filter_search")
        with col_date:
            valid_dates = df["_date_parsed"].dropna()
            date_filter = None
            if not valid_dates.empty:
                min_d, max_d = valid_dates.min(), valid_dates.max()
                today = _date.today()
                default_range = (today, today) if min_d <= today <= max_d else (min_d, max_d)
                date_filter = st.date_input(
                    t("inbound_table_date_range_label", lang), value=default_range,
                    min_value=min_d, max_value=max_d, key="inbound_filter_date",
                )
        with col_status:
            status_options = sorted(v for v in df["Call Status"].dropna().unique().tolist() if str(v).strip())
            status_filter = st.multiselect(
                t("inbound_table_status_label", lang), options=status_options, default=status_options,
                key="inbound_filter_status",
            )
        with col_details:
            details_options = sorted(v for v in df["Details"].dropna().unique().tolist() if str(v).strip())
            details_filter = st.multiselect(
                t("inbound_table_details_label", lang), options=details_options, default=details_options,
                key="inbound_filter_details",
            )
        with col_group:
            st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
            group_enabled = st.toggle(t("inbound_table_group_toggle", lang), value=False, key="inbound_filter_group")

    mask = pd.Series(True, index=df.index)
    if search_term:
        digits = _digits_only(search_term)
        if digits:
            mask &= df["Number"].astype(str).apply(_digits_only).str.contains(digits, na=False)
    if isinstance(date_filter, tuple) and len(date_filter) == 2:
        start_d, end_d = date_filter
        mask &= df["_date_parsed"].isna() | ((df["_date_parsed"] >= start_d) & (df["_date_parsed"] <= end_d))
    mask &= df["Call Status"].isin(status_filter) | ~df["Call Status"].astype(bool) if status_filter else False
    mask &= df["Details"].isin(details_filter) | ~df["Details"].astype(bool) if details_filter else False

    filtered_df = df[mask].drop(columns=["_date_parsed"])
    return filtered_df, group_enabled


def _group_rows(df: pd.DataFrame) -> pd.DataFrame:
    """يدمج صفوف نفس الرقم+التاريخ لصف واحد: عدد المكالمات + أول Details غير فاضي."""
    def _first_non_empty_details(s: pd.Series) -> str:
        non_empty = [v for v in s if str(v).strip()]
        return non_empty[0] if non_empty else ""

    return df.groupby(["Number", "Date"], as_index=False, sort=False).agg(
        **{
            "Inbound calls/out bound calls": ("Inbound calls/out bound calls", "first"),
            "Call Status": ("Call Status", "first"),
            "Details": ("Details", _first_non_empty_details),
            "call_count": ("Number", "count"),
        }
    )


def render_table_body(total_rows_count: int, filtered_df: pd.DataFrame, group_enabled: bool, lang: str) -> None:
    """يرسم بطاقة الجدول كاملة (شريط معلومات + جدول HTML + ترقيم + تصدير CSV) من بيانات
    مفلترة أصلًا (راجع render_filter_bar). total_rows_count: إجمالي صفوف الملف الأصلي كاملة
    (بدون فلترة) — لعرض 'عرض X من Y' بشكل صحيح."""
    with st.container(key="maz_table_card_results"):
        if filtered_df.empty:
            render_empty_state(t("inbound_table_no_results", lang))
            return

        show_all_cols = st.session_state.get(_SESSION_SHOW_ALL_COLS_KEY, False)
        empty_cols = [c for c in _DISPLAY_COLS if not filtered_df[c].astype(str).str.strip().any()]
        visible_cols = list(_DISPLAY_COLS) if show_all_cols else [c for c in _DISPLAY_COLS if c not in empty_cols]

        if group_enabled:
            table_df = _group_rows(filtered_df)
            visible_cols_final = visible_cols + (["call_count"] if "call_count" not in visible_cols else [])
        else:
            table_df = filtered_df.copy()
            visible_cols_final = visible_cols

        total_shown = len(table_df)

        info_left = t("inbound_table_showing", lang).format(shown=f"{total_shown:,}", total=f"{total_rows_count:,}")
        if empty_cols and not show_all_cols:
            hidden_labels = "، ".join(_col_label(c, lang) for c in empty_cols)
            info_strip, info_btn = st.columns([4, 1])
            with info_strip:
                st.markdown(
                    f'<div class="maz-table-info-strip"><span>{info_left}</span>'
                    f'<span>{t("inbound_table_hidden_columns", lang).format(count=len(empty_cols), cols=hidden_labels)}</span></div>',
                    unsafe_allow_html=True,
                )
            with info_btn:
                if st.button(t("inbound_table_show_all", lang), key="inbound_show_all_cols_btn", use_container_width=True):
                    st.session_state[_SESSION_SHOW_ALL_COLS_KEY] = True
                    st.rerun()
        else:
            st.markdown(f'<div class="maz-table-info-strip"><span>{info_left}</span><span></span></div>', unsafe_allow_html=True)

        total_pages = max(1, (total_shown + PAGE_SIZE - 1) // PAGE_SIZE)
        if _SESSION_PAGE_KEY not in st.session_state:
            st.session_state[_SESSION_PAGE_KEY] = 0
        st.session_state[_SESSION_PAGE_KEY] = min(st.session_state[_SESSION_PAGE_KEY], total_pages - 1)
        page = st.session_state[_SESSION_PAGE_KEY]

        nav_prev, nav_caption, nav_next, nav_csv = st.columns([0.7, 1.4, 0.7, 1.2])
        with nav_prev:
            if st.button(t("table_prev_page", lang), disabled=page <= 0, use_container_width=True, key="inbound_prev_page"):
                st.session_state[_SESSION_PAGE_KEY] -= 1
                st.rerun()
        with nav_caption:
            st.markdown(
                f'<div style="text-align:center;color:var(--text-secondary);padding-top:8px;">'
                f'{t("inbound_table_page_caption", lang).format(current=page + 1, total=total_pages)}</div>',
                unsafe_allow_html=True,
            )
        with nav_next:
            if st.button(t("table_next_page", lang), disabled=page >= total_pages - 1, use_container_width=True, key="inbound_next_page"):
                st.session_state[_SESSION_PAGE_KEY] += 1
                st.rerun()
        with nav_csv:
            csv_bytes = filtered_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                t("inbound_download_csv_label", lang), data=csv_bytes, file_name="inbound_calls_filtered.csv",
                mime="text/csv", use_container_width=True, key="inbound_csv_export",
            )

        page_df = table_df.iloc[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]

        header_html = "".join(f"<th>{html.escape(_col_label(c, lang))}</th>" for c in visible_cols_final)
        rows_html = []
        for _, r in page_df.iterrows():
            cells = []
            for col in visible_cols_final:
                if col == "Number":
                    cells.append(f'<td dir="ltr">{html.escape(format_phone_display(r[col]))}</td>')
                elif col == "Call Status":
                    cells.append(f"<td>{status_badge_html(r[col])}</td>")
                elif col == "Details":
                    cells.append(f"<td>{details_badge_html(r[col])}</td>")
                elif col == "call_count":
                    count = int(r[col])
                    cell_content = repeat_badge_html(count) if count > 1 else str(count)
                    cells.append(f'<td dir="ltr">{cell_content}</td>')
                else:
                    cells.append(f"<td>{html.escape(str(r[col]))}</td>")
            rows_html.append(f"<tr>{''.join(cells)}</tr>")

        table_html = (
            '<div class="maz-table-scroll"><table class="maz-table">'
            f"<thead><tr>{header_html}</tr></thead>"
            f"<tbody>{''.join(rows_html)}</tbody>"
            "</table></div>"
        )
        st.markdown(table_html, unsafe_allow_html=True)

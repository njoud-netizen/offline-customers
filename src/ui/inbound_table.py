"""جدول HTML مخصّص لنتائج صفحة Inbound Call — ترويسة ثابتة، تلوين صفوف متبادل، شارات ملوّنة،
فلاتر (بحث بالرقم/تاريخ/تفاصيل — بدون فلتر حالة، عمود "حالة المكالمة" غير قابل للفلترة عمدًا)،
دمج أرقام مكررة اختياري، إخفاء أعمدة فاضية تلقائيًا، ترقيم صفحات (25/صفحة)، وتصدير CSV
للعرض المفلتر بالقيم الخام.

مقسوم لثلاث دوال عمدًا: compute_filtered() (حساب بدون رسم، يُستخدم لتغذية KPI/المؤشرات
مبكرًا) ثم render_filter_toolbar() (رسم الودجتات بصريًا بموضعها الصحيح فوق الجدول مباشرة)
ثم render_table_body() — لأن بطاقات KPI/المؤشرات بصفحة Inbound Call يجب تتفاعل مع نفس
الفلاتر (مطلوب صراحة) لكنها تظهر بصريًا *قبلها*. الحل: compute_filtered() يقرأ قيم الفلاتر
من session_state مباشرة (بدون استدعاء أي ودجت) — الودجتات المفتاحة (key=) تُزامِن قيمها مع
الواجهة الأمامية قبل تشغيل أي سطر كود بالتشغيلة، بغض النظر عن مكان استدعاء الودجت نفسه، فتبقى
القيمة صحيحة سواء قُرئت قبل أو بعد الاستدعاء الفعلي. render_filter_toolbar() لاحقًا يرسم نفس
الودجتات (بنفس المفاتيح) بموضعها البصري الصحيح — بدون أي إعادة حساب للفلترة نفسها.

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
_DETAILS_ALL_VALUE = ""  # قيمة داخلية ثابتة (غير مترجمة) لخيار "الكل" بقائمة التفاصيل —
# مستقلة عن اللغة فلا تتأثر بتبديل عربي/إنجليزي بمنتصف الجلسة (النص المعروض عبر format_func)


def normalize_phone(raw: str) -> str:
    """ينظّف رقم جوال خام للمقارنة: يشيل المسافات و+ و-، ثم يوحّد صيغ 05xxxxxxxx /
    9665xxxxxxxx / 009665xxxxxxxx لنفس الشكل القياسي (5xxxxxxxx بدون أي بادئة دولة/صفر)."""
    digits = re.sub(r"\D", "", re.sub(r"[\s+\-]", "", raw or ""))
    if digits.startswith("00966"):
        digits = digits[5:]
    elif digits.startswith("966"):
        digits = digits[3:]
    elif digits.startswith("0"):
        digits = digits[1:]
    return digits


COMPANY_MULTISELECT_KEY = "inbound_company_multiselect"


def get_top_company(rows: list[dict]) -> str:
    """أعلى شركة (الأكثر تكرارًا) بكامل الصفوف — تُستخدم كاختيار افتراضي وحيد لـ
    st.multiselect الشركات أول ما يُرفع الملف (قبل أي تفاعل من المستخدم)."""
    df = pd.DataFrame(rows)
    if df.empty or "company" not in df.columns:
        return ""
    non_empty = df["company"][df["company"].astype(str).str.strip() != ""]
    if non_empty.empty:
        return ""
    return str(non_empty.value_counts().index[0])


def _call_type_html(value: str, lang: str) -> str:
    raw = (value or "").strip()
    if raw.lower() == "inbound":
        label = t("inbound_call_direction_inbound", lang)
        return f'<span class="maz-call-type"><span class="material-symbols-outlined">call_received</span>{html.escape(label)}</span>'
    return html.escape(raw) if raw else "—"


def _col_label(col: str, lang: str) -> str:
    return {
        "Date": t("inbound_table_col_date", lang),
        "Number": t("inbound_table_col_number", lang),
        "Inbound calls/out bound calls": t("inbound_table_col_type", lang),
        "Call Status": t("inbound_table_col_status", lang),
        "Details": t("inbound_table_col_details", lang),
        "call_count": t("inbound_table_col_count", lang),
    }.get(col, col)


def _filter_state_from_session(df: pd.DataFrame) -> dict:
    """يقرأ قيم الفلاتر الحالية من session_state (أو قيمها الافتراضية لو لسا ودجتات
    الفلاتر ما اترسمت بهذا التشغيلة) — بدون رسم أي ودجت. يسمح بحساب filtered_df *قبل*
    موضع ظهور شريط الفلاتر بصريًا (بعد 'أبرز المؤشرات' مباشرة، قبل الجدول)، لأن الودجتات
    المفتاحة (key=) تُزامِن session_state مع الواجهة الأمامية قبل تشغيل أي سطر كود، بغض
    النظر عن مكان استدعاء الودجت نفسه بالسكربت."""
    valid_dates = df["_date_parsed"].dropna()
    date_default = None
    if not valid_dates.empty:
        min_d, max_d = valid_dates.min(), valid_dates.max()
        today = _date.today()
        date_default = (today, today) if min_d <= today <= max_d else (min_d, max_d)
    details_options = sorted(v for v in df["Details"].dropna().unique().tolist() if str(v).strip())
    return {
        "date_filter": st.session_state.get("inbound_filter_date", date_default),
        "details_options": details_options,
        "details_filter": st.session_state.get("inbound_filter_details", _DETAILS_ALL_VALUE),
        "group_enabled": st.session_state.get("inbound_filter_group", False),
    }


def get_company_options(rows: list[dict]) -> list[str]:
    """قائمة الشركات الفريدة (غير فاضية) بترتيب أبجدي — تُستخدم لبناء قائمة فلتر الشركة
    بالهيدر؛ لا علاقة لها بمنطق compute_filtered (تُستدعى من ملف الصفوف الخام مباشرة قبله)."""
    df = pd.DataFrame(rows)
    if df.empty or "company" not in df.columns:
        return []
    return sorted(v for v in df["company"].dropna().unique().tolist() if str(v).strip())


def _apply_filter_mask(df: pd.DataFrame, state: dict) -> pd.DataFrame:
    """لا فلترة على عمود الحالة إطلاقًا (حُذف الفلتر بالكامل حسب الطلب) — عمود "حالة
    المكالمة" بالجدول يبقى كما هو دائمًا بغض النظر عن باقي الفلاتر."""
    mask = pd.Series(True, index=df.index)
    company_filter = state.get("company_filter")  # قائمة شركات أو None/[] = بدون فلترة (الكل)
    if company_filter:
        mask &= df.get("company", "").astype(str).isin(company_filter)
    phone_search = state.get("phone_search", "")
    if phone_search:
        target = normalize_phone(phone_search)
        if target:
            mask &= df["Number"].astype(str).apply(normalize_phone) == target
    date_filter = state["date_filter"]
    if isinstance(date_filter, tuple) and len(date_filter) == 2:
        start_d, end_d = date_filter
        mask &= df["_date_parsed"].isna() | ((df["_date_parsed"] >= start_d) & (df["_date_parsed"] <= end_d))
    details_filter = state["details_filter"]
    if details_filter and details_filter != _DETAILS_ALL_VALUE:
        mask &= df["Details"] == details_filter
    return df[mask]


def compute_filtered(
    rows: list[dict], lang: str, company_filter: list[str] | None = None, phone_search: str = "",
) -> tuple[pd.DataFrame, bool, dict, pd.DataFrame]:
    """يرجع (filtered_df, group_enabled, filter_state, df_with_date). company_filter: قائمة
    أسماء شركات (None أو [] = بدون فلترة، كل الشركات) — تُمرَّر مباشرة من القراءة المبكرة
    لـsession_state بصفحة ان باوند (قبل رسم ودجت multiselect الشركات الفعلي، نفس أسلوب
    التاريخ/التفاصيل أدناه). phone_search كذلك تُمرَّر مباشرة من ودجت البحث بالهيدر."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df, False, {}, df
    df["_date_parsed"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    state = _filter_state_from_session(df)
    state["company_filter"] = company_filter
    state["phone_search"] = phone_search
    filtered_df = _apply_filter_mask(df, state).drop(columns=["_date_parsed"])
    return filtered_df, state["group_enabled"], state, df


def phone_search_summary(filtered_df: pd.DataFrame, phone_search: str) -> dict | None:
    """بانر نتيجة البحث برقم الجوال (فوق البطاقات) — None لو ما فيه بحث نشط. مبني على
    filtered_df نفسه (بعد كل الفلاتر الأخرى بما فيها الشركة) حتى يتوافق مع باقي الصفحة."""
    if not phone_search or not normalize_phone(phone_search):
        return None
    if filtered_df.empty:
        return {"found": False}
    company = ""
    if "company" in filtered_df.columns:
        non_empty = filtered_df["company"][filtered_df["company"].astype(str).str.strip() != ""]
        company = str(non_empty.iloc[0]) if not non_empty.empty else ""
    return {
        "found": True,
        "count": len(filtered_df),
        "last_date": str(filtered_df["Date"].max()) if "Date" in filtered_df.columns else "",
        "company": company,
    }


def render_filter_toolbar(df_with_date: pd.DataFrame, state: dict, lang: str) -> None:
    """يرسم شريط الفلاتر بصريًا فقط (فوق الجدول مباشرة) — لا يُعيد حساب أي فلترة؛ نفس
    مفاتيح session_state المستخدمة بـcompute_filtered أعلاه فتبقى القيم متوافقة دائمًا.
    بحث الرقم والشركة انتقلا للهيدر — ما بقي هنا غير التاريخ/التفاصيل/الدمج فقط."""
    if df_with_date.empty:
        return
    with st.container(key="maz_card_inbound_filters"):
        col_date, col_details, col_group = st.columns([1.3, 1.3, 1.1])
        with col_date:
            valid_dates = df_with_date["_date_parsed"].dropna()
            if not valid_dates.empty:
                min_d, max_d = valid_dates.min(), valid_dates.max()
                st.date_input(
                    t("inbound_table_date_range_label", lang), value=state["date_filter"],
                    min_value=min_d, max_value=max_d, key="inbound_filter_date",
                )
        with col_details:
            details_select_options = [_DETAILS_ALL_VALUE] + state["details_options"]
            st.selectbox(
                t("inbound_table_details_label", lang), options=details_select_options,
                format_func=lambda v: t("filter_all_option", lang) if v == _DETAILS_ALL_VALUE else v,
                key="inbound_filter_details",
            )
        with col_group:
            st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
            st.toggle(t("inbound_table_group_toggle", lang), value=False, key="inbound_filter_group")


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
                elif col == "Inbound calls/out bound calls":
                    cells.append(f"<td>{_call_type_html(r[col], lang)}</td>")
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

"""صفحة لوحة التحكم — مصدرها منفصل تمامًا (تبويب "Sales Data" بنفس الشيت)، لا علاقة
له بمنطق مطابقة الفواتير الأساسي. لا تغيير بأي حساب موجود — فقط تنظيم بصري + رسوم
ومؤشرات إضافية مبنية على نفس df_sales.

هيكل الصفحة (بعد آخر جولة تعديلات): بطاقتا KPI فقط (إجمالي العملاء الأوفلاين،
إجمالي المبيعات) — بطاقة "عدد البراندات الظاهرة" حُذفت. رسم Plotly واحد مدمج
(مبيعات + عدد عملاء لكل شركة بمحورين) يستبدل رسمي "المبيعات حسب الشركة" و"عدد
العملاء الأوفلاين حسب الشركة" السابقين. رسما "المبيعات الشهرية" و"عدد العملاء
الأوفلاين شهريًا" حُذفا بالكامل (بيانات مزدحمة غير مقروءة). الربع السنوي/السنوي/
Donut التوزيعي باقون كما هم."""
from datetime import datetime

import pandas as pd
import streamlit as st

from src.config import credentials_path, load_config, resolve_path
from src.sales_data import load_sales_data_rows, rows_to_dataframe
from src.sheets import GoogleSheetsConnectionError, get_client
from src.translations import t

from .aggregations import aggregate_monthly_sales, aggregate_offline_monthly, period_over_period_change, previous_period_window
from .charts_combo import build_sales_offline_combo_chart
from .charts_offline import build_offline_donut_chart
from .charts_sales import build_annual_sales_chart, build_quarterly_sales_chart
from .chart_card import chart_card
from .empty_state import render_empty_state
from .filters import DashboardFilters, apply_filters, render_filters_bar
from .header import render_footer, render_page_header
from .kpi_card import KPICardData, render_kpi_row
from .last_runs import render_last_runs_card


def _apply_all_but_date(df: pd.DataFrame, filters: DashboardFilters) -> pd.DataFrame:
    """نفس قيود apply_filters عدا نطاق التاريخ — تُستخدم كأساس مشترك لمقارنة الفترة
    الحالية بالفترة السابقة بنفس بقية الفلاتر (براند/سنة) بالضبط."""
    d = df.dropna(subset=["date"])
    mask = d["company_name"].isin(filters.brands)
    if filters.year is not None:
        mask &= d["date"].dt.year == filters.year
    return d[mask]


def dashboard_page() -> None:
    lang = st.session_state.lang

    @st.cache_data(ttl=3600, show_spinner=t("spinner_dashboard_loading", lang))
    def load_dashboard_data(creds_path_str: str, spreadsheet_id: str, tab_name: str, gid: int, brand_dictionary: dict):
        gc = get_client(creds_path_str)
        rows = load_sales_data_rows(gc, spreadsheet_id, tab_name, gid)
        return rows_to_dataframe(rows, brand_dictionary)

    cfg = load_config()
    sd_cfg = cfg["google_sheets"]["sales_data_tab"]
    brand_dictionary = cfg["brand_dictionary"]

    if "dashboard_loaded_at" not in st.session_state:
        st.session_state["dashboard_loaded_at"] = None

    def _refresh() -> None:
        load_dashboard_data.clear()
        st.session_state["dashboard_loaded_at"] = None

    df_sales = None
    load_error: str | None = None
    try:
        df_sales = load_dashboard_data(
            str(credentials_path(cfg)),
            cfg["google_sheets"]["spreadsheet_id"],
            sd_cfg["name"],
            sd_cfg["gid"],
            brand_dictionary,
        )
        if st.session_state["dashboard_loaded_at"] is None:
            st.session_state["dashboard_loaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    except GoogleSheetsConnectionError as e:
        load_error = f"{t('error_sheets_connection', lang)}\n\n{e}"
    except Exception as e:
        load_error = f"{t('error_dashboard_load', lang)}\n\n{e}"

    render_page_header(
        t("dashboard_title", lang),
        t("dashboard_subtitle", lang),
        lang,
        last_updated=st.session_state["dashboard_loaded_at"],
        on_refresh=_refresh,
    )

    if load_error:
        st.error(load_error)
        render_footer(lang)
        return

    if df_sales is None or df_sales.empty:
        render_empty_state(t("info_no_sales_data", lang))
        render_footer(lang)
        return

    filters = render_filters_bar(df_sales, brand_dictionary, lang)
    filtered = apply_filters(df_sales, filters)

    if filtered.empty:
        render_empty_state(t("empty_no_data_matches_filters", lang))
        render_footer(lang)
        return

    filtered_offline = filtered[filtered["is_offline"]]

    # ==== بطاقتا KPI (إجمالي العملاء الأوفلاين، إجمالي المبيعات) ====
    # ملاحظة مهمة: تقتصران على السجلات المصنّفة Offline فقط (is_offline == True) — نفس
    # النطاق تمامًا، حتى تتطابق أرقام البطاقات مع بعضها ومع أي تحقق يدوي على الشيت.
    prev_start, prev_end = previous_period_window(filters.start_date, filters.end_date)
    base_for_comparison = _apply_all_but_date(df_sales, filters)
    base_for_comparison_offline = base_for_comparison[base_for_comparison["is_offline"]]

    total_sales = filtered_offline["amount_value"].sum()
    sales_delta = period_over_period_change(
        base_for_comparison_offline, "date", filters.start_date, filters.end_date, prev_start, prev_end, value_col="amount_value",
    )

    offline_count = len(filtered_offline)
    offline_delta = period_over_period_change(
        base_for_comparison_offline, "date", filters.start_date, filters.end_date, prev_start, prev_end,
    )

    monthly_sales_spark = aggregate_monthly_sales(filtered_offline, by_brand=False).rename(columns={"month": "x", "total_sales": "y"})
    monthly_offline_spark = aggregate_offline_monthly(filtered_offline, by_brand=False).rename(columns={"month": "x", "count": "y"})

    render_kpi_row(
        [
            KPICardData(
                label=t("kpi_total_offline", lang),
                value=f"{offline_count:,}",
                icon="👥",
                delta_pct=offline_delta,
                sparkline_df=monthly_offline_spark,
                tooltip=t("kpi_total_offline_tooltip", lang),
                accent=True,
            ),
            KPICardData(
                label=t("kpi_total_sales", lang),
                value=f"{total_sales:,.2f} {t('currency_default', lang)}",
                icon="💰",
                delta_pct=sales_delta,
                sparkline_df=monthly_sales_spark,
                tooltip=t("kpi_total_sales_tooltip", lang),
                accent=True,
            ),
        ]
    )

    # ==== شبكة الرسوم البيانية ====
    multi_brand = len(filters.brands) > 1

    # رسم Plotly واحد مدمج (مبيعات + عدد عملاء لكل شركة، بمحورين) يستبدل الرسمين
    # المنفصلين السابقين — راجع charts_combo.py لتفاصيل منطق الدمج ولوجيك الألوان.
    chart_card(
        "sales_offline_combo", t("chart_title_sales_offline_combo", lang), lang,
        build=lambda: build_sales_offline_combo_chart(filtered_offline, lang),
        caption=t("chart_desc_sales_offline_combo", lang),
        library="plotly",
    )

    row2_a, row2_b = st.columns(2)
    with row2_a:
        if filtered_offline.empty:
            year_for_quarter = filters.year if filters.year is not None else int(filtered["date"].dt.year.max())
        else:
            year_for_quarter = filters.year if filters.year is not None else int(filtered_offline["date"].dt.year.max())
        chart_card(
            "quarterly_sales", t("chart_title_quarterly_sales", lang), lang,
            build=lambda: build_quarterly_sales_chart(filtered_offline, year_for_quarter, lang, by_brand=multi_brand),
            caption=f"{t('chart_desc_quarterly_sales', lang)} ({year_for_quarter})",
        )
    with row2_b:
        chart_card(
            "annual_sales", t("chart_title_annual_sales", lang), lang,
            build=lambda: build_annual_sales_chart(filtered_offline, lang, by_brand=multi_brand),
            caption=t("chart_desc_annual_sales", lang),
        )

    # بعرض كامل عمدًا (بدل عمود ضيق محاط بعمودين فاضيين) — الرسم الأكبر + Legend
    # المفصّل بالأرقام (راجع charts_offline.py) يستغلان المساحة الإضافية دون فراغ.
    chart_card(
        "offline_donut", t("chart_title_offline_donut", lang), lang,
        build=lambda: build_offline_donut_chart(filtered_offline, lang),
        caption=t("chart_desc_offline_donut", lang),
    )

    # ==== آخر عمليات المعالجة (مبنية من output/summary_*.xlsx الفعلية) ====
    render_last_runs_card(resolve_path(cfg, cfg["paths"]["output_dir"]), lang)

    render_footer(lang)

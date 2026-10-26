"""صفحة Inbound Call — رفع تصدير Maqsam اليومي واستخراج تفاصيل المكالمات، بتصميم الثيم
الفاتح الجديد: صف KPI + صف "أبرز المؤشرات" (تفاعليان مع فلاتر الجدول) + جدول HTML مخصص
(inbound_table.py). المنطق الفعلي كله بـ src/inbound_pipeline.py — مسار مستقل تمامًا عن
run_pipeline الحالي، بدون أي تعديل عليه هنا.

ملاحظة معمارية: compute_filtered() يحسب الصفوف المفلترة (من session_state مباشرة، بدون رسم
أي ودجت) مبكرًا لتغذية KPI/المؤشرات، بينما render_filter_toolbar() يرسم شريط الفلاتر نفسه
بصريًا لاحقًا بموضعه الصحيح (فوق الجدول مباشرة) — راجع inbound_table.py للتفاصيل. الهيدر
أيضًا يُعاد رسمه عبر st.empty() (header_box) فور توفر النتائج ليصير "نتائج الاستخراج" بدل
هيدر الرفع الافتراضي، مع زر تحميل CSV."""
from datetime import date

import pandas as pd
import streamlit as st

from src.call_extraction import CallExtractionError
from src.config import load_config
from src.inbound_pipeline import run_inbound_import
from src.translations import t

from .empty_state import render_empty_state
from .header import render_footer, render_page_header, render_results_header
from .inbound_table import (
    CARD_COMPANY_KEY,
    COMPANY_ALL_VALUE,
    compute_filtered,
    get_company_options,
    phone_search_summary,
    render_filter_toolbar,
    render_table_body,
    sync_company_from_card,
)
from .kpi_card import KPICardData, render_kpi_row
from .phone_format import format_phone_display
from .step_indicator import render_step_indicator


def _icon_tile(name: str) -> str:
    return f'<span class="maz-kpi-icon-tile"><span class="material-symbols-outlined">{name}</span></span>'


_COMPANY_LIST_TOP_N = 4
_COMPANY_LIST_EXPANDED_KEY = "inbound_company_list_expanded"


# تصحيحات عرض فقط لأسماء أسباب معروفة بخطأ إملائي/تنسيق بالبيانات المصدرية — لا تغيّر أي
# شيء بالتجميع/الفلترة نفسها (يُطبَّق على نص العرض فقط، بعد الفرز والعدّ).
_REASON_DISPLAY_FIXES = {
    "jeddah branche": "Jeddah Branch",
}


def _display_reason_name(raw) -> str:
    key = str(raw).strip().lower()
    if key in _REASON_DISPLAY_FIXES:
        return _REASON_DISPLAY_FIXES[key]
    return str(raw).strip().title()


def _top_value_insight(series: pd.Series) -> tuple[str, int, float]:
    """يرجع (القيمة الأكثر تكرارًا, عددها, نسبتها من إجمالي الصفوف غير الفاضية)."""
    non_empty = series[series.astype(str).str.strip() != ""]
    if non_empty.empty:
        return "", 0, 0.0
    counts = non_empty.value_counts()
    top_value = counts.index[0]
    top_count = int(counts.iloc[0])
    pct = (top_count / len(non_empty)) * 100 if len(non_empty) else 0.0
    return str(top_value), top_count, pct


def _render_insight_cards(filtered_df: pd.DataFrame, lang: str, company_options: list[str], total_rows_count: int) -> None:
    with st.container(key="maz_insights_row_wrap"):
        st.markdown(f'<p class="maz-card-title" style="margin:4px 0 12px 0;">{t("inbound_insights_title", lang)}</p>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        # ==== المكالمات حسب الشركة — فلتر شركة ثانٍ داخل البطاقة نفسها، متزامن مع فلتر
        # الهيدر عبر نفس زوج مفاتيح session_state (راجع inbound_table.py: sync_company_from_*) ====
        with col1:
            with st.container(key="maz_card_company_insight"):
                st.markdown(
                    f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">business</span></div>'
                    f'<div class="maz-insight-label">{t("inbound_insight_top_company", lang)}</div>',
                    unsafe_allow_html=True,
                )
                company_select_options = [COMPANY_ALL_VALUE] + company_options
                card_selected_company = st.selectbox(
                    t("inbound_header_company_label", lang),
                    options=company_select_options,
                    format_func=lambda v: t("inbound_filter_all_companies", lang) if v == COMPANY_ALL_VALUE else v,
                    key=CARD_COMPANY_KEY,
                    on_change=sync_company_from_card,
                    label_visibility="collapsed",
                )
                if card_selected_company:
                    company_count = len(filtered_df)
                    pct_of_grand_total = (company_count / total_rows_count * 100) if total_rows_count else 0.0
                    meta = (
                        f'{t("inbound_insight_call_count", lang).format(count=company_count)} · '
                        f'{t("inbound_insight_of_total", lang).format(pct=f"{pct_of_grand_total:.0f}")}'
                    )
                    st.markdown(
                        f'<div class="maz-insight-value">{card_selected_company}</div>'
                        f'<div class="maz-insight-meta">{meta}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    company_series = filtered_df.get("company", pd.Series(dtype=str))
                    non_empty_companies = company_series[company_series.astype(str).str.strip() != ""]
                    company_counts = non_empty_companies.value_counts()
                    max_count = int(company_counts.iloc[0]) if not company_counts.empty else 0

                    show_all = st.session_state.get(_COMPANY_LIST_EXPANDED_KEY, False)
                    hidden_count = max(0, len(company_counts) - _COMPANY_LIST_TOP_N)
                    visible_counts = company_counts if show_all else company_counts.head(_COMPANY_LIST_TOP_N)

                    bars_html = ""
                    for idx, (value, cnt) in enumerate(visible_counts.items()):
                        pct_of_max = (cnt / max_count * 100) if max_count else 0
                        fill_class = "maz-reason-fill" if idx == 0 else "maz-reason-fill-secondary"
                        bars_html += (
                            f'<div class="maz-reason-row">'
                            f'<div class="maz-reason-label-row">'
                            f'<span title="{value}">{value}</span><span>{cnt}</span>'
                            f'</div>'
                            f'<div class="maz-reason-track"><div class="{fill_class}" style="width:{pct_of_max:.0f}%;"></div></div>'
                            f"</div>"
                        )
                    st.markdown(bars_html or '<div class="maz-insight-meta">—</div>', unsafe_allow_html=True)

                    if hidden_count > 0:
                        btn_label = (
                            t("inbound_show_less_companies", lang) if show_all
                            else t("inbound_show_all_companies", lang).format(count=hidden_count)
                        )
                        if st.button(btn_label, key="inbound_company_toggle_btn"):
                            st.session_state[_COMPANY_LIST_EXPANDED_KEY] = not show_all
                            st.rerun()

        # ==== أكثر سبب اتصال (Details) — أعلى 3 أسباب، الشريط نسبي لأعلى سبب (100%) ====
        with col2:
            details_series = filtered_df.get("Details", pd.Series(dtype=str))
            non_empty_details = details_series[details_series.astype(str).str.strip() != ""]
            top3 = non_empty_details.value_counts().head(3)
            max_count = int(top3.iloc[0]) if not top3.empty else 0

            bars_html = ""
            for idx, (value, cnt) in enumerate(top3.items()):
                pct_of_max = (cnt / max_count * 100) if max_count else 0
                fill_class = "maz-reason-fill" if idx == 0 else "maz-reason-fill-secondary"
                bars_html += (
                    f'<div class="maz-reason-row">'
                    f'<div class="maz-reason-label-row">'
                    f'<span title="{value}">{_display_reason_name(value)}</span><span>{cnt}</span>'
                    f'</div>'
                    f'<div class="maz-reason-track"><div class="{fill_class}" style="width:{pct_of_max:.0f}%;"></div></div>'
                    f"</div>"
                )
            st.markdown(
                f'<div class="maz-insight-card">'
                f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">forum</span></div>'
                f'<div class="maz-insight-label">{t("inbound_insight_top_reason", lang)}</div>'
                f"{bars_html}"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ==== أكثر رقم اتصل — سطر واحد nowrap، dir=ltr، محاذاة يمين ====
        with col3:
            number_series = filtered_df.get("Number", pd.Series(dtype=str))
            number, count, _ = _top_value_insight(number_series)
            display_number = format_phone_display(number) if number else "—"
            meta = t("inbound_insight_called_times", lang).format(count=count) if number else ""
            st.markdown(
                f'<div class="maz-insight-card">'
                f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">call</span></div>'
                f'<div class="maz-insight-label">{t("inbound_insight_top_number", lang)}</div>'
                f'<div class="maz-insight-value" dir="ltr">{display_number}</div>'
                f'<div class="maz-insight-meta">{meta}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


_INBOUND_STEPS = ["upload", "process", "results"]


def inbound_call_page() -> None:
    lang = st.session_state.lang
    step_labels = [t("inbound_step_upload_label", lang), t("inbound_step_process_label", lang), t("inbound_step_results_label", lang)]

    today_str = date.today().strftime("%Y-%m-%d")
    subtitle = t("inbound_subtitle_with_date", lang).format(date=today_str)

    header_box = st.empty()
    with header_box.container():
        # بدون eyebrow هنا عمدًا: eyebrow "ان باوند كول" + عنوان "ان باوند كول" يكرر نفس
        # النص مرتين بالهيدر الواحد — العنوان وحده كافٍ بحالة الرفع (قبل توفر النتائج).
        render_page_header(t("inbound_call_title", lang), subtitle, lang)

    step_box = st.empty()

    with st.container(key="maz_card_inbound_upload"):
        uploaded_file = st.file_uploader(
            t("inbound_uploader_label", lang), type=["xlsx", "csv"], label_visibility="collapsed",
        )
        st.markdown(
            f'<div class="maz-upload-chips">'
            f'<span class="maz-upload-chip">{t("upload_chip_xlsx", lang)}</span>'
            f'<span class="maz-upload-chip">{t("upload_chip_csv", lang)}</span>'
            f'<span class="maz-upload-chip">{t("upload_chip_maxsize", lang)}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f'<p class="maz-upload-hint">{t("inbound_upload_hint", lang)}</p>', unsafe_allow_html=True)

    if uploaded_file is None:
        with step_box.container():
            render_step_indicator("upload", step_labels, steps=_INBOUND_STEPS)
        render_footer(lang)
        return

    progress_box = st.empty()
    log_lines: list[str] = []

    def on_progress(msg: str) -> None:
        log_lines.append(msg)
        progress_box.info("\n\n".join(log_lines))

    result = None
    try:
        with st.spinner(t("inbound_spinner_processing", lang)):
            cfg = load_config()
            result = run_inbound_import(uploaded_file, cfg=cfg, on_progress=on_progress)
        progress_box.empty()
    except CallExtractionError as e:
        progress_box.empty()
        with step_box.container():
            render_step_indicator("process", step_labels, steps=_INBOUND_STEPS)
        st.error(f"{t('inbound_error_processing', lang)}\n\n{e}")
    except Exception as e:
        progress_box.empty()
        with step_box.container():
            render_step_indicator("process", step_labels, steps=_INBOUND_STEPS)
        st.error(f"{t('inbound_error_processing', lang)}\n\n{e}")

    if result is not None:
        with step_box.container():
            render_step_indicator("results", step_labels, steps=_INBOUND_STEPS)

        if not result.rows:
            st.success(t("inbound_success_processed", lang))
            render_empty_state(t("inbound_warning_no_rows", lang))
        else:
            total_rows_count = len(result.rows)
            company_options = get_company_options(result.rows)

            def _build_csv(phone_search: str, selected_company: str) -> bytes:
                csv_df, _, _, _ = compute_filtered(
                    result.rows, lang, company_filter=selected_company, phone_search=phone_search,
                )
                return csv_df.to_csv(index=False).encode("utf-8-sig")

            with header_box.container():
                phone_search, selected_company = render_results_header(
                    eyebrow=t("eyebrow_inbound", lang),
                    title=t("inbound_subheader_results", lang),
                    subtitle=subtitle,
                    lang=lang,
                    company_options=company_options,
                    download_label=t("inbound_download_csv_label", lang),
                    build_download_data=_build_csv,
                    download_filename="inbound_calls_filtered.csv",
                    download_mime="text/csv",
                )

            filtered_df, group_enabled, filter_state, df_with_date = compute_filtered(
                result.rows, lang, company_filter=selected_company, phone_search=phone_search,
            )

            phone_banner = phone_search_summary(filtered_df, phone_search)
            if phone_banner is not None:
                if phone_banner["found"]:
                    banner_text = t("inbound_phone_banner_found", lang).format(
                        count=phone_banner["count"],
                        date=phone_banner["last_date"] or "—",
                        company=phone_banner["company"] or "—",
                    )
                else:
                    banner_text = t("inbound_phone_banner_not_found", lang)
                st.markdown(
                    f'<p style="color:var(--text-secondary);font-size:0.88rem;margin:0 0 14px 0;">{banner_text}</p>',
                    unsafe_allow_html=True,
                )

            st.success(t("inbound_success_processed", lang))

            total = len(filtered_df)
            unclassified_count = int((filtered_df["Details"].astype(str).str.strip() == "").sum())
            unclassified_pct = (unclassified_count / total * 100) if total else 0.0
            repeat_numbers = filtered_df["Number"].value_counts()
            repeated_count = int((repeat_numbers > 1).sum())
            repeated_sub = (
                t("inbound_kpi_repeat_callers_zero", lang) if repeated_count == 0
                else t("inbound_kpi_repeat_callers_sub", lang)
            )

            render_kpi_row(
                [
                    KPICardData(
                        label=t("inbound_metric_total", lang), value=f"{total:,}", icon=_icon_tile("call"), accent=True,
                        sub_line=t("inbound_kpi_total_sub", lang),
                    ),
                    KPICardData(
                        label=t("inbound_kpi_unclassified", lang), value=f"{unclassified_count:,}",
                        icon=_icon_tile("label_off"),
                        sub_line=t("inbound_kpi_unclassified_sub", lang).format(pct=f"{unclassified_pct:.0f}"),
                    ),
                    KPICardData(
                        label=t("inbound_kpi_repeat_callers", lang), value=f"{repeated_count:,}",
                        icon=_icon_tile("group"),
                        sub_line=repeated_sub,
                    ),
                ]
            )

            _render_insight_cards(filtered_df, lang, company_options, total_rows_count)

            render_filter_toolbar(df_with_date, filter_state, lang)
            render_table_body(len(result.rows), filtered_df, group_enabled, lang)

        if result.needs_review:
            with st.expander(f"{t('inbound_expander_review', lang)} ({len(result.needs_review)})"):
                review_df = pd.DataFrame(result.needs_review).rename(columns={
                    "call_id": t("inbound_review_col_id", lang),
                    "number": t("inbound_review_col_number", lang),
                    "reason": t("inbound_review_col_reason", lang),
                    "call_summary": t("inbound_review_col_summary", lang),
                })
                st.dataframe(review_df, use_container_width=True, hide_index=True)

        if result.output_path:
            with open(result.output_path, "rb") as f:
                file_data = f.read()
            file_name = result.output_path.replace("\\", "/").split("/")[-1]
            st.download_button(
                t("inbound_download_label", lang),
                data=file_data,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    render_footer(lang)

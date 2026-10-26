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
from .inbound_table import compute_filtered, render_filter_toolbar, render_table_body
from .kpi_card import KPICardData, render_kpi_row
from .phone_format import format_phone_display
from .step_indicator import render_step_indicator


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


def _render_insight_cards(filtered_df: pd.DataFrame, lang: str) -> None:
    with st.container(key="maz_card_insights_row"):
        st.markdown(f'<p class="maz-card-title" style="margin:4px 0 12px 0;">{t("inbound_insights_title", lang)}</p>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        # ==== أكثر شركة ====
        with col1:
            company, count, pct = _top_value_insight(filtered_df.get("company", pd.Series(dtype=str)))
            meta = (
                f'{t("inbound_insight_call_count", lang).format(count=count)} · {t("inbound_insight_of_total", lang).format(pct=f"{pct:.0f}")}'
                if company else ""
            )
            st.markdown(
                f'<div class="maz-insight-card">'
                f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">business</span></div>'
                f'<div class="maz-insight-label">{t("inbound_insight_top_company", lang)}</div>'
                f'<div class="maz-insight-value">{company or "—"}</div>'
                f'<div class="maz-insight-meta">{meta}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        # ==== أكثر سبب اتصال (Details) ====
        with col2:
            details_series = filtered_df.get("Details", pd.Series(dtype=str))
            non_empty_details = details_series[details_series.astype(str).str.strip() != ""]
            empty_details_count = len(details_series) - len(non_empty_details)
            top3 = non_empty_details.value_counts().head(3)

            bars_html = ""
            for value, cnt in top3.items():
                pct_of_total = (cnt / len(non_empty_details) * 100) if len(non_empty_details) else 0
                bars_html += (
                    f'<div class="maz-reason-row">'
                    f'<div class="maz-reason-label-row">'
                    f'<span title="{value}">{str(value).strip().capitalize()}</span><span>{cnt}</span>'
                    f'</div>'
                    f'<div class="maz-reason-track"><div class="maz-reason-fill" style="width:{pct_of_total:.0f}%;"></div></div>'
                    f"</div>"
                )
            no_reason_line = (
                f'<div class="maz-reason-empty-line">{t("inbound_insight_no_reason", lang).format(count=empty_details_count)}</div>'
                if empty_details_count else ""
            )
            top_value_display = str(top3.index[0]).strip().capitalize() if not top3.empty else "—"
            st.markdown(
                f'<div class="maz-insight-card">'
                f'<div class="maz-insight-icon-tile maz-tile-reason"><span class="material-symbols-outlined">forum</span></div>'
                f'<div class="maz-insight-label">{t("inbound_insight_top_reason", lang)}</div>'
                f'<div class="maz-insight-value">{top_value_display}</div>'
                f"{bars_html}{no_reason_line}"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ==== أكثر رقم اتصل ====
        with col3:
            number_series = filtered_df.get("Number", pd.Series(dtype=str))
            number, count, _ = _top_value_insight(number_series)
            display_number = format_phone_display(number) if number else "—"
            meta = t("inbound_insight_called_times", lang).format(count=count) if number else ""
            st.markdown(
                f'<div class="maz-insight-card">'
                f'<div class="maz-insight-icon-tile maz-tile-number"><span class="material-symbols-outlined">call</span></div>'
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
            filtered_df, group_enabled, filter_state, df_with_date = compute_filtered(result.rows, lang)
            csv_bytes = filtered_df.to_csv(index=False).encode("utf-8-sig")

            with header_box.container():
                render_results_header(
                    eyebrow=t("eyebrow_inbound", lang),
                    title=t("inbound_subheader_results", lang),
                    subtitle=subtitle,
                    download_label=t("inbound_download_csv_label", lang),
                    download_data=csv_bytes,
                    download_filename="inbound_calls_filtered.csv",
                    download_mime="text/csv",
                )

            st.success(t("inbound_success_processed", lang))

            total = len(filtered_df)
            serviced_count = int((filtered_df["Call Status"].astype(str).str.lower() == "serviced").sum())
            serviced_pct = (serviced_count / total * 100) if total else 0.0
            unique_numbers = filtered_df["Number"].nunique()
            repeat_numbers = filtered_df["Number"].value_counts()
            repeated_count = int((repeat_numbers > 1).sum())

            render_kpi_row(
                [
                    KPICardData(
                        label=t("inbound_metric_total", lang), value=f"{total:,}", icon="📞", accent=True,
                        sub_line=t("inbound_kpi_total_sub", lang),
                    ),
                    KPICardData(
                        label=t("inbound_kpi_serviced", lang), value=f"{serviced_count:,}", icon="✅",
                        progress_pct=serviced_pct,
                    ),
                    KPICardData(
                        label=t("inbound_kpi_unique_numbers", lang), value=f"{unique_numbers:,}", icon="🔢",
                        sub_line=t("inbound_kpi_unique_sub", lang).format(count=repeated_count),
                    ),
                ]
            )

            _render_insight_cards(filtered_df, lang)

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

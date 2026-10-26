"""صفحة Inbound Call — رفع تصدير Maqsam اليومي واستخراج تفاصيل المكالمات بالذكاء الاصطناعي.
نفس أسلوب/هيكل upload_page.py تمامًا بتصميم موحّد؛ المنطق الفعلي كله بـ src/inbound_pipeline.py
(مسار مستقل تمامًا عن run_pipeline الحالي — بدون أي تداخل أو تأثير عليه)."""
import pandas as pd
import streamlit as st

from src.call_extraction import CallExtractionError
from src.config import load_config
from src.inbound_pipeline import run_inbound_import
from src.translations import t

from .empty_state import render_empty_state
from .header import render_footer, render_page_header
from .kpi_card import KPICardData, render_kpi_row


def inbound_call_page() -> None:
    lang = st.session_state.lang

    render_page_header(t("inbound_call_title", lang), t("inbound_call_subtitle", lang), lang)

    st.markdown('<div class="maz-card">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        t("inbound_uploader_label", lang), type=["xlsx", "csv"], label_visibility="collapsed",
    )
    st.markdown(f'<p class="maz-upload-hint">{t("inbound_upload_hint", lang)}</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_file is not None:
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
            st.error(f"{t('inbound_error_processing', lang)}\n\n{e}")
        except Exception as e:
            progress_box.empty()
            st.error(f"{t('inbound_error_processing', lang)}\n\n{e}")

        if result is not None:
            st.success(t("inbound_success_processed", lang))

            summary = result.summary
            render_kpi_row(
                [
                    KPICardData(label=t("inbound_metric_total", lang), value=f"{summary.get('مكالمات Inbound', 0):,}", icon="📞"),
                    KPICardData(label=t("inbound_metric_with_details", lang), value=f"{summary.get('صفوف تم استخراج Details لها', 0):,}", icon="📝", accent=True),
                    KPICardData(label=t("inbound_metric_review", lang), value=f"{summary.get('صفوف تحتاج مراجعة يدوية', 0):,}", icon="⚠️"),
                    KPICardData(label=t("inbound_metric_brands", lang), value=f"{summary.get('براندات تم حلّها', 0):,}", icon="🏢"),
                    KPICardData(label=t("inbound_metric_complaints", lang), value=f"{summary.get('شكاوى وزارة التجارة المحتملة', 0):,}", icon="🚨"),
                ]
            )

            st.subheader(t("inbound_subheader_results", lang))
            df_rows = pd.DataFrame(result.rows)
            if df_rows.empty:
                render_empty_state(t("inbound_warning_no_rows", lang))
            else:
                flags = result.highlight_flags
                if flags and any(flags):
                    def _highlight_row(row):
                        is_flagged = flags[row.name] if row.name < len(flags) else False
                        return ["background-color: #ffc7ce; color: #9c0006;" if is_flagged else "" for _ in row]
                    st.dataframe(df_rows.style.apply(_highlight_row, axis=1), use_container_width=True, hide_index=True)
                else:
                    st.dataframe(df_rows, use_container_width=True, hide_index=True)

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

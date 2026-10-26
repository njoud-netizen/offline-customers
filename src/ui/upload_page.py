"""صفحة رفع ملف الأوفلاين — نفس منطق/سلوك المعالجة الحالي تمامًا (run_pipeline نفسها
المستخدمة من CLI، بدء المعالجة تلقائيًا عند الرفع كما هو السلوك المقصود اليوم)، بتصميم
الثيم الفاتح الجديد + معاينة أول 10 صفوف + مؤشر خطوات + بانر خطأ أحمر. لا تغيير بأي حساب
أو تصنيف أو بمنطق run_pipeline/invoices.py نفسه — عرض إضافي فقط فوق بيانات موجودة أصلًا."""
import altair as alt
import pandas as pd
import streamlit as st

from src.config import load_config
from src.pipeline import run_pipeline
from src.sheets import GoogleSheetsConnectionError
from src.translations import t, translate_summary_label

from . import theme
from .data_table import render_offline_table
from .empty_state import render_empty_state
from .header import render_footer, render_page_header
from .kpi_card import KPICardData, render_kpi_row
from .step_indicator import STEP_EXTRACT, STEP_UPLOAD, STEP_VALIDATE, render_step_indicator

_SUMMARY_TOTAL_VALID = "إجمالي أرقام صالحة بالفاتورة (بعد التطبيع)"
_SUMMARY_OFFLINE = "مصنّفة كأوفلاين"
_SUMMARY_EXCLUDED = "مستبعدة (إجمالي)"
_SUMMARY_INVALID = "أرقام غير صالحة/مشبوهة (فاتورة + شيت)"
_EXCLUSION_PREFIX = "  -> استبعاد:"


def _exclusion_label(reason_key: str, lang: str) -> str:
    full = translate_summary_label(f"{_EXCLUSION_PREFIX} {reason_key}", lang)
    return full.replace(_EXCLUSION_PREFIX, "").replace("-> Excluded:", "").strip()


def _render_preview(uploaded_file, lang: str) -> None:
    """معاينة أول 10 صفوف خام من الملف كما هو — بدون أي تطبيع/تصنيف (عرض فقط، لا يُستخدم
    بأي مكان بمنطق run_pipeline الفعلي أدناه)."""
    try:
        name = getattr(uploaded_file, "name", "")
        uploaded_file.seek(0)
        if name.lower().endswith((".xlsx", ".xls")):
            full_df = pd.read_excel(uploaded_file)
        else:
            full_df = pd.read_csv(uploaded_file)
    except Exception:
        return
    finally:
        uploaded_file.seek(0)

    st.markdown('<div class="maz-card">', unsafe_allow_html=True)
    st.markdown(f'<p class="maz-card-title">{t("upload_preview_title", lang)}</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="maz-card-subtitle">{t("upload_preview_row_count", lang).format(count=f"{len(full_df):,}")}</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(full_df.head(10), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def upload_page() -> None:
    lang = st.session_state.lang
    step_labels = [t("step_upload_label", lang), t("step_validate_label", lang), t("step_extract_label", lang)]

    render_page_header(t("upload_title", lang), t("upload_subtitle", lang), lang, eyebrow=t("eyebrow_upload", lang))

    st.markdown('<div class="maz-card">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        t("uploader_label", lang), type=["xlsx", "csv"], label_visibility="collapsed",
    )
    st.markdown(f'<p class="maz-upload-hint">{t("upload_hint", lang)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="maz-upload-hint">{t("upload_dropzone_types_hint", lang)}</p>', unsafe_allow_html=True)
    preview_mode = st.checkbox(t("preview_checkbox_label", lang), value=False, help=t("preview_checkbox_help", lang))
    st.markdown("</div>", unsafe_allow_html=True)

    if preview_mode:
        st.warning(t("preview_warning", lang))

    if uploaded_file is None:
        render_step_indicator(STEP_UPLOAD, step_labels)
        render_footer(lang)
        return

    _render_preview(uploaded_file, lang)

    progress_box = st.empty()
    log_lines: list[str] = []

    def on_progress(msg: str) -> None:
        log_lines.append(msg)
        progress_box.info("\n\n".join(log_lines))

    pipeline_result = None
    try:
        with st.spinner(t("spinner_processing", lang)):
            cfg = load_config()
            pipeline_result = run_pipeline(
                uploaded_file, cfg=cfg, on_progress=on_progress, ignore_dedup=preview_mode
            )
        progress_box.empty()
    except GoogleSheetsConnectionError as e:
        progress_box.empty()
        render_step_indicator(STEP_VALIDATE, step_labels)
        st.error(f"{t('error_sheets_connection', lang)}\n\n{e}")
    except Exception as e:
        progress_box.empty()
        render_step_indicator(STEP_VALIDATE, step_labels)
        st.error(f"{t('error_processing', lang)}\n\n{e}")

    if pipeline_result is None:
        render_footer(lang)
        return

    render_step_indicator(STEP_EXTRACT, step_labels)

    if pipeline_result.invalid_rows:
        st.markdown(
            f'<div class="maz-card" style="border-color:#FCA5A5;background:#FEF2F2;">'
            f'<p class="maz-card-title" style="color:{theme.DANGER};">'
            f'{t("upload_error_banner_title", lang)} ({len(pipeline_result.invalid_rows)})</p>',
            unsafe_allow_html=True,
        )
        st.dataframe(pd.DataFrame(pipeline_result.invalid_rows), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div id="maz-offline-results"></div>', unsafe_allow_html=True)
    st.success(t("success_processed", lang))

    summary = pipeline_result.summary
    render_kpi_row(
        [
            KPICardData(label=t("metric_valid_numbers", lang), value=f"{summary.get(_SUMMARY_TOTAL_VALID, 0):,}", icon="📱"),
            KPICardData(label=t("metric_offline", lang), value=f"{summary.get(_SUMMARY_OFFLINE, 0):,}", icon="✅", accent=True),
            KPICardData(label=t("metric_excluded", lang), value=f"{summary.get(_SUMMARY_EXCLUDED, 0):,}", icon="🚫"),
            KPICardData(label=t("metric_invalid", lang), value=f"{summary.get(_SUMMARY_INVALID, 0):,}", icon="⚠️"),
        ]
    )

    with st.expander(t("expander_summary", lang)):
        summary_display = [(translate_summary_label(k, lang), v) for k, v in summary.items()]
        st.dataframe(
            pd.DataFrame(summary_display, columns=[t("summary_col_metric", lang), t("summary_col_value", lang)]),
            use_container_width=True, hide_index=True,
        )

    exclusion_breakdown = {
        k.replace(_EXCLUSION_PREFIX, "").strip(): v for k, v in summary.items() if k.startswith(_EXCLUSION_PREFIX)
    }
    if exclusion_breakdown:
        with st.expander(t("expander_exclusion_breakdown", lang)):
            reason_col = t("exclusion_table_col_reason", lang)
            count_col = t("exclusion_table_col_count", lang)
            reason_df = pd.DataFrame(
                [(_exclusion_label(k, lang), v) for k, v in exclusion_breakdown.items()],
                columns=[reason_col, count_col],
            ).sort_values(count_col, ascending=False)

            chart = (
                alt.Chart(reason_df)
                .mark_bar(color=theme.MAZNEXA_PURPLE, cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
                .encode(
                    y=alt.Y(f"{reason_col}:N", sort="-x", title=t("exclusion_chart_axis_reason", lang)),
                    x=alt.X(f"{count_col}:Q", title=t("chart_axis_count", lang)),
                    tooltip=[reason_col, count_col],
                )
                .properties(height=max(200, 36 * len(reason_df)))
            )
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(reason_df, use_container_width=True, hide_index=True)

    st.subheader(t("subheader_offline_customers", lang))
    df_offline = pd.DataFrame(pipeline_result.offline_rows)
    if df_offline.empty:
        render_empty_state(t("warning_no_offline", lang))
    else:
        render_offline_table(df_offline, lang)

    st.subheader(t("subheader_downloads", lang))
    labels = {
        "offline": (t("download_offline_label", lang), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "excluded": (t("download_excluded_label", lang), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "invalid": (t("download_invalid_label", lang), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "summary": (t("download_summary_label", lang), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    }
    dl_cols = st.columns(4)
    for i, key in enumerate(["offline", "excluded", "invalid", "summary"]):
        out_path = pipeline_result.output_paths.get(key)
        if not out_path:
            continue
        label, mime = labels[key]
        with open(out_path, "rb") as f:
            file_data = f.read()
        file_name = out_path.replace("\\", "/").split("/")[-1]
        dl_cols[i].download_button(
            label, data=file_data, file_name=file_name, mime=mime, use_container_width=True, key=f"dl_{key}",
        )

    render_footer(lang)

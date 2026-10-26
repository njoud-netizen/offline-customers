"""صفحة Inbound Call — رفع تصدير Maqsam اليومي واستخراج تفاصيل المكالمات، بتصميم الثيم
الفاتح الجديد: صف KPI + صف "أبرز المؤشرات" (تفاعليان مع فلاتر الجدول) + جدول HTML مخصص
(inbound_table.py). المنطق الفعلي كله بـ src/inbound_pipeline.py — مسار مستقل تمامًا عن
run_pipeline الحالي، بدون أي تعديل عليه هنا.

ملاحظة معمارية مهمة: الفلاتر تُصيَّر أولًا (render_filter_bar) لأن بطاقات KPI/المؤشرات
يجب تتفاعل معها، رغم إن المواصفة البصرية تضعها داخل بطاقة الجدول بصريًا — Streamlit يُصيَّر
من أعلى لأسفل بمرة واحدة فلا توجد طريقة لودجت لاحق يُغذّي محتوى أعلاه بنفس التشغيلة."""
from datetime import date

import pandas as pd
import streamlit as st

from src.call_extraction import CallExtractionError
from src.config import load_config
from src.inbound_pipeline import run_inbound_import
from src.translations import t

from .empty_state import render_empty_state
from .header import render_footer, render_page_header
from .inbound_table import render_filter_bar, render_table_body
from .kpi_card import KPICardData, render_kpi_row
from .phone_format import format_phone_display


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
    st.markdown(f'<p class="maz-card-title" style="margin:4px 0 12px 0;">{t("inbound_insights_title", lang)}</p>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    # ==== أكثر شركة ====
    with col1:
        company, count, pct = _top_value_insight(filtered_df.get("company", pd.Series(dtype=str)))
        meta = t("inbound_insight_of_total", lang).format(pct=f"{pct:.0f}") if company else t("inbound_insight_empty", lang)
        st.markdown(
            f'<div class="maz-insight-card">'
            f'<div class="maz-insight-icon-tile">🏢</div>'
            f'<div class="maz-insight-label">{t("inbound_insight_top_company", lang)}</div>'
            f'<div class="maz-insight-value">{company or "—"}</div>'
            f'<div class="maz-insight-meta">{t("inbound_insight_times", lang).format(count=count)} · {meta}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    # ==== أكثر سبب اتصال (Details) ====
    with col2:
        details_series = filtered_df.get("Details", pd.Series(dtype=str))
        non_empty_details = details_series[details_series.astype(str).str.strip() != ""]
        empty_details_count = len(details_series) - len(non_empty_details)
        top3 = non_empty_details.value_counts().head(3)
        max_count = int(top3.iloc[0]) if not top3.empty else 0

        bars_html = ""
        for value, cnt in top3.items():
            width_pct = (cnt / max_count * 100) if max_count else 0
            bars_html += (
                f'<div class="maz-mini-bar-row">'
                f'<span class="maz-mini-bar-label" title="{value}">{value}</span>'
                f'<div class="maz-mini-bar-track"><div class="maz-mini-bar-fill" style="width:{width_pct:.0f}%;"></div></div>'
                f'<span style="font-size:0.76rem;color:var(--text-secondary);">{cnt}</span>'
                f"</div>"
            )
        no_reason_line = (
            f'<div class="maz-insight-meta">{t("inbound_insight_no_reason", lang).format(count=empty_details_count)}</div>'
            if empty_details_count else ""
        )
        top_value_display = top3.index[0] if not top3.empty else "—"
        st.markdown(
            f'<div class="maz-insight-card">'
            f'<div class="maz-insight-icon-tile">💬</div>'
            f'<div class="maz-insight-label">{t("inbound_insight_top_reason", lang)}</div>'
            f'<div class="maz-insight-value" style="font-size:16px;">{top_value_display}</div>'
            f"{bars_html}{no_reason_line}"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ==== أكثر رقم اتصل ====
    with col3:
        number_series = filtered_df.get("Number", pd.Series(dtype=str))
        number, count, _ = _top_value_insight(number_series)
        common_reason = ""
        if number:
            rows_for_number = filtered_df[filtered_df["Number"] == number]
            common_reason, _, _ = _top_value_insight(rows_for_number.get("Details", pd.Series(dtype=str)))
        display_number = format_phone_display(number) if number else "—"
        meta = common_reason if common_reason else t("inbound_insight_empty", lang)
        st.markdown(
            f'<div class="maz-insight-card">'
            f'<div class="maz-insight-icon-tile">📞</div>'
            f'<div class="maz-insight-label">{t("inbound_insight_top_number", lang)}</div>'
            f'<div class="maz-insight-value" dir="ltr" style="font-size:18px;">{display_number}</div>'
            f'<div class="maz-insight-meta">{t("inbound_insight_times", lang).format(count=count)} · {meta}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )


def inbound_call_page() -> None:
    lang = st.session_state.lang

    today_str = date.today().strftime("%Y-%m-%d")
    render_page_header(
        t("inbound_call_title", lang),
        t("inbound_subtitle_with_date", lang).format(date=today_str),
        lang,
        eyebrow=t("eyebrow_inbound", lang),
    )

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

            if not result.rows:
                render_empty_state(t("inbound_warning_no_rows", lang))
            else:
                filtered_df, group_enabled = render_filter_bar(result.rows, lang)

                total = len(filtered_df)
                serviced_count = int((filtered_df["Call Status"].astype(str).str.lower() == "serviced").sum())
                serviced_pct = (serviced_count / total * 100) if total else 0.0
                unique_numbers = filtered_df["Number"].nunique()
                repeat_numbers = filtered_df["Number"].value_counts()
                repeated_count = int((repeat_numbers > 1).sum())

                render_kpi_row(
                    [
                        KPICardData(label=t("inbound_metric_total", lang), value=f"{total:,}", icon="📞", accent=True),
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

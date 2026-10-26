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
    COMPANY_MULTISELECT_KEY,
    compute_filtered,
    get_company_options,
    get_top_company,
    phone_search_summary,
    render_filter_toolbar,
    render_table_body,
)
from .kpi_card import KPICardData, render_kpi_row
from .phone_format import format_phone_display
from .step_indicator import render_step_indicator


def _icon_tile(name: str) -> str:
    return f'<span class="maz-kpi-icon-tile"><span class="material-symbols-outlined">{name}</span></span>'


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


def _format_called_times(count: int, lang: str) -> str:
    if count == 1:
        return t("inbound_called_once", lang)
    if count == 2:
        return t("inbound_called_twice", lang)
    return t("inbound_insight_called_times", lang).format(count=count)


def _ranked_bars_html(counts: "pd.Series[int]", display_fn=str) -> str:
    """يبني صفوف شريط مرتبة (اسم يمين + عدد يسار + شريط تحتها نسبي لأعلى قيمة) — نفس
    التنسيق المشترك بين بطاقتي الشركات والأسباب."""
    if counts.empty:
        return '<div class="maz-insight-meta">—</div>'
    max_count = int(counts.iloc[0])
    rows = []
    for idx, (value, cnt) in enumerate(counts.items()):
        pct_of_max = (cnt / max_count * 100) if max_count else 0
        fill_class = "maz-reason-fill" if idx == 0 else "maz-reason-fill-secondary"
        rows.append(
            f'<div class="maz-reason-row">'
            f'<div class="maz-reason-label-row">'
            f'<span title="{value}">{display_fn(value)}</span><span>{cnt}</span>'
            f'</div>'
            f'<div class="maz-reason-track"><div class="{fill_class}" style="width:{pct_of_max:.0f}%;"></div></div>'
            f"</div>"
        )
    return "".join(rows)


def _render_insight_section(
    filtered_df: pd.DataFrame, lang: str, company_options: list[str], top_company: str,
) -> None:
    """صف "أبرز المؤشرات": عنوان + st.multiselect الشركات (ودجتان حقيقيتان فوق)، ثم البطاقات
    الثلاث كـHTML خام واحد داخل CSS Grid (لا st.columns) — Grid مع align-items:stretch يجعل
    الثلاث بنفس الارتفاع تلقائيًا بكل الحالات، بدون أي حيلة DOM/CSS إضافية."""
    col_title, col_multiselect = st.columns([1, 2])
    with col_title:
        st.markdown(f'<p class="maz-card-title" style="margin:10px 0 0 0;">{t("inbound_insights_title", lang)}</p>', unsafe_allow_html=True)
    with col_multiselect:
        with st.container(key="maz_company_multiselect"):
            st.multiselect(
                t("inbound_company_multiselect_label", lang),
                options=company_options,
                default=[top_company] if top_company else [],
                placeholder=t("inbound_company_multiselect_placeholder", lang),
                key=COMPANY_MULTISELECT_KEY,
                label_visibility="collapsed",
            )

    # ==== بطاقة "المكالمات حسب الشركة" — سطر لكل شركة ظاهرة بالـfiltered_df نفسه (أصلًا
    # مفلتر حسب اختيار المستخدم أو كل الشركات لو فاضي — راجع compute_filtered بالمستدعي) ====
    company_series = filtered_df.get("company", pd.Series(dtype=str))
    company_counts = company_series[company_series.astype(str).str.strip() != ""].value_counts()
    company_card_html = (
        f'<div class="maz-insight-card">'
        f'<div class="maz-insight-header">'
        f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">business</span></div>'
        f'<div class="maz-insight-label">{t("inbound_insight_top_company", lang)}</div>'
        f"</div>"
        f'<div class="maz-insight-body">{_ranked_bars_html(company_counts)}</div>'
        f"</div>"
    )

    # ==== بطاقة "أكثر سبب اتصال" — أعلى 3 أسباب، نفس نمط الأشرطة ====
    details_series = filtered_df.get("Details", pd.Series(dtype=str))
    top3_details = details_series[details_series.astype(str).str.strip() != ""].value_counts().head(3)
    reason_card_html = (
        f'<div class="maz-insight-card">'
        f'<div class="maz-insight-header">'
        f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">forum</span></div>'
        f'<div class="maz-insight-label">{t("inbound_insight_top_reason", lang)}</div>'
        f"</div>"
        f'<div class="maz-insight-body">{_ranked_bars_html(top3_details, _display_reason_name)}</div>'
        f"</div>"
    )

    # ==== بطاقة "أكثر رقم اتصل" — سطر واحد nowrap، dir=ltr، محاذاة يمين ====
    number_series = filtered_df.get("Number", pd.Series(dtype=str))
    number, count, _ = _top_value_insight(number_series)
    display_number = format_phone_display(number) if number else "—"
    number_meta = _format_called_times(count, lang) if number else ""
    number_card_html = (
        f'<div class="maz-insight-card">'
        f'<div class="maz-insight-header">'
        f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">call</span></div>'
        f'<div class="maz-insight-label">{t("inbound_insight_top_number", lang)}</div>'
        f"</div>"
        f'<div class="maz-insight-body">'
        f'<div class="maz-insight-value" dir="ltr">{display_number}</div>'
        f'<div class="maz-insight-meta">{number_meta}</div>'
        f"</div></div>"
    )

    st.markdown(
        f'<div class="maz-insights-grid">{company_card_html}{reason_card_html}{number_card_html}</div>',
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
            company_options = get_company_options(result.rows)
            top_company = get_top_company(result.rows)
            # قراءة مبكرة لاختيار الشركات (نفس أسلوب التاريخ/التفاصيل بـinbound_table.py) —
            # ودجت multiselect الشركات نفسه يُرسم لاحقًا داخل _render_insight_section (فوق
            # البطاقات مباشرة)، لكن الهيدر يحتاج القيمة الحالية *قبل* ذلك لزر تحميل CSV.
            # الافتراضي [أعلى شركة] يطابق default= الممرر لاحقًا لنفس الودجت أول مرة بالضبط.
            selected_companies = st.session_state.get(
                COMPANY_MULTISELECT_KEY, [top_company] if top_company else [],
            )

            def _build_csv(phone_search: str) -> bytes:
                csv_df, _, _, _ = compute_filtered(
                    result.rows, lang, company_filter=selected_companies, phone_search=phone_search,
                )
                return csv_df.to_csv(index=False).encode("utf-8-sig")

            with header_box.container():
                phone_search = render_results_header(
                    eyebrow=t("eyebrow_inbound", lang),
                    title=t("inbound_subheader_results", lang),
                    subtitle=subtitle,
                    lang=lang,
                    download_label=t("inbound_download_csv_label", lang),
                    build_download_data=_build_csv,
                    download_filename="inbound_calls_filtered.csv",
                    download_mime="text/csv",
                )

            filtered_df, group_enabled, filter_state, df_with_date = compute_filtered(
                result.rows, lang, company_filter=selected_companies, phone_search=phone_search,
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

            _render_insight_section(filtered_df, lang, company_options, top_company)

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

"""صفحة Inbound Call — رفع تصدير Maqsam اليومي واستخراج تفاصيل المكالمات، بتصميم الثيم
الفاتح الجديد: صف KPI + صف "أبرز المؤشرات" (تفاعليان مع فلاتر الجدول) + جدول HTML مخصص
(inbound_table.py). المنطق الفعلي كله بـ src/inbound_pipeline.py — مسار مستقل تمامًا عن
run_pipeline الحالي، بدون أي تعديل عليه هنا.

ملاحظة معمارية: compute_filtered() يحسب الصفوف المفلترة (من session_state مباشرة، بدون رسم
أي ودجت) مبكرًا لتغذية KPI/المؤشرات، بينما render_filter_toolbar() يرسم شريط الفلاتر نفسه
بصريًا لاحقًا بموضعه الصحيح (فوق الجدول مباشرة) — راجع inbound_table.py للتفاصيل. الهيدر
أيضًا يُعاد رسمه عبر st.empty() (header_box) فور توفر النتائج ليصير "نتائج الاستخراج" بدل
هيدر الرفع الافتراضي، مع زر تحميل CSV."""
import html
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
    COMPANY_MODE_ALL,
    COMPANY_MODE_TOP,
    COMPANY_SELECT_KEY,
    NUMBER_MODE_TOP,
    NUMBER_SELECT_KEY,
    REASON_MODE_ALL,
    REASON_MODE_BOTTOM,
    REASON_MODE_TOP,
    REASON_SELECT_KEY,
    compute_filtered,
    phone_search_summary,
    render_filter_toolbar,
    render_table_body,
    resolve_insight_state,
)
from .kpi_card import KPICardData, render_kpi_row
from .phone_format import format_phone_display
from .step_indicator import render_step_indicator


def _icon_tile(name: str) -> str:
    return f'<span class="maz-kpi-icon-tile"><span class="material-symbols-outlined">{name}</span></span>'


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
        display_value = html.escape(str(display_fn(value)))
        rows.append(
            f'<div class="maz-reason-row">'
            f'<div class="maz-reason-label-row">'
            f'<span title="{display_value}">{display_value}</span><span>{cnt}</span>'
            f'</div>'
            f'<div class="maz-reason-track"><div class="{fill_class}" style="width:{pct_of_max:.0f}%;"></div></div>'
            f"</div>"
        )
    return "".join(rows)


def _company_option_label(value: str, lang: str) -> str:
    if value == COMPANY_MODE_TOP:
        return t("inbound_select_company_top", lang)
    if value == COMPANY_MODE_ALL:
        return t("inbound_filter_all_companies", lang)
    return value


def _reason_option_label(value: str, lang: str) -> str:
    if value == REASON_MODE_TOP:
        return t("inbound_select_reason_top", lang)
    if value == REASON_MODE_BOTTOM:
        return t("inbound_select_reason_bottom", lang)
    if value == REASON_MODE_ALL:
        return t("inbound_select_reason_all", lang)
    return str(value)


def _number_card_title(choice: str, lang: str) -> str:
    if choice == NUMBER_MODE_TOP:
        return t("inbound_insight_top_number", lang)
    return format_phone_display(choice)


def _number_option_label(value: str, counts: "pd.Series[int]", lang: str) -> str:
    if value == NUMBER_MODE_TOP:
        return t("inbound_insight_top_number", lang)
    count = int(counts.get(value, 0))
    return t("inbound_number_option_format", lang).format(number=format_phone_display(value), count=count)


def _isolated_value(value: str) -> str:
    """يعزل قيمة لاتينية (رقم/تاريخ/اسم إنجليزي) عن انعكاس ثنائي الاتجاه بالنص العربي
    المحيط بها (unicode-bidi: isolate)، بدون التأثير على القيمة نفسها."""
    return f'<span dir="ltr" style="unicode-bidi:isolate;">{value}</span>'


def _company_card_body(state: dict, lang: str) -> str:
    choice = state["company_choice"]
    if choice == COMPANY_MODE_ALL:
        return _ranked_bars_html(state["company_counts"])
    name = state["top_company"] if choice == COMPANY_MODE_TOP else choice
    if not name:
        return '<div class="maz-insight-meta">—</div>'
    count = int(state["company_counts"].get(name, 0))
    total = len(state["df"])
    pct = (count / total * 100) if total else 0.0
    meta = (
        f'{t("inbound_insight_call_count", lang).format(count=count)} · '
        f'{t("inbound_insight_of_total", lang).format(pct=f"{pct:.0f}")}'
    )
    return f'<div class="maz-insight-value">{html.escape(name)}</div><div class="maz-insight-meta">{meta}</div>'


def _reason_card_body(state: dict, lang: str) -> str:
    choice = state["reason_choice"]
    if choice == REASON_MODE_ALL:
        return _ranked_bars_html(state["reason_counts"])
    name = state["reason_display"]
    if not name:
        return '<div class="maz-insight-meta">—</div>'
    count = int(state["reason_counts"].get(name, 0))
    total = len(state["company_scoped_df"])
    pct = (count / total * 100) if total else 0.0
    meta = (
        f'{t("inbound_insight_call_count", lang).format(count=count)} · '
        f'{t("inbound_insight_of_company_total", lang).format(pct=f"{pct:.0f}")}'
    )
    return f'<div class="maz-insight-value">{html.escape(name)}</div><div class="maz-insight-meta">{meta}</div>'


def _number_card_body(state: dict, lang: str) -> str:
    number = state["number_display"]
    if not number:
        return '<div class="maz-insight-meta">—</div>'
    count = int(state["number_counts"].get(number, 0))
    display_number = format_phone_display(number)
    times_text = _format_called_times(count, lang)

    scoped = state["company_scoped_df"]
    rows_for_number = scoped[scoped["Number"] == number]
    last_date = str(rows_for_number["Date"].max()) if not rows_for_number.empty else "—"
    company_name = "—"
    reason_name = "—"
    if not rows_for_number.empty:
        nz_company = rows_for_number.get("company", pd.Series(dtype=str))
        nz_company = nz_company[nz_company.astype(str).str.strip() != ""]
        if not nz_company.empty:
            company_name = str(nz_company.iloc[0])
        nz_reason = rows_for_number.get("Details", pd.Series(dtype=str))
        nz_reason = nz_reason[nz_reason.astype(str).str.strip() != ""]
        if not nz_reason.empty:
            reason_name = str(nz_reason.iloc[0])

    date_line = f'{t("inbound_last_call_label", lang)} {_isolated_value(html.escape(last_date))}'
    company_line = f'{t("inbound_insight_company_label", lang)} {_isolated_value(html.escape(company_name))}'
    reason_line = f'{t("inbound_insight_reason_label", lang)} {_isolated_value(html.escape(reason_name))}'

    return (
        f'<div class="maz-insight-value">{_isolated_value(display_number)}</div>'
        f'<div class="maz-insight-meta">{times_text}</div>'
        f'<div class="maz-insight-meta">{date_line}</div>'
        f'<div class="maz-insight-meta">{company_line}</div>'
        f'<div class="maz-insight-meta">{reason_line}</div>'
    )


def _render_insight_section(state: dict, lang: str) -> None:
    """صف "أبرز المؤشرات": عنوان + صف 3 selectbox (نفس عرض/ترتيب البطاقات، كل عمود فوق
    بطاقته)، ثم البطاقات الثلاث كـHTML خام واحد داخل CSS Grid (لا st.columns للبطاقات نفسها)
    — Grid مع align-items:stretch يجعلها بنفس الارتفاع تلقائيًا بكل الحالات. state من
    resolve_insight_state (قراءة مبكرة سابقة بنفس التشغيلة) — هنا فقط نعيد رسم نفس الودجتات
    الثلاثة بنفس المفاتيح (بدون أي إعادة حساب) ثم نبني الكروت من state الجاهز."""
    st.markdown(f'<p class="maz-card-title" style="margin:10px 0 12px 0;">{t("inbound_insights_title", lang)}</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(key="maz_insight_select_company"):
            company_opts = [COMPANY_MODE_TOP, COMPANY_MODE_ALL] + state["company_options"]
            st.selectbox(
                t("inbound_select_company_top", lang), options=company_opts,
                format_func=lambda v: _company_option_label(v, lang),
                key=COMPANY_SELECT_KEY, label_visibility="collapsed",
            )
    with col2:
        with st.container(key="maz_insight_select_reason"):
            reason_opts = [REASON_MODE_TOP, REASON_MODE_BOTTOM, REASON_MODE_ALL] + state["reason_options"]
            st.selectbox(
                t("inbound_select_reason_top", lang), options=reason_opts,
                format_func=lambda v: _reason_option_label(v, lang),
                key=REASON_SELECT_KEY, label_visibility="collapsed",
            )
    with col3:
        with st.container(key="maz_insight_select_number"):
            number_opts = [NUMBER_MODE_TOP] + state["number_options"]
            st.selectbox(
                t("inbound_insight_top_number", lang), options=number_opts,
                format_func=lambda v: _number_option_label(v, state["number_counts"], lang),
                key=NUMBER_SELECT_KEY, label_visibility="collapsed",
            )

    company_label = _company_option_label(state["company_choice"], lang)
    reason_label = _reason_option_label(state["reason_choice"], lang)
    number_label = _number_card_title(state["number_choice"], lang)

    company_card_html = (
        f'<div class="maz-insight-card">'
        f'<div class="maz-insight-header">'
        f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">business</span></div>'
        f'<div class="maz-insight-label">{html.escape(company_label)}</div>'
        f"</div>"
        f'<div class="maz-insight-body">{_company_card_body(state, lang)}</div>'
        f"</div>"
    )
    reason_card_html = (
        f'<div class="maz-insight-card">'
        f'<div class="maz-insight-header">'
        f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">forum</span></div>'
        f'<div class="maz-insight-label">{html.escape(reason_label)}</div>'
        f"</div>"
        f'<div class="maz-insight-body">{_reason_card_body(state, lang)}</div>'
        f"</div>"
    )
    number_card_html = (
        f'<div class="maz-insight-card">'
        f'<div class="maz-insight-header">'
        f'<div class="maz-insight-icon-tile"><span class="material-symbols-outlined">call</span></div>'
        f'<div class="maz-insight-label">{html.escape(number_label)}</div>'
        f"</div>"
        f'<div class="maz-insight-body">{_number_card_body(state, lang)}</div>'
        f"</div>"
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

        if result.unmatched_values:
            items = ", ".join(
                f'{u["column"]}: {u["raw_value"]}' for u in result.unmatched_values
            )
            st.warning(t("inbound_unmatched_values_warning", lang).format(items=items))

        if not result.rows:
            st.success(t("inbound_success_processed", lang))
            render_empty_state(t("inbound_warning_no_rows", lang))
        else:
            # resolve_insight_state يُستدعى هنا مبكرًا (قبل رسم أي ودجت insight فعليًا) —
            # يقرأ اختيارات company/reason/number الحالية من session_state مباشرة (نفس أسلوب
            # القراءة المبكرة المستخدم للتاريخ/البحث بالجولات السابقة)، فالهيدر يحصل على فلاتر
            # الشركة/السبب/الرقم الصحيحة لزر تحميل CSV *قبل* أن تُرسم ودجتات الـselectbox
            # فعليًا لاحقًا داخل _render_insight_section (بنفس المفاتيح، فبالتالي بنفس القيمة).
            insight_state = resolve_insight_state(result.rows)
            # company_table_filter (مو company_filter): الجدول/KPI العلوي يتفلتر بالشركة فقط
            # لو المستخدم اختار شركة محددة صراحةً — بوضع "أكثر شركة" الافتراضي يبقى الإجمالي
            # الحقيقي لكل الشركات (company_filter نفسه يبقى خاص فقط بنطاق بطاقتي الاستفسار/الرقم).
            company_table_filter = insight_state["company_table_filter"]
            reason_table_filter = insight_state["reason_table_filter"]
            number_table_filter = insight_state["number_table_filter"]

            def _build_csv(phone_search: str) -> bytes:
                csv_df, _, _, _ = compute_filtered(
                    result.rows, lang, company_filter=company_table_filter, phone_search=phone_search,
                    reason_filter=reason_table_filter, number_filter=number_table_filter,
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
                result.rows, lang, company_filter=company_table_filter, phone_search=phone_search,
                reason_filter=reason_table_filter, number_filter=number_table_filter,
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

            _render_insight_section(insight_state, lang)

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

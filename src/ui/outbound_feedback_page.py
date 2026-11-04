"""صفحة "اوت باوند – فيد باك": رفع تصدير صوت -> معاينة الصفوف -> تحميل Excel أو نسخ الصفوف. مستقلة تمامًا عن
صفحتي Inbound Call ورفع الأوفلاين، وتعيد استخدام مكوّنات التصميم المشتركة فقط بدون أي تعديل عليها.
المنطق بـsrc/outbound_pipeline.py، والصفحة تقرأ من الشيت فقط ولا تكتب فيه أي شيء."""
import hashlib
import html
import io
from datetime import date

import streamlit as st

from src.config import load_config
from src.outbound_pipeline import (
    COL_AGENT,
    COL_CALL_STATUS,
    COL_CHANNEL,
    COL_COMPANY,
    COL_DATE,
    COL_DETAILS,
    COL_DIRECTION,
    COL_HOW_HEARD,
    COL_NAME,
    COL_NUMBER,
    COL_REMARK,
    COL_SATISFIED,
    COL_STATUS,
    COL_SUBJECT,
    DISSATISFIED,
    SATISFIED,
    STATUS_ANSWER,
    STATUS_NO_ANSWER,
    OutboundInputError,
    build_excel_bytes,
    build_result,
    build_tsv,
    load_export,
    load_sheet_context,
)
from src.translations import t

from .empty_state import render_empty_state
from .header import render_footer, render_page_header
from .kpi_card import KPICardData, render_kpi_row
from .step_indicator import render_step_indicator

_STEPS = ["upload", "process", "results"]
_PREVIEW_KEY = "outbound_preview"

_CALL_LINK = "_call_url"  # مفتاح عرض فقط، ليس من أعمدة الشيت
_EXISTS_MARK = "_exists"  # مفتاح عرض فقط، ليس من أعمدة الشيت
_EXISTS_ROW_STYLE = ' style="background:rgba(245,158,11,0.14);"'

_PREVIEW_COLUMNS = [
    (_EXISTS_MARK, "outbound_col_exists"),
    (COL_NAME, "outbound_col_name"),
    (COL_NUMBER, "outbound_col_number"),
    (_CALL_LINK, "outbound_col_call_link"),
    (COL_DIRECTION, "outbound_col_direction"),
    (COL_CALL_STATUS, "outbound_col_call_status"),
    (COL_CHANNEL, "outbound_col_channel"),
    (COL_SUBJECT, "outbound_col_subject"),
    (COL_DETAILS, "outbound_col_details"),
    (COL_STATUS, "outbound_col_status"),
    (COL_DATE, "outbound_col_date"),
    (COL_COMPANY, "outbound_col_company"),
    (COL_SATISFIED, "outbound_col_satisfied"),
    (COL_HOW_HEARD, "outbound_col_how_heard"),
    (COL_REMARK, "outbound_col_remark"),
    (COL_AGENT, "outbound_col_agent"),
]
_ISSUE_COLUMNS = [(COL_NAME, "outbound_col_name"), (COL_NUMBER, "outbound_col_number")]
_FOLLOW_UP_COLUMNS = _ISSUE_COLUMNS + [(_CALL_LINK, "outbound_col_call_link")]
_DISSATISFIED_COLUMNS = _ISSUE_COLUMNS + [(COL_COMPANY, "outbound_col_company"), (COL_REMARK, "outbound_col_remark")]


def _icon_tile(name: str) -> str:
    return f'<span class="maz-kpi-icon-tile"><span class="material-symbols-outlined">{name}</span></span>'


def _display_row(call) -> dict:
    return {**call.row, _CALL_LINK: call.call_url, _EXISTS_MARK: "1" if call.is_duplicate else ""}


def _table_html(rows: list, columns: list, lang: str, wide: bool = False) -> str:
    """نفس ستايل .maz-table بجدول Inbound Call. كل قيمة تمر عبر html.escape لأنها من ملف خارجي.
    wide: جدول المعاينة (14 عمود) بعرض أكبر وتمرير أفقي بدل كسر الكلمات داخل الخلايا الضيقة."""
    table_style = ' style="table-layout:auto;width:max-content;min-width:100%;"' if wide else ""
    cell_style = ' style="white-space:nowrap;"' if wide else ""
    note_style = ' style="min-width:260px;white-space:normal;"' if wide else ""
    header = "".join(f"<th{cell_style}>{html.escape(t(key, lang))}</th>" for _, key in columns)
    body = []
    for row in rows:
        cells = []
        for column, _ in columns:
            value = str(row.get(column, ""))
            if not value:
                cells.append(f'<td{cell_style}><span class="maz-table-dash">—</span></td>')
            elif column == _CALL_LINK:
                cells.append(
                    f'<td{cell_style}><a href="{html.escape(value)}" target="_blank" rel="noopener noreferrer">'
                    f'{html.escape(t("outbound_listen_call", lang))}</a></td>'
                )
            elif column == _EXISTS_MARK:
                cells.append(f'<td{cell_style}><strong>{html.escape(t("outbound_exists_mark", lang))}</strong></td>')
            elif column in (COL_NUMBER, COL_DATE):
                cells.append(f'<td{cell_style}><bdi dir="ltr" style="unicode-bidi:isolate;">{html.escape(value)}</bdi></td>')
            else:
                style = note_style if column == COL_REMARK else cell_style
                cells.append(f"<td{style}>{html.escape(value)}</td>")
        row_style = _EXISTS_ROW_STYLE if row.get(_EXISTS_MARK) else ""
        body.append(f"<tr{row_style}>{''.join(cells)}</tr>")
    return (
        f'<div class="maz-table-scroll"><table class="maz-table"{table_style}>'
        f"<thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def _render_table_section(key: str, title: str, rows: list, columns: list, lang: str, wide: bool = False) -> None:
    with st.container(key=f"maz_table_card_{key}"):
        st.markdown(f"<h3>{html.escape(title)}</h3>", unsafe_allow_html=True)
        st.markdown(_table_html(rows, columns, lang, wide), unsafe_allow_html=True)


def _load_preview(file_bytes: bytes, file_name: str, cfg: dict):
    """المعاينة تُحسب مرة واحدة لكل ملف: Streamlit يعيد تشغيل الصفحة مع كل ضغطة، وقراءة تبويب
    فيه ~80 ألف صف كل مرة بطيئة بلا فائدة."""
    digest = hashlib.md5(file_bytes).hexdigest()
    cached = st.session_state.get(_PREVIEW_KEY)
    if cached and cached["digest"] == digest:
        return cached["result"], cached["tab"]
    buffer = io.BytesIO(file_bytes)
    buffer.name = file_name
    df = load_export(buffer)
    ctx = load_sheet_context(cfg)
    result = build_result(df, cfg, ctx)
    st.session_state[_PREVIEW_KEY] = {"digest": digest, "result": result, "tab": ctx.tab}
    return result, ctx.tab


def _render_copy_button(rows: list, columns: list, lang: str) -> None:
    text = build_tsv(rows, columns)
    try:
        from .outbound_copy_button import render_copy_button
    except ImportError:
        st.caption(t("outbound_copy_fallback", lang))
        st.code(text, language=None)
        return
    render_copy_button(
        text,
        t("outbound_copy_button", lang),
        t("outbound_copied_message", lang),
        t("outbound_copy_failed", lang),
        "rtl" if lang == "ar" else "ltr",
    )


def _render_extra_columns(extras, lang: str) -> None:
    def label(column: str) -> str:
        if column in extras.transcript:
            return f'{column} ({t("outbound_extra_transcript", lang)})'
        if column in extras.summary:
            return f'{column} ({t("outbound_extra_summary", lang)})'
        if column in extras.source:
            return f'{column} ({t("outbound_extra_source", lang)})'
        return column

    names = "، ".join(label(c) for c in extras.names) or t("outbound_extra_none", lang)
    text = t("outbound_extra_columns", lang).format(columns=html.escape(names))
    st.markdown(f'<p class="maz-upload-hint">{text}</p>', unsafe_allow_html=True)


def _render_warnings(result, lang: str) -> None:
    if result.unlabelled_transcripts:
        st.warning(t("outbound_warning_unlabelled", lang).format(count=result.unlabelled_transcripts))
    if result.excluded_no_number:
        st.warning(t("outbound_warning_no_number", lang).format(count=result.excluded_no_number))
    if result.invalid_numbers:
        st.warning(t("outbound_warning_invalid_numbers", lang).format(items=", ".join(result.invalid_numbers)))
    if result.missing_dates:
        st.warning(t("outbound_warning_missing_dates", lang).format(count=result.missing_dates))
    if result.unmatched:
        items = ", ".join(sorted({f'{u["column"]}: {u["raw_value"]}' for u in result.unmatched}))
        st.warning(t("outbound_warning_unmatched", lang).format(items=items))


def outbound_feedback_page() -> None:
    lang = st.session_state.lang
    step_labels = [t("inbound_step_upload_label", lang), t("inbound_step_process_label", lang), t("inbound_step_results_label", lang)]
    subtitle = t("outbound_subtitle_with_date", lang).format(date=date.today().strftime("%Y-%m-%d"))

    render_page_header(t("outbound_feedback_title", lang), subtitle, lang)
    step_box = st.empty()

    with st.container(key="maz_card_outbound_upload"):
        uploaded_file = st.file_uploader(
            t("outbound_uploader_label", lang), type=["xlsx", "csv"], label_visibility="collapsed",
        )
        st.markdown(
            f'<div class="maz-upload-chips">'
            f'<span class="maz-upload-chip">{t("upload_chip_xlsx", lang)}</span>'
            f'<span class="maz-upload-chip">{t("upload_chip_csv", lang)}</span>'
            f'<span class="maz-upload-chip">{t("upload_chip_maxsize", lang)}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f'<p class="maz-upload-hint">{t("outbound_read_only_hint", lang)}</p>', unsafe_allow_html=True)

    if uploaded_file is None:
        with step_box.container():
            render_step_indicator("upload", step_labels, steps=_STEPS)
        render_footer(lang)
        return

    cfg = load_config()
    try:
        with st.spinner(t("outbound_spinner_processing", lang)):
            result, tab = _load_preview(uploaded_file.getvalue(), uploaded_file.name, cfg)
    except OutboundInputError as e:
        with step_box.container():
            render_step_indicator("process", step_labels, steps=_STEPS)
        st.error(t("outbound_error_missing_columns", lang).format(columns=e))
        render_footer(lang)
        return
    except Exception as e:
        with step_box.container():
            render_step_indicator("process", step_labels, steps=_STEPS)
        st.error(f"{t('outbound_error_processing', lang)}\n\n{e}")
        render_footer(lang)
        return

    with step_box.container():
        render_step_indicator("results", step_labels, steps=_STEPS)

    _render_extra_columns(result.extra_columns, lang)
    _render_warnings(result, lang)

    all_rows = [c.row for c in result.calls]
    if not all_rows:
        render_empty_state(t("outbound_warning_no_rows", lang))
        render_footer(lang)
        return

    def count(column: str, value: str) -> int:
        return sum(1 for r in all_rows if r[column] == value)

    render_kpi_row([
        KPICardData(label=t("outbound_kpi_total", lang), value=f"{len(all_rows):,}", icon=_icon_tile("call"), accent=True),
        KPICardData(label=t("outbound_kpi_answer", lang), value=f"{count(COL_CALL_STATUS, STATUS_ANSWER):,}", icon=_icon_tile("call_made")),
        KPICardData(label=t("outbound_kpi_no_answer", lang), value=f"{count(COL_CALL_STATUS, STATUS_NO_ANSWER):,}", icon=_icon_tile("phone_missed")),
        KPICardData(label=t("outbound_kpi_satisfied", lang), value=f"{count(COL_SATISFIED, SATISFIED):,}", icon=_icon_tile("thumb_up")),
        KPICardData(label=t("outbound_kpi_dissatisfied", lang), value=f"{count(COL_SATISFIED, DISSATISFIED):,}", icon=_icon_tile("thumb_down")),
    ])

    follow_up_rows = [_display_row(c) for c in result.calls if c.needs_follow_up]
    if follow_up_rows:
        st.warning(t("outbound_alert_follow_up", lang).format(count=len(follow_up_rows)))
        _render_table_section("outbound_follow_up", t("outbound_alert_follow_up_title", lang), follow_up_rows, _FOLLOW_UP_COLUMNS, lang)

    missing_how_rows = [r for r in all_rows if r[COL_CALL_STATUS] == STATUS_ANSWER and not r[COL_HOW_HEARD]]
    if missing_how_rows:
        st.warning(t("outbound_alert_missing_how", lang).format(count=len(missing_how_rows)))
        _render_table_section("outbound_missing_how", t("outbound_alert_missing_how_title", lang), missing_how_rows, _ISSUE_COLUMNS, lang)

    dissatisfied_rows = [r for r in all_rows if r[COL_SATISFIED] == DISSATISFIED]
    if dissatisfied_rows:
        _render_table_section("outbound_dissatisfied", t("outbound_dissatisfied_title", lang), dissatisfied_rows, _DISSATISFIED_COLUMNS, lang)

    if result.duplicate_count:
        st.warning(t("outbound_warning_duplicates", lang).format(count=result.duplicate_count))

    preview_rows = [_display_row(c) for c in result.calls]
    _render_table_section("outbound_preview", t("outbound_rows_title", lang).format(count=len(preview_rows)), preview_rows, _PREVIEW_COLUMNS, lang, wide=True)

    st.markdown(f'<p class="maz-upload-hint">{t("outbound_read_tab_note", lang).format(tab=html.escape(tab))}</p>', unsafe_allow_html=True)
    columns = cfg["google_sheets"]["columns"]
    col_copy, col_download = st.columns(2)
    with col_copy:
        _render_copy_button(all_rows, columns, lang)
    with col_download:
        st.download_button(
            t("outbound_download_excel", lang),
            data=build_excel_bytes(all_rows, columns),
            file_name="outbound_feedback.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="outbound_download_excel", use_container_width=True,
        )

    render_footer(lang)

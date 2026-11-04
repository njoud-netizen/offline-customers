"""صفحة "اوت باوند – فيد باك": رفع تصدير صوت -> زر تحميل Excel بالهيدر + خمس بطاقات، لكل بطاقة سهم يفتح قائمة مكالماتها.
مستقلة تمامًا عن صفحتي Inbound Call ورفع الأوفلاين، وتعيد استخدام مكوّنات التصميم المشتركة فقط بدون أي تعديل عليها.
المنطق بـsrc/outbound_pipeline.py، والصفحة تقرأ الملف المرفوع فقط ولا تتعامل مع الشيت إطلاقًا."""
import hashlib
import html
import io
from datetime import date

import streamlit as st

from src.config import load_config
from src.outbound_pipeline import (
    COL_CALL_STATUS,
    COL_COMPANY,
    COL_HOW_HEARD,
    COL_NAME,
    COL_NUMBER,
    COL_REMARK,
    COL_SATISFIED,
    DISSATISFIED,
    SATISFIED,
    STATUS_ANSWER,
    STATUS_NO_ANSWER,
    OutboundInputError,
    build_excel_bytes,
    build_result,
    load_export,
)
from src.translations import t

from .empty_state import render_empty_state
from .header import render_footer
from .icon_button import icon_download_button

_PREVIEW_KEY = "outbound_preview"
_OPEN_CARD_KEY = "outbound_open_card"

_CALL_LINK = "_call_url"  # مفتاح عرض فقط، ليس من أعمدة الشيت

_LIST_COLUMNS = [
    (COL_NAME, "outbound_col_name"),
    (COL_NUMBER, "outbound_col_number"),
    (COL_COMPANY, "outbound_col_company"),
    (COL_SATISFIED, "outbound_col_satisfied"),
    (COL_HOW_HEARD, "outbound_col_how_heard"),
    (COL_REMARK, "outbound_col_remark"),
    (_CALL_LINK, "outbound_col_listen"),
]
_NO_ANSWER_COLUMNS = [
    (COL_NAME, "outbound_col_name"),
    (COL_NUMBER, "outbound_col_number"),
    (COL_COMPANY, "outbound_col_company"),
    (_CALL_LINK, "outbound_col_listen"),
]

# (المعرّف، مفتاح الترجمة، الأيقونة، بطاقة معبّأة، شرط الصف، أعمدة القائمة)
_CARDS = [
    ("total", "outbound_kpi_total", "call", True, lambda r: True, _LIST_COLUMNS),
    ("answer", "outbound_kpi_answer", "call_made", False, lambda r: r[COL_CALL_STATUS] == STATUS_ANSWER, _LIST_COLUMNS),
    ("no_answer", "outbound_kpi_no_answer", "phone_missed", False, lambda r: r[COL_CALL_STATUS] == STATUS_NO_ANSWER, _NO_ANSWER_COLUMNS),
    ("satisfied", "outbound_kpi_satisfied", "thumb_up", False, lambda r: r[COL_SATISFIED] == SATISFIED, _LIST_COLUMNS),
    ("dissatisfied", "outbound_kpi_dissatisfied", "thumb_down", False, lambda r: r[COL_SATISFIED] == DISSATISFIED, _LIST_COLUMNS),
]

# theme.py يمد أي زر داخل بطاقة KPI فوق البطاقة كاملة وبشفافية، فهنا يُرجَّع مربعًا صغيرًا بالزاوية.
_PAGE_CSS = """
<style>
div[class*="st-key-kpi_card_"][class*="_outbound_"]:has(div[data-testid="stButton"]) { cursor: default; }
div[class*="st-key-outbound_chevron_"] {
    position: absolute !important;
    top: 12px;
    inset-inline-end: 12px;
    width: 32px !important;
    height: 32px;
    z-index: 5;
}
div[class*="st-key-kpi_card_"][class*="_outbound_"] div[data-testid="stButton"] {
    position: static;
    width: 32px;
    height: 32px;
}
div[class*="st-key-kpi_card_"][class*="_outbound_"] div[data-testid="stButton"] button {
    width: 32px;
    height: 32px;
    min-width: 32px;
    min-height: 32px;
    opacity: 1;
    border: none;
    border-radius: 8px;
    background: #F3EEFF;
    color: #683EB5;
    padding: 0;
    line-height: 1;
}
div[class*="st-key-kpi_card_"][class*="_outbound_"] div[data-testid="stButton"] button p {
    color: #683EB5;
    font-size: 22px;
    line-height: 1;
}
</style>
"""

# icon_download_button المشترك ممنوع تعديله ونص التلميح فيه ثابت "تصدير CSV"، فالنص يُستبدل هنا لهذا الزر
# فقط. والثيم يفرض ارتفاع 48px على أزرار التحميل، فيُرجَّع 40×40 ويُدفع لأقصى يسار الهيدر.
_EXCEL_BUTTON_CSS = """
<style>
div[class*="st-key-maz_icon_dl_outbound_excel"] { width: 40px !important; margin-inline-start: auto; }
div[class*="st-key-maz_icon_dl_outbound_excel"] [data-testid="stDownloadButton"] button { min-height: 40px; }
div[class*="st-key-maz_icon_dl_outbound_excel"] .maz-icon-dl-tooltip { font-size: 0; }
div[class*="st-key-maz_icon_dl_outbound_excel"] .maz-icon-dl-tooltip::after { content: "%s"; font-size: 0.72rem; }
</style>
"""


def _icon_tile(name: str) -> str:
    return f'<span class="maz-kpi-icon-tile"><span class="material-symbols-outlined">{name}</span></span>'


def _display_row(call) -> dict:
    return {**call.row, _CALL_LINK: call.call_url}


def _table_html(rows: list, columns: list, lang: str) -> str:
    """نفس ستايل .maz-table بجدول Inbound Call، بعرض يتمدد وتمرير أفقي بدل كسر الكلمات داخل الخلايا.
    كل قيمة تمر عبر html.escape لأنها من ملف خارجي."""
    cell_style = ' style="white-space:nowrap;"'
    note_style = ' style="min-width:260px;white-space:normal;"'
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
            elif column == COL_NUMBER:
                cells.append(f'<td{cell_style}><bdi dir="ltr" style="unicode-bidi:isolate;">{html.escape(value)}</bdi></td>')
            else:
                style = note_style if column == COL_REMARK else cell_style
                cells.append(f"<td{style}>{html.escape(value)}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<div class="maz-table-scroll"><table class="maz-table" style="table-layout:auto;width:max-content;min-width:100%;">'
        f"<thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def _render_header(lang: str):
    """نفس بطاقة render_page_header، وخانة يسار العنوان يُرسم فيها زر التحميل بعد قراءة الملف."""
    subtitle = t("outbound_subtitle_with_date", lang).format(date=date.today().strftime("%Y-%m-%d"))
    with st.container(key="maz_page_header"):
        col_text, col_action = st.columns([3, 1], vertical_alignment="center")
        with col_text:
            st.markdown(f'<h1>{t("outbound_feedback_title", lang)}</h1>', unsafe_allow_html=True)
            st.markdown(f'<div class="maz-page-subtitle">{subtitle}</div>', unsafe_allow_html=True)
        with col_action:
            return st.empty()


def _load_preview(file_bytes: bytes, file_name: str, cfg: dict):
    """المعاينة تُحسب مرة واحدة لكل ملف: Streamlit يعيد تشغيل الصفحة مع كل ضغطة، وإعادة الترجمة
    والتحليل كل مرة بطيئة بلا فائدة. ملف جديد يقفل أي قائمة مفتوحة من الملف السابق."""
    digest = hashlib.md5(file_bytes).hexdigest()
    cached = st.session_state.get(_PREVIEW_KEY)
    if cached and cached["digest"] == digest:
        return cached["result"]
    buffer = io.BytesIO(file_bytes)
    buffer.name = file_name
    df = load_export(buffer)
    result = build_result(df, cfg)
    st.session_state[_PREVIEW_KEY] = {"digest": digest, "result": result}
    st.session_state.pop(_OPEN_CARD_KEY, None)
    return result


def _toggle_card(card_id: str) -> None:
    is_open = st.session_state.get(_OPEN_CARD_KEY) == card_id
    st.session_state[_OPEN_CARD_KEY] = None if is_open else card_id


def _render_cards(calls: list, lang: str) -> None:
    """render_kpi_row المشتركة ما تدعم سهم بالزاوية، فالبطاقة تُرسم هنا بنفس كلاسات التصميم."""
    open_card = st.session_state.get(_OPEN_CARD_KEY)
    for col, (card_id, label_key, icon, accent, matches, _) in zip(st.columns(len(_CARDS)), _CARDS):
        count = sum(1 for c in calls if matches(c.row))
        with col, st.container(key=f"kpi_card_{'accent' if accent else 'plain'}_outbound_{card_id}"):
            st.markdown(
                f'<div class="maz-kpi-inner">'
                f'<div class="maz-kpi-label"><span class="maz-kpi-icon">{_icon_tile(icon)}</span> {html.escape(t(label_key, lang))}</div>'
                f'<div class="maz-kpi-value">{count:,}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.button(
                "▴" if open_card == card_id else "▾",
                key=f"outbound_chevron_{card_id}",
                on_click=_toggle_card,
                args=(card_id,),
            )


def _render_open_list(calls: list, lang: str) -> None:
    open_card = st.session_state.get(_OPEN_CARD_KEY)
    card = next((c for c in _CARDS if c[0] == open_card), None)
    if card is None:
        return
    _, label_key, _, _, matches, columns = card
    rows = [_display_row(c) for c in calls if matches(c.row)]
    with st.container(key="maz_table_card_outbound_list"):
        st.markdown(f"<h3>{html.escape(t(label_key, lang))} ({len(rows):,})</h3>", unsafe_allow_html=True)
        if rows:
            st.markdown(_table_html(rows, columns, lang), unsafe_allow_html=True)
        else:
            render_empty_state(t("outbound_list_empty", lang))


def outbound_feedback_page() -> None:
    lang = st.session_state.lang
    download_slot = _render_header(lang)
    st.markdown(_PAGE_CSS, unsafe_allow_html=True)

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
        st.markdown(f'<p class="maz-upload-hint">{t("outbound_file_only_hint", lang)}</p>', unsafe_allow_html=True)

    if uploaded_file is None:
        render_footer(lang)
        return

    cfg = load_config()
    try:
        with st.spinner(t("outbound_spinner_reading", lang)):
            result = _load_preview(uploaded_file.getvalue(), uploaded_file.name, cfg)
    except OutboundInputError as e:
        st.error(t("outbound_error_missing_columns", lang).format(columns=e))
        render_footer(lang)
        return
    except Exception as e:
        st.error(f"{t('outbound_error_processing', lang)}\n\n{e}")
        render_footer(lang)
        return

    if not result.calls:
        render_empty_state(t("outbound_warning_no_rows", lang))
        render_footer(lang)
        return

    st.markdown(_EXCEL_BUTTON_CSS % t("outbound_download_excel", lang), unsafe_allow_html=True)
    with download_slot.container():
        icon_download_button(
            data=build_excel_bytes([c.row for c in result.calls], cfg["outbound_feedback"]["output_columns"]),
            file_name="outbound_feedback.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="outbound_excel", lang=lang,
        )

    _render_cards(result.calls, lang)
    _render_open_list(result.calls, lang)

    render_footer(lang)

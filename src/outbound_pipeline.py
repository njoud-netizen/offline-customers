"""خط أنابيب صفحة "اوت باوند – فيد باك": تصدير صوت -> صفوف بنفس أعمدة شيت المزروع. مسار مستقل
تمامًا عن inbound_pipeline.py وpipeline.py — لا يكتب أي شيء بالشيت هنا إطلاقًا (الكتابة حصريًا
بـoutbound_sheet_writer.py وبعد ضغط الزر فقط).

القاعدة الأساسية: كل قيمة بعمود له قائمة منسدلة تُطابَق حرفيًا ضد قائمة التبويب المستهدف الحية،
وأي قيمة لا تطابق تبقى فاضية. الأعمدة تُقرأ بالموقع لا بالاسم، لأن عناوين الهيدر الفعلية تختلف بين
التبويبات (مثال حقيقي: A1 بتبويب Sara نص عشوائي، وعمودا WhatsApp مكرران بـNjoud)."""
import io
import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from typing import Callable

import openpyxl
import pandas as pd

from .config import credentials_path
from .phone import normalize_phone
from .sheet_values import match_literal
from .sheets import get_client
from .translate_helper import translate_to_arabic_status

REQUIRED_COLUMNS = [
    "To Number", "Duration (seconds)", "Created At", "Agent Name", "Call Outcome", "Follow-up Reason",
    "Customer Name", "Customer Request", "Call Quality Score", "Sentiment", "Sentiment Reason",
]

COL_REGION = "Region"
COL_NAME = "Name"
COL_NUMBER = "Number"
COL_DIRECTION = "Inbound calls/out bound calls"
COL_CALL_STATUS = "Call Status"
COL_CHANNEL = "WhatsApp&Calls"
COL_SUBJECT = "Subject"
COL_DETAILS = "Details"
COL_STATUS = "Status"
COL_DATE = "Date"
COL_COMPANY = "company"
COL_SATISFIED = "Satisfied/or not"
COL_HOW_HEARD = "How did you hear about us"
COL_REMARK = "Remark"
COL_AGENT = "Agent"

DIRECTION_OUTBOUND = "out bound"
STATUS_ANSWER = "Answer"
STATUS_NO_ANSWER = "No Answer"
CHANNEL_CALL = "call"
SUBJECT_FEEDBACK = "Feedback"
STATUS_DONE = "Done"
SATISFIED = "Satisfied"
DISSATISFIED = "Dissatisfied"
AGENT_AI = "AI"  # عمود Agent بلا قائمة منسدلة بالشيت — نفس الكتابة الحرفية بصفحة Inbound Call

NOTE_CALLBACK = "طلب إعادة الاتصال"
NOTE_GENERIC_DISSATISFIED = "العميل غير راضٍ"
NOTE_MAX_CHARS = 120
NOTE_MIN_REQUEST_WORDS = 3  # أقل من كذا ("أيوة مناسب") ما يوضح سبب عدم الرضا، فيُستخدم Sentiment Reason

_EMPTY_VALUES = {"", "n/a", "na", "nan", "none", "null", "-"}
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_SHEET_DATE_RE = re.compile(r"^\s*(\d{1,2})\s*/\s*([A-Za-z]{3})\s*/\s*(\d{4})\s*$")
_US_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")  # 11/03/2026, 05:56:26 PM GMT+3 = شهر/يوم/سنة
_ISO_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_ARABIC_RE = re.compile(r"[؀-ۿ]")
_DIACRITICS_RE = re.compile(r"[ً-ْ]")
_ALEF_RE = re.compile(r"[أإآ]")
# بادئات/لواحق عربية شائعة حول الكلمة المفتاحية — الكلمة لازم تكون كاملة، فـ"عرض" لا تطابق "المعرض"
_PREFIXES = "وبال|وال|بال|فال|كال|لل|ال|و|ف|ب|ل|ك"
_SUFFIXES = "تكم|تها|تي|كم|ها|نا|ني|ات|ة|ت|ه|ك|ي"


class OutboundInputError(Exception):
    """ملف الإدخال ناقص أو غير صالح — رسالة جاهزة للعرض بالواجهة."""


@dataclass
class SheetContext:
    tab: str
    dropdowns: dict  # {اسم العمود حسب config: [قيم القائمة المنسدلة حرفيًا]}
    existing_keys: set  # {(آخر 9 أرقام, التاريخ)} لصفوف out bound + Feedback + AI الموجودة


@dataclass
class OutboundCall:
    row: dict  # بأعمدة google_sheets.columns بالضبط وبنفس الترتيب
    is_duplicate: bool = False
    needs_manual: bool = False


@dataclass
class OutboundResult:
    calls: list = field(default_factory=list)
    excluded_no_number: int = 0  # مكالمات بدون رقم جوال أصلًا (WEB) — لا تُضاف للشيت
    unmatched: list = field(default_factory=list)  # {"column","raw_value"} خانات تُركت فاضية
    invalid_numbers: list = field(default_factory=list)
    missing_dates: int = 0

    @property
    def new_rows(self) -> list:
        return [c.row for c in self.calls if not c.is_duplicate]

    @property
    def duplicate_count(self) -> int:
        return sum(1 for c in self.calls if c.is_duplicate)


def _clean(value) -> str:
    text = str(value if value is not None else "").strip()
    return "" if text.lower() in _EMPTY_VALUES else text


def load_export(file) -> pd.DataFrame:
    """keep_default_na=False ضروري: pandas يحوّل "N/A" الحرفية لـNaN افتراضيًا، وقواعد الملف
    تعتمد عليها. file: ملف مرفوع من Streamlit أو مسار."""
    name = str(getattr(file, "name", file)).lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(file, dtype=str, keep_default_na=False)
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise OutboundInputError(", ".join(missing))
    return df


def _normalize_text(text: str) -> str:
    return _ALEF_RE.sub("ا", _DIACRITICS_RE.sub("", str(text or ""))).lower()


@lru_cache(maxsize=2048)
def _keyword_pattern(keyword: str) -> "re.Pattern":
    body = r"\s+".join(re.escape(part) for part in _normalize_text(keyword).split())
    return re.compile(rf"(?<!\w)(?:{_PREFIXES})?{body}(?:{_SUFFIXES})?(?!\w)")


def _mentions(text: str, keywords: list) -> bool:
    normalized = _normalize_text(text)
    return any(_keyword_pattern(k).search(normalized) for k in keywords)


def format_number(raw: str) -> tuple[str, bool]:
    """صيغة الشيت: بدون 966 وبدون صفر بأوله (552733333). يرجع (الرقم, صالح؟)؛ رقم غير سعودي يبقى
    بأرقامه كما هي مع تنبيه، وقيمة بلا أرقام (WEB) ترجع فاضية."""
    phone = normalize_phone(raw)
    if phone.valid:
        return phone.normalized[3:], True
    return (phone.normalized, False) if phone.normalized and phone.normalized.isdigit() else ("", False)


def parse_created_at(raw: str) -> "date | None":
    text = _clean(raw)
    try:
        m = _US_DATE_RE.search(text)
        if m:
            return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        m = _ISO_DATE_RE.search(text)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        pass
    return None


def format_sheet_date(value: date) -> str:
    """01 / Jan /2025 — أسماء الشهور ثابتة بدل strftime حتى لا تتأثر بلغة الجهاز."""
    return f"{value.day:02d} / {_MONTHS[value.month - 1]} /{value.year}"


def parse_sheet_date(text: str) -> "date | None":
    m = _SHEET_DATE_RE.match(str(text or ""))
    if not m or m.group(2).title() not in _MONTHS:
        return None
    try:
        return date(int(m.group(3)), _MONTHS.index(m.group(2).title()) + 1, int(m.group(1)))
    except ValueError:
        return None


def extract_company_text(agent_name: str) -> str:
    """"ساره : ليزي بوي  | رضا العملاء" -> "ليزي بوي"."""
    text = _clean(agent_name)
    if ":" not in text:
        return ""
    return text.split(":", 1)[1].split("|", 1)[0].strip()


def _resolve_company(agent_name: str, cfg: dict, values: list, unmatched: list) -> str:
    raw = extract_company_text(agent_name)
    if not raw:
        return ""
    aliases = cfg["outbound_feedback"]["company_aliases"]
    key = _normalize_text(raw)
    target = next((v for k, v in aliases.items() if _normalize_text(k) == key), raw)
    brand_aliases = {name: c.get("sheet_aliases", []) for name, c in cfg["brand_dictionary"].items()}
    literal = match_literal(target, values, aliases=brand_aliases)
    if not literal:
        unmatched.append({"column": COL_COMPANY, "raw_value": raw})
    return literal


def _resolve_how_heard(text: str, cfg: dict) -> str:
    for value, keywords in cfg["outbound_feedback"]["how_heard_keywords"].items():
        if _mentions(text, keywords):
            return value
    return ""


def _resolve_details(request: str, cfg: dict, values: list) -> str:
    """فاضية غالبًا (بالشيت الحقيقي صفان فقط من كل 2792/9300) — تُعبّأ فقط لو العميل ذكر شيئًا
    واضحًا: كلمة مفتاحية صريحة من الإعداد، أو اسم قيمة من القائمة نفسها حرفيًا."""
    if not request:
        return ""
    for value, keywords in cfg["outbound_feedback"]["details_keywords"].items():
        if _mentions(request, keywords):
            return match_literal(value, values)
    for value in values:
        if value.strip() and _mentions(request, [value]):
            return value
    return ""


def _is_dissatisfied(sentiment: str, score_raw: str) -> bool:
    if sentiment.lower() == "negative":
        return True
    score = pd.to_numeric(score_raw, errors="coerce")
    return bool(pd.notna(score) and score <= 3)


def _is_callback_without_rating(follow_up: str, request: str, reason: str, sentiment: str, cfg: dict) -> bool:
    """"دق بعدين" بدون أي تقييم: الرضا يبقى فاضي ويطلع بتنبيه الإكمال اليدوي. درجة الجودة هنا
    لا تعني رأي العميل، فلا تُعتبر تقييمًا، إلا إذا كان الانطباع Negative صريحًا."""
    if sentiment.lower() == "negative":
        return False
    section = cfg["outbound_feedback"]
    asked_callback = _mentions(f"{follow_up} {request} {reason}", section["callback_signals"])
    gave_rating = _mentions(f"{request} {reason}", section["rating_signals"])
    return asked_callback and not gave_rating


def _shorten(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= NOTE_MAX_CHARS:
        return text
    return text[:NOTE_MAX_CHARS].rsplit(" ", 1)[0] + "…"


def _dissatisfied_reason(request: str, reason: str, translate: Callable) -> str:
    """طلب العميل بالعربي هو الأدق لأنه كلامه هو. لو قصير جدًا نأخذ Sentiment Reason (غالبًا
    إنجليزي فيترجم)، ولو فشلت الترجمة جملة عامة بدل نص إنجليزي داخل الشيت."""
    if _ARABIC_RE.search(request) and len(request.split()) >= NOTE_MIN_REQUEST_WORDS:
        return _shorten(request)
    if reason:
        if _ARABIC_RE.search(reason):
            return _shorten(reason)
        translated, ok = translate(reason)
        if ok and _ARABIC_RE.search(translated):
            return _shorten(translated)
    return _shorten(request) if _ARABIC_RE.search(request) else NOTE_GENERIC_DISSATISFIED


def _literal(column: str, value: str, ctx: SheetContext, unmatched: list) -> str:
    literal = match_literal(value, ctx.dropdowns.get(column) or [])
    if value and not literal:
        unmatched.append({"column": column, "raw_value": value})
    return literal


def _row_key(number: str, value: "date | None") -> tuple:
    return (re.sub(r"\D", "", number or "")[-9:], value)


def existing_row_keys(values: list, columns: list) -> set:
    idx = {name: columns.index(name) for name in (COL_NUMBER, COL_DIRECTION, COL_SUBJECT, COL_DATE, COL_AGENT)}

    def cell(row, name):
        i = idx[name]
        return row[i].strip() if i < len(row) else ""

    keys = set()
    for row in values[1:]:
        if (cell(row, COL_DIRECTION).lower() == DIRECTION_OUTBOUND
                and cell(row, COL_SUBJECT).lower() == SUBJECT_FEEDBACK.lower()
                and cell(row, COL_AGENT) == AGENT_AI):
            keys.add(_row_key(cell(row, COL_NUMBER), parse_sheet_date(cell(row, COL_DATE))))
    return keys


def filter_new_rows(rows: list, existing_keys: set) -> list:
    return [r for r in rows if _row_key(r[COL_NUMBER], parse_sheet_date(r[COL_DATE])) not in existing_keys]


def _extract_dropdowns(cells: list, columns: list) -> dict:
    found = {}
    for i, column in enumerate(columns):
        dv = cells[i].get("dataValidation") if i < len(cells) else None
        condition = (dv or {}).get("condition", {})
        if condition.get("type") == "ONE_OF_LIST":
            values = [v.get("userEnteredValue", "") for v in condition.get("values", [])]
            found[column] = [v for v in values if v]
    return found


def load_sheet_context(cfg: dict) -> SheetContext:
    """قراءة فقط. القوائم تُقرأ من التبويب المستهدف نفسه عند أول صف فاضي (مكان الكتابة الفعلي)،
    ثم الصف 2 احتياطًا — القوائم تختلف فعليًا بين التبويبات وبين الصفوف."""
    google_cfg = cfg["google_sheets"]
    columns = google_cfg["columns"]
    tab = cfg["outbound_feedback"]["target_tab"]
    sh = get_client(str(credentials_path(cfg))).open_by_key(google_cfg["spreadsheet_id"])
    ws = sh.worksheet(tab)
    values = ws.get_all_values()
    landing = min(len(values) + 1, ws.row_count)
    meta = sh.fetch_sheet_metadata(params={
        "ranges": [f"'{tab}'!A2:ZZ2", f"'{tab}'!A{landing}:ZZ{landing}"],
        "includeGridData": True,
        "fields": "sheets(data(rowData(values(dataValidation))))",
    })
    dropdowns = {}
    for block in meta["sheets"][0]["data"]:  # الترتيب مقصود: قائمة مكان الكتابة تغلب قائمة الصف 2
        rows = block.get("rowData", [])
        dropdowns.update(_extract_dropdowns(rows[0].get("values", []) if rows else [], columns))
    return SheetContext(tab=tab, dropdowns=dropdowns, existing_keys=existing_row_keys(values, columns))


def build_result(
    df: pd.DataFrame, cfg: dict, ctx: SheetContext, translate: Callable = translate_to_arabic_status,
) -> OutboundResult:
    columns = cfg["google_sheets"]["columns"]
    result = OutboundResult()

    for _, src in df.iterrows():
        number, number_valid = format_number(src["To Number"])
        if not number:
            result.excluded_no_number += 1
            continue
        if not number_valid:
            result.invalid_numbers.append(number)

        created = parse_created_at(src["Created At"])
        if created is None:
            result.missing_dates += 1

        outcome = _clean(src["Call Outcome"])
        duration = pd.to_numeric(_clean(src["Duration (seconds)"]) or "0", errors="coerce")
        answered = bool(outcome) and not (pd.isna(duration) or duration == 0)

        satisfied = how_heard = remark = details = ""
        needs_manual = False
        if answered:
            request = _clean(src["Customer Request"])
            reason = _clean(src["Sentiment Reason"])
            follow_up = _clean(src["Follow-up Reason"])
            sentiment = _clean(src["Sentiment"])
            notes = []
            if _is_callback_without_rating(follow_up, request, reason, sentiment, cfg):
                needs_manual = True
            elif _is_dissatisfied(sentiment, _clean(src["Call Quality Score"])):
                satisfied = DISSATISFIED
                notes.append(_dissatisfied_reason(request, reason, translate))
            else:
                satisfied = SATISFIED
            if follow_up:
                notes.append(NOTE_CALLBACK)
            remark = " | ".join(notes)
            how_heard = _resolve_how_heard(f"{request} {reason}", cfg)
            details = _resolve_details(request, cfg, ctx.dropdowns.get(COL_DETAILS) or [])

        row = {column: "" for column in columns}
        row.update({
            COL_NAME: _clean(src["Customer Name"]),
            COL_NUMBER: number,
            COL_DIRECTION: _literal(COL_DIRECTION, DIRECTION_OUTBOUND, ctx, result.unmatched),
            COL_CALL_STATUS: _literal(COL_CALL_STATUS, STATUS_ANSWER if answered else STATUS_NO_ANSWER, ctx, result.unmatched),
            COL_CHANNEL: _literal(COL_CHANNEL, CHANNEL_CALL, ctx, result.unmatched),
            COL_SUBJECT: _literal(COL_SUBJECT, SUBJECT_FEEDBACK, ctx, result.unmatched),
            COL_DETAILS: details,
            COL_STATUS: _literal(COL_STATUS, STATUS_DONE, ctx, result.unmatched),
            COL_DATE: format_sheet_date(created) if created else "",
            COL_COMPANY: _resolve_company(src["Agent Name"], cfg, ctx.dropdowns.get(COL_COMPANY) or [], result.unmatched),
            COL_SATISFIED: _literal(COL_SATISFIED, satisfied, ctx, result.unmatched),
            COL_HOW_HEARD: _literal(COL_HOW_HEARD, how_heard, ctx, result.unmatched),
            COL_REMARK: remark,
            COL_AGENT: AGENT_AI,
        })
        result.calls.append(OutboundCall(
            row=row,
            is_duplicate=_row_key(number, created) in ctx.existing_keys,
            needs_manual=needs_manual,
        ))
    return result


def build_excel_bytes(rows: list, columns: list) -> bytes:
    """نفس أعمدة الشيت وبنفس الترتيب. كل نص يُحفظ كنص صريح حتى لا يتحول نص يبدأ بـ"=" لصيغة."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(columns)
    for row_idx, row in enumerate(rows, start=2):
        for col_idx, column in enumerate(columns, start=1):
            value = row.get(column, "")
            if column == COL_NUMBER and str(value).isdigit():
                ws.cell(row=row_idx, column=col_idx, value=int(value)).number_format = "0"
            elif value:
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.value = str(value)
                cell.data_type = "s"
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()

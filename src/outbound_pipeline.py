"""خط أنابيب صفحة "اوت باوند – فيد باك": تصدير صوت -> صفوف بنفس أعمدة شيت المزروع. مسار مستقل
تمامًا عن inbound_pipeline.py وpipeline.py — لا يكتب أي شيء بالشيت هنا إطلاقًا (الكتابة حصريًا
بـoutbound_sheet_writer.py وبعد ضغط الزر فقط).

القاعدة الأساسية: كل قيمة بعمود له قائمة منسدلة تُطابَق حرفيًا ضد قائمة التبويب المستهدف الحية،
وأي قيمة لا تطابق تبقى فاضية. الأعمدة تُقرأ بالموقع لا بالاسم، لأن عناوين الهيدر الفعلية تختلف بين
التبويبات (مثال حقيقي: A1 بتبويب Sara نص عشوائي، وعمودا WhatsApp مكرران بـNjoud)."""
import io
import json
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
BASE_COLUMNS = REQUIRED_COLUMNS + ["End Call Initiator", "Batch Name", "Follow-up Required"]

# الأعمدة الإضافية تُعرف من اسمها بعد التطبيع (بدون حروف كبيرة/مسافات/_). الترتيب هو الأولوية.
_TRANSCRIPT_KEYS = ("transcript", "transcription", "conversation", "محادثه", "محادثة", "نصالمكالمه", "نصالمكالمة")
_SUMMARY_KEYS = ("summary", "ملخص")
_SOURCE_KEYS = ("howdidyouhear", "leadsource", "كيفعرف", "source")

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
NOTE_CONTACT_LATER = "طلب التواصل لاحقًا"
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
_NEGATORS = {"ما", "مو", "مب", "مش", "مافي", "ماعندي", "مافيه", "بدون"}  # "لا" مستثناة: "لا، الخدمة سيئة" رأي سلبي فعلي
_NEGATION_WINDOW = 3
_CONFIRMATION_MAX_WORDS = 12
_TIMESTAMP_RE = re.compile(r"[\[(]\s*\d{1,2}(?::\d{2}){1,2}(?:\.\d+)?\s*[\])]|(?m:^\s*\d{1,2}(?::\d{2}){1,2}\s*)")
_TIME_AR_RE = re.compile(
    r"(?<!\w)(?:بعد بكر[ةه]|بكر[ةه]|باكر|غد[اً]+|الليل[ةه]|بالليل|الصبح|الصباح|الظهر|العصر|المغرب|العشاء?|المساء"
    r"|يوم (?:ال[أا]حد|ال[إا]ثنين|الثلاثاء|ال[أا]ربعاء|الخميس|الجمعة|السبت)|ال[أا]سبوع الجاي"
    r"|بعد (?:ساع[ةه]|ساعتين|\d+\s*ساعات|شوي[ةه]?)|الساعة\s*\d{1,2}(?:[:.]\d{2})?)(?!\w)"
)
_TIME_EN_WORDS = (
    ("tomorrow", "بكرة"), ("today", "اليوم"), ("tonight", "الليلة"), ("next week", "الأسبوع الجاي"),
    ("morning", "الصبح"), ("afternoon", "العصر"), ("evening", "المساء"),
)
_TIME_EN_CLOCK_RE = re.compile(r"\bat\s+(\d{1,2}(?::\d{2})?)\s*([ap])?\.?m?\b", re.IGNORECASE)


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
    needs_follow_up: bool = False  # العميل طلب التواصل لاحقًا
    call_url: str = ""  # للعرض بالصفحة فقط: خارج row عمدًا فلا يصل للشيت ولا لملف Excel


@dataclass
class ExtraColumns:
    names: list = field(default_factory=list)  # كل عمود خارج BASE_COLUMNS
    transcript: list = field(default_factory=list)
    summary: list = field(default_factory=list)
    source: list = field(default_factory=list)


@dataclass
class OutboundResult:
    calls: list = field(default_factory=list)
    excluded_no_number: int = 0  # مكالمات بدون رقم جوال أصلًا (WEB) — لا تُضاف للشيت
    unmatched: list = field(default_factory=list)  # {"column","raw_value"} خانات تُركت فاضية
    invalid_numbers: list = field(default_factory=list)
    missing_dates: int = 0
    extra_columns: ExtraColumns = field(default_factory=ExtraColumns)
    unlabelled_transcripts: int = 0  # نصوص ما تحدد المتحدث، فما تُستخدم حتى لا يختلط كلام الإيجنت بالعميل

    @property
    def new_rows(self) -> list:
        return [c.row for c in self.calls if not c.is_duplicate]

    @property
    def duplicate_count(self) -> int:
        return sum(1 for c in self.calls if c.is_duplicate)


@dataclass
class CallSpeech:
    """كلام المكالمة بعد الفصل: الأساس كلام العميل، وكلام الإيجنت يدخل فقط كتأكيد لجوابه."""
    customer: list = field(default_factory=list)  # كل جمل العميل
    statements: list = field(default_factory=list)  # جمله غير الاستفهامية
    confirmed: list = field(default_factory=list)  # جمل تأكيد الإيجنت بعد جواب العميل مباشرة
    rating_answers: list = field(default_factory=list)  # الكلام بعد سؤال الرأي مباشرة
    how_answers: list = field(default_factory=list)  # الكلام بعد سؤال "كيف عرفت عنا" مباشرة


def _clean(value) -> str:
    text = str(value if value is not None else "").strip()
    return "" if text.lower() in _EMPTY_VALUES else text


def _column_key(name) -> str:
    """"Follow-up Reason" و"follow_up_reason" و"FOLLOW UP REASON" نفس العمود."""
    return _ALEF_RE.sub("ا", re.sub(r"[\W_]+", "", str(name).lower()))


def load_export(file) -> pd.DataFrame:
    """keep_default_na=False ضروري: pandas يحوّل "N/A" الحرفية لـNaN افتراضيًا، وقواعد الملف
    تعتمد عليها. file: ملف مرفوع من Streamlit أو مسار."""
    name = str(getattr(file, "name", file)).lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(file, dtype=str, keep_default_na=False)
    canonical = {_column_key(c): c for c in BASE_COLUMNS}
    df.columns = [canonical.get(_column_key(c), str(c).strip()) for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise OutboundInputError(", ".join(missing))
    return df


def _safe_call_url(raw) -> str:
    """http/https فقط: القيمة من ملف خارجي وتنعرض كرابط، فأي مخطط ثاني (javascript:) ما يصير رابط."""
    url = _clean(raw)
    return url if re.match(r"https?://", url, re.IGNORECASE) else ""


def detect_extra_columns(df: pd.DataFrame) -> ExtraColumns:
    extras = [c for c in df.columns if c not in BASE_COLUMNS]

    def matching(keys: tuple) -> list:
        found = []
        for key in keys:
            found += [c for c in extras if key in _column_key(c) and c not in found]
        return found

    return ExtraColumns(
        names=extras,
        transcript=matching(_TRANSCRIPT_KEYS),
        summary=matching(_SUMMARY_KEYS),
        source=matching(_SOURCE_KEYS),
    )


def _normalize_text(text: str) -> str:
    return _ALEF_RE.sub("ا", _DIACRITICS_RE.sub("", str(text or ""))).lower()


@lru_cache(maxsize=2048)
def _keyword_pattern(keyword: str) -> "re.Pattern":
    body = r"\s+".join(re.escape(part) for part in _normalize_text(keyword).split())
    return re.compile(rf"(?<!\w)(?:{_PREFIXES})?{body}(?:{_SUFFIXES})?(?!\w)")


def _mentions(text: str, keywords: list) -> bool:
    normalized = _normalize_text(text)
    return any(_keyword_pattern(k).search(normalized) for k in keywords)


def _mentions_affirmed(text: str, keywords: list) -> bool:
    """مثل _mentions لكن تتجاهل الكلمة المنفية: "ما فيه مشكلة" ما تعني شكوى، و"ما شفت إعلان" ما تعني إعلان."""
    normalized = _normalize_text(text)
    for keyword in keywords:
        for match in _keyword_pattern(keyword).finditer(normalized):
            if not _NEGATORS & set(normalized[:match.start()].split()[-_NEGATION_WINDOW:]):
                return True
    return False


def _sentences(text: str) -> list:
    return [s.strip() for s in re.findall(r"[^.!؟?\n]+[.!؟?]*", str(text or "")) if s.strip(" .!؟?،,\n")]


def _is_question(sentence: str, cfg: dict) -> bool:
    """النصوص المفرّغة آليًا كثيرًا بدون علامات ترقيم، فلازم كلمات الاستفهام والتخيير ("ولا") كمان."""
    return sentence.rstrip().endswith(("؟", "?")) or _mentions(sentence, cfg["outbound_feedback"]["question_markers"])


def _agent_confirmation(text: str, cfg: dict) -> str:
    """أول جملة بدور الإيجنت لو كانت تأكيدًا ("تمام، عن طريق زميلك")، وإلا نص فاضي. السؤال أو
    تعداد الخيارات ("عن طريق انستقرام ولا صديق؟") ليس تأكيدًا أبدًا."""
    sentences = _sentences(text)
    if not sentences or _is_question(sentences[0], cfg):
        return ""
    words = sentences[0].split()
    if len(words) > _CONFIRMATION_MAX_WORDS:
        return ""
    return sentences[0] if _mentions(" ".join(words[:2]), cfg["outbound_feedback"]["agent_confirmation_signals"]) else ""


def _parse_json_turns(text: str, is_customer: Callable) -> list:
    try:
        items = json.loads(text)
    except ValueError:
        return []
    if not isinstance(items, list):
        return []
    turns = []
    for item in items:
        if isinstance(item, dict):
            speaker = item.get("role") or item.get("speaker") or item.get("from") or ""
            content = item.get("content") or item.get("text") or item.get("message") or ""
            if speaker and content:
                turns.append((is_customer(str(speaker)), str(content)))
    return turns


def parse_transcript(text: str, persona: str, cfg: dict) -> list:
    """يرجع [(هل المتحدث العميل؟, النص)]، أو [] لو النص ما يحدد المتحدثين."""
    section = cfg["outbound_feedback"]
    customer_labels = {label.lower() for label in section["customer_labels"]}

    def is_customer(label: str) -> bool:
        return label.strip().lower() in customer_labels

    stripped = str(text or "").strip()
    if stripped.startswith("["):
        turns = _parse_json_turns(stripped, is_customer)
        if turns:
            return turns
    labels = [*section["customer_labels"], *section["agent_labels"], *([persona] if persona else [])]
    alternatives = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
    pattern = re.compile(rf"(?<!\w)({alternatives})\s*(?:[:：]|\s-\s)", re.IGNORECASE)
    cleaned = _TIMESTAMP_RE.sub(" ", stripped)
    matches = list(pattern.finditer(cleaned))
    turns = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
        content = cleaned[match.end():end].strip()
        if content:
            turns.append((is_customer(match.group(1)), content))
    return turns


def _answer_window(turns: list, question_signals: list, cfg: dict) -> list:
    """جواب العميل بعد سؤال موضوع معيّن، مع تأكيد الإيجنت له. ينتهي عند أول سؤال جديد من الإيجنت."""
    answers = []
    active = False
    previous_customer = False
    for customer, content in turns:
        if customer:
            if active:
                answers += [s for s in _sentences(content) if not _is_question(s, cfg)]
        else:
            confirmation = _agent_confirmation(content, cfg) if previous_customer else ""
            if confirmation and (active or _mentions(confirmation, question_signals)):
                answers.append(confirmation)
            if any(_is_question(s, cfg) for s in _sentences(content)):
                active = _mentions(content, question_signals)
        previous_customer = customer
    return answers


def build_speech(src, extras: ExtraColumns, cfg: dict) -> "tuple[CallSpeech | None, bool]":
    """يرجع (الكلام أو None, هل فيه نص مكالمة بدون متحدثين؟). النص الكامل أولًا ثم الملخص. الملخص
    أصلًا بدون متحدثين فيُقرأ كله عدا الأسئلة، أما النص الكامل بدونهم فما يُستخدم."""
    section = cfg["outbound_feedback"]
    persona = _clean(src["Agent Name"]).split(":", 1)[0].strip()
    unlabelled = False
    for column in extras.transcript:
        text = _clean(src[column])
        if not text:
            continue
        turns = parse_transcript(text, persona, cfg)
        if not any(customer for customer, _ in turns):
            unlabelled = True
            continue
        customer = [s for is_customer, content in turns if is_customer for s in _sentences(content)]
        confirmed = []
        previous_customer = False
        for is_customer, content in turns:
            if not is_customer and previous_customer:
                confirmation = _agent_confirmation(content, cfg)
                if confirmation:
                    confirmed.append(confirmation)
            previous_customer = is_customer
        return CallSpeech(
            customer=customer,
            statements=[s for s in customer if not _is_question(s, cfg)],
            confirmed=confirmed,
            rating_answers=_answer_window(turns, section["rating_question_signals"], cfg),
            how_answers=_answer_window(turns, section["how_question_signals"], cfg),
        ), False
    for column in extras.summary:
        text = _clean(src[column])
        if text:
            customer = _sentences(text)
            return CallSpeech(customer=customer, statements=[s for s in customer if not _is_question(s, cfg)]), unlabelled
    return None, unlabelled


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


def _how_heard_from_text(text: str, cfg: dict) -> str:
    for value, keywords in cfg["outbound_feedback"]["how_heard_keywords"].items():
        if _mentions_affirmed(text, keywords):
            return value
    return ""


def _resolve_how_heard(src, extras: ExtraColumns, speech: "CallSpeech | None", cfg: dict, values: list, unmatched: list) -> str:
    """العمود الخاص أولًا، ثم جواب سؤال "كيف عرفت عنا"، ثم باقي كلام العميل، ثم مصادر الاحتياط."""
    for column in extras.source:
        raw = _clean(src[column])
        if raw:
            found = match_literal(raw, values) or _how_heard_from_text(raw, cfg)
            if found:
                return found
            unmatched.append({"column": column, "raw_value": raw})
    if speech:
        for sentences in (speech.how_answers, speech.statements):
            found = _how_heard_from_text("\n".join(sentences), cfg)
            if found:
                return found
    request = [s for s in _sentences(_clean(src["Customer Request"])) if not _is_question(s, cfg)]
    return _how_heard_from_text("\n".join([*request, _clean(src["Sentiment Reason"])]), cfg)


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


def _rating_from_text(text: str, cfg: dict) -> str:
    section = cfg["outbound_feedback"]
    if _mentions_affirmed(text, section["dissatisfied_signals"]):
        return DISSATISFIED
    return SATISFIED if _mentions_affirmed(text, section["satisfied_signals"]) else ""


def _rating_from_speech(speech: "CallSpeech | None", cfg: dict) -> str:
    """كلمات مثل "تمام" و"زين" تُحسب تقييمًا فقط بعد سؤال الرأي، لأنها قبله مجرد رد على التحية."""
    if not speech:
        return ""
    rating = _rating_from_text("\n".join([*speech.statements, *speech.confirmed]), cfg)
    if rating:
        return rating
    answers = "\n".join(speech.rating_answers)
    return SATISFIED if _mentions_affirmed(answers, cfg["outbound_feedback"]["satisfied_answer_signals"]) else ""


def _resolve_rating(speech: "CallSpeech | None", contact_later: bool, src, cfg: dict) -> str:
    sentiment = _clean(src["Sentiment"])
    spoken = _rating_from_speech(speech, cfg)
    if contact_later:
        # طلب التواصل لاحقًا: الرضا من الكلام فقط، ودرجة الجودة هنا ما تعني رأي العميل
        return (
            spoken
            or _rating_from_text(_clean(src["Customer Request"]), cfg)
            or _rating_from_text(_clean(src["Sentiment Reason"]), cfg)
        )
    if spoken:
        # انطباع Negative صريح يغلب كلمات المدح: اعتبار عميل زعلان راضيًا أسوأ من العكس
        return DISSATISFIED if sentiment.lower() == "negative" else spoken
    return DISSATISFIED if _is_dissatisfied(sentiment, _clean(src["Call Quality Score"])) else SATISFIED


def _extract_requested_time(text: str) -> str:
    found = []
    for value in _TIME_AR_RE.findall(text):
        if value not in found:
            found.append(value)
    lowered = text.lower()
    for word, arabic in _TIME_EN_WORDS:
        if re.search(rf"\b{word}\b", lowered) and arabic not in found:
            found.append(arabic)
    clock = _TIME_EN_CLOCK_RE.search(text)
    if clock:
        period = {"a": " صباحًا", "p": " مساءً"}.get((clock.group(2) or "").lower(), "")
        found.append(f"الساعة {clock.group(1)}{period}")
    return " ".join(found)


def _detect_contact_later(speech: "CallSpeech | None", follow_up: str, src, cfg: dict) -> "tuple[bool, str, bool]":
    """يرجع (طلب التواصل لاحقًا؟, الوقت المطلوب, هل المصدر كلام مباشر يثبت إن المكالمة انردت؟)."""
    section = cfg["outbound_feedback"]
    signals = section["callback_signals"]
    spoken = [s for s in (speech.statements if speech else []) if _mentions_affirmed(s, signals)]
    if spoken and _mentions(" ".join(spoken), section["voicemail_signals"]):
        spoken = []  # "المشترك مشغول" رسالة شبكة، مو كلام عميل
    if spoken:
        return True, _extract_requested_time(" ".join(spoken)) or _extract_requested_time(follow_up), True
    if _mentions_affirmed(follow_up, signals):
        return True, _extract_requested_time(follow_up), True
    request = _clean(src["Customer Request"])
    reason = _clean(src["Sentiment Reason"])
    for text in (request, reason):
        if _mentions_affirmed(text, signals):
            return True, _extract_requested_time(text), False
    return False, "", False


def _shorten(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= NOTE_MAX_CHARS:
        return text
    return text[:NOTE_MAX_CHARS].rsplit(" ", 1)[0] + "…"


def _dissatisfied_reason(speech: "CallSpeech | None", request: str, reason: str, cfg: dict, translate: Callable) -> str:
    """جملة العميل نفسها اللي فيها الشكوى هي الأدق، ثم طلبه. لو قصير جدًا نأخذ Sentiment Reason
    (غالبًا إنجليزي فيترجم)، ولو فشلت الترجمة جملة عامة بدل نص إنجليزي داخل الشيت."""
    for sentence in (speech.statements if speech else []):
        if (_ARABIC_RE.search(sentence) and len(sentence.split()) >= NOTE_MIN_REQUEST_WORDS
                and _mentions_affirmed(sentence, cfg["outbound_feedback"]["dissatisfied_signals"])):
            return _shorten(sentence)
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
    extras = detect_extra_columns(df)
    result = OutboundResult(extra_columns=extras)
    url_column = next((c for c in extras.names if _column_key(c) == "callurl"), None)

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
        has_duration = bool(pd.notna(duration) and duration > 0)
        follow_up = _clean(src["Follow-up Reason"])
        speech, unlabelled = build_speech(src, extras, cfg)
        if unlabelled:
            result.unlabelled_transcripts += 1
        contact_later, requested_time, direct_evidence = _detect_contact_later(speech, follow_up, src, cfg)
        # طلب التواصل لاحقًا يعني العميل رد فعلًا، حتى لو Call Outcome = N/A
        answered = has_duration and (bool(outcome) or (contact_later and direct_evidence))

        satisfied = how_heard = remark = details = ""
        needs_follow_up = False
        if answered:
            request = _clean(src["Customer Request"])
            reason = _clean(src["Sentiment Reason"])
            satisfied = _resolve_rating(speech, contact_later, src, cfg)
            notes = []
            if satisfied == DISSATISFIED:
                notes.append(_dissatisfied_reason(speech, request, reason, cfg, translate))
            if contact_later:
                needs_follow_up = True
                notes.append(f"{NOTE_CONTACT_LATER} ({requested_time})" if requested_time else NOTE_CONTACT_LATER)
            elif follow_up:
                notes.append(NOTE_CALLBACK)
            remark = " | ".join(notes)
            how_heard = _resolve_how_heard(src, extras, speech, cfg, ctx.dropdowns.get(COL_HOW_HEARD) or [], result.unmatched)
            details_values = ctx.dropdowns.get(COL_DETAILS) or []
            spoken_text = "\n".join([*speech.customer, *speech.confirmed]) if speech else ""
            details = _resolve_details(spoken_text, cfg, details_values) or _resolve_details(request, cfg, details_values)

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
            needs_follow_up=needs_follow_up,
            call_url=_safe_call_url(src[url_column]) if url_column else "",
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

"""قراءة تصدير Maqsam (صفحة Inbound Call) وتحليل Caller/Callee لتحديد رقم العميل والبراند.

لا علاقة لهذا الملف بمسار مطابقة الفواتير الحالي (pipeline.py/matcher.py) — مسار مستقل تمامًا.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from .phone import PhoneResult, normalize_phone

REQUIRED_COLUMNS = ["ID", "Type", "Created", "State", "Caller", "Callee"]
OPTIONAL_COLUMNS = ["Agent", "Sentiment", "Call Summary", "Recording Links"]


@dataclass
class MaqsamCallRecord:
    call_id: str
    call_type: str  # Inbound / Outbound
    agent: str
    created_raw: str
    created: "datetime | None"
    state: str
    caller_raw: str
    callee_raw: str
    sentiment: str
    call_summary: str
    recording_link: str
    customer_phone: PhoneResult
    brand_raw: "str | None"  # نص الخط غير المحلول (قد يكون غير معروف بـ brand_dictionary)
    canonical_company: "str | None"  # القيمة الكنسية المطابقة لعمود company بشيت المزروع


def _parse_created(value) -> "datetime | None":
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        parsed = pd.to_datetime(text, dayfirst=True)
        return parsed.to_pydatetime()
    except Exception:
        return None


def load_maqsam_export(file) -> pd.DataFrame:
    """
    يقبل مسار ملف أو كائن ملف بالذاكرة (Streamlit UploadedFile). صف العناوين بتصدير Maqsam
    هو الصف الأول دومًا (على عكس ملف الفواتير) — لا حاجة لاكتشاف صف العناوين تلقائيًا.
    """
    name = getattr(file, "name", None) or str(file)
    suffix = Path(name).suffix.lower()
    if hasattr(file, "seek"):
        file.seek(0)

    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(file, dtype=str)
    else:
        df = pd.read_csv(file, dtype=str, keep_default_na=False)

    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"ملف تصدير Maqsam ناقص الأعمدة التالية: {missing}. "
            f"تأكد إنه نفس تصدير 'Call Exports' الأصلي بدون تعديل أسماء الأعمدة."
        )
    for c in OPTIONAL_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df.fillna("")


def _normalize_brand_text(value: "str | None") -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def build_maqsam_line_index(brand_dictionary: dict) -> dict:
    """يرجع {نص الخط المطبّع: canonical_brand} من maqsam_line_aliases لكل براند بـ config.yaml."""
    index = {}
    for canonical, cfg in brand_dictionary.items():
        for alias in cfg.get("maqsam_line_aliases", []):
            index[_normalize_brand_text(alias)] = canonical
    return index


def resolve_customer_and_brand(caller: str, callee: str, maqsam_line_index: dict):
    """
    يجرّب normalize_phone على كل من Caller/Callee لتحديد أيّهم رقم العميل الحقيقي؛ الآخر
    يُفترض نص خط/براند ويُطابَق عبر maqsam_line_index. لا يعتمد على ترتيب العمودين لأن Maqsam
    يبدّل مكانهما بين Inbound/Outbound (ولوحظ بالعينة الحقيقية أن الترتيب قد يختلف حتى بنفس النوع).

    يرجع (phone: PhoneResult, brand_raw: str|None, canonical_company: str|None).
    """
    caller_phone = normalize_phone(caller)
    callee_phone = normalize_phone(callee)

    if caller_phone.valid and not callee_phone.valid:
        phone, brand_raw = caller_phone, callee or None
    elif callee_phone.valid and not caller_phone.valid:
        phone, brand_raw = callee_phone, caller or None
    elif caller_phone.valid and callee_phone.valid:
        # نادر: كلاهما يطبّع كرقم صالح — لا طريقة لتحديد العميل من البراند هنا، نفترض Caller
        # هو العميل (الحالة الغالبة بالمكالمات الحقيقية Inbound) بدون براند محلول.
        phone, brand_raw = caller_phone, None
    else:
        # لا أحدهما رقم صالح — لا رقم عميل يمكن تحديده بثقة؛ نحتفظ بـ Caller كمرجع للمراجعة اليدوية.
        phone, brand_raw = caller_phone, (callee or caller or None)

    canonical_company = maqsam_line_index.get(_normalize_brand_text(brand_raw)) if brand_raw else None
    return phone, brand_raw, canonical_company


def extract_inbound_records(df: pd.DataFrame, brand_dictionary: dict) -> list[MaqsamCallRecord]:
    """يفلتر Type == Inbound فقط — معزولة هنا بـ if واحد لتسهيل توسيعها لـ Outbound لاحقًا."""
    line_index = build_maqsam_line_index(brand_dictionary)
    records: list[MaqsamCallRecord] = []

    for _, row in df.iterrows():
        call_type = str(row.get("Type", "")).strip()
        if call_type.lower() != "inbound":
            continue

        caller = str(row.get("Caller", "")).strip()
        callee = str(row.get("Callee", "")).strip()
        phone, brand_raw, canonical_company = resolve_customer_and_brand(caller, callee, line_index)
        created_raw = str(row.get("Created", "")).strip()

        records.append(MaqsamCallRecord(
            call_id=str(row.get("ID", "")).strip(),
            call_type=call_type,
            agent=str(row.get("Agent", "")).strip(),
            created_raw=created_raw,
            created=_parse_created(created_raw),
            state=str(row.get("State", "")).strip(),
            caller_raw=caller,
            callee_raw=callee,
            sentiment=str(row.get("Sentiment", "")).strip(),
            call_summary=str(row.get("Call Summary", "")).strip(),
            recording_link=str(row.get("Recording Links", "")).strip(),
            customer_phone=phone,
            brand_raw=brand_raw,
            canonical_company=canonical_company,
        ))

    return records

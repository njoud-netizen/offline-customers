"""تطبيع أرقام الجوال — مصدر واحد موحد يُستخدم مع ملف الفواتير وشيت المزروع."""
import re
from dataclasses import dataclass

# أرقام هندية-عربية (Arabic-Indic) وأرقام فارسية موسّعة (Extended Arabic-Indic) -> لاتينية
_DIGIT_MAP = {}
_ARABIC_INDIC = "٠١٢٣٤٥٦٧٨٩"
_EXTENDED_ARABIC_INDIC = "۰۱۲۳۴۵۶۷۸۹"
for i, ch in enumerate(_ARABIC_INDIC):
    _DIGIT_MAP[ch] = str(i)
for i, ch in enumerate(_EXTENDED_ARABIC_INDIC):
    _DIGIT_MAP[ch] = str(i)
_DIGIT_TRANSLATION = str.maketrans(_DIGIT_MAP)

_SCIENTIFIC_NOTATION_RE = re.compile(r"^\s*\d+(\.\d+)?[eE]\+?\d+\s*$")
VALID_SAUDI_MOBILE_RE = re.compile(r"^9665\d{8}$")

# رموز Unicode غير مرئية (bidi control / zero-width) تتسرب أحيانًا من إكسل عند نسخ أرقام بجانب نص عربي:
# ZWSP, ZWNJ, ZWJ, LRM, RLM, LRE, RLE, PDF, LRO, RLO, LRI, RLI, FSI, PDI, BOM
_INVISIBLE_CODEPOINTS = [
    0x200B, 0x200C, 0x200D, 0x200E, 0x200F,
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
    0xFEFF,
]
_INVISIBLE_CHARS_RE = re.compile("[" + "".join(chr(cp) for cp in _INVISIBLE_CODEPOINTS) + "]")


@dataclass
class PhoneResult:
    raw: str
    normalized: str | None
    valid: bool
    reason: str | None  # سبب عدم الصلاحية إن وُجد


def _to_latin_digits(text: str) -> str:
    return text.translate(_DIGIT_TRANSLATION)


def normalize_phone(raw) -> PhoneResult:
    """
    يحوّل أي صيغة رقم جوال (محلي/دولي/أرقام هندية-عربية/تالف من إكسل) إلى الصيغة الموحدة:
    9665XXXXXXXX (966 + 5 + 8 أرقام = 12 رقم إجمالًا).
    أي رقم لا يطابق هذا النمط بعد التطبيع يُعاد بـ valid=False مع سبب دقيق، ولا يُستبعد بصمت.
    """
    original = "" if raw is None else str(raw).strip()

    if not original:
        return PhoneResult(raw=original, normalized=None, valid=False, reason="قيمة فارغة")

    original_cleaned = _INVISIBLE_CHARS_RE.sub("", original).strip()
    if not original_cleaned:
        return PhoneResult(raw=original, normalized=None, valid=False, reason="قيمة فارغة")

    if _SCIENTIFIC_NOTATION_RE.match(original_cleaned):
        return PhoneResult(
            raw=original, normalized=None, valid=False,
            reason="رقم تالف بصيغة Scientific Notation (تلف من إكسل)"
        )

    text = _to_latin_digits(original_cleaned)
    text = re.sub(r"[\s\-]", "", text)
    text = text.replace("+", "")

    if not text.isdigit():
        return PhoneResult(
            raw=original, normalized=None, valid=False,
            reason=f"يحتوي على رموز غير رقمية بعد التنظيف: '{text}'"
        )

    if text.startswith("00966"):
        text = text[2:]  # 00966 -> 966...

    if text.startswith("05") and len(text) == 10:
        normalized = "9665" + text[2:]
    elif text.startswith("5") and len(text) == 9:
        normalized = "9665" + text[1:]
    elif text.startswith("9665") and len(text) == 12:
        normalized = text
    elif text.startswith("966") and len(text) == 12:
        # 966 + 9 digits لكن الرقم الرابع ليس 5 بالضرورة إذا كان محليًا بصيغة أخرى؛ نتحقق أدناه
        normalized = text
    elif text.startswith("966") and len(text) == 13 and text[3] == "0":
        # حالة نادرة: 966 + 0XXXXXXXXX (تسرب صفر محلي أثناء الدمج) -> أزل الصفر الزائد
        normalized = "966" + text[4:]
    else:
        normalized = text  # نتركه للتحقق النهائي أدناه، قد يفشل ويُسجَّل كمشبوه

    if VALID_SAUDI_MOBILE_RE.match(normalized):
        return PhoneResult(raw=original, normalized=normalized, valid=True, reason=None)

    return PhoneResult(
        raw=original, normalized=normalized, valid=False,
        reason=f"لا يطابق نمط رقم جوال سعودي صحيح بعد التطبيع (الناتج: '{normalized}')"
    )

"""تحويل قيم المبالغ النصية (مع فواصل آلاف مثل '2,517.00') لأرقام عشرية.
وحدة منفصلة (بدون أي استيراد من ملفات أخرى بالمشروع) لتفادي استيراد دائري بين
invoices.py (يحتاجها لعمود Amount بالفاتورة) وsales_data.py (يحتاجها لعمود Amount بشيت Sales Data).
"""
import re

_AMOUNT_CLEAN_RE = re.compile(r"[^\d.\-]")


def parse_amount_value(raw) -> float:
    """يرجع 0.0 لأي قيمة فارغة/غير قابلة للتحويل بدل رفع استثناء."""
    if not raw or not str(raw).strip():
        return 0.0
    cleaned = _AMOUNT_CLEAN_RE.sub("", str(raw).strip())
    if not cleaned or cleaned in ("-", "."):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

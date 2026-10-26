"""تنسيق رقم الجوال للعرض فقط: "+966 5X XXX XXXX" بدل الرقم المطبّع الخام (9665XXXXXXXX).
القيمة الخام الأصلية تبقى هي المستخدمة بالبحث/الفرز/التصدير — هذا للعرض البصري فقط، ولا
علاقة له بـ src/phone.py (منطق التطبيع/التحقق نفسه غير مُمَسوس إطلاقًا)."""
import re

_NORMALIZED_RE = re.compile(r"^9665\d{8}$")


def format_phone_display(value: str) -> str:
    raw = (value or "").strip()
    if not _NORMALIZED_RE.match(raw):
        return raw  # رقم غير مطبّع/غير صالح أصلًا -> يُعرض كما هو بدون أي تنسيق
    return f"+966 {raw[3:5]} {raw[5:8]} {raw[8:12]}"

"""شارات ملوّنة (Pill Badges) لعمودي Details/Call Status بجدول Inbound Call.

القيم الخمس المذكورة صراحة بالمواصفة (Offers/Order/Other/Website/فاضي) تُترجم وتُلوَّن حسب
الطلب الصريح. باقي قيم Details الحقيقية (169 قيمة فعلية بالنظام، أكثر بكثير من هذي الأمثلة
الخمسة) تُعرض بنصها الأصلي كما هو (بدون ترجمة — نفس قاعدة translations.py العامة لقيم
البيانات) بلون محايد افتراضي، لأنه لا توجد ترجمة عربية معتمدة للـ164 قيمة الأخرى."""
import html

_KNOWN_DETAILS_LABELS = {
    "offers": ("عروض", "maz-badge-offers"),
    "order": ("طلب", "maz-badge-order"),
    "other": ("أخرى", "maz-badge-other"),
    "website": ("الموقع", "maz-badge-other"),
}


def details_badge_html(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return '<span class="maz-badge-pill maz-badge-other">—</span>'

    known = _KNOWN_DETAILS_LABELS.get(raw.lower())
    if known:
        label, css_class = known
        return f'<span class="maz-badge-pill {css_class}">{html.escape(label)}</span>'

    return f'<span class="maz-badge-pill maz-badge-other">{html.escape(raw)}</span>'


def status_badge_html(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return '<span class="maz-badge-pill maz-badge-other">—</span>'
    if raw.lower() == "serviced":
        return f'<span class="maz-badge-pill maz-badge-serviced">{html.escape(raw)}</span>'
    return f'<span class="maz-badge-pill maz-badge-other">{html.escape(raw)}</span>'


def repeat_badge_html(count: int) -> str:
    return f'<span class="maz-badge-pill maz-badge-repeat">×{count}</span>'

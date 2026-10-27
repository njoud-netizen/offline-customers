"""شارات ملوّنة (Pill Badges) لعمودي Details/Call Status بجدول Inbound Call.

Details: نص خام حرفي من البيانات المصدرية دائمًا — بدون أي ترجمة أو تصحيح إملائي أو
mapping يغيّر القيمة، حسب الطلب الصريح. شارة واحدة موحّدة الشكل لكل قيمة غير فاضية
(خلفية PURPLE_100 / نص PRIMARY_ACTION)؛ القيمة الفاضية تُعرض "—" بدون شارة إطلاقًا.

Call Status: الحالة الوحيدة التي لها ترجمة خاصة هي "Serviced" (تمت الخدمة بالعربي) —
تُترجم حسب لغة الواجهة الحالية عبر translations.py؛ أي حالة أخرى تُعرض بنصها الخام."""
import html

from src.translations import t


def details_badge_html(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return "—"
    return f'<span class="maz-badge-pill maz-badge-details">{html.escape(raw)}</span>'


def status_badge_html(value: str, lang: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return '<span class="maz-badge-pill maz-badge-other">—</span>'
    if raw.lower() == "serviced":
        label = t("inbound_kpi_serviced", lang)
        return (
            f'<span class="maz-badge-pill maz-badge-serviced">'
            f'<span class="maz-status-dot"></span>{html.escape(label)}</span>'
        )
    return f'<span class="maz-badge-pill maz-badge-other">{html.escape(raw)}</span>'


def repeat_badge_html(count: int) -> str:
    return f'<span class="maz-badge-pill maz-badge-repeat">×{count}</span>'

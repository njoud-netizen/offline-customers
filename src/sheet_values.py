"""مطابقة قيمة مستخرجة ضد قائمة منسدلة حية (company/Region/Details بشيت المزروع) — القاعدة
الأساسية: البرنامج يكتب فقط قيمة موجودة حرفيًا بالقائمة، وإلا تبقى الخانة فاضية. لا تخمين ولا
تطابق جزئي أبدًا.

ترتيب المطابقة: (1) تطابق تام مع القائمة بعد تجاهل الحروف الكبيرة/الصغيرة والمسافات والشرطات،
(2) قاموس ALIASES (راجع match_literal)، (3) غير كذا فاضي. القيمة المرجعة دائمًا نص القائمة
الحرفي كما هو (يحافظ على أي مسافة/حالة أحرف فعلية بالشيت الحقيقي، حتى لو كانت "خطأ إدخال")."""
import re


def normalize_for_match(value: str) -> str:
    return re.sub(r"[\s\-]+", "", str(value or "").strip().lower())


def match_literal(raw_value: str, allowed_values: list[str], aliases: dict[str, list[str]] | None = None) -> str:
    """يرجع القيمة الحرفية من allowed_values إذا طابقت raw_value (مباشرة أو عبر aliases)،
    وإلا نص فاضي "". aliases: {القيمة الكنسية المستهدفة: [صيغ بديلة]} — يُطابَق المفتاح نفسه
    وكل صيغة بديلة ضد raw_value، ثم القيمة الكنسية تُطابَق ضد allowed_values."""
    raw = str(raw_value or "").strip()
    if not raw or not allowed_values:
        return ""

    lookup = {normalize_for_match(v): v for v in allowed_values}
    key = normalize_for_match(raw)

    if key in lookup:
        return lookup[key]

    if aliases:
        for canonical, alt_forms in aliases.items():
            candidates = [canonical, *alt_forms]
            if any(key == normalize_for_match(c) for c in candidates):
                canonical_key = normalize_for_match(canonical)
                if canonical_key in lookup:
                    return lookup[canonical_key]
                break

    return ""

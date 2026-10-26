"""استخراج مجاني (بدون أي API مدفوع) لاسم العميل/المدينة/تصنيف Details من نص Call Summary،
بمطابقة كلمات مفتاحية/قوائم ثابتة. أقل دقة من Claude API (call_extraction.py) لكنه بدون تكلفة
إطلاقًا — وهذا هو المسار الافتراضي حاليًا (انظر call_import.extraction_mode بـ config.yaml)."""
import re

from .maqsam_import import MaqsamCallRecord

_DETAILS_OTHER = "Other"

_WORD_RE = re.compile(r"[a-zA-Z]+")

_KNOWN_CITIES = [
    "Riyadh", "Jeddah", "Dammam", "Khobar", "Al Khobar", "Alkhobar", "Mecca", "Makkah", "Medina",
    "Madinah", "Taif", "At-Taif", "Tabuk", "Jizan", "Jazan", "Qassim", "Al Ahsa", "Ahsa", "Hofuf",
    "Khamis Mushait", "Qatif", "Hail", "Najran", "Yanbu", "Jubail", "Abha", "Buraidah", "Unaizah",
    "Al Khafji", "Khafji", "Dhahran", "Sakaka", "Arar", "Baha", "Al Baha", "Majmaah", "Al Kharj",
    "Kharj", "Rabigh", "Al Qunfudhah", "Qunfudhah", "Rafha", "Hafr Al-Batin", "Hafr Albatin", "Bisha",
]

# قيم الكتالوج بصيغة "<مدينة> Branche" (خطأ إدخال شائع بالشيت الحقيقي بدل "Branch") — تُستخدم
# لاستخراج المدينة كذلك إذا تطابقت القيمة بالتصنيف، حتى لو ما وجدنا اسم المدينة صريحًا بالنص.
_BRANCH_DETAILS_TO_CITY = {
    "Riyadh Branche": "Riyadh", "Jeddah Branche": "Jeddah", "Khobar Branche": "Khobar",
    "Khamis Mushait Branche": "Khamis Mushait", "Qassim Branche": "Qassim", "Ahsa Branche": "Ahsa",
    "Medina Branche": "Medina", "Taif Branche": "Taif", "Mecca Branche": "Mecca",
    "Jizan Branche": "Jizan", "Tabuk Branche": "Tabuk", "Qatif Branche": "Qatif",
    "Branch Dammam": "Dammam",
}

# أنماط محافظة (تتطابق فقط على "customer/caller/client <اسم>" قبل فعل مباشر) لتقليل خطر
# استخراج اسم الموظف/الوكيل بالخطأ بدل اسم العميل الفعلي.
_NAME_VERBS = (
    r"requested|purchased|is|was|contacted|wants|needs|asked|expressed|inquired|"
    r"mentioned|confirmed|informed|stated|called|reported|complained"
)
# ملاحظة: كلمات customer/caller/client/his/her/provided بأول الجملة غالبًا تبدأ بحرف كبير
# ("Customer Yassin requested...") — لذا لازم تطابق الحالتين (كبيرة/صغيرة) صريحًا بدل الاعتماد
# على re.IGNORECASE (الذي سيجعل حرف الاسم الكبير [A-Z] غير مُلزم أيضًا، فيفتح الباب لمطابقات خاطئة).
_NAME_PATTERNS = [
    # "customer/caller/client [,] <Name> [,] <verb>" — الفاصلة اختيارية على الجهتين لتغطية صياغة
    # "The customer, Abdullah Al-Muharib, inquired..." بجانب "Customer Amer requested..." المباشرة.
    re.compile(rf"\b(?:[Cc]ustomer|[Cc]aller|[Cc]lient)\s*,?\s+([A-Z][a-zA-Z]+(?:[\s\-][A-Z][a-zA-Z]+){{0,2}})\s*,?\s+(?:{_NAME_VERBS})"),
    re.compile(r"\b[Cc]aller\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+from"),
    re.compile(r"\b(?:[Hh]is|[Hh]er)\s+name\s*\(([A-Z][a-zA-Z]+)\)"),
    re.compile(r"\b[Pp]rovided\s+(?:only\s+)?his\s+name\s*\(?([A-Z][a-zA-Z]+)\)?"),
]


def _singularize(word: str) -> str:
    """تطبيع بسيط للجمع الإنجليزي (branch/branches, recliner/recliners...) لتقليل الفوت بسبب فرق
    المفرد/الجمع فقط بين نص الملخص وقيمة الكتالوج — تقريبي عمدًا، لا قواعد لغوية كاملة."""
    if word == "branche":
        return "branch"  # خطأ إدخال شائع بقائمة Details الحقيقية ("Branche" بدل "Branch")
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokenize(text: str) -> set:
    return {_singularize(w.lower()) for w in _WORD_RE.findall(text)}


def classify_details(summary: str, details_catalog: list[str]) -> str:
    """
    يختار أقرب قيمة من details_catalog: تطابق تام للعبارة كـ substring يُفضَّل دومًا؛ وإلا يُشترط
    ظهور كل كلمات القيمة (بغض النظر عن ترتيبها) ضمن نص الملخص — مطابقة محافظة لتقليل الأخطاء.
    يرجع "Other" إذا لم تنطبق أي قيمة.
    """
    if not summary:
        return ""

    summary_lower = summary.lower()
    summary_words = _tokenize(summary)

    best_value = None
    best_score = 0

    for value in details_catalog:
        value_lower = value.lower()
        # حد أدنى لطول القيمة لتفادي قيم تافهة/أخطاء إدخال بالشيت الحقيقي (مثل "f" أو "P" بالقائمة
        # الحقيقية) تتطابق عشوائيًا مع أي نص — مطابقة بحدود كلمة (\b) وليس substring خام.
        if len(value_lower) < 3:
            continue
        if re.search(r"\b" + re.escape(value_lower) + r"\b", summary_lower):
            score = 1000 + len(value_lower)  # تطابق حرفي كامل -> أولوية قصوى
        else:
            value_words = {w for w in _tokenize(value) if len(w) >= 3}
            if not value_words or not value_words.issubset(summary_words):
                continue
            score = sum(len(w) for w in value_words)

        if score > best_score:
            best_score = score
            best_value = value

    return best_value or _DETAILS_OTHER


def extract_customer_name(summary: str) -> str:
    for pattern in _NAME_PATTERNS:
        m = pattern.search(summary)
        if m:
            return m.group(1).strip()
    return ""


def extract_city(summary: str) -> str:
    for city in _KNOWN_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", summary, re.IGNORECASE):
            return city
    return ""


def extract_call_fields_rule_based(
    records: list[MaqsamCallRecord],
    details_catalog: list[str],
    on_progress=None,
) -> dict:
    """نفس شكل إرجاع extract_call_fields بـ call_extraction.py (Claude) تمامًا، بدون أي استدعاء API."""
    log = on_progress or print
    results = {}
    processed = 0

    for r in records:
        if not r.call_summary.strip():
            continue
        details = classify_details(r.call_summary, details_catalog)
        city = extract_city(r.call_summary)
        if not city:
            city = _BRANCH_DETAILS_TO_CITY.get(details, "")
        results[r.call_id] = {
            "customer_name": extract_customer_name(r.call_summary),
            "city": city,
            "details": details,
            "details_suggested": "",
        }
        processed += 1

    log(f"استخراج مجاني (بدون AI) اكتمل: {processed} مكالمة فيها ملخص تمت معالجتها بمطابقة الكلمات المفتاحية.")
    return results

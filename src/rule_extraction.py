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
    """تطبيع بسيط للجمع الإنجليزي (branch/branches, recliner/recliners, mattress/mattresses...)
    لتقليل الفوت بسبب فرق المفرد/الجمع فقط بين نص الملخص وقيمة الكتالوج — تقريبي عمدًا، لا
    قواعد لغوية كاملة."""
    if word == "branche":
        return "branch"  # خطأ إدخال شائع بقائمة Details الحقيقية ("Branche" بدل "Branch")
    # جمع ينتهي بـ "-es" بعد s/ch/sh/x (mattresses -> mattress, branches -> branch, boxes -> box)
    if word.endswith(("sses", "ches", "shes", "xes")):
        return word[:-2]
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokenize(text: str) -> set:
    return {_singularize(w.lower()) for w in _WORD_RE.findall(text)}


# قاعدة عمل خاصة (طلب المستخدم): إذا المتصل هو من يعرض خدمات على الشركة (تسويق/إدارة سوشيال
# ميديا/إعلانات...) وليس عميل يسأل عن منتج، يُصنَّف "Advertisement" مباشرة — أولوية فوق أي
# تصنيف عام آخر، حتى لو ما وُجدت كلمة "Advertisement" حرفيًا بالنص.
_VENDOR_PITCH_SIGNALS = [
    "marketing management", "social media management", "offer marketing",
    "offering marketing", "marketing services", "advertising services",
    "advertising agency", "marketing agency", "digital marketing",
    "offer advertising", "offering advertising", "offer to advertise",
    "offering to advertise", "wants to offer", "offered to provide services",
    "proposed a partnership", "proposed a collaboration", "collaboration proposal",
    "partnership proposal", "offer their services", "offering their services",
    "offer our services", "offering our services", "seo services",
    "promote your", "promotion services", "sponsorship", "cold call",
]


def is_vendor_service_pitch(summary: str) -> bool:
    text_lower = summary.lower()
    return any(signal in text_lower for signal in _VENDOR_PITCH_SIGNALS)


# قاعدة عمل خاصة (طلب المستخدم، القائمة النهائية): job/jobs/توظيف/سيرة ذاتية تُصنَّف "Job Email"
# مباشرة دائمًا — أولوية فوق أي تصنيف آخر، وممنوع تُكتب القيمة الحرفية "job" نهائيًا (موجودة
# بالقائمة المنسدلة الحقيقية كقيمة منفصلة خاطئة، يجب تفاديها دومًا لصالح "Job Email").
_JOB_APPLICATION_SIGNALS = ["job", "jobs", "توظيف", "سيرة ذاتية"]


def is_job_application_inquiry(summary: str) -> bool:
    text_lower = summary.lower()
    return any(signal in text_lower for signal in _JOB_APPLICATION_SIGNALS)


# قاعدة عمل خاصة (طلب المستخدم): مكالمة فيها إشارة لشكوى/تهديد بشكوى لوزارة التجارة (أو جهة
# حماية المستهلك) تُعلَّم بعلم خاص — تظهر بقائمة "تحتاج مراجعة" وتُلوَّن صفها بالأحمر بملف
# الإخراج، بغض النظر عن تصنيف Details، لأنها حالة حساسة تحتاج انتباه فوري من الموظفة.
_COMMERCE_COMPLAINT_SIGNALS = [
    "ministry of commerce", "commerce ministry", "consumer protection",
    "file a complaint with the ministry", "report to the ministry",
    "threatened to file a complaint", "threatened to report",
    "threatened to complain", "escalate to the ministry",
    "ministry of commerce and investment", "consumer protection authority",
    "threatened legal action", "legal action against the company",
]


def is_commerce_complaint(summary: str) -> bool:
    text_lower = summary.lower()
    return any(signal in text_lower for signal in _COMMERCE_COMPLAINT_SIGNALS)


# قاعدة عمل خاصة (طلب المستخدم): استفسار عام عن "مراتب/مرتبة" بدون تحديد نوع/موديل معيّن
# (مثل Getha، Eclipse، Kluft...) يُصنَّف افتراضيًا "Medical Mattresses price" بدل Other — هذا
# fallback فقط يُطبَّق لو ما طابق أي قيمة أدق بالقائمة أولًا.
_GENERIC_MATTRESS_FALLBACK = "Medical Mattresses price"


def _mentions_mattress(summary_words: set) -> bool:
    return "mattress" in summary_words


def _words_appear_near(summary_lower: str, words: set, window: int = 40) -> bool:
    """يتحقق إن كل كلمات القيمة تظهر قريبة من بعض بالنص (وليس مجرد متناثرة بأي مكان) — يمنع
    مثلًا 'Job Email' من الانطباق لمجرد ظهور 'job' و'email' بسياقين منفصلين تمامًا بنفس الملخص."""
    positions = []
    for w in words:
        idx = summary_lower.find(w)
        if idx == -1:
            return False
        positions.append(idx)
    return (max(positions) - min(positions)) <= window


def classify_details(summary: str, details_catalog: list[str]) -> str:
    """
    يختار أقرب قيمة من details_catalog: تطابق تام للعبارة كـ substring يُفضَّل دومًا؛ وإلا يُشترط
    ظهور كل كلمات القيمة قريبة من بعض (نافذة 40 حرف) ضمن نص الملخص — مطابقة محافظة لتقليل
    الأخطاء (مثل "Job Email" لا تنطبق لمجرد وجود "job" و"email" بسياقين منفصلين بنفس النص).
    يرجع "Other" إذا لم تنطبق أي قيمة (مع fallback عام لاستفسارات المراتب — انظر أسفله).
    """
    if not summary:
        return ""

    if is_vendor_service_pitch(summary) and "Advertisement" in details_catalog:
        return "Advertisement"

    summary_lower = summary.lower()
    summary_words = _tokenize(summary)

    best_value = None
    best_score = (0, 0)  # (عدد الكلمات المميزة بالقيمة, طول الحروف) — الأكثر تحديدًا يفوز أولًا

    for value in details_catalog:
        value_lower = value.lower()
        # حد أدنى لطول القيمة لتفادي قيم تافهة/أخطاء إدخال بالشيت الحقيقي (مثل "f" أو "P" بالقائمة
        # الحقيقية) تتطابق عشوائيًا مع أي نص — مطابقة بحدود كلمة (\b) وليس substring خام.
        if len(value_lower) < 3:
            continue
        if re.search(r"\b" + re.escape(value_lower) + r"\b", summary_lower):
            # عدد الكلمات المميزة بالقيمة نفسها — يضمن إن "Job Email" (كلمتين) تتفوق على "job"
            # (كلمة وحدة) حتى لو الاثنتين انطابقتا، بدل بونص ثابت كان يرجّح القيم القصيرة دومًا.
            score = (max(len(_tokenize(value)), 1), len(value_lower))
        else:
            value_words = {w for w in _tokenize(value) if len(w) >= 3}
            if not value_words or not value_words.issubset(summary_words):
                continue
            if len(value_words) > 1 and not _words_appear_near(summary_lower, value_words):
                continue
            score = (len(value_words), sum(len(w) for w in value_words))

        if score > best_score:
            best_score = score
            best_value = value

    if best_value is None and _mentions_mattress(summary_words) and _GENERIC_MATTRESS_FALLBACK in details_catalog:
        return _GENERIC_MATTRESS_FALLBACK

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
            "flag_commerce_complaint": is_commerce_complaint(r.call_summary),
        }
        processed += 1

    log(f"استخراج مجاني (بدون AI) اكتمل: {processed} مكالمة فيها ملخص تمت معالجتها بمطابقة الكلمات المفتاحية.")
    return results

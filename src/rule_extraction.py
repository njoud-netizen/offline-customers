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


# محرك تصنيف عام مدفوع بالكامل من config.yaml (call_import.keyword_classifiers) — طلب صريح:
# أي تصنيف جديد يُضاف بالملف يشتغل بدون أي تعديل كود. استبدل الدوال المتخصصة القديمة
# (is_vendor_service_pitch/is_job_application_inquiry) اللي كانت بقوائم Python ثابتة هنا.
def classify_by_keywords(customer_text: str, classifiers: dict) -> "str | None":
    """يرجع اسم أول تصنيف (حسب ترتيب ظهور مفاتيح classifiers) إحدى كلماته المفتاحية ظهرت
    بـcustomer_text (نص العميل فقط — بعد استبعاد كلام الموظف عبر extract_customer_text أدناه)،
    أو None لو ما طابق أي تصنيف."""
    if not customer_text or not classifiers:
        return None
    text_lower = customer_text.lower()
    for target, keywords in classifiers.items():
        for kw in keywords:
            if str(kw).lower() in text_lower:
                return target
    return None


# جمل منسوبة للموظف/الوكيل (لا للعميل) تُستبعد من نص التصنيف قبل أي مطابقة كلمات مفتاحية —
# طلب صريح: "التصنيف حسب طلب العميل فقط، مو كلام الموظف". تقسيم تقريبي عملي بالجملة (لا تحليل
# نحوي حقيقي): أي جملة تحتوي إحدى عبارات agent_signals تُحذف بالكامل من النص المرسَل للمصنّفات.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?؟؛])\s+|\n+")


def extract_customer_text(summary: str, agent_signals: list) -> str:
    """يرجع نص الملخص بعد حذف الجمل المنسوبة للموظف/الوكيل فقط. لو انحذفت كل الجمل (مطابقة
    واسعة بالغلط) يرجع الملخص الأصلي كاملًا بدل نص فاضي يفسد التصنيف بالكامل."""
    if not summary or not agent_signals:
        return summary
    sentences = _SENTENCE_SPLIT_RE.split(summary)
    kept = [
        sent for sent in sentences
        if not any(str(sig).lower() in sent.lower() for sig in agent_signals)
    ]
    return " ".join(kept).strip() if kept else summary


def is_no_customer_request(summary: str, signals: list) -> bool:
    """طلب صريح: لو الملخص يقول إن العميل ما رد/ما طلب شي/انقطعت المكالمة، تبقى خانة Details
    فاضية دائمًا (الملاحظة تبقى تعرض الملخص الفعلي كما هو — هذا الفحص لا يغيّرها)."""
    if not summary or not signals:
        return False
    text_lower = summary.lower()
    return any(str(sig).lower() in text_lower for sig in signals)


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


# قاعدة عمل خاصة (طلب المستخدم، الملفات الجديدة فقط — بدون أي تعديل على صفوف قديمة): استفسار
# عن موظف — ثلاث حالات بالأولوية: (1) فرع مذكور وموجود بالكتالوج الحي -> اسم الفرع نفسه حرفيًا
# (مو "Employee"). (2) فرع مذكور وغير موجود بالكتالوج -> "Branches". (3) بدون ذكر أي فرع ->
# "Employee" كما هي بالقائمة. أسماء الفروع قد تُذكر بالعربي بالملخص (مثال: "الياسمين" = فرع
# الرياض) — _BRANCH_CITY_ALIASES تربطها باسم المدينة الإنجليزي المطابق لاسم الفرع بالكتالوج.
_EMPLOYEE_SIGNALS = ["employee", "staff member", "staff", "موظف"]

_BRANCH_CITY_ALIASES = {
    "الرياض": "riyadh", "الياسمين": "riyadh", "اليا سمين": "riyadh",
    "جدة": "jeddah", "جده": "jeddah",
    "الخبر": "khobar",
    "خميس مشيط": "khamis mushait", "خميس": "khamis mushait",
    "القصيم": "qassim", "بريدة": "qassim", "بريده": "qassim",
    "الأحساء": "ahsa", "الاحساء": "ahsa", "الهفوف": "ahsa",
    "المدينة المنورة": "medina", "المدينة": "medina",
    "الطائف": "taif",
    "مكة المكرمة": "mecca", "مكة": "mecca",
    "جازان": "jizan", "جيزان": "jizan",
    "تبوك": "tabuk",
    "القطيف": "qatif",
    "الدمام": "dammam",
    # صيغ إنجليزية بديلة شائعة تختلف عن تسمية الكتالوج نفسه
    "makkah": "mecca", "al khobar": "khobar", "madinah": "medina",
    "al madinah": "medina", "jazan": "jizan", "al ahsa": "ahsa", "al-ahsa": "ahsa",
}

_BRANCH_CATALOG_PATTERN = re.compile(r"^(.+?)\s+branche?s?$|^branche?s?\s+(.+)$", re.IGNORECASE)
_BRANCH_WORD_RE = re.compile(r"\bbranch(?:es)?\b", re.IGNORECASE)


def is_employee_inquiry(summary: str) -> bool:
    text_lower = summary.lower()
    return any(signal in text_lower for signal in _EMPLOYEE_SIGNALS)


def _branch_catalog_by_city(details_catalog: list[str]) -> dict:
    """{اسم المدينة (lower): قيمة الكتالوج الحرفية} لكل قيمة بصيغة '<مدينة> Branche' أو
    'Branch <مدينة>' — تُبنى ديناميكيًا من الكتالوج الفعلي المُمرَّر (حي من الشيت)، بدون أي
    قائمة مدن مكتوبة يدويًا هنا."""
    result = {}
    for entry in details_catalog:
        m = _BRANCH_CATALOG_PATTERN.match(entry.strip())
        if not m:
            continue
        city = (m.group(1) or m.group(2) or "").strip().lower()
        if city:
            result[city] = entry
    return result


def resolve_employee_details(summary: str, details_catalog: list[str]) -> "str | None":
    """يرجع None لو المكالمة مو عن موظف أصلًا (classify_details العادي يكمل كالمعتاد). غير
    كذا يرجع دائمًا نص (قد يكون فاضي "") — أبدًا None — حسب القاعدة: فرع معروف وبالكتالوج ->
    اسمه الحرفي؛ فرع مذكور (معروف أو لأ) لكن مو بالكتالوج -> "Branches"؛ بدون أي ذكر فرع ->
    "" (خانة فاضية — "Employee" ممنوعة نهائيًا حتى لو موجودة بالقائمة، نفس service/website/job)."""
    if not is_employee_inquiry(summary):
        return None

    branch_by_city = _branch_catalog_by_city(details_catalog)
    summary_lower = summary.lower()

    mentioned_city = None
    for city in branch_by_city:
        if re.search(r"\b" + re.escape(city) + r"\b", summary_lower):
            mentioned_city = city
            break
    if mentioned_city is None:
        for term, city in _BRANCH_CITY_ALIASES.items():
            if term in summary_lower:
                mentioned_city = city
                break

    if mentioned_city is not None:
        return branch_by_city.get(mentioned_city) or ("Branches" if "Branches" in details_catalog else "")

    # فرع مذكور لكن مدينته غير معروفة/غير موجودة بالكتالوج (مثال: "Dubai branch") — ما نقدر
    # نحدد اسمه الحرفي، لكنه لسه "فرع مذكور" حسب القاعدة -> "Branches" العامة.
    if _BRANCH_WORD_RE.search(summary) or "فرع" in summary:
        return "Branches" if "Branches" in details_catalog else ""

    # موظف بدون أي ذكر فرع -> خانة فاضية (مو "Employee" — ممنوعة نهائيًا). الصف بالملف النهائي
    # يحصل سطر "استفسار العميل: ..." بعمود Remark تلقائيًا (نفس آلية أي Details فاضية بالملف).
    return ""


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
    keyword_classifiers: "dict | None" = None,
    agent_signals: "list | None" = None,
    no_request_signals: "list | None" = None,
    on_progress=None,
) -> dict:
    """نفس شكل إرجاع extract_call_fields بـ call_extraction.py (Claude) تمامًا، بدون أي استدعاء API.

    تسلسل التصنيف بالأولوية (الأعلى يفوز، ويحمل details_priority=True فيمنع قاعدة الموظف
    بـinbound_pipeline.py من استبدال نتيجته لاحقًا):
    1) is_no_customer_request -> Details فاضية (العميل ما طلب شي أصلًا).
    2) classify_by_keywords (Advertisement/Job Email/Working Hours/أي تصنيف جديد بـconfig.yaml)
       — على نص العميل فقط (بعد استبعاد جمل الموظف/الوكيل عبر extract_customer_text).
    3) classify_details العام (مطابقة الكتالوج الكاملة) — fallback، على نص العميل فقط كذلك.
    """
    log = on_progress or print
    results = {}
    processed = 0
    keyword_classifiers = keyword_classifiers or {}
    agent_signals = agent_signals or []
    no_request_signals = no_request_signals or []

    for r in records:
        summary = r.call_summary
        if not summary.strip():
            continue

        customer_text = extract_customer_text(summary, agent_signals)

        details_priority = False
        if is_no_customer_request(summary, no_request_signals):
            details = ""
            details_priority = True
        else:
            kw_target = classify_by_keywords(customer_text, keyword_classifiers)
            if kw_target and kw_target in details_catalog:
                details = kw_target
                details_priority = True
            else:
                details = classify_details(customer_text, details_catalog)

        city = extract_city(summary)
        if not city:
            city = _BRANCH_DETAILS_TO_CITY.get(details, "")
        results[r.call_id] = {
            "customer_name": extract_customer_name(summary),
            "city": city,
            "details": details,
            "details_suggested": "",
            "details_priority": details_priority,
            "flag_commerce_complaint": is_commerce_complaint(summary),
        }
        processed += 1

    log(f"استخراج مجاني (بدون AI) اكتمل: {processed} مكالمة فيها ملخص تمت معالجتها بمطابقة الكلمات المفتاحية.")
    return results

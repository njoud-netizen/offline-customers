"""منطق التصنيف الأساسي: هل العميل 'أوفلاين' أم لا، مع تسجيل سبب الاستبعاد بدقة.

الرقم يُعتبر "أوفلاين" فقط إذا تحققت كل الشروط التالية معًا:
  1. الرقم موجود (بعد التطبيع) بأحد تبويبات Sara/Raghad/Njoud بشيت المزروع.
  2. عمود Details بشيت المزروع ليس ضمن: Support Email, Job Email, Maintenance, Delivery Time, order.
  3. عمود "Inbound calls/out bound calls" = Inbound فقط (وليس Outbound).
  4. تاريخ سجل التواصل نفسه ليس نفس تاريخ اليوم الحالي (تاريخ تشغيل النظام) — سجل تواصل بنفس يوم
     التشغيل يُعتبر لم يُعتمد بعد (ربما لم يكتمل تسجيله)، فلا يُستخدم كأساس للمطابقة؛ إن كان هو
     السبب الوحيد لعدم التصنيف يُعاد فحص الرقم بالتشغيلة القادمة دون اعتباره مكررًا (skip_dedup).
  5. تاريخ التواصل بالشيت ضمن نفس شهر وسنة تاريخ الفاتورة (لا يرجع لأي شهر سابق).
  6. تاريخ الفاتورة نفسه ليس نفس تاريخ اليوم الحالي (تاريخ تشغيل النظام) — فواتير اليوم لم
     تتم معالجتها بعد، وتُعاد محاولتها بالتشغيلة القادمة دون اعتبارها مكررة (skip_dedup).
  7. الكود المستخرج من عمود Show Room بالفاتورة لا يحتوي على "E-Commerce"/"Ecommerce".
  8. الكود المستخرج من Show Room (عبر brand_dictionary) يطابق قيمة company بشيت المزروع.

مصدر البراند هو عمود Show Room حصرًا (بحث نصي عن أي invoice_codes ضمن brand_dictionary،
مطابقة substring غير حساسة لحالة الأحرف) — وليس عمودي Brand/Brand Name، لأنهما قد لا يعكسان
براند المتجر الفعلي (مثال: متجر تابع لمجموعة BQ لكنه يبيع براند La-Z-Boy).
"""
import re
from collections import defaultdict
from dataclasses import dataclass

from .invoices import InvoiceRecord
from .sheets import ContactRecord


def normalize_text_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def build_exclusion_set(exclusion_details: list[str]) -> set:
    return {normalize_text_key(d) for d in exclusion_details}


def build_contacts_index(contacts: list[ContactRecord]) -> dict:
    index = defaultdict(list)
    for c in contacts:
        if c.phone.valid:
            index[c.phone.normalized].append(c)
    return index


def is_outbound(value: str) -> bool:
    """يطابق 'Outbound' أو 'out bound' (بأي تفاوت بالمسافات/حالة الأحرف)."""
    return re.sub(r"\s+", "", (value or "").strip().lower()) == "outbound"


def is_ecommerce_show_room(show_room_text: str) -> bool:
    text = (show_room_text or "").lower()
    return "e-commerce" in text or "ecommerce" in text


def resolve_canonical_brand_from_show_room(show_room_text: str, brand_dictionary: dict, on_progress=None) -> "str | None":
    """
    يبحث داخل نص Show Room كاملًا (وليس فقط بادئته) عن أي invoice_codes معرّفة بـ brand_dictionary،
    مطابقة substring غير حساسة لحالة الأحرف. عند تعدد الأكواد المتطابقة، الأولوية للأطول تطابقًا
    (مثال: 'BQ Khobar Lazboy01 Store' يحوي 'BQ' و'LAZ' معًا — يُختار 'LAZ' لأنه أطول وأكثر تحديدًا).
    عند تعادل الطول بين براندات مختلفة، تُسجَّل حالة غامضة عبر on_progress ولا يُفترض أي افتراضي.
    """
    text_lower = (show_room_text or "").strip().lower()
    if not text_lower:
        return None

    matches = []  # (code_len, code, canonical_brand)
    for canonical, cfg in brand_dictionary.items():
        for code in cfg.get("invoice_codes", []):
            code_clean = str(code).strip()
            if code_clean and code_clean.lower() in text_lower:
                matches.append((len(code_clean), code_clean, canonical))

    if not matches:
        return None

    max_len = max(m[0] for m in matches)
    best = [m for m in matches if m[0] == max_len]
    distinct_brands = sorted({m[2] for m in best})

    if len(distinct_brands) > 1:
        log = on_progress or print
        log(
            f"[تحذير] استخراج البراند غامض من Show Room='{show_room_text}': عدة براندات متطابقة "
            f"بنفس أطول تطابق ({max_len} حرف): {distinct_brands}. لم يُصنَّف تلقائيًا — يحتاج مراجعة "
            f"يدوية (راجع brand_dictionary بملف config.yaml)."
        )
        return None

    return distinct_brands[0]


def company_matches_brand(company_value: str, canonical_brand: "str | None", brand_dictionary: dict) -> bool:
    if not canonical_brand or canonical_brand not in brand_dictionary:
        return False
    aliases = brand_dictionary[canonical_brand].get("sheet_aliases", [])
    norm_company = normalize_text_key(company_value)
    if not norm_company:
        return False
    return any(normalize_text_key(a) == norm_company for a in aliases)


@dataclass
class ClassificationResult:
    status: str  # "offline" | "excluded" | "invalid"
    reason: str
    matched_contact: "ContactRecord | None" = None
    canonical_brand: "str | None" = None
    # True فقط لحالة "فاتورة بتاريخ اليوم" — لا يجب تسجيلها بقاعدة SQLite لأنها لم تُعالج فعليًا بعد
    skip_dedup: bool = False


def classify_invoice_record(
    record: InvoiceRecord,
    contacts_index: dict,
    brand_dictionary: dict,
    exclusion_set: set,
    today,
    on_progress=None,
) -> ClassificationResult:
    # استبعاد فواتير القيمة السالبة (مرتجعات/إشعارات دائن) فورًا — قبل أي شرط آخر، لأنها ليست عملية بيع فعلية
    if record.amount < 0:
        return ClassificationResult(status="excluded", reason="قيمة الفاتورة سالبة (مرتجع)")

    # الشرط 5: فواتير بتاريخ اليوم لم تتم معالجتها بعد — استبعاد فوري بدون تسجيل بقاعدة الـ dedup
    if record.invoice_date is not None and record.invoice_date.date() == today:
        return ClassificationResult(
            status="excluded",
            reason="فاتورة بتاريخ اليوم — لم تتم معالجتها بعد",
            skip_dedup=True,
        )

    if not record.phone.valid:
        return ClassificationResult(status="invalid", reason=record.phone.reason)

    # الشرط 1: الرقم موجود بأحد التبويبات الثلاثة
    contacts = contacts_index.get(record.phone.normalized, [])
    if not contacts:
        return ClassificationResult(
            status="excluded",
            reason="الرقم غير موجود ضمن أي من تبويبات Sara/Raghad/Njoud بشيت المزروع",
        )

    # الشرط 6: استبعاد فروع/مبيعات E-Commerce بالكامل، بغض النظر عن باقي الشروط
    if is_ecommerce_show_room(record.show_room_raw):
        return ClassificationResult(status="excluded", reason="بيع عبر E-Commerce")

    # الشرط 7 (استخراج): البراند من Show Room — إن تعذّر تحديده لا يُفترض أي قيمة افتراضية
    canonical_brand = resolve_canonical_brand_from_show_room(record.show_room_raw, brand_dictionary, on_progress)
    if canonical_brand is None:
        return ClassificationResult(
            status="excluded",
            reason=f"لم يُحدد البراند من Show Room ('{record.show_room_raw}')",
        )

    failure_reasons = []
    has_pending_today_contact = False

    for contact in contacts:
        # الشرط 2: استبعاد Details المحظورة
        details_norm = normalize_text_key(contact.details)
        if details_norm in exclusion_set:
            failure_reasons.append(
                f"[تواصل {contact.agent}#{contact.row_index}] مستبعد لأن Details = '{contact.details}'"
            )
            continue

        # الشرط 3: استبعاد الاتصالات الصادرة (Outbound) — أوفلاين فقط لو العميل هو من تواصل معنا
        if is_outbound(contact.inbound_outbound):
            failure_reasons.append(
                f"[تواصل {contact.agent}#{contact.row_index}] مستبعد لأن نوع الاتصال Outbound "
                f"وليس Inbound (القيمة: '{contact.inbound_outbound}')"
            )
            continue

        if contact.date is None:
            failure_reasons.append(
                f"[تواصل {contact.agent}#{contact.row_index}] تاريخ التواصل غير قابل للقراءة: '{contact.date_raw}'"
            )
            continue

        # الشرط 4: سجل تواصل بنفس تاريخ اليوم الحالي لا يُعتمد بعد كأساس للمطابقة
        if contact.date.date() == today:
            has_pending_today_contact = True
            failure_reasons.append(
                f"[تواصل {contact.agent}#{contact.row_index}] تاريخ التواصل ({contact.date.strftime('%Y-%m-%d')}) "
                f"هو نفس تاريخ تشغيل النظام اليوم — لم يُعتمد بعد، سيُعاد فحصه بالتشغيلة القادمة"
            )
            continue

        if record.invoice_date is None:
            failure_reasons.append(
                f"[تواصل {contact.agent}#{contact.row_index}] تاريخ الفاتورة غير قابل للقراءة: '{record.invoice_date_raw}'"
            )
            continue

        # الشرط 5: نفس شهر وسنة تاريخ الفاتورة فقط
        same_month_year = (
            contact.date.year == record.invoice_date.year
            and contact.date.month == record.invoice_date.month
        )
        if not same_month_year:
            failure_reasons.append(
                f"[تواصل {contact.agent}#{contact.row_index}] شهر/سنة التواصل ({contact.date.strftime('%Y-%m')}) "
                f"لا يطابق شهر/سنة الفاتورة ({record.invoice_date.strftime('%Y-%m')})"
            )
            continue

        # الشرط 8 (مطابقة): company بشيت المزروع يطابق البراند المستخرج من Show Room
        if not company_matches_brand(contact.company, canonical_brand, brand_dictionary):
            failure_reasons.append(
                f"[تواصل {contact.agent}#{contact.row_index}] company='{contact.company}' لا يطابق براند "
                f"Show Room ({canonical_brand})"
            )
            continue

        return ClassificationResult(
            status="offline", reason="تحققت جميع الشروط",
            matched_contact=contact, canonical_brand=canonical_brand,
        )

    return ClassificationResult(
        status="excluded", reason=" | ".join(failure_reasons),
        canonical_brand=canonical_brand, skip_dedup=has_pending_today_contact,
    )

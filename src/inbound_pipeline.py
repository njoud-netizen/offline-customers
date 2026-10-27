"""خط أنابيب صفحة Inbound Call: تصدير Maqsam -> صفوف بنفس أعمدة شيت المزروع بالضبط + قائمة
تحتاج مراجعة يدوية. مسار مستقل تمامًا عن pipeline.py/dedup.sqlite3 الحالي — لا تداخل بينهما.

القاعدة الأساسية (طلب صريح): يُكتب فقط قيمة موجودة حرفيًا بالقائمة المنسدلة الحقيقية لكل عمود
(company/Region/Details) — القوائم تُقرأ حية من الشيت نفسه (sheet_dropdowns.py)، لا تُكتب يدويًا
بالكود. أي قيمة مستخرجة لا تطابق القائمة (ولا أي ALIAS معروف) تبقى فاضية، ولا تُخترع أبدًا."""
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .call_extraction import extract_call_fields
from .config import credentials_path, resolve_path
from .maqsam_import import extract_inbound_records, load_maqsam_export
from .report import write_inbound_report
from .rule_extraction import (
    extract_call_fields_rule_based,
    extract_customer_text,
    resolve_employee_details,
)
from .sheet_dropdowns import fetch_dropdown_lists
from .sheet_values import match_literal
from .translate_helper import translate_to_arabic_status

_DETAILS_OTHER = "Other"
# قيم ممنوعة نهائيًا بعمود Details (طلب صريح) — تُستبعد من كتالوج المطابقة بالكامل، فلا يمكن
# لأي مصنّف (rules أو Claude) اختيارها أصلًا، بغض النظر عن وجودها بالقائمة المنسدلة الحقيقية.
_DETAILS_BANNED = {"service", "website", "job", "employee"}


class _TranslateThrottle:
    """فاصل تكيّفي بين طلبات ترجمة متتالية — MyMemory المجاني 5 طلبات/ثانية بس (مؤكَّد فعليًا
    بفحص حي: "you are allowed to make 5 requests per second"). يبدأ بفاصل أساسي، ويزيده
    تلقائيًا (بحد أقصى) كل ما فشلت ترجمة — فوق إعادة المحاولة الداخلية بـtranslate_helper.py."""

    def __init__(self, base_delay: float = 0.3, max_delay: float = 2.0):
        self.delay = base_delay
        self.max_delay = max_delay
        self.last_at = 0.0

    def translate(self, text: str) -> tuple[str, bool]:
        elapsed = time.perf_counter() - self.last_at
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        result, ok = translate_to_arabic_status(text)
        self.last_at = time.perf_counter()
        if not ok:
            self.delay = min(self.delay * 1.5, self.max_delay)
        return result, ok


@dataclass
class InboundImportResult:
    rows: list = field(default_factory=list)          # بنفس أعمدة google_sheets.columns بالضبط
    needs_review: list = field(default_factory=list)  # {"call_id","number","reason","call_summary"}
    summary: dict = field(default_factory=dict)
    output_path: "str | None" = None
    highlight_flags: list = field(default_factory=list)  # بنفس طول/ترتيب rows — True = شكوى محتملة
    unmatched_values: list = field(default_factory=list)  # {"column","raw_value"} — خانات تُركت فاضية لعدم تطابق القائمة
    translation_failures: int = 0  # عدد مرات فشلت فيها ترجمة ملخص المكالمة فعليًا (تشخيص)
    agent_ai_missing: bool = False  # True = قيمة "AI" غير موجودة بقائمة Agent المنسدلة الحقيقية


def _format_date(dt) -> str:
    return dt.strftime("%Y-%m-%d") if dt else ""


def _resolve_output_dir(cfg: dict) -> str:
    return str(resolve_path(cfg, cfg["paths"]["output_dir"]))


def _clean_details_catalog(raw_values: list[str]) -> list[str]:
    """كتالوج نظيف (بدون تكرار/مسافات زائدة/قيم ممنوعة) يُستخدم لمطابقة نص الملخص — القيمة
    النهائية المكتوبة تُطابَق لاحقًا ضد القائمة الحية الخام لاستعادة أي تنسيق فعلي بالشيت."""
    seen = set()
    cleaned = []
    for v in raw_values:
        clean = str(v).strip()
        key = clean.lower()
        if not clean or key in _DETAILS_BANNED or key in seen:
            continue
        seen.add(key)
        cleaned.append(clean)
    return cleaned


def run_inbound_import(file, cfg: dict, on_progress: Optional[Callable[[str], None]] = None) -> InboundImportResult:
    def progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    google_cfg = cfg["google_sheets"]
    columns = google_cfg["columns"]
    brand_dictionary = cfg["brand_dictionary"]
    call_import_cfg = cfg["call_import"]
    city_aliases = cfg.get("city_aliases", {})
    company_aliases = {name: c.get("sheet_aliases", []) for name, c in brand_dictionary.items()}
    keyword_classifiers = call_import_cfg.get("keyword_classifiers", {})
    agent_signals = call_import_cfg.get("agent_sentence_signals", [])
    no_request_signals = call_import_cfg.get("no_customer_request_signals", [])

    progress("قراءة القوائم المنسدلة الحية من شيت المزروع (company/Region/Details/Agent)...")
    try:
        live_lists = fetch_dropdown_lists(
            credentials_path=str(credentials_path(cfg)),
            spreadsheet_id=google_cfg["spreadsheet_id"],
            tabs_cfg=google_cfg["tabs"],
            column_names=["company", "Region", "Details", "Agent"],
        )
    except Exception as e:
        progress(f"[تحذير] تعذّر قراءة القوائم المنسدلة الحية ({e}) — سيُستخدم احتياطي محدود "
                 f"(company فقط من config.yaml، و Region/Details/Agent فاضية غالبًا).")
        live_lists = {}

    company_values = live_lists.get("company") or list(brand_dictionary.keys())
    region_values = live_lists.get("Region") or []
    details_values_raw = live_lists.get("Details") or call_import_cfg.get("details_catalog", [])
    details_catalog_clean = _clean_details_catalog(details_values_raw)
    agent_values = live_lists.get("Agent") or []
    # طلب صريح: كل صف جديد يكتب "AI" بعمود Agent (الكتابة الحرفية كما بالقائمة المنسدلة
    # الحقيقية، مطابقة بدون حساسية لحالة الأحرف/المسافات via match_literal) — بدل اسم الموظفة
    # الفعلي من ملف Maqsam. لو "AI" غير موجودة بالقائمة أصلًا، تبقى الخانة فاضية لكل الصفوف
    # وتُطلَق تحذير صريح (agent_ai_missing أدناه) بدل اختراع القيمة.
    agent_ai_literal = match_literal("AI", agent_values) if agent_values else ""
    agent_ai_missing = not agent_ai_literal
    if agent_ai_missing:
        progress("[تحذير] قيمة AI غير موجودة في قائمة Agent — عمود Agent سيبقى فاضيًا لكل الصفوف.")

    progress("قراءة ملف تصدير Maqsam...")
    t0 = time.perf_counter()
    df = load_maqsam_export(file)
    records = extract_inbound_records(df, brand_dictionary)
    progress(f"تم العثور على {len(records)} مكالمة Inbound من أصل {len(df)} صف بالملف. "
             f"(استغرق {time.perf_counter() - t0:.2f} ثانية)")

    extraction_mode = call_import_cfg.get("extraction_mode", "rules")
    t0 = time.perf_counter()
    if extraction_mode == "claude":
        extracted = extract_call_fields(
            records,
            details_catalog=details_catalog_clean,
            model=call_import_cfg["anthropic_model"],
            batch_size=call_import_cfg["batch_size"],
            on_progress=progress,
        )
    else:
        extracted = extract_call_fields_rule_based(
            records,
            details_catalog=details_catalog_clean,
            keyword_classifiers=keyword_classifiers,
            agent_signals=agent_signals,
            no_request_signals=no_request_signals,
            on_progress=progress,
        )
    progress(f"انتهى الاستخراج. (استغرق {time.perf_counter() - t0:.2f} ثانية)")

    rows = []
    needs_review = []
    resolved_companies = set()
    rows_with_details = 0
    highlight_flags = []  # نفس طول rows — True = شكوى محتملة لوزارة التجارة -> يُلوَّن أحمر بالإكسل
    complaint_count = 0
    unmatched_values = []  # {"column","raw_value"} لكل خانة تُركت فاضية لعدم وجودها بالقائمة الحقيقية
    translation_failures = 0  # فشل فعلي بترجمة Remark الخاص بملف الإخراج (العدّاد القديم — بلا تغيير)
    translate_throttle = _TranslateThrottle()
    summary_translated_ok = 0    # عدّادات طلب صريح: لوحة Inbound Call (ترجمة الملخص الكامل لكل صف)
    summary_translated_failed = 0
    summary_empty_count = 0

    for r in records:
        fields = extracted.get(r.call_id, {})
        name = fields.get("customer_name", "")
        city_raw = fields.get("city", "")
        details_raw = fields.get("details", "")
        details_priority = bool(fields.get("details_priority", False))
        is_complaint = bool(fields.get("flag_commerce_complaint", False))
        if is_complaint:
            complaint_count += 1

        # قاعدة الموظف (أولوية فوق التصنيف العام فقط — لا تتجاوز أي تصنيف ذو أولوية مُقرَّر
        # مسبقًا بـextract_call_fields_rule_based مثل Advertisement/Job Email/Working Hours أو
        # خانة فاضية إجبارية بسبب is_no_customer_request): فرع مذكور وبالكتالوج -> اسم الفرع،
        # فرع مذكور ومو بالكتالوج -> "Branches"، بدون فرع مذكور -> خانة فاضية. None = المكالمة
        # أصلًا مو عن موظف، فيكمل التصنيف العادي بلا تغيير. نفس تصفية نص العميل (بدون كلام
        # الموظف/الوكيل) تُستخدم هنا كذلك — طلب صريح: التصنيف حسب طلب العميل فقط.
        if r.call_summary and not details_priority:
            customer_text = extract_customer_text(r.call_summary, agent_signals)
            employee_override = resolve_employee_details(customer_text, details_catalog_clean)
            if employee_override is not None:
                details_raw = employee_override

        # مطابقة نهائية ضد القائمة المنسدلة الحية — القيمة المكتوبة حرفيًا كما بالشيت الحقيقي
        # (حتى لو فيها مسافات زائدة)، وإلا فاضية. "Other" = لم يطابق المصنّف أي قيمة من الأساس.
        details_literal = ""
        if details_raw and details_raw != _DETAILS_OTHER:
            details_literal = match_literal(details_raw, details_values_raw)
            if not details_literal:
                unmatched_values.append({"column": "Details", "raw_value": details_raw})
        if details_literal:
            rows_with_details += 1

        company_literal = ""
        if r.canonical_company:
            company_literal = match_literal(r.canonical_company, company_values, aliases=company_aliases)
            if company_literal:
                resolved_companies.add(company_literal)
            else:
                unmatched_values.append({"column": "company", "raw_value": r.canonical_company})

        region_literal = ""
        if city_raw:
            region_literal = match_literal(city_raw, region_values, aliases=city_aliases)
            if not region_literal:
                unmatched_values.append({"column": "Region", "raw_value": city_raw})

        # review_reasons: نصوص عربية جاهزة لعمود Remark بملف الإخراج/الشيت وneeds_review —
        # بلا أي تغيير عن السلوك السابق (ملف الإخراج/الشيت خارج نطاق هذي الجولة تمامًا). طلب
        # صريح: حذفت فحص صلاحية رقم الجوال نهائيًا من هذي القائمة — كل رقم دق يُعتبر صحيح،
        # ما يصير "يحتاج مراجعة" بسببه بعد اليوم (منطق normalize_phone نفسه بـphone.py لم
        # يتغيّر — يُستخدم لأغراض أخرى كتنسيق الرقم — فقط توقفنا عن استخدام نتيجته هنا).
        review_reasons = []
        if is_complaint:
            review_reasons.append("⚠️ شكوى محتملة لوزارة التجارة — تحتاج انتباه فوري")
        if r.brand_raw and not r.canonical_company:
            review_reasons.append(f"براند غير محلول من maqsam_line_aliases: '{r.brand_raw}'")

        number_value = r.customer_phone.normalized or r.customer_phone.raw

        remark = ""
        arabic_summary = ""
        if review_reasons:
            remark = "يحتاج مراجعة يدوية: " + " | ".join(review_reasons)
            if r.call_summary:
                # ملخص المكالمة نفسه مترجم للعربي — حتى ما تحتاج ترجع لماقسام وتسمع المكالمة
                # بنفسك عشان تعرف وش قال العميل. ترجمة مجانية (best-effort)؛ لو فشلت الترجمة
                # فعليًا يرجع النص الإنجليزي الأصلي بدل ما يوقف المعالجة — سلوك ملف الإخراج هذا
                # لم يتغيّر إطلاقًا (نفس الاقتطاع 450/400 حرف كالسابق).
                arabic_summary, _ok = translate_throttle.translate(r.call_summary[:450])
                if not _ok:
                    translation_failures += 1
                remark += f" || ملخص المكالمة: {arabic_summary[:400]}"
        elif not details_literal and r.call_summary:
            # طلب صريح: خانة Details الفاضية (ما له تصنيف بالقائمة) يرافقها سؤال العميل باختصار
            # بعمود الملاحظات المجاور بملف الإخراج (سلوك هذا الفرع لم يتغيّر إطلاقًا كذلك).
            short_note, _ok = translate_throttle.translate(r.call_summary[:200])
            if not _ok:
                translation_failures += 1
            remark = f"استفسار العميل: {short_note[:150]}"

        # ==== لوحة Inbound Call فقط (عمود "الملاحظات" بالداشبورد) — طلب صريح منفصل تمامًا عن
        # منطق ملف الإخراج أعلاه: كل مكالمة فيها ملخص (بدون استثناء — بغض النظر عن تصنيف
        # Details أو وجود شكوى/براند غير محلول) تاخذ ترجمة كاملة لملخصها الأصلي الكامل (بدون
        # اقتطاع)؛ الفاضي فقط لو الملخص نفسه فاضي بملف Maqsam. لا جملة بديلة عامة إطلاقًا —
        # عند فشل الترجمة فعليًا يُعرض النص الإنجليزي الكامل (القرار يُتّخذ بـinbound_table.py
        # حسب لغة الواجهة الحالية وقت العرض، لا هنا). ====
        if r.call_summary:
            summary_full_ar, full_ok = translate_throttle.translate(r.call_summary)
            if full_ok:
                summary_translated_ok += 1
            else:
                summary_translated_failed += 1
        else:
            summary_full_ar, full_ok = "", True
            summary_empty_count += 1

        remark_meta = {
            "has_summary": bool(r.call_summary),
            "summary_en_full": r.call_summary or "",
            "summary_ar_full": summary_full_ar,
            "translation_ok": full_ok,
            "needs_attention": is_complaint or bool(r.brand_raw and not r.canonical_company),
        }

        row = {
            "Region": region_literal,
            "Name": name,
            "Number": number_value,
            "Inbound calls/out bound calls": "Inbound",
            "Call Status": r.state,
            "WhatsApp&Calls": "",
            "Social Media": "",
            "Subject": "",
            "Details": details_literal,
            "Status": "",
            "Date": _format_date(r.created),
            "company": company_literal,
            "Satisfied/or not": "",
            "How did you hear about us": "",
            "Remark": remark,
            "Agent": agent_ai_literal,
            # Show Room بالشيت الحقيقي قائمة فروع دقيقة جدًا (مثال: "BQ Riyadh - Rowdah") لا علاقة
            # لها بالمدينة العامة — لا منطق استخراج حاليًا يحدد الفرع الدقيق، فتبقى فاضية دومًا
            # بدل كتابة مدينة عامة فيها (كانت تُكتب هنا سابقًا بالغلط، وهذا سبب المثلث الأحمر).
            "Show Room": "",
        }
        output_row = {col: row.get(col, "") for col in columns}  # ترتيب حرفي مضمون لملف الإخراج
        # _remark_meta ليست بـcolumns فلا تصل لملف الإكسل إطلاقًا (write_inbound_report يبني
        # الـDataFrame بـcolumns=columns صراحة فيتجاهل أي مفتاح زائد) — موجودة فقط لعرض لوحة
        # Inbound Call (result.rows) لبناء عمود الملاحظات حسب لغة الواجهة الحالية.
        output_row["_remark_meta"] = remark_meta
        rows.append(output_row)
        highlight_flags.append(is_complaint)

        if review_reasons:
            needs_review.append({
                "call_id": r.call_id,
                "number": number_value,
                "reason": " | ".join(review_reasons),
                "call_summary": arabic_summary[:400] if arabic_summary else r.call_summary[:200],
            })

    summary = {
        "إجمالي صفوف الملف": len(df),
        "مكالمات Inbound": len(records),
        "مكالمات فيها Call Summary": sum(1 for r in records if r.call_summary.strip()),
        "صفوف تم استخراج Details لها": rows_with_details,
        "براندات تم حلّها": len(resolved_companies),
        "صفوف تحتاج مراجعة يدوية": len(needs_review),
        "شكاوى وزارة التجارة المحتملة": complaint_count,
        "خانات لم تطابق أي قائمة منسدلة (تُركت فاضية)": len(unmatched_values),
        "محاولات ترجمة فشلت فعليًا (رجع النص الإنجليزي الأصلي)": translation_failures,
        "ترجمة ملاحظات الداشبورد — نجحت": summary_translated_ok,
        "ترجمة ملاحظات الداشبورد — فشلت": summary_translated_failed,
        "ترجمة ملاحظات الداشبورد — ملخص فاضي": summary_empty_count,
    }
    # طلب صريح: طباعة واضحة بالترمنال (progress تطبع لأي on_progress مُمرَّر، بما فيها
    # print() البسيطة بالاستخدام المباشر/CLI) لعدد صفوف ترجمة الملخص الكامل اللي نجحت/فشلت/فاضية.
    progress(
        f"ترجمة ملاحظات لوحة Inbound Call: {summary_translated_ok} نجحت، "
        f"{summary_translated_failed} فشلت (يُعرض النص الإنجليزي الأصلي بدلها)، "
        f"{summary_empty_count} صف بلا ملخص أصلًا (Call Summary فاضي)."
    )

    progress("كتابة ملف الإخراج (Excel)...")
    output_path = write_inbound_report(_resolve_output_dir(cfg), rows, columns, highlight_flags)

    return InboundImportResult(
        rows=rows, needs_review=needs_review, summary=summary,
        output_path=output_path, highlight_flags=highlight_flags,
        unmatched_values=unmatched_values, translation_failures=translation_failures,
        agent_ai_missing=agent_ai_missing,
    )

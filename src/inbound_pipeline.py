"""خط أنابيب صفحة Inbound Call: تصدير Maqsam -> صفوف بنفس أعمدة شيت المزروع بالضبط + قائمة
تحتاج مراجعة يدوية. مسار مستقل تمامًا عن pipeline.py/dedup.sqlite3 الحالي — لا تداخل بينهما."""
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .call_extraction import extract_call_fields
from .config import resolve_path
from .maqsam_import import extract_inbound_records, load_maqsam_export
from .report import write_inbound_report
from .rule_extraction import extract_call_fields_rule_based
from .translate_helper import translate_to_arabic

_DETAILS_OTHER = "Other"


@dataclass
class InboundImportResult:
    rows: list = field(default_factory=list)          # بنفس أعمدة google_sheets.columns بالضبط
    needs_review: list = field(default_factory=list)  # {"call_id","number","reason","call_summary"}
    summary: dict = field(default_factory=dict)
    output_path: "str | None" = None
    highlight_flags: list = field(default_factory=list)  # بنفس طول/ترتيب rows — True = شكوى محتملة


def _format_date(dt) -> str:
    return dt.strftime("%Y-%m-%d") if dt else ""


def _resolve_output_dir(cfg: dict) -> str:
    return str(resolve_path(cfg, cfg["paths"]["output_dir"]))


def run_inbound_import(file, cfg: dict, on_progress: Optional[Callable[[str], None]] = None) -> InboundImportResult:
    def progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    columns = cfg["google_sheets"]["columns"]
    brand_dictionary = cfg["brand_dictionary"]
    call_import_cfg = cfg["call_import"]

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
            details_catalog=call_import_cfg["details_catalog"],
            model=call_import_cfg["anthropic_model"],
            batch_size=call_import_cfg["batch_size"],
            on_progress=progress,
        )
    else:
        extracted = extract_call_fields_rule_based(
            records,
            details_catalog=call_import_cfg["details_catalog"],
            on_progress=progress,
        )
    progress(f"انتهى الاستخراج. (استغرق {time.perf_counter() - t0:.2f} ثانية)")

    rows = []
    needs_review = []
    resolved_companies = set()
    rows_with_details = 0
    highlight_flags = []  # نفس طول rows — True = شكوى محتملة لوزارة التجارة -> يُلوَّن أحمر بالإكسل
    complaint_count = 0

    for r in records:
        fields = extracted.get(r.call_id, {})
        name = fields.get("customer_name", "")
        city = fields.get("city", "")
        details = fields.get("details", "")
        is_complaint = bool(fields.get("flag_commerce_complaint", False))
        if details:
            rows_with_details += 1
        if is_complaint:
            complaint_count += 1

        review_reasons = []
        if is_complaint:
            review_reasons.append("⚠️ شكوى محتملة لوزارة التجارة — تحتاج انتباه فوري")
        if not r.customer_phone.valid:
            review_reasons.append(f"رقم غير صالح ({r.customer_phone.reason})")
        if r.brand_raw and not r.canonical_company:
            review_reasons.append(f"براند غير محلول من maqsam_line_aliases: '{r.brand_raw}'")
        if details == _DETAILS_OTHER:
            suggested = fields.get("details_suggested", "")
            msg = "Details لم يطابق القائمة الحالية"
            if suggested:
                msg += f" (مقترح: {suggested})"
            review_reasons.append(msg)

        if r.canonical_company:
            resolved_companies.add(r.canonical_company)

        number_value = r.customer_phone.normalized or r.customer_phone.raw

        remark = ""
        arabic_summary = ""
        if review_reasons:
            remark = "يحتاج مراجعة يدوية: " + " | ".join(review_reasons)
            if r.call_summary:
                # ملخص المكالمة نفسه مترجم للعربي — حتى ما تحتاج ترجع لماقسام وتسمع المكالمة
                # بنفسك عشان تعرف وش قال العميل. ترجمة مجانية (best-effort)؛ لو فشلت الترجمة
                # يرجع النص الإنجليزي الأصلي بدل ما يوقف المعالجة.
                arabic_summary = translate_to_arabic(r.call_summary[:450])
                remark += f" || ملخص المكالمة: {arabic_summary[:400]}"

        row = {
            "Name": name,
            "Number": number_value,
            "Inbound calls/out bound calls": "Inbound",
            "Call Status": r.state,
            "WhatsApp&Calls": "",
            "Social Media": "",
            "Subject": "",
            "Details": details,
            "Status": "",
            "Date": _format_date(r.created),
            "company": r.canonical_company or "",
            "Satisfied/or not": "",
            "How did you hear about us": "",
            "Remark": remark,
            "Agent": r.agent,
            "Show Room": city,
        }
        rows.append({col: row.get(col, "") for col in columns})  # ترتيب حرفي مضمون لملف الإخراج
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
    }

    progress("كتابة ملف الإخراج (Excel)...")
    output_path = write_inbound_report(_resolve_output_dir(cfg), rows, columns, highlight_flags)

    return InboundImportResult(
        rows=rows, needs_review=needs_review, summary=summary,
        output_path=output_path, highlight_flags=highlight_flags,
    )

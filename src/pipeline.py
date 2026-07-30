"""
مسار المعالجة الكامل المشترك بين CLI وواجهة Streamlit.
لا يوجد هنا أي تغيير بمنطق التطبيع/الاستبعاد/منع التكرار — فقط استخراج نفس خطوات
cli.py الأصلية إلى دالة واحدة قابلة لإعادة الاستخدام من أكثر من واجهة.
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

from .config import credentials_path, resolve_path
from .db import DedupStore
from .invoices import extract_invoice_records, load_invoice_file
from .matcher import build_contacts_index, build_exclusion_set, classify_invoice_record
from .report import write_reports
from .sheets import GoogleSheetsConnectionError, get_contacts_cached


@dataclass
class PipelineResult:
    offline_rows: list = field(default_factory=list)
    excluded_rows: list = field(default_factory=list)
    invalid_rows: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    output_paths: dict = field(default_factory=dict)


def run_pipeline(
    invoice_file,
    cfg: dict,
    on_progress: Optional[Callable[[str], None]] = None,
    ignore_dedup: bool = False,
) -> PipelineResult:
    """
    ignore_dedup=True هو "وضع المعاينة": يعالج كل السجلات بغض النظر عن قاعدة dedup،
    ولا يقرأ منها ولا يكتب إليها إطلاقًا (لا فتح اتصال أصلًا) — لا يؤثر على db/dedup.sqlite3 بأي شكل.
    """
    def progress(msg: str):
        if on_progress:
            on_progress(msg)

    timings: dict = {}
    invoice_columns_cfg = cfg["invoice_columns"]

    progress("قراءة ملف الفواتير...")
    t0 = time.perf_counter()
    df = load_invoice_file(invoice_file, invoice_columns_cfg, on_progress=progress)
    records, parse_errors = extract_invoice_records(df, invoice_columns_cfg)
    timings["قراءة وتحليل ملف الفواتير"] = time.perf_counter() - t0
    progress(f"تم استخراج {len(records)} صف صالح للتفكيك، و {len(parse_errors)} صف فشل تفكيكه. "
             f"(استغرق {timings['قراءة وتحليل ملف الفواتير']:.2f} ثانية)")

    store = None
    new_records = []
    skipped_already_processed = 0
    t0 = time.perf_counter()
    if ignore_dedup:
        new_records = records
        progress("وضع المعاينة مفعّل: تجاهل قاعدة dedup بالكامل — كل السجلات تُعامل كجديدة، "
                 "ولن تُسجَّل أي نتيجة بقاعدة dedup.sqlite3.")
    else:
        db_path = resolve_path(cfg, cfg["paths"]["db_path"])
        store = DedupStore(str(db_path))
        for r in records:
            phone_key = r.phone.normalized if r.phone.valid else f"RAW:{r.phone_raw}"
            if store.is_processed(phone_key, r.sales_order_id):
                skipped_already_processed += 1
                continue
            new_records.append(r)
    timings["فحص قاعدة dedup"] = time.perf_counter() - t0
    progress(f"فحص القاعدة المحلية للتكرار: {skipped_already_processed} صف مُعالج مسبقًا تم تجاهله، "
             f"{len(new_records)} صف جديد فعليًا. (استغرق {timings['فحص قاعدة dedup']:.2f} ثانية)")

    creds_path = credentials_path(cfg)
    if not creds_path.exists():
        if store:
            store.close()
        raise GoogleSheetsConnectionError(
            f"ملف بيانات اعتماد Google غير موجود بالمسار: {creds_path}\n"
            "ضع ملف Service Account JSON بهذا المسار، أو عيّن متغير البيئة GOOGLE_APPLICATION_CREDENTIALS."
        )

    progress("الاتصال بـ Google Sheets وجلب بيانات Sara/Raghad/Njoud (أو استخدام الكاش إن وُجد)...")
    t0 = time.perf_counter()
    try:
        contacts = get_contacts_cached(
            str(creds_path),
            cfg["google_sheets"]["spreadsheet_id"],
            cfg["google_sheets"]["tabs"],
            cfg["google_sheets"]["columns"],
            on_progress=progress,
        )
    except GoogleSheetsConnectionError:
        if store:
            store.close()
        raise
    except Exception as e:
        if store:
            store.close()
        raise GoogleSheetsConnectionError(
            f"فشل الاتصال بـ Google Sheets أو قراءة التبويبات: {e}\n"
            "تحقق من: مشاركة الشيت مع بريد Service Account بصلاحية Viewer، صحة spreadsheet_id بملف config.yaml، "
            "واتصال الإنترنت."
        ) from e
    timings["الاتصال بـ Google Sheets وجلب سجلات التواصل"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    contacts_index = build_contacts_index(contacts)
    timings["بناء فهرس الأرقام (contacts_index)"] = time.perf_counter() - t0
    progress(f"تم تحميل {len(contacts)} سجل تواصل من التبويبات الثلاثة. "
             f"(استغرق {timings['الاتصال بـ Google Sheets وجلب سجلات التواصل']:.2f} ثانية)")

    exclusion_set = build_exclusion_set(cfg["exclusion_details"])
    brand_dictionary = cfg["brand_dictionary"]

    offline_rows, excluded_rows, invalid_rows = [], [], []

    for pe in parse_errors:
        invalid_rows.append({
            "المصدر": "ملف الفواتير",
            "الرقم الأصلي": pe["customer_info_raw"],
            "اسم العميل/المتصل": "",
            "سبب عدم الصلاحية": pe["reason"],
            "Sales Order ID": "",
        })

    contacts_without_number = 0
    for c in contacts:
        if not c.phone.valid:
            if c.phone.reason == "قيمة فارغة":
                contacts_without_number += 1
                continue
            invalid_rows.append({
                "المصدر": f"شيت المزروع - {c.agent}",
                "الرقم الأصلي": c.number_raw,
                "اسم العميل/المتصل": c.name,
                "سبب عدم الصلاحية": c.phone.reason,
                "Sales Order ID": "",
            })

    phone_invoice_counts = defaultdict(int)
    for r in records:
        if r.phone.valid:
            phone_invoice_counts[r.phone.normalized] += 1

    today = date.today()
    progress("تطبيق شروط المطابقة على كل صف جديد...")
    t0 = time.perf_counter()
    for r in new_records:
        result = classify_invoice_record(r, contacts_index, brand_dictionary, exclusion_set, today, on_progress=progress)
        phone_key = r.phone.normalized if r.phone.valid else f"RAW:{r.phone_raw}"

        if result.status == "invalid":
            invalid_rows.append({
                "المصدر": "ملف الفواتير",
                "الرقم الأصلي": r.phone_raw,
                "اسم العميل/المتصل": r.customer_name,
                "سبب عدم الصلاحية": result.reason,
                "Sales Order ID": r.sales_order_id,
            })
        elif result.status == "excluded":
            excluded_rows.append({
                "رقم الجوال": r.phone.normalized or r.phone_raw,
                "اسم العميل": r.customer_name,
                "Brand": result.canonical_brand or r.brand_name_raw or r.brand_code or "",
                "Sales Order ID": r.sales_order_id,
                "تاريخ الفاتورة": r.invoice_date.strftime("%Y-%m-%d") if r.invoice_date else r.invoice_date_raw,
                "سبب الاستبعاد الدقيق": result.reason,
            })
        else:
            mc = result.matched_contact
            offline_rows.append({
                "رقم الجوال": r.phone.normalized,
                "اسم العميل": r.customer_name,
                "Brand": result.canonical_brand or r.brand_name_raw or r.brand_code or "",
                "تاريخ الفاتورة": r.invoice_date.strftime("%Y-%m-%d") if r.invoice_date else r.invoice_date_raw,
                "تاريخ التواصل بشيت المزروع": mc.date.strftime("%Y-%m-%d") if mc.date else mc.date_raw,
                "سبب التواصل (Details)": mc.details,
                "اسم الموظفة (Agent)": mc.agent,
                "Sales Order ID": r.sales_order_id,
                "عدد فواتير هذا الرقم": phone_invoice_counts.get(r.phone.normalized, 1),
                "الحالة": "أوفلاين",
                "Amount": r.amount,
            })

        if store is not None and not result.skip_dedup:
            store.mark_processed(phone_key, r.sales_order_id)

    timings["حلقة المطابقة (classify_invoice_record لكل صف)"] = time.perf_counter() - t0
    progress(f"انتهت المطابقة على {len(new_records)} صف. "
             f"(استغرقت {timings['حلقة المطابقة (classify_invoice_record لكل صف)']:.2f} ثانية)")

    if store:
        store.commit()
        store.close()

    exclusion_reason_breakdown = defaultdict(int)
    for row in excluded_rows:
        first_reason = row["سبب الاستبعاد الدقيق"].split(" | ")[0]
        if "فاتورة بتاريخ اليوم" in first_reason:
            key = "فاتورة بتاريخ اليوم (لم تُعالج بعد)"
        elif "نفس تاريخ تشغيل النظام اليوم" in first_reason:
            key = "تواصل بتاريخ اليوم (لم يُعتمد بعد)"
        elif "E-Commerce" in first_reason:
            key = "بيع عبر E-Commerce"
        elif "غير موجود ضمن" in first_reason:
            key = "الرقم غير موجود بشيت المزروع"
        elif "Details" in first_reason:
            key = "مستبعد بسبب Details"
        elif "Outbound" in first_reason:
            key = "مستبعد بسبب Outbound (اتصال صادر)"
        elif "شهر/سنة" in first_reason:
            key = "عدم تطابق الشهر/السنة"
        elif "لم يُحدد البراند" in first_reason:
            key = "لم يُحدد البراند من Show Room"
        elif "قيمة الفاتورة سالبة" in first_reason:
            key = "قيمة الفاتورة سالبة (مرتجع)"
        elif "company=" in first_reason or "براند" in first_reason:
            key = "عدم تطابق البراند/company"
        else:
            key = "أسباب أخرى"
        exclusion_reason_breakdown[key] += 1

    summary = {
        "إجمالي صفوف ملف الفواتير": len(df),
        "إجمالي أرقام صالحة بالفاتورة (بعد التطبيع)": sum(1 for r in records if r.phone.valid),
        "تم تجاهلها لأنها معالجة مسبقًا (dedup)": skipped_already_processed,
        "صفوف جديدة فعليًا بهذا التشغيل": len(new_records),
        "مصنّفة كأوفلاين": len(offline_rows),
        "مستبعدة (إجمالي)": len(excluded_rows),
        "أرقام غير صالحة/مشبوهة (فاتورة + شيت)": len(invalid_rows),
        "سجلات تواصل بشيت المزروع بدون رقم جوال مسجَّل أصلًا (معلومة فقط)": contacts_without_number,
    }
    for k, v in exclusion_reason_breakdown.items():
        summary[f"  -> استبعاد: {k}"] = v

    # توحيد التكرار بالنتيجة النهائية: صف واحد لكل رقم جوال — أسطر الفاتورة الإضافية لنفس الرقم
    # (نفس الأوردر بعدة أصناف، أو أوردرات مختلفة بنفس التشغيلة) تُدمج بجمع Amount فقط، وباقي
    # أعمدة الصف تبقى كما بأول ظهور لهذا الرقم. هذا التوحيد بعد حساب الملخص أعلاه عمدًا: مؤشر
    # "مصنّفة كأوفلاين" بالملخص يبقى يعكس عدد أسطر الفواتير المؤهلة كما كان دائمًا.
    consolidated_offline_rows = []
    phone_to_row_index = {}
    for row in offline_rows:
        phone = row["رقم الجوال"]
        if phone in phone_to_row_index:
            consolidated_offline_rows[phone_to_row_index[phone]]["Amount"] += row["Amount"]
        else:
            phone_to_row_index[phone] = len(consolidated_offline_rows)
            consolidated_offline_rows.append(dict(row))
    offline_rows = consolidated_offline_rows

    progress("كتابة ملفات المخرجات...")
    t0 = time.perf_counter()
    output_paths = write_reports(str(resolve_path(cfg, cfg["paths"]["output_dir"])),
                                  offline_rows, excluded_rows, invalid_rows, summary)
    timings["كتابة ملفات المخرجات (Excel)"] = time.perf_counter() - t0

    total_time = sum(timings.values())
    progress("\n=== قياس الزمن لكل مرحلة (بالثواني) ===")
    for phase, seconds in timings.items():
        pct = (seconds / total_time * 100) if total_time else 0
        progress(f"  {phase}: {seconds:.2f}s ({pct:.0f}%)")
    progress(f"  الإجمالي: {total_time:.2f}s")

    return PipelineResult(
        offline_rows=offline_rows,
        excluded_rows=excluded_rows,
        invalid_rows=invalid_rows,
        summary=summary,
        output_paths=output_paths,
    )

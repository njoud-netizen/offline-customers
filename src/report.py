"""بناء ملفات المخرجات الأربعة: أوفلاين، استبعادات، أرقام غير صالحة، ملخص."""
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.styles import PatternFill

_RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")


def write_reports(output_dir: str, offline_rows: list[dict], excluded_rows: list[dict],
                   invalid_rows: list[dict], summary: dict) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    paths = {}

    offline_path = out / f"offline_customers_{stamp}.xlsx"
    df_offline = pd.DataFrame(offline_rows, columns=[
        "رقم الجوال", "اسم العميل", "Brand", "تاريخ الفاتورة", "تاريخ التواصل بشيت المزروع",
        "سبب التواصل (Details)", "اسم الموظفة (Agent)", "Sales Order ID", "عدد فواتير هذا الرقم", "الحالة", "Amount",
    ])
    df_offline.to_excel(offline_path, index=False)
    paths["offline"] = str(offline_path)

    excluded_path = out / f"exclusions_{stamp}.xlsx"
    df_excluded = pd.DataFrame(excluded_rows, columns=[
        "رقم الجوال", "اسم العميل", "Brand", "Sales Order ID", "تاريخ الفاتورة", "سبب الاستبعاد الدقيق",
    ])
    df_excluded.to_excel(excluded_path, index=False)
    paths["excluded"] = str(excluded_path)

    invalid_path = out / f"invalid_numbers_{stamp}.xlsx"
    df_invalid = pd.DataFrame(invalid_rows, columns=[
        "المصدر", "الرقم الأصلي", "اسم العميل/المتصل", "سبب عدم الصلاحية", "Sales Order ID",
    ])
    df_invalid.to_excel(invalid_path, index=False)
    paths["invalid"] = str(invalid_path)

    summary_path = out / f"summary_{stamp}.xlsx"
    summary_rows = [{"المؤشر": k, "القيمة": v} for k, v in summary.items()]
    pd.DataFrame(summary_rows).to_excel(summary_path, index=False)
    paths["summary"] = str(summary_path)

    return paths


def write_inbound_report(output_dir: str, rows: list[dict], columns: list[str],
                          highlight_flags: "list[bool] | None" = None) -> str:
    """ملف صفحة Inbound Call: نفس أعمدة google_sheets.columns بالضبط وبنفس الترتيب — جاهز للصق
    المباشر بشيت المزروع، بدون أي عمود زائد. highlight_flags (بنفس طول rows): يلوّن الصف كاملًا
    بالأحمر لتنبيه فوري (مثلًا: مكالمة فيها شكوى محتملة لوزارة التجارة)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = out / f"inbound_calls_{stamp}.xlsx"
    df = pd.DataFrame(rows, columns=columns)
    df.to_excel(path, index=False)

    if highlight_flags and any(highlight_flags):
        from openpyxl import load_workbook
        wb = load_workbook(path)
        ws = wb.active
        for i, flagged in enumerate(highlight_flags):
            if not flagged:
                continue
            excel_row = i + 2  # +1 لصف العناوين، +1 لأن openpyxl يبدأ من 1 لا 0
            for col_idx in range(1, len(columns) + 1):
                ws.cell(row=excel_row, column=col_idx).fill = _RED_FILL
        wb.save(path)

    return str(path)

"""بناء ملفات المخرجات الأربعة: أوفلاين، استبعادات، أرقام غير صالحة، ملخص."""
from datetime import datetime
from pathlib import Path

import pandas as pd


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


def write_inbound_report(output_dir: str, rows: list[dict], columns: list[str]) -> str:
    """ملف صفحة Inbound Call: نفس أعمدة google_sheets.columns بالضبط وبنفس الترتيب — جاهز للصق
    المباشر بشيت المزروع، بدون أي عمود زائد."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = out / f"inbound_calls_{stamp}.xlsx"
    pd.DataFrame(rows, columns=columns).to_excel(path, index=False)
    return str(path)

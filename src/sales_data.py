"""
قراءة تبويب "Sales Data" المنفصل تمامًا عن Sara/Raghad/Njoud — يُستخدم فقط بلوحة التحكم
(Dashboard) لعرض إحصائيات تاريخية جاهزة (عمود Online/Offline موجود مسبقًا بالتبويب نفسه).
لا علاقة له بمنطق مطابقة الفواتير الأساسي بـ matcher.py.
"""
import re
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from .amounts import parse_amount_value
from .matcher import normalize_text_key

_DATE_RE_CLEAN = re.compile(r"\s+")


@dataclass
class SalesDataRow:
    client_name: str
    date: "datetime | None"
    company_name_raw: str
    is_offline: bool
    bill_num: str
    amount: str
    status: str


def _parse_sales_date(raw: str) -> "datetime | None":
    """يفكك صيغة التاريخ الفعلية بتبويب Sales Data، مثل '01 / Jan /2021'."""
    if not raw or not raw.strip():
        return None
    cleaned = _DATE_RE_CLEAN.sub("", raw.strip())  # "01/Jan/2021"
    for fmt in ("%d/%b/%Y", "%d/%B/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(raw, dayfirst=True).to_pydatetime()
    except Exception:
        return None


def load_sales_data_rows(gc, spreadsheet_id: str, tab_name: str, gid: int) -> list[SalesDataRow]:
    sh = gc.open_by_key(spreadsheet_id)
    ws = None
    for w in sh.worksheets():
        if w.id == gid:
            ws = w
            break
    if ws is None:
        for w in sh.worksheets():
            if w.title.strip().lower() == tab_name.strip().lower():
                ws = w
                break
    if ws is None:
        raise ValueError(f"لم يتم العثور على تبويب '{tab_name}' (gid={gid}) بالشيت.")

    values = ws.get_all_values()
    if not values:
        return []
    header = [h.strip() for h in values[0]]

    def col_index(name):
        return header.index(name) if name in header else None

    idx = {
        "client_name": col_index("Client Name"),
        "date": col_index("Date"),
        "company_name": col_index("Company Name"),
        "online_offline": col_index("Online/Offline"),
        "bill_num": col_index("Bill Num"),
        "amount": col_index("Amount"),
        "status": col_index("Status"),
    }
    missing = [k for k, v in idx.items() if v is None and k in ("client_name", "date", "company_name", "online_offline")]
    if missing:
        raise ValueError(f"أعمدة مطلوبة غير موجودة بتبويب '{tab_name}': {missing}")

    def cell(row, key):
        i = idx[key]
        return row[i].strip() if i is not None and i < len(row) else ""

    rows: list[SalesDataRow] = []
    for row in values[1:]:
        online_offline = cell(row, "online_offline").strip().upper()
        if online_offline not in ("ONLINE", "OFFLINE"):
            continue  # صف فارغ/تالف — تجاهل بصمت (ليس جزءًا من نطاق هذا التقرير)
        rows.append(SalesDataRow(
            client_name=cell(row, "client_name"),
            date=_parse_sales_date(cell(row, "date")),
            company_name_raw=cell(row, "company_name"),
            is_offline=(online_offline == "OFFLINE"),
            bill_num=cell(row, "bill_num"),
            amount=cell(row, "amount"),
            status=cell(row, "status"),
        ))
    return rows


def normalize_company_name(raw_name: str, brand_dictionary: dict) -> str:
    """يوحّد اسم الشركة عبر brand_dictionary الحالي؛ يُبقي النص الخام إن لم يوجد تطابق (لا إسقاط بصمت)."""
    if not raw_name:
        return "غير محدد"
    norm_raw = normalize_text_key(raw_name)
    for canonical, cfg in brand_dictionary.items():
        for alias in cfg.get("sheet_aliases", []):
            if normalize_text_key(alias) == norm_raw:
                return canonical
    return raw_name.strip()


def rows_to_dataframe(rows: list[SalesDataRow], brand_dictionary: dict) -> pd.DataFrame:
    records = []
    for r in rows:
        records.append({
            "client_name": r.client_name,
            "date": r.date,
            "company_name": normalize_company_name(r.company_name_raw, brand_dictionary),
            "is_offline": r.is_offline,
            "bill_num": r.bill_num,
            "amount": r.amount,
            "amount_value": parse_amount_value(r.amount),
            "status": r.status,
        })
    return pd.DataFrame(records)

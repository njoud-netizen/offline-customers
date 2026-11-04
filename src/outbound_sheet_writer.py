"""الكتابة الوحيدة بشيت المزروع بالمشروع كله: إضافة صفوف جديدة بآخر التبويب عبر طلب appendCells
فقط. لا يوجد هنا أي update/delete/clear، ولا لمس لأي قائمة منسدلة (fields لا تشمل dataValidation).
تُستدعى من صفحة "اوت باوند – فيد باك" بعد ضغط زر "إضافة للشيت" فقط.

الاتصال منفصل عن get_client بـsheets.py عمدًا: ذاك يبقى قراءة فقط لبقية الصفحات، وهنا نفس حساب
الخدمة بنطاق كتابة. صلاحية التعديل الفعلية على الشيت نفسه تُمنح من مالك الشيت، لا من هذا الكود."""
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

from .config import credentials_path
from .outbound_pipeline import COL_DATE, COL_NUMBER, parse_sheet_date
from .sheets import google_secrets_info

WRITE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_SHEETS_EPOCH = date(1899, 12, 30)
_DATE_FORMAT = {"type": "DATE", "pattern": 'dd" / "mmm" /"yyyy'}  # نفس تنسيق عمود Date الفعلي
_NUMBER_FORMAT = {"type": "NUMBER", "pattern": "0"}


class OutboundWritePermissionError(Exception):
    """حساب الخدمة ليس عنده صلاحية تعديل على الشيت."""


def _cell(column: str, value: str) -> dict:
    """التنسيق يُحدَّد صراحة للرقم والتاريخ لأن الخلايا الفاضية بآخر بعض التبويبات منسّقة غلط
    (عمود Number بتنسيق تاريخ بتبويب Sara)، فالرقم كان سيظهر كتاريخ."""
    if not value:
        return {}
    if column == COL_NUMBER and value.isdigit():
        return {"userEnteredValue": {"numberValue": int(value)}, "userEnteredFormat": {"numberFormat": _NUMBER_FORMAT}}
    if column == COL_DATE:
        parsed = parse_sheet_date(value)
        if parsed:
            return {
                "userEnteredValue": {"numberValue": (parsed - _SHEETS_EPOCH).days},
                "userEnteredFormat": {"numberFormat": _DATE_FORMAT},
            }
    return {"userEnteredValue": {"stringValue": value}}  # stringValue: لا يُفسَّر أي نص كصيغة


def build_append_request(sheet_id: int, rows: list, columns: list) -> dict:
    return {
        "requests": [{
            "appendCells": {
                "sheetId": sheet_id,
                "rows": [{"values": [_cell(c, row.get(c, "")) for c in columns]} for row in rows],
                "fields": "userEnteredValue,userEnteredFormat.numberFormat",
            }
        }]
    }


def _write_client(cfg: dict) -> gspread.Client:
    secrets_info = google_secrets_info()
    if secrets_info is not None:
        creds = Credentials.from_service_account_info(secrets_info, scopes=WRITE_SCOPES)
    else:
        creds = Credentials.from_service_account_file(str(credentials_path(cfg)), scopes=WRITE_SCOPES)
    return gspread.authorize(creds)


def append_rows_to_sheet(cfg: dict, rows: list) -> int:
    if not rows:
        return 0
    google_cfg = cfg["google_sheets"]
    sh = _write_client(cfg).open_by_key(google_cfg["spreadsheet_id"])
    ws = sh.worksheet(cfg["outbound_feedback"]["target_tab"])
    try:
        sh.batch_update(build_append_request(ws.id, rows, google_cfg["columns"]))
    except gspread.exceptions.APIError as e:
        if e.code == 403:
            raise OutboundWritePermissionError(str(e)) from e
        raise
    return len(rows)

"""الاتصال بـ Google Sheets وقراءة تبويبات Sara/Raghad/Njoud اعتمادًا على gid."""
import time
from dataclasses import dataclass
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from .phone import PhoneResult, normalize_phone

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# كاش بسيط بالذاكرة (بدون Streamlit) لتفادي إعادة جلب ~150 ألف صف من Sara/Raghad/Njoud
# بكل استدعاء — يعمل لكل من CLI وStreamlit على حد سواء لأنه لا يعتمد على أي إطار عمل.
CONTACTS_CACHE_TTL_SECONDS = 300  # 5 دقائق
_contacts_cache: dict = {}  # key -> (timestamp, contacts_list)


class GoogleSheetsConnectionError(Exception):
    """خطأ اتصال/صلاحيات واضح يمكن للواجهة (CLI أو Streamlit) عرضه للمستخدم مباشرة."""
    pass


@dataclass
class ContactRecord:
    agent: str  # Sara / Raghad / Njoud
    row_index: int
    name: str
    number_raw: str
    phone: PhoneResult
    inbound_outbound: str
    call_status: str
    whatsapp_calls: str
    social_media: str
    subject: str
    details: str
    status: str
    date_raw: str
    date: "datetime | None"
    company: str
    satisfied: str
    how_heard: str
    remark: str
    show_room: str


def google_secrets_info() -> dict | None:
    """يرجع بيانات اعتماد Google من Streamlit Secrets (المفتاح gcp_service_account) إن كنا
    منشورين على Streamlit Cloud، وإلا None — عندها يُقرأ الملف الفعلي كما بالتشغيل المحلي."""
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        pass
    return None


def get_client(credentials_path: str) -> gspread.Client:
    secrets_info = google_secrets_info()
    if secrets_info is not None:
        creds = Credentials.from_service_account_info(secrets_info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(str(credentials_path), scopes=SCOPES)
    return gspread.authorize(creds)


def validate_gids(gc: gspread.Client, spreadsheet_id: str, tabs_cfg: dict) -> dict:
    """
    يتحقق فعليًا من تطابق gid المذكور بالإعداد مع worksheet.id الحقيقي.
    يرجع dict {tab_name: gspread.Worksheet} بعد التحقق، ويطبع تحذيرًا عند أي تعارض
    بدل الاعتماد الأعمى على اسم التبويب أو الرقم المذكور بالإعداد.
    """
    sh = gc.open_by_key(spreadsheet_id)
    all_worksheets = sh.worksheets()
    by_id = {ws.id: ws for ws in all_worksheets}
    by_title = {ws.title: ws for ws in all_worksheets}

    resolved = {}
    for tab_name, tab_cfg in tabs_cfg.items():
        expected_gid = int(tab_cfg["gid"])
        ws = by_id.get(expected_gid)
        if ws is None:
            ws_by_title = by_title.get(tab_name)
            if ws_by_title is None:
                raise ValueError(
                    f"لم يتم العثور على تبويب '{tab_name}' لا بالـ gid ({expected_gid}) ولا بالاسم. "
                    f"تحقق من صلاحيات الوصول للشيت أو من صحة الاسم/الـ gid بملف config.yaml."
                )
            print(
                f"[تحذير] gid المذكور بالإعداد ({expected_gid}) للتبويب '{tab_name}' غير مطابق فعليًا. "
                f"تم استخدام التبويب بالاسم بدلًا منه (gid الفعلي: {ws_by_title.id}). "
                f"يُنصح بتحديث config.yaml إلى: {ws_by_title.id}"
            )
            resolved[tab_name] = ws_by_title
        else:
            if ws.title != tab_name:
                print(
                    f"[تحذير] التبويب صاحب gid={expected_gid} اسمه الفعلي '{ws.title}' وليس '{tab_name}'. "
                    f"سيُستخدم اعتمادًا على gid كما طُلب."
                )
            resolved[tab_name] = ws
    return resolved


def _parse_sheet_date(value: str):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        import pandas as pd
        return pd.to_datetime(text, dayfirst=True).to_pydatetime()
    except Exception:
        return None


def load_contacts(resolved_worksheets: dict, expected_columns: list[str]) -> list[ContactRecord]:
    records: list[ContactRecord] = []
    for agent_name, ws in resolved_worksheets.items():
        values = ws.get_all_values()
        if not values:
            continue
        header = [h.strip() for h in values[0]]
        col_index = {name: header.index(name) for name in expected_columns if name in header}
        missing = [name for name in expected_columns if name not in header]
        if missing:
            print(f"[تحذير] تبويب '{agent_name}': أعمدة غير موجودة بالهيدر الفعلي: {missing}")

        def cell(row, name):
            i = col_index.get(name)
            return row[i].strip() if i is not None and i < len(row) else ""

        for row_idx, row in enumerate(values[1:], start=2):
            number_raw = cell(row, "Number")
            if not number_raw and not cell(row, "Name"):
                continue  # صف فارغ تمامًا
            phone_result = normalize_phone(number_raw)
            date_raw = cell(row, "Date")
            records.append(ContactRecord(
                agent=agent_name,
                row_index=row_idx,
                name=cell(row, "Name"),
                number_raw=number_raw,
                phone=phone_result,
                inbound_outbound=cell(row, "Inbound calls/out bound calls"),
                call_status=cell(row, "Call Status"),
                whatsapp_calls=cell(row, "WhatsApp&Calls"),
                social_media=cell(row, "Social Media"),
                subject=cell(row, "Subject"),
                details=cell(row, "Details"),
                status=cell(row, "Status"),
                date_raw=date_raw,
                date=_parse_sheet_date(date_raw),
                company=cell(row, "company"),
                satisfied=cell(row, "Satisfied/or not"),
                how_heard=cell(row, "How did you hear about us"),
                remark=cell(row, "Remark"),
                show_room=cell(row, "Show Room"),
            ))
    return records


def get_contacts_cached(
    credentials_path: str,
    spreadsheet_id: str,
    tabs_cfg: dict,
    expected_columns: list[str],
    on_progress=None,
    ttl_seconds: int = CONTACTS_CACHE_TTL_SECONDS,
) -> list[ContactRecord]:
    """
    يجلب سجلات Sara/Raghad/Njoud مع كاش بسيط بالذاكرة (TTL افتراضي 5 دقائق) بدل الاتصال
    بـ Google Sheets وجلب ~150 ألف صف بكل استدعاء. يعمل لأي واجهة (CLI أو Streamlit) لأنه
    لا يعتمد على st.cache_data إطلاقًا.
    """
    log = on_progress or print
    cache_key = spreadsheet_id
    cached = _contacts_cache.get(cache_key)
    now = time.time()

    if cached is not None:
        timestamp, contacts = cached
        age = now - timestamp
        if age < ttl_seconds:
            log(f"[كاش] استُخدمت بيانات شيت المزروع من الذاكرة المحلية (عمرها {age:.0f} ثانية من أصل "
                f"{ttl_seconds} ثانية صلاحية) — لم تُجلب من Google Sheets من جديد.")
            return contacts

    gc = get_client(credentials_path)
    resolved_ws = validate_gids(gc, spreadsheet_id, tabs_cfg)
    contacts = load_contacts(resolved_ws, expected_columns)
    _contacts_cache[cache_key] = (now, contacts)
    return contacts

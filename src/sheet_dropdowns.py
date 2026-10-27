"""قراءة قوائم Data Validation (Dropdown) الحية من شيت المزروع نفسه — المصدر الوحيد المسموح
لقيم company/Region/Details عند الكتابة بملف الإخراج، حسب الطلب الصريح: "لا تكتب القوائم يدويًا
بالكود". تُقرأ عبر Sheets API (spreadsheets.get مع dataValidation) من الصف الأول بعد الهيدر
بكل تبويب (Sara/Raghad/Njoud) — تُفترض كلها تتشارك نفس القوائم فعليًا؛ أول تبويب فيه قائمة
غير فاضية لعمود معيّن هو المعتمد له."""
import time

from .sheets import get_client

DROPDOWN_CACHE_TTL_SECONDS = 300  # 5 دقائق — نفس مدة كاش get_contacts_cached بـ sheets.py
_dropdown_cache: dict = {}


def _extract_dropdown_values(row_cells: list[dict], header: list[str], column_names: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for idx, name in enumerate(header):
        if name not in column_names or idx >= len(row_cells):
            continue
        dv = row_cells[idx].get("dataValidation")
        if not dv:
            continue
        condition = dv.get("condition", {})
        if condition.get("type") != "ONE_OF_LIST":
            continue  # قائمة مبنية من Range/صيغة بدل قيم مباشرة — غير مدعومة حاليًا، تُعامَل كغير موجودة
        values = [v.get("userEnteredValue", "") for v in condition.get("values", [])]
        values = [v for v in values if v]
        if values:
            result[name] = values
    return result


def fetch_dropdown_lists(
    credentials_path: str,
    spreadsheet_id: str,
    tabs_cfg: dict,
    column_names: list[str],
    ttl_seconds: int = DROPDOWN_CACHE_TTL_SECONDS,
) -> dict[str, list[str]]:
    """يرجع {اسم العمود: [قيم القائمة المنسدلة حرفيًا كما هي بالشيت]} — بدون أي تنظيف/تعديل
    على القيم نفسها (حتى المسافات الزائدة تبقى كما هي، لأن القيمة المكتوبة لاحقًا يجب أن تطابق
    هذي القوائم حرفيًا بالضبط). كاش بالذاكرة لتفادي استدعاء API بكل رفع ملف متتالي."""
    cache_key = (spreadsheet_id, tuple(sorted(column_names)))
    cached = _dropdown_cache.get(cache_key)
    now = time.time()
    if cached is not None:
        timestamp, lists = cached
        if now - timestamp < ttl_seconds:
            return lists

    gc = get_client(credentials_path)
    sh = gc.open_by_key(spreadsheet_id)
    found: dict[str, list[str]] = {}

    for tab_name in tabs_cfg:
        if set(column_names) <= set(found):
            break
        try:
            meta = sh.fetch_sheet_metadata(params={
                "ranges": [f"{tab_name}!A1:ZZ2"],
                "includeGridData": True,
                "fields": "sheets(data(rowData(values(formattedValue,dataValidation))))",
            })
            sheet_data = meta["sheets"][0]["data"][0]["rowData"]
            header = [c.get("formattedValue", "").strip() for c in sheet_data[0].get("values", [])]
            data_row = sheet_data[1]["values"] if len(sheet_data) > 1 else []
            tab_lists = _extract_dropdown_values(data_row, header, column_names)
            for name, values in tab_lists.items():
                found.setdefault(name, values)
        except Exception:
            continue  # تبويب غير متاح أو هيكل غير متوقع — جرّب التبويب التالي بدل إيقاف كل شيء

    _dropdown_cache[cache_key] = (now, found)
    return found

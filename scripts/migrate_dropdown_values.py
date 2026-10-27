"""سكربت تصحيح لمرة واحدة للصفوف الموجودة فعليًا بشيت المزروع (Sara/Raghad/Njoud) — يطبّق
نفس قواعد المطابقة المستخدمة بصفحة Inbound Call (src/inbound_pipeline.py) على الأعمدة الثلاثة
اللي فيها قوائم منسدلة: company، Region، Details.

**وضع تقرير فقط حاليًا (Dry-Run) — لا يكتب أي شيء بالشيت.** يطبع لكل عمود: كم صف بيتغيّر،
أمثلة (قبل ← بعد)، وكم خانة بتنمسح — وينتظر مراجعة/موافقة المستخدم قبل أي كتابة فعلية.

ملاحظة مهمة: بيانات الاعتماد الحالية (SCOPES بـ src/sheets.py) قراءة فقط
(spreadsheets.readonly) — تفعيل --apply فعليًا يحتاج أولًا توسيع الصلاحية لـ
https://www.googleapis.com/auth/spreadsheets (قراءة وكتابة) ومنح حساب الخدمة صلاحية Editor
(وليس Viewer فقط) على الشيت الحقيقي؛ وإلا --apply يرفض العمل برسالة خطأ واضحة.

الاستخدام:
    python -m scripts.migrate_dropdown_values            # تقرير فقط (الوضع الافتراضي والوحيد المفعَّل حاليًا)
"""
import argparse
import re
import sys
from collections import defaultdict

from src.config import credentials_path, load_config
from src.rule_extraction import is_vendor_service_pitch
from src.sheet_dropdowns import fetch_dropdown_lists
from src.sheet_values import match_literal
from src.sheets import get_client, validate_gids

_TARGET_COLUMNS = ["company", "Region", "Details"]
_DETAILS_BANNED = {"service", "website"}
_BRANCH_WORD_RE = re.compile(r"\bbranche?s?\b", re.IGNORECASE)

MAX_EXAMPLES_PER_COLUMN = 8


def _looks_like_branch_mention(value: str) -> bool:
    return bool(_BRANCH_WORD_RE.search(value))


def _correct_details(raw: str, remark: str, details_values: list[str]) -> "str | None":
    """يرجع القيمة المصححة، أو None لو ما فيه تغيير مطلوب (القيمة الحالية بالخلية (raw، بدون
    أي strip — قد تكون مسافة زائدة جزء من القيمة الحقيقية بالقائمة المنسدلة نفسها) تطابق
    القائمة الحية حرفيًا أصلًا)."""
    if not raw.strip():
        return None
    key = raw.strip().lower()

    if key == "job":
        corrected = match_literal("Job Email", details_values)
        return None if corrected == raw else (corrected or "")

    if key in _DETAILS_BANNED:
        # "service"/"Website" تُمسح دائمًا، إلا لو الـRemark (أقرب أثر متاح لملخص المكالمة
        # الأصلي بالصفوف القديمة) فيه إشارة تسويق/عرض خدمات واضحة -> Advertisement بدلها.
        if remark and is_vendor_service_pitch(remark):
            corrected = match_literal("Advertisement", details_values)
            return None if corrected == raw else (corrected or "")
        return None if raw == "" else ""

    matched = match_literal(raw, details_values)
    if matched:
        return None if matched == raw else matched

    if _looks_like_branch_mention(raw):
        corrected = match_literal("Branches", details_values)
        return None if corrected == raw else (corrected or "")

    return None if raw == "" else ""


def _correct_simple(raw: str, allowed_values: list[str], aliases: dict) -> "str | None":
    if not raw.strip():
        return None
    corrected = match_literal(raw, allowed_values, aliases=aliases)
    return None if corrected == raw else (corrected or "")


def build_report(cfg: dict) -> dict:
    google_cfg = cfg["google_sheets"]
    brand_dictionary = cfg["brand_dictionary"]
    city_aliases = cfg.get("city_aliases", {})
    company_aliases = {name: c.get("sheet_aliases", []) for name, c in brand_dictionary.items()}

    print("جاري الاتصال بشيت المزروع وقراءة القوائم المنسدلة الحية...")
    gc = get_client(str(credentials_path(cfg)))
    live_lists = fetch_dropdown_lists(
        credentials_path=str(credentials_path(cfg)),
        spreadsheet_id=google_cfg["spreadsheet_id"],
        tabs_cfg=google_cfg["tabs"],
        column_names=_TARGET_COLUMNS,
    )
    for col in _TARGET_COLUMNS:
        print(f"  {col}: {len(live_lists.get(col, []))} قيمة بالقائمة الحية")

    resolved_ws = validate_gids(gc, google_cfg["spreadsheet_id"], google_cfg["tabs"])

    # {column: {"changes": [(tab, row_idx, before, after)], "blanked": int, "total_checked": int}}
    report = {col: {"changes": [], "blanked": 0, "total_checked": 0} for col in _TARGET_COLUMNS}

    for tab_name, ws in resolved_ws.items():
        print(f"قراءة تبويب {tab_name}...")
        values = ws.get_all_values()
        if not values:
            continue
        header = [h.strip() for h in values[0]]
        col_index = {name: header.index(name) for name in header}
        remark_idx = col_index.get("Remark")

        for row_idx, row in enumerate(values[1:], start=2):
            remark = row[remark_idx].strip() if remark_idx is not None and remark_idx < len(row) else ""

            for col in _TARGET_COLUMNS:
                if col not in col_index:
                    continue
                idx = col_index[col]
                raw = row[idx] if idx < len(row) else ""
                if not raw.strip():
                    continue
                report[col]["total_checked"] += 1

                if col == "Details":
                    corrected = _correct_details(raw, remark, live_lists.get("Details", []))
                elif col == "company":
                    corrected = _correct_simple(raw, live_lists.get("company", []), company_aliases)
                else:  # Region
                    corrected = _correct_simple(raw, live_lists.get("Region", []), city_aliases)

                if corrected is None:
                    continue  # لا تغيير مطلوب
                if corrected == "":
                    report[col]["blanked"] += 1
                report[col]["changes"].append((tab_name, row_idx, raw, corrected))

    return report


def print_report(report: dict) -> None:
    print("\n" + "=" * 70)
    print("تقرير التصحيح (Dry-Run — لم يُكتب أي شيء بالشيت)")
    print("=" * 70)
    for col, data in report.items():
        changed = len(data["changes"])
        print(f"\n--- عمود {col} ---")
        print(f"صفوف فُحصت (غير فاضية أصلًا): {data['total_checked']}")
        print(f"صفوف ستتغيّر: {changed}")
        print(f"منها خانات ستُمسح (تصير فاضية): {data['blanked']}")
        if changed:
            print("أمثلة (قبل ← بعد):")
            for tab_name, row_idx, before, after in data["changes"][:MAX_EXAMPLES_PER_COLUMN]:
                after_display = after if after else "(فاضي)"
                print(f'  [{tab_name}!{row_idx}] "{before}" ← "{after_display}"')
            if changed > MAX_EXAMPLES_PER_COLUMN:
                print(f"  ... و{changed - MAX_EXAMPLES_PER_COLUMN} تغيير إضافي غير معروض هنا.")
    print("\n" + "=" * 70)
    print("لم يُكتب أي شيء بالشيت حتى الآن. راجع التقرير أعلاه ووافق قبل أي تطبيق فعلي.")
    print("تنبيه: التطبيق الفعلي (كتابة التصحيحات) يحتاج أولًا توسيع صلاحية حساب الخدمة من")
    print("قراءة فقط إلى قراءة وكتابة (scope + صلاحية Editor على الشيت) — غير مفعّل بهذا السكربت حاليًا.")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="تقرير تصحيح قيم company/Region/Details بشيت المزروع حسب القوائم المنسدلة الحية (Dry-Run فقط)"
    )
    parser.add_argument("--config", default=None, help="مسار ملف config.yaml (اختياري)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    report = build_report(cfg)
    print_report(report)


if __name__ == "__main__":
    main()

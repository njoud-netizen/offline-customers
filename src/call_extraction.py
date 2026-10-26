"""استخراج اسم العميل/المدينة/تصنيف Details من نص Call Summary عبر Claude API، بالباتش.

يُستدعى فقط للمكالمات التي فيها Call Summary غير فاضي — باقي المكالمات (بلا رد/مشغول/قصيرة
بدون ملخص) لا تُستهلك منها أي طلب API إطلاقًا.
"""
import json
import os

from .maqsam_import import MaqsamCallRecord

_DETAILS_OTHER = "Other"


class CallExtractionError(Exception):
    """خطأ واضح يمكن للواجهة عرضه مباشرة (مفتاح ناقص، رد غير صالح من API...)."""
    pass


def anthropic_api_key() -> "str | None":
    """نفس أسلوب google_secrets_info() بـ src/sheets.py: Streamlit secrets أولًا، وإلا متغير بيئة."""
    try:
        import streamlit as st
        if "ANTHROPIC_API_KEY" in st.secrets:
            return str(st.secrets["ANTHROPIC_API_KEY"])
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def _build_prompt(batch: list, details_catalog: list[str]) -> str:
    catalog_text = "\n".join(f"- {d}" for d in details_catalog)
    calls_text = "\n\n".join(f'[{call_id}]\n"""{summary}"""' for call_id, summary in batch)
    return f"""لديك مجموعة ملخصات مكالمات خدمة عملاء (Call Summary) بالإنجليزية. لكل مكالمة، استخرج:
1. customer_name: اسم العميل إن ذُكر صريحًا بالنص فقط (وإلا نص فاضي "").
2. city: مدينة العميل إن ذُكرت صريحًا فقط (وإلا نص فاضي "").
3. details: أقرب قيمة مطابقة **حرفيًا تمامًا** لقيمة واحدة من هذي القائمة الثابتة:
{catalog_text}
   إذا لم تنطبق أي قيمة من القائمة على محتوى المكالمة، استخدم القيمة الحرفية "Other" فقط
   (بدون أي نص آخر بحقل details)، وضع اقتراحك القصير بحقل details_suggested.

مهم جدًا: لا تخترع قيمة details غير موجودة حرفيًا بالقائمة أعلاه — فقط قيمة من القائمة أو "Other".

المكالمات:
{calls_text}

أرجع فقط JSON array صالح (بدون أي نص إضافي قبله أو بعده، وبدون code fences)، كل عنصر بهذا
الشكل بالضبط:
{{"id": "...", "customer_name": "...", "city": "...", "details": "...", "details_suggested": "..."}}
"""


def _parse_response_text(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def extract_batch(client, model: str, batch: list, details_catalog: list[str]) -> dict:
    prompt = _build_prompt(batch, details_catalog)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = "".join(getattr(block, "text", "") for block in response.content)

    try:
        items = _parse_response_text(raw_text)
    except json.JSONDecodeError as e:
        raise CallExtractionError(f"رد Claude ليس JSON صالح: {e}\n\nالرد الخام (أول 500 حرف): {raw_text[:500]}") from e

    catalog_set = set(details_catalog)
    result = {}
    for item in items:
        call_id = str(item.get("id", "")).strip()
        if not call_id:
            continue
        details = str(item.get("details", "")).strip()
        if details not in catalog_set and details != _DETAILS_OTHER:
            # حماية إضافية: أي قيمة غير مطابقة حرفيًا للقائمة تُعتبر Other بدل كسر الـ dropdown بالشيت
            details = _DETAILS_OTHER
        result[call_id] = {
            "customer_name": str(item.get("customer_name", "")).strip(),
            "city": str(item.get("city", "")).strip(),
            "details": details,
            "details_suggested": str(item.get("details_suggested", "")).strip(),
        }
    return result


def extract_call_fields(
    records: list[MaqsamCallRecord],
    details_catalog: list[str],
    model: str,
    batch_size: int = 20,
    on_progress=None,
) -> dict:
    """
    يرجع {call_id: {"customer_name", "city", "details", "details_suggested"}} للمكالمات التي
    فيها Call Summary غير فاضي فقط. فشل دفعة واحدة لا يوقف باقي الدفعات — فقط تبقى مكالمات
    تلك الدفعة بلا استخراج (تظهر لاحقًا بقائمة "تحتاج مراجعة").
    """
    log = on_progress or print
    to_process = [(r.call_id, r.call_summary) for r in records if r.call_summary.strip()]

    if not to_process:
        log("لا توجد أي مكالمات فيها Call Summary بهذا الملف — لن يتم استدعاء Claude API.")
        return {}

    api_key = anthropic_api_key()
    if not api_key:
        raise CallExtractionError(
            "مفتاح ANTHROPIC_API_KEY غير موجود — ضعه بملف .streamlit/secrets.toml محليًا، أو بإعدادات "
            "Secrets لتطبيق Streamlit Cloud، أو كمتغير بيئة ANTHROPIC_API_KEY."
        )

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    results: dict = {}
    total_batches = (len(to_process) + batch_size - 1) // batch_size
    for i in range(0, len(to_process), batch_size):
        batch = to_process[i: i + batch_size]
        batch_num = i // batch_size + 1
        log(f"استخراج التفاصيل بالذكاء الاصطناعي — الدفعة {batch_num}/{total_batches} ({len(batch)} مكالمة)...")
        try:
            batch_result = extract_batch(client, model, batch, details_catalog)
            results.update(batch_result)
        except Exception as e:
            log(f"[تحذير] فشلت الدفعة {batch_num}: {e} — ستظهر مكالماتها بقائمة 'تحتاج مراجعة'.")

    log(f"اكتمل الاستخراج: {len(results)} مكالمة من أصل {len(to_process)} فيها ملخص.")
    return results

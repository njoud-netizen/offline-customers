"""ترجمة نص Call Summary للعربي — مجانية بالكامل عبر MyMemory (بدون أي مفتاح/تكلفة)، باتصال
HTTP مباشر (بدل deep_translator) لأن المكتبة لا تدعم timeout على الإطلاق — نحتاجه صراحة هنا
(حد 3 ثواني لكل طلب، طلب صريح). أفضل جهد فقط: عند أي فشل (شبكة/مهلة/حد الاستخدام اليومي) يرجع
النص الإنجليزي الأصلي بدل ما يكسر بقية المعالجة.

فيه كاش بالذاكرة (نص -> (ترجمة, نجحت؟)) لتفادي ترجمة نفس النص أكثر من مرة بنفس العملية —
مشترك بين translate_to_arabic (القديمة) وtranslate_to_arabic_status (الجديدة، ترجع علم نجاح
صريح). st.cache_data (بطبقة العرض بـinbound_table.py) يضيف طبقة كاش إضافية عبر إعادة
التشغيلات (reruns)، فوق هذا الكاش الداخلي.

نضوب الحصة اليومية (طلب صريح — مؤكَّد فعليًا بفحص حي على استجابة حقيقية): MyMemory يرجع HTTP
429 لكلا الحالتين (تجاوز 5 طلبات/ثانية المؤقت، ونضوب الحصة اليومية الكامل) — الفرق الوحيد هو
محتوى الجسم نفسه: نضوب الحصة اليومية يحمل نص تحذيري صريح داخل responseData.translatedText
(مثال فعلي موثّق: "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY").
لذلك يجب فحص جسم الاستجابة دومًا (حتى مع 429) قبل الحكم بفشل عادي قابل لإعادة المحاولة — أي
استجابة فيها هذا التحذير تُعتبر نضوب حصة فورًا (لا إعادة محاولة لها، ويتوقف أي استدعاء لاحق
فورًا لباقي عمر العملية الحالية — أقرب تفسير عملي لـ"باقي اليوم" بدون تخزين دائم عبر إعادة
تشغيل الخادم)، بعكس 429 العادي (بلا نص تحذيري) الذي يستمر إعادة المحاولة العادية فيه."""
import time

import requests

_cache: dict = {}  # text -> (translated_text, succeeded)
_MAX_RETRIES = 1  # طلب صريح: محاولة واحدة إضافية فقط (محاولتان إجمالًا) بدل 3 سابقًا
_RETRY_BASE_DELAY = 0.6
_REQUEST_TIMEOUT_SECONDS = 3  # طلب صريح: حد أقصى 3 ثواني لكل طلب ترجمة
_MYMEMORY_URL = "http://api.mymemory.translated.net/get"
_QUOTA_EXCEEDED_MARKERS = ("MYMEMORY WARNING", "QUOTA EXCEEDED", "YOU USED ALL AVAILABLE FREE TRANSLATIONS")

_quota_exhausted = False  # بمجرد True يتوقف أي استدعاء شبكة لاحق فورًا بدون إعادة محاولة


def is_quota_exhausted() -> bool:
    return _quota_exhausted


def _looks_like_quota_exceeded(text: str) -> bool:
    upper = (text or "").upper()
    return any(marker in upper for marker in _QUOTA_EXCEEDED_MARKERS)


def _call_mymemory(text: str) -> "str | None":
    """يرجع النص المترجم (أو نص التحذير نفسه كما هو لو نضبت الحصة اليومية — الفحص يحدث
    بالمستدعي) لأي استجابة JSON صالحة، بغض النظر عن status_code (حتى 429 قد يحمل جسمًا فيه
    نص التحذير الصريح للحصة اليومية، يجب فحصه قبل اعتباره فشلًا عاديًا قابلًا لإعادة المحاولة).
    يرجع None فقط لو الجسم نفسه غير قابل للقراءة كـJSON أو بلا نص مترجم إطلاقًا."""
    response = requests.get(
        _MYMEMORY_URL,
        params={"q": text, "langpair": "en-US|ar-SA"},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    data = response.json()
    translated = (data.get("responseData") or {}).get("translatedText")
    return translated.strip() if translated else None


def _translate_with_status(text: str) -> tuple[str, bool]:
    global _quota_exhausted
    text = (text or "").strip()
    if not text:
        return text, True
    if text in _cache:
        return _cache[text]
    if _quota_exhausted:
        # طلب صريح: توقف فوري بدون أي محاولة شبكة إضافية طول ما الحصة اليومية ناضبة.
        result = (text, False)
        _cache[text] = result
        return result

    result = (text, False)
    for attempt in range(_MAX_RETRIES + 1):
        try:
            translated = _call_mymemory(text)
            if translated:
                if _looks_like_quota_exceeded(translated):
                    _quota_exhausted = True
                    break  # نضوب حصة فعلي (حتى لو جاء بـHTTP 429) -> لا إعادة محاولة
                result = (translated, True)
                break
        except Exception:
            pass  # شبكة/مهلة/JSON غير صالح -> نجرّب مرة إضافية (إن بقيت محاولات) ثم نستسلم
        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_BASE_DELAY * (attempt + 1))

    _cache[text] = result
    return result


def translate_to_arabic(text: str) -> str:
    translated, _ = _translate_with_status(text)
    return translated


def translate_to_arabic_status(text: str) -> tuple[str, bool]:
    """نفس الترجمة بالضبط (نفس الكاش/الاستدعاء — لا طلب API إضافي)، لكن ترجع علم نجاح صريح."""
    return _translate_with_status(text)

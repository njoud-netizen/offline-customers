"""ترجمة نص Call Summary للعربي — مجانية بالكامل، بدون أي مفتاح/تكلفة. طلب صريح: Google
Translate المجاني هو المصدر الأساسي، وMyMemory احتياط يُجرَّب فقط لو Google فشل. كلاهما باتصال
HTTP مباشر (بدل استخدام deep_translator كمكتبة وسيطة) لأن صفوف المكتبة (GoogleTranslator عبر
scraping صفحة translate.google.com/m، وMyMemoryTranslator) لا تدعم أي timeout على الإطلاق —
نحتاجه صراحة هنا (حد 3 ثواني لكل طلب). أفضل جهد فقط: عند فشل كلا المصدرين (شبكة/مهلة/حد
الاستخدام اليومي) يرجع النص الإنجليزي الأصلي بدل ما يكسر بقية المعالجة.

فيه كاش بالذاكرة (نص -> (ترجمة, نجحت؟)) لتفادي ترجمة نفس النص أكثر من مرة بنفس العملية —
مشترك بين translate_to_arabic (القديمة) وtranslate_to_arabic_status (الجديدة، ترجع علم نجاح
صريح). st.cache_data (بطبقة العرض بـinbound_table.py) يضيف طبقة كاش إضافية عبر إعادة
التشغيلات (reruns)، فوق هذا الكاش الداخلي.

نضوب الحصة اليومية بـMyMemory (طلب صريح — مؤكَّد فعليًا بفحص حي على استجابة حقيقية): يرجع HTTP
429 لكلا الحالتين (تجاوز 5 طلبات/ثانية المؤقت، ونضوب الحصة اليومية الكامل) — الفرق الوحيد هو
محتوى الجسم نفسه: نضوب الحصة اليومية يحمل نص تحذيري صريح داخل responseData.translatedText
(مثال فعلي موثّق: "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY").
أي استجابة فيها هذا التحذير تُعتبر نضوب حصة فورًا (لا إعادة محاولة لها، ويتوقف أي استدعاء
MyMemory لاحق فورًا لباقي عمر العملية الحالية — أقرب تفسير عملي لـ"باقي اليوم" بدون تخزين دائم
عبر إعادة تشغيل الخادم)، بعكس 429 العادي (بلا نص تحذيري) الذي يستمر إعادة المحاولة العادية
فيه. لا يوجد إشارة نضوب حصة مماثلة موثّقة لـGoogle المجاني — فشله (أي سبب) يُعامَل كفشل عادي
لنص هذا الطلب تحديدًا فقط، يليه فورًا تجربة MyMemory لنفس النص (بدون علم دائم)."""
import time

import requests

_cache: dict = {}  # text -> (translated_text, succeeded)
_MAX_RETRIES = 1  # طلب صريح: محاولة واحدة إضافية فقط لكل مصدر (محاولتان إجمالًا لكل منهما)
_RETRY_BASE_DELAY = 0.6
_REQUEST_TIMEOUT_SECONDS = 3  # طلب صريح: حد أقصى 3 ثواني لكل طلب ترجمة
_GOOGLE_URL = "https://translate.googleapis.com/translate_a/single"
_MYMEMORY_URL = "http://api.mymemory.translated.net/get"
_QUOTA_EXCEEDED_MARKERS = ("MYMEMORY WARNING", "QUOTA EXCEEDED", "YOU USED ALL AVAILABLE FREE TRANSLATIONS")

_mymemory_quota_exhausted = False  # بمجرد True يتوقف أي استدعاء MyMemory لاحق فورًا بدون إعادة محاولة


def is_quota_exhausted() -> bool:
    return _mymemory_quota_exhausted


def _looks_like_quota_exceeded(text: str) -> bool:
    upper = (text or "").upper()
    return any(marker in upper for marker in _QUOTA_EXCEEDED_MARKERS)


def _call_google(text: str) -> "str | None":
    """نقطة translate_a/single المجانية (نفس التي تستخدمها أدوات مفتوحة المصدر معروفة مثل
    googletrans) — JSON نظيف بدون أي مفتاح، بدل صفحة translate.google.com/m المُستخدَمة بـ
    deep_translator (HTML scraping هش وبلا timeout). النص الطويل يرجع مقسّمًا لعدة جمل
    (قوائم فرعية)؛ هنا نلصقها كلها لنص عربي واحد متكامل."""
    response = requests.get(
        _GOOGLE_URL,
        params={"client": "gtx", "sl": "en", "tl": "ar", "dt": "t", "q": text},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        return None
    data = response.json()
    segments = data[0] if data else None
    if not segments:
        return None
    joined = "".join(seg[0] for seg in segments if seg and seg[0])
    return joined.strip() or None


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


def _try_source(call_fn, text: str) -> "str | None":
    """يجرّب مصدر ترجمة واحد حتى محاولتين إجمالًا (طلب صريح)، ويرجع النص أو None."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            result = call_fn(text)
            if result:
                return result
        except Exception:
            pass  # شبكة/مهلة/استجابة غير متوقعة -> نجرّب مرة إضافية (إن بقيت محاولات)
        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_BASE_DELAY * (attempt + 1))
    return None


def _translate_with_status(text: str) -> tuple[str, bool]:
    global _mymemory_quota_exhausted
    text = (text or "").strip()
    if not text:
        return text, True
    if text in _cache:
        return _cache[text]

    result = (text, False)

    # المصدر الأساسي (طلب صريح): Google Translate المجاني.
    translated = _try_source(_call_google, text)
    if translated:
        result = (translated, True)
    else:
        # احتياط: MyMemory — فقط لو ما نضبت حصته اليومية سابقًا بهذي العملية.
        if not _mymemory_quota_exhausted:
            for attempt in range(_MAX_RETRIES + 1):
                try:
                    mm_translated = _call_mymemory(text)
                    if mm_translated:
                        if _looks_like_quota_exceeded(mm_translated):
                            _mymemory_quota_exhausted = True
                            break  # نضوب حصة فعلي (حتى لو جاء بـHTTP 429) -> لا إعادة محاولة
                        result = (mm_translated, True)
                        break
                except Exception:
                    pass
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

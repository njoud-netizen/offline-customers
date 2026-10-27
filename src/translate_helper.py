"""ترجمة نص Call Summary للعربي — مجانية بالكامل، بدون أي مفتاح/تكلفة. طلب صريح: Google
Translate المجاني هو المصدر الأساسي، وMyMemory احتياط يُجرَّب فقط لو Google فشل. كلاهما باتصال
HTTP مباشر (بدل استخدام deep_translator كمكتبة وسيطة) لأن صفوف المكتبة (GoogleTranslator عبر
scraping صفحة translate.google.com/m، وMyMemoryTranslator) لا تدعم أي timeout على الإطلاق —
نحتاجه صراحة هنا (حد 3 ثواني لكل طلب). أفضل جهد فقط: عند فشل كلا المصدرين (شبكة/مهلة/حد
الاستخدام اليومي/حظر مؤقت بسبب كثرة الطلبات) يرجع النص الإنجليزي الأصلي بدل ما يكسر بقية
المعالجة — لكن طلب صريح: سبب كل فشل يُطبَع بالترمنال (print) فورًا، لا يُبلَع صامتًا.

فيه كاش بالذاكرة (نص -> (ترجمة, نجحت؟)) لتفادي ترجمة نفس النص أكثر من مرة بنفس العملية —
مشترك بين translate_to_arabic (القديمة) وtranslate_to_arabic_status (الجديدة، ترجع علم نجاح
صريح). peek_cached_translation (بطبقة العرض بـinbound_table.py) يتحقق من هذا الكاش بدون أي
استدعاء شبكة، فيسمح للجدول بالعرض الفوري بغض النظر عن حالة الترجمة.

نضوب الحصة اليومية بـMyMemory (مؤكَّد فعليًا بفحص حي على استجابة حقيقية): يرجع HTTP 429 لكلا
الحالتين (تجاوز 5 طلبات/ثانية المؤقت، ونضوب الحصة اليومية الكامل) — الفرق الوحيد هو محتوى
الجسم نفسه: نضوب الحصة اليومية يحمل نص تحذيري صريح داخل responseData.translatedText (مثال
فعلي موثّق: "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY"). أي
استجابة فيها هذا التحذير تُعتبر نضوب حصة فورًا (لا إعادة محاولة لها، ويتوقف أي استدعاء MyMemory
لاحق فورًا لباقي عمر العملية الحالية)، بعكس 429 العادي (بلا نص تحذيري) الذي يستمر إعادة
المحاولة العادية فيه.

Google المجاني أيضًا يرجع 429 عند كثرة الطلبات من نفس IP (مؤكَّد فعليًا — جسم HTML "Sorry..."
بدل JSON، وليس حظرًا دائمًا، عادة يزول بعد فترة قصيرة) — يُعامَل كفشل عادي لنص هذا الطلب
تحديدًا فقط (لا علم دائم مثل MyMemory لأنه غالبًا حظر IP مؤقت لا نضوب حصة حقيقي)، يليه فورًا
تجربة MyMemory لنفس النص."""
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


class _TranslationError(Exception):
    """فشل ترجمة عادي (شبكة/مهلة/حظر مؤقت) — قابل لإعادة المحاولة."""


class _QuotaExceededError(_TranslationError):
    """نضوب حصة يومية فعلي (MyMemory) — لا إعادة محاولة له إطلاقًا."""


def is_quota_exhausted() -> bool:
    return _mymemory_quota_exhausted


def _looks_like_quota_exceeded(text: str) -> bool:
    upper = (text or "").upper()
    return any(marker in upper for marker in _QUOTA_EXCEEDED_MARKERS)


def _call_google(text: str) -> str:
    """نقطة translate_a/single المجانية (نفس التي تستخدمها أدوات مفتوحة المصدر معروفة مثل
    googletrans) — JSON نظيف بدون أي مفتاح، بدل صفحة translate.google.com/m المُستخدَمة بـ
    deep_translator (HTML scraping هش وبلا timeout). النص الطويل يرجع مقسّمًا لعدة جمل
    (قوائم فرعية)؛ هنا نلصقها كلها لنص عربي واحد متكامل. يرفع _TranslationError بوصف دقيق
    لسبب كل فشل (لا يرجع None صامتًا) — طلب صريح: طباعة سبب الفشل بالترمنال."""
    response = requests.get(
        _GOOGLE_URL,
        params={"client": "gtx", "sl": "en", "tl": "ar", "dt": "t", "q": text},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise _TranslationError(
            f"Google Translate HTTP {response.status_code} "
            f"(غالبًا حظر مؤقت لكثرة الطلبات من نفس IP — يزول عادة بعد فترة قصيرة)"
        )
    try:
        data = response.json()
        segments = data[0] if data else None
    except Exception as e:
        raise _TranslationError(f"Google Translate: استجابة غير قابلة للقراءة ({e})") from e
    if not segments:
        raise _TranslationError("Google Translate: استجابة بلا نص مترجم (segments فاضية)")
    joined = "".join(seg[0] for seg in segments if seg and seg[0]).strip()
    if not joined:
        raise _TranslationError("Google Translate: نص الترجمة الناتج فاضي")
    return joined


def _call_mymemory(text: str) -> str:
    """يرفع _QuotaExceededError لو نضبت الحصة اليومية فعليًا (حتى لو جاءت بـHTTP 429)، أو
    _TranslationError لأي فشل عادي آخر — لا يرجع None صامتًا."""
    response = requests.get(
        _MYMEMORY_URL,
        params={"q": text, "langpair": "en-US|ar-SA"},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    try:
        data = response.json()
    except Exception as e:
        raise _TranslationError(f"MyMemory: استجابة غير قابلة للقراءة (HTTP {response.status_code}): {e}") from e
    translated = (data.get("responseData") or {}).get("translatedText")
    if not translated:
        raise _TranslationError(f"MyMemory: HTTP {response.status_code} بلا نص مترجم")
    translated = translated.strip()
    if _looks_like_quota_exceeded(translated):
        raise _QuotaExceededError("MyMemory: نضبت الحصة اليومية المجانية (" + translated[:120] + ")")
    return translated


def _try_source(call_fn, text: str, source_label: str) -> "str | None":
    """يجرّب مصدر ترجمة واحد حتى محاولتين إجمالًا (طلب صريح)، ويرجع النص أو None. طلب صريح:
    يطبع سبب الفشل بالترمنال لو استسلم كل المحاولات. _QuotaExceededError يُستثنى من إعادة
    المحاولة (ينتشر فورًا للمستدعي ليعطّل MyMemory لباقي العملية)."""
    last_error: "Exception | None" = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return call_fn(text)
        except _QuotaExceededError:
            raise
        except Exception as e:
            last_error = e
        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_BASE_DELAY * (attempt + 1))
    if last_error is not None:
        print(f"[ترجمة فشلت] {source_label}: {last_error}")
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
    translated = _try_source(_call_google, text, "Google Translate")
    if translated:
        result = (translated, True)
    elif not _mymemory_quota_exhausted:
        # احتياط: MyMemory — فقط لو ما نضبت حصته اليومية سابقًا بهذي العملية.
        try:
            translated = _try_source(_call_mymemory, text, "MyMemory")
            if translated:
                result = (translated, True)
        except _QuotaExceededError as e:
            _mymemory_quota_exhausted = True
            print(f"[ترجمة] {e} — سيتوقف MyMemory لباقي العملية الحالية.")

    _cache[text] = result
    return result


def translate_to_arabic(text: str) -> str:
    translated, _ = _translate_with_status(text)
    return translated


def translate_to_arabic_status(text: str) -> tuple[str, bool]:
    """نفس الترجمة بالضبط (نفس الكاش/الاستدعاء — لا طلب API إضافي)، لكن ترجع علم نجاح صريح."""
    return _translate_with_status(text)


def peek_cached_translation(text: str) -> "tuple[str, bool] | None":
    """يتحقق من الكاش فقط — بدون أي استدعاء شبكة إطلاقًا. يرجع None لو النص ما تُرجم (أو لم
    تتم محاولته) بعد بهذي العملية. طلب صريح: عرض الجدول لا يجب أن ينتظر أي ترجمة — هذه الدالة
    هي ما يسمح لواجهة الجدول (inbound_table.py) بعرض النص فورًا من الكاش الجاهز فقط، وتأجيل أي
    ترجمة غير جاهزة بعد لِما بعد عرض الجدول."""
    key = (text or "").strip()
    if not key:
        return key, True
    return _cache.get(key)

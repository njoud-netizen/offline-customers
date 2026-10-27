"""ترجمة نص Call Summary للعربي — مجانية بالكامل عبر MyMemory (بدون أي مفتاح/تكلفة).
أفضل جهد فقط: عند أي فشل (شبكة/حد استخدام يومي لحساب MyMemory المجاني المشترك) يرجع النص
الإنجليزي الأصلي بدل ما يكسر بقية المعالجة. فيه كاش بالذاكرة (نص -> (ترجمة, نجحت؟)) لتفادي
ترجمة نفس النص أكثر من مرة بنفس التشغيلة، ومُشترك بين translate_to_arabic (القديمة، تُستخدم
لعمود Remark بملف الإخراج/الشيت — سلوكها الظاهري لم يتغيّر إطلاقًا) وtranslate_to_arabic_status
(جديدة، تُستخدم فقط بعرض لوحة Inbound Call لمعرفة صراحة متى فشلت الترجمة).

إعادة محاولة (طلب صريح): حتى محاولتين إضافيتين (3 محاولات إجمالًا) بفاصل متزايد قبل اعتبار
الترجمة فاشلة فعليًا — يقلّل أثر TooManyRequests/StopIteration المؤقتة (مؤكَّدتان فعليًا
بفحص حي على بيانات حقيقية — راجع inbound_pipeline.py)."""
import time

_cache: dict = {}  # text -> (translated_text, succeeded)
_MAX_RETRIES = 2
_RETRY_BASE_DELAY = 0.6


def _translate_with_status(text: str) -> tuple[str, bool]:
    text = (text or "").strip()
    if not text:
        return text, True
    if text in _cache:
        return _cache[text]

    result = (text, False)
    for attempt in range(_MAX_RETRIES + 1):
        try:
            from deep_translator import MyMemoryTranslator
            translated = MyMemoryTranslator(source="en-US", target="ar-SA").translate(text)
            if translated and translated.strip():
                result = (translated.strip(), True)
                break
        except Exception:
            pass  # فشل الترجمة -> نرجع النص الإنجليزي الأصلي بدل كسر المعالجة (بعد المحاولات)
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

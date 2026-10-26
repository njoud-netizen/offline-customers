"""ترجمة نص Call Summary للعربي — مجانية بالكامل عبر MyMemory (بدون أي مفتاح/تكلفة).
أفضل جهد فقط: عند أي فشل (شبكة/حد استخدام يومي) يرجع النص الإنجليزي الأصلي بدل ما يكسر
بقية المعالجة. فيه كاش بالذاكرة لتفادي ترجمة نفس النص أكثر من مرة بنفس التشغيلة."""

_cache: dict = {}


def translate_to_arabic(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    if text in _cache:
        return _cache[text]

    try:
        from deep_translator import MyMemoryTranslator
        translated = MyMemoryTranslator(source="en-US", target="ar-SA").translate(text)
        result = translated.strip() if translated else text
    except Exception:
        result = text  # فشل الترجمة -> نرجع النص الإنجليزي الأصلي بدل كسر المعالجة

    _cache[text] = result
    return result

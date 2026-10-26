"""مؤشر 3 خطوات (رفع الملف -> التحقق -> الاستخراج) لصفحة رفع ملف الأوفلاين — عرض حالة فقط،
لا يغيّر أو يستبدل أي خطوة فعلية بـ run_pipeline."""
import streamlit as st

STEP_UPLOAD = "upload"
STEP_VALIDATE = "validate"
STEP_EXTRACT = "extract"

_STEPS = [STEP_UPLOAD, STEP_VALIDATE, STEP_EXTRACT]


def render_step_indicator(current_step: str, labels: list[str], steps: list[str] | None = None) -> None:
    """بطاقات بيضاء بحدود — الخطوة الحالية حدّها بنفسجي، دائرة الرقم بنفسجية دائمًا، الخطوات
    المنتهية تعرض ✓ بدل الرقم. steps: تسلسل مفاتيح مخصص (افتراضيًا STEP_UPLOAD/VALIDATE/EXTRACT)
    — مرّر تسلسلك الخاص لو عندك خطوات بأسماء مختلفة (مثال: صفحة Inbound Call)."""
    step_keys = steps or _STEPS
    current_idx = step_keys.index(current_step) if current_step in step_keys else 0

    parts = ['<div class="maz-step-indicator">']
    for i, label in enumerate(labels[:3]):
        if i < current_idx:
            card_cls, label_cls, icon = "maz-step-done", "maz-step-done", "✓"
        elif i == current_idx:
            card_cls, label_cls, icon = "maz-step-current", "maz-step-current", str(i + 1)
        else:
            card_cls, label_cls, icon = "", "", str(i + 1)
        parts.append(
            f'<div class="maz-step {card_cls}">'
            f'<div class="maz-step-circle">{icon}</div>'
            f'<span class="maz-step-label {label_cls}">{label}</span>'
            f"</div>"
        )
        if i < len(labels[:3]) - 1:
            parts.append('<div class="maz-step-connector"></div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

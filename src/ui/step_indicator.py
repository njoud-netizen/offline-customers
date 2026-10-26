"""مؤشر 3 خطوات (رفع الملف -> التحقق -> الاستخراج) لصفحة رفع ملف الأوفلاين — عرض حالة فقط،
لا يغيّر أو يستبدل أي خطوة فعلية بـ run_pipeline."""
import streamlit as st

STEP_UPLOAD = "upload"
STEP_VALIDATE = "validate"
STEP_EXTRACT = "extract"

_STEPS = [STEP_UPLOAD, STEP_VALIDATE, STEP_EXTRACT]


def render_step_indicator(current_step: str, labels: list[str]) -> None:
    """current_step: إحدى STEP_UPLOAD/STEP_VALIDATE/STEP_EXTRACT. الخطوات قبلها تُعرض
    "منتهية" (✓ أخضر)، الحالية بنفسجية، اللي بعدها محايدة. labels بنفس ترتيب الخطوات الثلاث."""
    current_idx = _STEPS.index(current_step) if current_step in _STEPS else 0

    parts = ['<div class="maz-step-indicator">']
    for i, label in enumerate(labels[:3]):
        if i < current_idx:
            circle_cls, label_cls, icon = "maz-step-done", "maz-step-done", "✓"
        elif i == current_idx:
            circle_cls, label_cls, icon = "maz-step-current", "maz-step-current", str(i + 1)
        else:
            circle_cls, label_cls, icon = "", "", str(i + 1)
        parts.append(
            f'<div class="maz-step">'
            f'<div class="maz-step-circle {circle_cls}">{icon}</div>'
            f'<span class="maz-step-label {label_cls}">{label}</span>'
            f"</div>"
        )
        if i < len(labels[:3]) - 1:
            connector_cls = "maz-step-done" if i < current_idx else ""
            parts.append(f'<div class="maz-step-connector {connector_cls}"></div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

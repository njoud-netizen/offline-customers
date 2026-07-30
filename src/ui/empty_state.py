"""حالة فارغة موحّدة تُستخدم بكل الرسوم/الجداول/البطاقات عند عدم توفر بيانات."""
import streamlit as st


def render_empty_state(message: str, icon: str = "📭") -> None:
    st.markdown(
        f"""
        <div class="maz-empty-state">
            <div class="maz-empty-icon">{icon}</div>
            <div>{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

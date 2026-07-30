"""بطاقات مؤشرات الأداء الرئيسية (KPI) — رقم كبير + أيقونة + Sparkline اختياري +
نسبة تغيير عن الفترة السابقة (فقط عند توفر بيانات حقيقية).

بنية كل بطاقة: الأيقونة + التسمية + الرقم + نسبة التغيير كلها HTML واحد متكامل داخل
استدعاء st.markdown() واحد فقط (لا st.metric() إطلاقًا) — لأن st.metric() عنصر
Streamlit منفصل بتنسيق CSS داخلي ثابت (يقصّ القيم الطويلة بـ ellipsis، وهذا بالضبط
سبب ظهور "ر...." بدل "ر.س" سابقًا)، ولأن أي بناء من عدة استدعاءات HTML/عناصر منفصلة
يجعل التموضع "داخل نفس الصندوق" غير مضمون. الـ Sparkline وحده يبقى عنصر Streamlit
منفصل (st.altair_chart) لأنه الاستثناء التقني الوحيد الذي لا يمكن تضمينه بنص HTML خام؛
لضمان أنه لا يزال داخل نفس الصندوق بصريًا (حدود/خلفية)، نضع كل شيء داخل st.container
حقيقي (key=...) وليس div مفتوح/مغلق يدويًا (الطريقة القديمة المكسورة)."""
from dataclasses import dataclass

import altair as alt
import pandas as pd
import streamlit as st

from . import theme


@dataclass
class KPICardData:
    label: str
    value: str
    icon: str | None = None
    delta_pct: float | None = None
    sparkline_df: pd.DataFrame | None = None  # أعمدة: "x" (تاريخ), "y" (قيمة)
    tooltip: str | None = None
    accent: bool = False


def _sparkline_chart(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_line(color=theme.MAZNEXA_PURPLE, strokeWidth=2)
        .encode(
            x=alt.X("x:T", axis=None),
            y=alt.Y("y:Q", axis=None),
        )
        .properties(height=36)
        .configure_view(strokeWidth=0)
    )


def _delta_html(delta_pct: float | None) -> str:
    if delta_pct is None:
        return ""
    is_up = delta_pct >= 0
    color = theme.SUCCESS if is_up else theme.DANGER
    arrow = "▲" if is_up else "▼"  # رمز صريح + لون — لا اعتماد على اللون وحده
    return f'<div class="maz-kpi-delta" style="color:{color};">{arrow} {delta_pct:+.1f}%</div>'


def render_kpi_row(cards: list[KPICardData]) -> None:
    if not cards:
        return
    cols = st.columns(len(cards))
    for i, (col, card) in enumerate(zip(cols, cards)):
        with col:
            container_key = f"kpi_card_{'accent' if card.accent else 'plain'}_{i}"
            with st.container(key=container_key):
                icon_html = f'<span class="maz-kpi-icon">{card.icon}</span> ' if card.icon else ""
                title_attr = f' title="{card.tooltip}"' if card.tooltip else ""
                card_html = (
                    f'<div class="maz-kpi-inner"{title_attr}>'
                    f'<div class="maz-kpi-label">{icon_html}{card.label}</div>'
                    f'<div class="maz-kpi-value">{card.value}</div>'
                    f"{_delta_html(card.delta_pct)}"
                    f"</div>"
                )
                st.markdown(card_html, unsafe_allow_html=True)
                if card.sparkline_df is not None and not card.sparkline_df.empty and len(card.sparkline_df) > 1:
                    st.altair_chart(_sparkline_chart(card.sparkline_df), use_container_width=True)

"""غلاف موحّد لكل رسم بياني: عنوان + وصف، حالة فارغة، معالجة خطأ واضحة، Expander
لعرض بيانات الرسم + زر تنزيل CSV. يدعم مكتبتي الرسوم المستخدمتين بالمشروع: Altair
(أغلب الرسوم) وPlotly (رسم المبيعات/العملاء المدمج ذو المحورين — راجع charts_combo.py).

ملاحظة تصحيح مهمة: كان الغلاف يُبنى سابقًا بفتح <div class="maz-card"> عبر استدعاء
st.markdown ثم إغلاقه بستدعاء منفصل لاحقًا — هذا النمط لا يُحيط فعليًا بأي محتوى
(نفس عطل بطاقات KPI المُصلَح سابقًا): فحصت الـ DOM الفعلي وتأكدت أن كل div.maz-card
كان يُصيّر بلا أي عنصر ابن على الإطلاق (<div class="maz-card"></div> فارغ تمامًا)،
والمظهر "المتّسق" كان فقط بسبب تطابق ألوان العناصر المتجاورة صدفة — وهذا بالضبط سبب
اختلاف مستوى زر "View chart data" بين شارتين متجاورين بالإنجليزية (اختلاف عدد أسطر
الوصف يُغيّر الارتفاع الكلي المستقل لكل عنصر، بلا حاوية فعلية تُوحّد الارتفاع). الحل:
st.container(key=...) حقيقي (يُحيط فعليًا)، مع حجز ارتفاع أدنى ثابت لمنطقة
العنوان+الوصف حتى يبدأ الرسم دائمًا بنفس النقطة الرأسية بغض النظر عن طول النص."""
from typing import Any, Callable, Literal, Optional

import pandas as pd
import streamlit as st

from src.translations import t

from .empty_state import render_empty_state

BuildResult = Optional[tuple[Any, pd.DataFrame]]


def chart_card(
    key: str,
    title: str,
    lang: str,
    build: Callable[[], BuildResult],
    caption: str | None = None,
    stretch: bool = True,
    theme: str | None = "streamlit",
    library: Literal["altair", "plotly"] = "altair",
) -> None:
    """library="plotly" يعرض الرسم عبر st.plotly_chart بدل st.altair_chart — نفس بقية
    السلوك (عنوان/وصف/حالة فارغة/معالجة خطأ/Expander بيانات/تنزيل CSV) موحّد للنوعين."""
    with st.container(key=f"chart_card_{key}"):
        header_html = f'<p class="maz-card-title">{title}</p>'
        if caption:
            header_html += f'<p class="maz-card-subtitle">{caption}</p>'
        st.markdown(f'<div class="maz-chart-card-header">{header_html}</div>', unsafe_allow_html=True)

        try:
            result = build()
        except Exception as e:
            st.error(f"{t('error_chart_render', lang)}\n\n{e}")
            return

        if result is None:
            render_empty_state(t("empty_chart_no_data", lang))
        else:
            chart, agg_df = result
            if caption:
                # مربّع أدوات Streamlit (تكبير/تنزيل) يطفو بارتفاع سالب (-16px تقريبًا)
                # أعلى كل رسم — فاصل صريح هنا يمنع تراكبه فوق آخر كلمات الوصف.
                st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
            if library == "plotly":
                st.plotly_chart(chart, use_container_width=stretch)
            else:
                st.altair_chart(chart, use_container_width=stretch, theme=theme)
            with st.expander(t("expander_view_data", lang)):
                st.dataframe(agg_df, use_container_width=True, hide_index=True)
                csv_bytes = agg_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    t("download_chart_data_label", lang),
                    data=csv_bytes,
                    file_name=f"{key}.csv",
                    mime="text/csv",
                    key=f"{key}_download",
                )

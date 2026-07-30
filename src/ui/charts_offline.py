"""بناء رسوم العملاء الأوفلاين (Altair) — Donut توزيعي فقط. الرسمان الآخران اللذان
كانا هنا سابقًا (عدد العملاء حسب الشركة أفقيًا، وعدد العملاء شهريًا) حُذفا بالكامل:
الأول دُمج مع رسم المبيعات ضمن رسم Plotly مزدوج المحور واحد (راجع charts_combo.py)،
والثاني حُذف نهائيًا لازدحام بياناته وصعوبة قراءته."""
import math

import altair as alt
import pandas as pd

from src.translations import t

from . import theme
from .aggregations import aggregate_offline_by_brand


def _side_legend(title: str) -> alt.Legend:
    """Legend بوضع Vega-Lite الافتراضي (عمودي، يمين الرسم) — الأكثر استقرارًا وأقل
    عرضة لتراكب النصوص من أي تخصيص أفقي علوي."""
    return alt.Legend(title=title, labelLimit=160)


def _readable_text_color(hex_color: str) -> str:
    """يحسب لون نص (أبيض/داكن) يضمن تباينًا مقروءًا فوق لون خلفية معطى (صيغة YIQ
    المعتادة لقياس السطوع المُدرَك) — يعمل بشكل صحيح لأي لون مستقبلي من brand_color_map،
    وليس فقط الألوان الثلاثة الحالية."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    yiq = (r * 299 + g * 587 + b * 114) / 1000
    return theme.CHARCOAL if yiq >= 150 else theme.TEXT_PRIMARY


def build_offline_donut_chart(df_offline: pd.DataFrame, lang: str):
    agg = aggregate_offline_by_brand(df_offline)
    if agg.empty:
        return None
    domain = list(agg["company_name"])
    color_map = theme.brand_color_map(domain)
    color_range = [color_map[c] for c in domain]
    total_count = int(agg["count"].sum())

    agg = agg.copy()
    # تسمية Data Label داخل كل شريحة: نسبة مئوية فقط (بدون الرقم الخام) — والليجند
    # يبقى اسم البراند + دائرة اللون فقط (بدون أرقام)، حسب الطلب الأحدث.
    agg["pct_label"] = agg["pct_of_total"].round(0).astype(int).astype(str) + "%"
    agg["label_text_color"] = [_readable_text_color(color_map[c]) for c in agg["company_name"]]

    # زاوية منتصف كل شريحة محسوبة يدويًا (Radians، 0 = الثانية 12، تزداد باتجاه عقارب
    # الساعة) — بنفس منطق تراكم Vega-Lite للأقواس بالضبط (بترتيب صفوف agg كما هو).
    # لماذا لا نعتمد على theta/radius التلقائي بطبقة النص: تحقّقت عمليًا (بفحص مباشر
    # لإحداثيات SVG الفعلية) أن Vega-Lite لا يضع نص radius+theta في منتصف الشريحة
    # المُكدَّسة تلقائيًا بنفس منطق طبقة الأقواس رغم تطابق ترتيب البيانات — فتنزاح كل
    # نسبة عن شريحتها الصحيحة. حساب الزاوية يدويًا هنا (ثم stack=None) يحل المشكلة
    # جذريًا بدل الاعتماد على تكديس Vega الضمني لطبقتين منفصلتين.
    fractions = (agg["count"] / total_count).tolist() if total_count else [0.0] * len(agg)
    cum = 0.0
    mid_angles = []
    for frac in fractions:
        start = cum
        cum += frac * 2 * math.pi
        mid_angles.append((start + cum) / 2)
    agg["theta_mid"] = mid_angles
    # ترتيب صريح (0..n-1) بنفس ترتيب صفوف agg — بدونه، طبقة الأقواس تُكدَّس افتراضيًا
    # حسب الفرز الأبجدي لحقل اللون (company_name)، وليس بترتيب الصفوف الفعلي؛ بينما
    # حساب theta_mid أعلاه يفترض تراكمًا بترتيب الصفوف بالضبط. لضمان تطابق الطبقتين
    # (الأقواس ونصوص النسب) 100%، يجب أن تُكدَّس الأقواس بنفس ترتيب الصفوف أيضًا.
    agg["sort_order"] = range(len(agg))

    base = (
        alt.Chart(agg)
        .mark_arc(innerRadius=95, outerRadius=165)
        .encode(
            theta=alt.Theta("count:Q"),
            order=alt.Order("sort_order:Q"),
            color=alt.Color(
                "company_name:N",
                sort=domain,
                scale=alt.Scale(domain=domain, range=color_range),
                legend=_side_legend(t("legend_title_brand", lang)),
            ),
            tooltip=[
                alt.Tooltip("company_name:N", title=t("tooltip_company", lang)),
                alt.Tooltip("count:Q", title=t("chart_axis_count", lang)),
                alt.Tooltip("pct_of_total:Q", title=t("chart_axis_pct", lang), format=".1f"),
            ],
        )
    )
    pct_labels = (
        alt.Chart(agg)
        .mark_text(radius=130, fontSize=15, fontWeight="bold")
        .encode(
            theta=alt.Theta("theta_mid:Q", stack=None, scale=None),
            text=alt.Text("pct_label:N"),
            color=alt.Color("label_text_color:N", scale=None, legend=None),
        )
    )
    center_df = pd.DataFrame({"label": [str(total_count)]})
    center_text = alt.Chart(center_df).mark_text(size=36, fontWeight="bold", color=theme.TEXT_PRIMARY).encode(text="label:N")
    return (base + pct_labels + center_text).properties(height=400), agg

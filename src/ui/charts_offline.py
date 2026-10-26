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
    """Legend أفقي أسفل الرسم مباشرة (orient="bottom") بدل الوضع الجانبي الافتراضي — يعطي
    مساحة كافية لعرض الأسماء كاملة بدون قصّ؛ labelLimit=0 يُلغي أي حدّ أقصى لطول النص
    صراحةً (Vega-Lite: 0 = بدون قصّ)."""
    return alt.Legend(title=title, orient="bottom", labelLimit=0)


# ألوان الشرائح الغامقة اللي تحتاج نص أبيض فوقها (حسب الطلب الصريح) — أي لون ثاني (بما فيها
# أي براند مستقبلي بلون غير معروف عبر DEFAULT_COLOR) ياخذ نص #2E1866 الداكن تلقائيًا.
_DARK_SLICE_COLORS = {"#2E1866", "#9354FF"}


def _readable_text_color(hex_color: str) -> str:
    """أبيض فوق الشرائح الغامقة المحدَّدة صراحةً (#2E1866 وَ#9354FF)، وإلا #2E1866 الداكن
    فوق أي شريحة فاتحة ثانية — بدل حساب YIQ تلقائي سابقًا."""
    return theme.WHITE if hex_color.upper() in _DARK_SLICE_COLORS else "#2E1866"


def build_offline_donut_chart(df_offline: pd.DataFrame, lang: str):
    agg = aggregate_offline_by_brand(df_offline)
    if agg.empty:
        return None
    domain = list(agg["company_name"])
    color_map = theme.brand_color_map(domain)
    color_range = [color_map[c] for c in domain]
    total_count = int(agg["count"].sum())

    agg = agg.copy()
    # تسمية Data Label داخل كل شريحة: نسبة مئوية فقط (بدون الرقم الخام) — تُخفى تمامًا لو
    # أقل من 2% (نص فاضي بدل "0%" أو "1%" مزدحم داخل شريحة صغيرة جدًا).
    agg["pct_label"] = [
        f"{round(p):.0f}%" if p >= 2.0 else "" for p in agg["pct_of_total"]
    ]
    agg["label_text_color"] = [_readable_text_color(color_map[c]) for c in agg["company_name"]]
    # الليجند الآن يعرض اسم البراند + العدد معًا (طلب صريح جديد) — حقل منفصل للّون بدل
    # company_name مباشرة، بنفس ترتيب صفوف agg حتى يبقى كل براند بلونه الحتمي الصحيح.
    agg["legend_label"] = agg["company_name"] + " (" + agg["count"].astype(int).astype(str) + ")"

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

    legend_domain = list(agg["legend_label"])
    base = (
        alt.Chart(agg)
        .mark_arc(innerRadius=95, outerRadius=165)
        .encode(
            theta=alt.Theta("count:Q"),
            order=alt.Order("sort_order:Q"),
            color=alt.Color(
                "legend_label:N",
                sort=legend_domain,
                scale=alt.Scale(domain=legend_domain, range=color_range),
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
    # ارتفاع أكبر قليلاً (كان 400) ليتسع الـlegend الأفقي أسفل الرسم بدون ازدحام مع الدونات.
    return (base + pct_labels + center_text).properties(height=460), agg

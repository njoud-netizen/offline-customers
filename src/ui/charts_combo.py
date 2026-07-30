"""رسم Plotly واحد مزدوج المحور يدمج إجمالي المبيعات وعدد العملاء الأوفلاين لكل
شركة/براند — يستبدل رسمي Altair المنفصلين السابقين (المبيعات حسب الشركة + عدد
العملاء الأوفلاين حسب الشركة). محوران رأسيان لاختلاف مقياسَي القيمتين اختلافًا كبيرًا
(المبيعات بالملايين، عدد العملاء بالمئات)، بلون مختلف واضح لكل نوع عمود (وليس لكل
شركة كما بالرسوم الأخرى)، وLegend أفقي أعلى الرسم (لا يتراكب فوق أسماء الشركات).

الألوان: درجتان من نفس عائلة البنفسجي (هوية Maznexa) — TECHNO_PURPLE (فاتحة) للمبيعات
وNIGHT_PURPLE (غامقة) لعدد العملاء الأوفلاين، بفارق إضاءة كبير بينهما لتمييز واضح دون
لبس. هذا التخصيص محلي لهذا الرسم فقط عبر استيراد مباشر من theme.py — لا يمس
BRAND_COLORS/brand_color_map المستخدمة بألوان البراندات (BedHouse/BedQuarterKSA/
LaZBoy) بباقي رسوم الداشبورد إطلاقًا."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.translations import t

from . import theme
from .aggregations import aggregate_sales_and_offline_by_brand


def build_sales_offline_combo_chart(df_offline: pd.DataFrame, lang: str):
    agg = aggregate_sales_and_offline_by_brand(df_offline)
    if agg.empty:
        return None

    companies = agg["company_name"].tolist()
    sales_values = agg["total_sales"].tolist()
    count_values = agg["count"].tolist()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=companies,
            y=sales_values,
            name=t("chart_axis_sales", lang),
            marker_color=theme.TECHNO_PURPLE,
            text=[f"{v:,.0f}" for v in sales_values],
            textposition="outside",
            textfont=dict(color=theme.TEXT_PRIMARY, size=12),
            hovertemplate="%{x}<br>" + t("chart_axis_sales", lang) + ": %{y:,.2f}<extra></extra>",
            # offsetgroup إلزامي هنا: بدونه Plotly لا يفصل بصريًا بين عمودَي كل شركة عند
            # استخدام محورين (secondary_y) — يتعامل معهما كأنهما "subplot" مختلف فيرسمهما
            # فوق بعض بنفس موضع X بدل جنب بعض (تأكّدت من هذا العطل بصورة فعلية).
            offsetgroup="sales",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=companies,
            y=count_values,
            name=t("kpi_total_offline", lang),
            marker_color=theme.NIGHT_PURPLE,
            offsetgroup="offline_count",
            text=[f"{v:,.0f}" for v in count_values],
            textposition="outside",
            textfont=dict(color=theme.TEXT_PRIMARY, size=12),
            hovertemplate="%{x}<br>" + t("kpi_total_offline", lang) + ": %{y:,}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        barmode="group",
        height=560,
        margin=dict(t=70, b=60, l=70, r=70),
        plot_bgcolor=theme.SURFACE,
        paper_bgcolor=theme.SURFACE,
        font=dict(color=theme.TEXT_PRIMARY),
        # Legend أفقي أعلى منطقة الرسم تمامًا (y=1.02 يضعه فوق حدود الرسم مباشرة) —
        # نفس الحل المطلوب صراحةً لتفادي أي تراكب فوق أسماء الشركات على المحور الأفقي.
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        uniformtext_minsize=9,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(title_text=t("chart_axis_brand", lang), tickangle=-20, gridcolor=theme.BORDER, color=theme.TEXT_SECONDARY)
    fig.update_yaxes(
        title_text=t("chart_axis_sales", lang), secondary_y=False,
        gridcolor=theme.BORDER, zeroline=False, color=theme.TEXT_SECONDARY,
    )
    fig.update_yaxes(
        title_text=t("kpi_total_offline", lang), secondary_y=True,
        showgrid=False, zeroline=False, color=theme.TEXT_SECONDARY,
    )
    return fig, agg

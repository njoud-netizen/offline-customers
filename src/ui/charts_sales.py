"""بناء رسوم المبيعات (Altair) — ربع سنوي / سنوي. رسما "المبيعات حسب الشركة" و"المبيعات
الشهرية" اللذان كانا هنا سابقًا حُذفا: الأول دُمج مع رسم عدد العملاء الأوفلاين ضمن رسم
Plotly واحد مزدوج المحور (راجع charts_combo.py)، والثاني حُذف نهائيًا لازدحام بياناته.

ملاحظات تخطيط مهمة (لتفادي أي تراكب نص/عمود):
- الرسوم متعددة السلاسل (حسب البراند) تحتاج Legend فعليًا للتمييز بين الشركات؛ نستخدم
  وضع Vega-Lite الافتراضي (عمودي يمين الرسم خارج منطقته تمامًا) لأنه الأكثر استقرارًا
  وأقل عرضة لتراكب النصوص من أي تخصيص أفقي علوي.
"""
import altair as alt
import pandas as pd

from src.translations import t

from . import theme
from .aggregations import aggregate_annual_sales, aggregate_quarterly_sales

QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]


def _money_tooltip(field: str, title: str) -> alt.Tooltip:
    return alt.Tooltip(field, title=title, format=",.2f")


def _side_legend(title: str) -> alt.Legend:
    """Legend بوضع Vega-Lite الافتراضي (عمودي، يمين الرسم، خارج منطقة الرسم تمامًا) —
    الأكثر استقرارًا؛ نضبط فقط العنوان وحدًا أقصى لطول التسمية."""
    return alt.Legend(title=title, labelLimit=160)


def build_quarterly_sales_chart(df: pd.DataFrame, year: int, lang: str, by_brand: bool = False):
    agg = aggregate_quarterly_sales(df, year, by_brand=by_brand)
    if agg.empty or agg["total_sales"].sum() == 0:
        return None

    if by_brand:
        domain = sorted(agg["company_name"].unique())
        color_map = theme.brand_color_map(domain)
        color_range = [color_map[c] for c in domain]
        chart = (
            alt.Chart(agg)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("quarter_label:N", sort=QUARTER_ORDER, title=t("chart_axis_quarter", lang)),
                xOffset="company_name:N",
                y=alt.Y("total_sales:Q", title=t("chart_axis_sales", lang)),
                color=alt.Color("company_name:N", scale=alt.Scale(domain=domain, range=color_range), legend=_side_legend(t("legend_title_brand", lang))),
                tooltip=[
                    alt.Tooltip("quarter_label:N", title=t("chart_axis_quarter", lang)),
                    alt.Tooltip("company_name:N", title=t("tooltip_company", lang)),
                    _money_tooltip("total_sales:Q", t("chart_axis_sales", lang)),
                ],
            )
            .properties(height=340)
        )
    else:
        chart = (
            alt.Chart(agg)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=56, color=theme.MAZNEXA_PURPLE)
            .encode(
                x=alt.X("quarter_label:N", sort=QUARTER_ORDER, title=t("chart_axis_quarter", lang)),
                y=alt.Y("total_sales:Q", title=t("chart_axis_sales", lang)),
                tooltip=[alt.Tooltip("quarter_label:N", title=t("chart_axis_quarter", lang)), _money_tooltip("total_sales:Q", t("chart_axis_sales", lang))],
            )
            .properties(height=340)
        )
    return chart, agg


def build_annual_sales_chart(df: pd.DataFrame, lang: str, by_brand: bool = False):
    agg = aggregate_annual_sales(df, by_brand=by_brand)
    if agg.empty:
        return None

    if by_brand:
        domain = sorted(agg["company_name"].unique())
        color_map = theme.brand_color_map(domain)
        color_range = [color_map[c] for c in domain]
        highlight = alt.selection_point(fields=["company_name"], bind="legend")
        chart = (
            alt.Chart(agg)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("year:O", title=t("chart_axis_year", lang)),
                y=alt.Y("total_sales:Q", title=t("chart_axis_sales", lang)),
                color=alt.Color("company_name:N", scale=alt.Scale(domain=domain, range=color_range), legend=_side_legend(t("legend_title_brand", lang))),
                opacity=alt.condition(highlight, alt.value(1), alt.value(0.15)),
                tooltip=[
                    alt.Tooltip("year:O", title=t("chart_axis_year", lang)),
                    alt.Tooltip("company_name:N", title=t("tooltip_company", lang)),
                    _money_tooltip("total_sales:Q", t("chart_axis_sales", lang)),
                ],
            )
            .add_params(highlight)
            .properties(height=340)
        )
    else:
        chart = (
            alt.Chart(agg)
            .mark_bar(color=theme.MAZNEXA_PURPLE, cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=50)
            .encode(
                x=alt.X("year:O", title=t("chart_axis_year", lang)),
                y=alt.Y("total_sales:Q", title=t("chart_axis_sales", lang)),
                tooltip=[alt.Tooltip("year:O", title=t("chart_axis_year", lang)), _money_tooltip("total_sales:Q", t("chart_axis_sales", lang))],
            )
            .properties(height=340)
        )
    return chart, agg

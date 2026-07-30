"""
دوال تجميع خالصة (Pandas فقط، بدون أي استيراد لـ streamlit) تُستخدم من صفحة لوحة
التحكم لبناء الرسوم البيانية. لا تُغيّر أي تعريف موجود بـ src/sales_data.py أو
src/pipeline.py — فقط تُعيد تشكيل DataFrame الجاهز (df_sales / offline rows) لعرضه.
"""
from datetime import date, timedelta

import pandas as pd

QUARTER_LABELS = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}


def headroom_domain(values: pd.Series, factor: float = 1.18) -> list[float]:
    """مجال محور Y مع هامش أعلى العمود (لتفادي التصاق تسمية القيمة بحافة الرسم/خطوط
    الشبكة). يُستخدم فقط مع الرسوم التي تعرض تسمية رقمية فوق الأعمدة/النقاط مباشرة."""
    top = float(values.max()) if len(values) else 0.0
    if top <= 0:
        return [0.0, 1.0]
    return [0.0, top * factor]


def aggregate_sales_by_brand(df: pd.DataFrame) -> pd.DataFrame:
    """إجمالي المبيعات (amount_value) لكل شركة/براند — ترتيب تنازلي."""
    if df.empty:
        return pd.DataFrame(columns=["company_name", "total_sales"])
    out = (
        df.groupby("company_name", as_index=False)["amount_value"]
        .sum()
        .rename(columns={"amount_value": "total_sales"})
        .sort_values("total_sales", ascending=False)
        .reset_index(drop=True)
    )
    return out


def aggregate_monthly_sales(df: pd.DataFrame, by_brand: bool = False) -> pd.DataFrame:
    """إجمالي المبيعات مجمّعة شهريًا (باستخدام تاريخ الفاتورة الحقيقي)، مع/بدون تقسيم حسب البراند."""
    d = df.dropna(subset=["date"]).copy()
    if d.empty:
        cols = ["month", "company_name", "total_sales"] if by_brand else ["month", "total_sales"]
        return pd.DataFrame(columns=cols)
    d["month"] = d["date"].dt.to_period("M").dt.to_timestamp()
    group_cols = ["month", "company_name"] if by_brand else ["month"]
    out = d.groupby(group_cols, as_index=False)["amount_value"].sum().rename(columns={"amount_value": "total_sales"})
    return out.sort_values("month").reset_index(drop=True)


def aggregate_quarterly_sales(df: pd.DataFrame, year: int, by_brand: bool = False) -> pd.DataFrame:
    """المبيعات مجمّعة حسب الربع السنوي (Q1..Q4) لسنة محددة فقط — الأرباع الأربعة تظهر
    دائمًا (بقيمة صفر لو لا بيانات) حتى يبقى محور الرسم ثابتًا Q1..Q4."""
    d = df.dropna(subset=["date"]).copy()
    d = d[d["date"].dt.year == year]
    if d.empty:
        cols = ["quarter", "company_name", "total_sales"] if by_brand else ["quarter", "total_sales"]
        return pd.DataFrame(columns=cols)
    d["quarter"] = d["date"].dt.quarter

    if by_brand:
        grouped = d.groupby(["quarter", "company_name"], as_index=False)["amount_value"].sum()
        companies = sorted(d["company_name"].unique())
        full_index = pd.MultiIndex.from_product([[1, 2, 3, 4], companies], names=["quarter", "company_name"])
        out = (
            grouped.set_index(["quarter", "company_name"])
            .reindex(full_index, fill_value=0)
            .reset_index()
            .rename(columns={"amount_value": "total_sales"})
        )
    else:
        grouped = d.groupby("quarter", as_index=False)["amount_value"].sum()
        out = (
            grouped.set_index("quarter")
            .reindex([1, 2, 3, 4], fill_value=0)
            .reset_index()
            .rename(columns={"amount_value": "total_sales"})
        )
    out["quarter_label"] = out["quarter"].map(QUARTER_LABELS)
    return out.sort_values("quarter").reset_index(drop=True)


def aggregate_annual_sales(df: pd.DataFrame, by_brand: bool = False) -> pd.DataFrame:
    """إجمالي المبيعات لكل سنة — تظهر فقط السنوات التي لها بيانات فعليًا."""
    d = df.dropna(subset=["date"]).copy()
    if d.empty:
        cols = ["year", "company_name", "total_sales"] if by_brand else ["year", "total_sales"]
        return pd.DataFrame(columns=cols)
    d["year"] = d["date"].dt.year
    group_cols = ["year", "company_name"] if by_brand else ["year"]
    out = d.groupby(group_cols, as_index=False)["amount_value"].sum().rename(columns={"amount_value": "total_sales"})
    return out.sort_values("year").reset_index(drop=True)


def aggregate_offline_by_brand(df_offline: pd.DataFrame) -> pd.DataFrame:
    """عدد العملاء الأوفلاين لكل شركة/براند + النسبة من الإجمالي — ترتيب تنازلي."""
    if df_offline.empty:
        return pd.DataFrame(columns=["company_name", "count", "pct_of_total"])
    counts = df_offline["company_name"].value_counts()
    out = counts.rename_axis("company_name").reset_index(name="count").sort_values("count", ascending=False)
    total = out["count"].sum()
    out["pct_of_total"] = (out["count"] / total * 100) if total else 0.0
    return out.reset_index(drop=True)


def aggregate_sales_and_offline_by_brand(df_offline: pd.DataFrame) -> pd.DataFrame:
    """يجمع إجمالي المبيعات وعدد العملاء الأوفلاين لكل شركة بنفس الصف الواحد — كلا
    القيمتين محسوبتان من نفس df_offline (السجلات المصنّفة أوفلاين فقط)، فلا تعارض بين
    المقياسين. تُستخدم لبناء رسم Plotly المدمج ذي المحورين (charts_combo.py)."""
    sales = aggregate_sales_by_brand(df_offline)
    counts = aggregate_offline_by_brand(df_offline)
    if sales.empty and counts.empty:
        return pd.DataFrame(columns=["company_name", "total_sales", "count"])
    merged = sales.merge(counts[["company_name", "count"]], on="company_name", how="outer")
    merged["total_sales"] = merged["total_sales"].fillna(0.0)
    merged["count"] = merged["count"].fillna(0).astype(int)
    return merged.sort_values("total_sales", ascending=False).reset_index(drop=True)


def aggregate_offline_monthly(df_offline: pd.DataFrame, by_brand: bool = False) -> pd.DataFrame:
    """عدد العملاء الأوفلاين مجمّعًا شهريًا — نفس منطق app.py الأصلي تمامًا (لا تغيير
    بتعريف "أوفلاين")، فقط بإضافة خيار التقسيم حسب البراند."""
    d = df_offline.dropna(subset=["date"]).copy()
    if d.empty:
        cols = ["month", "company_name", "count"] if by_brand else ["month", "count"]
        return pd.DataFrame(columns=cols)
    d["month"] = d["date"].dt.to_period("M").dt.to_timestamp()
    group_cols = ["month", "company_name"] if by_brand else ["month"]
    out = d.groupby(group_cols, as_index=False).size().rename(columns={"size": "count"})
    return out.sort_values("month").reset_index(drop=True)


def previous_period_window(start: date, end: date) -> tuple[date, date]:
    """يحسب نافذة سابقة مباشرة بنفس طول [start, end] للمقارنة الحقيقية بدون بيانات وهمية."""
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - (end - start)
    return prev_start, prev_end


def period_over_period_change(
    df: pd.DataFrame,
    date_col: str,
    current_start: date,
    current_end: date,
    prev_start: date,
    prev_end: date,
    value_col: str | None = None,
) -> float | None:
    """نسبة التغيير المئوية بين الفترة الحالية والفترة السابقة مباشرة (بنفس الطول).
    يعيد None (وليس 0.0) إن لم تتوفر بيانات حقيقية بالفترة السابقة — لا نسبة وهمية أبدًا."""
    d = df.dropna(subset=[date_col])
    if d.empty:
        return None
    dates = d[date_col].dt.date
    current_mask = (dates >= current_start) & (dates <= current_end)
    prev_mask = (dates >= prev_start) & (dates <= prev_end)

    if value_col:
        current_total = d.loc[current_mask, value_col].sum()
        prev_total = d.loc[prev_mask, value_col].sum()
    else:
        current_total = int(current_mask.sum())
        prev_total = int(prev_mask.sum())

    if not prev_total:
        return None
    return (current_total - prev_total) / prev_total * 100

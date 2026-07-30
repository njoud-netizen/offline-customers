"""بطاقة 'آخر عمليات المعالجة' — تُبنى بقراءة ملفات output/summary_*.xlsx الموجودة
فعليًا من كل تشغيلة سابقة لـ run_pipeline (بدون أي تعديل بـ backend). لا يوجد سجل رفع
محفوظ باسم الملف الأصلي أو اسم المستخدم — لذلك لا تُعرض هذي المعلومتان (غير متوفرتين)."""
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.translations import t, translate_summary_label

from .empty_state import render_empty_state

_RUN_STAMP_RE = re.compile(r"summary_(\d{8}_\d{6})\.xlsx$")

_TIME_COL_KEY = "وقت التشغيل"
_DISPLAY_KEYS = [
    "إجمالي صفوف ملف الفواتير",
    "صفوف جديدة فعليًا بهذا التشغيل",
    "مصنّفة كأوفلاين",
    "مستبعدة (إجمالي)",
    "أرقام غير صالحة/مشبوهة (فاتورة + شيت)",
]


def _run_timestamp(path: Path) -> datetime:
    m = _RUN_STAMP_RE.search(path.name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def load_last_runs(output_dir: Path, limit: int = 10) -> pd.DataFrame:
    if not output_dir.exists():
        return pd.DataFrame()
    files = list(output_dir.glob("summary_*.xlsx"))
    if not files:
        return pd.DataFrame()

    files_with_ts = sorted(((_run_timestamp(f), f) for f in files), key=lambda x: x[0], reverse=True)[:limit]

    rows: list[dict] = []
    for ts, f in files_with_ts:
        try:
            summary_df = pd.read_excel(f)
            summary_map = dict(zip(summary_df["المؤشر"], summary_df["القيمة"]))
        except Exception:
            continue
        row = {_TIME_COL_KEY: ts.strftime("%Y-%m-%d %H:%M")}
        for key in _DISPLAY_KEYS:
            row[key] = summary_map.get(key, 0)
        rows.append(row)
    return pd.DataFrame(rows)


def render_last_runs_card(output_dir: Path, lang: str) -> None:
    st.markdown('<div class="maz-card">', unsafe_allow_html=True)
    st.markdown(f'<p class="maz-card-title">{t("last_runs_title", lang)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="maz-card-subtitle">{t("last_runs_subtitle", lang)}</p>', unsafe_allow_html=True)

    df = load_last_runs(output_dir)
    if df.empty:
        render_empty_state(t("empty_no_runs_yet", lang))
    else:
        display_df = df.rename(
            columns={
                col: (t("last_runs_col_time", lang) if col == _TIME_COL_KEY else translate_summary_label(col, lang))
                for col in df.columns
            }
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)

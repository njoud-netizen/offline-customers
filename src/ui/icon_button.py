"""زر أيقونة فقط (تحميل/تصدير) بمربع 40×40px + Tooltip مخصص عند التمرير — يُستخدم بدل زر
'تحميل CSV' النصي بكل مواضعه (هيدر النتائج، شريط الجدول، نوافذ البطاقات المنبثقة). الوظيفة
(تحميل CSV) لا تتغيّر إطلاقًا — فقط الشكل. الـTooltip مبني بـHTML/CSS خالص (خلفية #131321
ونص أبيض) بدل tooltip المتصفح الافتراضي غير القابل للتنسيق (راجع .maz-icon-dl-tooltip
بـtheme.py للتنسيق الفعلي)."""
import streamlit as st

from src.translations import t


def icon_download_button(data: bytes, file_name: str, mime: str, key: str, lang: str) -> None:
    with st.container(key=f"maz_icon_dl_{key}"):
        st.markdown(
            f'<div class="maz-icon-dl-tooltip">{t("inbound_export_csv_tooltip", lang)}</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            "", data=data, file_name=file_name, mime=mime,
            icon=":material/download:", key=key,
        )

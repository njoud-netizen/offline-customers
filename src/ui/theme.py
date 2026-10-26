"""
Design tokens + الحقنة الموحّدة لـ CSS لثيم Maznexa **الفاتح** (Light Theme).

تبديل كامل من الثيم الداكن السابق (Enterprise Dark) لثيم فاتح حسب مواصفة بصرية مفصّلة من
المستخدم. كل الملفات الأخرى (charts_combo.py, charts_sales.py, charts_offline.py, kpi_card.py...)
تستورد الثوابت من هنا فقط (SURFACE, TEXT_PRIMARY, BORDER...) — تبديل القيم بهذا الملف ينعكس
تلقائيًا على كل مكان يستخدمها، بدون الحاجة لتعديل تلك الملفات نفسها في أغلب الحالات.
"""

# ==== Maznexa Brand Color Guidelines — قيم حرفية، لا تقريب ====
MAZNEXA_PURPLE = "#9354FF"
PURPLE_LINK = "#7A3BF0"
PURPLE_WAVE = "#683EB5"
NIGHT_PURPLE = "#3E296B"
DARK_PURPLE = "#131321"
TECHNO_PURPLE = "#C9AAFF"
LUMINOUS_PURPLE = "#AE7FFF"
NEON_BLUE = "#6265FE"

WHITE = "#FFFFFF"
OFF_WHITE = "#F5F5F5"
LIGHT_GRAY = "#C9C9C9"
MEDIUM_GRAY = "#9E9E9E"
DARK_GRAY = "#474747"
CHARCOAL = "#1B1B1B"

# ==== توكنز الثيم الفاتح (Light Theme) ====
BG_PRIMARY = "#F6F4FB"
BG_SECONDARY = "#FFFFFF"
SURFACE = "#FFFFFF"
SURFACE_HOVER = "#F6F4FB"
BORDER = "#ECE8F5"
BORDER_STRONG = "#DCD5EE"
TEXT_PRIMARY = "#16131F"
TEXT_SECONDARY = "#6B6880"

SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER = "#DC2626"

CHART_AXIS_PRIMARY = MAZNEXA_PURPLE
CHART_AXIS_SECONDARY = "#3B82F6"

GRADIENT_PRIMARY = f"linear-gradient(135deg, {MAZNEXA_PURPLE} 0%, {PURPLE_WAVE} 100%)"
GRADIENT_SOFT = f"linear-gradient(135deg, rgba(147,84,255,0.10) 0%, rgba(104,62,181,0.04) 100%)"

# ==== شارات الحالة/التصنيف (Pill Badges) — قيم حرفية من المواصفة ====
BADGE_SERVICED_TEXT = "#047857"
BADGE_SERVICED_BG = "#E7F8F0"
BADGE_SERVICED_BAR = "#10B981"
BADGE_OFFERS_TEXT = "#6D28D9"
BADGE_OFFERS_BG = "#F1EAFF"
BADGE_ORDER_TEXT = "#1D4ED8"
BADGE_ORDER_BG = "#E8F0FE"
BADGE_OTHER_TEXT = "#4B4B5C"
BADGE_OTHER_BG = "#F1F0F5"
BADGE_REPEAT_TEXT = "#92400E"
BADGE_REPEAT_BG = "#FEF3C7"

# ترتيب ثابت للألوان الفئوية (Categorical) بالرسوم — نفس البراند ياخذ نفس اللون دائمًا.
BRAND_PALETTE_ORDER = ["#9354FF", "#3B82F6", "#10B981", "#F59E0B", "#C4A6FF", "#A9A5BA"]
BRAND_COLORS = {
    "BedQuarterKSA": BRAND_PALETTE_ORDER[0],
    "BedHouse": BRAND_PALETTE_ORDER[1],
    "LaZBoy": BRAND_PALETTE_ORDER[2],
}
FALLBACK_BRAND_COLOR = MEDIUM_GRAY
_FALLBACK_PALETTE_CYCLE = BRAND_PALETTE_ORDER[3:] + BRAND_PALETTE_ORDER[:3]

FONT_STACK = "'IBM Plex Sans Arabic', 'Poppins', 'Segoe UI', Tahoma, Arial, sans-serif"
FONT_STACK_LTR = "'Poppins', 'IBM Plex Sans Arabic', 'Segoe UI', Tahoma, Arial, sans-serif"

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Sans+Arabic:wght@400;500;600;700;800"
    "&family=Poppins:wght@400;500;600;700;800&display=swap"
)


def brand_color_map(brand_names: list[str]) -> dict[str, str]:
    """يعيد {اسم البراند: لون} حتمي لأي عدد براندات — المعروفة بألوانها الثابتة، وأي براند
    إضافي ياخذ لونًا من دورة احتياطية بترتيب أبجدي (حتمي، لا عشوائية)."""
    result: dict[str, str] = {}
    unmatched: list[str] = []
    for name in brand_names:
        if name in BRAND_COLORS:
            result[name] = BRAND_COLORS[name]
        else:
            unmatched.append(name)
    for i, name in enumerate(sorted(unmatched)):
        result[name] = _FALLBACK_PALETTE_CYCLE[i % len(_FALLBACK_PALETTE_CYCLE)]
    return result


def inject_theme(lang: str) -> None:
    import streamlit as st

    text_dir = "rtl" if lang == "ar" else "ltr"
    is_rtl = lang == "ar"

    rtl_sidebar_css = f"""
    /* ===== RTL SIDEBAR MIRROR (best-effort) — راجع data-testid عند أي ترقية Streamlit ===== */
    [data-testid="stAppViewContainer"] > div:first-child {{
        flex-direction: row-reverse;
    }}
    [data-testid="stSidebarCollapsedControl"] {{
        right: auto;
        left: 0.75rem;
    }}
    [data-testid="stSidebar"] {{
        border-inline-end: none;
        border-inline-start: 1px solid {BORDER};
    }}
    @media (max-width: 640px) {{
        [data-testid="stSidebar"][aria-expanded="true"] {{
            right: 0;
            left: auto;
        }}
    }}
    """ if is_rtl else ""

    st.markdown(
        f"""
        <style>
        @import url('{GOOGLE_FONTS_URL}');

        :root {{
            --bg-primary: {BG_PRIMARY};
            --bg-secondary: {BG_SECONDARY};
            --surface: {SURFACE};
            --surface-hover: {SURFACE_HOVER};
            --border: {BORDER};
            --border-strong: {BORDER_STRONG};
            --text-primary: {TEXT_PRIMARY};
            --text-secondary: {TEXT_SECONDARY};
            --brand-primary: {MAZNEXA_PURPLE};
            --brand-link: {PURPLE_LINK};
            --brand-secondary: {NEON_BLUE};
            --success: {SUCCESS};
            --warning: {WARNING};
            --danger: {DANGER};
            --gradient-primary: {GRADIENT_PRIMARY};
            --radius-card: 20px;
            --radius-input: 12px;
        }}

        html, body, .stApp {{
            direction: {text_dir};
            background-color: var(--bg-primary) !important;
            color: var(--text-primary);
            font-family: {FONT_STACK};
        }}
        .stMarkdown, h1, h2, h3, h4, h5, p, label, .stCaption, span {{
            direction: {text_dir};
        }}
        .stApp, .stApp p, .stApp span, .stApp label, .stApp div {{
            text-align: start;
        }}
        /* عناصر أرقام/تواريخ/هاتف LTR صراحة — خط Poppins مخصص لها حسب المواصفة */
        [dir="ltr"], .maz-ltr, .maz-kpi-value {{
            font-family: {FONT_STACK_LTR};
        }}

        /* إخفاء قائمة Streamlit الافتراضية وإصلاح تراكب العنوان فوق الشريط العلوي */
        header[data-testid="stHeader"] {{ background: transparent; }}
        #MainMenu, footer {{ visibility: hidden; }}
        .block-container {{ padding-top: 2.75rem; padding-bottom: 2rem; max-width: 1320px; }}

        /* ==== الشريط الجانبي (أبيض) ==== */
        [data-testid="stSidebar"] {{
            background: var(--bg-secondary);
            border-inline-end: 1px solid var(--border);
        }}
        [data-testid="stSidebarNav"] a {{
            border-radius: var(--radius-input);
            margin: 2px 8px;
            color: var(--text-primary);
            transition: background 180ms ease-in-out, color 180ms ease-in-out;
            min-height: 44px;
            display: flex;
            align-items: center;
        }}
        [data-testid="stSidebarNav"] a:hover {{
            background: var(--surface-hover);
        }}
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: {MAZNEXA_PURPLE} !important;
        }}
        [data-testid="stSidebarNav"] a[aria-current="page"] span {{
            color: {WHITE} !important;
            font-weight: 700;
        }}

        {rtl_sidebar_css}

        /* ==== بطاقة عامة ==== */
        .maz-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            padding: 20px 22px;
            margin-bottom: 20px;
        }}
        .maz-card-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0 0 2px 0;
        }}
        .maz-card-subtitle {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin: 0 0 14px 0;
        }}

        /* ==== بطاقات الرسوم البيانية ==== */
        div[class*="st-key-chart_card_"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            padding: 20px 22px;
            margin-bottom: 20px;
        }}
        .maz-chart-card-header {{ min-height: 88px; }}
        .maz-chart-card-header .maz-card-title {{ margin: 0 0 2px 0; }}
        .maz-chart-card-header .maz-card-subtitle {{ margin: 0; }}

        /* ==== الشريط العلوي للصفحة (Header) ==== */
        .maz-eyebrow {{
            color: {MAZNEXA_PURPLE};
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 4px;
            letter-spacing: 0.02em;
        }}
        .maz-page-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            padding: 20px 26px;
            margin-bottom: 22px;
        }}
        .maz-page-header h1 {{
            font-size: 34px;
            font-weight: 800;
            color: var(--text-primary);
            margin: 0;
            line-height: 1.25;
        }}
        .maz-page-header .maz-page-subtitle {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}
        .maz-page-header .maz-page-meta {{
            font-size: 0.78rem;
            color: var(--text-secondary);
            white-space: nowrap;
        }}

        /* ==== أزرار ==== */
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
            background: {MAZNEXA_PURPLE};
            border: none;
            color: {WHITE};
            font-weight: 700;
            border-radius: var(--radius-input);
            min-height: 44px;
            transition: filter 180ms ease-in-out;
        }}
        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
            filter: brightness(1.08);
        }}
        .stButton > button[kind="secondary"], .stFormSubmitButton > button[kind="secondary"] {{
            background: {WHITE};
            border: 1px solid var(--border);
            color: var(--text-primary);
            border-radius: var(--radius-input);
            min-height: 44px;
        }}
        [data-testid="stDownloadButton"] button {{
            background: {WHITE};
            color: var(--text-primary);
            border: 1px solid var(--border);
            border-radius: var(--radius-input);
            font-weight: 600;
            min-height: 44px;
            transition: border-color 180ms ease-in-out;
        }}
        [data-testid="stDownloadButton"] button:hover {{
            border-color: {MAZNEXA_PURPLE};
            color: {PURPLE_LINK};
        }}
        button:focus-visible, [role="button"]:focus-visible, input:focus-visible, textarea:focus-visible {{
            outline: 2px solid {MAZNEXA_PURPLE} !important;
            outline-offset: 2px;
        }}

        /* ==== منطقة رفع الملف ==== */
        [data-testid="stFileUploaderDropzone"] {{
            background: #FAF8FE;
            border: 2px dashed #C4A6FF !important;
            border-radius: 14px !important;
        }}
        [data-testid="stFileUploaderDropzone"] svg {{
            fill: {MAZNEXA_PURPLE} !important;
            color: {MAZNEXA_PURPLE} !important;
        }}
        [data-testid="stFileUploaderDropzone"] button {{
            background-color: {MAZNEXA_PURPLE} !important;
            color: {WHITE} !important;
            border: none !important;
            border-radius: 8px !important;
        }}
        [data-testid="stFileUploaderDropzone"] button:hover {{
            background-color: {PURPLE_WAVE} !important;
        }}
        .maz-upload-hint {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 6px;
        }}

        /* ==== بطاقات المؤشرات (KPI) ==== */
        div[class*="st-key-kpi_card_"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 16px 18px 12px 18px;
            min-height: 158px;
            display: flex;
            flex-direction: column;
        }}
        div[class*="st-key-kpi_card_accent_"] {{
            background: {GRADIENT_PRIMARY};
            border-color: {MAZNEXA_PURPLE};
            box-shadow: 0 8px 24px rgba(147,84,255,0.28);
        }}
        div[class*="st-key-kpi_card_accent_"] .maz-kpi-label {{ color: rgba(255,255,255,0.85); }}
        div[class*="st-key-kpi_card_accent_"] .maz-kpi-value {{ color: {WHITE}; }}
        .maz-kpi-icon {{ font-size: 1.3rem; opacity: 0.9; }}
        .maz-kpi-inner {{ display: flex; flex-direction: column; }}
        .maz-kpi-label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-bottom: 6px;
        }}
        .maz-kpi-value {{
            color: var(--text-primary);
            font-weight: 800;
            font-size: 40px;
            line-height: 1.2;
            direction: ltr;
            unicode-bidi: plaintext;
            text-align: start;
            white-space: normal;
            overflow-wrap: break-word;
            word-break: break-word;
        }}
        .maz-kpi-delta {{
            font-size: 0.85rem;
            font-weight: 700;
            margin-top: 4px;
            direction: ltr;
            text-align: start;
        }}
        .maz-kpi-subline {{
            font-size: 0.78rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}
        div[class*="st-key-kpi_card_accent_"] .maz-kpi-subline {{ color: rgba(255,255,255,0.8); }}
        .maz-kpi-progress-track {{
            width: 100%;
            height: 6px;
            border-radius: 999px;
            background: {BADGE_SERVICED_BG};
            margin-top: 8px;
            overflow: hidden;
        }}
        .maz-kpi-progress-fill {{
            height: 100%;
            border-radius: 999px;
            background: {BADGE_SERVICED_BAR};
        }}

        /* ==== بطاقات الأبرز (Insight Cards) ==== */
        .maz-insight-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 16px 18px;
            min-height: 150px;
        }}
        .maz-insight-icon-tile {{
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: {GRADIENT_SOFT}, var(--surface);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            margin-bottom: 10px;
        }}
        .maz-insight-label {{ color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 4px; }}
        .maz-insight-value {{ color: var(--text-primary); font-weight: 800; font-size: 22px; line-height: 1.3; }}
        .maz-insight-meta {{ color: var(--text-secondary); font-size: 0.78rem; margin-top: 4px; }}
        .maz-mini-bar-row {{ display: flex; align-items: center; gap: 8px; margin-top: 6px; }}
        .maz-mini-bar-label {{ font-size: 0.76rem; color: var(--text-secondary); min-width: 86px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .maz-mini-bar-track {{ flex: 1; height: 6px; border-radius: 999px; background: var(--border); overflow: hidden; }}
        .maz-mini-bar-fill {{ height: 100%; border-radius: 999px; background: {MAZNEXA_PURPLE}; }}

        /* ==== شارات الحالة/التصنيف (Pill Badges) ==== */
        .maz-badge-pill {{
            display: inline-block;
            padding: 3px 12px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .maz-badge-serviced {{ background: {BADGE_SERVICED_BG}; color: {BADGE_SERVICED_TEXT}; }}
        .maz-badge-offers {{ background: {BADGE_OFFERS_BG}; color: {BADGE_OFFERS_TEXT}; }}
        .maz-badge-order {{ background: {BADGE_ORDER_BG}; color: {BADGE_ORDER_TEXT}; }}
        .maz-badge-other {{ background: {BADGE_OTHER_BG}; color: {BADGE_OTHER_TEXT}; }}
        .maz-badge-repeat {{ background: {BADGE_REPEAT_BG}; color: {BADGE_REPEAT_TEXT}; }}
        .maz-badge-danger {{ background: #FEE2E2; color: {DANGER}; }}

        /* ==== مؤشر الخطوات (Step Indicator) ==== */
        .maz-step-indicator {{ display: flex; align-items: center; gap: 10px; margin-bottom: 18px; }}
        .maz-step {{ display: flex; align-items: center; gap: 8px; }}
        .maz-step-circle {{
            width: 28px; height: 28px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.8rem; font-weight: 700; color: {WHITE};
            background: var(--border-strong);
        }}
        .maz-step-circle.maz-step-current {{ background: {MAZNEXA_PURPLE}; }}
        .maz-step-circle.maz-step-done {{ background: {SUCCESS}; }}
        .maz-step-label {{ font-size: 0.85rem; color: var(--text-secondary); }}
        .maz-step-label.maz-step-current, .maz-step-label.maz-step-done {{ color: var(--text-primary); font-weight: 600; }}
        .maz-step-connector {{ flex: 1; height: 2px; background: var(--border-strong); min-width: 24px; }}
        .maz-step-connector.maz-step-done {{ background: {SUCCESS}; }}

        /* ==== رسوم Vega-Lite (Altair) — إصلاح تراكب Legend فوق النص بـRTL ==== */
        [data-testid="stVegaLiteChart"],
        [data-testid="stVegaLiteChart"] * {{
            direction: ltr !important;
        }}

        /* ==== الجداول (st.dataframe) ==== */
        [data-testid="stDataFrame"] {{
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }}

        /* ==== الجدول المخصص (Inbound Call) ==== */
        .maz-table-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            box-shadow: 0 2px 18px rgba(22,19,31,0.06);
            padding: 20px 22px;
            margin-bottom: 20px;
        }}
        .maz-table-info-strip {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            font-size: 0.82rem;
            color: var(--text-secondary);
            margin: 10px 2px;
        }}
        .maz-table-info-strip a, .maz-table-link-btn {{
            color: {PURPLE_LINK};
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
        }}
        .maz-table-scroll {{
            overflow-x: auto;
            border: 1px solid var(--border);
            border-radius: 14px;
        }}
        table.maz-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            min-width: 640px;
        }}
        table.maz-table thead th {{
            position: sticky;
            top: 0;
            background: var(--surface);
            color: var(--text-secondary);
            font-weight: 700;
            text-align: start;
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
            z-index: 1;
        }}
        table.maz-table tbody td {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
            color: var(--text-primary);
            vertical-align: middle;
        }}
        table.maz-table tbody tr:nth-child(even) {{ background: #FCFBFE; }}
        table.maz-table tbody tr:hover {{ background: {GRADIENT_SOFT}, var(--surface); }}

        /* ==== حالة فارغة ==== */
        .maz-empty-state {{
            text-align: center;
            color: var(--text-secondary);
            padding: 38px 12px;
        }}
        .maz-empty-state .maz-empty-icon {{ font-size: 2rem; margin-bottom: 8px; }}

        /* ==== Expander ==== */
        [data-testid="stExpander"] {{
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface);
        }}

        /* ==== فلتر الشركة المضغوط ==== */
        .maz-compact-filter-label {{
            font-size: 0.875rem;
            color: var(--text-primary);
            margin-bottom: 4px;
        }}
        .maz-compact-filter-box {{
            background: var(--surface-hover);
            border: 1px solid var(--border-strong);
            border-radius: 8px;
            padding: 8px 12px;
            color: var(--text-primary);
            font-size: 0.95rem;
            min-height: 2.5rem;
            display: flex;
            align-items: center;
        }}

        /* ==== التذييل ==== */
        .maz-footer {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.8rem;
            margin-top: 30px;
            padding-top: 14px;
            border-top: 1px solid var(--border);
        }}

        /* ==== شاشات ضيقة (390px) ==== */
        @media (max-width: 480px) {{
            .maz-page-header {{ flex-direction: column; align-items: flex-start; }}
            .maz-page-header h1 {{ font-size: 1.5rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

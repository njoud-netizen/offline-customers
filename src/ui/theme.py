"""
Design tokens + الحقنة الموحّدة لـ CSS الخاصة بالتصميم الداكن الاحترافي (Maznexa).
القيم البنفسجية/الزرقاء أدناه حرفية من هوية Maznexa (لا تُقرَّب ولا تُغيَّر). التوكنز
الداكنة الجديدة (خلفيات/أسطح/حدود/نصوص) مضافة لإخراج Enterprise Analytics Dashboard
داكن — البنفسجي يُستخدم كـ Accent فقط (أزرار، عنصر نشط بالقائمة، بطاقة KPI أو بطاقتين،
بعض عناصر الرسوم)، وليس كلون مهيمن على كل عنصر.
"""

# ==== Maznexa Brand Color Guidelines — قيم حرفية، لا تقريب ====
MAZNEXA_PURPLE = "#9354FF"
PURPLE_WAVE = "#683EB5"
NIGHT_PURPLE = "#3E296B"
DARK_PURPLE = "#131321"
TECHNO_PURPLE = "#C9AAFF"
LUMINOUS_PURPLE = "#AE7FFF"
NEON_BLUE = "#6265FE"  # Secondary Blue — يُستخدم مع البنفسجي لإبراز الهوية

WHITE = "#FFFFFF"
OFF_WHITE = "#F5F5F5"
LIGHT_GRAY = "#C9C9C9"
MEDIUM_GRAY = "#9E9E9E"
DARK_GRAY = "#474747"
CHARCOAL = "#1B1B1B"

# ==== توكنز داكنة جديدة (Enterprise Dark Theme) ====
BG_PRIMARY = "#0E0F12"
BG_SECONDARY = "#14151A"
SURFACE = "#1A1B21"
SURFACE_HOVER = "#202128"
BORDER = "rgba(255,255,255,0.08)"
BORDER_STRONG = "rgba(255,255,255,0.16)"
TEXT_PRIMARY = "#F5F5F7"
TEXT_SECONDARY = "#9B9CA5"

SUCCESS = "#34D399"
WARNING = "#FBBF24"
DANGER = "#F87171"

GRADIENT_PRIMARY = f"linear-gradient(135deg, {MAZNEXA_PURPLE} 0%, {PURPLE_WAVE} 100%)"
GRADIENT_SOFT = f"linear-gradient(135deg, rgba(147,84,255,0.16) 0%, rgba(104,62,181,0.08) 100%)"

# ترتيب ثابت للألوان الفئوية (Categorical) الحالية — لا يتغيّر لهذي البراندات الثلاثة.
# LaZBoy كان NIGHT_PURPLE (#3E296B) — قريب جدًا من خلفية الداشبورد الداكنة فيصعب تمييز
# شريحته بالرسوم (خصوصًا Donut)؛ رُفع لـ PURPLE_WAVE (أفتح، بنفس عائلة البنفسجي) لتباين
# أوضح، مع تطبيق التغيير بكل الرسوم التي تستخدم BRAND_COLORS (سنوي/ربعي/Donut) حفاظًا
# على اتساق لون LaZBoy عبر الداشبورد كله، لا بالـ Donut فقط.
BRAND_COLORS = {
    "BedQuarterKSA": MAZNEXA_PURPLE,
    "BedHouse": NEON_BLUE,
    "LaZBoy": PURPLE_WAVE,
}
FALLBACK_BRAND_COLOR = MEDIUM_GRAY

# دورة ألوان احتياطية لأي براند مستقبلي غير موجود بـ BRAND_COLORS أعلاه — حتمية دائمًا
# (لا عشوائية)، تُطبَّق بالترتيب الأبجدي على البراندات غير المعروفة فقط.
_FALLBACK_PALETTE_CYCLE = [LUMINOUS_PURPLE, TECHNO_PURPLE, PURPLE_WAVE, NEON_BLUE, NIGHT_PURPLE, MAZNEXA_PURPLE]

FONT_STACK = '"Segoe UI", "Tahoma", "Arial", sans-serif'


def brand_color_map(brand_names: list[str]) -> dict[str, str]:
    """يعيد {اسم البراند: لون} حتمي لأي عدد براندات — الثلاثة المعروفة بألوانها الثابتة،
    وأي براند إضافي يأخذ لونًا من دورة احتياطية بترتيب أبجدي (متكرر دون تكرار بصري إلا
    بعد استنفاد الدورة)."""
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

    # قسم قلب الشريط الجانبي لليمين معزول بالكامل هنا — حل CSS غير رسمي (best-effort)
    # فوق بنية Streamlit الداخلية. عند أي ترقية مستقبلية لـ Streamlit تُغيّر أسماء
    # data-testid الداخلية، هذا القسم تحديدًا هو أول ما يجب فحصه/تعديله.
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
            --brand-secondary: {NEON_BLUE};
            --success: {SUCCESS};
            --warning: {WARNING};
            --danger: {DANGER};
            --gradient-primary: {GRADIENT_PRIMARY};
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

        header[data-testid="stHeader"] {{ background: transparent; }}
        #MainMenu, footer {{ visibility: hidden; }}
        .block-container {{ padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1320px; }}

        /* ==== الشريط الجانبي ==== */
        [data-testid="stSidebar"] {{
            background: var(--bg-secondary);
        }}
        [data-testid="stSidebarNav"] a {{
            border-radius: 10px;
            margin: 2px 8px;
            transition: background 180ms ease-in-out, color 180ms ease-in-out;
        }}
        [data-testid="stSidebarNav"] a:hover {{
            background: var(--surface-hover);
        }}
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: var(--gradient-primary) !important;
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
            border-radius: 16px;
            box-shadow: 0 2px 14px rgba(0,0,0,0.28);
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

        /* ==== بطاقات الرسوم البيانية: st.container(key="chart_card_...") حقيقية ====
           (بديل .maz-card المفتوح/المُغلَق يدويًا الذي تبيّن أنه لا يُحيط بأي محتوى
           فعليًا). نفس خلفية/حدود/ظل .maz-card، مع ارتفاع أدنى ثابت لمنطقة العنوان+
           الوصف (maz-chart-card-header) حتى يبدأ الرسم دائمًا بنفس النقطة الرأسية بغض
           النظر عن عدد أسطر النص (يختلف بين العربية والإنجليزية لنفس المحتوى) — هذا
           بالضبط ما يضمن محاذاة زر "عرض بيانات الرسم" بنفس المستوى بين شارتين متجاورين. */
        div[class*="st-key-chart_card_"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: 0 2px 14px rgba(0,0,0,0.28);
            padding: 20px 22px;
            margin-bottom: 20px;
        }}
        .maz-chart-card-header {{
            min-height: 88px;
        }}
        .maz-chart-card-header .maz-card-title {{ margin: 0 0 2px 0; }}
        .maz-chart-card-header .maz-card-subtitle {{ margin: 0; }}

        /* ==== الشريط العلوي للصفحة ==== */
        .maz-page-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            background: {GRADIENT_SOFT}, var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px 24px;
            margin-bottom: 22px;
        }}
        .maz-page-header h1 {{
            font-size: 1.4rem;
            font-weight: 800;
            color: var(--text-primary);
            margin: 0;
        }}
        .maz-page-header .maz-page-subtitle {{
            font-size: 0.88rem;
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
            background: var(--gradient-primary);
            border: none;
            color: {WHITE};
            font-weight: 700;
            border-radius: 10px;
            transition: filter 180ms ease-in-out;
        }}
        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
            filter: brightness(1.08);
        }}
        .stButton > button[kind="secondary"], .stFormSubmitButton > button[kind="secondary"] {{
            background: var(--surface-hover);
            border: 1px solid var(--border-strong);
            color: var(--text-primary);
            border-radius: 10px;
        }}
        [data-testid="stDownloadButton"] button {{
            background: var(--surface-hover);
            color: var(--text-primary);
            border: 1px solid var(--border-strong);
            border-radius: 10px;
            font-weight: 600;
            transition: border-color 180ms ease-in-out;
        }}
        [data-testid="stDownloadButton"] button:hover {{
            border-color: {MAZNEXA_PURPLE};
            color: {TECHNO_PURPLE};
        }}
        button:focus-visible, [role="button"]:focus-visible, input:focus-visible, textarea:focus-visible {{
            outline: 2px solid {MAZNEXA_PURPLE} !important;
            outline-offset: 2px;
        }}

        /* ==== منطقة رفع الملف ==== */
        [data-testid="stFileUploaderDropzone"] {{
            background: var(--surface);
            border: 2px dashed {PURPLE_WAVE} !important;
            border-radius: 14px !important;
        }}
        [data-testid="stFileUploaderDropzone"] svg {{
            fill: {TECHNO_PURPLE} !important;
            color: {TECHNO_PURPLE} !important;
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
        /* بطاقات KPI: st.container(key="kpi_card_...") الحقيقية — Streamlit يضيف صنف
           st-key-<key> تلقائيًا لهذا الحاوي (موثّق رسميًا)، فيضمن احتواء كل ما بداخله
           (نص HTML واحد متكامل + الرسم المصغّر) داخل نفس الصندوق فعليًا بالـ DOM —
           لا st.metric() إطلاقًا هنا (كان يقصّ القيم الطويلة بـ ellipsis، وهذا بالضبط
           سبب ظهور عملة مقطوعة سابقًا). النص نفسه (الأيقونة + التسمية + الرقم + نسبة
           التغيير) HTML خام واحد كامل من kpi_card.py — بلا قصّ ولا التفاف قسري. */
        div[class*="st-key-kpi_card_"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px 16px 10px 16px;
            min-height: 158px;
            display: flex;
            flex-direction: column;
        }}
        div[class*="st-key-kpi_card_accent_"] {{
            background: {GRADIENT_SOFT}, var(--surface);
            border-color: rgba(147,84,255,0.35);
        }}
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
            font-size: 1.5rem;
            line-height: 1.3;
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

        /* ==== رسوم Vega-Lite (Altair) — إصلاح تراكب Legend فوق النص ====
           السبب الجذري: عنصر Legend بمكتبة Vega-Lite (دائرة اللون + نص اسم البراند)
           يُبنى بإحداثيات SVG مطلقة على افتراض اتجاه LTR (الدائرة أولًا، ثم النص يمتد
           لليمين). بما أن الصفحة كلها direction: rtl، يرث عنصر <text> بالـ SVG هذا
           الاتجاه من الصفحة، فيعيد المتصفح "تصحيح" محاذاة النص (text-anchor) بافتراض
           RTL فيزحف النص للخلف فوق دائرة اللون بدل الامتداد بعدها — هذا بالضبط سبب
           تراكب اللون فوق حروف بمنتصف/نهاية الاسم. الحل: تثبيت اتجاه LTR صراحةً على
           حاوية الرسم بالكامل (لا يؤثر على اتجاه باقي عناصر الصفحة الأخرى إطلاقًا). */
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

        /* ==== شارات الحالة/البراند ==== */
        .maz-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .maz-badge-success {{ background: rgba(52,211,153,0.14); color: {SUCCESS}; }}
        .maz-badge-warning {{ background: rgba(251,191,36,0.14); color: {WARNING}; }}
        .maz-badge-danger {{ background: rgba(248,113,113,0.14); color: {DANGER}; }}
        .maz-badge-info {{ background: rgba(147,84,255,0.14); color: {TECHNO_PURPLE}; }}

        /* ==== فلتر الشركة المضغوط (عرض "كل الشركات" بدل Chips مزدحمة) ==== */
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

        /* ==== التذييل ==== */
        .maz-footer {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.8rem;
            margin-top: 30px;
            padding-top: 14px;
            border-top: 1px solid var(--border);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

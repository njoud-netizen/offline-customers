"""
Design tokens + الحقنة الموحّدة لـ CSS لثيم Maznexa **الفاتح** (Light Theme).

تبديل كامل من الثيم الداكن السابق (Enterprise Dark) لثيم فاتح حسب مواصفة بصرية مفصّلة من
المستخدم. كل الملفات الأخرى (charts_combo.py, charts_sales.py, charts_offline.py, kpi_card.py...)
تستورد الثوابت من هنا فقط (SURFACE, TEXT_PRIMARY, BORDER...) — تبديل القيم بهذا الملف ينعكس
تلقائيًا على كل مكان يستخدمها، بدون الحاجة لتعديل تلك الملفات نفسها في أغلب الحالات.
"""

# ==== Maznexa Official Brand Palette — القائمة المغلقة الوحيدة المسموحة بكل الألوان
# (+ الأبيض) حسب الطلب الصريح: ممنوع أي لون خارجها بأي مكان بالتطبيق. ====
PURPLE_50 = "#F3EEFF"
PURPLE_100 = "#E4D4FF"
PURPLE_200 = "#C9AAFF"
PURPLE_300 = "#AE7FFF"
PURPLE_400 = "#9354FF"
PURPLE_500 = "#683EB5"
PURPLE_600 = "#3E296B"
PURPLE_700 = "#131321"

BLUE_50 = "#CFE7FE"
BLUE_100 = "#B5B9FE"
BLUE_200 = "#8C8FFE"
BLUE_300 = "#6265FE"
BLUE_400 = "#5053C8"
BLUE_500 = "#3F4192"
BLUE_600 = "#252F77"
BLUE_700 = "#172242"

WHITE = "#FFFFFF"

# أسماء دلالية (semantic) تُستخدم بباقي الملف — كلها مجرد أسماء بديلة لنفس قيم القائمة أعلاه،
# بدون أي قيمة hex إضافية جديدة.
MAZNEXA_PURPLE = PURPLE_400          # اللون البنفسجي الأساسي — بطاقة KPI المعبّأة، أيقونات
PRIMARY_ACTION = PURPLE_500          # الأزرار + العنصر النشط بالسايدبار + primaryColor
TEXT_MUTED = PURPLE_600              # نص ثانوي
TEXT_MUTED_DARK = PURPLE_600         # نص محاور الرسوم (نفس القيمة — توحيد كامل)
STEP_CARD_BORDER = PURPLE_100

# ==== توكنز الثيم الفاتح (Light Theme) ====
BG_PRIMARY = PURPLE_50
BG_SECONDARY = WHITE
SURFACE = WHITE
SURFACE_HOVER = PURPLE_50
BORDER = PURPLE_100
BORDER_STRONG = PURPLE_200
TEXT_PRIMARY = PURPLE_700
TEXT_SECONDARY = PURPLE_600

# أحمر الأخطاء استثناء وحيد قائم من جولات سابقة (لا بديل بالقائمة المعتمدة لمعنى "خطأ") —
# يبقى محصورًا برسائل الخطأ فقط، لا يُستخدم بأي بطاقة/شارة/رسم.
DANGER = "#B42318"
DANGER_BG = "#FEE4E2"

# ==== ألوان الرسوم البيانية — من القائمة المعتمدة حصرًا، تُستخدم مباشرة بكل ملفات الرسوم
# (charts_combo.py, charts_sales.py, charts_offline.py) — لا قيم hex أخرى مكتوبة يدويًا هناك. ====
MAZ_COLORS = {
    "sales": "#9354FF",    # إجمالي المبيعات
    "offline": "#252F77",  # إجمالي العملاء الأوفلاين
}

GRADIENT_PRIMARY = f"linear-gradient(135deg, {PURPLE_400} 0%, {PURPLE_500} 100%)"
GRADIENT_SOFT = f"linear-gradient(135deg, rgba(147,84,255,0.10) 0%, rgba(104,62,181,0.04) 100%)"

# ==== شارات الحالة/التصنيف (Pill Badges) — من القائمة المعتمدة حصرًا ====
BADGE_SERVICED_TEXT = PURPLE_400
BADGE_SERVICED_BG = PURPLE_50
BADGE_SERVICED_DOT = PURPLE_400
BADGE_OFFERS_TEXT = BLUE_600
BADGE_OFFERS_BG = BLUE_50
BADGE_ORDER_TEXT = PURPLE_600
BADGE_ORDER_BG = PURPLE_100
BADGE_OTHER_TEXT = PURPLE_600
BADGE_OTHER_BG = PURPLE_50
BADGE_REPEAT_TEXT = WHITE
BADGE_REPEAT_BG = BLUE_600

# مربعات الأيقونات الخطية — موحّدة بالكامل بكل مكان بالتطبيق (بدون تمييز لوني لكل بطاقة).
ICON_TILE_BG = PURPLE_50
ICON_TILE_COLOR = PURPLE_400

# ترتيب ثابت للألوان الفئوية (Categorical) بالرسوم — نفس البراند ياخذ نفس اللون دائمًا.
# أي براند غير مذكور هنا ياخذ DEFAULT_COLOR (من القائمة المعتمدة أيضًا).
BRAND_COLORS = {
    "BedQuarterKSA": "#9354FF",
    "BedHouse": "#252F77",
    "LaZBoy": "#8C8FFE",
    "BedQuarterBAH": "#C9AAFF",
    "BedQuarterUAE": "#CFE7FE",
}
DEFAULT_COLOR = PURPLE_300
FALLBACK_BRAND_COLOR = DEFAULT_COLOR

FONT_STACK = "'IBM Plex Sans Arabic', 'Poppins', 'Segoe UI', Tahoma, Arial, sans-serif"
FONT_STACK_LTR = "'Poppins', 'IBM Plex Sans Arabic', 'Segoe UI', Tahoma, Arial, sans-serif"

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Sans+Arabic:wght@400;500;600;700;800"
    "&family=Poppins:wght@400;500;600;700;800&display=swap"
)
# أيقونات خطّية (Line icons) بدل الإيموجي — نفس تسمية :material/x: المستخدمة أصلًا بـ st.Page(icon=...)،
# محمّلة كخط قابل لتلوينه بـCSS (color) لاستخدامها بالـHTML الخام (بطاقات "أبرز المؤشرات").
MATERIAL_SYMBOLS_URL = (
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap"
)


def _maznexa_altair_theme() -> dict:
    """خلفية شفافة + محاور/نصوص #3E296B (TEXT_MUTED_DARK) + شبكة أفقية فقط (محور Y) — مطبَّقة مركزيًا على كل
    رسوم Altair بالتطبيق (charts_sales.py, charts_offline.py, exclusion chart بصفحة الرفع)
    بدون الحاجة لتعديل كل ملف رسم على حدة؛ لا تتعارض مع ألوان mark/encoding المحددة يدويًا
    بكل رسم (البراندات، الشرائح...) لأنها إعدادات هيكلية عامة فقط (خلفية/محاور/شبكة)."""
    return {
        "config": {
            "background": "transparent",
            "view": {"strokeWidth": 0},
            "font": "IBM Plex Sans Arabic",
            "axis": {
                "labelColor": TEXT_MUTED_DARK,
                "titleColor": TEXT_MUTED_DARK,
                "labelFont": "IBM Plex Sans Arabic",
                "titleFont": "IBM Plex Sans Arabic",
                "gridColor": BORDER,
                "domainColor": BORDER,
                "tickColor": BORDER,
            },
            "axisX": {"grid": False},
            "axisY": {"grid": True},
            "legend": {"labelColor": TEXT_MUTED_DARK, "titleColor": TEXT_MUTED_DARK},
        }
    }


def register_altair_theme() -> None:
    import altair as alt
    alt.themes.register("maznexa", _maznexa_altair_theme)
    alt.themes.enable("maznexa")


def brand_color_map(brand_names: list[str]) -> dict[str, str]:
    """يعيد {اسم البراند: لون} حتمي لأي عدد براندات — المعروفة بألوانها الثابتة بـBRAND_COLORS،
    وأي براند غير معروف ياخذ DEFAULT_COLOR (رمادي-بنفسجي محايد) بدل أي لون عشوائي."""
    return {name: BRAND_COLORS.get(name, DEFAULT_COLOR) for name in brand_names}


def inject_theme(lang: str) -> None:
    import streamlit as st

    register_altair_theme()

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
        @import url('{MATERIAL_SYMBOLS_URL}');

        .material-symbols-outlined {{
            font-family: 'Material Symbols Outlined';
            font-weight: normal;
            font-style: normal;
            font-size: 20px;
            line-height: 1;
            vertical-align: middle;
            -webkit-font-smoothing: antialiased;
        }}

        :root {{
            --bg-primary: {BG_PRIMARY};
            --bg-secondary: {BG_SECONDARY};
            --surface: {SURFACE};
            --surface-hover: {SURFACE_HOVER};
            --border: {BORDER};
            --border-strong: {BORDER_STRONG};
            --text-primary: {TEXT_PRIMARY};
            --text-secondary: {TEXT_SECONDARY};
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
        /* دعم اسمي testid محتملين حسب نسخة Streamlit (stSidebarNav a القديم، stSidebarNavLink
           الأحدث) معًا — غير ضار لو أحدهما غير مطابق فعليًا. عنصر الصفحة النشطة تعبئة مصمتة
           {PRIMARY_ACTION} بنص أبيض. */
        [data-testid="stSidebarNav"] a, [data-testid="stSidebarNavLink"] {{
            border-radius: var(--radius-input);
            margin: 2px 8px;
            color: {TEXT_MUTED_DARK};
            background: transparent;
            transition: background 180ms ease-in-out, color 180ms ease-in-out;
            min-height: 44px;
            display: flex;
            align-items: center;
        }}
        [data-testid="stSidebarNav"] a span, [data-testid="stSidebarNavLink"] span {{
            color: {TEXT_MUTED_DARK} !important;
            opacity: 1 !important;
        }}
        [data-testid="stSidebarNav"] a:hover, [data-testid="stSidebarNavLink"]:hover {{
            background: {PURPLE_50};
        }}
        /* العنصر النشط: تعبئة مصمتة {PURPLE_500} بنص أبيض (بدل التينت الفاتح السابق) — حسب الطلب */
        [data-testid="stSidebarNav"] a[aria-current="page"], [data-testid="stSidebarNavLink"][aria-current="page"] {{
            background: {PRIMARY_ACTION} !important;
            border-radius: 12px;
        }}
        [data-testid="stSidebarNav"] a[aria-current="page"] span, [data-testid="stSidebarNavLink"][aria-current="page"] span {{
            color: {WHITE} !important;
            font-weight: 600;
        }}
        [data-testid="stSidebarCollapseButton"] svg {{ color: {TEXT_MUTED} !important; }}
        /* مبدّل AR/EN بالشريط الجانبي: أبيض بحدود فاتحة ونص داكن (بدل ألوان Streamlit الافتراضية) */
        [data-testid="stSidebar"] [data-baseweb="select"] > div {{
            background: {WHITE} !important;
            border: 1px solid var(--border) !important;
            color: var(--text-primary) !important;
        }}

        {rtl_sidebar_css}

        /* ==== بطاقة عامة ====
           .maz-card (class خام): تُستخدم فقط عند بناء كل HTML الكرت بنص واحد كامل داخل
           st.markdown() واحد (فتح+محتوى+إغلاق بنفس الاستدعاء) — آمن.
           div[class*="st-key-maz_card_"]: المسار الصحيح لأي كرت يحوي ودجت Streamlit حقيقية
           بداخله (st.file_uploader, st.button...) — st.container(key="maz_card_...") حقيقي
           يُحيط فعليًا بكل ما بداخله بالـDOM، بعكس فتح/إغلاق <div> بنداءين منفصلين (كان العطل
           الجذري لـ"الأشرطة البيضاء الفاضية": كل st.markdown ينتج عنصر DOM مستقل تمامًا). */
        .maz-card, div[class*="st-key-maz_card_"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            overflow: hidden;
            padding: 20px 22px;
            margin-bottom: 20px;
        }}
        /* عناصر Streamlit الداخلية (stVerticalBlock/element-container) شفافة دائمًا داخل أي
        بطاقة — overflow:hidden أعلاه وحده يمنع أي ركن مربع من محتوى داخلي يلامس الحواف. */
        div[class*="st-key-maz_card_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-maz_card_"] [data-testid="stElementContainer"] {{
            background: transparent;
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
            overflow: hidden;
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
        .maz-page-header, div[class*="st-key-maz_page_header"] {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            overflow: hidden;
            padding: 20px 26px;
            margin-bottom: 20px;
        }}
        div[class*="st-key-maz_page_header"] > div {{ width: 100%; }}
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
        /* شريط عنوان "نتائج الاستخراج" بعد المعالجة — بدون بطاقة/حدود (خلفية الصفحة مباشرة)
        + زر تحميل CSV بالجهة المقابلة، حسب الصورة المرجعية */
        div[class*="st-key-maz_results_header"] {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 20px;
        }}
        div[class*="st-key-maz_results_header"] > div {{ width: 100%; }}
        div[class*="st-key-maz_results_header"] h1 {{
            font-size: 34px;
            font-weight: 800;
            color: var(--text-primary);
            margin: 0;
            line-height: 1.25;
        }}
        div[class*="st-key-maz_results_header"] .maz-page-subtitle {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}
        /* بحث/فلتر الشركة/زر التحميل بالهيدر — كلها ارتفاع 48px ونفس radius الإدخالات */
        div[class*="st-key-maz_results_header"] [data-testid="stTextInput"] input,
        div[class*="st-key-maz_results_header"] [data-baseweb="select"] > div {{
            min-height: 48px;
            border-radius: var(--radius-input);
        }}
        div[class*="st-key-maz_results_header"] [data-testid="stDownloadButton"] button {{
            min-height: 48px;
        }}
        .maz-page-header .maz-page-meta {{
            font-size: 0.78rem;
            color: var(--text-secondary);
            white-space: nowrap;
        }}

        /* ==== أزرار (كلها ارتفاع 48px ونفس radius الإدخالات) ==== */
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
            background: {PRIMARY_ACTION};
            border: none;
            color: {WHITE};
            font-weight: 700;
            border-radius: var(--radius-input);
            min-height: 48px;
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
            min-height: 48px;
        }}
        [data-testid="stDownloadButton"] button {{
            background: {WHITE};
            color: var(--text-primary);
            border: 1px solid var(--border);
            border-radius: var(--radius-input);
            font-weight: 600;
            min-height: 48px;
            transition: border-color 180ms ease-in-out;
        }}
        [data-testid="stDownloadButton"] button:hover {{
            border-color: {PRIMARY_ACTION};
            color: {PRIMARY_ACTION};
        }}
        button:focus-visible, [role="button"]:focus-visible, input:focus-visible, textarea:focus-visible {{
            outline: 2px solid {PRIMARY_ACTION} !important;
            outline-offset: 2px;
        }}

        /* ==== منطقة رفع الملف ==== */
        [data-testid="stFileUploaderDropzone"] {{
            background: {WHITE};
            border: 2px dashed {PURPLE_200} !important;
            border-radius: 24px !important;
            padding: 10px !important;
        }}
        /* أيقونة الرفع داخل دائرة {PURPLE_50} */
        [data-testid="stFileUploaderDropzoneIcon"] {{
            background: {PURPLE_50} !important;
            border-radius: 50% !important;
            padding: 10px !important;
            display: inline-flex !important;
        }}
        [data-testid="stFileUploaderDropzone"] svg {{
            fill: {PRIMARY_ACTION} !important;
            color: {PRIMARY_ACTION} !important;
        }}
        /* نص تعليمات الرفع الأصلي "200MB per file • XLSX, CSV" (إنجليزي، من Streamlit نفسها)
        يُخفى بالكامل ونستبدله بنص عربي عبر ::after — نفس أسلوب زر "اختر ملف" أدناه بالضبط.
        تحقّقنا من بنية الـ DOM الفعلية عبر المتصفح: العنصر div واحد مباشر تحت
        stFileUploaderDropzoneInstructions يحوي span النص (لا يوجد svg هنا إطلاقًا). */
        [data-testid="stFileUploaderDropzoneInstructions"] * {{
            font-size: 0 !important;
        }}
        [data-testid="stFileUploaderDropzoneInstructions"] > div::after {{
            content: "اسحب الملف هنا أو اضغط اختر ملف";
            font-size: 0.85rem;
            color: {TEXT_MUTED};
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}
        /* زر الرفع: نص "Browse files" الأصلي يُخفى ونستبدله بـ"اختر ملف" عبر ::after */
        [data-testid="stFileUploaderDropzone"] button {{
            background-color: {PRIMARY_ACTION} !important;
            color: transparent !important;
            font-size: 0 !important;
            border: none !important;
            border-radius: 8px !important;
            position: relative;
        }}
        [data-testid="stFileUploaderDropzone"] button::after {{
            content: "اختر ملف";
            color: {WHITE} !important;
            font-size: 0.95rem;
            font-weight: 600;
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            white-space: nowrap;
        }}
        [data-testid="stFileUploaderDropzone"] button:hover {{
            filter: brightness(1.1);
        }}
        .maz-upload-hint {{
            color: {TEXT_MUTED};
            font-size: 0.9rem;
            margin-top: 6px;
        }}
        /* Chips صغيرة تحت منطقة الرفع (XLSX · CSV · حتى 200MB) */
        .maz-upload-chips {{ display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }}
        .maz-upload-chip {{
            background: {PURPLE_50};
            color: {PRIMARY_ACTION};
            font-size: 0.76rem;
            font-weight: 600;
            padding: 3px 12px;
            border-radius: 999px;
        }}
        .maz-upload-helper-line {{
            color: {TEXT_MUTED};
            font-size: 0.82rem;
            margin-top: 10px;
        }}

        /* ==== بطاقات المؤشرات (KPI) ==== */
        div[class*="st-key-maz_kpi_row_wrap"] [data-testid="stHorizontalBlock"] {{
            align-items: stretch;
            gap: 20px;
        }}
        div[class*="st-key-maz_kpi_row_wrap"] [data-testid="stColumn"] > div {{ height: 100%; }}
        div[class*="st-key-kpi_card_"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            overflow: hidden;
            padding: 16px 18px 12px 18px;
            min-height: 158px;
            height: 100%;
            box-sizing: border-box;
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
        /* الأيقونة على البطاقة المعبّأة: مربع شفاف أبيض خفيف بدل {ICON_TILE_BG} الفاتح
        (يتضارب بصريًا مع الخلفية البنفسجية المصمتة) — أبيض فقط، لا لون جديد. */
        div[class*="st-key-kpi_card_accent_"] .maz-kpi-icon-tile {{ background: rgba(255,255,255,0.22); }}
        div[class*="st-key-kpi_card_accent_"] .maz-kpi-icon-tile .material-symbols-outlined {{ color: {WHITE}; }}
        .maz-kpi-icon {{ font-size: 1.3rem; opacity: 0.9; }}
        .maz-kpi-icon-tile {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 20px;
            height: 20px;
            border-radius: 12px;
            background: {ICON_TILE_BG};
            vertical-align: middle;
            margin-inline-end: 2px;
        }}
        .maz-kpi-icon-tile .material-symbols-outlined {{ color: {ICON_TILE_COLOR}; font-size: 14px; }}
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
            background: {BADGE_SERVICED_DOT};
        }}

        /* ==== بطاقات الأبرز (Insight Cards) ==== */
        div[class*="st-key-maz_insights_row_wrap"] {{ margin-bottom: 20px; }}
        div[class*="st-key-maz_insights_row_wrap"] [data-testid="stHorizontalBlock"] {{ align-items: stretch; }}
        div[class*="st-key-maz_insights_row_wrap"] [data-testid="stColumn"] > div {{ height: 100%; }}
        .maz-insight-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            overflow: hidden;
            padding: 16px 18px;
            min-height: 150px;
            height: 100%;
            box-sizing: border-box;
        }}
        /* أيقونات موحّدة بالكامل (بدون تمييز لوني لكل بطاقة) — {ICON_TILE_COLOR} داخل مربع
        {ICON_TILE_BG} بزوايا 12px، حسب الطلب الصريح. */
        .maz-insight-icon-tile {{
            width: 36px;
            height: 36px;
            border-radius: 12px;
            background: {ICON_TILE_BG};
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            margin-bottom: 10px;
        }}
        .maz-insight-icon-tile .material-symbols-outlined {{ color: {ICON_TILE_COLOR}; font-size: 20px; }}
        .maz-insight-label {{ color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 4px; }}
        .maz-insight-value {{
            color: {TEXT_PRIMARY};
            font-weight: 700;
            font-size: 26px;
            line-height: 1.3;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}
        .maz-insight-value[dir="ltr"] {{
            unicode-bidi: isolate;
            text-align: right;
            white-space: nowrap;
            font-family: 'IBM Plex Sans Arabic', sans-serif;
        }}
        .maz-insight-meta {{ color: {TEXT_MUTED}; font-size: 14px; margin-top: 4px; }}
        .maz-reason-row {{ margin-top: 12px; }}
        .maz-reason-label-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }}
        .maz-reason-track {{ width: 100%; height: 6px; border-radius: 999px; background: {PURPLE_50}; overflow: hidden; }}
        .maz-reason-fill {{ height: 100%; border-radius: 999px; background: {PURPLE_400}; }}
        .maz-reason-fill-secondary {{ height: 100%; border-radius: 999px; background: {PURPLE_200}; }}
        .maz-reason-empty-line {{
            color: {TEXT_MUTED};
            font-size: 13px;
            margin-top: 12px;
            padding-top: 8px;
            border-top: 1px solid {STEP_CARD_BORDER};
        }}

        /* ==== نقطة الحالة بشارة "تمت الخدمة" ==== */
        .maz-status-dot {{
            display: inline-block;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: {BADGE_SERVICED_DOT};
            margin-inline-end: 5px;
        }}

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
        .maz-badge-danger {{ background: {DANGER_BG}; color: {DANGER}; }}

        /* ==== بانر خطأ (أحمر — مسموح فقط لرسائل الخطأ) ==== */
        div[class*="st-key-maz_card_error_banner"] {{
            background: {DANGER_BG} !important;
            border-color: #FCA5A5 !important;
        }}

        /* ==== مؤشر الخطوات (Step Indicator) — بطاقات بيضاء بحدود، الخطوة الحالية حدها بنفسجي ==== */
        .maz-step-indicator {{ display: flex; align-items: center; gap: 10px; margin-bottom: 18px; }}
        .maz-step {{
            display: flex; align-items: center; gap: 8px;
            background: {WHITE};
            border: 1px solid {STEP_CARD_BORDER};
            border-radius: 14px;
            padding: 10px 16px;
            flex: 1;
        }}
        .maz-step.maz-step-current {{ border-color: {MAZNEXA_PURPLE}; }}
        .maz-step-circle {{
            width: 28px; height: 28px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.8rem; font-weight: 700; color: {WHITE};
            background: {PRIMARY_ACTION};
            flex-shrink: 0;
        }}
        .maz-step-label {{ font-size: 0.85rem; color: {TEXT_MUTED}; }}
        .maz-step-label.maz-step-current, .maz-step-label.maz-step-done {{ color: var(--text-primary); font-weight: 600; }}
        .maz-step-connector {{ width: 20px; height: 2px; background: {STEP_CARD_BORDER}; flex-shrink: 0; }}

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
        /* ==== شريط فلاتر جدول Inbound Call — صف واحد موزّع، نفس الارتفاع، عناوين {TEXT_MUTED} ==== */
        div[class*="st-key-maz_card_inbound_filters"] [data-testid="stHorizontalBlock"] {{
            align-items: flex-end;
            gap: 14px;
        }}
        div[class*="st-key-maz_card_inbound_filters"] [data-testid="stWidgetLabel"] p,
        div[class*="st-key-maz_card_inbound_filters"] [data-testid="stWidgetLabel"] {{
            color: {TEXT_MUTED} !important;
        }}

        .maz-table-card, div[class*="st-key-maz_table_card_"] {{
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
            color: {PRIMARY_ACTION};
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
        table.maz-table tbody tr:nth-child(even) {{ background: {PURPLE_50}; }}
        table.maz-table tbody tr:hover {{ background: {GRADIENT_SOFT}, var(--surface); }}
        table.maz-table tbody td[dir="ltr"] {{ font-weight: 700; }}
        .maz-call-type {{ display: inline-flex; align-items: center; gap: 6px; }}
        .maz-call-type .material-symbols-outlined {{ color: {TEXT_MUTED}; font-size: 16px; }}

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
            .maz-page-header, div[class*="st-key-maz_page_header"] {{ flex-direction: column; align-items: flex-start; }}
            .maz-page-header h1, div[class*="st-key-maz_page_header"] h1 {{ font-size: 1.5rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

"""
قاموس ترجمة مركزي لنصوص واجهة Streamlit فقط (AR/EN).
لا يشمل: أسماء الأعمدة الفعلية بمصادر البيانات (Details, Show Room...) ولا قيم البيانات
نفسها (أسماء عملاء، شركات...) — هذي تبقى كما هي بمصدرها الأصلي دائمًا.
"""

TRANSLATIONS = {
    "page_title": {"ar": "نظام تحديد العملاء الأوفلاين — Maznexa", "en": "Offline Customer Identification System — Maznexa"},
    "header_title": {"ar": "نظام تحديد العملاء الأوفلاين", "en": "Offline Customer Identification System"},

    "tab_upload": {"ar": "📤 رفع الفواتير", "en": "📤 Upload Invoices"},
    "tab_dashboard": {"ar": "📊 لوحة التحكم", "en": "📊 Dashboard"},

    # تبويب رفع الفواتير
    "uploader_label": {"ar": "ارفع ملف الفواتير", "en": "Upload invoice file"},
    "upload_hint": {
        "ar": "اسحب ملف الفواتير هنا أو اضغط للاختيار (Excel أو CSV فقط) — "
              "ستبدأ المعالجة تلقائيًا فور الرفع، بدون أي زر إضافي.",
        "en": "Drag the invoice file here or click to browse (Excel or CSV only) — "
              "processing starts automatically on upload, no extra button needed.",
    },
    "preview_checkbox_label": {"ar": "🔍 وضع المعاينة (تجاهل سجل المعالجة السابقة)", "en": "🔍 Preview mode (ignore previous processing history)"},
    "preview_checkbox_help": {
        "ar": "يعالج كل السجلات بغض النظر عن قاعدة dedup، ولا يسجّل أي نتيجة بها إطلاقًا — للاختبار/الاستعراض فقط.",
        "en": "Processes all records regardless of the dedup database, and never writes any result to it — for testing/preview only.",
    },
    "preview_warning": {
        "ar": "⚠️ أنت بوضع المعاينة — هذي النتائج لن تُسجَّل كمعالجة، وقد تظهر نفس النتائج عند رفع هذا "
              "الملف مرة أخرى بالوضع الطبيعي لاحقًا.",
        "en": "⚠️ You are in preview mode — these results will not be recorded as processed, and the same "
              "results may reappear if you upload this file again later in normal mode.",
    },
    "spinner_processing": {
        "ar": "جاري القراءة، الاتصال بـ Google Sheets، وتطبيق شروط المطابقة...",
        "en": "Reading the file, connecting to Google Sheets, and applying matching rules...",
    },
    "error_sheets_connection": {"ar": "❌ فشل الاتصال بـ Google Sheets:", "en": "❌ Failed to connect to Google Sheets:"},
    "error_processing": {"ar": "❌ حدث خطأ أثناء المعالجة:", "en": "❌ An error occurred during processing:"},
    "error_dashboard_load": {"ar": "❌ حدث خطأ أثناء تحميل بيانات لوحة التحكم:", "en": "❌ An error occurred while loading dashboard data:"},
    "success_processed": {"ar": "✅ تمت المعالجة بنجاح", "en": "✅ Processed successfully"},

    "metric_valid_numbers": {"ar": "أرقام صالحة بالفاتورة", "en": "Valid numbers in invoice"},
    "metric_offline": {"ar": "مصنّفة كأوفلاين", "en": "Classified offline"},
    "metric_excluded": {"ar": "مستبعدة", "en": "Excluded"},
    "metric_invalid": {"ar": "أرقام غير صالحة", "en": "Invalid numbers"},

    "expander_summary": {"ar": "عرض تفاصيل الملخص الكاملة (تفصيل أسباب الاستبعاد)", "en": "View full summary details (exclusion reason breakdown)"},
    "summary_col_metric": {"ar": "المؤشر", "en": "Metric"},
    "summary_col_value": {"ar": "القيمة", "en": "Value"},

    "subheader_offline_customers": {"ar": "العملاء الأوفلاين", "en": "Offline Customers"},
    "warning_no_offline": {
        "ar": "لا يوجد أي عميل مطابق لشروط 'أوفلاين' بهذا التشغيل.",
        "en": "No customer matched the 'offline' criteria in this run.",
    },
    "search_label": {"ar": "🔍 بحث بأي عمود (اسم، رقم، براند...)", "en": "🔍 Search any column (name, number, brand...)"},
    "sort_by_label": {"ar": "ترتيب حسب", "en": "Sort by"},
    "sort_direction_label": {"ar": "الاتجاه", "en": "Direction"},
    "sort_asc": {"ar": "تصاعدي", "en": "Ascending"},
    "sort_desc": {"ar": "تنازلي", "en": "Descending"},

    "subheader_downloads": {"ar": "تحميل ملفات المخرجات", "en": "Download Output Files"},
    "download_offline_label": {"ar": "📥 ملف العملاء الأوفلاين", "en": "📥 Offline Customers File"},
    "download_excluded_label": {"ar": "📥 ملف الاستبعادات", "en": "📥 Exclusions File"},
    "download_invalid_label": {"ar": "📥 ملف الأرقام غير الصالحة", "en": "📥 Invalid Numbers File"},
    "download_summary_label": {"ar": "📥 ملف الملخص", "en": "📥 Summary File"},

    # لوحة التحكم
    "filter_brand_label": {"ar": "🏢 فلتر اسم الشركة/البراند", "en": "🏢 Company/Brand filter"},
    "filter_date_range_label": {"ar": "📅 نطاق التاريخ (من - إلى)", "en": "📅 Date range (from - to)"},
    "metric_offline_filtered": {"ar": "عدد العملاء الأوفلاين (بالنطاق المحدد)", "en": "Offline customers (in selected range)"},
    "metric_total_sales": {"ar": "إجمالي المبيعات (بالنطاق المحدد)", "en": "Total Sales (in selected range)"},
    "currency_default": {"ar": "ر.س", "en": "SAR"},
    "info_no_offline_filtered": {
        "ar": "لا توجد بيانات أوفلاين ضمن الفلاتر المحددة.",
        "en": "No offline data within the selected filters.",
    },
    "info_no_sales_data": {"ar": "لا توجد بيانات بتبويب Sales Data حاليًا.", "en": "No data currently available in the Sales Data tab."},

    "subheader_brand_chart": {"ar": "عدد العملاء الأوفلاين حسب الشركة/البراند", "en": "Offline Customers by Company/Brand"},
    "chart_axis_brand": {"ar": "الشركة/البراند", "en": "Company/Brand"},
    "chart_axis_count": {"ar": "عدد العملاء الأوفلاين", "en": "Offline Customers"},
    "legend_title_brand": {"ar": "البراند", "en": "Brand"},
    "tooltip_company": {"ar": "الشركة", "en": "Company"},

    "subheader_monthly_chart": {"ar": "عدد العملاء الأوفلاين شهريًا", "en": "Offline Customers by Month"},
    "chart_axis_month": {"ar": "الشهر", "en": "Month"},

    "footer_text": {"ar": "منصّة Maznexa الداخلية", "en": "Maznexa Internal Platform"},
    "spinner_dashboard_loading": {
        "ar": "جاري تحميل بيانات Sales Data (يُحدَّث تلقائيًا كل ساعة)...",
        "en": "Loading Sales Data (auto-refreshes hourly)...",
    },

    "lang_toggle_label": {"ar": "اللغة", "en": "Language"},

    # ==== عام (فارغ/خطأ/تصدير بيانات الرسوم) ====
    "filter_all_option": {"ar": "الكل", "en": "All"},
    "empty_chart_no_data": {"ar": "لا توجد بيانات لعرضها بهذا الرسم ضمن الفلاتر الحالية.", "en": "No data to display for this chart with the current filters."},
    "empty_no_data_matches_filters": {"ar": "لا توجد بيانات تطابق الفلاتر المحددة.", "en": "No data matches the selected filters."},
    "empty_no_runs_yet": {"ar": "لا توجد أي عملية معالجة سابقة بعد.", "en": "No processing runs yet."},
    "error_chart_render": {"ar": "❌ تعذّر عرض هذا الرسم:", "en": "❌ Could not render this chart:"},
    "expander_view_data": {"ar": "📄 عرض بيانات الرسم", "en": "📄 View chart data"},
    "download_chart_data_label": {"ar": "⬇️ تنزيل بيانات الرسم (CSV)", "en": "⬇️ Download chart data (CSV)"},

    # ==== محاور/تسميات الرسوم الإضافية ====
    "chart_axis_sales": {"ar": "إجمالي المبيعات (ر.س)", "en": "Total Sales (SAR)"},
    "chart_axis_quarter": {"ar": "الربع السنوي", "en": "Quarter"},
    "chart_axis_year": {"ar": "السنة", "en": "Year"},
    "chart_axis_pct": {"ar": "النسبة من الإجمالي (%)", "en": "% of Total"},

    # ==== الشريط العلوي للصفحات ====
    "dashboard_last_updated_label": {"ar": "آخر تحديث للبيانات", "en": "Data last updated"},
    "dashboard_refresh_button": {"ar": "🔄 تحديث البيانات", "en": "🔄 Refresh data"},
    "dashboard_title": {"ar": "لوحة التحكم", "en": "Dashboard"},
    "dashboard_subtitle": {"ar": "ملخص شامل لأداء المبيعات والعملاء الأوفلاين حسب الفلاتر المحددة", "en": "A full summary of sales performance and offline customers based on the selected filters"},
    "upload_title": {"ar": "رفع ملف الأوفلاين", "en": "Upload Offline File"},
    "upload_subtitle": {"ar": "ارفع ملف فواتير المبيعات لاستخراج العملاء الأوفلاين تلقائيًا", "en": "Upload a sales invoice file to automatically extract offline customers"},

    # ==== شريط الفلاتر ====
    "filters_card_title": {"ar": "🔎 فلاتر لوحة التحكم", "en": "🔎 Dashboard Filters"},
    "filter_year_label": {"ar": "📆 السنة", "en": "📆 Year"},
    "filter_quarter_label": {"ar": "الربع السنوي", "en": "Quarter"},
    "filter_month_label": {"ar": "الشهر", "en": "Month"},
    "filter_apply_button": {"ar": "✅ تطبيق الفلاتر", "en": "✅ Apply Filters"},
    "filter_reset_button": {"ar": "↺ إعادة ضبط", "en": "↺ Reset"},
    "filter_brand_edit_button": {"ar": "تغيير", "en": "Change"},
    "quick_range_label": {"ar": "اختيار سريع للفترة:", "en": "Quick range:"},
    "quick_range_today": {"ar": "اليوم", "en": "Today"},
    "quick_range_yesterday": {"ar": "أمس", "en": "Yesterday"},
    "quick_range_last_7": {"ar": "آخر 7 أيام", "en": "Last 7 days"},
    "quick_range_last_30": {"ar": "آخر 30 يوم", "en": "Last 30 days"},
    "quick_range_this_month": {"ar": "هذا الشهر", "en": "This month"},
    "month_1": {"ar": "يناير", "en": "January"},
    "month_2": {"ar": "فبراير", "en": "February"},
    "month_3": {"ar": "مارس", "en": "March"},
    "month_4": {"ar": "أبريل", "en": "April"},
    "month_5": {"ar": "مايو", "en": "May"},
    "month_6": {"ar": "يونيو", "en": "June"},
    "month_7": {"ar": "يوليو", "en": "July"},
    "month_8": {"ar": "أغسطس", "en": "August"},
    "month_9": {"ar": "سبتمبر", "en": "September"},
    "month_10": {"ar": "أكتوبر", "en": "October"},
    "month_11": {"ar": "نوفمبر", "en": "November"},
    "month_12": {"ar": "ديسمبر", "en": "December"},

    # ==== بطاقات KPI بلوحة التحكم ====
    "kpi_total_sales": {"ar": "إجمالي المبيعات", "en": "Total Sales"},
    "kpi_total_sales_tooltip": {"ar": "مجموع قيمة المبيعات للسجلات المصنّفة Offline فقط (نفس نطاق 'عدد العملاء الأوفلاين' بالضبط) — لا يشمل مبيعات Online.", "en": "Sum of sales value for records flagged Offline only (the exact same scope as 'Total Offline Customers') — Online sales are not included."},
    "kpi_total_offline": {"ar": "إجمالي العملاء الأوفلاين", "en": "Total Offline Customers"},
    "kpi_total_offline_tooltip": {"ar": "عدد صفوف تبويب Sales Data المُعلَّمة Offline ضمن الفلاتر المحددة.", "en": "Number of Sales Data rows flagged Offline within the selected filters."},

    # ==== عناوين ووصف الرسوم البيانية ====
    "chart_title_sales_offline_combo": {"ar": "المبيعات وعدد العملاء الأوفلاين حسب الشركة", "en": "Sales & Offline Customers by Company"},
    "chart_desc_sales_offline_combo": {"ar": "مقارنة إجمالي المبيعات (المحور الأيسر) مع عدد العملاء الأوفلاين (المحور الأيمن) لكل شركة.", "en": "Comparing total sales (left axis) with offline customer count (right axis) per company."},
    "chart_title_quarterly_sales": {"ar": "المبيعات حسب الربع السنوي", "en": "Sales by Quarter"},
    "chart_desc_quarterly_sales": {"ar": "توزيع مبيعات العملاء الأوفلاين للسنة المحددة على الأرباع الأربعة.", "en": "Distribution of offline-customer sales across the four quarters of the selected year."},
    "chart_title_annual_sales": {"ar": "المبيعات السنوية", "en": "Annual Sales"},
    "chart_desc_annual_sales": {"ar": "إجمالي مبيعات العملاء الأوفلاين لكل سنة تتوفر لها بيانات فعليًا.", "en": "Total offline-customer sales for each year with actual data."},
    "chart_title_offline_donut": {"ar": "توزيع العملاء الأوفلاين", "en": "Offline Customers Distribution"},
    "chart_desc_offline_donut": {"ar": "نسبة كل شركة من إجمالي العملاء الأوفلاين.", "en": "Each company's share of total offline customers."},

    # ==== آخر عمليات المعالجة ====
    "last_runs_title": {"ar": "آخر عمليات المعالجة", "en": "Last Processing Runs"},
    "last_runs_subtitle": {"ar": "مبنية من ملفات الملخص المحفوظة بمجلد output — بدون اسم الملف الأصلي أو المستخدم (غير محفوظين حاليًا).", "en": "Built from the summary files saved in the output folder — original filename and username are not shown (not currently stored)."},
    "last_runs_col_time": {"ar": "وقت التشغيل", "en": "Run Time"},

    # ==== جدول العملاء الأوفلاين ====
    "table_filter_brand": {"ar": "فلتر الشركة", "en": "Company filter"},
    "table_filter_agent": {"ar": "فلتر الموظف", "en": "Agent filter"},
    "table_filter_date": {"ar": "فلتر تاريخ الفاتورة", "en": "Invoice date filter"},
    "table_page_size_label": {"ar": "عدد الصفوف بالصفحة", "en": "Rows per page"},
    "table_prev_page": {"ar": "◀ السابق", "en": "◀ Previous"},
    "table_next_page": {"ar": "التالي ▶", "en": "Next ▶"},
    "table_page_caption": {"ar": "صفحة {current} من {total}", "en": "Page {current} of {total}"},
    "table_export_button": {"ar": "⬇️ تصدير النتائج المعروضة (CSV)", "en": "⬇️ Export displayed results (CSV)"},

    # ==== تفاصيل أسباب الاستبعاد (صفحة الرفع) ====
    "expander_exclusion_breakdown": {"ar": "📊 تفاصيل أسباب الاستبعاد", "en": "📊 Exclusion Reason Breakdown"},
    "exclusion_chart_axis_reason": {"ar": "سبب الاستبعاد", "en": "Exclusion Reason"},
    "exclusion_table_col_reason": {"ar": "سبب الاستبعاد", "en": "Exclusion Reason"},
    "exclusion_table_col_count": {"ar": "العدد", "en": "Count"},

    # ==== صفحة Inbound Call (باوند كول) ====
    "inbound_call_title": {"ar": "ان باوند كول", "en": "Inbound Call"},
    "inbound_call_subtitle": {
        "ar": "ارفع تصدير المكالمات اليومي من Maqsam لاستخراج اسم العميل والاستفسار تلقائيًا بالذكاء الاصطناعي",
        "en": "Upload the daily Maqsam call export to automatically extract customer name and inquiry with AI",
    },
    "inbound_uploader_label": {"ar": "ارفع ملف تصدير Maqsam (Call Exports)", "en": "Upload Maqsam export file (Call Exports)"},
    "inbound_upload_hint": {
        "ar": "ارفع تصدير يوم واحد فقط (Excel أو CSV) — تُعالَج المكالمات الواردة (Inbound) فقط حاليًا، "
              "وتبدأ المعالجة تلقائيًا فور الرفع.",
        "en": "Upload a single day's export (Excel or CSV) — only Inbound calls are processed for now, "
              "processing starts automatically on upload.",
    },
    "inbound_spinner_processing": {
        "ar": "جاري قراءة الملف واستخراج تفاصيل المكالمات بالذكاء الاصطناعي...",
        "en": "Reading the file and extracting call details with AI...",
    },
    "inbound_error_processing": {"ar": "حدث خطأ أثناء معالجة ملف المكالمات:", "en": "An error occurred while processing the calls file:"},
    "inbound_success_processed": {"ar": "تمت المعالجة بنجاح", "en": "Processed successfully"},
    "inbound_warning_no_rows": {"ar": "لا توجد أي مكالمات Inbound بهذا الملف.", "en": "No Inbound calls found in this file."},

    "inbound_metric_total": {"ar": "إجمالي المكالمات", "en": "Total calls"},
    "inbound_metric_with_details": {"ar": "صفوف فيها تفاصيل مستخرجة", "en": "Rows with extracted details"},
    "inbound_metric_review": {"ar": "تحتاج مراجعة يدوية", "en": "Need manual review"},
    "inbound_metric_brands": {"ar": "براندات تم حلّها", "en": "Brands resolved"},
    "inbound_metric_complaints": {"ar": "شكاوى وزارة التجارة المحتملة", "en": "Possible Ministry of Commerce complaints"},

    "inbound_subheader_results": {"ar": "نتائج الاستخراج", "en": "Extraction Results"},
    "inbound_expander_review": {"ar": "صفوف تحتاج مراجعة يدوية", "en": "Rows needing manual review"},
    "inbound_review_col_id": {"ar": "رقم المكالمة", "en": "Call ID"},
    "inbound_review_col_number": {"ar": "الرقم", "en": "Number"},
    "inbound_review_col_reason": {"ar": "سبب المراجعة", "en": "Review Reason"},
    "inbound_review_col_summary": {"ar": "ملخص المكالمة (مختصر)", "en": "Call Summary (excerpt)"},

    "inbound_download_label": {"ar": "تحميل ملف المكالمات (جاهز للصق بشيت المزروع)", "en": "Download calls file (ready to paste into Almazro sheet)"},

    # ==== عناوين فرعية (Eyebrows) فوق عنوان كل صفحة ====
    "eyebrow_dashboard": {"ar": "لوحة التحكم", "en": "Dashboard"},
    "eyebrow_upload": {"ar": "رفع ملف الأوفلاين", "en": "Upload Offline File"},
    "eyebrow_inbound": {"ar": "ان باوند كول", "en": "Inbound Call"},

    # ==== مؤشر خطوات صفحة الرفع ====
    "step_upload_label": {"ar": "رفع الملف", "en": "Upload file"},
    "step_validate_label": {"ar": "التحقق", "en": "Validation"},
    "step_extract_label": {"ar": "الاستخراج", "en": "Extraction"},
    "upload_dropzone_types_hint": {"ar": "يقبل Excel أو CSV فقط، بحد أقصى 200 ميجابايت", "en": "Accepts Excel or CSV only, up to 200MB"},
    "upload_preview_title": {"ar": "معاينة أول 10 صفوف", "en": "Preview of first 10 rows"},
    "upload_preview_row_count": {"ar": "إجمالي عدد الصفوف بالملف: {count}", "en": "Total rows in file: {count}"},
    "upload_error_banner_title": {"ar": "⚠️ صفوف تعذّر تفكيكها بالملف", "en": "⚠️ Rows that could not be parsed"},
    "upload_cta_view_results": {"ar": "عرض نتائج الاستخراج ←", "en": "View extraction results →"},

    # ==== صفحة Inbound Call — القشرة الجديدة ====
    "inbound_subtitle_with_date": {"ar": "سجل المكالمات الواردة · {date}", "en": "Inbound call log · {date}"},
    "inbound_download_csv_label": {"ar": "تحميل CSV", "en": "Download CSV"},
    "inbound_kpi_serviced": {"ar": "تمت الخدمة", "en": "Serviced"},
    "inbound_kpi_total_sub": {"ar": "كلها واردة", "en": "All inbound"},
    "inbound_kpi_repeat_callers": {"ar": "أرقام اتصلت أكثر من مرة", "en": "Numbers that called more than once"},
    "inbound_kpi_repeat_callers_sub": {"ar": "عملاء رجعوا يتصلون", "en": "Customers who called back"},
    "inbound_kpi_repeat_callers_zero": {"ar": "ما فيه أرقام مكررة", "en": "No repeated numbers"},
    "inbound_kpi_unclassified": {"ar": "مكالمات بدون تصنيف", "en": "Unclassified calls"},
    "inbound_kpi_unclassified_sub": {"ar": "{pct}% من المكالمات ما انكتب لها سبب", "en": "{pct}% of calls have no recorded reason"},

    # ==== بحث/فلتر الشركة بالهيدر ====
    "inbound_header_search_label": {"ar": "بحث برقم الجوال", "en": "Search by phone number"},
    "inbound_header_search_placeholder": {"ar": "مثال: 0505749725", "en": "e.g. 0505749725"},
    "inbound_header_company_label": {"ar": "الشركة", "en": "Company"},
    "inbound_company_multiselect_label": {"ar": "الشركات", "en": "Companies"},
    "inbound_company_multiselect_placeholder": {"ar": "اختر شركة", "en": "Select a company"},
    "inbound_filter_all_companies": {"ar": "كل الشركات", "en": "All companies"},
    "inbound_phone_banner_found": {
        "ar": "هذا الرقم اتصل {count} مرات · آخر اتصال: {date} · الشركة: {company}",
        "en": "This number called {count} times · Last call: {date} · Company: {company}",
    },
    "inbound_phone_banner_not_found": {"ar": "ما فيه مكالمات من هذا الرقم", "en": "No calls from this number"},
    "inbound_insight_company_share": {"ar": "حصة الشركة", "en": "Company share"},
    "inbound_show_all_companies": {"ar": "عرض الكل ({count})", "en": "Show all ({count})"},
    "inbound_show_less_companies": {"ar": "عرض أقل", "en": "Show less"},

    # ==== منطقة الرفع المحسّنة (كل الصفحات) ====
    "upload_drag_here": {"ar": "اسحب الملف هنا", "en": "Drag file here"},
    "upload_chip_xlsx": {"ar": "XLSX", "en": "XLSX"},
    "upload_chip_csv": {"ar": "CSV", "en": "CSV"},
    "upload_chip_maxsize": {"ar": "حتى 200MB", "en": "Up to 200MB"},
    "upload_auto_process_helper": {
        "ar": "المعالجة تبدأ تلقائيًا بعد الرفع — ما تحتاج تضغط أي زر إضافي.",
        "en": "Processing starts automatically after upload — no extra button needed.",
    },
    "upload_preview_toggle_help": {
        "ar": "يعالج كل السجلات بغض النظر عن قاعدة dedup، ولا يسجّل أي نتيجة بها إطلاقًا — للاختبار/الاستعراض فقط.",
        "en": "Processes all records regardless of the dedup database, and never writes any result to it — for testing/preview only.",
    },

    # ==== مؤشر خطوات Inbound Call ====
    "inbound_step_upload_label": {"ar": "رفع الملف", "en": "Upload file"},
    "inbound_step_process_label": {"ar": "معالجة تلقائية", "en": "Auto processing"},
    "inbound_step_results_label": {"ar": "النتائج", "en": "Results"},

    "inbound_insights_title": {"ar": "أبرز المؤشرات", "en": "Top Insights"},
    "inbound_insight_top_company": {"ar": "المكالمات حسب الشركة", "en": "Calls by Company"},
    "inbound_insight_top_reason": {"ar": "أكثر سبب اتصال", "en": "Top contact reason"},
    "inbound_insight_top_number": {"ar": "أكثر رقم اتصل", "en": "Top caller"},
    "inbound_select_company_top": {"ar": "أكثر شركة", "en": "Top company"},
    "inbound_select_reason_top": {"ar": "أكثر استفسار", "en": "Top inquiry"},
    "inbound_select_reason_bottom": {"ar": "أقل استفسار", "en": "Least inquiry"},
    "inbound_select_reason_all": {"ar": "كل الاستفسارات", "en": "All inquiries"},
    "inbound_number_option_format": {"ar": "{number} ({count} مرات)", "en": "{number} ({count} times)"},
    "inbound_unmatched_values_warning": {
        "ar": "قيم غير موجودة في القوائم: {items}",
        "en": "Values not found in the dropdown lists: {items}",
    },
    "inbound_last_call_label": {"ar": "آخر اتصال:", "en": "Last call:"},
    "inbound_insight_company_label": {"ar": "الشركة:", "en": "Company:"},
    "inbound_insight_reason_label": {"ar": "السبب:", "en": "Reason:"},
    "inbound_insight_no_reason": {"ar": "{count} مكالمة بدون سبب مسجَّل", "en": "{count} calls with no recorded reason"},
    "inbound_insight_of_total": {"ar": "{pct}% من الإجمالي", "en": "{pct}% of total"},
    "inbound_insight_of_company_total": {"ar": "{pct}% من مكالمات الشركة", "en": "{pct}% of the company's calls"},
    "inbound_insight_of_named_company_total": {"ar": "{pct}% من مكالمات {company}", "en": "{pct}% of {company}'s calls"},
    "inbound_insight_times": {"ar": "×{count} مرة", "en": "×{count} times"},
    "inbound_insight_empty": {"ar": "لا توجد بيانات كافية", "en": "Not enough data"},
    "inbound_insight_calls_reason": {"ar": "مكالمات اليوم، السبب: {reason}", "en": "Today's calls, reason: {reason}"},
    "inbound_insight_call_count": {"ar": "{count} مكالمة", "en": "{count} calls"},
    "inbound_insight_called_times": {"ar": "اتصل {count} مرات", "en": "Called {count} times"},
    "inbound_called_once": {"ar": "اتصل مرة وحدة", "en": "Called once"},
    "inbound_called_twice": {"ar": "اتصل مرتين", "en": "Called twice"},
    "inbound_call_direction_inbound": {"ar": "واردة", "en": "Inbound"},

    "inbound_table_date_range_label": {"ar": "نطاق التاريخ", "en": "Date range"},
    "inbound_table_details_label": {"ar": "التفاصيل", "en": "Details"},
    "inbound_table_group_toggle": {"ar": "دمج الأرقام المكررة", "en": "Merge duplicate numbers"},
    "inbound_table_showing": {"ar": "عرض {shown} من {total}", "en": "Showing {shown} of {total}"},
    "inbound_table_hidden_columns": {"ar": "{count} أعمدة فاضية مخفية ({cols})", "en": "{count} empty columns hidden ({cols})"},
    "inbound_table_show_all": {"ar": "إظهار الكل", "en": "Show all"},
    "inbound_table_col_date": {"ar": "التاريخ", "en": "Date"},
    "inbound_table_col_number": {"ar": "رقم الجوال", "en": "Phone Number"},
    "inbound_table_col_company": {"ar": "الشركة", "en": "Company"},
    "inbound_table_col_type": {"ar": "نوع المكالمة", "en": "Call Type"},
    "inbound_table_col_status": {"ar": "حالة المكالمة", "en": "Call Status"},
    "inbound_table_col_details": {"ar": "التفاصيل", "en": "Details"},
    "inbound_table_col_notes": {"ar": "الملاحظات", "en": "Notes"},
    "inbound_table_col_count": {"ar": "عدد المكالمات", "en": "Call Count"},
    "inbound_table_no_results": {"ar": "لا توجد مكالمات تطابق الفلاتر المحددة.", "en": "No calls match the selected filters."},
    "inbound_table_page_caption": {"ar": "صفحة {current} من {total}", "en": "Page {current} of {total}"},
}


def t(key: str, lang: str) -> str:
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("ar", key))


# ترجمة مفاتيح ملخص pipeline.py الديناميكية — للعرض فقط، لا تغيّر أي شيء بـ pipeline.py نفسه.
SUMMARY_LABELS_EN = {
    "إجمالي صفوف ملف الفواتير": "Total invoice file rows",
    "إجمالي أرقام صالحة بالفاتورة (بعد التطبيع)": "Total valid numbers (after normalization)",
    "تم تجاهلها لأنها معالجة مسبقًا (dedup)": "Skipped as already processed (dedup)",
    "صفوف جديدة فعليًا بهذا التشغيل": "Actually new rows this run",
    "مصنّفة كأوفلاين": "Classified offline",
    "مستبعدة (إجمالي)": "Excluded (total)",
    "أرقام غير صالحة/مشبوهة (فاتورة + شيت)": "Invalid/suspicious numbers (invoice + sheet)",
    "سجلات تواصل بشيت المزروع بدون رقم جوال مسجَّل أصلًا (معلومة فقط)": "Sheet contact records with no phone number at all (info only)",
    "  -> استبعاد: فاتورة بتاريخ اليوم (لم تُعالج بعد)": "  -> Excluded: Invoice dated today (not yet processed)",
    "  -> استبعاد: تواصل بتاريخ اليوم (لم يُعتمد بعد)": "  -> Excluded: Contact dated today (not yet finalized)",
    "  -> استبعاد: بيع عبر E-Commerce": "  -> Excluded: E-Commerce sale",
    "  -> استبعاد: الرقم غير موجود بشيت المزروع": "  -> Excluded: Number not found in Almazro sheet",
    "  -> استبعاد: مستبعد بسبب Details": "  -> Excluded: Details value",
    "  -> استبعاد: مستبعد بسبب Outbound (اتصال صادر)": "  -> Excluded: Outbound call",
    "  -> استبعاد: عدم تطابق الشهر/السنة": "  -> Excluded: Month/year mismatch",
    "  -> استبعاد: لم يُحدد البراند من Show Room": "  -> Excluded: Brand not determined from Show Room",
    "  -> استبعاد: عدم تطابق البراند/company": "  -> Excluded: Brand/company mismatch",
    "  -> استبعاد: أسباب أخرى": "  -> Excluded: Other reasons",
}


def translate_summary_label(label: str, lang: str) -> str:
    if lang == "ar":
        return label
    return SUMMARY_LABELS_EN.get(label, label)


# ترجمة عناوين جدول العملاء الأوفلاين المعروض بالشاشة فقط (ملفات التحميل Excel تبقى بأسمائها الأصلية)
OFFLINE_TABLE_COLUMNS_EN = {
    "رقم الجوال": "Phone Number",
    "اسم العميل": "Customer Name",
    "تاريخ الفاتورة": "Invoice Date",
    "تاريخ التواصل بشيت المزروع": "Contact Date (Sheet)",
    "سبب التواصل (Details)": "Contact Reason (Details)",
    "اسم الموظفة (Agent)": "Agent Name",
    "عدد فواتير هذا الرقم": "Invoice Count",
    "الحالة": "Status",
}


def translate_offline_columns(columns, lang: str):
    if lang == "ar":
        return list(columns)
    return [OFFLINE_TABLE_COLUMNS_EN.get(c, c) for c in columns]

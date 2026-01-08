import streamlit as st
import pandas as pd
import datetime
import io
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import pytz
import dropbox  # ✅ أضفنا الـ import

# ---------- Dropbox Setup ----------
def upload_to_dropbox_silent(file_content, filename):
    """Upload file to Dropbox silently in background using Refresh Token"""
    try:
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=st.secrets["dropbox"]["refresh_token"],
            app_key=st.secrets["dropbox"]["app_key"],
            app_secret=st.secrets["dropbox"]["app_secret"]
        )
        
        # رفع الملف في مجلد KHOSOMAAT
        dbx.files_upload(
            file_content, 
            f"/KHOSOMAAT/{filename}", 
            mode=dropbox.files.WriteMode.overwrite
        )
        return True
    except Exception as e:
        return False

# ---------- Arabic helpers ----------
def fix_arabic(text):
    if pd.isna(text):
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def fill_down(series):
    return series.ffill()


def replace_muaaqal_with_confirm_safe(df):
    return df.replace('معلق', 'تم التأكيد')


# ---------- City classifier ----------
def classify_city(city):
    if pd.isna(city) or str(city).strip() == '':
        return "Other City"

    city = str(city).strip()

    city_map = {
        "منطقة صباح السالم": {"صباح السالم","العدان","المسيلة","أبو فطيرة","أبو الحصانية","مبارك الكبير",
                              "القصور","القرين","الفنيطيس","المسايل"},
        "منطقة المهبولة": {"الفنطاس","المهبولة"},
        "منطقة الفحيحيل": {"الفحيحيل الصناعية","أبو حليفة","المنقف","الفحيحيل"},
        "منطقة جابر الاحمد": {"مدينة جابر الأحمد","شمال غرب الصليبيخات","الرحاب","صباح الناصر",
                              "الفردوس","الأندلس","النهضة","غرناطة","الدوحة",
                              "جنوب الدوحة / القيروان","القيروان"},
        "منطقة العارضية": {"العارضية حرفية","العارضية","العارضية المنطقة الصناعية",
                            "الصليبخات","الري","اشبيلية","الرقعي"},
        "منطقة سلوي": {"مبارك العبدالله غرب مشرف","سلوى","بيان","الرميثية","مشرف"},
        "منطقة السالمية": {"السالمية","ميدان حولي","البدع"},
        "منطقة الجهراء": {"الجهراء","الصلبية الصناعية","الصليبية الصناعية","مزارع الصليبية",
                          "الصليبية السكنية","مدينة سعد العبد الله","الصليبية","أمغرة","سكراب امغرة",
                          "جنوب امغرة","القصر","النعيم","معسكرات الجهراء","تيماء","النسيم",
                          "الجهراء المنطقة الصناعية","جواخير الجهراء","العيون","الواحة",
                          "اسطبلات الجهراء","مزارع الطليبية"},
        "منطقة خيطان": {"خيطان"},
        "منطقة الفروانية": {"الفروانية"},
        "منطقه الصباحية": {"اسواق القرين","الظهر","جابر العلي","العقيلة","الرقة","المقوع",
                           "فهد الأحمد","الصباحية","هدية","الجليعه","علي صباح السالم"},
        "منطقة صباح الاحمد": {"صباح الأحمد3","الجليعة","صباح الأحمد","مدينة صباح الأحمد",
                             "ميناء عبد الله","بنيدر","الوفرة","الخيران","الزور","النويصب",
                             "شمال الأحمدي","جنوب الأحمدي","شرق الأحمدي","وسط الأحمدي",
                             "الأحمدي","غرب الأحمدي","ام الهيمان","الشعيبة"},
        "منطقة حولي": {"حولي"},
        "منطقة الجابرية": {"الجابرية","قرطبة","اليرموك","السرة"},
        "منطقة العاصمة": {"حدائق السور","دسمان","القبلة","المرقاب","مدينة الكويت","المباركية","شرق‎"},
        "منطقة الشويخ": {"الشويخ الصناعية","الشويخ","الشويخ السكنية","ميناء الشويخ"},
        "منطقة الشعب": {"ضاحية عبد الله السالم","الدعية","القادسية","النزهة","الفيحاء","كيفان",
                        "الشعب","الروضة","الخالدية","العديلية","الدسمة","الشامية","المنصورية","بنيد القار"},
        
        "منطقة عبدالله المبارك": {"الشدادية","غرب عبدالله المبارك","عبدالله المبارك",
        "كبد","الرحاب","الضجيج","الافينيوز","عبدالله مبارك الصباح"},
        
        "منطقة جنوب السرة": {"السلام",
                                 "العمرية","منطقة المطار","حطين","الشهداء","صبحان","الزهراء",
                                 "الصديق","الرابية","جنوب السرة",},

        
        "جليب الشيوخ": {"جليب الشيوخ","العباسية","شارع محمد بن القاسم","الحساوي"},
        "المطلاع": {"المطلاع","العبدلي","السكراب"},
    }

    for area, cities in city_map.items():
        if city in cities:
            return area

    return "Other City"


# ---------- PDF table builder ----------
def df_to_pdf_table(df, title="KHOSOMAAT"):
    if "اجمالي عدد القطع في الطلب" in df.columns:
        df = df.rename(columns={"اجمالي عدد القطع في الطلب": "عدد القطع"})

    final_cols = [
        'كود الاوردر', 'اسم العميل', 'المنطقة', 'العنوان',
        'المدينة', 'رقم موبايل العميل', 'حالة الاوردر',
        'عدد القطع', 'الملاحظات', 'اسم الصنف',
        'اللون', 'المقاس', 'الكمية', 'الإجمالي مع الشحن'
    ]

    df = df[[c for c in final_cols if c in df.columns]].copy()

    if 'رقم موبايل العميل' in df.columns:
        df['رقم موبايل العميل'] = df['رقم موبايل العميل'].apply(
            lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.', '', 1).isdigit()
            else ("" if pd.isna(x) else str(x))
        )

    safe_cols = {
        'الإجمالي مع الشحن', 'كود الاوردر', 'رقم موبايل العميل', 'اسم العميل',
        'المنطقة', 'العنوان', 'المدينة', 'حالة الاوردر', 'الملاحظات',
        'اسم الصنف', 'اللون', 'المقاس'
    }

    for col in df.columns:
        if col not in safe_cols:
            df[col] = df[col].apply(
                lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.', '', 1).isdigit()
                else ("" if pd.isna(x) else str(x))
            )

    styleN = ParagraphStyle(name='Normal', fontName='Arabic-Bold', fontSize=9, alignment=1, wordWrap='RTL')
    styleBH = ParagraphStyle(name='Header', fontName='Arabic-Bold', fontSize=10, alignment=1, wordWrap='RTL')
    styleTitle = ParagraphStyle(name='Title', fontName='Arabic-Bold', fontSize=14, alignment=1, wordWrap='RTL')

    data = []
    data.append([Paragraph(fix_arabic(col), styleBH) for col in df.columns])

    for _, row in df.iterrows():
        data.append([
            Paragraph(fix_arabic("" if pd.isna(row[col]) else str(row[col])), styleN)
            for col in df.columns
        ])

    col_widths_cm = [2, 2, 1.5, 3, 2, 3, 1.5, 1.5, 2.5, 3.5, 1.5, 1.5, 1, 1.5]
    col_widths = [max(c * 28.35, 15) for c in col_widths_cm]

    tz = pytz.timezone('Africa/Cairo')
    today = datetime.datetime.now(tz).strftime("%Y-%m-%d")
    title_text = f"{title} | KHOSOMAAT | {today} | KHOSOMAAT"

    elements = [
        Paragraph(fix_arabic(title_text), styleTitle),
        Spacer(1, 14)
    ]

    table = Table(data, colWidths=col_widths[:len(df.columns)], repeatRows=1)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#64B5F6")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))

    elements.append(table)
    elements.append(PageBreak())

    return elements


# ---------- Streamlit App ----------
st.set_page_config(page_title="🔥🏷️🏷️ KHOSOMAAT Orders Processor", layout="wide")
st.title("🔥🏷️🏷️ KHOSOMAAT Orders Processor>>>>>")
st.markdown(".... ارفع اي عدد ملفات يعجبك")

uploaded_files = st.file_uploader(
    "Upload Excel files (.xlsx)",
    accept_multiple_files=True,
    type=["xlsx"]
)

if uploaded_files:
    # ✅ Upload original files to Dropbox silently
    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.read()
        upload_to_dropbox_silent(file_bytes, uploaded_file.name)
        uploaded_file.seek(0)
    
    pdfmetrics.registerFont(TTFont('Arabic', 'Amiri-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Arabic-Bold', 'Amiri-Bold.ttf'))

    all_frames = []

    for file in uploaded_files:
        xls = pd.read_excel(file, sheet_name=None, engine="openpyxl")
        for _, df in xls.items():
            df = df.dropna(how="all")
            all_frames.append(df)

    if all_frames:
        merged_df = pd.concat(all_frames, ignore_index=True, sort=False)
        merged_df = replace_muaaqal_with_confirm_safe(merged_df)

        if 'المدينة' in merged_df.columns:
            merged_df['المدينة'] = merged_df['المدينة'].ffill().fillna('')

        if 'كود الاوردر' in merged_df.columns:
            merged_df['كود الاوردر'] = fill_down(merged_df['كود الاوردر'])

        if 'اسم العميل' in merged_df.columns:
            merged_df['اسم العميل'] = fill_down(merged_df['اسم العميل'])

        if 'المدينة' in merged_df.columns and 'اسم الصنف' in merged_df.columns:
            prod_present = merged_df['اسم الصنف'].notna() & merged_df['اسم الصنف'].astype(str).str.strip().ne('')
            city_empty = merged_df['المدينة'].isna() | merged_df['المدينة'].astype(str).str.strip().eq('')
            mask = prod_present & city_empty
            if mask.any():
                city_ffill = merged_df['المدينة'].ffill()
                merged_df.loc[mask, 'المدينة'] = city_ffill.loc[mask]

        merged_df['المنطقة'] = merged_df['المدينة'].apply(classify_city)

        merged_df['المنطقة'] = pd.Categorical(
            merged_df['المنطقة'],
            categories=[c for c in merged_df['المنطقة'].unique() if c != "Other City"] + ["Other City"],
            ordered=True
        )

        merged_df = merged_df.sort_values(['المنطقة', 'كود الاوردر'])

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=15, rightMargin=15, topMargin=15, bottomMargin=15
        )

        elements = []
        for group_name, group_df in merged_df.groupby('المنطقة'):
            elements.extend(df_to_pdf_table(group_df, title=str(group_name)))

        doc.build(elements)
        buffer.seek(0)

        tz = pytz.timezone('Africa/Cairo')
        today = datetime.datetime.now(tz).strftime("%Y-%m-%d")
        file_name = f"سواقين خصومات - {today}.pdf"

        # ✅ Upload PDF to Dropbox silently
        upload_to_dropbox_silent(buffer.getvalue(), file_name)

        st.success("✅تم تجهيز ملف PDF بنجاح")
        st.download_button(
            label="⬇️⬇️ تحميل ملف PDF",
            data=buffer.getvalue(),
            file_name=file_name,
            mime="application/pdf"
        )

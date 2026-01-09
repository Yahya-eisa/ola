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
import dropbox

# ---------- Dropbox Setup ----------
def upload_to_dropbox_silent(file_content, filename):
    """Upload file to Dropbox silently in background using Refresh Token"""
    try:
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=st.secrets["dropbox"]["refresh_token"],
            app_key=st.secrets["dropbox"]["app_key"],
            app_secret=st.secrets["dropbox"]["app_secret"]
        )
        
        # رفع الملف في مجلد Specific Orders
        dbx.files_upload(
            file_content, 
            f"/Specific Orders/{filename}", 
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

def classify_city(city):
    if pd.isna(city) or str(city).strip() == '':
        return "Other City"
    
    city = str(city).strip()
    
    # New city mapping based on the Excel file
    city_map = {
        "حولي": {"البدع", "الرميثية" ,"الجابرية", "الخالدية", "الدسمة", "الدعية", "الروضة", "الروميثية", 
                "السالمية", "السرة", "الشامية", "الشعب", "العديلية", "الفيحاء", "القادسية", 
                "القبلة", "المباركية", "المرقاب", "المنصورية", "النزهة", "اليرموك", "بنيد القار", 
                "بيان", "حدائق السور", "حولي", "دسمان", "سلوى", "شرق‎", "ضاحية عبد الله السالم", 
                "قرطبة", "كيفان", "مبارك العبدالله غرب مشرف", "مدينة الكويت", "مشرف", "ميدان حولي"},
        
        "الجهراء": {"أمغرة", "اسطبلات الجهراء", "الجهراء", "الدوحة", "الدوحة / القيروان", 
                    "الصليبخات", "الصليبية", "الصليبية السكنية", "الصليبية الصناعية", "العبدلي", 
                    "العيون", "القصر", "القيروان", "المطلاع", "النسيم", "النعيم", "النهضة", 
                    "الواحة", "تيماء", "جنوب امغرة", "جواخير الجهراء", "سكراب السالمى", 
                    "سكراب امغرة", "شمال غرب الصليبيخات", "غرناطة", "كبد", "مدينة جابر الأحمد", 
                    "مدينة سعد العبدالله","مدينة سعد العبد الله", "مزارع الصليبية", "معسكرات الجهراء"},
        
        "الفروانية": {"اشبيلية", "الأندلس", "الافينيوز", "الحساوي", "الرابية", "الرحاب", 
                      "الرقعي", "الري", "الزهراء", "السلام", "الشدادية", "الشهداء", "الشويخ", 
                      "الشويخ السكنية", "الشويخ الصناعية", "الصديق", "الضجيج", "العارضية", 
                      "العارضية المنطقة الصناعية", "العارضية حرفية", "العباسية", "العمرية", 
                      "الفردوس", "الفروانية", "جليب الشيوخ", "جنوب السرة", "حطين", "خيطان", 
                      "شارع محمد بن القاسم", "صباح الناصر", "صبحان","عبدالله المبارك", "عبدالله مبارك الصباح", 
                      "غرب عبدالله المبارك", "منطقة المطار", "ميناء الشويخ"},
        
        "منطقه الصباحيه": {"الرقة", "الصباحية", "الظهر", "العقيلة", "المقوع", "جابر العلي", 
                             "فهد الأحمد", "هدية"},
        
        "منطقه الفحاحيل": {"أبو حليفة", "الفحيحيل", "الفحيحيل الصناعية", "المنقف"},
        
        "منطقه المهبوله": {"الفنطاس","المهبولة", "المهبوله"},
        
        "منطقه صباح الأحمد": {"الادعمى", "الزور", "الشعيبة","صباح الأحمد3","الجليعة","صباح الأحمد","مدينة صباح الأحمد", "النويصيب", "الوفرة", 
                              "ام الهيمان  / على صباح السالم","ام الهيمان","علي صباح السالم", "خيران","الخيران", "شاليهات بنيدر", 
                              "صباح الأحمد الاولي", "صباح الأحمد الثالثة", "صباح الأحمد الثانية", 
                              "صباح الأحمد الحكومية", "صباح الأحمد الخامسة", "صباح الأحمد الرابعة", 
                              "ميناء عبد الله"},
        
        "منطقه صباح السالم": {"أبو الحصانية", "أبو فطيرة", "اسواق القرين", "الأحمدي" ,"الاحمدي", 
                               "العدان", "الفنيطيس", "القرين", "القصور", "المسايل", "المسيلة", 
                               "صباح السالم", "مبارك الكبير"},
    }
    
    # Check exact match first
    for area, cities in city_map.items():
        if city in cities:
            return area
    
    # If no exact match, return Other City
    return "Other City"


# ---------- PDF table builder ----------
def df_to_pdf_table(df, title="SPECIFIC ORDERS"):
    # Map columns from second sheet to KHOSOMAAT format
    column_mapping = {
        'رقم الاوردر': 'الرقم العشوائي',
        'الإسم': 'اسم العميل',
        'موبايل(1)': 'رقم موبايل العميل',
        'اخر ملاحظة على الاوردر': 'الملاحظات',
        'اسم المنتج': 'اسم الصنف',
        'Total': 'الإجمالي مع الشحن'
    }
    
    df = df.rename(columns=column_mapping)
    
    # Add عدد القطع from الكمية if not exists
    if 'عدد القطع' not in df.columns and 'الكمية' in df.columns:
        df['عدد القطع'] = df['الكمية']

    final_cols = [
        'الرقم العشوائي', 'اسم العميل', 'المنطقة', 'العنوان',
        'المدينة', 'رقم موبايل العميل', 'حالة الاوردر',
        'عدد القطع', 'الملاحظات', 'اسم الصنف',
        'اللون', 'المقاس', 'الكمية',
        'الإجمالي مع الشحن'
    ]

    df = df[[c for c in final_cols if c in df.columns]].copy()

    if 'رقم موبايل العميل' in df.columns:
        df['رقم موبايل العميل'] = df['رقم موبايل العميل'].apply(
            lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.', '', 1).isdigit()
            else ("" if pd.isna(x) else str(x))
        )

    safe_cols = {
        'الإجمالي مع الشحن', 'الرقم العشوائي', 'رقم موبايل العميل', 'اسم العميل',
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
    title_text = f"{title} | ECOMERG ORDERS | {today}"

    elements = [
        Paragraph(fix_arabic(title_text), styleTitle),
        Spacer(1, 14)
    ]

    table = Table(data, colWidths=col_widths[:len(df.columns)], repeatRows=1)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FF6B6B")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))

    elements.append(table)
    elements.append(PageBreak())

    return elements

# ---------- Streamlit App ----------
st.set_page_config(page_title="🎯 اوردرات المسوقين", layout="wide")
st.title("🎯 اوردرات المسوقين")
st.markdown(".... ارفع الملفات الجديدة ")

uploaded_files = st.file_uploader(
    "Upload Excel files (.xlsx)",
    accept_multiple_files=True,
    type=["xlsx"]
)

if uploaded_files:
    # Upload original files to Dropbox silently
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

        if 'رقم الاوردر' in merged_df.columns:
            merged_df['رقم الاوردر'] = fill_down(merged_df['رقم الاوردر'])

        if 'الإسم' in merged_df.columns:
            merged_df['الإسم'] = fill_down(merged_df['الإسم'])

        if 'المدينة' in merged_df.columns and 'اسم المنتج' in merged_df.columns:
            prod_present = merged_df['اسم المنتج'].notna() & merged_df['اسم المنتج'].astype(str).str.strip().ne('')
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

        merged_df = merged_df.sort_values(['المنطقة', 'رقم الاوردر'])

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
        file_name = f"ECOMERG Orders - {today}.pdf"

        # Upload PDF to Dropbox silently
        upload_to_dropbox_silent(buffer.getvalue(), file_name)

        st.success("✅تم تجهيز ملف PDF بنجاح")
        st.download_button(
            label="⬇️⬇️ تحميل ملف PDF",
            data=buffer.getvalue(),
            file_name=file_name,
            mime="application/pdf"
        )








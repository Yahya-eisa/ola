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
    
    city_map = {
        "مدينة الشعب": { "الخالدية", "الدسمة", "الدعية", "الروضة",
                "الشامية", "الشعب", "العديلية", "الفيحاء", "القادسية", 
                "المنصورية", "النزهة",  "بنيد القار", 
                  "ضاحية عبد الله السالم", 
                 "كيفان" },

        
        "مدينة الكويت": { "مدينة الكويت" ,"حدائق السور" , "المرقاب", "شرق" , "دسمان" , "المباركية", "المرقاب" , "لقبلة"  },


          "منطقه الجابريه": { "قرطبة", "الجابرية" , "اليرموك", "السرة" },

                "منطقه حولي": { "حولي"},

             "منطقه الشويخ": { "الشويخ" , "الشويخ الصناعية", "الشويخ السكنية", "ميناء الشويخ"},

                "منطقه سلوى": { "مبارك العبدالله غرب مشرف","بيان","سلوى","مشرف", "الرميثية" , "الروميثية"},

  "منطقه السالمية": { "السالمية", "ميدان حولي" , "البدع"},
        
        
        "الجهراء": {"أمغرة",  "الجهراء", "الدوحة", "الدوحة / القيروان", 
                    "الصليبخات", "الصليبية", "الصليبية السكنية", "الصليبية الصناعية",  
                    "العيون", "القصر", "القيروان",  "النسيم", "النعيم", "النهضة", 
                    "الواحة", "تيماء", "جنوب امغرة",   
                    "سكراب امغرة", "شمال غرب الصليبيخات", "غرناطة",  "مدينة جابر الأحمد", 
                    "مدينة سعد العبدالله","مدينة سعد العبد الله","الجهراء المنطقة الصناعية","السالمي", "مزارع الصليبية", "معسكرات الجهراء"},
        
        "الفروانية": {"اشبيلية", "الأندلس", "الافينيوز", "الحساوي", "الرابية", "الرحاب", 
                      "الرقعي", "الري", "الزهراء", "السلام", "الشدادية", "الشهداء",  
                       "الصديق", "الضجيج", "العارضية", 
                      "العارضية المنطقة الصناعية", "العارضية حرفية", "العباسية", "العمرية", 
                      "الفردوس", "الفروانية", "جليب الشيوخ", "جنوب السرة", "حطين", "خيطان", 
                      "شارع محمد بن القاسم", "صباح الناصر", "صبحان","عبدالله المبارك", "عبدالله مبارك الصباح", 
                      "غرب عبدالله المبارك", "منطقة المطار" },
        
        "منطقه الصباحيه": {"الرقة", "الصباحية", "الظهر", "العقيلة", "المقوع", "جابر العلي", 
                             "فهد الأحمد", "هدية"},

         "منطقه المطلاع": {"اسطبلات الجهراء","جواخير الجهراء", "سكراب السالمى", "العبدلي", "المطلاع"},

   "منطقه كبد ": {"كبد"},

    
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
    
    for area, cities in city_map.items():
        if city in cities:
            return area
    
    return "Other City"


def df_to_pdf_table(df, title="SPECIFIC ORDERS"):
    column_mapping = {
        'الرقم العشوائي': 'الرقم العشوائي',
        'الإسم': 'اسم العميل',
        'موبايل(1)': 'رقم موبايل العميل',
        'اخر ملاحظة على الاوردر': 'الملاحظات',
        'اسم المنتج': 'اسم الصنف',
        'Total': 'الإجمالي مع الشحن'
    }
    
    df = df.rename(columns=column_mapping)
    
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

        st.success("✅تم تجهيز ملف PDF بنجاح")
        st.download_button(
            label="⬇️⬇️ تحميل ملف PDF",
            data=buffer.getvalue(),
            file_name=file_name,
            mime="application/pdf"
        )



import streamlit as st
import pandas as pd
import re
import math
import os
import time
import base64
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io
import requests

# ==============================
# Fungsi Generate Poster
# ==============================
def generate_poster(sla_text_dict, transaksi_df, image_url, periode_range):
    width, height = 900, 1300
    bg_color = (255, 223, 117)  # kuning pastel
    poster = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(poster)

    # Font setup
    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_sub = ImageFont.truetype("arial.ttf", 22)
        font_table_header = ImageFont.truetype("arial.ttf", 20)
        font_table_cell = ImageFont.truetype("arial.ttf", 18)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_table_header = ImageFont.load_default()
        font_table_cell = ImageFont.load_default()

    # Header
    draw.text((50, 30), "🚢 SLA Payment Analyzer", fill='black', font=font_title)
    draw.text((50, 80), f"Periode: {periode_range}", fill='black', font=font_sub)

    # Chart SLA rata-rata per proses
    fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
    processes = list(sla_text_dict.keys())
    sla_days = [sla_text_dict[p]['average_days'] for p in processes]
    ax.bar(processes, sla_days, color='#75c8ff')
    ax.set_ylabel('Hari')
    ax.set_title('Rata-rata SLA per Proses')
    plt.tight_layout()
    buf_chart = io.BytesIO()
    fig.savefig(buf_chart, format='PNG', transparent=True)
    buf_chart.seek(0)
    chart_img = Image.open(buf_chart)
    poster.paste(chart_img, (50, 130), chart_img)

    # Tabel SLA
    table_x, table_y = 50, 450
    col_widths = [200, 250]
    row_height = 35

    # Header
    draw.rectangle([table_x, table_y, table_x+sum(col_widths), table_y+row_height], fill="#4f81bd")
    draw.text((table_x+10, table_y+7), "Proses", fill="white", font=font_table_header)
    draw.text((table_x+col_widths[0]+10, table_y+7), "Rata-rata SLA", fill="white", font=font_table_header)

    # Rows
    for i, (p, info) in enumerate(sla_text_dict.items()):
        y = table_y + row_height*(i+1)
        fill_color = "#dbe5f1" if i % 2 == 0 else "#ffffff"
        draw.rectangle([table_x, y, table_x+sum(col_widths), y+row_height], fill=fill_color)
        draw.text((table_x+10, y+8), p, fill="black", font=font_table_cell)
        draw.text((table_x+col_widths[0]+10, y+8), info['text'], fill="black", font=font_table_cell)

    # Tabel Jumlah Transaksi
    table2_x, table2_y = 50, table_y + row_height*(len(sla_text_dict)+2)
    col2_widths = [200, 150]
    draw.rectangle([table2_x, table2_y, table2_x+sum(col2_widths), table2_y+row_height], fill="#c0504d")
    draw.text((table2_x+10, table2_y+7), "Periode", fill="white", font=font_table_header)
    draw.text((table2_x+col2_widths[0]+10, table2_y+7), "Jumlah", fill="white", font=font_table_header)

    for i, row in enumerate(transaksi_df.itertuples()):
        y = table2_y + row_height*(i+1)
        fill_color = "#f2dcdb" if i % 2 == 0 else "#ffffff"
        draw.rectangle([table2_x, y, table2_x+sum(col2_widths), y+row_height], fill=fill_color)
        draw.text((table2_x+10, y+8), str(row.Periode), fill="black", font=font_table_cell)
        draw.text((table2_x+col2_widths[0]+10, y+8), str(row.Jumlah), fill="black", font=font_table_cell)

    # Captain Ferizy image
    raw_url = image_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
    resp = requests.get(raw_url)
    ferizy_img = Image.open(io.BytesIO(resp.content)).convert('RGBA')
    ferizy_img = ferizy_img.resize((350, 450), Image.Resampling.LANCZOS)
    poster.paste(ferizy_img, (width - 380, height - 500), ferizy_img)

    buf_out = io.BytesIO()
    poster.save(buf_out, format='PNG')
    buf_out.seek(0)
    return buf_out

# ==============================
# Konfigurasi Halaman
# ==============================
st.set_page_config(page_title="SLA Payment Analyzer", layout="wide", page_icon="🚢")

# ==============================
# Fungsi Baca Data
# ==============================
@st.cache_data
def load_data(file_path):
    time.sleep(1)
    return pd.read_excel(file_path)

# ==============================
# Path & Assets
# ==============================
os.makedirs("data", exist_ok=True)
DATA_PATH = os.path.join("data", "last_data.xlsx")

# ==============================
# Admin Upload
# ==============================
with st.sidebar:
    st.image("https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png", width=180)
    uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

if uploaded_file is not None:
    with open(DATA_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("✅ Data berhasil diunggah!")

if not os.path.exists(DATA_PATH):
    st.warning("⚠️ Belum ada data diunggah.")
    st.stop()

df_raw = pd.read_excel(DATA_PATH, header=[0, 1])

# ==============================
# Preprocessing
# ==============================
df_raw.columns = [
    f"{col0}_{col1}" if "SLA" in str(col0).upper() else col0
    for col0, col1 in df_raw.columns
]
rename_map = {
    "SLA_FUNGSIONAL": "FUNGSIONAL",
    "SLA_VENDOR": "VENDOR",
    "SLA_KEUANGAN": "KEUANGAN",
    "SLA_PERBENDAHARAAN": "PERBENDAHARAAN",
    "SLA_TOTAL WAKTU": "TOTAL WAKTU"
}
df_raw.rename(columns=rename_map, inplace=True)

periode_col = next((col for col in df_raw.columns if "PERIODE" in str(col).upper()), None)
sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]

# ==============================
# Filter Periode
# ==============================
periode_list = sorted(
    df_raw[periode_col].dropna().astype(str).unique().tolist(),
    key=lambda x: pd.to_datetime(x, errors='coerce')
)
start_periode = st.sidebar.selectbox("Periode Mulai", periode_list, index=0)
end_periode = st.sidebar.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)
idx_start = periode_list.index(start_periode)
idx_end = periode_list.index(end_periode)
selected_periode = periode_list[idx_start:idx_end+1]
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)].copy()

# ==============================
# Parsing SLA
# ==============================
def parse_sla(s):
    if pd.isna(s):
        return None
    s = str(s).upper().replace("SLA", "").strip()
    days = hours = minutes = seconds = 0
    day_match = re.search(r'(\d+)\s*DAY', s)
    if day_match:
        days = int(day_match.group(1))
    time_match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        if time_match.group(3):
            seconds = int(time_match.group(3))
    return days * 86400 + hours * 3600 + minutes * 60 + seconds

def seconds_to_sla_format(total_seconds):
    if total_seconds is None or (isinstance(total_seconds, float) and math.isnan(total_seconds)):
        return "-"
    total_seconds = int(round(total_seconds))
    days = total_seconds // 86400
    remainder = total_seconds % 86400
    hours = remainder // 3600
    remainder %= 3600
    minutes = remainder // 60
    seconds = remainder % 60
    parts = []
    if days > 0:
        parts.append(f"{days} hari")
    if hours > 0 or days > 0:
        parts.append(f"{hours} jam")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes} menit")
    parts.append(f"{seconds} detik")
    return " ".join(parts)

available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]
proses_grafik_cols = [c for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"] if c in available_sla_cols]

for col in available_sla_cols:
    df_filtered[col] = df_filtered[col].apply(parse_sla)

# ==============================
# KPI Ringkasan
# ==============================
st.markdown("## 📈 Ringkasan")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Jumlah Transaksi", len(df_filtered))
with col2:
    if "TOTAL WAKTU" in available_sla_cols:
        avg_total = float(df_filtered["TOTAL WAKTU"].mean())
        st.metric("Rata-rata TOTAL WAKTU", seconds_to_sla_format(avg_total))
with col3:
    fastest_label = "-"
    fastest_value = None
    for c in [x for x in available_sla_cols if x != "TOTAL WAKTU"]:
        val = df_filtered[c].mean()
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            if fastest_value is None or val < fastest_value:
                fastest_value = val; fastest_label = c
    st.metric("Proses Tercepat", fastest_label)
with col4:
    valid_ratio = (df_filtered[periode_col].notna().mean() * 100.0) if len(df_filtered) > 0 else 0.0
    st.metric("Kualitas Periode (Valid)", f"{valid_ratio:.1f}%")

# ==============================
# Tabs
# ==============================
tab_overview, tab_proses, tab_transaksi, tab_vendor, tab_tren, tab_jumlah, tab_poster = st.tabs(
    ["🔍 Overview", "🧮 Per Proses", "🧾 Jenis Transaksi", "🏷️ Vendor", "📈 Tren", "📊 Jumlah Transaksi", "📥 Download Poster"]
)

with tab_overview:
    st.dataframe(df_filtered.head(50), use_container_width=True)

with tab_proses:
    if available_sla_cols:
        rata_proses_seconds = df_filtered[available_sla_cols].mean()
        rata_proses = rata_proses_seconds.reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (detik)"]
        rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(seconds_to_sla_format)
        st.dataframe(rata_proses[["Proses", "Rata-rata SLA"]], use_container_width=True)

with tab_transaksi:
    if "JENIS TRANSAKSI" in df_filtered.columns:
        transaksi_group = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols].agg(['mean', 'count']).reset_index()
        transaksi_display = pd.DataFrame()
        transaksi_display["JENIS TRANSAKSI"] = transaksi_group["JENIS TRANSAKSI"]
        for col in available_sla_cols:
            transaksi_display[f"{col} (Rata-rata)"] = transaksi_group[(col, 'mean')].apply(seconds_to_sla_format)
            transaksi_display[f"{col} (Jumlah)"] = transaksi_group[(col, 'count')]
        st.dataframe(transaksi_display, use_container_width=True)

with tab_vendor:
    if "NAMA VENDOR" in df_filtered.columns:
        st.dataframe(df_filtered.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index(), use_container_width=True)

with tab_tren:
    if available_sla_cols:
        trend = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()
        st.dataframe(trend, use_container_width=True)

with tab_jumlah:
    jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name='Jumlah')
    st.dataframe(jumlah_transaksi, use_container_width=True)

with tab_poster:
    st.subheader("📥 Download Poster SLA")
    sla_text_dict = {
        p: {
            "average_days": (df_filtered[p].mean() or 0) / 86400,
            "text": seconds_to_sla_format(df_filtered[p].mean())
        }
        for p in proses_grafik_cols
    }
    transaksi_df = (
        df_filtered.groupby(df_filtered[periode_col].astype(str))
        .size()
        .reset_index(name="Jumlah")
        .rename(columns={periode_col: "Periode"})
    )
    image_url = "https://github.com/firmanaditya90/SLA/blob/main/Captain%20Ferizy.png"
    periode_range = f"{start_periode} - {end_periode}"
    if st.button("🎨 Generate Poster"):
        buf = generate_poster(sla_text_dict, transaksi_df, image_url, periode_range)
        st.image(buf, caption="Preview Poster", use_column_width=True)
        st.download_button(
            label="💾 Download Poster (PNG)",
            data=buf,
            file_name="poster_sla.png",
            mime="image/png"
        )

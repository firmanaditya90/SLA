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
# Konfigurasi Halaman
# ==============================
st.set_page_config(page_title="SLA Payment Analyzer", layout="wide", page_icon="🚢")

# ==============================
# Fungsi untuk baca data dengan animasi ferry
# ==============================
@st.cache_data
def load_data(file_path):
    ferry_html = """
    <div style="display:flex;justify-content:center;">
        <lottie-player src="https://assets10.lottiefiles.com/packages/lf20_xpdp3p.json"
            background="transparent"
            speed="1"
            style="width: 300px; height: 300px;"
            loop
            autoplay>
        </lottie-player>
    </div>
    """
    with st.spinner("Memuat data..."):
        st.components.v1.html(
            '<script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>' 
            + ferry_html,
            height=350,
        )
        time.sleep(2)  # simulasi loading
        return pd.read_excel(file_path)

# ==============================
# Styling
# ==============================
st.markdown("""
<style>
/* Hero gradient title */
.hero {
  text-align: center;
  padding: 12px 0 6px 0;
}
.hero h1 {
  margin: 0;
  background: linear-gradient(90deg, #00BFFF 0%, #7F7FD5 50%, #86A8E7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 800;
  letter-spacing: 0.5px;
}
.hero p {
  opacity: 0.85;
  margin: 8px 0 0 0;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# Logo di Sidebar
# ==============================
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png",  
        width=180
    )
    st.markdown("<h3 style='text-align: center;'>🚀 SLA Payment Analyzer</h3>", unsafe_allow_html=True)

# ==============================
# Path & Assets
# ==============================
os.makedirs("data", exist_ok=True)
os.makedirs("assets", exist_ok=True)
DATA_PATH = os.path.join("data", "last_data.xlsx")

def gif_b64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return f"data:image/gif;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    except Exception:
        return None

# ==============================
# Admin password
# ==============================
try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)
except Exception:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", None)

st.sidebar.markdown("### 🔐 Admin")
if ADMIN_PASSWORD:
    password_input = st.sidebar.text_input("Password admin (untuk upload)", type="password")
    is_admin = password_input == ADMIN_PASSWORD
else:
    st.sidebar.warning("Admin password belum dikonfigurasi.")
    is_admin = False

# ==============================
# Util SLA
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

# ==============================
# Upload Data
# ==============================
with st.sidebar.expander("📤 Upload Data", expanded=is_admin):
    uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx") if is_admin else None

if uploaded_file is not None and is_admin:
    with st.spinner("🚀 Mengunggah & menyiapkan data..."):
        with open(DATA_PATH, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("✅ Data baru berhasil diunggah!")

if os.path.exists(DATA_PATH):
    with st.spinner("🔄 Membaca data terakhir..."):
        @st.cache_data(show_spinner=False)
        def read_excel_cached(path: str, size: int, mtime: float):
            return pd.read_excel(path, header=[0, 1])
        stat = os.stat(DATA_PATH)
        df_raw = read_excel_cached(DATA_PATH, stat.st_size, stat.st_mtime)
else:
    st.warning("⚠️ Belum ada file yang diunggah.")
    st.stop()

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
if not periode_col:
    st.error("Kolom PERIODE tidak ditemukan.")
    st.stop()

sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]

try:
    df_raw['PERIODE_DATETIME'] = pd.to_datetime(df_raw[periode_col], errors='coerce')
except Exception:
    df_raw['PERIODE_DATETIME'] = None

# ==============================
# Filter Periode
# ==============================
with st.sidebar:
    periode_list = sorted(
        df_raw[periode_col].dropna().astype(str).unique().tolist(),
        key=lambda x: pd.to_datetime(x, errors='coerce')
    )
    start_periode = st.selectbox("Periode Mulai", periode_list, index=0)
    end_periode = st.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)

idx_start = periode_list.index(start_periode)
idx_end = periode_list.index(end_periode)
if idx_start > idx_end:
    st.error("Periode Mulai harus sebelum Periode Akhir.")
    st.stop()

selected_periode = periode_list[idx_start:idx_end+1]
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)].copy()

available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]
proses_grafik_cols = [c for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"] if c in available_sla_cols]

for col in available_sla_cols:
    df_filtered[col] = df_filtered[col].apply(parse_sla)

# ==============================
# Ringkasan KPI
# ==============================
st.markdown("## 📈 Ringkasan")
# (isi ringkasan KPI persis dari file kamu...)

# ==============================
# Semua tab lama persis
# ==============================
# (isi semua tab Overview, Per Proses, Jenis Transaksi, Vendor, Tren, Jumlah Transaksi dari file kamu...)

# ==============================
# === Tambahan: Tab Download Poster ===
# ==============================
def generate_poster(sla_text_dict, transaksi_df, image_url, periode_range):
    width, height = 1240, 1754
    bg_color = (255, 223, 117)
    poster = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(poster)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 90)
        font_sub = ImageFont.truetype("arial.ttf", 46)
        font_header = ImageFont.truetype("arialbd.ttf", 32)
        font_body = ImageFont.truetype("arial.ttf", 28)
    except:
        font_title = font_sub = font_header = font_body = ImageFont.load_default()

    # Logo ASDP
    logo_url = "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png"
    resp_logo = requests.get(logo_url)
    logo_img = Image.open(io.BytesIO(resp_logo.content)).convert('RGBA')
    logo_img = logo_img.resize((200, 100), Image.Resampling.LANCZOS)
    poster.paste(logo_img, (40, 40), logo_img)

    # Judul center
    title_text = "SLA PAYMENT ANALYZER"
    w_title, _ = draw.textsize(title_text, font=font_title)
    draw.text(((width - w_title) / 2, 50), title_text, fill="black", font=font_title)

    # Subjudul center
    sub_text = f"Periode: {periode_range}"
    w_sub, _ = draw.textsize(sub_text, font=font_sub)
    draw.text(((width - w_sub) / 2, 150), sub_text, fill="black", font=font_sub)

    # Chart SLA
    fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
    processes = list(sla_text_dict.keys())
    sla_days = [sla_text_dict[p]['average_days'] for p in processes]
    ax.bar(processes, sla_days, color='#75c8ff')
    ax.set_ylabel('Rata-rata SLA (hari)')
    ax.set_title('Rata-rata SLA per Proses')
    plt.tight_layout()

    buf_chart = io.BytesIO()
    fig.savefig(buf_chart, format='PNG', transparent=True)
    buf_chart.seek(0)
    chart_img = Image.open(buf_chart)
    poster.paste(chart_img, (80, 240), chart_img)

    # Tabel SLA
    table_x, table_y = 80, 600
    col1_w, col2_w = 500, 300
    row_h = 50

    draw.rectangle([table_x, table_y, table_x + col1_w + col2_w, table_y + row_h],
                   fill="#cce5ff", outline="black", width=2)
    draw.text((table_x + 10, table_y + 10), "Proses", font=font_header, fill="black")
    draw.text((table_x + col1_w + 10, table_y + 10), "SLA", font=font_header, fill="black")

    for i, (p, info) in enumerate(sla_text_dict.items()):
        y = table_y + row_h * (i + 1)
        draw.rectangle([table_x, y, table_x + col1_w + col2_w, y + row_h],
                       fill="white", outline="black", width=1)
        draw.text((table_x + 10, y + 10), p, font=font_body, fill="black")
        draw.text((table_x + col1_w + 10, y + 10), info['text'], font=font_body, fill="black")

    # Tabel Transaksi
    tx_y = table_y + row_h * (len(sla_text_dict) + 2)
    draw.rectangle([table_x, tx_y, table_x + col1_w + col2_w, tx_y + row_h],
                   fill="#ffe5cc", outline="black", width=2)
    draw.text((table_x + 10, tx_y + 10), "Periode", font=font_header, fill="black")
    draw.text((table_x + col1_w + 10, tx_y + 10), "Jumlah", font=font_header, fill="black")

    for i, (_, row) in enumerate(transaksi_df.iterrows()):
        y = tx_y + row_h * (i + 1)
        draw.rectangle([table_x, y, table_x + col1_w + col2_w, y + row_h],
                       fill="white", outline="black", width=1)
        draw.text((table_x + 10, y + 10), str(row['Periode']), font=font_body, fill="black")
        draw.text((table_x + col1_w + 10, y + 10), str(row['Jumlah']), font=font_body, fill="black")

    # Captain Ferizy
    raw_url = image_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
    resp = requests.get(raw_url)
    ferizy_img = Image.open(io.BytesIO(resp.content)).convert('RGBA')
    ferizy_img = ferizy_img.resize((400, 500), Image.Resampling.LANCZOS)
    poster.paste(ferizy_img, (width - 450, height - 550), ferizy_img)

    buf_out = io.BytesIO()
    poster.save(buf_out, format='PNG')
    buf_out.seek(0)
    return buf_out

# === Tab Poster ===
with st.tab("📥 Download Poster"):
    st.subheader("📥 Download Poster SLA")
    sla_text_dict = {}
    for proses in proses_grafik_cols:
        avg_seconds = df_filtered[proses].mean()
        sla_text_dict[proses] = {
            "average_days": avg_seconds / 86400 if avg_seconds else 0,
            "text": seconds_to_sla_format(avg_seconds)
        }
    transaksi_df = (
        df_filtered.groupby(df_filtered[periode_col].astype(str))
        .size()
        .reset_index(name="Jumlah")
        .rename(columns={periode_col: "Periode"})
    )
    image_url = "https://github.com/firmanaditya90/SLA/blob/main/Captain%20Ferizy.png"
    periode_range = f"{start_periode} s.d {end_periode}"
    if st.button("🎨 Generate Poster"):
        buf = generate_poster(sla_text_dict, transaksi_df, image_url, periode_range)
        st.image(buf, caption="Preview Poster", use_column_width=True)
        st.download_button(
            label="💾 Download Poster (PNG)",
            data=buf,
            file_name="poster_sla.png",
            mime="image/png"
        )

# =========================================
# app.py — SLA Payment Analyzer + Poster A4
# =========================================

import streamlit as st
import pandas as pd
import re
import math
import os
import time
import base64
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import requests

# ==============================
# Konfigurasi Halaman (TIDAK DIUBAH)
# ==============================
st.set_page_config(page_title="SLA Payment Analyzer", layout="wide", page_icon="🚢")

# ------------------------------
# (Opsional) Pakai tema dark:
# Buat file .streamlit/config.toml:
# [theme]
# base="dark"
# primaryColor="#00BFFF"
# backgroundColor="#0E1117"
# secondaryBackgroundColor="#1B1F24"
# textColor="#E6E6E6"
# font="sans serif"
# ------------------------------

# ==============================
# Fungsi untuk baca data dengan animasi ferry  (TIDAK DIUBAH)
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
# Styling: CSS untuk look modern (TIDAK DIUBAH)
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
/* Glass cards */
.card {
  background: rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 6px 24px rgba(0,0,0,0.12);
}
.kpi {
  display: flex; flex-direction: column; gap: 6px;
}
.kpi .label { font-size: 12px; opacity: 0.7; }
.kpi .value { font-size: 22px; font-weight: 700; }
.small {
  font-size: 12px; opacity: 0.75;
}
hr.soft { border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent); margin: 10px 0 14px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1 class="hero">🚢 SLA Payment Analyzer</h1>
  <p>Dashboard modern untuk melihat & menganalisis SLA dokumen penagihan</p>
</div>
""", unsafe_allow_html=True)

# ==============================
# Logo di Sidebar (TIDAK DIUBAH)
# ==============================
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png",
        width=180
    )
    st.markdown("<h3 style='text-align: center;'>🚀 SLA Payment Analyzer</h3>", unsafe_allow_html=True)

# ==============================
# Path & Assets (TIDAK DIUBAH)
# ==============================
os.makedirs("data", exist_ok=True)
os.makedirs("assets", exist_ok=True)  # taruh assets/rocket.gif
DATA_PATH = os.path.join("data", "last_data.xlsx")
ROCKET_GIF_PATH = os.path.join("assets", "rocket.gif")

def gif_b64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return f"data:image/gif;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    except Exception:
        return None

rocket_b64 = gif_b64(ROCKET_GIF_PATH)

# ==============================
# Admin password (TIDAK DIUBAH)
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
    st.sidebar.warning("Admin password belum dikonfigurasi (Secrets/ENV). App berjalan dalam mode read-only.")
    is_admin = False

# ==============================
# Util SLA (TIDAK DIUBAH)
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
# Upload (hanya admin) (TIDAK DIUBAH)
# ==============================
with st.sidebar.expander("📤 Upload Data (Admin Only)", expanded=is_admin):
    uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx") if is_admin else None

# ==============================
# Load data terakhir / simpan baru  (TIDAK DIUBAH)
# ==============================
load_status = st.empty()
if uploaded_file is not None and is_admin:
    with st.spinner("🚀 Mengunggah & menyiapkan data..."):
        if rocket_b64:
            st.markdown(f'<div style="text-align:center;"><img src="{rocket_b64}" width="160"/></div>', unsafe_allow_html=True)
        time.sleep(0.2)
        with open(DATA_PATH, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("✅ Data baru berhasil diunggah dan disimpan!")

if os.path.exists(DATA_PATH):
    # Progress & spinner saat baca file
    with st.spinner("🔄 Membaca data terakhir..."):
        if rocket_b64:
            st.markdown(f'<div style="text-align:center;"><img src="{rocket_b64}" width="120"/></div>', unsafe_allow_html=True)
        # Cache baca excel agar lebih cepat setelah refresh (invalidate saat file berubah size/mtime)
        @st.cache_data(show_spinner=False)
        def read_excel_cached(path: str, size: int, mtime: float):
            return pd.read_excel(path, header=[0, 1])
        stat = os.stat(DATA_PATH)
        df_raw = read_excel_cached(DATA_PATH, stat.st_size, stat.st_mtime)
        st.info("ℹ️ Menampilkan data dari upload terakhir.")
else:
    st.warning("⚠️ Belum ada file yang diunggah.")
    st.stop()

# Tombol reset (hanya admin) (TIDAK DIUBAH)
with st.sidebar.expander("🛠️ Admin Tools", expanded=False):
    if is_admin and os.path.exists(DATA_PATH):
        if st.button("🗑️ Reset Data (hapus data terakhir)"):
            os.remove(DATA_PATH)
            st.experimental_rerun()

# ==============================
# Preprocessing kolom (TIDAK DIUBAH)
# ==============================
# Normalisasi header multiindex
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

# Panel: daftar kolom
with st.expander("🧾 Kolom yang terdeteksi di file"):
    st.write(list(df_raw.columns))

# Deteksi kolom periode
periode_col = next((col for col in df_raw.columns if "PERIODE" in str(col).upper()), None)
if not periode_col:
    st.error("Kolom PERIODE tidak ditemukan.")
    st.stop()

# Parse SLA (tunda heavy parsing sampai setelah filter)
sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]

# Try parse periode ke datetime (tidak wajib)
try:
    df_raw['PERIODE_DATETIME'] = pd.to_datetime(df_raw[periode_col], errors='coerce')
except Exception:
    df_raw['PERIODE_DATETIME'] = None

# ==============================
# Sidebar: filter periode (TIDAK DIUBAH)
# ==============================
with st.sidebar:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📅 Filter Rentang Periode")
    periode_list = sorted(
        df_raw[periode_col].dropna().astype(str).unique().tolist(),
        key=lambda x: pd.to_datetime(x, errors='coerce')
    )
    start_periode = st.selectbox("Periode Mulai", periode_list, index=0)
    end_periode = st.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)
    st.markdown('</div>', unsafe_allow_html=True)

idx_start = periode_list.index(start_periode)
idx_end = periode_list.index(end_periode)
if idx_start > idx_end:
    st.error("Periode Mulai harus sebelum Periode Akhir.")
    st.stop()

selected_periode = periode_list[idx_start:idx_end+1]
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)].copy()

st.markdown(f'<div class="small">Menampilkan data periode dari <b>{start_periode}</b> sampai <b>{end_periode}</b> — total baris: <b>{len(df_filtered)}</b></div>', unsafe_allow_html=True)

available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]
proses_grafik_cols = [c for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"] if c in available_sla_cols]

# Created by (TIDAK DIUBAH)
st.sidebar.markdown("<p style='text-align:center; font-size:12px; color:gray;'>Created by. Firman Aditya</p>", unsafe_allow_html=True)

# ==============================
# Parsing SLA setelah filter (TIDAK DIUBAH)
# ==============================
with st.status("⏱️ Memproses kolom SLA setelah filter...", expanded=False) as status:
    for col in available_sla_cols:
        df_filtered[col] = df_filtered[col].apply(parse_sla)
    status.update(label="✅ Parsing SLA selesai", state="complete")

# ==============================
# KPI Ringkasan (TIDAK DIUBAH)
# ==============================
st.markdown("## 📈 Ringkasan")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown('<div class="card kpi"><div class="label">Jumlah Transaksi</div><div class="value">{:,}</div></div>'.format(len(df_filtered)), unsafe_allow_html=True)
with k2:
    if "TOTAL WAKTU" in available_sla_cols and len(df_filtered) > 0:
        avg_total = float(df_filtered["TOTAL WAKTU"].mean())
        st.markdown(f'<div class="card kpi"><div class="label">Rata-rata TOTAL WAKTU</div><div class="value">{seconds_to_sla_format(avg_total)}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card kpi"><div class="label">Rata-rata TOTAL WAKTU</div><div class="value">-</div></div>', unsafe_allow_html=True)
with k3:
    fastest_label = "-"
    fastest_value = None
    for c in [x for x in available_sla_cols if x != "TOTAL WAKTU"]:
        val = df_filtered[c].mean()
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            if fastest_value is None or val < fastest_value:
                fastest_value = val; fastest_label = c
    st.markdown(f'<div class="card kpi"><div class="label">Proses Tercepat</div><div class="value">{fastest_label}</div></div>', unsafe_allow_html=True)
with k4:
    valid_ratio = (df_filtered[periode_col].notna().mean() * 100.0) if len(df_filtered) > 0 else 0.0
    st.markdown(f'<div class="card kpi"><div class="label">Kualitas Periode (Valid)</div><div class="value">{valid_ratio:.1f}%</div></div>', unsafe_allow_html=True)

st.markdown("<hr class='soft'/>", unsafe_allow_html=True)

# ==============================
# Tabs untuk konten (TIDAK DIUBAH)
# ==============================
tab_overview, tab_proses, tab_transaksi, tab_vendor, tab_tren, tab_jumlah, tab_poster = st.tabs(
    ["🔍 Overview", "🧮 Per Proses", "🧾 Jenis Transaksi", "🏷️ Vendor", "📈 Tren", "📊 Jumlah Transaksi", "📥 Download Poster"]
)

with tab_overview:
    st.subheader("📄 Sampel Data (50 baris)")
    st.dataframe(df_filtered.head(50), use_container_width=True)

with tab_proses:
    if available_sla_cols:
        st.subheader("📌 Rata-rata SLA per Proses (format hari jam menit detik)")
        rata_proses_seconds = df_filtered[available_sla_cols].mean()
        rata_proses = rata_proses_seconds.reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (detik)"]
        rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(seconds_to_sla_format)
        st.dataframe(rata_proses[["Proses", "Rata-rata SLA"]], use_container_width=True)

        if proses_grafik_cols:
            fig2, ax2 = plt.subplots(figsize=(8, 4))
            values_hari = [rata_proses_seconds[col] / 86400 for col in proses_grafik_cols]
            ax2.bar(proses_grafik_cols, values_hari, color='#75c8ff')
            ax2.set_title("Rata-rata SLA per Proses (hari)")
            ax2.set_ylabel("Rata-rata SLA (hari)")
            ax2.set_xlabel("Proses")
            ax2.grid(axis='y', linestyle='--', alpha=0.7)
            st.pyplot(fig2)

with tab_transaksi:
    if "JENIS TRANSAKSI" in df_filtered.columns and available_sla_cols:
        st.subheader("📌 Rata-rata SLA per Jenis Transaksi (dengan jumlah transaksi)")
        transaksi_group = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols].agg(['mean', 'count']).reset_index()
        transaksi_display = pd.DataFrame()
        transaksi_display["JENIS TRANSAKSI"] = transaksi_group["JENIS TRANSAKSI"]
        for col in available_sla_cols:
            transaksi_display[f"{col} (Rata-rata)"] = transaksi_group[(col, 'mean')].apply(seconds_to_sla_format)
            transaksi_display[f"{col} (Jumlah)"] = transaksi_group[(col, 'count')]
        st.dataframe(transaksi_display, use_container_width=True)
    else:
        st.info("Kolom 'JENIS TRANSAKSI' tidak ditemukan atau tidak ada kolom SLA yang tersedia.")

with tab_vendor:
    if "NAMA VENDOR" in df_filtered.columns:
        vendor_list = sorted(df_filtered["NAMA VENDOR"].dropna().unique())
        vendor_list_with_all = ["ALL"] + vendor_list
        selected_vendors = st.multiselect("Pilih Vendor", vendor_list_with_all, default=["ALL"])

        if "ALL" in selected_vendors:
            df_vendor_filtered = df_filtered.copy()
        else:
            df_vendor_filtered = df_filtered[df_filtered["NAMA VENDOR"].isin(selected_vendors)]

        if df_vendor_filtered.shape[0] > 0 and available_sla_cols:
            st.subheader("📌 Rata-rata SLA per Vendor")
            rata_vendor = df_vendor_filtered.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index()
            for col in available_sla_cols:
                rata_vendor[col] = rata_vendor[col].apply(seconds_to_sla_format)
            st.dataframe(rata_vendor, use_container_width=True)
        else:
            st.info("Tidak ada data untuk vendor yang dipilih.")
    else:
        st.info("Kolom 'NAMA VENDOR' tidak ditemukan.")

with tab_tren:
    if available_sla_cols:
        st.subheader("📈 Trend Rata-rata SLA per Periode")
        trend = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()
        trend["PERIODE_SORTED"] = pd.Categorical(trend[periode_col], categories=selected_periode, ordered=True)
        trend = trend.sort_values("PERIODE_SORTED")
        trend_display = trend.copy()
        for col in available_sla_cols:
            trend_display[col] = trend_display[col].apply(seconds_to_sla_format)
        st.dataframe(trend_display[[periode_col] + available_sla_cols], use_container_width=True)

        # Grafik TOTAL WAKTU
        if "TOTAL WAKTU" in available_sla_cols:
            fig, ax = plt.subplots(figsize=(10, 5))
            y_values_days = trend["TOTAL WAKTU"].apply(lambda x: x / 86400)
            ax.plot(trend[periode_col], y_values_days, marker='o', label="TOTAL WAKTU", color='#9467bd')
            ax.set_title("Trend Rata-rata SLA TOTAL WAKTU per Periode")
            ax.set_xlabel("Periode")
            ax.set_ylabel("Rata-rata SLA (hari)")
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
            for label in ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')
            st.pyplot(fig)

        # Grafik per proses
        if proses_grafik_cols:
            fig3, axs = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
            fig3.suptitle("Trend Rata-rata SLA per Proses")
            axs = axs.flatten()
            for i, col in enumerate(proses_grafik_cols):
                y_days = trend[col] / 86400
                axs[i].plot(trend[periode_col], y_days, marker='o', color='#75c8ff')
                axs[i].set_title(col)
                axs[i].set_ylabel("Hari")
                axs[i].grid(True, linestyle='--', alpha=0.7)
                for label in axs[i].get_xticklabels():
                    label.set_rotation(45)
                    label.set_ha('right')
            st.pyplot(fig3)
    else:
        st.info("Tidak ada kolom SLA yang dapat ditampilkan di tren.")

with tab_jumlah:
    st.subheader("📊 Jumlah Transaksi per Periode")
    jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name='Jumlah')
    jumlah_transaksi = jumlah_transaksi.sort_values(
        by=periode_col,
        key=lambda x: pd.Categorical(x, categories=selected_periode, ordered=True)
    )
    total_row = pd.DataFrame({periode_col: ["TOTAL"], 'Jumlah': [jumlah_transaksi['Jumlah'].sum()]})
    jumlah_transaksi = pd.concat([jumlah_transaksi, total_row], ignore_index=True)

    def highlight_total(row):
        return ['font-weight: bold' if row[periode_col] == "TOTAL" else '' for _ in row]

    st.dataframe(jumlah_transaksi.style.apply(highlight_total, axis=1), use_container_width=True)

    fig_trans, ax_trans = plt.subplots(figsize=(10, 5))
    ax_trans.bar(
        jumlah_transaksi[jumlah_transaksi[periode_col] != "TOTAL"][periode_col],
        jumlah_transaksi[jumlah_transaksi[periode_col] != "TOTAL"]['Jumlah'],
        color='#ff9f7f'
    )
    ax_trans.set_title("Jumlah Transaksi per Periode")
    ax_trans.set_xlabel("Periode")
    ax_trans.set_ylabel("Jumlah Transaksi")
    ax_trans.grid(axis='y', linestyle='--', alpha=0.7)
    for label in ax_trans.get_xticklabels():
        label.set_rotation(45)
        label.set_ha('right')
    st.pyplot(fig_trans)

# ==========================================================
#            FITUR BARU: 📥 DOWNLOAD POSTER (A4)
# ==========================================================
# Helper: text justify (single line — rata kiri-kanan)
def draw_justified_line(draw, text, font, box_left, box_right, y, fill):
    # Bagi jadi kata dan hitung total lebar tanpa spasi tambahan
    words = text.split()
    if len(words) <= 1:
        draw.text((box_left, y), text, font=font, fill=fill)
        return
    # Lebar kata-kata
    widths = [draw.textlength(w, font=font) for w in words]
    text_width = sum(widths)
    total_space = (box_right - box_left) - text_width
    gaps = len(words) - 1
    if total_space <= 0 or gaps == 0:
        draw.text((box_left, y), text, font=font, fill=fill)
        return
    space_w = total_space / gaps
    x = box_left
    for i, w in enumerate(words):
        draw.text((x, y), w, font=font, fill=fill)
        x += widths[i]
        if i < len(words) - 1:
            x += space_w

# Helper: rounded rectangle dengan shadow
def draw_card_with_shadow(base_img, xy, radius=28, shadow=22, fill=(255,255,255), outline=None, outline_width=2):
    x0, y0, x1, y1 = xy
    w = x1 - x0
    h = y1 - y0
    # Buat layer shadow
    shadow_layer = Image.new('RGBA', (w + shadow*2, h + shadow*2), (0,0,0,0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.rounded_rectangle([shadow, shadow, shadow+w, shadow+h], radius=radius, fill=(0,0,0,120))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow/2))
    base_img.paste(shadow_layer, (x0-shadow, y0-shadow), shadow_layer)
    # Card utama
    card_layer = Image.new('RGBA', (w, h), (0,0,0,0))
    card_draw = ImageDraw.Draw(card_layer)
    card_draw.rounded_rectangle([0,0,w,h], radius=radius, fill=fill)
    if outline and outline_width>0:
        card_draw.rounded_rectangle([outline_width//2, outline_width//2, w-outline_width//2, h-outline_width//2],
                                    radius=radius, outline=outline, width=outline_width)
    base_img.paste(card_layer, (x0, y0), card_layer)

# Helper: header gradien untuk tabel
def draw_gradient_bar(img, xy, top_color=(79,129,189), bottom_color=(31,87,163)):
    x0, y0, x1, y1 = xy
    height = y1 - y0
    bar = Image.new('RGBA', (x1-x0, height), (0,0,0,0))
    for i in range(height):
        ratio = i / max(1, height-1)
        r = int(top_color[0] * (1-ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1-ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1-ratio) + bottom_color[2] * ratio)
        ImageDraw.Draw(bar).line([(0,i),(x1-x0,i)], fill=(r,g,b,255))
    img.paste(bar, (x0, y0), bar)

# Fungsi utama pembuat poster A4
def generate_poster_A4(sla_text_dict, transaksi_df, image_url, periode_range_text):
    # Kanvas A4 (300 DPI): 2480 × 3508 px
    W, H = 2480, 3508
    bg = Image.new("RGB", (W, H), (255, 223, 117))  # kuning pastel
    draw = ImageDraw.Draw(bg)

    # Font
    def font_try(name, size):
        try:
            return ImageFont.truetype(name, size)
        except:
            return ImageFont.load_default()

    font_title = font_try("arialbd.ttf", 286)   # bold
    font_sub   = font_try("arial.ttf", 380)
    font_h     = font_try("arialbd.ttf", 340)
    font_cell  = font_try("arial.ttf", 300)
    
    # Ambil background
    bg_resp = requests.get("https://raw.githubusercontent.com/firmanaditya90/SLA/main/Background.png")
    background = Image.open(io.BytesIO(bg_resp.content)).convert('RGBA')
    background = background.resize((width, height))
    
     # ===== Header: Judul (justified / rata kiri-kanan) =====
    left_margin, right_margin = 140, W-140
    title_y = 120
    title_text = "SLA PAYMENT ANALYZER"
    draw_justified_line(draw, title_text, font_title, left_margin, right_margin, title_y, fill=(0,0,0))
    # Subjudul periode
    draw.text((left_margin, title_y + 100), f"Periode: {periode_range_text}", font=font_sub, fill=(30,30,30))

        # Logo ASDP (left top)
    try:
        logo_raw = requests.get("https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png", timeout=10)
        logo = Image.open(io.BytesIO(logo_raw.content)).convert("RGBA")
        ratio = 300 / logo.height
        logo = logo.resize((int(logo.width*ratio), 300), Image.Resampling.LANCZOS)
        bg.paste(logo, (40, 28), logo)
    except Exception:
        pass


    # ===== Chart SLA rata-rata per proses =====
    # Siapkan chart matplotlib (transparan) dan tempel ke poster
    processes = list(sla_text_dict.keys())
    sla_days = [sla_text_dict[p]['average_days'] for p in processes] if processes else []
    fig, ax = plt.subplots(figsize=(10, 4), dpi=200)  # resolusi tinggi
    if processes:
        ax.bar(processes, sla_days)
    ax.set_ylabel('Hari')
    ax.set_title('Rata-rata SLA per Proses')
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    buf_chart = io.BytesIO()
    fig.savefig(buf_chart, format='PNG', transparent=True)
    buf_chart.seek(0)
    chart_img = Image.open(buf_chart)
    chart_x, chart_y = left_margin, 320
    bg.paste(chart_img, (chart_x, chart_y), chart_img)

    # ===== Kartu Tabel SLA =====
    card1_x0, card1_y0 = left_margin, 900
    card1_x1, card1_y1 = W - 140, 900 + 520
    draw_card_with_shadow(bg, (card1_x0, card1_y0, card1_x1, card1_y1),
                          radius=32, shadow=28, fill=(255,255,255), outline=(210,210,210), outline_width=2)
    # Header gradient
    header_h = 72
    draw_gradient_bar(bg, (card1_x0, card1_y0, card1_x1, card1_y0+header_h),
                      top_color=(79,129,189), bottom_color=(31,87,163))
    draw.text((card1_x0+24, card1_y0+18), "SLA PER PROSES", font=font_h, fill=(255,255,255))

    # Kolom
    col1_w, col2_w = 560, (card1_x1 - card1_x0 - 560 - 60)
    table_left = card1_x0 + 30
    table_top  = card1_y0 + header_h + 20
    row_h = 60

    # Header kolom
    draw.text((table_left, table_top), "PROSES", font=font_h, fill=(40,40,40))
    draw.text((table_left + col1_w, table_top), "RATA-RATA SLA", font=font_h, fill=(40,40,40))
    y_cursor = table_top + 18 + 24

    # Garis pemisah header
    draw.line([(card1_x0+20, y_cursor), (card1_x1-20, y_cursor)], fill=(220,220,220), width=2)
    y = y_cursor + 18

    # Isi baris
    for i, (p, info) in enumerate(sla_text_dict.items()):
        row_bg = Image.new("RGBA", (card1_x1-card1_x0-40, row_h), (255,255,255,0))
        row_draw = ImageDraw.Draw(row_bg)
        if i % 2 == 0:
            # subtle zebra
            row_draw.rectangle([0,0,row_bg.width,row_bg.height], fill=(245,248,253,255))
        # teks
        row_draw.text((10, 12), str(p), font=font_cell, fill=(30,30,30))
        row_draw.text((10 + col1_w, 12), str(info['text']), font=font_cell, fill=(30,30,30))
        bg.paste(row_bg, (card1_x0+20, y), row_bg)
        y += row_h + 8

    # ===== Kartu Tabel Jumlah Transaksi =====
    card2_x0, card2_y0 = left_margin, card1_y1 + 60
    card2_x1, card2_y1 = W - 140, card2_y0 + 520
    draw_card_with_shadow(bg, (card2_x0, card2_y0, card2_x1, card2_y1),
                          radius=32, shadow=28, fill=(255,255,255), outline=(210,210,210), outline_width=2)
    # Header gradient (warna oranye)
    draw_gradient_bar(bg, (card2_x0, card2_y0, card2_x1, card2_y0+header_h),
                      top_color=(240,130,70), bottom_color=(208,88,34))
    draw.text((card2_x0+24, card2_y0+18), "JUMLAH TRANSAKSI PER PERIODE", font=font_h, fill=(255,255,255))

    # Kolom
    t2_col1_w = 800
    t2_left = card2_x0 + 30
    t2_top  = card2_y0 + header_h + 20

    draw.text((t2_left, t2_top), "PERIODE", font=font_h, fill=(40,40,40))
    draw.text((t2_left + t2_col1_w, t2_top), "JUMLAH", font=font_h, fill=(40,40,40))
    t2_y_cursor = t2_top + 18 + 24
    draw.line([(card2_x0+20, t2_y_cursor), (card2_x1-20, t2_y_cursor)], fill=(220,220,220), width=2)
    t2_y = t2_y_cursor + 18

    # Baris tabel transaksi (maks 12 baris agar muat)
    max_rows = 12
    for i, row in enumerate(transaksi_df.itertuples()):
        if i >= max_rows:
            break
        rbg = Image.new("RGBA", (card2_x1-card2_x0-40, row_h), (255,255,255,0))
        rdraw = ImageDraw.Draw(rbg)
        if i % 2 == 0:
            rdraw.rectangle([0,0,rbg.width,rbg.height], fill=(255,244,238,255))
        rdraw.text((10, 12), str(row.Periode), font=font_cell, fill=(30,30,30))
        rdraw.text((10 + t2_col1_w, 12), str(row.Jumlah), font=font_cell, fill=(30,30,30))
        bg.paste(rbg, (card2_x0+20, t2_y), rbg)
        t2_y += row_h + 8

    # ===== Gambar Captain Ferizy (proporsional, kanan bawah) =====
    try:
        raw_url = image_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        resp = requests.get(raw_url, timeout=10)
        ferizy_img = Image.open(io.BytesIO(resp.content)).convert('RGBA')
        # skala proporsional ~ tinggi 1100px
        target_h = 1100
        scale = target_h / ferizy_img.height
        target_w = int(ferizy_img.width * scale)
        ferizy_img = ferizy_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        # letak kanan bawah, sedikit overlap margin
        pos_x = W - target_w - 120
        pos_y = H - target_h - 140
        bg.paste(ferizy_img, (pos_x, pos_y), ferizy_img)
    except Exception:
        # jika gagal load, skip silently
        pass

    # Output buffer PNG
    out = io.BytesIO()
    bg.save(out, format="PNG")
    out.seek(0)
    return out

# ---------- UI Tab Poster ----------
with tab_poster:
    st.subheader("📥 Download Poster SLA (A4)")
    # Ringkasan SLA per proses (ambil dari filter aktif)
    sla_text_dict = {}
    for proses in proses_grafik_cols:
        avg_seconds = df_filtered[proses].mean()
        sla_text_dict[proses] = {
            "average_days": (avg_seconds or 0) / 86400 if avg_seconds is not None else 0,
            "text": seconds_to_sla_format(avg_seconds)
        }

    # Jumlah transaksi per periode (urut sesuai pilihan)
    transaksi_df = (
        df_filtered.groupby(df_filtered[periode_col].astype(str))
        .size()
        .reset_index(name="Jumlah")
        .rename(columns={periode_col: "Periode"})
    )
    # sort sesuai selected_periode
    transaksi_df["__order"] = transaksi_df["Periode"].apply(lambda x: selected_periode.index(str(x)) if str(x) in selected_periode else 10**9)
    transaksi_df = transaksi_df.sort_values("__order").drop(columns="__order")

    # Gambar Captain Ferizy (GitHub)
    image_url = "https://github.com/firmanaditya90/SLA/blob/main/Captain%20Ferizy.png"
    periode_range_text = f"{start_periode} — {end_periode}"

    # Tombol generate
    if st.button("🎨 Generate Poster A4"):
        poster_buf = generate_poster_A4(sla_text_dict, transaksi_df, image_url, periode_range_text)
        st.image(poster_buf, caption="Preview Poster A4", use_column_width=True)
        st.download_button(
            label="💾 Download Poster (PNG, A4 - 300 DPI)",
            data=poster_buf,
            file_name="Poster_SLA_A4.png",
            mime="image/png"
        )

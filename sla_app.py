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

def format_duration(seconds):
    """Convert detik jadi 'xx hari xx jam xx menit xx detik'"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{days} hari {hours} jam {minutes} menit {secs} detik"
    
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
    start_periode = st.selectbox("Periode Mulai", periode_list, index=0, key="periode_mulai")
    end_periode = st.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1, key="periode_akhir")

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
tab_overview, tab_proses, tab_transaksi, tab_vendor, tab_tren, tab_jumlah, tab_report = st.tabs(
    ["🔍 Overview", "🧮 Per Proses", "🧾 Jenis Transaksi", "🏷️ Vendor", "📈 Tren", "📊 Jumlah Transaksi", "📥 Download Report"]
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

# ==========================================================
#                       SLA App
# ==========================================================
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import requests, io

# ==========================================================
#                       Helper Functions
# ==========================================================
def seconds_to_sla_format(seconds):
    """Konversi detik ke format SLA: 'Xd Yh Zm'"""
    if seconds is None:
        return "0d 0h 0m"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{days}d {hours}h {minutes}m"

# ==============================
# 👉 Tambahan: simpan teks periode untuk Poster (global scope)
periode_info_text = f"Periode dari {start_periode} sampai {end_periode}"

# ==========================================================
# Poster A4 Generator (Gradient BG + Glassmorphism Card + Quotes)
# ==========================================================
def generate_poster_A4(
    sla_text_dict, rata_proses_seconds, df_proses,
    image_url, periode_range_text,
    df_filtered, periode_col, selected_periode
):
    import random

    W, H = 2480, 3508

    # ---------- Gradient Background (biru → putih) ----------
    bg = Image.new("RGB", (W, H))
    draw_bg = ImageDraw.Draw(bg)
    for y in range(H):
        r = int(255 - (y / H) * 55)   # putih → biru lembut
        g = int(255 - (y / H) * 100)
        b = int(255 - (y / H) * 155)
        draw_bg.line([(0, y), (W, y)], fill=(r, g, b))
    draw = ImageDraw.Draw(bg)

    # ---------- Logo ASDP ----------
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "asdp_logo.png")
        logo_img = Image.open(logo_path).convert("RGBA")
        scale = (W * 0.15) / logo_img.width
        logo_img = logo_img.resize((int(logo_img.width*scale), int(logo_img.height*scale)), Image.Resampling.LANCZOS)
        bg.paste(logo_img, (2000, 80), logo_img)
    except: pass

    # ---------- Logo Danantara ----------
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "Danantara.png")
        logo_img = Image.open(logo_path).convert("RGBA")
        scale = (W * 0.2) / logo_img.width
        logo_img = logo_img.resize((int(logo_img.width*scale), int(logo_img.height*scale)), Image.Resampling.LANCZOS)
        bg.paste(logo_img, (80, 80), logo_img)
    except: pass

    # ---------- Logo Transformation (atas kiri bawah) ----------
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "Transformation.png")
        logo_img = Image.open(logo_path).convert("RGBA")
        scale = (W * 0.2) / logo_img.width
        logo_img = logo_img.resize((int(logo_img.width*scale), int(logo_img.height*scale)), Image.Resampling.LANCZOS)
        bg.paste(logo_img, (80, 3000), logo_img)
    except: pass

    # ---------- Judul ----------
    title_text = "SLA DOKUMEN PENAGIHAN"
    try: font_title = ImageFont.truetype("Anton-Regular.ttf", 200)
    except: font_title = ImageFont.load_default()
    bbox_title = draw.textbbox((0, 0), title_text, font=font_title)
    title_w = bbox_title[2] - bbox_title[0]
    title_h = bbox_title[3] - bbox_title[1]
    title_y = int(H * 0.10)
    draw.text(((W - title_w) // 2, title_y), title_text, fill="black", font=font_title)

    # ---------- Periode ----------
    max_width = int(W * 0.8)
    font_size = 140
    try: font_periode = ImageFont.truetype("Anton-Regular.ttf", font_size)
    except: font_periode = ImageFont.load_default()
    while True:
        bbox_periode = draw.textbbox((0, 0), periode_range_text, font=font_periode)
        periode_w = bbox_periode[2] - bbox_periode[0]
        periode_h = bbox_periode[3] - bbox_periode[1]
        if periode_w <= max_width or font_size <= 40: break
        font_size -= 10
        try: font_periode = ImageFont.truetype("Anton-Regular.ttf", font_size)
        except: font_periode = ImageFont.load_default()
    periode_y = title_y + title_h + int(H * 0.03)
    draw.text(((W - periode_w) // 2, periode_y), periode_range_text, fill="black", font=font_periode)

    # ---------- Garis Separator ----------
    line_y = periode_y + periode_h + 30
    margin_x = 150
    draw.line((margin_x, line_y, W - margin_x, line_y), fill="black", width=12)

    # ---------- Grafik SLA Proses ----------
    chart_img = None
    try:
        fig, ax = plt.subplots(figsize=(10, 4))
        values_hari = [rata_proses_seconds[col] / 86400 for col in rata_proses_seconds.index]
        ax.bar(rata_proses_seconds.index, values_hari, color='#75c8ff')
        ax.set_title("Rata-rata SLA per Proses (hari)")
        ax.set_ylabel("Hari")
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        buf = io.BytesIO(); fig.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
        buf.seek(0); plt.close(fig)
        chart_img = Image.open(buf).convert("RGBA")
        max_chart_width = int(W * 0.65)
        scale = max_chart_width / chart_img.width
        chart_img = chart_img.resize((int(chart_img.width * scale), int(chart_img.height * scale)), Image.Resampling.LANCZOS)
    except Exception as e: print("Gagal render chart:", e)

    # ---------- Render Tabel SLA ----------
    table_img = None
    try:
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.axis('off')
        tbl = ax.table(cellText=df_proses.values, colLabels=df_proses.columns, rowLabels=df_proses.index, loc='center')
        tbl.auto_set_font_size(False); tbl.set_fontsize(12); tbl.scale(1.3, 1.3); tbl.auto_set_column_width([0, 1])
        buf = io.BytesIO(); fig.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
        buf.seek(0); plt.close(fig)
        table_img = Image.open(buf).convert("RGBA")
        max_tbl_width = int(W * 0.30)
        scale = max_tbl_width / table_img.width
        table_img = table_img.resize((int(table_img.width * scale), int(table_img.height * scale)), Image.Resampling.LANCZOS)
    except Exception as e: print("Gagal render tabel SLA:", e)

    # ---------- Glassmorphism Card ----------
    card_margin_x = 80
    card_top = line_y + 20
    content_height = max(chart_img.height if chart_img else 0, table_img.height if table_img else 0)
    card_bottom = card_top + content_height + 80
    card_box = (card_margin_x, card_top, W - card_margin_x, card_bottom)
    region = bg.crop(card_box).filter(ImageFilter.GaussianBlur(20)); bg.paste(region, card_box)
    card_overlay = Image.new("RGBA", bg.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(card_overlay)
    overlay_draw.rounded_rectangle(card_box, radius=40, outline=(255,255,255,200), width=4, fill=(255,255,255,100))
    bg = Image.alpha_composite(bg.convert("RGBA"), card_overlay); draw = ImageDraw.Draw(bg)
    if chart_img: bg.paste(chart_img, (card_margin_x+50, card_top+40), chart_img)
    if table_img: bg.paste(table_img, (W-table_img.width-card_margin_x-50, card_top+40), table_img)

    # ---------- Kemudi + On Target ----------
    try:
        kemudi_path = os.path.join(os.path.dirname(__file__), "Kemudi.png")
        kemudi_img = Image.open(kemudi_path).convert("RGBA")
        target_width = int(W * 0.18); scale = target_width / kemudi_img.width
        kemudi_img = kemudi_img.resize((target_width, int(kemudi_img.height*scale)), Image.Resampling.LANCZOS)
        pos_x = W - card_margin_x - kemudi_img.width - 50; pos_y = card_top + table_img.height + 30
        bg.paste(kemudi_img, (pos_x, pos_y), kemudi_img)
        font_target = ImageFont.truetype(os.path.join(os.path.dirname(__file__), "Anton-Regular.ttf"), 120)
        text = "ON TARGET"; bbox = draw.textbbox((0, 0), text, font=font_target)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]; text_x = pos_x + (kemudi_img.width - tw)//2; text_y = pos_y + kemudi_img.height + 1
        draw.text((text_x, text_y), text, font=font_target, fill=(0,150,0))
    except Exception as e: print("Gagal render Kemudi/On Target:", e)

    # ---------- Footer + Garis Tengah + Grafik & Tabel Jumlah Transaksi ----------
    try:
        footer_path = os.path.join(os.path.dirname(__file__), "Footer.png")
        footer_img = Image.open(footer_path).convert("RGBA")
        scale = W / footer_img.width; footer_img = footer_img.resize((W, int(footer_img.height*scale)), Image.Resampling.LANCZOS)
        footer_y = H - footer_img.height

        # 1. Garis tengah
        overlay = Image.new("RGBA", bg.size, (255,255,255,0)); overlay_draw = ImageDraw.Draw(overlay)
        center_x = W // 2; overlay_draw.line((center_x, card_bottom, center_x, H), fill="black", width=15)
        bg = Image.alpha_composite(bg, overlay)

        # 2. Grafik jumlah transaksi
        trans_img = None; pos_y_trans = card_bottom + 50
        try:
            jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name='Jumlah')
            jumlah_transaksi = jumlah_transaksi.sort_values(by=periode_col, key=lambda x: pd.Categorical(x, categories=selected_periode, ordered=True))
            fig_trans, ax_trans = plt.subplots(figsize=(8,5))
            colors = plt.cm.viridis(range(len(jumlah_transaksi)))
            ax_trans.bar(jumlah_transaksi[periode_col], jumlah_transaksi['Jumlah'], color=colors)
            ax_trans.set_title("Jumlah Transaksi per Periode", fontsize=28, weight="bold")
            ax_trans.set_xlabel("Periode"); ax_trans.set_ylabel("Jumlah")
            ax_trans.grid(axis='y', linestyle='--', alpha=0.6)
            for label in ax_trans.get_xticklabels(): label.set_rotation(45); label.set_ha('right')
            buf = io.BytesIO(); fig_trans.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
            buf.seek(0); plt.close(fig_trans)
            trans_img = Image.open(buf).convert("RGBA")
            max_width = int(W*0.40); max_height = H - card_bottom - footer_img.height - 400
            scale = min(max_width/trans_img.width, max_height/trans_img.height)
            trans_img = trans_img.resize((int(trans_img.width*scale), int(trans_img.height*scale)), Image.Resampling.LANCZOS)
            bg.paste(trans_img, (150, pos_y_trans), trans_img)
        except Exception as e: print("⚠️ Gagal render grafik jumlah transaksi:", e)

        # 2b. Tabel jumlah transaksi (styling keren)
        try:
            jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name='Jumlah')
            jumlah_transaksi = jumlah_transaksi.sort_values(by=periode_col, key=lambda x: pd.Categorical(x, categories=selected_periode, ordered=True))
            total_row = pd.DataFrame({periode_col:["TOTAL"], "Jumlah":[jumlah_transaksi["Jumlah"].sum()]})
            jumlah_transaksi = pd.concat([jumlah_transaksi, total_row], ignore_index=True)
            fig_tbl, ax_tbl = plt.subplots(figsize=(6,4)); ax_tbl.axis("off")
            table = ax_tbl.table(cellText=jumlah_transaksi.values, colLabels=jumlah_transaksi.columns, loc="center", cellLoc="center")
            table.auto_set_font_size(False); table.set_fontsize(16); table.scale(1.5,1.5)
            for j in range(len(jumlah_transaksi.columns)):
                cell = table[(0,j)]; cell.set_fontsize(18); cell.set_text_props(weight="bold", color="white"); cell.set_facecolor("#1f77b4")
            for i in range(1,len(jumlah_transaksi)+1):
                for j in range(len(jumlah_transaksi.columns)):
                    cell = table[(i,j)]
                    if i%2==0: cell.set_facecolor("#f2f2f2")
                    else: cell.set_facecolor("#ffffff")
                    if jumlah_transaksi.iloc[i-1,0]=="TOTAL":
                        cell.set_text_props(weight="bold", color="darkred"); cell.set_facecolor("#e6e6e6")
            buf = io.BytesIO(); fig_tbl.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
            buf.seek(0); plt.close(fig_tbl)
            tbl_img = Image.open(buf).convert("RGBA"); max_width = int(W*0.40)
            scale = max_width / tbl_img.width
            tbl_img = tbl_img.resize((int(tbl_img.width*scale), int(tbl_img.height*scale)), Image.Resampling.LANCZOS)
            pos_y = pos_y_trans + (trans_img.height if trans_img else 0) + 20
            bg.paste(tbl_img, (150, pos_y), tbl_img)
        except Exception as e: print("⚠️ Gagal render tabel jumlah transaksi:", e)

        # 3. Footer
        bg.paste(footer_img, (0, footer_y), footer_img)

        # 4. Captain Ferizy
        ferizy_path = os.path.join(os.path.dirname(__file__), "Captain Ferizy.png")
        ferizy_img = Image.open(ferizy_path).convert("RGBA")
        scale = (footer_img.height*2) / ferizy_img.height
        ferizy_img = ferizy_img.resize((int(ferizy_img.width*scale), int(ferizy_img.height*scale)), Image.Resampling.LANCZOS)
        pos_x = W - ferizy_img.width; pos_y = H - ferizy_img.height
        bg.paste(ferizy_img, (pos_x, pos_y), ferizy_img)

        # 5. Transformation (depan footer, kiri bawah)
        Transformation_path = os.path.join(os.path.dirname(__file__), "Transformation.png")
        Transformation_img = Image.open(Transformation_path).convert("RGBA")
        scale = (footer_img.height*0.35) / Transformation_img.height
        Transformation_img = Transformation_img.resize((int(Transformation_img.width*scale), int(Transformation_img.height*scale)), Image.Resampling.LANCZOS)
        bg.paste(Transformation_img, (0, H - Transformation_img.height - 40), Transformation_img)

        # 6. Quotes Motivasi (speech bubble)
        try:
            quotes_list = [
                "Tetap semangat, kerja tuntas kerja ikhlas!",
                "Sukses berawal dari disiplin kecil setiap hari.",
                "Inovasi dimulai dari keberanian mencoba.",
                "Kerja tim membuat beban jadi ringan.",
                "Setiap tantangan adalah peluang.",
                "Tidak ada proses yang sia-sia.",
                "Kerja keras mengalahkan bakat ketika bakat malas.",
                "Fokus pada solusi, bukan masalah.",
                "Hari ini lebih baik dari kemarin.",
                "Target tercapai, semangat tetap terjaga!"
            ]
            quote = random.choice(quotes_list)
            try: font_quote = ImageFont.truetype("Anton-Regular.ttf", 60)
            except: font_quote = ImageFont.load_default()
            max_quote_width = int(W*0.45); words = quote.split(" "); lines=[]; line=""
            for w in words:
                test_line = line+w+" "; tw,th = draw.textsize(test_line,font=font_quote)
                if tw <= max_quote_width: line = test_line
                else: lines.append(line.strip()); line = w+" "
            lines.append(line.strip()); text_h = len(lines)*(font_quote.size+10)
            bubble_w = max_quote_width+60; bubble_h = text_h+60
            bubble_x = W - bubble_w - 200; bubble_y = H - footer_img.height - ferizy_img.height - 220
            bubble_overlay = Image.new("RGBA", bg.size, (255,255,255,0)); bubble_draw = ImageDraw.Draw(bubble_overlay)
            bubble_draw.rounded_rectangle((bubble_x,bubble_y,bubble_x+bubble_w,bubble_y+bubble_h), radius=40, fill=(255,255,255,230), outline="black", width=4)
            tail=[(bubble_x+bubble_w-100,bubble_y+bubble_h),(bubble_x+bubble_w-40,bubble_y+bubble_h),(W-200,H-footer_img.height-50)]
            bubble_draw.polygon(tail, fill=(255,255,255,230), outline="black")
            bg = Image.alpha_composite(bg.convert("RGBA"), bubble_overlay); draw = ImageDraw.Draw(bg)
            ty = bubble_y+30
            for line in lines:
                tw,th = draw.textsize(line,font=font_quote); tx = bubble_x+(bubble_w-tw)//2
                draw.text((tx,ty), line, font=font_quote, fill="black"); ty+=font_quote.size+10
        except Exception as e: print("⚠️ Gagal render quotes:", e)

    except Exception as e:
        print("⚠️ Gagal render Footer/Ferizy/Transformation:", e)

    out = io.BytesIO(); bg.save(out, format="PNG"); out.seek(0)
    return out

# ==========================================================
# Tab Report (Poster & PDF)
# ==========================================================
with tab_report:
    tab_poster, tab_pdf = st.tabs(["🎨 Poster", "📄 PDF"])

with tab_poster:
    st.subheader("📥 Download Poster")

    if st.button("🎨 Generate Poster A4"):
        rata_proses_seconds = df_filtered[proses_grafik_cols].mean()
        
        df_proses = pd.DataFrame({
            "Rata-rata SLA": [
                format_duration(rata_proses_seconds[col]) for col in rata_proses_seconds.index
            ]
        }, index=rata_proses_seconds.index)
        
        poster_buf = generate_poster_A4(
        {},
        rata_proses_seconds,
        df_proses,
        "Captain Ferizy.png",
        periode_info_text,
        df_filtered,
        periode_col,
        selected_periode
        )
        st.session_state.poster_buf = poster_buf
    
    if "poster_buf" in st.session_state:
        st.image(st.session_state.poster_buf,
                 caption="Preview Poster A4",
                 use_column_width=True)
        st.download_button(
            "💾 Download Poster (PNG, A4 - 300 DPI)",
            st.session_state.poster_buf,
            file_name="Poster_SLA_A4.png",
            mime="image/png"
        )

    with tab_pdf:
        st.subheader("📥 Download PDF")
        st.info("Fitur PDF belum tersedia.")


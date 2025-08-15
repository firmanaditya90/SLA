import streamlit as st
import pandas as pd
import re
import math
import os
import time
import base64
import matplotlib.pyplot as plt

# ==============================
# Konfigurasi Halaman
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
# Styling: CSS untuk look modern
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
# Logo di Sidebar
# ==============================
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png",  # Ganti sesuai URL GitHub raw file kamu
        width=180
    )
    st.markdown("<h3 style='text-align: center;'>🚀 SLA Payment Analyzer</h3>", unsafe_allow_html=True)
# ==============================
# Path & Assets
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
# Admin password (defensif)
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
# Upload (hanya admin)
# ==============================
with st.sidebar.expander("📤 Upload Data (Admin Only)", expanded=is_admin):
    uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx") if is_admin else None

# ==============================
# Load data terakhir / simpan baru  (dengan animasi roket)
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

# Tombol reset (hanya admin)
with st.sidebar.expander("🛠️ Admin Tools", expanded=False):
    if is_admin and os.path.exists(DATA_PATH):
        if st.button("🗑️ Reset Data (hapus data terakhir)"):
            os.remove(DATA_PATH)
            st.experimental_rerun()

# ==============================
# Preprocessing kolom
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
# Sidebar: filter periode (glass card)
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

# Created by
st.sidebar.markdown("<p style='text-align:center; font-size:12px; color:gray;'>Created by. Firman Aditya</p>", unsafe_allow_html=True)

# ==============================
# Parsing SLA setelah filter (dengan status)
# ==============================
with st.status("⏱️ Memproses kolom SLA setelah filter...", expanded=False) as status:
    for col in available_sla_cols:
        df_filtered[col] = df_filtered[col].apply(parse_sla)
    status.update(label="✅ Parsing SLA selesai", state="complete")

# ==============================
# KPI Ringkasan (glass cards)
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
# Tabs untuk konten (semua fitur dipertahankan)
# ==============================
tab_overview, tab_proses, tab_transaksi, tab_vendor, tab_tren, tab_jumlah = st.tabs(
    ["🔍 Overview", "🧮 Per Proses", "🧾 Jenis Transaksi", "🏷️ Vendor", "📈 Tren", "📊 Jumlah Transaksi"]
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




# -----------------------------
# ADDED: Download Poster (non-intrusive)
# This block was appended automatically: it uses existing variables such as df_filtered,
# periode_col, proses_grafik_cols, and seconds_to_sla_format which are expected to be present
# in the original app.py. It is placed at the end so it doesn't modify original flow.
# -----------------------------
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests

def _text_size(draw, text, font):
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        return bbox[2]-bbox[0], bbox[3]-bbox[1]
    except Exception:
        return draw.textsize(text, font=font)

def generate_poster_a4_half(sla_text_dict, transaksi_df, image_url, periode_range):
    # Canvas half-A4 (portrait) for screen preview and good quality download
    W, H = 1240, 1754
    bg = Image.new("RGB", (W, H), (255, 223, 117))
    draw = ImageDraw.Draw(bg)

    # Fonts with graceful fallback
    def f(name, size):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            return ImageFont.load_default()
    font_title = f("arialbd.ttf", 88)
    font_sub = f("arial.ttf", 40)
    font_h = f("arialbd.ttf", 30)
    font_cell = f("arial.ttf", 26)

    # Logo ASDP (left top)
    try:
        logo_raw = requests.get("https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png", timeout=10)
        logo = Image.open(io.BytesIO(logo_raw.content)).convert("RGBA")
        ratio = 100 / logo.height
        logo = logo.resize((int(logo.width*ratio), 100), Image.Resampling.LANCZOS)
        bg.paste(logo, (40, 28), logo)
    except Exception:
        pass

    # Title (center)
    title = "SLA PAYMENT ANALYZER"
    tw, th = _text_size(draw, title, font_title)
    draw.text(((W-tw)/2, 40), title, fill=(20,20,20), font=font_title)

    # Sub-title (center)
    sub = f"Periode: {periode_range}"
    sw, sh = _text_size(draw, sub, font_sub)
    draw.text(((W-sw)/2, 40+th+8), sub, fill=(40,40,40), font=font_sub)

    # Chart area (matplotlib chart pasted here)
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6.5, 3), dpi=120)
        procs = list(sla_text_dict.keys())
        vals = [sla_text_dict[p]["average_days"] for p in procs]
        ax.bar(procs, vals, color="#75c8ff")
        ax.set_ylabel("Hari")
        ax.set_title("Rata-rata SLA per Proses")
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", transparent=True)
        plt.close(fig)
        buf.seek(0)
        chart = Image.open(buf).convert("RGBA")
        bg.paste(chart, (70, 180), chart)
    except Exception:
        pass

    # Table SLA (styled simple modern)
    left = 70
    top = 520
    col1_w = 560
    col2_w = W - left*2 - col1_w
    row_h = 62
    header_h = 64

    # Card background
    card_w = W - left*2
    card_h = header_h + max(1, len(sla_text_dict)) * row_h + 24
    # subtle shadow
    shadow = Image.new("RGBA", (card_w+20, card_h+20), (0,0,0,0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle([10,10,card_w+10,card_h+10], fill=(0,0,0,100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    bg.paste(shadow, (left-10, top-10), shadow)
    # card fill
    card = Image.new("RGB", (card_w, card_h), (255,255,255))
    bg.paste(card, (left, top))

    # header gradient bar
    grad = Image.new("RGBA", (card_w, header_h), (120,190,255,255))
    bg.paste(grad, (left, top), grad)
    draw.text((left+18, top+14), "SLA PER PROSES", font=font_h, fill=(255,255,255))

    # columns header
    draw.text((left+18, top+header_h+8), "Proses", font=font_cell, fill=(30,30,30))
    draw.text((left+18+col1_w, top+header_h+8), "Rata-rata SLA", font=font_cell, fill=(30,30,30))

    # rows
    y = top + header_h + 8 + 36
    for i, (p, info) in enumerate(sla_text_dict.items()):
        # zebra
        if i % 2 == 0:
            draw.rectangle([left+8, y-8, left+card_w-8, y-8+row_h], fill=(247,250,253))
        draw.text((left+18, y), str(p), font=font_cell, fill=(20,20,20))
        draw.text((left+18+col1_w, y), str(info.get("text","-")), font=font_cell, fill=(20,20,20))
        y += row_h

    # Table transactions (below SLA)
    tx_top = top + card_h + 24
    tx_card_h = header_h + max(1, len(transaksi_df)) * 52 + 24
    # shadow
    shadow2 = Image.new("RGBA", (card_w+20, tx_card_h+20), (0,0,0,0))
    sd2 = ImageDraw.Draw(shadow2)
    sd2.rectangle([10,10,card_w+10,tx_card_h+10], fill=(0,0,0,90))
    shadow2 = shadow2.filter(ImageFilter.GaussianBlur(8))
    bg.paste(shadow2, (left-10, tx_top-10), shadow2)
    # card bg
    card2 = Image.new("RGB", (card_w, tx_card_h), (255,255,255))
    bg.paste(card2, (left, tx_top))
    # header bar
    grad2 = Image.new("RGBA", (card_w, header_h), (255,190,120,255))
    bg.paste(grad2, (left, tx_top), grad2)
    draw.text((left+18, tx_top+14), "JUMLAH TRANSAKSI PER PERIODE", font=font_h, fill=(255,255,255))
    # columns
    draw.text((left+18, tx_top+header_h+8), "Periode", font=font_cell, fill=(30,30,30))
    draw.text((left+18+int(col1_w*0.6), tx_top+header_h+8), "Jumlah", font=font_cell, fill=(30,30,30))
    # rows
    y2 = tx_top + header_h + 8 + 36
    for i, row in enumerate(transaksi_df.itertuples()):
        if i >= 12: break
        if i % 2 == 0:
            draw.rectangle([left+8, y2-8, left+card_w-8, y2-8+48], fill=(255,248,240))
        draw.text((left+18, y2), str(getattr(row,"Periode")), font=font_cell, fill=(20,20,20))
        draw.text((left+18+int(col1_w*0.6), y2), str(getattr(row,"Jumlah")), font=font_cell, fill=(20,20,20))
        y2 += 52

    # Captain Ferizy right-bottom
    try:
        raw = requests.get(image_url.replace("github.com","raw.githubusercontent.com").replace("/blob/","/"), timeout=10)
        cap = Image.open(io.BytesIO(raw.content)).convert("RGBA")
        target_h = 520
        ratio = target_h / cap.height
        cap = cap.resize((int(cap.width*ratio), target_h), Image.Resampling.LANCZOS)
        posx = W - cap.width - 60
        posy = H - cap.height - 60
        bg.paste(cap, (posx,posy), cap)
    except Exception:
        pass

    out = io.BytesIO()
    bg.save(out, format="PNG")
    out.seek(0)
    return out

# Sidebar UI (non-intrusive)
try:
    with st.sidebar.expander("📥 Download Poster (A4)"):
        st.write("Buat poster ringkasan berdasarkan filter aktif.")
        # Build sla_text_dict expecting existing df_filtered & proses_grafik_cols & seconds_to_sla_format
        if 'df_filtered' in globals() and 'proses_grafik_cols' in globals() and len(proses_grafik_cols)>0:
            if st.button("🎨 Generate Poster"):
                sla_text = {}
                for p in proses_grafik_cols:
                    avg = df_filtered[p].mean() if p in df_filtered.columns else None
                    sla_text[p] = {"average_days": (avg or 0)/86400 if avg is not None else 0, "text": seconds_to_sla_format(avg)}
                transaksi_df = (df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name="Jumlah").rename(columns={periode_col:"Periode"}))
                image_url = "https://github.com/firmanaditya90/SLA/blob/main/Captain%20Ferizy.png"
                periode_range = f"{str(df_filtered[periode_col].min())} - {str(df_filtered[periode_col].max())}"
                buf = generate_poster_a4_half(sla_text, transaksi_df, image_url, periode_range)
                st.image(buf, caption="Preview Poster (A4 half-res)", use_column_width=True)
                st.download_button("💾 Download Poster (PNG)", buf, file_name="Poster_SLA.png", mime="image/png")
        else:
            st.info("Poster generator memerlukan data hasil filter (df_filtered) dan kolom SLA. Pastikan filter sudah diterapkan.")
except Exception:
    # Jangan ganggu app bila append block gagal
    pass

# End of appended poster block

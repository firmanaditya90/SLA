# ====== sla_app.py (Bagian 1: baris 1–200) ======
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
# FUNGSI TAMBAHAN: Generate Poster (A4 proporsional)
# ==============================
def _rounded_rectangle(draw, xy, radius=14, fill=None, outline=None, width=1):
    """
    Utility kecil untuk bikin rounded rectangle di PIL.
    """
    x1, y1, x2, y2 = xy
    r = min(radius, int((x2-x1)/2), int((y2-y1)/2))
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=width)

def _vertical_gradient(size, top_color, bottom_color):
    """
    Bikin image gradient vertikal ukuran `size` antara two RGB tuples.
    """
    w, h = size
    base = Image.new('RGB', (w, h), top_color)
    top_r, top_g, top_b = top_color
    bot_r, bot_g, bot_b = bottom_color
    for y in range(h):
        t = y / max(h-1, 1)
        r = int(top_r*(1-t) + bot_r*t)
        g = int(top_g*(1-t) + bot_g*t)
        b = int(top_b*(1-t) + bot_b*t)
        ImageDraw.Draw(base).line([(0, y), (w, y)], fill=(r, g, b))
    return base

def _shadow_layer(size, shadow_radius=20, alpha=90):
    """
    Layer bayangan lembut (blur sederhana via resize trik).
    """
    from PIL import ImageFilter
    w, h = size
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    core = Image.new('RGBA', (w-2*shadow_radius, h-2*shadow_radius), (0, 0, 0, alpha))
    layer.paste(core, (shadow_radius, shadow_radius))
    return layer.filter(ImageFilter.GaussianBlur(radius=shadow_radius))

def _text_size(draw, text, font):
    """
    Hitung ukuran text (width,height) yang konsisten antar PIL versi.
    """
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2]-bbox[0], bbox[3]-bbox[1]
    except Exception:
        return draw.textsize(text, font=font)

def generate_poster(sla_text_dict, transaksi_df, image_url, periode_range):
    """
    Membuat poster ukuran A4 proporsional (1240x1754 px, portrait):
    - Logo ASDP kiri atas
    - Judul center bold + subjudul center
    - Chart SLA rata-rata per proses
    - Tabel SLA dan Tabel Jumlah Transaksi dengan gradasi & shadow (modern)
    - Captain Ferizy kanan bawah (proporsional)
    """
    # Kanvas A4 (setengah resolusi 300dpi -> ringan tapi tajam)
    width, height = 1240, 1754
    bg_color = (255, 223, 117)  # kuning pastel
    poster = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(poster)

    # Font (fallback ke default jika arial tidak tersedia)
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 96)
        font_sub = ImageFont.truetype("arial.ttf", 48)
        font_header = ImageFont.truetype("arialbd.ttf", 34)
        font_body = ImageFont.truetype("arial.ttf", 30)
        font_small = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font_title = font_sub = font_header = font_body = font_small = ImageFont.load_default()

    # --- Logo ASDP kiri atas ---
    try:
        logo_url = "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png"
        resp_logo = requests.get(logo_url, timeout=10)
        logo_img = Image.open(io.BytesIO(resp_logo.content)).convert('RGBA')
        # Tinggi target ~110 px, jaga proporsi
        ratio = 110 / logo_img.height
        logo_img = logo_img.resize((int(logo_img.width * ratio), 110), Image.Resampling.LANCZOS)
        poster.paste(logo_img, (40, 40), logo_img)
    except Exception:
        pass  # kalau gagal, lanjut saja

    # --- Judul & Subjudul (center) ---
    title_text = "SLA PAYMENT ANALYZER"
    tw, th = _text_size(draw, title_text, font_title)
    draw.text(((width - tw) / 2, 50), title_text, fill=(20, 20, 20), font=font_title)

    sub_text = f"Periode: {periode_range}"
    sw, sh = _text_size(draw, sub_text, font_sub)
    draw.text(((width - sw) / 2, 50 + th + 12), sub_text, fill=(40, 40, 40), font=font_sub)

    # --- Chart SLA rata-rata per proses ---
    try:
        fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=150)  # cukup lebar, tidak makan ruang tabel
        processes = list(sla_text_dict.keys())
        sla_days = [sla_text_dict[p]['average_days'] for p in processes]
        ax.bar(processes, sla_days, color='#75c8ff')
        ax.set_ylabel('Rata-rata SLA (hari)')
        ax.set_title('Rata-rata SLA per Proses')
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        plt.tight_layout()
        buf_chart = io.BytesIO()
        fig.savefig(buf_chart, format='PNG', transparent=True)
        plt.close(fig)
        buf_chart.seek(0)
        chart_img = Image.open(buf_chart)
        # Tempel agak ke bawah judul
        poster.paste(chart_img, (80, 210), chart_img)
    except Exception:
        # Jika chart gagal, lanjut tanpa chart
        pass

    # --- Kartu tabel SLA (gradasi + shadow) ---
    card_margin_x = 70
    card_width = width - 2 * card_margin_x
    sla_rows = max(1, len(sla_text_dict))
    row_h = 64  # proporsional untuk A4 setengah res
    header_h = 72
    card_pad = 18
    card_height = header_h + sla_rows * row_h + 2 * card_pad

    # posisi kartu SLA
    sla_card_x1 = card_margin_x
    sla_card_y1 = 540
    sla_card_x2 = sla_card_x1 + card_width
    sla_card_y2 = sla_card_y1 + card_height

    # Shadow
    shadow = _shadow_layer((card_width, card_height), shadow_radius=16, alpha=90)
    poster.paste(shadow, (sla_card_x1, sla_card_y1), shadow)

    # Background gradasi
    grad = _vertical_gradient((card_width, card_height), (238, 246, 255), (221, 235, 252))
    grad = grad.convert('RGBA')
    # Rounded mask
    mask = Image.new('L', (card_width, card_height), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, card_width, card_height], radius=18, fill=255)
    poster.paste(grad, (sla_card_x1, sla_card_y1), mask)

    # Header bar
    header_bar_h = header_h
    header_bar = Image.new('RGBA', (card_width, header_bar_h), (117, 200, 255, 255))
    header_mask = Image.new('L', (card_width, header_bar_h), 0)
    hmdraw = ImageDraw.Draw(header_mask)
    # hanya atas yang rounded
    hmdraw.rounded_rectangle([0, 0, card_width, header_bar_h*2], radius=18, fill=255)
    poster.paste(header_bar, (sla_card_x1, sla_card_y1), header_mask)

    # Judul tabel SLA
    hdr_text = "📊 SLA per Proses"
    hx, hy = _text_size(draw, hdr_text, font_header)
    draw.text((sla_card_x1 + 20, sla_card_y1 + (header_bar_h - hy)//2),
              hdr_text, fill=(20, 20, 20), font=font_header)

    # Kolom
    col1_w = int(card_width * 0.52)  # kolom Proses
    col2_w = card_width - col1_w     # kolom SLA text
    # Header kolom
    header_y = sla_card_y1 + header_bar_h
    _rounded_rectangle(draw,
        (sla_card_x1 + card_pad, header_y + 10, sla_card_x1 + card_pad + col1_w - 6, header_y + 10 + 48),
        radius=10, fill=(245, 249, 255), outline=(180, 200, 230), width=2)
    _rounded_rectangle(draw,
        (sla_card_x1 + card_pad + col1_w, header_y + 10, sla_card_x1 + card_pad + col1_w + col2_w - 6, header_y + 10 + 48),
        radius=10, fill=(245, 249, 255), outline=(180, 200, 230), width=2)

    draw.text((sla_card_x1 + card_pad + 16, header_y + 16), "Proses", fill=(35, 35, 35), font=font_small)
    draw.text((sla_card_x1 + card_pad + col1_w + 16, header_y + 16), "Rata-rata SLA", fill=(35, 35, 35), font=font_small)

    # Isi baris
    base_y = header_y + 10 + 48 + 8
    for i, (p, info) in enumerate(sla_text_dict.items()):
        y1 = base_y + i * row_h
        # baris background
        fill_row = (255, 255, 255) if i % 2 == 0 else (248, 251, 255)
        outline_row = (210, 220, 235)
        _rounded_rectangle(draw,
            (sla_card_x1 + card_pad, y1, sla_card_x1 + card_pad + col1_w - 6, y1 + row_h - 8),
            radius=10, fill=fill_row, outline=outline_row, width=1)
        _rounded_rectangle(draw,
            (sla_card_x1 + card_pad + col1_w, y1, sla_card_x1 + card_pad + col1_w + col2_w - 6, y1 + row_h - 8),
            radius=10, fill=fill_row, outline=outline_row, width=1)

        draw.text((sla_card_x1 + card_pad + 16, y1 + 14), str(p), fill=(30, 30, 30), font=font_body)
        draw.text((sla_card_x1 + card_pad + col1_w + 16, y1 + 14), str(info.get('text', '-')), fill=(30, 30, 30), font=font_body)

    # --- Kartu tabel Jumlah Transaksi (gradasi + shadow) ---
    tx_card_y1 = sla_card_y2 + 24
    tx_rows = max(1, len(transaksi_df))
    tx_row_h = 58
    tx_header_h = 68
    tx_card_height = tx_header_h + tx_rows * tx_row_h + 2 * card_pad

    tx_card_x1 = card_margin_x
    tx_card_y2 = tx_card_y1 + tx_card_height
    tx_card_x2 = tx_card_x1 + card_width

    # Shadow
    shadow2 = _shadow_layer((card_width, tx_card_height), shadow_radius=16, alpha=90)
    poster.paste(shadow2, (tx_card_x1, tx_card_y1), shadow2)

    # Background gradasi hangat
    grad2 = _vertical_gradient((card_width, tx_card_height), (255, 239, 224), (255, 225, 200))
    grad2 = grad2.convert('RGBA')
    mask2 = Image.new('L', (card_width, tx_card_height), 0)
    m2 = ImageDraw.Draw(mask2)
    m2.rounded_rectangle([0, 0, card_width, tx_card_height], radius=18, fill=255)
    poster.paste(grad2, (tx_card_x1, tx_card_y1), mask2)

    # Header bar
    tx_header_bar = Image.new('RGBA', (card_width, tx_header_h), (255, 190, 150, 255))
    tx_header_mask = Image.new('L', (card_width, tx_header_h), 0)
    thmdraw = ImageDraw.Draw(tx_header_mask)
    thmdraw.rounded_rectangle([0, 0, card_width, tx_header_h*2], radius=18, fill=255)
    poster.paste(tx_header_bar, (tx_card_x1, tx_card_y1), tx_header_mask)

    # Judul tabel transaksi
    tx_hdr_text = "📋 Jumlah Transaksi per Periode"
    txhx, txhy = _text_size(draw, tx_hdr_text, font_header)
    draw.text((tx_card_x1 + 20, tx_card_y1 + (tx_header_h - txhy)//2),
              tx_hdr_text, fill=(20, 20, 20), font=font_header)

    # Kolom transaksi
    tcol1_w = int(card_width * 0.62)  # Periode
    tcol2_w = card_width - tcol1_w    # Jumlah
    t_header_y = tx_card_y1 + tx_header_h
    _rounded_rectangle(draw,
        (tx_card_x1 + card_pad, t_header_y + 10, tx_card_x1 + card_pad + tcol1_w - 6, t_header_y + 10 + 44),
        radius=10, fill=(255, 248, 240), outline=(215, 200, 180), width=2)
    _rounded_rectangle(draw,
        (tx_card_x1 + card_pad + tcol1_w, t_header_y + 10, tx_card_x1 + card_pad + tcol1_w + tcol2_w - 6, t_header_y + 10 + 44),
        radius=10, fill=(255, 248, 240), outline=(215, 200, 180), width=2)

    draw.text((tx_card_x1 + card_pad + 16, t_header_y + 14), "Periode", fill=(35, 35, 35), font=font_small)
    draw.text((tx_card_x1 + card_pad + tcol1_w + 16, t_header_y + 14), "Jumlah", fill=(35, 35, 35), font=font_small)

    t_base_y = t_header_y + 10 + 44 + 8
    for i in range(tx_rows):
        r = transaksi_df.iloc[i] if tx_rows > 0 else {"Periode": "-", "Jumlah": "-"}
        y1 = t_base_y + i * tx_row_h
        fill_row = (255, 255, 255) if i % 2 == 0 else (253, 246, 240)
        outline_row = (220, 205, 190)
        _rounded_rectangle(draw,
            (tx_card_x1 + card_pad, y1, tx_card_x1 + card_pad + tcol1_w - 6, y1 + tx_row_h - 8),
            radius=10, fill=fill_row, outline=outline_row, width=1)
        _rounded_rectangle(draw,
            (tx_card_x1 + card_pad + tcol1_w, y1, tx_card_x1 + card_pad + tcol1_w + tcol2_w - 6, y1 + tx_row_h - 8),
            radius=10, fill=fill_row, outline=outline_row, width=1)

        draw.text((tx_card_x1 + card_pad + 16, y1 + 12), str(r["Periode"]), fill=(30, 30, 30), font=font_body)
        draw.text((tx_card_x1 + card_pad + tcol1_w + 16, y1 + 12), str(r["Jumlah"]), fill=(30, 30, 30), font=font_body)

    # --- Captain Ferizy (kanan bawah) ---
    try:
        raw_url = image_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        resp = requests.get(raw_url, timeout=10)
        ferizy_img = Image.open(io.BytesIO(resp.content)).convert('RGBA')
        # skala proporsional: tinggi target ~520 px, tidak terlalu kecil
        ratio_f = 520 / ferizy_img.height
        ferizy_img = ferizy_img.resize((int(ferizy_img.width * ratio_f), 520), Image.Resampling.LANCZOS)
        pos_x = width - ferizy_img.width - 60
        pos_y = height - ferizy_img.height - 60
        poster.paste(ferizy_img, (pos_x, pos_y), ferizy_img)
    except Exception:
        pass

    # Output buffer
    buf_out = io.BytesIO()
    poster.save(buf_out, format='PNG')
    buf_out.seek(0)
    return buf_out

# ==============================
# Konfigurasi Halaman (ASLI, tidak diubah)
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
# Styling: CSS untuk look modern (ASLI, tidak diubah)
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
# Logo di Sidebar (ASLI)
# ==============================
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png",
        width=180
    )
    st.markdown("<h3 style='text-align: center;'>🚀 SLA Payment Analyzer</h3>", unsafe_allow_html=True)

# ==============================
# Path & Assets (ASLI)
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
# Admin password (ASLI)
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
# ====== sla_app.py (Bagian 2: baris 201–400) ======

# ==============================
# Fungsi Utilitas (ASLI)
# ==============================
def seconds_to_sla_format(seconds):
    if pd.isna(seconds):
        return "-"
    seconds = int(seconds)
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    return f"{days}h {hours}j" if days else f"{hours}j"

def parse_sla(col: pd.Series) -> pd.Series:
    """
    Parse format SLA text "Xh Yj" atau "Xj" menjadi detik.
    """
    pattern = re.compile(r'(?:(\d+)h)?\s*(?:(\d+)j)?', re.IGNORECASE)
    def _parse_val(val):
        if pd.isna(val):
            return None
        if isinstance(val, (int, float)):
            return val
        m = pattern.search(str(val))
        if not m:
            return None
        days = int(m.group(1) or 0)
        hours = int(m.group(2) or 0)
        return days * 86400 + hours * 3600
    return col.apply(_parse_val)

# ==============================
# Upload Data (ASLI)
# ==============================
st.sidebar.markdown("### 📤 Upload Data")
if is_admin:
    uploaded_file = st.sidebar.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])
    if uploaded_file is not None:
        with open(DATA_PATH, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("✅ File berhasil diunggah!")
else:
    st.sidebar.info("Login sebagai admin untuk mengunggah data.")

# ==============================
# Load Data (ASLI)
# ==============================
@st.cache_data(show_spinner=False)
def load_data():
    if not os.path.exists(DATA_PATH):
        return None
    try:
        return pd.read_excel(DATA_PATH)
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return None

df = load_data()
if df is None:
    st.warning("⚠️ Belum ada data. Admin dapat mengunggah file Excel di sidebar.")
    st.stop()

# ==============================
# Preprocessing (ASLI)
# ==============================
# Deteksi kolom SLA
sla_cols = [c for c in df.columns if re.search(r'\bSLA\b', c, flags=re.IGNORECASE)]
proses_grafik_cols = [c for c in df.columns if c not in sla_cols and c not in ["Periode", "Vendor", "Jenis Transaksi"]]

# Pastikan kolom Periode ada
periode_col = None
for cand in ["Periode", "periode", "Tahun-Bulan", "Bulan"]:
    if cand in df.columns:
        periode_col = cand
        break
if periode_col is None:
    st.error("Tidak ditemukan kolom Periode di data.")
    st.stop()

# Konversi kolom SLA menjadi detik
for c in sla_cols:
    df[c] = parse_sla(df[c])

# ==============================
# Filter Periode (ASLI)
# ==============================
periode_list = sorted(df[periode_col].dropna().unique())
start_periode, end_periode = st.sidebar.select_slider(
    "Rentang Periode",
    options=periode_list,
    value=(periode_list[0], periode_list[-1])
)
mask = (df[periode_col] >= start_periode) & (df[periode_col] <= end_periode)
df_filtered = df.loc[mask]

# ==============================
# Parsing SLA & Ringkasan (ASLI)
# ==============================
sla_summary = {}
for c in sla_cols:
    avg_seconds = df_filtered[c].mean()
    sla_summary[c] = {
        "average_days": avg_seconds / 86400 if avg_seconds else 0,
        "text": seconds_to_sla_format(avg_seconds)
    }

# KPI ringkasan di Overview
with st.container():
    cols = st.columns(len(sla_summary))
    for idx, (proc, info) in enumerate(sla_summary.items()):
        with cols[idx]:
            st.markdown(f"""
            <div class="card kpi">
                <div class="label">{proc}</div>
                <div class="value">{info['text']}</div>
                <div class="small">({info['average_days']:.2f} hari)</div>
            </div>
            """, unsafe_allow_html=True)

# ==============================
# Tabs Utama (ASLI + tambahan 📥 Download Poster di akhir)
# ==============================
tab_overview, tab_proses, tab_transaksi, tab_vendor, tab_tren, tab_jumlah, tab_poster = st.tabs(
    ["🔍 Overview", "🧮 Per Proses", "🧾 Jenis Transaksi", "🏷️ Vendor", "📈 Tren", "📊 Jumlah Transaksi", "📥 Download Poster"]
)

# ====== sla_app.py (Bagian 3: baris 401–selesai) ======

# ==============================
# Tab Overview (ASLI)
# ==============================
with tab_overview:
    st.subheader("📄 Sampel Data")
    st.dataframe(df_filtered.head(50), use_container_width=True)

# ==============================
# Tab Per Proses (ASLI)
# ==============================
with tab_proses:
    if sla_cols:
        st.subheader("📌 Rata-rata SLA per Proses")
        rata_proses_seconds = df_filtered[sla_cols].mean()
        rata_proses = rata_proses_seconds.reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (detik)"]
        rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(seconds_to_sla_format)
        st.dataframe(rata_proses[["Proses", "Rata-rata SLA"]], use_container_width=True)

        fig2, ax2 = plt.subplots(figsize=(8, 4))
        values_hari = [rata_proses_seconds[col] / 86400 for col in sla_cols]
        ax2.bar(sla_cols, values_hari, color='#75c8ff')
        ax2.set_title("Rata-rata SLA per Proses (hari)")
        ax2.set_ylabel("Hari")
        st.pyplot(fig2)

# ==============================
# Tab Jenis Transaksi (ASLI)
# ==============================
with tab_transaksi:
    if "Jenis Transaksi" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
        transaksi_group = df_filtered.groupby("Jenis Transaksi")[sla_cols].agg(['mean', 'count']).reset_index()
        transaksi_display = pd.DataFrame()
        transaksi_display["Jenis Transaksi"] = transaksi_group["Jenis Transaksi"]
        for col in sla_cols:
            transaksi_display[f"{col} (Rata-rata)"] = transaksi_group[(col, 'mean')].apply(seconds_to_sla_format)
            transaksi_display[f"{col} (Jumlah)"] = transaksi_group[(col, 'count')]
        st.dataframe(transaksi_display, use_container_width=True)

# ==============================
# Tab Vendor (ASLI)
# ==============================
with tab_vendor:
    if "Vendor" in df_filtered.columns:
        vendor_list = sorted(df_filtered["Vendor"].dropna().unique())
        vendor_list_with_all = ["ALL"] + vendor_list
        selected_vendors = st.multiselect("Pilih Vendor", vendor_list_with_all, default=["ALL"])
        if "ALL" in selected_vendors:
            df_vendor_filtered = df_filtered.copy()
        else:
            df_vendor_filtered = df_filtered[df_filtered["Vendor"].isin(selected_vendors)]
        
        if df_vendor_filtered.shape[0] > 0 and sla_cols:
            st.subheader("📌 Rata-rata SLA per Vendor")
            rata_vendor = df_vendor_filtered.groupby("Vendor")[sla_cols].mean().reset_index()
            for col in sla_cols:
                rata_vendor[col] = rata_vendor[col].apply(seconds_to_sla_format)
            st.dataframe(rata_vendor, use_container_width=True)

# ==============================
# Tab Tren (ASLI)
# ==============================
with tab_tren:
    if sla_cols:
        st.subheader("📈 Tren Rata-rata SLA per Periode")
        trend = df_filtered.groupby(periode_col)[sla_cols].mean().reset_index()
        for col in sla_cols:
            fig, ax = plt.subplots()
            ax.plot(trend[periode_col], trend[col] / 86400, marker='o')
            ax.set_title(f"Trend {col} (hari)")
            ax.set_ylabel("Hari")
            ax.set_xlabel("Periode")
            plt.xticks(rotation=45)
            st.pyplot(fig)

# ==============================
# Tab Jumlah Transaksi (ASLI)
# ==============================
with tab_jumlah:
    st.subheader("📊 Jumlah Transaksi per Periode")
    jumlah_transaksi = df_filtered.groupby(periode_col).size().reset_index(name='Jumlah')
    jumlah_transaksi = jumlah_transaksi.sort_values(periode_col)
    total_row = pd.DataFrame({periode_col: ["TOTAL"], 'Jumlah': [jumlah_transaksi['Jumlah'].sum()]})
    jumlah_transaksi = pd.concat([jumlah_transaksi, total_row], ignore_index=True)

    def highlight_total(row):
        return ['font-weight: bold' if row[periode_col] == "TOTAL" else '' for _ in row]

    st.dataframe(jumlah_transaksi.style.apply(highlight_total, axis=1), use_container_width=True)

    fig_trans, ax_trans = plt.subplots(figsize=(8, 4))
    ax_trans.bar(jumlah_transaksi[jumlah_transaksi[periode_col] != "TOTAL"][periode_col],
                 jumlah_transaksi[jumlah_transaksi[periode_col] != "TOTAL"]['Jumlah'],
                 color='#ff9f7f')
    ax_trans.set_title("Jumlah Transaksi per Periode")
    ax_trans.set_xlabel("Periode")
    ax_trans.set_ylabel("Jumlah")
    plt.xticks(rotation=45)
    st.pyplot(fig_trans)

# ==============================
# Tab Download Poster (BARU)
# ==============================
with tab_poster:
    st.subheader("📥 Download Poster SLA")
    sla_text_dict = {}
    for proses in sla_cols:
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



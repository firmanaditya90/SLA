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
import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO   # << tambahkan ini
import base64
import streamlit.components.v1 as components

from datetime import datetime

KPI_FILE = os.path.join("data", "kpi_target.json")
KPI_GITHUB_PATH = "data/kpi_target.json"

def load_kpi():
    """Load target KPI dari GitHub (utama) atau lokal (fallback)."""
    # 1) Coba ambil dari GitHub
    if GITHUB_TOKEN and GITHUB_REPO:
        info = github_get_file_info(KPI_GITHUB_PATH)
        if info and "content" in info:
            try:
                decoded = base64.b64decode(info["content"]).decode()
                return json.loads(decoded).get("target_kpi", None)
            except Exception as e:
                st.error(f"Gagal parse KPI dari GitHub: {e}")
                return None

    # 2) Fallback ke lokal
    if os.path.exists(KPI_FILE):
        try:
            with open(KPI_FILE, "r") as f:
                return json.load(f).get("target_kpi", None)
        except Exception as e:
            st.error(f"Gagal baca KPI lokal: {e}")
            return None
    return None


def save_kpi(value):
    """Simpan target KPI ke lokal & GitHub."""
    data = {"target_kpi": value}

    # 1) Simpan ke lokal
    with open(KPI_FILE, "w") as f:
        json.dump(data, f)

    # 2) Simpan ke GitHub
    if GITHUB_TOKEN and GITHUB_REPO:
        upload_file_to_github(
            json.dumps(data).encode(),
            path=KPI_GITHUB_PATH,
            message="Update Target KPI (via app)"
        )

def format_duration(seconds):
    """Convert detik jadi 'xx hari xx jam xx menit xx detik'"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{days} hari {hours} jam {minutes} menit {secs} detik"

import os
import io
import base64
import requests
import pandas as pd
import streamlit as st
from io import BytesIO

# ============================
# KONFIGURASI
# ============================
DATA_PATH = os.path.join("data", "last_data.xlsx")
ROCKET_GIF_PATH = "rocket.gif"
LOGO_PATH = "asdp_logo.png"

# GitHub config (gunakan secrets di Streamlit)
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]     # contoh: "firmanaditya90/SLA"
    GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")
    GITHUB_PATH = st.secrets.get("GITHUB_PATH", "data/last_data.xlsx")
except Exception:
    GITHUB_TOKEN = GITHUB_REPO = None

_headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

# ============================
# HELPER FUNCTIONS
# ============================
def github_get_file_info(path: str):
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=_headers)
    return r.json() if r.status_code == 200 else None

def download_file_from_github(path: str = None) -> bytes | None:
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    path = path or GITHUB_PATH
    info = github_get_file_info(path)
    if not info:
        return None
    return base64.b64decode(info["content"].encode())

def upload_file_to_github(file_bytes: bytes, path: str = None, message="Update SLA data"):
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    path = path or GITHUB_PATH
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    info = github_get_file_info(path)
    sha = info.get("sha") if info else None
    data = {
        "message": message,
        "content": base64.b64encode(file_bytes).decode(),
        "branch": GITHUB_BRANCH
    }
    if sha:
        data["sha"] = sha
    r = requests.put(url, headers=_headers, json=data)
    return r.json() if r.status_code in (200, 201) else None

@st.cache_data
def read_excel_cached(path, size, mtime):
    return pd.read_excel(path, header=[0, 1])

def gif_b64(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")

def delete_file_from_github(path: str = None, message="Delete SLA data"):
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    path = path or GITHUB_PATH
    info = github_get_file_info(path)
    if not info or "sha" not in info:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    data = {
        "message": message,
        "sha": info["sha"],
        "branch": GITHUB_BRANCH
    }
    r = requests.delete(url, headers=_headers, json=data)
    return r.json() if r.status_code == 200 else None


# ============================
# LOAD DATA
# ============================
df_raw = None

# coba ambil dari GitHub
if GITHUB_TOKEN and GITHUB_REPO:
    with st.spinner("🔄 Mengambil data dari GitHub..."):
        content = download_file_from_github()
        if content:
            df_raw = pd.read_excel(BytesIO(content), header=[0, 1])
            st.info("✅ Data dimuat dari GitHub.")

# fallback lokal
if df_raw is None and os.path.exists(DATA_PATH):
    with st.spinner("🔄 Membaca data terakhir (lokal)..."):
        stat = os.stat(DATA_PATH)
        df_raw = read_excel_cached(DATA_PATH, stat.st_size, stat.st_mtime)
        st.info("ℹ️ Menampilkan data dari upload terakhir (lokal).")

if df_raw is None:
    st.warning("⚠️ Belum ada file yang diunggah.")
    df_raw = None

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
/* Ringkasan Cards */
.summary-card {
  background: rgba(25, 30, 55, 0.55);
  border-radius: 18px;
  padding: 18px 20px;
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 6px 20px rgba(0,0,0,0.25);
  backdrop-filter: blur(10px);
  text-align: center;
  transition: all 0.25s ease;
}
.summary-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 28px rgba(0,0,0,0.35);
}
.summary-icon {
  font-size: 28px;
  margin-bottom: 6px;
  opacity: 0.9;
}
.summary-label {
  font-size: 13px;
  text-transform: uppercase;
  opacity: 0.7;
  margin-bottom: 2px;
}
.summary-value {
  font-size: 26px;
  font-weight: 800;
  background: linear-gradient(90deg, #00eaff, #00ff9d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
/* Modern KPI Cards */
.kpi-card {
  background: rgba(20, 25, 45, 0.55);
  border-radius: 20px;
  padding: 18px 20px;
  border: 1px solid rgba(255,255,255,0.15);
  box-shadow: 0 8px 25px rgba(0,0,0,0.25);
  backdrop-filter: blur(12px);
  text-align: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.35);
}
.kpi-label {
  font-size: 13px;
  opacity: 0.75;
  margin-bottom: 4px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.kpi-value {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(90deg, #00eaff, #00ff9d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.kpi-sub {
  font-size: 12px;
  opacity: 0.65;
}
.kpi-status-on {
  font-size: 24px;
  font-weight: 800;
  color: #00ffb0;
  text-shadow: 0 0 8px rgba(0,255,160,0.7);
}
.kpi-status-off {
  font-size: 24px;
  font-weight: 800;
  color: #ff4f70;
  text-shadow: 0 0 8px rgba(255,80,100,0.7);
}
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
.poster {
  background: linear-gradient(135deg, #1a2a6c, #b21f1f, #fdbb2d);
  border-radius: 20px;
  padding: 25px;
  margin: 20px 0;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.poster-left {
  flex: 1;
  padding-right: 20px;
  border-right: 2px solid rgba(255,255,255,0.4);
}
.poster-right {
  flex: 2;
  padding-left: 20px;
}
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
    
import requests, io

# ==============================
# Sidebar khusus Admin
# ==============================
st.sidebar.markdown("## 🔐 Admin Tools")

# cek password admin
admin_pass = st.sidebar.text_input("Masukkan Password Admin", type="password")

if admin_pass == "AP123":  # <-- ganti dengan password admin beneran
    st.sidebar.success("Login Admin ✅")

    st.sidebar.markdown("### 📥 Download & Gabungkan SLA per Tahun")

    tahun = st.sidebar.number_input("Pilih Tahun", min_value=2020, max_value=2100, value=2025, step=1)
    if st.sidebar.button("Download Data Tahunan"):
        base_url = "https://fidias.asdp.id/anggaran/anggaran_mutasi_json/excel_sla?reqPeriode="
        dfs = []

        progress = st.sidebar.progress(0)
        for m in range(1, 13):
            period = f"{m:02d}{tahun}"
            url = f"{base_url}?reqPeriode={period}"

            try:
                res = requests.get(url)
                if res.ok:
                    df = pd.read_excel(io.BytesIO(res.content))
                    df["Periode"] = period
                    dfs.append(df)
                else:
                    st.sidebar.warning(f"Gagal {period}: {res.status_code}")
            except Exception as e:
                st.sidebar.error(f"Error {period}: {e}")

            progress.progress(m/12.0)

        if dfs:
            df_all = pd.concat(dfs, ignore_index=True)
            st.sidebar.success(f"✅ Data {tahun} berhasil digabung ({len(df_all)} baris)")

            # Simpan ke Excel untuk download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_all.to_excel(writer, index=False, sheet_name=f"SLA_{tahun}")
            st.sidebar.download_button(
                "💾 Download Excel Tahunan",
                data=output.getvalue(),
                file_name=f"SLA_{tahun}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.sidebar.error("Tidak ada data yang berhasil diunduh.")

elif admin_pass != "":
    st.sidebar.error("❌ Password salah!")


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
# Load data terakhir / simpan baru  (TIDAK DIUBAH + FIX: sinkronisasi GitHub)
# ==============================
load_status = st.empty()
if uploaded_file is not None and is_admin:
    with st.spinner("🚀 Mengunggah & menyiapkan data..."):
        if rocket_b64:
            st.markdown(
                f'<div style="text-align:center;"><img src="{rocket_b64}" width="160"/></div>',
                unsafe_allow_html=True
            )
        time.sleep(0.2)

        # Simpan ke lokal
        file_bytes = uploaded_file.getbuffer()
        with open(DATA_PATH, "wb") as f:
            f.write(file_bytes)

        # Upload juga ke GitHub agar semua user sinkron
        result = upload_file_to_github(file_bytes, path=GITHUB_PATH, message="Update SLA data (via app)")
        if result:
            st.success("✅ Data baru berhasil diunggah & disinkronkan ke GitHub!")
        else:
            st.warning("⚠️ Data tersimpan lokal, tapi gagal update ke GitHub.")

# Jika ada file data, baca & tampilkan
if os.path.exists(DATA_PATH):
    # Progress & spinner saat baca file
    with st.spinner("🔄 Membaca data terakhir..."):
        if rocket_b64:
            st.markdown(
                f'<div style="text-align:center;"><img src="{rocket_b64}" width="120"/></div>',
                unsafe_allow_html=True
            )

        # Cache baca excel agar lebih cepat setelah refresh
        @st.cache_data(show_spinner=False)
        def read_excel_cached(path: str, size: int, mtime: float):
            return pd.read_excel(path, header=[0, 1])

        stat = os.stat(DATA_PATH)
        df_raw = read_excel_cached(DATA_PATH, stat.st_size, stat.st_mtime)
        st.info("ℹ️ Menampilkan data dari upload terakhir.")
else:
    st.warning("⚠️ Belum ada file yang diunggah.")
    st.stop()

# Tombol reset (hanya admin) (TIDAK DIUBAH + FIX sinkron GitHub)
with st.sidebar.expander("🛠️ Admin Tools", expanded=False):
    if is_admin and os.path.exists(DATA_PATH):
        if st.button("🗑️ Reset Data (hapus data terakhir)"):
            # Hapus lokal
            os.remove(DATA_PATH)
            
            # Hapus juga di GitHub
            result = delete_file_from_github(path=GITHUB_PATH, message="Reset SLA data (via app)")
            if result:
                st.success("✅ Data berhasil dihapus dari lokal & GitHub.")
            else:
                st.warning("⚠️ Data lokal terhapus, tapi gagal menghapus dari GitHub.")

            st.rerun()


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

import io, base64

def render_sparkline(data, width=180, height=60, color="#00eaff"):
    """Render sparkline sederhana (line chart kecil) sebagai PNG base64"""
    if not data or len(data) == 0:
        return ""
    fig, ax = plt.subplots(figsize=(width/100, height/100))
    ax.plot(data, color=color, linewidth=2, marker='o', markersize=3)
    ax.set_facecolor("none")
    ax.axis('off')
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    buf.seek(0)
    plt.close(fig)
    return f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"

import streamlit.components.v1 as components

# ==============================
# KPI Ringkasan (2x2 Digital Cards + Count-Up FIX)
# ==============================
st.markdown("## 📈 Ringkasan")

jumlah_transaksi = len(df_filtered)
if "TOTAL WAKTU" in available_sla_cols and len(df_filtered) > 0:
    avg_total_days = float(df_filtered["TOTAL WAKTU"].mean()) / 86400
else:
    avg_total_days = 0.0
fastest_process = "Perbendaharaan"
valid_ratio = (df_filtered[periode_col].notna().mean() * 100.0) if len(df_filtered) > 0 else 0.0

html_code = f"""
<style>
.summary-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 18px;
    justify-items: center;
    margin: 15px auto 25px auto;
    max-width: 700px;
}}
.summary-card {{
    width: 100%;
    min-height: 110px;
    border-radius: 14px;
    padding: 12px;
    text-align: center;
    color: #fff;
    font-family: 'Segoe UI', sans-serif;
    box-shadow: 0 4px 14px rgba(0,0,0,0.15);
    transition: all 0.3s ease;
}}
.summary-card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 6px 18px rgba(0,0,0,0.25);
}}
.summary-icon {{ font-size: 22px; margin-bottom: 4px; }}
.summary-label {{ font-size: 13px; font-weight: 500; opacity: 0.9; }}
.summary-value {{ font-size: 22px; font-weight: 700; margin-top: 3px; }}
.card-1 {{ background: linear-gradient(135deg, #4facfe, #00f2fe); }}
.card-2 {{ background: linear-gradient(135deg, #43e97b, #38f9d7); }}
.card-3 {{ background: linear-gradient(135deg, #fa709a, #fee140); }}
.card-4 {{ background: linear-gradient(135deg, #7f00ff, #e100ff); }}
</style>

<div class="summary-grid">
  <div class="summary-card card-1">
    <div class="summary-icon">🧾</div>
    <div class="summary-label">Jumlah Transaksi</div>
    <div id="val1" class="summary-value">0</div>
  </div>
  <div class="summary-card card-2">
    <div class="summary-icon">⏱️</div>
    <div class="summary-label">Rata-rata TOTAL Waktu</div>
    <div id="val2" class="summary-value">0</div>
  </div>
  <div class="summary-card card-3">
    <div class="summary-icon">⚡</div>
    <div class="summary-label">Proses Tercepat</div>
    <div class="summary-value">{fastest_process}</div>
  </div>
  <div class="summary-card card-4">
    <div class="summary-icon">✅</div>
    <div class="summary-label">Kualitas Data</div>
    <div id="val4" class="summary-value">0</div>
  </div>
</div>

<script>
function animateValue(id, start, end, duration, decimals=0, suffix="") {{
    var obj = document.getElementById(id);
    if (!obj) return;
    var range = end - start;
    var current = start;
    var increment = range / 60;
    var stepTime = duration / 60;
    var timer = setInterval(function() {{
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {{
            current = end;
            clearInterval(timer);
        }}
        obj.innerHTML = Number(current).toFixed(decimals) + suffix;
    }}, stepTime);
}}

animateValue("val1", 0, {jumlah_transaksi}, 1000, 0, "");
animateValue("val2", 0, {avg_total_days:.2f}, 1000, 2, " hari");
animateValue("val4", 0, {valid_ratio:.1f}, 1000, 1, "%");
</script>
"""

components.html(html_code, height=350)

# ==============================
# Tabs untuk konten (TIDAK DIUBAH)
# ==============================
tab_overview, tab_proses, tab_transaksi, tab_vendor, tab_tren, tab_jumlah, tab_report = st.tabs(
    ["🔍 Overview", "🧮 Per Proses", "🧾 Jenis Transaksi", "🏷️ Vendor", "📈 Tren", "📊 Jumlah Transaksi", "📥 Download Report"]
)

with tab_overview:
    st.subheader("📊 KPI Verifikasi Dokumen Penagihan")

    # Hitung rata-rata SLA Keuangan
    if "KEUANGAN" in df_filtered.columns and len(df_filtered) > 0:
        avg_keu_seconds = df_filtered["KEUANGAN"].mean()
        avg_keu_days = round(avg_keu_seconds / 86400, 2)  # format desimal hari
        avg_keu_text = seconds_to_sla_format(avg_keu_seconds)  # format hari jam menit detik
    else:
        avg_keu_seconds = None
        avg_keu_days = None
        avg_keu_text = "-"

    # Load target KPI dari file
    saved_kpi = load_kpi()

    # Input Target KPI (hanya admin)
    if is_admin:
        st.markdown("### 🎯 Atur Target KPI (Admin Only)")
        new_kpi = st.number_input(
            "Target KPI (hari, desimal)", 
            min_value=0.0, step=0.1,
            value=saved_kpi if saved_kpi else 1.5,
            key="target_kpi_input"
        )
        if st.button("💾 Simpan Target KPI"):
            save_kpi(new_kpi)
            st.success(f"Target KPI berhasil disimpan: {new_kpi} hari")
            saved_kpi = new_kpi
    else:
        if saved_kpi is None:
            st.info("Belum ada Target KPI yang ditentukan admin.")

    # Layout 3 kolom KPI
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Target KPI Verifikasi Dokumen</div>
                <div class="kpi-value">{saved_kpi if saved_kpi else "-" } hari</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Pencapaian</div>
                <div class="kpi-value">{avg_keu_text}</div>
                <div class="kpi-sub">({avg_keu_days if avg_keu_days is not None else "-"} hari)</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        if saved_kpi and avg_keu_days is not None:
            if avg_keu_days <= saved_kpi:
                st.markdown("""
                    <div class="kpi-card">
                        <div class="kpi-label">Status</div>
                        <div class="kpi-status-on">✅ ON TARGET</div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div class="kpi-card">
                        <div class="kpi-label">Status</div>
                        <div class="kpi-status-off">❌ NOT ON TARGET</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="kpi-card">
                    <div class="kpi-label">Status</div>
                    <div class="kpi-value">-</div>
                </div>
            """, unsafe_allow_html=True)

    # ==============================
    # Tabel Rata-rata SLA Keuangan per Periode (wide format)
    # ==============================
    if "KEUANGAN" in df_filtered.columns and len(df_filtered) > 0:
        st.markdown("<hr class='soft'/>", unsafe_allow_html=True)
        st.subheader("📊 Tabel Rata-rata SLA Keuangan (Hari) per Periode")

        # Hitung rata-rata per periode
        trend_keu = df_filtered.groupby(df_filtered[periode_col].astype(str))["KEUANGAN"].mean().reset_index()
        trend_keu["PERIODE_SORTED"] = pd.Categorical(trend_keu[periode_col], categories=selected_periode, ordered=True)
        trend_keu = trend_keu.sort_values("PERIODE_SORTED")

        # Konversi ke hari desimal
        trend_keu["Rata-rata SLA (hari)"] = (trend_keu["KEUANGAN"] / 86400).round(2)

        # Bentuk tabel wide format
        table_data = pd.DataFrame(
            [trend_keu["Rata-rata SLA (hari)"].tolist()],
            columns=trend_keu[periode_col].tolist(),
            index=["SLA Verifikasi Dokumen Penagihan"]
        )

        # Tampilkan tabel dengan styling
        st.dataframe(table_data.style.format("{:.2f}"), use_container_width=True)

    # ==============================
    # Grafik SLA Keuangan per Periode (dengan label angka)
    # ==============================
    if "KEUANGAN" in df_filtered.columns and len(df_filtered) > 0:
        st.markdown("<hr class='soft'/>", unsafe_allow_html=True)
        st.subheader("📈 Trend Rata-rata SLA Keuangan per Periode")

        # Hitung rata-rata per periode
        trend_keu = df_filtered.groupby(df_filtered[periode_col].astype(str))["KEUANGAN"].mean().reset_index()
        trend_keu["PERIODE_SORTED"] = pd.Categorical(trend_keu[periode_col], categories=selected_periode, ordered=True)
        trend_keu = trend_keu.sort_values("PERIODE_SORTED")

        # Konversi ke hari desimal
        trend_keu["Rata-rata SLA (hari)"] = (trend_keu["KEUANGAN"] / 86400).round(2)

        # Plot line chart dengan label di dot
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(trend_keu[periode_col], trend_keu["Rata-rata SLA (hari)"], marker='o', color='#1f77b4')

        # Label angka
        for i, val in enumerate(trend_keu["Rata-rata SLA (hari)"]):
            ax.text(i, val, f"{val}", ha='center', va='bottom', fontsize=9, color="black", weight="bold")

        ax.set_title("Trend Rata-rata SLA Keuangan per Periode")
        ax.set_xlabel("Periode")
        ax.set_ylabel("Rata-rata SLA (hari)")
        ax.grid(True, linestyle='--', alpha=0.7)

        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')

        st.pyplot(fig)
    else:
        st.info("Tidak ada kolom SLA Keuangan yang bisa ditampilkan.")

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
    import plotly.express as px
    import streamlit.components.v1 as components

    # ==============================
    # Helper: format detik -> "x hari x jam x menit x detik"
    # ==============================
    def fmt_duration(seconds):
        if pd.isna(seconds):
            return "-"
        try:
            s = int(round(float(seconds)))
        except Exception:
            return "-"
        days = s // 86400
        s %= 86400
        hours = s // 3600
        s %= 3600
        minutes = s // 60
        secs = s % 60
        return f"{days} hari {hours} jam {minutes} menit {secs} detik"

    if "NAMA VENDOR" in df_filtered.columns:
        # ==============================
        # 1) FILTER KATEGORI
        # ==============================
        kategori_filter = st.selectbox(
            "Pilih Kategori Vendor",
            ["ALL", "ALL CABANG", "ALL PUSAT", "ALL VENDOR"]
        )

        if kategori_filter == "ALL CABANG":
            df_vendor_filtered = df_filtered[
                df_filtered["NAMA VENDOR"].astype(str).str.upper().str.contains("GM CABANG", na=False)
            ].copy()
            df_vendor_filtered["SLA_USED"] = pd.to_numeric(df_vendor_filtered["FUNGSIONAL"], errors="coerce")

        elif kategori_filter == "ALL PUSAT":
            nama = df_filtered["NAMA VENDOR"].astype(str)
            mask_pusat = nama.str[:3].eq("110") & (nama.str.len() >= 12) & nama.str[11].eq("-")
            df_vendor_filtered = df_filtered[mask_pusat].copy()
            df_vendor_filtered["SLA_USED"] = pd.to_numeric(df_vendor_filtered["FUNGSIONAL"], errors="coerce")

        elif kategori_filter == "ALL VENDOR":
            nama = df_filtered["NAMA VENDOR"].astype(str)
            mask_cabang = nama.str.upper().str.contains("GM CABANG", na=False)
            mask_pusat = nama.str[:3].eq("110") & (nama.str.len() >= 12) & nama.str[11].eq("-")
            df_vendor_filtered = df_filtered[~(mask_cabang | mask_pusat)].copy()
            df_vendor_filtered["SLA_USED"] = pd.to_numeric(df_vendor_filtered["VENDOR"], errors="coerce")

        else:  # "ALL"
            df_vendor_filtered = df_filtered.copy()

            def pick_sla(row):
                nama = str(row["NAMA VENDOR"]).upper()
                if "GM CABANG" in nama:
                    return row.get("FUNGSIONAL")
                elif nama.startswith("110") and len(nama) >= 12 and nama[11] == "-":
                    return row.get("FUNGSIONAL")
                else:
                    return row.get("VENDOR")

            df_vendor_filtered["SLA_USED"] = df_vendor_filtered.apply(pick_sla, axis=1)
            df_vendor_filtered["SLA_USED"] = pd.to_numeric(df_vendor_filtered["SLA_USED"], errors="coerce")

        df_vendor_filtered["SLA_USED_FMT"] = df_vendor_filtered["SLA_USED"].apply(fmt_duration)

        # ==============================
        # 2) FILTER VENDOR
        # ==============================
        vendor_list = sorted(df_vendor_filtered["NAMA VENDOR"].dropna().astype(str).unique())
        vendor_list_with_all = ["ALL"] + vendor_list
        selected_vendors = st.multiselect("Pilih Vendor", vendor_list_with_all, default=[])

        if not selected_vendors:
            st.info("Silakan pilih vendor untuk melihat analisis.")
        else:
            if "ALL" in selected_vendors:
                selected_vendors = vendor_list
            df_vendor_filtered = df_vendor_filtered[df_vendor_filtered["NAMA VENDOR"].isin(selected_vendors)]

            # ==============================
            # 3) Kartu Digital Ringkasan
            # ==============================
            total_vendor = df_vendor_filtered["NAMA VENDOR"].nunique()
            total_transaksi = len(df_vendor_filtered)
            rata_sla_global_hari = float(df_vendor_filtered["SLA_USED"].mean() / 86400) if df_vendor_filtered["SLA_USED"].notna().any() else 0.0

            card_template = f"""
            <style>
            .card-container{{display:flex;gap:20px;justify-content:center;margin-top:20px;}}
            .card{{flex:1;padding:20px;border-radius:16px;text-align:center;color:white;
            box-shadow:0 4px 12px rgba(0,0,0,0.2);transition:transform 0.3s ease;}}
            .card:hover{{transform:scale(1.05);box-shadow:0 8px 20px rgba(0,0,0,0.3);}}
            .card-icon{{font-size:40px;}}.card-title{{font-size:18px;font-weight:600;}}.card-value{{font-size:28px;font-weight:800;}}
            </style>
            <div class="card-container">
              <div class="card" style="background:linear-gradient(135deg,#00eaff,#007bff);">
                <div class="card-icon">🏢</div><div class="card-title">Total Vendor</div><div id="vendorCount" class="card-value">0</div>
              </div>
              <div class="card" style="background:linear-gradient(135deg,#ff9a9e,#ff4f70);">
                <div class="card-icon">📄</div><div class="card-title">Total Transaksi</div><div id="trxCount" class="card-value">0</div>
              </div>
              <div class="card" style="background:linear-gradient(135deg,#42e695,#3bb2b8);">
                <div class="card-icon">⏱️</div><div class="card-title">Rata-rata SLA (Hari)</div><div id="slaCount" class="card-value">0.00</div>
              </div>
            </div>
            <script>
            function animateValue(id,start,end,duration){{
                var range=end-start; var current=start;
                var increment=range/100; var stepTime=Math.abs(Math.floor(duration/100));
                var obj=document.getElementById(id);
                var timer=setInterval(function(){{
                    current+=increment;
                    if ((increment>0 && current>=end)||(increment<0&&current<=end)){{current=end;clearInterval(timer);}}
                    obj.innerHTML=current.toFixed(2);
                }},stepTime);}}
            animateValue("vendorCount",0,{total_vendor},1000);
            animateValue("trxCount",0,{total_transaksi},1200);
            animateValue("slaCount",0,{round(rata_sla_global_hari,2)},1500);
            </script>
            """
            components.html(card_template, height=250)

            # ==============================
            # 4) Tabel Data Detail
            # ==============================
            if df_vendor_filtered.shape[0] > 0:
                st.subheader("📋 Data Terfilter")
                st.dataframe(df_vendor_filtered, use_container_width=True)

                # ==============================
                # 5) Agregasi per Vendor
                # ==============================
                rata_vendor = (
                    df_vendor_filtered
                    .groupby("NAMA VENDOR", dropna=True)["SLA_USED"]
                    .mean()
                    .reset_index()
                )
                rata_vendor["SLA_USED"] = pd.to_numeric(rata_vendor["SLA_USED"], errors="coerce")
                rata_vendor["SLA (hari)"] = rata_vendor["SLA_USED"] / 86400.0
                rata_vendor["SLA (format)"] = rata_vendor["SLA_USED"].apply(fmt_duration)

                # ==============================
                # 6) Leaderboard Vendor
                # ==============================
                st.subheader("⚡ Leaderboard SLA Vendor")
                lb = rata_vendor.dropna(subset=["SLA_USED"]).copy()

                if not lb.empty:
                    lb_sorted = lb.sort_values("SLA_USED", ascending=True).reset_index(drop=True)
                    min_sla = float(lb_sorted["SLA_USED"].min())
                    max_sla = float(lb_sorted["SLA_USED"].max())

                    rows = ""
                    for i, row in lb_sorted.iterrows():
                        nama = row["NAMA VENDOR"]
                        sla_used = float(row["SLA_USED"])
                        sla_hari = sla_used / 86400.0

                        badge = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🚨" if i == len(lb_sorted)-1 else ""

                        ratio = (sla_used - min_sla) / (max_sla - min_sla + 1e-9)
                        red = int(255 * ratio)
                        green = int(255 * (1 - ratio))
                        color = f"rgba({red},{green},120,0.85)"
                        progress_pct = int((sla_used / (max_sla+1e-9)) * 100)

                        rows += f"""
                        <div style='padding:10px 14px;border-radius:12px;background:{color};margin-bottom:8px;'>
                            <div style='display:flex;justify-content:space-between;font-weight:600;color:white;'>
                                <span>{badge} {nama}</span>
                                <span>{sla_hari:.2f} hari</span>
                            </div>
                            <div style="width:100%;background:#333;border-radius:6px;margin-top:6px;">
                                <div style="width:{progress_pct}%;background:#00eaff;height:8px;border-radius:6px;"></div>
                            </div>
                        </div>
                        """

                    leaderboard_html = f"""
                    <div style="max-height:500px;overflow-y:auto;display:flex;flex-direction:column;">
                        {rows}
                    </div>
                    """
                    components.html(leaderboard_html, height=600)

                # ==============================
                # 7) Grafik & Drilldown
                # ==============================
                st.subheader("📊 Interaktif SLA per Vendor")
                if not rata_vendor.empty and rata_vendor["SLA (hari)"].notna().any():
                    fig = px.bar(
                        rata_vendor, x="NAMA VENDOR", y="SLA (hari)",
                        color="SLA (hari)", color_continuous_scale="Blues",
                        title="Rata-rata SLA per Vendor"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                clicked_vendor = st.selectbox("🔍 Pilih vendor untuk drill-down detail:",
                                              rata_vendor["NAMA VENDOR"].tolist() if not rata_vendor.empty else [])
                if clicked_vendor:
                    df_vendor_detail = df_vendor_filtered[df_vendor_filtered["NAMA VENDOR"] == clicked_vendor]
                    if "JENIS TRANSAKSI" in df_vendor_detail.columns and not df_vendor_detail.empty:
                        st.markdown(f"### 📊 Detail SLA — {clicked_vendor}")

                        transaksi_group = (
                            df_vendor_detail
                            .groupby("JENIS TRANSAKSI")["SLA_USED"]
                            .mean()
                            .reset_index()
                        )
                        transaksi_group["SLA (hari)"] = transaksi_group["SLA_USED"] / 86400.0
                        transaksi_group["SLA (format)"] = transaksi_group["SLA_USED"].apply(fmt_duration)
                        st.dataframe(transaksi_group, use_container_width=True)

                        fig2 = px.bar(transaksi_group, x="SLA (hari)", y="JENIS TRANSAKSI",
                                      orientation="h", color="SLA (hari)", color_continuous_scale="Viridis")
                        st.plotly_chart(fig2, use_container_width=True)

                        jumlah_per_transaksi = (
                            df_vendor_detail
                            .groupby("JENIS TRANSAKSI")
                            .size()
                            .reset_index(name="Jumlah")
                        )
                        fig_pie = px.pie(jumlah_per_transaksi, values="Jumlah", names="JENIS TRANSAKSI")
                        st.plotly_chart(fig_pie, use_container_width=True)

                # ==============================
                # 8) Distribusi Multi Vendor
                # ==============================
                if len(selected_vendors) > 1 and "JENIS TRANSAKSI" in df_vendor_filtered.columns:
                    st.subheader(f"📊 Distribusi Transaksi — {len(selected_vendors)} Vendor")
                    jumlah_multi = (
                        df_vendor_filtered.groupby(["NAMA VENDOR","JENIS TRANSAKSI"])
                        .size()
                        .reset_index(name="Jumlah")
                    )
                    pivot_jumlah = jumlah_multi.pivot(index="NAMA VENDOR", columns="JENIS TRANSAKSI", values="Jumlah").fillna(0)
                    st.dataframe(pivot_jumlah, use_container_width=True)

            else:
                st.info("Tidak ada data untuk vendor yang dipilih.")
    else:
        st.info("Kolom 'NAMA VENDOR' tidak ditemukan.")

with tab_tren:
    if available_sla_cols:
        st.subheader("📈 Trend Rata-rata SLA per Periode")
        
        # Hitung rata-rata per periode
        trend = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()
        trend["PERIODE_SORTED"] = pd.Categorical(trend[periode_col], categories=selected_periode, ordered=True)
        trend = trend.sort_values("PERIODE_SORTED").reset_index(drop=True)

        # Tambahkan kolom nomor urut
        trend.insert(0, "No", range(1, len(trend) + 1))

        # Buat tampilan dengan format detik -> string
        trend_display = trend.copy()
        for col in available_sla_cols:
            trend_display[col] = trend_display[col].apply(seconds_to_sla_format)

        # Hapus kolom bantu & sembunyikan index Pandas
        st.dataframe(
            trend_display.drop(columns=["PERIODE_SORTED"]).set_index("No").style.hide(axis="index"),
            use_container_width=True
        )

        # ==============================
        # Grafik TOTAL WAKTU
        # ==============================
        if "TOTAL WAKTU" in available_sla_cols:
            fig, ax = plt.subplots(figsize=(10, 5))
            y_values_days = trend["TOTAL WAKTU"] / 86400
            x_values = trend[periode_col]

            ax.plot(x_values, y_values_days, marker='o', label="TOTAL WAKTU", color='#9467bd')

            # Tambahkan angka di setiap dot (2 angka desimal)
            for x, y in zip(x_values, y_values_days):
                ax.text(x, y, f"{y:.2f}", ha='center', va='bottom', fontsize=9, color="black", weight="bold")

            ax.set_title("Trend Rata-rata SLA TOTAL WAKTU per Periode")
            ax.set_xlabel("Periode")
            ax.set_ylabel("Rata-rata SLA (hari)")
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()

            for label in ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')

            st.pyplot(fig)

        # ==============================
        # Grafik per proses
        # ==============================
        if proses_grafik_cols:
            fig3, axs = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
            fig3.suptitle("Trend Rata-rata SLA per Proses")
            axs = axs.flatten()

            for i, col in enumerate(proses_grafik_cols):
                y_days = trend[col] / 86400
                x_values = trend[periode_col]

                axs[i].plot(x_values, y_days, marker='o', color='#75c8ff')

                # Tambahkan angka di setiap dot (2 angka desimal)
                for x, y in zip(x_values, y_days):
                    axs[i].text(x, y, f"{y:.2f}", ha='center', va='bottom', fontsize=8, color="black")

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
# Poster A4 Generator (Gradient BG + Glassmorphism Card)
# ==========================================================
def generate_poster_A4(
    sla_text_dict, rata_proses_seconds, df_proses,
    image_url, periode_range_text,
    df_filtered, periode_col, selected_periode
):
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
    except:
        pass

    # ---------- Logo Danantara ----------
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "Danantara.png")
        logo_img = Image.open(logo_path).convert("RGBA")
        scale = (W * 0.2) / logo_img.width
        logo_img = logo_img.resize((int(logo_img.width*scale), int(logo_img.height*scale)), Image.Resampling.LANCZOS)
        bg.paste(logo_img, (80, 80), logo_img)
    except:
        pass

    # ---------- Logo Transformation (atas kiri bawah) ----------
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "Transformation.png")
        logo_img = Image.open(logo_path).convert("RGBA")
        scale = (W * 0.2) / logo_img.width
        logo_img = logo_img.resize((int(logo_img.width*scale), int(logo_img.height*scale)), Image.Resampling.LANCZOS)
        bg.paste(logo_img, (80, 3000), logo_img)
    except:
        pass

    # ---------- Judul ----------
    title_text = "SLA DOKUMEN PENAGIHAN"
    try:
        font_title = ImageFont.truetype("Anton-Regular.ttf", 200)
    except:
        font_title = ImageFont.load_default()
    bbox_title = draw.textbbox((0, 0), title_text, font=font_title)
    title_w = bbox_title[2] - bbox_title[0]
    title_h = bbox_title[3] - bbox_title[1]
    title_y = int(H * 0.10)
    draw.text(((W - title_w) // 2, title_y), title_text, fill="black", font=font_title)

    # ---------- Periode ----------
    max_width = int(W * 0.8)
    font_size = 140
    try:
        font_periode = ImageFont.truetype("Anton-Regular.ttf", font_size)
    except:
        font_periode = ImageFont.load_default()
    while True:
        bbox_periode = draw.textbbox((0, 0), periode_range_text, font=font_periode)
        periode_w = bbox_periode[2] - bbox_periode[0]
        periode_h = bbox_periode[3] - bbox_periode[1]
        if periode_w <= max_width or font_size <= 40:
            break
        font_size -= 10
        try:
            font_periode = ImageFont.truetype("Anton-Regular.ttf", font_size)
        except:
            font_periode = ImageFont.load_default()
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
        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
        buf.seek(0); plt.close(fig)
        chart_img = Image.open(buf).convert("RGBA")
        max_chart_width = int(W * 0.65)
        scale = max_chart_width / chart_img.width
        chart_img = chart_img.resize(
            (int(chart_img.width * scale), int(chart_img.height * scale)),
            Image.Resampling.LANCZOS
        )
    except Exception as e:
        print("Gagal render chart:", e)

    # ---------- Render Tabel SLA ----------
    table_img = None
    try:
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.axis('off')
        tbl = ax.table(
            cellText=df_proses.values,
            colLabels=df_proses.columns,
            rowLabels=df_proses.index,
            loc='center'
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(12)
        tbl.scale(1.3, 1.3)
        tbl.auto_set_column_width([0, 1])
        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
        buf.seek(0); plt.close(fig)
        table_img = Image.open(buf).convert("RGBA")
        max_tbl_width = int(W * 0.30)
        scale = max_tbl_width / table_img.width
        table_img = table_img.resize(
            (int(table_img.width * scale), int(table_img.height * scale)),
            Image.Resampling.LANCZOS
        )
    except Exception as e:
        print("Gagal render tabel SLA:", e)

    # ---------- Glassmorphism Card ----------
    card_margin_x = 80
    card_top = line_y + 20
    content_height = max(chart_img.height if chart_img else 0, table_img.height if table_img else 0)
    card_bottom = card_top + content_height + 80
    card_box = (card_margin_x, card_top, W - card_margin_x, card_bottom)

    # Blur background dalam area card
    region = bg.crop(card_box).filter(ImageFilter.GaussianBlur(20))
    bg.paste(region, card_box)

    # Semi transparan overlay
    card_overlay = Image.new("RGBA", bg.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(card_overlay)
    overlay_draw.rounded_rectangle(
        card_box,
        radius=40,
        outline=(255, 255, 255, 200),
        width=4,
        fill=(255, 255, 255, 100)
    )
    bg = Image.alpha_composite(bg.convert("RGBA"), card_overlay)
    draw = ImageDraw.Draw(bg)

    if chart_img:
        pos_x = card_margin_x + 50
        pos_y = card_top + 40
        bg.paste(chart_img, (pos_x, pos_y), chart_img)
    if table_img:
        pos_x = W - table_img.width - card_margin_x - 50
        pos_y = card_top + 40
        bg.paste(table_img, (pos_x, pos_y), table_img)    # ---------- Kemudi + On Target ----------
    try:
        kemudi_path = os.path.join(os.path.dirname(__file__), "Kemudi.png")
        kemudi_img = Image.open(kemudi_path).convert("RGBA")
        target_width = int(W * 0.18)
        scale = target_width / kemudi_img.width
        kemudi_img = kemudi_img.resize((target_width, int(kemudi_img.height * scale)), Image.Resampling.LANCZOS)
        pos_x = W - card_margin_x - kemudi_img.width - 50
        pos_y = card_top + table_img.height + 30
        bg.paste(kemudi_img, (pos_x, pos_y), kemudi_img)
        font_target = ImageFont.truetype(os.path.join(os.path.dirname(__file__), "Anton-Regular.ttf"), 120)
        text = "ON TARGET"
        bbox = draw.textbbox((0, 0), text, font=font_target)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        text_x = pos_x + (kemudi_img.width - tw) // 2
        text_y = pos_y + kemudi_img.height + 1
        draw.text((text_x, text_y), text, font=font_target, fill=(0, 150, 0))
    except Exception as e:
        print("Gagal render Kemudi/On Target:", e)

    # ---------- Footer + Garis Tengah + Grafik & Tabel Jumlah Transaksi ----------
    try:
        footer_path = os.path.join(os.path.dirname(__file__), "Footer.png")
        footer_img = Image.open(footer_path).convert("RGBA")
        scale = W / footer_img.width
        footer_img = footer_img.resize((W, int(footer_img.height * scale)), Image.Resampling.LANCZOS)
        footer_y = H - footer_img.height

        # 1. Garis tengah
        overlay = Image.new("RGBA", bg.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        center_x = W // 2
        overlay_draw.line((center_x, card_bottom, center_x, H), fill="black", width=15)
        bg = Image.alpha_composite(bg, overlay)

        # 2. Grafik jumlah transaksi
        trans_img = None
        pos_y_trans = card_bottom + 50
        try:
            jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name='Jumlah')
            jumlah_transaksi = jumlah_transaksi.sort_values(
                by=periode_col,
                key=lambda x: pd.Categorical(x, categories=selected_periode, ordered=True)
            )
            fig_trans, ax_trans = plt.subplots(figsize=(8, 5))
            colors = plt.cm.viridis(range(len(jumlah_transaksi)))
            ax_trans.bar(jumlah_transaksi[periode_col], jumlah_transaksi['Jumlah'], color=colors)
            ax_trans.set_title("Jumlah Transaksi per Periode", fontsize=28, weight="bold")
            ax_trans.set_xlabel("Periode")
            ax_trans.set_ylabel("Jumlah")
            ax_trans.grid(axis='y', linestyle='--', alpha=0.6)
            for label in ax_trans.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')
            buf = io.BytesIO()
            fig_trans.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
            buf.seek(0); plt.close(fig_trans)
            trans_img = Image.open(buf).convert("RGBA")
            max_width = int(W * 0.40)
            max_height = H - card_bottom - footer_img.height - 400
            scale = min(max_width / trans_img.width, max_height / trans_img.height)
            trans_img = trans_img.resize((int(trans_img.width * scale), int(trans_img.height * scale)), Image.Resampling.LANCZOS)
            pos_x = 150
            bg.paste(trans_img, (pos_x, pos_y_trans), trans_img)
        except Exception as e:
            print("⚠️ Gagal render grafik jumlah transaksi:", e)

        # 2b. Tabel jumlah transaksi (lebih keren, dinaikkan sedikit)
        try:
            jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name='Jumlah')
            jumlah_transaksi = jumlah_transaksi.sort_values(
                by=periode_col,
                key=lambda x: pd.Categorical(x, categories=selected_periode, ordered=True)
            )
            total_row = pd.DataFrame({periode_col: ["TOTAL"], "Jumlah": [jumlah_transaksi["Jumlah"].sum()]})
            jumlah_transaksi = pd.concat([jumlah_transaksi, total_row], ignore_index=True)

            fig_tbl, ax_tbl = plt.subplots(figsize=(6, 4))
            ax_tbl.axis("off")
            table = ax_tbl.table(
                cellText=jumlah_transaksi.values,
                colLabels=jumlah_transaksi.columns,
                loc="center",
                cellLoc="center"
            )
            table.auto_set_font_size(False)
            table.set_fontsize(16)
            table.scale(1.5, 1.5)

            # Header style
            for j in range(len(jumlah_transaksi.columns)):
                cell = table[(0, j)]
                cell.set_fontsize(18)
                cell.set_text_props(weight="bold", color="white")
                cell.set_facecolor("#1f77b4")

            # Row styling
            for i in range(1, len(jumlah_transaksi) + 1):
                for j in range(len(jumlah_transaksi.columns)):
                    cell = table[(i, j)]
                    if i % 2 == 0:
                        cell.set_facecolor("#f2f2f2")
                    else:
                        cell.set_facecolor("#ffffff")
                    if jumlah_transaksi.iloc[i-1, 0] == "TOTAL":
                        cell.set_text_props(weight="bold", color="darkred")
                        cell.set_facecolor("#e6e6e6")

            buf = io.BytesIO()
            fig_tbl.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
            buf.seek(0); plt.close(fig_tbl)
            tbl_img = Image.open(buf).convert("RGBA")
            max_width = int(W * 0.40)
            scale = max_width / tbl_img.width
            tbl_img = tbl_img.resize((int(tbl_img.width * scale), int(tbl_img.height * scale)), Image.Resampling.LANCZOS)
            pos_x = 150
            if trans_img:
                pos_y = pos_y_trans + trans_img.height + 20  # lebih dekat ke grafik
            else:
                pos_y = pos_y_trans
            bg.paste(tbl_img, (pos_x, pos_y), tbl_img)
        except Exception as e:
            print("⚠️ Gagal render tabel jumlah transaksi:", e)

        # 3. Footer
        bg.paste(footer_img, (0, footer_y), footer_img)

        # 4. Captain Ferizy
        ferizy_path = os.path.join(os.path.dirname(__file__), "Captain Ferizy.png")
        ferizy_img = Image.open(ferizy_path).convert("RGBA")
        scale = (footer_img.height * 2) / ferizy_img.height
        ferizy_img = ferizy_img.resize((int(ferizy_img.width * scale), int(ferizy_img.height * scale)), Image.Resampling.LANCZOS)
        pos_x = W - ferizy_img.width
        pos_y = H - ferizy_img.height
        bg.paste(ferizy_img, (pos_x, pos_y), ferizy_img)

        # 5. Transformation (depan footer, kiri bawah)
        Transformation_path = os.path.join(os.path.dirname(__file__), "Transformation.png")
        Transformation_img = Image.open(Transformation_path).convert("RGBA")
        scale = (footer_img.height * 0.35) / Transformation_img.height
        Transformation_img = Transformation_img.resize((int(Transformation_img.width * scale), int(Transformation_img.height * scale)), Image.Resampling.LANCZOS)
        pos_x = 0
        pos_y = H - Transformation_img.height - 40
        bg.paste(Transformation_img, (pos_x, pos_y), Transformation_img)

    except Exception as e:
        print("⚠️ Gagal render Footer/Ferizy/Transformation:", e)

    out = io.BytesIO()
    bg.save(out, format="PNG")
    out.seek(0)
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



# =====================[ HELPERS PDF ]=====================
# ====================== IMPORTS ======================
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak
)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import io, matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ====================== LOGO ASSET ======================
LOGO_LEFT_URL  = "https://raw.githubusercontent.com/firmanaditya90/SLA/main/Danantara.png"
LOGO_RIGHT_URL = "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png"
LOGO_ASDP_URL  = LOGO_RIGHT_URL  # cover logo center

# ====================== STYLES ======================
_styles = getSampleStyleSheet()
_styles.add(ParagraphStyle(name="CoverTitle", fontName="Helvetica-Bold", fontSize=30, leading=34, alignment=1, spaceAfter=12))
_styles.add(ParagraphStyle(name="CoverSub",   fontName="Helvetica-Bold", fontSize=16, leading=20, alignment=1, spaceAfter=20))
_styles.add(ParagraphStyle(name="HeadingCenter", fontName="Helvetica-Bold", fontSize=20, leading=24, alignment=1, spaceAfter=12, textColor=colors.HexColor("#0f172a")))
_styles.add(ParagraphStyle(name="TOCItem", fontName="Helvetica", fontSize=13, leading=18, alignment=0, leftIndent=0))
_styles.add(ParagraphStyle(name="Narr", fontName="Helvetica", fontSize=11, leading=15, alignment=1, spaceBefore=8, spaceAfter=8))
_styles.add(ParagraphStyle(name="KPI", fontName="Helvetica-Bold", fontSize=12, leading=15, alignment=1, spaceAfter=10))
_styles.add(ParagraphStyle(name="SmallRight", fontName="Helvetica", fontSize=9, alignment=2))

# ====================== HELPERS ======================
def _img_reader(url):
    try: return ImageReader(url)
    except: return None

def _plot_to_rlimage(fig, w_cm=11, h_cm=6, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return RLImage(buf, width=w_cm*cm, height=h_cm*cm)

def _nice_table(data, colWidths=None, header_bg="#0ea5e9", align="CENTER"):
    tbl = Table(data, colWidths=colWidths, hAlign=align)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor(header_bg)),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,0),11),
        ("ALIGN",(0,0),(-1,0),"CENTER"),
        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
        ("FONTSIZE",(0,1),(-1,-1),10),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    return tbl

def _toc_row(title, page, dots_len=80):
    dots = "." * dots_len
    tbl = Table(
        [[Paragraph(title, _styles["TOCItem"]),
          Paragraph(dots, _styles["TOCItem"]),
          Paragraph(page, _styles["TOCItem"])]],
        colWidths=[12*cm, 11*cm, 1.5*cm],
        hAlign="CENTER"
    )
    tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("FONTSIZE",(0,0),(-1,-1),12),
    ]))
    return tbl

# ====================== NARRASI HELPERS ======================
def _narasi_overview(avg_days, kpi_target_days):
    if avg_days is None: return "Data KEUANGAN tidak tersedia."
    if kpi_target_days is None: return f"Rata-rata SLA KEUANGAN {avg_days:.2f} hari."
    status = "di bawah" if avg_days <= kpi_target_days else "di atas"
    return f"Rata-rata SLA KEUANGAN {avg_days:.2f} hari, {status} target KPI {kpi_target_days:.2f} hari."

def _narasi_top_bottom(series_days):
    if series_days is None or len(series_days)==0: return "Tidak ada data."
    s = pd.Series(series_days).dropna().sort_values()
    if s.empty: return "Tidak ada data."
    lo, hi = s.index[0], s.index[-1]
    return f"Proses tercepat: {lo} ({s.iloc[0]:.2f} hari). Terlama: {hi} ({s.iloc[-1]:.2f} hari)."

def _narasi_tren(df_days):
    desc=[]
    for col in df_days.columns:
        s = df_days[col].dropna()
        if len(s)>=2:
            delta = s.iloc[-1]-s.iloc[0]
            arah = "naik" if delta>0 else ("turun" if delta<0 else "stabil")
            desc.append(f"{col}: {arah} {abs(delta):.2f} hari")
    return "Ringkasan tren: " + "; ".join(desc) if desc else "Tren belum dapat dianalisis."

def _narasi_transaksi(trans_df):
    if trans_df.empty: return "Tidak ada data transaksi."
    peak = trans_df.loc[trans_df["Jumlah"].idxmax()]
    low  = trans_df.loc[trans_df["Jumlah"].idxmin()]
    mean = trans_df["Jumlah"].mean()
    return f"Rata-rata transaksi {mean:.1f}. Tertinggi {peak['Periode']} ({int(peak['Jumlah'])}), terendah {low['Periode']} ({int(low['Jumlah'])})."

# ====================== HEADER & FOOTER ======================
def _first_page(canvas, doc):
    pw, ph = landscape(A4)
    try:
        canvas.drawImage(_img_reader(LOGO_ASDP_URL), pw/2 - 3*cm, ph - 10*cm,
                         width=6*cm, height=6*cm, mask='auto')
    except: pass

def _later_pages(canvas, doc):
    pw, ph = landscape(A4)
    try: canvas.drawImage(_img_reader(LOGO_LEFT_URL), 1.5*cm, ph - 3.6*cm, width=4.5*cm, height=1.6*cm, mask='auto')
    except: pass
    try: canvas.drawImage(_img_reader(LOGO_RIGHT_URL), pw - 5.1*cm, ph - 3.6*cm, width=3*cm, height=3*cm, mask='auto')
    except: pass
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(pw - 1.6*cm, 1.05*cm, f"Halaman {doc.page}")

# ====================== MAIN FUNCTION ======================
def generate_pdf_report_v6(df_ord, selected_periode, periode_col, available_sla_cols, proses_cols, kpi_target_days=None):
    df = df_ord.copy()
    df[periode_col] = df[periode_col].astype(str)
    categories = [str(p) for p in selected_periode]
    df[periode_col] = pd.Categorical(df[periode_col], categories=categories, ordered=True)
    df_filt = df[df[periode_col].notna()].sort_values(periode_col)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=3.6*cm, bottomMargin=2*cm)
    story = []

    # === Cover
    story.append(Spacer(1, 7*cm))
    story.append(Paragraph("LAPORAN SLA VERIFIKASI DOKUMEN PENAGIHAN PT ASDP INDONESIA FERRY (PERSERO)", _styles["CoverTitle"]))
    if selected_periode:
        story.append(Paragraph(f"PERIODE: {str(selected_periode[0]).upper()} – {str(selected_periode[-1]).upper()}", _styles["CoverSub"]))
    story.append(PageBreak())

    # === TOC
    story.append(Paragraph("DAFTAR ISI", _styles["HeadingCenter"]))
    story.append(Spacer(1,0.6*cm))
    toc_map=[("OVERVIEW","3"),("SLA PER PROSES","4"),("SLA PER JENIS TRANSAKSI","5"),
             ("TREN SLA","6"),("JUMLAH TRANSAKSI","8"),("KESIMPULAN","9")]
    for t,p in toc_map:
        story.append(_toc_row(t,p,dots_len=70))
        story.append(Spacer(1,0.2*cm))
    story.append(PageBreak())

    # === Page 3: Overview
    story.append(Paragraph("OVERVIEW", _styles["HeadingCenter"]))
    total_trans = len(df_filt)
    avg_keu_days = None
    if "KEUANGAN" in df_filt.columns:
        avg_keu_days = float((df_filt["KEUANGAN"].mean()/86400.0).round(2))
    kpi_lines = [f"<b>JUMLAH TRANSAKSI</b>: {total_trans:,}"]
    if avg_keu_days: kpi_lines.append(f"<b>RATA-RATA SLA KEUANGAN</b>: {avg_keu_days:.2f} HARI")
    if kpi_target_days: kpi_lines.append(f"<b>TARGET KPI</b>: {kpi_target_days:.2f} HARI")
    story.append(Paragraph("<br/>".join(kpi_lines), _styles["KPI"]))
    if "KEUANGAN" in df_filt.columns:
        df_keu=df_filt.groupby(periode_col)["KEUANGAN"].mean().reindex(categories).reset_index()
        df_keu["SLA (hari)"]=(df_keu["KEUANGAN"]/86400.0).round(2)
        df_keu.rename(columns={periode_col:"Periode"}, inplace=True)
        tbl=_nice_table([["Periode","SLA (hari)"]]+df_keu[["Periode","SLA (hari)"]].astype(str).values.tolist(), colWidths=[4*cm,4*cm])
        fig,ax=plt.subplots(figsize=(7,4))
        ax.plot(df_keu["Periode"],df_keu["SLA (hari)"],marker="o",color="#0ea5e9")
        ax.tick_params(axis="x",rotation=45)
        if kpi_target_days: ax.axhline(y=kpi_target_days,ls="--",c="r")
        chart=_plot_to_rlimage(fig,w_cm=13,h_cm=7)
        pair=Table([[chart,tbl]],colWidths=[13*cm,8*cm],hAlign="CENTER")
        pair.setStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
        story.append(pair)
        story.append(Spacer(1,0.5*cm))
    story.append(PageBreak())
    
    # === Page 4: SLA PER PROSES
    story.append(Paragraph("SLA PER PROSES", _styles["HeadingCenter"]))
    valid_proc=[c for c in (proses_cols or []) if c in df_filt.columns]
    if valid_proc:
        dfp=(df_filt[valid_proc].mean()/86400.0).round(2)
        tbl=_nice_table([["Proses","SLA (hari)"]]+[[i,f"{v:.2f}"] for i,v in dfp.items()])
        fig,ax=plt.subplots(figsize=(7,4))
        ax.bar(dfp.index,dfp.values,color="#0ea5e9")
        ax.tick_params(axis="x",rotation=45)
        chart=_plot_to_rlimage(fig,w_cm=13,h_cm=7)

        # Layout → Grafik kiri, tabel kanan, sejajar atas
        pair=Table([[chart,tbl]],colWidths=[13*cm,8*cm],hAlign="CENTER")
        pair.setStyle([
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("VALIGN",(0,0),(-1,-1),"TOP"),   # <<< ini penting: sejajarkan ke atas
        ])
        story.append(pair)

        story.append(Spacer(1,0.5*cm))
        narasi_tbl=Table(
            [[Paragraph(_narasi_top_bottom(dfp),_styles["Narr"])]],
            colWidths=[21*cm],
            hAlign="CENTER"
        )
        story.append(narasi_tbl)
    story.append(PageBreak())

    # === Page 5: SLA PER JENIS TRANSAKSI
    story.append(Paragraph("SLA PER JENIS TRANSAKSI", _styles["HeadingCenter"]))
    jns_candidates=["JENIS_TRANSAKSI","JENIS TRANSAKSI","Jenis Transaksi","Jenis_Transaksi","jenis_transaksi"]
    jns_col=next((c for c in jns_candidates if c in df_filt.columns),None)
    main_sla="KEUANGAN" if "KEUANGAN" in df_filt.columns else (available_sla_cols[0] if available_sla_cols else None)
    if jns_col and main_sla:
        dfj=df_filt.groupby(jns_col)[main_sla].agg(["count","mean"]).reset_index()
        dfj["SLA (hari)"]=(dfj["mean"]/86400.0).round(2)
        dfj=dfj.sort_values("SLA (hari)",ascending=False)
        tbl=_nice_table([["Jenis Transaksi","Jumlah","SLA (hari)"]]+dfj[[jns_col,"count","SLA (hari)"]].astype(str).values.tolist())
        story.append(tbl)
        story.append(Spacer(1,0.5*cm))
        story.append(Paragraph(_narasi_top_bottom(pd.Series(dfj["SLA (hari)"].values,index=dfj[jns_col].values)),_styles["Narr"]))
    story.append(PageBreak())

    # === Page 6: TREN SLA (adaptif)
    story.append(Paragraph("TREN SLA", _styles["HeadingCenter"]))
    valid_sla=[c for c in (available_sla_cols or []) if c in df_filt.columns]
    if valid_sla:
        trend=df_filt.groupby(periode_col)[valid_sla].mean().reindex(categories)
        trend_days=(trend/86400.0).round(2)

        if len(valid_sla) <= 3:
            # --- Layout A: grafik kiri, tabel kanan ---
            data=[["Periode"]+valid_sla]+trend_days.reset_index().astype(str).values.tolist()
            tbl=_nice_table(data, colWidths=[4*cm]+[4*cm]*len(valid_sla))
            fig,ax=plt.subplots(figsize=(7,4))
            for c in valid_sla:
                ax.plot(trend_days.index.astype(str),trend_days[c],marker="o",label=c)
            ax.legend(fontsize=8)
            ax.tick_params(axis="x",rotation=45)
            chart=_plot_to_rlimage(fig,w_cm=13,h_cm=7)
            pair=Table([[chart,tbl]],colWidths=[13*cm,8*cm],hAlign="CENTER")
            pair.setStyle([
                ("LEFTPADDING",(0,0),(-1,-1),0),
                ("RIGHTPADDING",(0,0),(-1,-1),0),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
            ])
            story.append(pair)

        else:
            # --- Layout B: grafik atas, tabel bawah ---
            fig,ax=plt.subplots(figsize=(10,4))
            for c in valid_sla:
                ax.plot(trend_days.index.astype(str),trend_days[c],marker="o",label=c)
            ax.legend(fontsize=8,ncol=2)
            ax.tick_params(axis="x",rotation=45)
            story.append(_plot_to_rlimage(fig,w_cm=21,h_cm=8))
            story.append(Spacer(1,0.4*cm))

            data=[["Periode"]+valid_sla]+trend_days.reset_index().astype(str).values.tolist()
            col_w=[4*cm]+[ (21-4)/len(valid_sla)*cm ]*len(valid_sla)
            tbl=_nice_table(data, colWidths=col_w)
            tbl.setStyle([
                ("FONTSIZE",(0,0),(-1,-1),9),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ])
            story.append(tbl)

        # --- Narasi ---
        story.append(Spacer(1,0.5*cm))
        narasi_tbl=Table([[Paragraph(_narasi_tren(trend_days),_styles["Narr"])]],
                         colWidths=[21*cm], hAlign="CENTER")
        story.append(narasi_tbl)

    story.append(PageBreak())

    # === Page 7: JUMLAH TRANSAKSI
    story.append(Paragraph("JUMLAH TRANSAKSI", _styles["HeadingCenter"]))
    trans=df_filt.groupby(periode_col).size().reindex(categories).reset_index(name="Jumlah").rename(columns={periode_col:"Periode"})
    tbl=_nice_table([["Periode","Jumlah"]]+trans.astype(str).values.tolist())
    fig,ax=plt.subplots(figsize=(7,4))
    ax.bar(trans["Periode"],trans["Jumlah"],color="#14b8a6"); ax.tick_params(axis="x",rotation=45)
    chart=_plot_to_rlimage(fig,w_cm=13,h_cm=7)
    pair=Table([[chart,tbl]],colWidths=[13*cm,8*cm],hAlign="CENTER")
    pair.setStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
    story.append(pair)
    story.append(Spacer(1,0.5*cm))
    narasi_tbl=Table([[Paragraph(_narasi_transaksi(trans),_styles["Narr"])]],colWidths=[21*cm],hAlign="CENTER")
    story.append(narasi_tbl)
    story.append(PageBreak())

    # === Page 8: KESIMPULAN
    story.append(Paragraph("KESIMPULAN", _styles["HeadingCenter"]))

    # rangkum otomatis dari halaman-halaman sebelumnya
    summary_parts = []
    if "KEUANGAN" in df_filt.columns:
        summary_parts.append(_narasi_overview(avg_keu_days, kpi_target_days))
    if 'valid_proc' in locals() and valid_proc:
        dfp_days = (df_filt[valid_proc].mean()/86400.0).round(2)
        summary_parts.append(_narasi_top_bottom(dfp_days))
    if 'valid_sla' in locals() and valid_sla:
        trend_days_all = (df_filt.groupby(periode_col)[valid_sla].mean()/86400.0).round(2).reindex(categories)
        summary_parts.append(_narasi_tren(trend_days_all))
    # transaksi
    summary_parts.append(_narasi_transaksi(trans.copy()))

    story.append(Paragraph(" ".join(summary_parts), _styles["Narr"]))

    # rekomendasi eye-catching (blok lebar)
    recs = [
        "Pertahankan proses yang sudah efisien.",
        "Prioritaskan perbaikan pada SLA terlama.",
        "Analisis akar masalah pada periode outlier.",
        "Optimalkan SDM saat puncak transaksi.",
        "Perkuat monitoring KPI (real-time alert).",
        "Evaluasi otomasi pada aktivitas manual."
    ]
    rec_tbl = _nice_table(
        [["REKOMENDASI PRIORITAS"]] + [[f"• {r}"] for r in recs],
        colWidths=[25.5*cm],
        header_bg="#0ea5e9",
        align="CENTER"
    )
    story.append(Spacer(1, 0.6*cm))
    story.append(rec_tbl)

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("Laporan ini dihasilkan otomatis oleh SLA Dashboard.", _styles["SmallRight"]))

    # Build PDF
    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_pages)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# ====================== STREAMLIT TAB: PDF v6 ======================
with tab_pdf:
    st.subheader("📑 Laporan SLA")

    try:
        pdf_bytes = generate_pdf_report_v6(
            df_ord=df_filtered,                    # DataFrame hasil filter
            selected_periode=selected_periode,     # urutan periode (string)
            periode_col=periode_col,               # nama kolom periode
            available_sla_cols=available_sla_cols, # list kolom SLA
            proses_cols=proses_grafik_cols,        # kolom proses untuk Bab 4
            kpi_target_days=target_kpi_hari if 'target_kpi_hari' in globals() else None
        )

        st.download_button(
            "⬇️ Download Laporan PDF",
            data=pdf_bytes,
            file_name="LAPORAN_SLA_VERIFIKASI_DOKUMEN_PENAGIHAN.pdf",
            mime="application/pdf"
        )
        st.success("PDF siap diunduh ✅")
    except Exception as e:
        import traceback
        st.error(f"Gagal membuat PDF: {type(e).__name__}: {e}")
        traceback.print_exc()



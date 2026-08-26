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

if "show_sela" not in st.session_state:
    st.session_state["show_sela"] = False


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

# Created by
st.sidebar.markdown(
    "<p style='text-align:center; font-size:12px; color:gray;'>Created by. Firman Aditya</p>",
    unsafe_allow_html=True,
)

# Tombol "Tanya SELA" di sidebar
with st.sidebar:
    st.markdown("### 🤖 Tanya SELA")
    if st.button("💬 Buka / Tutup SELA"):
        st.session_state["show_sela"] = not st.session_state["show_sela"]
    st.caption("SELA 3D + AI hanya di-load saat Anda membukanya, supaya dashboard tetap ringan.")


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
tab_overview, tab_proses, tab_transaksi, tab_vendor, tab_tren, tab_jumlah, tab_nilai, tab_report, tab_analisis = st.tabs(
    ["🔍 Overview", "🧮 Per Proses", "🧾 Jenis Transaksi", "🏷️ Vendor", "📈 Tren", "📊 Jumlah Transaksi", "💰 Nilai Transaksi", "📥 Download Report", "🧠 Analisis Data"]
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
    import os
    import io
    import html
    import base64
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import streamlit.components.v1 as components
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    st.subheader("🧾 Analisis SLA per Jenis Transaksi")

    # =====================================================
    # LOCAL HELPERS
    # =====================================================
    def trx_fmt_int(x):
        try:
            return f"{int(x):,}".replace(",", ".")
        except Exception:
            return "-"

    def trx_fmt_hari(x):
        try:
            if x is None or pd.isna(x):
                return "-"
            return f"{float(x):.2f} hari"
        except Exception:
            return "-"

    def trx_seconds_to_text(seconds):
        try:
            if seconds is None or pd.isna(seconds):
                return "-"
            seconds = int(round(float(seconds)))
            days = seconds // 86400
            seconds %= 86400
            hours = seconds // 3600
            seconds %= 3600
            minutes = seconds // 60
            secs = seconds % 60

            parts = []
            if days > 0:
                parts.append(f"{days} hari")
            if hours > 0 or days > 0:
                parts.append(f"{hours} jam")
            if minutes > 0 or hours > 0 or days > 0:
                parts.append(f"{minutes} menit")
            parts.append(f"{secs} detik")
            return " ".join(parts)
        except Exception:
            return "-"

    def trx_safe_text(x, max_len=55):
        x = str(x)
        return x if len(x) <= max_len else x[:max_len] + "..."

    def trx_html_list(items, max_items=None):
        if not items:
            return "<li>Belum ada insight yang dapat ditampilkan.</li>"
        if max_items:
            items = items[:max_items]
        return "".join([f"<li>{html.escape(str(x))}</li>" for x in items])


    def trx_norm_col_name(col):
        """Normalisasi nama kolom agar deteksi kolom tahan terhadap spasi/titik/underscore."""
        s = str(col).upper()
        s = re.sub(r"[^A-Z0-9]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def trx_detect_permohonan_col(df):
        """Deteksi kolom Nomor Permohonan secara fleksibel."""
        exact_candidates = {
            "NOMOR PERMOHONAN",
            "NO PERMOHONAN",
            "NO PERMOHONAN DOKUMEN",
            "NOMOR PERMINTAAN",
            "NO PERMINTAAN",
            "NO REQUEST",
            "REQUEST NUMBER",
        }

        for col in df.columns:
            norm = trx_norm_col_name(col)
            if norm in exact_candidates:
                return col

        for col in df.columns:
            norm = trx_norm_col_name(col)
            has_number_hint = any(token in norm.split() for token in ["NO", "NOMOR", "NUMBER"])
            has_request_hint = any(token in norm for token in ["PERMOHONAN", "PERMINTAAN", "REQUEST"])
            if has_number_hint and has_request_hint:
                return col

        return None

    def trx_sorted_unique(series):
        """Ambil unique value sebagai string, urut natural, dan tetap aman untuk NaN."""
        values = (
            series
            .dropna()
            .astype(str)
            .map(str.strip)
        )
        values = [v for v in values.unique().tolist() if v and v.upper() not in ["NAN", "NONE"]]

        def natural_key(x):
            return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(x))]

        return sorted(values, key=natural_key)

    def trx_apply_main_filters(df_input, nomor_col, selected_permohonan, selected_jenis_data):
        """Filter utama berbasis baris transaksi, sebelum proses agregasi jenis transaksi."""
        df_out = df_input.copy()

        if nomor_col and selected_permohonan and "ALL" not in selected_permohonan:
            df_out = df_out[
                df_out[nomor_col]
                .astype(str)
                .str.strip()
                .isin([str(x).strip() for x in selected_permohonan])
            ].copy()

        if selected_jenis_data and "ALL" not in selected_jenis_data:
            df_out = df_out[
                df_out["JENIS TRANSAKSI"]
                .astype(str)
                .str.strip()
                .isin([str(x).strip() for x in selected_jenis_data])
            ].copy()

        return df_out

    def trx_filter_label(selected_values, all_label="ALL"):
        if not selected_values or all_label in selected_values:
            return "ALL"
        if len(selected_values) <= 3:
            return ", ".join([str(x) for x in selected_values])
        return f"{len(selected_values)} pilihan"

    def trx_get_font(size=28, bold=False):
        candidates = []
        if bold:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "arialbd.ttf",
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "arial.ttf",
            ]

        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

        return ImageFont.load_default()

    def trx_resample_filter():
        try:
            return Image.Resampling.LANCZOS
        except Exception:
            return Image.LANCZOS

    def trx_base_dir():
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except Exception:
            return os.getcwd()

    def trx_logo_paths():
        base_dir = trx_base_dir()
        return [
            os.path.join(base_dir, "asdp_logo.png"),
            os.path.join(os.getcwd(), "asdp_logo.png"),
            "asdp_logo.png",
        ]

    def trx_load_logo_image():
        for path in trx_logo_paths():
            if os.path.exists(path):
                try:
                    return Image.open(path).convert("RGBA")
                except Exception:
                    pass
        return None

    def trx_logo_data_uri():
        for path in trx_logo_paths():
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    return f"data:image/png;base64,{b64}"
                except Exception:
                    pass
        return ""

    def trx_draw_wrapped_text(draw, text, xy, font, fill, max_width, line_gap=7):
        x, y = xy
        words = str(text).split()
        lines = []
        current = ""

        for word in words:
            test = current + (" " if current else "") + word
            bbox = draw.textbbox((0, 0), test, font=font)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        for line in lines:
            draw.text((x, y), line, font=font, fill=fill)
            bbox = draw.textbbox((0, 0), line, font=font)
            y += (bbox[3] - bbox[1]) + line_gap

        return y

    def trx_round_rect(draw, box, radius, fill, outline=None, width=1):
        draw.rounded_rectangle(
            box,
            radius=radius,
            fill=fill,
            outline=outline,
            width=width,
        )

    def trx_gradient_bg(width, height):
        img = Image.new("RGB", (width, height), "#07111f")
        draw = ImageDraw.Draw(img)

        top = (4, 13, 33)
        mid = (10, 38, 84)
        bottom = (0, 105, 120)

        for y in range(height):
            t = y / max(height - 1, 1)
            if t < 0.55:
                k = t / 0.55
                r = int(top[0] * (1 - k) + mid[0] * k)
                g = int(top[1] * (1 - k) + mid[1] * k)
                b = int(top[2] * (1 - k) + mid[2] * k)
            else:
                k = (t - 0.55) / 0.45
                r = int(mid[0] * (1 - k) + bottom[0] * k)
                g = int(mid[1] * (1 - k) + bottom[1] * k)
                b = int(mid[2] * (1 - k) + bottom[2] * k)

            draw.line([(0, y), (width, y)], fill=(r, g, b))

        return img.convert("RGBA")

    # =====================================================
    # AI INSIGHT
    # =====================================================
    def trx_generate_ai_insight(trx_ai_base, proses_bottleneck_cols):
        if trx_ai_base is None or trx_ai_base.empty:
            return {
                "headline": "Belum ada data yang cukup untuk menghasilkan insight.",
                "summary": [],
                "risks": [],
                "recommendations": [],
                "priority_df": pd.DataFrame(),
                "status_label": "NO DATA",
                "status_class": "trx-status-neutral",
                "p1_count": 0,
                "bottleneck_proses": "-",
                "bottleneck_value": np.nan,
            }

        df_ai = trx_ai_base.copy()

        fastest = df_ai.sort_values("SLA Utama (hari)", ascending=True).iloc[0]
        slowest = df_ai.sort_values("SLA Utama (hari)", ascending=False).iloc[0]
        biggest = df_ai.sort_values("Jumlah Transaksi", ascending=False).iloc[0]

        avg_sla = df_ai["SLA Utama (hari)"].mean()
        max_sla = df_ai["SLA Utama (hari)"].max()

        proses_hari_cols = [
            f"{p} (hari)"
            for p in proses_bottleneck_cols
            if f"{p} (hari)" in df_ai.columns
        ]

        bottleneck_proses = "-"
        bottleneck_value = np.nan
        bottleneck_text = "-"

        if proses_hari_cols:
            proses_mean = df_ai[proses_hari_cols].mean().dropna().sort_values(ascending=False)
            if not proses_mean.empty:
                bottleneck_col = proses_mean.index[0]
                bottleneck_proses = bottleneck_col.replace(" (hari)", "")
                bottleneck_value = proses_mean.iloc[0]
                bottleneck_text = f"{bottleneck_proses} dengan rata-rata {trx_fmt_hari(bottleneck_value)}"

        sla_threshold = df_ai["SLA Utama (hari)"].median()
        volume_threshold = df_ai["Jumlah Transaksi"].median()

        def priority_label(row):
            high_sla = row["SLA Utama (hari)"] >= sla_threshold
            high_vol = row["Jumlah Transaksi"] >= volume_threshold

            if high_sla and high_vol:
                return "Prioritas 1 — SLA tinggi & volume besar"
            elif high_sla and not high_vol:
                return "Prioritas 2 — SLA tinggi"
            elif not high_sla and high_vol:
                return "Prioritas 3 — Volume besar"
            else:
                return "Normal"

        df_ai["Prioritas AI"] = df_ai.apply(priority_label, axis=1)

        priority_order = {
            "Prioritas 1 — SLA tinggi & volume besar": 1,
            "Prioritas 2 — SLA tinggi": 2,
            "Prioritas 3 — Volume besar": 3,
            "Normal": 4,
        }

        df_ai["__PRIORITY_SORT__"] = df_ai["Prioritas AI"].map(priority_order).fillna(9)

        priority_df = (
            df_ai[
                [
                    "JENIS TRANSAKSI",
                    "Jumlah Transaksi",
                    "SLA Utama (hari)",
                    "Prioritas AI",
                    "__PRIORITY_SORT__",
                ]
            ]
            .sort_values(
                by=["__PRIORITY_SORT__", "SLA Utama (hari)", "Jumlah Transaksi"],
                ascending=[True, False, False],
            )
            .drop(columns=["__PRIORITY_SORT__"])
        )

        p1_df = df_ai[df_ai["Prioritas AI"].str.contains("Prioritas 1", na=False)]
        p1_count = len(p1_df)

        if p1_count >= 3:
            status_label = "CRITICAL"
            status_class = "trx-status-critical"
        elif p1_count >= 1:
            status_label = "WATCHLIST"
            status_class = "trx-status-watch"
        else:
            status_label = "CONTROLLED"
            status_class = "trx-status-good"

        if not p1_df.empty:
            top_priority = p1_df.sort_values(
                ["SLA Utama (hari)", "Jumlah Transaksi"],
                ascending=[False, False],
            ).iloc[0]

            headline = (
                f"Fokus utama perbaikan adalah jenis transaksi "
                f"“{trx_safe_text(top_priority['JENIS TRANSAKSI'])}” karena memiliki kombinasi "
                f"SLA relatif tinggi ({trx_fmt_hari(top_priority['SLA Utama (hari)'])}) "
                f"dan volume transaksi besar ({trx_fmt_int(top_priority['Jumlah Transaksi'])} transaksi)."
            )
        else:
            headline = (
                f"Secara umum, SLA jenis transaksi relatif terkendali. "
                f"Namun jenis transaksi “{trx_safe_text(slowest['JENIS TRANSAKSI'])}” tetap perlu dimonitor "
                f"karena menjadi kategori dengan SLA paling lama, yaitu "
                f"{trx_fmt_hari(slowest['SLA Utama (hari)'])}."
            )

        summary = [
            f"Jenis transaksi tercepat adalah “{trx_safe_text(fastest['JENIS TRANSAKSI'])}” dengan SLA rata-rata {trx_fmt_hari(fastest['SLA Utama (hari)'])}.",
            f"Jenis transaksi terlama adalah “{trx_safe_text(slowest['JENIS TRANSAKSI'])}” dengan SLA rata-rata {trx_fmt_hari(slowest['SLA Utama (hari)'])}.",
            f"Jenis transaksi dengan volume terbesar adalah “{trx_safe_text(biggest['JENIS TRANSAKSI'])}” sebanyak {trx_fmt_int(biggest['Jumlah Transaksi'])} transaksi.",
            f"Bottleneck proses terbesar terindikasi pada proses {bottleneck_text}.",
        ]

        risks = []

        if pd.notna(avg_sla) and avg_sla > 0 and pd.notna(max_sla) and max_sla > avg_sla * 1.5:
            risks.append(
                f"Terdapat outlier SLA: kategori “{trx_safe_text(slowest['JENIS TRANSAKSI'])}” jauh di atas rata-rata keseluruhan."
            )

        if p1_count > 0:
            risks.append(
                f"Terdapat {p1_count} jenis transaksi prioritas tinggi karena SLA dan volume sama-sama relatif besar."
            )

        if bottleneck_proses != "-" and not pd.isna(bottleneck_value):
            risks.append(
                f"Proses {bottleneck_proses} berpotensi menjadi titik perlambatan utama pada siklus dokumen."
            )

        if not risks:
            risks.append("Tidak terdapat anomali besar pada data yang sedang ditampilkan.")

        recommendations = []

        if not p1_df.empty:
            top3 = p1_df.sort_values(
                ["SLA Utama (hari)", "Jumlah Transaksi"],
                ascending=[False, False],
            ).head(3)

            focus_names = ", ".join(
                [f"“{trx_safe_text(x)}”" for x in top3["JENIS TRANSAKSI"].tolist()]
            )

            recommendations.append(
                f"Prioritaskan review proses untuk {focus_names}, karena kategori tersebut paling berdampak terhadap SLA keseluruhan."
            )
        else:
            recommendations.append(
                f"Fokus monitoring cukup diarahkan pada kategori dengan SLA tertinggi, yaitu “{trx_safe_text(slowest['JENIS TRANSAKSI'])}”."
            )

        if bottleneck_proses != "-":
            recommendations.append(
                f"Lakukan pendalaman pada proses {bottleneck_proses}, termasuk cek antrean dokumen, approval, kelengkapan dokumen, dan pola keterlambatan per vendor/unit."
            )

        recommendations.append(
            "Gunakan bubble matrix untuk menentukan quick win: dahulukan titik kanan-atas karena menunjukkan volume besar dan SLA tinggi."
        )

        return {
            "headline": headline,
            "summary": summary,
            "risks": risks,
            "recommendations": recommendations,
            "priority_df": priority_df,
            "status_label": status_label,
            "status_class": status_class,
            "p1_count": p1_count,
            "bottleneck_proses": bottleneck_proses,
            "bottleneck_value": bottleneck_value,
        }

    # =====================================================
    # CHART BUILDERS
    # =====================================================
    def trx_build_rank_fig(trx_view, sla_utama_label):
        fig = px.bar(
            trx_view.sort_values("SLA Utama (hari)", ascending=True),
            x="SLA Utama (hari)",
            y="JENIS TRANSAKSI",
            orientation="h",
            text="SLA Utama (hari)",
            color="SLA Utama (hari)",
            color_continuous_scale="Tealrose",
            hover_data={"Jumlah Transaksi": True, "SLA Utama (hari)": ":.2f"},
            title=f"Ranking Rata-rata SLA — Acuan: {sla_utama_label}",
        )

        fig.update_traces(
            texttemplate="%{text:.2f} hari",
            textposition="outside",
            marker_line_width=0,
        )

        fig.update_layout(
            height=max(430, 42 * len(trx_view)),
            xaxis_title="Rata-rata SLA (hari)",
            yaxis_title="Jenis Transaksi",
            coloraxis_showscale=False,
            margin=dict(l=20, r=80, t=70, b=30),
            title_font=dict(size=20),
        )

        return fig

    def trx_build_heat_fig(trx_view, chart_proses_cols):
        value_cols = [
            f"{c} (hari)"
            for c in chart_proses_cols
            if f"{c} (hari)" in trx_view.columns
        ]

        if not value_cols:
            return None

        heatmap_data = trx_view.set_index("JENIS TRANSAKSI")[value_cols].copy()
        heatmap_data.columns = [c.replace(" (hari)", "") for c in value_cols]

        fig = px.imshow(
            heatmap_data,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="Turbo",
            title="Peta Panas Rata-rata SLA: Jenis Transaksi vs Proses",
        )

        fig.update_layout(
            height=max(430, 38 * len(heatmap_data)),
            xaxis_title="Proses",
            yaxis_title="Jenis Transaksi",
            margin=dict(l=20, r=20, t=70, b=40),
            title_font=dict(size=20),
        )

        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>Proses: %{x}<br>SLA: %{z:.2f} hari<extra></extra>"
        )

        return fig

    def trx_build_group_fig(trx_long_view):
        fig = px.bar(
            trx_long_view,
            x="JENIS TRANSAKSI",
            y="Rata-rata SLA (hari)",
            color="Proses",
            barmode="group",
            text="Rata-rata SLA (hari)",
            title="Rata-rata SLA Masing-masing Proses per Jenis Transaksi",
            hover_data={"Jumlah Transaksi": True, "Rata-rata SLA (hari)": ":.2f"},
        )

        fig.update_traces(
            texttemplate="%{text:.1f}",
            textposition="outside",
        )

        fig.update_layout(
            height=560,
            xaxis_title="Jenis Transaksi",
            yaxis_title="Rata-rata SLA (hari)",
            legend_title="Proses",
            margin=dict(l=20, r=20, t=70, b=140),
            title_font=dict(size=20),
            xaxis_tickangle=-35,
        )

        return fig

    def trx_build_bubble_fig(trx_view):
        median_volume = trx_view["Jumlah Transaksi"].median()
        median_sla = trx_view["SLA Utama (hari)"].median()

        fig = px.scatter(
            trx_view,
            x="Jumlah Transaksi",
            y="SLA Utama (hari)",
            size="Jumlah Transaksi",
            color="SLA Utama (hari)",
            color_continuous_scale="Plasma",
            hover_name="JENIS TRANSAKSI",
            text="JENIS TRANSAKSI",
            size_max=58,
            title="Peta Prioritas: Volume Besar dan SLA Tinggi",
        )

        fig.add_vline(
            x=median_volume,
            line_dash="dash",
            line_color="gray",
            annotation_text="Median Volume",
            annotation_position="top left",
        )

        fig.add_hline(
            y=median_sla,
            line_dash="dash",
            line_color="gray",
            annotation_text="Median SLA",
            annotation_position="bottom right",
        )

        fig.update_traces(
            textposition="top center",
            marker=dict(opacity=0.78, line=dict(width=1, color="white")),
        )

        fig.update_layout(
            height=580,
            xaxis_title="Jumlah Transaksi",
            yaxis_title="Rata-rata SLA (hari)",
            coloraxis_colorbar_title="SLA Hari",
            margin=dict(l=20, r=20, t=70, b=40),
            title_font=dict(size=20),
        )

        return fig

    def trx_build_donut_fig(trx_view):
        fig = px.pie(
            trx_view,
            values="Jumlah Transaksi",
            names="JENIS TRANSAKSI",
            hole=0.58,
            title="Komposisi Transaksi berdasarkan Jenis Transaksi",
        )

        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            pull=[0.03] * len(trx_view),
        )

        fig.update_layout(
            height=530,
            margin=dict(l=20, r=20, t=70, b=30),
            title_font=dict(size=20),
            legend_title="Jenis Transaksi",
        )

        return fig

    def trx_build_process_fig(data_proses, proses):
        col_hari = f"{proses} (hari)"

        fig = px.bar(
            data_proses,
            x=col_hari,
            y="JENIS TRANSAKSI",
            orientation="h",
            text=col_hari,
            color=col_hari,
            color_continuous_scale="Blues",
            title=f"SLA {proses}",
        )

        fig.update_traces(
            texttemplate="%{text:.2f}",
            textposition="outside",
            marker_line_width=0,
        )

        fig.update_layout(
            height=max(360, 32 * len(data_proses)),
            xaxis_title="Hari",
            yaxis_title="",
            coloraxis_showscale=False,
            margin=dict(l=10, r=55, t=55, b=25),
            title_font=dict(size=16),
        )

        return fig

    def trx_build_detail_fig(detail_chart, selected_detail):
        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=detail_chart["Proses"],
                y=detail_chart["Rata-rata SLA (hari)"],
                text=detail_chart["Rata-rata SLA (hari)"],
                texttemplate="%{text:.2f} hari",
                textposition="outside",
                marker=dict(
                    color=detail_chart["Rata-rata SLA (hari)"],
                    colorscale="Viridis",
                    line=dict(width=0),
                ),
            )
        )

        fig.update_layout(
            title=f"Profil SLA per Proses — {selected_detail}",
            height=470,
            xaxis_title="Proses",
            yaxis_title="Rata-rata SLA (hari)",
            margin=dict(l=20, r=20, t=70, b=40),
            title_font=dict(size=20),
        )

        return fig

    # =====================================================
    # EXECUTIVE IMAGE + PDF
    # =====================================================
    def trx_make_summary_image(trx_exec_base, ai_result, sla_utama_label, start_periode, end_periode):
        W, H = 1920, 1080

        img = trx_gradient_bg(W, H)
        draw = ImageDraw.Draw(img)

        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((-220, -180, 520, 520), fill=(0, 234, 255, 55))
        gd.ellipse((1320, 650, 2150, 1420), fill=(56, 239, 125, 45))
        gd.ellipse((1280, -220, 2100, 480), fill=(255, 65, 108, 28))
        glow = glow.filter(ImageFilter.GaussianBlur(22))

        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)

        font_title = trx_get_font(54, True)
        font_sub = trx_get_font(22, False)
        font_h = trx_get_font(28, True)
        font_kpi_label = trx_get_font(18, True)
        font_kpi_value = trx_get_font(36, True)
        font_body = trx_get_font(21, False)
        font_body_bold = trx_get_font(21, True)
        font_small = trx_get_font(15, False)
        font_badge = trx_get_font(21, True)

        exec_df = trx_exec_base.copy()

        total_jenis_exec = exec_df["JENIS TRANSAKSI"].nunique()
        total_trx_exec = int(exec_df["Jumlah Transaksi"].sum())
        avg_sla_exec = float(exec_df["SLA Utama (hari)"].mean())

        fastest_exec = exec_df.sort_values("SLA Utama (hari)", ascending=True).iloc[0]
        slowest_exec = exec_df.sort_values("SLA Utama (hari)", ascending=False).iloc[0]
        biggest_exec = exec_df.sort_values("Jumlah Transaksi", ascending=False).iloc[0]

        priority_df_exec = ai_result.get("priority_df", pd.DataFrame()).copy()
        p1_count = ai_result.get("p1_count", 0)
        status_label = ai_result.get("status_label", "CONTROLLED")
        bottleneck_proses = ai_result.get("bottleneck_proses", "-")
        bottleneck_value = ai_result.get("bottleneck_value", np.nan)
        headline = ai_result.get("headline", "-")
        reco_items = ai_result.get("recommendations", [])[:3]

        if status_label == "CRITICAL":
            status_fill = (255, 65, 108, 235)
            status_outline = (255, 180, 195, 255)
        elif status_label == "WATCHLIST":
            status_fill = (255, 180, 60, 235)
            status_outline = (255, 235, 150, 255)
        else:
            status_fill = (40, 200, 145, 235)
            status_outline = (160, 255, 210, 255)

        logo = trx_load_logo_image()
        title_x = 70

        if logo is not None:
            logo = logo.copy()
            logo.thumbnail((210, 82), trx_resample_filter())
            img.alpha_composite(logo, (70, 42))
            title_x = 310

        draw.text((title_x, 52), "EXECUTIVE SUMMARY", font=font_title, fill=(255, 255, 255, 255))
        draw.text(
            (title_x + 3, 122),
            f"SLA Jenis Transaksi | Periode {start_periode} s.d. {end_periode} | Acuan: {sla_utama_label}",
            font=font_sub,
            fill=(210, 235, 255, 235),
        )

        badge_box = (1495, 58, 1835, 118)
        trx_round_rect(draw, badge_box, 30, status_fill, status_outline, 2)

        bbox = draw.textbbox((0, 0), status_label, font=font_badge)
        draw.text(
            (
                badge_box[0] + (badge_box[2] - badge_box[0] - (bbox[2] - bbox[0])) / 2,
                badge_box[1] + 15,
            ),
            status_label,
            font=font_badge,
            fill=(255, 255, 255, 255),
        )

        headline_box = (70, 170, 1850, 300)
        trx_round_rect(draw, headline_box, 30, (10, 25, 55, 235), (0, 234, 255, 125), 3)

        trx_draw_wrapped_text(
            draw,
            headline,
            (105, 205),
            trx_get_font(26, True),
            (255, 255, 255, 245),
            1705,
            9,
        )

        kpis = [
            ("TOTAL TRANSAKSI", trx_fmt_int(total_trx_exec), "Filter jenis transaksi aktif"),
            ("JENIS TRANSAKSI", trx_fmt_int(total_jenis_exec), "Kategori dianalisis"),
            ("RATA-RATA SLA", trx_fmt_hari(avg_sla_exec), "SLA utama"),
            ("PRIORITAS TINGGI", trx_fmt_int(p1_count), "SLA tinggi & volume besar"),
        ]

        card_y = 330
        card_w = 420
        card_h = 138
        card_gap = 35

        for i, (label, value, sub) in enumerate(kpis):
            x = 70 + i * (card_w + card_gap)
            box = (x, card_y, x + card_w, card_y + card_h)

            trx_round_rect(draw, box, 26, (10, 25, 55, 230), (255, 255, 255, 95), 2)

            draw.text((x + 28, card_y + 24), label, font=font_kpi_label, fill=(130, 230, 255, 255))
            draw.text((x + 28, card_y + 58), value, font=font_kpi_value, fill=(255, 255, 255, 255))
            draw.text((x + 28, card_y + 108), sub, font=font_small, fill=(205, 225, 240, 220))

        left_box = (70, 505, 1050, 955)
        trx_round_rect(draw, left_box, 30, (10, 25, 55, 230), (255, 255, 255, 85), 2)

        draw.text((105, 535), "Executive Notes", font=font_h, fill=(255, 255, 255, 255))

        notes = [
            f"Jenis tercepat: {trx_safe_text(fastest_exec['JENIS TRANSAKSI'], 54)} ({trx_fmt_hari(fastest_exec['SLA Utama (hari)'])}).",
            f"Jenis terlama: {trx_safe_text(slowest_exec['JENIS TRANSAKSI'], 54)} ({trx_fmt_hari(slowest_exec['SLA Utama (hari)'])}).",
            f"Volume terbesar: {trx_safe_text(biggest_exec['JENIS TRANSAKSI'], 54)} ({trx_fmt_int(biggest_exec['Jumlah Transaksi'])} trx).",
            f"Bottleneck proses: {bottleneck_proses}"
            + ("" if pd.isna(bottleneck_value) else f" ({trx_fmt_hari(bottleneck_value)})."),
        ]

        y = 585

        for note in notes:
            draw.text((112, y), "•", font=font_body_bold, fill=(0, 234, 255, 255))
            y = trx_draw_wrapped_text(
                draw,
                note,
                (140, y),
                font_body,
                (245, 250, 255, 245),
                850,
                6,
            )
            y += 8

        draw.text((105, 760), "Recommended Actions", font=font_h, fill=(255, 255, 255, 255))

        y = 810

        if not reco_items:
            reco_items = ["Lakukan monitoring berkala terhadap jenis transaksi dengan SLA tertinggi."]

        for reco in reco_items:
            draw.text((112, y), "✓", font=font_body_bold, fill=(56, 239, 125, 255))
            y = trx_draw_wrapped_text(
                draw,
                reco,
                (145, y),
                font_body,
                (245, 250, 255, 245),
                830,
                6,
            )
            y += 8

        right_box = (1090, 505, 1850, 955)
        trx_round_rect(draw, right_box, 30, (10, 25, 55, 230), (255, 255, 255, 85), 2)

        draw.text((1125, 535), "Top Priority Transactions", font=font_h, fill=(255, 255, 255, 255))

        if priority_df_exec.empty:
            priority_df_exec = exec_df[
                ["JENIS TRANSAKSI", "Jumlah Transaksi", "SLA Utama (hari)"]
            ].copy()
            priority_df_exec["Prioritas AI"] = "Prioritas belum tersedia"

        top_priority = priority_df_exec.head(5).copy()

        max_sla = top_priority["SLA Utama (hari)"].max()
        max_sla = max_sla if pd.notna(max_sla) and max_sla > 0 else 1

        y = 595

        for _, row in top_priority.iterrows():
            name = trx_safe_text(row["JENIS TRANSAKSI"], 40)
            sla_val = float(row["SLA Utama (hari)"])
            trx_val = int(row["Jumlah Transaksi"])
            prio = str(row.get("Prioritas AI", ""))

            row_box = (1125, y, 1815, y + 62)
            trx_round_rect(draw, row_box, 18, (18, 42, 88, 245), (0, 234, 255, 90), 1)

            draw.text((1148, y + 9), name, font=trx_get_font(19, True), fill=(255, 255, 255, 250))
            draw.text((1148, y + 35), prio[:48], font=trx_get_font(14, False), fill=(200, 225, 240, 220))

            bar_x = 1515
            bar_y = y + 40
            bar_w = 170
            bar_h = 9

            trx_round_rect(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), 5, (255, 255, 255, 55), None, 1)

            fill_w = int(bar_w * min(sla_val / max_sla, 1))

            trx_round_rect(draw, (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), 5, (0, 234, 255, 240), None, 1)

            draw.text((1705, y + 9), trx_fmt_hari(sla_val), font=trx_get_font(16, True), fill=(255, 255, 255, 245))
            draw.text((1705, y + 34), f"{trx_fmt_int(trx_val)} trx", font=trx_get_font(14, False), fill=(200, 225, 240, 220))

            y += 72

        draw.text(
            (70, 1005),
            "Generated automatically from Tab Jenis Transaksi filter.",
            font=font_small,
            fill=(210, 230, 245, 190),
        )

        draw.text(
            (1415, 1005),
            "SLA Payment Analyzer | Executive View",
            font=font_small,
            fill=(210, 230, 245, 190),
        )

        return img.convert("RGB")

    def trx_image_to_png_bytes(img):
        out_png = io.BytesIO()
        img.save(out_png, format="PNG", quality=95)
        return out_png.getvalue()

    def trx_make_placeholder_page(title, message):
        W, H = 1920, 1080
        page = trx_gradient_bg(W, H)
        draw = ImageDraw.Draw(page)

        trx_round_rect(draw, (90, 100, 1830, 980), 35, (10, 25, 55, 230), (0, 234, 255, 100), 2)

        draw.text((140, 150), title, font=trx_get_font(44, True), fill=(255, 255, 255, 255))

        trx_draw_wrapped_text(
            draw,
            message,
            (140, 240),
            trx_get_font(26, False),
            (230, 245, 255, 230),
            1600,
            10,
        )

        return page.convert("RGB")

    def trx_fig_to_pdf_page(fig, title):
        W, H = 1920, 1080
        page = trx_gradient_bg(W, H)
        draw = ImageDraw.Draw(page)

        try:
            png_bytes = fig.to_image(
                format="png",
                width=1600,
                height=820,
                scale=2,
            )
            chart_img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception as e:
            return trx_make_placeholder_page(
                title,
                "Chart tidak dapat dirender ke PDF. Pastikan dependency 'kaleido' sudah masuk ke requirements.txt.\n\nDetail error: "
                + str(e),
            )

        draw.text((70, 48), title, font=trx_get_font(42, True), fill=(255, 255, 255, 255))

        trx_round_rect(
            draw,
            (70, 115, 1850, 1015),
            28,
            (245, 250, 255, 245),
            (0, 234, 255, 95),
            2,
        )

        chart_img.thumbnail((1710, 840), trx_resample_filter())

        x = 70 + (1780 - chart_img.width) // 2
        y = 135 + (860 - chart_img.height) // 2

        page.alpha_composite(chart_img, (x, y))

        return page.convert("RGB")

    def trx_table_pages(df, title, subtitle="", rows_per_page=24, max_pages=8):
        if df is None or df.empty:
            return [trx_make_placeholder_page(title, "Tidak ada data tabel yang dapat ditampilkan.")]

        df_show = df.copy().astype(str)
        pages = []
        total_rows = len(df_show)

        chunks = [
            df_show.iloc[i:i + rows_per_page]
            for i in range(0, total_rows, rows_per_page)
        ][:max_pages]

        for page_idx, chunk in enumerate(chunks, start=1):
            W, H = 1920, 1080
            page = trx_gradient_bg(W, H)
            draw = ImageDraw.Draw(page)

            draw.text((70, 45), title, font=trx_get_font(42, True), fill=(255, 255, 255, 255))

            if subtitle:
                draw.text((72, 98), subtitle, font=trx_get_font(20, False), fill=(210, 235, 255, 220))

            draw.text(
                (1560, 98),
                f"Page {page_idx}/{len(chunks)}",
                font=trx_get_font(20, True),
                fill=(210, 235, 255, 220),
            )

            box = (70, 140, 1850, 1010)
            trx_round_rect(draw, box, 28, (10, 25, 55, 230), (0, 234, 255, 90), 2)

            cols = list(chunk.columns)
            table_x = 105
            table_y = 180
            table_w = 1710
            row_h = 31
            header_h = 38
            col_w = max(120, table_w // max(len(cols), 1))

            for j, col in enumerate(cols):
                x = table_x + j * col_w
                if x >= table_x + table_w:
                    continue

                draw.rectangle(
                    (
                        x,
                        table_y,
                        min(x + col_w, table_x + table_w),
                        table_y + header_h,
                    ),
                    fill=(0, 160, 190, 210),
                )

                draw.text(
                    (x + 8, table_y + 9),
                    trx_safe_text(col, 18),
                    font=trx_get_font(15, True),
                    fill=(255, 255, 255, 255),
                )

            y = table_y + header_h

            for i, (_, row) in enumerate(chunk.iterrows()):
                fill = (255, 255, 255, 22) if i % 2 == 0 else (255, 255, 255, 12)
                draw.rectangle((table_x, y, table_x + table_w, y + row_h), fill=fill)

                for j, col in enumerate(cols):
                    x = table_x + j * col_w
                    if x >= table_x + table_w:
                        continue

                    draw.text(
                        (x + 8, y + 8),
                        trx_safe_text(row[col], 24),
                        font=trx_get_font(14, False),
                        fill=(235, 245, 255, 235),
                    )

                y += row_h

            if total_rows > rows_per_page * max_pages and page_idx == len(chunks):
                draw.text(
                    (105, 970),
                    f"Catatan: tabel dibatasi sampai {rows_per_page * max_pages} baris pertama agar ukuran PDF tetap wajar.",
                    font=trx_get_font(16, False),
                    fill=(255, 220, 150, 230),
                )

            pages.append(page.convert("RGB"))

        return pages

    def trx_make_full_pdf_report(
        summary_img,
        trx_view,
        trx_long_view,
        chart_proses_cols,
        sla_utama_label,
        priority_df,
        transaksi_display,
        detail_df,
        detail_chart,
        selected_detail,
    ):
        pages = [summary_img.convert("RGB")]

        chart_pages = [
            ("Ranking SLA per Jenis Transaksi", trx_build_rank_fig(trx_view, sla_utama_label)),
            ("Perbandingan SLA Masing-masing Proses", trx_build_group_fig(trx_long_view)),
            ("Bubble Matrix Volume vs SLA", trx_build_bubble_fig(trx_view)),
            ("Komposisi Jumlah Transaksi", trx_build_donut_fig(trx_view)),
        ]

        fig_heat = trx_build_heat_fig(trx_view, chart_proses_cols)
        if fig_heat is not None:
            chart_pages.insert(1, ("Heatmap SLA per Proses", fig_heat))

        if detail_chart is not None and not detail_chart.empty:
            chart_pages.append(
                (
                    f"Drilldown SLA — {selected_detail}",
                    trx_build_detail_fig(detail_chart, selected_detail),
                )
            )

        for title, fig in chart_pages:
            pages.append(trx_fig_to_pdf_page(fig, title))

        for proses in chart_proses_cols:
            col_hari = f"{proses} (hari)"
            if col_hari in trx_view.columns:
                data_proses = trx_view.sort_values(col_hari, ascending=True)
                pages.append(
                    trx_fig_to_pdf_page(
                        trx_build_process_fig(data_proses, proses),
                        f"Grafik SLA Proses {proses}",
                    )
                )

        priority_table = priority_df.copy()

        if not priority_table.empty and "SLA Utama (hari)" in priority_table.columns:
            priority_table["SLA Utama (hari)"] = priority_table["SLA Utama (hari)"].round(2)

        pages.extend(
            trx_table_pages(
                priority_table,
                "Tabel Matriks Prioritas AI",
                "Prioritas berdasarkan kombinasi SLA dan volume transaksi.",
                rows_per_page=24,
                max_pages=6,
            )
        )

        pages.extend(
            trx_table_pages(
                transaksi_display,
                "Tabel Rata-rata SLA per Jenis Transaksi",
                "Ringkasan rata-rata SLA setiap proses per jenis transaksi sesuai tampilan aktif.",
                rows_per_page=24,
                max_pages=8,
            )
        )

        if detail_df is not None and not detail_df.empty:
            detail_pdf_df = detail_df.head(120).copy()

            pages.extend(
                trx_table_pages(
                    detail_pdf_df,
                    f"Tabel Detail Data — {selected_detail}",
                    "Menampilkan maksimum 120 baris pertama agar ukuran PDF tetap stabil.",
                    rows_per_page=20,
                    max_pages=6,
                )
            )

        out_pdf = io.BytesIO()

        pages[0].save(
            out_pdf,
            format="PDF",
            save_all=True,
            append_images=pages[1:],
            resolution=150.0,
        )

        return out_pdf.getvalue()

    # =====================================================
    # MAIN TAB LOGIC
    # =====================================================
    if "JENIS TRANSAKSI" not in df_filtered.columns or not available_sla_cols:
        st.info("Kolom 'JENIS TRANSAKSI' tidak ditemukan atau tidak ada kolom SLA yang tersedia.")

    else:
        df_trx = df_filtered.copy()

        df_trx["JENIS TRANSAKSI"] = (
            df_trx["JENIS TRANSAKSI"]
            .fillna("TIDAK TERDETEKSI")
            .astype(str)
        )

        proses_cols = [
            c for c in [
                "FUNGSIONAL",
                "VENDOR",
                "KEUANGAN",
                "PERBENDAHARAAN",
                "TOTAL WAKTU",
            ]
            if c in available_sla_cols
        ]

        proses_bottleneck_cols = [
            c for c in [
                "FUNGSIONAL",
                "VENDOR",
                "KEUANGAN",
                "PERBENDAHARAAN",
            ]
            if c in proses_cols
        ]

        chart_proses_cols = proses_cols.copy()

        if not proses_cols:
            st.info("Tidak ada kolom SLA yang dapat dianalisis.")

        else:
            # =====================================================
            # FILTER DATA UTAMA — sebelum agregasi
            # =====================================================
            # Catatan penting:
            # Filter Nomor Permohonan dan Jenis Transaksi harus dilakukan di level baris
            # sebelum groupby, agar seluruh KPI, AI Insight, Executive Summary, grafik,
            # PDF, dan drilldown membaca subset data yang sama.
            nomor_permohonan_col = trx_detect_permohonan_col(df_trx)

            st.markdown("### 🎛️ Filter Data Transaksi")

            fcol1, fcol2 = st.columns([1.35, 1.25])

            with fcol1:
                if nomor_permohonan_col:
                    nomor_options = trx_sorted_unique(df_trx[nomor_permohonan_col])

                    # =====================================================
                    # FIX HIGH-CARDINALITY MULTISELECT
                    # =====================================================
                    # Streamlit/React Multiselect dapat mengalami
                    # ``RangeError: Maximum call stack size exceeded`` jika
                    # puluhan ribu opsi dikirim sekaligus ke browser.
                    #
                    # Untuk dataset kecil, perilaku lama DIPERTAHANKAN.
                    # Untuk dataset besar, filter otomatis beralih ke mode
                    # pencarian server-side sehingga widget hanya menerima
                    # sebagian kecil opsi. Downstream tetap menerima format
                    # selected_permohonan yang sama: ["ALL"] atau list nomor.
                    TRX_NOMOR_DIRECT_LIMIT = 800
                    TRX_NOMOR_SEARCH_LIMIT = 250

                    if len(nomor_options) <= TRX_NOMOR_DIRECT_LIMIT:
                        selected_permohonan = st.multiselect(
                            "Filter Nomor Permohonan",
                            options=["ALL"] + nomor_options,
                            default=["ALL"],
                            help=(
                                "Bisa pilih 1 atau lebih Nomor Permohonan. "
                                "Pilih ALL untuk menampilkan seluruh nomor."
                            ),
                            key="trx_filter_nomor_permohonan_main",
                        )
                    else:
                        st.markdown("**Filter Nomor Permohonan**")
                        st.caption(
                            f"Terdeteksi {trx_fmt_int(len(nomor_options))} Nomor Permohonan unik. "
                            "Mode pencarian aman diaktifkan agar dashboard tetap ringan dan tidak error."
                        )

                        use_all_nomor = st.checkbox(
                            "Gunakan seluruh Nomor Permohonan (ALL)",
                            value=True,
                            key="trx_filter_nomor_all_safe_v1",
                            help=(
                                "Aktifkan untuk menganalisis seluruh Nomor Permohonan. "
                                "Nonaktifkan jika ingin mencari dan memilih nomor tertentu."
                            ),
                        )

                        if use_all_nomor:
                            selected_permohonan = ["ALL"]
                        else:
                            nomor_query = st.text_input(
                                "Cari Nomor Permohonan",
                                value="",
                                placeholder="Ketik nomor / sebagian nomor. Bisa beberapa, pisahkan dengan koma.",
                                key="trx_filter_nomor_search_safe_v1",
                                help=(
                                    "Pencarian dilakukan sebelum opsi dikirim ke multiselect. "
                                    "Gunakan koma, titik koma, atau baris baru untuk mencari beberapa nomor sekaligus."
                                ),
                            )

                            search_terms = [
                                token.strip().casefold()
                                for token in re.split(r"[,;\n]+", nomor_query or "")
                                if token.strip()
                            ]

                            matched_nomor = []
                            if search_terms:
                                matched_nomor = [
                                    value
                                    for value in nomor_options
                                    if any(term in str(value).casefold() for term in search_terms)
                                ]

                            safe_key = "trx_filter_nomor_permohonan_safe_v1"
                            if safe_key not in st.session_state:
                                st.session_state[safe_key] = []

                            # Opsi yang sudah dipilih tetap dipertahankan walau
                            # user mengganti kata pencarian, sehingga pilihan
                            # beberapa nomor dapat dikumpulkan bertahap.
                            previous_selected = [
                                str(v) for v in st.session_state.get(safe_key, [])
                                if str(v) in set(nomor_options)
                            ]

                            matched_limited = matched_nomor[:TRX_NOMOR_SEARCH_LIMIT]
                            safe_options = list(dict.fromkeys(previous_selected + matched_limited))

                            # Pastikan state widget tidak membawa value yang
                            # sudah tidak tersedia setelah periode/filter berubah.
                            if st.session_state.get(safe_key, []) != previous_selected:
                                st.session_state[safe_key] = previous_selected

                            selected_permohonan = st.multiselect(
                                "Pilih Nomor Permohonan hasil pencarian",
                                options=safe_options,
                                key=safe_key,
                                help=(
                                    "Pilih satu atau lebih nomor dari hasil pencarian. "
                                    "Pilihan yang sudah dipilih tetap tersimpan saat kata pencarian diganti."
                                ),
                            )

                            if not search_terms and not selected_permohonan:
                                st.info(
                                    "Ketik Nomor Permohonan pada kolom pencarian di atas. "
                                    "Selama belum ada nomor yang dipilih, filter Nomor Permohonan dianggap ALL."
                                )
                                selected_permohonan = ["ALL"]
                            elif search_terms and not matched_nomor and not selected_permohonan:
                                st.warning("Nomor Permohonan yang dicari tidak ditemukan pada periode aktif.")
                                # Gunakan sentinel agar hasil benar-benar kosong,
                                # bukan tanpa sengaja kembali ke ALL.
                                selected_permohonan = ["__NO_MATCH__"]
                            elif len(matched_nomor) > TRX_NOMOR_SEARCH_LIMIT:
                                st.caption(
                                    f"Ditemukan {trx_fmt_int(len(matched_nomor))} hasil. "
                                    f"Hanya {trx_fmt_int(TRX_NOMOR_SEARCH_LIMIT)} hasil pertama ditampilkan; "
                                    "ketik pencarian yang lebih spesifik untuk mempersempit hasil."
                                )
                            elif search_terms:
                                st.caption(
                                    f"Ditemukan {trx_fmt_int(len(matched_nomor))} hasil pencarian."
                                )
                else:
                    selected_permohonan = ["ALL"]
                    st.warning(
                        "Kolom Nomor Permohonan tidak terdeteksi. "
                        "Pastikan nama kolom mengandung kata 'Nomor/No' dan 'Permohonan/Permintaan/Request'."
                    )

            with fcol2:
                jenis_options_data = trx_sorted_unique(df_trx["JENIS TRANSAKSI"])
                selected_jenis_data = st.multiselect(
                    "Filter Jenis Transaksi",
                    options=["ALL"] + jenis_options_data,
                    default=["ALL"],
                    help="Bisa pilih 1 atau lebih jenis transaksi. Filter ini bekerja sebelum agregasi SLA.",
                    key="trx_filter_jenis_data_main",
                )

            df_trx_before_filter = df_trx.copy()
            df_trx = trx_apply_main_filters(
                df_input=df_trx_before_filter,
                nomor_col=nomor_permohonan_col,
                selected_permohonan=selected_permohonan,
                selected_jenis_data=selected_jenis_data,
            )

            kf1, kf2, kf3, kf4 = st.columns(4)
            kf1.metric("Baris Awal", trx_fmt_int(len(df_trx_before_filter)))
            kf2.metric("Baris Terfilter", trx_fmt_int(len(df_trx)))
            kf3.metric("Nomor Dipilih", trx_filter_label(selected_permohonan))
            kf4.metric("Jenis Dipilih", trx_filter_label(selected_jenis_data))

            if df_trx.empty:
                st.warning("Tidak ada data untuk kombinasi filter Nomor Permohonan dan Jenis Transaksi yang dipilih.")

            trx_mean_sec = (
                df_trx
                .groupby("JENIS TRANSAKSI")[proses_cols]
                .mean()
                .reset_index()
            )

            trx_count = (
                df_trx
                .groupby("JENIS TRANSAKSI")
                .size()
                .reset_index(name="Jumlah Transaksi")
            )

            trx_summary = trx_mean_sec.merge(
                trx_count,
                on="JENIS TRANSAKSI",
                how="left",
            )

            for col in proses_cols:
                trx_summary[f"{col} (hari)"] = trx_summary[col] / 86400

            if "TOTAL WAKTU" in proses_cols:
                trx_summary["SLA Utama (detik)"] = trx_summary["TOTAL WAKTU"]
                trx_summary["SLA Utama (hari)"] = trx_summary["TOTAL WAKTU (hari)"]
                sla_utama_label = "TOTAL WAKTU"
            else:
                trx_summary["SLA Utama (detik)"] = trx_summary[proses_cols].mean(axis=1)
                trx_summary["SLA Utama (hari)"] = trx_summary["SLA Utama (detik)"] / 86400
                sla_utama_label = "RATA-RATA PROSES"

            trx_summary = trx_summary.dropna(subset=["SLA Utama (hari)"]).copy()

            if trx_summary.empty:
                st.warning("Tidak ada data SLA valid untuk tab jenis transaksi.")

            else:
                trx_summary = trx_summary.sort_values("SLA Utama (hari)", ascending=True)

                # =====================================================
                # SLA TRANSAKSIONAL DAN KUMULATIF
                # =====================================================
                st.markdown("### 🔬 SLA Transaksional & Kumulatif atas Filter Aktif")

                with st.expander("📄 Lihat SLA Transaksional per Baris / Nomor Permohonan", expanded=False):
                    detail_transaksional = df_trx.copy()

                    # Format kolom SLA agar mudah dibaca user. Kolom asli detik tetap tidak diubah.
                    for col in chart_proses_cols:
                        if col in detail_transaksional.columns:
                            detail_transaksional[f"{col} (SLA)"] = detail_transaksional[col].apply(trx_seconds_to_text)

                    base_detail_cols = []
                    for candidate_col in [
                        periode_col,
                        nomor_permohonan_col,
                        "JENIS TRANSAKSI",
                        "NAMA VENDOR",
                        "NILAI TRANSAKSI",
                        "NOMINAL",
                        "TOTAL NILAI",
                    ]:
                        if candidate_col and candidate_col in detail_transaksional.columns and candidate_col not in base_detail_cols:
                            base_detail_cols.append(candidate_col)

                    sla_detail_cols = [
                        f"{col} (SLA)"
                        for col in chart_proses_cols
                        if f"{col} (SLA)" in detail_transaksional.columns
                    ]

                    detail_cols_show = base_detail_cols + sla_detail_cols

                    if detail_cols_show:
                        st.dataframe(
                            detail_transaksional[detail_cols_show],
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.dataframe(detail_transaksional, use_container_width=True, hide_index=True)

                kumulatif_rows = []
                for col in chart_proses_cols:
                    if col in df_trx.columns:
                        sec_series = pd.to_numeric(df_trx[col], errors="coerce").dropna()
                        if not sec_series.empty:
                            kumulatif_rows.append({
                                "Proses": col,
                                "Jumlah Data Valid": int(sec_series.count()),
                                "Rata-rata SLA": trx_seconds_to_text(sec_series.mean()),
                                "Rata-rata SLA (hari)": round(float(sec_series.mean()) / 86400, 2),
                                "Akumulasi SLA": trx_seconds_to_text(sec_series.sum()),
                                "Akumulasi SLA (hari)": round(float(sec_series.sum()) / 86400, 2),
                            })

                kumulatif_df = pd.DataFrame(kumulatif_rows)

                if not kumulatif_df.empty:
                    st.dataframe(kumulatif_df, use_container_width=True, hide_index=True)
                    st.caption(
                        "Catatan: Akumulasi SLA adalah penjumlahan durasi SLA seluruh baris transaksi terfilter. "
                        "Untuk evaluasi performa proses, kolom rata-rata SLA biasanya lebih representatif."
                    )

                if nomor_permohonan_col and nomor_permohonan_col in df_trx.columns:
                    with st.expander("🧮 Ringkasan Kumulatif per Nomor Permohonan", expanded=False):
                        group_cols_permohonan = [nomor_permohonan_col, "JENIS TRANSAKSI"]

                        permohonan_summary = (
                            df_trx
                            .groupby(group_cols_permohonan, dropna=False)[proses_cols]
                            .mean()
                            .reset_index()
                        )

                        permohonan_count = (
                            df_trx
                            .groupby(group_cols_permohonan, dropna=False)
                            .size()
                            .reset_index(name="Jumlah Baris")
                        )

                        permohonan_summary = permohonan_summary.merge(
                            permohonan_count,
                            on=group_cols_permohonan,
                            how="left",
                        )

                        for col in proses_cols:
                            permohonan_summary[f"{col} (Rata-rata)"] = permohonan_summary[col].apply(trx_seconds_to_text)

                        permohonan_display_cols = (
                            group_cols_permohonan
                            + ["Jumlah Baris"]
                            + [
                                f"{col} (Rata-rata)"
                                for col in proses_cols
                                if f"{col} (Rata-rata)" in permohonan_summary.columns
                            ]
                        )

                        st.dataframe(
                            permohonan_summary[permohonan_display_cols],
                            use_container_width=True,
                            hide_index=True,
                        )

                # =====================================================
                # KPI DIGITAL CARDS
                # =====================================================
                total_jenis = trx_summary["JENIS TRANSAKSI"].nunique()
                total_transaksi_trx = int(trx_summary["Jumlah Transaksi"].sum())

                fastest_row = trx_summary.sort_values("SLA Utama (hari)", ascending=True).iloc[0]
                slowest_row = trx_summary.sort_values("SLA Utama (hari)", ascending=False).iloc[0]

                fastest_name = html.escape(str(fastest_row["JENIS TRANSAKSI"]))
                slowest_name = html.escape(str(slowest_row["JENIS TRANSAKSI"]))

                kpi_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    font-family: Segoe UI, sans-serif;
                }}

                .trx-kpi-grid {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 16px;
                    margin: 4px 0 10px 0;
                }}

                .trx-kpi-card {{
                    border-radius: 20px;
                    padding: 18px;
                    color: white;
                    min-height: 135px;
                    box-shadow: 0 12px 30px rgba(0,0,0,0.22);
                    overflow: hidden;
                    position: relative;
                }}

                .trx-kpi-card::after {{
                    content: "";
                    position: absolute;
                    right: -35px;
                    top: -35px;
                    width: 125px;
                    height: 125px;
                    border-radius: 50%;
                    background: rgba(255,255,255,0.18);
                }}

                .trx-kpi-icon {{
                    font-size: 30px;
                    margin-bottom: 8px;
                }}

                .trx-kpi-label {{
                    font-size: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.6px;
                    opacity: 0.88;
                    margin-bottom: 4px;
                }}

                .trx-kpi-value {{
                    font-size: 25px;
                    font-weight: 900;
                    line-height: 1.12;
                    word-break: break-word;
                }}

                .trx-kpi-sub {{
                    margin-top: 8px;
                    font-size: 11.5px;
                    opacity: 0.82;
                    line-height: 1.32;
                }}

                .trx-blue {{ background: linear-gradient(135deg, #0072ff, #00c6ff); }}
                .trx-green {{ background: linear-gradient(135deg, #11998e, #38ef7d); }}
                .trx-purple {{ background: linear-gradient(135deg, #7f00ff, #e100ff); }}
                .trx-red {{ background: linear-gradient(135deg, #ff416c, #ff4b2b); }}

                @media (max-width: 900px) {{
                    .trx-kpi-grid {{
                        grid-template-columns: repeat(2, 1fr);
                    }}
                }}
                </style>
                </head>

                <body>
                <div class="trx-kpi-grid">
                    <div class="trx-kpi-card trx-blue">
                        <div class="trx-kpi-icon">🧾</div>
                        <div class="trx-kpi-label">Total Jenis Transaksi</div>
                        <div class="trx-kpi-value">{trx_fmt_int(total_jenis)}</div>
                        <div class="trx-kpi-sub">Kategori transaksi terdeteksi</div>
                    </div>

                    <div class="trx-kpi-card trx-green">
                        <div class="trx-kpi-icon">📄</div>
                        <div class="trx-kpi-label">Total Transaksi</div>
                        <div class="trx-kpi-value">{trx_fmt_int(total_transaksi_trx)}</div>
                        <div class="trx-kpi-sub">Dalam periode terpilih</div>
                    </div>

                    <div class="trx-kpi-card trx-purple">
                        <div class="trx-kpi-icon">⚡</div>
                        <div class="trx-kpi-label">Jenis Tercepat</div>
                        <div class="trx-kpi-value" style="font-size:18px;">{fastest_name}</div>
                        <div class="trx-kpi-sub">{trx_fmt_hari(fastest_row["SLA Utama (hari)"])} berdasarkan {sla_utama_label}</div>
                    </div>

                    <div class="trx-kpi-card trx-red">
                        <div class="trx-kpi-icon">🚨</div>
                        <div class="trx-kpi-label">Jenis Terlama</div>
                        <div class="trx-kpi-value" style="font-size:18px;">{slowest_name}</div>
                        <div class="trx-kpi-sub">{trx_fmt_hari(slowest_row["SLA Utama (hari)"])} berdasarkan {sla_utama_label}</div>
                    </div>
                </div>
                </body>
                </html>
                """

                components.html(kpi_html, height=190, scrolling=False)

                # =====================================================
                # FILTER VISUALISASI
                # =====================================================
                st.markdown("### 🔎 Filter Visualisasi")

                c_filter1, c_filter2, c_filter3 = st.columns([1.4, 1.2, 1.2])

                with c_filter1:
                    jenis_options = trx_summary["JENIS TRANSAKSI"].tolist()

                    selected_jenis = st.multiselect(
                        "Pilih Jenis Transaksi untuk visualisasi",
                        options=["ALL"] + jenis_options,
                        default=["ALL"],
                        key="trx_filter_jenis_wow",
                    )

                if "ALL" in selected_jenis or not selected_jenis:
                    trx_ai_base = trx_summary.copy()
                else:
                    trx_ai_base = trx_summary[
                        trx_summary["JENIS TRANSAKSI"].isin(selected_jenis)
                    ].copy()

                with c_filter2:
                    # =====================================================
                    # FIX: slider tidak boleh memiliki min_value == max_value
                    # =====================================================
                    # Kondisi ini terjadi ketika filter utama menyisakan hanya
                    # 1 jenis transaksi. Streamlit melempar StreamlitAPIException
                    # jika st.slider dibuat dengan min=1 dan max=1.
                    max_top_n = min(30, len(trx_ai_base))

                    if max_top_n <= 0:
                        top_n = 0
                        st.metric("Top N ditampilkan", "0")
                    elif max_top_n == 1:
                        top_n = 1
                        # Tetap tampilkan kontrol di posisi yang sama, namun
                        # nonaktif karena hanya ada satu kategori yang tersedia.
                        st.selectbox(
                            "Top N ditampilkan",
                            options=[1],
                            index=0,
                            disabled=True,
                            key="trx_top_n_wow_single",
                            help="Hanya ada 1 jenis transaksi pada filter aktif.",
                        )
                    else:
                        default_top_n = min(10, max_top_n)

                        # Bersihkan state slider lama jika nilainya berada di
                        # luar range baru setelah user mempersempit filter.
                        old_top_n = st.session_state.get("trx_top_n_wow")
                        if old_top_n is not None:
                            try:
                                old_top_n_int = int(old_top_n)
                            except Exception:
                                old_top_n_int = default_top_n
                            if old_top_n_int < 1 or old_top_n_int > max_top_n:
                                st.session_state.pop("trx_top_n_wow", None)

                        top_n = st.slider(
                            "Top N ditampilkan",
                            min_value=1,
                            max_value=max_top_n,
                            value=default_top_n,
                            step=1,
                            key="trx_top_n_wow",
                        )

                with c_filter3:
                    sort_mode = st.selectbox(
                        "Urutkan berdasarkan",
                        [
                            "SLA tercepat",
                            "SLA terlama",
                            "Jumlah transaksi terbesar",
                        ],
                        key="trx_sort_mode_wow",
                    )

                if trx_ai_base.empty:
                    st.warning("Tidak ada data untuk kombinasi filter yang dipilih.")

                else:
                    trx_view = trx_ai_base.copy()

                    if sort_mode == "SLA tercepat":
                        trx_view = trx_view.sort_values("SLA Utama (hari)", ascending=True)
                    elif sort_mode == "SLA terlama":
                        trx_view = trx_view.sort_values("SLA Utama (hari)", ascending=False)
                    else:
                        trx_view = trx_view.sort_values("Jumlah Transaksi", ascending=False)

                    trx_view = trx_view.head(top_n)

                    if trx_view.empty:
                        st.warning("Tidak ada data untuk kombinasi filter yang dipilih.")

                    else:
                        value_vars_chart = [
                            f"{c} (hari)"
                            for c in chart_proses_cols
                            if f"{c} (hari)" in trx_view.columns
                        ]

                        trx_long_view = trx_view.melt(
                            id_vars=["JENIS TRANSAKSI", "Jumlah Transaksi"],
                            value_vars=value_vars_chart,
                            var_name="Proses",
                            value_name="Rata-rata SLA (hari)",
                        )

                        trx_long_view["Proses"] = trx_long_view["Proses"].str.replace(
                            " (hari)",
                            "",
                            regex=False,
                        )

                        trx_long_view = trx_long_view.dropna(subset=["Rata-rata SLA (hari)"])

                        # =====================================================
                        # AI EXECUTIVE INSIGHT
                        # =====================================================
                        st.markdown("### 🤖 AI Executive Insight")

                        ai_result = trx_generate_ai_insight(
                            trx_ai_base,
                            proses_bottleneck_cols,
                        )

                        summary_html = trx_html_list(ai_result.get("summary", []))
                        risk_html = trx_html_list(ai_result.get("risks", []))
                        reco_html = trx_html_list(ai_result.get("recommendations", []))

                        status_label = ai_result.get("status_label", "CONTROLLED")
                        status_class = ai_result.get("status_class", "trx-status-good")

                        ai_height = 430 + 28 * max(
                            len(ai_result.get("summary", [])),
                            len(ai_result.get("risks", [])),
                            len(ai_result.get("recommendations", [])),
                        )

                        ai_html = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                        <style>
                        body {{
                            margin: 0;
                            padding: 0;
                            background: transparent;
                            font-family: Segoe UI, sans-serif;
                        }}

                        .trx-ai-wrap {{
                            width: 100%;
                            box-sizing: border-box;
                            background:
                                radial-gradient(circle at top left, rgba(0,234,255,0.30), transparent 28%),
                                radial-gradient(circle at bottom right, rgba(225,0,255,0.25), transparent 30%),
                                linear-gradient(135deg, rgba(13,19,45,0.98), rgba(20,28,60,0.94));
                            border: 1px solid rgba(255,255,255,0.18);
                            border-radius: 26px;
                            padding: 24px;
                            box-shadow: 0 18px 48px rgba(0,0,0,0.35);
                            color: white;
                            overflow: hidden;
                        }}

                        .trx-ai-header {{
                            display: flex;
                            flex-wrap: wrap;
                            justify-content: space-between;
                            align-items: center;
                            gap: 12px;
                            margin-bottom: 16px;
                        }}

                        .trx-ai-title {{
                            font-size: 30px;
                            font-weight: 950;
                            letter-spacing: 0.3px;
                            background: linear-gradient(90deg, #00eaff, #38ef7d, #fee140);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                        }}

                        .trx-ai-badge-row {{
                            display: flex;
                            flex-wrap: wrap;
                            gap: 10px;
                            align-items: center;
                        }}

                        .trx-ai-badge {{
                            background: rgba(255,255,255,0.13);
                            border: 1px solid rgba(255,255,255,0.22);
                            padding: 8px 12px;
                            border-radius: 999px;
                            font-size: 12px;
                            font-weight: 800;
                            color: #dffcff;
                        }}

                        .trx-ai-status {{
                            padding: 8px 14px;
                            border-radius: 999px;
                            font-size: 12px;
                            font-weight: 950;
                            letter-spacing: 0.6px;
                            border: 1px solid rgba(255,255,255,0.20);
                        }}

                        .trx-status-critical {{
                            background: rgba(255,65,108,0.24);
                            color: #ffdce5;
                        }}

                        .trx-status-watch {{
                            background: rgba(254,225,64,0.22);
                            color: #fff4b0;
                        }}

                        .trx-status-good {{
                            background: rgba(56,239,125,0.20);
                            color: #d9ffe9;
                        }}

                        .trx-status-neutral {{
                            background: rgba(255,255,255,0.14);
                            color: #ffffff;
                        }}

                        .trx-ai-headline {{
                            background: rgba(255,255,255,0.10);
                            border: 1px solid rgba(255,255,255,0.16);
                            border-radius: 20px;
                            padding: 18px 20px;
                            font-size: 18px;
                            font-weight: 760;
                            line-height: 1.48;
                            margin-bottom: 18px;
                            box-shadow: inset 0 0 18px rgba(255,255,255,0.05);
                            color: rgba(255,255,255,0.96);
                        }}

                        .trx-ai-grid {{
                            display: grid;
                            grid-template-columns: repeat(3, 1fr);
                            gap: 16px;
                            align-items: stretch;
                        }}

                        .trx-ai-box {{
                            background: rgba(255,255,255,0.09);
                            border: 1px solid rgba(255,255,255,0.14);
                            border-radius: 20px;
                            padding: 18px;
                            backdrop-filter: blur(10px);
                            min-height: 220px;
                        }}

                        .trx-ai-box h4 {{
                            margin: 0 0 12px 0;
                            font-size: 16px;
                            letter-spacing: 0.4px;
                            color: rgba(255,255,255,0.98);
                        }}

                        .trx-ai-box ul {{
                            margin: 0;
                            padding-left: 20px;
                        }}

                        .trx-ai-box li {{
                            margin-bottom: 9px;
                            font-size: 13.5px;
                            line-height: 1.45;
                            color: rgba(255,255,255,0.92);
                        }}

                        .trx-ai-foot {{
                            margin-top: 14px;
                            font-size: 11.5px;
                            opacity: 0.67;
                            text-align: right;
                        }}

                        @media (max-width: 900px) {{
                            .trx-ai-grid {{
                                grid-template-columns: 1fr;
                            }}
                        }}
                        </style>
                        </head>

                        <body>
                        <div class="trx-ai-wrap">
                            <div class="trx-ai-header">
                                <div class="trx-ai-title">🤖 AI Executive Insight</div>
                                <div class="trx-ai-badge-row">
                                    <div class="trx-ai-status {status_class}">{html.escape(status_label)}</div>
                                    <div class="trx-ai-badge">Auto-generated from filtered transaction type</div>
                                </div>
                            </div>

                            <div class="trx-ai-headline">
                                {html.escape(str(ai_result.get("headline", "-")))}
                            </div>

                            <div class="trx-ai-grid">
                                <div class="trx-ai-box">
                                    <h4>📌 Key Findings</h4>
                                    <ul>{summary_html}</ul>
                                </div>

                                <div class="trx-ai-box">
                                    <h4>🚨 Risk Signals</h4>
                                    <ul>{risk_html}</ul>
                                </div>

                                <div class="trx-ai-box">
                                    <h4>✅ Recommended Actions</h4>
                                    <ul>{reco_html}</ul>
                                </div>
                            </div>

                            <div class="trx-ai-foot">
                                Insight mengikuti filter jenis transaksi aktif, namun tidak bias oleh Top N dan sorting visual.
                            </div>
                        </div>
                        </body>
                        </html>
                        """

                        components.html(ai_html, height=ai_height, scrolling=False)

                        # =====================================================
                        # PRIORITY MATRIX TABLE
                        # =====================================================
                        with st.expander("🧠 Lihat Matriks Prioritas AI", expanded=False):
                            priority_show = ai_result.get("priority_df", pd.DataFrame()).copy()

                            if not priority_show.empty:
                                priority_show["SLA Utama (hari)"] = priority_show["SLA Utama (hari)"].round(2)

                                def style_priority(row):
                                    label = str(row["Prioritas AI"])

                                    if "Prioritas 1" in label:
                                        return [
                                            "background-color: #ffe2e2; color: #7a0000; font-weight: bold"
                                        ] * len(row)
                                    elif "Prioritas 2" in label:
                                        return [
                                            "background-color: #fff3cd; color: #6b4e00; font-weight: bold"
                                        ] * len(row)
                                    elif "Prioritas 3" in label:
                                        return [
                                            "background-color: #dff5ff; color: #004761; font-weight: bold"
                                        ] * len(row)
                                    else:
                                        return [""] * len(row)

                                st.dataframe(
                                    priority_show.style.apply(style_priority, axis=1),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            else:
                                st.info("Belum ada matriks prioritas yang dapat ditampilkan.")

                        # =====================================================
                        # EXECUTIVE SUMMARY DIREKSI
                        # =====================================================
                        st.markdown("### 🎯 Executive Summary Direksi")

                        exec_df = trx_ai_base.copy()

                        total_jenis_exec = exec_df["JENIS TRANSAKSI"].nunique()
                        total_trx_exec = int(exec_df["Jumlah Transaksi"].sum())
                        avg_sla_exec = float(exec_df["SLA Utama (hari)"].mean())

                        fastest_exec = exec_df.sort_values("SLA Utama (hari)", ascending=True).iloc[0]
                        slowest_exec = exec_df.sort_values("SLA Utama (hari)", ascending=False).iloc[0]
                        biggest_exec = exec_df.sort_values("Jumlah Transaksi", ascending=False).iloc[0]

                        priority_df_exec = ai_result.get("priority_df", pd.DataFrame()).copy()
                        p1_count = ai_result.get("p1_count", 0)
                        bottleneck_proses = ai_result.get("bottleneck_proses", "-")
                        bottleneck_value = ai_result.get("bottleneck_value", np.nan)

                        if status_label == "CRITICAL":
                            status_desc = "Perlu perhatian segera karena beberapa jenis transaksi memiliki kombinasi SLA tinggi dan volume besar."
                        elif status_label == "WATCHLIST":
                            status_desc = "Terdapat transaksi prioritas yang perlu dipantau dan ditindaklanjuti."
                        else:
                            status_desc = "Secara umum kondisi transaksi masih terkendali pada filter yang aktif."

                        top_priority_html = ""

                        if not priority_df_exec.empty:
                            priority_show_exec = priority_df_exec.head(5).copy()

                            for _, row in priority_show_exec.iterrows():
                                trx_name = html.escape(trx_safe_text(row["JENIS TRANSAKSI"], 42))
                                trx_count = trx_fmt_int(row["Jumlah Transaksi"])
                                trx_sla = trx_fmt_hari(row["SLA Utama (hari)"])
                                trx_priority = html.escape(str(row["Prioritas AI"]))

                                top_priority_html += f"""
                                <div class="trx-exec-prio-row">
                                    <div>
                                        <div class="trx-exec-prio-name">{trx_name}</div>
                                        <div class="trx-exec-prio-sub">{trx_priority}</div>
                                    </div>
                                    <div class="trx-exec-prio-metric">
                                        <b>{trx_sla}</b><br>
                                        <span>{trx_count} trx</span>
                                    </div>
                                </div>
                                """

                        if top_priority_html == "":
                            top_priority_html = """
                            <div class="trx-exec-prio-row">
                                <div>
                                    <div class="trx-exec-prio-name">Belum ada prioritas khusus</div>
                                    <div class="trx-exec-prio-sub">Data prioritas tidak tersedia</div>
                                </div>
                                <div class="trx-exec-prio-metric"><b>-</b></div>
                            </div>
                            """

                        bottleneck_sentence = "."

                        if not pd.isna(bottleneck_value):
                            bottleneck_sentence = f" dengan rata-rata {trx_fmt_hari(bottleneck_value)}."

                        exec_height = 790 + (len(priority_df_exec.head(5)) * 12)

                        exec_fastest_name = html.escape(trx_safe_text(fastest_exec["JENIS TRANSAKSI"]))
                        exec_slowest_name = html.escape(trx_safe_text(slowest_exec["JENIS TRANSAKSI"]))
                        exec_biggest_name = html.escape(trx_safe_text(biggest_exec["JENIS TRANSAKSI"]))

                        logo_src = trx_logo_data_uri()

                        if logo_src:
                            logo_html = f'<img src="{logo_src}" class="trx-exec-logo" />'
                        else:
                            logo_html = '<div class="trx-exec-logo-fallback">ASDP</div>'

                        exec_html = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                        <style>
                        body {{
                            margin: 0;
                            padding: 0;
                            background: transparent;
                            font-family: Segoe UI, sans-serif;
                        }}

                        .trx-exec-wrap {{
                            width: 100%;
                            box-sizing: border-box;
                            background:
                                radial-gradient(circle at top left, rgba(0, 234, 255, 0.34), transparent 25%),
                                radial-gradient(circle at bottom right, rgba(56, 239, 125, 0.22), transparent 30%),
                                linear-gradient(135deg, #061126 0%, #102a58 50%, #034e62 100%);
                            border: 1px solid rgba(255,255,255,0.18);
                            border-radius: 28px;
                            padding: 24px;
                            color: white;
                            box-shadow: 0 22px 58px rgba(0,0,0,0.38);
                            overflow: hidden;
                        }}

                        .trx-exec-header {{
                            display: flex;
                            flex-wrap: wrap;
                            justify-content: space-between;
                            align-items: flex-start;
                            gap: 14px;
                            margin-bottom: 18px;
                        }}

                        .trx-exec-brand {{
                            display: flex;
                            align-items: center;
                            gap: 18px;
                        }}

                        .trx-exec-logo {{
                            max-width: 150px;
                            max-height: 58px;
                            object-fit: contain;
                            background: rgba(255,255,255,0.92);
                            padding: 8px 12px;
                            border-radius: 14px;
                        }}

                        .trx-exec-logo-fallback {{
                            width: 120px;
                            height: 46px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            background: rgba(255,255,255,0.92);
                            color: #005577;
                            font-weight: 950;
                            border-radius: 14px;
                        }}

                        .trx-exec-title {{
                            font-size: 34px;
                            font-weight: 950;
                            letter-spacing: 0.2px;
                            line-height: 1.08;
                        }}

                        .trx-exec-subtitle {{
                            margin-top: 8px;
                            opacity: 0.82;
                            font-size: 14px;
                            line-height: 1.35;
                        }}

                        .trx-exec-status {{
                            padding: 12px 16px;
                            border-radius: 999px;
                            font-size: 13px;
                            font-weight: 950;
                            letter-spacing: 0.7px;
                            border: 1px solid rgba(255,255,255,0.22);
                        }}

                        .trx-exec-headline {{
                            background: rgba(10,25,55,0.76);
                            border: 1px solid rgba(0,234,255,0.40);
                            border-radius: 22px;
                            padding: 18px 20px;
                            font-size: 18px;
                            font-weight: 760;
                            line-height: 1.48;
                            margin-bottom: 18px;
                        }}

                        .trx-exec-kpi-grid {{
                            display: grid;
                            grid-template-columns: repeat(4, 1fr);
                            gap: 14px;
                            margin-bottom: 18px;
                        }}

                        .trx-exec-kpi {{
                            background: rgba(10,25,55,0.74);
                            border: 1px solid rgba(255,255,255,0.16);
                            border-radius: 20px;
                            padding: 16px;
                            min-height: 110px;
                        }}

                        .trx-exec-kpi-label {{
                            font-size: 12px;
                            opacity: 0.78;
                            text-transform: uppercase;
                            letter-spacing: 0.6px;
                            color: #84eaff;
                        }}

                        .trx-exec-kpi-value {{
                            margin-top: 8px;
                            font-size: 24px;
                            font-weight: 950;
                            color: #ffffff;
                        }}

                        .trx-exec-kpi-sub {{
                            margin-top: 6px;
                            font-size: 11.5px;
                            opacity: 0.76;
                            line-height: 1.28;
                        }}

                        .trx-exec-main-grid {{
                            display: grid;
                            grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
                            gap: 16px;
                        }}

                        .trx-exec-box {{
                            background: rgba(10,25,55,0.74);
                            border: 1px solid rgba(255,255,255,0.14);
                            border-radius: 22px;
                            padding: 18px;
                        }}

                        .trx-exec-box h4 {{
                            margin: 0 0 12px 0;
                            font-size: 16px;
                        }}

                        .trx-exec-box ul {{
                            margin: 0;
                            padding-left: 20px;
                        }}

                        .trx-exec-box li {{
                            margin-bottom: 9px;
                            line-height: 1.42;
                            font-size: 13.5px;
                            color: rgba(255,255,255,0.91);
                        }}

                        .trx-exec-prio-row {{
                            display: flex;
                            justify-content: space-between;
                            gap: 12px;
                            padding: 12px 0;
                            border-bottom: 1px solid rgba(255,255,255,0.14);
                        }}

                        .trx-exec-prio-name {{
                            font-size: 13.5px;
                            font-weight: 850;
                            line-height: 1.25;
                        }}

                        .trx-exec-prio-sub {{
                            font-size: 11px;
                            opacity: 0.76;
                            margin-top: 4px;
                            line-height: 1.25;
                        }}

                        .trx-exec-prio-metric {{
                            text-align: right;
                            font-size: 12px;
                            min-width: 108px;
                        }}

                        .trx-exec-prio-metric span {{
                            opacity: 0.72;
                        }}

                        .trx-exec-note {{
                            margin-top: 14px;
                            font-size: 11.5px;
                            opacity: 0.62;
                            text-align: right;
                        }}

                        .trx-status-critical {{
                            background: rgba(255,65,108,0.24);
                            color: #ffdce5;
                        }}

                        .trx-status-watch {{
                            background: rgba(254,225,64,0.22);
                            color: #fff4b0;
                        }}

                        .trx-status-good {{
                            background: rgba(56,239,125,0.20);
                            color: #d9ffe9;
                        }}

                        .trx-status-neutral {{
                            background: rgba(255,255,255,0.14);
                            color: #ffffff;
                        }}

                        @media (max-width: 950px) {{
                            .trx-exec-kpi-grid {{
                                grid-template-columns: repeat(2, 1fr);
                            }}

                            .trx-exec-main-grid {{
                                grid-template-columns: 1fr;
                            }}
                        }}
                        </style>
                        </head>

                        <body>
                        <div class="trx-exec-wrap">
                            <div class="trx-exec-header">
                                <div class="trx-exec-brand">
                                    {logo_html}
                                    <div>
                                        <div class="trx-exec-title">Executive Summary<br>SLA Jenis Transaksi</div>
                                        <div class="trx-exec-subtitle">
                                            Periode {html.escape(str(start_periode))} s.d. {html.escape(str(end_periode))}
                                            • Acuan: {html.escape(str(sla_utama_label))}
                                        </div>
                                    </div>
                                </div>

                                <div class="trx-exec-status {status_class}">{html.escape(status_label)}</div>
                            </div>

                            <div class="trx-exec-headline">
                                {html.escape(str(ai_result.get("headline", "-")))}
                            </div>

                            <div class="trx-exec-kpi-grid">
                                <div class="trx-exec-kpi">
                                    <div class="trx-exec-kpi-label">Total Transaksi</div>
                                    <div class="trx-exec-kpi-value">{trx_fmt_int(total_trx_exec)}</div>
                                    <div class="trx-exec-kpi-sub">Jumlah transaksi pada filter jenis transaksi aktif</div>
                                </div>

                                <div class="trx-exec-kpi">
                                    <div class="trx-exec-kpi-label">Jenis Transaksi</div>
                                    <div class="trx-exec-kpi-value">{trx_fmt_int(total_jenis_exec)}</div>
                                    <div class="trx-exec-kpi-sub">Kategori transaksi dianalisis</div>
                                </div>

                                <div class="trx-exec-kpi">
                                    <div class="trx-exec-kpi-label">Rata-rata SLA</div>
                                    <div class="trx-exec-kpi-value">{trx_fmt_hari(avg_sla_exec)}</div>
                                    <div class="trx-exec-kpi-sub">Rata-rata SLA utama</div>
                                </div>

                                <div class="trx-exec-kpi">
                                    <div class="trx-exec-kpi-label">Prioritas Tinggi</div>
                                    <div class="trx-exec-kpi-value">{trx_fmt_int(p1_count)}</div>
                                    <div class="trx-exec-kpi-sub">{html.escape(status_desc)}</div>
                                </div>
                            </div>

                            <div class="trx-exec-main-grid">
                                <div class="trx-exec-box">
                                    <h4>📌 Executive Notes</h4>
                                    <ul>
                                        <li>Jenis tercepat: <b>{exec_fastest_name}</b> dengan SLA {trx_fmt_hari(fastest_exec["SLA Utama (hari)"])}.</li>
                                        <li>Jenis terlama: <b>{exec_slowest_name}</b> dengan SLA {trx_fmt_hari(slowest_exec["SLA Utama (hari)"])}.</li>
                                        <li>Volume terbesar: <b>{exec_biggest_name}</b> sebanyak {trx_fmt_int(biggest_exec["Jumlah Transaksi"])} transaksi.</li>
                                        <li>Bottleneck proses: <b>{html.escape(str(bottleneck_proses))}</b>{bottleneck_sentence}</li>
                                    </ul>

                                    <h4 style="margin-top:18px;">✅ Recommended Actions</h4>
                                    <ul>{trx_html_list(ai_result.get("recommendations", []), max_items=3)}</ul>
                                </div>

                                <div class="trx-exec-box">
                                    <h4>🔥 Top Priority Transactions</h4>
                                    {top_priority_html}
                                </div>
                            </div>

                            <div class="trx-exec-note">
                                Executive summary otomatis mengikuti filter jenis transaksi aktif.
                            </div>
                        </div>
                        </body>
                        </html>
                        """

                        components.html(exec_html, height=exec_height, scrolling=False)

                        # =====================================================
                        # DETAIL OBJECTS
                        # =====================================================
                        def trx_get_detail_objects(selected_name):
                            detail_df_local = df_trx[
                                df_trx["JENIS TRANSAKSI"] == selected_name
                            ].copy()

                            detail_mean_local = trx_summary[
                                trx_summary["JENIS TRANSAKSI"] == selected_name
                            ].copy()

                            detail_chart_local = pd.DataFrame()

                            if not detail_mean_local.empty:
                                detail_row_local = detail_mean_local.iloc[0]
                                rows = []

                                for p in chart_proses_cols:
                                    col_hari = f"{p} (hari)"
                                    if col_hari in detail_row_local.index:
                                        val = detail_row_local[col_hari]
                                        if pd.notna(val):
                                            rows.append(
                                                {
                                                    "Proses": p,
                                                    "Rata-rata SLA (hari)": val,
                                                }
                                            )

                                detail_chart_local = pd.DataFrame(rows)

                            return detail_df_local, detail_mean_local, detail_chart_local

                        detail_options = trx_view["JENIS TRANSAKSI"].tolist()

                        previous_detail = st.session_state.get("trx_detail_select_wow", None)

                        if previous_detail in detail_options:
                            pdf_selected_detail = previous_detail
                        else:
                            pdf_selected_detail = detail_options[0]

                        detail_df_for_pdf, detail_mean_for_pdf, detail_chart_for_pdf = trx_get_detail_objects(
                            pdf_selected_detail
                        )

                        # =====================================================
                        # DOWNLOAD EXECUTIVE PACK
                        # =====================================================
                        st.markdown("### 📥 Download Executive Pack")

                        col_down1, col_down2, col_down3 = st.columns([1, 1, 1.25])

                        with col_down1:
                            if st.button("🎨 Generate Executive Pack", key="generate_exec_summary_trx"):
                                try:
                                    transaksi_display_pdf = trx_view.copy()

                                    for col in chart_proses_cols:
                                        if col in transaksi_display_pdf.columns:
                                            transaksi_display_pdf[f"{col} (Rata-rata)"] = transaksi_display_pdf[col].apply(
                                                trx_seconds_to_text
                                            )

                                    display_cols_pdf = (
                                        ["JENIS TRANSAKSI", "Jumlah Transaksi"]
                                        + [
                                            f"{col} (Rata-rata)"
                                            for col in chart_proses_cols
                                            if f"{col} (Rata-rata)" in transaksi_display_pdf.columns
                                        ]
                                    )

                                    transaksi_display_pdf = transaksi_display_pdf[display_cols_pdf]

                                    summary_img = trx_make_summary_image(
                                        trx_exec_base=trx_ai_base,
                                        ai_result=ai_result,
                                        sla_utama_label=sla_utama_label,
                                        start_periode=start_periode,
                                        end_periode=end_periode,
                                    )

                                    png_bytes = trx_image_to_png_bytes(summary_img)
                                    st.session_state["trx_exec_summary_png"] = png_bytes

                                    try:
                                        pdf_bytes = trx_make_full_pdf_report(
                                            summary_img=summary_img,
                                            trx_view=trx_view,
                                            trx_long_view=trx_long_view,
                                            chart_proses_cols=chart_proses_cols,
                                            sla_utama_label=sla_utama_label,
                                            priority_df=ai_result.get("priority_df", pd.DataFrame()),
                                            transaksi_display=transaksi_display_pdf,
                                            detail_df=detail_df_for_pdf,
                                            detail_chart=detail_chart_for_pdf,
                                            selected_detail=pdf_selected_detail,
                                        )

                                        st.session_state["trx_exec_report_pdf"] = pdf_bytes
                                        st.success("Executive Pack berhasil dibuat. PNG dan PDF lengkap siap di-download.")

                                    except Exception as e_pdf:
                                        if "trx_exec_report_pdf" in st.session_state:
                                            del st.session_state["trx_exec_report_pdf"]

                                        st.warning(
                                            "PNG berhasil dibuat, tetapi PDF gagal dibuat. "
                                            "Pastikan dependency 'kaleido' sudah ada di requirements.txt."
                                        )
                                        st.exception(e_pdf)

                                except Exception as e:
                                    st.error("Executive Pack gagal dibuat.")
                                    st.exception(e)

                        with col_down2:
                            if "trx_exec_summary_png" in st.session_state:
                                st.download_button(
                                    "⬇️ Download PNG Summary",
                                    data=st.session_state["trx_exec_summary_png"],
                                    file_name="Executive_Summary_Tab_Transaksi.png",
                                    mime="image/png",
                                    key="download_exec_summary_png",
                                )

                        with col_down3:
                            if "trx_exec_report_pdf" in st.session_state:
                                st.download_button(
                                    "⬇️ Download PDF Lengkap",
                                    data=st.session_state["trx_exec_report_pdf"],
                                    file_name="Executive_Report_Tab_Transaksi_Lengkap.pdf",
                                    mime="application/pdf",
                                    key="download_exec_report_pdf",
                                )

                        if "trx_exec_summary_png" in st.session_state:
                            with st.expander("👀 Preview Executive Summary 16:9", expanded=True):
                                st.image(
                                    st.session_state["trx_exec_summary_png"],
                                    caption="Preview Executive Summary 16:9",
                                    use_container_width=True,
                                )

                        # =====================================================
                        # MAIN CHARTS
                        # =====================================================
                        st.markdown("### 🏆 Ranking SLA per Jenis Transaksi")
                        fig_rank = trx_build_rank_fig(trx_view, sla_utama_label)
                        st.plotly_chart(fig_rank, use_container_width=True)

                        st.markdown("### 🔥 Heatmap SLA per Proses")
                        fig_heat = trx_build_heat_fig(trx_view, chart_proses_cols)

                        if fig_heat is not None:
                            st.plotly_chart(fig_heat, use_container_width=True)
                        else:
                            st.info("Tidak ada kolom proses yang dapat ditampilkan pada heatmap.")

                        st.markdown("### 📊 Perbandingan SLA Masing-masing Proses")

                        if not trx_long_view.empty:
                            fig_group = trx_build_group_fig(trx_long_view)
                            st.plotly_chart(fig_group, use_container_width=True)
                        else:
                            st.info("Tidak ada data SLA proses yang valid untuk grafik perbandingan.")

                        st.markdown("### 🫧 Bubble Matrix: Volume vs SLA")
                        fig_bubble = trx_build_bubble_fig(trx_view)
                        st.plotly_chart(fig_bubble, use_container_width=True)

                        st.markdown("### 🍩 Komposisi Jumlah Transaksi")
                        fig_donut = trx_build_donut_fig(trx_view)
                        st.plotly_chart(fig_donut, use_container_width=True)

                        st.markdown("### ⚙️ Grafik Masing-masing Proses")

                        cols_per_row = 2
                        proses_chunks = [
                            chart_proses_cols[i:i + cols_per_row]
                            for i in range(0, len(chart_proses_cols), cols_per_row)
                        ]

                        for chunk in proses_chunks:
                            chart_cols = st.columns(len(chunk))

                            for i, proses in enumerate(chunk):
                                with chart_cols[i]:
                                    col_hari = f"{proses} (hari)"

                                    if col_hari not in trx_view.columns:
                                        continue

                                    data_proses = trx_view.dropna(subset=[col_hari]).sort_values(
                                        col_hari,
                                        ascending=True,
                                    )

                                    if data_proses.empty:
                                        st.info(f"Tidak ada data valid untuk proses {proses}.")
                                    else:
                                        fig_each = trx_build_process_fig(data_proses, proses)
                                        st.plotly_chart(fig_each, use_container_width=True)

                        # =====================================================
                        # TABEL RATA-RATA SLA
                        # =====================================================
                        with st.expander("📋 Tabel Detail Rata-rata SLA per Jenis Transaksi", expanded=False):
                            transaksi_display = trx_view.copy()

                            for col in chart_proses_cols:
                                if col in transaksi_display.columns:
                                    transaksi_display[f"{col} (Rata-rata)"] = transaksi_display[col].apply(
                                        trx_seconds_to_text
                                    )

                            display_cols = (
                                ["JENIS TRANSAKSI", "Jumlah Transaksi"]
                                + [
                                    f"{col} (Rata-rata)"
                                    for col in chart_proses_cols
                                    if f"{col} (Rata-rata)" in transaksi_display.columns
                                ]
                            )

                            st.dataframe(
                                transaksi_display[display_cols],
                                use_container_width=True,
                                hide_index=True,
                            )

                        # =====================================================
                        # DRILLDOWN DETAIL - SAFE MODE TANPA st.fragment
                        # =====================================================
                        st.markdown("### 🔍 Drilldown Detail Jenis Transaksi")

                        # Catatan:
                        # Jangan gunakan st.fragment di dalam st.tabs untuk kasus ini.
                        # Pada beberapa versi Streamlit, fragment rerun di dalam tab bisa membuat
                        # output menumpuk / keluar dari konteks tab, sehingga isi tab lain tampak
                        # muncul di bawah tab aktif.

                        if not detail_options:
                            st.info("Tidak ada jenis transaksi yang dapat ditampilkan untuk drilldown.")
                        else:
                            current_value = st.session_state.get(
                                "trx_detail_select_wow",
                                detail_options[0],
                            )

                            if current_value not in detail_options:
                                current_index = 0
                            else:
                                current_index = detail_options.index(current_value)

                            selected_detail = st.selectbox(
                                "Pilih jenis transaksi untuk drilldown",
                                options=detail_options,
                                index=current_index,
                                key="trx_detail_select_wow",
                            )

                            detail_df, detail_mean, detail_chart = trx_get_detail_objects(selected_detail)

                            if not detail_mean.empty:
                                detail_row = detail_mean.iloc[0]

                                d1, d2, d3 = st.columns(3)

                                d1.metric(
                                    "Jumlah Transaksi",
                                    trx_fmt_int(detail_row["Jumlah Transaksi"]),
                                )

                                d2.metric(
                                    "SLA Utama",
                                    trx_fmt_hari(detail_row["SLA Utama (hari)"]),
                                )

                                d3.metric(
                                    "Acuan SLA",
                                    sla_utama_label,
                                )

                                if not detail_chart.empty:
                                    fig_detail = trx_build_detail_fig(detail_chart, selected_detail)
                                    st.plotly_chart(
                                        fig_detail,
                                        use_container_width=True,
                                        key="trx_detail_chart_safe_wow",
                                    )
                                else:
                                    st.info("Tidak ada data SLA proses yang valid untuk jenis transaksi ini.")
                            else:
                                st.warning("Detail transaksi tidak ditemukan untuk pilihan ini.")

                            with st.expander("🔎 Lihat Data Baris Detail", expanded=False):
                                st.dataframe(
                                    detail_df,
                                    use_container_width=True,
                                    key="trx_detail_table_safe_wow",
                                )
# ===================== END OF TAB_TRANSAKSI =====================

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


# =========================================
# [ADD] Konfigurasi file khusus Nilai Transaksi
# =========================================
NILAI_DATA_PATH = os.path.join("data", "nilai_transaksi.xlsx")
NILAI_GITHUB_PATH = "data/nilai_transaksi.xlsx"  # bisa ubah kalau mau folder lain


def download_nilai_xlsx_from_github() -> bytes | None:
    """Ambil file nilai_transaksi.xlsx dari GitHub (kalau ada secrets)."""
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    info = github_get_file_info(NILAI_GITHUB_PATH)
    if not info or "content" not in info:
        return None
    try:
        return base64.b64decode(info["content"].encode())
    except Exception:
        return None


def upload_nilai_xlsx_to_github(file_bytes: bytes, message="Update Nilai Transaksi (via tab Nilai)") -> dict | None:
    """Upload/overwrite file nilai_transaksi.xlsx ke GitHub."""
    return upload_file_to_github(file_bytes, path=NILAI_GITHUB_PATH, message=message)


@st.cache_data(show_spinner=False)
def _read_nilai_excel_bytes(xlsx_bytes: bytes) -> pd.DataFrame:
    """Read excel dari bytes (cache)."""
    return pd.read_excel(BytesIO(xlsx_bytes))


@st.cache_data(show_spinner=False)
def _read_nilai_excel_path(path: str, size: int, mtime: float) -> pd.DataFrame:
    """Read excel dari path (cache)."""
    return pd.read_excel(path)


def load_nilai_df() -> pd.DataFrame | None:
    """Load data nilai: GitHub -> lokal -> None."""
    # 1) GitHub
    content = download_nilai_xlsx_from_github()
    if content:
        try:
            return _read_nilai_excel_bytes(content)
        except Exception:
            pass

    # 2) Lokal
    if os.path.exists(NILAI_DATA_PATH):
        try:
            stat = os.stat(NILAI_DATA_PATH)
            return _read_nilai_excel_path(NILAI_DATA_PATH, stat.st_size, stat.st_mtime)
        except Exception:
            return None

    return None


def _parse_rupiah_series(s: pd.Series) -> pd.Series:
    """
    Parse kolom NILAI dari:
    - angka
    - '192.250.000' / 'Rp 192.250.000'
    Menjadi float.
    """
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() >= 0.7:
        return num

    def one(v):
        if v is None:
            return float("nan")
        txt = str(v).strip()
        if txt == "" or txt.lower() in {"nan", "none", "-", "null"}:
            return float("nan")
        txt = txt.upper().replace("RP", "").replace("RUPIAH", "").strip()
        txt = re.sub(r"\s+", "", txt)
        # format Indonesia: 192.250.000 -> remove dots
        txt = txt.replace(".", "")
        # kalau ada koma sebagai desimal (jarang untuk rupiah), ubah ke titik
        txt = txt.replace(",", ".")
        return pd.to_numeric(txt, errors="coerce")

    return s.apply(one)


def _detect_col(df: pd.DataFrame, keywords: list[str]) -> str | None:
    cols = list(df.columns)
    for c in cols:
        cu = re.sub(r"\s+", " ", str(c).strip().upper())
        if all(k in cu for k in keywords):
            return c
    for c in cols:
        cu = re.sub(r"\s+", " ", str(c).strip().upper())
        if any(k in cu for k in keywords):
            return c
    return None


# =========================================
# [ADD] TAB NILAI TRANSAKSI (upload hanya di tab ini)
# =========================================
# ==============================
# TAB NILAI TRANSAKSI (FULL)
# ==============================
# ==============================
# TAB NILAI TRANSAKSI (FULL + SAVE BUCKET + FILTER PERIODE)
# ==============================
# ==============================
# TAB NILAI TRANSAKSI (EXEC DASH + COMPARE YEAR + FAST)
# ==============================
# ==============================
# FULL TAB NILAI TRANSAKSI (WOW + FAST + YOY BUCKETS DYNAMIC)
# ==============================
with tab_nilai:
    import os
    import re
    import json
    import math
    import base64
    from io import BytesIO
    from typing import Optional, List, Dict

    import pandas as pd
    import matplotlib.pyplot as plt
    import streamlit as st

    # =========================
    # CONFIG
    # =========================
    DATA_PATH = "data/nilai_transaksi.xlsx"
    DATA_GITHUB_PATH = "data/nilai_transaksi.xlsx"
    BUCKET_PATH = "data/nilai_bucket.json"
    BUCKET_GITHUB_PATH = "data/nilai_bucket.json"

    os.makedirs("data", exist_ok=True)

    st.subheader("💰 Nilai Transaksi — Direksi Dashboard")

    # =========================
    # FORMATTERS
    # =========================
    def fmt_int(n: float | int) -> str:
        try:
            return f"{int(n):,}".replace(",", ".")
        except Exception:
            return "-"

    def fmt_rp(x: float) -> str:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "-"
        return "Rp " + f"{x:,.0f}".replace(",", ".")

    def fmt_pct(x: float) -> str:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "-"
        return f"{x:.1f}%".replace(".", ",")

    def pct_delta(curr: float, prev: Optional[float]) -> Optional[str]:
        if prev is None or prev == 0 or (isinstance(prev, float) and math.isnan(prev)):
            return None
        p = (curr - prev) / prev * 100.0
        sign = "+" if p >= 0 else ""
        return f"{sign}{p:.1f}%".replace(".", ",")

    # =========================
    # GITHUB HELPERS (expects existing functions)
    # github_get_file_info(path)
    # upload_file_to_github(content_bytes, path=..., message=...)
    # =========================
    def github_get_bytes(path: str) -> Optional[bytes]:
        if not (GITHUB_TOKEN and GITHUB_REPO):
            return None
        try:
            info = github_get_file_info(path)
            if not info or "content" not in info:
                return None
            return base64.b64decode(info["content"].encode())
        except Exception:
            return None

    def github_put_bytes(path: str, content: bytes, message: str) -> bool:
        if not (GITHUB_TOKEN and GITHUB_REPO):
            return False
        try:
            res = upload_file_to_github(content, path=path, message=message)
            return bool(res)
        except Exception:
            return False

    # =========================
    # FAST IO
    # =========================
    @st.cache_data(show_spinner=False)
    def read_excel_cached(path: str, size: int, mtime: float) -> pd.DataFrame:
        return pd.read_excel(path)

    @st.cache_data(show_spinner=False)
    def read_excel_bytes(b: bytes) -> pd.DataFrame:
        return pd.read_excel(BytesIO(b))

    def load_local_df() -> Optional[pd.DataFrame]:
        if not os.path.exists(DATA_PATH):
            return None
        try:
            stat = os.stat(DATA_PATH)
            return read_excel_cached(DATA_PATH, stat.st_size, stat.st_mtime)
        except Exception:
            return None

    # =========================
    # COLUMN DETECT + PARSING
    # =========================
    def detect_col(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
        cols = list(df.columns)
        for c in cols:
            cu = re.sub(r"\s+", " ", str(c).strip().upper())
            if all(k in cu for k in keywords):
                return c
        for c in cols:
            cu = re.sub(r"\s+", " ", str(c).strip().upper())
            if any(k in cu for k in keywords):
                return c
        return None

    def parse_rupiah_vectorized(s: pd.Series) -> pd.Series:
        num = pd.to_numeric(s, errors="coerce")
        if num.notna().mean() >= 0.7:
            return num
        txt = s.astype(str).str.upper().str.strip()
        txt = txt.replace({"NAN": "", "NONE": "", "NULL": "", "-": ""})
        txt = txt.str.replace("RUPIAH", "", regex=False)
        txt = txt.str.replace("RP", "", regex=False)
        txt = txt.str.replace(r"\s+", "", regex=True)
        txt = txt.str.replace(".", "", regex=False)
        txt = txt.str.replace(",", "", regex=False)
        txt = txt.str.replace(r"[^0-9\-]", "", regex=True)
        return pd.to_numeric(txt, errors="coerce")

    def extract_year(period_s: pd.Series) -> pd.Series:
        s = period_s.astype(str).str.strip()
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        year = dt.dt.year
        mask = year.isna()
        if mask.any():
            extracted = s[mask].str.extract(r"(\d{4})", expand=False)
            year.loc[mask] = pd.to_numeric(extracted, errors="coerce")
        return year

    @st.cache_data(show_spinner=False)
    def preprocess(df: pd.DataFrame, col_periode: str, col_nilai: str) -> pd.DataFrame:
        out = df.copy()
        out["__YEAR__"] = extract_year(out[col_periode])
        out["__NILAI_NUM__"] = parse_rupiah_vectorized(out[col_nilai])
        out = out.dropna(subset=["__YEAR__", "__NILAI_NUM__"]).copy()
        out["__YEAR__"] = out["__YEAR__"].astype(int)
        return out

    # =========================
    # BUCKETS (dynamic thresholds)
    # thresholds: [t1,t2,...] => 0–t1, t1–t2, ..., >tN
    # =========================
    def build_edges(thresholds: List[float]) -> List[float]:
        t = [float(x) for x in thresholds if x is not None and not math.isnan(float(x))]
        t = sorted(set([x for x in t if x > 0]))
        return [0.0] + t + [float("inf")]

    def build_labels(edges: List[float]) -> List[str]:
        labs: List[str] = []
        for i in range(len(edges) - 1):
            lo, hi = edges[i], edges[i + 1]
            if math.isinf(hi):
                labs.append(f"> {lo:,.0f}".replace(",", "."))
            else:
                labs.append(f"{lo:,.0f} – {hi:,.0f}".replace(",", "."))
        return labs

    def load_bucket_cfg() -> Dict:
        default = {"mode": "dynamic", "thresholds": [10e6, 50e6, 500e6]}
        if os.path.exists(BUCKET_PATH):
            try:
                with open(BUCKET_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if isinstance(cfg, dict) and isinstance(cfg.get("thresholds"), list):
                        return cfg
            except Exception:
                pass
        b = github_get_bytes(BUCKET_GITHUB_PATH)
        if b:
            try:
                cfg = json.loads(b.decode("utf-8"))
                if isinstance(cfg, dict) and isinstance(cfg.get("thresholds"), list):
                    with open(BUCKET_PATH, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, ensure_ascii=False, indent=2)
                    return cfg
            except Exception:
                pass
        return default

    def save_bucket_cfg(thresholds: List[float]) -> None:
        thresholds = sorted(set([float(x) for x in thresholds if x is not None and float(x) > 0]))
        edges = build_edges(thresholds)
        payload = {
            "mode": "dynamic",
            "thresholds": thresholds,
            "edges": [("inf" if math.isinf(x) else x) for x in edges],
            "labels": build_labels(edges),
        }
        with open(BUCKET_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        if GITHUB_TOKEN and GITHUB_REPO:
            github_put_bytes(
                BUCKET_GITHUB_PATH,
                json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                "Update Nilai Buckets (dynamic)",
            )

    # =========================
    # ADMIN UPLOAD + MANUAL SYNC
    # =========================
    left, right = st.columns([2, 1])
    with left:
        with st.expander("📤 Upload Data Nilai Transaksi (Admin Only)", expanded=is_admin):
            if not is_admin:
                st.info("Hanya admin yang dapat upload.")
                uploaded = None
            else:
                uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"], key="nilai_upload_rewrite_v1")
            if is_admin and uploaded is not None:
                b = uploaded.getvalue()
                try:
                    df_now = read_excel_bytes(b)
                    st.session_state["nilai_raw_df"] = df_now
                    st.success(f"✅ Upload terbaca: {fmt_int(len(df_now))} baris")
                    st.dataframe(df_now.head(20), use_container_width=True)
                except Exception as e:
                    st.error(f"Gagal baca Excel: {e}")
                    st.stop()

                with open(DATA_PATH, "wb") as f:
                    f.write(b)

                if GITHUB_TOKEN and GITHUB_REPO:
                    with st.spinner("Sync ke GitHub..."):
                        ok = github_put_bytes(DATA_GITHUB_PATH, b, "Update Nilai Transaksi (tab Nilai)")
                    if ok:
                        st.success("✅ Tersimpan lokal & tersinkron ke GitHub.")
                    else:
                        st.warning("⚠️ Tersimpan lokal, tapi gagal upload ke GitHub.")
                else:
                    st.success("✅ Tersimpan lokal (GitHub tidak dikonfigurasi).")

                st.cache_data.clear()
                st.rerun()

    with right:
        st.caption("⚡ Fast mode: load local-first. GitHub sync manual.")
        if is_admin and (GITHUB_TOKEN and GITHUB_REPO):
            if st.button("🔄 Sync dari GitHub", key="nilai_sync_rewrite_v1"):
                with st.spinner("Mengambil file dari GitHub..."):
                    xlsx = github_get_bytes(DATA_GITHUB_PATH)
                    cfgb = github_get_bytes(BUCKET_GITHUB_PATH)

                if xlsx:
                    df_now = read_excel_bytes(xlsx)
                    st.session_state["nilai_raw_df"] = df_now
                    with open(DATA_PATH, "wb") as f:
                        f.write(xlsx)

                if cfgb:
                    try:
                        cfg = json.loads(cfgb.decode("utf-8"))
                        with open(BUCKET_PATH, "w", encoding="utf-8") as f:
                            json.dump(cfg, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                st.cache_data.clear()
                st.success("✅ Sync selesai.")
                st.rerun()

    # =========================
    # LOAD DATA (SESSION -> LOCAL)
    # =========================
    df_raw = st.session_state.get("nilai_raw_df")
    if df_raw is None:
        df_raw = load_local_df()
    if df_raw is None or df_raw.empty:
        st.warning("Belum ada data Nilai Transaksi. Admin silakan upload di atas.")
        st.stop()

    st.caption(f"Loaded: {fmt_int(len(df_raw))} baris")

    # =========================
    # MAPPING KOLOM
    # =========================
    cols = list(df_raw.columns)
    auto_periode = detect_col(df_raw, ["PERIODE"]) or detect_col(df_raw, ["PERIOD"]) or cols[0]
    auto_nilai = (
        detect_col(df_raw, ["NILAI"])
        or detect_col(df_raw, ["AMOUNT"])
        or detect_col(df_raw, ["VALUE"])
        or detect_col(df_raw, ["NOMINAL"])
        or cols[0]
    )
    auto_vendor = detect_col(df_raw, ["VENDOR"]) or detect_col(df_raw, ["NAMA", "VENDOR"])
    auto_jenis = detect_col(df_raw, ["JENIS", "TRANSAKSI"]) or detect_col(df_raw, ["TRANSAKSI"])

    with st.expander("⚙️ Mapping Kolom", expanded=False):
        col_periode = st.selectbox("Kolom PERIODE", cols, index=cols.index(auto_periode), key="map_periode_rewrite_v1")
        col_nilai = st.selectbox("Kolom NILAI", cols, index=cols.index(auto_nilai), key="map_nilai_rewrite_v1")
        col_vendor = st.selectbox(
            "Kolom VENDOR (opsional)",
            ["(none)"] + cols,
            index=(["(none)"] + cols).index(auto_vendor) if auto_vendor in cols else 0,
            key="map_vendor_rewrite_v1",
        )
        col_jenis = st.selectbox(
            "Kolom JENIS TRANSAKSI (opsional)",
            ["(none)"] + cols,
            index=(["(none)"] + cols).index(auto_jenis) if auto_jenis in cols else 0,
            key="map_jenis_rewrite_v1",
        )

    # =========================
    # PREPROCESS (CACHED)
    # =========================
    df = preprocess(df_raw, col_periode=col_periode, col_nilai=col_nilai)
    if df.empty:
        st.error("Tidak ada data valid setelah parsing YEAR/NILAI. Cek mapping & format data.")
        st.dataframe(df_raw.head(30), use_container_width=True)
        st.stop()

    years_all = sorted(df["__YEAR__"].unique().tolist())

    # =========================
    # GLOBAL FILTERS (apply to all)
    # =========================
    st.markdown("### 🔎 Filter Global (berlaku untuk semua tab)")
    gf1, gf2 = st.columns([1.2, 2.0])

    with gf1:
        years_global = st.multiselect(
            "Tahun",
            options=years_all,
            default=years_all[-3:] if len(years_all) >= 3 else years_all,
            key="global_years_rewrite_v1",
        )
    if not years_global:
        st.warning("Pilih minimal 1 tahun.")
        st.stop()

    df_global = df[df["__YEAR__"].isin([int(y) for y in years_global])].copy()

    with gf2:
        if col_jenis != "(none)" and col_jenis in df_global.columns:
            jenis_opts = sorted(df_global[col_jenis].dropna().astype(str).unique().tolist())
            jenis_selected = st.multiselect(
                "Jenis Transaksi (multi)",
                options=jenis_opts,
                default=jenis_opts,
                key="global_jenis_rewrite_v1",
            )
            if not jenis_selected:
                st.warning("Pilih minimal 1 jenis transaksi.")
                st.stop()
            df_global = df_global[df_global[col_jenis].astype(str).isin(jenis_selected)].copy()
        else:
            jenis_selected = None
            st.caption("Filter jenis transaksi nonaktif (mapping jenis belum dipilih).")

    if df_global.empty:
        st.warning("Tidak ada data untuk kombinasi filter global.")
        st.stop()

    # =========================
    # SUB-TABS
    # =========================
    tab_nilai_exec, tab_nilai_yoy, tab_nilai_vendor = st.tabs(
        ["🏁 Executive Summary", "📊 YoY Buckets & Analysis", "🏷️ Vendor & Drilldown"]
    )

    # =====================================================
    # TAB 1: EXECUTIVE SUMMARY (Bucket multi OR Custom Range multi)
    # =====================================================
    with tab_nilai_exec:
        st.markdown("### 🎯 Executive Snapshot")

        cfg0 = load_bucket_cfg()
        thresholds0 = cfg0.get("thresholds", [10e6, 50e6, 500e6])
        edges0 = build_edges(thresholds0)
        labs0 = build_labels(edges0)

        dfx = df_global.copy()
        dfx["Bucket"] = pd.cut(dfx["__NILAI_NUM__"], bins=edges0, labels=labs0, right=False, include_lowest=True)

        c1, c2, c3 = st.columns([1.6, 1.6, 1.2])
        with c1:
            focus_mode = st.radio(
                "Mode sorot",
                options=["Bucket", "Custom Range (Rp)"],
                horizontal=True,
                key="exec_focus_mode_rewrite_v1",
            )
        with c2:
            quick_focus = st.selectbox(
                "Quick focus",
                options=["(none)", ">= 100 juta", ">= 250 juta", ">= 500 juta", ">= 1 Miliar"],
                index=0,
                key="exec_quick_focus_rewrite_v1",
            )
        with c3:
            show_insight = st.toggle("Insight otomatis", value=True, key="exec_insight_rewrite_v1")

        # ---- custom range multi helpers
        def _ensure_ranges_session(key: str, defaults: list[dict]) -> None:
            if key not in st.session_state:
                st.session_state[key] = defaults

        def _clamp_nonneg(x: float) -> float:
            try:
                return max(0.0, float(x))
            except Exception:
                return 0.0

        focus_df = dfx.copy()
        focus_title = ""

        if focus_mode == "Bucket":
            focus_buckets = st.multiselect(
                "Sorot bucket (multi)",
                options=labs0,
                default=[labs0[min(2, len(labs0) - 1)]],
                key="exec_focus_buckets_rewrite_v1",
            )
            if not focus_buckets:
                st.warning("Pilih minimal 1 bucket untuk sorotan.")
                st.stop()
            focus_df = dfx[dfx["Bucket"].astype(str).isin([str(x) for x in focus_buckets])].copy()
            focus_title = " + ".join([str(x) for x in focus_buckets])

        else:
            st.markdown("#### 🎚️ Sorot Range Custom (multi)")
            st.caption("Isi min–max sendiri. Jika max ∞ → tanpa batas atas.")

            _default_ranges = [
                {"min": 0.0, "max": 10_000_000.0},
                {"min": 10_000_000.0, "max": 50_000_000.0},
                {"min": 50_000_000.0, "max": 500_000_000.0},
                {"min": 500_000_000.0, "max": None},
            ]
            _ensure_ranges_session("exec_custom_ranges_rewrite_v1", _default_ranges)

            r1, r2, r3 = st.columns([1, 1, 2])
            with r1:
                if st.button("➕ Tambah range", key="exec_add_range_rewrite_v1"):
                    st.session_state["exec_custom_ranges_rewrite_v1"].append({"min": 0.0, "max": None})
            with r2:
                if st.button("➖ Hapus terakhir", key="exec_del_range_rewrite_v1"):
                    if st.session_state["exec_custom_ranges_rewrite_v1"]:
                        st.session_state["exec_custom_ranges_rewrite_v1"] = st.session_state["exec_custom_ranges_rewrite_v1"][:-1]
            with r3:
                if quick_focus != "(none)":
                    if quick_focus == ">= 100 juta":
                        st.session_state["exec_custom_ranges_rewrite_v1"] = [{"min": 100_000_000.0, "max": None}]
                    elif quick_focus == ">= 250 juta":
                        st.session_state["exec_custom_ranges_rewrite_v1"] = [{"min": 250_000_000.0, "max": None}]
                    elif quick_focus == ">= 500 juta":
                        st.session_state["exec_custom_ranges_rewrite_v1"] = [{"min": 500_000_000.0, "max": None}]
                    elif quick_focus == ">= 1 Miliar":
                        st.session_state["exec_custom_ranges_rewrite_v1"] = [{"min": 1_000_000_000.0, "max": None}]

            ranges_ui: list[dict] = []
            for i, rr in enumerate(st.session_state["exec_custom_ranges_rewrite_v1"], start=1):
                cmin, cmax, cen = st.columns([1, 1, 1.1])
                with cmin:
                    vmin = st.number_input(
                        f"Range {i} — Min (Rp)",
                        min_value=0.0,
                        value=float(rr.get("min") or 0.0),
                        step=1e6,
                        key=f"exec_rmin_rewrite_{i}_v1",
                    )
                with cmax:
                    inf = st.checkbox("∞ (tanpa max)", value=(rr.get("max") is None), key=f"exec_rinf_rewrite_{i}_v1")
                    if inf:
                        vmax = None
                    else:
                        vmax = st.number_input(
                            f"Range {i} — Max (Rp)",
                            min_value=0.0,
                            value=float(rr.get("max") or 0.0),
                            step=1e6,
                            key=f"exec_rmax_rewrite_{i}_v1",
                        )
                with cen:
                    enabled = st.checkbox("Aktif", value=True, key=f"exec_ren_rewrite_{i}_v1")

                ranges_ui.append(
                    {"min": _clamp_nonneg(vmin), "max": None if vmax is None else _clamp_nonneg(vmax), "enabled": bool(enabled)}
                )

            ranges_active = []
            for rr in ranges_ui:
                if not rr["enabled"]:
                    continue
                lo = float(rr["min"])
                hi = rr["max"]
                if hi is not None and hi < lo:
                    lo, hi = hi, lo
                ranges_active.append({"min": lo, "max": hi})

            if not ranges_active:
                st.warning("Aktifkan minimal 1 range.")
                st.stop()

            mask = pd.Series(False, index=focus_df.index)
            for rr in ranges_active:
                lo, hi = rr["min"], rr["max"]
                if hi is None:
                    mask = mask | (focus_df["__NILAI_NUM__"] >= lo)
                else:
                    mask = mask | ((focus_df["__NILAI_NUM__"] >= lo) & (focus_df["__NILAI_NUM__"] <= hi))

            focus_df = focus_df[mask].copy()

            parts = []
            for rr in ranges_active:
                lo, hi = rr["min"], rr["max"]
                if hi is None:
                    parts.append(f">= {fmt_rp(lo)}")
                else:
                    parts.append(f"{fmt_rp(lo)} — {fmt_rp(hi)}")
            focus_title = " + ".join(parts)

        st.markdown(f"**Sorotan aktif:** {focus_title}")

        # ---- overall KPI YoY (All)
        overall = (
            dfx.groupby("__YEAR__")["__NILAI_NUM__"]
            .agg(Transaksi="size", Total="sum", Rata2="mean")
            .reset_index()
            .rename(columns={"__YEAR__": "Tahun"})
            .sort_values("Tahun")
        )
        last_year = int(overall["Tahun"].max())
        prev_year = int(sorted(overall["Tahun"].unique())[-2]) if len(overall["Tahun"].unique()) >= 2 else None
        ov = overall.set_index("Tahun")

        cur_tx = float(ov.loc[last_year, "Transaksi"])
        cur_total = float(ov.loc[last_year, "Total"])
        cur_avg = float(ov.loc[last_year, "Rata2"])

        prev_tx = float(ov.loc[prev_year, "Transaksi"]) if (prev_year in ov.index) else None
        prev_total = float(ov.loc[prev_year, "Total"]) if (prev_year in ov.index) else None
        prev_avg = float(ov.loc[prev_year, "Rata2"]) if (prev_year in ov.index) else None

        st.markdown("#### 🧾 KPI Utama (All Transactions)")
        k1, k2, k3 = st.columns(3)
        k1.metric(f"Jumlah Transaksi ({last_year})", fmt_int(cur_tx), delta=pct_delta(cur_tx, prev_tx))
        k2.metric(f"Total Nilai ({last_year})", fmt_rp(cur_total), delta=pct_delta(cur_total, prev_total))
        k3.metric(f"Rata-rata ({last_year})", fmt_rp(cur_avg), delta=pct_delta(cur_avg, prev_avg))

        st.markdown(f"#### 🔥 KPI Sorotan: **{focus_title}**")
        if focus_df.empty:
            st.info("Tidak ada data pada sorotan untuk filter global saat ini.")
        else:
            focus_kpi = (
                focus_df.groupby("__YEAR__")["__NILAI_NUM__"]
                .agg(Transaksi="size", Total="sum", Rata2="mean")
                .reset_index()
                .rename(columns={"__YEAR__": "Tahun"})
                .sort_values("Tahun")
            )
            fk = focus_kpi.set_index("Tahun")

            cur_f_tx = float(fk.loc[last_year, "Transaksi"]) if (last_year in fk.index) else 0.0
            cur_f_total = float(fk.loc[last_year, "Total"]) if (last_year in fk.index) else 0.0
            cur_f_avg = float(fk.loc[last_year, "Rata2"]) if (last_year in fk.index) else float("nan")

            prev_f_tx = float(fk.loc[prev_year, "Transaksi"]) if (prev_year in fk.index) else None
            prev_f_total = float(fk.loc[prev_year, "Total"]) if (prev_year in fk.index) else None
            prev_f_avg = float(fk.loc[prev_year, "Rata2"]) if (prev_year in fk.index) else None

            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Transaksi (sorotan)", fmt_int(cur_f_tx), delta=pct_delta(cur_f_tx, prev_f_tx))
            b2.metric("Total Nilai (sorotan)", fmt_rp(cur_f_total), delta=pct_delta(cur_f_total, prev_f_total))
            b3.metric("Rata-rata (sorotan)", fmt_rp(cur_f_avg) if not pd.isna(cur_f_avg) else "-", delta=pct_delta(cur_f_avg, prev_f_avg))
            b4.metric("% share transaksi", fmt_pct((cur_f_tx / cur_tx * 100.0) if cur_tx else float("nan")))

            with st.expander("📋 Tabel KPI Sorotan (YoY)", expanded=False):
                show_focus = focus_kpi.copy()
                show_focus["Total"] = show_focus["Total"].apply(lambda x: fmt_rp(float(x)))
                show_focus["Rata2"] = show_focus["Rata2"].apply(lambda x: fmt_rp(float(x)) if not pd.isna(x) else "-")
                st.dataframe(show_focus, use_container_width=True)

        st.markdown("#### 📈 Tren YoY")
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(overall["Tahun"].astype(str), overall["Total"], marker="o")
        ax1.set_title("Total Nilai per Tahun")
        ax1.set_xlabel("Tahun")
        ax1.set_ylabel("Total Nilai (Rp)")
        ax1.grid(axis="y", linestyle="--", alpha=0.35)
        st.pyplot(fig1)

        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.bar(overall["Tahun"].astype(str), overall["Transaksi"])
        ax2.set_title("Jumlah Transaksi per Tahun")
        ax2.set_xlabel("Tahun")
        ax2.set_ylabel("Jumlah")
        ax2.grid(axis="y", linestyle="--", alpha=0.35)
        st.pyplot(fig2)

        if show_insight and len(overall) >= 2:
            st.markdown("#### 🧠 Insight Otomatis")
            top_year = overall.sort_values("Total", ascending=False).iloc[0]
            st.write(
                f"- Tahun tertinggi (Total Nilai): **{int(top_year['Tahun'])}** ({fmt_rp(float(top_year['Total']))}).\n"
                f"- Tahun terakhir **{last_year}**: Total {pct_delta(cur_total, prev_total) or 'n/a'} | Qty {pct_delta(cur_tx, prev_tx) or 'n/a'}."
            )

        with st.expander("📋 Tabel KPI YoY (All)", expanded=False):
            show_overall = overall.copy()
            show_overall["Total"] = show_overall["Total"].apply(lambda x: fmt_rp(float(x)))
            show_overall["Rata2"] = show_overall["Rata2"].apply(lambda x: fmt_rp(float(x)))
            st.dataframe(show_overall, use_container_width=True)

    # =====================================================
    # TAB 2: YOY BUCKETS & ANALYSIS (uses global filters too)
    # =====================================================
    with tab_nilai_yoy:
        st.markdown("### 📊 Analisis YoY per Range Nilai (Custom)")

        cfg = load_bucket_cfg()
        base_thresholds = cfg.get("thresholds", [10e6, 50e6, 500e6])

        if "dyn_thresholds_yoy_rewrite_v1" not in st.session_state:
            st.session_state["dyn_thresholds_yoy_rewrite_v1"] = [float(x) for x in base_thresholds]

        with st.expander("🧩 Editor Range (Tambah/Kurangi) + Simpan", expanded=True):
            st.caption("Threshold membentuk bucket: 0–t1, t1–t2, ..., >tN.")

            a1, a2, a3, a4 = st.columns([1, 1, 1.2, 1.8])
            if a1.button("➕ Tambah threshold", key="yoy_add_thr_rewrite_v1"):
                last = st.session_state["dyn_thresholds_yoy_rewrite_v1"][-1] if st.session_state["dyn_thresholds_yoy_rewrite_v1"] else 10e6
                st.session_state["dyn_thresholds_yoy_rewrite_v1"].append(float(last * 2))

            if a2.button("➖ Hapus terakhir", key="yoy_del_thr_rewrite_v1"):
                if st.session_state["dyn_thresholds_yoy_rewrite_v1"]:
                    st.session_state["dyn_thresholds_yoy_rewrite_v1"] = st.session_state["dyn_thresholds_yoy_rewrite_v1"][:-1]

            if a3.button("↩ Reset default", key="yoy_reset_thr_rewrite_v1"):
                st.session_state["dyn_thresholds_yoy_rewrite_v1"] = [float(x) for x in base_thresholds]

            thresholds_ui: List[float] = []
            for i, v in enumerate(st.session_state["dyn_thresholds_yoy_rewrite_v1"], start=1):
                thresholds_ui.append(
                    st.number_input(
                        f"Threshold {i} (Rp)",
                        min_value=0.0,
                        value=float(v),
                        step=1e6,
                        key=f"yoy_thr_input_rewrite_{i}_v1",
                    )
                )

            thresholds_norm = sorted(set([float(x) for x in thresholds_ui if x is not None and float(x) > 0]))
            edges = build_edges(thresholds_norm)
            labs = build_labels(edges)

            st.write("Preview bucket:")
            st.write(labs)

            if is_admin:
                if a4.button("💾 Simpan Bucket (Persisten)", key="yoy_save_thr_rewrite_v1"):
                    save_bucket_cfg(thresholds_norm)
                    st.session_state["dyn_thresholds_yoy_rewrite_v1"] = thresholds_norm
                    st.success("✅ Bucket tersimpan.")
            else:
                st.info("Hanya admin yang bisa menyimpan. Anda tetap bisa mencoba sementara.")

        dfy = df_global.copy()
        dfy["Bucket"] = pd.cut(dfy["__NILAI_NUM__"], bins=edges, labels=labs, right=False, include_lowest=True)

        grp = (
            dfy.dropna(subset=["Bucket"])
            .groupby(["__YEAR__", "Bucket"])["__NILAI_NUM__"]
            .agg(Jumlah="size", Total="sum")
            .reset_index()
            .rename(columns={"__YEAR__": "Tahun"})
        )

        pivot_cnt = grp.pivot_table(index="Bucket", columns="Tahun", values="Jumlah", fill_value=0).reindex(labs)
        pivot_total = grp.pivot_table(index="Bucket", columns="Tahun", values="Total", fill_value=0.0).reindex(labs)

        st.markdown("#### ✅ Jumlah Transaksi per Range (per Tahun)")
        st.dataframe(pivot_cnt, use_container_width=True)

        st.markdown("#### ✅ Total Nilai per Range (per Tahun)")
        pivot_total_fmt = pivot_total.copy()
        for c in pivot_total_fmt.columns:
            pivot_total_fmt[c] = pivot_total_fmt[c].apply(lambda x: fmt_rp(float(x)))
        st.dataframe(pivot_total_fmt, use_container_width=True)

        st.markdown("#### 📌 % Share Quantity (per Range, per Tahun)")
        qty_share = pivot_cnt.div(pivot_cnt.sum(axis=0).replace(0, float("nan")), axis=1) * 100.0
        qty_share_fmt = qty_share.copy()
        for c in qty_share_fmt.columns:
            qty_share_fmt[c] = qty_share_fmt[c].apply(lambda x: fmt_pct(float(x)) if not pd.isna(x) else "-")
        st.dataframe(qty_share_fmt, use_container_width=True)

        st.markdown("#### 📌 % Share Nilai (per Range, per Tahun)")
        val_share = pivot_total.div(pivot_total.sum(axis=0).replace(0, float("nan")), axis=1) * 100.0
        val_share_fmt = val_share.copy()
        for c in val_share_fmt.columns:
            val_share_fmt[c] = val_share_fmt[c].apply(lambda x: fmt_pct(float(x)) if not pd.isna(x) else "-")
        st.dataframe(val_share_fmt, use_container_width=True)

        years_sorted = sorted(pivot_cnt.columns.tolist())
        x = list(range(len(years_sorted)))

        st.markdown("#### 📊 100% Stacked — Komposisi Quantity")
        label_pct_qty = st.toggle("Tampilkan label % (Quantity)", value=False, key="yoy_label_qty_rewrite_v1")

        figq, axq = plt.subplots(figsize=(10, 5))
        bottom = [0.0] * len(years_sorted)
        for bucket in labs:
            vals = []
            for y in years_sorted:
                v = float(qty_share.loc[bucket, y]) if (bucket in qty_share.index and y in qty_share.columns) else 0.0
                vals.append(0.0 if math.isnan(v) else v)
            axq.bar(x, vals, bottom=bottom, label=str(bucket))
            if label_pct_qty:
                for i, p in enumerate(vals):
                    if p >= 6.0:
                        axq.text(i, bottom[i] + p / 2, f"{p:.0f}%", ha="center", va="center", fontsize=8)
            bottom = [bottom[i] + vals[i] for i in range(len(vals))]

        axq.set_title("Komposisi % Jumlah Transaksi per Tahun (100% Stacked)")
        axq.set_xlabel("Tahun")
        axq.set_ylabel("% Quantity")
        axq.set_xticks(x)
        axq.set_xticklabels([str(y) for y in years_sorted])
        axq.set_ylim(0, 100)
        axq.grid(axis="y", linestyle="--", alpha=0.35)
        axq.legend(title="Bucket", bbox_to_anchor=(1.02, 1), loc="upper left")
        st.pyplot(figq)

        st.markdown("#### 💰 100% Stacked — Komposisi Nilai")
        label_pct_val = st.toggle("Tampilkan label % (Nilai)", value=False, key="yoy_label_val_rewrite_v1")

        figv, axv = plt.subplots(figsize=(10, 5))
        bottom = [0.0] * len(years_sorted)
        for bucket in labs:
            vals = []
            for y in years_sorted:
                v = float(val_share.loc[bucket, y]) if (bucket in val_share.index and y in val_share.columns) else 0.0
                vals.append(0.0 if math.isnan(v) else v)
            axv.bar(x, vals, bottom=bottom, label=str(bucket))
            if label_pct_val:
                for i, p in enumerate(vals):
                    if p >= 6.0:
                        axv.text(i, bottom[i] + p / 2, f"{p:.0f}%", ha="center", va="center", fontsize=8)
            bottom = [bottom[i] + vals[i] for i in range(len(vals))]

        axv.set_title("Komposisi % Total Nilai per Tahun (100% Stacked)")
        axv.set_xlabel("Tahun")
        axv.set_ylabel("% Nilai")
        axv.set_xticks(x)
        axv.set_xticklabels([str(y) for y in years_sorted])
        axv.set_ylim(0, 100)
        axv.grid(axis="y", linestyle="--", alpha=0.35)
        axv.legend(title="Bucket", bbox_to_anchor=(1.02, 1), loc="upper left")
        st.pyplot(figv)

        st.markdown("#### 🧠 Insight Bucket (ringkas)")
        try:
            last_y = max(years_sorted)
            top_qty_bucket = pivot_cnt[last_y].idxmax()
            top_val_bucket = pivot_total[last_y].idxmax()
            st.write(
                f"- Tahun **{last_y}**: bucket **qty terbesar** = **{top_qty_bucket}** "
                f"({fmt_int(int(pivot_cnt.loc[top_qty_bucket, last_y]))} transaksi; {fmt_pct(float(qty_share.loc[top_qty_bucket, last_y]))})."
            )
            st.write(
                f"- Tahun **{last_y}**: bucket **nilai terbesar** = **{top_val_bucket}** "
                f"({fmt_rp(float(pivot_total.loc[top_val_bucket, last_y]))}; {fmt_pct(float(val_share.loc[top_val_bucket, last_y]))})."
            )
        except Exception:
            pass

        with st.expander("🔎 Detail groupby (opsional)", expanded=False):
            st.dataframe(grp.sort_values(["Tahun", "Bucket"]), use_container_width=True)

    # =====================================================
    # TAB 3: VENDOR (also uses global filters)
    # =====================================================
    with tab_nilai_vendor:
        st.markdown("### 🏷️ Vendor Spotlight")

        if col_vendor == "(none)":
            st.info("Pilih kolom vendor di Mapping Kolom untuk membuka analisis vendor.")
            st.stop()

        cfg = load_bucket_cfg()
        thresholds = cfg.get("thresholds", [10e6, 50e6, 500e6])
        edges = build_edges(thresholds)
        labs = build_labels(edges)

        dfv = df_global.copy()
        dfv["Bucket"] = pd.cut(dfv["__NILAI_NUM__"], bins=edges, labels=labs, right=False, include_lowest=True)

        c1, c2, c3 = st.columns([1.3, 1.0, 1.7])
        with c1:
            bucket_pick = st.selectbox("Bucket fokus", options=labs, index=min(2, len(labs) - 1), key="vendor_bucket_rewrite_v1")
        with c2:
            topn = st.number_input("Top N", min_value=5, max_value=50, value=10, step=5, key="vendor_topn_rewrite_v1")
        with c3:
            show_detail = st.toggle("Tampilkan detail baris (lebih berat)", value=False, key="vendor_detail_rewrite_v1")

        dv = dfv[dfv["Bucket"].astype(str) == str(bucket_pick)].copy()
        if dv.empty:
            st.warning("Tidak ada data untuk filter ini.")
            st.stop()

        top_vendor = (
            dv.groupby(dv[col_vendor].astype(str))["__NILAI_NUM__"]
            .agg(Total="sum", Transaksi="size")
            .reset_index()
            .sort_values("Total", ascending=False)
            .head(int(topn))
        )

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(top_vendor[col_vendor].astype(str), top_vendor["Transaksi"])
        ax.set_title(f"Top Vendor — Jumlah Transaksi (Bucket {bucket_pick})")
        ax.set_xlabel("Vendor")
        ax.set_ylabel("Jumlah")
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        for lab in ax.get_xticklabels():
            lab.set_rotation(25)
            lab.set_ha("right")
        st.pyplot(fig)

        show_vendor = top_vendor.copy()
        show_vendor["Total"] = show_vendor["Total"].apply(lambda x: fmt_rp(float(x)))
        st.dataframe(show_vendor, use_container_width=True)

        if show_detail:
            st.markdown("#### 🔎 Detail Baris (Filtered)")
            detail_cols = [c for c in [col_periode, col_vendor, col_nilai] if c in dv.columns]
            if col_jenis != "(none)" and col_jenis in dv.columns:
                detail_cols.insert(1, col_jenis)
            detail_cols += ["__YEAR__", "__NILAI_NUM__", "Bucket"]
            st.dataframe(dv[detail_cols].sort_values("__NILAI_NUM__", ascending=False), use_container_width=True)
    

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

# =========================
# TAB ANALISIS DATA (BARU)
# =========================
def render_tab_analisis_data_v1(df_source: pd.DataFrame, periode_col="PERIODE_DATETIME", sla_col="SLA"):
    import numpy as np
    import pandas as pd
    import streamlit as st

    def safe_pct(a, b):
        if a is None or pd.isna(a) or a == 0:
            return np.nan
        return (b - a) / a * 100

    def filter_range(df, start_dt, end_dt):
        m = (df[periode_col] >= start_dt) & (df[periode_col] <= end_dt)
        return df.loc[m].copy()

    def ensure_sla_seconds_local(df):
        # kolom aman: tidak bentrok dengan tab lain
        col = "__SLA_SECONDS_ANALYSIS__"
        if col not in df.columns:
            df[col] = df[sla_col].apply(parse_sla)
        return df, col

    st.subheader("📊 Analisis Data (Perbandingan 2 Periode)")

    if df_source is None or df_source.empty:
        st.warning("Data kosong.")
        return

    if periode_col not in df_source.columns:
        st.error(f"Kolom {periode_col} tidak ditemukan.")
        return

    df_base = df_source.dropna(subset=[periode_col]).copy()
    if df_base.empty:
        st.warning("Data periode kosong.")
        return

    labels = sorted(df_base[periode_col].dt.to_period("M").astype(str).unique().tolist())
    if not labels:
        st.warning("Tidak ada periode yang bisa dipilih.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Periode A (Baseline)**")
        startA = st.selectbox("Mulai A", labels, index=0, key="ana_startA")
        endA   = st.selectbox("Sampai A", labels, index=len(labels)-1, key="ana_endA")
    with c2:
        st.markdown("**Periode B (Pembanding)**")
        startB = st.selectbox("Mulai B", labels, index=0, key="ana_startB")
        endB   = st.selectbox("Sampai B", labels, index=len(labels)-1, key="ana_endB")

    startA_dt = pd.Period(startA).to_timestamp()
    endA_dt   = pd.Period(endA).to_timestamp() + pd.offsets.MonthEnd(0)
    startB_dt = pd.Period(startB).to_timestamp()
    endB_dt   = pd.Period(endB).to_timestamp() + pd.offsets.MonthEnd(0)

    if startA_dt > endA_dt or startB_dt > endB_dt:
        st.error("Rentang periode tidak valid.")
        return

    dfA = filter_range(df_base, startA_dt, endA_dt)
    dfB = filter_range(df_base, startB_dt, endB_dt)

    # ===== VOLUME TRANSAKSI =====
    totalA, totalB = len(dfA), len(dfB)
    d_total = totalB - totalA
    p_total = safe_pct(totalA, totalB)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Transaksi (A)", f"{totalA:,}")
    m2.metric(
        "Total Transaksi (B)",
        f"{totalB:,}",
        delta=f"{d_total:+,}" + ("" if np.isnan(p_total) else f" ({p_total:+.1f}%)")
    )

    # ===== SLA COMPARISON =====
    if sla_col not in df_base.columns:
        st.info(f"Kolom SLA '{sla_col}' tidak ada → analisis SLA tidak ditampilkan (hanya volume transaksi).")
        return

    dfA, sla_sec_col = ensure_sla_seconds_local(dfA)
    dfB, _ = ensure_sla_seconds_local(dfB)

    sA = dfA[sla_sec_col].dropna()
    sB = dfB[sla_sec_col].dropna()

    meanA = float(sA.mean()) if len(sA) else np.nan
    meanB = float(sB.mean()) if len(sB) else np.nan
    d_mean = meanB - meanA if np.isfinite(meanA) and np.isfinite(meanB) else np.nan
    p_mean = safe_pct(meanA, meanB) if np.isfinite(meanA) and np.isfinite(meanB) else np.nan

    m3.metric("Rata-rata SLA (A)", "-" if np.isnan(meanA) else seconds_to_sla_format(meanA))
    m4.metric(
        "Rata-rata SLA (B)",
        "-" if np.isnan(meanB) else seconds_to_sla_format(meanB),
        delta="-" if np.isnan(d_mean) else f"{seconds_to_sla_format(d_mean)}" + ("" if np.isnan(p_mean) else f" ({p_mean:+.1f}%)")
    )

    st.markdown("### Ringkasan (Nominal & %)")
    summary = pd.DataFrame([
        ["Transaksi", totalA, totalB, d_total, p_total],
        ["Mean SLA (detik)", meanA, meanB, d_mean, p_mean],
    ], columns=["Metrik", "A", "B", "Δ (B-A)", "Δ %"])

    st.dataframe(summary, use_container_width=True)

# =========================
# TAB ANALISIS DATA — FAST + EXECUTIVE DASHBOARD (Direksi)
# Update:
# - Warna font lebih kontras (lebih "kelihatan")
# - SLA ringkas: 2 desimal -> "3,22 hari"
# - KPI card & badge tetap aman (tidak ganggu fitur tab lain)
# =========================
# ============================================================
# FULL COPY-PASTE PACKAGE
# 1) HELPER FUNCTIONS (tempel di atas: with tab_analisis:)
# 2) TAB_ANALISIS (full)
# 3) BLOK POSTER EXECUTIVE SUMMARY (sudah include di tab_analisis)
#
# FIX UTAMA:
# - Layout poster dirapikan agar TIDAK TIMPANG TINDIH
# - Logo kiri/kanan aman (auto-fit)
# - Judul/subjudul/period/timestamp diposisikan ulang
# - Badge delta dipindah ke area yang aman
# - Chart diberi ruang lebih, label bulan diputar & diperkecil
# ============================================================

import io, os, re
import numpy as np
import pandas as pd
from datetime import datetime

# Logo (sesuai koreksi)
LOGO_LEFT_URL  = "https://raw.githubusercontent.com/firmanaditya90/SLA/main/Danantara.png"   # Danantara (kiri atas)
LOGO_RIGHT_URL = "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png"   # ASDP (kanan atas)

@st.cache_data(show_spinner=False)
def _fetch_image_bytes(url: str) -> bytes | None:
    """Download bytes gambar dari URL (cache biar cepat)."""
    try:
        import requests
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        return r.content
    except Exception:
        return None

def _id_num(x, nd=2, suffix=""):
    """Format angka Indonesia: 1234.56 -> 1.234,56"""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        s = f"{float(x):,.{nd}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        if nd == 0:
            s = s.split(",")[0]
        return s + suffix
    except Exception:
        return "-"

def _id_int(x):
    """Format integer Indonesia: 46530 -> 46.530"""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        return f"{int(x):,}".replace(",", ".")
    except Exception:
        return "-"

def _sla_short_days(seconds, nd=2):
    """Ringkas: '3,22 hari'"""
    if seconds is None or (isinstance(seconds, float) and np.isnan(seconds)):
        return "-"
    return _id_num(float(seconds) / 86400.0, nd=nd, suffix=" hari")

def _sla_long_id(seconds):
    """Detail: '3 hari 17 jam 41 menit'"""
    if seconds is None or (isinstance(seconds, float) and np.isnan(seconds)):
        return "-"
    sec = float(seconds)
    neg = sec < 0
    sec = abs(sec)
    d = int(sec // 86400)
    h = int((sec % 86400) // 3600)
    m = int((sec % 3600) // 60)
    parts = []
    if d: parts.append(f"{d} hari")
    if h: parts.append(f"{h} jam")
    if m or not parts: parts.append(f"{m} menit")
    s = " ".join(parts)
    return f"-{s}" if neg else s

def pct_change(a, b):
    if a is None or pd.isna(a) or a == 0:
        return np.nan
    return (b - a) / a * 100

def year_or_label(sel_periods, fallback):
    yrs = sorted({int(p.year) for p in sel_periods}) if sel_periods else []
    return str(yrs[0]) if len(yrs) == 1 else fallback

def build_auto_headline(totalA, totalB, meanA, meanB, p_total, d_total):
    """Headline otomatis untuk Direksi."""
    vol_dir = "naik" if d_total > 0 else ("turun" if d_total < 0 else "stabil")
    vol_part = f"Volume {vol_dir} {_id_num(abs(p_total),2,'%')}" if np.isfinite(p_total) else f"Volume {vol_dir}"

    if not (np.isfinite(meanA) and np.isfinite(meanB)):
        sla_part = "SLA: data belum lengkap"
    else:
        d = meanB - meanA
        sla_dir = "membaik" if d < 0 else ("memburuk" if d > 0 else "stabil")
        imp = (meanA - meanB) / meanA * 100 if meanA else np.nan
        sla_part = f"SLA {sla_dir} {_id_num(abs(imp),2,'%')}" if np.isfinite(imp) else f"SLA {sla_dir}"

    return f"{sla_part} • {vol_part}"

def make_exec_poster_png_v3(
    *,
    labelA, labelB,
    seriesA, seriesB,
    totalA, totalB, p_total, d_total,
    meanA, meanB,
    kpi_days, complianceB, coverageB,
    d_comp, d_cov,
    vol_month_df=None,   # columns: Bulan, seriesA, seriesB
    sla_month_df=None,   # columns: Bulan, seriesA, seriesB (hari)
    headline="",
    logo_left_bytes=None,    # Danantara (kiri atas)
    logo_right_bytes=None,   # ASDP (kanan atas)
    title="EXECUTIVE SUMMARY",
    subtitle="Analisis SLA & Transaksi",
):
    """
    POSTER FIXED LAYOUT (NO OVERLAP):
    - Header 3 baris: title/subtitle + timestamp/period
    - Logo kiri & kanan auto-fit dan tidak menimpa teks
    - Card grid rapi (4 + 4)
    - Chart grid rapi (2) dengan label bulan rotate supaya tidak bertabrakan
    """
    import matplotlib.pyplot as plt
    from PIL import Image
    import textwrap

    dpi = 200
    W, H = int(11.69 * dpi), int(8.27 * dpi)   # A4 landscape @200dpi ≈ 2338x1654
    fig = plt.figure(figsize=(W/dpi, H/dpi), dpi=dpi)
    fig.patch.set_facecolor("white")

    # =======================
    # BACKGROUND (gradient + accent)
    # =======================
    ax_bg = fig.add_axes([0, 0, 1, 1])
    ax_bg.axis("off")
    grad = np.linspace(0, 1, H).reshape(H, 1)
    top = np.array([18, 34, 84]) / 255.0        # navy
    bottom = np.array([255, 255, 255]) / 255.0  # white
    bg = bottom + (top - bottom) * (1 - grad)
    bg = np.repeat(bg, W, axis=1)
    ax_bg.imshow(bg, aspect="auto", extent=[0, 1, 0, 1])

    # Accent bars
    ax_bg.add_patch(plt.Rectangle((0.00, 0.92), 1.0, 0.08, color=(0.10,0.55,0.85,0.26), ec=(0,0,0,0)))
    ax_bg.add_patch(plt.Rectangle((0.00, 0.00), 1.0, 0.06, color=(0.00,0.70,0.55,0.18), ec=(0,0,0,0)))
    ax_bg.add_patch(plt.Circle((0.12, 0.52), 0.20, color=(1.0,0.55,0.0,0.07), ec=(0,0,0,0)))
    ax_bg.add_patch(plt.Circle((0.92, 0.46), 0.25, color=(0.00,0.70,0.55,0.10), ec=(0,0,0,0)))

    # =======================
    # LOGOS (dedicated safe zone)
    # =======================
    def _logo_ax(bytes_, x, y, w, h):
        if not bytes_:
            return
        try:
            im = Image.open(io.BytesIO(bytes_)).convert("RGBA")
            ax = fig.add_axes([x, y, w, h])
            ax.axis("off")
            ax.imshow(im)
        except Exception:
            pass

    # Left logo (Danantara) and right logo (ASDP)
    _logo_ax(logo_left_bytes,  0.02, 0.915, 0.10, 0.07)
    _logo_ax(logo_right_bytes, 0.88, 0.915, 0.10, 0.07)

    # =======================
    # HEADER TEXT (safe zone middle, no overlap with logos)
    # =======================
    axH = fig.add_axes([0.14, 0.915, 0.72, 0.07])
    axH.axis("off")
    axH.text(0.00, 0.72, title, fontsize=24, fontweight="bold", color=(1,1,1,0.96), va="center")
    axH.text(0.00, 0.22, subtitle, fontsize=10, fontweight="bold", color=(1,1,1,0.90), va="center")

    axHP = fig.add_axes([0.14, 0.875, 0.84, 0.04])
    axHP.axis("off")
    axHP.text(1.00, 0.50, datetime.now().strftime("%d %b %Y %H:%M"),
              ha="right", fontsize=8, color=(1,1,1,0.88), fontweight="bold")
    axHP.text(0.00, 0.50, f"Periode: {labelA} vs {labelB}",
              ha="left", fontsize=10, color=(1,1,1,0.92), fontweight="bold")

    # =======================
    # HEADLINE STRIP (wrap to avoid overflow)
    # =======================
    axHL = fig.add_axes([0.03, 0.83, 0.94, 0.055]); axHL.axis("off")
    axHL.add_patch(plt.Rectangle((0,0),1,1, facecolor=(1,1,1,0.86), edgecolor=(0,0,0,0.10)))
    htxt = headline if headline else "-"
    htxt = "\n".join(textwrap.wrap(htxt, width=70))
    axHL.text(0.02, 0.50, htxt, va="center", fontsize=14, fontweight="bold", color=(0.05,0.10,0.20,0.98))

    # =======================
    # CARD HELPER (fixed internal layout)
    # =======================
    def card(axpos, title, value, sub, badge=None, good=True):
        ax = fig.add_axes(axpos); ax.axis("off")
        ax.add_patch(plt.Rectangle((0,0),1,1, facecolor=(1,1,1,0.94), edgecolor=(0,0,0,0.13), linewidth=1.0))
        ax.text(0.05, 0.80, title, fontsize=8, fontweight="bold", color=(0.08,0.12,0.20,0.92))
        ax.text(0.05, 0.42, value, fontsize=12, fontweight="bold", color=(0.02,0.08,0.16,0.98))
        ax.text(0.05, 0.14, sub, fontsize=8, color=(0.08,0.12,0.20,0.72), fontweight="bold")

        if badge:
            fc = (0.05, 0.65, 0.50, 0.18) if good else (0.85, 0.20, 0.20, 0.16)
            tc = (0.02, 0.45, 0.34, 0.95) if good else (0.55, 0.10, 0.10, 0.95)
            # badge always top-right inside card
            ax.add_patch(plt.Rectangle((0.67, 0.70), 0.30, 0.22, facecolor=fc, edgecolor=(0,0,0,0.10)))
            ax.text(0.82, 0.81, badge, ha="center", va="center", fontsize=8, fontweight="bold", color=tc)

    # =======================
    # KPI VALUES
    # =======================
    vol_badge = f"{_id_int(d_total)} ({_id_num(p_total,2,'%')})" if np.isfinite(p_total) else _id_int(d_total)
    d_sla = (meanB - meanA) if (np.isfinite(meanA) and np.isfinite(meanB)) else np.nan
    d_sla_badge = (("−" if d_sla < 0 else "+") + _sla_short_days(abs(d_sla),2)) if np.isfinite(d_sla) else "-"
    good_sla = True if (not np.isfinite(d_sla)) else (d_sla < 0)

    comp_val = _id_num(complianceB,2,"%") if np.isfinite(complianceB) else "-"
    cov_val  = _id_num(coverageB,2,"%") if np.isfinite(coverageB) else "-"
    comp_badge = _id_num(d_comp,2," poin") if np.isfinite(d_comp) else "-"
    cov_badge  = _id_num(d_cov,2," poin") if np.isfinite(d_cov) else "-"

    sla_word = "membaik" if (np.isfinite(d_sla) and d_sla < 0) else ("memburuk" if (np.isfinite(d_sla) and d_sla > 0) else "stabil")

    # =======================
    # CARD GRID POSITIONS (NO OVERLAP)
    # =======================
    # Row 1 (Ringkasan Utama)
    y1 = 0.69
    h1 = 0.12
    w = 0.225
    gap = 0.015
    xs = [0.03, 0.03+w+gap, 0.03+2*(w+gap), 0.03+3*(w+gap)]
    card([xs[0], y1, w, h1], f"Total Transaksi ({seriesA})", _id_int(totalA), "Baseline")
    card([xs[1], y1, w, h1], f"Total Transaksi ({seriesB})", _id_int(totalB), "Perubahan vs A", vol_badge, good=(d_total>=0))
    card([xs[2], y1, w, h1], f"Avg SLA ({seriesA})", _sla_short_days(meanA,2), _sla_long_id(meanA))
    card([xs[3], y1, w, h1], f"Avg SLA ({seriesB})", _sla_short_days(meanB,2), _sla_long_id(meanB), d_sla_badge, good=good_sla)

    # Executive Score label (separate line)
    axES = fig.add_axes([0.03, 0.63, 0.94, 0.05]); axES.axis("off")
    axES.text(0.00, 0.70, "Executive Score", fontsize=12, fontweight="bold", color=(0.02,0.08,0.16,0.95))
    axES.text(0.00, 0.35, f"Target KPI SLA: {_id_num(kpi_days,2,' hari')}", fontsize=10, color=(0.02,0.08,0.16,0.70), fontweight="bold")

    # Row 2 (Executive Score cards)
    y2 = 0.52
    h2 = 0.12
    card([xs[0], y2, w, h2], "Growth Volume", _id_num(p_total,2,"%") if np.isfinite(p_total) else "-", "Δ transaksi vs A", f"{_id_int(d_total)} trx", good=(d_total>=0))
    card([xs[1], y2, w, h2], "Perubahan SLA", sla_word, "Ringkas (hari)", d_sla_badge, good=good_sla)
    card([xs[2], y2, w, h2], f"KPI Compliance ≤ {_id_num(kpi_days,2,' hari')}", comp_val, "Δ poin vs A", comp_badge, good=(d_comp>=0 if np.isfinite(d_comp) else True))
    card([xs[3], y2, w, h2], "Coverage SLA", cov_val, "Kualitas data SLA", cov_badge, good=(d_cov>=0 if np.isfinite(d_cov) else True))

    # =======================
    # CHARTS (bigger bottom margin, rotated labels)
    # =======================
    # Volume chart
    axV = fig.add_axes([0.05, 0.10, 0.44, 0.36])
    axV.set_title("Tren Volume (bulan)", fontsize=16, fontweight="bold", loc="left", color=(0.02,0.08,0.16,0.95))
    if isinstance(vol_month_df, pd.DataFrame) and "Bulan" in vol_month_df.columns and seriesA in vol_month_df.columns and seriesB in vol_month_df.columns:
        x = list(range(len(vol_month_df["Bulan"])))
        axV.plot(x, vol_month_df[seriesA].values, marker="o", linewidth=2.8, label=str(seriesA))
        axV.plot(x, vol_month_df[seriesB].values, marker="o", linewidth=2.8, label=str(seriesB))
        axV.set_xticks(x)
        axV.set_xticklabels(vol_month_df["Bulan"].tolist(), fontsize=9, rotation=35, ha="right")
        axV.grid(True, alpha=0.22)
        axV.legend(frameon=True, fontsize=11, loc="upper left")
    else:
        axV.text(0.5, 0.5, "Data tren volume tidak tersedia", ha="center", va="center", alpha=0.7)
        axV.axis("off")

    # SLA chart
    axT = fig.add_axes([0.53, 0.10, 0.44, 0.36])
    axT.set_title("Tren SLA (hari, bulan)", fontsize=16, fontweight="bold", loc="left", color=(0.02,0.08,0.16,0.95))
    if isinstance(sla_month_df, pd.DataFrame) and "Bulan" in sla_month_df.columns and seriesA in sla_month_df.columns and seriesB in sla_month_df.columns:
        x = list(range(len(sla_month_df["Bulan"])))
        axT.plot(x, sla_month_df[seriesA].values, marker="o", linewidth=2.8, label=str(seriesA))
        axT.plot(x, sla_month_df[seriesB].values, marker="o", linewidth=2.8, label=str(seriesB))
        axT.set_xticks(x)
        axT.set_xticklabels(sla_month_df["Bulan"].tolist(), fontsize=10, rotation=25, ha="right")
        axT.grid(True, alpha=0.22)
        axT.legend(frameon=True, fontsize=11, loc="upper right")
    else:
        axT.text(0.5, 0.5, "Data tren SLA tidak tersedia", ha="center", va="center", alpha=0.7)
        axT.axis("off")

    # =======================
    # FOOTER (safe zone)
    # =======================
    axF = fig.add_axes([0.03, 0.02, 0.94, 0.05]); axF.axis("off")
    axF.text(0.00, 0.50, "",
             fontsize=8, alpha=0.80, color=(0.02,0.08,0.16,0.80), fontweight="bold")
    axF.text(1.00, 0.20, "Sumber: Tab Analisis (hasil filter aktif)",
             fontsize=10, alpha=0.80, ha="right", color=(0.02,0.08,0.16,0.80), fontweight="bold")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.10)
    plt.close(fig)
    return buf.getvalue()

def make_exec_poster_pdf_from_png(png_bytes):
    """Convert PNG poster ke 1 halaman PDF (A4 landscape)."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    W, H = landscape(A4)
    margin = 18
    img = ImageReader(io.BytesIO(png_bytes))
    c.drawImage(img, margin, margin, width=W-2*margin, height=H-2*margin, preserveAspectRatio=True, anchor="c")
    c.showPage()
    c.save()
    return buf.getvalue()


# ============================================================
# TAB ANALISIS — FULL (tempel di: with tab_analisis:)
# ============================================================

with tab_analisis:
    import plotly.express as px

    st.markdown("## 📊 Analisis Data — Executive Dashboard")
    st.caption("Bandingkan **A vs B** (Tahun vs Tahun, Bulan vs Bulan, atau Rentang vs Rentang). Angka di sini mengikuti filter tab_analisis.")

    # Guard
    if "df_raw" not in locals() or df_raw is None or df_raw.empty:
        st.warning("Data kosong.")
        st.stop()
    if "periode_col" not in locals() or periode_col is None or periode_col not in df_raw.columns:
        st.error("Kolom periode (periode_col) tidak ditemukan.")
        st.stop()

    # Toggle filter scope
    use_sidebar_filter = st.toggle("Gunakan filter sidebar (df_filtered)", value=True, key="ana_usefilter_all_v3")
    df_base = df_filtered.copy() if (use_sidebar_filter and "df_filtered" in locals()) else df_raw.copy()
    if df_base is None or df_base.empty:
        st.warning("Data kosong (setelah filter).")
        st.stop()

    # -------------------------
    # Filter tambahan: Jenis Transaksi (multi-select) - ALL / 1 / banyak
    # -------------------------
    trx_col = None
    for _c in df_base.columns:
        _cu = re.sub(r"\s+", " ", str(_c).strip().upper())
        if _cu in {"JENIS TRANSAKSI", "JENIS_TRANSAKSI", "TRANSAKSI", "NAMA TRANSAKSI", "TYPE TRANSAKSI", "TIPE TRANSAKSI"}:
            trx_col = _c
            break
        if ("JENIS" in _cu and "TRANSAK" in _cu) or (_cu.endswith("TRANSAKSI")):
            trx_col = _c
            break

    if trx_col:
        trx_options = sorted([x for x in df_base[trx_col].dropna().astype(str).unique().tolist() if str(x).strip() != ""])
        trx_pick = st.multiselect(
            "Filter transaksi (pilih 1/lebih, atau ALL)",
            options=["ALL"] + trx_options,
            default=["ALL"],
            key="ana_trx_filter_v1"
        )
        if trx_pick and "ALL" not in trx_pick:
            df_base = df_base[df_base[trx_col].astype(str).isin(trx_pick)].copy()

    if df_base.empty:
        st.warning("Data kosong setelah filter transaksi.")
        st.stop()

    # Month names
    month_id = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    id_month = {v.lower(): k for k, v in month_id.items()}

    # CSS cards (kontras)
    st.markdown("""
<style>
.kpi-wrap{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:10px}
.kpi-card{
  border:1px solid rgba(49,51,63,.15);
  border-radius:16px;
  padding:14px 14px 12px;
  background:white;
  box-shadow:0 10px 22px rgba(0,0,0,.08);
}
.kpi-title{font-size:13px;color:rgba(15,23,42,.78);margin:0 0 6px 0;font-weight:700;text-align:center}
.kpi-value{font-size:38px;font-weight:900;line-height:1.1;margin:0;color:rgb(15,23,42);text-align:center}
.kpi-sub{font-size:12px;color:rgba(15,23,42,.70);margin-top:6px;font-weight:700;text-align:center}
.badge{
  display:inline-block;padding:5px 11px;border-radius:999px;
  font-size:12px;font-weight:900;margin-top:10px
}
.badge-up{background:rgba(16,185,129,.15);color:rgb(4,120,87)}
.badge-down{background:rgba(239,68,68,.15);color:rgb(153,27,27)}
.badge-flat{background:rgba(100,116,139,.16);color:rgb(30,41,59)}
.hero{
  border-radius:16px;padding:14px 16px;
  background:rgba(34,197,94,.10);
  border:1px solid rgba(34,197,94,.28);
  margin-top:12px;
  color:rgb(15,23,42);
  font-weight:750;
}
.hero b{font-weight:950}
.small-cap{color:rgba(15,23,42,.72);font-weight:750}
@media(max-width:1100px){
  .kpi-wrap{grid-template-columns:1fr}
}
</style>
""", unsafe_allow_html=True)

    def badge_class(delta):
        try:
            if delta is None or (isinstance(delta, float) and np.isnan(delta)):
                return "badge-flat"
            if delta > 0:
                return "badge-up"
            if delta < 0:
                return "badge-down"
            return "badge-flat"
        except Exception:
            return "badge-flat"

    def safe_pct(a, b):
        if a is None or pd.isna(a) or a == 0:
            return np.nan
        return (b - a) / a * 100

    # -------------------------
    # Periode parsing -> PERIOD_M (Period[M])
    # -------------------------
    def to_period_month(x):
        if pd.isna(x):
            return pd.NaT
        if isinstance(x, pd.Period):
            return x.asfreq("M")
        if isinstance(x, (pd.Timestamp,)):
            return x.to_period("M")
        s = str(x).strip()
        if not s:
            return pd.NaT

        dt = pd.to_datetime(s, errors="coerce")
        if pd.notna(dt):
            return dt.to_period("M")

        m = re.search(r"(\d{4})[-/](\d{1,2})", s)
        if m:
            y = int(m.group(1)); mo = int(m.group(2))
            if 1 <= mo <= 12:
                return pd.Period(f"{y}-{mo:02d}", freq="M")

        s_low = s.lower()
        for nama, mo in id_month.items():
            if nama in s_low:
                y_m = re.search(r"(\d{4})", s_low)
                if y_m:
                    y = int(y_m.group(1))
                    return pd.Period(f"{y}-{mo:02d}", freq="M")
        return pd.NaT

    if "PERIOD_M" not in df_base.columns:
        df_base["PERIOD_M"] = df_base[periode_col].apply(to_period_month)

    df_base = df_base.dropna(subset=["PERIOD_M"]).copy()
    if df_base.empty:
        st.warning("Data periode kosong.")
        st.stop()

    periods = sorted(df_base["PERIOD_M"].unique().tolist())
    years = sorted({int(p.year) for p in periods})

    def period_label(p: pd.Period):
        return f"{month_id[int(p.month)]} {int(p.year)}"

    period_labels = [period_label(p) for p in periods]
    label_to_period = {period_label(p): p for p in periods}

    # -------------------------
    # Mode Perbandingan
    # -------------------------
    st.markdown("### ⚙️ Mode Perbandingan")
    mode = st.radio(
        "Pilih mode",
        ["Tahun vs Tahun", "Bulan vs Bulan (tahun bebas)", "Rentang (A) vs Rentang (B)"],
        horizontal=True,
        key="ana_mode_all_v5"
    )

    colA, colB, colS = st.columns([1, 1, 1])
    with colS:
        st.markdown("**Metrik SLA**")

        # pilih kolom SLA (pakai daftar helper kalau ada)
        sla_candidates = []
        if "available_sla_cols" in globals() and isinstance(available_sla_cols, list):
            sla_candidates += [c for c in available_sla_cols if c in df_base.columns]

        # fallback kolom populer
        for c in ["KEUANGAN", "TOTAL WAKTU", "TOTAL_WAKTU", "SLA", "SLA (DETIK)", "SLA_DETIK", "SLA_HARI", "SLA HARI"]:
            if c in df_base.columns and c not in sla_candidates:
                sla_candidates.append(c)

        sla_options = [c for c in sla_candidates if c in df_base.columns]
        if sla_options:
            default_idx = 0
            for prefer in ["KEUANGAN", "TOTAL WAKTU", "TOTAL_WAKTU", "SLA", "SLA (DETIK)", "SLA_DETIK"]:
                if prefer in sla_options:
                    default_idx = sla_options.index(prefer)
                    break
            sla_pick = st.selectbox("Kolom SLA", sla_options, index=default_idx, key="ana_sla_pick_v5")
        else:
            sla_pick = None
            st.info("Kolom SLA tidak terdeteksi (SLA card & chart akan mengikuti kondisi data).")

    labelA = labelB = ""
    selA = []
    selB = []

    if mode == "Tahun vs Tahun":
        with colA:
            yearA = st.selectbox("Periode A — Tahun", years, index=0, key="ana_yearA_v5")
        with colB:
            yearB = st.selectbox("Periode B — Tahun", years, index=min(1, len(years) - 1), key="ana_yearB_v5")

        selA = [p for p in periods if int(p.year) == int(yearA)]
        selB = [p for p in periods if int(p.year) == int(yearB)]
        labelA, labelB = f"Tahun {yearA}", f"Tahun {yearB}"

    elif mode == "Bulan vs Bulan (tahun bebas)":
        with colA:
            mA = st.selectbox("Periode A — Bulan", period_labels, index=0, key="ana_monthA_v5")
        with colB:
            mB = st.selectbox("Periode B — Bulan", period_labels, index=min(1, len(period_labels) - 1), key="ana_monthB_v5")

        selA = [label_to_period[mA]]
        selB = [label_to_period[mB]]
        labelA, labelB = mA, mB

    else:  # range
        with colA:
            startA = st.selectbox("Periode A — Mulai", period_labels, index=0, key="ana_startA_v5")
            endA   = st.selectbox("Periode A — Sampai", period_labels, index=len(period_labels)-1, key="ana_endA_v5")
        with colB:
            startB = st.selectbox("Periode B — Mulai", period_labels, index=0, key="ana_startB_v5")
            endB   = st.selectbox("Periode B — Sampai", period_labels, index=len(period_labels)-1, key="ana_endB_v5")

        pA0 = label_to_period[startA]; pA1 = label_to_period[endA]
        pB0 = label_to_period[startB]; pB1 = label_to_period[endB]

        if pA0 > pA1: pA0, pA1 = pA1, pA0
        if pB0 > pB1: pB0, pB1 = pB1, pB0

        selA = [p for p in periods if pA0 <= p <= pA1]
        selB = [p for p in periods if pB0 <= p <= pB1]
        labelA = f"{period_label(selA[0])} – {period_label(selA[-1])}" if selA else "Periode A"
        labelB = f"{period_label(selB[0])} – {period_label(selB[-1])}" if selB else "Periode B"

    if not selA or not selB:
        st.warning("Pilihan periode A/B kosong. Silakan ubah pilihan.")
        st.stop()

    dfA = df_base[df_base["PERIOD_M"].isin(selA)].copy()
    dfB = df_base[df_base["PERIOD_M"].isin(selB)].copy()

    # -------------------------
    # KPI Target (ambil dari Tab Overview)
    # -------------------------
    try:
        kpi_days = load_kpi()
    except Exception:
        kpi_days = None
    kpi_sec = float(kpi_days) * 86400.0 if (kpi_days is not None and not pd.isna(kpi_days)) else None

    # -------------------------
    # SLA seconds: FIXED parsing (numeric dulu, baru parse_sla)
    # -------------------------
    has_sla = bool(sla_pick) and (sla_pick in df_base.columns)

    def ensure_sla_seconds_local(df):
        out_col = "__SLA_SECONDS_ANALYSIS__"
        if out_col in df.columns:
            return df, out_col

        if (not has_sla) or (sla_pick not in df.columns):
            df[out_col] = np.nan
            return df, out_col

        s = df[sla_pick]

        # 1) numeric langsung (kalau SLA sudah detik)
        num = pd.to_numeric(s, errors="coerce")

        # 2) non-numeric -> parse_sla (format teks)
        if "parse_sla" in globals():
            def _parse_if_needed(v, n):
                if pd.notna(n):
                    return float(n)

                if v is None:
                    return np.nan
                vs = str(v).strip().lower()
                if vs in {"", "nan", "none", "-", "null"}:
                    return np.nan

                try:
                    sec = parse_sla(v)
                except Exception:
                    sec = np.nan

                # parse gagal -> NaN (hindari garis 0)
                try:
                    if (sec == 0 or sec == 0.0) and vs not in {"0", "0.0"}:
                        return np.nan
                except Exception:
                    pass

                return float(sec) if pd.notna(sec) else np.nan

            df[out_col] = [_parse_if_needed(v, n) for v, n in zip(s.tolist(), num.tolist())]
        else:
            df[out_col] = num

        return df, out_col

    meanA = meanB = np.nan
    coverageA = coverageB = np.nan
    complianceA = complianceB = np.nan

    if has_sla:
        dfA, sla_sec_col = ensure_sla_seconds_local(dfA)
        dfB, _ = ensure_sla_seconds_local(dfB)

        sA_all = dfA[sla_sec_col]
        sB_all = dfB[sla_sec_col]
        validA = sA_all.dropna()
        validB = sB_all.dropna()

        meanA = float(validA.mean()) if len(validA) else np.nan
        meanB = float(validB.mean()) if len(validB) else np.nan

        coverageA = float(sA_all.notna().mean() * 100) if len(dfA) else np.nan
        coverageB = float(sB_all.notna().mean() * 100) if len(dfB) else np.nan

        if kpi_sec is not None:
            complianceA = float((validA <= kpi_sec).mean() * 100) if len(validA) else np.nan
            complianceB = float((validB <= kpi_sec).mean() * 100) if len(validB) else np.nan

    d_cov = coverageB - coverageA if (np.isfinite(coverageA) and np.isfinite(coverageB)) else np.nan

    # -------------------------
    # KPI Cards (Total Nilai dihapus)
    # -------------------------
    totalA, totalB = len(dfA), len(dfB)
    d_total = totalB - totalA
    p_total = safe_pct(totalA, totalB)

    d_sla = meanB - meanA if (np.isfinite(meanA) and np.isfinite(meanB)) else np.nan
    p_sla = safe_pct(meanA, meanB) if (np.isfinite(meanA) and np.isfinite(meanB)) else np.nan

    d_comp = complianceB - complianceA if (np.isfinite(complianceA) and np.isfinite(complianceB)) else np.nan
    p_comp = safe_pct(complianceA, complianceB) if (np.isfinite(complianceA) and np.isfinite(complianceB)) else np.nan

    badge_vol = f"{_id_int(d_total)} ({_id_num(p_total,2,'%')})" if np.isfinite(p_total) else _id_int(d_total)
    badge_sla = (("−" if d_sla < 0 else "+") + _sla_short_days(abs(d_sla), 2) + (f" ({p_sla:+.1f}%)" if np.isfinite(p_sla) else "")) if np.isfinite(d_sla) else "-"
    badge_comp = (f"{d_comp:+.1f} pts" + (f" ({p_comp:+.1f}%)" if np.isfinite(p_comp) else "")) if np.isfinite(d_comp) else "-"

    trx_sub = f"{labelA}: {_id_int(totalA)} • {labelB}: {_id_int(totalB)}"
    if np.isfinite(p_total):
        trx_sub += f" • Δ: {badge_vol}"

    if has_sla and np.isfinite(meanA) and np.isfinite(meanB):
        sla_sub = (
            f"{labelA}: {_sla_short_days(meanA,2)} | {seconds_to_sla_format(meanA)}<br/>"
            f"{labelB}: {_sla_short_days(meanB,2)} | {seconds_to_sla_format(meanB)}"
        )
    else:
        sla_sub = "Data SLA tidak tersedia / belum terbaca (cek pilihan kolom SLA)."

    if kpi_days is not None and has_sla and np.isfinite(complianceB):
        comp_sub = f"Target KPI {float(kpi_days):.2f} hari • {labelA}: {complianceA:.1f}% • {labelB}: {complianceB:.1f}%"
    elif kpi_days is not None:
        comp_sub = f"Target KPI {float(kpi_days):.2f} hari"
    else:
        comp_sub = "Target KPI belum diatur di Tab Overview."

    html_cards = f"""
    <div class="kpi-wrap">
      <div class="kpi-card">
        <p class="kpi-title">Jumlah Transaksi (A vs B)</p>
        <p class="kpi-value">{_id_int(totalB)}</p>
        <span class="badge {badge_class(d_total)}">{badge_vol}</span>
        <div class="kpi-sub">{trx_sub}</div>
      </div>

      <div class="kpi-card">
        <p class="kpi-title">Rata-rata SLA (A vs B)</p>
        <p class="kpi-value">{_sla_short_days(meanB,2) if (has_sla and np.isfinite(meanB)) else "-"}</p>
        <span class="badge {badge_class(-1 if (np.isfinite(d_sla) and d_sla<0) else (1 if (np.isfinite(d_sla) and d_sla>0) else 0))}">{badge_sla}</span>
        <div class="kpi-sub">{sla_sub}</div>
      </div>

      <div class="kpi-card">
        <p class="kpi-title">Success Rate vs Target KPI</p>
        <p class="kpi-value">{(f"{complianceB:.1f}%") if (has_sla and np.isfinite(complianceB)) else "-"}</p>
        <span class="badge {badge_class(d_comp)}">{badge_comp}</span>
        <div class="kpi-sub">{comp_sub}</div>
      </div>
    </div>
    """
    st.markdown(html_cards, unsafe_allow_html=True)

    # Highlight ringkas
    vol_dir = "naik" if d_total > 0 else ("turun" if d_total < 0 else "stabil")
    spot = f"• Volume transaksi <b>{vol_dir}</b>: {_id_int(totalA)} → {_id_int(totalB)} (Δ {badge_vol})."
    if has_sla and np.isfinite(d_sla):
        sla_dir = "membaik" if d_sla < 0 else ("memburuk" if d_sla > 0 else "stabil")
        spot += f" • SLA <b>{sla_dir}</b>: <b>{_sla_short_days(meanA,2)}</b> → <b>{_sla_short_days(meanB,2)}</b> (Δ {badge_sla})."
    if kpi_days is not None and has_sla and np.isfinite(complianceB):
        spot += f" • Dengan target KPI <b>{float(kpi_days):.2f} hari</b>, {labelB} memenuhi target sebesar <b>{complianceB:.1f}%</b>."
    st.markdown(f"<div class='hero'>{spot}</div>", unsafe_allow_html=True)

    # (opsional) debug SLA
    with st.expander("🧪 Debug SLA (cek pembacaan detik)", expanded=False):
        st.write("Kolom SLA dipilih:", sla_pick)
        if "__SLA_SECONDS_ANALYSIS__" in dfA.columns:
            st.write("Sample A (seconds):", dfA["__SLA_SECONDS_ANALYSIS__"].dropna().head(10).tolist())
        if "__SLA_SECONDS_ANALYSIS__" in dfB.columns:
            st.write("Sample B (seconds):", dfB["__SLA_SECONDS_ANALYSIS__"].dropna().head(10).tolist())

    # -------------------------
    # Diagram 1 & 2 (per bulan, sumbu X Jan–Des, warna = periode A vs B)
    # -------------------------
    st.markdown("### 📈 Grafik Perbandingan (per Bulan)")

    def year_or_label(sel_periods, fallback_tag):
        ys = sorted({int(p.year) for p in sel_periods})
        if len(ys) == 1:
            return f"Tahun {ys[0]}"
        return fallback_tag

    seriesA = year_or_label(selA, "A")
    seriesB = year_or_label(selB, "B")

    month_order = [month_id[m] for m in range(1, 13)]

    # Diagram 1: jumlah transaksi per bulan
    def trx_by_monthnum(df):
        if df.empty:
            return {}
        g = df.groupby("PERIOD_M").size().reset_index(name="trx")
        g["m"] = g["PERIOD_M"].apply(lambda p: int(p.month))
        return g.groupby("m")["trx"].sum().to_dict()

    A_trx = trx_by_monthnum(dfA)
    B_trx = trx_by_monthnum(dfB)

    vol_month = pd.DataFrame({
        "Bulan": month_order,
        seriesA: [float(A_trx.get(m, 0)) for m in range(1, 13)],
        seriesB: [float(B_trx.get(m, 0)) for m in range(1, 13)],
    })

    vol_long = vol_month.melt(id_vars=["Bulan"], var_name="Periode", value_name="Jumlah Transaksi")
    fig_trx = px.bar(
        vol_long,
        x="Bulan",
        y="Jumlah Transaksi",
        color="Periode",
        barmode="group",
        category_orders={"Bulan": month_order},
        title=f"Diagram 1 — Jumlah Transaksi per Bulan ({seriesA} vs {seriesB})"
    )
    fig_trx.update_layout(xaxis_title=None, yaxis_title="Jumlah Transaksi", legend_title=None, height=430)
    st.plotly_chart(fig_trx, use_container_width=True)

    # Diagram 2: rata-rata SLA per bulan (hari)
    sla_month = pd.DataFrame({"Bulan": month_order})
    if has_sla and "__SLA_SECONDS_ANALYSIS__" in dfA.columns and "__SLA_SECONDS_ANALYSIS__" in dfB.columns:
        def mean_sla_days_by_month(df, sec_col):
            if df.empty:
                return {}
            d = df.copy()
            d = d[d[sec_col].notna()].copy()
            if d.empty:
                return {}
            g = d.groupby("PERIOD_M")[sec_col].mean().reset_index(name="sec")
            g["m"] = g["PERIOD_M"].apply(lambda p: int(p.month))
            g["days"] = g["sec"] / 86400.0
            return g.groupby("m")["days"].mean().to_dict()

        A_days = mean_sla_days_by_month(dfA, "__SLA_SECONDS_ANALYSIS__")
        B_days = mean_sla_days_by_month(dfB, "__SLA_SECONDS_ANALYSIS__")

        sla_month[seriesA] = [float(A_days.get(m, np.nan)) for m in range(1, 13)]
        sla_month[seriesB] = [float(B_days.get(m, np.nan)) for m in range(1, 13)]

        sla_long = sla_month.melt(id_vars=["Bulan"], var_name="Periode", value_name="Rata-rata SLA (hari)")
        fig_sla = px.line(
            sla_long,
            x="Bulan",
            y="Rata-rata SLA (hari)",
            color="Periode",
            markers=True,
            category_orders={"Bulan": month_order},
            title=f"Diagram 2 — Rata-rata SLA per Bulan ({seriesA} vs {seriesB})"
        )
        fig_sla.update_layout(xaxis_title=None, yaxis_title="Rata-rata SLA (hari)", legend_title=None, height=430)
        st.plotly_chart(fig_sla, use_container_width=True)
    else:
        st.info("Diagram 2 (SLA) tidak ditampilkan karena kolom SLA belum tersedia/terdeteksi atau nilainya tidak terbaca.")
        sla_month[seriesA] = [np.nan] * 12
        sla_month[seriesB] = [np.nan] * 12

    # ============================================================
    # BLOK POSTER EXECUTIVE SUMMARY — FIXED LAYOUT (NO OVERLAP)
    # ============================================================
    st.markdown("---")
    st.markdown("### 🖼️ Poster Executive Summary (Analisis)")

    # (opsional) animasi di UI saja
    gif_url = "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"
    gif_bytes = _fetch_image_bytes(gif_url)
    if gif_bytes:
        st.image(gif_bytes, width=220)

    # Logo (kiri/kanan)
    logo_left_bytes = _fetch_image_bytes(LOGO_LEFT_URL) if "LOGO_LEFT_URL" in globals() else None
    logo_right_bytes = _fetch_image_bytes(LOGO_RIGHT_URL) if "LOGO_RIGHT_URL" in globals() else None

    c1, c2 = st.columns([1, 1])
    with c1:
        poster_title = st.text_input("Judul Poster", value="EXECUTIVE SUMMARY", key="ana_poster_title_v3")
    with c2:
        poster_subtitle = st.text_input("Sub Judul", value="Analisis SLA & Transaksi", key="ana_poster_subtitle_v3")

    headline = build_auto_headline(totalA, totalB, meanA, meanB, p_total, d_total) if "build_auto_headline" in globals() else ""

    @st.cache_data(show_spinner=False)
    def _gen_exec_poster_cached(payload: dict):
        png = make_exec_poster_png_v3(**payload)
        pdf = make_exec_poster_pdf_from_png(png)
        return png, pdf

    payload = dict(
        labelA=labelA, labelB=labelB,
        seriesA=seriesA, seriesB=seriesB,
        totalA=totalA, totalB=totalB, p_total=p_total, d_total=d_total,
        meanA=meanA, meanB=meanB,
        kpi_days=kpi_days, complianceB=complianceB, coverageB=coverageB,
        d_comp=d_comp, d_cov=d_cov,
        vol_month_df=vol_month,
        sla_month_df=sla_month,
        headline=headline,
        logo_left_bytes=logo_left_bytes,
        logo_right_bytes=logo_right_bytes,
        title=poster_title,
        subtitle=poster_subtitle,
    )

    png_bytes, pdf_bytes = _gen_exec_poster_cached(payload)

    st.image(png_bytes, caption="Preview Poster Executive Summary (layout sudah rapih & tidak overlap)", use_container_width=True)

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "⬇️ Download Poster PNG (WA)",
            data=png_bytes,
            file_name="Poster_Executive_Summary_Analisis.png",
            mime="image/png",
            use_container_width=True
        )
    with d2:
        st.download_button(
            "⬇️ Download Poster PDF (Email/Arsip)",
            data=pdf_bytes,
            file_name="Poster_Executive_Summary_Analisis.pdf",
            mime="application/pdf",
            use_container_width=True
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

# ====================== LOGO ASSET PDF (LOCAL) ======================
# Logo PDF dibaca langsung dari folder yang sama dengan app.py.
# Resolver juga memeriksa current working directory dan nama file secara
# case-insensitive agar tetap stabil saat dijalankan lokal maupun Streamlit Cloud.
try:
    PDF_APP_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception:
    PDF_APP_DIR = os.getcwd()

PDF_LOGO_DANANTARA_NAME = "danantara.png"
PDF_LOGO_ASDP_NAME = "asdp_logo.png"


def _resolve_pdf_asset(filename):
    """Cari file aset PDF secara aman dan kembalikan absolute path-nya."""
    search_dirs = []
    for directory in (PDF_APP_DIR, os.getcwd()):
        directory = os.path.abspath(directory)
        if directory not in search_dirs:
            search_dirs.append(directory)

    # Pencarian nama persis terlebih dahulu.
    for directory in search_dirs:
        candidate = os.path.join(directory, filename)
        if os.path.isfile(candidate):
            return candidate

    # Fallback case-insensitive untuk Linux/Streamlit Cloud.
    target_lower = filename.lower()
    for directory in search_dirs:
        try:
            for entry in os.listdir(directory):
                if entry.lower() == target_lower:
                    candidate = os.path.join(directory, entry)
                    if os.path.isfile(candidate):
                        return candidate
        except OSError:
            continue

    searched = ", ".join(search_dirs)
    raise FileNotFoundError(
        f"Aset PDF '{filename}' tidak ditemukan. Folder yang diperiksa: {searched}"
    )


def _validate_pdf_logo_assets():
    """Pastikan kedua logo tersedia sebelum laporan PDF dibuat."""
    return {
        "danantara": _resolve_pdf_asset(PDF_LOGO_DANANTARA_NAME),
        "asdp": _resolve_pdf_asset(PDF_LOGO_ASDP_NAME),
    }

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
def _img_reader(image_source):
    """Buat ImageReader ReportLab dari local path/bytes tanpa menelan error."""
    if isinstance(image_source, (bytes, bytearray)):
        return ImageReader(io.BytesIO(image_source))
    return ImageReader(str(image_source))


def _draw_pdf_logo(canvas, image_path, x, y, width, height, label="Logo"):
    """Gambar logo dengan aspect ratio terjaga dan error yang informatif."""
    try:
        canvas.drawImage(
            _img_reader(image_path),
            x,
            y,
            width=width,
            height=height,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
        return True
    except Exception as exc:
        print(
            f"[PDF LOGO ERROR] {label} gagal dimuat dari '{image_path}': "
            f"{type(exc).__name__}: {exc}"
        )
        return False

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
    """Logo cover PDF: Danantara kiri, ASDP kanan, dan ASDP utama di tengah."""
    canvas.saveState()
    pw, ph = landscape(A4)

    try:
        logos = _validate_pdf_logo_assets()

        _draw_pdf_logo(
            canvas,
            logos["danantara"],
            1.5 * cm,
            ph - 3.45 * cm,
            4.8 * cm,
            1.55 * cm,
            "Danantara - Cover",
        )

        _draw_pdf_logo(
            canvas,
            logos["asdp"],
            pw - 5.0 * cm,
            ph - 3.65 * cm,
            3.2 * cm,
            2.15 * cm,
            "ASDP - Cover Header",
        )

        _draw_pdf_logo(
            canvas,
            logos["asdp"],
            (pw - 5.4 * cm) / 2,
            ph - 9.35 * cm,
            5.4 * cm,
            4.0 * cm,
            "ASDP - Cover Center",
        )
    finally:
        canvas.restoreState()


def _later_pages(canvas, doc):
    """Logo header dan nomor halaman untuk seluruh halaman setelah cover."""
    canvas.saveState()
    pw, ph = landscape(A4)

    try:
        logos = _validate_pdf_logo_assets()

        _draw_pdf_logo(
            canvas,
            logos["danantara"],
            1.5 * cm,
            ph - 3.45 * cm,
            4.8 * cm,
            1.55 * cm,
            "Danantara - Header",
        )

        _draw_pdf_logo(
            canvas,
            logos["asdp"],
            pw - 5.0 * cm,
            ph - 3.65 * cm,
            3.2 * cm,
            2.15 * cm,
            "ASDP - Header",
        )

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawRightString(
            pw - 1.6 * cm,
            1.05 * cm,
            f"Halaman {doc.page}",
        )
    finally:
        canvas.restoreState()

# ====================== MAIN FUNCTION ======================
def generate_pdf_report_v6(df_ord, selected_periode, periode_col, available_sla_cols, proses_cols, kpi_target_days=None):
    # Fail-fast dengan pesan jelas jika file logo belum ikut ter-deploy.
    _validate_pdf_logo_assets()

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

# ==========================================================
#  SELA v10 — Smooth Lip-Sync Smart Period Analyst
#  - Avatar wanita natural (ringan, CSS/SVG)
#  - Voice input via Web Speech API
#  - Voice output via Speech Synthesis
#  - Jawaban natural berbasis data aktif dashboard
# ==========================================================
import streamlit.components.v1 as components
import json
import pandas as pd
import numpy as np
import re


def _format_num_id(val):
    try:
        v = float(val)
        if abs(v) >= 1000:
            return f"{v:,.0f}".replace(",", ".")
        if float(v).is_integer():
            return str(int(v))
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(val)


def _format_days_text(days):
    try:
        d = float(days)
    except Exception:
        return "0 hari"
    if d < 0:
        d = 0
    total_seconds = int(round(d * 86400))
    dd = total_seconds // 86400
    hh = (total_seconds % 86400) // 3600
    mm = (total_seconds % 3600) // 60
    if dd > 0:
        return f"{dd} hari {hh} jam {mm} menit"
    if hh > 0:
        return f"{hh} jam {mm} menit"
    return f"{mm} menit"


def _safe_mode(series):
    try:
        mode = series.mode(dropna=True)
        return None if mode.empty else str(mode.iloc[0])
    except Exception:
        return None


def _choose_col(cols, candidates):
    norm = {str(c).strip().upper(): c for c in cols}
    for cand in candidates:
        if cand.upper() in norm:
            return norm[cand.upper()]
    for c in cols:
        cu = str(c).strip().upper()
        if any(k.upper() in cu for k in candidates):
            return c
    return None


def _sela_month_year_from_period(value):
    """Parse periode string into {year, month, month_name, month_key}; supports Januari 2023, Jan-2023, 2023-01, 01/2023."""
    s = str(value or "").strip().lower()
    year_match = re.search(r"(20\d{2})", s)
    if not year_match:
        return {"year": None, "month": None, "month_name": None, "month_key": None}
    year = year_match.group(1)
    month_map = {
        "januari": 1, "jan": 1, "january": 1,
        "februari": 2, "feb": 2, "february": 2,
        "maret": 3, "mar": 3, "march": 3,
        "april": 4, "apr": 4,
        "mei": 5, "may": 5,
        "juni": 6, "jun": 6, "june": 6,
        "juli": 7, "jul": 7, "july": 7,
        "agustus": 8, "agus": 8, "agt": 8, "agu": 8, "aug": 8, "august": 8,
        "september": 9, "sep": 9, "sept": 9,
        "oktober": 10, "okt": 10, "oct": 10, "october": 10,
        "november": 11, "nov": 11,
        "desember": 12, "des": 12, "dec": 12, "december": 12,
    }
    month = None
    # match longest labels first so "maret" is preferred over "mar"
    for label, num in sorted(month_map.items(), key=lambda kv: len(kv[0]), reverse=True):
        if re.search(r"(^|[^a-z])" + re.escape(label) + r"([^a-z]|$)", s):
            month = num
            break
    if month is None:
        # numeric patterns such as 2024-04, 04/2024, 04.2024
        pats = [
            r"20\d{2}[^0-9]([01]?\d)",
            r"([01]?\d)[^0-9]20\d{2}",
        ]
        for pat in pats:
            m = re.search(pat, s)
            if m:
                cand = int(m.group(1))
                if 1 <= cand <= 12:
                    month = cand
                    break
    month_names = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    if month is None:
        return {"year": year, "month": None, "month_name": None, "month_key": None}
    return {
        "year": year,
        "month": int(month),
        "month_name": month_names[int(month)-1],
        "month_key": f"{year}-{int(month):02d}",
    }


def build_sela_payload(df_filtered, periode_col: str):
    payload = {
        "meta": {
            "assistant_name": "SELA",
            "version": "v10",
        },
        "metrics": {},
        "period_stats": [],
        "year_stats": [],
        "transaction_stats": [],
        "vendor_stats": [],
        "nomor_stats": [],
        "proses_stats": [],
        "process_year_stats": [],
        "process_month_stats": [],
        "process_period_stats": [],
        "process_transaction_year_stats": [],
        "process_transaction_month_stats": [],
        "process_vendor_year_stats": [],
        "process_vendor_month_stats": [],
        "sample_records": [],
    }

    if df_filtered is None or not isinstance(df_filtered, pd.DataFrame) or df_filtered.empty:
        payload["meta"]["status"] = "empty"
        return payload

    df = df_filtered.copy()
    cols = list(df.columns)
    trx_col = _choose_col(cols, ["JENIS TRANSAKSI", "JENIS_TRANSAKSI", "TRANSAKSI"])
    vendor_col = _choose_col(cols, ["NAMA VENDOR", "VENDOR", "NAMA CABANG", "CABANG"])
    nomor_col = _choose_col(cols, ["NOMOR PERMOHONAN", "NO PERMOHONAN", "NO. PERMOHONAN", "NOMOR REQUEST", "REQUEST NUMBER"])
    nilai_col = _choose_col(cols, ["NILAI TRANSAKSI", "NILAI", "AMOUNT", "TOTAL NILAI"])

    sla_candidates = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    sla_cols = [c for c in sla_candidates if c in df.columns]

    for c in sla_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # convert SLA to days helper series
    days_map = {}
    for c in sla_cols:
        days_map[c] = df[c] / 86400.0

    total_rows = int(len(df))
    total_sla_days = float(days_map.get("TOTAL WAKTU", pd.Series(dtype=float)).mean() or 0)
    period_values = df[periode_col].dropna().astype(str).tolist() if periode_col in df.columns else []
    period_first = period_values[0] if period_values else "-"
    period_last = period_values[-1] if period_values else "-"
    period_mode = _safe_mode(df[periode_col].astype(str)) if periode_col in df.columns else None

    # period stats
    if periode_col in df.columns:
        grp_p = df.groupby(periode_col, dropna=False)
        period_rows = []
        for p, g in grp_p:
            row = {
                "periode": str(p),
                "count": int(len(g)),
            }
            _my = _sela_month_year_from_period(p)
            row.update(_my)
            if "TOTAL WAKTU" in g.columns:
                row["avg_sla_days"] = round(float(pd.to_numeric(g["TOTAL WAKTU"], errors="coerce").mean() / 86400.0), 2) if len(g) else 0
            period_rows.append(row)
        payload["period_stats"] = period_rows

        # derive years
        year_map = {}
        for r in period_rows:
            m = re.search(r"(20\d{2})", r["periode"])
            if m:
                y = m.group(1)
                year_map.setdefault(y, {"year": y, "count": 0, "sum_sla": 0.0, "n_sla": 0})
                year_map[y]["count"] += r["count"]
        if year_map:
            # use raw df for better avg
            tmp = df.copy()
            tmp["_year_sela"] = tmp[periode_col].astype(str).str.extract(r"(20\d{2})")
            for y, g in tmp.dropna(subset=["_year_sela"]).groupby("_year_sela"):
                item = year_map.setdefault(str(y), {"year": str(y), "count": 0, "sum_sla": 0.0, "n_sla": 0})
                item["count"] = int(len(g))
                if "TOTAL WAKTU" in g.columns:
                    item["avg_sla_days"] = round(float(pd.to_numeric(g["TOTAL WAKTU"], errors="coerce").mean() / 86400.0), 2)
            payload["year_stats"] = sorted(year_map.values(), key=lambda x: x["year"])

        # intelligent process aggregates for SELA natural filtering.
        def _sela_process_avg_row(g):
            item = {"count": int(len(g))}
            for c in sla_cols:
                if c in g.columns:
                    s = pd.to_numeric(g[c], errors="coerce")
                    item[c] = round(float(s.mean() / 86400.0), 2) if s.notna().any() else None
            return item

        tmp_proc = df.copy()
        tmp_proc["_year_sela"] = tmp_proc[periode_col].astype(str).str.extract(r"(20\d{2})")
        _my_df = tmp_proc[periode_col].astype(str).apply(_sela_month_year_from_period).apply(pd.Series)
        tmp_proc["_month_key_sela"] = _my_df.get("month_key")
        tmp_proc["_month_name_sela"] = _my_df.get("month_name")
        tmp_proc["_month_num_sela"] = _my_df.get("month")

        process_year_rows = []
        for y, g in tmp_proc.dropna(subset=["_year_sela"]).groupby("_year_sela"):
            item = {"year": str(y)}
            item.update(_sela_process_avg_row(g))
            process_year_rows.append(item)
        payload["process_year_stats"] = sorted(process_year_rows, key=lambda x: x["year"])

        process_period_rows = []
        for p, g in df.groupby(periode_col, dropna=False):
            item = {"periode": str(p)}
            item.update(_sela_month_year_from_period(p))
            item.update(_sela_process_avg_row(g))
            process_period_rows.append(item)
        payload["process_period_stats"] = process_period_rows

        process_month_rows = []
        month_ready = tmp_proc.dropna(subset=["_month_key_sela"]).copy()
        if not month_ready.empty:
            for mk, g in month_ready.groupby("_month_key_sela", dropna=False):
                item = {
                    "month_key": str(mk),
                    "year": str(g["_year_sela"].dropna().iloc[0]) if g["_year_sela"].notna().any() else None,
                    "month": int(g["_month_num_sela"].dropna().iloc[0]) if g["_month_num_sela"].notna().any() else None,
                    "month_name": str(g["_month_name_sela"].dropna().iloc[0]) if g["_month_name_sela"].notna().any() else None,
                    "periode": str(g[periode_col].dropna().astype(str).iloc[0]) if g[periode_col].notna().any() else str(mk),
                }
                item.update(_sela_process_avg_row(g))
                process_month_rows.append(item)
        payload["process_month_stats"] = sorted(process_month_rows, key=lambda x: x.get("month_key") or "")

        if trx_col and trx_col in tmp_proc.columns:
            process_trx_year_rows = []
            for (y, k), g in tmp_proc.dropna(subset=["_year_sela"]).groupby(["_year_sela", trx_col], dropna=False):
                item = {"year": str(y), "name": str(k)}
                item.update(_sela_process_avg_row(g))
                process_trx_year_rows.append(item)
            payload["process_transaction_year_stats"] = sorted(process_trx_year_rows, key=lambda x: x.get("count", 0), reverse=True)[:500]

            process_trx_month_rows = []
            trx_month_ready = tmp_proc.dropna(subset=["_month_key_sela"])
            for (mk, k), g in trx_month_ready.groupby(["_month_key_sela", trx_col], dropna=False):
                item = {
                    "month_key": str(mk),
                    "year": str(g["_year_sela"].dropna().iloc[0]) if g["_year_sela"].notna().any() else None,
                    "month": int(g["_month_num_sela"].dropna().iloc[0]) if g["_month_num_sela"].notna().any() else None,
                    "month_name": str(g["_month_name_sela"].dropna().iloc[0]) if g["_month_name_sela"].notna().any() else None,
                    "name": str(k),
                }
                item.update(_sela_process_avg_row(g))
                process_trx_month_rows.append(item)
            payload["process_transaction_month_stats"] = sorted(process_trx_month_rows, key=lambda x: x.get("count", 0), reverse=True)[:800]

        if vendor_col and vendor_col in tmp_proc.columns:
            process_vendor_year_rows = []
            for (y, k), g in tmp_proc.dropna(subset=["_year_sela"]).groupby(["_year_sela", vendor_col], dropna=False):
                item = {"year": str(y), "name": str(k)}
                item.update(_sela_process_avg_row(g))
                process_vendor_year_rows.append(item)
            payload["process_vendor_year_stats"] = sorted(process_vendor_year_rows, key=lambda x: x.get("count", 0), reverse=True)[:500]

            process_vendor_month_rows = []
            vendor_month_ready = tmp_proc.dropna(subset=["_month_key_sela"])
            for (mk, k), g in vendor_month_ready.groupby(["_month_key_sela", vendor_col], dropna=False):
                item = {
                    "month_key": str(mk),
                    "year": str(g["_year_sela"].dropna().iloc[0]) if g["_year_sela"].notna().any() else None,
                    "month": int(g["_month_num_sela"].dropna().iloc[0]) if g["_month_num_sela"].notna().any() else None,
                    "month_name": str(g["_month_name_sela"].dropna().iloc[0]) if g["_month_name_sela"].notna().any() else None,
                    "name": str(k),
                }
                item.update(_sela_process_avg_row(g))
                process_vendor_month_rows.append(item)
            payload["process_vendor_month_stats"] = sorted(process_vendor_month_rows, key=lambda x: x.get("count", 0), reverse=True)[:800]

    # top transaksi
    if trx_col and trx_col in df.columns:
        out=[]
        for k,g in df.groupby(trx_col, dropna=False):
            item={"name": str(k), "count": int(len(g))}
            if "TOTAL WAKTU" in g.columns:
                item["avg_sla_days"] = round(float(pd.to_numeric(g["TOTAL WAKTU"], errors="coerce").mean()/86400.0),2)
            out.append(item)
        out=sorted(out, key=lambda x: (x.get("avg_sla_days",0), x["count"]), reverse=True)
        payload["transaction_stats"] = out[:15]

    # top vendor
    if vendor_col and vendor_col in df.columns:
        out=[]
        for k,g in df.groupby(vendor_col, dropna=False):
            item={"name": str(k), "count": int(len(g))}
            if "TOTAL WAKTU" in g.columns:
                item["avg_sla_days"] = round(float(pd.to_numeric(g["TOTAL WAKTU"], errors="coerce").mean()/86400.0),2)
            out.append(item)
        out=sorted(out, key=lambda x: (x.get("avg_sla_days",0), x["count"]), reverse=True)
        payload["vendor_stats"] = out[:15]

    # top nomor permohonan
    if nomor_col and nomor_col in df.columns:
        out=[]
        for k,g in df.groupby(nomor_col, dropna=False):
            item={"name": str(k), "count": int(len(g))}
            if "TOTAL WAKTU" in g.columns:
                item["avg_sla_days"] = round(float(pd.to_numeric(g["TOTAL WAKTU"], errors="coerce").mean()/86400.0),2)
            out.append(item)
        out=sorted(out, key=lambda x: (x.get("avg_sla_days",0), x["count"]), reverse=True)
        payload["nomor_stats"] = out[:15]

    # bottleneck proses
    proses = []
    for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]:
        if c in df.columns:
            avg_days = float(pd.to_numeric(df[c], errors="coerce").mean()/86400.0)
            proses.append({"name": c, "avg_sla_days": round(avg_days,2)})
    proses = sorted(proses, key=lambda x: x["avg_sla_days"], reverse=True)
    payload["proses_stats"] = proses

    # sample records کوچک
    sample_cols = [c for c in [periode_col, nomor_col, trx_col, vendor_col, "FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU", nilai_col] if c]
    sample_cols = [c for c in sample_cols if c in df.columns]
    if sample_cols:
        sdf = df[sample_cols].head(80).copy()
        for c in sla_cols:
            if c in sdf.columns:
                sdf[c] = pd.to_numeric(sdf[c], errors="coerce").fillna(0).div(86400).round(2)
        payload["sample_records"] = json.loads(sdf.to_json(orient="records", force_ascii=False))

    last_count = payload["period_stats"][-1]["count"] if payload["period_stats"] else total_rows
    prev_count = payload["period_stats"][-2]["count"] if len(payload["period_stats"]) > 1 else None
    growth = None
    if prev_count and prev_count != 0:
        growth = round(((last_count - prev_count) / prev_count) * 100, 2)

    top_trx = payload["transaction_stats"][0] if payload["transaction_stats"] else None
    top_vendor = payload["vendor_stats"][0] if payload["vendor_stats"] else None
    top_nomor = payload["nomor_stats"][0] if payload["nomor_stats"] else None
    bottleneck = payload["proses_stats"][0] if payload["proses_stats"] else None
    total_nilai = None
    if nilai_col and nilai_col in df.columns:
        try:
            total_nilai = float(pd.to_numeric(df[nilai_col], errors="coerce").sum())
        except Exception:
            total_nilai = None

    payload["metrics"] = {
        "transaction_count": total_rows,
        "avg_sla_days": round(total_sla_days, 2),
        "period_first": str(period_rows[0]["periode"]) if payload["period_stats"] else (period_first or "-"),
        "period_last": str(period_rows[-1]["periode"]) if payload["period_stats"] else (period_last or "-"),
        "period_mode": period_mode or "-",
        "latest_growth_pct": growth,
        "latest_count": last_count,
        "prev_count": prev_count,
        "top_transaction": top_trx,
        "top_vendor": top_vendor,
        "top_nomor": top_nomor,
        "bottleneck": bottleneck,
        "total_nilai": total_nilai,
        "currency_label": "Rp" if total_nilai is not None else None,
    }
    payload["meta"].update({
        "trx_col": trx_col,
        "vendor_col": vendor_col,
        "nomor_col": nomor_col,
        "periode_col": periode_col,
        "nilai_col": nilai_col,
        "status": "ok",
    })
    return payload



def render_sela_widget(df_filtered, periode_col: str):
    payload = build_sela_payload(df_filtered, periode_col)
    data_json = json.dumps(payload, ensure_ascii=False)

    html = """
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    :root{
      --bg1:#07111f;
      --bg2:#0b2034;
      --bg3:#17314a;
      --card:rgba(255,255,255,.08);
      --line:rgba(255,255,255,.14);
      --text:#eef6ff;
      --muted:#a8bdd2;
      --accent:#34d399;
      --accent2:#60a5fa;
      --pink:#f472b6;
      --warning:#fbbf24;
    }
    *{box-sizing:border-box}
    body{margin:0;background:transparent;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:var(--text)}
    .sela-root{
      width:100%;
      min-height:820px;
      border-radius:28px;
      border:1px solid rgba(255,255,255,.08);
      background:
        radial-gradient(circle at top left, rgba(96,165,250,.18), transparent 30%),
        radial-gradient(circle at bottom right, rgba(52,211,153,.18), transparent 28%),
        linear-gradient(145deg,var(--bg2),var(--bg1) 56%,#081321 100%);
      box-shadow:0 24px 64px rgba(0,0,0,.45);
      overflow:hidden;
    }
    .head{display:flex;justify-content:space-between;align-items:flex-start;padding:22px 24px 16px 24px;border-bottom:1px solid var(--line);gap:16px;flex-wrap:wrap}
    .brand{display:flex;gap:14px;align-items:center;min-width:0}
    .logo{
      width:56px;height:56px;border-radius:18px;background:linear-gradient(135deg,#60a5fa,#34d399);display:flex;align-items:center;justify-content:center;
      font-weight:800;font-size:26px;color:#fff;box-shadow:0 12px 24px rgba(52,211,153,.28)
    }
    .title{font-size:28px;font-weight:800;line-height:1.1;margin:0}
    .subtitle{color:var(--muted);font-size:15px;max-width:720px;margin-top:6px}
    .head-tags{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
    .tag{padding:10px 16px;border:1px solid rgba(96,165,250,.4);border-radius:999px;background:rgba(9,31,51,.72);font-size:12px;font-weight:700;color:#d7ebff;letter-spacing:.03em}
    .content{padding:22px;display:grid;grid-template-columns:360px minmax(0,1fr);gap:20px;align-items:start}
    .panel{background:var(--card);border:1px solid var(--line);border-radius:24px;backdrop-filter:blur(10px)}
    .avatar-panel{padding:18px;display:flex;flex-direction:column;gap:14px;min-height:690px}
    .hero-stage{position:relative;flex:1;min-height:500px;border-radius:24px;background:linear-gradient(180deg,rgba(96,165,250,.12),rgba(255,255,255,.02));overflow:hidden;border:1px solid rgba(255,255,255,.08)}
    .hero-stage::before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 50% 28%, rgba(96,165,250,.18), transparent 42%),radial-gradient(circle at 50% 80%, rgba(52,211,153,.15), transparent 30%);pointer-events:none}
    .hero-stage::after{content:"";position:absolute;inset:14px;border-radius:22px;border:1px solid rgba(255,255,255,.06);pointer-events:none}
    .avatar-wrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:20px}
    .female-avatar{position:relative;width:min(100%,290px);height:min(100%,430px);display:flex;align-items:center;justify-content:center;transition:transform .18s ease, filter .18s ease}
    .avatar-halo{position:absolute;inset:auto 50% 12px auto;transform:translateX(50%);width:230px;height:230px;border-radius:50%;background:radial-gradient(circle, rgba(52,211,153,.16), transparent 68%);filter:blur(10px);animation:pulse 3.8s ease-in-out infinite}
    .avatar-card{position:relative;width:100%;height:100%;border-radius:28px;overflow:hidden;background:linear-gradient(180deg, rgba(7,17,31,.85), rgba(9,20,37,.98));box-shadow:0 18px 50px rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.08)}
    .avatar-photo{width:100%;height:100%;object-fit:cover;display:block;filter:saturate(1.05) contrast(1.04) brightness(1.01)}
    .lip-sync-mouth{position:absolute;left:50%;top:49.7%;transform:translate(-50%,-50%) scaleY(var(--mouth-open,.20)) scaleX(var(--mouth-wide,1));width:43px;height:20px;border-radius:0 0 26px 26px;background:radial-gradient(ellipse at 50% 16%,#f2a0b2 0 8%,#b94b66 22%,#64172d 72%);box-shadow:0 2px 8px rgba(0,0,0,.30), inset 0 3px 2px rgba(255,218,225,.34), inset 0 -7px 8px rgba(50,4,20,.55);opacity:.82;z-index:3;transition:transform .055s linear, width .08s linear, opacity .12s ease;will-change:transform,width}
    .lip-sync-mouth::before{content:"";position:absolute;left:4px;right:4px;top:-2px;height:5px;border-radius:999px;background:linear-gradient(90deg,transparent,#c9697c,transparent);opacity:.82}
    .lip-sync-mouth::after{content:"";position:absolute;left:9px;right:9px;top:5px;height:3px;border-radius:999px;background:rgba(255,230,235,.55);filter:blur(.2px)}
    .female-avatar.speaking .lip-sync-mouth{opacity:.97}
    .female-avatar.listening .lip-sync-mouth{--mouth-open:.16;--mouth-wide:.92;opacity:.74}
    .avatar-overlay{position:absolute;inset:0;background:linear-gradient(180deg, rgba(7,17,31,.05) 0%, rgba(7,17,31,.00) 35%, rgba(7,17,31,.35) 100%)}
    .avatar-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(96,165,250,.07) 1px, transparent 1px),linear-gradient(90deg, rgba(96,165,250,.07) 1px, transparent 1px);background-size:28px 28px;mask-image:linear-gradient(to bottom, rgba(0,0,0,.0), rgba(0,0,0,.8) 25%, rgba(0,0,0,.9) 75%, rgba(0,0,0,0))}
    .avatar-label{position:absolute;left:16px;right:16px;bottom:16px;padding:11px 14px;border-radius:16px;background:rgba(9,20,37,.72);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.08);color:#dff3ff;font-size:13px;line-height:1.4}
    .avatar-label strong{display:block;font-size:14px;color:#ffffff;margin-bottom:2px}
    .female-avatar.listening{transform:scale(1.012)}
    .female-avatar.listening .avatar-card{box-shadow:0 0 0 1px rgba(96,165,250,.25),0 18px 50px rgba(24,119,242,.22)}
    .female-avatar.listening .avatar-halo{background:radial-gradient(circle, rgba(96,165,250,.28), transparent 68%)}
    .female-avatar.speaking{transform:translateY(-2px)}
    .female-avatar.speaking .avatar-card{box-shadow:0 0 0 1px rgba(52,211,153,.26),0 20px 56px rgba(34,197,94,.24)}
    .female-avatar.speaking .avatar-halo{background:radial-gradient(circle, rgba(52,211,153,.28), transparent 68%)}
    .wavebar-wrap{display:flex;justify-content:center;gap:6px;padding-top:8px}
    .wavebar{width:6px;height:10px;border-radius:999px;background:linear-gradient(180deg,#60a5fa,#34d399);opacity:.68;animation:wave 1.25s ease-in-out infinite}
    .wavebar:nth-child(2){animation-delay:.1s}.wavebar:nth-child(3){animation-delay:.2s}.wavebar:nth-child(4){animation-delay:.3s}.wavebar:nth-child(5){animation-delay:.4s}
    .right-panel{padding:18px;display:grid;grid-template-rows:auto auto 1fr auto;gap:16px;min-height:690px}
    .speech{padding:16px 18px;border-radius:18px;background:linear-gradient(180deg,rgba(18,30,48,.95),rgba(23,37,62,.88));border:1px solid rgba(255,255,255,.08);line-height:1.55;font-size:15px;box-shadow:inset 0 1px 0 rgba(255,255,255,.05)}
    .metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
    .metric{padding:14px;border-radius:18px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);min-height:92px}
    .metric .label{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#b8cde0;margin-bottom:8px}
    .metric .value{font-size:26px;font-weight:800;line-height:1.1}
    .metric .sub{font-size:12px;color:#aac2d8;margin-top:6px;line-height:1.35}
    .selectors{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:10px;align-items:center}
    .selectors select,.chat-input{width:100%;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);border-radius:14px;color:#eef6ff;padding:12px 14px;font-size:14px;outline:none}
    .btn{border:none;border-radius:14px;padding:12px 15px;font-weight:700;font-size:14px;cursor:pointer;transition:.18s ease;background:rgba(255,255,255,.08);color:#eef6ff;border:1px solid rgba(255,255,255,.12)}
    .btn:hover{transform:translateY(-1px)}
    .btn.primary{background:linear-gradient(135deg,#34d399,#22c55e);color:#052e22;box-shadow:0 10px 24px rgba(34,197,94,.25)}
    .btn.secondary{background:linear-gradient(135deg,#60a5fa,#3b82f6);color:white}
    .btn.dark{background:rgba(15,23,42,.88)}
    .chips{display:flex;flex-wrap:wrap;gap:10px}
    .chip{padding:10px 14px;border-radius:999px;border:1px solid rgba(52,211,153,.45);background:rgba(15,23,42,.88);color:#e8f5ff;font-size:13px;font-weight:700;cursor:pointer}
    .chip:hover{background:rgba(52,211,153,.16)}
    .chatbox{min-height:245px;max-height:320px;overflow:auto;padding-right:4px;display:flex;flex-direction:column;gap:12px}
    .msg{max-width:88%;padding:12px 14px;border-radius:18px;line-height:1.5;font-size:14px;box-shadow:0 8px 18px rgba(0,0,0,.08)}
    .msg.user{align-self:flex-end;background:linear-gradient(135deg,#2563eb,#0ea5e9);border-bottom-right-radius:6px}
    .msg.bot{align-self:flex-start;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.08);border-bottom-left-radius:6px}
    .msg small{display:block;color:#c7d9ea;margin-top:6px}
    .composer{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px;align-items:center}
    .footer-note{font-size:12px;color:#9eb7cb;line-height:1.45}
    .statusline{font-size:12px;color:#bfd8eb}
    @keyframes blink{0%,46%,48%,100%{transform:scaleY(0)}47%{transform:scaleY(1)}}
    @keyframes wave{0%,100%{height:10px;opacity:.45}50%{height:28px;opacity:1}}
    @keyframes talkMouth{0%{height:7px;width:42px;border-radius:0 0 24px 24px}28%{height:22px;width:34px;border-radius:4px 4px 22px 22px}55%{height:12px;width:46px;border-radius:0 0 26px 26px}78%{height:26px;width:31px;border-radius:4px 4px 20px 20px}100%{height:8px;width:42px;border-radius:0 0 24px 24px}}
    @keyframes pulse{0%,100%{transform:translateX(-50%) scale(1);opacity:.75}50%{transform:translateX(-50%) scale(1.08);opacity:1}}
    @media (max-width: 1180px){.content{grid-template-columns:1fr}.avatar-panel,.right-panel{min-height:unset}.hero-stage{min-height:430px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.selectors{grid-template-columns:1fr 1fr}.composer{grid-template-columns:1fr 1fr}.btn.send{grid-column:span 2}}
    @media (max-width: 720px){.title{font-size:22px}.head{padding:18px}.content{padding:16px}.metrics{grid-template-columns:1fr}.selectors{grid-template-columns:1fr}.composer{grid-template-columns:1fr}.female-avatar{transform:scale(.92)}}
  </style>
</head>
<body>
  <div class="sela-root">
    <div class="head">
      <div class="brand">
        <div class="logo">S</div>
        <div>
          <div class="title">SELA v10 • Smart Virtual Human</div>
          <div class="subtitle">Asisten virtual human wanita dengan lip-sync lebih halus, analisis periode sampai level bulan, dan kemampuan menjawab SLA otomatis sesuai filter yang diminta.</div>
        </div>
      </div>
      <div class="head-tags">
        <div class="tag">DATA CONNECTED</div>
        <div class="tag">VOICE READY</div>
        <div class="tag">LIP SYNC</div>
        <div class="tag">SMART FILTER</div>
      </div>
    </div>

    <div class="content">
      <div class="panel avatar-panel">
        <div class="hero-stage">
          <div class="avatar-wrap">
            <div id="femaleAvatar" class="female-avatar">
              <div class="avatar-halo"></div>
              <div class="avatar-card">
                <img class="avatar-photo" src="data:image/webp;base64,UklGRq4lAQBXRUJQVlA4IKIlAQBwwgedASo+BKgFPmEulEekKjKsolLJ6lAMCWdt36gUbRgcwWfVrCcbeJNtG9z73P/Vrfdoc2noX+b7ZfjD0AvDf8EhAvzAM1P676g/nwfr//Q6lP/d4UWC86e7ruVTEz9vJT4Hy1fd++H/3PZR/WPRX8tz9x/hp/b//X6wP5//wP3P92v1I/2n1HP7N/quvH/uPqZ+cz62P9t/9Ppw6lt8W/+nod+U/7X7eeUf5p+l/7/9tnQflD197aP+/yT/ff9j0IP2fzm5cPrAqZl/S42oX+W59jWn+e+eIL94fpmifpDkrXLpc26OzyULtM+n19rFoqSG4Hnd/QDFOVaCXMkJ+NcSU0IWv7cshByXxq9k/gqP2YdhGWyrEV2HY2wY8I44yg7msHFuWtY1azza0bcKE86Zl5S75/vuyKt+TmIKt1pquULRsp4l68s1eVc0LtRJwpe/8spYFqFLp1PSOjmKbGNKg5wgnIPxsbKvQyK1AlNf/vsSP6qT/5blB3hNRUzfl76DGR9lnLRwOHwSO3wYW4AtJceb0oKbOSUJejGru9DrLl9kLBVpVjKSaAAHwSDPDn23ntABy6qgQ8qywFQtzkY6vkZJ7dNlkTyCN8ZoK0U+4lXRJlRHAVSFLlgJ5UD48//3n88SHwzg3tkcZ/ZGvkaKLG0tZstCkr5sy13DAkonM9yOJqcy+SQhz7JZ2KKzrjPw8xBfGRoxTL9Tpg6h4M9efbqTGmVr2OT9MeZzNQx0BRPvqKDiqqy0lCyLB8Vwk5Y+vwJQAF5nsyUhDF5P/+Z1odJEIsKazQ/pT3oQ7ufStsZqPyA1h22ECZkkumCo/bIdFMgjNFfc3F/8nZ3Xj1LhUSE52Ump91qvmJUBklAUF8VrfZDCHo6OJKpZvUbxyv7fTLJ/LiDNEqU4qYRuUzKxzLYz8p3PN6bVY5xSGHiRFk5rUJ/Z6yFSvtP8dJiiXIbGUyuowazgyuTJ+8CVpgM+d6JPM/FZKME8vvCx1THTvJoR+XrlP1BUzDmzs2STzESlOCoTPPvA21WjoEqVT5tVcNaTTqqSTTQAHK859+N+F0UzZWBgQTbijPm8EEga+0bA5tb+8OSB41iwzNPS+2g44mHHL3MlC39LeSNt6RvlTqBUU6Gnm5slYpYYodhLgsZNBlgzUrBwC+mgtbiFbSVOqs/6EUf0dUSMMOtJowsh3xkja5N8i4k3MYSepk++r7Ro4BeAjaoKU6HOwGHlt8AtzSZpdj8S+fRJc+GpGdKWxG/302WmiSv9AuizIpkZ6hpNOBxecALs7WS8qVPz/AXck158C3+F8El/RUXC3DjmeJ/CRwg/zSS8Ox+QsifPvggEzsPmDOb1QUtudVC697H9xG2jpy12CZfbLfTQwSE0KXuCQSe/apO/CTBCSVlXZu11JnVShMQFeNSBmKgjeyyaksnKbPDQRmVIFkY36C0WM067YgdGWj+2TNtgBdgyGGNM/2TzH91M0x/yMXS7AZipdQvDyjagBLlvN8eggJZu8QxIavzHGpuNt91meejsNAl2stFsklY6DM6wypNz+CQ2OXf2OagdCHsLgSAsDt3LfT+0g1CFw2RzuROs/PwAg2pppRStp1LHnm2lzhBMfqLp5dP5+hlJYUY6MxdiqJd0kGKVESJt9psKwlrmFlJZCAZCAo5o1ot4UyV60g5bCUhUKqc8/ugh1F0S7ZcNvnTp2WdS9Srt5gWxmnf4aVeIeE/LDns2Vg/alRbaqAyixaTb/b56TpgQhs5HdiLgRKt3BUd9I5j6klJTjAu2dDIiqITlRa3WgidCvyiiytLCkTO+xo6Wmz5vOn0ncA4tQ5Hif+jZQjaQbxjvFCrkgmmK6e0cspsbIM67nAHCYJjIEdxR60pOZb8n8S5mKH/vg6FGnm9LfH4fF8SyxI3dfcL1CgRCFy3MUXjLjtu2a+9wK6Q0kywbJihDfm/u12KJblVtpct8940sGqLCD6qU34Vi2ELKwRIk0zsAci9RAiE/474rgIxpHJ/N0UgbULHpaVjK6RGM6gjN2jva7sMB2xBY6AYu90MGh7CKArfB4E0QEgb5qz/YGzdCsr3DVeKDd//hFYKkiLH7euUuTmds5W1lvcULwutrXUonMVIqdylStRYmpj7LQ+oYxKSQg4G6VYVVbLGxePATwcjTmqFvq79G84hCZgv1KN+uiNmX4A2y84PenQtGyVhM2nSYQBfGxHZ2ZJhonwbgSri/vPQmoRh/R1ETuNc82sXj5mExru7Wwo/w/7gXRt6MNzCuFcFm8oNNahqgV/OoKhUt7YgpUHrbEJlUp4cYSxRORvy6jQB98clFIezbuzK30x3ZKcgu6h7ugvoOG2lR9FGGYP3afr4U+er0iKqKBk8lhzJoGurL978k9+Bx0ix/TST9UFXrwiLclESA+lZPfKGDBRM84UMHAWp7atTtOiHMHYrpmjpT/i3zlVa6I6O4KBMuVMteq7Rr0VpmVfwIm6Y6Jff88B1p2Irsf19sk6fljMT+Ng0g9o3I3nPtJlpHU8pWfeKnBOnc1jII+V8SgyqEFYeYOhwLTcyNveO00l60Dx5mW0HvHjGGnBEGFBcrGPTstBXe9eLv7HNiCAuRX1KzXfWbDIF4mTZGv1pUybLFMp/tAxeUoDDmbkjDXinOgWBTwd/useqIWWywZaWbGOH0uTCqaAdQ0GG3Q7yl8t6WLLwCkxUbBgOHMg6ozFaVo3GvaipOU3uQ8OLpuF/08TnMX7E5W9Jko52cAHIjwfHbP2c4w6oeKKOkJzEkj/IXellGXRRdZup1e8VWJhJH4BVPl9BtENkLSA0apBjr/OBKgXAxZMeLa9vvipwKxguqpdlhtdaN1dfqxTScGX18BDk6IhKm9gFQaZKa0+jV3K4xa51wt67D+AI2ztjJu8DIjAyA9wupdjdPKEeC65OSwzv+FJQMx0fyCxVy7o1Nyj9BTnLWv35aEuzHGboTTmMsmFVhJT1N623j/MNcYGbiEg5qVEXAROKwH1tw/WuuYUjCiAn7NysgTUlhG0B4C7E8tC1wanqsvNcoRkQbdzqW6GAmtL8JEWupaniruHgDe8ABGOyLsjBHw6TA2AIo0xbALuc80ypVBzEBDazWR0oTzR2oa5rX0C7lMz+AiTCOC7cOMmDcqkEpGTXHnww0RTvBnAlsjIZ3liWE/eZF8NY3Z7eTRDu/SDUFOP4BCCMXClYlUSsBNJ8lAMpxmrQfymFPJWdA8vz8Z3VIBEc1DAlDjwVz3eEciGyi6cMb9csu5DGn0pQqBZt483hieuaLjPKW2v8ZKzaT51vylUscRhQYZ2GKSftXw4jzxD0/BzqnGbcZsaio9pgyRk/i8mU0LnzyED19vcaJsHBmhipj+EWgvVHLF7gmDjia7lUxoAq6pS/8/iJOpTYuphEyjkIPEYWerPk4fXO7IwwZs1Z2n5t3BUziqg+Iw1NgSAm/Ir0jGMR/E1lfBvRlTbwLfQJfXX0dY+8Hv3u9nQJje4D8qhdPxzgKg6Gu8NYurYoPpagW5kreqQLBOXnBvihAABvAV6a/PRptz/O0OWFHotuyqMsJFN+lKUD9bkwcb7MZeKNlAvgDNDNexTMAoFrn89mwxaB6I5mwObPmQJ+P+suuRKH0L37hPsiYgeU9fLLEumh90SAVK5L/pWRWXYzNDREGI+FReDhxQ1KHfA9wFkJfzJiJKn+nJrxXxe2od4gXW7JZaLuVtyFdt9mU08hjTKXbmuoRnwQNyY/74Gd5ylMMeBseOk16lRUHJrkgkCx/TiyL78vkBYd98Mru3MJIjVI46Qztj2lW+4tKGBopIYqS835kac8pRY5L3SNPum6LNxoeR8Z3GLW0yFR0dAB8YkwoubJKAuQr9DJTh0+VlT3C9XrudPBco1amLVh7+Bw9Twz3uzQ9y1GSRZ5ssB73JvkckZBMIC17WH7PrSbx9sPX4PUACqG8RuYY1D30oVlzYvDrDyXZQUkH2kPl/xq4e7MB4tXyrShsDUB2N2G1TMarwNhXsYcgzrj3nS7L8iZfdtCY9UP7byhUmF0xmGle0xCoYKYYkw3E4pfEgO5A/rdoKQ2fUOQW0/EIXqeHswMtfBpDAXRgYrGTVk1ScRhwct1Do1U8KD/zrbk+/FCFfcaCsmXB8J2k4Iupa6U38DOHwDjUTmZpK6iE4LTvQ8s2ZIiHs+sSfhSV2AZ1oBjhMaF7EAC0Tf7CszacrvKQ8NajAI63XW350GHRyY/ZRPJJMn6B+Vc5R+ZnycUhPbQo5V57XipO9kxOx3QK2q1DT8FzbDm5rk6QWxdtnobcxiQQfnRkpgMoQl1APJaIbh7CITVMvYM8xbEOOE6d318OSynLdtHJzczclw+nCMwBj8sOYcrkme5ank7lVNbkMIyl7xpisEnfPxdC0SUb2YrfYXgnsDBr66tDDba8ffaxzNN9PgRCqZ/slNcQbDhIQCQ//9pjdK9ddnbyjfcuTZRbTk1fK7+HrbSPeNI9o1YCkn1ncZB+uO1f726hat483G/aaQlX4lipXSd5v//8Bc+/ExtW7Y0U1xiuoJeLX/htrViW5ZEPkS2kec9g3S0vE8FtoxMHqbnEAdNduptRN7GaiUtwX0mIEduKPdgOz9Y+gZDZoYVY3ihMnr/xvi7kpcpBppwvEHlBOQyMyJ7ASzrzTA+KE3f8s/c19/jntMnrnMkIMXlgdU/cm5NB9MmH22rkU94KrgxnJTdRWaNoB5UzTq8tIPC0PB8+eYQVdudpmZiZ9jHQ+zVmOuZl9LIgWW1Udm5qx9/VEAEnBKuMDn3C3GND1psk3JAV3vcZRzzE6u9j19dkAPkAoN9uQk65fhrGUoDWwLOrMtXXCe/8NxXZeefYVEqT3QUw5IRyOq+3vW7yk5GETufh9U2hP9qRCh7Si858yfD0BurbT/qNZ1ZZ7INsQTy6RQ6DRmZBDH8PRUelOZQlFokLJJGlZevigSU8MrB8k8g3aHK/ShiOwdE/8ef81pShHFmYNupioKNO4BTQEcC6ZOPgQCP7uzpFZ5zTFirknBrpmM+68BEEeipcaJtp6jqrJN++2Fy1S5zOhdgb/foKZZgtKh80+3RNqctC15YdQqBBJvy4SDy3sVgs0j1A+Jh1iZL8v7HA/IOTvPr3GevQce/NuGKMiaGonKoiRrPzEXlJyU7mx5r9BI3dFKRSMDKhn2gIA9KdGgS4hbwugvgq1osnm7JklB1pq+Bv7a+bNnk0CvBtYZtT8K1sWcmLUXmHX0WU3dzKA7QSoHqni6gfinncCldw12aFrDv5YMoH0nNYKsZzJfVws4FbH+xaGK4xrKz7HTp0LkffFDG9yuwqH1Bdpx0N/SbZJxTYvP0kFqqH7x+MZjePmQzSBo9SZ7r5a4UOrxugWo1kuZVtLTkqUotZK/P5dze+61DwCTqfigHeKCDTdsYBeZpxHzn2pgPKI+RfShJ/ZgPzrEtIHz83bw7ScD+oTacn39j9ODMzqKfzO+tZLaM7sWswkP/Ew0IEgtOEi5+t5HXJ3mjgI5Iq/K/AmIqLYuDJeH7BbhjeTs/VvLlzGOkzavYaeAP2tKIRZDhFXOZn9u9SlmP7eol60/FsLP8nPflLOVjRJzv/E6O+TpdfzHVfAUcL/yol5GPBwkqWJjAXYkuHSdc5Psx2+j7mQakAEA52P18y7NFsttDeBI5dnIHdU/P5mzPPZnb+AkXkjOb+9xydDi00rSHgJTZ+qHhzAIImv7wvJ5NEr24pKBQuDl2ZBeUssYHna20S8NscfO7mc1LtV9rL7Qt8xGQULnB2BEU7zV6K8n9EJb7eYNPWtkcToCWAwaFYczK9DU8YrWLnZ7jOIIv19HoGm4yFNVXXINEt6OLxJFYwiceLPxDKYmYP9z9Vop+7eDQaCxMvgG4S01GjTMl3+iZTSNUpwZLpCxYjwZ/mAhQ2RuwYnzx9ppW7sv26SeGXa4goAvYoWQlWFJzUM2hDSwfYN5Bk5YBzToNCorqnHa1K6oj9ehDLGtpfJF9+rVCiKFaQWmyVxfIkSAx8AtRN+C91qNVoVqqjvOrv10H/sDU2oCPs0Bih8bZICz1tthrqbBzgVdf9H9VIH5AXdnjTcfaGQ2auqH1bSE/vIZon+wrbXUahmYkNdK4Gp7CAOdnRU2U3XAxNwta5n+tOQxuqtxz1Zp+4NA/4fEVIq4mtgQWXJ942Mzq0nOyHHtnH/Thqwq1+vAYgHruYVzIsGnEcOa4GngkZhyhzqyV3N2ysOvCNLYU50kkVjX0O/BcCjtepX92I2yBAQhBDxZJaKyAHXDJootiv8eJSyDfwXC9nKlG2JWcJYki9jOSrDrpl3r28aWvSZapFPwryj0bOkWeE+WN9xZBCqoPyaf/WAWXTKM+bG/vUIpYS5wN6C52YzWi/twS3fuX51wUchVEND6dXDEcKzWMGci7Pusq746xg1YOHB6+6MDOGb+XWKvNRvf/zJQIwpgeIKbuGk858FFlEjNNqnjhV3oDlEeu023jZ5pwLc6iT99CtRTQgvSiiLJHYoPeHTIuZj9HQ0IaBPEz/2Nga5hw0JTIgk2MSUhSt1Wjd/lun4tnwmYmowhF079788Ixn49V3VK4FM1so0bH/LEFovxAq0xjZC82PO3aIsG11mfH8TDYGrZuGzVmX542DtTwXWIAo9WiHhoalD5RKybzoh7LdBBvYwsU9GWLCu5eVev2Zz+Br7joQt9UONeXv+gNDEpa2Mv++5rKOuzwhFfYHqf7sMlvHC/OIRf9kz2/hAKlRv4e8EQLw+beGB6N0sH75WfnLabHq7qxwIFmPfJuK6SSszIKTNvIbXl7dBXt+9yYaZceIkq+in0if6dCTzND10s0g+K9/PYz8A7sWneFIAx+r1jOZHer3O90MgyFdBWqYu8BgggbzRxZYAFyHL8PpqiawSl7Uf/IIHL5zwqhSa9NT45Fd/K0ueDPhgdYBi9QcWz1FWRDY42fGQN7fB9vWEwyT7AIWqdmfAFKIsFagXSHUbZF9X7A8c66QvzIKKSa9VhTstvdItyOqr01msS71glyA2qkACz5U4Df6iU7pvjAcpmSB3Kb48VX5luiAi4rZZAf/1y6GG2hBo3P7Rpe6gCbWMNMllyzc/hHtE8JRig7RU2cBv0UgTbglt/RfbbH+zp6ofuLoo+SBvFFCRZ1413Tf5J1Zy8mEVqZc0V/AUOQvSxHuoDhqnWkOQPrMoSTm6gfEHe4hf6TwLjK4x7ZCDt26+cktu0+Kl+NLQXl0S5TTE3lDL+Be09YqOT/oVSKej/OAAP59Ew+0GUPBhAP38yO1bVY5khOxV3UIxjc48svny8Dd+XeSyauXf0hwjd75WlwhiDkSkbbnpmwiZaIg1IelryzlJ0IFhWUMKt+yEFyGit0pM8wGu8gs9UXsCrT8gjvKr1Gy/pL/sPkTR/ZW+ubeQStDbVnz0VprWR+Kg1h9CKQIt+UvnC7VSmoVdTBSj3ovh8qLuBjdHG0BkPPDbIQ/5rl5CSBGWb7iHKsgilcME0lv8i2KxOg+oTGtBqbi5juKgRBQqZuifo2SYQg480ggvCS3J1yH1k5O0mLQXJurjN54x+exUc9nElpP3l5s8e6Bv1qK9GpuJITOmcMvPLgy365Ldqrkfz/SohHMsTYSEfWPKF5eG/dtnVO+2komn2r1oDhNfSypfFyqHC1J8h2Pjb4JXvjftATx2y3rLBnflUzJhxN9z/+peg25Q/fNH8ln8///2e+XVwyylw4WuAcV/w/7JywNUYgczoFcokCVVEMazbDDNHG+LBHkaJGc2sfI+vnN2WQem3l8XeekgSPrTEr3zKwHpPMEyXTHm8BNuwl9K+u4cLfhc6zj0W9VS2NqfhdO1pCRP5zXFYiGxDgtCLg4lgi9hlPzZchB1uqMfflYVHzEtv6FUDe8ZHZOh6WcVoa5DI6LiMPhvc+NVX6Ly1md5y8weUbTwd+/nRPn3gUebQ9Gr2bD+SwBAzGnyIs9/pH8j4eKAMrpPNJl+vRZ2CoXFkpT2a+XOOenGf9UFD0CPOKQfl7OzfuLlDiaeVXokntAZD036OqL96xe+MvsgBxafLC33hhNB72xg24pAX4ATLZf1YOINhFScUOYTE2lgAvtX+lq/axHCXB7gsiMryVlLcQ8a9Gc1gZ619A8mWulHzukDULJXIPrIh4h5wX7q7lpbTorZxX/7x0FItxrTp9DbPWxxp5LDU/5AkusXNEoQqz0wu8GDehVxnnAknqUmPhxUNgcJIQH8rUe8WEOcfGu+xwg0kJndcNwmKedGMSkw0Q7HLPhR/qXc2Ga3TaKjisASwonNdLCuUQa+hpoterNWBDKbH5CMO27bSeUbWKkiBCBVH/OIxT/BKzMA13N4NiIsh0M5nim27ZbYwjXHUuGSyonOcnX+uAkbx6xerxLe8tTjs0ZpqdDaq6XlliyzI/vGyXl+gKJbCQmUD4TRX+RAa7MCCoNfb7TqSPcpx3zOYSEeineNDv4QfTpcXmrvBoyHQ29uSTVUZfzX41FsLQbW5qZDm4vv8P+8/f/UgNfbVVyF5xsQy8M+ObfpLeme+SqfklaaXkhyAG+p8dMRLcLaw3SqzGl9cYkj6IiESLnmlmNIC+KJL9Yn5i9qWn1z1r+54W/oyRSqWF1KThzocUubd5XOWEbBbquzlcuMOcPvOEfwFkhSt+QkSXMnCWARtd9XYDRNl/o8h/SYwSN3W1GnBVPspW+Fp2Wt1D64PNHrREDX+DfS18/P5ZZwltKJaR17WJRFZDfhLmCKV1UbiRiA36cSo52fPYO54nEccut1gi5uriC/2yACQHTVX3gHXopyds8IRJfpD2nVcvz5ERqY80l66qSLZ5Ac7V/lHGI+TXhL9YHXWKAk89dywbK/CmLGb5lc9WKVY9+mTXjtaq11Ti2Tj1U7PYWsneNdKJm3llpwifHMeOJRUVyzWa/BfzrN0J8semxVUklPZVac3eVNUHh1uW4HYKVg7GT0uF5YvgR2P5b9hQTxBMHO26nFcHIiTVTEc3q7jMwoHatzwF03+XRSElnJQ14JqCXWu1n4Ka9qI2uPuyjCrPUFvZvu8ROKuwynr06Khe4YPEUHkmGk4GojmSwB3gctYhniRC8p2hrLkhMOJHJLkAE+zRvWtQs266Dc3s0qdWdVxN5TEcpkcv02xyW91IpUZ4QXhyrjtq+G1dvdkoe77YR8HPkvgv3RT+Yb+rJ7ok6ywiOX5C0HIYmQhHW0uc/oT1lRkW0C/MQFq39OI2rSGJCo7gLb02rhQLQ39+o60ynjgMTuag7f1B7asQd0AtD8aTEvvV9GXxt1AtsZGAVrxMd5Tme+nZbqedoc+5itcVEkBTTtBtAH4mBRYpUwKGMwTYWLK7wrRWeuOOWylTKoqc4swG4g+ebzf7vYdVXxtJ2TuDarLF8rHx0++WbllMb0UMehFVcBz0vJ6PqqpyTeK92etUCDoDptGgrbnzECU2tDWQR8BlKlc0Iha2d6J3vk0Wg6abhmtTLMNkhWNEPChtrklJLgpdqRoiJwVlapeT83KzNXuWsswEcd/EKiLljCCTt50pXg/W8Kv5qLyPg2S/m9qho/uM9IH3Er3nJPfpwqmEd5h/t/Tk4l0IBGXXdnhGNNncSEA+FKRTn/sy/i+2hzGk0nVZFq289EyVmUNdu0u800oO2c5lOERPCkMFj2GCZHzk5nGX8EpxXl6YmaAsmYjJicaIdcP2dhf1HcGmad5TYyJ8LwptJXj/1aw0+D+pNNC3uEod40wPjMdbGvr/tlMfGxYk2cfiRZX+z0Yk56JTn5WQuqAQk9CUBPXb9gEkUtrA7tz5hJjNLS5rD4dfc/YaZX2nW3zIBeqspEaukHr+jNJklL382s19Sg3vBy0ckn3CL3DweacQm7mLmE43eGzXy26RllXwuGW6uTpoAJjPtvZWsvtsqrqAxoSYv6ccUmYLLh1leuaITBSWFmmAhdYqGRMmNkryefLTwoRAMizULduTEtLs2S3Ag0iRo/7/kCkUC7SAqGyOWcano77VHgID8Lu4sTieBpKhiH4iD8/hjyTbyT5sxA+y9hTJJEP7//J6CUOpWgSq6JUfN8EQckx06fsCDDsPGzgSVxdEWDlCcsJTgtpSro8mq+zaSZP7l8IZBwtshHU2k7y0v3q6xD2N73D+ZOIOFXq9kMSZq+TEKAQyKLYI38EEsZXU4FLjbx9gu3omD1gYAntWvRwuoy7NiKhDH8mvbNaJCPgMLgOz4s2Do0JOcv3DbcpNMV/QVGlcgITdxH1aGwWeOE4qKpkMYK+/M7WYNZ0B5zhe+OIVm90X0ti3O3UR8/kp0FCm78oK5HdH/rR16bmpuX7iSqz3wYCPp90K5lEXiSFPZMlJnaIcnXYOKNICrL1mD5DZM5+dTGyZXZOdPks/0ibzKBYCfAPeiwgLSrfcw3sNIa71klR/C+Ys/RToE5fFA1TClj926/EZe/OeGbos/zB1czTvylNjyIKbmvGBijylnP0Ek5UobjZNKMGXbCpVbqASEjONHENCtbwyj7HAJbx5r7gHuKinzhYQyZKYeDbb/xXM7toyGUIlltkaHAM0rS/zf0B43AzCyTsjtAXepvvyHKx91Ruvmga3uUOYRdUzY6Uh92Q6DkKnT2q1L+sEOyXS3abNWo9Cxj9v7Hm3qi6Seh1QkAiNZh0+IfC7sv/JOTQJq7fAdVOv/FQYXnMiDRf1KqcHSxFfea4PlcpvW36fuGLeIwWqg5UEjepHePyXzdAw+bBUCtmqMXBb1hIBg7psJ7HuZoIp3VzxOoF4ffGmwa6zGWF3x9zc1UuzYpZF5jmK377vV4UryO42aEHJsKqdxMEJ0/RQh4mo/+5iuqHYHo0UTluPWsOhoAUmlgb5hC8psZPJhwEeS0oYBuKJmA82fLz8vJTSzKdnhj0fBTw0M/imWMNt7GHKwnofgVp17BIFlmQ9NHhUyRp4C4qlO0XDkPnPC7YGVVEOoCr9UC4Eg7ELzix3nK6Y/9GYwchSPDnCf9mGFQK13iNW/douLYQjRqJw6MhxsqgA+O1WokLjkPOOAtM2amKy9EVMrNzuHN2vOey3SEsHIw5zTRWK7oJc5rJdaQm+hESE1L7PD2vk9yuqcCRRI8uv0/icftTQ1mZ+WC9YnzKFWsPRvClUzRJSSUuc8j5AHu5wLGFxje6om65TcO7YY9d0Wpd9ghGI0r71f0yuRzOBb0+0EzXeYWnBej183WOybRCL/lHjcOcY4dmPclNM89+mlDJjejHU7Munwlj4qlfGl/PDn5wq08tIoNpSLY/kr01Oo+qb4UYRcC2DqS3fSBo6W+uZyAGw/9UyqBK72HW5ElKBTWxtCFyzbjgx2Liu3wV8rw1XTVHys2uBBKYqxQsy9Jd6rYIOuo/tZqO9hVE0xSSN+6NyCGc82Z1bcW369730MJ28c/yy4AWEMaMM15Y8xBpj8oMgidyuW1GXiBsmagDzpuFLt1l5lRCGSWd5s0LSPXNvkVeVXsfkLbUuGla1GmyO5v+kysHnkyBxDAmAaeqZQNLoK1NUxVnezYoERcuD+b+EoZ6wYL+tiRrURdapqW27sYWSotXbO40i1cNm20cTPk5imixkZ2wgrjlj4HlttqCDBn0qvD/3aIGDR/C60gl5PFgXgy65MGeSkGc6vVDpnQomBKMhIU/CLlfXmanJpHOn3KB8KO5FjVG/EchTzwVXr5RbwXA91UgBmV4AnkDHJ1qT+v061Ry6sFs0af94oRZ2WhuJLSgR3ey4D8llGIBQzTOCaJ3OHZE0fRAReLqYJQB9qpR+TkbGZvAEypue6J3YM1NTnwFyeeaEMs+DgTPcPQ70yWXMWSE/G+3YJr+isoAJEIsNS7hJlpk3Zd8KTfthKMEcQ4Q+5HiYSX3C2g3NxDqzzVB2YeOivma6iCftcxMvvbhQlmsheG1xy6vtXM9uGuxx4JTjxZqq4DLcrVsv5/n06rSzndbScD18z4EI/gyrVs/8s+1N8VyXGuMikY7yo+nCCighrqMAup/lWThs34rPB2XmGRQngQZEttH09TcIDiHKj3/tSkweeKE2HHZSYPjyfEn5NsIDeLQsjD12VjMmy5yG/V50z6hyglOR3nD/ngi4cWWgTCMyhQpNTmiTwVZwNhcnzLe76hcAzgIlhz0DYVWHfh7X7NLdfX4n7GlI+NWhgAHq6perfnzYjTzC2kMueAFU8PHTH3ZCiy910VqEsdycjSpFlDTIeStZzQFIaWA4qb2CZME+0Jzu/l5RC16oZOP/t6N3cMHgMO5Kxc11QEH6FYXc1pnEzeFf7TkYUIkxNwFr7paKQhWGnpUFtV3xaFd3wTsrz7UynKThLVJ8j9HgBY9doS5lD4d0OvQznJqY6b/OLhXK09rZPApqwdswsB6NjPVtIYkYJjqzHsm13u89NdtisOJXMoA0VsCttZ6iqYOP87t5m8S1lAbPVUXLhwWbcfknHhRljt2P/4VrabOyvK1a7L54f00a2JjcRft81BG9yshmLi86BguyueD194/hfUoxtNheizilnBL9JtYIMMMD/eGxN9tZBbzAkAjgNj+nZOU9zASyW6w5kX2ceMmBN6HosoR1Ct8XpNyetVJL2hQ1YoTmMJybC0Wsk5R1qnAiyDvbahbYfYjo3+xHz1tbYr5DdBP4Lmu/hlwvyUwcwPKGVlbgosgjPBMNQXR4c5f/uvgmgRH2Us04E+VKaNlKnUJUfSwUZQInSXXX1ABudhCl3sIiVPnB38NL+bANBrj9TnWXnRZwonMeAY5R6t1SO/pJVvuqVt+On3+xjbOhWMirEk1THyBASgG71t4qAk0+TF9V6Km0at8kzf0zdRwqw+vz2BOrNSU5lvo32yme2gADKCkZIpJ4To332iBMZ38WhES9rzuOcNKs4tm4ueMUVm9y1miqITlxrQDlG5DpOT0Wyo3ww1UZdTkTwBr1pEgtreKgKzwcrIWZehI3x2vaYkqJ6GJUa2PP/EdClWe7oznDgstO6zQhco9csusNPD8XkXIkqNQ390ms35NSVGT0zgWZwecMLBcCKpYTwLfjXSg4QnedUsv0L+AT+aLpXPv5t1PVCaYfq5GgyOwrIsa7CYvTFeS1pO32f3RQIy0yc0YZyo1QkngT4dYOelxsZWCJdTd5X8iTIx5ZuQxY3uMG6ZDt3LVTLMnZDejuS2DnKimvnRNiU2D0NCqSib5M5wrwHZ7FAL89cYM9WsGMNDe7+Eo8Pdt9yuxNbolxthCh6Z/RjaDC+6yzDeOkVS07AJoK+fcoZNvfephFF0s06zKKoLEV0boYO5+lMdjTimuTlyW0iCKoaRFk15pYphBXYXuVDJ6YG69Y+vLu8SuMSn/MUBfgEjd3ze2X4m8z2jbqMS7eMJgWKsXIEhflczHOmArXNiwif0H25wBcGIvugWdtADrVwwSRrC0ltd/j9SCw1gO83csKr4owmi2FdXc2nD9BoeeAlv+mzsd1h9LcfyUyB83qIlvsqKYR18wQunysRuLoF2yFxqxAoXcX4bFQg+rgIV6kO8bpGgNS6oe0Px7PgmdsRQyUUCfT+rov/orVgFa+CX7winoPQDYjyz1lJ77ktwZOuwLOS1KmJcquMRV0VlpbueKt8dQ9mBNgukLcnO+AcdAKERGSezHb3J9GVYJ7ZY9bkRJ9UOBK1cH2m0th4KHWFERp/JQP2+CfXqflqCBJsr1U5zeXr8wwdVw87UZqL1vtDJOrPVvnMc0DJzdhWwELKr5fmLxlUNApBlhuRWHclyiS/X8qEyVh+WmqiCXyYmbwhfysSdtJf3BFzGKIpMX1/6DpE/R1hUHProlXQZeXiX2A1BF9/lYGODiVJjLbdToTHu1j6GXDiBfe/SNTVw/OSlewmeFJJg9OHzGm8F7oxSPDzL9rzdOll11gTI0xarCp/kGr/2FdI+4ue4DM1O3uFljQJYAxl7fifujazXgPlz3uzO7BxKy2OmBPlVX+AG+gZrMeySEROSDyf8jchWAwPwIP/T82sPpLy4bILjhMhzeZArkPTbN+HwI1wzK4RKlkMaSeV8HQtoS6AhzmkWaV2GZkQ0AN82xiPxgFGPF5o0Lq6Cb6QtJffQvbRrJ+OfnECmL568nVMBUYY2PoawOq+PKPEy/rpBGek4/wS37fJyEuJfGYMhyaOC3GplFtQho9QSATQZZKXtvqsrfthynCVHBOKI0PDypXPzXjfaL6KaMLiBhuXChXPuWkWlN/UoNeqGx6+KittuqfkaPZeRJ6+HjbV4qualClgkzV2vQtpLfo44qxsxZ52MTtI6N8RKWyMBqHwWDSXAZcmkgMlaGBFoMgygxeN7RBJRHpLx9WyQ+fbN0Lf7ApSjzRxhUufCg+ZD3/0+k4ZcXzhVHlvns89nGl0jYEDxZ2c+AqWYASvBxD0pqySHDZeYfyTzTQkr2oWaYoVMqtnNk2t7qZbglgGFkMXrWwi6ZlFl8vhqDFEH5SVwlSxJjxrBp4W1uvMrS0Orp3/doihyYDPSWiHlxoVylYRaN/D1TIWGzDweySBi0MkO6sufm5IGZX/FzAiuCwXtt2WLYwPSmU82llsU07g80Ui05xFokEuPAmr0GZ3pJPI5JUQ10Rb3PL+8PpQYh5flacLP2NYSxzKPl6WPu9K3F3bvMMYafnAJDxfxZqCF/12Rt3nsaFBpY9kyCHFXopSrmEcDSAnMgfjcLSvT/ab5dmTq1Sr4sFmT1wKYNTZeBdID/GpANvTgQm4GdceBe8c0AJO3VRZdMLDxtUrCeitGT3/nGO8gHKttbIOuGURXSaNgba90z7RWgY0c0eVWA66P8RnopZ1opcF8Qjyxw8zhRe1rMDdlmi8dWeNvnWYWKyVINHUDFZ0Rk3QjrtWzFBjklOfuMBOw1qe4XLx5lRFJPoA9xArPCmu/0DLpmfQtqzPlyBlXI3PUvlqhL2N88ud1Etx5vsjyJ7fu0tAw6fIfZimjU5YTiSBxHbyjvDGGk7KlHYpR1Q7xmBdcq7ayoqy/3E/Zea5bzCoWufb+vBuvm9eXCV4MSpPbbWNAMJUoQVtaLdU5w+DblbjZ9sjT+xajrAK3EbTE0k1E300FnfMIpmok0utgpGlOLNSIJsAFwteY7Ff+5rp4YBUeiHqXDsCLzI5iprHMFTRDd+ys9kFck1jod5XrfAlZSHpu3BikMufLS6a07d7Js4FJ3CXRjU/OpF4DlLfgUgyrg4LkeSrNFBUjK/VndGCZ/I5/UFETLrVma1nvNotuyf2D7KVfsyxh7O4oO6vpF/u6PK255P4QNDzKg+/dSi5OGz+Cbwm4T3ygbKV5hP9qfVM+dxaMjt2dWlAX2bnEULJr5kxiWjDyFy1A7AKQS9Bb15ArRUr+wILCVl1KCon/uoC7HQM/YKzw/WJc5mU9wQEfYOjqKPdhj1EYmZtxaNNberBYKpeci2RgWeZeWyYhOpWqznQ1oMhemOsSagJKKbkpfJ0aS+16osddOldCkdkPOKjr6DiC2TYmaQXIKETzVBBv7Sv2crcVNE5Cgc+EEzayHbjIZQE5AHkbn8ze/K5VfqVmhf5SLOaKiHh4g8IO/9CjAfFaqBAxPrH7KCafAwRgU18/5ysPKbYjyRPAty0DVYcmlGPeikF6W+7/MOeCDyRqtuhPz2TeEZa+4TmCdI2BS3UWJFFjwH4qz4hKiTjaghrAAobmbNPjktqv7EwyfwjlZ+D6wM81kLfCb1+MvZlHoulHIyOPS3NzhVcfc9PnTDecol3J+IVtljXNZCnRkMmnCv207dmsPD5FsTOX/s6THq5dBTvgCIQKWIfPksJZD1SrJjr1kzEYRn9VZmJo6fIim0a4ax+0ft/ywXkctc77YDYTer7FcYbeVEGRSp7RwxBc89Cw0sSiJToIsKe4d1yzVDyVce3PBOZWUcxQRS1FOyc6K+ZS6de0omLy1wsGu1hxtNZwoRXwm+GdvmW1aidg1ntE0w7Gs/MY1LhZuyZlZBKnsMXrM9X0FQt36zfVITd5ilU4BU2GEiitxl0Vw2JP3mL7N3pJa6yCIE78N5JzS3elHxLxrbhi1ij21KfCvu9C1wFgwiiV0e7vkoKXwm070IXP2D+mQnpuxiwPtU9/HRvM11rQXrKg9OvX7+yrZ9hAj4yB4aZO1XDhmX2PXTW9NwE+NP/H1yCBU24EOlELWf5dZyG9JPStPMm+6eHez49JAAmbGK5lJ/H3TVvmoWlftXYFYizlDDhgHqqLzdADoVgjO1y1I0IeIceCRx0wM6/8uc2e/EmNa8YC16x5XMby/u6Oolu1VzuDXj7gZU5EBvMkKUVl0TeGR2OyBE/xkAHx7usWvVE7pjF27g2UJEWEK4IfH1YPWdlS6nwDuWxiCmfONUUA6NIefwV+T4i1cfUn8kCS4ig/KgWjk7/rK4yf4Z4qZEXWYUbDPXyQFU9lk7Gl5oU/Ell9ETqycSSQox+RfK9lO6NzptVJK+EVdx7eo5+AiIqKczOl3NDjOG0WWOmovP0feQnQ9oy4+epdPvOQQmiYeZ5NEDALVSENlTKduIoax4UP+Qf1l59smpQCgg0BLA7qWOyirdk4bjXZxsBHeBWUCWV+SU+NlwVKx9wUgedVK4xB6DtfcbNMC29ye/mYgLu5SNQnpT7TwR/nB9bec1xbzAs+Aj9H43Y6VJUj4TrjnNXfrrIy2Y/fHdKRlEQTM499LtjphdfTKCOZWPIBxksF+lfwC3N1lkjRx/AnklpbYXU7o4jxgacT4CieiQdHEprYaMohxPAnJUDRVeZhIMTs+TiL1ZUqnxNG+NPzVLftRatEgXNHuJ6QrzHuQrtU+jZomytXWsQpuUhIyqBICCTjPcTnHLYA6krs6a2eIV8GZZwyN38jfg20bc9lv0PPfzs9qI3/2Aev/DixCP5o32552HlcYz/DkkAOkWow7VU+E8+MxJ+apAzbwj/EsOGL0ZDyTgPstJ2mdY8RGOf7xuGqJssYO3v1qfp4RY1/06HoZqcUBUWVbM2O9w9SjhpJYkzpIOAW4LLOCB9KaQtdd3Wtzn1fCKNNQCM+srP4J40nZIt7iLw3jrhCCRsMxgooHuaP++tTh/eJrB2RUYfectucrINPme6fZ2oeikGxncEQBKfkyel7aAT29lSPJVPaieB4x6Ws0EORu7TL/Y/LlaIi0imlO8OCOnzjlD9uRfNEH6V7mBqmUVh7Gl/fDH9keoMOGokEvBD3PUNmSvq/3NoOD80D7rl2VxohP6BG+eECF5JlFF/QWzbeUjHItojQWZ5+NoyHh206uR9P4tt+g2Sld23JPvQGgZxW/Y2rztOlF/Y4fkvcuu2UvWR6Z/cwjoqQxJRmsFrn3bMI1fnpZcAR7JZgc6yCUMDjab6/Ix1M3o74UtmVJwgymdv3HemVmI0LpG0lgt4twBu2YJyAvUSYFHjTvGD1eww1DTGBI6RAMQSLm0SI+PV1xeJY9L7rZ3cJXF307IfDnXr8CbGACPSh96Bde6hFv//fFMD/6dHO8GdO3OteX7tTOUvA+vXZOlYFQYlqMJiJdNS4IJjL6zTZX3PtMNm5UXO5gthdEMWe57nB4w9NUJCrnAQodWM2h2Wcu4BOQLH5TGAhBsGvu05VXGR1R6++OptYGtJBOSgWOTE6yRWNFWg70x1PJwauNadnv0kYkIPtoj8uO1AoAuMlYP/b4+7vHYLRBVVo3R/XaE36myObPTEx1shGjrglqjYMbOMuxTYOvs2vAX4hN4pmcatLksNQwpubzRprRK6UTkN5yZAaCIjaNtjr//iwJJ/xkOD9TAqtrO6JUF8DhxSLB1e2JkWIcCALY6oarfV6v3Wi/IffRgGD04d1QJI/llHsJ6UP+Mdjxc2Ea6VmhI3dEX3uobrDxlzQOcRvYCZ3EHQZ7eb7UH6ZFujwTGsU6rr4Pxe/WyN0ZQSsAMoJznsLu5E9631WW78XwCe9kdcr6cx+N5mfr+hv4M6jG6k2JhnTXNlMev27B2utxiFYcrOsp1dTqR4hn8xUDMNpTxvWsadsGpn3yCTTQvThYW/lyH9dDs8FrPk0UddsdjQ7qY2qiY3sL9AQlJs7QI4dsTXOjTO3BXhS/g0GmU71PaMVVAsWYvlHuML8YohjboQx1FR7m6gDmeSL64cT/K+r95P8dgBDIGh96L57HWs2IBYQkw3/9c7B8Xy2SBEERm528V5CWAwDcRnpYa9syUXYf8qWgNFolhNTLJQL4u2veqD4xGJxDBtemLHGTNyut/qeVjpfFAvfds6FA++wLesHDOjx+X+0VT2HZ6FPjY1919VHT8IG5C2Oa4NFIiu0e44QDrb+BoICbGmrQgBD5KzAZQy5y3eRylSdk8EPEqD/TPU2UAdbKkTnpLtCeImiNFMZQCrlRMZNhg758mjf5ERi/BZRnCm/U3CNl0UiHrkmMBqcoaDOGD+qqZN1c2OiuMyuB/TUsBAXuUuliZSMETMqV7kZ9LYrmmzDooN2Pc2S0QdYIkfLG62mm2mv7EjqpKXTiivZVteqkLuKE7OLjsayltPDJmVZvhlCluGaau9yBmlWncOOt/+EZw0PUgfYikv2R79iTh3AnvpK2I/GY0tM6+/ZW8R1ihZ1jxrFcjuX8jq/87a3v61sKx6J2F6syAhdaZhAEVCitZdvS887slZZhWMFL8lzaIAXZJjdf7DlIh+Ap66RKvDcrg7YJyJh6jFbksP6vfJ46p6LaYi/3aECQLWCceYSFjlslI8f8eA+RIGf4ExII3zQkzFIHjnMI5z6bquM6VCC4E1yE3Lmn7ViZXv0K7aCML61xmmp1JR4z371cAnhxZp7ZeAy70Uy37rf+17vthLysQTjOMCDWqid69c1JuNtXr+hgTbjprAx6KdX/AfJNr/WbEexiokr4fVqau+sUBNxdPHU6Mx0rCA+uDeoBt+3vbLuZiRMxRvZGSYaxTbsyBhiAxJ9C6qQiOyBuVb/2IMYEdkn9jSASq1nGU1st0tzJMnyyiYviUrVfDOIrZyM9JEiWZvQIS/NMBrotSLK1kc9sP3l7/hhMAv7VdcrLrSNCPOSa6omIkXfajEM7zw0ansZSwa3VyyvfulwvdY27VchOz4eJP/+sp2szp+mjCS9y1HMx+tPs54Q58DlGpgHF0/WXLdnxNpwQlsONhOJY+weTy6AFZWQOhXccGa2GtWa1g4GcsnzvCQQMIS+tzwbRsJ9Sw2b66JtgUGc8EhD7qGZcqlxMg+XHi8sozF1/AxRo2E5wUn9qh/MIM2M4Oh/WZmcwhUie6r+ECOwyl0cERCWb7wj9oQLAMGhuc6JqfJUFgaBVoPJc5lCmpA4Nmj3x8Ax3smA/VQBNR6CcqcL7ybKJMXDWkKjj1iuSpCmmrc/K5YlrlNfAob5mHAK3er+oSatZC/Qfvpfm9T9+/fo1/XNSdi6kdiF8reWwDxPHzFk5xrKqQfIjBVXEjTVZ/1lVAYZzFs1wmW9v/5latBhchPfSAZlz3eV71HQeVbH0/TrchkJvye73ZY24tMG3lxr16x//AHljwAzOGxtYpG3ccPyMZPKjnEBjmuU2q7m6cWSZvyeqAR8IEPG1MUlIFrNgPcJC52OApGGr94dmN7eJ5crSsNI1kW3asF2E7gEEzrL1KXEaiujGTKOKWtWxre3yFjwCnnFRNMLRzMtiPuanoxUdCAyIGuB514NHZQe7XCpo41qv5v3Wku0ijFR61t/Y+zf8+tUUTka1z/aKp5M3IljoLkxz6+CMW6MxfinCZuTq945KKGstOjT1DGacGwNp+Eetn6RhrTtZFPMqQlYkL1ITr/mAZIUL7EX1WHY0dw1lf04J8fl27phX8o+tKqxpKFAMkN2F0/c6WsLuPOXZiSCzWkRpDRfrvH3E0F/30o16aRsPuFe5Y6dkr5cD+fx3Zu7w0LCNf0gHTuHxfswNtT4WDBVl4yWpnjqUuUTxFNa6JEsTHHQbm5lWGUOk9LJWib57J/AaoegYu5bSVwcm5N7ulMgVmi8ijmFoVThI673vgJeDoqEwaLgHHqEibukEutwPH3q6kkUNxo/K3iw1PD0ybGgIU1bifyGMjA4ueWA5KTjp14CKgvNDZlkxiNsQgHOZqLUYDEQ/v1ZqvEAhhrYh5OhQ8nt8paQkXVPvp7OX9w5HyGSsfxuTsa6lnRnM/izN1og3x5TMZOscvNF9c8085LAF1HvsnjHppFCxK/bT1MvqJrR4KKlJf4U3SDAFcXiNXyf8EsKKji+rggzSVI5ufwnK5DWsR+YAJQ3RrnmzpIdGEDQSf2QiWaWosRzTDXTiVTuq/3Ho/mqzBzusK8lP9qZEahTDtAfiRIb+yHYE/kK5dPQFESNDlz89aWSu1/WkQozp16pSGDJSlTn9vMDEtNoEv4/c5UbQvNVOBg+uG1ESzE5YRYCho2aiZBgYpQlM4uLWh8pHoAP23DBT1Ayz6f/bcIizzqSKBzgzgbFS5LL52dV/OxUes2RvlGUbrj42OlFwjNhRX6CGxtZX6rJY0EG/rUG0zPwNwe3PJnmFBF4H8oeCMzzG8tHOoyOf+jiTesTcsHBey0m5mBWMXj1x/F0vqCbbP+oZKQZrqeR9eLWmmsX723orbpuPUDBnNZprTPdwG6PyUcSNqXntVRkkF3BKMsbdngefX5Ob3Urf2NcjhQ34mANRh6XAWgtRkqWFSPUMhMbEYxnV359Q728pqlWtk4k8AzXF8ELRQCBf8y3Xi2wFE65XRnIIUmS2VLsGSOdMXrzXre/nrfvWuPy54FUoMCf2dBVWeGGDAlo+DsK4Xfops8UPCius+KTo3yMbJVpPg7NgCFDECbRGqJu3/fKeggRsJcJc8EI0Yp4lRrYTv3VjrRPZXoGujYkQEyALZZtEkWq7BRgRtsJWMUOsQu8sy0YD9Ie4T1m5e7aOLpu64GkyaNLzUMfi1KKsW3E12tPi/yEWal8QnQOGxa9YXD0ullZzL/hiWBYQgnUAG2Z0J+uJCbQyvHvBXoQerIdgl9540ry395Uhu82Rru5dyoMcf9JvVVTAtXORipBWTf8EdGVeuWg6sjEaP2CjVRrhkBEmCWJsBJoKNpmP88XRmlKlMbv/IP3bt8muB4mLi513F+YsRxUTbcjUvb1Z3PvgmJtQxTlga48MPKPx7/RWR7KqykqAldai5RoE/ICRaetXt/TZLIoTyyk5op4aQ7XbuiBo7WPef8kWAA/vY3dF8zaUgUj5YOGECqZrvX3RM/QnBifPSelCwU8RC5RHbTaqAAN8BZ9Z9bifxcaMV9WwtnjibhdcaFi3aN+KHKncYOleKxH4YusMl+pbYbbaguA9YmKSvaZzjjZMPokqBSzRxy2iCIXmeE4YHw6T+z2qjkQJ5PUjvKD3OmOueuRCroA3JP07IAIAwIG9lMEFkxqOkogZMWPZGi1crb0ca3EyRsdOZo2rJ4ItpXJSnX5gUq0I+y/uprctLWjDYF3SLH0CM5BCwaOhX4lvWQwQb1mutwB/qSTUOI7Tlk/5ssQUV8LlkLS3G6JOv6dbj6M3fbRFIrB2nR3b123J5Yk8o7qu3chgyhmX+x7wxg9oTuJfYqc2A0h9bLBL6NrcDD7NjA551bz3avguVrGNrXFKJrPrRy4Nl1KxM7KS4w2gpTZ0ncyoSTpHL5FV952Ifn8Fz4kjer1xCDvEx5aSKcuTCL6XULM27AQmbfBylXPwuVDKAxU4zDz9N+aG+cFoWJq1EYpNqIp9pOAdtnyN5GoifiB2xyqL7uGb8yNKooX9V+NdsPGDjCuGkVqJlEFkoeIUh94oAAHnQxxJlDi5rMJG9VeBVwaGqWW6TkoJtBHS/XG/icQf9tMRT5C8M7B9LoAUQ8OqlRIotCkA7ztCt/2CJFo54XwBrJvlRpJm+6fjcytTE335p/4wFsh6SHmS2rqTJksDVKmlwgg/YXv7/y6caoUCFLqkRiAi5N8aYBvpX1Ft1UhGZpRrrehbvPdpb+SsJYGNjA0bmazsvY1RN1pXdyLeRL18iMeeS6bQ26Xpdle0v6VjZd4hS9and4nn70SlWwlH8hzgyDjWtz+2O6kr5QwA+QQ9TVGn322xwELGQZvtMiDBYu3pkvxFIvTGz8ocVPuU+7s2By8DWEIGGYeCc6GmZ3VL7EwtFqwIti3aAMe0eUVIQOLr2WEOToZ01t+xIABKSX0IgDl6S3aGoa6wTAPa9kfSN+zJG+BV2kPSw1nGZfdS+yurI5yyBw8jsKhClmkCEXHsM1QwsVpGZzlH/AwEBkuoJtO4wUJ3QlsRs8E0fYT9kcvXz5+Pnf+hyyK6W/eDafq8YvdgfZWbUbKh1PCt/dC1jN3C0cntMQMVbIyEv4JqzufxDXFQHlzCv1299ySXRi+DigGYhp5/ZRo5UZ+2iHN7VHqO4oinVLHlf0/2kNNfXgAyjSkBhPXCpVkdrJOlLSrbjiyJAedggNFLAWIoFgnOmwRBkIkjgUT2Zk/jjNwntrelb1clGIeZVGURH2ExDBTiFnBTJk7SmhqMtL+STmoaoHTJN/rgyc4Edu/KldmX8lHqKYxw45en/nRuSs88gdsu4Yd0hSu6XSAhAyFZOdR3/PDsB103s2QhjM80THtWUEHDrxv1braiW2oECV5ajac3MfSL5AkaCgcD0WSMWi5lfZvFU6ROeKqSc6QDJF0GumT/i9Dh/eN1iUBstr+mMlvfC1UeI5JOdSCK57pz3C/hWhZ/ImhCwLaleUVpYsEtnDNEGbNmTSOERa63LjB1XWOyYIO2gpudaGAgDpyB4iJb7MIyVn/33OScQYSM3q3/o0d8dJFJpoSe43n+Cwlv7BLuxr8VA3zLKpHB62MwCfaYWoYvHjl7SBYluFykAfTvXe64rct/bGx7PmBwaj+LYIFelLdf19pztq+D6xQx5SfQ9jWS44rU2qXc9F0fUEvzNy4t7DbvyH890UULkOdLLbRdh0nZ0IkJ4hnBoAFDG1bs4RvCzkQdBvAPpWZHVE/QIvvXgcCDEnspI3XlrN0wWbWl2RuKjcUS2etaFxl6gPH2kC4naM4jQ0FwdAltIwf9AkTyYoRjh7Q2GW0DEOsN8tNtEEC8tX6XDD9xSdAte9saC/cGAZbGBCCn2m/x7HiO26eb5yDiuh5QCwbC5Qll9q2c8kJ1OspNw+fWBLfj0EjkyvrdjhPvjCtYWNRnFG8IguWbMeenB5hsD89SDZIGyMJ7PgXTw90Zzi5bTKax/O3H7YD/wj/qOrJmUi63xfncVhHDziYV8uNoXOcgSm5iHDohMdh5RjhuipUTEyjFNGfTW6adVY2w7hmnlAeMJQDo3TlHl0qLNxsagTM/jLHthihzAub0MEdQ55rAC2qgfZ2Gt1J58YgBx9ndnfqbtLSbHkj5hcgdhOWhnCoE+P85Ep0/6PH70b1cOAjEzZLdkxPrGNc5uMOD6vTsh48f2O9DjfZz9HeygU9AFkC+9TtkGyLXgJdKUx8mGC29THUnVfeUGmgyqXfCDTDGrHr1k1/wUpzB7c7oXs8jQX+foarwAkLvoa3vDbPNWsvFjb+IothQlMHgNNdAEuwyGAZnR4JkUIdPXvy/EepagvaEfCLbeQnX6TZdhAVud+HarCpTdV9SpMaCZtUPA1/Hr95yz81sQeByi5Q4wQizp9uzmldjwxx7Ih5HwFaplNPVFo/OT98p5o50KBo8BSZjz3rF+XZTZiG616CGwiHqofLkfCZjvC4dk1850UebPK4eQR2rxMWFpkhHtHQcG2DfaevTp+PgqVs8GvX+0TMzNobsCQZ4iM04jxt9DDF7x8sbOKPCkdS6d1G5qw/P/m0urqRxRgM32GD2HOeXRAfOfN5ZWiYaM9h53PnttJH4oXTwMQlRZY9XeTikqYjr2SY4kxW80Ms8fR7e3Fsc1J5mduKkuGVolu/YvkKkaaVeUBpnzyc1oOvi+lZOyvg1/VpHIVo2A7hTabcGg6Gm/Kr5LQmupsFPBAeWHyxjIoq6y+3lUreG/20GK+TBdufFSqr9qo+/cHBW5pknBoOVJJowZuGCJ2AA8aesSHtm8vaGd54Ka2KAN0p3hCgAvGV9CcuTCZs6VelR0dcTb3PxIvcoaMyUoLDOhr0m1gHnW8Sihug4bD9/aeOJyhw9KZ30ykOjxve/Ua09yslKxoHYAD0sjOa4T4qsy+1+V20bSafoMET6LpRj6SACdLqK4nfUT88/IymPvlc6MtsGmZvnLP01U9EEuT7npeXYPN3j/ZCjPM5sxDvqDMp6R7pb5pL4v6SwYt8+/AMVISjfowQHTw88lZx8xSGuxyL7q//cv5Gvgv719eotW9T2ZFELae5tlEMSTYI4jn1wY8IdE6UWwImAHxlpXN9Gu87LfuvDnUwLKFqaNw0lKEjH6WIu25fhjjaq3Zml848/2cmQUlSpNaHlbeg7w9YEC9mt0oq3M73tDndyc+WSVtnpej6oRaafuOAKQxQhI1nGefEgYv+u8RgIkGiuemnUODUX98PM7zOYq8HFv609epyKf/UPq1KouemxDSwDzD7ubA6mrzoo8C7kDA3peg4+otIOw5EVh5j9jq5mfHUe//DWHIcT2DJrTP72JFvVFkkO+N1+6NzRv2QsrwzQDwAh2dVkvqHyrPx9xIJZBGt/owpjz2DV/j45ttLtec8AJn/y7nVOn+Kffs8nj2sbPORajUtBh32W5M79utjMvK5WMU20EgbviA04iu+n84oactPPPhX2JhAa+iz/ZMUw2UPikCFIJG8xAoZjcwUWLJ1mr14wZKzujzG3GhFVUDxi/TcCKYYUhWSP+44bUUrKVVwrCI6iQc+f+VnRJJg+iIbf0ZavaYwQ8KGIEWAULyG+TGytzXy+H49KKPgcAP8h03kAnGVPdNiqqh4s2epMBzNs/SB1qjKxob0hVvIELRsC4s6wHwLMeta2aeYh2JcJge3Y9+N2IMPBiAnR1hAkDaLnU/KSuxNMakjHhvX8VGEAm2CZ81EXQPVWTvmv4WUWPP2s3IVex6LNW0ndbVnpAsonNhnxELFVf7cO5uXuQ7Q9VRyE3rVhkJW5f52VDDg5MvFW8dHNwv5XAFl8PPgfl8n0eaju5iYRGeRUWtilw2AU7w16RaBinU8fTJnX0FAxcXfwjjRoxWA3o7CCx5xN3592rvtCrzWEvDLvRHBkgP/B/ZgqU8ubLziY+CPSHWVsw7rMsOY+YN3aIrKkUkgxz/0g+Ih5haKZ+dRuaHyH5iq0+pfmy3Ej/uprwxtmW4TSMx9480wN5Ox8IVBHBy7I0NRfDalUd555kSheXhNSId7K7XFIXNcTpz8c4vu5N+uQeP+zGf5pV0PSgNaQoWMFX7uOr3oVrRhGl7IsADlSCvMm1JnTPGU+fltHMwPjs4ke96j2MzMw8NoEa3Gu4Kbg/3NjxP+Dp4mfkpr7tohvomnSuJZ87Bduq+lZfrsWf71LTYBqV17WXkNUtR0diACVNuaUilIpwHbF9/IyjzMnnihowe0mLXvRHnoCrV9vq0ALEABJcAAAKUK9vDk751hMONQh6VO9nrkAJ+bXO7+0beIfo50z1pBk5KBXCfCmzfsSDJlwlz647jccXTuddyYAQud4CgUXMcma+dnK5/gYef/O8Vir7ISWGgB1/Fchby110CpE34sRjntnsvaDiDIX/mGrJ/mIwO5whzJcJLM1laAASTXn/6DSiuKgrJ+2byJbsHzHgh3JA+jsz/z/p6JWG7QMAZvfpIgxBUXDra8jjZdZcG6oQx682Z0wiFfl3aig1vpsl18kbbsGpCP+SczYLICugwgPNBvbA9IXESmUn68QGpH3W5jcXkG52h+9n37sL6x3t2D2ftfzzGImK0iE9vkVTmhrH/vtr0IHEAXzp0NliHlULDO0yPfm+K8rRAP2uajmj8I2rdsoK39VPqkxmn4x97v0sAFQ+RlNt2PZb0v4X7gFpZHfJvM7mhcBnOpkzITUP61QSLSoPq27Edvqor/K2dkgjXukHbsaibsOMlE++oXarZlG3yrm81B/I/O0OtWugPgcBihEjHmBQiGGHNVoHS9viwanibd2NaTq+FS47afvQB2y6zj56jfPA+6oN0u9Y8TdozwHYBJ5ePdgCZGf9MmkJ6ZqgA8lEAcXK6+YdxRyu7JPG8yOVHp+fQhuS+LcLtTO13GfanLi/S4lOm4MTrp/SRPW818DhNY7CjvNkNwJQm4pNb69cNePD9S3ig2AEbov5jtbruEVoRu91zsYzUuiPDFjuj9jsTVd8zJGcWvFsrKWU1Theqf6QqGEXCn6HAN8NyWQblQGzdfmNnxR7OG2BPWZsXObt4FkmTUaWVrtT9bRzp0mOjclLjpkggvQbkriEbGRbqBX3HbgD7RZVy1gZSgEG87M9JtZeUtHyu32fRApOfOQ+/kKVOG53joE3JX8qJKY6KwsML+x57jF0p/EGD9UOP6xs1hn0ndtm1/jzltsBZ9P4zCn4uB2MMOAAAGfKAAASMSCgfWLe0eB33kxMIVW9ffUsiji30oD0Y3In11f9ci1EuHFbqlYBPhF482pT5ODH+vahyFMLw2VCnOAFq+lV7RCN1J0PrUHYh4gJBdaz1wWC46dcH69ZE7ofcKuSCKu3WPxE8cLtXCN0xTNzS8qpUw+M7Gxc0fh2fB1nn/FPa84huEVwZvOWKA1Ix3SVU6EP9m7F2FactFi9LQCVzAiJgvFtcJAdehhxnBWYiNWYr3d2FEhWZh+uyycuvNTfkhJIe7NR7AdvUPAw4lDKgoPNocDYJnXSySF1lFzpf6kDJxz2cWUCXdBGDhKtU04+o5QyiuTPctbbb2Iy4wso/b5eilCT36F+kPaReNR+BRZcsOkWN5GWKkm7WbSgz2rR67eCS2dxkSKNLC48J7mdB3riQloH23w2UlFnmn6ypr0rVNgCG3YYHE0X4QRl22LYLlzTiitY0S9V1bQE1tNsu0AOMXzsW12P6EL69Ze1BBbokyQL8u9PTIP1A7Rief3V9cGvKCGNcXdUGtQePw7QAlHkVi9rus9U2ioP1ykD08r6CndXP6+t7i4ORf93SfoTkhl3bFPUsgEQJ9KJUAwjHlENiQSpyyxZgoUae/hqF8XiFE3Q+jYxMynUjWb+vozMHQ+73SRjHP2Bvw5XzCIYGx4VP39Wctbg4yYDv2zQoWD3nmarfHeE2tI+R02z2OT9hJfNkFfEvQF42CgzjwT9CFXl6VCATyDYd342URfrjVUtmm0pzDv0O4VB87oaBa29vshpdqttOcCYty50sGgA5+KS3R0CSdoP4vENb0MdlyizXAyCMnVCwDvayChFkiTpOk3OsqxbbBMSRvpNxg7bLqQEp34re1W96+JkJtKiOSeAMBgxvvRzh7Xq3N+9oDdJIpXdrv/vtaUMXFEpsw6gDOTWFeVzSmoAKpvVUp7FpDOia325+fSKpBMHj1/WMGmpVF/WlVuRrzYKisVwgvNsgmQboCxshlArb14zaPhfMycrKOIGGAV1VzK1mVaH+/cCdZEk0eQeb5Jhqlc+1HEd+BVNJN1aVytD3zlFezcC0vfEOtcV8s4NMD/qJd+DW7vWP5BEK3VkkPcplcH9kXo4dasRiXHELZbK2vaKiRh8u0dWPUFlHguNxl+w/NUcXyXR11F1lh/MrVq+veZcxTc6D237yztUdGm+skC1Uz5+5I0yVoqbr+FBkNnWZphU8snpcL92wTiglTo11aaGuoUbMxNSFJoyofc+1gp+gA0VMCHzW+D8yq6K2I/8tpF3xp9XHC1wwc7FUY919ir10q6DBypdBzCXKj+2iaAAAKD4ABlEIydde9cQf2BQZCJHEbf49o5VcvBKWQPijs8xSh6r01wEJGzB+Q7dP89VqMXjrDjtr0q1Erz0EPsw6UhlgsBXx2X0eUREqELSZ0uBJyvEcIfZ6x/3i/jJ0672/yoAzgE9AzWO4HzRmEpp0RuEeJsw3wjw1CUNkvrPVKEwACGh0n61ITeNOdXqX1bT+oHisAS6S1IOidkA1f++CUusH5ZH3EU/3eQABZ3gtkrU0r1pVioU1MePu1pzWQQm6ws1Bpj4zNO2NAeYmRQa+wJ/Xk6AjU9KQj0oj4EQQsEf/9myR2w6MUn+Qun5KGJfjmHhvY5c6OqZAklRvE3+mZyDT719Re+ypU9i0TvNgsXGdoJX5k0RZXYdCUld8vSCdyIRjktts3nq5NQGkmR/GyLc7YBwa6pGItU4R+Az8ZJZfp389Z9Y0uAaoVolWnI1guzdvEUenPM38AxbvMw47W31IIJrWQicDMNqzGcud1aadpki6VLQKIHuXDg7yam/MtSH4f3XrJ4Hh3+qFNF0OGYYqs/yaIy3THEbqdgWYckyz1kPxu2MY1GG2SlErVhRSh/tWlL9rjw7fugJ6FniQsYWdjdpA3woOvKFPKKGBII8xE48os3dQaBU/FnulkqROwTQLrHASDHTlUVbvzpdh+8vJzeoNbXIn4QBh+Qv9UxDNZzgW237F2F2dY2SLCCguorEi5nOEEqdjr0I1aVSXOZW4x4UDKa7msCi+rwb3LK6czyq1a8IFBcYFdsMy3TU0KS8KPrrZn3PO1e7RueJhb7uVS+lPweKq9MfCGUoUVSz177OMt+5NOuf+bDisIwyBqCFle0QplmRAbxyL3YOQalFqgpd3zO810r0kthZ7V2mJk9bL4E6SPgm5B3uEZ+JeMTyQGWh8AaKTXv3um8O5J4P13SW0yyZxIGQ5wk0eOq8mHENmo0rG5awP6A2IwKa5yb2Q/kubc1R7GeqhXFPXWSf3ISykHpo5/BXmBwhWtD6D3GccyypqKqY5XyeHdh+eO8rHsYs+S/yZ8N8pFPsqgVWYr9RdpQJdjuOcab5UzWyZ4c+NAKdhzz5t0tYOHRgX20H7aJBIyGvTAK8DBN/YTwL9x8yWGAXElvkr5GZEXeB93+evH7uHjKIll3gID/5mRmJC+LNlFudFtwL6G9UbpQhpt7PQoZxMecdMzz2bNmBGGEKfI8T46BAEyyK2+5CDY/6w/LJLS5ynOol1wg6H+gBhoSxCRdBplSRHa9tP3Jj76iTZhng5gbZOP3z6+r86edPLsz9RWUbX6FgpXJFBu4qDK9QJYtR57GroEZ4F8gf44IVpSP3u0tYCzBu+WXa06o9DCkGLwA985tZamBRf9MCt54pGt1MJZZ7Ok0E5BRDtqhzD/zuC1cwBz/fPYXSPawBB4HE92UwVn+UTUO+u6sEluEKVqLfK/f5E9kGyI4WgnqXezACJoIlnyXwlCy6HmHRd0qVhOvNVdxlF/tBFwEI77tigTNTQokX0em/KH8nP8ndW8ZYukzCdE33C2pL6hqQYQg6O/gkbwVwQMpbjORO4Pu3a3f0Z0fIXgQHdfSo1PIHU+Ed7sp6EKesC6ujiXG+bEyqU1Oi1fXJ1B4icEFeBWQICESqkmz4mcaucyIEW7ICR5YuhU+y1mWBZHcplCTpqUiyXeQyTB+X++JzY/kEAHh1johnNhQNZ8ZOY0zMnitY0PriNPaXOCPGQ1D1iS0vmLWktAxriGS3mSFvHcJwOGyfbAiag1CftXW8l8aO9DKYanTt9aKpm7L91T+DHv1xeI5UV8BZ5vtYD1sklBvcEdJeX3gyP1xaPwS1Z8ktwgZXa7Hq79oduhYgbps8hrLZkD1L5PTR6bc0Km4oOOa0KZQUo8U8PBy0GI8OC3aUOMskds2fbh5FPAZflS4KYLFbrEWP+sul7DSqRYilU91jqlNJKyDG/BEFMCLo3v1TppPZKz++jBbChYnfeJu9/Qo81xRAoLsXVks/XiR2rdeOyOViZ4Qj2pCbFfYpmmNMCC2AOvEaFEfUov7lKB8wwKklvFyfZACdl/zzl9EbMWYub+JFeKZkU2gn4Mu6wNdFbe5gtvpN39641h0sZ80RH68VH+yWXlbYj8LGcPHVeDOTP51iCdeIecFxfHxf0o8mD6UK6wnI9t+HPjCHcqyK17BKh0u1oLwutJt1uejp/pz7EYMsAqDDvH4neMdxPZAjiNrzcB2tnGmDvL2Z6RacdRQ1UBfOb2iEZTUC009bQjMW0H3KpS0dMB8Jx2VLC8EZIzsoBSoJjy8e5qmMKGokTpVGLRskXR2s6N6SQ+ZO2icTPXNylllthq3MOKignq4CdXkpQKTSPDDciD0hOzIVD4tou4O5a5rJddxvw+BWHrDhGS3Pr4LMGDd630KTAY26pzk/BgTZiodQupP6Gn/tS4zls2Zc9EPGS/RC57b0/ZlIHGltLm5mDcG+pbdK8Ak9QVi6w0vTuBxkc1ROgkkKwd+AYPgO7R1HPvhWqZUnFa559tQz91Y9cBPtc6IqK6sY5BtqWdI2YLEh5x6oGqLZBNICL4mVZBVxNB3JOMqQhDN5Ho1ac+pcAVeSPPG9WSmD8+EQ3cN7SbUbCI/ujMBQDpbe+KXu1ve8NNsGG8GFFusV07GuagRkpH1a3cLhshqWYaGMGY42cMK7xWWeYg2seeZW+gJzSVSHbgAURw83m9y7DzGSThrZRHqPVCO64XYg9//SgKzmkfOhiJaTUZuLMGrGn7i4MiA6JKl4x8eLqD3qLd2nsJ2IT0MeoNMqHRCUEY3OFjSa59gc20neFpxNC5p8oOC1bt9y7D4XK50rlDnPhrFUbu+RuGC0dYDKJPvENLi0J21GdzZYTOhHefC4/i3kBr/f3Z5DZOG6UDazkXDd0gzkr6TMrKO+fwdwFCmLoNNq2Vt98gOnwSj+w3ayRbknksFYF3BDl4+FmFKH9FsSV3v3dLmrVnhBdte4+/F8lGLXylxUk6q0uHuwmdcqY9Bz/AxZxduTvXJorV7yV8aiAKJbT3O95tYhRX8HrnxZw5khV2E0LgtemSpPEFiJEUp30e9J6ZnNyUWHlij0wwlxbn3dXmXgba+O2u3jR+PsrxEAWw/u7fsrcMOqfYK2ma7onRZi3/Bge+91e89NerscyZSYVKayrQuBzTX/EyYOxQ+QrxbrgCmYHZ6L+tSm53U7ZiO8/XAcWjApkYz1EtXUmRaN62+O4x8H5QQve6LyCxamLnTU50RN+2uy2NLLGSgAwbsF5nP72T8+SBoDJ1poFdmGhkyol0Xquv09ouIYgDSW80nBkOmMPYSFNXY5tEkjQ/EsqLxAgNSi1RExYrupgbbiv/XJimBpjqBpZAn7Vs9c7XZzfEJ+bm/nOzBLltJTFHKg9m+p97dniR8AENQ2MM6i91JrmZD6mnIgzwegeUMa//BkgjMBBJkFtruaztAhm4Q3+8BzszRwCUNPJnFc9TmbyjpaA84DHskjvCSAMlUCnfgnYpPfreLDREGFJjXFGtA+n49dcjffyPF9oEQNSlEPL35Iaowunap8/kYGduv8jW+Kjb6BE5fBvNHlf+8UbFOLu9pEdk42schzAFXJN0rcLZ9MBa7l/WidUNCbNDZfCy7gxbiuAZDgIX7HsVTTgncw3+aiuJLU/090yeeqPU3Cod7WzKcZH7aNhU4Dca/DUyu7oXz/hM3x3i7tgQY6Ij5vMUW8BPzZdR377eZnIygb/UpmF3xHg5mBW55/CSotcPSwgVIf3VKnF+uYDMiqtO04aZOJowWIHW9R6CNrMZw0upWLxiKvRpMPSvIrdp/k/R0lT92mY/cK9gRPJ7idFeT+U/JHkiZLieHxgQltyPH88KvpOdJrv3IRk6JuzneOUrqA/2Tqo+0huletIZV7FArc1bxgXPCrD4ZxSaqgJGShJzoZU+GrmSMsxkPnNkbK+z19J4csmVHS36++SG7N+KCsywong8OKXbFL5hACuc1rarOmqyuhiqzUgpauJHne+9vug44IYVEaOWFrdmG2/2vZYQ8hF0XZJYAwBuB2PC9JSM+ZX6ixMk/G6aZO2OlhzKNutUrmuxWEnC/X1B+cjhsU4JNmmEAhoSI6GtULie1tbiS/L06mWmzXTi4lcjIn8k76ovAfS14OSVB2GZGgcb028uFaj37m61u7dmn4oaRYNTvk3dm9/NSBoFDMZ/SxV5h34rg51XKt1ztXTXl+6V5/urcb23Xq26N+lQZR6WcDXkWeLWV0t7Q0k1YSzrjufJi27JdqF923skYf+nDGKo/Kld+BSIz32u8n8eha9e9L3M0U8IV8yNyMYGpwTem0gl8pTRzlZcLMr1jDSOt6uPb2b7v1n5htL56ur6j67Fctii6s64Q0Pi4pZgX7jcH3eW66RXNMs6ma5FX4l3mmvCOi/cWZ7cbZlQQO/XCruXV8tyJ1KCMTnICu1zbJRBqdFQlB/SeSTbeg/IQzwVXz7vHaxSG4b81AIK1sXt7l8oINkVDI61GsIe97pAU3feCSUMWxVzB/YX/pF+LhKf8Ngo0KHcya6V7tfdbyBPzGfNlLeTKk00zV9SuLHIsaZhYFWPDZ4QzqzCmY3eS0JxULM+49F636TuKV4IWyuH8oHHi8Hclvu9p//glMmniPYYiv0DkyovNh0QDgCd2r7+m7E8QwB7u6UgwvuDHfbNR5lwXcntPpVxhmj6WXtM8AWoVBroT9FY2oXTOQSq0eEirQQpnScQEmJXdMDsK34Fgh6V4qyfAUs2rgSqO2NkvxzG1KQxldgkkeSeKipH7xsqSWn7upc/oFGqbxj0ZCmM8FvDiIKBfk9pcT2c2N5Z3/LMvx2grT+tCdWRZZIrj/Wof0NlBR26mBS7SQPw5+mVcyEcWL3Bogn3+dcB3ZcNc41nJ12FIANs2tDdsWV/LF3qL/gnPQYLaoULdbDETR3NQWIwUNTC80R8MouW0JaWM5O/LePaN9rJ2P61LZPMBXgbu1PKckB52RAG0FFAQzGMPX+ow/G8BJ3DiZ+q8UvjEUUfEw/NLEzz3RA2hRDu2c9z5bD5v/cIHDFStHxAjVK7BaQU8w3avyYLDxuGl0HKdX+VtpigES5ocwvCkDhq6rrXdhrSIarewUIl2N99w5gXPXDw46Mg1u4HajENLpFzyluKEJ6VhTZ6Kyqa+q9whT3guEBtFUzUaHYqT2Wjy4fdTI38oO/wKf1iJu67wSMGwmGqXap0NtBo4fiwOPIwLpARxGhqpVZpMn+5cxrqHmh5Oj5z+6pPBgisKZMNmq6VGh3SWyGK+JqlECnJ3i4nFkLK9XkA8AOd/0gWtIq0hfbIXP4kVTU8mZMQ+tzBrBKUZlCRGc0kGGHHM1X5tyJt8e3+aQa1NKnHQ2pkVmOLujO2doQyIC0SEZ0OLMEu4kK9LaEDWgkmMwlF+QdnUTJUgtOXqOir3GiQUFekyBTxpij6Lgub1aZajv5WjvU0hvoFAxx3ntx3yyCVx6OW7hOniT+03pa156poqYfATn0YnbEAhWLGzTZmDtSzFV4Y7Vp7CLFiYQsubmDJuJFRtfi5baotSZ0bfKM3BxeJ2+On2dNSL7oIBZ52pn/k7+SV+SOinSQ2Uk786Wr0hJbX5wxjFsSpkGG+V/CZYnRnkVKPyaFjozXKzLX1z/u8QOc3IegGfuMneQLlNnnca/td2idBA4Cl7ce1qEAe3t/hWd3Heaydfe0x+7DzLW4NR/BkH8e+8hbO7oolGSIr+MjBOY1H57y1RGl0q5UJu/WjtmINk21SJyNFxiEMH2LboGxfpXOcI2AR0RUpXwZh+mtEOdl1uvCNRnFh4aJRh4TvmnXjIleuQSV2aCpy96/nLl2tpC5mGBVSfxbWTT6ISSNzG6DfA7xDCmmcWZ/GRUNkd+XYa7W/qnVFzMCfEGm9WBnRofv0KDaaJnNrQiJQ672kmJoQ/VNX07XnGgbTV4WdFpxIHjEly7dbz/RAPclvI7zpNMgws9veTiFJABqBF1pZsVDe4uT4ruaHfIWED/xWooLiv+Tq/D2q/rCpXt4vIY2aXK8ze4prX2ZjhbtdEx9p8ZIhd0ryihZ0YbLztzhRdJ4qY6bAr4O7NwyCTXLAmLgtZvNzzwjbB5UR+W6ssXkyUgFZxG57XPologSFvrC9yMZbuPmxxlHvvy/aXxZ1rKPyFvgEK5pRfr6BrR/NE2bctysUxdG+X6r/6YdH80FU6Fgd6p6sCCTxF6noBS10ruqnsx1nXXXqw3xFGk9IUKDtiCEPd/ywxDyfHL2RfOVKVbZKWSw3F2SwbmGwvFkDyYEI+7M+hOzNyH2apAYjgJvmHZQ9adZKfi/UYw7+tYAvuUX8QuYrrnzrBZypZsFm1olIi6SNNXbDNOjYm01WFlEOdfFu3Nk5O+arG2nqA58fZnNcbSW8QIdUz0pUtAuO/PAmYXvxui5TGRHOxHZM0k7hUOS1w/XiC2JMXMMjYlWk57hf/jlVywgojkFQ/hSt2Fv/Ve3kYYg3TmGedZigeAjpA+XetV6DubeIj/6V2EULGurGRUqjD5jTpiY5JEhTYLjagUZyQWBD26Y5LN92UsdzixBc0ZKFJLU2iyKDmullCyowW7Wn8PcvlcaPpNuRbRfiHC365eTcT11YLJMH99FklFysy3XDG9DTRf6IfG4HYCIEwD58odkglRc0Fq9nbHXc5lFhfftAXQ9InoJjOzACHd0ao/WCz0lzMhxBkkcd3olETcnc0DaViT8vCLAtRGHCtnYSXzR7EMihqMJ43blIg8ySoPF15TxpwrZYjcPl0ciHwl/u6Nq9lHzhkGyp6IzmbxQypCJGk/H8VsR6A3YDAumldxrCv3bzamFXVdqDGDLA/q7lrYjWDsKsO//0j8NFDV+noCefqa4jpm/D+Hq6eX8B3EsWF3uir4jSKbQusOSmfUVYje9qLS1DDl7hmg4E5miDTzmRTt8M8CpxvJ86BK2CNdC+A/xA1zCaMQ8rmmhZX03z+SrGWBhAYuF5YHY2CWh0TeI1WDpryNiNyInfx2xpciWSeqE4l3GpfFWOGaZq0sRazeJd2W9TEDsZZVS3sOkhbtOmEgl/4TFshdtDJk4Kei3BHd3Ce7OHgPjKPjqzNyzOIlH5+P2r2191QelmOg0oyJwaEtCKCpgx0xpmF1mavBFzh8tpGEkJfZcxqJ46ATrN/6MKLjiLnd3CLPzNJALag3U9qCvoU5NL1npShZM71ZK2DTSAnlavPfGOPglahQm/ALHQKcQ5MiCOIRIlq764WGC88BBLLYZOnapTHhjSI7k4kSCuMmI9R30oy5IE1+LyRAccL4jDeAtQ1tsIM4fZTuPCOZqzoxUaC71ctsIhydY9RUoDGn/cM3NZ1TagO52kzSe1PrJPT1TsVjnFH23AUjUDG6/vP6ZcEVMbf8nGk/6kFPdwZOvHmHHcOsHn69UNGKzhAtIYShuQ0yfvmrgruPKrblfEc8m93hvJiZmgw3EwdeY1b1eeeJhnIkGH6CPQ6NdmFK4WOkIdIeO6u8jnLeq0mD48htNkDL16kpVk7ozg8cbFgmprPmT/KokF8eDV8UWQUVrFp6f3dqeAd/KNAeQ8IBnKmsjKMkcC/nYwoYx8p/d1yzTWnrIcray6FycbDGzHANl03tbBBn6vAGSbG1ZDV3OWAhG7rVT3B90RODug9imBMiJ8LxWWz9ZuaX86BxEAC45qoLOumcaS8SbBVgHCCPVDBNxYyQUYYu1qNnmpfNKtcGzq40c2H52ki0TIDqxCAZfpMBXXt2Vk+oYFy+qrZVcszQijG1O6CUHlSQwa0iFju+0LkG7oD0WJ4iEvjxiEjECgwOsSS+V14FHEzSd2ZzCvXgPX3a2Oq7z5W52692gbJ0rzQYkGGBByq+ZztbCmxjiFQiXObms0kXzPCORPXnCQRGgdcKhhA+7ngA9ixPdSeunGIhgPuSuR0ZADrZxNhYRKJPqZLow/bZF758L4tI4bQhoxkJFqwUNr1JApnOrxukC2onTJowpCBwA2MPTiJ3YzDNTrjNzOM99GdBRk5NItbWfqsGyiNjqYAbNOtu+wc5O7n/Q1KHqyiQrRZYqzRgZaTQDY40STAldY5cIwDc8SEsAMShsvvHlgGFsf7a4V1vqpldsMdIfaL2fZNncr/cKIzS2nPUUfg1Mg5YqTyd5GEz1e6RGCHQNUAY2p5wiOCdt6TFNWorESCtISpcO2xO7iO51BVjnmMBZyxYck/pR5pIAA2yEWeSgImVrK+91gVHbDQ8rQCDEZ8jnWpjT+yPJEPrLmN7uvYwnLBX0JFFsbb54Ukw9EBqdH7Way9yXuB8am03tvECbpIXDE17QhlWaI8OpeiUUFcrth5Bm98eY2lwNfU+w8Lm9BIn1hQBazTGo6Iu7ex937Nj7ENFw4sha4qd1btlK7IzluYEoG8lHkgD+qZWfxlczPfupic/PHsuIE2V2bFZ8+1XqopByE1ZuT4hw+f5QkqSfHAkT0alTND8idqfZBK1FCOJ8Dyyo22Dv9AwugtRrAg91xN/KldrLKAeLmZ2NSxiftB9/vgu59+fImw4ugFyV/7ttvRR+OlVSuVSVNwCOyh/Xau1mQjm8xHa+W29+oKJ0crG9yN2s+HvXaqdOOLwDG62XlG6fGv+nPTocbr8FfLsh9CAP3TQLvmz1Fw/iNYqtpPBUWxrXXrumqpbGP/xBV6jd4kk/VPabrdE44ZrNSMB20AFwNaMjc2KVMiNeFFSLJG+iph7xla8BAUXM2Z5bFNqB5vzIAb8hspYdO1Knie2yKBSJgFPWWNdwmvlPZ1lG9qjVNfvTbn+yR08ee2jjKK8IP5I6viwHwRzfS+LWB6gUOxPnOv6g8Rk4T/WrDsCKMXro+3YN4Yp5+Z+ixEPN2pxapJ5xP82ao8XgMoK2UMZe690xCEe7a6jeaodxhGI8uzgP4Ljp/Bd0CeMFxaZBGi3csR21sH03F40AqvKyX+2uAE5eHkxQFeYzx84AL3PjsbKWDHa16RCdkxmv3TM4ayAFzgKhaceorjHo0xEkwErDEskKI64ftCtTT+l75O+ezIjTQ1NYZRpW/6jcxJZZuvVWZwzecV+oJwql3o2S767P6KwHqAJQmOuTaZDbe2sqhzvelDm1nT6t/Hun5Pxl9Z1RYNGiXbUVPkgajnF5sQudu4zKBHc+r8/DlfZC0AsLimG0Y8XmAH2b0uJk52d3n10YDdGVn3CZ7yeqoEyfkiks2f+aLgX+YeesSHX589fJay7K7enaRQGTkIlsIUP3lnDF5y2wYdJ9aSDYokJLDWtK+ZV8t97E47qbKOSj4gARwU3EiNmr/w/CjCSAlp9MeAvUywMyTYczNEitOzizZF5teuGaKRkdnwC3qumGbPaD0UXzeV8YUnijN6FBtXtBTku+kY6opOCZQyP3wZzzvxM2i5wRX3HGicw1Sc8wFFRv72qkoP8LshmLIdGD7+qK1cGsZuO05/Zv37XamL+/9xlj/BmRhbS1QvG920U8XfhYeIzJfPxXJwQuoJRvuDIBZj0enitsg5COGNQSFItZqPFy0DWO87HeiDDk/7D5tuKBDA4rphJ2wiCkDikEWUcWMpGu7UGlxBHNxKdbZ++ZyXXKJXFqwgfwY6NcdzG9S5tEB74IbDBJwGG+pAZnv+sH7WC66yc9KfF/7QjV6L8PeVCZ4qm2xLCld1ZZ+hcyf7N73swtAhNol984M8IB8MP5bCLJJigbr9WswMrsRRktvc5RImRTq0qyqroY4Ma8vY4BubH4/ajyuXQ0T2cak5EtCrL+OIQj/rw0G+hJJpZcODgsXyN54wjfkJWSS2DLQzUrX1/1zAWzLdSBB0yTjgp7JRniZbSucmA24Rh15b4k03Ab6APEn4Lg1JgNu7K4YS8Dc1Z1QDiv1OaUM8fQizeYXfRqsVwLB2gDxQplQtk0z9/TTuUwJrj03GoCOdPt6lVq5YhslMh104q1unJB+MFyOMe1ziMoEj8LfeI8HWY2L6Mrar3CNbT27KqHRcRdk/e5wlpTA4CjBYLCDZtFA7UDydiLf+v1khRvi6NLbAlmMbyk8kAMRiz5jKZSIoWPAWa21JZgwCps94z6e08mxxpe8XjVHBK1eKMvvtm6G6zzRw1wiIaKcR+ZlGJIwVlO2rwx+58ju97H5a/JOR5T+3uYWNdRFpo1E1P7jp3v8ENJlLl2efF77Oy0BfqRevB13Udxek/Ie3IXkYFhfdHmqJitAEDOp8rhiJHk+MmAPpEAKZLs8ZW6fCnnRh+SIECBrzrqNPwMXYfzcF7s/GsV4tx/1mSyovN6OK9QLcXxvwF04A+VaaB+1Hgukuy6nKU42n2hfIFjbjYp2vU2/5LA3JIwvlQBRHYkkBp7VbOueoddQZyR2Kxk0MI02eiEmyO//L70G8milSBlf6Zu7ck0UT+XDhl5HWYQYAsXHOvsyHgaTn7T7nFi14a+MjKXSoSGxhGkhl3a7k2VDYIzNv/firPIKkFf0WSXTEW0f7Ej8pDPcXaKkQvFTD2JZy4dhssroUNJ3NX6ah5dt897L7oSYb+10M26wqmXefb5A5DqhRH5yX7Ead1L3tHgSrM5v1EiVzD8g+KKuE1ZwaH2yfSSwRt92LKYz6xXzFVvI8pg3XMpxaT9A2/SQDjct7jAm0OfbjEv7qSIWM5YI/cIT9FT61smtibUuBRI5mlZIby+EYHKKdnKuFHx6MTXNmVFEG+tT5yeccaahYDmIwhgMIi8eOnhjWEn0KzTgAgDZMN3Vp4RiMNRApMazWMCjVEnghwoUlgJS9Kc+S2M/Ahb1YS+YfiBAYQpZRLQT7LQ9qOW2nulH1kmTsUkqMbDQgzKgHFzWlrO2Nk82XZCW05IrWzn6GKx4C5KRprQpk7zoobBZRsuhmiLecpwCIBm3WkYTwNTM+z3U20nzT1CUJIPGiiJSrw8HmZIbrCZlbfXV+Y1c8OdI1h/I36YFNMw85wl6LQF5UtJvJGSLIyJJRT6o6HsKcynXUAz+hnBYDDzRC/UQ0KUuxn6YpeVdpChVV6VFH0tqIOuummuLhO6wYHYhcvZGXjdImFJxr9uOJgVegc4FMdJD1ZS5AA9r56iNuAMgP+yG7QNJDZIWdYBUdB29pMrjOzzO0cAeJHpfFByF08BhdbjZZIvSXMly3rElK+GuI9KrJM3ItDR1jozuGe24BwMN+sUI1V0OlxejZEzCvIN95YNetCne97kPZ4brtttrL0xE+cG3C1eaAvjW27lXD1Mhn1WlZD2LWEbTKEmtwRR2URKYWLoQ1llYpfZz20GK7LeFImrKhNwpDVNDRoNx3tF4IKq4Sh7suiAcRubM1L5qxuu+aR95lv5eh4RK8XSTLq1kr20Fja5PvxM2tp/IAh6Ti/u7JtGGmH08OgZiE6iBZglw2rmBqiTzImVGOutb8GJcphqQ3ENNMN5XBzDxXJakhzP/iRSlDub1eY/kUk6BlRWv8hsC2eyUiNORuxAo1bn1jleLDTelufPKQKf/d8mXXldk7urpICCjKWmlYznoMGyTTXKhH4Gxun48k1RPw+7Lwomwne93M1Ha+QF6xCQZfU2ridiPbzU3DLnHtZ+rpWkKmLl/zdzolvDTy0nvDLgd5Qa+0KGsDZpJA9t5wsG+Z2TXvp/v4NXdBVNiZRIrvg1FQwJ7dX7DjIri3YmNMiDBa92BSfWbfYQOfK4amfj0y4+TOqVGm3DfljpDQXz9mkbTdTeUVrw5m9OyBNMo5IpHrcPUuzl1fUKrpNPDaicJa5Yb33gBp9Pbd7yHhX3HuIpq0QN5r/+9RTUNP20I0Tjuf8YUsB1aYkvjvOa6lo6FRdOLU5sc9JPLsMFdJJKEBJqxoP2sfxOawOBeyyaTmxaNg5k05THoKkskHNAjz/5GEvudObub5bqsYoLGcBJhFx+W2q91R1ari4ErlGO66nvw7Gfuw0t56lTHG80xx+7+dFxnye9LmLTdMkIWvNjNrTrj0bOf56CABZPypVOGC5p67Xal5PKikzyTepG/JNgTpfhIkJTtNuWkMFAtVnY4fnU+RfCfXJmj/Wl5wO3zaY4vMS83xOYSSqlZMJrc+6zRBfiPey8IR/z/L7Z+Tbf3O/tgI+fSD711iKKR8R+wHANDJbS1v6sMAngbJPtOxXEt1ERxiMgh8lQrcCqbVZ4DEkcrnLfZ0dQldbzMEhVXQFArMebIXpIROFUqhF/BFg8HRYNbAvKElLSYu2Wrxp5YRn74y7STEkLhmnQEiGK0ali4dYcQRd4sAZXiMFr5Y2wKrEnjfxOKNNSdDU+xCYd/i8bWS8PMFgXrfGeV+RiXcBRgbJo1+2ZI5qmXQoIRX3Ivq6+NJEakhCpgHypRPSiU15jxT/0JnrbkcgtEiwsOd6iDhqZK6x/MQ6aD/NjUplTKRZSc9NkPW2g2IlSNoXxWXt5VKTzd3oGXo7Lyubdn2XH9E1HpgMRw2/YK9Ei8d0stLnQ+n1lTISETsMMN1Hqv03fnalSoV+PzbDFrDhhW4cqOyVr29NhxehALEw6pPbE7Q3CvOM2xqb+XDmpD8EIxBI45Gqk+aklkFudFiivdPtnhLe6fJ9yCx5LIkPDB8PUVjppvqNJYASqOncgDfueK4ZGOw/+JHjl1W5gMShAS2Ws2wmwXTywuWX3MjnMC6L1p8ijS8t7jxKSFB4atVu6v8pKNptwVD8QMfFcL3FawOUyKLZ/Gq5HC2ZRkHQ/Rn8GGZBoQvmc2YD7YlUFzVi6gbu3jId7oQH06gMjYA+jQfw2KXqf51sQPIzCRzJMgOvXEtfZikwslE3WMqQOGV801gTDZQc3aNh75MuPpxQT2jZ2Eyb8N3ZSnp6oVY0i2nOCvQRhNHzHZojOGUDIOT1C/AySmr+RpOkAU67/sIMtFJkWQ9Vnj+eh8ffi3xG8BRAE85sRtOp8EoWey8lzScKTBaa2WwTdk97eWKwX3cJHlJpYwQAEvMZaMi7vz36yYIMRv1cRFjh7IAgGJeOcUg0VYSIBNC+YaRilaV9mTJGFs8HsxECfNx08R/5eviSsA/O/lm9ZYlYQec9qgWnl+WQYeS9oYaEQEJ+IihXgA45suB7n/ooKvbsfr66zHEyqwNT9Jw7y93pEOjV8Me/kIqrZe1myLum7MwGHl9ouav9rAAt3YUmZ/3U7wH4jrr6OEQKCQk5E37Oa+IeeNyqHEQzZhlxWxWTwJg83bGO8XKRK7lGyU2zgHKyoxML3LQo00OFJmqIGZxyhLZ3B8+mxBPyvEFcdNQvpYLoC3darZtdANK8vBqWSC5NbszK/MDfWDhXDI+nzf3EdHmU9+R+9b4tgLL/2Sgbc6DtlslALus0kUPE5le3jtbAfS1Vely2Upd2c5F7vzwRtpEpq5ZGX5m7QOW5xpfZDRBNEgqkSrBbwtK+4ZLn13u0Y128ylwPIjwbZV7/+SO0NBo68em0Wf/eoaNa2xXARysXQ9RiC6WqZalLvVRACgO6ojQew9RC4IUkMCO60U/Rv7bh+pZ11fm0uhfU2tUxbvQ7AzdrhDfe6ed3nj9CDmgrZ7+YE59MQQsUgj+JW4fed/WVThvdUQ2RIL2sp+6wdIieOqjMKfuUL6/D+vg/QIsrUIrpaiN6prMjwpO+g+F5V2pTERC7f1Ky1ZHr9UZw/nK3qHfuGzyt13xjIWd0iHvSYZRHHGAS35EhAOjM6W5yeC7gOLYGIXFFkfyicY5Mhz6Xjcb1HAkz3JhpjudlXFCN4wNfPEX22qAf6a+EGzx8ik9mrI6vy+o4C+8YLVz9gv+UTfoLhLL7eYn7i3fZfVTUwJcnw3jqoR5Pe37TohwD294kYtOURb4uR4M8um3hu4QkWYcjrtAOsbSeSVD2Y5zGC3euR4x270RsP3awwrUt7968zxOa39qII9e1rEVeauE7kMeeFK/BsBvM4z9zJBVs/D1AFHqWer/hJN8SByNPLyDuDs6rSPe2av13SKUqFDxxang8/UyAOFI9VXBwctrgq/pBtYdd+Oopx8xKTom0gVaEQ0n6NzupcwgnFexptijUjudzklb7RfzQbjrdbCAJ0HtEWfztoOWz5N79YeAAMaynFZT1ZL7aZ20Jcmq0sNzWr0kgPCEaXdCDWYwiEyGNwCQ83GpUpZu440vMeuAszU1VSA/UWdlb1tNriPIjrWaNhxZcUZdL/CdX2aC+M00kscz/8wlL7+aLM7khDKUIvuiH6nWZwBvfbGBYlNxFQMb/zWkb/4v2HxJkLtfaaTAMw9lIvrdNFQ3TzpH6EV2a2ZZwA6QnjVLWCZurkDiFsFi4ted3kMjRONv9KXzc7avpULjqlvCll4UpmczFZpjxHhdQ4kCE6B/CUWxtBkiYyfJWzLgtXJ+4SJLIMvBk/Ye7ZbhiY+9xEduWTo/m5YJmsrpRbDmm/tXSlPXnIFPGlnkMcTS8pLAXimzLZ48YC2Qk/G7epumWBVFY0p/O3igW7HhtpTBIZd3zTSzh4rosHU/kgq6bVUeW+cV3RaMdjKUIuKYJUV9TNgFINi+gqxGTKR3518p7fiwnfG4gVUwWmoGnasazPl2272y3LmxxmV8TUmNh+2PYj+Kt2r4jMHqDECVyiJlWegUegXl09AyRckNa7G+0K1CbcbmrDHQ1vfueqOBMUp1qtqr1lqlhwTtoTPbuWd6hIOmD6d9caGPsOy5kZhleWJUwDYe3Eq+Fkh1gX0B8DD7LnSoFZeruV7RRjXE7NrUnNf5VoggGnke6+BCsdZiwexIBSlGk6RjpLLHBNd2+uWIp0eb5Cw37j5CLa9AGbeJx+IzJr5tgUc7n3fpX3YsyuBTOfhixf0Bi173Oo1yXGa0dSw4vjII3+2qkLhQGIDqa4rbD1vpGRwc1DsIsAEXSz+lcGe5nl/ZHhaMT956jGa6R2+TG3IXmjoWtSoZGdPqOVaP/BIXUiXqtzcVFK5hdUzCIyMZK8OVab90roV/o9gvBG3JbLXJVWQL3217W1Oi+YIsCluzHOoT39q681jA1sTbQnORpGDX0/0rYai4pICwAq6U3/zq/bIfjfFkUNtqb7Ua9hZ1hRBFEtAiQx8Srg2xuYwSOrCKdAc1uKlMmgbin9JTxyqO8Y7/AlvcKuVYn19on+XjWYXXQZSSn6GSdrhQDAXYG55k+54lbo1PK8SfHsTddIryIVvMCZseInKZrivPUzwEDUCsawvcHLokdyS1oStJnwfP79MxejOm593KQI9iab8pm5GMDhRSWym5B1lqWUj7YxuLCneECo1PHpYRe66GbgI2qX1SJGc/uz4HCIB0wvcCbxfxAIqKuNTTAei3huBNXE7HxImC0IWe6kTgN3CecoyuR1hRyiQ9XXJ57MVvL2HQeMJecX2/hrZhpP0h4IhYb6V1Mh0SZnEU9MLjTLqUmFGz/o6NncAeVe+/NW4eYW40Y8Vj9lL0WowkJFgi/azHhKblbYb13Pit5rxQLL+gWcLUM0+jfIkWPCBLdxzzQjfprs97th2kkimWV8xL9ulZbN1p0gcAOFVsQI0qOzYvCcoukAgCI5olZeypa+s0+nyc3YH6TzjmpbLTvLgRbfHXD1TIOFRaMtazzrLs5qPh8yAEVdOxrQm9phU7W70HWLC75B9wFtBmYYubnNGHcb6eVDRpmgCaqmnFphpczL+s4dEpaodFrwBVbQq82ThUI6zvf3bxjh9mT5l5Gdi3bw2ATrH3P9X6whQUmmDhsTdk1W9FjsjAADp/lWm6TmzGWa8eKIh1RnUXQaquZvxwIoMIwRY5AqsOIrJMFZbXxJ+yl0C+8ZcHkj7zKsEQJhOHntpz2VWDkbXyvh4/prL9Ey1UbNoLSPT7DOEGyorxOpEtlDCqM4t12uimH6rxmuP1R4zfERnhpCm886tRGcD8g90hndrTB5knRur6d7f9TZlB1KpTJ/KzEOFnI9xg8am3wLf+e8QeJFoxWV1ulPLb31SHvSdwVaHAnQfvkzuOVb4xT3gRDcb4SSwBiCjdqlqu7Cc5BSwCEC8rrcnFUebNhy61EhOoy3qwqbdLbEIN6jbBndAPgcIJ6K1e3zRz7lkZtWCuHV63BJBLuu+yFImVs1b0nv1nfT9V/10wBFli31BRpCYxzNZDyp4ZIIfBTWFclFjIazIwMBiIjtMwdLBXr2bgH1FxDqtG1yDMqw6c2jJmyd5ruU6Kl5lVQw9VSYLIu8jumxmYw+BS6gp6cRNCZQ5Ckc2XvtX2N6xzLMyqmYGpIJgScWI6+u4Ozyr+rwVZd8jTUDStgq5YGYweCV1N0KTsxmqL93cjf3Ss41Y6E/C4TPxJawl1ZRbVzP7vfH8YGjTtkfg0fBA+w5BNAJAosrMYbTLzQB6zL042JMF+TI/l+FeAEvEF1dyHvjzOrArW1nF85DlKgjNh2Lf7GXon7kmwKtW0T64T6Cb4sIPS3Lmi8thwi1q9XBUV9pgGAjx4/rdvVkdLCZZ2E9MuSM+VxxzJ+eyw8cL4ndOmct97xS1NyHj1qUIGIzjqiH0eXDo1jCC/H6skjgaMjY0qo+GdxUi1xZ9rmzFASvZNKoL1A/7E/HSHcnLJ2/v/MA9ttxnxYipJzQX4Osa+LOoqdSdR3B2dZPbhunBsU8k9iIPzi4eKn9bg8IeUxcbJc6u3f1Yzvi/d0rUivTszr5hSJI9DmApCGiHhEVuBRGiDImP+bl0C5gPjlBsV6ebY1TBE6kJy0aab3KauZGO8oM43PDsN52c+z/1NLt9kfZ9bnha48cJeSMBAhdVIVhM+20kugnJhDdLLFDNbk9vc7mdbd6ez1VY+xjFncwpOBfvjWcj+YUuP7dWBc3jDPgX4I5fI+Dexti+P2rnXqwMGjW5KtTFFTnVgiIML4nW2qqSq74xnacozCMLRDru+WhpksyFhZInwwPfGCJV7+7y9Z5B6ftCyYTUT5Qku458/gcUoCuxCTNlte7q+4j8jaQfxZGjAhbImEb8LTpPpfOb+i4sQhgh/zvRoU1UUTtAZV0sTYTW3/VEYCvMkAo6FwrZrshysdaZEbsFotbWAhvI5i0/BAzubXdHcnid0e0ygLNFiKORVoJ6KyearpywvDg42efPKqgePGpzljDsGSwwIO5H0iYhj/+h3OnpXyZj3aocfHsnTBNfDdWOnhBN+IPjwcyt3pqcBEotL0rvgYwe+WeDtj1GkYjtHm7KBbEJ9f3+adbHrZQiG6AhcODKfSbPWOl9O4P0U2+DxeePDkHooqefD0rYFPKhonTATLMkbnvlZxKkKjtt8iYK5exu7lZBDX6htHYPf5uh0o9A8fH4uLk7JVvCjjreQPxbFHHvnJT+wd+PquSpNqeHwvPuCbR8kFNXxkRaST5nF9ixLBvLiJmnk6yHJcA4D78OQi1/mPbsCQkfoVM8R8Uh09Dce4rXr0FPqdhq/G8S2mOuGgv/RofL+NK/tNopGP8Ec8cYO/FO6+l9NzI3aFIuzJhDBA0/o5uqz5u9AM/Q4ssPoH7LnyE7a0/GEDsuCiA7T14yenEb1UaUIokepOogs4ieSfMit8jHHC3xWkrmFyDf284iN0RLyE0+xHGAn6P2Qjq6By8msJ344QN+6d0pqIIHZ8+0+8XLb7sO+EraPL9TgB/N9rSMfMlFkLWZ/+qVnFT+ACk0G0kFsLUr47x9d65fWtF/OSRV4tm6LtpPYRDI7LnFFErFT3el+Z0zcSJxnMZ+3jKTIMhIln/58tAkxwDAorvpDzaI59nc7Si1cgkbEwJW4MAfUcc9IPp9S40Ki9H7toqPrbwPwQL5S7yL4DgJoaBA/YRW+efYBE0iKnXvdeNrEz1h07t9Idk9u2AwKCWugIKvE8HAcVhxaD/ofKSpPCLWQ6KIfDLUuB8WvAPubtMo8dj4CB4ycAsKKhJ+uLZs5iriCjkq+cD/NIgjiGcjqKfAKqmVMBBd0pSlSaGPhn+jWev/Glm5wIwkVjoFolOaM2ITjpiAOvSanvLERvXObnnuHYkz75VOSZw0kyC+1vFGvp/SmMGR+d/jm/yI2dfOjCT0Zuy04w5iiQReCm7CS5saZEa/hu+yaa/siEL/QDgqJ0O8FUpidILjqQckWcLLACI1VUozHVzoMV4CwuXtthYafJ0gj21Uw7AJaAv73wRKMBH/kPTP0yIsYe2pJ5W8zqgX+xtYe7YdtCwc7svTrLy1hEBq/BjRbBDKFlLeiir1QHWl9f0bKH4cYYXzyk9LbPwVaPVuN7DU9lH94g/ORrfvDCytd7Rxt13vECNqF/lY39IzkINwfplaiafM/KQ2vz+DDl+Jfl3GnkI27oRDZjYmete4VdSwauAa7wgrJU9Dj85YneT6LXAJ3zVnV6Ko7RTV42DYvJCTZjBb2F09ITPlQ+nJcfPXQ33KzCfO2D+kY/YJ9zb6I6umT8OdZ5bK4SZS71nExIw1s/gHB/g0DQ7gDTHPbt6KnOX0qgir/HIiD5J/rtxTwXQDgxt3ITnY9HAtkNjHUQP8CqhSC05GB7JL2aTm9DnOR3Iky6UtPT/u0mVIoRb4BoCkqUQz+edS/EajtKqlob0pF9JdTYTwI+l0slykbTBva6C2oJzeYCAL54hcdXeoKf3l+V0cy1CJ7o8ug+jVXnF9jiW4Nhcskia/z2zY+SzF3gdTCCcKnid8LMxh7KxHbEznlctfDRgiPokijFnJNfJCKAg0PPaeXlg92ZukqmeDzE0lpPAKpnSg+4P9YCoQ2PI6/IHnzaQQfEi1xIJgFNr/za17iTiMNre5JnBqOHOcS3nuzOddPVpYWLl2YmHSdWa8N0Ecgu2oWLsn8JB8Io5Wt6BgyoyF59irSNF4JhUC5wwq64MxNisMdF0dT2BMnbYemzvQUYMEmdPKFJc8tRr6cL+eNxXVv6RQ3YRnlE38oSUsaGgyDU1m+5SUB9y/YVd2+ko2sRceQFjgGloR+j1r0eEqRWT/H+ytGIcsuQhi+MQg9ygJTcI8Z5Fs6oTi6giE4vtnKfBgSmWOq8Ixcnp0xdHirbS5Q40T2cepEbwUbe5xHHnFO86V+ucA4pR0WH/afBmhW/3GZAtbq0jF9/bsaLfQIMl5RbPGjMVi9Hyp11jfyfIYcPG7zSTviQJIvjbQbte85fiF7ow1JgyG4Z6VeQ6bBZmEzaZSgV061+OfnQIGrhIJDv1mbh1daIeKPvUdFQfjhbMuubz/JbvhnymPMO9F6dwSTdXUJpFiF1IAK4ovto7d4GdM8rY6G7Zt2K2PXzJu/ajL+3J8CgGplzzvQEOTqwJ4qw2m+0QKiHSaNLyTSrdb1HPXq4iYkwqRTzxaDbCFn3GJ9bJK8i2sWT/NCf957qcvglR4CNnH8sRFU2CwfgbJzcFSbMe61Rgg2EisnGPBimw4Hp+bEO0/aMCOAbaue7QKw0hxTamrbS0OttivOS6t6I682dKHzhkpwvPyAJNzybxTxQixuCrv8gdPsNn1678+KDIzp3O3Tg+J2qexTW3anoaD3DMVZXNzdYiGLVnRqkMJg9weekM+D6f3ugI5T0fTG83sKfxKQ3f+mb6MjiTjLv44bf3HXu/9y+qfOd1hIl5/HKbA5iIMrDs5/HhWIiNApeWxMF7G1yQb/iUkUACMml9AVYSgCNuvn2rxVUqxQet+DyLpemhFg54fD8niiXNYF+mIGhNLsFTfoZfCsYXEIgouZaVToGg2OZcpYSpZRdONEQDEVlz9tOjc21pS8hNJIFq3EW1Y9xOGlOdy6M/hmp/HJHZ1V9TpeRVBnk2WXpYn3TVglQdM0v9cvtVw3t+b4CrTp95qm2syYOjTOEN80ijujBvMo7Zv87Z3NZYqVjzWaejrwI8G4J6yfjfoDRCn8hds3//zxflKKTLyi7K8CyuFYUcTr+m+H8Xug7xfcgZnBIe8cVrjVIuPOHlYfVmhuaHsmEc4UISq2gHPy1UM+Owm9o5C2JiOuFSbWnE6lV6FlGwTP1ODVBWTy4dWeGAcbogt6ellELA+rVDSqHTHcCatetixCIBiaS58md61QtA7lepKAbYio3u3HUQQY8Q5WaYBX+2ssPvbZswoNzVDgDSOM5tmz3FhvXJbgiIc4DjtNNYwDHbBGzs5dQ1nz9ukSNA143baNdjEQw+JBrSe7p0hRCvN1o/YCs+dhV/aGp+GOvFgiermfHt+SlKKoNqvzcYG4aQmC3V0nsNilS45msNQPQGxaaMm6eaO9DRpFV8ryXLOj6M+JkkEVD9iuPzs/tQsBniTwv2Bz+1VyHhoSreF8M1nhYrDiDuuadVlgzjScFYHx1OswGbub+6/fTChJKcGenUqW3gfBh7hmheTOcdMH8tB3gN4Bd+6Ooeq/3+nFXXTLiI/8D2op6bK7GL2t4HtZ3j5NAuMqjtBKrfud4WU9VbAhpokNfmOKYJl+m1Oo30+zT+jFlE4MMkFRxHqBTlCe4PNBCaIJgtx2J/o30aHrQal9LnmDjiKLKhMxgcUTu/vOQ96ftZQt6KQH4MPzw1MgZKvaHPj+ExkK/yCqS+9qaJvXjM5G9KY/dgeWw5jeiVy7FWIB7DTYK0r7xU6hIp4f5ye8BllztVon8iyW6Af4RPWqMdLEPjtR17DpGy7urZseYqsd/glrOO31cRZGsoKY5pkpJSYhhfBv1sB9FitbEdl/HXWeKZbdNNDAUGc5qtazJuCHvMH1gVe/0pIIONjg7VwRaBZV8cENljLNdR5X2WEiF3bXvF7aM//LqKtgJ8ErD2ClBWYV3lhgZGn7wu6tWdaDjEpn63IWyXbQjuBqY+4a71LCmsIIP7lg3Ss2JEHDIMdE+JX/E/KeSfd7xLR/dviHWVkNCBw5Dj6jie7TYsB6kcfDp+/gyxk/m5z4yxOzrEmr4p2LTy1p72QzzpN/4F7uPYf/Td04V+HAdkf8hErAjBQxBeL35vMl9yMYEqCOjCzq4Ghqlwtuh/yYvzQoSdyywnBubgx8axXe//+4XsEk/CPbKHKHMtR5GexsnUZT4spWpzjlgaUgBMo0ClLMzcZD6b/R4/0eYPsIuOFPYh3rZ9SJ2aeu+PC2/5CbUi3mAhoJbCTmHbqhcz5HvEjU3svAvK4N0v7JmQxaOqPNqF8BJdQ1+dH5u/XjD0x9Ee/tVo2ZwVR/gCxFTfL4eGwJc6Kl4UzCpCtfvpgJDv061tjbF/BploQsIKBRA8GfNsyL0OLOX8Po9UhcY7qyBrgnufcdye/fmL/pOH2RLflNW0DRCbYglKFdPBhK1IlXIBF6aXYcpJrfNROXb1TQihPxlQmIUMpOsY49qZ0Pg2SxNaGOrBaJW8BFaQdYKZHPTtyDk7W0YvcTNvcHnC2vwCNdVTtLTADYjswfzv9XQXUyCQ4rYI9osLQUU+OZQP7mRUm/VEw03m8tLMpBtBf0jAfOaocDL+bVG6Jnxl1oNTOcj7OQACs0CsTHOb5n4Rtya7yA7da+98355IrVEznaW7GgJ8OTzSCw9H4FmVTv6gcBHveIPRKwb0soshRItD18V2+gD3hpgxhz94jAU/FTT5alEEag8WHVBx81xZpwpMbZOiBE8rgW66cb3sXQ5KKRReVjDozG01psVbkDb1G0Mqg6yRVWYiitoh+57iQ6pmwzGGQwyPBAgAk3XqQtXCqzJ4eXy5bYIU/bow1WRqCcjb5IbxGJTdKdGhCWApupH43eFQq3Uomu7SjarKGmliguyVX6TKVxAGap4+MO63btLKw1FEmxEahVuaA9NW2cDPeNr59G1kyRL9/vFeIUqyaRlXrI2DsPSMoVDF2zLmWpwho9ZajaOzmEYEgsHoLSokOCuy3BXVu6X3Wo096BCPlam/r0ljhoOU0VgZDANoJ7mwxYQS/gdvX19vS0e6JONsuGIcM/jO9oyb04Ou8oxjaBzCp2kaE+Ae9izhlz3+aDlDDnpAhij9NNXa7veYtnLwsUWML8XEByfBDGtc1XKndRfv1cg8pICxhXvni0xAVUz7U+/Eq+vig35D0qBd0L3TJt+y/Ra3zyB/dnHmG3e3c3R42mLiZb3fULGi5USUsveNsQSjqwCvQfxKty+sMiqWw2buq0e887d5EYIuAHrD0vf4WrDm7JKC4eApQSe1sG34KdDrytikmg+H7aDQecb1XKv/aSAOqXCJoUXXfYf1vhhTl3LvSGaQzgECqlQtDSfqR/OMjgtCiGWn47B0QrAC5W213KXqQHb5DlE6xTxc2Gs7VtlTsqwpKUJHdvDY224P+ZnlGaXj7JoXS5Cc4r4Y4zFRaJwyRYWpkm+CNljLSd27IYio1DP0AdW0eRJouchvBw7HNGNO+isfaqDtA7Gbwdu+vgQNZ2S7eKMkNK/whTEg85CBFlRW2CLMo0hc/R7xD0OlRsoP9tjXhI5OsNYhyIIXe0AO/CQb3fXmSViCuNqowMoxR4ZkWCuajG8AiPhG7ALFw3NclfTtrGZwiUICFIpbJLaU0yrdhjN1x+koggmp/y7bEcXlyuNgQcRz5cz4iDR7AWgl4eSpnVwfG7DR5qCvfIOlw87ioZtqGetKBraZxtlB4Y3ZU2A/ZrctzwmDKx1RwIUJSu5FoThRvhyKF88Oc8HqsOB1yaQiAWkF4WToNpmr0hNa3+0E7vwHGB0dSSR5A2UFo8nVOOxV8IXmH1/kBfA36oQbN9Iyz6UwTE01/kQn6CWduisxdcSSCNZSq/LqADcmrlNZWr9B06rlTLHDxgGm7YNUTarmd8Irstr0Vur67wjoiqP8rZU0KaVbb6aNEgOt/kQ4ZCGtgXZkzzaUyrCS5lNRAHiIDh/pqVMYRldyTdM1ifp+cKUd2/hQ30U636OXbkReu9cl3z0sjP+rpCGZD6LCFBEC9UxLH6Md7ZZRwXgs/ww54X5/yMUTvYbyovhA7EL5/VK6cQJhUU7tUY4iYq0K7lhaYacxDJYTg7elUp9qeiBTpRUkiFFMsIC8iLySKfB25Lu5UhvlN1ubPOT7jWoJwkAQ4epu0SRNVHMMtAtj3ODneqayIzi1sDAzGliVYdDptwvuU8CyCPy8VszUBVxNKioq9TClGtrxwkqXJq+7viCylEdrOMsOgYwXOcjU2k9Jm3q4OI6El5rpM28I8/inzFinMMGrG5A3Z3AepJnY8ehEZeo6FsJxuI7slmbUG1irOvspE+jEImY4dlGD8VRrkqQUHjDlBluF69pRrKC2qtTcgdu72cKwt7AkUc3UYmMeqkDi1M03VHEQg0Q/SugJ2M7K/lqpiql+sBcvkn5Wn0vbWMWNtvvtCboYsDp5vWEds38XfX3L4N4WEkra/gzy4BUziyU8AHTzPYhAHbLg96IeX/Za512/LiOjJlOhzUJ5Y0gvu/ofUFbPNYwbOWOYJ0A11lLDBr3Ol3XBVNyWxYINQ3qeKJ2WmW25ZpKSmokZaqkCmLNJRY7MGQeGHcmoYOqQ7YrCMSixQwQLQ8o8wDuuafDGN/hD7y3x6dua2GOOycS+TtYhH9GX9aI6suSZxyS3WlT+8Z1hMp5I+arEtn7sl06xUwWFqWiJCRRicK7LTRxANUsOP79oPFKOrXGqrDlibPQofhN+GD/YXha4q/5SC7qTOv4C7gkfEpkTOy8b3Jkmhnxk4qh+kXmVl4LKb1RyIg7yLUFmUrqsdctmulRFRUhay72gMiWbj6rSNuX0rZ8CQcB3kbYNRg59elfbkhyIQc/VyEp1aFauHdQD7kR1LbvkSejoE2VhrpNm7bLDe3FteW4YY8JeXODzwQcIC9e2imYgs1V3klR7p6CtccgImDi4FRmTp/mXbJoTxZuzKFHhvuKQRFmTtPatq1DNBaeX/At5XOMKUdPDdb1s7o5rHxx3obYU0ozztwmUlo70I7891yvRUjC44K1/p1g4XjEkfVjweApAgw2E49ORlCpANFjNKBzaO3znYaFgi4uKkHfyWfWHTa1Cq2lz2ihR63XTwFPzxeQHXscVoaNsHKxwRiCBtcd5ZDtu3CLw/HiD7pmQyWbFLVVOFn0sZvBQEoZpQbXkfkFgyKpTYME6CA3w52pN28d9uSXgVB/v/mJNzvYaHRH+yjja+gil/LGpglhK8vMYATbg7iREHjiMT6B/DC/eb7jOu7rdJCeCNlBOyz82+E65AhpMnS8AgyKEb+3JsRpbO3FNQVpyImKnRRghUnUq6eRFUnYP+UmYBYgrhWjwA08iKsBOGaEjL9WVOGbPKAva4lWsWPqn/H3v7K2mJlfxC2etzVkBp8DOoEh7ZOcC2OT4TdZTbAaK/pOzmVaIWtZ5/D021CfIJKuF+BfNtdiysE/xtMe2RZUhgbcbTSxE4rUozGGr2Ptvr2/dX9EOVEqQpyZUS3Er/jJzHH5QM/LwalDlFTbuGTYjIc4j3GKUSyLN6SJ/8rst8YznGvMV7Zh74Him+wjv6wnTsUX9eSyOF+eX6pAsSTBtD4czSYCpb+EAKRbH/TLsf0WJOH5rZ7zomXzJHp+yxbmrqsjYh2E0klHt0UBz5fZBuln1JEXGhQ/4Fn9ISXqfC72Cv8llBA4/AlOQLHYlphUWB0Bh3qlTxhgMoWyef4rdSObw1SA8cCeLLbZVpX+wGsQA/Gz4v2+qLq8uYA/WRH/e2UiIBrfdGJehD0E1TozbwqGNPDEkwLq7YtwnJsKfJmOT2gAEFpmIOug7IYwYOyy45YcAHR5/WHvm8CR/m34vf/YmWds+9r7QhDcAZd/nq7QuSjSdNgdC3+bwfQOd3Rs78wD12hJV8WS39yYE8pEp5+udZlmFb3HfAPQEDMdB9sV7ZlkXrqUH8cU4NGqlbEfuOnas+ExRPhfZY6zwyc8fZhczOmHmvCaQNP9n/fF4Qhm5iiBXPrFsXtBNf4aGGuqhzqUplvLhdGQvf+KrlfcN9WfhCKexxf8fXSuWoyNnGxQwZaqn5Hkx944U463m4de0hZeutFhcAbCzO4rvhivSjnZZ3sMvjGEKtt34liRMNn8y2mYsUHsyoDCVZb+JpzfLRR/gXb2YNwVzy4/lWsWCiso23RFotTHTnNfyLF1hR9MtqyzA+3vJOomL1L5dkAOziRkj826vAFOGAFUAifik3fptcALlYTxrvlj5X5eyk4VVxtsMWYM+5j6Z810eYzr+kVzM2m5wrOgyRsCHvbF3B/EdL86z3ns1W0s5vJzTQSOJJYsrSvVXVL66qMTxsitSTF7KsdD8EnRfB88CWN9KhaCI1GFU4/IIG+GP1kLVQ5ZgJp6yTdkcsvekOAXvA7+yPGcAZDKje+gfmTftCRi2RFGib7C+6Cikp1StADIcNrzk17juUxwjW3l00Fe9Ls2PsiqbmJ+rsCo1XX09zFD//bxvJB6MVj73uxnnW515yMecLey+dQLGH05jDeMCvfNUw5/0yDlYeR/bGTBD+ho404l2BkKqqWTTz2PB46atd0fJG+krup1S6dmqdr8Hqg0ipCdNnXo8dfnUbzWY9lmHb+wBvtr5XY7BoOEQ21p684ov4IYseTeQIoGdX0TXSM564smX2K319wdlslFoSzCuwcXvHhIXdLORVYScKuoI0x8dxx/M4IVFwtAJL7W0opekAGBH1iiAVhGULzpdzRDOJ/WCblqV2dF3mNQYv+wOtSAnGCw4045QAFFMwwaFee7Q6Bpt7vwvX8Bzjzee73NfSVTkaeyTfPekiMAS1HNc40WN8xSsxF716kyNyXVkT8nRLAhDY+dEg3B/Ppn4sPJWOFh1dW3HYMPcIVdD++Nn8zmM7WJk3WbSwGtAwKf2ao1o3Xf4VZwYS371H/xxe2dE4B1BS6PK+UzPixVTb6EDWrcy69lBlzl43AhgAmaEvmG5aou6fdVAbuxuZ+l0R4HQOACfjze3/52pqKydNm8tDhKP2enPnKbryd7FKkyZVRHO7yLrKs+twQ6wETKzc1lA5S51ONVcNpH4KZcVNcN3Y1xQUjYj3S/PPaw53Nj80Mb20MIJS7ZrXsJ90Kwz8xQPTK9BAZW3u5bp5nLgt9qaAdwoaRuZlw7MYP7KPt4k3OjKJL73omenHYA57rKOyRLtWmvk3t/0X6F16cY45lqbLEO2ukMU+Se3oprq8Efzh7wnTnblzcESNOx9h7WpBKKkmoqdhvRXQ5osgQd4psm4/buzPR0TMO4F/+0Km8w/O97HK+sh8XA2dnTWL+LWQJj9R+UEzcg3FR17XtK3pPeU1RFlnpZoLRmEWwJ90/WvYCLno4QE26dl6oIwcHmOjWPjUK/xD3ITER38Nrq9VVtnwr4KmCM7ccBLqHaGk7z++qEMn+/nr7+p5+aNsbl1Rhw6ug78NYJtP8QXVkGMDphNgJ4vYu2rBNOZniHNNvs/bitS57HfrOz9QdPnnq/Sms/AqkE7wv38il6htUBqPdKdO3HbA09s+6u4MC9Q1WjYnKy81mOqX+rYrHB9Sw+FJx45l0QQVGp++ffn+FjXJxJYBFrqcN1bc3Bo0/fB1j/FFKt6QKKAVmS9STvDF2yS1d/NrbtNjB1VUOl+BvOjQnW4A3nFcPFRC39p3Z8gw6oKdrO0T40XcKWmHO+UOBKn7cyKwL0XzoA8x43rX3/aTnZo5f5T3F4n41+Ed8q2PlMDsO6JHOjh37jQpZFF9Wpy8oj2VOir0TFeBQtUZQY90WILAt5Vbrri6+Dln34yFXknc/pff5uYgPBaHQ1ek96iPYAC3Bc+PCjH733Of8TzJwNg0HXh1OmIWJlMmHP0LwgtNdCIt4SeFxP43ahRpDS/R8uRqlaBZx9b5huMOiu6RVE5aj/7V1tnzFW90D1bCPdwsodJG5uZRgf2nMNzRryMzbTLPaj0DczAZhYY0l02UouFoPTRVlfrUir+vygfeD/m/Gea4Lu4aLcdD2jax5Tdok4aE8fkXDBP9p0opjgRf635wpapVYaAn645gBV+ZNekYb8bxdLT9lIXU7h/oj8vPqzd9vqsQv8TSZ/YQPUVD4pZgH26e+zjz0xASX9swi0yXZD4aAJqWASprRmTcQcgHHH6n57RjH4q5V6k3GR26lRKmIwR0nGm9WFW0yyBE+YW53x4Vrd2iZ8KjWMsaewtXkmtPvdvBsiRTSEnnymADMgc+o6pMeG2n+gtOP3t3NZeQaiTWSZxa99IG2kH5SxqSGZ8Df8DCJOUqRgqN0MQwTxW988b4baXX943DRYXKjjMv3QVY8KGmrGEgucEo0bOtc55nQxdSUKH/5EvfsqiWEQiKOGU4RQPk3tZG8V01+M5/Ayfn4qZtdUA0XDcokAmoZf/2GVzbVAQUd05mLupQPpF3UCq+W6c+lld4dSIwChIDWo8ug4PeuKW/mKoOcsSak8r3vK6SLM5tJ8HrfGHTcFHwgZ68u1MEz3Why13pro4jiMJeAMmN0PhVBPS6Ovolm3wehvc4C6x03oiNkXqoxlJZ6dtj/2RfGpsSwup/ctXVYOsdvvJleg6lcIHcMvO4YCUW5lNixnUSemj/zeLOkJCJRsvQGo8QFdq725g2lgA36Nq/XyvOdpMDt23ne3N7iayTXuKiZHxsnZELMrTIWvXVvRgU3irU9WDKAedi+DAJkXvnmre00wd7Mv7aFnCnMobwjzy9Eq/q0cMKDieyECuJi05F8GdV3U71q1mm5AJFaIRnEvwBDFKc1ZsP5Y/2iNJeBG7XLVbqe7H/10R8mv5vkxBMJ7HthIsd1NACOf9bei7vSphSn9od/lAT/SNM6lzqS+HmPgj/AA2Rlvham8OincYHgrwPkvnrlX41j5UMLc7HQh8wTFVKiSjYNisBIPeJisWfLQxkG2Pvt0tlEWr1DeYt6POqwCd30QjGG3n5djoYoFr9OtkXgJ02ru9bXNC5s55VXRzE9NRSNFeZHcDmG16tEoTAycsyyWF2NsnBHS6A//eoKifWgCbBG0wW5uahYOYqaASUc+XQVQYZeVXX2bczpUP0SfmT44Q3ZTTpD46G1aU62wtysazHNWCYCybwCJQdYwbGx63qeVczKIvruNNA5GhrW2GC8BrSqKdSSS4Ee4dHLeYAfg1MyLyDsQ/bMsKdsYr3b9q6YyqMWESFv06VTFva6VOM4G6NAGk5W1SYPqd3qDMmAIGI5idBGid1RarQAnyLqg0V9pVQhbHt+5Fd0rhnCuIj4xrr30A+a5VNqdsehy4Z9kqViaMxUSoYew3xk8O4ToNSlU7Qu6w7FlMEmX3/n39cMoVWTXpA5JZ/Y2Qeuo2SvSMfuXDzG2hYy1EBnfelEQkZ3soN7PhfWPEgOLTYSkm8NHDCz24ooH0+FUAe0jpLh0TJUr999ud4D8PGgj0THpJKbMMW60XqbKctu+k907qzmRmulmR6R8/HjLp5ublvX2YxngaFaPMy8LS7iqDhZyr4CexbEJzdhcSa9ALZ6/HuVwlYdr7Qbh43CunNqltRgSfd73CzRf0sGnYz/kRD+4oZkACNDfazHCNhHCLUfbMuWLYrqp4xfvCZXQg0kbXyP0xawPOHErmLMYbuyktmvbYVCqc4za1rYWZbgONB4m5Yy2Vhvp2OKm7xrREKLPDkNxJpmhopE+glp6Gv7mnIQ30Qr/CVYcL52M4/9SvxST7Eu+wjeJhoJfIm0oz+bmxecFB37G1slJWaZmT3ADwQIJ7j5cGLpJoRHdNeoUMRYppDOtLTcgXdRFc7ZYYHJHHbfvfp2X4C3swZ35qbPti4BBx//NC76MIT/SA33K0PtxnRAsS9hDbVRNYHPUVdjxlXkA5UKz/e7uD0XTx6a1ai3yC8ndX1wJvaYKROIDzKpsMmnUSlBDleyVXr6ZzhnmJ/ulI+HtKKZrpzwJAXSJBevyeND2OOr+S2SljRdsazDoSK/x/wMpV6P0SPPIAbBCeUEfVO/9iG53ZpAWcLA8x0dAHYdnA9Rb4hk8uGPn7lFLm92HO0j5tCp+vujkIDs7vhTnx8DAo3zIdbK8jp4Btf9xCPJndqQx+asB4vP5M9+qlHC/nHwhBW0i2TRQuGdJrfX/onwGsfV3K2qGky5rOpjDdUUnndEPBiDk6a7mmaeOTQBbpjsqbBWt5KOoYwBoFmm1Wp7nRajiGn0fxDsmELTn/uQ7AsocnUbsxJs5A6KlUI2j0m66fErqEWfEH9bR39Nj8MExJ64npb3qKyUzBI8aVr11sYaMtxfl5xHnLD+ZX6ajwUJ7uep2nyP1v8v4wup5Jyh1r2azEClVhOpVwD40vw9fUNPnUz0Qk+Eo9FxunYQvTRQEgsAKJVWUfyXoAA9GIWehaKUmblGy+SKmcbZU2jV6egd0tyJjDqhHQw8wIp7QRP6dT+3wZrmSmZFDHVV8UD35cv70yR9Jy+zeZKY3sBdTpYUMGoS17Jc59oP1/ZCy3z1xQLU4nrq5aEcRIP2qCdPWdOeGFC4LxJ6mPfGOG/hCT8Jz+YLA3EKkA1EfBGw3CUwIhdqcBvRcAJX5RVM0Iwk7FNwHsj38b19n74kV4BVeZiBl7HFsml/mGQYD/zmpm2/++GdGthwy2UXdv0vx/Fclws8950/nRPIA9CPJntia6zUGEicdXOtCBNFoRWTKI0kAMCTA0/4GqSf36BEc/cM+oagOo/G66/z9FBNBQhoBEUiQ4po7vceXinb6SYLoFMX9QqNlmqiPj+ZN6p3vzKCIdY+grEgmIdPIRBXXrMidG+/mnIjL2j7wCatbz9k+4z+vavac73tXE4YqW0YB6AxNySJXerx/1tlCHaOJrQqbMuLPqBYTebztmS2p0cDbC1Ra5FgErrB5dzxzK5NyOp+45WTO1vC5pTPf1MuiRPJrNm07M9TA1r4HwPVhXSEYss/KRDnlntsxwd0HvuXYzXHYFaBKIpUCJ28xtAd/5lMgX7NYje2LX14hC3bsglfcHJsWg/reKSvqpv6fplDS83daUVdtfdFCaxsn1KAXsbd44+yu3YGuaGRyNhNmYLaKLebZWaurTvaJUW/Gu5y7SS01Vkh2644caCC6tijvp5Za5q+qjZKTfKcjmvxRJL7G8vsshlVmkDfE8zT/IeRcD0EJxx5Ve/+TEnhf3a0CPAguDy9t0t7h5mXS9WpmUj69Km0xZoYXlWAJraEg1wpnVUTFoGKnd4vH3p57NDHhK4xPumCEZpr9VF6DTha0CXKekd8sG/ob4o0EZC9CdBh2G7WWIjvJ59Gk9TCfDZzfFm9zCigaiVrkEJgFxDY/VEU/N3P0KAG4zFEk0Ort4+MKWUW3APnMWuCuLqNCPjBiiNC0ylCBtmFoW2+SwRZ/S2wYzZxTyG1niFMEGbjDgO0yidyDIvHRbZtGB30VcVk3emR8FoRKls98n5+DMB/G/z16IKuH4RirK83vlk8wa4+gGMWkIkiZ0WobJImSP9J/2N6S12oJMAhsnEYTxL+98CqYzXGcZtyStErldzYp/EGbsvL7a5j/oEo2XrOOyZMKQtgFZDowaaaUsMb/VhHQgSaDw8NSbGbUcS0G79JacpxBMDSWp119F6V4JeZpoj7PF/pgJU4aoDyLTGJi6xGH/cV2cVg8ymiR5938f6HSAL2h+yWO621tYAt95+muTtcW2sVR/FYozrFZPMLOINVBnQk4MjI3sU04zm/aJFJ57IyfOT1Xve9Dapuf0E0P3WCb6FAewg4WqFMaCGEKngV3iM36aQK5mpqoQgZWWzxrarVUc86LaKhb4s0EdAkZWW4SyRUqNCeOQ/3yg5bYzwEafCpQ+snsjxAfBQ9+n/D78N4CO4qNhiFdBST0cTGVSlkrpPv6AUyR9arVhN6H14oNKItVMKsoKWj7krzStqPGopMDRjXKNF1G9b4a8hwI1lpzRjg15ljeEX/NCkT+M2/NK3CRcnEobulJnTeq3gwwt4fYw96as1R+52K8tF5EFCzB6fOjdJOp9JvzXi3CNHmKooHNHsjPc4SM6KN4NHJm4Gis3lUlTi2zGJxPdH/g1BffZHRYOkC/yyXCMDmv1m+9jh+xmlHRCxU1vP3HrCR8JUGcDRoCvXVXP2JzUKnh22JPUdtTrCn1uDpqYAWxfIM/CyYF0dh8lUqFcz7+WAilnNnRAL2VhTEFTToE5w8MM4SAhn1kObfFzXJ+6ByB/NUuSWhYqUacbmWFDo1UOjAkG8zzi1qRGrNuvNn+c8RghPDV2y3k8x8/KLC9CQV91QplJVUY3wp51iblbwpVC2nwA11An7tRhtPM97I625Xk9x6zDJ5gRyNOfjCQWJ1l9uVJlfRZHZ9MAKP/o28WGkN8k6/EPt+TTBf2qzzUNeuI/ZsKhghW4wUgI988bfJoOtC9foQ0f3c//ywJb7x6mEtNLU66ACFkUpM8cqV8QUc5HehsIYjze5fqXWgpQOzpCOpf4ohShVMbdAWoyzRueX/h1IP+Rm/930K0JaYgdMcdPRc7YZpNuHKriuwCV4S9+/x93YnVLhfhiWfjEEg0gpCjQ21f0oKW68HaxxO0GqVL/CuEbUz5/hB9sahG9nwJJdXQrREQbvW8rTlx0LhSul+P9byqv0euL9M9fCGQT6WrNt3YNOEH+U7/6csIx2EwhmxRv+ZCRWkgKhwyulEU3LJlUbjI90WijnQE/symr87QVEcQzlhTQEwC8gUhAcm+xcqjUlAbpL9wdVhrkmbvP9b9lkVnjpFeRVdkffJmintlspBCi2GEB/6qBNINTjGjYHxWYK/EAGSX0X2OCIm+pOkDVac5Fd+wXgnRQXgften7XzkpDWVWKYz+sHtAnZgJD1sqmHpE/HZLT1rj+PGmumJ5b+AfffOsKrU4VTY36n/0aJbk0wMXlrWaiVmj3UnRqc1y9QVRL5Q2k+Q27MglTIUz3Eq3+wULpUU6/g8KXgHOz38OnJvk9fLFX4VmeG9xHeAuCxKb8P5iF2RDcIgvNgUiEz2R2mln38eA/0SCLbaslOCuDWuwsngiNAxYDtv5owzi/+oBCtYdP/4oYLEMn59LOMn+pfu+dFry/jHLUhRn4HzvEinzLFn/LFSLAv4iXUm3QkWplBbBBSpRnlr35wRkJRhMY/ZpSC/EidGiJGG+JXGXfT/Nu0iIjgayzuZ5TPswXWDji2+RstQcvBWjxu9lfsZ7UzfnPIwnWuE7wAxLcxyMr9qafFAfeArSpZ6LmfZegNRh7lx4ZX53Ff1W2e3yKzSDLS+QmYH0UPgukz/+CZdo5NlYCuhetpVGAAAOTs6WMjUCZM4OJMKmz8B3v+GNXW6yGY9D4MO6vdJQswYIhfdn1nEWcvk0r3vKo1G6m3bjA7Sa6WDwTpuMYdU9LLRvW1d2Ai9is3IokqEpHpGqJLWXDADzMVMLIq4Ml2oufbqkvmE6K6uZf+wTl17BjLcmPHay0agBmXKWWtoUsEOmKrdQjdiGc/ZQlqVIkH2KDyLAWRNsJAFzxC+o6M9MdI2omE5tuEZBs0Vf+kpC/O+T12fcPUIDD5jRIplt/kCe3MMAtZH9Gt0fhcsg08QLq+IyDzA6tWpT6VFFDjXpMHTg8JZfX3zST4RU5Uw+UNMD7OEUqp8Ysle8rYARsZiAMY4/taySsN+FSdiZkyNZ4lmTX3+XlhB+WHEM9w4fbIS9Ai8gRQ3dtPmAgAObhHtxx0RPQ9APqATLmOKVFaQMHTOpms8XkUdydzcAPXOSMNwjlu4F+gKKLuaBIjAZdjlZegQAOqYgRH6ccyrGWXz5ltkzz0AuYzLmVrWHvYujQR07VScBMmUnGIgavsuxBmb3fyMXuF0OssagUnqzE578vprDPNhKFuWR/QlGcUV9ty0idVRtNvmuZw5W/T0zbkak4OOv9KaUiIhKXaRAXKU0EBLe1lhLphEUpPW2wR0yQYkeW7uouSraaO7xwbN0eqJtMnMrCozkcqDIKIEHXH720toc0OgSFymsf2fuOCRIklntXJivdwZyrzEW5lhRhtbwPQeN6Z1A3Uq3DWL8IbOtKgXIZTcMooU/Vo9PhaShia5Cdy556bqJXM4WJmAYTm8VdfL/HSxNeO0oGjPujyj4wMqKB7TrH6xgdVDVChomD0C/3pmVJT94MByeZkaEn5WvRDTkeWjt6k4lcOB9UFRxEoKW0fRE6cWS2wUu8UTkHBkbq5ulJqqrx17H+cmGXw5pt+GRI2dawAtjDAwTGAmTeC1sNcL2PfknmtzNgetrfhVwdmJpQsoySMaZFZ43L2WwwgweY7BisDn71FHw4BwNPLhMied1/sXjy3VACJdD+pAAEYTs3rtfuh6El930FVD2k+EhmLFPkfhWGHm24Q94RvBYWAEnAL4NFopWhALjsz9zjy7LK9GfKDrhowqilOcYysKgntE5Wl1EnwhEPtDs3P5XKJKD+dbeqtsJ9FOhAET6oTli+dE9Q9/YdzpQjFxtn8RNtIx367qxzMMXNV7bnMaptVUNyodmA1G1g/1n0cDiyGGIFPM5StimZOjHzULjD/HKvBV0LbC6Sx7+59pRLk81fZkrcb3BLtVsQL8rPZPwOehyvdAmFJuU4/TA8FBsyOz2XoyV+FczsSVkNzQ6tM+nBDjFm3+9xnWQ+BCjOA4Ws5NoajkzY6go1xipcGTe8sMxa1yUG4zto5fIdc3mo16scgedP8WCqbeFOMq/uakc+o8v6ktaLnnFjPDiyikidxZSs8kHQPYXGCr38mcIo9v89f9Yz5ZNC58TQlU8vTYqS550GAiyLSrm/NQADClmKvXag5oj0/xQ5PYJaLd21DvdbA339d75Hrsc2w45Lkps56Q7ThffRxjGPhrN9gYYBpsDZXOkEIcJXlRlFHNkErsuCdCRAACj4r0cQkmOAjceboZenGnwWA4UJJg+DIjfhE0ZCufoIip0xQDTpeI2hgS/4Xul09C2UDOGasf+fgENVmvn+osr1jLkFoDVfsIg/fW2Zm4qn28wGh2/qjtqpV525V4blQHl3tbwxMhBwD57CMrFbRkwzmGFf+9npzBNZtzVO6+1hwiZu1j7Zbiun8CfEN2Ja5Ta+LU9Zx1fuazjyf++VJdOifqPgOGGAd5aYhFZSiO/g5uJb5JZRNXIEfSYeQpornRoRwLHN/EiMoF5cgQpIoBvzpegE8iiDdbRbfbNxoFABwrE7bLu+TT2u8vvaQh491CJG6ylZMeEnBpPd+n9tuCu6vkZKkdTCNWQpfnn4NCzJOzry9ezNvxsfA2VanyWkSTbVIN8z/n39ZF3kr93cUsBjpqCUuhFa3wdin0mQYAJ5qGby++2X7MXqm8CUaF8lSUtJCVXrq7TZ+g+/iTAMdBAFY4NhT+3nNOtf9hpynLIsckKzLKno8smyzHbqIIU/qP2aAMNq4QxOshSQk6zUGBPHzPX8/5dlEH9Vljl1A2GY/Yfn/7/3CZZbyThuWLDLKtn7H3I7UiN7tW2chDUlhDStxRwLqkDYWlDwqBm428pVRNlo72e2RoWGoPfKiiN+IGeqqC62WfnlZf1c2S64lfva0LbGDNSNaSBgoOK6jKdPrUet5sbsl9naqc/JkwP4DqZITALKTPM0pNzIl//6cCsPaUOReVY7/GYWx7ilQUCly+t1abhR/+j6hh5AAXfaPL5Nq8YZN3+z0RQFXGk8hnD6YnsOkRVa4o0sGhAIGDt54/3Rjclt/Q8yAn938nN60FBGzjxjs9MCEhI4bNM/hUDSFxISpygOJsHPyHwzwgrijFxqDy+x5vKm9C23+IPQbE/L5d19iwd5Qb/W/vU2+S7gMxv9Ua8QG0keuwrO2kCnrgihvlPLdeMeWpIfTS3UPIy3KaLqrjBWQMcJ1eHHMN+BEKbX98oWkiHRNCOkpW6Or53oG5AvOrC929LaAlSXslZ56/WeLxAidnQSDZr8gXPIXDfZ714tb/09+TuwxN5DsvsHBLxQg/UHhE1Pr08s1YbTiFH3mxnKr1c3C6xR3u616AvXLIELWsRIxGjdbtoMaBoHnAWNgYWtoC+jhQOgxF5UntFIH1pBBPtSIMoU6MqCB9tcfRV+8z4CzI3une2Dd6DOjeMrtHwZHa/TAZeY7bMigTfNy15iLTtI14dHL695Rjg7pEST9i7gFG62+wAkRWQ6CePYwD//SwZsPmB6BNemS7hs9sSjE8+eWUtfVXNVKt1NVYUOnCnWtynb5eMk1x52DnS4xcDD6RlPjhC+PTMq2339kc/F6PyI8n2WgmktDahgnQluWrZs75pg3O8tuxNqpy3P9ueYqfAeYOW23OdYG7hnq3sRGcaYLYTCCw2F3p8FAC15FAzI9eYY6cNUayw3HIdh+PRtyYd8BMKDHl7gvpQGLw7Lgx27WfND2oHCZepV7MAXVoj31RAeRV1fxlJuUoFTYNM0Y+gjxOc1sMtiLuZnp4ZWpl4cL33kqfwrEPFup7glXixUmu0VayqIZxoIHd+qUE2LOvZomPZECnyS92ptk5ydMDpLIIaESeKn71+K6mgM9nRvetCVMXyJLqNiuUtgYGTZcenm6RR6F5wK18/DFcR2p8CPr9etA/qyOrF35dVpTgZw8i/brLZylETH7BPf+G8/k1aosrf3eoNnHXgXEhVMw+H6IfrKkrh6zR7rPW3AWM1lzswxgm+dpZ1TaoMe1aFVnTB2Z/BWhN2r4jTDiSUmN7lcVQ9Rt2iSOOIP7dV7RYrfquXcaFvek0C6h3jeWn4HLhwX2ikvQYhxY0X/56zv1YmsEkjmMJwcyummeRK+2OrpzHmVpCp6h0aEA19DrDHmc6vkAs6TcFdVZQwK4q9OIfAgCvj3pa5jl5FKk66vPy1HikB4bwj6Qq/YkkPYFk5qarBmNu0OBIvFmFSjZWzZExaaNyI1ZlPzDHskF1GVqsZx/bYvrl95mGSnnYR/ObRQNLfTDHJ9fmBRo8YNm3EZ2/13gGpfinIvOUstabTfYGU/heBEkLxx8jCTdklA8LLLvCUaWNI0imAlcvfmUPdk/mpeocMPLXKPfhDwENv87+9LYBM1YXgkCiN+2utEXU4yRG4pz7SHsUT3Xl+I36xD/Otn+ydkwOSdRW/HLxsMjh9IX5MXjKkeKRau7ehX5Vz1nOboCm1ICM8NpcY17IuIeTJ9lFaXJRDX7Npu8fiTNbBx2s2U3rtyh1sNROzmn7w87iRP4DvCd/Hplgk+PylX2mkJ1H0onUKdG32ao1gmSvq2nkE748/dWbuBkj/Vjqd4Qv6FoLywK0NEJNTIAhkQtnnY2wgb5z5QPaJ7STND7mtJl87vYMzw5HFsxjmusaE9lQrrPlCAooWrL9rHIx7cQTbCjCvTdpgri6JU9o+WCA59z+W+BJNJm/hmbXBl4XTUP0HCHVYYCukD3y9C+qmHSRDfFRS/qwLaTNf/nzvKMgk+ykK7YzNlKoBuJwdUOdqhaas1kLu7MNl5GG5Tnf9AXP3RYlrk3evjr/AHxhGm0iEHJNwg++Fu8a0JwkpNsbCXP+sh6tbBJqnaDP/fdid9YdJsiZMJBIizju9BxmTAQDsOJzdkJvEJWzm9FQWVfUPXq5gwfYDYr6tGs4oUwuB+nviVuKwC95+r5NrNmM1NmI8PWi2ExEDYPwLgIwP5EE5iFG93VYxZ5ovGlN6jn7gETfAOTwLmW1W6MCeJ0zFbE+LBnfjU8LvQhCLRuPATraCsaFU62JsuZ7h2PiEwRVhHP0wgVAnUoc7vOyP9GhmAcZxBF+B0CRru+C2X4iFD0LbWR0R30bOVhVx+vmqiBKeg16CwtfXQ9V6+e5GTVbNObiQGJAlaGasx9czTxmkCWJd/Czhg8PqoRhLqRq27HJLGalnwWDNyc3IHzndfAuy0uTOs4VnFnDJtWr7X4xW9DsKLlqRF/BLOsNrJAPNNP+GIuwUH35qexqtZ+DlEsDEWXSr3xjLg3s0GVwmFPFnIY2M+TmK8nluOQ/qhoP9090pEmF3N49t+Y565QKOmUJpZMgKqOwooelyIyzNVjg+NBHk9Y2t9rj0sHkbv8ePpJnBYVYiQgkuEbOTbXRdMucjpRuVfcUMixpc2SGSIrPslwrkUqrUR3cbS+ZZL+Hzk2DTz3NBQsm+lWhrvQCFUXrKVhmKgE5edpQ1xGHR8ZtJDtNouEeEFCShYjtMu3sGTrHGEQNXBwYIYXrbJVZrO5fH7piQdGj/bvxHQVHkO1vxEVpouaF1VSDVjz4H5B7x67UpPGNsVMBH5iJDla6fnCTJk6cCwWKDp6O0xKxziFDkQFu0PBk3Ghne2HitqCvl8/CVN4EHttv7RswGu2AytII1EU85HZnEals+FsbG4QO2uR4U25FRUKK8DWwcMs1NUuJgX4U8Ur9H7aY8/FxkH9ei5TEcRjLBPPFc7XPS+DPfF2ksPOM0r5vfzKBGwW7xHB2fc+mct2OaNpcAyoQVxfTn6olOc7fs3hJ059d+ybaL7WNWnzTQ/sV0JSB9F3Fpg4hN23K8ai70KuzdWx8PE2goJ9cVLDBfvpsvkL1JCsN/GTG74r3JIkwfEOMD8cNCurqctmcM/E8JHWBrfLmdq0qHjVznjoEl2OJwt4GdhQxqLFH6E/7AeLBUd+e7CD76LDktzvJ9GdffrYlmm3HY5UeLNyVlGjIpErKaXvOVO1quOmkU/I5QbqRHrXkUTsvkq6dMMLwkq3F6HYTN/Z/N4+9LKiNQM57v63hofAlMutisdz07FjSejrD4JksVItFFyXA7f+DgjjAKm0DMUNsaAD0eNnRvuFbK9h8C2vs51Ka/ZB3C22+n0g5Syy0IMFIEv1kP3LKeNO9XnnM/Fc0EiVrrYPA+n+8THptYTFNYcK0eN4wpKTn9ra5tXUPSrCrCO5OvoDvrcq0OJ1yA/RlX4tf5Ks+OGMG3XM6E4QVHjsHIbT3FOtXWSQUtTMVYXvfBO/1Gin0PtRT7zVVA+IIROEtwQTCAo9G4+vmYtBBLBKCWFGUZQISTx8lbZJwPaT6oytKLC/BuJvBU1xYYLuN7xhA+sXYdTrCl2Ks9N7R3YixkBq5/umnV5Inbpj9idsGl9TvdkpgUDgZMyeKI9tNbL2hbzJe40MQ+siAORvgY9kcWxeEsXou9ElaTr6uLH+sYufbr/JrflPfs79ru0vEZNktRZXMRjC26pwNZctUqvWabO+6gejG3bndRVjBQWh/DDqqvDw6TsjCV8aGSgRGNKwY9sRPlssmenKvXPqWfesrU8WTpCa2bATs+CCXPsd16cPXSejgILNC8IQN25PFV1xPtYJ0dJHxkmdTJBtqTDGO/S+gy9HSachfI2UJnWDFEmb5FEb8oEZ4zNu9hCHfbT57IW0gFMAc9Hi68NS6lLgBPH3RIA42losfZockzVsdmD1paKB9snF8KQtekb9CVPM0GmGIhoT7thbFJOUNwb36OCNr3e4m3OlziKVQloyCKxKw5GhpOP5CmZg8RK25ywE2eKJ7UVJJktIZoUdqligtxvu1fPT1Aod5dvXq6LOSuzaGKq3Q03BPbhRASYYr296vhkJw5mE3qOmq/n9fv34bLyjZKEvwD39DGlp8b20fSGlV2sE04Bg9MBKNXnZnXE59y5sgL0Q9m/HrWyaO0FPtMqCBKWzRTYTANS/yj/IAJ/oxkXXx4sv3xtv1Q/EUSjfQrEJZBK+C5PQFRYGFez9H63hPUaNF7qzduFF+I0137SaBL4t9qWwhBRqZ4cMN+anrEMNTrpU8l4qSQPDF87+LAlWj9YfYX31wXm1/qMBK5egKUZWi5VJzvQoUzT6NfR3Ph6/AnQrLkkKG3/PnQSmvWu3ISq+zHb5peaTersaKhkbNkq3q/ptw8SpxhOv+PVcmOThKObLOPyhSMVUM6Xm2Y8EY4FTjxlZS9lbm3S9W5thCk/uhgLMfW5lJTJolv/wYXulpO1Xq2fOXcTlC1nN6+jZKAhv5G/pkCBD6s/yCRitOpZBz6nK/ALXyYU/Xl9/dlmUWZOqorkET3LJDkPScJ5fHwUiUpKXf9JLBqLGSGht2Rvxw7IbkaHv5cuRP5/nnUT0gw9fi51hkvDH19LcWsdLnmp5MS2PZW5CIArCkLH3FNyvRXmjb9zPpE4EZow5xecHHRefgAW8vriU2GRs0KKdxCp8gxdZAqQU6cJGY0JzMBkbE6o7f+lLJL6+3Ad3pge/qwFjKcVTku7fxwpjMtWvbYC6DqU4/f23sbjjVf09KtqeYZy93HE3LKA0zYbF5Zb2tf4Omf1ckBVjTgR1/+WC8Ke2/9/dc+cEfa5fe5Jj576lQJlKJN1UPzLUzxuBr3YVCx+z6v0cyLS4up/Lju5p9sUaBDBFd3nJ3RYaKLiqErSUKfVHvz0vKUnvnt4953ldBQrkQsZG3xOZHwZu9Z3AtvxOATsub5ICMRx3Yy7IYqPh65E3+NfP47HylNz8vmRyhuyRrezRDTwkyIIl4QnvijypBjYVwynKRQ+8btH5sTjP0HsFgo2GwACTbWys/q3W0ODrLrEMHfZBn0A5/76W6ff/rS+9llaWvHZ2QNTzSbZwMjJDHi5bABEDmw2nyDCsvH6/w0nv7DRXf1d/3Hap/rN3qpOfvEhFQtaHfAmB55WFLtBw7gF9X3gz3WwLCu5V320K7S6iXTfgK7ugYaHDZPyMjM9dcQ2ot61lpCb6nXclFurXSI/qD38vE1dFg2xM09fse91iuiVN917CcV/bAdOwXS+PeipdPXSw4OsSG18pqPIrembjYqKOly5YnpgjQ7L/Obm+gcUO7SEsk+bclXiVatI3hvCM8qA14MMVQKLUXMcwWWpF48t9e1mgDx/E7VDFOx5jgBeZylwxw9eAaCeSmtx2PbV8MVeIF9ec/wty/FzMQF5B1k9nVu8cz9Josb/S+zR8ZRYas5t30Il/WaqJehEt1aEM6NIMTOXAu32goASgzGRSo4Ao4oPo8bazbmAeEPQqeXaBxigz4C9Tv7yjG3HXSrVBH5kxtl2UDqD50fvDr5SEnHB/BIYlfkQvGWnU+JEaWm8hpWy/c91PiDgv9pvXWU0aQz+5CMsqdN4NchWURfw+BV0f4XZUN40snkwTbs7Q03PBJ98KKBRFhqgB2nrgB3BpHx5fQEmfyCo/NQcpmPmKHBsPCRM8qQ6COJ8hvKYMWLp/8qE7hiV8G3XC2a3NESOzmsmvY1dArxBwrDandZlvJPUOSK52RIrHIUem9XTyM1Ig9jLTgshehE1cvv/aCoC3hCJisarurhnsEc3IJKLXDTcptMqzJl1KpXTXt/XpwWlKT1zlb1m0U5NnsYBxFKwpmqd9QkdQKc+MeFkTVKceMVT0qL+TDBj0SKe5gZi2KCXaGmuiCvaJNgA8DU94ZH6oWfgRibx81UH/xUDjtvCFonzlZPdVjyEZDDPX8qW0FLPVNH5hmmtjE6J1OZo/17CgXQf7lhyDdtfStaJqVmCt5mqawZhBkdxRzYgeRJ96AU4vxBD+1bFUpRGL8R/QKRuGhak0ObRTtZ/Xsz+MyvVrpldTsguY9mf+m9sT/Z6kvQsDCKuPamw6YeH518jHWtoiyYqO1lZ/guzAPzVzMMUfrOI3HdffNA/mLFDxUmqt3QLmkpwMT5SbD5wE5/+zVOnmScMkCpBE+5mLHXrR3PKLNxW1WYL8lVRsBcnNzDvBhm1iWC31OJe6aZXE/pnONwboRR7eZ71jbUrmfaienQS0J/ki4VJpgxx39bjtOBmVlKI//t6JbPyA6YPBt2GlfylbkS16q90riN4FLtAXn7n3MA8p/2NqBge+mczLnEC1AjUWLSvkd10R47d8IxygKazPQ66wU2CduCU13BCZrEB+vaUkZW39eGy+0iGn4OpnboMmbs0gUoNby0eLFh6cTDLSrBL03S5rPe1owLZfXboFd1q0+AX5/WCXkF1cyS7TlwZn8iYaLZfzJTEOXHeSPBEYT2aowzYRJLF7KlmQ+564ggoIkebh49+tj17z6VHklJcgsJQ402Ni240CV8kphJ80NRvAd7v8lTFnafWNuq+iYlLBs5wPpFSaJlifyDPWqeNscC4tdyuZB1ZgZEYG4tquIn4BCQeAIelsNVYsmKp5Lc8XYxbJvp1bULb+Iq25RjzeLSc99z67auNxjlc/oyWItoL/JQdm576KbPqTcUCOMpXJ3CAV3KKzvzNBt4uotNR5fZAhOXaHXXlXWC52D5MRDFLfxkWnOIz6MpHLzzz05oBUQiwYdIHbXIWABcN992ei/oMD38F6ZEiF2wVlpqxNiptv86LfTg1oZDIrWXCuDGrHF5oSp47BKOJbzPmApHpq32XA6BAFQwC8gV09aP73FaeqoHfMuQ35VB8uG1EU7OnTLvb8AMLGXHyIZbMmHSDscnUwiuIzhjWhID2ShChqofCezpAUbUcD4iVDo7i5sR6vWaPTpcCrkt70jBpaAK5KMSIbYr7lfRWpFzongqwsX1+gQJstArEYh3RC7bGTr0sBs4VsTxFEOyIrjwKCRAttEyK1sBbESklkqRtT0ZIsZ0thMgtuED2NtLEsFWcIuajiqgbmShFbTME7nQGPDL2GCP4NG9knwFD1WRgMJX2liiwt1u9krTsL8+oU+Xan4n6cRtnojclRulr+LHSCRHPEVgNWEpXeNfiYeoqMFuEViSFNkGt8Zbl4PgOQDaUow6sjErpImWTLNVRhJpbytzuRHNoHNDB3pessf2WW7V6yMuqbYXh/kMjjLMMG77nFS+ESJYKSy1LbZ5FMNijIpIE0dhzdrlsy2C1g7Tke+T/L/KW5zbGaqdRn5Dcwz0f/P7a6RXJ6hZ9ycGion1TgII8hrVXixRhdmGbhf+Lfq/PwwUw48alUXZbSmrryiDK3PT196R3zLOe6PbMS1dZ9cnkM2JbBf2bfwiE3sMkRjY9EYfwNoihsFfn3iMhEEtxRGhYWHqI1mRVg3Rv66st+h4xd+lpM8wWbice8wX/nwG1dMK8KDW7ON3JpWA8lU/2H5jdGnpnG+IPtzBDNBuOVDnsv1EwmHFhJ25HNKD+QaXE2mbilFft33Q0shYj4Ex3iG9Ad6qb8GDWPncEwhl0SsJxwkqjOyg3uHYACa3fsA0lrB11f/MZs4Y2SzeQ61RXNsffyxyn+BIGJo790E0H3UzPPTgYjwQBPfVdYfyw3o4bS4AbJWCdC7N33N+iuCTmxyXVmXXIQ95atvRMdoZDEeJX0GSJGlRV+seGUees2AFDsXBpNDJgRjthqxRNZdOghg43vYNwZVofNVXwXOR8leu1kgzocqdlVqUbXnsxL0i4OMZf2esWKZqXC8seB7lYyXxd3gtxekQqNCWLZP80t7zuZaUOwbZ2hy91t9EdQ31z4QQ6FtF+UphYSjpVmlfCtkpa+CmuM/0t+SOO55u+HAAemgTM4jPyHCaPwZT7+MBlzaSarePWwShjmRH+gCP+bCSSlnc5eoaxOaoN5Uw1Kn6ut1syC/LPRo3DI+cvLatZg/U+3KumDGvOgrx51mtkM6YV/mrh+ZXGFxHWflwEZci8rfNhYM8LckLoAKjfgs0zT347FCWqJcTy2ibztWiOuE4DcVfwx7e95YTqCfwHJ6yCeG6RT/PxO0LJbbqiQlZalb5HRAEmaUJZYsojb/kkY8SH3yBevAznzagG+GjXvEl8BiNkRViID+PkE6tKizWXpe+Z6VhifqGom74lVbgVAEdb+0bktOYxBwTICTfp/FiT7autBeqOE+GzktRQOhBGDYul4ODClNGSvVTkTdly01dmCl7V8HeG5T3qBvgjk8Pev6E5fkJkifccfpB8PcGWGmlvHkDrz8HLf/oXLYdZ82K1wKLoAlUE+919wMBmAYjw7sm6FmYxQII2hfyq+qate0oFE/tqk6Bqd3DZVKVw0fpPrrWUoGIqFhPQZQHYK5orSndQflth5JOvnPomiFVYpBq/DFOju3GlcxRrwAbGIguoqUQQDaQqqFgKJR62RPJVplK6b4lE9/Fp6JYLDzM0p7Lk6yA0iWWKayoj/V2feCm7CSqG0BlaXCU+zfS/WYKbgmCxctYB02247g0otja8GnuaLRN8lObwBN2tBe01BUtaqfs30RJf/lOeht3a7+is5+SMQ8kgm9+EkDgYJMLCUPWFePm0GbMVLUWu0NKtWAjVJZOdHhp2bgzmwIWoSN2N8XvDGpv9UUZBrDyFMM6Eqf5UhKLIOprCZh1j5J2ES9y2hF5brgzMd3AfqeMaTtA0a33Iu0/Wd+7xF5mouWLvjsVE0iCA72HyxQCcJ17E7mPaqwGbSKk1yVoWOCsX3MbWsV8kHd7j39xKvHX/K1nf9ipuXMQ4yD5SMs45HEezfNH426TcohNczz84zrsPRbqypDU2x6MtC07oJx/7HYMppf/PBkWykUAaGazAju8pCHqroXa52IHZlEdBKJqBZpTKcMAQfeb0ZqxsZSjZknBtUtWMGXNwi7Gu7EjIDq5V5WhUq7fodpwDGC1ygXRLw6Y6ksFymhB9l9cfP6nvzM0XDMxt3h7h49PG6p0rE9q+3p6I9VFphZTxKyFJm8/XfDHCme1NWew35DeKETJD/Lt4zTfyd4AN7lAUdEHuty3eQvji+zgVHPpYDJfj3rM/5frewGi655wBvEaHZv+Zlmo0dkt/yd4xf7Ds/iopwClh1Z7uoG5U21Q/0DN6SH4YU4plgoxtgiyEvTUFaYyrRI4ronicEJT64rIOXUs+iFChWiS4i/vJJYVYXANEwbpHk486oaaOJf4Ud2LJgozLcKcJ5mDBonnDqmhm4jqep2kyyUE6pihbLFUP8Xgis8yfzCB7ZR1VWzDgH6kd1Wf4Q4QZ7t0lEme1sLTgDGWIqNjI7UUfg8Hme2WDP7RqRb37s/9wehdJEstGbK2j+x4yD9OE6PCBzFjFnYw9WhTtDZFYjrCa7cBbJIYzn+UA005sl2JDousnjcxX8tct3fnVsH94vmNlHvcU9y559Hh0GmWJjS23Jl3CplgW71fzv+pwhUqAM9QX3w4bTwDd0nCsUEfliHYiHaVDp+COpCMbyw+9M3QBcmsZqK34MwWerE2BqjXubSHbrfAZm7DeWx1wGuKk+i+ly1c7Wr1WTKLoKYc4JvPqTOgbcbiBuQKxhqcSfJ7+7HbuehMjqPFx9rcrkSVB+XWk8zDLhlKw0j4H8DOFTK6rQlcaWUK/gKvgyInVSawBDymugaKED32YhgTu2ffYUSBbg9+MHUFacUSujgGK1Q1XB9ZRHXu4h69DLkeGrfmYKT0DBML3xX+E6xQYG97zro8Mu/EzYUYGfUsdw7o+DAEtdBGhqsw7cl17n2gnh1N7WbVxJr52QySohWU2BMEzIf10kSuwZFIWWni/VV4fnYtm+s0LdTR5oZUUE1BrmH8ZD5Z6G9Q8TuzWSMU2RP77+o/xFV9T4/ETq+QghdnI7qzHsaQs7m1lDpaVdox1Up5p3hpLQm9iku2vLnjCs2F3j2mFGjsOX/ZI7x0TE5dJk4M3xksRlT9YrEjMlkPqpwK4yFZGmIVcD6/jt5hgMaOAC2DQJ97yYmZJM99SPANAXZO0ofIh9NdoB6/xGB9qo8M5Ccn5Uah0gukiN7ad67pPlyPaVXZZXDAvUc4lKn6T/zYJK/VFhylWaTmdAEFNiOmEZJOyhi9dPNN7WQfhZ0+xRyCrJ2YX7eudAsFy6ke37QXQ6QW6YKPbKzz95xrtlXPESwplUu3ZMSKuwEWF+hsNSNYGoiy5Yqczx5V53i+As5NxotIHIH6usdr2IRQdmyNbimtWoxeqbhOxD2T8KCJMw7h6NsD5XeD55bQcTH5vUNAY3RTn4BqtEJZS2vCztgcJDRFvoCXjFWSzWJO6EP9NerrVRLCY/dlggFN6IFELhqa+otWfXscemOfpFtf3Sip6VTU5t/W/GuxL42awYpGPRb6YBeWxgw90CkUNRJIQwY+dmFb02pcAa7HcjP6jql/5JCCoeJp5LQ3wf7vorxO1swAajnKdTNA2p3Dx7a4NeIMsNqEPrP85zgP68xz8+/L/RnWZO67ctAnZ+Ctvz/hZMAcsx4Ls4VcZYwFfGv/6xjP8aXgMcF7W+hhznZoM1d5+ZBNictrTOutDUrcwTq1z9vhHInA9jCOqjk0/Hyyaf04OTUnQYROLCAKfJR3NVSRbAbWz5wkvSMwsnG2T4/JRjPxQOOpAB68KeJld2p5Ph1c+d9K/lQzRT7357HDzPinQuqJKOJwp5qtDl4mOuAwSt1v5q310+ge+eAG3G4ZpOw/MQkxL3r2GwBsY5D3P5xqRTAouZJ03dkQ1bMgxCgDo3EfFEqyk0A+vqRRXfq+o6W7cnkVKDmiKKBHZ6iVHXGUVqh/DsjgyBxl64+B3WAEwrf3c9BKVnsRA7IHXl735LH/Fi7Pc+nY8ANM65gXL2bv/lpR7zm70U/hVfAV0YrrEWZ1kWjpDjqjh/JwzZvLwAkmAloW0BOe4WpdDL9oOj16oPRat+aQPGgRPkoDqftG1DR8LJoeEAvqb1MvXy2LUI/1b8Wg1kqAMVqi5bFe0XUsY2It9ZUNFBINdxD49svFt1rYVTClkj0aRgvknCPBBskzI8UHEMydlsbDrn21urHg0a4HXYH6S1IGpCcWBXSX70qpBG7RAp3EKxGiIoysEijtLLkcfkPh+bYEEYtYF2+FUnw+9JR3T/N94j53k5EMwKNB2oZZoHsqcZ9hkp74LNsn/m/rvPo7Rpp/gsUbJo7dEQ5+ojrdvhLadRyToT6uJBSmJpwCTRJXQ/pGXZRAy2LOiDb0vqNrdFof1TqZHtoeqg/qaN0AxND5TPGg1h4bpNnG3VGfLE1YBDTXUJ0UNRjGeCcUdQD5cwpTeBq5YjHUR+7AndfzlrbbhhQsEUfoevpwhSOopN5BCCumpuGfGP9mVRTNNyfgTFrifbUardqLyle3gByiT29F5BQ6IcHAUZt2hKLkpYnlLzImmuj1i8Hkc6VqVL5ZisAjUWqpKyDr7sbIRz3gp799YQpp2J14+uyv8EX3ZHQ49EABeLCdpcRqacAwFAVjSLalu1BQTkGBcthEANlUO+RZEQTJynUhJHnm/g98y4wG5p8r8a+poZ7Ayys1H6F2K7KoonLjjX+QnJLbttsplqzYhGOXbZdaK9KmN2Ne8tFO4mezg7DF7H8N9jDOEEoySkJ3/O3DOq5vPHyx5bMeGNtMrAV5aXJYXY8Nrq0jCV+/L+GgJJbxSj2M0aTkESZpVT3043G7SnNHEn67jNg674sFCvOnX7U300mZCadpL7clj59EMAX5TppLmhmW74mq0FGuP0AcDl83uEIo80OllFzOkBFHUJvg9ioarcGrUiZdMx4CA6h5WquGnaLlEN9f7B+v43NOPMS4kI0WtpxytYrGXxSexRMUb9usSbpAAbLmZ1wedE1xsn6RbOBAk8TviUSAvFcJUEQNGAdU0Lrzxk9PHe8QATm4imXVJNDZeqmang0lXcU+Q3ISSE2FYK+VnX945Bz3TCMN3Rzw4iTiZ1lrIFbDvMfWQ+owmSoy7sqfjwEopPsiEUluMNFt+UfLWIgwHYJD6unmwTAtjJB/m/Fp+1XT2RgW8MSJe/zuPC/Ki9IAQU0Mrqp13M9ZkLF7VgtI4otZJi5Wjd2CHWrZmFiqCHaIiyucafNG8hkM8USD32Isq/ZKESkfE1Mj5WuwKS5Qg7f+1rN2q0DrSm7+OdtsX58qQSUETybXTlE0ptn3KnnN/GCLUi3GgGxaOFvyzbaKKxlSZcMZF5VICBBt+lxb7xDasLEEzvUfQuAUY3IzrhpJiAsLLbqCUXp8KC60d6F2L6LXMIlECuEr53gHYNmvfr4bCmKW+711FnNqhZg8fQgEc0cRIQ33W7QUf/RTORi4y3z2lq8kpULsY8f3AzuNXl9ITJ3PBwJDCpk+bftR5yVEf01dJvTyksAIEL28phGuSyVm3tMC08Vpx+mmQyVhOTV7vSSLqzczFtZIlioyu9VlCaZ8Q8mRNvyu8D7v5Y5g9mSwWGl/nfHxg6hZqdFmukkXhaG3V1wLbKSUsLzVnex8tBaXnW6739VXJ/PDL4O8SVnsA97liy+ZUFT96k3o0QcF3/W1CycbWuVGJ7qaZy6lwy1B/eY0f081X1SwVgyppHyomu9teoMveIQ+NMZh9LuwBDu5HBquQbndE0qgO2g6lN6o3b9z6nqWc1WOgMLEFbzFSDHuOckxUEVOk7uU0VxQuvAKN9UH46lyk8NNAYc98jseemzSs2BeHPDK/RdLMe9MJ0DhYDlV2Uyw7DhMNZ5ScJqE9Ko96Y2s8e9qK+vB66a5SyAih9hM/ExQryeKtp37ATHMcUu55V/h4CoWhDNXMZHSqBWSMUUVfrGR626RRgnBLZv6Py01gjTuXFzd6cmIwVzpFZcqwDhVmGa30jNTmTnUm186frFOukay/lRlpY5ej/PhYpdzJjytr5bUGPV31U1Gx7dhoHq3rJgLQVEBZxiya0he0QnHn4EgPslZrs4cZy6JzYFi0kecmwqLtp1fGSiJOU0gtYmqyHIx9zUmOoa4MpPUN/1JMS1Ref3n3HSML6fEAobsycILk9f9CgNtZ3tbdX6ZpZ7sm6aNt/WqI1gQpihMjltGQy8sZHG7Dze3RL0wGWDNSgc2neNI7IvLU5MsNLTcibORBx+OaBIFTCtjqdiG6YU4nMwK0uzq8qOkcopZu4y1GYLyfMDFMRYahnMrc4as7bX4Vp+M/UGZhwYBPB29v+p8NJdBbrSbtRerbR2kP9lhAxI3ZV5ROGCtJM7ks3J2bdcHRgf1mXLb23KTJHkeCBK8rG6aUrBLhQt8BKQTK5y447OdbR66TgM+PFg7IjEXKi/qxTy1+yR0s0kPzXWv7qVa4pH+XP0DIqYq/Xs8caSf9iUwXdB5uRxf12K+5a72F6K/S7cQEieh86b7H9Gez0A5I/FQeN7IQ5eq9IPmVDM8CGdMyZ5azDdgtQu4/T75dGOxb13EWv6NfV3toANq9AHJE/13vHTr7wg3LRhwKDRkTfeAcIluynEw3OZHiZJsXPhWiocqNL8niBYJ9n9WrHNeRLrdtcZr2MSA5+HAzSzkvua8hd3MjnWqDCNJRukCS+5nSjW/sfM8mQfOnf7OftvoJJ5/6PLUzH/KdiwD0DPOIHTMtoqqagYQKSBww/fFHkPwRroF6xySUXJC7QPSxGWbckXIjxJd+5GlT6tas8X5SpQZDozIGniLb6bNuqK0kVDQn3yrKYf/MkHoL2l4+12ghoiazKDcu9PihTD1atfcdheGHNbmbNI5X3XAqDchMagoYOQaCKUq80Mjp7W27EFb99eoIcUbwjzBsc+ZTJXmzg4Dp5E2Vd3KQ9eDPpvD2N99Csd4cLk1fMubSOSMS57frOPpy5hx8RAYOBghRkwadV1SAhZ2u54ydskTNl2MyyZukESQN3HaNvpJj1rmn0SHl9ETBQvFdzD/Ui+ddCZMyvpox78tiDiP+KzFa3cti3apPnAJk032vOJnRHqNbaMspS/m24w39hdafVheULOBAzPuHVZuUb9iMwrqxQezlYqbAY8WQ3CMQTA6PtTnNHIOffCzsHtv+aZzW+qmb4hE1ubR1JXWzPf//dFbb9WB1DlGTbrpvSrYJZzRF7vaYQ9HtDiSxbm/HHf3H6A5vvOeqQj8VIwSlEIYmYwqQ6u76UdIB2qTNQqKlKA5LDmVS4RXlfFfkSzsuPq9d7NT3vCfm5CktYbQ3IA04wWMxVWSjvirLQ7xvgMUMdxINLNF2I0AJJawJnhXOkm3vmdPy9tFY2gNaCUt87/QCG4iG+E/tTdJTx3Z8Y3gfva/flc8TmbLxvGDukhAghOEh+iqt0oKthwueDipU4X3z1010l/B8OijIt9haeV4231YQMfZ68sL9ePalJ9EENtWZkyvfZnGf84ppz6fvN0dZsRrxFhmWHyV3W6fWI/KopwTjRUI3Ax7JeW9aKAq0qnlBO+kleHaQza1QYJTVmutKAzl21CHiYu5t3+0bdKMgBQXdxxq53AQZjXQf5UINudaWXQWujT/xqktmtV5SMULP1OtmiWA4JxmM6GXAFb01InKDrAbpZW/0Pu8d9K1Tr434MPlRzL1bMv6yAbd58ZzKRbi6rs1fGLo1BoACfxteTVSEBwqau5HtXuW0vU2hMIa8lF/wHNJdPirs1sO+/PfzZCixxFcq+kzBjNo23C4VaMyRbTj4WnZ971b9zASoweCH5G5i21PIrd3x6I4lQcDle93GKupOCX1AQEnU4ug4ZKh7h1Y1PphiRrp0XEX/mK6E5qzOIZgcOOXH8EnIqlP4jtqCopjl4K4PwFeFywQKO3hGxp4uC4olnYGxwm4/pDUBWaKLFG63zjTL9NX35nfljCjSbrAB8F0saVecAdSPHBn+y74nZyuNVW0OVfiXDT1vNuxDGdK53Grv2moo8XW84I+okB9BaDn2urUf+9/JTwc3owhIYd26rCoAkPJGk8SNy1R5Gg7F/7px15ZxYwVEpXAOaY2dHtC4/NGttorpOStPYM+SbfaRoKTJKFOYrCMJdz2dYdBdVmxm8H/y9/vhFUM06aNW9fnfn1BK+LTCzWJdY22NMlDM1SIM4VD6ME7eNBfc9xLRiJCwjYEm4aHBlF8N2/8+bfI78KmXI6MrFcASxWZE7UO8GF6nkheKx6HLoc80+EfyakfJiR9iebxZc+G4sQXq+6TqlzABSfevxVdBhmmSj3BVEGZ1/yL7pEPgUogUJQXzxeJcui2u/7eYG5mA2KWSHoKjZot1lWCGGprib3bdxbV3qAwHGuyOBb2P8ZvCnUj/Voeh3gwUsCr6tsRP63EFpqpc6gMAIxpi84K4MO1WQ33ukVfAu0QNc+U/T0eGY3jXNVkYXYF3pE2+36KToXx/3ViwfsU/Z6qtsf5oYCQQbe1/KLCsiv7UsqMn3NLnLhBRLwIksQxerVfzWUDazzh7z5cnnK6LuPbKvtOuyvhaKZhTqJnVF8VBtzOQ4EjGcUZqPyaFVPomzbomWcQtkh7Uz+uENxjEwoXBsJseEWSM4oMj78er/tqnq3pm2c6LpUDQYujx0Be/gM1pK5yo08KnUk3FzV19vdpRggvoHchJyPt5GnL9lSOWP5L42RQQbvdRtNqZLliTUXWij44Zgyp1+ubmY/F+bHlG5LUDu/VS6gAi0QQ88LtHfkmSyLRLrwlaZ3eAMyFpIc+eX3NiyGbvlWx0JAGSrTRaSdaYxsqgYJMd4tIWvsTbXCxgDIPbGx9FX+cdlnnsmNGZLQXTKk0ADWTA6Zk0IItLQzoTtwgFmqHLWXLZN4HA3Vvu9x4L3b7doEl35Ab8gRMyncuwMu+F35wl+hfzAyluvN3D4tU6dIcmxxx/jg8LzwWs/c4Tz5SYpY915L9lRlSCK/Xjt9ldiLPnnylO1WYd5tz7cECYE8WCKX/P8UMrptAwCAXWY7IYQDzGwEVr6ARdkDkbHhRYENBL/Js+73/ix1v451ObUts0/jwNxSAYkxFrWuGvf/eWkasuOLQ/4Hi3+dkwLSsztZAVPmHpf9syO1KL4oyIfDi6CO3tlkXUgZEalQ9RRF7YVXhIz7oxkHG8ZUQVoV/2y31Mtav0w9J9aUALZgCdIn89RtwgeWo5mpokwZTNDFyIciT1ctN/oHpbF9MH5DN5owhbk2O+3Vlqsypd4Wcrr9HD8Mq5/2HiqgcHzQeAk8/yDWYvc56eoPvm6Ac1N6TtBQRBqoBCw/gRdWhpfOBGUVnK0Z+wnH+JzdUcYUL+tfcCC8ww72ahyD0jAOt8uis3rEqOyi8HPF6YwwdwF5qWXNhi3YGqhWcsS2CjtBe67aGXbSZaIpCoBoysX1YkR3AAMsOvBrazCIUR6KJvsctGUV1D6rJzeHGYWUKSqxYYCZM+fzmbr/siDTSM5IKAGMFxqgR0Qb7toh6nj8iGOSKoYmSko1beYZ5MIaLcxbENlsrniJVFBljofXm/iPjccRJD3hJzCMQAMFmlYD94zqpurV/ZcUrmrr5uNBoTN4ys3ZD6dtWGB1GiFgFTIeFiIedeYpmu+w/TbmUXvdTgFDL24z6Kvjfb4ci1Nkrxj22gXYvicnyCT6X5O8eu0fcX/eH0EUTtM5MTUpYpRMx1EGAkkv4/k2cvlxCDdxV7rq/F44BHqB2ceCTAxs608LFGa7ZR5/ldaljSqLIUhNpMf2/TyUOsE5IDWWLxFY6h/oowNctfbQ+d1iKjsw6kC6f4j7FNLHXRx+HMKJ6gPTou2l3smTAqu4XIZVT6ptmh5ze1SVkq7EXDgihQ6imWOBwjb6yJ0ZJzeEN1wsN2g/WpjjUvAMZGnRJgMjVQ4qdRwdcLb28iAeiIE1nt9KoKyI9wQ9scCNNz6ON6f+KjnVWp5Z/Is6/9SWpFca9/zLrEsb8huNAGAGmRM09jIxWhQSBcT3paM9RevjAfbEYT2fYPUOuLCn8OTgVP+YlLBH6lxhG+4D+6tSVfmR/UU0/i1jsMLw3aM2wyzInf0HviZLDWcHDZfN0IlzEefVrqqXK185nQzQjABVXuizHj4Oe+3LtRJXQ8CB0peWWABTPyuXTr6/EI00+bcnnYYegwXHOSu8stYk0LcaRGWKw1B4FJAlwj55RnBHw7D7Wy4TxpEtYptwk/hMKpbCzqba/w3MKsVxavnt3mk1FycJwhvkLqKcF9l0QJjpzBE0oVYNq1KZ8XYiTgN0H9hHhVxOwYvEswNWoKYLDoeQfwbpiTrwLS97PpFwJKYeakqV4ogYJUhXQaAnbEFX9L3o6UovjIMb0ttHDAtlmdOHSUtkgO+oYm8Edb38N+BurOyfyVyyy9zoz+IIin+26E6i7Cijdx9HqrpGvxDS30R30KzHijdbjXemFBfVaKlagf5LsoTceLBuw5GMGqnQoYG4sWBrpY8hPtXfI3/JS16umiTSdPsL3vxseTUdjAu1uKinbWkegMkEOYU19ZcFUgntPgQywhHCRB4INAX81wBahcbPWc/WFDhsZg208/1Za9Rm1XFhe62apeAUzl1DYAZZdSmmLiGKyAuS3n8RiDh9XBUuhRgoRPcumgfObCCH2GgxP1OhDEk79F3ky+497iLMQsmxb85G1+s9qKMgCcFQeJfEtsLkUVM0mx+1XnthvO7LoCGy37dB1XvCdOgMiqq6/AkD5U/UfrDY4xEH9eLZeHEn2fYTToTH0hkZOvMhZwP5yG1sU3Uy8zLdABtzIEZgy0bCvyaAHuGdEjCuW3kTH2wdzT1m3D/qgwdO9PzRwPqmG+15HsofV2jtzmRRHfmpQp+laQRQl6xGejeShercZVSMUfLt8rCPu4uJBZnv4hLUrN+X/IoTzVDiTtUxey5nbLr01WrB+1ijWcsiWVWbCMGHS07rWnRxj/wkpkw6Ouupj6xI89Wx6rblK5eKzzaCeEj9yX3sTrbaqYiF0S+wV4XF4AGWZ+chFVfiZfKYAL2Nhakv1ewM2uvVEL9X9rdfm1F7jCLH4PnKzm+/1U24+hMJYmqacdpZn+YC/5+NHyH4nCzR1B0VcB6vINWLuVSwuY5Woh+hj46eG0cbtAOQEdqrCBS5Pm6rivGrT+QVMaMJHNQuizqx9gAAyLfn+FHH+GYT4aWtw0fo/CoVtWtbJJK39WmxXfTaJfYfPLaZ3XzbjCK0lcPxYTBEKs/ov21+NWf2E2lYXp/S4Uq9QVPcuNti1Yb6DrQuDEMCc9NVxXMuvybPnKwtu8lqEkqYjdBbY2jLdH11szjfmhMlCR9No/X5WJnJE4Hc6Gg7jEBvmrxVKtU1AtrNgZ6Qdq+tC83kx7o/bNlT/LqfCcYL+//f1Lx9CD/97DMjJrQxmtIJncfBRMgCAqenXaI9B7n7SVkzd37XnrUsd/FugLYhV4/8qWOAK6+oKir/9qiHeaMVOSOZWBz0O6aJgzYuxiG2H2+n2xXYmn/umrHmwHSkJ/M7F7/XhtubbZITeteOW16GHZcy65uG0m6n5d6LWatD3Dr0bioZwP+WmTzW2qr6Bj3ZS0KvWsqug2ILX57gunXYzlG/291aK77pc/Rwb8gtae4D/teC5RSnxm5/ipbpLnKC2+yKH7NaxxYmFaDPtgWiCiGjkPetEnmd1VvWNO/P4A6DqE5HATE3l2JYW7T7JNOw0lxYhnq7iidYJuuATt4GXM2piA4wD9SpEdyWcGhtG9/tGKBXFt3ZLherXEaF6uqq44q43GeEBopNYhfC2335TRqyYG5GdcYnSCbeeGzaxGSsJNF8tkvDk0mndazpvPBpdqePuCrIzb/Tymv5HW7MnqsnHHYCQlH32EYFh3Hx0T1n2JSRBoPvJIYNkXhKoRddOWqdgcitYT/qlX1Kp6inRTPN3Yfg8KG4DG7IGEmDkI6dv/qs6CN/8aOQD1UT+5lM1hVZmmjzId6gmSMfVBveynZCBGHq0+Fz9eAPirbqpQtOFZK+KbLAB+bVJsMJqu6YVG6KipQwpNv8ghUol6A/Msi3ljLI7LS8L+z1fiQQtFKDWNKHsHm7H1XV+lCC9fCmXWpflzpmENGi1DwQy7BqRU/STh3/+LMU/pyE+0zBRvCtCusvhuumtV2+twNzf+Q6xD86uRbFR2CfYTSqTyAtpFmzPCStB8L9J5NDa7REq8p7GuVoUdvX0qN8733lHk6NMHwRI8n0PMk3uS2Tnq1fTFJtC4aW/t9KC2t3U8fa+SLSkEY/n2BXILgCshzrYpn+kkeSgiM4HBU5IfeT5Cv5tPxCqimDJQf+eG6JcbhjdGTMpZRhHYwcaCanHvrIEc80OQwO42krQGeK0MlA2tDjZycVxaCRokmyMKafmqHC2jTbqSexVOrvzlsMDIUMfsxr4XX2z2vXvgzVGLYFkQhU7UhqnTkD78Sx4m/I+eA6YLQUF381+IcdCUibWL97Jw5erCgLuFdx6p3Dzijuet+vwy8sUb7g0a9DAVvvKX30Ua3Uh1IDiwIMfnig16iUsyjRlHLu4IAXgWFAJqG8cUH9YjMNdjvXxKkfBYRyPBSBXaf8sgx6ySs75TGOrxoEzo1aaxs8auwYQwDoynAjzOU07k9MhnTZo44ACr+w4wQgwqpoukogGTEl3lhqvr+fsqTVsbU62qD8UQfiSpRNxzjHpdV3fuCLTX42rBriU5WwCaV7sKAIdk976LmKXxLVok3RALYy7LUewLcyOmE4ujKUqAqIag/9ih9Guwid1foYcXxcecuPTiyPKWozDhaMVgQ+E5biVCk5zrIRGhrP5TDIm9HR/GO3HfGOH1cINXS5P2WlAsELffyrALfetz5X9tMzb7FhaXbNwhxq5rSkqvEztFeeREtBk+GkGTfarlXQscKd0BsqrpK0qrwNAtJqDEB7ES9OYWUN19EkuzshI3CxmaHXSnDRFYwO5k9zYBAs/Cr5jE3rWI4ho/HnRwx+v+gMarFT0F+fo9Xx1ftefxmKnqnxOyFPRFnhS7l+/+ohy15NerSE73WrD8cw7lYAVrR/z22i6GEEQZuo0L9wU+uhx11f1B9cCnCbyVulWC4TdGKWU9VF8rkHZf9ASlCcY0gzRdzHGJCnh//j1LxOgguIExcnpYr38Btno6R3oD+vJq/rlDFnIwPbtOj8w/t1MnLE9sdv4cSLVa/icUX6KQ40jFLCpCTPK8XJygW/vunp6/qTd0ruEBMbvK8e1V0osToctnVqMel2teJQeHg82XVv7KUebf88924ss8CObD3pHPDex3HLFs8KRYPG6l6fxz5gLt7IbZ2WwGYKodz1K3s40rktGVV9YUPbkdj95cQ19D6GCgL/2Od+t7XEQW/WTJ1RRscooFzLYeWSe8v4sNI+WLULNxjb3GnHpGaEBPbzCaHLxC2yGevWk0Gc0yUs7VLyJnjlZE+yYET1+I5skSD7LCoCS0LF+myiHZ+87Mt5UMW8WQyJNQexWajxM/DiYLIoLEq1+ls40tdwGWMUTAP2Lg/6Mfe06BtvW4pAo1VvMMatiU8cRV0Bty1zleHNwlD2Rt/ljG2ldl07pWqaBXXzD8Um/7FytGcYwz2TQ8+gtFPbNk1doAlYz4B8uCCiL7MwRzsB7g2+H9qOr7+DHmTB/lTgehe1C2MQtoXss3bjdYDqW7xV66GAMk8fEa1EUYGQdwJNUDebi+5lGg0swWWChJRrobCgwy+6C2FZnJJEotYreVFSC1/oy6sqC8LHzTMhukX0gqy1gRK1OIqmlSRZDGerdcgLc7WNvKnbUCKywgp9O0fdEMj4F6N92jtJ4/BLe9S8o6VfIbev/mOgRnp13yMaT2xeJ+o+3ie8NLhOM8Sw0w2UkV3NU+qDLjGOAeC4KglvHa4xhkIWqdNVQRCSTGb8UZXrVYL0WUfpR6gcwtGBqSmkaCI+7sy9RTWYLe0posdUt8uY9S3IPRPXBkpVjVnsjIzN5QCiUj1Ga6Io+1aaO/LZE16gY915cdisI0PM3PuXdJT7umwSrUWV1LP5liBmcYulkRDUlHqxsoVSRjeW86MgrGgMWSb1uxLB0/eh+LXs2UBkhUWFVT3vu5GqEyv/2T4BAgoPvO4IUaq5n4p5CqY4+dXwoa9AAETH223+RXbG/XrF/EdL7uUsKTt7mxARXwjMZWnqp/EvKVzqFwNgE/ttIZqLAvwqyeNvc1uANUkTzi3PE0HKoghaMPtTQiKsud1p9iDD1uMhHvX6+tGTcfzt/98r0x53xGos8xpX5GTye16aREpugeQDL7ZIN7YZk5JxEFuPoXG4jRzlqAsWRH2LKaPo0bTEQ2ojrKvTdY+5YjjQjoJRgcIClT/cqDTYHWJHEbAQI8ZofH52VN67Nkw3ueMtbyshbLKvrlyDEZhiYrm8fqANCNDpAttFrgpn0WFr1qeMHtHXNh6QQkUuJikmshbAZUY3aD4ay/tAQwh9AVTa4qtDH+Lv7kdFYejRtJOomlZKkOB6HDL9Nj7n0DApumeKHb7KnLEeLqmcA2gzRPK0MNTvYNTRBz0XMgHutOF8qE0FmgYBU9zyjQCVLdxd1i4Xc7XlqHwI/XJ86Oa7wMXuZAsQAQLUWLucO8nSwK7WPtl8iKm+Vmy7ugh/z0rja19KhTKKxPS2OKDW7iwl77Rw4OtZPOM7oCJ7E63hRUEIRzPqD1Z3dfHu7NVLY4j6Ik7hV8EVxKjLEf4evr5+Y0g4V4qcDw2bJYJ+FGliGBiOD43uR0izPprNSywxdC4hQNuBGcuM9F3d7kBAhcQVYmiKiqFrzPxFFJ/nGgVf5QMKjpRMpsDQspk4xDS3b74NL0zfWD3RUYQI4q9kq7BILS5CG9VqGIQikqW+P7C+syU6a+eLdtpiBj4iTydLn52WgG0GG4Dy5ZQo5CivBDLV0gx2R30Qo61foqmhhzV00W8kYWIgbqRWPoJBx2CMYAEgfL3LhSRxL2F1CXdjbPwo/WDafdk0dv8xOkDR2KB6ZIgN249ae7MmIk1E0ZSLv2lkL87qiecoqvM2rSuvlU2/050n8fyjnsYIf1wAgfq/Ye9CQDXw+cvo3XS+j5wreQTtPGBCUNswtkrGa0o+3NGM8bf+cGLbLa07jdhIeR9ff6T9jgRiJ59ZzgPiEuuLXMuv0gt7ZGE3iQCWUYAV/iZKHRtS9OgSg3ou1y2S3j4DBvt+4paw+SB5h9D/4Gahs8hHnaCelf3jRb0/eDvdXCrzoTiozobiaJWT4f0oBBmEsvRrJtAv5Gcs8+/UAX+35jAVMGeBJ5XuqelsP+rR/wNy4jjTl++mzb9XPFwBtgtGHWcO9f5Fu3Da5twHk5lGlPMHelO/aAZ5AdLJW3fVcSx6IvMEW6xGNapRWVuLVrpF1KkbnQbHNqUr5S0Duf03RZ1kvThFnJK9VNcCl7kkBNJeLNEe7eHqoP6fbtFRBTj+zHvp8RndXAmiUW2eTwk81ptMBPlioUXS+5mwUyssIvtmyGA0aA0W4FPlie+N2sQAULta1Uc3geDZyLfrjdHGvz0VrJ/SFQ5//fLe7qhEhUskVF8OKHy02f67IWrfNpNNiYs28BFm4kfR7dTNpKTJa6+oTnXlidVdLPYzNiqvyht/Nand32T838tHdnDwHeb4xkcRuU7ACKNyxf98tOVl4gpTj5QFj9WyU8JrUS4Mb8eDQnQeVHADevy3w6fWBhCQ9vFBy1mawsH3StviBUaRMP97V+6rRCH+dn/+b4mADyPfRqrFwyuUjQXLvzvamGdoGIwj7nokN1bINemH/TFCIVXLsrCKhkhAFyEf0E0DznLS1BAuHnErKWB2xPnONY2hfpu1A5D8xFVop2rZ7abLSBqHYvZhUIg8qDnKz679k7LbgY9vXEdBicO1F+xZrcE9cMkjYkAS/7pgzhHFTr4E5U+7QcopvAzPqItljCNqODmLOth/Z7lx5ccBEe+ZaANtCkZIKMkuFfW7V6AgdOmk6kZJIraSIl5o8dek9uvDrYqlEI0gNtPO4BAG53x0CCgUKtG0W/wbRcEIKSvjOH3K4sNAUHrXqItIrgFpjahAWJBR78F1RqGaArcmQMe0ZPBlGwCSZ9GzB1CSGc6qtcBQ9iHzMBl5oWBB/50OrRFj4vSuRmAzR64aACwl0FttXxS/6o+UB2dVioI6bk4f5SEqDbzAAl6K31fgQONthAVW6KEczxo007G6MFn0Rz8X8GAeKklQFndhnEyEnZXcyFWCSCKyhEzLihdbhqEfnYgkhOiLIGxKX1CXzwCgPZaQYqC4HGI/iAKnU/tJA/NzQRCEwIcC8ZGEmgGkKFRm/nCET1UP9uUC0Ordrg0S84cUTVzc5VvfFN8tFXDNPD2l75Evxetr6CNGQG4QEYw5afnVbt4U+QGw/dos4chcljG+WZtKNfT/Z/0xAUL3XA9VjMfT+Z9EvzakGLorQYSIoDkWntKMry35lu/gKhZHOam5LDumfYJ2pAenODvcyR8jFrF4RJfhChnkwM331Qe5lz6PKpYTzlM66JsxfpzA1qQ4V21VDm5lKkabSi5z1KB8ZA++9q+D/AYItEszzcd++uBB99D0y38QIAJ1fQor8c9QpvmKhll0kq3hJ2r77lBqYfvkTnL4eW6soICDtXhn+5e3uYv2dIqIQwsX2uGYgbSoyYOv5P5O9eD9kHT+/XzXump8puWIlgocpIWRYpegeNX80b+5f5B1NSSonZI8FeAaAmUQyIWyls3/ZdMbVLbtizcZjdSg4esHv+XCj09tAr38vjpGsQQCHZ7SqTDa8UMEkC1BQaKOFP1SNainTiYSjSZ9II6/CYwVnWhsEHIni7qHIT/+/gAX3zDaTQLy7Qw8U9VuEUNW+qUCpGMDS+Nyvt0HobzGSzGe+WYMlpjX4IKJVeipBMWjmE1O81jlSzFEG7t5a8U7Kdk5melTQEKwt4kMHpb23VZ61yo4+MbETJRYmL9AB0YotVAwxz2YaxG13MEx3c5pvoF/guCLk64m4q4JSYg5qjBFFPSUfSLupgcOa6KxMzWeFPEtX41Lt21x2KSYDWp5exiwfFLMOr8S40HBjMiBe45nORQ+tdfdAmCBXivAOEy6mhVz9UPICbYaoy3hHmafzN8DWw9b4rPwEN2ZRir+fM1XCM0yF2IIMuJFN2HT5r9m0x/8xF55kH8Vi57a6+0QtYW1HLcprxDl/UGQUYl10kHDLLUrZ8txYyweR9tOnFUwiHuDHYRL03ekC3wTvse2UOnx4YMvQqEq6CT6pihtRumaOZWwpWr+pvuTkhUr7Yt0l6/br8k2q4p+uo02G0U05C+Dxgyr9+9x0owUCIfVhs1J6L0q2YuVFjseWrYrwIgEw1UNFwDkoyiCH+Cvx38iNrEmrejIdkbZ+oUBUnrQK6OiBX06ZwoiUUZJA5kNUEqDUn20lFwvjl0w5Oi6zH2MisBVuY5IXfMdz6C0+FmpeMJbKtaA3cMZxKlZXVwkyfgx8LfjJ5wE9Byv3HEP9hYze/se9BVk09TWVCDbGnylyfJuvat22K4d8xYynoih5RBNVqXKruTxDxiO0pRUKHlxF1N+IbpBpwSoew4lSh59DaH6MJtwV9avcl5Oko1VYNx8KOyZlC6sabgPjp7LFqfCZm8P/QmzAgIoeAMPxQdSUb3A1KHjmEkBdpUCW96d5N51kGHB2x9g8xlIlxRe72yEODSdtSU2vEqm5YokkwRWS49EsiodqiuFN0AuLQs2DrQsK2/AvxuyWNp64J5g84Uj9nnoBraR39HnxEMnr80xMlauYQqkdmt+kO/5kcSbaUpHrnGmrx2KU0jnXC30wsW6c4LySl+9Eg7oFehiuUBCPUN7JLm21Qg72glSmiflsRSWKPMRoDz6XMlnIo6jDXFu5/kZIWXztd0T7uw0E31bHE4u8duI8HDydupodu6cOG3Hg3zH12Ypg4fRPBfStx8/24xhCOicSgoUtT2l75DIftuTqeW4YE3eTnyV/BBX8D96ANKhxNAz3b7+nU7JfwFofJ4dJvDrM5JWchAfjPC4/LF3VBQ2URzkLFRhG2V+HYhF8AnZzK5mOT7J707qzmHqTDF18+tpMku59175OwrN4Ngqupyf6AM9G903VkM6nmlgaBEt4hBry3SmmeS6ZK8vvyhgRp5qXagMybPzjd7qRMMx20Btt9+n9N24mjhnlX02hld1y6sbbIwdrf0Suh68HkegMaxjskp4RR1hfQRJdLviHR3T+I440p+4VvMnThUWxlv9beZuMsT7ImnSxhzGJrqdFHX5rw/O2nhbNzBwe3nXYvURz3FlwLImA1kPN1dNrICojsAMFffPbp0Fp8jSoLijkh9VEB9xCzlgq/vX5Px/vTmkkTUXGhCe1PhES7K7GrM+J3Sv5yR2piJyrUYuVZEQDMDVBxc+nHIuGaOJtFLiPcNBPxIJGoLkcKTo1DgfK37tdaItPToAt3znA5yqRRlIA6Xy0hmKv9+19KrSbvd0TWgtPRBs8l6/wjtThd67pMmgQuTNTOE0Rh+gD+YhRaeouBsJRZziKxtcdPZwmgQjVLpUd4UpfbF0kM+D9kLBQ2L+PExVOeCmxmZ3RkS86JSJbZYBQOETd4B77PfL+vtPdOxTcJCWrjQx2fTvaHLDwvotPgVJPUzh6U/SpXRvg+x46hxu2c7PqSEba/gIcDwyKN39JQTPMBxrb1CyoG0tmlK+CIlj713n80/z9Y2k0uAudX0xO+YiTgSmUsteW6AqevT/XiIuqImssRQFfnJscrC1M1UCjz+QfLL+UpGI93muMceU/a1D8y2Pbw9zXssBwX/0ndrsvHW54SID6VdfpLuDLVPbraFYBFu1g5/uPjFOOLIIG2a/k4FnUQ7azS4qBLCAQziPTAI5Ik3doC3ntVp2F5reT3+Lh4yZMwttiEc24Vd3LPW0PAEjDImQIVh4mGAMiQ/O1KA4G2qmzCVl04vkKeuJbs5ZHQA7oowNPh1DTyUXSHNxuhT6uh7ADjzRRsh5zm+P4UrE9G1SmYZh92FNTaAw3TAC2Rfax3O0wG4SQHhMgflKoStlt4oIrULqKPPyNMpyJiSBWglSDsz/fzCLZDJ6H7Kmhp7S0SpK0rkyi3aN7AHpGTlsQlX0ls8k8LhU0xfNCgf1RLaYG1eIpJnqTN5e3yey/f3ZRVG2pH9EY8iJL8FBu/antd2HX513xBNku3eLfY/lxNbPsvBDGoIxzMYKEq4cxLnM6LKg9Rcwpt7LAY+bJ8ovmPiPYUSPHE/+ekYsDZSfobfW+wGVPNplZwiID/wYe+Tnzt04rQHd6jP8DTw5fiY3ea0rtPjNEVTS6J/2YSztOuVB2fdDR1Ujn2Kf7IhiLOIzCf8k8PN4eq0OawVCJ3bfCPGYJ/K0dp3/Ez0hbk8EW7PKkoQh8HHCdBhLJWcc5Q6LPC2owkogqC4UdPFMdGjQn+zzWK2uETtw5mVr2g4qhPbntvScYWbkH9a8HqFH2FssM4cijqfIfDjt1mJhfGgxQZ1evfXs4EXzmUBfFbJPcF2A9uHTvz2mKlEWLhK4/6tjLokTtc467oPgWiUe4uEdn4PdAOybJRfj9ILEQSrID8HGAbnIG1AiiPuYPAXjXuJ1MLMFPwc6qN09pgnqcl1tg0zy2yohmxl8P/pbkJTEAn1V9w25f0FzQuFTRLh1VZOEVCTar4IjBhusxJMw1hMxcnvj9GbYEfG4ezito6SwD7C9hudzFbVHGMdzj2oraI022U/su5THZ5iJ1u/DxpB1g9n7TRLJXoHq9nrPOkZqwWEaE9Z9vGsODJoSeLBXhGcm6R3OgXzMJXzeG3xqNGmM5OhUuLJ0YPTGEtvj1sPXevl6Yhk8JVCCXj1GH52Oslgv4BqaMYDSc2+sbethUK1ce0i01Tb8B6zKLeBXRr55tvoO04LYZL/2JDT6rxwiv0CK5lT8Oy+8o8nkF0tAdVigORHYMz0ZdpCXsmswP0Wax0q+aJD//yRH4p70yDPPtW7jqaOfDJCkQuULCCsK1a4mISwgPu77YCtuFy0S5a7fAkXwhwozV7DZB561AThrIvqomgNjmQ4M/ZNfTnkJsZo0qI4yikknICKO0unyfNPOK/ZqyHqRG/stE+uwt10RUSJvaZImVYb8DarOeRdXpK4hwS1Ft29dFE3gu+v/7AoCwypU/zPi4PkzQHJDPCimJoUKpdrT2DvD5/vYWmj7WqTEirhpII2S1c2yoHVtNSNCRVqVUfKdOnaU/1wsjp0y8Y6Os6dO0JasfGlNbwBRQHoNcYZVw0tnIDh+MGS34/Ixj6r423AFVUF0CW4xwshgrfs1NVb274yg9J2O9y7n5V/6Hgn5jUz93fbWgDdoq8Ic76QaN7OXde+mIf87JqGn6+7HsO6QoyeYUfy9chMk1UtYLC90li5pjcyGShblYsfB5MD/wrYU/ZyA9uymhCIMKJOsut6e5XSHfprlqEuHCZNj+1ivC/rKEUAHmm2Yb2F32qDy3Rriu/xj83qUkSQS5nmipA0l3ZCNSBxmXR0wiXAIE9Bp+oghS6/7ckMc4N7be4rLAAEIZbtn56oKi4yWDLbWGFrZ8DniqjCockRk5Z37Phqjk1+XXI5CrNyqufeVHBXlPUPldX91jZ8Bmtt2T6YarA2Wx/rrdS29c8OXBRDmYN9uFEWoinFmV/lQdk00pEUTNDRMcMSGD+91AQehBLVa4rKyiZQWeXxFU5hJfYH9zGy5IpqmHK6l41I8geqaqSH15es+qfZOp8Rl9NWyvlVzu0/Npwf6HflHDJII6sbVPQpgvDrDbF3vWFCM35QS25ZkpyeDbpLUAAjdwf5a/VwMTte1ZIaDt4QPIAB3I1ZfeJkdtKYgxHX8cMi71zlcfw/LPrEQ5R/lf/c4EUDVs3F4hNiQknGu5HiqGR8422ooJq/jfxxU7FC+ww3EozLNyEdG+XQusshIeo4ZJYxc/Oyw7NwB8Kz2WkMV8qbuQIdc0Tm1dfCt3w63sbJgqr+M8f9wHfQixrEGZ+XwpS7F4Q6KryBe0yKDAjgTXlEdaDWU9AC6pHXpWTYmGXvCelkwflGiTMKHp/eYjZgGrur5JfZiRps5X1F/F/U+MS5pyOmoNTuTc+OYLZRSJR5+PZtuaxzLe7IXP75bnAZJrr2u1dF63WnT+MHEThzPsmePmWvnU57JdwXxr7k+1L3T2tUTgGsER052A3nE0045IrTRwfo1WSTdDXt5gi6M5HzA5oyT1hCzaDJieLvQJtJ1bHP/wxpX741E2QWGVNt8XdY6pkIJHZbGwvBUg2q0jg2l8ZrHMr7oI7BjD3+0UJLkku5L5nft9K5dkOew3GhQ/qLRFG7dVNq8i/v2EYbfkflAm6wlx0LJP7OJ9wav1xJbdMWTLgIHEp5jUhtiYCgwmmE+YxD02oxdq7yd2z7Yj6pfRQdaW9uDvus3ejsvGUyA23lUaa3UAeLKim/bUANkCVX0RiJGlwa8GElLrDZc++HqQs6kUBPHhialEn5i3SaWVjhvDtreyD6Ll3fHZG0+9+BScZnVqnjg3+AJwBpjQV1cLqxoT8bPvNDh/h96DuNsWYJ+tlPHU4unQ2qzRfDetwsrj/hvZqPreKe4X+houieai2nL5vECmTvwEJbOHOIWIo2nRRzVZlbzSDUj5g5lfW79A/Vyn+1vUMW0T11GSMtJMpCSwWhhSc0AA35LrnvY3VZaJ4YRa2BQPpL0iEMzh4g7Om2qAS/TmxBhr85R9RVyr8ogCjSiaYsOphSVI1xhZ/yJ4y3odcjBw0rI7mU0rGRRAziwgIlZovYSSbjY6aRq+6SGXsXbMDqzH2Hmx/HgMpHtAffhE1Z2o7O5nVUpxNrc8fRxVfS1nryj6HFOm0zRdO+gxG6SSGExcw4sEcPWPAaw3VMy3E7pFQJOO2KQ3seRRlwZYoCUAm/llLKPM4krngnlVZ3D6CaG/Dx99htIXoU9gtM336TZAx7y60JvO+DcGRop9lxbxDlOpFpFPIfSmvg0z1qCGsgOftdCS1Yrtp/PgI4zbReyLSli71U2/MmEs4FPN4exZFVyskqtDankHptFmE9MFLoiqSuyeUq1eVGuRQWjegzKrgrVQlb8aDGuU7FPvxn0oSF8+UqnyRE0UHIt/ayYwjA77cSycJuZNYuKxrNjlV5e0qrruXBoRcXmb4UXKmgfM24C2k6BYGYQwuwz/vRh3qBEdU3g+D6sqqcb6Xh6wgTctuddIIjjHrPvvyVVvmWyN48TMJx2Rq7PeouSd2MWO8W8jRCcuHfpOPvMDV9Mb84oJvhnenNQ6xVjos1KrED6vZQK/jbX+PXkaB7QpKqlYV7HNaJ+GEWMPFs6ncnj1rZhMW5iHbbntm1MmSL8vcOYTdE1qb41USKUs4WyYeTlznzDqiuIKsheduftcyWgGm2w56f5Z7MEAiBXC0r+T5aAWXYE0N5pHKmUB6yq8AsGNidcP7VfxqiImv5VtE3pF7CRVu+Fwp09v0Q72kZcPazIU4OL4sCYI6Gm6krjICIHq1jrApHf3+Bi8/MAKFARes3tSLw1eb+SmtD3GZiBCj6X06E3CVcIwobeTKObPOFHooPi+n86dnebdRu3GQfJ8mGgCx93X7q0ipE6mPq5UUgtTa88cBtxViBSmpjbBGW4jdnKuc+2XC6JJqymasAFr04JqOU5Dg3XC4prxngrWiai+hmmnlXtN9sXRTp8MIXcRZfy+eLFLMYt9n624HMJFbW8beVDd8FUhDh/8RdUcL6IpJrRUIkd/sMhL3taWaabdkYGiBQJgZmDDDKZMsYR34U5rFijwZ3r4rzbd2P35nhF1ifX2ccWUsiHK2d+iql+fgdCIhptS6p0Uz/AS8yCNLZ95P43gGLP9Q+VijT6E3BdOpXBM4NXWFLQ3lcFWBDxb5ozZ5pwYIqHqm+/FSxzjvHyfLX9Sa4Hunev0nYtmbiLOPa8SwJNQFROYrAGXF+MAAolBBApscjOm1VOsQ/cob+jXZFor8cbO3e4litRN2sq6O2Fk8TBIvb+zVPgenEni8WDQ3GUloKYL2pc8olhzH6fXr6NkhKUkIZKisIUpJ6KtxdK334tNahswI8BMJFg//gh2fhQfVhdhWUziTCJCVWOtEjNpagaQoVcZZ2Vna/LVbQ/CCzVUwUc5EGrIraiF6sdEJGHzFtO9XkPbDPZNCjRlJWM1GFgAodoEVwRMYo5QyQ636jh/G4agrdF+PrYd+3s1laMem0d3hsCqpobxMiJ7tqjmPICvDdx66Q8ZQOAOnxChKBOVrgRx+kyOnQDKlwc2xB8ASds1KotlnpLm/Gr67WQg7RmLNwM7WwcfQxpSWIKRbD5tbpJg0FzaRZFgKlPyndv2OEppIwdfzQGg2jOZjzVExIU6KhrhwohSfmEiUZieBlMJEfDeItATZiJNA5NBs0350sn0xmwWLb23zpalkBeMGbsZrVjm54K5GHf+eNNu3T1BYT5ciBP+ft3aSxX2nsF7W6TmArzCMbT4ksLuxmrqIl7ww+OfOrlAcPa5abf9h7D6FN3mBVPDqwRJVhXerk7jpI2X8sCFstdaOVIKvzTn+laInJJFqbnrDkAqT1quT96dlGV6wAJPzXfXv+4TJIF1E+0TdKFOZG1B8CioeEwk+O+usqtBLhhOtOMcwcLuCBft1AsKFDilT9FFXgR0/KoYW650MSf7RLKEto1Q7/u7JXIvo05BuY8fkR6Y5p0L7KuVuKW0dpozUQLaWtSfWiV/whItldjTdHH1KJhlQd20OMIS5I2ycfhO4bYSghj/wv5SnOpCLX1iOrokLYP//7eq00oNmbUNujGVbMwCMisGMD0eWtW8hrHMk9IEBmQCb1/YfXHy7OudAIo5CHi1N8xz0d9ew7Jbmu8OyoraKhOGVMKDDXV3BasgLPa1xe1NaCeA5NmADOq6KnA0JIi8uZr6kpdv8mcbYLNiSkCnVrHFXwcKZwj0c5ee2BxWVlRy7j4dGdf03N/3ZMPH4QacsHdAXosuaeYQiBUT5oNXjL/EmQISRMVBz9WTdJQuXPlIq/Tvm8tgwS1QoIO2Rm0mc5SoOhFCCXqmW5dEWNWK6kz2dICXwWB2pnRrYr+pWZL2kUAS9NeSypaQqUa9+tH/1CvFfOuzlGYxjXuuBRPPBEH034/d2VjMaCHYhunZ3lcki071KR42RJHPWECQifltaGdv3JAn6WB5vMgAGV0H6mbMcJb88GYNUlhGmnM9CnK9CkehFShHLHVFFAyB9cOP2XWUaOzYMhEaoS2RPVRTmCZ/+1DCOthpEBVf25iGzyFBlyaY6EVgQ8ImIizPXXOncz7LO4u85xFMgh00Tsxcq7vFyz7EnfAEjgEQYp/l8Ps6RCQqwBsbzUm4S6v0vP7mCMghqv7F4AgHI+HcpA1ZD2NWwb+Ab17rUMiLQsTq2Dozb+HUGYtznL/TotbIgEZhtzTN8OQrqfkTlRDeI4N/t8uGlyUgdcSiV+B3zJbliVkPSNmgCBt4KMjksd30EBM2eznO9yG6NPe+h71lEeAwR6PiCrmpdAw7fUDfRybjbBn2OAMvmIvHBbG+Vnt2EQyk03b31PoQbQWL6l3EDFH/EYWcB9CNvHwYp+VKYjextd+3yRGinXam7r0ihDRaOnEf5a0IakvYwnmn5re15z069EJvlwdJ1/MBPKoEiPSzs/OsmBqIiENTY2Afpcwyb5xXxGHHO2p5S2bsmLCTYUTwLdb+MPJJYEcThPcoMilCquCmIdzQob4/H1ksWcNphjQf48IPEsJxo8sNm+HVqgNDhBHryHQFM7KVrTmIfCw5d0++hZw4RM3iHO28EQc0rPdtDe8fmEYLG8uonYwCTmAJGIAIslCgWlpfbBsqLFHe5rKy5FsAswrwlf7+ikqRmYuYgFziUkVxbevRuxTeB6zhkgQz9+zknzFwJ6OJ6jFAk/AMsV2fSccCOGCdTpVZK6kR7ud4fdsBScTf7m9l0JHxc8r/mU9D1rx2hTjN/VNGsfllDJefBM37tiEmXQe/tcBaAWoGM1B2Y4bzEFsMUIY8wvOoD+S1CxeRIe3HBq7aFGfmYxBCi+5rfCvVSTBu/IT7vO4tkdnS4VIEdTgzBEkuKmEBHmv6ZLXzbvk4Oofnc1VjlNwuT8a70MIre+RwGYxZJv7FK3uA0vq1sMZjDSq0QRbSSNOfLXqdyD9IQ80rF87QuMM0W4MdxpoIEEAXXgiyrXEZlRbydwgDlBiJNprCAmUf0cXh2MNtya5csbCX9DljCkwJO6yCCW/W2SITWcdi08zvHX9UKTZPXbUyUfxqx4VTh7hgk3NhNykwqqz8ehe1mFiEzJOKpwhz8vN6+G5Ory4oi9cLcmKQ0DJkhpa0eBO6UBlG4pq98YHiPmPM7Aibo/KZCnhlmdslB+kUUogmO5VXOs/vJLe05zmW1bUtWtSEsDA8RaghDqutN9S8iA4I9f0Mx89hcncHIy1EXm0BNK3wa8QwnjxAf0MgTy9s9RL79AL6nItXA2c8vwZ8AU2EKSoMII6mDt7a23ZTXuHTr4+1LzEQsLbrwHQSwNLiWjGEwsO2EAMVnYz4RAb/4wTiChRI/AA4Mn98F3r55p7F/c3nZfCAGZrHUCJMjdSVv1ghWNeMxltf2KVJ4SDxeJAUlgdyjXpHOC5p8yH7gidh0H81QQbc/j2BYMrHDNZ5gK4LOQZro/cxVKgXNfS10p7AoWWa/0aYF3aSby8AaluxjOrOOV+XfSlqGCZTUU//ymMzO/aPjlweINquo+d5GFEU7C5PZGtEn8nd773bE7u+pbVXQ3E7k5qjOjp+gbBTggO9zoQ45UKRDHYqbLw1wKUw9ssT0jvauBCf7lGpyXLIy7326/RXKs5XBeoc0B6UxMHbwJJfV/SQirpTLiZSD9xnXyI3boFkDCPMdnGSFrktzSAbpC6BqvnajuE4ogZh/f0wEJTKvzjr/QUfxlxj2899FokmIB31dVdjSp0wilWiX4anclxtx2s7vshN1t2Znrf1kDBh4UTnEazQL4xlInVBP47U9uI1sZx2hx4tA6sECZgZGCgUn0eshf4bVVmE6mlOJ16b7432ehyNqL7QjlzTLuuDAyQrueHRbd2+MCOrCHdK0VPJIPqDAHwYYkba8T/chTkXBqrdE95v1vA1BsG2kDj5H+Nh1k/GY6Vsl1Vbo4TM0A5aiTpLFsp7UlAQDG/zt/YQfsQhXCWxCWTOgPazDPcD6lf+Y0YhHfBny9sqK8FenHsYhaZgj1YTVzLwrBgYcx+bcVJoIkK1AbirlA6zFORcScXUToaveYao3kRFB5XOn/EJS/YIat1+Km7kvv23LtHZfAA8uRcphN1aFrZJBEwdVcSVfZpW/RO1R2iQ9lubMG8Px9p3g1wkD6dXM3KcEIeHc0Gijyq/LbepjrZCbsPreSGSDUozO+yumcRW5tYHs+NaeyEfDmQGzHNngnqQ3mg8Vym6fANxJt4zyC8OjbZb7dFUSsHVyb4yjyW1wBq0HK3+lHu7rA6oCBWafJ8ulSinZZgElSBfyy1UMEalZRViDotp6So7WHyWKZTGBQB5eZpavQ3UBHzrrUtHM2MLhkHaLHpj7E7CCqF7nAtAp3l4W8RlSxUUMxcnKzS3uvBAXO/aNJCwQTddYgnfAC3xEAsJqCGCEGWvj2+Gpk+0w6ZEylclo3C3yj8Ot6zMlMUy7FELbJYYF2xS91Rer+DamwyVWH1hbDVOMpE1EdpQwjRYU+Wse8w8l2R7O/TavTjr9Q/FZ7KrsEPKRy/XvFADwijJbvWSNfS17BPuX9TR/DsRLr3Ai7n9wC/Pquc/8RO24HhFSw3d/SnF1vZIO1PVj1hPN1tm4O0QDGhqDjHBsFM2Ib4D+EAi2E6B4Xz/pq+VdyarUBBNOKu7mieVkJx5toDABiuNsb/cq9QonqZJnmQdUqBykLFpxR6ENcfZeLma7lU2Zrow6aJQewsMpTh9QjxdYFNG1ysJ74h4b1aGPbK/YRvNKuWvO+9n+yrSYG1Z44cqm8rXnnNuQv9UXIOJbWidL9nL7rRuCE5CDy+0+ENUMTllmCn4Jrc1k4HgLUuvfDjq9qpwbiEqISN0xsciy9VnVSEj7HdMXP59nMkJq0uUY22MA4mKMi1bjypnbNTmn1UGDD1ni18Z19CHj+wA2eeC3+jf/FdrnNHICTXFAdEBKzvoOaUMK8F9K1HD4whhrlhHHrSBI8qhPH9pjerzxDt7FR31cKW/Z4izmZtJq0V6qoO0jwdHr4xClQX4AwaLSAoeebEUMqPY63bLFrQ+Oy8DaocAgzAaQKsetm1ARDkZMgLloUwCWkCP9Vi6KOfx//BItZKAVfciALSHcBFGwAalFXbeBadQexLAqbichcK8f3SxCfD15g4FEgT8C+YoRS70iUSFytVtsgvkoKDhOUkjT95votaML/ylUFto42QP6a3m8pU79TJVqac/lHK9PoV1TQ4DYEKBn8fezNI0KmYTcs6hyZ3n8CTRajCgRjwI8/YaXc1OYdcfmju3SyRimISYg62/r9KzCRXZHQj6jPZUN5pIJOnylSorN/DKk+M/kqR9R4hjS9fiDRzVVCNBX/eFi0SEDrM3lmmJ1ZGtg7iIshL6SkTWDb7x6n0W9i4LzHkuYNV2v87e0AwLYNNsXyCjBFy8/BkGoO8FjGzQzklTiAsbnuOooxX0qhEUDZgCZlwOFUYz1F7plW3YLrNOwz3iK5KAY2/78UNNonmi8tM6k8onEBaHwWd7trQ3x7aQpE+1lzMofmbXsbH4inYe99glpKHFEFQEHx3J6L5d7kZaKk2MGWOo9KiIuqLvs+2aPRzFJ8qq07YQSYaoAXfRfBUTxRfGLiEGJ+DlHBAuJalXjRyt8hcGP1vTx7ERGkMWCaEVpwGZzcaVHZeQ02RM3ONGKJSzxjhlR7OEvmJIzzMeQ96h+otKeHXvIA0mWHFuYwFlQiBVduHv4ACBCxrzLIGnczh6H09uDRqQav96wJ1/LtLXAFB7J0gWg9MmH2EvRDL6csl1/nW8BQzsyUoDx7z1xgzOYoIIambiaO6ML23yUmYd0N2lb+OvWZ84wjuKi8lDw6XdCAb6tBPSAEjMhp8i/u2CzyEyXIWWGD2S8//zbVHcQSSu7TqYK5Wy8+CxGeV9IFf8xcAKDog+R8738p4zJX5TOSWlH3QhygVTZkkO6PPH4O9/tPFDQmlIGMF0bjokrVsa68dNZFogiGjJE3IOwzYR9OeqKVahSY/asgXS3mnlNVhaFRpeFMZDhuwD41w93tQvEGL6JVvJ6XmA4nkbG0+KHltg2vPSiJy8Ak/I5CZUNjQnP9GbhAE7oooWAwafAHF3GxPku00mEG61+NiB9Dl1VXVcGPnKkAB1z5QMOimd9qBtX4HiwuK6+KF1CjXlqB4gGb4Htgcu0jswHSKCgNwidhYKul160jAptaJAJ3hz9rBp4HI7AC6M920VBhTAxNtEGd1f4r9awq6BkD0Uzk20PaON47/lUhvxVlboEj4Tu63UOxVzVBXQGfv/AnyL079Ch//4e48/Ra5f2+gVneIe+ln85v5YPJPZWwv0iyjNGdt6PabhIX1RnMwTHalvHznkwfVzFRcpD/wNwJ45xB3R03HMh0/odTFS2Bc9Fk2Crmxbmz4E4EYcdJSrp6Z4ndfyA69U178VOBBx5kmDBrKswnZDnoWQROODTUgNYUNtsKa7uJhMgIz9JkBcqsJ2fYqEFpQBeN0/d1bON/flK12dB8euwRH9pyDE8fb089mFb5nNUsmXxrDd5PrMtMEg8hbY0kAuTbYTRSIKUOkZHc5sUA5qVJbeVNUjrI+a607d380jWr4tFt/8wbDzm39RWNWguLiBOGp5xcSvPEnd/J97pkVZ4HnBBtgbemc056PF2B/XcixcaH51GpjNHwkUQ0F+nULlDSurV4l5OKYDS3Eust8ni6YY96jSdbROTb6AvysCraJLn6tkm3rTNv0DdPDRmSRR22pO9bOWBJyPwNtj1XqRbXQFUPfqHYBEmSifQfUbn+opgQATPT0YSKJ+fCZ0bH5n3emfaVTByIW4b62C4C4eDrttxESE2pH5NAYG8+rJn57MnTP7p58VK7a0NAD/zkjudgHWBI55RDZI9Q+0bZ0Tn7St/4ZzqMQ7GnQ1AJEWxZV+goN40Bu3iTfxhddZ5rcv5BQuKaXwI/XBjf2J1SBnv76myur1OBTdDTqTUB4I9FnusZjLayqlOk1OC2pbaWvkLVwWoRL0sWpbbMjQzWzrsZucfNtoszALjwn02hRd0E8hiilYygHUyVIpbsdcnWAOOjbXpTBEbQXprlFKmlPOEJiK+cL8hk3o62drS90zLqPQsDlMzyPT41m/z7fWo8euY8vd9sxYM5pBLAmbic5g5FCOCNRsGv0bg42ljK+RpIfXRwphi0lOSXWQ2R+SurCskP2PJ9s4XPSMBHSb5kmWCdAYhwbev/FK9Is8Td75/5RTMzM2dXWTdFSOtc0SjbKYPXP/1BmH1E9MKE91nKjNgA+ovnsdY2+w50s8wVRWb3cqShMK8NsRZiFQbieGZ9ws68QZ+wIKPi0LbOZyQM2uCzQpuaMoyvFSRQC2izRFUhsB0b8I/zIkf16cieSazxML7nvV1/9QuolVIPB8KH2IDC/KbN6VCRD0n+KQhOw6CdyipcwVYx/Tb9tIjjwcqsLr2TYLjo6QTkzUX1JKBckQGCEYCESBxXUwwyYS2NRh1ay3Qpr2HNbgAbxIwaILYQafiWNPS29vzR2X0WKdKl8aIyT//nMlgQN95OTWYriHgNihKnd7wE9vkk3aUv9SVwnylF6VUvS2pe4jvGP9sz+zg0ibhAslqmYPazvYzH4Bku7nDIC2EsCtq2of6cwbuiLzswQ1vfggmxQn8uN65znEJqBnZ9iCWXj6KvT/y2TCLoctAGUoQn6BSKzhAQrXkqGEKyWCY/jw70aNsQY/R+YUAKfmANzYK91rx/49InlCHVa5UEJZaTc4tWNatXvPY9eg41eNzKSrUtcBuaaHogAc4+fvaPNHgqGdS9xsUv9kah73nYEse7UpS/kp5Al0NnvU64KDTQAYJYa2MkApaZdkVvclpL45Wigoc8Yk9JOcWXHnG+U3/ZUqJ+XS83Nz40QPaKvW5NhFzgnZZ9/YT40Jsc921dbdzEcNVhfOe9/lgGp9reAVv6fHfjGrUSg/sejktIuy6nGsV59NdlTYV/humU/voidmjKyA54muBviT7Ecsz1WRuDwdYIDCydERoADcumDWHDlFFlKOrAV1Nddx2irgDAVGLYHe6me1cYFmlOcHxgBJSVKVQeIJC5XuwglgS2Z2udVvtJKYiR0+2w7Cd63FShnFqVUxbfySFWB7bN5oTmgdwLhIYBogDZYjTsPMABAh3RuA4o9K5caob3tvXwsmnmQDye9mDY7NwJvgEqmRH4yZJI/FNXSS4e68YXXFUsQvi0LYIkdC2NUseQEEGJgkEU6tgpKuyxLzCuKzvw8veiVVH9F7xjuGs0zK4VlcsHcAAERhf/jOGoxo57mCWQNn1NYzZUQxOye7qFOGHBhvaT21whKPmFnlJhqUg3mZeJY18ge2qusyidzUhbQquSFLuXfx2dLLZ8QtXzW4E+IXERH5RUGhUWmoCeNiKCQ9vJtI4hmSkwAWAuPUl5zOaHQAAAwkQog6QiL7wRXtol8G4Gj4e7mo3HWFSf0gACGH8dO9V/Vw5XkD0m0Wd9iz5Ho4T4hfMsKEnSraAhb9kcdhixIWgMGjk3+yVUxG+RPhjms3byiF0UCcxl7Lzr1TsHy+h7Tst0uMiCyyEN4+PXXBgyKq3k+pvonKEZLzeo/wMjTZM4UqZz3LLZQpedu2G1cgAFl7C/OwZCtbA4UmjIEH69gFhXByyljQ+9YqFgZZUZuEAVeA2q97jsBjLX4Dw4dCNAWNu+8KOeFM/iKmsl/BqKXedTqrQL2qgOXnlcgH+5FD8KABqhAUHnky7YAIsHnL45Xs4cYghhpZQqNRVhOR8Xsc+6vU102wjeQk3vJJxBEiQ4nURGe9eKOE5B8QDa67yVSAPRhPKOiiZCyrp4IM+4wTYlksNl11KFIhtAbc4Hw5QJ26AY47rlTQ7ll88VSYzSvag/Oyq7R5P8DgEEcd5ViIjhCuRc6DghqmijAA8h2WN5hAmNuJeZADwtPS6vkWlx4zO8PxeUEadjD7AZ0N1MjudgwF7eUL3iqs0/Qv1+sBN3tM7oAaWzwLJTuowFk1/610MQjab54Jw03sMExrSQAAAAA==" alt="SELA virtual human" />
                <div class="lip-sync-mouth" aria-hidden="true"></div>
                <div class="avatar-overlay"></div>
                <div class="avatar-grid"></div>
                <div class="avatar-label"><strong>SELA • Virtual Human</strong>Mulut bergerak saat berbicara, sekaligus menganalisis data SLA berdasarkan periode, proses, vendor, transaksi, dan nomor permohonan.</div>
              </div>
            </div>
          </div>
        </div>
        <div class="wavebar-wrap"><div class="wavebar"></div><div class="wavebar"></div><div class="wavebar"></div><div class="wavebar"></div><div class="wavebar"></div></div>
        <div class="hero-caption" id="heroCaption">Halo, saya SELA. Saya siap membantu Anda membaca SLA, tren transaksi, bottleneck, growth, vendor, nomor permohonan, dan menyusun ringkasan Direksi dengan bahasa yang natural.</div>
      </div>

      <div class="panel right-panel">
        <div id="speechBubble" class="speech">Halo, saya SELA. Silakan bicara atau ketik pertanyaan Anda. Saya akan menjawab dengan bahasa yang natural berdasarkan data yang tersedia di dashboard ini.</div>

        <div class="metrics">
          <div class="metric"><div class="label">Transaksi Aktif</div><div id="metricCount" class="value">0</div><div class="sub" id="metricPeriod">-</div></div>
          <div class="metric"><div class="label">Rata-rata SLA</div><div id="metricSLA" class="value">0 hari</div><div class="sub" id="metricBottleneck">Bottleneck: -</div></div>
          <div class="metric"><div class="label">Growth Terakhir</div><div id="metricGrowth" class="value">-</div><div class="sub" id="metricGrowthSub">Dibanding periode sebelumnya</div></div>
          <div class="metric"><div class="label">Prioritas Utama</div><div id="metricTopTrx" class="value" style="font-size:18px">-</div><div class="sub" id="metricTopVendor">Vendor: -</div></div>
        </div>

        <div class="selectors">
          <select id="voiceSelect"></select>
          <button id="checkMicBtn" class="btn dark">Cek Mic</button>
          <button id="testVoiceBtn" class="btn secondary">Uji Suara</button>
          <button id="stopVoiceBtn" class="btn dark">Stop Suara</button>
        </div>

        <div class="chips" id="quickChips">
          <button class="chip" data-question="Buatkan ringkasan direksi">Ringkasan Direksi</button>
          <button class="chip" data-question="Jenis transaksi apa yang SLA-nya paling lama?">Top SLA</button>
          <button class="chip" data-question="Bagaimana growth transaksi?">Growth</button>
          <button class="chip" data-question="Apa bottleneck utamanya?">Bottleneck</button>
          <button class="chip" data-question="Vendor mana yang paling lambat?">Vendor Lambat</button>
          <button class="chip" data-question="Nomor permohonan mana yang perlu dipantau?">Nomor Permohonan</button>
          <button class="chip" data-question="Apa rekomendasi perbaikannya?">Rekomendasi</button>
        </div>

        <div id="chatbox" class="chatbox"></div>

        <div class="composer">
          <input id="textInput" class="chat-input" type="text" placeholder="Tanya apa saja tentang data SLA, transaksi, vendor, growth, atau nomor permohonan..." />
          <button id="micBtn" class="btn primary">🎙️ Bicara</button>
          <button id="sendBtn" class="btn send secondary">Kirim</button>
        </div>
        <div class="statusline" id="statusLine">Status: SELA siap membantu. Anda bisa bicara atau mengetik.</div>
        <div class="footer-note">SELA akan menjawab berdasarkan data yang sedang aktif. Jika datanya belum tersedia di dashboard, saya akan memberi tahu secara jujur.</div>
      </div>
    </div>
  </div>

  <script>
    const payload = ___SELA_PAYLOAD___;
    const metrics = payload.metrics || {};
    const periodStats = payload.period_stats || [];
    const yearStats = payload.year_stats || [];
    const trxStats = payload.transaction_stats || [];
    const vendorStats = payload.vendor_stats || [];
    const nomorStats = payload.nomor_stats || [];
    const prosesStats = payload.proses_stats || [];
    const processYearStats = payload.process_year_stats || [];
    const processMonthStats = payload.process_month_stats || [];
    const processPeriodStats = payload.process_period_stats || [];
    const processTransactionYearStats = payload.process_transaction_year_stats || [];
    const processTransactionMonthStats = payload.process_transaction_month_stats || [];
    const processVendorYearStats = payload.process_vendor_year_stats || [];
    const processVendorMonthStats = payload.process_vendor_month_stats || [];
    const records = payload.sample_records || [];

    const speechBubble = document.getElementById('speechBubble');
    const heroCaption = document.getElementById('heroCaption');
    const statusLine = document.getElementById('statusLine');
    const chatbox = document.getElementById('chatbox');
    const textInput = document.getElementById('textInput');
    const micBtn = document.getElementById('micBtn');
    const sendBtn = document.getElementById('sendBtn');
    const checkMicBtn = document.getElementById('checkMicBtn');
    const testVoiceBtn = document.getElementById('testVoiceBtn');
    const stopVoiceBtn = document.getElementById('stopVoiceBtn');
    const femaleAvatar = document.getElementById('femaleAvatar');
    const lipSyncMouth = document.querySelector('.lip-sync-mouth');
    const voiceSelect = document.getElementById('voiceSelect');

    function fmtNum(n){
      if(n === null || n === undefined || Number.isNaN(Number(n))) return '-';
      return new Intl.NumberFormat('id-ID').format(Number(n));
    }
    function fmtPct(n){
      if(n === null || n === undefined || Number.isNaN(Number(n))) return '-';
      const v = Number(n);
      return (v > 0 ? '+' : '') + v.toLocaleString('id-ID', {maximumFractionDigits:2, minimumFractionDigits:2}) + '%';
    }
    function fmtDays(d){
      if(d === null || d === undefined || Number.isNaN(Number(d))) return '-';
      const v = Number(d);
      const totalSec = Math.round(v * 86400);
      const day = Math.floor(totalSec/86400);
      const hr = Math.floor((totalSec%86400)/3600);
      const mn = Math.floor((totalSec%3600)/60);
      if(day > 0) return `${day} hari ${hr} jam ${mn} menit`;
      if(hr > 0) return `${hr} jam ${mn} menit`;
      return `${mn} menit`;
    }
    function normalize(s){ return String(s||'').toLowerCase().trim(); }
    function addMsg(role, text){
      const div = document.createElement('div');
      div.className = `msg ${role}`;
      div.innerHTML = text + `<small>${role === 'bot' ? 'SELA' : 'Anda'}</small>`;
      chatbox.appendChild(div);
      chatbox.scrollTop = chatbox.scrollHeight;
    }
    function setBubble(text){ speechBubble.textContent = text; heroCaption.textContent = text; }
    let mouthAnimFrame = null;
    let mouthSpeaking = false;
    let mouthOpen = 0.18;
    let mouthTarget = 0.18;
    let mouthWide = 1;
    let mouthLastTargetAt = 0;

    function startSmoothMouth(){
      mouthSpeaking = true;
      mouthLastTargetAt = 0;
      if(!mouthAnimFrame) mouthAnimFrame = requestAnimationFrame(animateMouth);
    }
    function stopSmoothMouth(){
      mouthSpeaking = false;
      mouthTarget = 0.16;
    }
    function animateMouth(ts){
      if(!lipSyncMouth){ mouthAnimFrame = null; return; }
      if(mouthSpeaking && (!mouthLastTargetAt || ts - mouthLastTargetAt > 82)){
        const vowelLike = 0.30 + Math.random() * 0.92;
        mouthTarget = vowelLike;
        mouthWide = 0.88 + Math.random() * 0.34;
        mouthLastTargetAt = ts;
      }
      if(!mouthSpeaking){
        mouthTarget = 0.14;
        mouthWide = 0.94;
      }
      mouthOpen += (mouthTarget - mouthOpen) * 0.34;
      const micro = mouthSpeaking ? Math.sin(ts / 38) * 0.035 : 0;
      const open = Math.max(0.12, Math.min(1.28, mouthOpen + micro));
      lipSyncMouth.style.setProperty('--mouth-open', open.toFixed(3));
      lipSyncMouth.style.setProperty('--mouth-wide', mouthWide.toFixed(3));
      if(mouthSpeaking || mouthOpen > 0.17){
        mouthAnimFrame = requestAnimationFrame(animateMouth);
      } else {
        mouthAnimFrame = null;
      }
    }
    function setAvatarState(state){
      femaleAvatar.classList.remove('speaking','listening');
      if(state) femaleAvatar.classList.add(state);
      if(state === 'speaking') startSmoothMouth();
      else stopSmoothMouth();
    }

    function populateMetrics(){
      document.getElementById('metricCount').textContent = fmtNum(metrics.transaction_count || 0);
      document.getElementById('metricPeriod').textContent = `${metrics.period_first || '-'} s.d. ${metrics.period_last || '-'}`;
      document.getElementById('metricSLA').textContent = fmtDays(metrics.avg_sla_days || 0);
      document.getElementById('metricBottleneck').textContent = `Bottleneck: ${(metrics.bottleneck && metrics.bottleneck.name) ? metrics.bottleneck.name : '-'}`;
      document.getElementById('metricGrowth').textContent = fmtPct(metrics.latest_growth_pct);
      document.getElementById('metricTopTrx').textContent = (metrics.top_transaction && metrics.top_transaction.name) ? metrics.top_transaction.name : '-';
      document.getElementById('metricTopVendor').textContent = `Vendor: ${(metrics.top_vendor && metrics.top_vendor.name) ? metrics.top_vendor.name : '-'}`;
      if(metrics.latest_count && metrics.prev_count){
        document.getElementById('metricGrowthSub').textContent = `${fmtNum(metrics.prev_count)} → ${fmtNum(metrics.latest_count)} transaksi`;
      }
    }

    // Voices
    let availableVoices = [];
    function loadVoices(){
      if(!('speechSynthesis' in window)) return;
      availableVoices = window.speechSynthesis.getVoices() || [];
      const preferred = availableVoices.filter(v => /id|indonesia/i.test(v.lang + ' ' + v.name));
      const femaleHints = (preferred.length ? preferred : availableVoices).filter(v => /female|zira|siti|gadis|woman|indonesia/i.test(v.name.toLowerCase()) || /id/i.test(v.lang.toLowerCase()));
      const list = femaleHints.length ? femaleHints : (preferred.length ? preferred : availableVoices);
      voiceSelect.innerHTML = '';
      list.forEach((v, idx) => {
        const opt = document.createElement('option');
        opt.value = v.name; opt.textContent = `${v.name} (${v.lang})`;
        if(idx === 0) opt.selected = true;
        voiceSelect.appendChild(opt);
      });
      if(!list.length){
        const opt = document.createElement('option');
        opt.textContent = 'Voice browser default';
        voiceSelect.appendChild(opt);
      }
    }
    if('speechSynthesis' in window){
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
    function pickVoice(){
      const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
      const chosen = voiceSelect.value;
      return voices.find(v => v.name === chosen) || voices.find(v => /id|indonesia/i.test(v.lang + ' ' + v.name)) || null;
    }
    function speak(text){
      if(!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const utt = new SpeechSynthesisUtterance(text);
      utt.lang = 'id-ID';
      const voice = pickVoice();
      if(voice) utt.voice = voice;
      utt.rate = 0.98;
      utt.pitch = 1.12;
      utt.volume = 1;
      utt.onstart = () => { setAvatarState('speaking'); statusLine.textContent = 'Status: SELA sedang menjawab.'; };
      utt.onboundary = (event) => {
        if(event && (event.name === 'word' || event.charIndex >= 0)){
          mouthTarget = 0.46 + Math.random() * 0.72;
          mouthWide = 0.9 + Math.random() * 0.28;
        }
      };
      utt.onpause = () => { mouthTarget = 0.18; };
      utt.onend = () => { setAvatarState(''); statusLine.textContent = 'Status: SELA siap membantu pertanyaan berikutnya.'; };
      utt.onerror = () => { setAvatarState(''); statusLine.textContent = 'Status: suara berhenti atau tidak tersedia.'; };
      window.speechSynthesis.speak(utt);
    }

    function topByName(arr, name){
      return arr.find(x => normalize(x.name) === normalize(name));
    }
    function periodByName(name){
      return periodStats.find(x => normalize(x.periode) === normalize(name));
    }
    function extractYear(text){ const m = String(text).match(/(20\\d{2})/); return m ? m[1] : null; }
    const MONTH_DEFS = [
      ['januari','jan','january'], ['februari','feb','february'], ['maret','mar','march'], ['april','apr'], ['mei','may'], ['juni','jun','june'],
      ['juli','jul','july'], ['agustus','agus','agt','agu','august','aug'], ['september','sep','sept'], ['oktober','okt','october','oct'], ['november','nov'], ['desember','des','december','dec']
    ];
    const MONTH_NAMES_ID = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];
    function extractMonthYear(text){
      const lower = normalize(text);
      const year = extractYear(text);
      if(!year) return null;
      let month = null;
      for(let i=0;i<MONTH_DEFS.length;i++){
        for(const label of MONTH_DEFS[i]){
          const re = new RegExp('(^|[^a-z])' + label + '([^a-z]|$)', 'i');
          if(re.test(lower)){ month = i + 1; break; }
        }
        if(month) break;
      }
      if(!month){
        const patterns = [/20\\d{2}[^0-9]([01]?\\d)/, /([01]?\\d)[^0-9]20\\d{2}/];
        for(const pat of patterns){
          const m = lower.match(pat);
          if(m){ const cand = Number(m[1]); if(cand >= 1 && cand <= 12){ month = cand; break; } }
        }
      }
      if(!month) return null;
      return {year: String(year), month, monthName: MONTH_NAMES_ID[month-1], monthKey: `${year}-${String(month).padStart(2,'0')}`};
    }
    function findMentionedPeriod(text){
      const lower = normalize(text);
      const item = periodStats.find(p => lower.includes(normalize(p.periode)));
      return item || null;
    }
    function findNaturalMonthRow(text, source){
      const my = extractMonthYear(text);
      if(!my) return null;
      const arr = source || processMonthStats;
      return arr.find(p => p.month_key === my.monthKey) || arr.find(p => String(p.year) === my.year && Number(p.month) === Number(my.month)) || null;
    }
    function findMentionedTransaction(text){
      const lower = normalize(text);
      return trxStats.find(t => lower.includes(normalize(t.name)));
    }
    function findMentionedVendor(text){
      const lower = normalize(text);
      return vendorStats.find(t => lower.includes(normalize(t.name)));
    }
    function findMentionedNomor(text){
      const lower = normalize(text);
      return nomorStats.find(t => lower.includes(normalize(t.name)));
    }

    function detectProcess(text){
      const q = normalize(text);
      if(/total\\s*waktu|sla\\s*total|total sla|keseluruhan/.test(q)) return 'TOTAL WAKTU';
      if(/perbendaharaan|treasury/.test(q)) return 'PERBENDAHARAAN';
      if(/keuangan|finance/.test(q)) return 'KEUANGAN';
      if(/fungsional|fungsi|user/.test(q)) return 'FUNGSIONAL';
      if(/sla\\s+vendor|proses\\s+vendor|vendor\\s+periode|vendor\\s+tahun|vendor\\s+20\\d{2}/.test(q)) return 'VENDOR';
      return null;
    }
    function prettyProcessName(p){
      if(!p) return '-';
      return p.replace('TOTAL WAKTU','Total Waktu').replace('PERBENDAHARAAN','Perbendaharaan').replace('KEUANGAN','Keuangan').replace('FUNGSIONAL','Fungsional').replace('VENDOR','Vendor');
    }
    function findMonthYearPeriod(text){
      const explicit = findMentionedPeriod(text);
      if(explicit) return explicit;
      return findNaturalMonthRow(text, processMonthStats) || findNaturalMonthRow(text, processPeriodStats) || null;
    }
    function describeMonth(myRow){
      if(!myRow) return '';
      if(myRow.month_name && myRow.year) return `${myRow.month_name} ${myRow.year}`;
      return myRow.periode || myRow.month_key || 'periode yang diminta';
    }
    function answerProcessSLA(q){
      const process = detectProcess(q);
      if(!process || !/sla|berapa|rata|waktu|durasi/.test(q)) return null;
      const year = extractYear(q);
      const monthInfo = extractMonthYear(q);
      const monthRow = findMonthYearPeriod(q);
      const trxObj = findMentionedTransaction(q);
      const vendorObj = findMentionedVendor(q);

      // Month-level answer takes priority over year-level answer.
      if(monthInfo && trxObj){
        const row = processTransactionMonthStats.find(x => x.month_key === monthInfo.monthKey && normalize(x.name) === normalize(trxObj.name));
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Untuk jenis transaksi ${trxObj.name} pada ${monthInfo.monthName} ${monthInfo.year}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      if(monthInfo && vendorObj && !/sla\\s+vendor/.test(q)){
        const row = processVendorMonthStats.find(x => x.month_key === monthInfo.monthKey && normalize(x.name) === normalize(vendorObj.name));
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Untuk vendor ${vendorObj.name} pada ${monthInfo.monthName} ${monthInfo.year}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      if(monthInfo || monthRow){
        const row = monthRow || processMonthStats.find(x => x.month_key === monthInfo.monthKey);
        if(row && row[process] !== undefined && row[process] !== null){
          const periodLabel = monthInfo ? `${monthInfo.monthName} ${monthInfo.year}` : describeMonth(row);
          const extra = row['TOTAL WAKTU'] !== undefined && process !== 'TOTAL WAKTU' ? ` Sebagai pembanding, rata-rata Total Waktu pada periode tersebut adalah ${fmtDays(row['TOTAL WAKTU'])}.` : '';
          return `${naturalLead()} Rata-rata SLA ${prettyProcessName(process)} untuk periode ${periodLabel} adalah ${fmtDays(row[process])}, dihitung dari ${fmtNum(row.count)} transaksi.${extra}`;
        }
        if(monthInfo){
          return `Saya belum menemukan data SLA ${prettyProcessName(process)} untuk periode ${monthInfo.monthName} ${monthInfo.year} pada filter aktif.`;
        }
      }

      if(year && trxObj){
        const row = processTransactionYearStats.find(x => String(x.year) === String(year) && normalize(x.name) === normalize(trxObj.name));
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Untuk jenis transaksi ${trxObj.name} pada tahun ${year}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      if(year && vendorObj && !/sla\\s+vendor/.test(q)){
        const row = processVendorYearStats.find(x => String(x.year) === String(year) && normalize(x.name) === normalize(vendorObj.name));
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Untuk vendor ${vendorObj.name} pada tahun ${year}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      if(year){
        const row = processYearStats.find(x => String(x.year) === String(year));
        if(row && row[process] !== undefined && row[process] !== null){
          const extra = row['TOTAL WAKTU'] !== undefined && process !== 'TOTAL WAKTU' ? ` Sebagai pembanding, rata-rata Total Waktu pada tahun tersebut adalah ${fmtDays(row['TOTAL WAKTU'])}.` : '';
          return `${naturalLead()} Rata-rata SLA ${prettyProcessName(process)} untuk tahun ${year} adalah ${fmtDays(row[process])}, dihitung dari ${fmtNum(row.count)} transaksi.${extra}`;
        }
        return `Saya belum menemukan data SLA ${prettyProcessName(process)} untuk tahun ${year} pada filter aktif.`;
      }
      const periodObj = findMentionedPeriod(q);
      if(periodObj){
        const row = processPeriodStats.find(x => normalize(x.periode) === normalize(periodObj.periode)) || periodObj;
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Pada periode ${row.periode}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      const rowAll = prosesStats.find(x => normalize(x.name) === normalize(process));
      if(rowAll){
        return `${naturalLead()} Pada seluruh data aktif, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(rowAll.avg_sla_days || 0)}.`;
      }
      return null;
    }

    function naturalLead(){
      const leads = [
        'Baik, saya bantu jelaskan ya.',
        'Siap, saya bacakan hasil analisisnya ya.',
        'Oke, dari data yang sedang aktif saya lihat seperti ini.',
        'Tentu, saya rangkum secara singkat ya.',
        'Baik, berdasarkan data yang tersedia hasilnya seperti ini.'
      ];
      return leads[Math.floor(Math.random() * leads.length)];
    }
    function recommendationText(){
      const topTrx = metrics.top_transaction;
      const bottleneck = metrics.bottleneck;
      let rec = [];
      if(topTrx){
        rec.push(`Prioritaskan evaluasi jenis transaksi ${topTrx.name} karena rata-rata SLA-nya mencapai ${fmtDays(topTrx.avg_sla_days || 0)}.`);
      }
      if(bottleneck){
        rec.push(`Lakukan pendalaman pada proses ${bottleneck.name} karena saat ini menjadi bottleneck terbesar dengan rata-rata ${fmtDays(bottleneck.avg_sla_days || 0)}.`);
      }
      if(metrics.latest_growth_pct !== null && metrics.latest_growth_pct !== undefined){
        if(Number(metrics.latest_growth_pct) > 0){
          rec.push(`Karena volume transaksi terakhir tumbuh ${fmtPct(metrics.latest_growth_pct)}, monitoring kapasitas proses dan aging dokumen perlu diperketat.`);
        } else if(Number(metrics.latest_growth_pct) < 0){
          rec.push(`Walau volume transaksi turun ${fmtPct(metrics.latest_growth_pct)}, percepatan SLA tetap perlu dijaga agar perbaikan kinerja konsisten.`);
        }
      }
      return rec.join(' ');
    }

    function answer(text){
      const q = normalize(text);
      if(!q) return 'Silakan sampaikan pertanyaannya ya, saya siap membantu.';
      if(payload.meta.status === 'empty') return 'Saat ini belum ada data aktif yang bisa saya baca. Silakan upload atau aktifkan data terlebih dahulu.';

      const processAnswer = answerProcessSLA(q);
      if(processAnswer) return processAnswer;

      if(/halo|hai|selamat|pagi|siang|sore|malam/.test(q)){
        return 'Halo, saya SELA. Senang bisa membantu Anda. Silakan tanyakan apa saja terkait jumlah transaksi, SLA, vendor, bottleneck, growth, nomor permohonan, atau minta saya buatkan ringkasan Direksi.';
      }
      if(/siapa kamu|kamu siapa|nama kamu/.test(q)){
        return 'Saya SELA, asisten virtual wanita untuk SLA Payment Analyzer. Saya membaca data yang sedang aktif dan membantu menjelaskannya secara natural.';
      }
      if(/ringkasan direksi|executive|direksi|summary/.test(q)){
        const parts = [];
        parts.push(`${naturalLead()} Pada data aktif terdapat ${fmtNum(metrics.transaction_count || 0)} transaksi dengan rata-rata SLA total ${fmtDays(metrics.avg_sla_days || 0)}.`);
        if(metrics.top_transaction) parts.push(`Jenis transaksi yang paling perlu menjadi perhatian adalah ${metrics.top_transaction.name} dengan rata-rata SLA ${fmtDays(metrics.top_transaction.avg_sla_days || 0)}.`);
        if(metrics.bottleneck) parts.push(`Bottleneck terbesar saat ini berada pada proses ${metrics.bottleneck.name} dengan rata-rata ${fmtDays(metrics.bottleneck.avg_sla_days || 0)}.`);
        if(metrics.latest_growth_pct !== null && metrics.latest_growth_pct !== undefined) parts.push(`Secara volume, transaksi terakhir ${Number(metrics.latest_growth_pct) >= 0 ? 'naik' : 'turun'} ${fmtPct(metrics.latest_growth_pct).replace('+','')} dibanding periode sebelumnya.`);
        parts.push(recommendationText());
        return parts.join(' ');
      }
      if(/rekomendasi|saran|apa yang harus diperbaiki|tindak lanjut/.test(q)){
        return `${naturalLead()} ${recommendationText() || 'Secara umum, fokuskan perbaikan pada proses dengan SLA terbesar dan lakukan pemantauan rutin terhadap transaksi prioritas.'}`;
      }
      if(/growth|pertumbuhan|naik|turun|dibanding periode sebelumnya|perbandingan periode/.test(q)){
        if(metrics.latest_growth_pct === null || metrics.latest_growth_pct === undefined){
          return 'Saat ini saya belum bisa menghitung growth karena data periodenya belum cukup untuk dibandingkan.';
        }
        const dir = Number(metrics.latest_growth_pct) >= 0 ? 'naik' : 'turun';
        let ans = `${naturalLead()} Jumlah transaksi pada periode terakhir ${dir} ${fmtPct(metrics.latest_growth_pct).replace('+','')} dibanding periode sebelumnya, dari ${fmtNum(metrics.prev_count || 0)} menjadi ${fmtNum(metrics.latest_count || 0)} transaksi.`;
        const latestPeriod = periodStats[periodStats.length-1];
        if(latestPeriod) ans += ` Periode terakhir yang terbaca adalah ${latestPeriod.periode}.`;
        return ans;
      }
      if(/berapa jumlah transaksi|total transaksi|jumlah transaksi/.test(q)){
        const p = findMentionedPeriod(q) || findMonthYearPeriod(q);
        const year = extractYear(q);
        if(p) return `${naturalLead()} Pada periode ${describeMonth(p)}, jumlah transaksinya sebanyak ${fmtNum(p.count)} transaksi.`;
        if(year){
          const y = yearStats.find(x => String(x.year) === String(year));
          if(y) return `${naturalLead()} Untuk tahun ${year}, total transaksi yang tercatat sebanyak ${fmtNum(y.count)} transaksi dengan rata-rata SLA ${fmtDays(y.avg_sla_days || 0)}.`;
        }
        return `${naturalLead()} Total transaksi aktif saat ini adalah ${fmtNum(metrics.transaction_count || 0)} transaksi, dengan cakupan periode ${metrics.period_first || '-'} sampai ${metrics.period_last || '-'}.`;
      }
      if(/sla total|rata-rata sla|sla keseluruhan|berapa sla/.test(q)){
        const p = findMentionedPeriod(q) || findMonthYearPeriod(q);
        const tr = findMentionedTransaction(q);
        const vd = findMentionedVendor(q);
        const nm = findMentionedNomor(q);
        if(p && p.avg_sla_days !== undefined) return `${naturalLead()} Pada periode ${describeMonth(p)}, rata-rata SLA totalnya adalah ${fmtDays(p.avg_sla_days)}.`;
        if(tr) return `${naturalLead()} Untuk jenis transaksi ${tr.name}, rata-rata SLA totalnya adalah ${fmtDays(tr.avg_sla_days || 0)} dengan volume ${fmtNum(tr.count || 0)} transaksi.`;
        if(vd) return `${naturalLead()} Untuk vendor ${vd.name}, rata-rata SLA totalnya adalah ${fmtDays(vd.avg_sla_days || 0)} dari ${fmtNum(vd.count || 0)} transaksi.`;
        if(nm) return `${naturalLead()} Untuk nomor permohonan ${nm.name}, rata-rata SLA totalnya adalah ${fmtDays(nm.avg_sla_days || 0)} dari ${fmtNum(nm.count || 0)} transaksi.`;
        return `${naturalLead()} Rata-rata SLA total seluruh data aktif saat ini adalah ${fmtDays(metrics.avg_sla_days || 0)}.`;
      }
      if(/jenis transaksi|transaksi apa yang paling lama|top sla|paling lambat/.test(q)){
        if(metrics.top_transaction){
          return `${naturalLead()} Jenis transaksi yang SLA-nya paling tinggi saat ini adalah ${metrics.top_transaction.name} dengan rata-rata ${fmtDays(metrics.top_transaction.avg_sla_days || 0)} dan volume ${fmtNum(metrics.top_transaction.count || 0)} transaksi.`;
        }
        return 'Saat ini saya belum menemukan data jenis transaksi yang cukup untuk dianalisis.';
      }
      if(/vendor|cabang/.test(q)){
        if(metrics.top_vendor){
          return `${naturalLead()} Vendor yang paling perlu dipantau saat ini adalah ${metrics.top_vendor.name} dengan rata-rata SLA ${fmtDays(metrics.top_vendor.avg_sla_days || 0)} dari ${fmtNum(metrics.top_vendor.count || 0)} transaksi.`;
        }
        return 'Saat ini data vendor/cabang belum tersedia atau belum cukup untuk dianalisis.';
      }
      if(/nomor permohonan|permohonan mana|request number|no permohonan/.test(q)){
        if(metrics.top_nomor){
          return `${naturalLead()} Nomor permohonan yang paling perlu dipantau saat ini adalah ${metrics.top_nomor.name} dengan rata-rata SLA ${fmtDays(metrics.top_nomor.avg_sla_days || 0)} dari ${fmtNum(metrics.top_nomor.count || 0)} transaksi.`;
        }
        return 'Saat ini saya belum menemukan kolom nomor permohonan pada data aktif.';
      }
      if(/bottleneck|kendala utama|proses paling lama|hambatan/.test(q)){
        if(metrics.bottleneck){
          return `${naturalLead()} Bottleneck terbesar saat ini berada pada proses ${metrics.bottleneck.name} dengan rata-rata SLA ${fmtDays(metrics.bottleneck.avg_sla_days || 0)}.`;
        }
        return 'Saat ini saya belum dapat menentukan bottleneck karena data SLA proses belum lengkap.';
      }
      if(/bandingkan.*20\\d{2}.*20\\d{2}|perbandingan.*20\\d{2}.*20\\d{2}/.test(q)){
        const years = text.match(/20\\d{2}/g) || [];
        if(years.length >= 2){
          const y1 = yearStats.find(y => String(y.year) === years[0]);
          const y2 = yearStats.find(y => String(y.year) === years[1]);
          if(y1 && y2){
            const diff = y1.count ? ((y2.count - y1.count) / y1.count * 100) : null;
            return `${naturalLead()} Pada tahun ${y1.year} terdapat ${fmtNum(y1.count)} transaksi, sedangkan tahun ${y2.year} terdapat ${fmtNum(y2.count)} transaksi. Perubahannya ${diff === null ? '-' : fmtPct(diff).replace('+','')} dengan rata-rata SLA masing-masing ${fmtDays(y1.avg_sla_days || 0)} dan ${fmtDays(y2.avg_sla_days || 0)}.`;
          }
        }
      }
      if(/nilai transaksi|nominal|amount/.test(q)){
        if(metrics.total_nilai !== null && metrics.total_nilai !== undefined){
          return `${naturalLead()} Total nilai transaksi pada data aktif adalah Rp ${fmtNum(metrics.total_nilai)}.`;
        }
        return 'Maaf, saat ini data nilai transaksi belum tersedia pada dataset aktif.';
      }
      if(/semua yang saya tanyakan|bisa jawab apa saja|apa yang bisa kamu jawab/.test(q)){
        return 'Saya bisa membantu menjawab pertanyaan terkait jumlah transaksi, perbandingan tahun atau periode, rata-rata SLA total, SLA per jenis transaksi, vendor/cabang paling lambat, nomor permohonan yang perlu dipantau, bottleneck proses, growth transaksi, nilai transaksi jika tersedia, serta membuat ringkasan Direksi dan rekomendasi perbaikan.';
      }
      return `${naturalLead()} Berdasarkan data aktif, terdapat ${fmtNum(metrics.transaction_count || 0)} transaksi dengan rata-rata SLA total ${fmtDays(metrics.avg_sla_days || 0)}. ${metrics.top_transaction ? `Jenis transaksi prioritas saat ini adalah ${metrics.top_transaction.name}. ` : ''}${metrics.bottleneck ? `Bottleneck terbesarnya berada pada proses ${metrics.bottleneck.name}. ` : ''}Jika ingin, Anda bisa bertanya lebih spesifik seperti “berapa SLA Vendor tahun 2025”, “SLA Keuangan Juni 2026”, “vendor mana paling lambat”, atau “buatkan ringkasan Direksi”.`;
    }

    function handleQuestion(question){
      const q = String(question || '').trim();
      if(!q) return;
      addMsg('user', q);
      statusLine.textContent = 'Status: SELA sedang menganalisis pertanyaan Anda.';
      setAvatarState('listening');
      setTimeout(() => {
        const ans = answer(q);
        addMsg('bot', ans);
        setBubble(ans);
        speak(ans);
      }, 260);
      textInput.value = '';
    }

    // mic
    let recognizer = null;
    let recognizing = false;
    function setupRecognizer(){
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if(!SR){
        statusLine.textContent = 'Status: browser ini belum mendukung pengenalan suara. Gunakan Chrome atau Edge, atau pakai input teks.';
        return null;
      }
      recognizer = new SR();
      recognizer.lang = 'id-ID';
      recognizer.interimResults = false;
      recognizer.maxAlternatives = 1;
      recognizer.onstart = () => {recognizing = true; setAvatarState('listening'); micBtn.textContent='⏹️ Stop'; statusLine.textContent='Status: SELA sedang mendengarkan...'; setBubble('Saya sedang mendengarkan. Silakan bicara dengan jelas ya.'); };
      recognizer.onerror = (e) => {recognizing = false; micBtn.textContent='🎙️ Bicara'; setAvatarState(''); statusLine.textContent = 'Status: mic belum masuk. Pastikan izin microphone di browser sudah Allow, lalu coba lagi. Detail: ' + e.error; setBubble('Saya belum menangkap suara. Coba klik Mic lagi, izinkan microphone, atau gunakan input teks.'); };
      recognizer.onend = () => {recognizing = false; micBtn.textContent='🎙️ Bicara'; if(!window.speechSynthesis.speaking){ setAvatarState(''); statusLine.textContent='Status: selesai mendengarkan, saya siap untuk pertanyaan berikutnya.'; } };
      recognizer.onresult = (event) => { const text = event.results && event.results[0] && event.results[0][0] ? event.results[0][0].transcript : ''; handleQuestion(text); };
      return recognizer;
    }

    micBtn.addEventListener('click', () => {
      if(!recognizer) setupRecognizer();
      if(!recognizer) return;
      try{
        if(!recognizing) recognizer.start(); else recognizer.stop();
      }catch(err){
        statusLine.textContent = 'Status: mic belum bisa digunakan. Coba refresh browser atau izinkan microphone.';
      }
    });
    checkMicBtn.addEventListener('click', () => {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if(SR){
        statusLine.textContent = 'Status: fitur microphone tersedia di browser. Jika belum masuk, pastikan izin microphone = Allow.';
        setBubble('Fitur mic tersedia. Sekarang coba klik tombol Bicara, lalu ucapkan pertanyaannya dengan jelas.');
      } else {
        statusLine.textContent = 'Status: browser ini belum mendukung microphone Web Speech API.';
        setBubble('Browser ini belum mendukung pengenalan suara. Silakan gunakan Chrome atau Edge, atau ketik pertanyaan Anda.');
      }
    });
    testVoiceBtn.addEventListener('click', () => {
      const txt = 'Halo, saya SELA. Suara saya sudah aktif dan siap membantu Anda.';
      setBubble(txt); speak(txt);
    });
    stopVoiceBtn.addEventListener('click', () => {
      if('speechSynthesis' in window) window.speechSynthesis.cancel();
      setAvatarState('');
      statusLine.textContent = 'Status: suara dihentikan.';
    });
    sendBtn.addEventListener('click', () => handleQuestion(textInput.value));
    textInput.addEventListener('keydown', (e) => { if(e.key === 'Enter') handleQuestion(textInput.value); });
    document.querySelectorAll('.chip').forEach(btn => btn.addEventListener('click', () => handleQuestion(btn.dataset.question)));

    populateMetrics();
    addMsg('bot', 'Halo, saya SELA. Senang bisa membantu Anda. Silakan tanyakan apa saja terkait data SLA yang sedang aktif, dan saya akan menjawabnya dengan bahasa yang natural, ramah, dan informatif.');
  </script>
</body>
</html>
    """

    components.html(
        html.replace("___SELA_PAYLOAD___", data_json),
        height=980,
        scrolling=False,
    )


# PANGGIL SELA HANYA JIKA USER MINTA (lebih ringan untuk halaman awal)
if st.session_state.get("show_sela", False):
    render_sela_widget(df_filtered, periode_col)

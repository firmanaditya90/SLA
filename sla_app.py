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
tab_overview, tab_proses, tab_transaksi, tab_vendor, tab_tren, tab_jumlah, tab_report, tab_analisis = st.tabs(
    ["🔍 Overview", "🧮 Per Proses", "🧾 Jenis Transaksi", "🏷️ Vendor", "📈 Tren", "📊 Jumlah Transaksi", "📥 Download Report","🧠 Analisis Data"]
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
    axES.text(0.00, 0.60, "Executive Score", fontsize=18, fontweight="bold", color=(0.02,0.08,0.16,0.95))
    axES.text(0.00, 0.10, f"Target KPI SLA: {_id_num(kpi_days,2,' hari')}", fontsize=13, color=(0.02,0.08,0.16,0.70), fontweight="bold")

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
    axF.text(1.00, 0.50, "Sumber: Tab Analisis (hasil filter aktif)",
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

    # Month names
    month_id = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    id_month = {v.lower(): k for k, v in month_id.items()}

    # CSS cards (kontras)
    st.markdown("""
<style>
.kpi-wrap{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:10px}
.kpi-card{
  border:1px solid rgba(49,51,63,.15);
  border-radius:16px;
  padding:14px 14px 12px;
  background:white;
  box-shadow:0 10px 22px rgba(0,0,0,.08);
}
.kpi-title{font-size:13px;color:rgba(15,23,42,.78);margin:0 0 6px 0;font-weight:700;text-align:center}
.kpi-value{font-size:40px;font-weight:900;line-height:1.1;margin:0;color:rgb(15,23,42);text-align:center}
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
</style>
""", unsafe_allow_html=True)

    def badge_class(delta):
        if delta is None or (isinstance(delta, float) and np.isnan(delta)):
            return "badge-flat"
        if delta > 0:
            return "badge-up"
        if delta < 0:
            return "badge-down"
        return "badge-flat"

    # -------------------------
    # Period lookup (FAST)
    # -------------------------
    @st.cache_data(show_spinner=False)
    def build_period_lookup(unique_period_values: tuple):
        def parse_to_period_m(s):
            if s is None:
                return pd.NaT
            s = str(s).strip()

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

        raw_to_period = {}
        for v in unique_period_values:
            raw = "" if v is None else str(v)
            raw_to_period[raw] = parse_to_period_m(raw)

        periods_sorted = sorted({p for p in raw_to_period.values() if pd.notna(p)})

        def month_label_from_period(p):
            return f"{month_id[int(p.month)]} {int(p.year)}"

        period_to_label = {p: month_label_from_period(p) for p in periods_sorted}
        labels_sorted = [period_to_label[p] for p in periods_sorted]
        years_sorted = sorted({int(p.year) for p in periods_sorted})

        return raw_to_period, periods_sorted, labels_sorted, period_to_label, years_sorted

    unique_period_values = tuple(pd.Series(df_raw[periode_col].astype(str).unique()).tolist())
    raw_to_period, periods, period_labels, period_to_label, years = build_period_lookup(unique_period_values)

    if not periods:
        st.warning("Tidak ada periode yang berhasil diparse. Periksa format kolom periode.")
        st.stop()

    label_to_period = {period_to_label[p]: p for p in periods}

    # SLA pick
    sla_options = available_sla_cols if "available_sla_cols" in locals() else []
    default_sla = "TOTAL WAKTU" if "TOTAL WAKTU" in sla_options else (sla_options[0] if sla_options else None)

    # -------------------------
    # Mode & Input
    # -------------------------
    st.markdown("### ⚙️ Mode Perbandingan")
    mode = st.radio(
        "Pilih mode",
        ["By Tahun (kumulatif)", "By Bulan (1 bulan)", "By Rentang (range bulan)"],
        horizontal=True,
        key="ana_mode_all_v3"
    )

    colA, colB, colS = st.columns([1, 1, 1])
    with colS:
        st.markdown("**Metrik SLA**")
        if default_sla:
            sla_pick = st.selectbox("Pilih SLA", sla_options, index=sla_options.index(default_sla), key="ana_sla_all_v3")
        else:
            sla_pick = None
            st.info("Kolom SLA tidak terdeteksi.")

    labelA = labelB = ""
    selA = []
    selB = []

    if mode == "By Tahun (kumulatif)":
        with colA:
            yearA = st.selectbox("Tahun A", years, index=0, key="ana_yearA_all_v3")
        with colB:
            yearB = st.selectbox("Tahun B", years, index=min(1, len(years) - 1), key="ana_yearB_all_v3")

        selA = [p for p in periods if int(p.year) == int(yearA)]
        selB = [p for p in periods if int(p.year) == int(yearB)]
        labelA, labelB = f"Tahun {yearA}", f"Tahun {yearB}"

    elif mode == "By Bulan (1 bulan)":
        with colA:
            mA = st.selectbox("Bulan A", period_labels, index=0, key="ana_monthA_all_v3")
        with colB:
            mB = st.selectbox("Bulan B", period_labels, index=min(1, len(period_labels) - 1), key="ana_monthB_all_v3")

        selA = [label_to_period[mA]]
        selB = [label_to_period[mB]]
        labelA, labelB = mA, mB

    else:  # range
        with colA:
            sA = st.selectbox("Mulai A", period_labels, index=0, key="ana_startA_all_v3")
            eA = st.selectbox("Sampai A", period_labels, index=len(period_labels) - 1, key="ana_endA_all_v3")
        with colB:
            sB = st.selectbox("Mulai B", period_labels, index=0, key="ana_startB_all_v3")
            eB = st.selectbox("Sampai B", period_labels, index=len(period_labels) - 1, key="ana_endB_all_v3")

        pA1, pA2 = label_to_period[sA], label_to_period[eA]
        pB1, pB2 = label_to_period[sB], label_to_period[eB]
        if pA1 > pA2 or pB1 > pB2:
            st.error("Rentang tidak valid (Mulai > Sampai).")
            st.stop()

        selA = [p for p in periods if pA1 <= p <= pA2]
        selB = [p for p in periods if pB1 <= p <= pB2]
        labelA, labelB = f"{sA} – {eA}", f"{sB} – {eB}"

    if not selA or not selB:
        st.warning("Periode A/B tidak memiliki data (hasil parse kosong).")
        st.stop()

    # Filter A/B
    df_base_local = df_base.copy()
    df_base_local["PERIOD_M"] = df_base_local[periode_col].astype(str).map(raw_to_period)

    dfA = df_base_local[df_base_local["PERIOD_M"].isin(selA)].copy()
    dfB = df_base_local[df_base_local["PERIOD_M"].isin(selB)].copy()

    # Core metrics
    totalA, totalB = len(dfA), len(dfB)
    d_total = totalB - totalA
    p_total = pct_change(totalA, totalB)

    has_sla = bool(sla_pick and sla_pick in df_base_local.columns)
    meanA = meanB = np.nan

    if has_sla:
        sA = pd.to_numeric(dfA[sla_pick], errors="coerce").dropna()
        sB = pd.to_numeric(dfB[sla_pick], errors="coerce").dropna()
        meanA = float(sA.mean()) if len(sA) else np.nan
        meanB = float(sB.mean()) if len(sB) else np.nan

    # -------------------------
    # Ringkasan Utama (Direksi)
    # -------------------------
    st.markdown("---")
    st.markdown("### 🧾 Ringkasan Utama (Direksi)")

    d_sla = (meanB - meanA) if (has_sla and np.isfinite(meanA) and np.isfinite(meanB)) else np.nan
    badge_sla = (("−" if d_sla < 0 else "+") + _sla_short_days(abs(d_sla), 2)) if np.isfinite(d_sla) else "-"
    badge_vol = f"{_id_int(d_total)} ({_id_num(p_total,2,'%')})" if np.isfinite(p_total) else _id_int(d_total)

    html_cards = f"""
    <div class="kpi-wrap">
      <div class="kpi-card">
        <p class="kpi-title">Total Transaksi ({labelA})</p>
        <p class="kpi-value">{_id_int(totalA)}</p>
        <div class="kpi-sub">Baseline periode A</div>
      </div>

      <div class="kpi-card">
        <p class="kpi-title">Total Transaksi ({labelB})</p>
        <p class="kpi-value">{_id_int(totalB)}</p>
        <span class="badge {badge_class(d_total)}">{badge_vol}</span>
        <div class="kpi-sub">Perubahan vs A</div>
      </div>

      <div class="kpi-card">
        <p class="kpi-title">Avg SLA ({labelA})</p>
        <p class="kpi-value">{_sla_short_days(meanA,2)}</p>
        <div class="kpi-sub">{_sla_long_id(meanA)}</div>
      </div>

      <div class="kpi-card">
        <p class="kpi-title">Avg SLA ({labelB})</p>
        <p class="kpi-value">{_sla_short_days(meanB,2)}</p>
        <span class="badge {badge_class(-1 if (np.isfinite(d_sla) and d_sla<0) else (1 if (np.isfinite(d_sla) and d_sla>0) else 0))}">{badge_sla}</span>
        <div class="kpi-sub">{_sla_long_id(meanB)}</div>
      </div>
    </div>
    """
    st.markdown(html_cards, unsafe_allow_html=True)

    vol_dir = "naik" if d_total > 0 else ("turun" if d_total < 0 else "stabil")
    spot = f"• Volume transaksi <b>{vol_dir}</b>: {_id_int(totalA)} → {_id_int(totalB)} (Δ {badge_vol})."
    if has_sla and np.isfinite(d_sla):
        sla_dir = "membaik" if d_sla < 0 else ("memburuk" if d_sla > 0 else "stabil")
        spot += f" • SLA <b>{sla_dir}</b>: <b>{_sla_short_days(meanA,2)}</b> → <b>{_sla_short_days(meanB,2)}</b> (Δ {badge_sla})."
    else:
        spot += " • SLA: <b>tidak tersedia</b>."
    st.markdown(f'<div class="hero">{spot}</div>', unsafe_allow_html=True)

    # -------------------------
    # Executive Score
    # -------------------------
    st.markdown("### 🏁 Executive Score")
    saved_kpi = load_kpi() if "load_kpi" in globals() else None
    kpi_days = float(saved_kpi) if saved_kpi is not None else 1.5
    kpi_sec = kpi_days * 86400.0
    st.markdown(f'<div class="small-cap">Target KPI SLA (mengikuti Overview): <b>{_id_num(kpi_days,2," hari")}</b></div>', unsafe_allow_html=True)

    complianceA = complianceB = np.nan
    coverageA = coverageB = np.nan
    d_comp = d_cov = np.nan

    if has_sla:
        sA_all = pd.to_numeric(dfA[sla_pick], errors="coerce")
        sB_all = pd.to_numeric(dfB[sla_pick], errors="coerce")

        coverageA = float(sA_all.notna().mean() * 100) if len(dfA) else np.nan
        coverageB = float(sB_all.notna().mean() * 100) if len(dfB) else np.nan
        d_cov = coverageB - coverageA if (np.isfinite(coverageA) and np.isfinite(coverageB)) else np.nan

        validA = sA_all.dropna()
        validB = sB_all.dropna()
        complianceA = float((validA <= kpi_sec).mean() * 100) if len(validA) else np.nan
        complianceB = float((validB <= kpi_sec).mean() * 100) if len(validB) else np.nan
        d_comp = complianceB - complianceA if (np.isfinite(complianceA) and np.isfinite(complianceB)) else np.nan

    # -------------------------
    # Tren overlay (A vs B, sumbu x = bulan)
    # -------------------------
    st.markdown("### 📈 Tren (Per Bulan — Overlay A vs B)")

    seriesA = year_or_label(selA, "A")
    seriesB = year_or_label(selB, "B")

    months_union = sorted({int(p.month) for p in selA} | {int(p.month) for p in selB})
    if not months_union:
        months_union = list(range(1, 13))
    month_order = [month_id[m] for m in months_union]

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
        seriesA: [float(A_trx.get(m, 0)) for m in months_union],
        seriesB: [float(B_trx.get(m, 0)) for m in months_union],
    })
    vol_long = vol_month.melt(id_vars=["Bulan"], var_name="Seri", value_name="Transaksi")

    fig_vol = px.line(
        vol_long, x="Bulan", y="Transaksi", color="Seri",
        markers=True, category_orders={"Bulan": month_order},
        title=f"Volume Transaksi — {seriesA} vs {seriesB}"
    )
    fig_vol.update_layout(xaxis_title=None, yaxis_title="Jumlah Transaksi", legend_title=None)
    st.plotly_chart(fig_vol, use_container_width=True)

    sla_month = None
    if has_sla:
        def sla_by_monthnum(df):
            if df.empty:
                return {}
            x = df.copy()
            x[sla_pick] = pd.to_numeric(x[sla_pick], errors="coerce")
            g = x.groupby("PERIOD_M")[sla_pick].mean().reset_index(name="sla_sec")
            g["m"] = g["PERIOD_M"].apply(lambda p: int(p.month))
            return g.groupby("m")["sla_sec"].mean().to_dict()

        A_sla = sla_by_monthnum(dfA)
        B_sla = sla_by_monthnum(dfB)

        sla_month = pd.DataFrame({
            "Bulan": month_order,
            seriesA: [float(A_sla.get(m, np.nan)) / 86400.0 for m in months_union],
            seriesB: [float(B_sla.get(m, np.nan)) / 86400.0 for m in months_union],
        })
        sla_long = sla_month.melt(id_vars=["Bulan"], var_name="Seri", value_name="SLA (hari)")

        fig_sla = px.line(
            sla_long, x="Bulan", y="SLA (hari)", color="Seri",
            markers=True, category_orders={"Bulan": month_order},
            title=f"SLA Rata-rata (hari) — {sla_pick} | {seriesA} vs {seriesB}"
        )
        fig_sla.update_layout(xaxis_title=None, yaxis_title="Rata-rata SLA (hari)", legend_title=None)
        st.plotly_chart(fig_sla, use_container_width=True)
    else:
        st.info("Grafik SLA tidak ditampilkan karena kolom SLA tidak tersedia/valid.")

    # -------------------------
    # Insight Otomatis (tabel ringkas per bulan)
    # -------------------------
    st.markdown("### 🧠 Insight Otomatis (Ringkas per Bulan)")
    colA_name = year_or_label(selA, "A")
    colB_name = year_or_label(selB, "B")

    months_union2 = sorted({int(p.month) for p in selA} | {int(p.month) for p in selB})
    if not months_union2:
        months_union2 = list(range(1, 13))
    month_rows2 = [month_id[m] for m in months_union2]

    A_trx2 = trx_by_monthnum(dfA)
    B_trx2 = trx_by_monthnum(dfB)

    tbl = pd.DataFrame({"Bulan": month_rows2})
    tbl[colA_name] = [float(A_trx2.get(m, 0)) for m in months_union2]
    tbl[colB_name] = [float(B_trx2.get(m, 0)) for m in months_union2]
    tbl["Selisih"] = tbl[colB_name] - tbl[colA_name]
    tbl["Growth %"] = np.where(tbl[colA_name] == 0, np.nan, (tbl[colB_name] - tbl[colA_name]) / tbl[colA_name] * 100)

    st.dataframe(
        tbl.set_index("Bulan").style
            .format({colA_name: "{:,.0f}", colB_name: "{:,.0f}", "Selisih": "{:+,.0f}", "Growth %": "{:+.2f}%"})
            .highlight_null(color="lightgray"),
        use_container_width=True
    )

    st.info(
        f"• Total transaksi {colA_name}: **{_id_int(tbl[colA_name].sum())}** | {colB_name}: **{_id_int(tbl[colB_name].sum())}**\n"
        f"• Growth total: **{_id_num(p_total,2,'%') if np.isfinite(p_total) else '-'}** (Δ **{_id_int(d_total)} trx**)\n"
        f"• KPI Compliance ≤ {_id_num(kpi_days,2,' hari')}: **{_id_num(complianceB,2,'%') if np.isfinite(complianceB) else '-'}**\n"
        f"• Coverage SLA: **{_id_num(coverageB,2,'%') if np.isfinite(coverageB) else '-'}**"
    )

    # ============================================================
    # BLOK POSTER EXECUTIVE SUMMARY — FIXED LAYOUT (NO OVERLAP)
    # ============================================================
    st.markdown("---")
    st.markdown("### 🖼️ Poster Executive Summary (Analisis)")

    # (opsional) animasi di UI saja (bukan di poster)
    gif_url = "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"
    gif_bytes = _fetch_image_bytes(gif_url)
    if gif_bytes:
        st.image(gif_bytes, width=220)

    # Logo Danantara (kiri), ASDP (kanan)
    logo_left_bytes = _fetch_image_bytes(LOGO_LEFT_URL)
    logo_right_bytes = _fetch_image_bytes(LOGO_RIGHT_URL)

    c1, c2 = st.columns([1, 1])
    with c1:
        poster_title = st.text_input("Judul Poster", value="EXECUTIVE SUMMARY", key="ana_poster_title_v3")
    with c2:
        poster_subtitle = st.text_input("Sub Judul", value="Analisis SLA & Transaksi", key="ana_poster_subtitle_v3")

    headline = build_auto_headline(totalA, totalB, meanA, meanB, p_total, d_total)

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

# ==========================================================
#  VIRTUAL ASSISTANT: "Tanya SELA"
#  - 3D avatar (Three.js + GLTFLoader)
#  - WebLLM (MLC) dengan lazy-load (baru download saat tombol 🎤 ditekan)
#  - Jawaban lebih dulu berbasis data df_filtered (SLA & transaksi)
# ==========================================================
import streamlit.components.v1 as components
import json
import pandas as pd


def render_sela_widget(df_filtered, periode_col: str):
    """
    df_filtered : DataFrame yang sedang aktif di tab (sudah difilter oleh user)
    periode_col : nama kolom periode, misalnya "PERIODE"
    """
    rows = []
    if (
        df_filtered is not None
        and isinstance(df_filtered, pd.DataFrame)
        and not df_filtered.empty
        and periode_col in df_filtered.columns
    ):
        cols = df_filtered.columns
        for _, r in df_filtered.iterrows():
            rec = {"periode": str(r[periode_col])}

            # Vendor / Cabang
            if "NAMA VENDOR" in cols:
                rec["nama_vendor"] = str(r["NAMA VENDOR"])

            # Jenis transaksi
            if "JENIS TRANSAKSI" in cols:
                rec["jenis_transaksi"] = str(r["JENIS TRANSAKSI"])

            # Kolom SLA (detik)
            for col in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]:
                if col in cols:
                    val = r[col]
                    if pd.notna(val):
                        try:
                            rec[col.lower().replace(" ", "_")] = float(val)
                        except Exception:
                            pass

            rows.append(rec)

    data_json = json.dumps(rows, ensure_ascii=False)

    html = """
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    .sela-panel-root {
      width: 100%;
      max-width: 420px;
      height: 480px;
      margin: 0 auto;
      background: rgba(15,23,42,0.96);
      border-radius: 20px;
      box-shadow: 0 18px 40px rgba(0,0,0,0.65);
      border: 1px solid rgba(148,163,184,0.7);
      backdrop-filter: blur(16px);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      color: #e5e7eb;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .sela-panel-header {
      padding: 10px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(148,163,184,0.4);
      background: radial-gradient(circle at top left, rgba(80,250,123,0.15), transparent);
    }
    .sela-panel-header-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .sela-avatar-circle {
      width: 30px;
      height: 30px;
      border-radius: 999px;
      background: linear-gradient(135deg,#7f5af0,#2cb67d);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 14px;
      color: #fff;
    }
    .sela-title {
      font-size: 13px;
      font-weight: 600;
    }
    .sela-subtitle {
      font-size: 11px;
      opacity: 0.75;
    }

    .sela-3d-container {
      flex: 1.6;
      background: #ffffff;
      position: relative;
    }
    #sela-canvas {
      width: 100%;
      height: 100%;
      display: block;
    }

    .sela-status {
      padding: 6px 11px;
      font-size: 11px;
      border-bottom: 1px solid rgba(51,65,85,0.8);
      background: rgba(15,23,42,0.95);
    }

    .sela-bottom {
      flex: 0.9;
      padding: 10px 12px 12px 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      background: radial-gradient(circle at bottom right, rgba(56,189,248,0.25), transparent);
    }

    .sela-tip {
      font-size: 11px;
      opacity: 0.82;
    }

    .sela-controls {
      display: flex;
      gap: 8px;
      align-items: center;
      margin-top: 2px;
    }

    .sela-talk-btn {
      flex: 1;
      border-radius: 999px;
      border: none;
      padding: 8px 10px;
      font-size: 13px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      cursor: pointer;
      background: linear-gradient(135deg,#22c55e,#4ade80);
      color: #022c22;
      box-shadow: 0 8px 22px rgba(16,185,129,0.5);
    }
    .sela-talk-btn.sela-listening {
      background: linear-gradient(135deg,#f97316,#fb923c);
      color: #111827;
      box-shadow: 0 8px 22px rgba(248,113,113,0.55);
    }

    .sela-mini-led {
      width: 11px;
      height: 11px;
      border-radius: 999px;
      background: #22c55e;
      box-shadow: 0 0 8px rgba(34,197,94,0.9);
    }
    .sela-mini-led.off {
      background: #9ca3af;
      box-shadow: none;
    }

    .sela-note {
      font-size: 10px;
      opacity: 0.75;
    }
  </style>
</head>
<body>
  <div class="sela-panel-root">
    <div class="sela-panel-header">
      <div class="sela-panel-header-left">
        <div class="sela-avatar-circle">S</div>
        <div>
          <div class="sela-title">SELA • Virtual Assistant</div>
          <div class="sela-subtitle">
            “Saya bantu bacakan data SLA & transaksi, sekaligus jawab pertanyaan umum.”
          </div>
        </div>
      </div>
    </div>

    <div class="sela-3d-container">
      <canvas id="sela-canvas"></canvas>
    </div>

    <div id="sela-status" class="sela-status">
      Status: menyiapkan SELA (3D + AI) dalam mode hemat sumber daya...
    </div>

    <div class="sela-bottom">
      <div class="sela-tip">
        Contoh pertanyaan:
        <ul style="margin:4px 0 0 14px;padding:0;font-size:11px;">
          <li>“Berapa jumlah transaksi tahun 2025?”</li>
          <li>“Bandingkan transaksi 2025 dengan 2024.”</li>
          <li>“Berapa SLA total periode Juni 2024?”</li>
          <li>“Berapa transaksi dari Januari 2025 sampai November 2025?”</li>
        </ul>
      </div>
      <div class="sela-controls">
        <button id="sela-talk-btn" class="sela-talk-btn">
          🎤 Bicara dengan SELA
        </button>
        <div>
          <div id="sela-led" class="sela-mini-led off"></div>
        </div>
      </div>
      <div class="sela-note">
        *Model AI baru diunduh saat tombol 🎤 pertama kali ditekan, supaya dashboard tetap ringan.
      </div>
    </div>
  </div>

  <script type="module">
    import * as THREE from "https://esm.run/three@0.160.0";
    import { GLTFLoader } from "https://esm.run/three@0.160.0/examples/jsm/loaders/GLTFLoader.js";

    // ========= DATA DARI STREAMLIT =========
    const selaDataRows = ___SELA_DATA___;

    const statusEl = document.getElementById("sela-status");
    const talkBtn  = document.getElementById("sela-talk-btn");
    const led      = document.getElementById("sela-led");
    window._sela_processing = false;

    // ========= HELPER WAKTU & PERIODE =========
    function secondsToPretty(sec) {
      if (sec == null || isNaN(sec)) return "0 hari 0 jam 0 menit";
      const s = Math.max(0, Number(sec));
      const d = Math.floor(s / 86400);
      const h = Math.floor((s % 86400) / 3600);
      const m = Math.floor((s % 3600) / 60);
      return d + " hari " + h + " jam " + m + " menit";
    }

    const MONTH_DEFS = [
      { num: 1,  labels: ["januari","jan"] },
      { num: 2,  labels: ["februari","feb"] },
      { num: 3,  labels: ["maret","mar"] },
      { num: 4,  labels: ["april","apr"] },
      { num: 5,  labels: ["mei","mei"] },
      { num: 6,  labels: ["juni","jun"] },
      { num: 7,  labels: ["juli","jul"] },
      { num: 8,  labels: ["agustus","agus","agt","agu"] },
      { num: 9,  labels: ["september","sep"] },
      { num: 10, labels: ["oktober","okt"] },
      { num: 11, labels: ["november","nov"] },
      { num: 12, labels: ["desember","des"] }
    ];
    const MONTH_LABEL_ID = [
      "Januari","Februari","Maret","April","Mei","Juni",
      "Juli","Agustus","September","Oktober","November","Desember"
    ];
    function monthNameFromNum(n) {
      if (n < 1 || n > 12) return "bulan ke-" + n;
      return MONTH_LABEL_ID[n - 1];
    }

    function parsePeriodeInfo(str) {
      const lower = String(str || "").toLowerCase();
      const yearMatch = lower.match(/20\\d{2}/);
      if (!yearMatch) return null;
      const year = parseInt(yearMatch[0], 10);
      let month = null;
      for (let i = 0; i < MONTH_DEFS.length; i++) {
        const m = MONTH_DEFS[i];
        for (let j = 0; j < m.labels.length; j++) {
          const label = m.labels[j];
          if (lower.indexOf(label) >= 0) {
            month = m.num;
            break;
          }
        }
        if (month) break;
      }
      return { year, month };
    }

    function parseRangeFromText(text) {
      const lower = (text || "").toLowerCase();
      const yearMatch = lower.match(/20\\d{2}/);
      const year = yearMatch ? parseInt(yearMatch[0], 10) : null;

      const mentionYearOnly =
        year && (lower.includes("tahun") || lower.includes("selama") || lower.includes("sepanjang"));

      const monthHits = [];
      MONTH_DEFS.forEach((m) => {
        let bestPos = null;
        m.labels.forEach((label) => {
          const pos = lower.indexOf(label);
          if (pos >= 0 && (bestPos === null || pos < bestPos)) bestPos = pos;
        });
        if (bestPos !== null) monthHits.push({ month: m.num, pos: bestPos });
      });
      monthHits.sort((a,b) => a.pos - b.pos);

      if (year && monthHits.length >= 2) {
        const startM = monthHits[0].month;
        const endM   = monthHits[monthHits.length - 1].month;
        if (startM <= endM) {
          return { type: "month-range", year, startMonth: startM, endMonth: endM };
        }
      }
      if (mentionYearOnly && year) {
        return { type: "year", year };
      }
      return null;
    }

    function describeRange(range) {
      if (!range) return null;
      if (range.type === "year") {
        return "tahun " + range.year;
      }
      if (range.type === "month-range") {
        return "dari " + monthNameFromNum(range.startMonth) + " " + range.year +
               " sampai " + monthNameFromNum(range.endMonth) + " " + range.year;
      }
      return null;
    }

    function rowInRange(periodeStr, range) {
      if (!range) return true;
      const info = parsePeriodeInfo(periodeStr);
      if (!info) return false;
      if (range.type === "year") {
        return info.year === range.year;
      }
      if (range.type === "month-range") {
        if (info.year !== range.year) return false;
        if (!info.month) return false;
        return info.month >= range.startMonth && info.month <= range.endMonth;
      }
      return true;
    }

    function findPeriodeInData(userText) {
      if (!selaDataRows || !selaDataRows.length) return null;
      const txt = (userText || "").toLowerCase();
      const uniques = [];
      selaDataRows.forEach((r) => {
        const p = String(r.periode || "");
        if (p && !uniques.includes(p)) uniques.push(p);
      });
      let found = null;
      uniques.forEach((p) => {
        const pl = p.toLowerCase();
        if (pl && txt.indexOf(pl) >= 0) found = p;
      });
      return found;
    }

    function findAllPeriodesInText(userText) {
      if (!selaDataRows || !selaDataRows.length) return [];
      const txt = (userText || "").toLowerCase();
      const uniques = [];
      selaDataRows.forEach((r) => {
        const p = String(r.periode || "");
        if (p && !uniques.includes(p)) uniques.push(p);
      });
      const matches = [];
      const seen = {};
      uniques.forEach((p) => {
        const label = p.toLowerCase();
        const pos = txt.indexOf(label);
        if (pos >= 0 && !seen[label]) {
          seen[label] = true;
          matches.push({ periode: p, pos });
        }
      });
      matches.sort((a,b) => a.pos - b.pos);
      return matches.map((m) => m.periode);
    }

    function findVendorInText(userText) {
      if (!selaDataRows || !selaDataRows.length) return null;
      const txt = (userText || "").toLowerCase();
      const vendors = [];
      selaDataRows.forEach((r) => {
        const v = r.nama_vendor ? String(r.nama_vendor) : "";
        if (v && !vendors.includes(v)) vendors.push(v);
      });
      let found = null;
      vendors.forEach((v) => {
        const lv = v.toLowerCase();
        if (lv && txt.indexOf(lv) >= 0) found = v;
      });
      return found;
    }

    function findJenisTransaksiInText(userText) {
      if (!selaDataRows || !selaDataRows.length) return null;
      const txt = (userText || "").toLowerCase();
      const jenisList = [];
      selaDataRows.forEach((r) => {
        const v = r.jenis_transaksi ? String(r.jenis_transaksi) : "";
        if (v && !jenisList.includes(v)) jenisList.push(v);
      });
      let found = null;
      jenisList.forEach((v) => {
        const lv = v.toLowerCase();
        if (lv && txt.indexOf(lv) >= 0) found = v;
      });
      return found;
    }

    function countTransaksi(periode, vendor, jenis, range) {
      if (!selaDataRows || !selaDataRows.length) return 0;
      return selaDataRows.filter((r) => {
        if (range && !rowInRange(r.periode, range)) return false;
        if (!range && periode && String(r.periode) !== String(periode)) return false;
        if (vendor && String(r.nama_vendor || "").toLowerCase() !== vendor.toLowerCase()) return false;
        if (jenis && String(r.jenis_transaksi || "").toLowerCase() !== jenis.toLowerCase()) return false;
        return true;
      }).length;
    }

    function aggregateSLA(colKey, periode, vendor, jenis, range) {
      if (!selaDataRows || !selaDataRows.length) return null;
      const rows = selaDataRows.filter((r) => {
        if (range && !rowInRange(r.periode, range)) return false;
        if (!range && periode && String(r.periode) !== String(periode)) return false;
        if (vendor && String(r.nama_vendor || "").toLowerCase() !== vendor.toLowerCase()) return false;
        if (jenis && String(r.jenis_transaksi || "").toLowerCase() !== jenis.toLowerCase()) return false;
        return typeof r[colKey] === "number";
      });
      if (!rows.length) return null;
      const sum = rows.reduce((a,b) => a + b[colKey], 0);
      const avg = sum / rows.length;
      return { avg, text: secondsToPretty(avg), count: rows.length };
    }

    // ========= JAWABAN DATA-FIRST (ANALITIS) =========
    function answerWithData(userText) {
      if (!selaDataRows || !selaDataRows.length) return null;

      const t = (userText || "").toLowerCase();
      const periodeSingle = findPeriodeInData(userText);
      const range         = parseRangeFromText(userText);
      const vendor        = findVendorInText(userText);
      const jenis         = findJenisTransaksiInText(userText);
      const periodesText  = findAllPeriodesInText(userText);

      const timeDesc = range
        ? describeRange(range)
        : (periodeSingle ? "periode " + periodeSingle : "periode yang sedang ditampilkan");

      const isCompareIntent =
        t.includes("banding") ||
        t.includes("dibanding") ||
        t.includes("versus") ||
        t.includes(" vs ");

      const isDifferenceIntent =
        t.includes("selisih") ||
        t.includes("beda") ||
        t.includes("perbedaan");

      // ---- deteksi 2 tahun untuk bandingkan transaksi ----
      const yearMatchesRaw = t.match(/20\\d{2}/g);
      const uniqueYears = [];
      if (yearMatchesRaw) {
        yearMatchesRaw.forEach((yy) => {
          if (!uniqueYears.includes(yy)) uniqueYears.push(yy);
        });
      }

      const compareYearIntent =
        uniqueYears.length >= 2 &&
        (isCompareIntent || isDifferenceIntent || t.includes("bandingkan")) &&
        t.includes("transaksi") &&
        (t.includes("tahun") || t.includes("th"));

      if (compareYearIntent) {
        const y1 = parseInt(uniqueYears[0], 10);
        const y2 = parseInt(uniqueYears[1], 10);

        const range1 = { type: "year", year: y1 };
        const range2 = { type: "year", year: y2 };

        const n1 = countTransaksi(null, vendor || null, jenis || null, range1);
        const n2 = countTransaksi(null, vendor || null, jenis || null, range2);

        if (n1 === 0 && n2 === 0) {
          return "Maaf, saya tidak menemukan transaksi untuk tahun " + y1 +
                 " maupun " + y2 + " pada data yang sedang ditampilkan.";
        }

        let konteksY = "";
        if (vendor) konteksY += " untuk vendor " + vendor;
        if (jenis)  konteksY += " dengan jenis transaksi " + jenis;

        const diff    = n1 - n2;
        const absDiff = Math.abs(diff);

        let arah = "perubahan";
        if (diff > 0) arah = "peningkatan";
        else if (diff < 0) arah = "penurunan";

        const base = Math.min(n1, n2);
        let pct = 0;
        if (base > 0 && absDiff > 0) {
          pct = Math.round((absDiff / base) * 100);
        }

        const kal1 =
          "Jumlah transaksi tahun " + y1 + konteksY +
          " sekitar " + n1 + " transaksi, sedangkan tahun " +
          y2 + " sekitar " + n2 + " transaksi.";

        let kal2 = "";
        if (absDiff === 0) {
          kal2 = " Artinya, volume transaksi di kedua tahun tersebut relatif sama besar dalam data ini.";
        } else {
          kal2 = " Artinya terdapat " + arah + " sekitar " + absDiff +
                 " transaksi (sekitar " + pct +
                 "%) jika dibandingkan tahun dengan volume transaksi yang lebih kecil.";
        }

        return kal1 + kal2;
      }

      // ---- bandingkan jumlah transaksi dua periode ----
      if (periodesText.length >= 2 && (isCompareIntent || isDifferenceIntent)) {
        const p1 = periodesText[0];
        const p2 = periodesText[1];

        const isTransaksiCompare =
          t.includes("jumlah transaksi") ||
          t.includes("banyak transaksi") ||
          (t.includes("transaksi") && (isCompareIntent || isDifferenceIntent));

        if (isTransaksiCompare) {
          const n1 = countTransaksi(p1, vendor || null, jenis || null, null);
          const n2 = countTransaksi(p2, vendor || null, jenis || null, null);

          if (n1 === 0 && n2 === 0) {
            return "Maaf, saya tidak menemukan transaksi untuk periode " + p1 +
                   " maupun " + p2 + " pada data ini.";
          }

          let konteks = "";
          if (vendor) konteks += " untuk vendor " + vendor;
          if (jenis)  konteks += " dengan jenis transaksi " + jenis;

          if (isDifferenceIntent) {
            const diff    = Math.abs(n1 - n2);
            const base    = Math.min(n1, n2);
            let pctText   = "";
            if (base > 0 && diff > 0) {
              const pct = Math.round((diff / base) * 100);
              pctText   = " (sekitar " + pct +
                          "% dibanding periode dengan transaksi lebih sedikit)";
            }

            let siapa;
            if (n1 > n2) {
              siapa = "periode " + p1 + " memiliki sekitar " + (n1 - n2) +
                      " transaksi lebih banyak daripada " + p2 + pctText;
            } else if (n2 > n1) {
              siapa = "periode " + p2 + " memiliki sekitar " + (n2 - n1) +
                      " transaksi lebih banyak daripada " + p1 + pctText;
            } else {
              siapa = "jumlah transaksinya sama besar pada kedua periode";
            }

            return "Selisih jumlah transaksi" + konteks +
                   " antara periode " + p1 + " (" + n1 +
                   ") dan " + p2 + " (" + n2 +
                   ") sekitar " + diff +
                   " transaksi; " + siapa + ".";
          } else {
            let isi;
            if (n1 > n2) {
              isi = "periode " + p1 + " memiliki transaksi lebih banyak (" +
                    n1 + ") dibanding periode " + p2 + " (" + n2 + ").";
            } else if (n2 > n1) {
              isi = "periode " + p2 + " memiliki transaksi lebih banyak (" +
                    n2 + ") dibanding periode " + p1 + " (" + n1 + ").";
            } else {
              isi = "jumlah transaksi pada periode " + p1 + " dan " + p2 +
                    " sama, yaitu " + n1 + " transaksi.";
            }
            return "Untuk transaksi" + konteks + ", " + isi;
          }
        }
      }

      // ---- jumlah transaksi tahun / range bulan / satu periode ----
      if (t.includes("jumlah transaksi") || t.includes("berapa transaksi")) {
        const n = countTransaksi(
          range ? null : (periodeSingle || null),
          vendor || null,
          jenis || null,
          range || null
        );
        let desc = range ? describeRange(range) : (periodeSingle || "periode yang sedang ditampilkan");
        if (vendor) desc += " untuk vendor " + vendor;
        if (jenis)  desc += " dengan jenis transaksi " + jenis;
        return (
          "Jumlah transaksi pada " +
          desc +
          " sekitar " +
          n +
          " transaksi berdasarkan data yang sedang ditampilkan."
        );
      }

      // ---- rata-rata SLA total / per proses ----
      const prosesMap = [
        { triggers: ["sla keuangan"],            key: "keuangan",       label: "SLA Keuangan" },
        { triggers: ["sla fungsional"],          key: "fungsional",     label: "SLA Fungsional" },
        { triggers: ["sla vendor"],              key: "vendor",         label: "SLA Vendor" },
        { triggers: ["sla perbendaharaan"],      key: "perbendaharaan", label: "SLA Perbendaharaan" },
        { triggers: ["sla total","total waktu"], key: "total_waktu",    label: "SLA Total Waktu" }
      ];

      for (let i = 0; i < prosesMap.length; i++) {
        const pp = prosesMap[i];
        const match = pp.triggers.some((tr) => t.includes(tr));
        if (!match) continue;

        const agg = aggregateSLA(
          pp.key,
          range ? null : (periodeSingle || null),
          vendor || null,
          jenis || null,
          range || null
        );
        if (!agg) {
          return (
            "Maaf, saya belum menemukan data " +
            pp.label +
            " pada " +
            timeDesc +
            " untuk kombinasi filter yang sedang dipakai."
          );
        }

        let konteks = " pada " + timeDesc;
        if (vendor) konteks += " untuk vendor " + vendor;
        if (jenis)  konteks += " dengan jenis transaksi " + jenis;

        return (
          pp.label +
          " rata-rata sekitar " +
          agg.text +
          konteks +
          ". Nilai ini bisa dipakai sebagai gambaran seberapa cepat proses tersebut berjalan."
        );
      }

      return null;
    }

    // ========= 3D AVATAR SELA =========
    const AVATAR_URL = "https://raw.githubusercontent.com/met4citizen/TalkingHead/main/avatars/brunette.glb";

    function pickIndonesianVoice() {
      if (!("speechSynthesis" in window)) return null;
      const voices = window.speechSynthesis.getVoices() || [];
      for (let i = 0; i < voices.length; i++) {
        const v = voices[i];
        if (v.lang && v.lang.toLowerCase().indexOf("id") === 0) return v;
      }
      return null;
    }

    const canvas = document.getElementById("sela-canvas");
    const scene  = new THREE.Scene();
    scene.background = new THREE.Color(0xffffff);

    const camera = new THREE.PerspectiveCamera(
      40,
      (canvas.clientWidth || 360) / (canvas.clientHeight || 260),
      0.1,
      100
    );
    camera.position.set(0, 1.4, 5);
    camera.lookAt(0, 1.4, 0);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    function resizeRenderer() {
      const width  = canvas.clientWidth || 360;
      const height = canvas.clientHeight || 260;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
    resizeRenderer();
    window.addEventListener("resize", resizeRenderer);

    const hemi = new THREE.HemisphereLight(0xffffff, 0xdddddd, 1.2);
    scene.add(hemi);
    const dir = new THREE.DirectionalLight(0xffffff, 0.9);
    dir.position.set(2, 4, 3);
    scene.add(dir);

    // fallback bola+silinder sederhana
    const headGeo = new THREE.SphereGeometry(0.8, 40, 32);
    const headMat = new THREE.MeshStandardMaterial({ color: 0xf9a8d4, metalness: 0.1, roughness: 0.3 });
    const head = new THREE.Mesh(headGeo, headMat);
    head.position.y = 0.6;
    scene.add(head);

    const bodyGeo = new THREE.CylinderGeometry(0.9, 1.0, 1.3, 32);
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, metalness: 0.1, roughness: 0.4 });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = -0.4;
    scene.add(body);

    const mouthGeo = new THREE.CapsuleGeometry(0.18, 0.06, 4, 12);
    const mouthMat = new THREE.MeshStandardMaterial({ color: 0x0f172a });
    const mouth_fb = new THREE.Mesh(mouthGeo, mouthMat);
    mouth_fb.position.set(0, 0.48, 0.72);
    scene.add(mouth_fb);

    function hideFallback() {
      head.visible = false;
      body.visible = false;
      mouth_fb.visible = false;
    }

    let selaModel = null;
    let headBone  = null;
    let jawBone   = null;
    let eyeBones  = [];
    let faceMeshes = [];
    let talking   = false;
    let talkPhase = 0;
    let blinkPhase= 0;
    const clock   = new THREE.Clock();

    function setTalking(flag) {
      talking = flag;
      if (flag) led.classList.remove("off");
      else led.classList.add("off");
    }

    function detectMorphTargets(root) {
      faceMeshes = [];
      headBone   = null;
      jawBone    = null;
      eyeBones   = [];

      const mouthNames = ["mouthOpen","jawOpen","mouthSmile","viseme_aa","viseme_E","viseme_O","viseme_U"];
      const blinkLeftNames  = ["eyeBlinkLeft","eyesClosedLeft","eyeSquintLeft"];
      const blinkRightNames = ["eyeBlinkRight","eyesClosedRight","eyeSquintRight"];

      root.traverse((obj) => {
        const name = (obj.name || "").toLowerCase();

        if (obj.isBone) {
          if (!headBone && name.includes("head")) headBone = obj;
          if (!jawBone  && name.includes("jaw"))  jawBone  = obj;
          if (name.includes("eye") && !name.includes("brow")) {
            eyeBones.push(obj);
          }
        }

        if (obj.isMesh && obj.morphTargetDictionary) {
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => { if (m) m.morphTargets = true; });
          } else if (obj.material) {
            obj.material.morphTargets = true;
          }
          if (obj.updateMorphTargets) obj.updateMorphTargets();

          const dict  = obj.morphTargetDictionary;
          const mouth = [];
          const blinkL = [];
          const blinkR = [];

          mouthNames.forEach((n) => { if (dict[n] !== undefined) mouth.push(dict[n]); });
          blinkLeftNames.forEach((n)  => { if (dict[n] !== undefined) blinkL.push(dict[n]); });
          blinkRightNames.forEach((n) => { if (dict[n] !== undefined) blinkR.push(dict[n]); });

          if (mouth.length || blinkL.length || blinkR.length) {
            faceMeshes.push({ mesh: obj, mouthIndices: mouth, blinkL, blinkR });
          }
        }
      });

      console.log("[SELA] faceMeshes:", faceMeshes.length);
    }

    function loadSelaAvatar() {
      statusEl.textContent = "Status: mengunduh avatar 3D SELA...";
      const loader = new GLTFLoader();
      loader.load(
        AVATAR_URL,
        (gltf) => {
          try {
            selaModel = gltf.scene;

            const box0  = new THREE.Box3().setFromObject(selaModel);
            const size0 = box0.getSize(new THREE.Vector3());
            const h0    = size0.y || 1;
            const s     = 2.2 / h0;
            selaModel.scale.setScalar(s);

            const box1   = new THREE.Box3().setFromObject(selaModel);
            const center1= box1.getCenter(new THREE.Vector3());
            selaModel.position.sub(center1);

            const box    = new THREE.Box3().setFromObject(selaModel);
            const size   = box.getSize(new THREE.Vector3());
            const headTopY = box.min.y + size.y * 0.98;
            const chestY   = box.min.y + size.y * 0.80;
            const faceCenterY = (headTopY + chestY) / 2;
            const visHeight   = headTopY - chestY;
            const fovRad      = camera.fov * Math.PI / 180;
            const dist        = (visHeight / 2) / Math.tan(fovRad / 2);

            hideFallback();
            scene.add(selaModel);

            camera.position.set(0, faceCenterY + 0.05, dist * 1.08);
            camera.lookAt(0, faceCenterY, 0);

            detectMorphTargets(selaModel);
            statusEl.textContent = "Status: SELA siap membaca data dan menjawab pertanyaan.";
          } catch (e) {
            console.error("[SELA] Error avatar:", e);
            statusEl.textContent = "Status: avatar 3D sederhana (fallback).";
          }
        },
        undefined,
        (err) => {
          console.error("[SELA] Gagal memuat avatar:", err);
          statusEl.textContent = "Status: gagal memuat avatar 3D SELA, pakai avatar sederhana.";
        }
      );
    }

    loadSelaAvatar();

    function animate() {
      requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      if (faceMeshes.length > 0) {
        faceMeshes.forEach((face) => {
          const infl = face.mesh.morphTargetInfluences;
          if (!infl) return;

          for (let i = 0; i < infl.length; i++) infl[i] *= 0.8;

          if (talking && face.mouthIndices.length > 0) {
            talkPhase += 0.25;
            const v = 0.3 + 0.7 * Math.abs(Math.sin(talkPhase));
            face.mouthIndices.slice(0, 2).forEach((idx) => { infl[idx] = v; });
          }

          if (face.blinkL.length || face.blinkR.length) {
            blinkPhase += 0.03;
            const tb = blinkPhase % 2.4;
            let b = 0;
            if (tb < 0.12)       b = tb / 0.12;
            else if (tb < 0.24)  b = 1 - (tb - 0.12)/0.12;
            else                 b = 0;
            face.blinkL.forEach((idx)=>{ infl[idx] = Math.max(infl[idx] || 0, b); });
            face.blinkR.forEach((idx)=>{ infl[idx] = Math.max(infl[idx] || 0, b); });
          }
        });
      } else {
        if (talking) {
          talkPhase += 0.25;
          const scaleY = 0.8 + Math.abs(Math.sin(talkPhase)) * 0.5;
          mouth_fb.scale.y = scaleY;
          mouth_fb.position.y = 0.48 - (scaleY - 0.8) * 0.06;
        } else {
          mouth_fb.scale.y = 1.0;
        }
      }

      if (headBone) {
        headBone.rotation.z = 0.04 * Math.sin(t * 0.4);
        headBone.rotation.y = 0.03 * Math.sin(t * 0.6);
      } else {
        if (!talking) {
          head.rotation.y += 0.002;
          body.rotation.y += 0.002;
        }
      }

      if (jawBone) {
        if (talking) {
          const jawOpen = 0.45 * Math.abs(Math.sin(talkPhase));
          jawBone.rotation.x = -jawOpen;
        } else {
          jawBone.rotation.x *= 0.85;
        }
      }

      renderer.render(scene, camera);
    }
    animate();

    // ========= WEBLLM + MIC (LAZY LOAD) =========
    let engine   = null;
    let messages = [
      {
        role: "system",
        content:
          "Kamu adalah SELA, asisten virtual perempuan yang ramah. " +
          "Fokus membantu soal SLA pembayaran, vendor, cabang, transaksi, dan pertanyaan keuangan ringan. " +
          "Jika pengguna menanyakan angka SLA, periode, vendor, jenis transaksi, atau jumlah transaksi, " +
          "gunakan data yang sudah diberikan (jangan mengarang angka). " +
          "Jawab singkat (1–3 kalimat), jelas, dan boleh tambahkan sedikit analisis tren."
      }
    ];
    const MAX_HISTORY = 4;

    let recognizer   = null;
    let recognizing  = false;
    let micReady     = false;
    let initializing = false;

    async function ensureLLMAndMic() {
      if (engine || initializing) return;
      initializing = true;

      try {
        statusEl.textContent = "Status: mengunduh & memuat model AI di browser...";
        const webllm = await import("https://esm.run/@mlc-ai/web-llm");

        engine = new webllm.MLCEngine();
        engine.setInitProgressCallback(function(rep) {
          if (rep && rep.text) statusEl.textContent = "Status: " + rep.text;
        });

        const modelList = webllm.prebuiltAppConfig && webllm.prebuiltAppConfig.model_list;
        const modelId = (modelList && modelList[0] && modelList[0].model_id) ||
                        "TinyLlama-1.1B-Chat-v0.4-q4f32_1-MLC-1k";

        await engine.reload(modelId, { temperature: 0.5, top_p: 0.9 });

        const SpeechRecognition =
          window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
          statusEl.textContent =
            "Browser ini tidak mendukung pengenalan suara. Coba Chrome (desktop/Android).";
          return;
        }

        recognizer = new SpeechRecognition();
        recognizer.lang = "id-ID";
        recognizer.interimResults = false;
        recognizer.maxAlternatives = 1;

        recognizer.onstart = function() {
          recognizing = true;
          talkBtn.classList.add("sela-listening");
          statusEl.textContent = "Status: mendengarkan... silakan bicara.";
        };
        recognizer.onerror = function(e) {
          recognizing = false;
          talkBtn.classList.remove("sela-listening");
          statusEl.textContent = "Error mic: " + e.error;
        };
        recognizer.onend = function() {
          recognizing = false;
          talkBtn.classList.remove("sela-listening");
          if (!window._sela_processing) {
            statusEl.textContent =
              "Status: selesai mendengar, siap menunggu pertanyaan berikutnya.";
          }
        };
        recognizer.onresult = async function(event) {
          const text = event.results[0][0].transcript;
          statusEl.textContent = 'Kamu: "' + text + '". SELA sedang berpikir...';
          window._sela_processing = true;

          const reply = await answerUser(text);
          statusEl.textContent = "SELA: " + reply;

          if ("speechSynthesis" in window) {
            const utt = new SpeechSynthesisUtterance(reply);
            utt.lang   = "id-ID";
            const voice = pickIndonesianVoice();
            if (voice) utt.voice = voice;
            utt.rate   = 0.96;
            utt.pitch  = 1.02;
            utt.volume = 1.0;

            utt.onstart = function() { setTalking(true); };
            utt.onend   = function() {
              setTalking(false);
              window._sela_processing = false;
              statusEl.textContent = "Status: SELA siap bicara lagi.";
            };
            window.speechSynthesis.speak(utt);
          } else {
            window._sela_processing = false;
          }
        };

        micReady = true;
        statusEl.textContent = "Status: SELA siap. Klik 🎤 lalu bicara.";
      } catch (e) {
        console.error("[SELA] Gagal memuat WebLLM:", e);
        statusEl.textContent =
          "Gagal memuat model AI di browser. Koneksi lambat atau perangkat tidak mendukung.";
      } finally {
        initializing = false;
      }
    }

    async function askSELA(userText) {
      const dataAnswer = answerWithData(userText);
      if (dataAnswer) return dataAnswer;

      if (!engine) {
        return "Maaf, otak SELA belum sepenuhnya siap. Coba klik tombol lagi setelah beberapa detik.";
      }

      messages.push({ role: "user", content: userText });
      if (messages.length > 1 + MAX_HISTORY) {
        const sys = messages[0];
        messages = [sys].concat(messages.slice(-MAX_HISTORY));
      }

      let cur = "";
      const completion = await engine.chat.completions.create({
        stream: true,
        messages: messages,
        max_tokens: 80,
        temperature: 0.5,
        top_p: 0.9
      });
      for await (const chunk of completion) {
        const delta = chunk.choices[0].delta.content;
        if (delta) cur += delta;
      }
      messages.push({ role: "assistant", content: cur });
      return cur;
    }

    async function answerUser(text) {
      try {
        const ans = await askSELA(text);
        return ans;
      } catch (e) {
        console.error("[SELA] Error saat menjawab:", e);
        return "Maaf, SELA mengalami kendala saat memproses jawaban.";
      }
    }

    function pickGreeting() {
      if (!("speechSynthesis" in window)) return;
      const text = "Halooo, saya Sela. Saya akan bantu bacakan data SLA dan transaksi dari dashboard ini ya.";
      const utt  = new SpeechSynthesisUtterance(text);
      utt.lang   = "id-ID";
      const v = pickIndonesianVoice();
      if (v) utt.voice = v;
      utt.rate = 0.96;
      utt.pitch= 1.04;
      window.speechSynthesis.speak(utt);
    }

    pickGreeting();
    statusEl.textContent = "Status: SELA siap secara visual. Klik 🎤 untuk mulai mengaktifkan otak AI.";

    talkBtn.addEventListener("click", async function() {
      if (!engine || !micReady || !recognizer) {
        await ensureLLMAndMic();
      }
      if (!recognizer) return;

      if (!recognizing) recognizer.start();
      else recognizer.stop();
    });
  </script>
</body>
</html>
    """

    components.html(
        html.replace("___SELA_DATA___", data_json),
        height=500,
        scrolling=False,
    )


# PANGGIL SELA HANYA JIKA USER MINTA (lebih ringan untuk halaman awal)
if st.session_state.get("show_sela", False):
    render_sela_widget(df_filtered, periode_col)




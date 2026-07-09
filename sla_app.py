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
    st.caption("SELA Natural Voice aktif saat dibuka; tanpa model AI browser berat agar dashboard tetap ringan.")


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
                    selected_permohonan = st.multiselect(
                        "Filter Nomor Permohonan",
                        options=["ALL"] + nomor_options,
                        default=["ALL"],
                        help="Bisa pilih 1 atau lebih Nomor Permohonan. Pilih ALL untuk menampilkan seluruh nomor.",
                        key="trx_filter_nomor_permohonan_main",
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
                    max_top_n = max(0, min(30, len(trx_ai_base)))

                    # Streamlit slider akan error jika min_value == max_value.
                    # Karena itu, saat hasil filter hanya 0 atau 1 baris, tampilkan metric saja.
                    if max_top_n <= 0:
                        top_n = 0
                        st.info("Tidak ada data untuk Top N.")
                    elif max_top_n == 1:
                        top_n = 1
                        st.metric("Top N ditampilkan", "1")
                        st.caption("Hanya ada 1 jenis transaksi pada filter aktif.")
                    else:
                        prev_top_n = st.session_state.get("trx_top_n_wow", min(10, max_top_n))
                        safe_default_top_n = min(max(int(prev_top_n), 1), max_top_n)

                        top_n = st.slider(
                            "Top N ditampilkan",
                            min_value=1,
                            max_value=max_top_n,
                            value=safe_default_top_n,
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
#  SELA v5 — Natural Female Voice Data Copilot
#  Revisi:
#  - Menghapus total model AI browser berat agar tidak hang.
#  - Tidak mengirim seluruh dataframe ke browser; hanya ringkasan kecil.
#  - Avatar 3D-style ringan berbasis CSS, dengan blink, glow, listening pulse,
#    mouth movement saat berbicara, dan suara wanita via browser SpeechSynthesis.
#  - Mic memakai Web Speech API. Jika browser tidak support, tetap bisa ketik.
# ==========================================================
import streamlit.components.v1 as components
import json
import re
import math
import pandas as pd
import numpy as np


def _sela_seconds_to_text(seconds):
    """Format detik ke teks Indonesia yang ringkas."""
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
        if not parts:
            parts.append(f"{secs} detik")
        return " ".join(parts)
    except Exception:
        return "-"


def _sela_fmt_int(x):
    try:
        return f"{int(x):,}".replace(",", ".")
    except Exception:
        return "-"


def _sela_fmt_days(x):
    try:
        if x is None or pd.isna(x):
            return "-"
        return f"{float(x):.2f} hari"
    except Exception:
        return "-"


def _sela_find_col(df, patterns):
    """Cari nama kolom secara fleksibel berdasarkan daftar regex/potongan kata."""
    if df is None or not isinstance(df, pd.DataFrame):
        return None

    for col in df.columns:
        norm = re.sub(r"[^A-Z0-9]+", " ", str(col).upper()).strip()
        if all(re.search(pat, norm) for pat in patterns):
            return col
    return None


def _sela_natural_key(x):
    return [int(t) if str(t).isdigit() else str(t).lower() for t in re.split(r"(\d+)", str(x))]


def _sela_safe_top_records(df, name_col, value_col, count_col=None, n=5, ascending=False):
    if df is None or df.empty or name_col not in df.columns or value_col not in df.columns:
        return []

    d = df.dropna(subset=[name_col, value_col]).copy()
    if d.empty:
        return []

    d = d.sort_values(value_col, ascending=ascending).head(n)

    out = []
    for _, row in d.iterrows():
        item = {
            "name": str(row[name_col]),
            "value": float(row[value_col]) if pd.notna(row[value_col]) else None,
            "value_text": _sela_fmt_days(row[value_col]),
        }
        if count_col and count_col in d.columns:
            try:
                item["count"] = int(row[count_col])
                item["count_text"] = _sela_fmt_int(row[count_col])
            except Exception:
                item["count"] = None
                item["count_text"] = "-"
        out.append(item)

    return out


def build_sela_context(df_active, periode_col, available_sla_cols=None, selected_periode=None):
    """Bangun ringkasan kecil untuk SELA. Jangan kirim dataframe mentah ke browser."""
    ctx = {
        "ok": False,
        "period_start": "-",
        "period_end": "-",
        "period_count": 0,
        "total_rows": 0,
        "total_rows_text": "0",
        "avg_total_days": None,
        "avg_total_text": "-",
        "avg_keuangan_days": None,
        "avg_keuangan_text": "-",
        "bottleneck_process": "-",
        "bottleneck_days": None,
        "bottleneck_text": "-",
        "growth_latest_pct": None,
        "growth_latest_text": "-",
        "avg_growth_pct": None,
        "avg_growth_text": "-",
        "last_period": "-",
        "last_period_count": None,
        "previous_period": "-",
        "previous_period_count": None,
        "process_means": [],
        "volume_by_period": [],
        "top_slowest_transactions": [],
        "top_fastest_transactions": [],
        "top_vendors": [],
        "top_permohonan": [],
        "data_scope": "Data aktif mengikuti filter periode dashboard.",
    }

    if df_active is None or not isinstance(df_active, pd.DataFrame) or df_active.empty:
        return ctx

    if not periode_col or periode_col not in df_active.columns:
        return ctx

    df = df_active.copy()
    ctx["ok"] = True
    ctx["total_rows"] = int(len(df))
    ctx["total_rows_text"] = _sela_fmt_int(len(df))

    # Periode aktif
    try:
        if selected_periode:
            periods = [str(x) for x in selected_periode if str(x).strip()]
        else:
            periods = sorted(df[periode_col].dropna().astype(str).unique().tolist(), key=_sela_natural_key)

        if periods:
            ctx["period_start"] = str(periods[0])
            ctx["period_end"] = str(periods[-1])
            ctx["period_count"] = len(periods)
    except Exception:
        periods = sorted(df[periode_col].dropna().astype(str).unique().tolist(), key=_sela_natural_key)

    # SLA columns
    available_sla_cols = available_sla_cols or []
    sla_candidates = [c for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"] if c in df.columns]
    if not sla_candidates and available_sla_cols:
        sla_candidates = [c for c in available_sla_cols if c in df.columns]

    def mean_days(col):
        if col not in df.columns:
            return None
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            return None
        return float(s.mean() / 86400)

    total_days = mean_days("TOTAL WAKTU")
    if total_days is not None:
        ctx["avg_total_days"] = total_days
        ctx["avg_total_text"] = _sela_fmt_days(total_days)

    keu_days = mean_days("KEUANGAN")
    if keu_days is not None:
        ctx["avg_keuangan_days"] = keu_days
        ctx["avg_keuangan_text"] = _sela_fmt_days(keu_days)

    process_rows = []
    for col in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"]:
        d = mean_days(col)
        if d is not None:
            process_rows.append({"process": col, "days": d, "days_text": _sela_fmt_days(d)})

    process_rows = sorted(process_rows, key=lambda x: x["days"], reverse=True)
    ctx["process_means"] = process_rows

    if process_rows:
        top = process_rows[0]
        ctx["bottleneck_process"] = top["process"]
        ctx["bottleneck_days"] = top["days"]
        ctx["bottleneck_text"] = top["days_text"]

    # Volume & growth by period
    try:
        vol = (
            df.groupby(df[periode_col].astype(str))
            .size()
            .reset_index(name="Jumlah")
        )
        order = periods if periods else sorted(vol[periode_col].astype(str).unique().tolist(), key=_sela_natural_key)
        vol["_ORDER"] = pd.Categorical(vol[periode_col].astype(str), categories=order, ordered=True)
        vol = vol.sort_values("_ORDER").drop(columns=["_ORDER"])

        vol["Growth"] = vol["Jumlah"].pct_change() * 100

        ctx["volume_by_period"] = [
            {
                "period": str(r[periode_col]),
                "count": int(r["Jumlah"]),
                "count_text": _sela_fmt_int(r["Jumlah"]),
                "growth": None if pd.isna(r["Growth"]) else float(r["Growth"]),
                "growth_text": "-" if pd.isna(r["Growth"]) else f"{float(r['Growth']):+.2f}%",
            }
            for _, r in vol.iterrows()
        ]

        if len(vol) >= 1:
            last = vol.iloc[-1]
            ctx["last_period"] = str(last[periode_col])
            ctx["last_period_count"] = int(last["Jumlah"])

        if len(vol) >= 2:
            prev = vol.iloc[-2]
            last = vol.iloc[-1]
            ctx["previous_period"] = str(prev[periode_col])
            ctx["previous_period_count"] = int(prev["Jumlah"])
            if pd.notna(last["Growth"]):
                ctx["growth_latest_pct"] = float(last["Growth"])
                ctx["growth_latest_text"] = f"{float(last['Growth']):+.2f}%"

        valid_growth = vol["Growth"].dropna()
        if not valid_growth.empty:
            ctx["avg_growth_pct"] = float(valid_growth.mean())
            ctx["avg_growth_text"] = f"{float(valid_growth.mean()):+.2f}%"
    except Exception:
        pass

    # Top jenis transaksi
    if "JENIS TRANSAKSI" in df.columns:
        sla_col_for_trx = "TOTAL WAKTU" if "TOTAL WAKTU" in df.columns else ("KEUANGAN" if "KEUANGAN" in df.columns else None)
        if sla_col_for_trx:
            trx = (
                df.groupby("JENIS TRANSAKSI", dropna=False)
                .agg(
                    Jumlah=("JENIS TRANSAKSI", "size"),
                    SLA_Detik=(sla_col_for_trx, lambda s: pd.to_numeric(s, errors="coerce").mean()),
                )
                .reset_index()
            )
            trx["SLA_Hari"] = trx["SLA_Detik"] / 86400

            ctx["top_slowest_transactions"] = _sela_safe_top_records(
                trx, "JENIS TRANSAKSI", "SLA_Hari", "Jumlah", n=5, ascending=False
            )
            ctx["top_fastest_transactions"] = _sela_safe_top_records(
                trx, "JENIS TRANSAKSI", "SLA_Hari", "Jumlah", n=5, ascending=True
            )

    # Top vendor/cabang
    if "NAMA VENDOR" in df.columns:
        vendor_sla_col = "TOTAL WAKTU" if "TOTAL WAKTU" in df.columns else ("VENDOR" if "VENDOR" in df.columns else None)
        if vendor_sla_col:
            vd = (
                df.groupby("NAMA VENDOR", dropna=False)
                .agg(
                    Jumlah=("NAMA VENDOR", "size"),
                    SLA_Detik=(vendor_sla_col, lambda s: pd.to_numeric(s, errors="coerce").mean()),
                )
                .reset_index()
            )
            vd["SLA_Hari"] = vd["SLA_Detik"] / 86400
            ctx["top_vendors"] = _sela_safe_top_records(
                vd, "NAMA VENDOR", "SLA_Hari", "Jumlah", n=5, ascending=False
            )

    # Top nomor permohonan
    nomor_col = (
        _sela_find_col(df, [r"(NO|NOMOR|NUMBER)", r"(PERMOHONAN|PERMINTAAN|REQUEST)"])
        or _sela_find_col(df, [r"(NO|NOMOR)", r"(DOKUMEN)"])
    )

    if nomor_col:
        perm_sla_col = "TOTAL WAKTU" if "TOTAL WAKTU" in df.columns else ("KEUANGAN" if "KEUANGAN" in df.columns else None)
        if perm_sla_col:
            pm = (
                df.groupby(nomor_col, dropna=False)
                .agg(
                    Jumlah=(nomor_col, "size"),
                    SLA_Detik=(perm_sla_col, lambda s: pd.to_numeric(s, errors="coerce").mean()),
                )
                .reset_index()
            )
            pm["SLA_Hari"] = pm["SLA_Detik"] / 86400
            top_pm = _sela_safe_top_records(pm, nomor_col, "SLA_Hari", "Jumlah", n=5, ascending=False)
            ctx["top_permohonan"] = top_pm
            ctx["nomor_permohonan_col"] = str(nomor_col)

    return ctx


def render_sela_natural_voice(df_filtered, periode_col, available_sla_cols=None, selected_periode=None):
    ctx = build_sela_context(
        df_active=df_filtered,
        periode_col=periode_col,
        available_sla_cols=available_sla_cols,
        selected_periode=selected_periode,
    )

    ctx_json = json.dumps(ctx, ensure_ascii=False).replace("</", "<\\/")

    html_template = r"""
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<style>
:root {
  --bg0:#07111f;
  --bg1:#0b1f3a;
  --cyan:#00eaff;
  --green:#38ef7d;
  --purple:#9b5cff;
  --pink:#ff6aa2;
  --text:#eef8ff;
  --muted:#9fb6c9;
}
* { box-sizing: border-box; }
body {
  margin:0;
  background:transparent;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
.sela-shell {
  width:100%;
  max-width:760px;
  margin: 0 auto;
  border-radius:28px;
  overflow:hidden;
  color:var(--text);
  background:
    radial-gradient(circle at 15% 5%, rgba(0,234,255,.28), transparent 28%),
    radial-gradient(circle at 90% 20%, rgba(255,106,162,.20), transparent 28%),
    linear-gradient(145deg, rgba(7,17,31,.98), rgba(9,35,69,.96) 55%, rgba(3,79,98,.94));
  border:1px solid rgba(255,255,255,.16);
  box-shadow:0 24px 65px rgba(0,0,0,.45);
}
.sela-header {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:14px;
  padding:18px 20px;
  border-bottom:1px solid rgba(255,255,255,.12);
}
.brand {
  display:flex;
  gap:13px;
  align-items:center;
}
.brand-dot {
  width:44px;height:44px;border-radius:50%;
  background:linear-gradient(135deg,var(--cyan),var(--green));
  display:grid;place-items:center;
  color:#062032;font-weight:950;font-size:20px;
  box-shadow:0 0 25px rgba(0,234,255,.32);
}
.title { font-size:20px; font-weight:950; letter-spacing:.2px; }
.subtitle { font-size:12px; color:var(--muted); margin-top:3px; line-height:1.35; }
.badges { display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }
.badge {
  border:1px solid rgba(255,255,255,.16);
  background:rgba(255,255,255,.08);
  color:#dffcff;
  padding:7px 10px;
  border-radius:999px;
  font-size:11px;
  font-weight:800;
}
.sela-main {
  display:grid;
  grid-template-columns: 290px minmax(0,1fr);
  gap:0;
  min-height:540px;
}
.avatar-zone {
  position:relative;
  min-height:540px;
  background:
    radial-gradient(circle at 50% 18%, rgba(255,255,255,.18), transparent 22%),
    linear-gradient(180deg, rgba(255,255,255,.96), rgba(225,246,255,.90));
  overflow:hidden;
  display:flex;
  align-items:center;
  justify-content:center;
  perspective:1000px;
}
.holo-ring {
  position:absolute;
  width:230px;height:230px;
  border-radius:50%;
  border:2px solid rgba(0,234,255,.34);
  box-shadow:0 0 35px rgba(0,234,255,.32), inset 0 0 25px rgba(155,92,255,.18);
  transform: rotateX(72deg) translateY(130px);
  bottom:30px;
  animation:ringPulse 3s infinite ease-in-out;
}
.avatar {
  width:205px;height:305px;
  position:relative;
  transform-style:preserve-3d;
  animation:floaty 4.4s ease-in-out infinite;
}
.hair-back {
  position:absolute;left:45px;top:28px;width:115px;height:170px;
  background:linear-gradient(135deg,#111827,#020617);
  border-radius:58px 58px 52px 52px;
  box-shadow: inset -18px 0 22px rgba(255,255,255,.05);
}
.neck {
  position:absolute;left:88px;top:162px;width:38px;height:45px;
  background:linear-gradient(180deg,#d49a7d,#b97863);
  border-radius:14px;
  z-index:2;
}
.face {
  position:absolute;left:48px;top:42px;width:112px;height:135px;
  background:linear-gradient(145deg,#e7b394,#c8846e 78%);
  border-radius:49% 49% 46% 46%;
  box-shadow: inset -10px -8px 18px rgba(73,33,24,.16), inset 8px 7px 14px rgba(255,255,255,.18), 0 14px 22px rgba(0,0,0,.22);
  z-index:3;
}
.bangs {
  position:absolute;left:47px;top:33px;width:116px;height:52px;
  background:linear-gradient(135deg,#0b0f1a,#020617);
  border-radius:60px 60px 25px 20px;
  z-index:5;
  clip-path:polygon(0 0,100% 0,100% 67%,78% 52%,63% 85%,43% 54%,25% 82%,10% 52%,0 70%);
}
.hair-left,.hair-right {
  position:absolute;top:80px;width:34px;height:145px;background:#050814;z-index:4;
  border-radius:24px;
}
.hair-left { left:31px; transform:rotate(7deg); }
.hair-right{ right:31px; transform:rotate(-7deg); }
.eye {
  position:absolute;top:88px;width:29px;height:18px;border-radius:50%;
  background:#f8fafc;z-index:6;
  box-shadow: inset 0 0 5px rgba(0,0,0,.25);
}
.eye.left { left:70px; }
.eye.right{ left:112px; }
.pupil {
  position:absolute;left:9px;top:4px;width:10px;height:10px;border-radius:50%;
  background:#243045;
}
.eye::after {
  content:"";position:absolute;inset:0;background:#c8846e;border-radius:50%;
  transform:scaleY(0);transform-origin:center;
  animation:blink 4.8s infinite;
}
.glasses {
  position:absolute;left:63px;top:83px;width:90px;height:30px;z-index:8;
}
.glass {
  position:absolute;top:0;width:37px;height:26px;border:4px solid #0f172a;border-radius:10px;
  background:rgba(255,255,255,.03);
}
.glass.l{left:0}.glass.r{right:0}
.bridge { position:absolute;left:38px;top:12px;width:17px;height:4px;background:#0f172a;border-radius:3px; }
.nose {
  position:absolute;left:100px;top:106px;width:12px;height:25px;border-radius:50%;
  border-right:3px solid rgba(88,43,32,.28);z-index:7;
}
.mouth {
  position:absolute;left:86px;top:140px;width:38px;height:10px;
  background:#7d3247;border-radius:4px 4px 18px 18px;z-index:8;
  transform-origin:center top;
}
.speaking .mouth { animation:mouthTalk .18s infinite alternate; }
.listening .holo-ring { border-color:rgba(56,239,125,.62); box-shadow:0 0 50px rgba(56,239,125,.52); }
.thinking .avatar { animation:floaty 1.4s ease-in-out infinite; }
.body {
  position:absolute;left:34px;top:190px;width:142px;height:118px;
  background:linear-gradient(135deg,#273348,#111827);
  border-radius:38px 38px 16px 16px;
  z-index:1;box-shadow:0 14px 26px rgba(0,0,0,.24);
}
.badge-s {
  position:absolute;left:82px;top:217px;width:44px;height:44px;border-radius:50%;
  background:linear-gradient(135deg,var(--cyan),var(--purple));display:grid;place-items:center;
  color:white;font-weight:950;z-index:2;box-shadow:0 0 18px rgba(0,234,255,.35);
}
.wave {
  position:absolute;bottom:18px;display:flex;gap:5px;align-items:flex-end;
}
.wave span {
  width:6px;height:10px;border-radius:999px;background:linear-gradient(180deg,var(--cyan),var(--green));
  opacity:.45;
}
.speaking .wave span, .listening .wave span { animation:wave 0.55s infinite ease-in-out; opacity:1; }
.wave span:nth-child(2){animation-delay:.08s}.wave span:nth-child(3){animation-delay:.16s}.wave span:nth-child(4){animation-delay:.24s}.wave span:nth-child(5){animation-delay:.32s}

.chat-zone {
  padding:18px;
  display:flex;
  flex-direction:column;
  gap:12px;
  min-width:0;
}
.status {
  border:1px solid rgba(255,255,255,.14);
  background:rgba(255,255,255,.08);
  border-radius:18px;
  padding:12px 14px;
  font-size:12.5px;
  line-height:1.42;
  color:#dbeafe;
}
.kpi-mini {
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:9px;
}
.kpi {
  border:1px solid rgba(255,255,255,.12);
  background:rgba(255,255,255,.08);
  border-radius:16px;
  padding:11px;
}
.kpi-label { font-size:10px; color:#a9c3d9; text-transform:uppercase; letter-spacing:.5px; }
.kpi-value { font-size:18px; font-weight:950; margin-top:3px; }
.chat-log {
  height:184px;
  overflow-y:auto;
  padding:10px;
  border-radius:18px;
  border:1px solid rgba(255,255,255,.12);
  background:rgba(3,10,24,.38);
}
.msg {
  max-width:92%;
  padding:10px 12px;
  border-radius:16px;
  margin-bottom:9px;
  font-size:13px;
  line-height:1.42;
}
.msg.sela {
  background:linear-gradient(135deg,rgba(0,234,255,.16),rgba(56,239,125,.10));
  border:1px solid rgba(0,234,255,.22);
  margin-right:auto;
}
.msg.user {
  background:rgba(255,255,255,.13);
  border:1px solid rgba(255,255,255,.12);
  margin-left:auto;
}
.controls {
  display:grid;
  grid-template-columns:1fr auto;
  gap:8px;
}
.input {
  width:100%;
  border:1px solid rgba(255,255,255,.15);
  background:rgba(255,255,255,.09);
  color:white;
  outline:none;
  border-radius:999px;
  padding:12px 14px;
  font-size:13px;
}
.btn-row { display:flex; gap:8px; }
.btn {
  border:0;cursor:pointer;border-radius:999px;
  padding:11px 13px;font-weight:900;
  color:#062032;background:linear-gradient(135deg,var(--cyan),var(--green));
  box-shadow:0 10px 24px rgba(0,234,255,.22);
}
.btn.secondary {
  background:rgba(255,255,255,.12);
  color:#e5f6ff;
  border:1px solid rgba(255,255,255,.14);
  box-shadow:none;
}
.chips {
  display:flex;flex-wrap:wrap;gap:8px;
}
.chip {
  border:1px solid rgba(255,255,255,.14);
  background:rgba(255,255,255,.08);
  color:#e5f6ff;
  padding:8px 10px;
  border-radius:999px;
  font-size:11px;
  cursor:pointer;
}
.voice-select {
  width:100%;
  background:rgba(255,255,255,.09);
  color:#e5f6ff;
  border:1px solid rgba(255,255,255,.14);
  border-radius:12px;
  padding:8px 10px;
  font-size:12px;
}
.voice-select option { color:#111827; }
.foot {
  color:#9fb6c9;
  font-size:10.8px;
  line-height:1.35;
}
@keyframes floaty {
  0%,100% { transform: translateY(0) rotateY(-5deg); }
  50% { transform: translateY(-10px) rotateY(5deg); }
}
@keyframes blink {
  0%, 92%, 100% { transform:scaleY(0); }
  95% { transform:scaleY(1); }
}
@keyframes mouthTalk {
  from { transform:scaleY(.65); }
  to   { transform:scaleY(1.85); }
}
@keyframes wave {
  0%,100%{height:10px}
  50%{height:34px}
}
@keyframes ringPulse {
  0%,100%{transform:rotateX(72deg) translateY(130px) scale(.95);opacity:.65}
  50%{transform:rotateX(72deg) translateY(130px) scale(1.08);opacity:1}
}
@media(max-width:760px){
  .sela-main{grid-template-columns:1fr}
  .avatar-zone{min-height:360px}
  .kpi-mini{grid-template-columns:1fr}
}
</style>
</head>
<body>
<div id="selaShell" class="sela-shell">
  <div class="sela-header">
    <div class="brand">
      <div class="brand-dot">S</div>
      <div>
        <div class="title">SELA v5 • Natural Female Voice</div>
        <div class="subtitle">Asisten suara untuk membaca data SLA aktif, menjawab pertanyaan, dan memberi insight seperti analis pribadi.</div>
      </div>
    </div>
    <div class="badges">
      <div class="badge">DATA CONNECTED</div>
      <div class="badge">LIGHT VOICE</div>
      <div class="badge">VOICE READY</div>
    </div>
  </div>

  <div class="sela-main">
    <div id="avatarZone" class="avatar-zone">
      <div class="holo-ring"></div>
      <div class="avatar">
        <div class="hair-back"></div>
        <div class="neck"></div>
        <div class="body"></div>
        <div class="badge-s">S</div>
        <div class="face"></div>
        <div class="bangs"></div>
        <div class="hair-left"></div>
        <div class="hair-right"></div>
        <div class="eye left"><div class="pupil"></div></div>
        <div class="eye right"><div class="pupil"></div></div>
        <div class="glasses"><div class="glass l"></div><div class="bridge"></div><div class="glass r"></div></div>
        <div class="nose"></div>
        <div class="mouth"></div>
      </div>
      <div class="wave"><span></span><span></span><span></span><span></span><span></span></div>
    </div>

    <div class="chat-zone">
      <div id="status" class="status">SELA sedang menyiapkan mode suara...</div>

      <div class="kpi-mini">
        <div class="kpi">
          <div class="kpi-label">Transaksi</div>
          <div id="kpiTransaksi" class="kpi-value">-</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Avg SLA</div>
          <div id="kpiSla" class="kpi-value">-</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Growth</div>
          <div id="kpiGrowth" class="kpi-value">-</div>
        </div>
      </div>

      <div id="chatLog" class="chat-log"></div>

      <select id="voiceSelect" class="voice-select">
        <option>Memuat daftar suara...</option>
      </select>

      <div class="controls">
        <input id="userInput" class="input" placeholder="Tulis pertanyaan atau klik mic untuk bicara..." />
        <div class="btn-row">
          <button id="sendBtn" class="btn">Kirim</button>
          <button id="micBtn" class="btn secondary">🎙️</button>
          <button id="testBtn" class="btn secondary">🔊</button>
        </div>
      </div>

      <div class="chips">
        <button class="chip" data-q="Buatkan ringkasan direksi">Ringkasan Direksi</button>
        <button class="chip" data-q="Jenis transaksi apa yang paling lambat?">Top SLA</button>
        <button class="chip" data-q="Bagaimana growth transaksi?">Growth</button>
        <button class="chip" data-q="Bottleneck utama ada di mana?">Bottleneck</button>
        <button class="chip" data-q="Vendor mana yang paling lambat?">Vendor Lambat</button>
        <button class="chip" data-q="Nomor permohonan mana yang perlu dipantau?">Nomor Permohonan</button>
      </div>

      <div class="foot">
        SELA v5 memakai ringkasan data aktif dashboard. Mic dan suara bergantung izin browser/HTTPS. Jika mic tidak aktif, gunakan kolom ketik.
      </div>
    </div>
  </div>
</div>

<script>
const SELA_CONTEXT = __SELA_CONTEXT_JSON__;

const shell = document.getElementById("selaShell");
const avatarZone = document.getElementById("avatarZone");
const statusEl = document.getElementById("status");
const chatLog = document.getElementById("chatLog");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const testBtn = document.getElementById("testBtn");
const voiceSelect = document.getElementById("voiceSelect");
const kpiTransaksi = document.getElementById("kpiTransaksi");
const kpiSla = document.getElementById("kpiSla");
const kpiGrowth = document.getElementById("kpiGrowth");

let voices = [];
let recognition = null;
let recognizing = false;

function escapeHtml(str) {
  return String(str || "").replace(/[&<>"']/g, m => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[m]));
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + (role === "user" ? "user" : "sela");
  div.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setMode(mode, text) {
  avatarZone.classList.remove("speaking","listening","thinking");
  if (mode) avatarZone.classList.add(mode);
  if (text) statusEl.textContent = text;
}

function formatPct(x) {
  if (x === null || x === undefined || isNaN(x)) return "-";
  const sign = Number(x) > 0 ? "+" : "";
  return sign + Number(x).toFixed(2) + "%";
}

function topList(items, prefix) {
  if (!items || !items.length) return "Belum ada data yang cukup untuk bagian ini.";
  return items.map((it, idx) => `${idx+1}. ${it.name}: ${it.value_text}${it.count_text ? ` (${it.count_text} transaksi)` : ""}`).join("\n");
}

function initKpi() {
  kpiTransaksi.textContent = SELA_CONTEXT.total_rows_text || "-";
  kpiSla.textContent = SELA_CONTEXT.avg_total_text || SELA_CONTEXT.avg_keuangan_text || "-";
  kpiGrowth.textContent = SELA_CONTEXT.growth_latest_text || "-";
}

function summarizeForDirector() {
  if (!SELA_CONTEXT.ok) {
    return "Maaf, saya belum menemukan data aktif untuk diringkas. Silakan pastikan file SLA sudah dimuat dan periode sudah dipilih.";
  }

  let s = `Baik, saya buatkan ringkasan singkat untuk Direksi. Pada periode ${SELA_CONTEXT.period_start} sampai ${SELA_CONTEXT.period_end}, terdapat ${SELA_CONTEXT.total_rows_text} transaksi.`;

  if (SELA_CONTEXT.avg_total_text && SELA_CONTEXT.avg_total_text !== "-") {
    s += ` Rata-rata SLA total tercatat ${SELA_CONTEXT.avg_total_text}.`;
  } else if (SELA_CONTEXT.avg_keuangan_text && SELA_CONTEXT.avg_keuangan_text !== "-") {
    s += ` Rata-rata SLA Keuangan tercatat ${SELA_CONTEXT.avg_keuangan_text}.`;
  }

  if (SELA_CONTEXT.bottleneck_process && SELA_CONTEXT.bottleneck_process !== "-") {
    s += ` Bottleneck utama terindikasi pada proses ${SELA_CONTEXT.bottleneck_process} dengan rata-rata ${SELA_CONTEXT.bottleneck_text}.`;
  }

  if (SELA_CONTEXT.growth_latest_text && SELA_CONTEXT.growth_latest_text !== "-") {
    const arah = Number(SELA_CONTEXT.growth_latest_pct) >= 0 ? "meningkat" : "menurun";
    s += ` Jumlah transaksi periode terakhir ${arah} ${SELA_CONTEXT.growth_latest_text} dibanding periode sebelumnya.`;
  }

  if (SELA_CONTEXT.top_slowest_transactions && SELA_CONTEXT.top_slowest_transactions.length) {
    const top = SELA_CONTEXT.top_slowest_transactions[0];
    s += ` Jenis transaksi yang perlu menjadi perhatian utama adalah ${top.name}, dengan SLA rata-rata ${top.value_text}.`;
  }

  s += " Rekomendasi saya: fokuskan monitoring pada transaksi ber-SLA tinggi, proses bottleneck, serta kategori dengan volume besar agar perbaikan berdampak langsung ke SLA keseluruhan.";
  return s;
}

function answerQuestion(q) {
  const query = (q || "").toLowerCase();

  if (!SELA_CONTEXT.ok) {
    return "Maaf, saya belum menemukan data aktif. Pastikan data SLA sudah berhasil dimuat, lalu pilih periode yang ingin dianalisis.";
  }

  if (/(halo|hai|hello|pagi|siang|sore|malam|apa kabar)/.test(query)) {
    return `Halo, saya SELA. Saya siap membantu membaca data SLA periode ${SELA_CONTEXT.period_start} sampai ${SELA_CONTEXT.period_end}. Mau saya buatkan ringkasan Direksi atau cek bottleneck terlebih dahulu?`;
  }

  if (/(siapa kamu|kamu siapa|perkenalkan|fungsi kamu|bisa apa)/.test(query)) {
    return "Saya SELA, asisten suara di SLA Payment Analyzer. Saya bisa membantu menjelaskan jumlah transaksi, growth, SLA tertinggi, bottleneck proses, vendor yang perlu dipantau, nomor permohonan, dan ringkasan untuk Direksi berdasarkan data aktif dashboard.";
  }

  if (/(ringkasan|direksi|executive|resume|summary|kesimpulan)/.test(query)) {
    return summarizeForDirector();
  }

  if (/(jumlah|total).*(transaksi)|transaksi.*(berapa|jumlah|total)/.test(query)) {
    let s = `Pada filter aktif, jumlah transaksi adalah ${SELA_CONTEXT.total_rows_text} transaksi untuk periode ${SELA_CONTEXT.period_start} sampai ${SELA_CONTEXT.period_end}.`;
    if (SELA_CONTEXT.last_period_count !== null && SELA_CONTEXT.last_period_count !== undefined) {
      s += ` Periode terakhir, yaitu ${SELA_CONTEXT.last_period}, berisi ${Number(SELA_CONTEXT.last_period_count).toLocaleString("id-ID")} transaksi.`;
    }
    return s;
  }

  if (/(growth|pertumbuhan|naik|turun|kenaikan|penurunan|dibanding)/.test(query)) {
    if (SELA_CONTEXT.growth_latest_text && SELA_CONTEXT.growth_latest_text !== "-") {
      const arah = Number(SELA_CONTEXT.growth_latest_pct) >= 0 ? "naik" : "turun";
      let s = `Growth transaksi terakhir ${arah} ${SELA_CONTEXT.growth_latest_text}, dari periode ${SELA_CONTEXT.previous_period} ke ${SELA_CONTEXT.last_period}.`;
      if (SELA_CONTEXT.avg_growth_text && SELA_CONTEXT.avg_growth_text !== "-") {
        s += ` Rata-rata growth antar-periode pada filter aktif adalah ${SELA_CONTEXT.avg_growth_text}.`;
      }
      if (Math.abs(Number(SELA_CONTEXT.growth_latest_pct)) >= 20) {
        s += " Perubahan ini cukup signifikan, sehingga sebaiknya dipantau dampaknya terhadap beban verifikasi dan SLA.";
      } else {
        s += " Pergerakannya masih relatif terkendali, namun tetap perlu dimonitor.";
      }
      return s;
    }
    return "Growth belum dapat dihitung karena periode aktif hanya satu atau data periode sebelumnya tidak tersedia.";
  }

  if (/(bottleneck|hambatan|penyebab|proses.*lambat|lambat.*proses|terlambat)/.test(query)) {
    if (SELA_CONTEXT.bottleneck_process && SELA_CONTEXT.bottleneck_process !== "-") {
      let s = `Bottleneck utama berada pada proses ${SELA_CONTEXT.bottleneck_process}, dengan rata-rata SLA ${SELA_CONTEXT.bottleneck_text}.`;
      if (SELA_CONTEXT.process_means && SELA_CONTEXT.process_means.length > 1) {
        s += " Ranking rata-rata SLA proses adalah: " + SELA_CONTEXT.process_means.map(x => `${x.process} ${x.days_text}`).join(", ") + ".";
      }
      s += " Saya sarankan dilakukan pengecekan antrean dokumen, approval, kelengkapan dokumen, dan pola keterlambatan pada proses tersebut.";
      return s;
    }
    return "Saya belum menemukan kolom proses SLA yang cukup untuk menentukan bottleneck.";
  }

  if (/(terlama|paling lambat|sla tertinggi|top sla|lama)/.test(query)) {
    if (SELA_CONTEXT.top_slowest_transactions && SELA_CONTEXT.top_slowest_transactions.length) {
      return "Jenis transaksi dengan SLA paling lama adalah:\n" + topList(SELA_CONTEXT.top_slowest_transactions);
    }
    return "Saya belum menemukan data jenis transaksi dan SLA yang cukup untuk membuat ranking SLA terlama.";
  }

  if (/(tercepat|paling cepat|sla terendah|cepat)/.test(query)) {
    if (SELA_CONTEXT.top_fastest_transactions && SELA_CONTEXT.top_fastest_transactions.length) {
      return "Jenis transaksi dengan SLA tercepat adalah:\n" + topList(SELA_CONTEXT.top_fastest_transactions);
    }
    return "Saya belum menemukan data jenis transaksi dan SLA yang cukup untuk membuat ranking SLA tercepat.";
  }

  if (/(vendor|cabang|pihak|supplier)/.test(query)) {
    if (SELA_CONTEXT.top_vendors && SELA_CONTEXT.top_vendors.length) {
      return "Vendor atau cabang yang perlu dipantau berdasarkan SLA terlama adalah:\n" + topList(SELA_CONTEXT.top_vendors);
    }
    return "Saya belum menemukan kolom NAMA VENDOR atau data SLA vendor yang cukup untuk dianalisis.";
  }

  if (/(nomor|no\.?|permohonan|request|dokumen)/.test(query)) {
    if (SELA_CONTEXT.top_permohonan && SELA_CONTEXT.top_permohonan.length) {
      return "Nomor permohonan yang perlu dipantau berdasarkan SLA terlama adalah:\n" + topList(SELA_CONTEXT.top_permohonan);
    }
    return "Saya belum menemukan kolom Nomor Permohonan atau data SLA per nomor yang cukup. Pastikan nama kolom mengandung Nomor/No dan Permohonan/Request.";
  }

  if (/(rekomendasi|saran|perbaikan|tindak lanjut|action)/.test(query)) {
    let s = "Rekomendasi utama saya: ";
    if (SELA_CONTEXT.bottleneck_process && SELA_CONTEXT.bottleneck_process !== "-") {
      s += `pertama, fokus pada proses ${SELA_CONTEXT.bottleneck_process} karena menjadi bottleneck terbesar. `;
    }
    if (SELA_CONTEXT.top_slowest_transactions && SELA_CONTEXT.top_slowest_transactions.length) {
      s += `Kedua, lakukan review khusus pada jenis transaksi ${SELA_CONTEXT.top_slowest_transactions[0].name}. `;
    }
    s += "Ketiga, buat monitoring transaksi aging dan alert untuk nomor permohonan yang melewati threshold SLA.";
    return s;
  }

  if (/(nilai|nominal|rupiah|amount)/.test(query)) {
    return "Untuk analisis nilai transaksi, saya bisa bantu jika kolom nominal/nilai transaksi tersedia dan sudah diproses di tab Nilai Transaksi. Pada mode suara ini, saya terutama membaca volume, SLA, vendor, jenis transaksi, dan nomor permohonan dari data aktif.";
  }

  return `Saya bisa bantu jawab berdasarkan data aktif. Saat ini saya membaca ${SELA_CONTEXT.total_rows_text} transaksi periode ${SELA_CONTEXT.period_start} sampai ${SELA_CONTEXT.period_end}. Pertanyaan yang paling akurat untuk saya misalnya: growth transaksi, SLA paling lama, bottleneck proses, vendor lambat, nomor permohonan, atau ringkasan Direksi.`;
}

function populateVoices() {
  voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  voiceSelect.innerHTML = "";

  if (!voices.length) {
    const opt = document.createElement("option");
    opt.textContent = "Voice browser belum tersedia";
    voiceSelect.appendChild(opt);
    return;
  }

  const scored = voices.map((v, i) => {
    const name = (v.name || "").toLowerCase();
    const lang = (v.lang || "").toLowerCase();
    let score = 0;
    if (lang.includes("id")) score += 20;
    if (lang.includes("en")) score += 4;
    if (/female|woman|zira|aria|susan|samantha|google|natural|neural|indonesia/.test(name)) score += 8;
    return {v, i, score};
  }).sort((a,b)=>b.score-a.score);

  scored.forEach(({v, i}) => {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = `${v.name} (${v.lang})`;
    voiceSelect.appendChild(opt);
  });

  if (scored.length) voiceSelect.value = String(scored[0].i);
}

function speak(text) {
  if (!window.speechSynthesis) {
    setMode("", "Browser tidak mendukung text-to-speech. Jawaban tetap tampil sebagai teks.");
    return;
  }

  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.lang = "id-ID";

  const idx = Number(voiceSelect.value);
  if (!isNaN(idx) && voices[idx]) utt.voice = voices[idx];

  utt.rate = 0.95;
  utt.pitch = 1.12;
  utt.volume = 1.0;

  utt.onstart = () => setMode("speaking", "SELA sedang menjawab dengan suara...");
  utt.onend = () => setMode("", "SELA siap menerima pertanyaan berikutnya.");
  utt.onerror = () => setMode("", "Suara gagal diputar oleh browser. Jawaban tetap tersedia dalam teks.");

  window.speechSynthesis.speak(utt);
}

function handleQuestion(q) {
  const question = String(q || "").trim();
  if (!question) return;

  addMessage("user", question);
  userInput.value = "";
  setMode("thinking", "SELA sedang menganalisis data aktif...");

  setTimeout(() => {
    const ans = answerQuestion(question);
    addMessage("sela", ans);
    speak(ans);
  }, 280);
}

function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    micBtn.disabled = false;
    micBtn.title = "Browser tidak mendukung speech recognition. Gunakan input teks.";
    return null;
  }

  const rec = new SR();
  rec.lang = "id-ID";
  rec.interimResults = false;
  rec.continuous = false;

  rec.onstart = () => {
    recognizing = true;
    micBtn.textContent = "🛑";
    setMode("listening", "SELA sedang mendengarkan... silakan bicara.");
  };

  rec.onend = () => {
    recognizing = false;
    micBtn.textContent = "🎙️";
    if (!avatarZone.classList.contains("speaking")) {
      setMode("", "SELA siap. Klik mic atau ketik pertanyaan.");
    }
  };

  rec.onerror = (event) => {
    recognizing = false;
    micBtn.textContent = "🎙️";
    const msg = "Mic tidak dapat digunakan: " + (event.error || "izin browser belum diberikan") + ". Silakan gunakan input teks.";
    setMode("", msg);
    addMessage("sela", msg);
  };

  rec.onresult = (event) => {
    let transcript = "";
    try {
      transcript = event.results[0][0].transcript;
    } catch(e) {}
    if (transcript) handleQuestion(transcript);
  };

  return rec;
}

sendBtn.addEventListener("click", () => handleQuestion(userInput.value));
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleQuestion(userInput.value);
});

micBtn.addEventListener("click", () => {
  if (!recognition) {
    const msg = "Browser ini belum mendukung speech recognition, atau akses mic dibatasi. Silakan ketik pertanyaan di kolom input.";
    setMode("", msg);
    addMessage("sela", msg);
    speak(msg);
    return;
  }
  if (!recognizing) recognition.start();
  else recognition.stop();
});

testBtn.addEventListener("click", () => {
  const text = "Halo, saya SELA. Suara saya sudah aktif. Silakan tanyakan data SLA, growth transaksi, bottleneck, vendor, atau ringkasan Direksi.";
  addMessage("sela", text);
  speak(text);
});

document.querySelectorAll(".chip").forEach(btn => {
  btn.addEventListener("click", () => handleQuestion(btn.getAttribute("data-q")));
});

if (window.speechSynthesis) {
  populateVoices();
  window.speechSynthesis.onvoiceschanged = populateVoices;
}

recognition = initRecognition();
initKpi();

const greeting = `Halo, saya SELA. Saya sudah membaca ${SELA_CONTEXT.total_rows_text || "0"} transaksi dari periode ${SELA_CONTEXT.period_start || "-"} sampai ${SELA_CONTEXT.period_end || "-"}. Silakan bicara atau ketik pertanyaan.`;
addMessage("sela", greeting);
setMode("", recognition ? "SELA siap. Klik mic untuk berbicara, atau ketik pertanyaan." : "SELA siap dalam mode ketik. Browser tidak mendukung mic.");
</script>
</body>
</html>
    """

    components.html(
        html_template.replace("__SELA_CONTEXT_JSON__", ctx_json),
        height=780,
        scrolling=False,
    )


# PANGGIL SELA HANYA JIKA USER MINTA
if st.session_state.get("show_sela", False):
    render_sela_natural_voice(
        df_filtered=df_filtered,
        periode_col=periode_col,
        available_sla_cols=available_sla_cols,
        selected_periode=selected_periode if "selected_periode" in globals() else None,
    )

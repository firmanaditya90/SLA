import streamlit as st
import pandas as pd
import re
import math
import os
import matplotlib.pyplot as plt
import requests
import time

# ==============================
# Fungsi untuk memuat animasi Lottie
# ==============================
def load_lottie_url(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None

# ==============================
# Konfigurasi Halaman
# ==============================
st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")

# ==============================
# Logo di Sidebar
# ==============================
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/7/7c/Logo_PT._ASDP_Indonesia_Ferry_%28Persero%29.png",
        width=200
    )
    st.markdown("<h3 style='text-align: center;'>🔒 Admin Panel</h3>", unsafe_allow_html=True)

# ==============================
# Admin password
# ==============================
os.makedirs("data", exist_ok=True)
DATA_PATH = os.path.join("data", "last_data.xlsx")

try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)
except Exception:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", None)

if ADMIN_PASSWORD:
    password_input = st.sidebar.text_input("Masukkan password admin", type="password")
    is_admin = password_input == ADMIN_PASSWORD
else:
    st.sidebar.warning("⚠️ Admin password belum dikonfigurasi (Secrets/ENV). App berjalan dalam mode read-only.")
    is_admin = False

# ==============================
# Fungsi util
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
uploaded_file = st.file_uploader("📂 Upload file Excel (.xlsx) [Admin only]", type="xlsx") if is_admin else None

# ==============================
# Animasi Rocket saat baca data
# ==============================
lottie_rocket = load_lottie_url("https://assets4.lottiefiles.com/packages/lf20_jcikwtux.json")

if uploaded_file is not None and is_admin:
    with open(DATA_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("✅ Data baru berhasil diunggah!")

    if lottie_rocket:
        st.markdown("<h4 style='text-align:center'>🚀 Memproses data...</h4>", unsafe_allow_html=True)
        from streamlit_lottie import st_lottie
        st_lottie(lottie_rocket, height=300, key="rocket")
        time.sleep(2)

    df_raw = pd.read_excel(DATA_PATH, header=[0, 1])

elif os.path.exists(DATA_PATH):
    if lottie_rocket:
        st.markdown("<h4 style='text-align:center'>🚀 Memuat data terakhir...</h4>", unsafe_allow_html=True)
        from streamlit_lottie import st_lottie
        st_lottie(lottie_rocket, height=300, key="rocket_last")
        time.sleep(2)

    df_raw = pd.read_excel(DATA_PATH, header=[0, 1])
    st.info("ℹ️ Menampilkan data dari upload terakhir.")

else:
    st.warning("⚠️ Belum ada file yang diunggah.")
    st.stop()

# ==============================
# Tombol reset
# ==============================
if is_admin and os.path.exists(DATA_PATH):
    if st.sidebar.button("🗑️ Reset Data (hapus data terakhir)"):
        os.remove(DATA_PATH)
        st.experimental_rerun()

# ==============================
# Preprocessing kolom
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
for col in sla_cols:
    if col in df_raw.columns:
        df_raw[col] = df_raw[col].apply(parse_sla)

try:
    df_raw['PERIODE_DATETIME'] = pd.to_datetime(df_raw[periode_col], errors='coerce')
except Exception:
    df_raw['PERIODE_DATETIME'] = None

# ==============================
# Sidebar filter periode
# ==============================
st.sidebar.subheader("📅 Filter Rentang Periode")
periode_list = sorted(
    df_raw[periode_col].dropna().astype(str).unique().tolist(),
    key=lambda x: pd.to_datetime(x, errors='coerce')
)
start_periode = st.sidebar.selectbox("Periode Mulai", periode_list, index=0)
end_periode = st.sidebar.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)

# Created by
st.sidebar.markdown("<p style='text-align:center; font-size:12px; color:gray;'>Created by. Firman Aditya</p>", unsafe_allow_html=True)

idx_start = periode_list.index(start_periode)
idx_end = periode_list.index(end_periode)
if idx_start > idx_end:
    st.error("Periode Mulai harus sebelum Periode Akhir.")
    st.stop()

selected_periode = periode_list[idx_start:idx_end+1]
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)]
available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]
proses_grafik_cols = [c for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"] if c in available_sla_cols]

# ==============================
# Analisis Rata-rata SLA
# ==============================
avg_sla = {col: seconds_to_sla_format(df_filtered[col].mean()) for col in available_sla_cols}

st.markdown("## 📊 Rata-rata SLA")
col_count = len(available_sla_cols)
cols = st.columns(col_count)
for i, col in enumerate(available_sla_cols):
    cols[i].metric(label=col, value=avg_sla[col])

# ==============================
# Grafik SLA per tahap
# ==============================
if proses_grafik_cols:
    st.markdown("## 📈 Grafik SLA per Proses")
    fig, ax = plt.subplots(figsize=(10, 6))
    avg_values = [df_filtered[col].mean() / 3600 for col in proses_grafik_cols]
    ax.bar(proses_grafik_cols, avg_values, color='skyblue')
    ax.set_ylabel("Rata-rata Waktu (Jam)")
    ax.set_title("Rata-rata SLA per Tahap Proses")
    st.pyplot(fig)

# ==============================
# Data Table
# ==============================
st.markdown("## 📄 Data SLA")
df_display = df_filtered.copy()
for col in available_sla_cols:
    df_display[col] = df_display[col].apply(seconds_to_sla_format)
st.dataframe(df_display)

# ==============================
# Download Data
# ==============================
st.download_button(
    label="💾 Download Data",
    data=df_display.to_csv(index=False).encode('utf-8'),
    file_name="sla_data.csv",
    mime="text/csv"
)

import streamlit as st
import pandas as pd
import re
import math
import os
import matplotlib.pyplot as plt
from streamlit_lottie import st_lottie
import requests
from io import BytesIO

# ==============================
# Konfigurasi Awal
# ==============================
st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.markdown("<h1 style='text-align:center;'>📊 SLA Payment Analyzer</h1>", unsafe_allow_html=True)
st.write("Analisis SLA dokumen penagihan berdasarkan data yang diunggah. "
         "Siapa pun bisa melihat data terakhir. Upload hanya untuk admin.")

# ==============================
# Fungsi untuk Lottie Animasi
# ==============================
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Animasi rocket
rocket_lottie = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_jcikwtux.json")

# ==============================
# Sidebar: Logo + Password Admin
# ==============================
# Logo PT ASDP (pastikan ada file di folder assets/asdp_logo.png)
logo_path = "assets/asdp_logo.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_column_width=True)

# Password Admin
try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)
except Exception:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", None)

if ADMIN_PASSWORD:
    password_input = st.sidebar.text_input("Masukkan password admin", type="password")
    is_admin = password_input == ADMIN_PASSWORD
else:
    st.sidebar.warning("Admin password belum dikonfigurasi. Mode read-only.")
    is_admin = False

# ==============================
# Folder & File Data
# ==============================
os.makedirs("data", exist_ok=True)
DATA_PATH = os.path.join("data", "last_data.xlsx")

# ==============================
# Fungsi Parsing SLA
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
uploaded_file = st.file_uploader("Upload file Excel (.xlsx) [Admin only]", type="xlsx") if is_admin else None

# ==============================
# Load Data Terakhir
# ==============================
with st.spinner("📡 Membaca data, mohon tunggu..."):
    st_lottie(rocket_lottie, height=200, key="rocket")

if uploaded_file is not None and is_admin:
    with open(DATA_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("✅ Data baru berhasil diunggah dan disimpan!")
    df_raw = pd.read_excel(DATA_PATH, header=[0, 1])
elif os.path.exists(DATA_PATH):
    df_raw = pd.read_excel(DATA_PATH, header=[0, 1])
    st.info("ℹ️ Menampilkan data dari upload terakhir.")
else:
    st.warning("⚠️ Belum ada file yang diunggah.")
    st.stop()

# Tombol Reset Data
if is_admin and os.path.exists(DATA_PATH):
    if st.sidebar.button("🗑️ Reset Data"):
        os.remove(DATA_PATH)
        st.experimental_rerun()

# ==============================
# Normalisasi Kolom
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

st.subheader("📄 Kolom Terdeteksi")
st.write(list(df_raw.columns))

# ==============================
# Deteksi Periode
# ==============================
periode_col = next((col for col in df_raw.columns if "PERIODE" in str(col).upper()), None)
if not periode_col:
    st.error("Kolom PERIODE tidak ditemukan.")
    st.stop()

# Parse SLA
sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
for col in sla_cols:
    if col in df_raw.columns:
        df_raw[col] = df_raw[col].apply(parse_sla)

try:
    df_raw['PERIODE_DATETIME'] = pd.to_datetime(df_raw[periode_col], errors='coerce')
except Exception:
    df_raw['PERIODE_DATETIME'] = None

# ==============================
# Filter Periode
# ==============================
st.sidebar.subheader("Filter Rentang Periode")
periode_list = sorted(
    df_raw[periode_col].dropna().astype(str).unique().tolist(),
    key=lambda x: pd.to_datetime(x, errors='coerce')
)
start_periode = st.sidebar.selectbox("Periode Mulai", periode_list, index=0)
end_periode = st.sidebar.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)

st.sidebar.markdown("---")
st.sidebar.markdown("<small>Created by. <b>Firman Aditya</b></small>", unsafe_allow_html=True)

idx_start = periode_list.index(start_periode)
idx_end = periode_list.index(end_periode)
if idx_start > idx_end:
    st.error("Periode Mulai harus sebelum Periode Akhir.")
    st.stop()

selected_periode = periode_list[idx_start:idx_end+1]
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)]
st.write(f"Menampilkan data periode dari **{start_periode}** sampai **{end_periode}**, total baris: {len(df_filtered)}")

available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]
proses_grafik_cols = [c for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"] if c in available_sla_cols]

# ==============================
# Analisis Rata-rata SLA per Proses
# ==============================
if available_sla_cols:
    st.subheader("📌 Rata-rata SLA per Proses")
    rata_proses_seconds = df_filtered[available_sla_cols].mean()
    rata_proses = rata_proses_seconds.reset_index()
    rata_proses.columns = ["Proses", "Rata-rata (detik)"]
    rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(seconds_to_sla_format)
    st.dataframe(rata_proses[["Proses", "Rata-rata SLA"]])

    if proses_grafik_cols:
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        values_hari = [rata_proses_seconds[col] / 86400 for col in proses_grafik_cols]
        ax2.bar(proses_grafik_cols, values_hari, color='skyblue')
        ax2.set_title("Rata-rata SLA per Proses (hari)")
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        st.pyplot(fig2)

# ==============================
# SLA per Jenis Transaksi
# ==============================
if "JENIS TRANSAKSI" in df_filtered.columns and available_sla_cols:
    st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
    transaksi_group = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols].agg(['mean', 'count']).reset_index()
    transaksi_display = pd.DataFrame()
    transaksi_display["JENIS TRANSAKSI"] = transaksi_group["JENIS TRANSAKSI"]
    for col in available_sla_cols:
        transaksi_display[f"{col} (Rata-rata)"] = transaksi_group[(col, 'mean')].apply(seconds_to_sla_format)
        transaksi_display[f"{col} (Jumlah)"] = transaksi_group[(col, 'count')]
    st.dataframe(transaksi_display)

# ==============================
# SLA per Vendor
# ==============================
if "NAMA VENDOR" in df_filtered.columns:
    vendor_list = sorted(df_filtered["NAMA VENDOR"].dropna().unique())
    vendor_list_with_all = ["ALL"] + vendor_list
    selected_vendors = st.sidebar.multiselect("Pilih Vendor", vendor_list_with_all, default=["ALL"])

    if "ALL" in selected_vendors:
        df_vendor_filtered = df_filtered.copy()
    else:
        df_vendor_filtered = df_filtered[df_filtered["NAMA VENDOR"].isin(selected_vendors)]
    
    if df_vendor_filtered.shape[0] > 0 and available_sla_cols:
        st.subheader("📌 Rata-rata SLA per Vendor")
        rata_vendor = df_vendor_filtered.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index()
        for col in available_sla_cols:
            rata_vendor[col] = rata_vendor[col].apply(seconds_to_sla_format)
        st.dataframe(rata_vendor)
    else:
        st.info("Tidak ada data untuk vendor yang dipilih.")

# ==============================
# Trend SLA per Periode
# ==============================
if available_sla_cols:
    st.subheader("📈 Trend SLA per Periode")
    trend = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()
    trend["PERIODE_SORTED"] = pd.Categorical(trend[periode_col], categories=selected_periode, ordered=True)
    trend = trend.sort_values("PERIODE_SORTED")

    if "TOTAL WAKTU" in available_sla_cols:
        fig, ax = plt.subplots(figsize=(10, 5))
        y_values_days = trend["TOTAL WAKTU"].apply(lambda x: x / 86400)
        ax.plot(trend[periode_col], y_values_days, marker='o', label="TOTAL WAKTU", color='#9467bd')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()
        for label in ax.get_xticklabels():
            label.set_rotation(45)
        st.pyplot(fig)

# ==============================
# Jumlah Transaksi per Periode
# ==============================
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

st.dataframe(jumlah_transaksi.style.apply(highlight_total, axis=1))

fig_trans, ax_trans = plt.subplots(figsize=(10, 5))
ax_trans.bar(
    jumlah_transaksi[jumlah_transaksi[periode_col] != "TOTAL"][periode_col],
    jumlah_transaksi[jumlah_transaksi[periode_col] != "TOTAL"]['Jumlah'],
    color='coral'
)
ax_trans.grid(axis='y', linestyle='--', alpha=0.7)
for label in ax_trans.get_xticklabels():
    label.set_rotation(45)
st.pyplot(fig_trans)

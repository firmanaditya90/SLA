import streamlit as st
import pandas as pd
import re
import math
import os
import matplotlib.pyplot as plt

# ==============================
# Konfigurasi Halaman
# ==============================
st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Analisis SLA dokumen penagihan berdasarkan data yang diunggah.")

# ==============================
# Path Penyimpanan
# ==============================
os.makedirs("data", exist_ok=True)
DATA_PATH = os.path.join("data", "last_data.xlsx")

# ==============================
# Fungsi utilitas SLA
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
# Fungsi Load Data dengan Cache
# ==============================
@st.cache_data
def load_excel(file_path):
    df = pd.read_excel(file_path, engine="openpyxl", header=[0, 1])
    # Flatten MultiIndex menjadi single level
    df.columns = ["_".join([str(c) for c in col if str(c) != 'nan']) for col in df.columns]
    return df

# ==============================
# Login Admin untuk Upload
# ==============================
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)
is_admin = False
if ADMIN_PASSWORD:
    pwd = st.sidebar.text_input("Password admin", type="password")
    is_admin = pwd == ADMIN_PASSWORD

# ==============================
# Upload File (Hanya Admin)
# ==============================
if is_admin:
    uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")
    if uploaded_file is not None:
        with open(DATA_PATH, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("✅ Data baru berhasil disimpan!")
        st.cache_data.clear()

# ==============================
# Load Data yang Tersimpan
# ==============================
if os.path.exists(DATA_PATH):
    df_raw = load_excel(DATA_PATH)
else:
    st.warning("⚠️ Belum ada file yang diunggah.")
    st.stop()

# ==============================
# Pilih Periode
# ==============================
periode_col = next((col for col in df_raw.columns if "PERIODE" in col.upper()), None)
if not periode_col:
    st.error("Kolom PERIODE tidak ditemukan.")
    st.stop()

periode_list = sorted(
    df_raw[periode_col].dropna().astype(str).unique(),
    key=lambda x: pd.to_datetime(x, errors="coerce")
)

start_periode = st.sidebar.selectbox("Periode Mulai", periode_list, index=0)
end_periode = st.sidebar.selectbox("Periode Akhir", periode_list, index=len(periode_list) - 1)

idx_start = periode_list.index(start_periode)
idx_end = periode_list.index(end_periode)
if idx_start > idx_end:
    st.error("Periode Mulai harus sebelum Periode Akhir.")
    st.stop()

selected_periode = periode_list[idx_start:idx_end + 1]
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)]

# ==============================
# Parsing SLA Setelah Filter
# ==============================
sla_cols = [
    "SLA_FUNGSIONAL",
    "SLA_VENDOR",
    "SLA_KEUANGAN",
    "SLA_PERBENDAHARAAN",
    "SLA_TOTAL WAKTU"
]
sla_cols = [col for col in sla_cols if col in df_filtered.columns]
for col in sla_cols:
    df_filtered[col] = df_filtered[col].apply(parse_sla)

# ==============================
# Tabel Data
# ==============================
st.subheader("📄 Data Filtered")
st.dataframe(df_filtered.head(50))  # tampilkan 50 baris pertama

# ==============================
# Ringkasan SLA
# ==============================
if sla_cols:
    st.subheader("📊 Rata-rata SLA per Proses")
    rata_proses_seconds = df_filtered[sla_cols].mean()
    rata_df = rata_proses_seconds.reset_index()
    rata_df.columns = ["Proses", "Rata-rata (detik)"]
    rata_df["Rata-rata SLA"] = rata_df["Rata-rata (detik)"].apply(seconds_to_sla_format)
    st.dataframe(rata_df[["Proses", "Rata-rata SLA"]])

    # ==============================
    # Grafik SLA
    # ==============================
    fig, ax = plt.subplots()
    ax.bar(rata_df["Proses"], rata_df["Rata-rata (detik)"])
    ax.set_ylabel("Rata-rata (detik)")
    ax.set_title("Rata-rata SLA per Proses")
    plt.xticks(rotation=45)
    st.pyplot(fig)

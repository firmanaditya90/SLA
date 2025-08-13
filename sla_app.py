import streamlit as st
import pandas as pd
import re
from datetime import timedelta

st.set_page_config(page_title="📊 SLA Payment Analyzer", layout="wide")

st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

# ===== Fungsi Helper =====
def parse_sla_to_seconds(value):
    """Konversi SLA ke detik dari format string, timedelta, atau angka."""
    if pd.isna(value):
        return None
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        text = value.strip().lower()
        total_seconds = 0
        match = re.findall(r"(\d+)\s*(hari|jam|menit|detik)", text)
        for jumlah, unit in match:
            jumlah = int(jumlah)
            if unit == "hari":
                total_seconds += jumlah * 86400
            elif unit == "jam":
                total_seconds += jumlah * 3600
            elif unit == "menit":
                total_seconds += jumlah * 60
            elif unit == "detik":
                total_seconds += jumlah
        if total_seconds > 0:
            return total_seconds
    return None

def seconds_to_dhms(seconds):
    """Konversi detik menjadi format 'x hari x jam x menit x detik'."""
    if seconds is None or pd.isna(seconds):
        return "-"
    seconds = int(seconds)
    hari = seconds // 86400
    seconds %= 86400
    jam = seconds // 3600
    seconds %= 3600
    menit = seconds // 60
    detik = seconds % 60
    return f"{hari} hari {jam} jam {menit} menit {detik} detik"

# ===== Upload File =====
uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Baca file Excel
        df_raw = pd.read_excel(uploaded_file, header=1)  # Mulai dari baris ke-2 karena baris 1 merge
        df = df_raw.copy()

        # Tampilkan kolom terdeteksi
        st.write("📄 **Kolom yang terdeteksi di file**")
        st.write(list(df.columns))

        # Pastikan kolom wajib ada
        required_cols = ["PERIODE", "NO PERMOHONAN", "JENIS TRANSAKSI", "NAMA VENDOR"]
        sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]

        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"

import streamlit as st
import pandas as pd
import re
import math

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

def parse_sla(s):
    """Konversi SLA string menjadi total detik (int).
    Contoh format input:
    - 'SLA 2 days 03:45:30'
    - '2 days 3:45'
    - 'SLA 1 day 5:20:15'
    """
    if pd.isna(s):
        return None
    s = str(s).upper().replace("SLA", "").strip()

    days = 0
    hours = 0
    minutes = 0
    seconds = 0

    # Cari hari (day/days)
    day_match = re.search(r'(\d+)\s*DAY', s)
    if day_match:
        days = int(day_match.group(1))

    # Cari waktu jam:menit[:detik]
    time_match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        if time_match.group(3):
            seconds = int(time_match.group(3))

    total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total_seconds

def seconds_to_sla_format(total_seconds):
    """Konversi total detik ke format 'xx hari xx jam xx menit xx detik'"""
    if total_seconds is None or math.isnan(total_seconds):
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

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file, header=[0, 1])

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

    st.subheader("📄 Kolom yang terdeteksi di file")
    st.write(list(df_raw.columns))

    periode_col = None
    for col in df_raw.columns:
        if "PERIODE" in str(col).upper():
            periode_col = col
            break
    if not periode_col:
        st.error("Kolom PERIODE tidak ditemukan.")
        st.stop()

    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    for col in sla_cols:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(parse_sla)

    periode_list = sorted(df_raw[periode_col].astype(str).dropna().unique().tolist())
    periode_filter = st.multiselect("Filter Periode", periode_list, default=periode_list)
    df_filtered = df_raw[df_raw[periode_col].astype(str).isin(periode_filter)]

    available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]
    if available_sla_cols:
        st.subheader("📌 Rata-rata SLA per Proses (format hari jam menit detik)")

        rata_proses_seconds = df_filtered[available_sla_cols].mean()
        rata_proses = rata_proses_seconds.reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (detik)"]

        # Tambahkan kolom formatted string
        rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(seconds_to_sla_format)

        st.dataframe(rata_proses[["Proses", "Rata-rata SLA"]])

    if "JENIS TRANSAKSI" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
        rata_transaksi_seconds = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols].mean().reset_index()

        # Konversi semua kolom SLA ke format string
        for col in available_sla_cols:
            rata_transaksi_seconds[col] = rata_transaksi_seconds[col].apply(seconds_to_sla_format)

        st.dataframe(rata_transaksi_seconds)

    if "NAMA VENDOR" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Vendor")
        rata_vendor_seconds = df_filtered.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index()

        for col in available_sla_cols:
            rata_vendor_seconds[col] = rata_vendor_seconds[col].apply(seconds_to_sla_format)

        st.dataframe(rata_vendor_seconds)
else:
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

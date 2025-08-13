import streamlit as st
import pandas as pd
import re
import math
import matplotlib.pyplot as plt

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

def parse_sla(s):
    if pd.isna(s):
        return None
    s = str(s).upper().replace("SLA", "").strip()
    days = 0
    hours = 0
    minutes = 0
    seconds = 0
    day_match = re.search(r'(\d+)\s*DAY', s)
    if day_match:
        days = int(day_match.group(1))
    time_match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        if time_match.group(3):
            seconds = int(time_match.group(3))
    total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total_seconds

def seconds_to_sla_format(total_seconds):
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

    periode_col = None
    for col in df_raw.columns:
        if "PERIODE" in str(col).upper():
            periode_col = col
            break
    if not periode_col:
        st.error("Kolom PERIODE tidak ditemukan.")
        st.stop()

    # Konversi kolom PERIODE ke datetime, coba-coba
    try:
        df_raw[periode_col] = pd.to_datetime(df_raw[periode_col])
    except Exception:
        st.error("Kolom PERIODE tidak bisa di-convert ke tanggal. Pastikan format tanggal benar.")
        st.stop()

    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    for col in sla_cols:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(parse_sla)

    # Pilih rentang periode
    min_date = df_raw[periode_col].min()
    max_date = df_raw[periode_col].max()
    st.subheader("Filter Rentang Periode")
    date_range = st.date_input("Pilih rentang tanggal", [min_date, max_date], min_value=min_date, max_value=max_date)

    if len(date_range) != 2:
        st.warning("Pilih tanggal mulai dan tanggal akhir")
        st.stop()

    start_date, end_date = date_range
    mask = (df_raw[periode_col] >= pd.Timestamp(start_date)) & (df_raw[periode_col] <= pd.Timestamp(end_date))
    df_filtered = df_raw.loc[mask]

    st.write(f"Menampilkan data dari {start_date} sampai {end_date}, total baris: {len(df_filtered)}")

    available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]

    # Rata-rata SLA per Proses seperti sebelumnya
    if available_sla_cols:
        st.subheader("📌 Rata-rata SLA per Proses (format hari jam menit detik)")
        rata_proses_seconds = df_filtered[available_sla_cols].mean()
        rata_proses = rata_proses_seconds.reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (detik)"]
        rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(seconds_to_sla_format)
        st.dataframe(rata_proses[["Proses", "Rata-rata SLA"]])

    # Buat kolom periode bulan-tahun untuk analisis trend
    df_filtered["PERIODE_BULAN"] = df_filtered[periode_col].dt.to_period("M").dt.to_timestamp()

    st.subheader("📈 Trend Rata-rata SLA per Periode Bulanan")

    # Hitung rata-rata SLA per bulan
    trend = df_filtered.groupby("PERIODE_BULAN")[available_sla_cols].mean().reset_index()

    # Tampilkan tabel dengan format SLA string
    trend_display = trend.copy()
    for col in available_sla_cols:
        trend_display[col] = trend_display[col].apply(seconds_to_sla_format)
    st.dataframe(trend_display)

    # Plot grafik trend (contoh untuk TOTAL WAKTU)
    if "TOTAL WAKTU" in available_sla_cols:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(trend["PERIODE_BULAN"], trend["TOTAL WAKTU"], marker='o', label="TOTAL WAKTU")
        ax.set_title("Trend Rata-rata SLA TOTAL WAKTU per Bulan")
        ax.set_xlabel("Periode")
        ax.set_ylabel("Rata-rata SLA (detik)")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

else:
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

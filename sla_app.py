import streamlit as st
import pandas as pd

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

def parse_sla(s):
    """Konversi SLA string menjadi jumlah hari (float)"""
    if pd.isna(s):
        return None
    s = str(s).replace("SLA", "").strip()
    days = 0
    hours = 0
    minutes = 0
    parts = s.split()
    if "days" in parts:
        days = int(parts[parts.index("days") - 1])
    elif "day" in parts:
        days = int(parts[parts.index("day") - 1])
    if ":" in parts[-1]:
        t = parts[-1].split(":")
        hours = int(t[0])
        minutes = int(t[1])
    return round(days + hours / 24 + minutes / 1440, 2)

if uploaded_file:
    # Baca 2 baris header
    df_raw = pd.read_excel(uploaded_file, header=[0, 1])

    # Gabungkan nama kolom
    df_raw.columns = [
        f"{col0}_{col1}" if "SLA" in str(col0).upper() else col0
        for col0, col1 in df_raw.columns
    ]

    # Rename supaya rapi
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

    # Pastikan kolom PERIODE ada
    periode_col = None
    for col in df_raw.columns:
        if "PERIODE" in str(col).upper():
            periode_col = col
            break
    if not periode_col:
        st.error("Kolom PERIODE tidak ditemukan.")
        st.stop()

    # Konversi kolom SLA jadi hari (float)
    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    for col in sla_cols:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(parse_sla)

    # Filter Periode
    periode_list = sorted(df_raw[periode_col].astype(str).dropna().unique().tolist())
    periode_filter = st.multiselect("Filter Periode", periode_list, default=periode_list)
    df_filtered = df_raw[df_raw[periode_col].astype(str).isin(periode_filter)]

    # Rata-rata SLA per Proses
    available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]
    if available_sla_cols:
        st.subheader("📌 Rata-rata SLA per Proses (hari)")
        rata_proses = df_filtered[available_sla_cols].mean().reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (hari)"]
        st.dataframe(rata_proses)

    # Rata-rata SLA per Jenis Transaksi
    if "JENIS TRANSAKSI" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
        rata_transaksi = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols].mean().reset_index()
        st.dataframe(rata_transaksi)

    # Rata-rata SLA per Vendor
    if "NAMA VENDOR" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Vendor")
        rata_vendor = df_filtered.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index()
        st.dataframe(rata_vendor)
else:
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

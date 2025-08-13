import streamlit as st
import pandas as pd

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")

st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

# Fungsi parsing SLA string ke hari (float)
def parse_sla(s):
    if pd.isna(s):
        return None
    s = str(s).replace("SLA", "").replace("TOTAL", "").strip()
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
    # Baca file dengan 2 baris header lalu gabungkan jadi satu
    df = pd.read_excel(uploaded_file, header=[0, 1])

    # Gabungkan multi-index kolom jadi satu baris nama
    df.columns = [str(col[0]).strip() if col[0] != 'nan' else str(col[1]).strip() for col in df.columns]

    # Normalisasi nama kolom (hapus spasi extra, uppercase semua)
    df.columns = [col.strip().upper() for col in df.columns]

    st.subheader("📄 Kolom yang terdeteksi di file")
    st.write(list(df.columns))

    # Tentukan kolom SLA
    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    for col in sla_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_sla)

    # Ambil list periode (pastikan kolom ada)
    periode_col = [col for col in df.columns if "PERIODE" in col]
    if periode_col:
        periode_list = df[periode_col[0]].dropna().unique().tolist()
        periode_filter = st.multiselect("Filter Periode", periode_list, default=periode_list)
        df_filtered = df[df[periode_col[0]].isin(periode_filter)]
    else:
        st.error("Kolom 'PERIODE' tidak ditemukan di file.")
        st.stop()

    # Rata-rata SLA per proses
    st.subheader("📌 Rata-rata SLA per Proses (hari)")
    rata_proses = df_filtered[sla_cols[:-1]].mean().reset_index()
    rata_proses.columns = ["Proses", "Rata-rata (hari)"]
    st.dataframe(rata_proses)

    # Rata-rata SLA per jenis transaksi
    jenis_col = [col for col in df.columns if "JENIS" in col]
    if jenis_col:
        st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
        rata_transaksi = df_filtered.groupby(jenis_col[0])[sla_cols[:-1]].mean().reset_index()
        st.dataframe(rata_transaksi)

    # Rata-rata SLA per vendor
    vendor_col = [col for col in df.columns if "VENDOR" in col and col != "VENDOR"]
    if vendor_col:
        st.subheader("📌 Rata-rata SLA per Vendor")
        rata_vendor = df_filtered.groupby(vendor_col[0])[sla_cols[:-1]].mean().reset_index()
        st.dataframe(rata_vendor)

else:
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

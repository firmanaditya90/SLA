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
    # Baca file mulai dari baris kedua sebagai header
    df = pd.read_excel(uploaded_file, header=1)

    st.subheader("📄 Kolom yang terdeteksi di file")
    st.write(list(df.columns))

    # Cari kolom PERIODE secara fleksibel
    periode_col = None
    for col in df.columns:
        if "PERIODE" in str(col).upper():
            periode_col = col
            break
    if not periode_col:
        st.error("Kolom PERIODE tidak ditemukan.")
        st.stop()

    # Cari kolom SLA proses
    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    available_sla_cols = [col for col in sla_cols if col in df.columns]

    # Konversi SLA menjadi hari
    for col in available_sla_cols:
        df[col] = df[col].apply(parse_sla)

    # ==== FILTER PERIODE ====
    periode_list = df[periode_col].dropna().unique().tolist()
    try:
        periode_list_dt = pd.to_datetime(periode_list, errors="coerce")
        if periode_list_dt.notna().all():
            periode_list = sorted(periode_list_dt)
        else:
            periode_list = sorted([str(p) for p in periode_list])
    except Exception:
        periode_list = sorted([str(p) for p in periode_list])

    periode_filter = st.multiselect(
        "Filter Periode",
        [str(p) for p in periode_list],
        default=[str(p) for p in periode_list]
    )

    df_filtered = df[df[periode_col].astype(str).isin(periode_filter)]

    # ==== Rata-rata SLA per Proses ====
    if available_sla_cols:
        st.subheader("📌 Rata-rata SLA per Proses (hari)")
        rata_proses = df_filtered[available_sla_cols[:-1]].mean().reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (hari)"]
        st.dataframe(rata_proses)

    # ==== Rata-rata SLA per Jenis Transaksi ====
    if "JENIS TRANSAKSI" in df.columns:
        st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
        rata_transaksi = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols[:-1]].mean().reset_index()
        st.dataframe(rata_transaksi)

    # ==== Rata-rata SLA per Vendor ====
    if "NAMA VENDOR" in df.columns:
        st.subheader("📌 Rata-rata SLA per Vendor")
        rata_vendor = df_filtered.groupby("NAMA VENDOR")[available_sla_cols[:-1]].mean().reset_index()
        st.dataframe(rata_vendor)

else:
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

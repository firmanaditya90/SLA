import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")

st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor, lengkap dengan grafik visualisasi.")

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
    # Baca dengan 2 baris header
    df = pd.read_excel(uploaded_file, header=[0, 1])

    # Gabungkan header multi-index jadi string
    df.columns = [
        (str(col[0]).strip() if col[0] != 'nan' else '') + " " + str(col[1]).strip()
        if col[1] != 'nan' else str(col[0]).strip()
        for col in df.columns
    ]
    df.columns = [col.strip().upper().replace("  ", " ") for col in df.columns]

    st.subheader("📄 Kolom yang terdeteksi di file")
    st.write(list(df.columns))

    # Tentukan kolom SLA
    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    for col in sla_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_sla)

    # Filter Periode
    periode_col = [col for col in df.columns if "PERIODE" in col]
    if periode_col:
        periode_list = sorted(df[periode_col[0]].dropna().unique().tolist())
        periode_filter = st.multiselect("Filter Periode", periode_list, default=periode_list)
        df_filtered = df[df[periode_col[0]].isin(periode_filter)]
    else:
        st.error("Kolom 'PERIODE' tidak ditemukan di file.")
        st.stop()

    # --- 1. Rata-rata SLA per proses ---
    st.subheader("📌 Rata-rata SLA per Proses (hari)")
    rata_proses = df_filtered[sla_cols[:-1]].mean().reset_index()
    rata_proses.columns = ["Proses", "Rata-rata (hari)"]
    st.dataframe(rata_proses)

    fig1, ax1 = plt.subplots()
    ax1.bar(rata_proses["Proses"], rata_proses["Rata-rata (hari)"], color="skyblue")
    ax1.set_ylabel("Hari")
    ax1.set_title("Rata-rata SLA per Proses")
    st.pyplot(fig1)

    # --- 2. Rata-rata SLA per jenis transaksi ---
    jenis_col = [col for col in df.columns if "JENIS" in col]
    if jenis_col:
        st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
        rata_transaksi = df_filtered.groupby(jenis_col[0])[sla_cols[:-1]].mean().reset_index()
        st.dataframe(rata_transaksi)

        fig2, ax2 = plt.subplots(figsize=(8, 4))
        for col in sla_cols[:-1]:
            ax2.plot(rata_transaksi[jenis_col[0]], rata_transaksi[col], marker="o", label=col)
        ax2.set_ylabel("Hari")
        ax2.set_title("Rata-rata SLA per Jenis Transaksi")
        ax2.legend()
        plt.xticks(rotation=45, ha='right')
        st.pyplot(fig2)

    # --- 3. Rata-rata SLA per vendor ---
    vendor_col = [col for col in df.columns if "NAMA VENDOR" in col]
    if vendor_col:
        st.subheader("📌 Rata-rata SLA per Vendor (Top 10 Terlama)")
        rata_vendor = (
            df_filtered.groupby(vendor_col[0])[sla_cols[:-1]]
            .mean()
            .reset_index()
            .sort_values(by="TOTAL WAKTU", ascending=False)
            .head(10)
        )
        st.dataframe(rata_vendor)

        fig3, ax3 = plt.subplots(figsize=(8, 5))
        ax3.barh(rata_vendor[vendor_col[0]], rata_vendor["TOTAL WAKTU"], color="salmon")
        ax3.set_xlabel("Hari")
        ax3.set_title("Top 10 Vendor dengan SLA Terlama")
        plt.gca().invert_yaxis()
        st.pyplot(fig3)

else:
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

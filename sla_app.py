import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="📊 SLA Payment Analyzer", layout="wide")

st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

def seconds_to_hms(seconds):
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, sec = divmod(remainder, 60)
    return f"{days} hari {hours} jam {minutes} menit {sec} detik"

if uploaded_file:
    try:
        # Baca 2 baris pertama untuk header
        raw_df = pd.read_excel(uploaded_file, header=None)
        header_row1 = raw_df.iloc[0].astype(str).replace("nan", "").tolist()
        header_row2 = raw_df.iloc[1].astype(str).replace("nan", "").tolist()

        # Gabungkan dua baris jadi satu header
        new_header = []
        for h1, h2 in zip(header_row1, header_row2):
            if h1 and h1.strip() != "":
                if h2 and h2.strip() != "":
                    new_header.append(h2.strip())
                else:
                    new_header.append(h1.strip())
            else:
                new_header.append(h2.strip() if h2.strip() != "" else "")

        # Baca ulang data mulai baris ketiga
        df = pd.read_excel(uploaded_file, header=None, skiprows=2)
        df.columns = new_header

        # Ubah SLA jadi nama proses sesuai urutan
        sla_labels = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
        sla_index = 0
        for i, col in enumerate(df.columns):
            if col.upper() == "SLA" and sla_index < len(sla_labels):
                df.rename(columns={col: sla_labels[sla_index]}, inplace=True)
                sla_index += 1

        st.write("📄 Kolom yang terdeteksi di file")
        st.write(list(df.columns))

        required_cols = ["PERIODE", "NO PERMOHONAN", "JENIS TRANSAKSI", "NAMA VENDOR"] + sla_labels
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Kolom berikut tidak ditemukan di file: {', '.join(missing_cols)}")
        else:
            # Konversi SLA ke detik
            for col in sla_labels:
                df[col] = pd.to_timedelta(df[col], errors='coerce').dt.total_seconds()

            # Filter periode
            periode_list = sorted(df["PERIODE"].dropna().unique().tolist())
            periode_filter = st.selectbox("Filter Periode", periode_list)
            filtered_df = df[df["PERIODE"] == periode_filter]

            # Rata-rata per proses
            st.subheader("📌 Rata-rata SLA per Proses")
            avg_per_proses = filtered_df[sla_labels].mean()
            avg_per_proses_fmt = avg_per_proses.apply(seconds_to_hms)
            st.dataframe(avg_per_proses_fmt.reset_index().rename(columns={"index": "Proses", 0: "Rata-rata SLA"}))

            # Rata-rata per jenis transaksi
            st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
            avg_per_jenis = filtered_df.groupby("JENIS TRANSAKSI")[sla_labels].mean().applymap(seconds_to_hms)
            st.dataframe(avg_per_jenis)

            # Rata-rata per vendor
            st.subheader("📌 Rata-rata SLA per Vendor")
            avg_per_vendor = filtered_df.groupby("NAMA VENDOR")[sla_labels].mean().applymap(seconds_to_hms)
            st.dataframe(avg_per_vendor)

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")

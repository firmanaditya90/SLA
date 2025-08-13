import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")

st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Baca file Excel
        df = pd.read_excel(uploaded_file)

        # Bersihkan nama kolom
        df.columns = df.columns.str.strip().str.upper()

        # Debug: tampilkan nama kolom
        st.subheader("📋 Kolom yang terdeteksi di file")
        st.write(list(df.columns))

        # Cari kolom SLA otomatis
        sla_cols = [col for col in df.columns if "SLA" in col or "TOTAL WAKTU" in col]

        if not sla_cols:
            st.error("❌ Tidak ditemukan kolom SLA atau TOTAL WAKTU di file ini.")
        else:
            st.success(f"Kolom SLA yang dipakai: {sla_cols}")

        # Fungsi parsing SLA string -> hari (float)
        def parse_sla(s):
            if pd.isna(s):
                return None
            s = str(s).strip().upper()
            match = re.search(r'(\d+)\s*DAYS?\s*(\d+):(\d+):(\d+)', s)
            if match:
                days, hours, minutes, seconds = map(int, match.groups())
                return days + hours / 24 + minutes / 1440 + seconds / 86400
            else:
                match = re.search(r'(\d+):(\d+):(\d+)', s)  # HH:MM:SS tanpa 'days'
                if match:
                    hours, minutes, seconds = map(int, match.groups())
                    return hours / 24 + minutes / 1440 + seconds / 86400
            return None

        # Konversi semua kolom SLA
        for col in sla_cols:
            df[col + "_HARI"] = df[col].apply(parse_sla)

        # Filter periode (kalau kolom PERIODE ada)
        if "PERIODE" in df.columns:
            periode_list = sorted(df["PERIODE"].dropna().unique().tolist())
            selected_periode = st.multiselect("Filter Periode", periode_list, default=periode_list)
            df = df[df["PERIODE"].isin(selected_periode)]

        # Tabel rata-rata SLA per proses
        if sla_cols:
            avg_sla = df[[col + "_HARI" for col in sla_cols]].mean().reset_index()
            avg_sla.columns = ["Proses", "Rata-rata (hari)"]
            avg_sla["Proses"] = avg_sla["Proses"].str.replace("_HARI", "")
            st.subheader("📈 Rata-rata SLA (hari)")
            st.dataframe(avg_sla)

        # Rekap per jenis transaksi
        if "JENIS TRANSAKSI" in df.columns and sla_cols:
            rekap_transaksi = df.groupby("JENIS TRANSAKSI")[[col + "_HARI" for col in sla_cols]].mean().reset_index()
            st.subheader("📌 Rekap per Jenis Transaksi")
            st.dataframe(rekap_transaksi)

        # Rekap per vendor
        if "NAMA VENDOR" in df.columns and sla_cols:
            rekap_vendor = df.groupby("NAMA VENDOR")[[col + "_HARI" for col in sla_cols]].mean().reset_index()
            st.subheader("🏢 Rekap per Vendor")
            st.dataframe(rekap_vendor)

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")

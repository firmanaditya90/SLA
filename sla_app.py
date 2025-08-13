import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")

st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)

        # Tampilkan kolom yang terdeteksi
        st.subheader("📋 Kolom yang terdeteksi di file")
        st.json(list(df.columns))

        # Bersihkan nama kolom
        df.columns = [str(c).strip().upper() for c in df.columns]

        # Pastikan kolom PERIODE jadi string agar tidak error sorting
        if "PERIODE" in df.columns:
            df["PERIODE"] = df["PERIODE"].astype(str)

        # Konversi kolom SLA ke numerik (jika berupa tanggal, konversi ke hari)
        if "SLA" in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df["SLA"]):
                df["SLA_HARI"] = (df["SLA"] - df["SLA"].min()).dt.days
            else:
                df["SLA_HARI"] = pd.to_numeric(df["SLA"], errors="coerce")
        else:
            st.error("Kolom 'SLA' tidak ditemukan di file.")
            st.stop()

        # Filter periode
        if "PERIODE" in df.columns:
            periode_list = sorted(df["PERIODE"].dropna().unique())
            periode_filter = st.multiselect("Filter Periode", periode_list, default=periode_list)
            df = df[df["PERIODE"].isin(periode_filter)]

        # Hitung rata-rata SLA
        rata_sla = pd.DataFrame({"Proses": ["SLA"], "Rata-rata (hari)": [round(df["SLA_HARI"].mean(), 2)]})

        st.subheader("📏 Rata-rata SLA (hari)")
        st.dataframe(rata_sla, use_container_width=True)

        # Grafik rata-rata SLA per jenis transaksi
        if "JENIS TRANSAKSI" in df.columns:
            rekap_transaksi = df.groupby("JENIS TRANSAKSI", as_index=False)["SLA_HARI"].mean()
            rekap_transaksi["SLA_HARI"] = rekap_transaksi["SLA_HARI"].round(2)

            st.subheader("📌 Rekap per Jenis Transaksi")
            st.dataframe(rekap_transaksi, use_container_width=True)

            fig, ax = plt.subplots()
            ax.barh(rekap_transaksi["JENIS TRANSAKSI"], rekap_transaksi["SLA_HARI"])
            ax.set_xlabel("Rata-rata SLA (hari)")
            ax.set_ylabel("Jenis Transaksi")
            ax.set_title("Rata-rata SLA per Jenis Transaksi")
            st.pyplot(fig)

        # Grafik rata-rata SLA per vendor
        if "NAMA VENDOR" in df.columns:
            rekap_vendor = df.groupby("NAMA VENDOR", as_index=False)["SLA_HARI"].mean()
            rekap_vendor["SLA_HARI"] = rekap_vendor["SLA_HARI"].round(2)

            st.subheader("🏢 Rekap per Vendor")
            st.dataframe(rekap_vendor, use_container_width=True)

            fig, ax = plt.subplots()
            ax.barh(rekap_vendor["NAMA VENDOR"], rekap_vendor["SLA_HARI"])
            ax.set_xlabel("Rata-rata SLA (hari)")
            ax.set_ylabel("Vendor")
            ax.set_title("Rata-rata SLA per Vendor")
            st.pyplot(fig)

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")

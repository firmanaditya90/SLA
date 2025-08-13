import streamlit as st
import pandas as pd
import re
from datetime import timedelta

# === Fungsi konversi SLA ke hari ===
def parse_sla(sla_str):
    if pd.isna(sla_str):
        return None
    sla_str = str(sla_str).replace("SLA ", "").strip()
    days = 0
    time_str = sla_str
    if "days" in sla_str:
        match = re.match(r"(\d+)\s+days?\s+(\d+:\d+:\d+)", sla_str)
        if match:
            days = int(match.group(1))
            time_str = match.group(2)
    try:
        h, m, s = map(int, time_str.split(":"))
    except ValueError:
        return None
    td = timedelta(days=days, hours=h, minutes=m, seconds=s)
    return td.total_seconds() / 86400  # hasilnya dalam hari

# === UI ===
st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)

        # Pastikan kolom wajib ada
        required_cols = ["PERIODE", "JENIS TRANSAKSI", "NAMA VENDOR"]
        for col in required_cols:
            if col not in df.columns:
                st.error(f"Kolom '{col}' tidak ditemukan di file!")
                st.stop()

        # Deteksi kolom SLA
        sla_columns = [col for col in df.columns if str(col).upper() in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL"]]

        # Konversi ke _days
        for col in sla_columns:
            df[col + "_days"] = df[col].apply(parse_sla)

        # === Filter Periode ===
        periode_list = sorted(df["PERIODE"].dropna().unique())
        periode_selected = st.sidebar.multiselect("Filter Periode", periode_list, default=periode_list)
        df_filtered = df[df["PERIODE"].isin(periode_selected)]

        # === Rata-rata semua data ===
        st.subheader("📈 Rata-rata SLA (hari)")
        avg_sla = df_filtered[[c for c in df_filtered.columns if c.endswith("_days")]].mean().round(2)
        st.dataframe(avg_sla.reset_index().rename(columns={"index": "Proses", 0: "Rata-rata (hari)"}))

        # === Rekap per Jenis Transaksi ===
        st.subheader("📌 Rekap per Jenis Transaksi")
        rekap_jenis = df_filtered.groupby("JENIS TRANSAKSI")[[c for c in df_filtered.columns if c.endswith("_days")]].mean().round(2)
        st.dataframe(rekap_jenis)

        # === Rekap per Vendor ===
        st.subheader("🏢 Rekap per Vendor")
        rekap_vendor = df_filtered.groupby("NAMA VENDOR")[[c for c in df_filtered.columns if c.endswith("_days")]].mean().round(2)
        st.dataframe(rekap_vendor)

        # Download rekap
        output = pd.ExcelWriter("rekap_sla.xlsx", engine="xlsxwriter")
        avg_sla.to_frame("Rata-rata (hari)").to_excel(output, sheet_name="Rata-rata SLA")
        rekap_jenis.to_excel(output, sheet_name="Rekap Jenis Transaksi")
        rekap_vendor.to_excel(output, sheet_name="Rekap Vendor")
        output.close()

        with open("rekap_sla.xlsx", "rb") as f:
            st.download_button("💾 Download Rekap SLA", f, file_name="rekap_sla.xlsx")

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")

import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")

st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

# Fungsi parsing SLA string → hari (float)
def parse_sla_to_days(s):
    if pd.isna(s):
        return None
    if isinstance(s, (int, float)):
        return s
    s = str(s).strip()
    s = s.replace("TOTAL", "").replace("SLA", "").strip()
    pattern = r"(?:(\d+)\s*days?)?\s*(\d+):(\d+):(\d+)"
    match = re.search(pattern, s)
    if match:
        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0)
        minutes = int(match.group(3) or 0)
        seconds = int(match.group(4) or 0)
        return days + hours / 24 + minutes / 1440 + seconds / 86400
    return None

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Bersihkan nama kolom
    df.columns = df.columns.astype(str).str.strip()

    # Filter periode
    if "PERIODE" in df.columns:
        periode_list = sorted(df["PERIODE"].dropna().astype(str).unique())
        selected_periode = st.sidebar.multiselect("Filter Periode", periode_list, default=periode_list)
        df["PERIODE"] = df["PERIODE"].astype(str)
        df = df[df["PERIODE"].isin(selected_periode)]
    else:
        st.error("Kolom 'PERIODE' tidak ditemukan di file.")
        st.stop()

    # Kolom SLA
    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    for col in sla_cols:
        if col in df.columns:
            df[col + " (hari)"] = df[col].apply(parse_sla_to_days)

    # Rata-rata SLA per proses
    avg_sla = df[[c + " (hari)" for c in sla_cols if c in df.columns]].mean().reset_index()
    avg_sla.columns = ["Proses", "Rata-rata (hari)"]

    # Rekap per jenis transaksi
    if "JENIS TRANSAKSI" in df.columns:
        rekap_jenis = df.groupby("JENIS TRANSAKSI")[[c + " (hari)" for c in sla_cols if c in df.columns]].mean().reset_index()
    else:
        rekap_jenis = pd.DataFrame()

    # Rekap per vendor
    if "NAMA VENDOR" in df.columns:
        rekap_vendor = df.groupby("NAMA VENDOR")[[c + " (hari)" for c in sla_cols if c in df.columns]].mean().reset_index()
    else:
        rekap_vendor = pd.DataFrame()

    st.subheader("📈 Rata-rata SLA (hari)")
    st.dataframe(avg_sla, use_container_width=True)

    st.subheader("📌 Rekap per Jenis Transaksi")
    st.dataframe(rekap_jenis, use_container_width=True)

    st.subheader("🏢 Rekap per Vendor")
    st.dataframe(rekap_vendor, use_container_width=True)

    # Download hasil olahan
    with pd.ExcelWriter("hasil_sla.xlsx") as writer:
        avg_sla.to_excel(writer, sheet_name="Rata-rata SLA", index=False)
        rekap_jenis.to_excel(writer, sheet_name="Rekap Jenis", index=False)
        rekap_vendor.to_excel(writer, sheet_name="Rekap Vendor", index=False)

    with open("hasil_sla.xlsx", "rb") as f:
        st.download_button("💾 Download Hasil Rekap", f, file_name="hasil_sla.xlsx")

import streamlit as st
import pandas as pd
import re
import math
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

# ================== Fungsi =====================
def parse_sla(s):
    if pd.isna(s):
        return None
    s = str(s).upper().replace("SLA", "").strip()
    days, hours, minutes, seconds = 0, 0, 0, 0
    day_match = re.search(r'(\d+)\s*DAY', s)
    if day_match:
        days = int(day_match.group(1))
    time_match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        if time_match.group(3):
            seconds = int(time_match.group(3))
    return days*86400 + hours*3600 + minutes*60 + seconds

def seconds_to_sla_format(total_seconds):
    if total_seconds is None or (isinstance(total_seconds, float) and math.isnan(total_seconds)):
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

# ================== Upload File =====================
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file, header=[0,1])
    df_raw.columns = [f"{col0}_{col1}" if "SLA" in str(col0).upper() else col0 for col0,col1 in df_raw.columns]
    rename_map = {"SLA_FUNGSIONAL":"FUNGSIONAL","SLA_VENDOR":"VENDOR","SLA_KEUANGAN":"KEUANGAN","SLA_PERBENDAHARAAN":"PERBENDAHARAAN","SLA_TOTAL WAKTU":"TOTAL WAKTU"}
    df_raw.rename(columns=rename_map, inplace=True)

    # Cari kolom periode
    periode_col = None
    for col in df_raw.columns:
        if "PERIODE" in str(col).upper():
            periode_col = col
            break
    if not periode_col:
        st.error("Kolom PERIODE tidak ditemukan.")
        st.stop()

    sla_cols = [c for c in ["FUNGSIONAL","VENDOR","KEUANGAN","PERBENDAHARAAN","TOTAL WAKTU"] if c in df_raw.columns]
    for col in sla_cols:
        df_raw[col] = df_raw[col].apply(parse_sla)

    # Filter Periode
    periode_list = sorted(df_raw[periode_col].dropna().unique())
    st.sidebar.subheader("Filter Rentang Periode")
    start_periode = st.sidebar.selectbox("Periode Mulai", periode_list, index=0)
    end_periode = st.sidebar.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)

    idx_start, idx_end = periode_list.index(start_periode), periode_list.index(end_periode)
    if idx_start > idx_end:
        st.error("Periode Mulai harus sebelum Periode Akhir.")
        st.stop()

    selected_periode = periode_list[idx_start:idx_end+1]
    df_filtered = df_raw[df_raw[periode_col].isin(selected_periode)]

    st.write(f"Menampilkan data periode dari **{start_periode}** sampai **{end_periode}**, total baris: {len(df_filtered)}")

    # Filter Vendor
    if "NAMA VENDOR" in df_filtered.columns:
        vendor_list = sorted(df_filtered["NAMA VENDOR"].dropna().unique())
        selected_vendors = st.sidebar.multiselect("Pilih Vendor", vendor_list, default=vendor_list)
        df_filtered = df_filtered[df_filtered["NAMA VENDOR"].isin(selected_vendors)]

    # ================== Rata-rata SLA per Proses =====================
    st.subheader("📌 Rata-rata SLA per Proses")
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

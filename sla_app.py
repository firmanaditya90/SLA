import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="📊 SLA Payment Analyzer", layout="wide")

# ---------------- Fungsi Konversi ---------------- #
def parse_sla_to_seconds(s):
    """Konversi format SLA menjadi total detik"""
    if pd.isna(s):
        return None
    
    # Timedelta (Excel biasanya baca ini kalau format [hh]:mm:ss)
    if isinstance(s, pd.Timedelta):
        return int(s.total_seconds())
    
    # Timestamp (datetime)
    if isinstance(s, pd.Timestamp):
        return s.hour * 3600 + s.minute * 60 + s.second
    
    # Angka (mungkin jumlah hari)
    if isinstance(s, (int, float)):
        return int(s * 86400)
    
    # String → parsing manual
    s = str(s).replace("SLA", "").strip()
    days, hours, minutes, seconds = 0, 0, 0, 0
    
    # Cari "X days"
    match = re.search(r"(\d+)\s+day", s)
    if match:
        days = int(match.group(1))
    
    # Cari "HH:MM:SS"
    time_match = re.search(r"(\d+):(\d+):(\d+)", s)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        seconds = int(time_match.group(3))
    
    return days * 86400 + hours * 3600 + minutes * 60 + seconds

def seconds_to_dhms(seconds):
    """Ubah detik → X hari X jam X menit X detik"""
    if pd.isna(seconds) or seconds is None:
        return "-"
    seconds = int(seconds)
    days = seconds // 86400
    seconds %= 86400
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f"{days} hari {hours} jam {minutes} menit {seconds} detik"

# ---------------- UI ---------------- #
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Baca file dengan header di baris kedua (index 1)
        df = pd.read_excel(uploaded_file, header=1)
        
        # Tampilkan kolom yang terdeteksi
        st.subheader("📄 Kolom yang terdeteksi di file")
        st.write(list(df.columns))
        
        # Pastikan nama kolom
        expected_cols = ["PERIODE", "NO PERMOHONAN", "JENIS TRANSAKSI", "NAMA VENDOR", 
                         "FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
        
        for col in expected_cols:
            if col not in df.columns:
                st.warning(f"Kolom '{col}' tidak ditemukan di file.")
        
        # Filter periode
        periode_list = sorted(df["PERIODE"].dropna().unique().tolist())
        selected_periode = st.selectbox("Filter Periode", periode_list)
        df_filtered = df[df["PERIODE"] == selected_periode]
        
        # Konversi SLA ke detik
        sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
        for col in sla_cols:
            if col in df_filtered.columns:
                df_filtered[col + "_SEC"] = df_filtered[col].apply(parse_sla_to_seconds)
        
        # Rata-rata SLA tiap proses
        st.subheader("📊 Rata-rata SLA per Proses")
        avg_sla = {}
        for col in sla_cols:
            if col in df_filtered.columns:
                avg_val = df_filtered[col + "_SEC"].mean()
                avg_sla[col] = seconds_to_dhms(avg_val)
        st.write(avg_sla)
        
        # Rata-rata per jenis transaksi
        st.subheader("📈 Rata-rata SLA per Jenis Transaksi")
        group_trans = df_filtered.groupby("JENIS TRANSAKSI")[[c + "_SEC" for c in sla_cols]].mean().reset_index()
        for col in sla_cols:
            if col in group_trans.columns:
                group_trans[col + "_FORMATTED"] = group_trans[col + "_SEC"].apply(seconds_to_dhms)
        st.dataframe(group_trans[["JENIS TRANSAKSI"] + [c + "_FORMATTED" for c in sla_cols]])
        
        # Rata-rata per vendor
        st.subheader("🏢 Rata-rata SLA per Vendor")
        group_vendor = df_filtered.groupby("NAMA VENDOR")[[c + "_SEC" for c in sla_cols]].mean().reset_index()
        for col in sla_cols:
            if col in group_vendor.columns:
                group_vendor[col + "_FORMATTED"] = group_vendor[col + "_SEC"].apply(seconds_to_dhms)
        st.dataframe(group_vendor[["NAMA VENDOR"] + [c + "_FORMATTED" for c in sla_cols]])
    
    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")

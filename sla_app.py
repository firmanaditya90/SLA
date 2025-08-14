import streamlit as st
import pandas as pd
import re
import math
import matplotlib.pyplot as plt

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

def parse_sla(s):
    if pd.isna(s):
        return None
    s = str(s).upper().replace("SLA", "").strip()
    days = hours = minutes = seconds = 0
    day_match = re.search(r'(\d+)\s*DAY', s)
    if day_match:
        days = int(day_match.group(1))
    time_match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        if time_match.group(3):
            seconds = int(time_match.group(3))
    return days * 86400 + hours * 3600 + minutes * 60 + seconds

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

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file, header=[0,1])
    df_raw.columns = [
        f"{col0}_{col1}" if "SLA" in str(col0).upper() else col0
        for col0, col1 in df_raw.columns
    ]
    rename_map = {
        "SLA_FUNGSIONAL": "FUNGSIONAL",
        "SLA_VENDOR": "VENDOR",
        "SLA_KEUANGAN": "KEUANGAN",
        "SLA_PERBENDAHARAAN": "PERBENDAHARAAN",
        "SLA_TOTAL WAKTU": "TOTAL WAKTU"
    }
    df_raw.rename(columns=rename_map, inplace=True)

    st.subheader("📄 Kolom yang terdeteksi di file")
    st.write(list(df_raw.columns))

    periode_col = next((col for col in df_raw.columns if "PERIODE" in str(col).upper()), None)
    if not periode_col:
        st.error("Kolom PERIODE tidak ditemukan.")
        st.stop()

    sla_cols = ["FUNGSIONAL","VENDOR","KEUANGAN","PERBENDAHARAAN","TOTAL WAKTU"]
    for col in sla_cols:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(parse_sla)

    # Konversi PERIODE ke datetime jika memungkinkan
    try:
        df_raw['PERIODE_DATETIME'] = pd.to_datetime(df_raw[periode_col], errors='coerce')
    except:
        df_raw['PERIODE_DATETIME'] = None

    st.sidebar.subheader("Filter Rentang Periode")
    periode_list = df_raw[periode_col].dropna().astype(str).unique().tolist()
    start_periode = st.sidebar.selectbox("Periode Mulai", periode_list, index=0)
    end_periode = st.sidebar.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)

    try:
        idx_start = periode_list.index(start_periode)
        idx_end = periode_list.index(end_periode)
        if idx_start > idx_end:
            st.error("Periode Mulai harus sebelum Periode Akhir.")
            st.stop()
    except ValueError:
        st.error("Periode yang dipilih tidak valid.")
        st.stop()

    selected_periode = periode_list[idx_start:idx_end+1]
    df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)]
    st.write(f"Menampilkan data periode dari **{start_periode}** sampai **{end_periode}**, total baris: {len(df_filtered)}")

    available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]

    # Rata-rata SLA per Proses
    if available_sla_cols:
        st.subheader("📌 Rata-rata SLA per Proses")
        rata_proses_seconds = df_filtered[available_sla_cols].mean()
        rata_proses = rata_proses_seconds.reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (detik)"]
        rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(seconds_to_sla_format)
        st.dataframe(rata_proses[["Proses","Rata-rata SLA"]])

        proses_grafik_cols = [c for c in ["FUNGSIONAL","VENDOR","KEUANGAN","PERBENDAHARAAN"] if c in available_sla_cols]
        if proses_grafik_cols:
            fig2, ax2 = plt.subplots(figsize=(8,4))
            values_hari = [rata_proses_seconds[col]/86400 for col in proses_grafik_cols]
            ax2.bar(proses_grafik_cols, values_hari, color='skyblue')
            ax2.set_title("Rata-rata SLA per Proses (hari)")
            ax2.set_ylabel("Rata-rata SLA (hari)")
            ax2.set_xlabel("Proses")
            ax2.grid(axis='y', linestyle='--', alpha=0.7)
            st.pyplot(fig2)

    # Jumlah Transaksi per Periode
    st.subheader("📊 Jumlah Transaksi per Periode")
    def format_periode(p):
        if pd.isna(p):
            return ""
        if isinstance(p, pd.Timestamp):
            return p.strftime("%B %Y")
        try:
            return pd.to_datetime(p).strftime("%B %Y")
        except:
            return str(p)

    jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].apply(format_periode)).size().reset_index(name="Jumlah Transaksi")

    bulan_order = ["Januari","Februari","Maret","April","Mei","Juni","Juli","Agustus","September","Oktober","November","Desember"]
    def periode_key(p):
        try:
            bulan, tahun = p.split()
            return int(tahun), bulan_order.index(bulan)
        except:
            return (9999,99)

    jumlah_transaksi = jumlah_transaksi.sort_values(by=jumlah_transaksi[periode_col].apply(periode_key))
    total_row = pd.DataFrame({periode_col:["TOTAL"], "Jumlah Transaksi":[jumlah_transaksi["Jumlah Transaksi"].sum()]})
    jumlah_transaksi = pd.concat([jumlah_transaksi, total_row], ignore_index=True)
    st.dataframe(jumlah_transaksi.style.format({"Jumlah Transaksi":"{:,}"}).apply(lambda x: ['font-weight:bold' if x.name==len(jumlah_transaksi)-1 else '' for i in x], axis=1))

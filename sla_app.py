import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="📊 SLA Payment Analyzer", layout="wide")

st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

def parse_sla_to_seconds(s):
    """Konversi format SLA menjadi total detik"""
    if pd.isna(s):
        return None
    if isinstance(s, pd.Timedelta):
        return int(s.total_seconds())
    s = str(s).replace("SLA", "").strip()
    days, hours, minutes, seconds = 0, 0, 0, 0
    match = re.search(r"(\d+)\s+day", s)
    if match:
        days = int(match.group(1))
    time_match = re.search(r"(\d+):(\d+):(\d+)", s)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        seconds = int(time_match.group(3))
    return days * 86400 + hours * 3600 + minutes * 60 + seconds

def format_seconds(total_seconds):
    """Ubah total detik jadi format hari, jam, menit, detik"""
    if pd.isna(total_seconds):
        return None
    d = total_seconds // 86400
    h = (total_seconds % 86400) // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{d} hari {h} jam {m} menit {s} detik"

if uploaded_file:
    try:
        # Baca Excel dengan 2 baris header
        df_raw = pd.read_excel(uploaded_file, header=[0, 1])

        # Gabungkan header, pakai baris kedua kalau ada
        new_cols = []
        for col in df_raw.columns:
            if "Unnamed" in str(col[1]):
                new_cols.append(str(col[0]).strip().upper())
            else:
                new_cols.append(str(col[1]).strip().upper())
        df_raw.columns = new_cols

        sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
        periode_col = "PERIODE"
        jenis_col = "JENIS TRANSAKSI"
        vendor_col = "NAMA VENDOR"

        st.write("📄 Kolom yang terdeteksi di file")
        st.write(df_raw.columns.tolist())

        missing = [col for col in sla_cols if col not in df_raw.columns]
        if missing:
            st.error(f"Kolom SLA berikut tidak ditemukan: {missing}")
        else:
            # Konversi SLA ke detik & string
            for col in sla_cols:
                df_raw[col + "_SEC"] = df_raw[col].apply(parse_sla_to_seconds)
                df_raw[col + "_STR"] = df_raw[col + "_SEC"].apply(format_seconds)

            df_filtered = df_raw

            # Filter periode
            if periode_col in df_filtered.columns:
                periode_list = sorted(df_filtered[periode_col].dropna().unique().tolist())
                periode_selected = st.multiselect("Filter Periode", periode_list, default=periode_list)
                df_filtered = df_filtered[df_filtered[periode_col].isin(periode_selected)]

            # Filter jenis transaksi
            if jenis_col in df_filtered.columns:
                jenis_list = sorted(df_filtered[jenis_col].dropna().unique().tolist())
                jenis_selected = st.multiselect("Filter Jenis Transaksi", jenis_list, default=jenis_list)
                df_filtered = df_filtered[df_filtered[jenis_col].isin(jenis_selected)]

            # Filter vendor
            if vendor_col in df_filtered.columns:
                vendor_list = sorted(df_filtered[vendor_col].dropna().unique().tolist())
                vendor_selected = st.multiselect("Filter Vendor", vendor_list, default=vendor_list)
                df_filtered = df_filtered[df_filtered[vendor_col].isin(vendor_selected)]

            # Hitung rata-rata SLA
            avg_sla = {col: df_filtered[col + "_SEC"].mean() for col in sla_cols}
            avg_sla_formatted = {col: format_seconds(v) for col, v in avg_sla.items()}

            st.subheader("📊 Rata-rata SLA per Proses")
            st.table(pd.DataFrame.from_dict(avg_sla_formatted, orient="index", columns=["Rata-rata"]))

            # Rekap per jenis transaksi
            if jenis_col in df_filtered.columns:
                st.subheader("📑 Rata-rata SLA per Jenis Transaksi")
                jenis_group = df_filtered.groupby(jenis_col)[[c + "_SEC" for c in sla_cols]].mean().reset_index()
                for col in sla_cols:
                    jenis_group[col] = jenis_group[col + "_SEC"].apply(format_seconds)
                st.dataframe(jenis_group[[jenis_col] + sla_cols])

            # Rekap per vendor
            if vendor_col in df_filtered.columns:
                st.subheader("🏢 Rata-rata SLA per Vendor")
                vendor_group = df_filtered.groupby(vendor_col)[[c + "_SEC" for c in sla_cols]].mean().reset_index()
                for col in sla_cols:
                    vendor_group[col] = vendor_group[col + "_SEC"].apply(format_seconds)
                st.dataframe(vendor_group[[vendor_col] + sla_cols])

            st.subheader("📋 Data SLA (Format waktu lengkap)")
            st.dataframe(df_filtered[[periode_col, jenis_col, vendor_col] + [c + "_STR" for c in sla_cols]])

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")

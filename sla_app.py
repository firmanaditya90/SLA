import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="📊 SLA Payment Analyzer", layout="wide")

# ---------------- Fungsi Konversi ---------------- #
def parse_sla_to_seconds(s):
    """Konversi SLA (timedelta, datetime, string) menjadi total detik"""
    if pd.isna(s):
        return None
    if isinstance(s, pd.Timedelta):
        return int(s.total_seconds())
    if isinstance(s, pd.Timestamp):
        return s.hour * 3600 + s.minute * 60 + s.second
    if isinstance(s, (int, float)):
        return int(s * 86400)
    s = str(s).strip()
    # format "xx days HH:MM:SS"
    match = re.search(r"(\d+)\s+day", s)
    days = int(match.group(1)) if match else 0
    time_match = re.search(r"(\d+):(\d+):(\d+)", s)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        seconds = int(time_match.group(3))
    else:
        hours = minutes = seconds = 0
    return days * 86400 + hours * 3600 + minutes * 60 + seconds

def seconds_to_dhms(seconds):
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
        # Baca tanpa header
        raw_df = pd.read_excel(uploaded_file, header=None)

        # Gabungkan dua baris pertama jadi header
        header_row1 = raw_df.iloc[0].fillna("")
        header_row2 = raw_df.iloc[1].fillna("")
        new_header = []
        for h1, h2 in zip(header_row1, header_row2):
            if h1 and h2:
                new_header.append(str(h2).strip())
            elif h1 and not h2:
                new_header.append(str(h1).strip())
            elif not h1 and h2:
                new_header.append(str(h2).strip())
            else:
                new_header.append("")

        # Data mulai dari baris ke-3 (index 2)
        df = raw_df[2:].copy()
        df.columns = new_header

        st.subheader("📄 Kolom yang terdeteksi di file")
        st.write(list(df.columns))

        expected_cols = ["PERIODE", "NO PERMOHONAN", "JENIS TRANSAKSI", "NAMA VENDOR",
                         "FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
        missing = [c for c in expected_cols if c not in df.columns]
        if missing:
            st.warning(f"Kolom berikut tidak ditemukan: {missing}")

        if "PERIODE" not in df.columns:
            st.stop()

        periode_list = sorted(df["PERIODE"].dropna().unique().tolist())
        selected_periode = st.selectbox("Filter Periode", periode_list)
        df_filtered = df[df["PERIODE"] == selected_periode].copy()

        sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
        for col in sla_cols:
            if col in df_filtered.columns:
                df_filtered[col + "_SEC"] = df_filtered[col].apply(parse_sla_to_seconds)

        # ---------------- Rata-rata SLA per Proses ----------------
        st.subheader("📊 Rata-rata SLA per Proses")
        avg_sla = {col: seconds_to_dhms(df_filtered[col + "_SEC"].mean())
                   for col in sla_cols if col in df_filtered.columns}
        st.write(avg_sla)

        # ---------------- Rata-rata SLA per Jenis Transaksi ----------------
        if "JENIS TRANSAKSI" in df_filtered.columns:
            st.subheader("📈 Rata-rata SLA per Jenis Transaksi")
            group_trans = df_filtered.groupby("JENIS TRANSAKSI")[[c + "_SEC" for c in sla_cols if c in df_filtered.columns]].mean().reset_index()
            for col in sla_cols:
                if col in df_filtered.columns:
                    group_trans[col] = group_trans[col + "_SEC"].apply(seconds_to_dhms)
            st.dataframe(group_trans[["JENIS TRANSAKSI"] + [c for c in sla_cols if c in df_filtered.columns]])

        # ---------------- Rata-rata SLA per Vendor ----------------
        if "NAMA VENDOR" in df_filtered.columns:
            st.subheader("🏢 Rata-rata SLA per Vendor")
            group_vendor = df_filtered.groupby("NAMA VENDOR")[[c + "_SEC" for c in sla_cols if c in df_filtered.columns]].mean().reset_index()
            for col in sla_cols:
                if col in df_filtered.columns:
                    group_vendor[col] = group_vendor[col + "_SEC"].apply(seconds_to_dhms)
            st.dataframe(group_vendor[["NAMA VENDOR"] + [c for c in sla_cols if c in df_filtered.columns]])

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")

import streamlit as st
import pandas as pd
import re
import math
import plotly.express as px
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA .xlsx untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

# --- Fungsi Parsing SLA ---
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
    total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total_seconds

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
    if days > 0: parts.append(f"{days} hari")
    if hours > 0 or days > 0: parts.append(f"{hours} jam")
    if minutes > 0 or hours > 0 or days > 0: parts.append(f"{minutes} menit")
    parts.append(f"{seconds} detik")
    return " ".join(parts)

# --- Proses Upload File ---
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file, header=[0, 1])
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

    periode_col = next((col for col in df_raw.columns if "PERIODE" in str(col).upper()), None)
    if not periode_col:
        st.error("Kolom PERIODE tidak ditemukan.")
        st.stop()

    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    for col in sla_cols:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(parse_sla)

    # --- Sidebar Filter ---
    st.sidebar.header("Filter Data")
    periode_list = list(dict.fromkeys(df_raw[periode_col].dropna().astype(str)))
    start_periode = st.sidebar.selectbox("Periode Mulai", periode_list, index=0)
    end_periode = st.sidebar.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)

    idx_start = periode_list.index(start_periode)
    idx_end = periode_list.index(end_periode)
    if idx_start > idx_end:
        st.error("Periode Mulai harus sebelum Periode Akhir.")
        st.stop()
    selected_periode = periode_list[idx_start:idx_end+1]
    df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)]

    if "NAMA VENDOR" in df_filtered.columns:
        vendor_list = sorted(df_filtered["NAMA VENDOR"].dropna().unique())
        selected_vendors = st.sidebar.multiselect("Pilih Vendor", vendor_list, default=vendor_list)
        df_filtered = df_filtered[df_filtered["NAMA VENDOR"].isin(selected_vendors)]

    st.write(f"Menampilkan data periode dari **{start_periode}** sampai **{end_periode}**, total baris: {len(df_filtered)}")
    available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]

    # --- KPI Metric Cards ---
    st.subheader("📊 Rata-rata SLA per Proses")
    if available_sla_cols:
        rata_proses_seconds = df_filtered[available_sla_cols].mean()
        col1, col2, col3, col4, col5 = st.columns(len(available_sla_cols))
        for i, col_name in enumerate(available_sla_cols):
            col_avg = seconds_to_sla_format(rata_proses_seconds[col_name])
            eval(f"col{i+1}.metric('{col_name}', '{col_avg}')")

    # --- Trend SLA per Periode (Plotly Interaktif) ---
    st.subheader("📈 Trend Rata-rata SLA per Periode")
    trend = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()
    trend_display = trend.copy()
    for col in available_sla_cols:
        trend_display[col] = trend_display[col].apply(seconds_to_sla_format)

    st.dataframe(trend_display[[periode_col]+available_sla_cols])

    # Grafik interaktif
    if "TOTAL WAKTU" in available_sla_cols:
        fig = px.line(trend, x=periode_col, y="TOTAL WAKTU", markers=True,
                      labels={"TOTAL WAKTU":"Rata-rata SLA (detik)"},
                      title="Trend SLA TOTAL WAKTU per Periode")
        st.plotly_chart(fig, use_container_width=True)

    # --- Rata-rata SLA per Vendor ---
    if "NAMA VENDOR" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Vendor")
        rata_vendor = df_filtered.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index()
        for col in available_sla_cols:
            rata_vendor[col] = rata_vendor[col].apply(seconds_to_sla_format)
        st.dataframe(rata_vendor)

    # --- Jumlah Transaksi per Periode ---
    if "JENIS TRANSAKSI" in df_filtered.columns:
        st.subheader("📊 Jumlah Transaksi per Periode")
        jumlah_trx = df_filtered.groupby(df_filtered[periode_col].astype(str))["JENIS TRANSAKSI"].count().reset_index()
        jumlah_trx.columns = [periode_col, "Jumlah Transaksi"]
        st.dataframe(jumlah_trx)
        fig_trx = px.bar(jumlah_trx, x=periode_col, y="Jumlah Transaksi", text="Jumlah Transaksi",
                         labels={"Jumlah Transaksi":"Jumlah Transaksi"}, title="Jumlah Transaksi per Periode")
        st.plotly_chart(fig_trx, use_container_width=True)

    # --- Tombol Download ---
    # Excel
    towrite = BytesIO()
    df_filtered.to_excel(towrite, index=False)
    towrite.seek(0)
    st.download_button("⬇️ Download Excel", data=towrite, file_name="SLA_Report.xlsx")

    # PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "SLA Report", ln=1, align="C")
    for i, row in df_filtered.iterrows():
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, str(row.to_dict()))
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name="SLA_Report.pdf")

else:
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

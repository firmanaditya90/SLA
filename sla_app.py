import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import calendar

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

def parse_sla(s):
    """Konversi SLA string menjadi jumlah detik"""
    if pd.isna(s):
        return None
    s = str(s).replace("SLA", "").strip()
    days = hours = minutes = seconds = 0
    parts = s.split()
    if "days" in parts:
        days = int(parts[parts.index("days") - 1])
    elif "day" in parts:
        days = int(parts[parts.index("day") - 1])
    if ":" in parts[-1]:
        t = parts[-1].split(":")
        hours = int(t[0])
        minutes = int(t[1])
    return days*86400 + hours*3600 + minutes*60  # total detik

def format_sla_seconds(sec):
    if pd.isna(sec):
        return "-"
    days, remainder = divmod(int(sec), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} hari {hours} jam {minutes} menit {seconds} detik"

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

    st.subheader("📄 Kolom yang terdeteksi di file")
    st.write(list(df_raw.columns))

    periode_col = next((col for col in df_raw.columns if "PERIODE" in str(col).upper()), None)
    if not periode_col:
        st.error("Kolom PERIODE tidak ditemukan.")
        st.stop()

    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    for col in sla_cols:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(parse_sla)

    # Filter Periode
    periode_list = sorted(df_raw[periode_col].astype(str).dropna().unique().tolist())
    periode_filter = st.multiselect("Filter Periode", periode_list, default=periode_list)
    df_filtered = df_raw[df_raw[periode_col].astype(str).isin(periode_filter)]

    # Filter Vendor
    if "NAMA VENDOR" in df_filtered.columns:
        vendor_list = sorted(df_filtered["NAMA VENDOR"].dropna().unique())
        vendor_filter = st.multiselect("Filter Vendor", vendor_list, default=vendor_list)
        df_filtered = df_filtered[df_filtered["NAMA VENDOR"].isin(vendor_filter)]

    # Rata-rata SLA per Proses
    available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]
    if available_sla_cols:
        st.subheader("📌 Rata-rata SLA per Proses")
        rata_proses = df_filtered[available_sla_cols].mean().reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (detik)"]
        rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(format_sla_seconds)
        st.dataframe(rata_proses[["Proses", "Rata-rata SLA"]])

    # Rata-rata SLA per Jenis Transaksi
    if "JENIS TRANSAKSI" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
        rata_transaksi = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols].agg(['mean', 'count'])
        rata_transaksi = rata_transaksi.reset_index()
        for col in available_sla_cols:
            rata_transaksi[(col, 'mean')] = rata_transaksi[(col, 'mean')].apply(format_sla_seconds)
        st.dataframe(rata_transaksi)

    # Rata-rata SLA per Vendor
    if "NAMA VENDOR" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Vendor")
        rata_vendor = df_filtered.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index()
        for col in available_sla_cols:
            rata_vendor[col] = rata_vendor[col].apply(format_sla_seconds)
        st.dataframe(rata_vendor)

    # Grafik trend SLA per Proses (hari)
    if periode_filter and available_sla_cols:
        st.subheader("📈 Trend Rata-rata SLA per Proses (hari)")

        # Konversi PERIODE ke datetime untuk sorting kronologis
        def periode_to_date(p):
            try:
                bulan_str, tahun = p.split()
                bulan_num = list(calendar.month_name).index(bulan_str)
                return pd.Timestamp(year=int(tahun), month=bulan_num, day=1)
            except:
                return pd.NaT

        df_filtered['PERIODE_DT'] = df_filtered[periode_col].astype(str).apply(periode_to_date)
        df_filtered = df_filtered.dropna(subset=['PERIODE_DT'])

        trend = df_filtered.groupby('PERIODE_DT')[available_sla_cols].mean().reset_index()
        trend = trend.sort_values('PERIODE_DT')

        fig, axs = plt.subplots(len(available_sla_cols), 1, figsize=(10, 4*len(available_sla_cols)))
        if len(available_sla_cols) == 1:
            axs = [axs]
        for i, col in enumerate(available_sla_cols):
            axs[i].plot(trend['PERIODE_DT'], trend[col]/86400, marker='o', color='skyblue')
            axs[i].set_title(col)
            axs[i].set_ylabel("Hari")
            axs[i].set_xlabel("Periode")
            axs[i].grid(True, linestyle='--', alpha=0.7)
            for label in axs[i].get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')
        st.pyplot(fig)

    # Jumlah transaksi per periode (urut kronologis)
    if "JENIS TRANSAKSI" in df_filtered.columns:
        st.subheader("📊 Jumlah Transaksi per Periode")
        jumlah_trx = df_filtered.groupby('PERIODE_DT')["JENIS TRANSAKSI"].count().reset_index()
        jumlah_trx = jumlah_trx.sort_values('PERIODE_DT')
        jumlah_trx[periode_col] = jumlah_trx['PERIODE_DT'].dt.strftime('%B %Y')
        jumlah_trx = jumlah_trx[[periode_col, 'JENIS TRANSAKSI']]
        jumlah_trx.columns = [periode_col, "Jumlah Transaksi"]
        st.dataframe(jumlah_trx)

        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.bar(jumlah_trx[periode_col], jumlah_trx["Jumlah Transaksi"], color='#2ca02c')
        ax2.set_title("Jumlah Transaksi per Periode")
        ax2.set_xlabel("Periode")
        ax2.set_ylabel("Jumlah Transaksi")
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        for label in ax2.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        st.pyplot(fig2)

else:
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

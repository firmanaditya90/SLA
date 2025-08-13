import streamlit as st
import pandas as pd
import re
import math
import matplotlib.pyplot as plt

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide")
st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA .xlsx untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type="xlsx")

def parse_sla(s):
    if pd.isna(s):
        return None
    s = str(s).upper().replace("SLA", "").strip()
    days = 0
    hours = 0
    minutes = 0
    seconds = 0
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
    if days > 0:
        parts.append(f"{days} hari")
    if hours > 0 or days > 0:
        parts.append(f"{hours} jam")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes} menit")
    parts.append(f"{seconds} detik")
    return " ".join(parts)

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

    periode_col = None
    for col in df_raw.columns:
        if "PERIODE" in str(col).upper():
            periode_col = col
            break
    if not periode_col:
        st.error("Kolom PERIODE tidak ditemukan.")
        st.stop()

    sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    for col in sla_cols:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(parse_sla)

    periode_list = list(dict.fromkeys(df_raw[periode_col].dropna().astype(str)))

    st.subheader("Filter Rentang Periode (berdasarkan urutan)")
    start_periode = st.selectbox("Periode Mulai", periode_list, index=0)
    end_periode = st.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)

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
        st.subheader("📌 Rata-rata SLA per Proses (format hari jam menit detik)")
        rata_proses_seconds = df_filtered[available_sla_cols].mean()
        rata_proses = rata_proses_seconds.reset_index()
        rata_proses.columns = ["Proses", "Rata-rata (detik)"]
        rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(seconds_to_sla_format)
        st.dataframe(rata_proses[["Proses", "Rata-rata SLA"]])

        # Grafik rata-rata SLA per proses (kecuali TOTAL WAKTU)
        proses_grafik_cols = [c for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"] if c in available_sla_cols]
        if proses_grafik_cols:
            fig2, ax2 = plt.subplots(figsize=(8, 4))
            values_hari = [rata_proses_seconds[col] / 86400 for col in proses_grafik_cols]
            ax2.bar(proses_grafik_cols, values_hari, color='skyblue')
            ax2.set_title("Rata-rata SLA per Proses (hari)")
            ax2.set_ylabel("Rata-rata SLA (hari)")
            ax2.set_xlabel("Proses")
            ax2.grid(axis='y', linestyle='--', alpha=0.7)
            st.pyplot(fig2)

    # Rata-rata SLA per Jenis Transaksi
    if "JENIS TRANSAKSI" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Jenis Transaksi (dengan jumlah transaksi)")
        transaksi_group = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols].agg(['mean','count']).reset_index()
        transaksi_display = pd.DataFrame()
        transaksi_display["JENIS TRANSAKSI"] = transaksi_group["JENIS TRANSAKSI"]
        for col in available_sla_cols:
            transaksi_display[f"{col} (Rata-rata)"] = transaksi_group[(col,'mean')].apply(seconds_to_sla_format)
            transaksi_display[f"{col} (Jumlah)"] = transaksi_group[(col,'count')]
        st.dataframe(transaksi_display)

    # Filter nama vendor
    if "NAMA VENDOR" in df_filtered.columns:
        st.subheader("📌 Rata-rata SLA per Vendor")
        vendor_list = sorted(df_filtered["NAMA VENDOR"].dropna().unique())
        selected_vendors = st.multiselect("Pilih Vendor", vendor_list, default=vendor_list)
        df_vendor_filtered = df_filtered[df_filtered["NAMA VENDOR"].isin(selected_vendors)]
        if not df_vendor_filtered.empty:
            rata_vendor = df_vendor_filtered.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index()
            for col in available_sla_cols:
                rata_vendor[col] = rata_vendor[col].apply(seconds_to_sla_format)
            st.dataframe(rata_vendor)
        else:
            st.info("Tidak ada data untuk vendor yang dipilih.")

    # Trend Rata-rata SLA per Periode
    st.subheader("📈 Trend Rata-rata SLA per Periode")
    trend = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()
    trend["PERIODE_SORTED"] = pd.Categorical(trend[periode_col], categories=selected_periode, ordered=True)
    trend = trend.sort_values("PERIODE_SORTED")
    trend_display = trend.copy()
    for col in available_sla_cols:
        trend_display[col] = trend_display[col].apply(seconds_to_sla_format)
    st.dataframe(trend_display[[periode_col] + available_sla_cols])

    # Grafik trend SLA TOTAL WAKTU dalam satuan hari
    if "TOTAL WAKTU" in available_sla_cols:
        fig, ax = plt.subplots(figsize=(10, 5))
        y_values_days = trend["TOTAL WAKTU"].apply(lambda x: x/86400)
        ax.plot(trend[periode_col], y_values_days, marker='o', label="TOTAL WAKTU", color='#9467bd')
        ax.set_title("Trend Rata-rata SLA TOTAL WAKTU per Periode")
        ax.set_xlabel("Periode")
        ax.set_ylabel("Rata-rata SLA (hari)")
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        st.pyplot(fig)

    # Grafik trend SLA per proses (kecuali TOTAL WAKTU)
    if proses_grafik_cols:
        fig3, axs = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
        fig3.suptitle("Trend Rata-rata SLA per Proses per Periode (hari)", fontsize=16)
        axs = axs.flatten()
        for i, col in enumerate(proses_grafik_cols):
            y_vals = trend[col]/86400
            axs[i].plot(trend[periode_col], y_vals, marker='o', color='skyblue')
            axs[i].set_title(col)
            axs[i].set_ylabel("Hari")
            axs[i].set_xlabel("Periode")
            axs[i].grid(True, linestyle='--', alpha=0.7)
            for label in axs[i].get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')
        st.pyplot(fig3)

    # Jumlah transaksi per periode
    if "JENIS TRANSAKSI" in df_filtered.columns:
        st.subheader("📊 Jumlah Transaksi per Periode")
        jumlah_trx = df_filtered.groupby(df_filtered[periode_col].astype(str))["JENIS TRANSAKSI"].count().reset_index()
        jumlah_trx.columns = [periode_col, "Jumlah Transaksi"]
        st.dataframe(jumlah_trx)

        fig4, ax4 = plt.subplots(figsize=(10, 4))
        ax4.bar(jumlah_trx[periode_col], jumlah_trx["Jumlah Transaksi"], color='#2ca02c')
        ax4.set_title("Jumlah Transaksi per Periode")
        ax4.set_xlabel("Periode")
        ax4.set_ylabel("Jumlah Transaksi")
        ax4.grid(axis='y', linestyle='--', alpha=0.7)
        for label in ax4.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        st.pyplot(fig4)

else:
    st.info("Silakan upload file Excel SLA terlebih dahulu.")

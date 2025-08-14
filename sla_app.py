import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime

st.set_page_config(page_title="SLA Dashboard", layout="wide")

# ======= Helper Function =======
def seconds_to_sla_format(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{int(days)} hari {int(hours)} jam {int(minutes)} menit {int(secs)} detik"

# ======= Data Load =======
@st.cache_data
def load_data():
    # Ganti path atau cara load sesuai kebutuhan
    df = pd.read_excel("data_sla.xlsx")
    return df

df = load_data()

# ======= Sidebar Filters =======
with st.sidebar:
    st.header("Filter Data")
    periode_min = st.date_input("Periode Mulai", min(df['TANGGAL']))
    periode_max = st.date_input("Periode Akhir", max(df['TANGGAL']))
    vendor_list = ["Semua"] + df['VENDOR'].unique().tolist()
    vendor_selected = st.selectbox("Pilih Vendor", vendor_list)

# ======= Filter Data =======
df_filtered = df[(df['TANGGAL'] >= pd.to_datetime(periode_min)) & (df['TANGGAL'] <= pd.to_datetime(periode_max))]
if vendor_selected != "Semua":
    df_filtered = df_filtered[df_filtered['VENDOR'] == vendor_selected]

# ======= Jumlah Transaksi Per Periode =======
st.subheader("📊 Jumlah Transaksi per Periode")
jumlah_transaksi = df_filtered.groupby(df_filtered['PERIODE'].astype(str)).size().reset_index(name="JUMLAH")
jumlah_transaksi = jumlah_transaksi.sort_values("PERIODE")

# Tambahkan total
total = pd.DataFrame([["TOTAL", jumlah_transaksi["JUMLAH"].sum()]], columns=jumlah_transaksi.columns)
jumlah_transaksi = pd.concat([jumlah_transaksi, total], ignore_index=True)

# Highlight total
def highlight_total(row):
    if row["PERIODE"] == "TOTAL":
        return ['font-weight: bold']*len(row)
    return ['']*len(row)

st.dataframe(jumlah_transaksi.style.apply(highlight_total, axis=1))

# ======= SLA Rata-rata Per Periode =======
st.subheader("📊 Rata-rata SLA per Periode")
available_sla_cols = [col for col in df.columns if "SLA" in col]
periode_col = "PERIODE"

# Trend numeric untuk grafik
trend_numeric = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()
trend_numeric["PERIODE_SORTED"] = pd.Categorical(trend_numeric[periode_col], categories=sorted(trend_numeric[periode_col].unique()), ordered=True)
trend_numeric = trend_numeric.sort_values("PERIODE_SORTED")

# Trend display untuk tabel
trend_display = trend_numeric.copy()
for col in available_sla_cols:
    trend_display[col] = trend_display[col].apply(seconds_to_sla_format)

st.dataframe(trend_display[[periode_col] + available_sla_cols])

# ======= Grafik TOTAL WAKTU =======
if "TOTAL WAKTU" in available_sla_cols:
    fig, ax = plt.subplots(figsize=(10, 5))
    y_values_days = trend_numeric["TOTAL WAKTU"] / 86400  # detik -> hari
    ax.plot(trend_numeric[periode_col], y_values_days, marker='o', label="TOTAL WAKTU", color='#9467bd')
    ax.set_title("Trend Rata-rata SLA TOTAL WAKTU per Periode")
    ax.set_xlabel("Periode")
    ax.set_ylabel("Rata-rata SLA (hari)")
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend()
    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_ha('right')
    st.pyplot(fig)

# ======= Grafik trend per proses (kecuali TOTAL WAKTU) =======
proses_grafik_cols = [col for col in available_sla_cols if col != "TOTAL WAKTU"]
if proses_grafik_cols:
    fig3, axs = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
    fig3.suptitle("Trend Rata-rata SLA per Proses per Periode (hari)", fontsize=16)
    axs = axs.flatten()
    for i, col in enumerate(proses_grafik_cols):
        axs[i].plot(trend_numeric[periode_col], trend_numeric[col]/86400, marker='o', color='skyblue')
        axs[i].set_title(col)
        axs[i].set_ylabel("Hari")
        axs[i].set_xlabel("Periode")
        axs[i].grid(True, linestyle='--', alpha=0.7)
        for label in axs[i].get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
    st.pyplot(fig3)

import streamlit as st
import pandas as pd

st.set_page_config(page_title="📊 SLA Payment Analyzer", layout="wide")

st.title("📊 SLA Payment Analyzer")
st.write("Upload file SLA `.xlsx` untuk menghitung rata-rata SLA per proses, per jenis transaksi, dan per vendor.")

uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

def seconds_to_hms(seconds):
    """Konversi detik ke format xx hari xx jam xx menit xx detik"""
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, sec = divmod(remainder, 60)
    return f"{days} hari {hours} jam {minutes} menit {sec} detik"

if uploaded_file:
    try:
        # Baca semua data tanpa header
        raw_df = pd.read_excel(uploaded_file, header=None)
        
        # Ambil header dari baris ke-2 (index 1) -> bisa disesuaikan
        header_row = raw_df.iloc[1].tolist()
        df = pd.read_excel(uploaded_file, header=1)
        
        # Pastikan semua kolom unnamed diganti
        df.columns = [str(col).strip() for col in header_row]
        
        # Jika ada kolom SLA yang dobel -> ganti sesuai urutan
        sla_labels = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
        for i, col in enumerate(df.columns):
            if col.upper() == "SLA" and i - 4 < len(sla_labels) and i >= 4:
                df.rename(columns={col: sla_labels[i - 4]}, inplace=True)
        
        st.write("📄 Kolom yang terdeteksi di file")
        st.write(list(df.columns))
        
        required_cols = ["PERIODE", "NO PERMOHONAN", "JENIS TRANSAKSI", "NAMA VENDOR",
                         "FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Kolom berikut tidak ditemukan di file: {', '.join(missing_cols)}")
        else:
            # Pastikan semua SLA jadi numeric (detik)
            for col in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]:
                df[col] = pd.to_timedelta(df[col], errors='coerce').dt.total_seconds()
            
            # Filter periode
            periode_list = sorted(df["PERIODE"].dropna().unique().tolist())
            periode_filter = st.selectbox("Filter Periode", periode_list)
            filtered_df = df[df["PERIODE"] == periode_filter]
            
            # Rata-rata SLA per proses
            st.subheader("📌 Rata-rata SLA per Proses")
            avg_per_proses = filtered_df[["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]].mean()
            avg_per_proses_fmt = avg_per_proses.apply(seconds_to_hms)
            st.dataframe(avg_per_proses_fmt.reset_index().rename(columns={"index": "Proses", 0: "Rata-rata SLA"}))
            
            # Rata-rata SLA per Jenis Transaksi
            st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
            avg_per_jenis = filtered_df.groupby("JENIS TRANSAKSI")[
                ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
            ].mean().applymap(seconds_to_hms)
            st.dataframe(avg_per_jenis)
            
            # Rata-rata SLA per Vendor
            st.subheader("📌 Rata-rata SLA per Vendor")
            avg_per_vendor = filtered_df.groupby("NAMA VENDOR")[
                ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
            ].mean().applymap(seconds_to_hms)
            st.dataframe(avg_per_vendor)

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")

# app.py
import os
import re
import math
import base64
import time
import pandas as pd
import streamlit as st
import plotly.express as px

# ==============================
# Konfigurasi Halaman
# ==============================
st.set_page_config(page_title="SLA Payment Analyzer", layout="wide", page_icon="🚀")

# ------------------------------
# THEME TIP (opsional, buat file .streamlit/config.toml):
# [theme]
# base="dark"
# primaryColor="#00BFFF"
# backgroundColor="#0E1117"
# secondaryBackgroundColor="#1B1F24"
# textColor="#E6E6E6"
# font="sans serif"
# ------------------------------

# ==============================
# Util: GIF loader
# ==============================
def load_gif_b64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            data = f.read()
        return f"data:image/gif;base64,{base64.b64encode(data).decode('utf-8')}"
    except Exception:
        return None

# ==============================
# Util: SLA parse & format
# ==============================
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

# ==============================
# Path Data & Assets
# ==============================
os.makedirs("data", exist_ok=True)
os.makedirs("assets", exist_ok=True)  # taruh assets/rocket.gif kalau mau
EXCEL_PATH = os.path.join("data", "last_data.xlsx")
PARQUET_PATH = os.path.join("data", "last_data.parquet")
ROCKET_GIF = os.path.join("assets", "rocket.gif")

# ==============================
# Admin Auth (secrets/env)
# ==============================
try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)
except Exception:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", None)

st.sidebar.markdown("### 🔐 Admin")
pwd_input = st.sidebar.text_input("Password admin (untuk upload)", type="password")
is_admin = bool(ADMIN_PASSWORD) and (pwd_input == ADMIN_PASSWORD)
if not ADMIN_PASSWORD:
    st.sidebar.info("Admin password belum dikonfigurasi (Secrets/ENV). Mode publik aktif.")

# ==============================
# Cache: IO Helpers
# ==============================
@st.cache_data(show_spinner=False)
def load_parquet(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)

@st.cache_data(show_spinner=False)
def load_excel_flatten(path: str) -> pd.DataFrame:
    # Baca Excel (multiheader) lalu flatten
    df = pd.read_excel(path, engine="openpyxl", header=[0, 1])
    df.columns = ["_".join([str(c) for c in col if str(c) != 'nan']) for col in df.columns]
    return df

@st.cache_data(show_spinner=False)
def flatten_df(df_multi: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df_multi.columns, pd.MultiIndex):
        df_multi = df_multi.copy()
        df_multi.columns = ["_".join([str(c) for c in col if str(c) != 'nan']) for col in df_multi.columns]
    return df_multi

# ==============================
# Header Hero Section
# ==============================
st.markdown(
    """
    <div style="text-align:center; margin-bottom: 0.75rem;">
        <h1 style="margin:0;">🚀 SLA Payment Analyzer</h1>
        <p style="opacity:0.85; margin:0;">Dashboard modern untuk memantau dan menganalisis SLA dokumen penagihan</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ==============================
# Upload (Admin Only)
# ==============================
with st.sidebar.expander("📤 Upload Data (Admin Only)", expanded=is_admin):
    if is_admin:
        up = st.file_uploader("Upload Excel (.xlsx)", type="xlsx")
        if up is not None:
            # Tampilkan animasi saat proses simpan
            with st.spinner("🚀 Mengunggah & memproses data..."):
                # Baca lalu flatten agar aman
                df_new = pd.read_excel(up, engine="openpyxl", header=[0, 1])
                df_new = flatten_df(df_new)

                # Simpan ke Excel & Parquet (Parquet sebagai sumber baca utama)
                df_new.to_excel(EXCEL_PATH, index=False)
                df_new.to_parquet(PARQUET_PATH, index=False)

                # Clear cache agar langsung pakai data baru
                st.cache_data.clear()
                st.success("✅ Data berhasil diupload & disimpan.")
                st.toast("Data terbaru sudah aktif.", icon="✅")
    else:
        st.caption("Masukkan password di atas untuk mengaktifkan upload.")

# ==============================
# Membaca Data (dengan animasi roket)
# ==============================
rocket_b64 = load_gif_b64(ROCKET_GIF)

with st.spinner("🔄 Menyiapkan data & komponen dashboard..."):
    # Tampilkan animasi roket saat load
    if rocket_b64:
        st.markdown(
            f'<div style="text-align:center; margin: 6px 0 12px 0;"><img src="{rocket_b64}" width="140"/></div>',
            unsafe_allow_html=True
        )
    else:
        st.caption("💡 Tip: tambahkan assets/rocket.gif untuk animasi loading yang lebih kece.")

    # Simulasi efek loading kecil (opsional, bisa dihapus)
    time.sleep(0.3)

# Urutan baca: Parquet (cepat) -> Excel (jika Parquet belum ada)
df_raw = None
if os.path.exists(PARQUET_PATH):
    df_raw = load_parquet(PARQUET_PATH)
elif os.path.exists(EXCEL_PATH):
    df_raw = load_excel_flatten(EXCEL_PATH)

if df_raw is None or df_raw.empty:
    st.warning("⚠️ Belum ada data yang dapat ditampilkan. Admin perlu upload file terlebih dahulu.")
    st.stop()

# ==============================
# Deteksi & Normalisasi Kolom
# ==============================
# Peta rename jika ada pola SLA_* seperti data lama
rename_map = {
    "SLA_FUNGSIONAL": "FUNGSIONAL",
    "SLA_VENDOR": "VENDOR",
    "SLA_KEUANGAN": "KEUANGAN",
    "SLA_PERBENDAHARAAN": "PERBENDAHARAAN",
    "SLA_TOTAL WAKTU": "TOTAL WAKTU"
}
df_raw = df_raw.rename(columns={k: v for k, v in rename_map.items() if k in df_raw.columns})

periode_col = next((c for c in df_raw.columns if "PERIODE" in str(c).upper()), None)
if not periode_col:
    st.error("Kolom PERIODE tidak ditemukan pada dataset.")
    st.stop()

# ==============================
# Sidebar: Filter Periode
# ==============================
st.sidebar.markdown("### 📅 Filter Periode")
periode_list = (
    df_raw[periode_col]
    .dropna()
    .astype(str)
    .drop_duplicates()
    .tolist()
)

# Sort periode secara kronologis jika format memungkinkan
try:
    periode_list_sorted = sorted(periode_list, key=lambda x: pd.to_datetime(x, errors="coerce"))
except Exception:
    periode_list_sorted = sorted(periode_list)

start_periode = st.sidebar.selectbox("Periode Mulai", periode_list_sorted, index=0)
end_periode = st.sidebar.selectbox("Periode Akhir", periode_list_sorted, index=len(periode_list_sorted) - 1)

try:
    i0 = periode_list_sorted.index(start_periode)
    i1 = periode_list_sorted.index(end_periode)
except Exception:
    st.error("Nilai periode tidak valid.")
    st.stop()

if i0 > i1:
    st.error("Periode Mulai harus <= Periode Akhir.")
    st.stop()

selected_periode = set(periode_list_sorted[i0:i1+1])
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)].copy()

# ==============================
# Parse SLA (setelah filter untuk hemat waktu)
# ==============================
sla_cols_candidates = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
available_sla_cols = [c for c in sla_cols_candidates if c in df_filtered.columns]

for col in available_sla_cols:
    df_filtered[col] = df_filtered[col].apply(parse_sla)

# ==============================
# HERO METRICS (Cards)
# ==============================
st.markdown("---")
st.markdown("#### 📈 Ringkasan")
colA, colB, colC, colD = st.columns(4)

total_rows = len(df_filtered)
colA.metric("Jumlah Transaksi", f"{total_rows:,}")

if "TOTAL WAKTU" in available_sla_cols and total_rows > 0:
    avg_total_sec = float(df_filtered["TOTAL WAKTU"].mean())
    colB.metric("Rata-rata TOTAL WAKTU", seconds_to_sla_format(avg_total_sec))
else:
    colB.metric("Rata-rata TOTAL WAKTU", "-")

# Cari proses tercepat (mean SLA terkecil)
fastest_label = "-"
fastest_value = None
for c in [x for x in available_sla_cols if x != "TOTAL WAKTU"]:
    val = df_filtered[c].mean()
    if val is not None and not math.isnan(val):
        if fastest_value is None or val < fastest_value:
            fastest_value = val
            fastest_label = c
colC.metric("Proses Tercepat", fastest_label if fastest_value is not None else "-")

# Rasio baris valid periode (sekadar contoh indikator kualitas data)
valid_periode_ratio = (df_filtered[periode_col].notna().mean() * 100.0) if total_rows > 0 else 0.0
colD.metric("Kualitas Periode (Valid)", f"{valid_periode_ratio:.1f}%")

# ==============================
# Data Preview
# ==============================
with st.expander("📄 Lihat Sampel Data (50 baris pertama)", expanded=False):
    st.dataframe(df_filtered.head(50), use_container_width=True)

# ==============================
# Rata-rata SLA per Proses (tabel + bar chart)
# ==============================
if available_sla_cols:
    st.markdown("### 🧮 Rata-rata SLA per Proses")
    mean_series = df_filtered[available_sla_cols].mean()
    mean_df = mean_series.reset_index()
    mean_df.columns = ["Proses", "Rata-rata (detik)"]
    mean_df["Rata-rata (format)"] = mean_df["Rata-rata (detik)"].apply(seconds_to_sla_format)

    st.dataframe(mean_df[["Proses", "Rata-rata (format)"]], use_container_width=True)

    fig_bar = px.bar(
        mean_df[mean_df["Proses"] != "TOTAL WAKTU"],
        x="Proses",
        y="Rata-rata (detik)",
        title="Rata-rata SLA per Proses (detik)",
        text="Rata-rata (detik)",
    )
    fig_bar.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    fig_bar.update_layout(yaxis_title="Detik", xaxis_title="", uniformtext_minsize=10, uniformtext_mode="hide")
    st.plotly_chart(fig_bar, use_container_width=True)

# ==============================
# Rata-rata SLA per Jenis Transaksi
# ==============================
if "JENIS TRANSAKSI" in df_filtered.columns and available_sla_cols:
    st.markdown("### 🧾 Rata-rata SLA per Jenis Transaksi")
    grp = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols].agg(["mean", "count"]).reset_index()
    disp = pd.DataFrame({"JENIS TRANSAKSI": grp["JENIS TRANSAKSI"]})
    for c in available_sla_cols:
        disp[f"{c} (Rata-rata)"] = grp[(c, "mean")].apply(seconds_to_sla_format)
        disp[f"{c} (Jumlah)"] = grp[(c, "count")]
    st.dataframe(disp, use_container_width=True)

# ==============================
# Filter Vendor & SLA per Vendor
# ==============================
if "NAMA VENDOR" in df_filtered.columns and available_sla_cols:
    st.markdown("### 🏷️ Rata-rata SLA per Vendor")
    vendor_list = sorted([v for v in df_filtered["NAMA VENDOR"].dropna().unique().tolist()])
    chosen = st.multiselect("Pilih Vendor", ["ALL"] + vendor_list, default=["ALL"])
    if "ALL" in chosen or not chosen:
        dfv = df_filtered.copy()
    else:
        dfv = df_filtered[df_filtered["NAMA VENDOR"].isin(chosen)]

    if len(dfv) > 0:
        rv = dfv.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index()
        for c in available_sla_cols:
            rv[c] = rv[c].apply(seconds_to_sla_format)
        st.dataframe(rv, use_container_width=True)
    else:
        st.info("Tidak ada data untuk vendor yang dipilih.")

# ==============================
# Trend SLA per Periode (Line)
# ==============================
if available_sla_cols:
    st.markdown("### 📈 Trend SLA per Periode")
    trend = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()

    # Plot TOTAL WAKTU bila ada
    if "TOTAL WAKTU" in available_sla_cols and not trend.empty:
        trend_days = trend.copy()
        trend_days["TOTAL WAKTU (hari)"] = trend_days["TOTAL WAKTU"] / 86400.0
        fig_line = px.line(
            trend_days,
            x=trend_days.columns[0],
            y="TOTAL WAKTU (hari)",
            markers=True,
            title="Trend Rata-rata SLA TOTAL WAKTU per Periode (hari)",
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # Multi-line proses per komponen (kecuali total)
    proses_cols = [c for c in available_sla_cols if c != "TOTAL WAKTU"]
    if proses_cols:
        long_df = trend.melt(id_vars=[trend.columns[0]], value_vars=proses_cols,
                             var_name="Proses", value_name="Detik")
        long_df["Hari"] = long_df["Detik"] / 86400.0
        fig_multi = px.line(long_df, x=trend.columns[0], y="Hari", color="Proses", markers=True,
                            title="Trend Rata-rata SLA per Proses (hari)")
        st.plotly_chart(fig_multi, use_container_width=True)

# ==============================
# Jumlah Transaksi per Periode
# ==============================
st.markdown("### 📊 Jumlah Transaksi per Periode")
jumlah = (
    df_filtered.groupby(df_filtered[periode_col].astype(str))
    .size()
    .reset_index(name="Jumlah")
)
st.dataframe(jumlah, use_container_width=True)
fig_cnt = px.bar(jumlah, x=periode_col, y="Jumlah", text="Jumlah", title="Jumlah Transaksi per Periode")
fig_cnt.update_traces(textposition="outside")
st.plotly_chart(fig_cnt, use_container_width=True)

# ==============================
# Download Dataset Terfilter
# ==============================
st.markdown("### ⬇️ Unduh Data Terfilter")
csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv_bytes, file_name="sla_filtered.csv", mime="text/csv")

# ==============================
# Admin Tools (reset)
# ==============================
with st.sidebar.expander("🛠️ Admin Tools", expanded=False):
    if is_admin:
        if st.button("🗑️ Reset Data (hapus data terakhir)"):
            try:
                if os.path.exists(PARQUET_PATH): os.remove(PARQUET_PATH)
                if os.path.exists(EXCEL_PATH): os.remove(EXCEL_PATH)
                st.cache_data.clear()
                st.success("Data dihapus. Muat ulang halaman.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Gagal menghapus data: {e}")
    else:
        st.caption("Login admin untuk mengakses tools ini.")

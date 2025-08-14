# app.py
import os
import time
import base64
import re
import math
import json
import tempfile

import pandas as pd
import streamlit as st

# plotting libs
try:
    import plotly.express as px
    _HAS_PLOTLY = True
except Exception:
    import matplotlib.pyplot as plt
    _HAS_PLOTLY = False

# Lottie support
try:
    from streamlit_lottie import st_lottie
    _HAS_LOTTIE = True
except Exception:
    _HAS_LOTTIE = False

# ==============================
# Page config & minimal CSS
# ==============================
st.set_page_config(page_title="🚀 SLA Payment Analyzer", layout="wide", page_icon="🚀")
st.markdown(
    """
    <style>
      /* Hero style */
      .hero { text-align:center; margin-bottom: 8px; }
      .hero h1 { 
        margin:0; 
        font-weight:800; 
        background: linear-gradient(90deg,#00BFFF 0%, #7F7FD5 50%, #86A8E7 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      }
      .card { background: rgba(255,255,255,0.03); border-radius:12px; padding:12px; border:1px solid rgba(255,255,255,0.04); }
      .small { font-size:12px; opacity:0.85; }
      hr.soft { border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent); margin: 10px 0 14px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="hero"><h1>🚀 SLA Payment Analyzer</h1><p class="small">Dashboard modern untuk memantau & menganalisis SLA dokumen penagihan</p></div>', unsafe_allow_html=True)

# ==============================
# Paths & assets
# ==============================
os.makedirs("data", exist_ok=True)
os.makedirs("assets", exist_ok=True)
EXCEL_PATH = os.path.join("data", "last_data.xlsx")
PARQUET_PATH = os.path.join("data", "last_data.parquet")
ROCKET_GIF_PATH = os.path.join("assets", "rocket.gif")  # optional fallback GIF
LOTTIE_URL = "https://assets3.lottiefiles.com/packages/lf20_jtkhrafb.json"  # public rocket Lottie

# ==============================
# Admin password (secrets -> env fallback)
# ==============================
try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)
except Exception:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", None)

st.sidebar.markdown("### 🔐 Admin")
if ADMIN_PASSWORD:
    pwd = st.sidebar.text_input("Password admin (untuk upload/reset)", type="password")
    is_admin = bool(pwd and pwd == ADMIN_PASSWORD)
    if is_admin:
        st.sidebar.success("Mode admin aktif")
else:
    st.sidebar.info("Admin password belum dikonfigurasi. App berjalan read-only.")
    is_admin = False

# ==============================
# utility: Lottie loader or GIF fallback
# ==============================
def load_lottie_from_url(url: str):
    """Try load Lottie JSON from URL (internet)."""
    try:
        import requests
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

def get_rocket_anim():
    # prefer local lottie file in assets/rocket.json
    local_json = os.path.join("assets", "rocket.json")
    if os.path.exists(local_json):
        try:
            with open(local_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # try to fetch Lottie URL if internet available and streamlit-lottie installed
    if _HAS_LOTTIE:
        l = load_lottie_from_url(LOTTIE_URL)
        return l
    # fallback: if local gif exists, return path for base64 display
    if os.path.exists(ROCKET_GIF_PATH):
        with open(ROCKET_GIF_PATH, "rb") as f:
            return "data:image/gif;base64," + base64.b64encode(f.read()).decode("utf-8")
    return None

rocket_anim = get_rocket_anim()

# ==============================
# SLA parse & formatter
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
# IO: cached loaders
# invalidate by file size+mtime
# ==============================
@st.cache_data
def read_parquet(path, size, mtime):
    return pd.read_parquet(path)

@st.cache_data
def read_excel_flat(path, size, mtime):
    # read with header multiindex then flatten columns
    df = pd.read_excel(path, engine="openpyxl", header=[0,1])
    # flatten multiindex into single names
    df.columns = ["_".join([str(c) for c in col if str(c) != 'nan']).strip() for col in df.columns]
    return df

def save_parquet_safe(df, path):
    # write to tmp then move to avoid partial writes
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".parquet")
    try:
        df.to_parquet(tmp.name, index=False)
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        try:
            tmp.close()
            os.unlink(tmp.name)
        except Exception:
            pass

# ==============================
# Upload (admin only)
# ==============================
with st.sidebar.expander("📤 Upload Data (Admin only)", expanded=is_admin):
    if is_admin:
        up = st.file_uploader("Upload Excel (.xlsx) — header multi (multi-row)", type="xlsx")
        if up is not None:
            # show rocket animation while saving
            with st.spinner("🚀 Mengunggah & memproses file..."):
                # read upload into df (handle multiindex)
                try:
                    df_new = pd.read_excel(up, engine="openpyxl", header=[0,1])
                    # flatten columns immediately so downstream is consistent
                    df_new.columns = ["_".join([str(c) for c in col if str(c) != 'nan']).strip() for col in df_new.columns]
                except Exception as e:
                    st.error(f"Gagal membaca file upload: {e}")
                    st.stop()
                # save excel (flattened), and save parquet
                try:
                    df_new.to_excel(EXCEL_PATH, index=False)
                except Exception:
                    # some runtimes may block writing excel; ignore but ensure parquet saved
                    pass
                try:
                    save_parquet_safe(df_new, PARQUET_PATH)
                except Exception as e:
                    st.warning(f"Gagal menyimpan Parquet: {e}")
                st.success("✅ Upload selesai. Data terbaru aktif.")
                # clear cache so subsequent reads use new file
                st.cache_data.clear()
                # optional celebratory effect
                try:
                    st.balloons()
                except Exception:
                    pass

# ==============================
# Load data (Parquet preferred)
# ==============================
if os.path.exists(PARQUET_PATH):
    st.info("Memuat data (parquet) — cepat.")
    stat = os.stat(PARQUET_PATH)
    with st.spinner("🚀 Menyiapkan data..."):
        # show rocket animation while loading
        if rocket_anim:
            if _HAS_LOTTIE and isinstance(rocket_anim, dict):
                st_lottie(rocket_anim, height=160, key="rocket1")
            elif isinstance(rocket_anim, str) and rocket_anim.startswith("data:image"):
                st.markdown(f'<div style="text-align:center;"><img src="{rocket_anim}" width="160" /></div>', unsafe_allow_html=True)
        df_raw = read_parquet(PARQUET_PATH, stat.st_size, stat.st_mtime)
elif os.path.exists(EXCEL_PATH):
    st.info("Memuat data (excel). Akan disimpan sebagai parquet otomatis untuk percepatan selanjutnya.")
    stat = os.stat(EXCEL_PATH)
    with st.spinner("🚀 Membaca file Excel..."):
        if rocket_anim:
            if _HAS_LOTTIE and isinstance(rocket_anim, dict):
                st_lottie(rocket_anim, height=160, key="rocket2")
            elif isinstance(rocket_anim, str) and rocket_anim.startswith("data:image"):
                st.markdown(f'<div style="text-align:center;"><img src="{rocket_anim}" width="160" /></div>', unsafe_allow_html=True)
        df_raw = read_excel_flat(EXCEL_PATH, stat.st_size, stat.st_mtime)
        # save parquet for faster future loads
        try:
            save_parquet_safe(df_raw, PARQUET_PATH)
        except Exception:
            pass
else:
    st.warning("Belum ada data. Admin perlu upload file.")
    st.stop()

# minimal sanity
if df_raw is None or df_raw.empty:
    st.warning("Data kosong atau gagal dimuat.")
    st.stop()

# ==============================
# normalize column names (legacy mapping)
# ==============================
# if columns like 'SLA' exist at first level we've flattened earlier; still keep mapping
rename_map = {
    "SLA_FUNGSIONAL": "FUNGSIONAL",
    "SLA_VENDOR": "VENDOR",
    "SLA_KEUANGAN": "KEUANGAN",
    "SLA_PERBENDAHARAAN": "PERBENDAHARAAN",
    "SLA_TOTAL WAKTU": "TOTAL WAKTU"
}
df_raw = df_raw.rename(columns={k: v for k, v in rename_map.items() if k in df_raw.columns})

# detect periode column
periode_col = next((c for c in df_raw.columns if "PERIODE" in str(c).upper()), None)
if not periode_col:
    st.error("Kolom PERIODE tidak ditemukan pada data.")
    st.stop()

# try datetime parse (non-fatal)
try:
    df_raw['PERIODE_DATETIME'] = pd.to_datetime(df_raw[periode_col], errors='coerce')
except Exception:
    df_raw['PERIODE_DATETIME'] = None

# ==============================
# Sidebar: periode filter (glass card effect)
# ==============================
with st.sidebar:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📅 Filter Rentang Periode")
    periode_list = df_raw[periode_col].dropna().astype(str).unique().tolist()
    # sort if possible chronologically
    try:
        periode_list = sorted(periode_list, key=lambda x: pd.to_datetime(x, errors='coerce'))
    except Exception:
        periode_list = sorted(periode_list)
    start_periode = st.selectbox("Periode Mulai", periode_list, index=0)
    end_periode = st.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)
    st.markdown('</div>', unsafe_allow_html=True)

# validate
try:
    idx0 = periode_list.index(start_periode)
    idx1 = periode_list.index(end_periode)
    if idx0 > idx1:
        st.error("Periode Mulai harus sebelum/atau sama dengan Periode Akhir.")
        st.stop()
except Exception:
    st.error("Periode tidak valid.")
    st.stop()

selected_periods = set(periode_list[idx0:idx1+1])
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periods)].copy()
st.markdown(f'<div class="small">Menampilkan periode <b>{start_periode}</b> sampai <b>{end_periode}</b> — total baris: <b>{len(df_filtered)}</b></div>', unsafe_allow_html=True)

# SLA columns to consider
sla_candidates = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
available_sla_cols = [c for c in sla_candidates if c in df_filtered.columns]
proses_grafik_cols = [c for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"] if c in available_sla_cols]

# ==============================
# parse SLA only after filtering (faster)
# ==============================
progress_placeholder = st.empty()
with st.spinner("⏱️ Memproses kolom SLA..."):
    # show small progress bar
    p = st.progress(0)
    for i, col in enumerate(available_sla_cols):
        df_filtered[col] = df_filtered[col].apply(parse_sla)
        p.progress(int((i+1)/max(1, len(available_sla_cols)) * 100))
    p.empty()
    progress_placeholder.empty()

# ==============================
# HERO metrics
# ==============================
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Jumlah Transaksi", f"{len(df_filtered):,}")
with col2:
    if "TOTAL WAKTU" in available_sla_cols and len(df_filtered)>0:
        avg_total = df_filtered["TOTAL WAKTU"].mean()
        st.metric("Rata-rata TOTAL WAKTU", seconds_to_sla_format(avg_total))
    else:
        st.metric("Rata-rata TOTAL WAKTU", "-")
with col3:
    fastest = "-"
    fastest_val = None
    for c in [x for x in available_sla_cols if x!="TOTAL WAKTU"]:
        val = df_filtered[c].mean()
        if pd.notna(val):
            if fastest_val is None or val < fastest_val:
                fastest_val = val; fastest = c
    st.metric("Proses Tercepat (mean)", fastest)
with col4:
    valid_pct = 100.0 * df_filtered[periode_col].notna().mean() if len(df_filtered)>0 else 0.0
    st.metric("Kualitas Periode (valid)", f"{valid_pct:.1f}%")

st.markdown("<hr class='soft'/>", unsafe_allow_html=True)

# ==============================
# Tabs (Overview, Per Proses, Jenis Transaksi, Vendor, Tren, Jumlah)
# ==============================
tabs = st.tabs(["🔍 Overview", "🧮 Per Proses", "🧾 Jenis Transaksi", "🏷️ Vendor", "📈 Tren", "📊 Jumlah Transaksi"])

# Overview
with tabs[0]:
    st.subheader("📄 Sampel Data (50 baris)")
    st.dataframe(df_filtered.head(50), use_container_width=True)
    st.markdown("### ⬇️ Unduh data terfilter")
    csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name="sla_filtered.csv", mime="text/csv")

# Per Proses
with tabs[1]:
    st.subheader("📌 Rata-rata SLA per Proses")
    if available_sla_cols:
        means = df_filtered[available_sla_cols].mean().rename("mean_seconds")
        mean_df = means.reset_index()
        mean_df.columns = ["Proses", "Rata-rata (detik)"]
        mean_df["Rata-rata (format)"] = mean_df["Rata-rata (detik)"].apply(seconds_to_sla_format)
        st.dataframe(mean_df[["Proses", "Rata-rata (format)"]], use_container_width=True)

        # interactive chart
        if _HAS_PLOTLY:
            fig = px.bar(mean_df[mean_df["Proses"]!="TOTAL WAKTU"], x="Proses", y="Rata-rata (detik)",
                         title="Rata-rata SLA per Proses (detik)", text="Rata-rata (detik)")
            fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
            fig.update_layout(yaxis_title="Detik", xaxis_title="", uniformtext_minsize=8)
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig, ax = plt.subplots(figsize=(8,4))
            vals = [means[c] for c in proses_grafik_cols]
            ax.bar(proses_grafik_cols, [v/86400 for v in vals], color='#75c8ff')
            ax.set_ylabel("Hari")
            ax.set_title("Rata-rata SLA per Proses (hari)")
            st.pyplot(fig)
    else:
        st.info("Tidak ada kolom SLA yang tersedia untuk ditampilkan.")

# Jenis Transaksi
with tabs[2]:
    st.subheader("📌 Rata-rata SLA per Jenis Transaksi")
    if "JENIS TRANSAKSI" in df_filtered.columns and available_sla_cols:
        grp = df_filtered.groupby("JENIS TRANSAKSI")[available_sla_cols].agg(['mean','count']).reset_index()
        disp = pd.DataFrame({"JENIS TRANSAKSI": grp["JENIS TRANSAKSI"]})
        for c in available_sla_cols:
            disp[f"{c} (Rata-rata)"] = grp[(c,'mean')].apply(seconds_to_sla_format)
            disp[f"{c} (Jumlah)"] = grp[(c,'count')]
        st.dataframe(disp, use_container_width=True)
    else:
        st.info("Kolom 'JENIS TRANSAKSI' tidak tersedia atau tidak ada kolom SLA.")

# Vendor
with tabs[3]:
    st.subheader("📌 Rata-rata SLA per Vendor")
    if "NAMA VENDOR" in df_filtered.columns and available_sla_cols:
        vendors = sorted(df_filtered["NAMA VENDOR"].dropna().unique())
        sel = st.multiselect("Pilih Vendor", ["ALL"]+vendors, default=["ALL"])
        if "ALL" in sel or not sel:
            dfv = df_filtered.copy()
        else:
            dfv = df_filtered[df_filtered["NAMA VENDOR"].isin(sel)]
        if len(dfv)>0:
            rv = dfv.groupby("NAMA VENDOR")[available_sla_cols].mean().reset_index()
            for c in available_sla_cols:
                rv[c] = rv[c].apply(seconds_to_sla_format)
            st.dataframe(rv, use_container_width=True)
        else:
            st.info("Tidak ada data untuk vendor yang dipilih.")
    else:
        st.info("Kolom 'NAMA VENDOR' tidak tersedia.")

# Tren
with tabs[4]:
    st.subheader("📈 Trend Rata-rata SLA per Periode")
    if available_sla_cols:
        trend = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()
        # order
        trend["PERIODE_SORTED"] = pd.Categorical(trend[periode_col], categories=list(selected_periods), ordered=True)
        trend = trend.sort_values("PERIODE_SORTED")
        st.dataframe(trend[[periode_col]+available_sla_cols], use_container_width=True)

        if "TOTAL WAKTU" in available_sla_cols:
            if _HAS_PLOTLY:
                tdf = trend.copy()
                tdf["TOTAL_WAKTU_days"] = tdf["TOTAL WAKTU"]/86400.0
                fig = px.line(tdf, x=periode_col, y="TOTAL_WAKTU_days", markers=True, title="Trend TOTAL WAKTU (hari)")
                fig.update_layout(yaxis_title="Hari", xaxis_title="Periode")
                st.plotly_chart(fig, use_container_width=True)
            else:
                fig, ax = plt.subplots(figsize=(10,5))
                ax.plot(trend[periode_col], trend["TOTAL WAKTU"]/86400.0, marker='o')
                ax.set_ylabel("Hari")
                ax.set_title("Trend TOTAL WAKTU (hari)")
                st.pyplot(fig)

        # multi-line per proses
        proc_cols = [c for c in available_sla_cols if c!="TOTAL WAKTU"]
        if proc_cols:
            if _HAS_PLOTLY:
                long = trend.melt(id_vars=[periode_col], value_vars=proc_cols, var_name="Proses", value_name="Detik")
                long["Hari"] = long["Detik"]/86400.0
                fig2 = px.line(long, x=periode_col, y="Hari", color="Proses", markers=True, title="Trend per Proses (hari)")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                fig, axs = plt.subplots(min(2, len(proc_cols)), 2, figsize=(14,6), constrained_layout=True)
                axs = axs.flatten()
                for i, c in enumerate(proc_cols):
                    axs[i].plot(trend[periode_col], trend[c]/86400.0, marker='o')
                    axs[i].set_title(c)
                st.pyplot(fig)
    else:
        st.info("Tidak ada kolom SLA untuk tren.")

# Jumlah
with tabs[5]:
    st.subheader("📊 Jumlah Transaksi per Periode")
    jumlah = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name="Jumlah")
    # order
    try:
        jumlah = jumlah.sort_values(by=periode_col, key=lambda x: pd.Categorical(x, categories=list(selected_periods), ordered=True))
    except Exception:
        pass
    total_row = pd.DataFrame({periode_col:["TOTAL"], "Jumlah":[jumlah["Jumlah"].sum()]})
    jumlah = pd.concat([jumlah, total_row], ignore_index=True)
    st.dataframe(jumlah, use_container_width=True)

    if _HAS_PLOTLY:
        fig = px.bar(jumlah[jumlah[periode_col]!="TOTAL"], x=periode_col, y="Jumlah", text="Jumlah", title="Jumlah Transaksi per Periode")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig, ax = plt.subplots(figsize=(10,5))
        ax.bar(jumlah[jumlah[periode_col]!="TOTAL"][periode_col], jumlah[jumlah[periode_col]!="TOTAL"]["Jumlah"])
        st.pyplot(fig)

# ==============================
# Admin reset (sidebar)
# ==============================
with st.sidebar.expander("🛠️ Admin Tools", expanded=False):
    if is_admin:
        if st.button("🗑️ Reset (hapus data terakhir)"):
            try:
                if os.path.exists(PARQUET_PATH):
                    os.remove(PARQUET_PATH)
                if os.path.exists(EXCEL_PATH):
                    os.remove(EXCEL_PATH)
                st.cache_data.clear()
                st.success("Data dihapus. Silakan muat ulang halaman.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Gagal menghapus data: {e}")
    else:
        st.write("Login admin untuk aksesoris.")

# ==============================
# Final tip
# ==============================
st.markdown("<hr class='soft'/>", unsafe_allow_html=True)
st.caption("Tip: untuk performa terbaik, upload file Excel sekali; app akan menyimpan versi Parquet yang dimuat jauh lebih cepat pada kunjungan berikutnya.")

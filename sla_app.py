# app.py
import os
import time
import base64
import re
import math
import tempfile

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="🚀 SLA Payment Analyzer", layout="wide", page_icon="🚀")

# -------------------------
# Minimal CSS (modern look)
# -------------------------
st.markdown(
    """
<style>
/* Hero gradient title */
.hero { text-align: center; padding: 12px 0 6px 0; }
.hero h1 { margin: 0;
  background: linear-gradient(90deg, #00BFFF 0%, #7F7FD5 50%, #86A8E7 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  font-weight: 800; letter-spacing: 0.5px; }
.hero p { opacity: 0.85; margin: 8px 0 0 0; }

/* Glass cards */
.card { background: rgba(255,255,255,0.06); border-radius: 12px;
       padding: 10px 12px; border:1px solid rgba(255,255,255,0.06); }
.kpi { display:flex; flex-direction:column; gap:6px; }
.kpi .label { font-size:12px; opacity:0.75; }
.kpi .value { font-size:20px; font-weight:700; }

.small { font-size:12px; opacity:0.75; }
hr.soft { border:none; height:1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent); margin:10px 0 14px 0; }

.sidebar-logo { display:flex; justify-content:center; margin-bottom:6px; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <h1>🚀 SLA Payment Analyzer</h1>
  <p>Dashboard modern untuk melihat & menganalisis SLA dokumen penagihan</p>
</div>
""",
    unsafe_allow_html=True,
)

# -------------------------
# Paths & assets
# -------------------------
os.makedirs("data", exist_ok=True)
os.makedirs("assets", exist_ok=True)
EXCEL_PATH = os.path.join("data", "last_data.xlsx")
PARQUET_PATH = os.path.join("data", "last_data.parquet")
ASDP_LOGO = os.path.join("assets", "asdp_logo.png")
ROCKET_GIF = os.path.join("assets", "rocket.gif")

# -------------------------
# Admin password (secrets or env)
# -------------------------
try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)
except Exception:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", None)

# -------------------------
# Sidebar: logo + admin panel
# -------------------------
with st.sidebar:
    # logo (fallback to text)
    if os.path.exists(ASDP_LOGO):
        with open(ASDP_LOGO, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(f'<div class="sidebar-logo"><img src="data:image/png;base64,{img_b64}" width="140"/></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="sidebar-logo"><b>PT. ASDP Indonesia Ferry (Persero)</b></div>', unsafe_allow_html=True)

    st.markdown("### 🔐 Admin")
    if ADMIN_PASSWORD:
        pwd = st.text_input("Password admin (untuk upload/reset)", type="password")
        is_admin = bool(pwd and pwd == ADMIN_PASSWORD)
        if is_admin:
            st.success("Mode admin aktif")
    else:
        st.info("Admin password belum dikonfigurasi. App berjalan read-only.")
        is_admin = False

# -------------------------
# Helpers: SLA parse & format
# -------------------------
def parse_sla(s):
    if pd.isna(s):
        return None
    s = str(s).upper().replace("SLA", "").strip()
    days = hours = minutes = seconds = 0
    m = re.search(r'(\d+)\s*DAY', s)
    if m:
        days = int(m.group(1))
    tm = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if tm:
        hours = int(tm.group(1))
        minutes = int(tm.group(2))
        if tm.group(3):
            seconds = int(tm.group(3))
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
    if days > 0: parts.append(f"{days} hari")
    if hours > 0 or days > 0: parts.append(f"{hours} jam")
    if minutes > 0 or hours > 0 or days > 0: parts.append(f"{minutes} menit")
    parts.append(f"{seconds} detik")
    return " ".join(parts)

# -------------------------
# IO helpers & caching
# -------------------------
@st.cache_data(show_spinner=False)
def read_parquet(path, size, mtime):
    return pd.read_parquet(path)

@st.cache_data(show_spinner=False)
def read_excel_multi_header(path, size, mtime):
    # read multi-row header (0,1) then flatten
    df = pd.read_excel(path, engine="openpyxl", header=[0,1])
    # flatten: join non-null parts
    df.columns = ["_".join([str(part).strip() for part in col if str(part) != 'nan']).strip() for col in df.columns]
    return df

def save_parquet_safe(df, path):
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

# -------------------------
# Upload area (admin-only)
# -------------------------
with st.sidebar.expander("📤 Upload Data (Admin Only)", expanded=is_admin):
    if is_admin:
        upload = st.file_uploader("Upload Excel (.xlsx) — header multi-row", type="xlsx")
        if upload is not None:
            try:
                df_new = pd.read_excel(upload, engine="openpyxl", header=[0,1])
                # flatten columns
                df_new.columns = ["_".join([str(part).strip() for part in col if str(part) != 'nan']).strip() for col in df_new.columns]
            except Exception as e:
                st.error(f"Gagal membaca file upload: {e}")
                upload = None
                df_new = None
            if df_new is not None:
                # save excel (flattened) and parquet
                os.makedirs("data", exist_ok=True)
                try:
                    df_new.to_excel(EXCEL_PATH, index=False)
                except Exception:
                    # some runtimes may not allow excel write; ignore
                    pass
                try:
                    save_parquet_safe(df_new, PARQUET_PATH)
                except Exception:
                    pass
                st.success("✅ Upload selesai — data terbaru aktif.")
                st.cache_data.clear()
                # small celebratory effect
                try:
                    st.balloons()
                except Exception:
                    pass

# -------------------------
# Rocket animation HTML (Lottie via web player) with take-off script
# -------------------------
def show_rocket_takeoff_html(duration: int = 2200):
    """
    Render a Lottie player that will play and then animate upward (take-off) then hide.
    duration in ms for how long to show before take-off begins.
    """
    # Lottie file (take-off style). If you prefer another Lottie URL, replace here.
    lottie_url = "https://assets5.lottiefiles.com/packages/lf20_jcikwtux.json"
    # If rocket gif exists, use it as fallback image (no JS animation)
    if os.path.exists(ROCKET_GIF):
        with open(ROCKET_GIF, "rb") as f:
            gif_b64 = base64.b64encode(f.read()).decode("utf-8")
        html = f"""
        <div id="rocket_wrap" style="display:flex;justify-content:center;">
          <img id="rocket_img" src="data:image/gif;base64,{gif_b64}" width="220"/>
        </div>
        <script>
        setTimeout(function(){{
            var el = document.getElementById('rocket_wrap');
            el.style.transition = 'transform 700ms ease-in, opacity 600ms';
            el.style.transform = 'translateY(-400px) scale(0.6)';
            el.style.opacity = '0';
            setTimeout(function(){{ el.remove(); }}, 800);
        }},{duration});
        </script>
        """
    else:
        html = f"""
        <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
        <div id="rocket_wrap" style="display:flex;justify-content:center;">
          <lottie-player id="rocket_lp"
            src="{lottie_url}"
            background="transparent"
            speed="1"
            style="width:220px; height:220px;"
            loop autoplay>
          </lottie-player>
        </div>
        <script>
        // after `duration` ms, animate upward (take-off) and then remove element
        setTimeout(function(){{
            const el = document.getElementById('rocket_wrap');
            if (!el) return;
            el.style.transition = 'transform 900ms cubic-bezier(.2,-0.5,.2,1), opacity 700ms';
            el.style.transform = 'translateY(-500px) scale(0.5)';
            el.style.opacity = '0';
            setTimeout(function(){{ el.remove(); }}, 900);
        }},{duration});
        </script>
        """
    st.components.v1.html(html, height=300)

# -------------------------
# Load data (prefer parquet for speed)
# -------------------------
df_raw = None
if os.path.exists(PARQUET_PATH):
    stat = os.stat(PARQUET_PATH)
    with st.spinner("🚀 Menyiapkan data (parquet)..."):
        # show rocket take-off once while loading
        show_rocket_takeoff_html(duration=1400)
        time.sleep(0.6)
        df_raw = read_parquet(PARQUET_PATH, stat.st_size, stat.st_mtime)
        st.success("✅ Data dimuat dari cache (parquet).")
elif os.path.exists(EXCEL_PATH):
    stat = os.stat(EXCEL_PATH)
    with st.spinner("🚀 Membaca file Excel — menyimpan cache..."):
        show_rocket_takeoff_html(duration=1400)
        time.sleep(0.6)
        df_raw = read_excel_multi_header(EXCEL_PATH, stat.st_size, stat.st_mtime)
        # try save parquet for next time
        try:
            save_parquet_safe(df_raw, PARQUET_PATH)
        except Exception:
            pass
        st.success("✅ Data Excel dimuat.")
else:
    st.warning("⚠️ Belum ada file yang diunggah. Admin dapat upload file di sidebar.")
    st.stop()

# sanity
if df_raw is None or df_raw.empty:
    st.warning("Data kosong atau gagal dimuat.")
    st.stop()

# -------------------------
# Normalize column names (map SLA_* to simpler)
# -------------------------
rename_map = {
    "SLA_FUNGSIONAL": "FUNGSIONAL",
    "SLA_VENDOR": "VENDOR",
    "SLA_KEUANGAN": "KEUANGAN",
    "SLA_PERBENDAHARAAN": "PERBENDAHARAAN",
    "SLA_TOTAL WAKTU": "TOTAL WAKTU"
}
df_raw = df_raw.rename(columns={k:v for k,v in rename_map.items() if k in df_raw.columns})

# detect periode column
periode_col = next((c for c in df_raw.columns if "PERIODE" in str(c).upper()), None)
if not periode_col:
    st.error("Kolom PERIODE tidak ditemukan pada data.")
    st.stop()

# try convert to datetime (non-fatal)
try:
    df_raw['PERIODE_DATETIME'] = pd.to_datetime(df_raw[periode_col], errors='coerce')
except Exception:
    df_raw['PERIODE_DATETIME'] = None

# -------------------------
# Sidebar: periode filter (glass card)
# -------------------------
with st.sidebar:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📅 Filter Rentang Periode")
    periode_list = df_raw[periode_col].dropna().astype(str).unique().tolist()
    try:
        periode_list = sorted(periode_list, key=lambda x: pd.to_datetime(x, errors='coerce'))
    except Exception:
        periode_list = sorted(periode_list)
    start_periode = st.selectbox("Periode Mulai", periode_list, index=0)
    end_periode = st.selectbox("Periode Akhir", periode_list, index=len(periode_list)-1)
    st.markdown('</div>', unsafe_allow_html=True)

    # Created by text placed under the filter
    st.markdown("---")
    st.markdown('<div style="text-align:center; font-size:12px; opacity:0.7;">Created by. <b>Firman Aditya</b></div>', unsafe_allow_html=True)

# validate
try:
    idx0 = periode_list.index(start_periode)
    idx1 = periode_list.index(end_periode)
    if idx0 > idx1:
        st.error("Periode Mulai harus sebelum Periode Akhir.")
        st.stop()
except Exception:
    st.error("Periode tidak valid.")
    st.stop()

selected_periods = periode_list[idx0:idx1+1]
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periods)].copy()
st.markdown(f'<div class="small">Menampilkan periode <b>{start_periode}</b> sampai <b>{end_periode}</b> — total baris: <b>{len(df_filtered)}</b></div>', unsafe_allow_html=True)

# determine available SLA cols
sla_candidates = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
available_sla_cols = [c for c in sla_candidates if c in df_filtered.columns]
proses_grafik_cols = [c for c in ["FUNGSIONAL","VENDOR","KEUANGAN","PERBENDAHARAAN"] if c in available_sla_cols]

# -------------------------
# parse SLA only after filtering (faster)
# -------------------------
with st.spinner("⏱️ Memproses kolom SLA ..."):
    for c in available_sla_cols:
        df_filtered[c] = df_filtered[c].apply(parse_sla)

# -------------------------
# KPI top
# -------------------------
st.markdown("---")
c1,c2,c3,c4 = st.columns(4)
with c1:
    st.markdown('<div class="card kpi"><div class="label">Jumlah Transaksi</div><div class="value">{:,}</div></div>'.format(len(df_filtered)), unsafe_allow_html=True)
with c2:
    if "TOTAL WAKTU" in available_sla_cols and len(df_filtered)>0:
        avg_total = df_filtered["TOTAL WAKTU"].mean()
        st.markdown(f'<div class="card kpi"><div class="label">Rata-rata TOTAL WAKTU</div><div class="value">{seconds_to_sla_format(avg_total)}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card kpi"><div class="label">Rata-rata TOTAL WAKTU</div><div class="value">-</div></div>', unsafe_allow_html=True)
with c3:
    fastest = "-"
    fastest_val = None
    for col in [x for x in available_sla_cols if x!="TOTAL WAKTU"]:
        v = df_filtered[col].mean()
        if pd.notna(v):
            if fastest_val is None or v < fastest_val:
                fastest_val = v; fastest = col
    st.markdown(f'<div class="card kpi"><div class="label">Proses Tercepat (mean)</div><div class="value">{fastest}</div></div>', unsafe_allow_html=True)
with c4:
    valid_pct = 100.0 * df_filtered[periode_col].notna().mean() if len(df_filtered)>0 else 0.0
    st.markdown(f'<div class="card kpi"><div class="label">Kualitas Periode (Valid)</div><div class="value">{valid_pct:.1f}%</div></div>', unsafe_allow_html=True)

st.markdown("<hr class='soft'/>", unsafe_allow_html=True)

# -------------------------
# Tabs with content
# -------------------------
tabs = st.tabs(["🔍 Overview","🧮 Per Proses","🧾 Jenis Transaksi","🏷️ Vendor","📈 Tren","📊 Jumlah Transaksi"])

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
        mean_df.columns = ["Proses","Rata-rata (detik)"]
        mean_df["Rata-rata (format)"] = mean_df["Rata-rata (detik)"].apply(seconds_to_sla_format)
        st.dataframe(mean_df[["Proses","Rata-rata (format)"]], use_container_width=True)

        # simple matplotlib bar (days)
        if proses_grafik_cols:
            fig, ax = plt.subplots(figsize=(8,4))
            vals = [means[c]/86400 for c in proses_grafik_cols]
            ax.bar(proses_grafik_cols, vals, color='#75c8ff')
            ax.set_ylabel("Hari")
            ax.set_title("Rata-rata SLA per Proses (hari)")
            st.pyplot(fig)
    else:
        st.info("Tidak ada kolom SLA untuk ditampilkan.")

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
        trend["PERIODE_SORTED"] = pd.Categorical(trend[periode_col], categories=selected_periods, ordered=True)
        trend = trend.sort_values("PERIODE_SORTED")
        st.dataframe(trend[[periode_col]+available_sla_cols], use_container_width=True)

        if "TOTAL WAKTU" in available_sla_cols:
            fig, ax = plt.subplots(figsize=(10,5))
            ax.plot(trend[periode_col], trend["TOTAL WAKTU"]/86400.0, marker='o', color='#9467bd')
            ax.set_ylabel("Hari")
            ax.set_title("Trend TOTAL WAKTU (hari)")
            for label in ax.get_xticklabels(): label.set_rotation(45); label.set_ha('right')
            st.pyplot(fig)

        proc_cols = [c for c in available_sla_cols if c!="TOTAL WAKTU"]
        if proc_cols:
            fig, axs = plt.subplots(min(2,len(proc_cols)), 2, figsize=(14,6), constrained_layout=True)
            axs = axs.flatten()
            for i,c in enumerate(proc_cols):
                axs[i].plot(trend[periode_col], trend[c]/86400.0, marker='o')
                axs[i].set_title(c)
                for label in axs[i].get_xticklabels(): label.set_rotation(45); label.set_ha('right')
            st.pyplot(fig)
    else:
        st.info("Tidak ada kolom SLA untuk tren.")

# Jumlah Transaksi
with tabs[5]:
    st.subheader("📊 Jumlah Transaksi per Periode")
    jumlah = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name="Jumlah")
    try:
        jumlah = jumlah.sort_values(by=periode_col, key=lambda x: pd.Categorical(x, categories=selected_periods, ordered=True))
    except Exception:
        pass
    total_row = pd.DataFrame({periode_col:["TOTAL"], "Jumlah":[jumlah["Jumlah"].sum()]})
    jumlah = pd.concat([jumlah, total_row], ignore_index=True)
    st.dataframe(jumlah, use_container_width=True)

    fig, ax = plt.subplots(figsize=(10,5))
    ax.bar(jumlah[jumlah[periode_col]!="TOTAL"][periode_col], jumlah[jumlah[periode_col]!="TOTAL"]["Jumlah"], color='#ff9f7f')
    for label in ax.get_xticklabels(): label.set_rotation(45); label.set_ha('right')
    ax.set_title("Jumlah Transaksi per Periode")
    st.pyplot(fig)

# -------------------------
# Admin tools: reset
# -------------------------
with st.sidebar.expander("🛠️ Admin Tools", expanded=False):
    if is_admin:
        if st.button("🗑️ Reset Data (hapus semua cache & file)"):
            try:
                if os.path.exists(PARQUET_PATH): os.remove(PARQUET_PATH)
                if os.path.exists(EXCEL_PATH): os.remove(EXCEL_PATH)
            except Exception:
                pass
            st.cache_data.clear()
            st.success("Data dihapus. Silakan muat ulang halaman.")
            st.experimental_rerun()
    else:
        st.write("Login admin untuk melihat tools.")

# -------------------------
# Footer / tip
# -------------------------
st.markdown("<hr class='soft'/>", unsafe_allow_html=True)
st.caption("Tip: upload file Excel satu kali — app akan menyimpan versi Parquet untuk memuat jauh lebih cepat di kunjungan berikutnya.")

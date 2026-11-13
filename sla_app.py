# -*- coding: utf-8 -*-
# =========================================
# app.py \u2014 SLA Payment Analyzer + Poster A4
# =========================================

import streamlit as st
import pandas as pd
import re
import math
import os
import time
import base64
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import requests
import json
import html as slae_html
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO   # << tambahkan ini
import base64
import streamlit.components.v1 as components
import hashlib
import inspect

st.set_page_config(page_title="SLA Payment Analyzer", layout="wide", page_icon="\U0001f6a2")

if "show_sela" not in st.session_state:
    st.session_state["show_sela"] = False

# SELA launcher uses Streamlit's native widget state, not links or query parameters.
# This prevents duplicate Chrome tabs and keeps the dashboard in the same session.

from datetime import datetime

KPI_FILE = os.path.join("data", "kpi_target.json")
KPI_GITHUB_PATH = "data/kpi_target.json"

def load_kpi():
    """Load target KPI dari GitHub (utama) atau lokal (fallback)."""
    # 1) Coba ambil dari GitHub
    if GITHUB_TOKEN and GITHUB_REPO:
        info = github_get_file_info(KPI_GITHUB_PATH)
        if info and "content" in info:
            try:
                decoded = base64.b64decode(info["content"]).decode()
                return json.loads(decoded).get("target_kpi", None)
            except Exception as e:
                st.error(f"Gagal parse KPI dari GitHub: {e}")
                return None

    # 2) Fallback ke lokal
    if os.path.exists(KPI_FILE):
        try:
            with open(KPI_FILE, "r") as f:
                return json.load(f).get("target_kpi", None)
        except Exception as e:
            st.error(f"Gagal baca KPI lokal: {e}")
            return None
    return None


def save_kpi(value):
    """Simpan target KPI ke lokal & GitHub."""
    data = {"target_kpi": value}

    # 1) Simpan ke lokal
    with open(KPI_FILE, "w") as f:
        json.dump(data, f)

    # 2) Simpan ke GitHub
    if GITHUB_TOKEN and GITHUB_REPO:
        upload_file_to_github(
            json.dumps(data).encode(),
            path=KPI_GITHUB_PATH,
            message="Update Target KPI (via app)"
        )

def format_duration(seconds):
    """Convert detik jadi 'xx hari xx jam xx menit xx detik'"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{days} hari {hours} jam {minutes} menit {secs} detik"

import os
import io
import base64
import requests
import pandas as pd
import streamlit as st
from io import BytesIO

# ============================
# KONFIGURASI
# ============================
DATA_PATH = os.path.join("data", "last_data.xlsx")
SLA_DATA_PATH = DATA_PATH
ROCKET_GIF_PATH = "rocket.gif"
LOGO_PATH = "asdp_logo.png"

# GitHub config (gunakan secrets di Streamlit)
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]     # contoh: "firmanaditya90/SLA"
    GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")
    GITHUB_PATH = st.secrets.get("GITHUB_PATH", "data/last_data.xlsx")
except Exception:
    GITHUB_TOKEN = GITHUB_REPO = None
    GITHUB_BRANCH = "main"
    GITHUB_PATH = "data/last_data.xlsx"

_headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

# ============================
# HELPER FUNCTIONS
# ============================
@st.cache_data(ttl=45, max_entries=24, show_spinner=False)
def _github_file_info_cached(repo: str, branch: str, path: str):
    """GitHub version+content check, cached briefly between Streamlit reruns."""
    if not (repo and GITHUB_TOKEN):
        return None
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    try:
        response = requests.get(
            url, params={"ref": branch}, headers=_headers, timeout=(4, 12)
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return None


def github_get_file_info(path: str, use_cache: bool = True):
    """Keep legacy helper interface; bypass cache for GitHub writes."""
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    if use_cache:
        return _github_file_info_cached(GITHUB_REPO, GITHUB_BRANCH, path)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    try:
        response = requests.get(
            url, params={"ref": GITHUB_BRANCH}, headers=_headers, timeout=(4, 12)
        )
        return response.json() if response.status_code == 200 else None
    except requests.RequestException:
        return None

def download_file_from_github(path: str = None) -> bytes | None:
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    path = path or GITHUB_PATH
    info = github_get_file_info(path)
    if not info:
        return None
    if info.get("content"):
        return base64.b64decode(info["content"].encode())
    download_url = info.get("download_url")
    if download_url and str(download_url).startswith('https://'):
        try:
            response = requests.get(download_url, headers=_headers, timeout=(5, 40))
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            return None
    return None

def upload_file_to_github(file_bytes: bytes, path: str = None, message="Update SLA data"):
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    path = path or GITHUB_PATH
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    info = github_get_file_info(path, use_cache=False)
    sha = info.get("sha") if info else None
    data = {
        "message": message,
        "content": base64.b64encode(file_bytes).decode(),
        "branch": GITHUB_BRANCH
    }
    if sha:
        data["sha"] = sha
    try:
        r = requests.put(url, headers=_headers, json=data, timeout=(4, 25))
        if r.status_code in (200, 201):
            _github_file_info_cached.clear()
            return r.json()
    except requests.RequestException:
        pass
    return None

@st.cache_data
def read_excel_cached(path, size, mtime):
    return pd.read_excel(path, header=[0, 1])

def gif_b64(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")

def delete_file_from_github(path: str = None, message="Delete SLA data"):
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    path = path or GITHUB_PATH
    info = github_get_file_info(path, use_cache=False)
    if not info or "sha" not in info:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    data = {
        "message": message,
        "sha": info["sha"],
        "branch": GITHUB_BRANCH
    }
    try:
        r = requests.delete(url, headers=_headers, json=data, timeout=(4, 15))
        if r.status_code == 200:
            _github_file_info_cached.clear()
            return r.json()
    except requests.RequestException:
        pass
    return None


# ============================
# SLA SMART DATA ENGINE -- deferred load (single pass, versioned cache).
# Main dataset is loaded only once, AFTER any new upload is processed.
# ============================
@st.cache_data(show_spinner=False, max_entries=8)
def _read_sla_excel_bytes_cached(file_version: str, _contents: bytes) -> pd.DataFrame:
    """Read a newly uploaded Excel once by its SHA-256 content digest."""
    return pd.read_excel(BytesIO(_contents), header=[0, 1])


@st.cache_data(show_spinner=False, max_entries=8)
def _read_sla_github_cached(file_version: str, _info: dict) -> pd.DataFrame:
    """Parse a GitHub version once, including files >1MB with no inline content."""
    content = _info.get('content')
    if content:
        data = base64.b64decode(content)
    else:
        download_url = _info.get('download_url')
        if not download_url or not str(download_url).startswith('https://'):
            raise ValueError('GitHub tidak menyediakan konten atau download_url')
        response = requests.get(download_url, headers=_headers, timeout=(5, 40))
        response.raise_for_status()
        data = response.content
    return pd.read_excel(BytesIO(data), header=[0, 1])


@st.cache_data(show_spinner=False, max_entries=8)
def _read_sla_local_cached(file_path: str, file_size: int, mtime_ns: int) -> pd.DataFrame:
    """mtime_ns and size invalidate the cache when local source changes."""
    return pd.read_excel(file_path, header=[0, 1])


def _load_sla_dataset(prefer_uploaded: bytes | None = None):
    """Choose one authoritative source (new upload / GitHub / local fallback)."""
    if prefer_uploaded is not None:
        digest = hashlib.sha256(prefer_uploaded).hexdigest()
        return _read_sla_excel_bytes_cached('upload:' + digest, prefer_uploaded), 'upload:' + digest, 'upload'

    # GitHub remains shared source when configured; metadata refreshes every 45 s.
    if GITHUB_TOKEN and GITHUB_REPO:
        info = github_get_file_info(GITHUB_PATH)
        if info and (info.get('content') or info.get('download_url')):
            sha = str(info.get('sha') or '')
            try:
                # Content is decoded/downloaded only when its version changes.
                version = f'github:{GITHUB_REPO}:{GITHUB_BRANCH}:{GITHUB_PATH}:{sha}'
                return _read_sla_github_cached(version, info), version, 'github'
            except Exception:
                # If GitHub is unavailable, retain the local fallback.
                pass

    if os.path.exists(SLA_DATA_PATH):
        stat = os.stat(SLA_DATA_PATH)
        version = f'local:{os.path.abspath(SLA_DATA_PATH)}:{stat.st_size}:{stat.st_mtime_ns}'
        return _read_sla_local_cached(SLA_DATA_PATH, stat.st_size, stat.st_mtime_ns), version, 'local'

    return None, None, None


# ==============================
# Konfigurasi Halaman (TIDAK DIUBAH)
# ==============================
# Page configuration initialized before any UI output (see startup block).

# ------------------------------
# (Opsional) Pakai tema dark:
# Buat file .streamlit/config.toml:
# [theme]
# base="dark"
# primaryColor="#00BFFF"
# backgroundColor="#0E1117"
# secondaryBackgroundColor="#1B1F24"
# textColor="#E6E6E6"
# font="sans serif"
# ------------------------------

# ==============================
# Fungsi untuk baca data dengan animasi ferry  (TIDAK DIUBAH)
# ==============================
@st.cache_data
def load_data(file_path):
    ferry_html = """
    <div style="display:flex;justify-content:center;">
        <lottie-player src="https://assets10.lottiefiles.com/packages/lf20_xpdp3p.json"
            background="transparent"
            speed="1"
            style="width: 300px; height: 300px;"
            loop
            autoplay>
        </lottie-player>
    </div>
    """
    with st.spinner("Memuat data..."):
        st.components.v1.html(
            '<script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>'
            + ferry_html,
            height=350,
        )
        time.sleep(2)  # simulasi loading
        return pd.read_excel(file_path)

# ==============================
# Styling: CSS untuk look modern (TIDAK DIUBAH)
# ==============================
st.markdown("""
<style>
/* Ringkasan Cards */
.summary-card {
  background: rgba(25, 30, 55, 0.55);
  border-radius: 18px;
  padding: 18px 20px;
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 6px 20px rgba(0,0,0,0.25);
  backdrop-filter: blur(10px);
  text-align: center;
  transition: all 0.25s ease;
}
.summary-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 28px rgba(0,0,0,0.35);
}
.summary-icon {
  font-size: 28px;
  margin-bottom: 6px;
  opacity: 0.9;
}
.summary-label {
  font-size: 13px;
  text-transform: uppercase;
  opacity: 0.7;
  margin-bottom: 2px;
}
.summary-value {
  font-size: 26px;
  font-weight: 800;
  background: linear-gradient(90deg, #00eaff, #00ff9d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
/* Modern KPI Cards */
.kpi-card {
  background: rgba(20, 25, 45, 0.55);
  border-radius: 20px;
  padding: 18px 20px;
  border: 1px solid rgba(255,255,255,0.15);
  box-shadow: 0 8px 25px rgba(0,0,0,0.25);
  backdrop-filter: blur(12px);
  text-align: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.35);
}
.kpi-label {
  font-size: 13px;
  opacity: 0.75;
  margin-bottom: 4px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.kpi-value {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(90deg, #00eaff, #00ff9d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.kpi-sub {
  font-size: 12px;
  opacity: 0.65;
}
.kpi-status-on {
  font-size: 24px;
  font-weight: 800;
  color: #00ffb0;
  text-shadow: 0 0 8px rgba(0,255,160,0.7);
}
.kpi-status-off {
  font-size: 24px;
  font-weight: 800;
  color: #ff4f70;
  text-shadow: 0 0 8px rgba(255,80,100,0.7);
}
/* Hero gradient title */
.hero {
  text-align: center;
  padding: 12px 0 6px 0;
}
.hero h1 {
  margin: 0;
  background: linear-gradient(90deg, #00BFFF 0%, #7F7FD5 50%, #86A8E7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 800;
  letter-spacing: 0.5px;
}
.hero p {
  opacity: 0.85;
  margin: 8px 0 0 0;
}
/* Glass cards */
.card {
  background: rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 6px 24px rgba(0,0,0,0.12);
}
.kpi {
  display: flex; flex-direction: column; gap: 6px;
}
.kpi .label { font-size: 12px; opacity: 0.7; }
.kpi .value { font-size: 22px; font-weight: 700; }
.small {
  font-size: 12px; opacity: 0.75;
}
hr.soft { border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent); margin: 10px 0 14px 0; }
.poster {
  background: linear-gradient(135deg, #1a2a6c, #b21f1f, #fdbb2d);
  border-radius: 20px;
  padding: 25px;
  margin: 20px 0;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.poster-left {
  flex: 1;
  padding-right: 20px;
  border-right: 2px solid rgba(255,255,255,0.4);
}
.poster-right {
  flex: 2;
  padding-left: 20px;
}

.avatar-photo{background:transparent!important;filter:drop-shadow(0 18px 30px rgba(8,23,41,.36));border-radius:0!important}
.avatar-overlay,.avatar-grid{display:none!important}
.avatar-card::before{content:"";position:absolute;inset:auto 12% 12px 12%;height:56px;border-radius:50%;background:radial-gradient(circle,rgba(95,226,208,.18),rgba(95,226,208,0));filter:blur(12px);z-index:0}
.avatar-card > *{position:relative;z-index:1}


  </style>
""", unsafe_allow_html=True)

# Visual-only CSS overlay: contains no widget, data or server-side operations.
st.markdown(r"""
<style>
/* ===============================================================
   ASDP SLA PAYMENT ANALYZER - EXECUTIVE PREMIUM DESIGN SYSTEM
   Pure CSS visual overlay. No application logic or chart datasets.
   Local fonts only. No external assets, JS, animations, or HTTP.
   =============================================================== */
:root {
  --sla-ink: #122945;
  --sla-navy: #0b2747;
  --sla-navy-mid: #174c70;
  --sla-blue: #3474ba;
  --sla-teal: #0ca9a3;
  --sla-mint: #27c7af;
  --sla-gold: #d7a956;
  --sla-muted: #5b728b;
  --sla-border: #dbe6f0;
  --sla-paper: #ffffff;
  --sla-shadow: 0 5px 14px rgba(18, 51, 83, .035),
                0 18px 46px rgba(18, 51, 83, .075);
  --sla-radius: 16px;
}

/* App canvas - calm luxury, restrained highlights and generous whitespace. */
[data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at 98% -8%,rgba(39,189,188,.075),transparent 34%),
              radial-gradient(circle at 15% 4%,rgba(59,121,193,.07),transparent 34%),
              linear-gradient(180deg,#f5f9fd 0%,#f9fbfe 42%,#f5f8fc 100%);
  color: var(--sla-ink);
}
[data-testid="stAppViewContainer"] > .main,
[data-testid="stMain"] {background: transparent;}
[data-testid="stMainBlockContainer"] {
  padding-top: 1.65rem;
  padding-bottom: 3.5rem;
}
[data-testid="stMain"] {font-family: Inter, 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p {line-height: 1.56;}
[data-testid="stMain"] [data-testid="stHeadingWithActionElements"] h2,
[data-testid="stMain"] [data-testid="stHeadingWithActionElements"] h3 {
  color: var(--sla-navy);
  font-weight: 780;
  letter-spacing: -.55px;
}
[data-testid="stMain"] [data-testid="stHeadingWithActionElements"] h2 {
  padding-top: .3rem;
  margin-bottom: .45rem;
}
[data-testid="stMain"] [data-testid="stHeadingWithActionElements"] h3 {letter-spacing: -.35px;}

/* Page masthead - original title and description preserved. */
.sla-hero-premium {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  gap: 16px;
  align-items: center;
  padding: 30px 34px 31px;
  margin: 2px 0 27px;
  border-radius: 23px;
  border: 1px solid rgba(105,194,220,.25);
  background: radial-gradient(circle at 87% 14%,rgba(32,192,181,.16),transparent 36%),
              radial-gradient(circle at 5% 100%,rgba(76,116,204,.17),transparent 43%),
              linear-gradient(115deg,#091e3b 0%,#0c345a 55%,#165474 100%);
  box-shadow: 0 15px 40px rgba(10,34,68,.16);
  color: #f7fbff;
  overflow: hidden;
  position: relative;
}
.sla-hero-premium::before {
  content: "";
  position: absolute;
  width: 260px;
  height: 260px;
  border: 1px solid rgba(176,222,243,.14);
  border-radius: 50%;
  right: -105px;
  top: -125px;
  pointer-events: none;
}
.sla-hero-premium::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 32px;
  width: 160px;
  height: 3px;
  background: linear-gradient(90deg,var(--sla-mint),#bde2f4,transparent);
}
.sla-hero-premium .sla-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: #79e2d6;
  font-size: 10px;
  font-weight: 820;
  letter-spacing: 2.1px;
  text-transform: uppercase;
  margin-bottom: 10px;
}
.sla-hero-premium .sla-eyebrow::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #54d9c1;
  box-shadow: 0 0 0 4px rgba(84,217,193,.13);
}
.sla-hero-premium h1 {
  margin: 0;
  font-weight: 840;
  font-size: clamp(26px, 3.2vw, 42px);
  line-height: 1.18;
  letter-spacing: -1.5px;
  color: #fff !important;
  background: none !important;
  -webkit-text-fill-color: #fff !important;
}
.sla-hero-premium .sla-hero-description {
  margin: 12px 0 0;
  color: #d3e5f1;
  font-size: clamp(12px, 1vw, 14px);
  max-width: 780px;
}
.sla-hero-premium .sla-hero-seal {
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: center;
  justify-content: center;
  color: #d9eff5;
  border: 1px solid rgba(205,238,243,.24);
  background: rgba(255,255,255,.075);
  border-radius: 15px;
  padding: 17px 20px;
  min-width: 130px;
  white-space: nowrap;
}
.sla-hero-premium .sla-hero-seal strong {font-size: 17px;letter-spacing: 1.5px;color:#fff;}
.sla-hero-premium .sla-hero-seal span {font-size: 9px;letter-spacing: 1.3px;color:#8be4d5;}

/* Sidebar: crisp white navigation panel, readable in bright environments. */
[data-testid="stSidebar"] {
  background: #f9fbfe;
  border-right: 1px solid #e1eaf2;
  box-shadow: 3px 0 24px rgba(21,61,101,.035);
}
[data-testid="stSidebar"] > div:first-child {
  background: linear-gradient(180deg,#fff 0%,#f9fbfe 100%);
}
[data-testid="stSidebar"] [data-testid="stImage"] img {
  object-fit: contain;
  max-width: 100%;
}
.sla-side-brand {
  margin: 7px 0 19px;
  padding: 16px 13px;
  border-radius: 14px;
  border: 1px solid #e1eaf1;
  background: linear-gradient(145deg,#fff,#f2f8fc);
  text-align: center;
}
.sla-side-brand strong {display:block;color:#0a3458;font-size:14px;letter-spacing:-.2px;}
.sla-side-brand span {display:block;color:#5d8e9f;font-size:9px;font-weight:800;letter-spacing:1.35px;margin-top:5px;}
[data-testid="stSidebar"] h3 {font-weight: 800 !important;color: #113456 !important;font-size: 15px;}
[data-testid="stSidebar"] label {font-weight:600;color:#39536c;}
[data-testid="stSidebar"] [data-testid="stExpander"] {
  border-radius: 12px;
  background: #fff;
  border: 1px solid #dce7ef;
  box-shadow: 0 2px 8px rgba(18,52,87,.035);
}

/* Tabs: compact, touch-friendly, clearly distinguish active section. */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 4px;
  padding: 7px 7px 6px;
  margin: 8px 0 13px;
  border-radius: 14px;
  border: 1px solid #dce7f0;
  background: #fff;
  box-shadow: 0 5px 19px rgba(21,60,99,.05);
  overflow-x: auto;
  scrollbar-width: thin;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 12px;
  font-weight: 690;
  color: #52687d;
  border: 1px solid transparent;
  background: transparent;
  transition: background-color .12s ease, color .12s ease;
  white-space: nowrap;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
  background: #ecf6fb;
  color: #173b5b;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(120deg,#0d3158,#16627c);
  border-color: #286781;
  color: #fff;
  box-shadow: 0 4px 10px rgba(16,55,92,.14);
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {display:none;}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {padding-top: .35rem;}

/* Native widgets - only borders, surface and focus; no runtime state. */
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
[data-testid="stDateInput"] [data-baseweb="input"] > div,
[data-testid="stTextInput"] [data-baseweb="input"] > div,
[data-testid="stNumberInput"] [data-baseweb="input"] > div {
  border: 1px solid #cfdeea;
  border-radius: 11px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(19,62,98,.025);
  min-height: 40px;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within,
[data-testid="stTextInput"] [data-baseweb="input"] > div:focus-within {
  border-color: #19aca5;
  box-shadow: 0 0 0 3px rgba(24,172,166,.11);
}
[data-testid="stFileUploader"] {
  border: 1px dashed #bbd4e3;
  border-radius: 13px;
  background: #f9fdff;
  padding: 7px;
}
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button,
[data-testid="stFormSubmitButton"] button {
  min-height: 39px;
  border-radius: 10px;
  font-weight: 700;
  letter-spacing: .08px;
  border: 1px solid #d3e2ed;
  background: linear-gradient(180deg,#fff,#f5faff);
  color: #184466;
  box-shadow: 0 2px 7px rgba(25,64,99,.045);
  transition: background-color .12s ease, box-shadow .12s ease;
}
[data-testid="stButton"] button:hover,
[data-testid="stDownloadButton"] button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  border-color: #23aeb0;
  background: #ebf9f7;
  color: #115c64;
  box-shadow: 0 5px 12px rgba(13,74,86,.09);
}
[data-testid="stButton"] button[kind="primary"],
[data-testid="stDownloadButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
  color: #fff;
  border-color: #145777;
  background: linear-gradient(120deg,#123e69,#137b87);
}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stDownloadButton"] button[kind="primary"]:hover {
  color: #fff;
  background: linear-gradient(120deg,#174f81,#139e99);
}

/* Native reporting surfaces, dataframes, expander and KPI widgets. */
[data-testid="stMetric"] {
  background: #fff;
  border-radius: 15px;
  border: 1px solid var(--sla-border);
  padding: 16px 18px;
  box-shadow: 0 7px 19px rgba(22,53,86,.055);
  min-height: 109px;
}
[data-testid="stMetricLabel"] {color: #5a758e;font-weight:680;}
[data-testid="stMetricValue"] {color: #0c3758;font-weight:810;letter-spacing:-.8px;}
[data-testid="stDataFrame"] {
  background: #fff;
  border: 1px solid #d8e5ef;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(20,51,83,.055);
  margin-top: 5px;
  margin-bottom: 9px;
}
[data-testid="stTable"] {
  border: 1px solid #dae8f1;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(20,54,84,.045);
}
[data-testid="stExpander"] {
  border-radius: 13px;
  border: 1px solid #dbe7f0;
  background: #fff;
  box-shadow: 0 4px 13px rgba(18,53,89,.035);
}
[data-testid="stExpander"] summary {
  font-weight: 700;
  color: #1c4868;
}
[data-testid="stPlotlyChart"],
[data-testid="stPyplotGlobalUse"] {
  border-radius: 15px;
  overflow: hidden;
  border: 1px solid rgba(198,216,231,.82);
  box-shadow: 0 7px 25px rgba(19,52,84,.055);
  background: #fff;
}
[data-testid="stAlert"] {
  border-radius: 12px;
  border-left-width: 3px;
}
[data-testid="stCaptionContainer"] {color: #647e94;}

/* Existing custom HTML KPI card surfaces: uplift without altering values. */
.kpi-card {
  background: linear-gradient(145deg,#fff,#f5faff);
  border: 1px solid #dbe7f1;
  border-radius: 16px;
  box-shadow: var(--sla-shadow);
  padding: 20px 18px;
  backdrop-filter: none;
}
.kpi-card:hover {box-shadow: 0 12px 31px rgba(21,59,93,.115);transform: translateY(-2px);}
.kpi-label {color: #56758f;opacity: 1;font-weight: 720;letter-spacing: .8px;}
.kpi-value {
  color: #0b496e;
  background: linear-gradient(100deg,#0b3d6b,#0ba99d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -.9px;
}
.kpi-sub {color:#6a8092;opacity:1;}
.kpi-status-on {color:#078970;text-shadow:none;}
.kpi-status-off {color:#ca4b53;text-shadow:none;}
.card {
  background: #fff;
  border: 1px solid #dbe7f0;
  box-shadow: 0 5px 16px rgba(20,50,79,.045);
}
hr.soft {background:linear-gradient(90deg,transparent,#cbdce9,transparent);}

/* ---------------------------------------------------------------
   SLA TABLES: Per Proses & Tren — lightweight visual-only upgrade
   Isolated class names, no JS / fonts / network requests.
   --------------------------------------------------------------- */
.slae-wrap{margin:12px 0 16px;min-width:0;}
.slae-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:14px 0 18px;}
.slae-kpi{border:1px solid #d9e7ef;border-radius:15px;padding:15px 17px;
  background:linear-gradient(140deg,#fff 0%,#f5fafc 100%);
  box-shadow:0 5px 19px rgba(20,56,86,.045);min-width:0;}
.slae-kpi-label{color:#537088;font-size:10px;font-weight:800;letter-spacing:.7px;text-transform:uppercase;}
.slae-kpi-value{color:#102e4e;font-size:21px;line-height:1.28;font-weight:840;
  letter-spacing:-.5px;margin-top:9px;overflow-wrap:anywhere;font-variant-numeric:tabular-nums;}
.slae-kpi-sub{color:#6f8597;font-size:11px;margin-top:5px;line-height:1.4;}
.slae-panel{background:#fff;border:1px solid #d9e6ef;border-radius:18px;overflow:hidden;
  box-shadow:0 10px 31px rgba(13,47,76,.085);}
.slae-panel-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;
  background:linear-gradient(112deg,#0a2748 0%,#134e70 80%,#126472 100%);padding:17px 20px;}
.slae-panel-title{font-weight:850;font-size:16px;letter-spacing:.1px;color:#fff;line-height:1.4;}
.slae-panel-note{color:#a6f0dc;font-size:10px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;}
.slae-scroll{overflow-x:auto;overflow-y:auto;max-height:620px;scrollbar-width:thin;}
.slae-table{border-collapse:separate;border-spacing:0;min-width:720px;width:100%;
  font-family:Inter,'Segoe UI',Arial,sans-serif;font-size:12px;color:#213b54;}
.slae-table th{position:sticky;top:0;z-index:2;background:#ecf3f9;color:#37536b;
  letter-spacing:.55px;text-transform:uppercase;font-size:10px;font-weight:850;
  text-align:left;padding:15px 15px;border-bottom:1px solid #d7e4ee;white-space:nowrap;}
.slae-table td{padding:13px 15px;border-bottom:1px solid #e6eef4;vertical-align:middle;}
.slae-table tbody tr:nth-child(even){background:#f7fafd;}
.slae-table tbody tr:hover{background:#eaf8f6;}
.slae-table tbody tr:last-child td{border-bottom:0;}
.slae-table .slae-numeric{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
.slae-label{font-size:12px;font-weight:800;color:#173957;}
.slae-hint{font-size:10px;color:#74899b;margin-top:3px;line-height:1.35;}
.slae-duration{font-weight:820;color:#183f63;font-variant-numeric:tabular-nums;white-space:nowrap;}
.slae-days{font-weight:800;color:#0c7e79;white-space:nowrap;font-variant-numeric:tabular-nums;}
.slae-pill{display:inline-block;border-radius:999px;padding:4px 9px;
  background:#e5f6f2;color:#087a6a;font-size:10px;font-weight:850;white-space:nowrap;}
.slae-pill-e2e{background:#e7edf9;color:#294b83;}
.slae-pill-current{background:#e0f6ef;color:#13765d;}
.slae-track{min-width:95px;width:100%;background:#e7eef4;height:8px;border-radius:99px;overflow:hidden;}
.slae-track-fill{height:100%;background:linear-gradient(90deg,#2d83c3,#1bb7a8);border-radius:99px;}
.slae-trend-table{min-width:920px;}
.slae-trend-table th:first-child,.slae-trend-table td:first-child{position:sticky;left:0;z-index:1;
  background:#f4f8fc;box-shadow:1px 0 0 #e2ebf3;}
.slae-trend-table th:first-child{z-index:4;background:#e6f0f8;}
.slae-trend-table tr.slae-latest td{background:#ecf9f6;}
.slae-trend-table tr.slae-latest td:first-child{background:#e1f5ef;}
.slae-trend-table .slae-small-value{font-size:10px;color:#768b9b;margin-top:3px;white-space:nowrap;}
.slae-trend-table .slae-period{font-weight:850;color:#184565;white-space:nowrap;}
.slae-empty{font-size:12px;color:#8896a7;}
.slae-foot{font-size:11px;color:#637d91;margin:10px 3px 4px;line-height:1.6;}
@media(max-width:1100px){.slae-kpis{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:640px){.slae-kpis{grid-template-columns:1fr 1fr;gap:8px;}
  .slae-kpi{padding:12px;}.slae-kpi-value{font-size:17px;}
  .slae-panel-head{padding:14px;}.slae-panel-title{font-size:14px;}}

/* Loading and UI for narrower viewports. */
@media(max-width: 1100px) {
  [data-testid="stMainBlockContainer"] {padding-top: 1rem;}
  .sla-hero-premium {padding: 24px 24px 25px;}
}
@media(max-width: 700px) {
  .sla-hero-premium {grid-template-columns:1fr;padding: 22px 21px;margin-bottom:18px;}
  .sla-hero-premium .sla-hero-seal {display:none;}
  .sla-hero-premium h1 {font-size:27px;letter-spacing:-.9px;}
  [data-testid="stTabs"] [data-baseweb="tab"] {padding:9px 10px;font-size:11px;}
  [data-testid="stMainBlockContainer"] {padding-left: 1rem;padding-right: 1rem;}
}
@media(prefers-reduced-motion: reduce) {
  [data-testid="stTabs"] [data-baseweb="tab"],
  [data-testid="stButton"] button,
  [data-testid="stDownloadButton"] button,
  .kpi-card {transition:none!important;}
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<section class="sla-hero-premium" aria-label="SLA Payment Analyzer">
  <div>
    <div class="sla-eyebrow">PT ASDP INDONESIA FERRY &middot; PAYMENT INTELLIGENCE</div>
    <h1>\U0001f6a2 SLA Payment Analyzer</h1>
    <p class="sla-hero-description">Dashboard modern untuk melihat &amp; menganalisis SLA dokumen penagihan</p>
  </div>
  <div class="sla-hero-seal" aria-hidden="true">
    <strong>ASDP</strong>
    <span>EXECUTIVE VIEW</span>
  </div>
</section>
""", unsafe_allow_html=True)

# ==============================
# Logo di Sidebar (TIDAK DIUBAH)
# ==============================
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png",
        width=180
    )
    st.markdown(
        '<div class="sla-side-brand">'
        '<strong>\U0001f680 SLA Payment Analyzer</strong>'
        '<span>PAYMENT PERFORMANCE CENTER</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# ==============================
# Path & Assets (TIDAK DIUBAH)
# ==============================
os.makedirs("data", exist_ok=True)
os.makedirs("assets", exist_ok=True)  # taruh assets/rocket.gif
DATA_PATH = os.path.join("data", "last_data.xlsx")
ROCKET_GIF_PATH = os.path.join("assets", "rocket.gif")

def gif_b64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return f"data:image/gif;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    except Exception:
        return None

rocket_b64 = gif_b64(ROCKET_GIF_PATH)

# ==============================
# Admin password (TIDAK DIUBAH)
# ==============================
try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", None)
except Exception:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", None)

st.sidebar.markdown("### \U0001f510 Admin")
if ADMIN_PASSWORD:
    password_input = st.sidebar.text_input("Password admin (untuk upload)", type="password")
    is_admin = password_input == ADMIN_PASSWORD
else:
    st.sidebar.warning("Admin password belum dikonfigurasi (Secrets/ENV). App berjalan dalam mode read-only.")
    is_admin = False
    
# ==============================
# Util SLA (TIDAK DIUBAH)
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
# Upload (hanya admin) (TIDAK DIUBAH)
# ==============================
with st.sidebar.expander("\U0001f4e4 Upload Data (Admin Only)", expanded=is_admin):
    # A new widget identity after Reset ensures the previous upload is not
    # submitted again automatically during st.rerun().
    _sla_uploader_generation = st.session_state.setdefault('_sla_uploader_generation', 0)
    uploaded_file = (
        st.file_uploader(
            "Upload file Excel (.xlsx)", type="xlsx",
            key=f"sla_main_uploader_{_sla_uploader_generation}"
        ) if is_admin else None
    )

# ==============================
# SMART UPLOAD + SINGLE DATA LOAD (performance-safe revision)
# Upload-once per file digest prevents uploading again on every widget rerun.
# The GitHub remote file stays authoritative across users; local is fallback.
# ==============================
load_status = st.empty()
_sla_just_uploaded_bytes = None
if uploaded_file is not None and is_admin:
    # Compute digest using buffer without changing filename/format.
    _sla_upload_buffer = uploaded_file.getvalue()
    _sla_upload_digest = hashlib.sha256(_sla_upload_buffer).hexdigest()
    if st.session_state.get('_sla_last_uploaded_digest') != _sla_upload_digest:
        with st.spinner("\U0001f680 Mengunggah & menyiapkan data..."):
            if rocket_b64:
                st.markdown(
                    f'<div style="text-align:center;"><img src="{rocket_b64}" width="160"/></div>',
                    unsafe_allow_html=True
                )
            # Validate spreadsheet BEFORE replacing an existing good file.
            try:
                _sla_verified_upload = _read_sla_excel_bytes_cached(
                    'upload:' + _sla_upload_digest, _sla_upload_buffer
                )
                if _sla_verified_upload.empty:
                    raise ValueError("File Excel kosong.")
            except Exception as exc:
                st.error(f"File Excel tidak dapat dibaca; data lama dipertahankan: {exc}")
            else:
                with open(SLA_DATA_PATH, "wb") as f:
                    f.write(_sla_upload_buffer)
                _sla_just_uploaded_bytes = _sla_upload_buffer
                _result = upload_file_to_github(
                    _sla_upload_buffer, path=GITHUB_PATH,
                    message="Update SLA data (via app)"
                )
                st.session_state['_sla_last_uploaded_digest'] = _sla_upload_digest
                if _result:
                    st.session_state['_sla_upload_prefer_local'] = False
                    st.success("\u2705 Data baru berhasil diunggah & disinkronkan ke GitHub!")
                else:
                    st.session_state['_sla_upload_prefer_local'] = True
                    st.warning("\u26a0\ufe0f Data tersimpan lokal, tapi gagal update ke GitHub.")

# If the current upload has not synced, use it in this session (no stale remote override).
if _sla_just_uploaded_bytes is None and st.session_state.get('_sla_upload_prefer_local'):
    if os.path.exists(SLA_DATA_PATH):
        with open(SLA_DATA_PATH, 'rb') as f:
            _sla_just_uploaded_bytes = f.read()

with st.spinner("\U0001f504 Membaca data terakhir..."):
    df_raw, _sla_source_version, _sla_source_kind = _load_sla_dataset(_sla_just_uploaded_bytes)

if df_raw is None:
    st.warning("\u26a0\ufe0f Belum ada file SLA yang diunggah atau sumber data tidak dapat diakses.")
    st.stop()

if _sla_source_kind == 'github':
    st.info("\u2705 Menampilkan data terbaru dari GitHub.")
elif _sla_source_kind == 'local':
    st.info("\u2139\ufe0f Menampilkan data dari upload terakhir (lokal).")
else:
    st.info("\u2139\ufe0f Menampilkan data dari upload terakhir.")

# Tombol reset (hanya admin) (TIDAK DIUBAH + FIX sinkron GitHub)
with st.sidebar.expander("\U0001f6e0\ufe0f Admin Tools", expanded=False):
    if is_admin and os.path.exists(DATA_PATH):
        if st.button("\U0001f5d1\ufe0f Reset Data (hapus data terakhir)"):
            # Hapus lokal
            os.remove(SLA_DATA_PATH)
            st.session_state.pop('_sla_last_uploaded_digest', None)
            st.session_state.pop('_sla_upload_prefer_local', None)
            st.session_state['_sla_uploader_generation'] = st.session_state.get('_sla_uploader_generation', 0) + 1
            _read_sla_local_cached.clear()
            _read_sla_excel_bytes_cached.clear()
            
            # Hapus juga di GitHub
            result = delete_file_from_github(path=GITHUB_PATH, message="Reset SLA data (via app)")
            if result:
                st.success("\u2705 Data berhasil dihapus dari lokal & GitHub.")
            else:
                st.warning("\u26a0\ufe0f Data lokal terhapus, tapi gagal menghapus dari GitHub.")

            st.rerun()


# ==============================
# Preprocessing kolom (TIDAK DIUBAH)
# ==============================
# Normalisasi header multiindex
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

# Panel: daftar kolom
with st.expander("🧾 Kolom yang terdeteksi di file"):
    st.write(list(df_raw.columns))

# Deteksi kolom periode
periode_col = next((col for col in df_raw.columns if "PERIODE" in str(col).upper()), None)
if not periode_col:
    st.error("Kolom PERIODE tidak ditemukan.")
    st.stop()

# Parse SLA (tunda heavy parsing sampai setelah filter)
sla_cols = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]

# Helper periode: sorting & default range yang konsisten di seluruh tab/laporan.
MONTH_MAP_ID = {
    "januari": 1, "jan": 1, "january": 1,
    "februari": 2, "feb": 2, "february": 2,
    "maret": 3, "mar": 3, "march": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "jun": 6, "june": 6,
    "juli": 7, "jul": 7, "july": 7,
    "agustus": 8, "agu": 8, "agus": 8, "agt": 8, "aug": 8, "august": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10, "oct": 10, "october": 10,
    "november": 11, "nov": 11,
    "desember": 12, "des": 12, "dec": 12, "december": 12,
}

def parse_period_label_to_timestamp(value):
    """Parse label periode menjadi timestamp awal bulan.
    Mendukung format: Oktober 2026, Okt-2026, 2026-10, 10/2026, datetime, dll.
    """
    if value is None or pd.isna(value):
        return pd.NaT

    if isinstance(value, (pd.Timestamp, datetime)):
        try:
            return pd.Timestamp(year=value.year, month=value.month, day=1)
        except Exception:
            return pd.NaT

    s = str(value).strip()
    if not s:
        return pd.NaT

    # Coba parser umum terlebih dahulu untuk format numerik / ISO.
    dt = pd.to_datetime(s, errors='coerce', dayfirst=True)
    if pd.notna(dt):
        return pd.Timestamp(year=dt.year, month=dt.month, day=1)

    s_lower = s.lower()
    year_match = re.search(r'(?:19|20)\d{2}', s_lower)
    if not year_match:
        return pd.NaT
    year = int(year_match.group(0))

    month = None
    for label, month_num in sorted(MONTH_MAP_ID.items(), key=lambda kv: len(kv[0]), reverse=True):
        if re.search(r'(^|[^a-z])' + re.escape(label) + r'([^a-z]|$)', s_lower):
            month = month_num
            break

    if month is None:
        patterns = [
            r'((?:19|20)\d{2})[^0-9]([01]?\d)',
            r'([01]?\d)[^0-9]((?:19|20)\d{2})',
        ]
        for pat in patterns:
            m = re.search(pat, s_lower)
            if m:
                g1, g2 = m.groups()
                cand = int(g2) if len(g1) == 4 else int(g1)
                if 1 <= cand <= 12:
                    month = cand
                    break

    if month is None:
        return pd.NaT

    try:
        return pd.Timestamp(year=year, month=month, day=1)
    except Exception:
        return pd.NaT


def build_sorted_period_list(series):
    values = [str(v).strip() for v in series.dropna().tolist() if str(v).strip()]
    unique_values = list(dict.fromkeys(values))
    tagged = [(label, parse_period_label_to_timestamp(label)) for label in unique_values]
    parsed = [(label, ts) for label, ts in tagged if pd.notna(ts)]
    unparsed = [label for label, ts in tagged if pd.isna(ts)]
    parsed_sorted = [label for label, _ in sorted(parsed, key=lambda item: (item[1], str(item[0]).lower()))]
    return parsed_sorted + unparsed


def get_default_period_range(periode_values):
    if not periode_values:
        return None, None

    parsed = [(label, parse_period_label_to_timestamp(label)) for label in periode_values]
    parsed = [(label, ts) for label, ts in parsed if pd.notna(ts)]

    if not parsed:
        return periode_values[0], periode_values[-1]

    latest_label, latest_ts = max(parsed, key=lambda item: item[1])
    target_year = latest_ts.year

    same_year = [(label, ts) for label, ts in parsed if ts.year == target_year]
    january_candidates = [label for label, ts in same_year if ts.month == 1]

    if january_candidates:
        default_start = january_candidates[0]
    elif same_year:
        default_start = min(same_year, key=lambda item: item[1])[0]
    else:
        default_start = periode_values[0]

    return default_start, latest_label


# Parse only UNIQUE period labels (typically tens rather than 90k rows).
# .map preserves source labels and yields same date values as the legacy .apply.
try:
    _sla_period_labels = df_raw[periode_col].astype(str)
    _sla_unique_labels = _sla_period_labels.unique().tolist()
    _sla_period_lookup = {
        label: parse_period_label_to_timestamp(label)
        for label in _sla_unique_labels
    }
    df_raw['PERIODE_DATETIME'] = _sla_period_labels.map(_sla_period_lookup)
except Exception:
    df_raw['PERIODE_DATETIME'] = pd.NaT

# ==============================
# Sidebar: filter periode (REVISI)
# Default: Januari pada tahun dari periode terbaru s.d. periode upload terakhir.
# Seluruh tab dan laporan memakai filter yang sama melalui df_filtered & selected_periode.
# ==============================
periode_list = build_sorted_period_list(df_raw[periode_col])
if not periode_list:
    st.error("Data periode tidak ditemukan pada file upload.")
    st.stop()

default_start_periode, default_end_periode = get_default_period_range(periode_list)
period_signature = "||".join(periode_list)

should_reset_period_state = (
    st.session_state.get('_periode_options_signature') != period_signature
    or st.session_state.get('periode_mulai') not in periode_list
    or st.session_state.get('periode_akhir') not in periode_list
)

if should_reset_period_state:
    st.session_state['periode_mulai'] = default_start_periode
    st.session_state['periode_akhir'] = default_end_periode
    st.session_state['_periode_options_signature'] = period_signature

with st.sidebar:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📅 Filter Rentang Periode")

    start_periode = st.selectbox(
        "Periode Mulai",
        periode_list,
        index=periode_list.index(st.session_state.get('periode_mulai', default_start_periode)),
        key="periode_mulai",
    )
    end_periode = st.selectbox(
        "Periode Akhir",
        periode_list,
        index=periode_list.index(st.session_state.get('periode_akhir', default_end_periode)),
        key="periode_akhir",
    )

idx_start = periode_list.index(start_periode)
idx_end = periode_list.index(end_periode)
if idx_start > idx_end:
    st.warning("Periode Mulai lebih besar dari Periode Akhir. Filter otomatis dikembalikan ke rentang default dataset aktif.")
    start_periode = default_start_periode
    end_periode = default_end_periode
    st.session_state['periode_mulai'] = start_periode
    st.session_state['periode_akhir'] = end_periode
    idx_start = periode_list.index(start_periode)
    idx_end = periode_list.index(end_periode)

selected_periode = periode_list[idx_start:idx_end+1]
df_filtered = df_raw[df_raw[periode_col].astype(str).isin(selected_periode)].copy()

st.markdown(f'<div class="small">Menampilkan data periode dari <b>{start_periode}</b> sampai <b>{end_periode}</b> \u2014 total baris: <b>{len(df_filtered)}</b></div>', unsafe_allow_html=True)

available_sla_cols = [col for col in sla_cols if col in df_filtered.columns]
proses_grafik_cols = [c for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"] if c in available_sla_cols]

# Created by
st.sidebar.markdown(
    "<p style='text-align:center; font-size:12px; color:gray;'>Created by. Firman Aditya</p>",
    unsafe_allow_html=True,
)

# Backup launcher di sidebar. Arahkan ke modal yang sama dengan tombol melayang.
with st.sidebar:
    st.markdown("### 🤖 Tanya SELA")
    _sela_sidebar_clicked = st.button(
        "💬 Buka SELA", key="sela_sidebar_launcher_v15",
        help="Buka asisten pribadi SELA di halaman ini tanpa tab baru.",
    )
    st.caption("SELA tetap ringan: hanya diproses saat dibuka. Gunakan ikon SELA Premium di kanan atas layar.")

# Floating action button akan dirender pada akhir script, setelah semua fungsi SELA tersedia.
# CSS berikut hanya memengaruhi tombol SELA; komponen dashboard lain tidak diubah.
st.markdown("""
<style>
/* SELA Premium Top-right Launcher — display-only upgrade to the working v15 button.
   The Streamlit widget key and dialog callback are unchanged. */
.st-key-sela_floating_launcher_v15 {
  position:fixed!important;
  top:82px!important;
  right:24px!important;
  bottom:auto!important;
  width:max-content!important;
  max-width:calc(100vw - 24px)!important;
  z-index:9998!important;
  pointer-events:auto!important;
}
.st-key-sela_floating_launcher_v15 button {
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:11px!important;
  min-height:56px!important;
  min-width:185px!important;
  padding:8px 12px 8px 9px!important;
  border-radius:18px!important;
  border:1px solid rgba(104,218,219,.53)!important;
  background:linear-gradient(125deg,#0b2948 0%,#0e3f62 55%,#13576d 100%)!important;
  box-shadow:0 14px 32px rgba(5,28,51,.23),inset 0 1px 0 rgba(255,255,255,.14)!important;
  color:#f5fbff!important;
  font-family:Inter,'Segoe UI',sans-serif!important;
  font-size:15px!important;
  font-weight:850!important;
  letter-spacing:.03em!important;
  white-space:nowrap!important;
  cursor:pointer!important;
  transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease!important;
}
/* A compact premium assistant insignia, without an extra image or network request. */
.st-key-sela_floating_launcher_v15 button::before {
  content:"✦";
  flex:0 0 40px;
  width:40px;
  height:40px;
  display:grid;
  place-items:center;
  border-radius:13px;
  background:linear-gradient(145deg,#74f5df 0%,#48bed7 56%,#6e96f7 100%);
  box-shadow:0 5px 15px rgba(35,193,204,.31),inset 0 1px 0 rgba(255,255,255,.55);
  color:#06344d;
  font-size:22px;
  font-weight:900;
  line-height:1;
}
.st-key-sela_floating_launcher_v15 button::after {
  content:"AI";
  margin-left:2px;
  padding:5px 7px;
  border-radius:8px;
  border:1px solid rgba(150,236,236,.23);
  background:rgba(255,255,255,.09);
  color:#bdf7f1;
  font-size:10px;
  font-weight:800;
  letter-spacing:.12em;
}
.st-key-sela_floating_launcher_v15 button:hover {
  transform:translateY(-2px)!important;
  border-color:rgba(125,246,229,.83)!important;
  box-shadow:0 19px 38px rgba(5,28,51,.30),0 0 0 3px rgba(84,213,214,.07)!important;
}
.st-key-sela_floating_launcher_v15 button:active {
  transform:translateY(0)!important;
}
.st-key-sela_floating_launcher_v15 button:focus-visible {
  outline:3px solid #7ef1dd!important;
  outline-offset:3px!important;
}
/* Never cover the popup's close button while the personal assistant is open. */
body:has([data-testid="stDialog"] [role="dialog"])
  .st-key-sela_floating_launcher_v15 {
  visibility:hidden!important;
  pointer-events:none!important;
}
/* Keep the native SELA dialog scrollable without changing its content. */
div[data-testid="stDialog"] div[role="dialog"] {
  max-height:calc(100dvh - 30px)!important;
  overflow-y:auto!important;
}
@media(max-width:700px){
  .st-key-sela_floating_launcher_v15 {
    top:72px!important;
    right:12px!important;
  }
  .st-key-sela_floating_launcher_v15 button {
    min-height:49px!important;
    min-width:136px!important;
    font-size:13px!important;
    padding:6px 10px 6px 6px!important;
    gap:7px!important;
    border-radius:15px!important;
  }
  .st-key-sela_floating_launcher_v15 button::before {
    flex-basis:35px;
    width:35px;
    height:35px;
    border-radius:11px;
    font-size:20px;
  }
  .st-key-sela_floating_launcher_v15 button::after {
    font-size:9px;
    padding:4px 5px;
  }
}
@media(prefers-reduced-motion:reduce){
  .st-key-sela_floating_launcher_v15 button {transition:none!important;}
}
</style>
""", unsafe_allow_html=True)

# ==============================
# Parsing SLA setelah filter (TIDAK DIUBAH)
# ==============================
@st.cache_data(show_spinner=False, max_entries=12)
def _parse_sla_filtered_cached(source_version: str, period_keys: tuple, _filtered_input: pd.DataFrame, sla_names: tuple):
    """Reuse exact legacy parser result while version+period selection is unchanged."""
    output = _filtered_input.copy()
    for col in sla_names:
        output[col] = output[col].apply(parse_sla)
    return output

with st.status("\u23f1\ufe0f Memproses kolom SLA setelah filter...", expanded=False) as status:
    df_filtered = _parse_sla_filtered_cached(
        _sla_source_version,
        tuple(selected_periode),
        df_filtered,
        tuple(available_sla_cols),
    )
    status.update(label="\u2705 Parsing SLA selesai", state="complete")

# Preserve the original SLA upload before another tab can rebind df_raw.
# SELA's historical comparison must never use the separate nilai-transaksi sheet.
_sela_full_history_source = df_raw

import io, base64

def render_sparkline(data, width=180, height=60, color="#00eaff"):
    """Render sparkline sederhana (line chart kecil) sebagai PNG base64"""
    if not data or len(data) == 0:
        return ""
    fig, ax = plt.subplots(figsize=(width/100, height/100))
    ax.plot(data, color=color, linewidth=2, marker='o', markersize=3)
    ax.set_facecolor("none")
    ax.axis('off')
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    buf.seek(0)
    plt.close(fig)
    return f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"

import streamlit.components.v1 as components

# ==============================
# KPI Ringkasan (2x2 Digital Cards + Count-Up FIX)
# ==============================
st.markdown("## \U0001f4c8 Ringkasan")

jumlah_transaksi = len(df_filtered)
if "TOTAL WAKTU" in available_sla_cols and len(df_filtered) > 0:
    avg_total_days = float(df_filtered["TOTAL WAKTU"].mean()) / 86400
else:
    avg_total_days = 0.0
fastest_process = "Perbendaharaan"
valid_ratio = (df_filtered[periode_col].notna().mean() * 100.0) if len(df_filtered) > 0 else 0.0

html_code = f"""
<style>
.summary-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 18px;
    justify-items: center;
    margin: 15px auto 25px auto;
    max-width: 880px;
}}
.summary-card {{
    box-sizing: border-box;
    width: 100%;
    min-height: 116px;
    border-radius: 17px;
    padding: 17px 16px;
    text-align: center;
    color: #f8fcff;
    font-family: 'Segoe UI', Arial, sans-serif;
    border: 1px solid rgba(209,236,249,.20);
    box-shadow: 0 12px 25px rgba(11,38,75,.16);
    transition: transform .16s ease, box-shadow .16s ease;
}}
.summary-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 16px 31px rgba(11,38,75,.20);
}}
.summary-icon {{ font-size: 22px; margin-bottom: 6px; }}
.summary-label {{ font-size: 12px; font-weight: 750; opacity: .85; letter-spacing: 1px; text-transform: uppercase; }}
.summary-value {{ font-size: 25px; font-weight: 850; margin-top: 7px; letter-spacing: -.7px; }}
.card-1 {{ background: linear-gradient(125deg, #0c3156, #194d79); }}
.card-2 {{ background: linear-gradient(125deg, #07545f, #0c8e91); }}
.card-3 {{ background: linear-gradient(125deg, #293e6b, #405a94); }}
.card-4 {{ background: linear-gradient(125deg, #173956, #205f74); }}
@media(max-width:520px){{
    .summary-grid{{gap:10px;margin:8px auto 12px;}}
    .summary-card{{min-height:120px;padding:12px 9px;}}
    .summary-label{{font-size:10px;}}
    .summary-value{{font-size:18px;}}
}}
</style>

<div class="summary-grid">
  <div class="summary-card card-1">
    <div class="summary-icon">\U0001f9fe</div>
    <div class="summary-label">Jumlah Transaksi</div>
    <div id="val1" class="summary-value">0</div>
  </div>
  <div class="summary-card card-2">
    <div class="summary-icon">\u23f1\ufe0f</div>
    <div class="summary-label">Rata-rata TOTAL Waktu</div>
    <div id="val2" class="summary-value">0</div>
  </div>
  <div class="summary-card card-3">
    <div class="summary-icon">\u26a1</div>
    <div class="summary-label">Proses Tercepat</div>
    <div class="summary-value">{fastest_process}</div>
  </div>
  <div class="summary-card card-4">
    <div class="summary-icon">\u2705</div>
    <div class="summary-label">Kualitas Data</div>
    <div id="val4" class="summary-value">0</div>
  </div>
</div>

<script>
function animateValue(id, start, end, duration, decimals=0, suffix="") {{
    var obj = document.getElementById(id);
    if (!obj) return;
    var range = end - start;
    var current = start;
    var increment = range / 60;
    var stepTime = duration / 60;
    var timer = setInterval(function() {{
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {{
            current = end;
            clearInterval(timer);
        }}
        obj.innerHTML = Number(current).toFixed(decimals) + suffix;
    }}, stepTime);
}}

animateValue("val1", 0, {jumlah_transaksi}, 1000, 0, "");
animateValue("val2", 0, {avg_total_days:.2f}, 1000, 2, " hari");
animateValue("val4", 0, {valid_ratio:.1f}, 1000, 1, "%");
</script>
"""

components.html(html_code, height=350)

# ==============================
# Tabs untuk konten (TIDAK DIUBAH)
# ==============================
_SLA_TAB_LABELS = [
    "\U0001f50d Overview", "\U0001f9ee Per Proses", "\U0001f9fe Jenis Transaksi",
    "\U0001f3f7\ufe0f Vendor", "\U0001f4c8 Tren", "\U0001f4ca Jumlah Transaksi",
    "\U0001f4b0 Nilai Transaksi", "\U0001f4e5 Download Report", "\U0001f9e0 Analisis Data"
]
try:
    _SLA_LAZY_TABS = "on_change" in inspect.signature(st.tabs).parameters
except (ValueError, TypeError):
    _SLA_LAZY_TABS = False

# No UI changes: the original nine tab labels and their internal layout are preserved.
if _SLA_LAZY_TABS:
    _sla_main_tabs = st.tabs(_SLA_TAB_LABELS, on_change="rerun", key="sla_active_main_tab")
else:
    _sla_main_tabs = st.tabs(_SLA_TAB_LABELS)

tab_overview, tab_proses, tab_transaksi, tab_vendor, tab_tren, tab_jumlah, tab_nilai, tab_report, tab_analisis = _sla_main_tabs

# Keep explicit-key widget selections across tab changes in lazy-render mode.
# Streamlit normally cleans up widget state when its tab was not rendered.
if _SLA_LAZY_TABS:
    _sla_backup = st.session_state.setdefault('_sla_saved_widget_values', {})
    for _sla_key, _sla_value in list(_sla_backup.items()):
        if _sla_key not in st.session_state:
            st.session_state[_sla_key] = _sla_value


if (not _SLA_LAZY_TABS) or bool(getattr(tab_overview, "open", False)):
    with tab_overview:
        st.subheader("\U0001f4ca KPI Verifikasi Dokumen Penagihan")

        # Hitung rata-rata SLA Keuangan
        if "KEUANGAN" in df_filtered.columns and len(df_filtered) > 0:
            avg_keu_seconds = df_filtered["KEUANGAN"].mean()
            avg_keu_days = round(avg_keu_seconds / 86400, 2)  # format desimal hari
            avg_keu_text = seconds_to_sla_format(avg_keu_seconds)  # format hari jam menit detik
        else:
            avg_keu_seconds = None
            avg_keu_days = None
            avg_keu_text = "-"

        # Load target KPI dari file
        saved_kpi = load_kpi()

        # Input Target KPI (hanya admin)
        if is_admin:
            st.markdown("### \U0001f3af Atur Target KPI (Admin Only)")
            new_kpi = st.number_input(
                "Target KPI (hari, desimal)", 
                min_value=0.0, step=0.1,
                value=saved_kpi if saved_kpi else 1.5,
                key="target_kpi_input"
            )
            if st.button("\U0001f4be Simpan Target KPI"):
                save_kpi(new_kpi)
                st.success(f"Target KPI berhasil disimpan: {new_kpi} hari")
                saved_kpi = new_kpi
        else:
            if saved_kpi is None:
                st.info("Belum ada Target KPI yang ditentukan admin.")

        # Layout 3 kolom KPI
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Target KPI Verifikasi Dokumen</div>
                <div class="kpi-value">{saved_kpi if saved_kpi else "-" } hari</div>
            </div>
        """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Pencapaian</div>
                <div class="kpi-value">{avg_keu_text}</div>
                <div class="kpi-sub">({avg_keu_days if avg_keu_days is not None else "-"} hari)</div>
            </div>
        """, unsafe_allow_html=True)

        with col3:
            if saved_kpi and avg_keu_days is not None:
                if avg_keu_days <= saved_kpi:
                    st.markdown("""
                    <div class="kpi-card">
                        <div class="kpi-label">Status</div>
                        <div class="kpi-status-on">\u2705 ON TARGET</div>
                    </div>
                """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="kpi-card">
                        <div class="kpi-label">Status</div>
                        <div class="kpi-status-off">\u274c NOT ON TARGET</div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="kpi-card">
                    <div class="kpi-label">Status</div>
                    <div class="kpi-value">-</div>
                </div>
            """, unsafe_allow_html=True)

        # ==============================
        # Tabel Rata-rata SLA Keuangan per Periode (wide format)
        # ==============================
        if "KEUANGAN" in df_filtered.columns and len(df_filtered) > 0:
            st.markdown("<hr class='soft'/>", unsafe_allow_html=True)
            st.subheader("\U0001f4ca Tabel Rata-rata SLA Keuangan (Hari) per Periode")

            # Hitung rata-rata per periode
            trend_keu = df_filtered.groupby(df_filtered[periode_col].astype(str))["KEUANGAN"].mean().reset_index()
            trend_keu["PERIODE_SORTED"] = pd.Categorical(trend_keu[periode_col], categories=selected_periode, ordered=True)
            trend_keu = trend_keu.sort_values("PERIODE_SORTED")

            # Konversi ke hari desimal
            trend_keu["Rata-rata SLA (hari)"] = (trend_keu["KEUANGAN"] / 86400).round(2)

            # Bentuk tabel wide format
            table_data = pd.DataFrame(
                [trend_keu["Rata-rata SLA (hari)"].tolist()],
                columns=trend_keu[periode_col].tolist(),
                index=["SLA Verifikasi Dokumen Penagihan"]
            )

            # Tampilkan tabel dengan styling
            st.dataframe(table_data.style.format("{:.2f}"), use_container_width=True)

        # ==============================
        # Grafik SLA Keuangan per Periode (dengan label angka)
        # ==============================
        if "KEUANGAN" in df_filtered.columns and len(df_filtered) > 0:
            st.markdown("<hr class='soft'/>", unsafe_allow_html=True)
            st.subheader("\U0001f4c8 Trend Rata-rata SLA Keuangan per Periode")

            # Hitung rata-rata per periode
            trend_keu = df_filtered.groupby(df_filtered[periode_col].astype(str))["KEUANGAN"].mean().reset_index()
            trend_keu["PERIODE_SORTED"] = pd.Categorical(trend_keu[periode_col], categories=selected_periode, ordered=True)
            trend_keu = trend_keu.sort_values("PERIODE_SORTED")

            # Konversi ke hari desimal
            trend_keu["Rata-rata SLA (hari)"] = (trend_keu["KEUANGAN"] / 86400).round(2)

            # Plot line chart dengan label di dot
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(trend_keu[periode_col], trend_keu["Rata-rata SLA (hari)"], marker='o', color='#1f77b4')

            # Label angka
            for i, val in enumerate(trend_keu["Rata-rata SLA (hari)"]):
                ax.text(i, val, f"{val}", ha='center', va='bottom', fontsize=9, color="black", weight="bold")

            ax.set_title("Trend Rata-rata SLA Keuangan per Periode")
            ax.set_xlabel("Periode")
            ax.set_ylabel("Rata-rata SLA (hari)")
            ax.grid(True, linestyle='--', alpha=0.7)

            for label in ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')

            st.pyplot(fig)
        else:
            st.info("Tidak ada kolom SLA Keuangan yang bisa ditampilkan.")

if (not _SLA_LAZY_TABS) or bool(getattr(tab_proses, "open", False)):
    with tab_proses:
        if available_sla_cols:
            st.subheader("\U0001f4cc Rata-rata SLA per Proses (format hari jam menit detik)")
            rata_proses_seconds = df_filtered[available_sla_cols].mean()
            rata_proses = rata_proses_seconds.reset_index()
            rata_proses.columns = ["Proses", "Rata-rata (detik)"]
            rata_proses["Rata-rata SLA"] = rata_proses["Rata-rata (detik)"].apply(seconds_to_sla_format)
            # PREMIUM TABLE: murni presentasi, rata-rata existing tidak dimodifikasi.
            # Tabel Streamlit original tetap tersedia untuk sort/copy/audit.
            _slae_proc_names = [c for c in proses_grafik_cols if c in rata_proses_seconds.index]
            _slae_valid_proc = [c for c in _slae_proc_names if pd.notna(rata_proses_seconds[c])]
            _slae_fast = (min(_slae_valid_proc, key=lambda c: rata_proses_seconds[c])
                          if _slae_valid_proc else None)
            _slae_slow = (max(_slae_valid_proc, key=lambda c: rata_proses_seconds[c])
                          if _slae_valid_proc else None)
            _slae_total_seconds = (rata_proses_seconds.get("TOTAL WAKTU")
                                   if "TOTAL WAKTU" in rata_proses_seconds.index else None)
            _slae_total_days = (float(_slae_total_seconds) / 86400
                                if _slae_total_seconds is not None and pd.notna(_slae_total_seconds) else None)
            _slae_max_raw = max(
                [float(v) for v in rata_proses_seconds if pd.notna(v) and float(v) > 0],
                default=0.0,
            )
            _slae_proc_cards = [
                ("TAHAPAN DIPANTAU", str(len(_slae_proc_names)), "Di luar total end-to-end"),
                ("TAHAP TERCEPAT", (_slae_fast or "—").title(),
                 seconds_to_sla_format(rata_proses_seconds[_slae_fast]) if _slae_fast else "Belum tersedia"),
                ("DURASI TERTINGGI", (_slae_slow or "—").title(),
                 seconds_to_sla_format(rata_proses_seconds[_slae_slow]) if _slae_slow else "Belum tersedia"),
                ("TOTAL WAKTU", (f"{_slae_total_days:.2f}".replace(".", ",") + " hari")
                 if _slae_total_days is not None else "—", "Rata-rata end-to-end bila tersedia"),
            ]
            _slae_cards_html = "".join(
                '<div class="slae-kpi"><div class="slae-kpi-label">' + slae_html.escape(k) +
                '</div><div class="slae-kpi-value">' + slae_html.escape(v) +
                '</div><div class="slae-kpi-sub">' + slae_html.escape(d) + '</div></div>'
                for k, v, d in _slae_proc_cards
            )
            _slae_proc_rows = []
            for _, _slae_record in rata_proses.iterrows():
                _slae_name = str(_slae_record["Proses"])
                _slae_sec = _slae_record["Rata-rata (detik)"]
                _slae_ok = pd.notna(_slae_sec)
                _slae_days_str = (f"{float(_slae_sec)/86400:.2f}".replace(".", ",") + " hari") if _slae_ok else "—"
                _slae_pct = (max(0.0, min(100.0, float(_slae_sec) / _slae_max_raw * 100))
                             if _slae_ok and _slae_max_raw > 0 else 0.0)
                _slae_is_total = _slae_name == "TOTAL WAKTU"
                _slae_kind = "End-to-End" if _slae_is_total else "Tahapan proses"
                _slae_badge = "slae-pill slae-pill-e2e" if _slae_is_total else "slae-pill"
                _slae_proc_rows.append(
                    '<tr><td><div class="slae-label">' + slae_html.escape(_slae_name) +
                    '</div><div class="slae-hint"><span class="' + _slae_badge + '">' + _slae_kind +
                    '</span></div></td><td><span class="slae-duration">' +
                    slae_html.escape(str(_slae_record["Rata-rata SLA"])) +
                    '</span></td><td class="slae-numeric"><span class="slae-days">' + _slae_days_str +
                    '</span></td><td class="slae-numeric">' +
                    f'{int(df_filtered[_slae_name].count()):,}'.replace(',', '.') +
                    '</td><td><div class="slae-track" title="Skala relatif terhadap durasi rata-rata tertinggi">'
                    '<div class="slae-track-fill" style="width:' + f'{_slae_pct:.1f}' + '%"></div>'
                    '</div></td></tr>'
                )
            st.markdown(
                '<div class="slae-wrap"><div class="slae-kpis">' + _slae_cards_html +
                '</div><section class="slae-panel"><div class="slae-panel-head">'
                '<div class="slae-panel-title">Process SLA Performance Ledger</div>'
                '<div class="slae-panel-note">ASDP · PROCESS INTELLIGENCE</div></div>'
                '<div class="slae-scroll"><table class="slae-table"><thead><tr>'
                '<th>Proses</th><th>Rata-rata SLA</th><th style="text-align:right">Dalam Hari</th>'
                '<th style="text-align:right">Data Valid</th><th>Durasi Relatif</th>'
                '</tr></thead><tbody>' + ''.join(_slae_proc_rows) +
                '</tbody></table></div></section><div class="slae-foot">'
                'Bar menunjukkan skala relatif terhadap durasi rata-rata terbesar, bukan persentase '
                'kontribusi proses. Nilai berasal dari agregasi SLA existing; angka grafik dan laporan tidak diubah.'
                '</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander("🔎 Tabel original — sortir, salin & audit", expanded=False):
                st.dataframe(rata_proses[["Proses", "Rata-rata SLA"]], use_container_width=True)

            if proses_grafik_cols:
                fig2, ax2 = plt.subplots(figsize=(8, 4))
                values_hari = [rata_proses_seconds[col] / 86400 for col in proses_grafik_cols]
                ax2.bar(proses_grafik_cols, values_hari, color='#75c8ff')
                ax2.set_title("Rata-rata SLA per Proses (hari)")
                ax2.set_ylabel("Rata-rata SLA (hari)")
                ax2.set_xlabel("Proses")
                ax2.grid(axis='y', linestyle='--', alpha=0.7)
                st.pyplot(fig2)

if (not _SLA_LAZY_TABS) or bool(getattr(tab_transaksi, "open", False)):
    with tab_transaksi:
        import os
        import io
        import html
        import base64
        import numpy as np
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        import streamlit.components.v1 as components
        from PIL import Image, ImageDraw, ImageFont, ImageFilter

        st.subheader("\U0001f9fe Analisis SLA per Jenis Transaksi")

        # =====================================================
        # LOCAL HELPERS
        # =====================================================
        def trx_fmt_int(x):
            try:
                return f"{int(x):,}".replace(",", ".")
            except Exception:
                return "-"

        def trx_fmt_hari(x):
            try:
                if x is None or pd.isna(x):
                    return "-"
                return f"{float(x):.2f} hari"
            except Exception:
                return "-"

        def trx_seconds_to_text(seconds):
            try:
                if seconds is None or pd.isna(seconds):
                    return "-"
                seconds = int(round(float(seconds)))
                days = seconds // 86400
                seconds %= 86400
                hours = seconds // 3600
                seconds %= 3600
                minutes = seconds // 60
                secs = seconds % 60

                parts = []
                if days > 0:
                    parts.append(f"{days} hari")
                if hours > 0 or days > 0:
                    parts.append(f"{hours} jam")
                if minutes > 0 or hours > 0 or days > 0:
                    parts.append(f"{minutes} menit")
                parts.append(f"{secs} detik")
                return " ".join(parts)
            except Exception:
                return "-"

        def trx_safe_text(x, max_len=55):
            x = str(x)
            return x if len(x) <= max_len else x[:max_len] + "..."

        def trx_html_list(items, max_items=None):
            if not items:
                return "<li>Belum ada insight yang dapat ditampilkan.</li>"
            if max_items:
                items = items[:max_items]
            return "".join([f"<li>{html.escape(str(x))}</li>" for x in items])


        def trx_norm_col_name(col):
            """Normalisasi nama kolom agar deteksi kolom tahan terhadap spasi/titik/underscore."""
            s = str(col).upper()
            s = re.sub(r"[^A-Z0-9]+", " ", s)
            return re.sub(r"\s+", " ", s).strip()

        def trx_detect_permohonan_col(df):
            """Deteksi kolom Nomor Permohonan secara fleksibel."""
            exact_candidates = {
                "NOMOR PERMOHONAN",
                "NO PERMOHONAN",
                "NO PERMOHONAN DOKUMEN",
                "NOMOR PERMINTAAN",
                "NO PERMINTAAN",
                "NO REQUEST",
                "REQUEST NUMBER",
            }

            for col in df.columns:
                norm = trx_norm_col_name(col)
                if norm in exact_candidates:
                    return col

            for col in df.columns:
                norm = trx_norm_col_name(col)
                has_number_hint = any(token in norm.split() for token in ["NO", "NOMOR", "NUMBER"])
                has_request_hint = any(token in norm for token in ["PERMOHONAN", "PERMINTAAN", "REQUEST"])
                if has_number_hint and has_request_hint:
                    return col

            return None

        def trx_sorted_unique(series):
            """Ambil unique value sebagai string, urut natural, dan tetap aman untuk NaN."""
            values = (
                series
                .dropna()
                .astype(str)
                .map(str.strip)
            )
            values = [v for v in values.unique().tolist() if v and v.upper() not in ["NAN", "NONE"]]

            def natural_key(x):
                return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(x))]

            return sorted(values, key=natural_key)

        def trx_apply_main_filters(df_input, nomor_col, selected_permohonan, selected_jenis_data):
            """Filter utama berbasis baris transaksi, sebelum proses agregasi jenis transaksi."""
            df_out = df_input.copy()

            if nomor_col and selected_permohonan and "ALL" not in selected_permohonan:
                df_out = df_out[
                    df_out[nomor_col]
                    .astype(str)
                    .str.strip()
                    .isin([str(x).strip() for x in selected_permohonan])
                ].copy()

            if selected_jenis_data and "ALL" not in selected_jenis_data:
                df_out = df_out[
                    df_out["JENIS TRANSAKSI"]
                    .astype(str)
                    .str.strip()
                    .isin([str(x).strip() for x in selected_jenis_data])
                ].copy()

            return df_out

        def trx_filter_label(selected_values, all_label="ALL"):
            if not selected_values or all_label in selected_values:
                return "ALL"
            if len(selected_values) <= 3:
                return ", ".join([str(x) for x in selected_values])
            return f"{len(selected_values)} pilihan"

        def trx_get_font(size=28, bold=False):
            candidates = []
            if bold:
                candidates = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "C:/Windows/Fonts/arialbd.ttf",
                    "arialbd.ttf",
                ]
            else:
                candidates = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "C:/Windows/Fonts/arial.ttf",
                    "arial.ttf",
                ]

            for path in candidates:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass

            return ImageFont.load_default()

        def trx_resample_filter():
            try:
                return Image.Resampling.LANCZOS
            except Exception:
                return Image.LANCZOS

        def trx_base_dir():
            try:
                return os.path.dirname(os.path.abspath(__file__))
            except Exception:
                return os.getcwd()

        def trx_logo_paths():
            base_dir = trx_base_dir()
            return [
                os.path.join(base_dir, "asdp_logo.png"),
                os.path.join(os.getcwd(), "asdp_logo.png"),
                "asdp_logo.png",
            ]

        def trx_load_logo_image():
            for path in trx_logo_paths():
                if os.path.exists(path):
                    try:
                        return Image.open(path).convert("RGBA")
                    except Exception:
                        pass
            return None

        def trx_logo_data_uri():
            for path in trx_logo_paths():
                if os.path.exists(path):
                    try:
                        with open(path, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("utf-8")
                        return f"data:image/png;base64,{b64}"
                    except Exception:
                        pass
            return ""

        def trx_draw_wrapped_text(draw, text, xy, font, fill, max_width, line_gap=7):
            x, y = xy
            words = str(text).split()
            lines = []
            current = ""

            for word in words:
                test = current + (" " if current else "") + word
                bbox = draw.textbbox((0, 0), test, font=font)
                width = bbox[2] - bbox[0]

                if width <= max_width:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word

            if current:
                lines.append(current)

            for line in lines:
                draw.text((x, y), line, font=font, fill=fill)
                bbox = draw.textbbox((0, 0), line, font=font)
                y += (bbox[3] - bbox[1]) + line_gap

            return y

        def trx_round_rect(draw, box, radius, fill, outline=None, width=1):
            draw.rounded_rectangle(
                box,
                radius=radius,
                fill=fill,
                outline=outline,
                width=width,
            )

        def trx_gradient_bg(width, height):
            img = Image.new("RGB", (width, height), "#07111f")
            draw = ImageDraw.Draw(img)

            top = (4, 13, 33)
            mid = (10, 38, 84)
            bottom = (0, 105, 120)

            for y in range(height):
                t = y / max(height - 1, 1)
                if t < 0.55:
                    k = t / 0.55
                    r = int(top[0] * (1 - k) + mid[0] * k)
                    g = int(top[1] * (1 - k) + mid[1] * k)
                    b = int(top[2] * (1 - k) + mid[2] * k)
                else:
                    k = (t - 0.55) / 0.45
                    r = int(mid[0] * (1 - k) + bottom[0] * k)
                    g = int(mid[1] * (1 - k) + bottom[1] * k)
                    b = int(mid[2] * (1 - k) + bottom[2] * k)

                draw.line([(0, y), (width, y)], fill=(r, g, b))

            return img.convert("RGBA")

        # =====================================================
        # AI INSIGHT
        # =====================================================
        def trx_generate_ai_insight(trx_ai_base, proses_bottleneck_cols):
            if trx_ai_base is None or trx_ai_base.empty:
                return {
                    "headline": "Belum ada data yang cukup untuk menghasilkan insight.",
                    "summary": [],
                    "risks": [],
                    "recommendations": [],
                    "priority_df": pd.DataFrame(),
                    "status_label": "NO DATA",
                    "status_class": "trx-status-neutral",
                    "p1_count": 0,
                    "bottleneck_proses": "-",
                    "bottleneck_value": np.nan,
                }

            df_ai = trx_ai_base.copy()

            fastest = df_ai.sort_values("SLA Utama (hari)", ascending=True).iloc[0]
            slowest = df_ai.sort_values("SLA Utama (hari)", ascending=False).iloc[0]
            biggest = df_ai.sort_values("Jumlah Transaksi", ascending=False).iloc[0]

            avg_sla = df_ai["SLA Utama (hari)"].mean()
            max_sla = df_ai["SLA Utama (hari)"].max()

            proses_hari_cols = [
                f"{p} (hari)"
                for p in proses_bottleneck_cols
                if f"{p} (hari)" in df_ai.columns
            ]

            bottleneck_proses = "-"
            bottleneck_value = np.nan
            bottleneck_text = "-"

            if proses_hari_cols:
                proses_mean = df_ai[proses_hari_cols].mean().dropna().sort_values(ascending=False)
                if not proses_mean.empty:
                    bottleneck_col = proses_mean.index[0]
                    bottleneck_proses = bottleneck_col.replace(" (hari)", "")
                    bottleneck_value = proses_mean.iloc[0]
                    bottleneck_text = f"{bottleneck_proses} dengan rata-rata {trx_fmt_hari(bottleneck_value)}"

            sla_threshold = df_ai["SLA Utama (hari)"].median()
            volume_threshold = df_ai["Jumlah Transaksi"].median()

            def priority_label(row):
                high_sla = row["SLA Utama (hari)"] >= sla_threshold
                high_vol = row["Jumlah Transaksi"] >= volume_threshold

                if high_sla and high_vol:
                    return "Prioritas 1 \u2014 SLA tinggi & volume besar"
                elif high_sla and not high_vol:
                    return "Prioritas 2 \u2014 SLA tinggi"
                elif not high_sla and high_vol:
                    return "Prioritas 3 \u2014 Volume besar"
                else:
                    return "Normal"

            df_ai["Prioritas AI"] = df_ai.apply(priority_label, axis=1)

            priority_order = {
                "Prioritas 1 \u2014 SLA tinggi & volume besar": 1,
                "Prioritas 2 \u2014 SLA tinggi": 2,
                "Prioritas 3 \u2014 Volume besar": 3,
                "Normal": 4,
            }

            df_ai["__PRIORITY_SORT__"] = df_ai["Prioritas AI"].map(priority_order).fillna(9)

            priority_df = (
                df_ai[
                    [
                        "JENIS TRANSAKSI",
                        "Jumlah Transaksi",
                        "SLA Utama (hari)",
                        "Prioritas AI",
                        "__PRIORITY_SORT__",
                    ]
                ]
                .sort_values(
                    by=["__PRIORITY_SORT__", "SLA Utama (hari)", "Jumlah Transaksi"],
                    ascending=[True, False, False],
                )
                .drop(columns=["__PRIORITY_SORT__"])
            )

            p1_df = df_ai[df_ai["Prioritas AI"].str.contains("Prioritas 1", na=False)]
            p1_count = len(p1_df)

            if p1_count >= 3:
                status_label = "CRITICAL"
                status_class = "trx-status-critical"
            elif p1_count >= 1:
                status_label = "WATCHLIST"
                status_class = "trx-status-watch"
            else:
                status_label = "CONTROLLED"
                status_class = "trx-status-good"

            if not p1_df.empty:
                top_priority = p1_df.sort_values(
                    ["SLA Utama (hari)", "Jumlah Transaksi"],
                    ascending=[False, False],
                ).iloc[0]

                headline = (
                    f"Fokus utama perbaikan adalah jenis transaksi "
                    f"\u201c{trx_safe_text(top_priority['JENIS TRANSAKSI'])}\u201d karena memiliki kombinasi "
                    f"SLA relatif tinggi ({trx_fmt_hari(top_priority['SLA Utama (hari)'])}) "
                    f"dan volume transaksi besar ({trx_fmt_int(top_priority['Jumlah Transaksi'])} transaksi)."
                )
            else:
                headline = (
                    f"Secara umum, SLA jenis transaksi relatif terkendali. "
                    f"Namun jenis transaksi \u201c{trx_safe_text(slowest['JENIS TRANSAKSI'])}\u201d tetap perlu dimonitor "
                    f"karena menjadi kategori dengan SLA paling lama, yaitu "
                    f"{trx_fmt_hari(slowest['SLA Utama (hari)'])}."
                )

            summary = [
                f"Jenis transaksi tercepat adalah \u201c{trx_safe_text(fastest['JENIS TRANSAKSI'])}\u201d dengan SLA rata-rata {trx_fmt_hari(fastest['SLA Utama (hari)'])}.",
                f"Jenis transaksi terlama adalah \u201c{trx_safe_text(slowest['JENIS TRANSAKSI'])}\u201d dengan SLA rata-rata {trx_fmt_hari(slowest['SLA Utama (hari)'])}.",
                f"Jenis transaksi dengan volume terbesar adalah \u201c{trx_safe_text(biggest['JENIS TRANSAKSI'])}\u201d sebanyak {trx_fmt_int(biggest['Jumlah Transaksi'])} transaksi.",
                f"Bottleneck proses terbesar terindikasi pada proses {bottleneck_text}.",
            ]

            risks = []

            if pd.notna(avg_sla) and avg_sla > 0 and pd.notna(max_sla) and max_sla > avg_sla * 1.5:
                risks.append(
                    f"Terdapat outlier SLA: kategori \u201c{trx_safe_text(slowest['JENIS TRANSAKSI'])}\u201d jauh di atas rata-rata keseluruhan."
                )

            if p1_count > 0:
                risks.append(
                    f"Terdapat {p1_count} jenis transaksi prioritas tinggi karena SLA dan volume sama-sama relatif besar."
                )

            if bottleneck_proses != "-" and not pd.isna(bottleneck_value):
                risks.append(
                    f"Proses {bottleneck_proses} berpotensi menjadi titik perlambatan utama pada siklus dokumen."
                )

            if not risks:
                risks.append("Tidak terdapat anomali besar pada data yang sedang ditampilkan.")

            recommendations = []

            if not p1_df.empty:
                top3 = p1_df.sort_values(
                    ["SLA Utama (hari)", "Jumlah Transaksi"],
                    ascending=[False, False],
                ).head(3)

                focus_names = ", ".join(
                    [f"\u201c{trx_safe_text(x)}\u201d" for x in top3["JENIS TRANSAKSI"].tolist()]
                )

                recommendations.append(
                    f"Prioritaskan review proses untuk {focus_names}, karena kategori tersebut paling berdampak terhadap SLA keseluruhan."
                )
            else:
                recommendations.append(
                    f"Fokus monitoring cukup diarahkan pada kategori dengan SLA tertinggi, yaitu \u201c{trx_safe_text(slowest['JENIS TRANSAKSI'])}\u201d."
                )

            if bottleneck_proses != "-":
                recommendations.append(
                    f"Lakukan pendalaman pada proses {bottleneck_proses}, termasuk cek antrean dokumen, approval, kelengkapan dokumen, dan pola keterlambatan per vendor/unit."
                )

            recommendations.append(
                "Gunakan bubble matrix untuk menentukan quick win: dahulukan titik kanan-atas karena menunjukkan volume besar dan SLA tinggi."
            )

            return {
                "headline": headline,
                "summary": summary,
                "risks": risks,
                "recommendations": recommendations,
                "priority_df": priority_df,
                "status_label": status_label,
                "status_class": status_class,
                "p1_count": p1_count,
                "bottleneck_proses": bottleneck_proses,
                "bottleneck_value": bottleneck_value,
            }

        # =====================================================
        # CHART BUILDERS
        # =====================================================
        def trx_build_rank_fig(trx_view, sla_utama_label):
            fig = px.bar(
                trx_view.sort_values("SLA Utama (hari)", ascending=True),
                x="SLA Utama (hari)",
                y="JENIS TRANSAKSI",
                orientation="h",
                text="SLA Utama (hari)",
                color="SLA Utama (hari)",
                color_continuous_scale="Tealrose",
                hover_data={"Jumlah Transaksi": True, "SLA Utama (hari)": ":.2f"},
                title=f"Ranking Rata-rata SLA \u2014 Acuan: {sla_utama_label}",
            )

            fig.update_traces(
                texttemplate="%{text:.2f} hari",
                textposition="outside",
                marker_line_width=0,
            )

            fig.update_layout(
                height=max(430, 42 * len(trx_view)),
                xaxis_title="Rata-rata SLA (hari)",
                yaxis_title="Jenis Transaksi",
                coloraxis_showscale=False,
                margin=dict(l=20, r=80, t=70, b=30),
                title_font=dict(size=20),
            )

            return fig

        def trx_build_heat_fig(trx_view, chart_proses_cols):
            value_cols = [
                f"{c} (hari)"
                for c in chart_proses_cols
                if f"{c} (hari)" in trx_view.columns
            ]

            if not value_cols:
                return None

            heatmap_data = trx_view.set_index("JENIS TRANSAKSI")[value_cols].copy()
            heatmap_data.columns = [c.replace(" (hari)", "") for c in value_cols]

            fig = px.imshow(
                heatmap_data,
                text_auto=".2f",
                aspect="auto",
                color_continuous_scale="Turbo",
                title="Peta Panas Rata-rata SLA: Jenis Transaksi vs Proses",
            )

            fig.update_layout(
                height=max(430, 38 * len(heatmap_data)),
                xaxis_title="Proses",
                yaxis_title="Jenis Transaksi",
                margin=dict(l=20, r=20, t=70, b=40),
                title_font=dict(size=20),
            )

            fig.update_traces(
                hovertemplate="<b>%{y}</b><br>Proses: %{x}<br>SLA: %{z:.2f} hari<extra></extra>"
            )

            return fig

        def trx_build_group_fig(trx_long_view):
            fig = px.bar(
                trx_long_view,
                x="JENIS TRANSAKSI",
                y="Rata-rata SLA (hari)",
                color="Proses",
                barmode="group",
                text="Rata-rata SLA (hari)",
                title="Rata-rata SLA Masing-masing Proses per Jenis Transaksi",
                hover_data={"Jumlah Transaksi": True, "Rata-rata SLA (hari)": ":.2f"},
            )

            fig.update_traces(
                texttemplate="%{text:.1f}",
                textposition="outside",
            )

            fig.update_layout(
                height=560,
                xaxis_title="Jenis Transaksi",
                yaxis_title="Rata-rata SLA (hari)",
                legend_title="Proses",
                margin=dict(l=20, r=20, t=70, b=140),
                title_font=dict(size=20),
                xaxis_tickangle=-35,
            )

            return fig

        def trx_build_bubble_fig(trx_view):
            median_volume = trx_view["Jumlah Transaksi"].median()
            median_sla = trx_view["SLA Utama (hari)"].median()

            fig = px.scatter(
                trx_view,
                x="Jumlah Transaksi",
                y="SLA Utama (hari)",
                size="Jumlah Transaksi",
                color="SLA Utama (hari)",
                color_continuous_scale="Plasma",
                hover_name="JENIS TRANSAKSI",
                text="JENIS TRANSAKSI",
                size_max=58,
                title="Peta Prioritas: Volume Besar dan SLA Tinggi",
            )

            fig.add_vline(
                x=median_volume,
                line_dash="dash",
                line_color="gray",
                annotation_text="Median Volume",
                annotation_position="top left",
            )

            fig.add_hline(
                y=median_sla,
                line_dash="dash",
                line_color="gray",
                annotation_text="Median SLA",
                annotation_position="bottom right",
            )

            fig.update_traces(
                textposition="top center",
                marker=dict(opacity=0.78, line=dict(width=1, color="white")),
            )

            fig.update_layout(
                height=580,
                xaxis_title="Jumlah Transaksi",
                yaxis_title="Rata-rata SLA (hari)",
                coloraxis_colorbar_title="SLA Hari",
                margin=dict(l=20, r=20, t=70, b=40),
                title_font=dict(size=20),
            )

            return fig

        def trx_build_donut_fig(trx_view):
            fig = px.pie(
                trx_view,
                values="Jumlah Transaksi",
                names="JENIS TRANSAKSI",
                hole=0.58,
                title="Komposisi Transaksi berdasarkan Jenis Transaksi",
            )

            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                pull=[0.03] * len(trx_view),
            )

            fig.update_layout(
                height=530,
                margin=dict(l=20, r=20, t=70, b=30),
                title_font=dict(size=20),
                legend_title="Jenis Transaksi",
            )

            return fig

        def trx_build_process_fig(data_proses, proses):
            col_hari = f"{proses} (hari)"

            fig = px.bar(
                data_proses,
                x=col_hari,
                y="JENIS TRANSAKSI",
                orientation="h",
                text=col_hari,
                color=col_hari,
                color_continuous_scale="Blues",
                title=f"SLA {proses}",
            )

            fig.update_traces(
                texttemplate="%{text:.2f}",
                textposition="outside",
                marker_line_width=0,
            )

            fig.update_layout(
                height=max(360, 32 * len(data_proses)),
                xaxis_title="Hari",
                yaxis_title="",
                coloraxis_showscale=False,
                margin=dict(l=10, r=55, t=55, b=25),
                title_font=dict(size=16),
            )

            return fig

        def trx_build_detail_fig(detail_chart, selected_detail):
            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=detail_chart["Proses"],
                    y=detail_chart["Rata-rata SLA (hari)"],
                    text=detail_chart["Rata-rata SLA (hari)"],
                    texttemplate="%{text:.2f} hari",
                    textposition="outside",
                    marker=dict(
                        color=detail_chart["Rata-rata SLA (hari)"],
                        colorscale="Viridis",
                        line=dict(width=0),
                    ),
                )
            )

            fig.update_layout(
                title=f"Profil SLA per Proses \u2014 {selected_detail}",
                height=470,
                xaxis_title="Proses",
                yaxis_title="Rata-rata SLA (hari)",
                margin=dict(l=20, r=20, t=70, b=40),
                title_font=dict(size=20),
            )

            return fig

        # =====================================================
        # EXECUTIVE IMAGE + PDF
        # =====================================================
        def trx_make_summary_image(trx_exec_base, ai_result, sla_utama_label, start_periode, end_periode):
            W, H = 1920, 1080

            img = trx_gradient_bg(W, H)
            draw = ImageDraw.Draw(img)

            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            gd.ellipse((-220, -180, 520, 520), fill=(0, 234, 255, 55))
            gd.ellipse((1320, 650, 2150, 1420), fill=(56, 239, 125, 45))
            gd.ellipse((1280, -220, 2100, 480), fill=(255, 65, 108, 28))
            glow = glow.filter(ImageFilter.GaussianBlur(22))

            img = Image.alpha_composite(img, glow)
            draw = ImageDraw.Draw(img)

            font_title = trx_get_font(54, True)
            font_sub = trx_get_font(22, False)
            font_h = trx_get_font(28, True)
            font_kpi_label = trx_get_font(18, True)
            font_kpi_value = trx_get_font(36, True)
            font_body = trx_get_font(21, False)
            font_body_bold = trx_get_font(21, True)
            font_small = trx_get_font(15, False)
            font_badge = trx_get_font(21, True)

            exec_df = trx_exec_base.copy()

            total_jenis_exec = exec_df["JENIS TRANSAKSI"].nunique()
            total_trx_exec = int(exec_df["Jumlah Transaksi"].sum())
            avg_sla_exec = float(exec_df["SLA Utama (hari)"].mean())

            fastest_exec = exec_df.sort_values("SLA Utama (hari)", ascending=True).iloc[0]
            slowest_exec = exec_df.sort_values("SLA Utama (hari)", ascending=False).iloc[0]
            biggest_exec = exec_df.sort_values("Jumlah Transaksi", ascending=False).iloc[0]

            priority_df_exec = ai_result.get("priority_df", pd.DataFrame()).copy()
            p1_count = ai_result.get("p1_count", 0)
            status_label = ai_result.get("status_label", "CONTROLLED")
            bottleneck_proses = ai_result.get("bottleneck_proses", "-")
            bottleneck_value = ai_result.get("bottleneck_value", np.nan)
            headline = ai_result.get("headline", "-")
            reco_items = ai_result.get("recommendations", [])[:3]

            if status_label == "CRITICAL":
                status_fill = (255, 65, 108, 235)
                status_outline = (255, 180, 195, 255)
            elif status_label == "WATCHLIST":
                status_fill = (255, 180, 60, 235)
                status_outline = (255, 235, 150, 255)
            else:
                status_fill = (40, 200, 145, 235)
                status_outline = (160, 255, 210, 255)

            logo = trx_load_logo_image()
            title_x = 70

            if logo is not None:
                logo = logo.copy()
                logo.thumbnail((210, 82), trx_resample_filter())
                img.alpha_composite(logo, (70, 42))
                title_x = 310

            draw.text((title_x, 52), "EXECUTIVE SUMMARY", font=font_title, fill=(255, 255, 255, 255))
            draw.text(
                (title_x + 3, 122),
                f"SLA Jenis Transaksi | Periode {start_periode} s.d. {end_periode} | Acuan: {sla_utama_label}",
                font=font_sub,
                fill=(210, 235, 255, 235),
            )

            badge_box = (1495, 58, 1835, 118)
            trx_round_rect(draw, badge_box, 30, status_fill, status_outline, 2)

            bbox = draw.textbbox((0, 0), status_label, font=font_badge)
            draw.text(
                (
                    badge_box[0] + (badge_box[2] - badge_box[0] - (bbox[2] - bbox[0])) / 2,
                    badge_box[1] + 15,
                ),
                status_label,
                font=font_badge,
                fill=(255, 255, 255, 255),
            )

            headline_box = (70, 170, 1850, 300)
            trx_round_rect(draw, headline_box, 30, (10, 25, 55, 235), (0, 234, 255, 125), 3)

            trx_draw_wrapped_text(
                draw,
                headline,
                (105, 205),
                trx_get_font(26, True),
                (255, 255, 255, 245),
                1705,
                9,
            )

            kpis = [
                ("TOTAL TRANSAKSI", trx_fmt_int(total_trx_exec), "Filter jenis transaksi aktif"),
                ("JENIS TRANSAKSI", trx_fmt_int(total_jenis_exec), "Kategori dianalisis"),
                ("RATA-RATA SLA", trx_fmt_hari(avg_sla_exec), "SLA utama"),
                ("PRIORITAS TINGGI", trx_fmt_int(p1_count), "SLA tinggi & volume besar"),
            ]

            card_y = 330
            card_w = 420
            card_h = 138
            card_gap = 35

            for i, (label, value, sub) in enumerate(kpis):
                x = 70 + i * (card_w + card_gap)
                box = (x, card_y, x + card_w, card_y + card_h)

                trx_round_rect(draw, box, 26, (10, 25, 55, 230), (255, 255, 255, 95), 2)

                draw.text((x + 28, card_y + 24), label, font=font_kpi_label, fill=(130, 230, 255, 255))
                draw.text((x + 28, card_y + 58), value, font=font_kpi_value, fill=(255, 255, 255, 255))
                draw.text((x + 28, card_y + 108), sub, font=font_small, fill=(205, 225, 240, 220))

            left_box = (70, 505, 1050, 955)
            trx_round_rect(draw, left_box, 30, (10, 25, 55, 230), (255, 255, 255, 85), 2)

            draw.text((105, 535), "Executive Notes", font=font_h, fill=(255, 255, 255, 255))

            notes = [
                f"Jenis tercepat: {trx_safe_text(fastest_exec['JENIS TRANSAKSI'], 54)} ({trx_fmt_hari(fastest_exec['SLA Utama (hari)'])}).",
                f"Jenis terlama: {trx_safe_text(slowest_exec['JENIS TRANSAKSI'], 54)} ({trx_fmt_hari(slowest_exec['SLA Utama (hari)'])}).",
                f"Volume terbesar: {trx_safe_text(biggest_exec['JENIS TRANSAKSI'], 54)} ({trx_fmt_int(biggest_exec['Jumlah Transaksi'])} trx).",
                f"Bottleneck proses: {bottleneck_proses}"
                + ("" if pd.isna(bottleneck_value) else f" ({trx_fmt_hari(bottleneck_value)})."),
            ]

            y = 585

            for note in notes:
                draw.text((112, y), "\u2022", font=font_body_bold, fill=(0, 234, 255, 255))
                y = trx_draw_wrapped_text(
                    draw,
                    note,
                    (140, y),
                    font_body,
                    (245, 250, 255, 245),
                    850,
                    6,
                )
                y += 8

            draw.text((105, 760), "Recommended Actions", font=font_h, fill=(255, 255, 255, 255))

            y = 810

            if not reco_items:
                reco_items = ["Lakukan monitoring berkala terhadap jenis transaksi dengan SLA tertinggi."]

            for reco in reco_items:
                draw.text((112, y), "\u2713", font=font_body_bold, fill=(56, 239, 125, 255))
                y = trx_draw_wrapped_text(
                    draw,
                    reco,
                    (145, y),
                    font_body,
                    (245, 250, 255, 245),
                    830,
                    6,
                )
                y += 8

            right_box = (1090, 505, 1850, 955)
            trx_round_rect(draw, right_box, 30, (10, 25, 55, 230), (255, 255, 255, 85), 2)

            draw.text((1125, 535), "Top Priority Transactions", font=font_h, fill=(255, 255, 255, 255))

            if priority_df_exec.empty:
                priority_df_exec = exec_df[
                    ["JENIS TRANSAKSI", "Jumlah Transaksi", "SLA Utama (hari)"]
                ].copy()
                priority_df_exec["Prioritas AI"] = "Prioritas belum tersedia"

            top_priority = priority_df_exec.head(5).copy()

            max_sla = top_priority["SLA Utama (hari)"].max()
            max_sla = max_sla if pd.notna(max_sla) and max_sla > 0 else 1

            y = 595

            for _, row in top_priority.iterrows():
                name = trx_safe_text(row["JENIS TRANSAKSI"], 40)
                sla_val = float(row["SLA Utama (hari)"])
                trx_val = int(row["Jumlah Transaksi"])
                prio = str(row.get("Prioritas AI", ""))

                row_box = (1125, y, 1815, y + 62)
                trx_round_rect(draw, row_box, 18, (18, 42, 88, 245), (0, 234, 255, 90), 1)

                draw.text((1148, y + 9), name, font=trx_get_font(19, True), fill=(255, 255, 255, 250))
                draw.text((1148, y + 35), prio[:48], font=trx_get_font(14, False), fill=(200, 225, 240, 220))

                bar_x = 1515
                bar_y = y + 40
                bar_w = 170
                bar_h = 9

                trx_round_rect(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), 5, (255, 255, 255, 55), None, 1)

                fill_w = int(bar_w * min(sla_val / max_sla, 1))

                trx_round_rect(draw, (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), 5, (0, 234, 255, 240), None, 1)

                draw.text((1705, y + 9), trx_fmt_hari(sla_val), font=trx_get_font(16, True), fill=(255, 255, 255, 245))
                draw.text((1705, y + 34), f"{trx_fmt_int(trx_val)} trx", font=trx_get_font(14, False), fill=(200, 225, 240, 220))

                y += 72

            draw.text(
                (70, 1005),
                "Generated automatically from Tab Jenis Transaksi filter.",
                font=font_small,
                fill=(210, 230, 245, 190),
            )

            draw.text(
                (1415, 1005),
                "SLA Payment Analyzer | Executive View",
                font=font_small,
                fill=(210, 230, 245, 190),
            )

            return img.convert("RGB")

        def trx_image_to_png_bytes(img):
            out_png = io.BytesIO()
            img.save(out_png, format="PNG", quality=95)
            return out_png.getvalue()

        def trx_make_placeholder_page(title, message):
            W, H = 1920, 1080
            page = trx_gradient_bg(W, H)
            draw = ImageDraw.Draw(page)

            trx_round_rect(draw, (90, 100, 1830, 980), 35, (10, 25, 55, 230), (0, 234, 255, 100), 2)

            draw.text((140, 150), title, font=trx_get_font(44, True), fill=(255, 255, 255, 255))

            trx_draw_wrapped_text(
                draw,
                message,
                (140, 240),
                trx_get_font(26, False),
                (230, 245, 255, 230),
                1600,
                10,
            )

            return page.convert("RGB")

        def trx_fig_to_pdf_page(fig, title):
            W, H = 1920, 1080
            page = trx_gradient_bg(W, H)
            draw = ImageDraw.Draw(page)

            try:
                png_bytes = fig.to_image(
                    format="png",
                    width=1600,
                    height=820,
                    scale=2,
                )
                chart_img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
            except Exception as e:
                return trx_make_placeholder_page(
                    title,
                    "Chart tidak dapat dirender ke PDF. Pastikan dependency 'kaleido' sudah masuk ke requirements.txt.\n\nDetail error: "
                    + str(e),
                )

            draw.text((70, 48), title, font=trx_get_font(42, True), fill=(255, 255, 255, 255))

            trx_round_rect(
                draw,
                (70, 115, 1850, 1015),
                28,
                (245, 250, 255, 245),
                (0, 234, 255, 95),
                2,
            )

            chart_img.thumbnail((1710, 840), trx_resample_filter())

            x = 70 + (1780 - chart_img.width) // 2
            y = 135 + (860 - chart_img.height) // 2

            page.alpha_composite(chart_img, (x, y))

            return page.convert("RGB")

        def trx_table_pages(df, title, subtitle="", rows_per_page=24, max_pages=8):
            if df is None or df.empty:
                return [trx_make_placeholder_page(title, "Tidak ada data tabel yang dapat ditampilkan.")]

            df_show = df.copy().astype(str)
            pages = []
            total_rows = len(df_show)

            chunks = [
                df_show.iloc[i:i + rows_per_page]
                for i in range(0, total_rows, rows_per_page)
            ][:max_pages]

            for page_idx, chunk in enumerate(chunks, start=1):
                W, H = 1920, 1080
                page = trx_gradient_bg(W, H)
                draw = ImageDraw.Draw(page)

                draw.text((70, 45), title, font=trx_get_font(42, True), fill=(255, 255, 255, 255))

                if subtitle:
                    draw.text((72, 98), subtitle, font=trx_get_font(20, False), fill=(210, 235, 255, 220))

                draw.text(
                    (1560, 98),
                    f"Page {page_idx}/{len(chunks)}",
                    font=trx_get_font(20, True),
                    fill=(210, 235, 255, 220),
                )

                box = (70, 140, 1850, 1010)
                trx_round_rect(draw, box, 28, (10, 25, 55, 230), (0, 234, 255, 90), 2)

                cols = list(chunk.columns)
                table_x = 105
                table_y = 180
                table_w = 1710
                row_h = 31
                header_h = 38
                col_w = max(120, table_w // max(len(cols), 1))

                for j, col in enumerate(cols):
                    x = table_x + j * col_w
                    if x >= table_x + table_w:
                        continue

                    draw.rectangle(
                        (
                            x,
                            table_y,
                            min(x + col_w, table_x + table_w),
                            table_y + header_h,
                        ),
                        fill=(0, 160, 190, 210),
                    )

                    draw.text(
                        (x + 8, table_y + 9),
                        trx_safe_text(col, 18),
                        font=trx_get_font(15, True),
                        fill=(255, 255, 255, 255),
                    )

                y = table_y + header_h

                for i, (_, row) in enumerate(chunk.iterrows()):
                    fill = (255, 255, 255, 22) if i % 2 == 0 else (255, 255, 255, 12)
                    draw.rectangle((table_x, y, table_x + table_w, y + row_h), fill=fill)

                    for j, col in enumerate(cols):
                        x = table_x + j * col_w
                        if x >= table_x + table_w:
                            continue

                        draw.text(
                            (x + 8, y + 8),
                            trx_safe_text(row[col], 24),
                            font=trx_get_font(14, False),
                            fill=(235, 245, 255, 235),
                        )

                    y += row_h

                if total_rows > rows_per_page * max_pages and page_idx == len(chunks):
                    draw.text(
                        (105, 970),
                        f"Catatan: tabel dibatasi sampai {rows_per_page * max_pages} baris pertama agar ukuran PDF tetap wajar.",
                        font=trx_get_font(16, False),
                        fill=(255, 220, 150, 230),
                    )

                pages.append(page.convert("RGB"))

            return pages

        def trx_make_full_pdf_report(
            summary_img,
            trx_view,
            trx_long_view,
            chart_proses_cols,
            sla_utama_label,
            priority_df,
            transaksi_display,
            detail_df,
            detail_chart,
            selected_detail,
        ):
            pages = [summary_img.convert("RGB")]

            chart_pages = [
                ("Ranking SLA per Jenis Transaksi", trx_build_rank_fig(trx_view, sla_utama_label)),
                ("Perbandingan SLA Masing-masing Proses", trx_build_group_fig(trx_long_view)),
                ("Bubble Matrix Volume vs SLA", trx_build_bubble_fig(trx_view)),
                ("Komposisi Jumlah Transaksi", trx_build_donut_fig(trx_view)),
            ]

            fig_heat = trx_build_heat_fig(trx_view, chart_proses_cols)
            if fig_heat is not None:
                chart_pages.insert(1, ("Heatmap SLA per Proses", fig_heat))

            if detail_chart is not None and not detail_chart.empty:
                chart_pages.append(
                    (
                        f"Drilldown SLA \u2014 {selected_detail}",
                        trx_build_detail_fig(detail_chart, selected_detail),
                    )
                )

            for title, fig in chart_pages:
                pages.append(trx_fig_to_pdf_page(fig, title))

            for proses in chart_proses_cols:
                col_hari = f"{proses} (hari)"
                if col_hari in trx_view.columns:
                    data_proses = trx_view.sort_values(col_hari, ascending=True)
                    pages.append(
                        trx_fig_to_pdf_page(
                            trx_build_process_fig(data_proses, proses),
                            f"Grafik SLA Proses {proses}",
                        )
                    )

            priority_table = priority_df.copy()

            if not priority_table.empty and "SLA Utama (hari)" in priority_table.columns:
                priority_table["SLA Utama (hari)"] = priority_table["SLA Utama (hari)"].round(2)

            pages.extend(
                trx_table_pages(
                    priority_table,
                    "Tabel Matriks Prioritas AI",
                    "Prioritas berdasarkan kombinasi SLA dan volume transaksi.",
                    rows_per_page=24,
                    max_pages=6,
                )
            )

            pages.extend(
                trx_table_pages(
                    transaksi_display,
                    "Tabel Rata-rata SLA per Jenis Transaksi",
                    "Ringkasan rata-rata SLA setiap proses per jenis transaksi sesuai tampilan aktif.",
                    rows_per_page=24,
                    max_pages=8,
                )
            )

            if detail_df is not None and not detail_df.empty:
                detail_pdf_df = detail_df.head(120).copy()

                pages.extend(
                    trx_table_pages(
                        detail_pdf_df,
                        f"Tabel Detail Data \u2014 {selected_detail}",
                        "Menampilkan maksimum 120 baris pertama agar ukuran PDF tetap stabil.",
                        rows_per_page=20,
                        max_pages=6,
                    )
                )

            out_pdf = io.BytesIO()

            pages[0].save(
                out_pdf,
                format="PDF",
                save_all=True,
                append_images=pages[1:],
                resolution=150.0,
            )

            return out_pdf.getvalue()

        # =====================================================
        # MAIN TAB LOGIC
        # =====================================================
        if "JENIS TRANSAKSI" not in df_filtered.columns or not available_sla_cols:
            st.info("Kolom 'JENIS TRANSAKSI' tidak ditemukan atau tidak ada kolom SLA yang tersedia.")

        else:
            df_trx = df_filtered.copy()

            df_trx["JENIS TRANSAKSI"] = (
                df_trx["JENIS TRANSAKSI"]
                .fillna("TIDAK TERDETEKSI")
                .astype(str)
            )

            proses_cols = [
                c for c in [
                    "FUNGSIONAL",
                    "VENDOR",
                    "KEUANGAN",
                    "PERBENDAHARAAN",
                    "TOTAL WAKTU",
                ]
                if c in available_sla_cols
            ]

            proses_bottleneck_cols = [
                c for c in [
                    "FUNGSIONAL",
                    "VENDOR",
                    "KEUANGAN",
                    "PERBENDAHARAAN",
                ]
                if c in proses_cols
            ]

            chart_proses_cols = proses_cols.copy()

            if not proses_cols:
                st.info("Tidak ada kolom SLA yang dapat dianalisis.")

            else:
                # =====================================================
                # FILTER DATA UTAMA \u2014 sebelum agregasi
                # =====================================================
                # Catatan penting:
                # Filter Nomor Permohonan dan Jenis Transaksi harus dilakukan di level baris
                # sebelum groupby, agar seluruh KPI, AI Insight, Executive Summary, grafik,
                # PDF, dan drilldown membaca subset data yang sama.
                nomor_permohonan_col = trx_detect_permohonan_col(df_trx)

                st.markdown("### \U0001f39b\ufe0f Filter Data Transaksi")

                fcol1, fcol2 = st.columns([1.35, 1.25])

                with fcol1:
                    if nomor_permohonan_col:
                        nomor_options = trx_sorted_unique(df_trx[nomor_permohonan_col])

                        # =====================================================
                        # FIX HIGH-CARDINALITY MULTISELECT
                        # =====================================================
                        # Streamlit/React Multiselect dapat mengalami
                        # ``RangeError: Maximum call stack size exceeded`` jika
                        # puluhan ribu opsi dikirim sekaligus ke browser.
                        #
                        # Untuk dataset kecil, perilaku lama DIPERTAHANKAN.
                        # Untuk dataset besar, filter otomatis beralih ke mode
                        # pencarian server-side sehingga widget hanya menerima
                        # sebagian kecil opsi. Downstream tetap menerima format
                        # selected_permohonan yang sama: ["ALL"] atau list nomor.
                        TRX_NOMOR_DIRECT_LIMIT = 800
                        TRX_NOMOR_SEARCH_LIMIT = 250

                        if len(nomor_options) <= TRX_NOMOR_DIRECT_LIMIT:
                            selected_permohonan = st.multiselect(
                                "Filter Nomor Permohonan",
                                options=["ALL"] + nomor_options,
                                default=["ALL"],
                                help=(
                                    "Bisa pilih 1 atau lebih Nomor Permohonan. "
                                    "Pilih ALL untuk menampilkan seluruh nomor."
                                ),
                                key="trx_filter_nomor_permohonan_main",
                            )
                        else:
                            st.markdown("**Filter Nomor Permohonan**")
                            st.caption(
                                f"Terdeteksi {trx_fmt_int(len(nomor_options))} Nomor Permohonan unik. "
                                "Mode pencarian aman diaktifkan agar dashboard tetap ringan dan tidak error."
                            )

                            use_all_nomor = st.checkbox(
                                "Gunakan seluruh Nomor Permohonan (ALL)",
                                value=True,
                                key="trx_filter_nomor_all_safe_v1",
                                help=(
                                    "Aktifkan untuk menganalisis seluruh Nomor Permohonan. "
                                    "Nonaktifkan jika ingin mencari dan memilih nomor tertentu."
                                ),
                            )

                            if use_all_nomor:
                                selected_permohonan = ["ALL"]
                            else:
                                nomor_query = st.text_input(
                                    "Cari Nomor Permohonan",
                                    value="",
                                    placeholder="Ketik nomor / sebagian nomor. Bisa beberapa, pisahkan dengan koma.",
                                    key="trx_filter_nomor_search_safe_v1",
                                    help=(
                                        "Pencarian dilakukan sebelum opsi dikirim ke multiselect. "
                                        "Gunakan koma, titik koma, atau baris baru untuk mencari beberapa nomor sekaligus."
                                    ),
                                )

                                search_terms = [
                                    token.strip().casefold()
                                    for token in re.split(r"[,;\n]+", nomor_query or "")
                                    if token.strip()
                                ]

                                matched_nomor = []
                                if search_terms:
                                    matched_nomor = [
                                        value
                                        for value in nomor_options
                                        if any(term in str(value).casefold() for term in search_terms)
                                    ]

                                safe_key = "trx_filter_nomor_permohonan_safe_v1"
                                if safe_key not in st.session_state:
                                    st.session_state[safe_key] = []

                                # Opsi yang sudah dipilih tetap dipertahankan walau
                                # user mengganti kata pencarian, sehingga pilihan
                                # beberapa nomor dapat dikumpulkan bertahap.
                                previous_selected = [
                                    str(v) for v in st.session_state.get(safe_key, [])
                                    if str(v) in set(nomor_options)
                                ]

                                matched_limited = matched_nomor[:TRX_NOMOR_SEARCH_LIMIT]
                                safe_options = list(dict.fromkeys(previous_selected + matched_limited))

                                # Pastikan state widget tidak membawa value yang
                                # sudah tidak tersedia setelah periode/filter berubah.
                                if st.session_state.get(safe_key, []) != previous_selected:
                                    st.session_state[safe_key] = previous_selected

                                selected_permohonan = st.multiselect(
                                    "Pilih Nomor Permohonan hasil pencarian",
                                    options=safe_options,
                                    key=safe_key,
                                    help=(
                                        "Pilih satu atau lebih nomor dari hasil pencarian. "
                                        "Pilihan yang sudah dipilih tetap tersimpan saat kata pencarian diganti."
                                    ),
                                )

                                if not search_terms and not selected_permohonan:
                                    st.info(
                                        "Ketik Nomor Permohonan pada kolom pencarian di atas. "
                                        "Selama belum ada nomor yang dipilih, filter Nomor Permohonan dianggap ALL."
                                    )
                                    selected_permohonan = ["ALL"]
                                elif search_terms and not matched_nomor and not selected_permohonan:
                                    st.warning("Nomor Permohonan yang dicari tidak ditemukan pada periode aktif.")
                                    # Gunakan sentinel agar hasil benar-benar kosong,
                                    # bukan tanpa sengaja kembali ke ALL.
                                    selected_permohonan = ["__NO_MATCH__"]
                                elif len(matched_nomor) > TRX_NOMOR_SEARCH_LIMIT:
                                    st.caption(
                                        f"Ditemukan {trx_fmt_int(len(matched_nomor))} hasil. "
                                        f"Hanya {trx_fmt_int(TRX_NOMOR_SEARCH_LIMIT)} hasil pertama ditampilkan; "
                                        "ketik pencarian yang lebih spesifik untuk mempersempit hasil."
                                    )
                                elif search_terms:
                                    st.caption(
                                        f"Ditemukan {trx_fmt_int(len(matched_nomor))} hasil pencarian."
                                    )
                    else:
                        selected_permohonan = ["ALL"]
                        st.warning(
                            "Kolom Nomor Permohonan tidak terdeteksi. "
                            "Pastikan nama kolom mengandung kata 'Nomor/No' dan 'Permohonan/Permintaan/Request'."
                        )

                with fcol2:
                    jenis_options_data = trx_sorted_unique(df_trx["JENIS TRANSAKSI"])
                    selected_jenis_data = st.multiselect(
                        "Filter Jenis Transaksi",
                        options=["ALL"] + jenis_options_data,
                        default=["ALL"],
                        help="Bisa pilih 1 atau lebih jenis transaksi. Filter ini bekerja sebelum agregasi SLA.",
                        key="trx_filter_jenis_data_main",
                    )

                df_trx_before_filter = df_trx.copy()
                df_trx = trx_apply_main_filters(
                    df_input=df_trx_before_filter,
                    nomor_col=nomor_permohonan_col,
                    selected_permohonan=selected_permohonan,
                    selected_jenis_data=selected_jenis_data,
                )

                kf1, kf2, kf3, kf4 = st.columns(4)
                kf1.metric("Baris Awal", trx_fmt_int(len(df_trx_before_filter)))
                kf2.metric("Baris Terfilter", trx_fmt_int(len(df_trx)))
                kf3.metric("Nomor Dipilih", trx_filter_label(selected_permohonan))
                kf4.metric("Jenis Dipilih", trx_filter_label(selected_jenis_data))

                if df_trx.empty:
                    st.warning("Tidak ada data untuk kombinasi filter Nomor Permohonan dan Jenis Transaksi yang dipilih.")

                trx_mean_sec = (
                    df_trx
                    .groupby("JENIS TRANSAKSI")[proses_cols]
                    .mean()
                    .reset_index()
                )

                trx_count = (
                    df_trx
                    .groupby("JENIS TRANSAKSI")
                    .size()
                    .reset_index(name="Jumlah Transaksi")
                )

                trx_summary = trx_mean_sec.merge(
                    trx_count,
                    on="JENIS TRANSAKSI",
                    how="left",
                )

                for col in proses_cols:
                    trx_summary[f"{col} (hari)"] = trx_summary[col] / 86400

                if "TOTAL WAKTU" in proses_cols:
                    trx_summary["SLA Utama (detik)"] = trx_summary["TOTAL WAKTU"]
                    trx_summary["SLA Utama (hari)"] = trx_summary["TOTAL WAKTU (hari)"]
                    sla_utama_label = "TOTAL WAKTU"
                else:
                    trx_summary["SLA Utama (detik)"] = trx_summary[proses_cols].mean(axis=1)
                    trx_summary["SLA Utama (hari)"] = trx_summary["SLA Utama (detik)"] / 86400
                    sla_utama_label = "RATA-RATA PROSES"

                trx_summary = trx_summary.dropna(subset=["SLA Utama (hari)"]).copy()

                if trx_summary.empty:
                    st.warning("Tidak ada data SLA valid untuk tab jenis transaksi.")

                else:
                    trx_summary = trx_summary.sort_values("SLA Utama (hari)", ascending=True)

                    # =====================================================
                    # SLA TRANSAKSIONAL DAN KUMULATIF
                    # =====================================================
                    st.markdown("### \U0001f52c SLA Transaksional & Kumulatif atas Filter Aktif")

                    with st.expander("\U0001f4c4 Lihat SLA Transaksional per Baris / Nomor Permohonan", expanded=False):
                        detail_transaksional = df_trx.copy()

                        # Format kolom SLA agar mudah dibaca user. Kolom asli detik tetap tidak diubah.
                        for col in chart_proses_cols:
                            if col in detail_transaksional.columns:
                                detail_transaksional[f"{col} (SLA)"] = detail_transaksional[col].apply(trx_seconds_to_text)

                        base_detail_cols = []
                        for candidate_col in [
                            periode_col,
                            nomor_permohonan_col,
                            "JENIS TRANSAKSI",
                            "NAMA VENDOR",
                            "NILAI TRANSAKSI",
                            "NOMINAL",
                            "TOTAL NILAI",
                        ]:
                            if candidate_col and candidate_col in detail_transaksional.columns and candidate_col not in base_detail_cols:
                                base_detail_cols.append(candidate_col)

                        sla_detail_cols = [
                            f"{col} (SLA)"
                            for col in chart_proses_cols
                            if f"{col} (SLA)" in detail_transaksional.columns
                        ]

                        detail_cols_show = base_detail_cols + sla_detail_cols

                        if detail_cols_show:
                            st.dataframe(
                                detail_transaksional[detail_cols_show],
                                use_container_width=True,
                                hide_index=True,
                            )
                        else:
                            st.dataframe(detail_transaksional, use_container_width=True, hide_index=True)

                    kumulatif_rows = []
                    for col in chart_proses_cols:
                        if col in df_trx.columns:
                            sec_series = pd.to_numeric(df_trx[col], errors="coerce").dropna()
                            if not sec_series.empty:
                                kumulatif_rows.append({
                                    "Proses": col,
                                    "Jumlah Data Valid": int(sec_series.count()),
                                    "Rata-rata SLA": trx_seconds_to_text(sec_series.mean()),
                                    "Rata-rata SLA (hari)": round(float(sec_series.mean()) / 86400, 2),
                                    "Akumulasi SLA": trx_seconds_to_text(sec_series.sum()),
                                    "Akumulasi SLA (hari)": round(float(sec_series.sum()) / 86400, 2),
                                })

                    kumulatif_df = pd.DataFrame(kumulatif_rows)

                    if not kumulatif_df.empty:
                        st.dataframe(kumulatif_df, use_container_width=True, hide_index=True)
                        st.caption(
                            "Catatan: Akumulasi SLA adalah penjumlahan durasi SLA seluruh baris transaksi terfilter. "
                            "Untuk evaluasi performa proses, kolom rata-rata SLA biasanya lebih representatif."
                        )

                    if nomor_permohonan_col and nomor_permohonan_col in df_trx.columns:
                        with st.expander("\U0001f9ee Ringkasan Kumulatif per Nomor Permohonan", expanded=False):
                            group_cols_permohonan = [nomor_permohonan_col, "JENIS TRANSAKSI"]

                            permohonan_summary = (
                                df_trx
                                .groupby(group_cols_permohonan, dropna=False)[proses_cols]
                                .mean()
                                .reset_index()
                            )

                            permohonan_count = (
                                df_trx
                                .groupby(group_cols_permohonan, dropna=False)
                                .size()
                                .reset_index(name="Jumlah Baris")
                            )

                            permohonan_summary = permohonan_summary.merge(
                                permohonan_count,
                                on=group_cols_permohonan,
                                how="left",
                            )

                            for col in proses_cols:
                                permohonan_summary[f"{col} (Rata-rata)"] = permohonan_summary[col].apply(trx_seconds_to_text)

                            permohonan_display_cols = (
                                group_cols_permohonan
                                + ["Jumlah Baris"]
                                + [
                                    f"{col} (Rata-rata)"
                                    for col in proses_cols
                                    if f"{col} (Rata-rata)" in permohonan_summary.columns
                                ]
                            )

                            st.dataframe(
                                permohonan_summary[permohonan_display_cols],
                                use_container_width=True,
                                hide_index=True,
                            )

                    # =====================================================
                    # KPI DIGITAL CARDS
                    # =====================================================
                    total_jenis = trx_summary["JENIS TRANSAKSI"].nunique()
                    total_transaksi_trx = int(trx_summary["Jumlah Transaksi"].sum())

                    fastest_row = trx_summary.sort_values("SLA Utama (hari)", ascending=True).iloc[0]
                    slowest_row = trx_summary.sort_values("SLA Utama (hari)", ascending=False).iloc[0]

                    fastest_name = html.escape(str(fastest_row["JENIS TRANSAKSI"]))
                    slowest_name = html.escape(str(slowest_row["JENIS TRANSAKSI"]))

                    kpi_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    font-family: Segoe UI, sans-serif;
                }}

                .trx-kpi-grid {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 16px;
                    margin: 4px 0 10px 0;
                }}

                .trx-kpi-card {{
                    border-radius: 20px;
                    padding: 18px;
                    color: white;
                    min-height: 135px;
                    box-shadow: 0 12px 30px rgba(0,0,0,0.22);
                    overflow: hidden;
                    position: relative;
                }}

                .trx-kpi-card::after {{
                    content: "";
                    position: absolute;
                    right: -35px;
                    top: -35px;
                    width: 125px;
                    height: 125px;
                    border-radius: 50%;
                    background: rgba(255,255,255,0.18);
                }}

                .trx-kpi-icon {{
                    font-size: 30px;
                    margin-bottom: 8px;
                }}

                .trx-kpi-label {{
                    font-size: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.6px;
                    opacity: 0.88;
                    margin-bottom: 4px;
                }}

                .trx-kpi-value {{
                    font-size: 25px;
                    font-weight: 900;
                    line-height: 1.12;
                    word-break: break-word;
                }}

                .trx-kpi-sub {{
                    margin-top: 8px;
                    font-size: 11.5px;
                    opacity: 0.82;
                    line-height: 1.32;
                }}

                .trx-blue {{ background: linear-gradient(135deg, #0072ff, #00c6ff); }}
                .trx-green {{ background: linear-gradient(135deg, #11998e, #38ef7d); }}
                .trx-purple {{ background: linear-gradient(135deg, #7f00ff, #e100ff); }}
                .trx-red {{ background: linear-gradient(135deg, #ff416c, #ff4b2b); }}

                @media (max-width: 900px) {{
                    .trx-kpi-grid {{
                        grid-template-columns: repeat(2, 1fr);
                    }}
                }}
                </style>
                </head>

                <body>
                <div class="trx-kpi-grid">
                    <div class="trx-kpi-card trx-blue">
                        <div class="trx-kpi-icon">\U0001f9fe</div>
                        <div class="trx-kpi-label">Total Jenis Transaksi</div>
                        <div class="trx-kpi-value">{trx_fmt_int(total_jenis)}</div>
                        <div class="trx-kpi-sub">Kategori transaksi terdeteksi</div>
                    </div>

                    <div class="trx-kpi-card trx-green">
                        <div class="trx-kpi-icon">\U0001f4c4</div>
                        <div class="trx-kpi-label">Total Transaksi</div>
                        <div class="trx-kpi-value">{trx_fmt_int(total_transaksi_trx)}</div>
                        <div class="trx-kpi-sub">Dalam periode terpilih</div>
                    </div>

                    <div class="trx-kpi-card trx-purple">
                        <div class="trx-kpi-icon">\u26a1</div>
                        <div class="trx-kpi-label">Jenis Tercepat</div>
                        <div class="trx-kpi-value" style="font-size:18px;">{fastest_name}</div>
                        <div class="trx-kpi-sub">{trx_fmt_hari(fastest_row["SLA Utama (hari)"])} berdasarkan {sla_utama_label}</div>
                    </div>

                    <div class="trx-kpi-card trx-red">
                        <div class="trx-kpi-icon">\U0001f6a8</div>
                        <div class="trx-kpi-label">Jenis Terlama</div>
                        <div class="trx-kpi-value" style="font-size:18px;">{slowest_name}</div>
                        <div class="trx-kpi-sub">{trx_fmt_hari(slowest_row["SLA Utama (hari)"])} berdasarkan {sla_utama_label}</div>
                    </div>
                </div>
                </body>
                </html>
                """

                    components.html(kpi_html, height=190, scrolling=False)

                    # =====================================================
                    # FILTER VISUALISASI
                    # =====================================================
                    st.markdown("### \U0001f50e Filter Visualisasi")

                    c_filter1, c_filter2, c_filter3 = st.columns([1.4, 1.2, 1.2])

                    with c_filter1:
                        jenis_options = trx_summary["JENIS TRANSAKSI"].tolist()

                        selected_jenis = st.multiselect(
                            "Pilih Jenis Transaksi untuk visualisasi",
                            options=["ALL"] + jenis_options,
                            default=["ALL"],
                            key="trx_filter_jenis_wow",
                        )

                    if "ALL" in selected_jenis or not selected_jenis:
                        trx_ai_base = trx_summary.copy()
                    else:
                        trx_ai_base = trx_summary[
                            trx_summary["JENIS TRANSAKSI"].isin(selected_jenis)
                        ].copy()

                    with c_filter2:
                        # =====================================================
                        # FIX: slider tidak boleh memiliki min_value == max_value
                        # =====================================================
                        # Kondisi ini terjadi ketika filter utama menyisakan hanya
                        # 1 jenis transaksi. Streamlit melempar StreamlitAPIException
                        # jika st.slider dibuat dengan min=1 dan max=1.
                        max_top_n = min(30, len(trx_ai_base))

                        if max_top_n <= 0:
                            top_n = 0
                            st.metric("Top N ditampilkan", "0")
                        elif max_top_n == 1:
                            top_n = 1
                            # Tetap tampilkan kontrol di posisi yang sama, namun
                            # nonaktif karena hanya ada satu kategori yang tersedia.
                            st.selectbox(
                                "Top N ditampilkan",
                                options=[1],
                                index=0,
                                disabled=True,
                                key="trx_top_n_wow_single",
                                help="Hanya ada 1 jenis transaksi pada filter aktif.",
                            )
                        else:
                            default_top_n = min(10, max_top_n)

                            # Bersihkan state slider lama jika nilainya berada di
                            # luar range baru setelah user mempersempit filter.
                            old_top_n = st.session_state.get("trx_top_n_wow")
                            if old_top_n is not None:
                                try:
                                    old_top_n_int = int(old_top_n)
                                except Exception:
                                    old_top_n_int = default_top_n
                                if old_top_n_int < 1 or old_top_n_int > max_top_n:
                                    st.session_state.pop("trx_top_n_wow", None)

                            top_n = st.slider(
                                "Top N ditampilkan",
                                min_value=1,
                                max_value=max_top_n,
                                value=default_top_n,
                                step=1,
                                key="trx_top_n_wow",
                            )

                    with c_filter3:
                        sort_mode = st.selectbox(
                            "Urutkan berdasarkan",
                            [
                                "SLA tercepat",
                                "SLA terlama",
                                "Jumlah transaksi terbesar",
                            ],
                            key="trx_sort_mode_wow",
                        )

                    if trx_ai_base.empty:
                        st.warning("Tidak ada data untuk kombinasi filter yang dipilih.")

                    else:
                        trx_view = trx_ai_base.copy()

                        if sort_mode == "SLA tercepat":
                            trx_view = trx_view.sort_values("SLA Utama (hari)", ascending=True)
                        elif sort_mode == "SLA terlama":
                            trx_view = trx_view.sort_values("SLA Utama (hari)", ascending=False)
                        else:
                            trx_view = trx_view.sort_values("Jumlah Transaksi", ascending=False)

                        trx_view = trx_view.head(top_n)

                        if trx_view.empty:
                            st.warning("Tidak ada data untuk kombinasi filter yang dipilih.")

                        else:
                            value_vars_chart = [
                                f"{c} (hari)"
                                for c in chart_proses_cols
                                if f"{c} (hari)" in trx_view.columns
                            ]

                            trx_long_view = trx_view.melt(
                                id_vars=["JENIS TRANSAKSI", "Jumlah Transaksi"],
                                value_vars=value_vars_chart,
                                var_name="Proses",
                                value_name="Rata-rata SLA (hari)",
                            )

                            trx_long_view["Proses"] = trx_long_view["Proses"].str.replace(
                                " (hari)",
                                "",
                                regex=False,
                            )

                            trx_long_view = trx_long_view.dropna(subset=["Rata-rata SLA (hari)"])

                            # =====================================================
                            # AI EXECUTIVE INSIGHT
                            # =====================================================
                            st.markdown("### \U0001f916 AI Executive Insight")

                            ai_result = trx_generate_ai_insight(
                                trx_ai_base,
                                proses_bottleneck_cols,
                            )

                            summary_html = trx_html_list(ai_result.get("summary", []))
                            risk_html = trx_html_list(ai_result.get("risks", []))
                            reco_html = trx_html_list(ai_result.get("recommendations", []))

                            status_label = ai_result.get("status_label", "CONTROLLED")
                            status_class = ai_result.get("status_class", "trx-status-good")

                            ai_height = 430 + 28 * max(
                                len(ai_result.get("summary", [])),
                                len(ai_result.get("risks", [])),
                                len(ai_result.get("recommendations", [])),
                            )

                            ai_html = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                        <style>
                        body {{
                            margin: 0;
                            padding: 0;
                            background: transparent;
                            font-family: Segoe UI, sans-serif;
                        }}

                        .trx-ai-wrap {{
                            width: 100%;
                            box-sizing: border-box;
                            background:
                                radial-gradient(circle at top left, rgba(0,234,255,0.30), transparent 28%),
                                radial-gradient(circle at bottom right, rgba(225,0,255,0.25), transparent 30%),
                                linear-gradient(135deg, rgba(13,19,45,0.98), rgba(20,28,60,0.94));
                            border: 1px solid rgba(255,255,255,0.18);
                            border-radius: 26px;
                            padding: 24px;
                            box-shadow: 0 18px 48px rgba(0,0,0,0.35);
                            color: white;
                            overflow: hidden;
                        }}

                        .trx-ai-header {{
                            display: flex;
                            flex-wrap: wrap;
                            justify-content: space-between;
                            align-items: center;
                            gap: 12px;
                            margin-bottom: 16px;
                        }}

                        .trx-ai-title {{
                            font-size: 30px;
                            font-weight: 950;
                            letter-spacing: 0.3px;
                            background: linear-gradient(90deg, #00eaff, #38ef7d, #fee140);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                        }}

                        .trx-ai-badge-row {{
                            display: flex;
                            flex-wrap: wrap;
                            gap: 10px;
                            align-items: center;
                        }}

                        .trx-ai-badge {{
                            background: rgba(255,255,255,0.13);
                            border: 1px solid rgba(255,255,255,0.22);
                            padding: 8px 12px;
                            border-radius: 999px;
                            font-size: 12px;
                            font-weight: 800;
                            color: #dffcff;
                        }}

                        .trx-ai-status {{
                            padding: 8px 14px;
                            border-radius: 999px;
                            font-size: 12px;
                            font-weight: 950;
                            letter-spacing: 0.6px;
                            border: 1px solid rgba(255,255,255,0.20);
                        }}

                        .trx-status-critical {{
                            background: rgba(255,65,108,0.24);
                            color: #ffdce5;
                        }}

                        .trx-status-watch {{
                            background: rgba(254,225,64,0.22);
                            color: #fff4b0;
                        }}

                        .trx-status-good {{
                            background: rgba(56,239,125,0.20);
                            color: #d9ffe9;
                        }}

                        .trx-status-neutral {{
                            background: rgba(255,255,255,0.14);
                            color: #ffffff;
                        }}

                        .trx-ai-headline {{
                            background: rgba(255,255,255,0.10);
                            border: 1px solid rgba(255,255,255,0.16);
                            border-radius: 20px;
                            padding: 18px 20px;
                            font-size: 18px;
                            font-weight: 760;
                            line-height: 1.48;
                            margin-bottom: 18px;
                            box-shadow: inset 0 0 18px rgba(255,255,255,0.05);
                            color: rgba(255,255,255,0.96);
                        }}

                        .trx-ai-grid {{
                            display: grid;
                            grid-template-columns: repeat(3, 1fr);
                            gap: 16px;
                            align-items: stretch;
                        }}

                        .trx-ai-box {{
                            background: rgba(255,255,255,0.09);
                            border: 1px solid rgba(255,255,255,0.14);
                            border-radius: 20px;
                            padding: 18px;
                            backdrop-filter: blur(10px);
                            min-height: 220px;
                        }}

                        .trx-ai-box h4 {{
                            margin: 0 0 12px 0;
                            font-size: 16px;
                            letter-spacing: 0.4px;
                            color: rgba(255,255,255,0.98);
                        }}

                        .trx-ai-box ul {{
                            margin: 0;
                            padding-left: 20px;
                        }}

                        .trx-ai-box li {{
                            margin-bottom: 9px;
                            font-size: 13.5px;
                            line-height: 1.45;
                            color: rgba(255,255,255,0.92);
                        }}

                        .trx-ai-foot {{
                            margin-top: 14px;
                            font-size: 11.5px;
                            opacity: 0.67;
                            text-align: right;
                        }}

                        @media (max-width: 900px) {{
                            .trx-ai-grid {{
                                grid-template-columns: 1fr;
                            }}
                        }}
                        </style>
                        </head>

                        <body>
                        <div class="trx-ai-wrap">
                            <div class="trx-ai-header">
                                <div class="trx-ai-title">\U0001f916 AI Executive Insight</div>
                                <div class="trx-ai-badge-row">
                                    <div class="trx-ai-status {status_class}">{html.escape(status_label)}</div>
                                    <div class="trx-ai-badge">Auto-generated from filtered transaction type</div>
                                </div>
                            </div>

                            <div class="trx-ai-headline">
                                {html.escape(str(ai_result.get("headline", "-")))}
                            </div>

                            <div class="trx-ai-grid">
                                <div class="trx-ai-box">
                                    <h4>\U0001f4cc Key Findings</h4>
                                    <ul>{summary_html}</ul>
                                </div>

                                <div class="trx-ai-box">
                                    <h4>\U0001f6a8 Risk Signals</h4>
                                    <ul>{risk_html}</ul>
                                </div>

                                <div class="trx-ai-box">
                                    <h4>\u2705 Recommended Actions</h4>
                                    <ul>{reco_html}</ul>
                                </div>
                            </div>

                            <div class="trx-ai-foot">
                                Insight mengikuti filter jenis transaksi aktif, namun tidak bias oleh Top N dan sorting visual.
                            </div>
                        </div>
                        </body>
                        </html>
                        """

                            components.html(ai_html, height=ai_height, scrolling=False)

                            # =====================================================
                            # PRIORITY MATRIX TABLE
                            # =====================================================
                            with st.expander("\U0001f9e0 Lihat Matriks Prioritas AI", expanded=False):
                                priority_show = ai_result.get("priority_df", pd.DataFrame()).copy()

                                if not priority_show.empty:
                                    priority_show["SLA Utama (hari)"] = priority_show["SLA Utama (hari)"].round(2)

                                    def style_priority(row):
                                        label = str(row["Prioritas AI"])

                                        if "Prioritas 1" in label:
                                            return [
                                                "background-color: #ffe2e2; color: #7a0000; font-weight: bold"
                                            ] * len(row)
                                        elif "Prioritas 2" in label:
                                            return [
                                                "background-color: #fff3cd; color: #6b4e00; font-weight: bold"
                                            ] * len(row)
                                        elif "Prioritas 3" in label:
                                            return [
                                                "background-color: #dff5ff; color: #004761; font-weight: bold"
                                            ] * len(row)
                                        else:
                                            return [""] * len(row)

                                    st.dataframe(
                                        priority_show.style.apply(style_priority, axis=1),
                                        use_container_width=True,
                                        hide_index=True,
                                    )
                                else:
                                    st.info("Belum ada matriks prioritas yang dapat ditampilkan.")

                            # =====================================================
                            # EXECUTIVE SUMMARY DIREKSI
                            # =====================================================
                            st.markdown("### \U0001f3af Executive Summary Direksi")

                            exec_df = trx_ai_base.copy()

                            total_jenis_exec = exec_df["JENIS TRANSAKSI"].nunique()
                            total_trx_exec = int(exec_df["Jumlah Transaksi"].sum())
                            avg_sla_exec = float(exec_df["SLA Utama (hari)"].mean())

                            fastest_exec = exec_df.sort_values("SLA Utama (hari)", ascending=True).iloc[0]
                            slowest_exec = exec_df.sort_values("SLA Utama (hari)", ascending=False).iloc[0]
                            biggest_exec = exec_df.sort_values("Jumlah Transaksi", ascending=False).iloc[0]

                            priority_df_exec = ai_result.get("priority_df", pd.DataFrame()).copy()
                            p1_count = ai_result.get("p1_count", 0)
                            bottleneck_proses = ai_result.get("bottleneck_proses", "-")
                            bottleneck_value = ai_result.get("bottleneck_value", np.nan)

                            if status_label == "CRITICAL":
                                status_desc = "Perlu perhatian segera karena beberapa jenis transaksi memiliki kombinasi SLA tinggi dan volume besar."
                            elif status_label == "WATCHLIST":
                                status_desc = "Terdapat transaksi prioritas yang perlu dipantau dan ditindaklanjuti."
                            else:
                                status_desc = "Secara umum kondisi transaksi masih terkendali pada filter yang aktif."

                            top_priority_html = ""

                            if not priority_df_exec.empty:
                                priority_show_exec = priority_df_exec.head(5).copy()

                                for _, row in priority_show_exec.iterrows():
                                    trx_name = html.escape(trx_safe_text(row["JENIS TRANSAKSI"], 42))
                                    trx_count = trx_fmt_int(row["Jumlah Transaksi"])
                                    trx_sla = trx_fmt_hari(row["SLA Utama (hari)"])
                                    trx_priority = html.escape(str(row["Prioritas AI"]))

                                    top_priority_html += f"""
                                <div class="trx-exec-prio-row">
                                    <div>
                                        <div class="trx-exec-prio-name">{trx_name}</div>
                                        <div class="trx-exec-prio-sub">{trx_priority}</div>
                                    </div>
                                    <div class="trx-exec-prio-metric">
                                        <b>{trx_sla}</b><br>
                                        <span>{trx_count} trx</span>
                                    </div>
                                </div>
                                """

                            if top_priority_html == "":
                                top_priority_html = """
                            <div class="trx-exec-prio-row">
                                <div>
                                    <div class="trx-exec-prio-name">Belum ada prioritas khusus</div>
                                    <div class="trx-exec-prio-sub">Data prioritas tidak tersedia</div>
                                </div>
                                <div class="trx-exec-prio-metric"><b>-</b></div>
                            </div>
                            """

                            bottleneck_sentence = "."

                            if not pd.isna(bottleneck_value):
                                bottleneck_sentence = f" dengan rata-rata {trx_fmt_hari(bottleneck_value)}."

                            exec_height = 790 + (len(priority_df_exec.head(5)) * 12)

                            exec_fastest_name = html.escape(trx_safe_text(fastest_exec["JENIS TRANSAKSI"]))
                            exec_slowest_name = html.escape(trx_safe_text(slowest_exec["JENIS TRANSAKSI"]))
                            exec_biggest_name = html.escape(trx_safe_text(biggest_exec["JENIS TRANSAKSI"]))

                            logo_src = trx_logo_data_uri()

                            if logo_src:
                                logo_html = f'<img src="{logo_src}" class="trx-exec-logo" />'
                            else:
                                logo_html = '<div class="trx-exec-logo-fallback">ASDP</div>'

                            exec_html = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                        <style>
                        body {{
                            margin: 0;
                            padding: 0;
                            background: transparent;
                            font-family: Segoe UI, sans-serif;
                        }}

                        .trx-exec-wrap {{
                            width: 100%;
                            box-sizing: border-box;
                            background:
                                radial-gradient(circle at top left, rgba(0, 234, 255, 0.34), transparent 25%),
                                radial-gradient(circle at bottom right, rgba(56, 239, 125, 0.22), transparent 30%),
                                linear-gradient(135deg, #061126 0%, #102a58 50%, #034e62 100%);
                            border: 1px solid rgba(255,255,255,0.18);
                            border-radius: 28px;
                            padding: 24px;
                            color: white;
                            box-shadow: 0 22px 58px rgba(0,0,0,0.38);
                            overflow: hidden;
                        }}

                        .trx-exec-header {{
                            display: flex;
                            flex-wrap: wrap;
                            justify-content: space-between;
                            align-items: flex-start;
                            gap: 14px;
                            margin-bottom: 18px;
                        }}

                        .trx-exec-brand {{
                            display: flex;
                            align-items: center;
                            gap: 18px;
                        }}

                        .trx-exec-logo {{
                            max-width: 150px;
                            max-height: 58px;
                            object-fit: contain;
                            background: rgba(255,255,255,0.92);
                            padding: 8px 12px;
                            border-radius: 14px;
                        }}

                        .trx-exec-logo-fallback {{
                            width: 120px;
                            height: 46px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            background: rgba(255,255,255,0.92);
                            color: #005577;
                            font-weight: 950;
                            border-radius: 14px;
                        }}

                        .trx-exec-title {{
                            font-size: 34px;
                            font-weight: 950;
                            letter-spacing: 0.2px;
                            line-height: 1.08;
                        }}

                        .trx-exec-subtitle {{
                            margin-top: 8px;
                            opacity: 0.82;
                            font-size: 14px;
                            line-height: 1.35;
                        }}

                        .trx-exec-status {{
                            padding: 12px 16px;
                            border-radius: 999px;
                            font-size: 13px;
                            font-weight: 950;
                            letter-spacing: 0.7px;
                            border: 1px solid rgba(255,255,255,0.22);
                        }}

                        .trx-exec-headline {{
                            background: rgba(10,25,55,0.76);
                            border: 1px solid rgba(0,234,255,0.40);
                            border-radius: 22px;
                            padding: 18px 20px;
                            font-size: 18px;
                            font-weight: 760;
                            line-height: 1.48;
                            margin-bottom: 18px;
                        }}

                        .trx-exec-kpi-grid {{
                            display: grid;
                            grid-template-columns: repeat(4, 1fr);
                            gap: 14px;
                            margin-bottom: 18px;
                        }}

                        .trx-exec-kpi {{
                            background: rgba(10,25,55,0.74);
                            border: 1px solid rgba(255,255,255,0.16);
                            border-radius: 20px;
                            padding: 16px;
                            min-height: 110px;
                        }}

                        .trx-exec-kpi-label {{
                            font-size: 12px;
                            opacity: 0.78;
                            text-transform: uppercase;
                            letter-spacing: 0.6px;
                            color: #84eaff;
                        }}

                        .trx-exec-kpi-value {{
                            margin-top: 8px;
                            font-size: 24px;
                            font-weight: 950;
                            color: #ffffff;
                        }}

                        .trx-exec-kpi-sub {{
                            margin-top: 6px;
                            font-size: 11.5px;
                            opacity: 0.76;
                            line-height: 1.28;
                        }}

                        .trx-exec-main-grid {{
                            display: grid;
                            grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
                            gap: 16px;
                        }}

                        .trx-exec-box {{
                            background: rgba(10,25,55,0.74);
                            border: 1px solid rgba(255,255,255,0.14);
                            border-radius: 22px;
                            padding: 18px;
                        }}

                        .trx-exec-box h4 {{
                            margin: 0 0 12px 0;
                            font-size: 16px;
                        }}

                        .trx-exec-box ul {{
                            margin: 0;
                            padding-left: 20px;
                        }}

                        .trx-exec-box li {{
                            margin-bottom: 9px;
                            line-height: 1.42;
                            font-size: 13.5px;
                            color: rgba(255,255,255,0.91);
                        }}

                        .trx-exec-prio-row {{
                            display: flex;
                            justify-content: space-between;
                            gap: 12px;
                            padding: 12px 0;
                            border-bottom: 1px solid rgba(255,255,255,0.14);
                        }}

                        .trx-exec-prio-name {{
                            font-size: 13.5px;
                            font-weight: 850;
                            line-height: 1.25;
                        }}

                        .trx-exec-prio-sub {{
                            font-size: 11px;
                            opacity: 0.76;
                            margin-top: 4px;
                            line-height: 1.25;
                        }}

                        .trx-exec-prio-metric {{
                            text-align: right;
                            font-size: 12px;
                            min-width: 108px;
                        }}

                        .trx-exec-prio-metric span {{
                            opacity: 0.72;
                        }}

                        .trx-exec-note {{
                            margin-top: 14px;
                            font-size: 11.5px;
                            opacity: 0.62;
                            text-align: right;
                        }}

                        .trx-status-critical {{
                            background: rgba(255,65,108,0.24);
                            color: #ffdce5;
                        }}

                        .trx-status-watch {{
                            background: rgba(254,225,64,0.22);
                            color: #fff4b0;
                        }}

                        .trx-status-good {{
                            background: rgba(56,239,125,0.20);
                            color: #d9ffe9;
                        }}

                        .trx-status-neutral {{
                            background: rgba(255,255,255,0.14);
                            color: #ffffff;
                        }}

                        @media (max-width: 950px) {{
                            .trx-exec-kpi-grid {{
                                grid-template-columns: repeat(2, 1fr);
                            }}

                            .trx-exec-main-grid {{
                                grid-template-columns: 1fr;
                            }}
                        }}
                        </style>
                        </head>

                        <body>
                        <div class="trx-exec-wrap">
                            <div class="trx-exec-header">
                                <div class="trx-exec-brand">
                                    {logo_html}
                                    <div>
                                        <div class="trx-exec-title">Executive Summary<br>SLA Jenis Transaksi</div>
                                        <div class="trx-exec-subtitle">
                                            Periode {html.escape(str(start_periode))} s.d. {html.escape(str(end_periode))}
                                            \u2022 Acuan: {html.escape(str(sla_utama_label))}
                                        </div>
                                    </div>
                                </div>

                                <div class="trx-exec-status {status_class}">{html.escape(status_label)}</div>
                            </div>

                            <div class="trx-exec-headline">
                                {html.escape(str(ai_result.get("headline", "-")))}
                            </div>

                            <div class="trx-exec-kpi-grid">
                                <div class="trx-exec-kpi">
                                    <div class="trx-exec-kpi-label">Total Transaksi</div>
                                    <div class="trx-exec-kpi-value">{trx_fmt_int(total_trx_exec)}</div>
                                    <div class="trx-exec-kpi-sub">Jumlah transaksi pada filter jenis transaksi aktif</div>
                                </div>

                                <div class="trx-exec-kpi">
                                    <div class="trx-exec-kpi-label">Jenis Transaksi</div>
                                    <div class="trx-exec-kpi-value">{trx_fmt_int(total_jenis_exec)}</div>
                                    <div class="trx-exec-kpi-sub">Kategori transaksi dianalisis</div>
                                </div>

                                <div class="trx-exec-kpi">
                                    <div class="trx-exec-kpi-label">Rata-rata SLA</div>
                                    <div class="trx-exec-kpi-value">{trx_fmt_hari(avg_sla_exec)}</div>
                                    <div class="trx-exec-kpi-sub">Rata-rata SLA utama</div>
                                </div>

                                <div class="trx-exec-kpi">
                                    <div class="trx-exec-kpi-label">Prioritas Tinggi</div>
                                    <div class="trx-exec-kpi-value">{trx_fmt_int(p1_count)}</div>
                                    <div class="trx-exec-kpi-sub">{html.escape(status_desc)}</div>
                                </div>
                            </div>

                            <div class="trx-exec-main-grid">
                                <div class="trx-exec-box">
                                    <h4>\U0001f4cc Executive Notes</h4>
                                    <ul>
                                        <li>Jenis tercepat: <b>{exec_fastest_name}</b> dengan SLA {trx_fmt_hari(fastest_exec["SLA Utama (hari)"])}.</li>
                                        <li>Jenis terlama: <b>{exec_slowest_name}</b> dengan SLA {trx_fmt_hari(slowest_exec["SLA Utama (hari)"])}.</li>
                                        <li>Volume terbesar: <b>{exec_biggest_name}</b> sebanyak {trx_fmt_int(biggest_exec["Jumlah Transaksi"])} transaksi.</li>
                                        <li>Bottleneck proses: <b>{html.escape(str(bottleneck_proses))}</b>{bottleneck_sentence}</li>
                                    </ul>

                                    <h4 style="margin-top:18px;">\u2705 Recommended Actions</h4>
                                    <ul>{trx_html_list(ai_result.get("recommendations", []), max_items=3)}</ul>
                                </div>

                                <div class="trx-exec-box">
                                    <h4>\U0001f525 Top Priority Transactions</h4>
                                    {top_priority_html}
                                </div>
                            </div>

                            <div class="trx-exec-note">
                                Executive summary otomatis mengikuti filter jenis transaksi aktif.
                            </div>
                        </div>
                        </body>
                        </html>
                        """

                            components.html(exec_html, height=exec_height, scrolling=False)

                            # =====================================================
                            # DETAIL OBJECTS
                            # =====================================================
                            def trx_get_detail_objects(selected_name):
                                detail_df_local = df_trx[
                                    df_trx["JENIS TRANSAKSI"] == selected_name
                                ].copy()

                                detail_mean_local = trx_summary[
                                    trx_summary["JENIS TRANSAKSI"] == selected_name
                                ].copy()

                                detail_chart_local = pd.DataFrame()

                                if not detail_mean_local.empty:
                                    detail_row_local = detail_mean_local.iloc[0]
                                    rows = []

                                    for p in chart_proses_cols:
                                        col_hari = f"{p} (hari)"
                                        if col_hari in detail_row_local.index:
                                            val = detail_row_local[col_hari]
                                            if pd.notna(val):
                                                rows.append(
                                                    {
                                                        "Proses": p,
                                                        "Rata-rata SLA (hari)": val,
                                                    }
                                                )

                                    detail_chart_local = pd.DataFrame(rows)

                                return detail_df_local, detail_mean_local, detail_chart_local

                            detail_options = trx_view["JENIS TRANSAKSI"].tolist()

                            previous_detail = st.session_state.get("trx_detail_select_wow", None)

                            if previous_detail in detail_options:
                                pdf_selected_detail = previous_detail
                            else:
                                pdf_selected_detail = detail_options[0]

                            detail_df_for_pdf, detail_mean_for_pdf, detail_chart_for_pdf = trx_get_detail_objects(
                                pdf_selected_detail
                            )

                            # =====================================================
                            # DOWNLOAD EXECUTIVE PACK
                            # =====================================================
                            st.markdown("### \U0001f4e5 Download Executive Pack")

                            col_down1, col_down2, col_down3 = st.columns([1, 1, 1.25])

                            with col_down1:
                                if st.button("\U0001f3a8 Generate Executive Pack", key="generate_exec_summary_trx"):
                                    try:
                                        transaksi_display_pdf = trx_view.copy()

                                        for col in chart_proses_cols:
                                            if col in transaksi_display_pdf.columns:
                                                transaksi_display_pdf[f"{col} (Rata-rata)"] = transaksi_display_pdf[col].apply(
                                                    trx_seconds_to_text
                                                )

                                        display_cols_pdf = (
                                            ["JENIS TRANSAKSI", "Jumlah Transaksi"]
                                            + [
                                                f"{col} (Rata-rata)"
                                                for col in chart_proses_cols
                                                if f"{col} (Rata-rata)" in transaksi_display_pdf.columns
                                            ]
                                        )

                                        transaksi_display_pdf = transaksi_display_pdf[display_cols_pdf]

                                        summary_img = trx_make_summary_image(
                                            trx_exec_base=trx_ai_base,
                                            ai_result=ai_result,
                                            sla_utama_label=sla_utama_label,
                                            start_periode=start_periode,
                                            end_periode=end_periode,
                                        )

                                        png_bytes = trx_image_to_png_bytes(summary_img)
                                        st.session_state["trx_exec_summary_png"] = png_bytes

                                        try:
                                            pdf_bytes = trx_make_full_pdf_report(
                                                summary_img=summary_img,
                                                trx_view=trx_view,
                                                trx_long_view=trx_long_view,
                                                chart_proses_cols=chart_proses_cols,
                                                sla_utama_label=sla_utama_label,
                                                priority_df=ai_result.get("priority_df", pd.DataFrame()),
                                                transaksi_display=transaksi_display_pdf,
                                                detail_df=detail_df_for_pdf,
                                                detail_chart=detail_chart_for_pdf,
                                                selected_detail=pdf_selected_detail,
                                            )

                                            st.session_state["trx_exec_report_pdf"] = pdf_bytes
                                            st.success("Executive Pack berhasil dibuat. PNG dan PDF lengkap siap di-download.")

                                        except Exception as e_pdf:
                                            if "trx_exec_report_pdf" in st.session_state:
                                                del st.session_state["trx_exec_report_pdf"]

                                            st.warning(
                                                "PNG berhasil dibuat, tetapi PDF gagal dibuat. "
                                                "Pastikan dependency 'kaleido' sudah ada di requirements.txt."
                                            )
                                            st.exception(e_pdf)

                                    except Exception as e:
                                        st.error("Executive Pack gagal dibuat.")
                                        st.exception(e)

                            with col_down2:
                                if "trx_exec_summary_png" in st.session_state:
                                    st.download_button(
                                        "\u2b07\ufe0f Download PNG Summary",
                                        data=st.session_state["trx_exec_summary_png"],
                                        file_name="Executive_Summary_Tab_Transaksi.png",
                                        mime="image/png",
                                        key="download_exec_summary_png",
                                    )

                            with col_down3:
                                if "trx_exec_report_pdf" in st.session_state:
                                    st.download_button(
                                        "\u2b07\ufe0f Download PDF Lengkap",
                                        data=st.session_state["trx_exec_report_pdf"],
                                        file_name="Executive_Report_Tab_Transaksi_Lengkap.pdf",
                                        mime="application/pdf",
                                        key="download_exec_report_pdf",
                                    )

                            if "trx_exec_summary_png" in st.session_state:
                                with st.expander("\U0001f440 Preview Executive Summary 16:9", expanded=True):
                                    st.image(
                                        st.session_state["trx_exec_summary_png"],
                                        caption="Preview Executive Summary 16:9",
                                        use_container_width=True,
                                    )

                            # =====================================================
                            # MAIN CHARTS
                            # =====================================================
                            st.markdown("### \U0001f3c6 Ranking SLA per Jenis Transaksi")
                            fig_rank = trx_build_rank_fig(trx_view, sla_utama_label)
                            st.plotly_chart(fig_rank, use_container_width=True)

                            st.markdown("### \U0001f525 Heatmap SLA per Proses")
                            fig_heat = trx_build_heat_fig(trx_view, chart_proses_cols)

                            if fig_heat is not None:
                                st.plotly_chart(fig_heat, use_container_width=True)
                            else:
                                st.info("Tidak ada kolom proses yang dapat ditampilkan pada heatmap.")

                            st.markdown("### \U0001f4ca Perbandingan SLA Masing-masing Proses")

                            if not trx_long_view.empty:
                                fig_group = trx_build_group_fig(trx_long_view)
                                st.plotly_chart(fig_group, use_container_width=True)
                            else:
                                st.info("Tidak ada data SLA proses yang valid untuk grafik perbandingan.")

                            st.markdown("### \U0001fae7 Bubble Matrix: Volume vs SLA")
                            fig_bubble = trx_build_bubble_fig(trx_view)
                            st.plotly_chart(fig_bubble, use_container_width=True)

                            st.markdown("### \U0001f369 Komposisi Jumlah Transaksi")
                            fig_donut = trx_build_donut_fig(trx_view)
                            st.plotly_chart(fig_donut, use_container_width=True)

                            st.markdown("### \u2699\ufe0f Grafik Masing-masing Proses")

                            cols_per_row = 2
                            proses_chunks = [
                                chart_proses_cols[i:i + cols_per_row]
                                for i in range(0, len(chart_proses_cols), cols_per_row)
                            ]

                            for chunk in proses_chunks:
                                chart_cols = st.columns(len(chunk))

                                for i, proses in enumerate(chunk):
                                    with chart_cols[i]:
                                        col_hari = f"{proses} (hari)"

                                        if col_hari not in trx_view.columns:
                                            continue

                                        data_proses = trx_view.dropna(subset=[col_hari]).sort_values(
                                            col_hari,
                                            ascending=True,
                                        )

                                        if data_proses.empty:
                                            st.info(f"Tidak ada data valid untuk proses {proses}.")
                                        else:
                                            fig_each = trx_build_process_fig(data_proses, proses)
                                            st.plotly_chart(fig_each, use_container_width=True)

                            # =====================================================
                            # TABEL RATA-RATA SLA
                            # =====================================================
                            with st.expander("\U0001f4cb Tabel Detail Rata-rata SLA per Jenis Transaksi", expanded=False):
                                transaksi_display = trx_view.copy()

                                for col in chart_proses_cols:
                                    if col in transaksi_display.columns:
                                        transaksi_display[f"{col} (Rata-rata)"] = transaksi_display[col].apply(
                                            trx_seconds_to_text
                                        )

                                display_cols = (
                                    ["JENIS TRANSAKSI", "Jumlah Transaksi"]
                                    + [
                                        f"{col} (Rata-rata)"
                                        for col in chart_proses_cols
                                        if f"{col} (Rata-rata)" in transaksi_display.columns
                                    ]
                                )

                                st.dataframe(
                                    transaksi_display[display_cols],
                                    use_container_width=True,
                                    hide_index=True,
                                )

                            # =====================================================
                            # DRILLDOWN DETAIL - SAFE MODE TANPA st.fragment
                            # =====================================================
                            st.markdown("### \U0001f50d Drilldown Detail Jenis Transaksi")

                            # Catatan:
                            # Jangan gunakan st.fragment di dalam st.tabs untuk kasus ini.
                            # Pada beberapa versi Streamlit, fragment rerun di dalam tab bisa membuat
                            # output menumpuk / keluar dari konteks tab, sehingga isi tab lain tampak
                            # muncul di bawah tab aktif.

                            if not detail_options:
                                st.info("Tidak ada jenis transaksi yang dapat ditampilkan untuk drilldown.")
                            else:
                                current_value = st.session_state.get(
                                    "trx_detail_select_wow",
                                    detail_options[0],
                                )

                                if current_value not in detail_options:
                                    current_index = 0
                                else:
                                    current_index = detail_options.index(current_value)

                                selected_detail = st.selectbox(
                                    "Pilih jenis transaksi untuk drilldown",
                                    options=detail_options,
                                    index=current_index,
                                    key="trx_detail_select_wow",
                                )

                                detail_df, detail_mean, detail_chart = trx_get_detail_objects(selected_detail)

                                if not detail_mean.empty:
                                    detail_row = detail_mean.iloc[0]

                                    d1, d2, d3 = st.columns(3)

                                    d1.metric(
                                        "Jumlah Transaksi",
                                        trx_fmt_int(detail_row["Jumlah Transaksi"]),
                                    )

                                    d2.metric(
                                        "SLA Utama",
                                        trx_fmt_hari(detail_row["SLA Utama (hari)"]),
                                    )

                                    d3.metric(
                                        "Acuan SLA",
                                        sla_utama_label,
                                    )

                                    if not detail_chart.empty:
                                        fig_detail = trx_build_detail_fig(detail_chart, selected_detail)
                                        st.plotly_chart(
                                            fig_detail,
                                            use_container_width=True,
                                            key="trx_detail_chart_safe_wow",
                                        )
                                    else:
                                        st.info("Tidak ada data SLA proses yang valid untuk jenis transaksi ini.")
                                else:
                                    st.warning("Detail transaksi tidak ditemukan untuk pilihan ini.")

                                with st.expander("\U0001f50e Lihat Data Baris Detail", expanded=False):
                                    st.dataframe(
                                        detail_df,
                                        use_container_width=True,
                                        key="trx_detail_table_safe_wow",
                                    )
# ===================== END OF TAB_TRANSAKSI =====================

if (not _SLA_LAZY_TABS) or bool(getattr(tab_vendor, "open", False)):
    with tab_vendor:
        import plotly.express as px
        import streamlit.components.v1 as components

        # ==============================
        # Helper: format detik -> "x hari x jam x menit x detik"
        # ==============================
        def fmt_duration(seconds):
            if pd.isna(seconds):
                return "-"
            try:
                s = int(round(float(seconds)))
            except Exception:
                return "-"
            days = s // 86400
            s %= 86400
            hours = s // 3600
            s %= 3600
            minutes = s // 60
            secs = s % 60
            return f"{days} hari {hours} jam {minutes} menit {secs} detik"

        if "NAMA VENDOR" in df_filtered.columns:
            # ==============================
            # 1) FILTER KATEGORI
            # ==============================
            kategori_filter = st.selectbox(
                "Pilih Kategori Vendor",
                ["ALL", "ALL CABANG", "ALL PUSAT", "ALL VENDOR"]
            )

            if kategori_filter == "ALL CABANG":
                df_vendor_filtered = df_filtered[
                    df_filtered["NAMA VENDOR"].astype(str).str.upper().str.contains("GM CABANG", na=False)
                ].copy()
                df_vendor_filtered["SLA_USED"] = pd.to_numeric(df_vendor_filtered["FUNGSIONAL"], errors="coerce")

            elif kategori_filter == "ALL PUSAT":
                nama = df_filtered["NAMA VENDOR"].astype(str)
                mask_pusat = nama.str[:3].eq("110") & (nama.str.len() >= 12) & nama.str[11].eq("-")
                df_vendor_filtered = df_filtered[mask_pusat].copy()
                df_vendor_filtered["SLA_USED"] = pd.to_numeric(df_vendor_filtered["FUNGSIONAL"], errors="coerce")

            elif kategori_filter == "ALL VENDOR":
                nama = df_filtered["NAMA VENDOR"].astype(str)
                mask_cabang = nama.str.upper().str.contains("GM CABANG", na=False)
                mask_pusat = nama.str[:3].eq("110") & (nama.str.len() >= 12) & nama.str[11].eq("-")
                df_vendor_filtered = df_filtered[~(mask_cabang | mask_pusat)].copy()
                df_vendor_filtered["SLA_USED"] = pd.to_numeric(df_vendor_filtered["VENDOR"], errors="coerce")

            else:  # "ALL"
                df_vendor_filtered = df_filtered.copy()

                def pick_sla(row):
                    nama = str(row["NAMA VENDOR"]).upper()
                    if "GM CABANG" in nama:
                        return row.get("FUNGSIONAL")
                    elif nama.startswith("110") and len(nama) >= 12 and nama[11] == "-":
                        return row.get("FUNGSIONAL")
                    else:
                        return row.get("VENDOR")

                df_vendor_filtered["SLA_USED"] = df_vendor_filtered.apply(pick_sla, axis=1)
                df_vendor_filtered["SLA_USED"] = pd.to_numeric(df_vendor_filtered["SLA_USED"], errors="coerce")

            df_vendor_filtered["SLA_USED_FMT"] = df_vendor_filtered["SLA_USED"].apply(fmt_duration)

            # ==============================
            # 2) FILTER VENDOR
            # ==============================
            vendor_list = sorted(df_vendor_filtered["NAMA VENDOR"].dropna().astype(str).unique())
            vendor_list_with_all = ["ALL"] + vendor_list
            selected_vendors = st.multiselect("Pilih Vendor", vendor_list_with_all, default=[])

            if not selected_vendors:
                st.info("Silakan pilih vendor untuk melihat analisis.")
            else:
                if "ALL" in selected_vendors:
                    selected_vendors = vendor_list
                df_vendor_filtered = df_vendor_filtered[df_vendor_filtered["NAMA VENDOR"].isin(selected_vendors)]

                # ==============================
                # 3) Kartu Digital Ringkasan
                # ==============================
                total_vendor = df_vendor_filtered["NAMA VENDOR"].nunique()
                total_transaksi = len(df_vendor_filtered)
                rata_sla_global_hari = float(df_vendor_filtered["SLA_USED"].mean() / 86400) if df_vendor_filtered["SLA_USED"].notna().any() else 0.0

                card_template = f"""
            <style>
            .card-container{{display:flex;gap:20px;justify-content:center;margin-top:20px;}}
            .card{{flex:1;padding:20px;border-radius:16px;text-align:center;color:white;
            box-shadow:0 4px 12px rgba(0,0,0,0.2);transition:transform 0.3s ease;}}
            .card:hover{{transform:scale(1.05);box-shadow:0 8px 20px rgba(0,0,0,0.3);}}
            .card-icon{{font-size:40px;}}.card-title{{font-size:18px;font-weight:600;}}.card-value{{font-size:28px;font-weight:800;}}
            </style>
            <div class="card-container">
              <div class="card" style="background:linear-gradient(135deg,#00eaff,#007bff);">
                <div class="card-icon">\U0001f3e2</div><div class="card-title">Total Vendor</div><div id="vendorCount" class="card-value">0</div>
              </div>
              <div class="card" style="background:linear-gradient(135deg,#ff9a9e,#ff4f70);">
                <div class="card-icon">\U0001f4c4</div><div class="card-title">Total Transaksi</div><div id="trxCount" class="card-value">0</div>
              </div>
              <div class="card" style="background:linear-gradient(135deg,#42e695,#3bb2b8);">
                <div class="card-icon">\u23f1\ufe0f</div><div class="card-title">Rata-rata SLA (Hari)</div><div id="slaCount" class="card-value">0.00</div>
              </div>
            </div>
            <script>
            function animateValue(id,start,end,duration){{
                var range=end-start; var current=start;
                var increment=range/100; var stepTime=Math.abs(Math.floor(duration/100));
                var obj=document.getElementById(id);
                var timer=setInterval(function(){{
                    current+=increment;
                    if ((increment>0 && current>=end)||(increment<0&&current<=end)){{current=end;clearInterval(timer);}}
                    obj.innerHTML=current.toFixed(2);
                }},stepTime);}}
            animateValue("vendorCount",0,{total_vendor},1000);
            animateValue("trxCount",0,{total_transaksi},1200);
            animateValue("slaCount",0,{round(rata_sla_global_hari,2)},1500);
            </script>
            """
                components.html(card_template, height=250)

                # ==============================
                # 4) Tabel Data Detail
                # ==============================
                if df_vendor_filtered.shape[0] > 0:
                    st.subheader("\U0001f4cb Data Terfilter")
                    st.dataframe(df_vendor_filtered, use_container_width=True)

                    # ==============================
                    # 5) Agregasi per Vendor
                    # ==============================
                    rata_vendor = (
                        df_vendor_filtered
                        .groupby("NAMA VENDOR", dropna=True)["SLA_USED"]
                        .mean()
                        .reset_index()
                    )
                    rata_vendor["SLA_USED"] = pd.to_numeric(rata_vendor["SLA_USED"], errors="coerce")
                    rata_vendor["SLA (hari)"] = rata_vendor["SLA_USED"] / 86400.0
                    rata_vendor["SLA (format)"] = rata_vendor["SLA_USED"].apply(fmt_duration)

                    # ==============================
                    # 6) Leaderboard Vendor
                    # ==============================
                    st.subheader("\u26a1 Leaderboard SLA Vendor")
                    lb = rata_vendor.dropna(subset=["SLA_USED"]).copy()

                    if not lb.empty:
                        lb_sorted = lb.sort_values("SLA_USED", ascending=True).reset_index(drop=True)
                        min_sla = float(lb_sorted["SLA_USED"].min())
                        max_sla = float(lb_sorted["SLA_USED"].max())

                        rows = ""
                        for i, row in lb_sorted.iterrows():
                            nama = row["NAMA VENDOR"]
                            sla_used = float(row["SLA_USED"])
                            sla_hari = sla_used / 86400.0

                            badge = "\U0001f947" if i == 0 else "\U0001f948" if i == 1 else "\U0001f949" if i == 2 else "\U0001f6a8" if i == len(lb_sorted)-1 else ""

                            ratio = (sla_used - min_sla) / (max_sla - min_sla + 1e-9)
                            red = int(255 * ratio)
                            green = int(255 * (1 - ratio))
                            color = f"rgba({red},{green},120,0.85)"
                            progress_pct = int((sla_used / (max_sla+1e-9)) * 100)

                            rows += f"""
                        <div style='padding:10px 14px;border-radius:12px;background:{color};margin-bottom:8px;'>
                            <div style='display:flex;justify-content:space-between;font-weight:600;color:white;'>
                                <span>{badge} {nama}</span>
                                <span>{sla_hari:.2f} hari</span>
                            </div>
                            <div style="width:100%;background:#333;border-radius:6px;margin-top:6px;">
                                <div style="width:{progress_pct}%;background:#00eaff;height:8px;border-radius:6px;"></div>
                            </div>
                        </div>
                        """

                        leaderboard_html = f"""
                    <div style="max-height:500px;overflow-y:auto;display:flex;flex-direction:column;">
                        {rows}
                    </div>
                    """
                        components.html(leaderboard_html, height=600)

                    # ==============================
                    # 7) Grafik & Drilldown
                    # ==============================
                    st.subheader("\U0001f4ca Interaktif SLA per Vendor")
                    if not rata_vendor.empty and rata_vendor["SLA (hari)"].notna().any():
                        fig = px.bar(
                            rata_vendor, x="NAMA VENDOR", y="SLA (hari)",
                            color="SLA (hari)", color_continuous_scale="Blues",
                            title="Rata-rata SLA per Vendor"
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    clicked_vendor = st.selectbox("\U0001f50d Pilih vendor untuk drill-down detail:",
                                                  rata_vendor["NAMA VENDOR"].tolist() if not rata_vendor.empty else [])
                    if clicked_vendor:
                        df_vendor_detail = df_vendor_filtered[df_vendor_filtered["NAMA VENDOR"] == clicked_vendor]
                        if "JENIS TRANSAKSI" in df_vendor_detail.columns and not df_vendor_detail.empty:
                            st.markdown(f"### \U0001f4ca Detail SLA \u2014 {clicked_vendor}")

                            transaksi_group = (
                                df_vendor_detail
                                .groupby("JENIS TRANSAKSI")["SLA_USED"]
                                .mean()
                                .reset_index()
                            )
                            transaksi_group["SLA (hari)"] = transaksi_group["SLA_USED"] / 86400.0
                            transaksi_group["SLA (format)"] = transaksi_group["SLA_USED"].apply(fmt_duration)
                            st.dataframe(transaksi_group, use_container_width=True)

                            fig2 = px.bar(transaksi_group, x="SLA (hari)", y="JENIS TRANSAKSI",
                                          orientation="h", color="SLA (hari)", color_continuous_scale="Viridis")
                            st.plotly_chart(fig2, use_container_width=True)

                            jumlah_per_transaksi = (
                                df_vendor_detail
                                .groupby("JENIS TRANSAKSI")
                                .size()
                                .reset_index(name="Jumlah")
                            )
                            fig_pie = px.pie(jumlah_per_transaksi, values="Jumlah", names="JENIS TRANSAKSI")
                            st.plotly_chart(fig_pie, use_container_width=True)

                    # ==============================
                    # 8) Distribusi Multi Vendor
                    # ==============================
                    if len(selected_vendors) > 1 and "JENIS TRANSAKSI" in df_vendor_filtered.columns:
                        st.subheader(f"\U0001f4ca Distribusi Transaksi \u2014 {len(selected_vendors)} Vendor")
                        jumlah_multi = (
                            df_vendor_filtered.groupby(["NAMA VENDOR","JENIS TRANSAKSI"])
                            .size()
                            .reset_index(name="Jumlah")
                        )
                        pivot_jumlah = jumlah_multi.pivot(index="NAMA VENDOR", columns="JENIS TRANSAKSI", values="Jumlah").fillna(0)
                        st.dataframe(pivot_jumlah, use_container_width=True)

                else:
                    st.info("Tidak ada data untuk vendor yang dipilih.")
        else:
            st.info("Kolom 'NAMA VENDOR' tidak ditemukan.")

if (not _SLA_LAZY_TABS) or bool(getattr(tab_tren, "open", False)):
    with tab_tren:
        if available_sla_cols:
            st.subheader("\U0001f4c8 Trend Rata-rata SLA per Periode")
        
            # Hitung rata-rata per periode
            trend = df_filtered.groupby(df_filtered[periode_col].astype(str))[available_sla_cols].mean().reset_index()
            trend["PERIODE_SORTED"] = pd.Categorical(trend[periode_col], categories=selected_periode, ordered=True)
            trend = trend.sort_values("PERIODE_SORTED").reset_index(drop=True)

            # Tambahkan kolom nomor urut
            trend.insert(0, "No", range(1, len(trend) + 1))

            # Buat tampilan dengan format detik -> string
            trend_display = trend.copy()
            for col in available_sla_cols:
                trend_display[col] = trend_display[col].apply(seconds_to_sla_format)

            # PREMIUM TREND TABLE: tampilan alternatif dari trend_display yang sama.
            # Tabel native original tetap dipertahankan (sort, copy, audit).
            _slae_trend_last = str(trend.iloc[-1][periode_col]) if len(trend) else "—"
            _slae_trend_total_col = ("TOTAL WAKTU" if "TOTAL WAKTU" in available_sla_cols else
                                     ("KEUANGAN" if "KEUANGAN" in available_sla_cols else available_sla_cols[0]))
            _slae_latest_sec = trend.iloc[-1][_slae_trend_total_col] if len(trend) else None
            _slae_previous_sec = trend.iloc[-2][_slae_trend_total_col] if len(trend) > 1 else None
            _slae_latest_days = (float(_slae_latest_sec) / 86400 if _slae_latest_sec is not None and
                                 pd.notna(_slae_latest_sec) else None)
            _slae_change_days = (float(_slae_latest_sec - _slae_previous_sec) / 86400 if
                                 _slae_latest_sec is not None and pd.notna(_slae_latest_sec) and
                                 _slae_previous_sec is not None and pd.notna(_slae_previous_sec) else None)
            _slae_trend_cards = [
                ("PERIODE TERANALISIS", str(len(trend)), "Periode dengan data pada filter"),
                ("PERIODE TERAKHIR", _slae_trend_last, "Dalam rentang filter aktif"),
                ("SLA TERAKHIR", (f"{_slae_latest_days:.2f}".replace('.', ',') + " hari")
                 if _slae_latest_days is not None else "—", _slae_trend_total_col),
                ("PERUBAHAN SLA", (f"{_slae_change_days:+.2f}".replace('.', ',') + " hari")
                 if _slae_change_days is not None else "—", "Dibandingkan periode data sebelumnya"),
            ]
            _slae_trend_cards_html = "".join(
                '<div class="slae-kpi"><div class="slae-kpi-label">' + slae_html.escape(k) +
                '</div><div class="slae-kpi-value">' + slae_html.escape(v) +
                '</div><div class="slae-kpi-sub">' + slae_html.escape(d) + '</div></div>'
                for k, v, d in _slae_trend_cards
            )
            _slae_trend_head = '<th>Periode</th>' + ''.join(
                '<th>' + slae_html.escape(str(c)) + '</th>' for c in available_sla_cols
            )
            _slae_trend_rows = []
            for _slae_ridx, _slae_record in trend_display.iterrows():
                _slae_current = _slae_ridx == len(trend_display) - 1
                _slae_period_value = slae_html.escape(str(_slae_record[periode_col]))
                _slae_period_badge = (' <span class="slae-pill slae-pill-current">TERBARU</span>'
                                      if _slae_current else '')
                _slae_cells = []
                for _slae_col in available_sla_cols:
                    _slae_raw = trend.iloc[_slae_ridx][_slae_col]
                    _slae_txt = slae_html.escape(str(_slae_record[_slae_col]))
                    _slae_short = (f"{float(_slae_raw)/86400:.2f}".replace('.', ',') + " hari") if pd.notna(_slae_raw) else ""
                    _slae_cells.append(
                        '<td><div class="slae-duration">' + _slae_txt + '</div>' +
                        ('<div class="slae-small-value">' + _slae_short + '</div>' if _slae_short else '') +
                        '</td>'
                    )
                _slae_trend_rows.append(
                    '<tr' + (' class="slae-latest"' if _slae_current else '') + '>'
                    '<td><div class="slae-period">' + _slae_period_value + _slae_period_badge +
                    '</div><div class="slae-hint">Periode ' + str(int(_slae_record['No'])) +
                    '</div></td>' + ''.join(_slae_cells) + '</tr>'
                )
            st.markdown(
                '<div class="slae-wrap"><div class="slae-kpis">' + _slae_trend_cards_html +
                '</div><section class="slae-panel"><div class="slae-panel-head">'
                '<div class="slae-panel-title">Monthly SLA Trend Ledger</div>'
                '<div class="slae-panel-note">ASDP · HISTORICAL PERFORMANCE</div></div>'
                '<div class="slae-scroll"><table class="slae-table slae-trend-table"><thead><tr>' +
                _slae_trend_head + '</tr></thead><tbody>' + ''.join(_slae_trend_rows) +
                '</tbody></table></div></section><div class="slae-foot">'
                'Durasi ditampilkan dalam format asli serta hari desimal untuk memudahkan pembacaan. '
                'Baris terakhir menandai periode terbaru pada filter aktif, bukan data real-time.'
                '</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander("🔎 Tabel Tren original — sortir, salin & audit", expanded=False):
                st.dataframe(
                    trend_display.drop(columns=["PERIODE_SORTED"]).set_index("No").style.hide(axis="index"),
                    use_container_width=True
                )

            # ==============================
            # Grafik TOTAL WAKTU
            # ==============================
            if "TOTAL WAKTU" in available_sla_cols:
                fig, ax = plt.subplots(figsize=(10, 5))
                y_values_days = trend["TOTAL WAKTU"] / 86400
                x_values = trend[periode_col]

                ax.plot(x_values, y_values_days, marker='o', label="TOTAL WAKTU", color='#9467bd')

                # Tambahkan angka di setiap dot (2 angka desimal)
                for x, y in zip(x_values, y_values_days):
                    ax.text(x, y, f"{y:.2f}", ha='center', va='bottom', fontsize=9, color="black", weight="bold")

                ax.set_title("Trend Rata-rata SLA TOTAL WAKTU per Periode")
                ax.set_xlabel("Periode")
                ax.set_ylabel("Rata-rata SLA (hari)")
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend()

                for label in ax.get_xticklabels():
                    label.set_rotation(45)
                    label.set_ha('right')

                st.pyplot(fig)

            # ==============================
            # Grafik per proses
            # ==============================
            if proses_grafik_cols:
                fig3, axs = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
                fig3.suptitle("Trend Rata-rata SLA per Proses")
                axs = axs.flatten()

                for i, col in enumerate(proses_grafik_cols):
                    y_days = trend[col] / 86400
                    x_values = trend[periode_col]

                    axs[i].plot(x_values, y_days, marker='o', color='#75c8ff')

                    # Tambahkan angka di setiap dot (2 angka desimal)
                    for x, y in zip(x_values, y_days):
                        axs[i].text(x, y, f"{y:.2f}", ha='center', va='bottom', fontsize=8, color="black")

                    axs[i].set_title(col)
                    axs[i].set_ylabel("Hari")
                    axs[i].grid(True, linestyle='--', alpha=0.7)

                    for label in axs[i].get_xticklabels():
                        label.set_rotation(45)
                        label.set_ha('right')

                st.pyplot(fig3)

        else:
            st.info("Tidak ada kolom SLA yang dapat ditampilkan di tren.")


if (not _SLA_LAZY_TABS) or bool(getattr(tab_jumlah, "open", False)):
    with tab_jumlah:
        st.subheader("\U0001f4ca Jumlah Transaksi per Periode")
        jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name='Jumlah')
        jumlah_transaksi = jumlah_transaksi.sort_values(
            by=periode_col,
            key=lambda x: pd.Categorical(x, categories=selected_periode, ordered=True)
        )
        total_row = pd.DataFrame({periode_col: ["TOTAL"], 'Jumlah': [jumlah_transaksi['Jumlah'].sum()]})
        jumlah_transaksi = pd.concat([jumlah_transaksi, total_row], ignore_index=True)

        def highlight_total(row):
            return ['font-weight: bold' if row[periode_col] == "TOTAL" else '' for _ in row]

        # ========================================================================
        # PREMIUM TRANSACTION TABLE - tambahan visual; data dan grafik existing tetap.
        # ========================================================================
        import html as jtm_html

        jtm_body = jumlah_transaksi[jumlah_transaksi[periode_col].astype(str) != "TOTAL"].copy()
        jtm_total = int(pd.to_numeric(jtm_body["Jumlah"], errors="coerce").fillna(0).sum())
        jtm_n = len(jtm_body)
        jtm_peak = (jtm_body.loc[jtm_body["Jumlah"].idxmax(), periode_col]
                    if jtm_n else "Belum ada data")
        jtm_peak_v = int(jtm_body["Jumlah"].max()) if jtm_n else 0
        jtm_avg = (jtm_total / jtm_n) if jtm_n else 0.0
        jtm_max = max(jtm_peak_v, 1)

        st.markdown("""
    <style>
    .jtm-summary {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:12px 0 19px;}
    .jtm-card {padding:19px 20px;border-radius:17px;min-height:97px;
       background:linear-gradient(125deg,#102b4e,#153f65);color:#fff;
       border:1px solid #295778;box-shadow:0 7px 19px rgba(14,34,63,.12);}
    .jtm-card-label{font-size:11px;letter-spacing:1px;font-weight:750;color:#9fcce7;margin-bottom:11px;}
    .jtm-card-value{font-size:25px;font-weight:850;color:#f5fbff;line-height:1.14;overflow-wrap:anywhere;}
    .jtm-card-sub{color:#aac8dc;font-size:11px;margin-top:6px;}
    .jtm-frame{border:1px solid #d7e5ef;border-radius:20px;overflow:hidden;
       background:#fff;box-shadow:0 11px 30px rgba(13,46,77,.10);margin:7px 0 12px;}
    .jtm-frame-head{background:linear-gradient(110deg,#09294a,#144e72);padding:19px 22px;
       display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap;}
    .jtm-frame-title{color:#fff;font-size:18px;font-weight:850;letter-spacing:.2px;}
    .jtm-frame-meta{color:#a9eae2;font-size:11px;letter-spacing:1px;font-weight:800;}
    .jtm-table-scroll{max-height:560px;overflow:auto;}
    table.jtm-table{border-collapse:separate;border-spacing:0;width:100%;min-width:790px;
       font-family:Segoe UI,Arial,sans-serif;font-size:13px;text-align:left;}
    .jtm-table thead th{position:sticky;top:0;z-index:2;background:#eaf2f9;color:#24425e;
       font-size:11px;letter-spacing:.75px;padding:14px 17px;text-transform:uppercase;
       border-bottom:1px solid #d7e4ee;white-space:nowrap;}
    .jtm-table tbody td{padding:13px 17px;border-bottom:1px solid #e8eef4;color:#213b57;white-space:nowrap;}
    .jtm-table tbody tr:nth-child(even){background:#f4f8fc;}
    .jtm-table tbody tr:hover{background:#eaf9f8;}
    .jtm-table .jtm-num{text-align:right;font-variant-numeric:tabular-nums;font-weight:750;}
    .jtm-tag{display:inline-block;padding:4px 9px;border-radius:50px;font-size:11px;font-weight:800;}
    .jtm-up{background:#e0f8ef;color:#087557;}.jtm-down{background:#ffece7;color:#bd5435;}
    .jtm-flat{background:#eaf0f8;color:#62758e;}
    .jtm-progress{width:100%;min-width:100px;height:8px;background:#e0eaf3;border-radius:20px;overflow:hidden;}
    .jtm-progress-fill{height:100%;border-radius:20px;background:linear-gradient(90deg,#2d85f0,#20ccb7);}
    .jtm-table tfoot td{position:sticky;bottom:0;background:#123b5d;color:#fff;
       font-weight:850;padding:15px 17px;border-top:2px solid #38d1c4;}
    .jtm-table tfoot .jtm-num{color:#76f0d9;}
    .jtm-foot{font-size:11px;color:#688097;margin:10px 3px 18px;line-height:1.6;}
    @media(max-width:1000px){.jtm-summary{grid-template-columns:repeat(2,minmax(0,1fr));}}
    @media(max-width:540px){.jtm-summary{grid-template-columns:1fr;}.jtm-card{min-height:60px;}}
    </style>
    """, unsafe_allow_html=True)

        jtm_kpis = [
            ("TOTAL TRANSAKSI", f"{jtm_total:,}".replace(",", "."), "Periode aktif di sidebar"),
            ("BULAN TERSEDIA", str(jtm_n), "Bulan dengan data transaksi"),
            ("RATA-RATA / BULAN", f"{jtm_avg:,.0f}".replace(",", "."), "Dari bulan yang tersedia"),
            ("BULAN TERTINGGI", f"{jtm_peak_v:,}".replace(",", "."), str(jtm_peak)),
        ]
        jtm_cards_html = "".join(
            f'<div class="jtm-card"><div class="jtm-card-label">{jtm_html.escape(label)}</div>'
            f'<div class="jtm-card-value">{jtm_html.escape(val)}</div>'
            f'<div class="jtm-card-sub">{jtm_html.escape(note)}</div></div>'
            for label, val, note in jtm_kpis
        )
        st.markdown(f'<div class="jtm-summary">{jtm_cards_html}</div>', unsafe_allow_html=True)

        jtm_rows = []
        jtm_previous = None
        jtm_csv_rows = []
        for _, jtm_row in jtm_body.iterrows():
            jtm_period = str(jtm_row[periode_col])
            jtm_count = int(jtm_row["Jumlah"])
            jtm_share = 100 * jtm_count / jtm_total if jtm_total else 0.0
            jtm_width = 100 * jtm_count / jtm_max
            if jtm_previous is None:
                jtm_delta, jtm_growth, jtm_class, jtm_sign = None, None, "jtm-flat", "—"
            else:
                jtm_delta = jtm_count - jtm_previous
                jtm_growth = 100 * jtm_delta / jtm_previous if jtm_previous else None
                jtm_class = "jtm-up" if jtm_delta > 0 else ("jtm-down" if jtm_delta < 0 else "jtm-flat")
                jtm_sign = f"{jtm_delta:+,}".replace(",", ".")
            jtm_growth_html = "—" if jtm_growth is None else f"{jtm_growth:+.2f}%".replace(".", ",")
            jtm_csv_rows.append({
                "PERIODE": jtm_period, "Jumlah": jtm_count,
                "Selisih vs Periode Sebelumnya": jtm_delta,
                "Pertumbuhan (%)": round(jtm_growth, 2) if jtm_growth is not None else None,
                "Kontribusi (%)": round(jtm_share, 2),
            })
            jtm_rows.append(
                '<tr>'
                f'<td><b>{jtm_html.escape(jtm_period)}</b></td>'
                f'<td class="jtm-num">{jtm_count:,}</td>'
                f'<td class="jtm-num"><span class="jtm-tag {jtm_class}">{jtm_sign}</span></td>'
                f'<td class="jtm-num"><span class="jtm-tag {jtm_class}">{jtm_growth_html}</span></td>'
                f'<td class="jtm-num">{jtm_share:.2f}%</td>'
                f'<td><div class="jtm-progress" title="{jtm_count:,} transaksi">'
                f'<div class="jtm-progress-fill" style="width:{jtm_width:.2f}%"></div></div></td>'
                '</tr>'
            )
            jtm_previous = jtm_count

        jtm_table_html = (
            '<div class="jtm-frame"><div class="jtm-frame-head">'
            '<div class="jtm-frame-title">Transaction Volume Ledger</div>'
            '<div class="jtm-frame-meta">LIVE FILTER • MONTHLY PERFORMANCE</div></div>'
            '<div class="jtm-table-scroll"><table class="jtm-table"><thead><tr>'
            '<th>Periode</th><th style="text-align:right">Jumlah Transaksi</th>'
            '<th style="text-align:right">Selisih</th><th style="text-align:right">Growth</th>'
            '<th style="text-align:right">Kontribusi</th><th>Distribusi Volume</th>'
            '</tr></thead><tbody>' + ''.join(jtm_rows) + '</tbody><tfoot><tr>'
            '<td>TOTAL</td><td class="jtm-num">' + f'{jtm_total:,}'.replace(",", ".") + '</td>'
            '<td>—</td><td>—</td><td class="jtm-num">' + ("100,00%" if jtm_total else "—") + '</td><td>—</td>'
            '</tr></tfoot></table></div></div>'
        )
        st.markdown(jtm_table_html, unsafe_allow_html=True)
        st.markdown('<div class="jtm-foot">Selisih &amp; growth membandingkan bulan dengan data sebelumnya dalam filter aktif. '
                    'Tabel asli tetap tersedia untuk disortir dan disalin. Angka pada grafik existing tidak diubah.</div>',
                    unsafe_allow_html=True)
        with st.expander("🔎 Tabel data original — sortir, salin & audit", expanded=False):
            st.dataframe(jumlah_transaksi.style.apply(highlight_total, axis=1),
                         use_container_width=True)
        st.download_button(
            "⬇️ Ekspor tabel Jumlah Transaksi (CSV)",
            data=pd.DataFrame(jtm_csv_rows).to_csv(index=False).encode("utf-8-sig"),
            file_name="SLA_Jumlah_Transaksi_Tabel_Periode.csv", mime="text/csv",
            key="jtm_export_main_table",
        )

        fig_trans, ax_trans = plt.subplots(figsize=(10, 5))
        ax_trans.bar(
            jumlah_transaksi[jumlah_transaksi[periode_col] != "TOTAL"][periode_col],
            jumlah_transaksi[jumlah_transaksi[periode_col] != "TOTAL"]['Jumlah'],
            color='#ff9f7f'
        )
        ax_trans.set_title("Jumlah Transaksi per Periode")
        ax_trans.set_xlabel("Periode")
        ax_trans.set_ylabel("Jumlah Transaksi")
        ax_trans.grid(axis='y', linestyle='--', alpha=0.7)
        for label in ax_trans.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        st.pyplot(fig_trans)

        # ===========================================================================
        # ADVANCED TRANSACTION VOLUME COMPARISON
        # Tambahan murni di bawah grafik existing tab Jumlah Transaksi.
        # TIDAK memodifikasi df_filtered, periode_list, selected_periode, atau tab lain.
        # Dataset khusus perbandingan = SELURUH periode historis file upload.
        # ===========================================================================
        import html as jt_html
        import plotly.graph_objects as jt_go

        JT_MONTH_NAMES = (
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        )
        JT_MONTH_SHORT = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")
        JT_BLUE = "#4F91FA"
        JT_TEAL = "#21CAB5"
        JT_ORANGE = "#FFBA69"
        JT_WHITE = "#E9F2FE"


        def jt_format_int(num):
            return f"{int(num):,}".replace(",", ".")


        def jt_month_text(period):
            return f"{JT_MONTH_NAMES[period.month - 1]} {period.year}"


        def jt_delta_data(a, b):
            """Pertumbuhan terhadap A; hindari membagi nol/tidak ada data."""
            if a is None or b is None:
                return None, None
            a, b = int(a), int(b)
            gap = b - a
            if a == 0:
                return gap, (0.0 if b == 0 else None)
            return gap, 100 * gap / a


        def jt_format_change_pct(percent):
            return "N/A (basis 0)" if percent is None else f"{percent:+,.2f}%".replace(",", "_").replace(".", ",").replace("_", ".")


        def jt_summary_cards(label_a, label_b, count_a, count_b):
            delta, pct = jt_delta_data(count_a, count_b)
            sign_class = "positive" if delta is not None and delta >= 0 else "negative"
            label_a = jt_html.escape(str(label_a))
            label_b = jt_html.escape(str(label_b))
            cards = [
                ("PERIODE A", label_a, jt_format_int(count_a), "blue"),
                ("PERIODE B", label_b, jt_format_int(count_b), "teal"),
                ("SELISIH TRANSAKSI (B - A)", "Perubahan volume", f"{delta:+,}".replace(",", ".") if delta is not None else "—", sign_class),
                ("PERTUMBUHAN B vs A", "Dibanding periode A", jt_format_change_pct(pct), sign_class),
            ]
            html_cards = "".join(
                f'<div class="jt-kpi jt-kpi-{color}"><div class="jt-kpi-label">{jt_html.escape(k)}</div>'
                f'<div class="jt-kpi-period">{period}</div><div class="jt-kpi-value">{jt_html.escape(value)}</div></div>'
                for k, period, value, color in cards
            )
            st.markdown(f'<div class="jt-kpi-grid">{html_cards}</div>', unsafe_allow_html=True)
            return delta, pct


        def jt_plot_style(fig, title, y_title="Jumlah transaksi", height=410):
            fig.update_layout(
                title=dict(text=title, font=dict(size=19, color=JT_WHITE), x=0.03),
                height=height,
                paper_bgcolor="#0D2648",
                plot_bgcolor="#123155",
                font=dict(family="Segoe UI, Arial, sans-serif", color="#D2E4FA", size=12),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                    title_text="Tahun / Periode", font=dict(size=12, color="#E7F2FF"),
                    bgcolor="rgba(13,38,72,.45)", bordercolor="rgba(130,180,220,.22)", borderwidth=1,
                    itemclick="toggleothers"
                ),
                margin=dict(l=32, r=30, t=95, b=50),
                hovermode="x unified",
                barmode="group",
            )
            fig.update_xaxes(showgrid=False, tickfont=dict(size=11), zeroline=False)
            fig.update_yaxes(title=y_title, showgrid=True, gridcolor="rgba(140,170,200,.15)",
                             zeroline=False, rangemode="tozero")
            return fig


        def jt_months_series(month_counts, year, end_month=12):
            return [month_counts.get(pd.Period(year=year, month=m, freq="M")) for m in range(1, end_month + 1)]


        def jt_count_sum(values):
            return sum(int(x) for x in values if x is not None)


        def jt_export_buttons(df, mode_name, summary, extra_sheets=None):
            """CSV + Excel, mendukung 2 periode klasik maupun multi-pembanding."""
            detail_df = df.copy()
            csv_bytes = detail_df.to_csv(index=False).encode("utf-8-sig")
            left, right = st.columns(2)
            with left:
                jt_download_button_compat(
                    "⬇️ Download Data Perbandingan (CSV)",
                    data=csv_bytes,
                    file_name=f"SLA_Jumlah_Transaksi_{mode_name}.csv",
                    mime="text/csv",
                    key_base=f"jt_csv_{mode_name}_v2",
                )
            with right:
                try:
                    buf = io.BytesIO()
                    summary_df = pd.DataFrame(summary if isinstance(summary, list) else [summary])
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        summary_df.to_excel(writer, sheet_name="Ringkasan", index=False)
                        detail_df.to_excel(writer, sheet_name="Perbandingan", index=False)
                        if extra_sheets:
                            for sheet_name, sheet_df in extra_sheets.items():
                                if sheet_name not in {"Ringkasan", "Perbandingan", "Metodologi"}:
                                    sheet_df.to_excel(writer, sheet_name=str(sheet_name)[:31], index=False)
                        pd.DataFrame({"Ketentuan": [
                            "Sumber: seluruh histori PERIODE pada file upload terakhir.",
                            "Jumlah transaksi = jumlah baris per bulan, sesuai dashboard existing.",
                            "Tahun, bulan, dan rentang perbandingan dapat dipilih lebih dari dua.",
                            "Selisih/Growth dihitung terhadap acuan yang dipilih pengguna.",
                            "Growth = (Pembanding-Acuan)/Acuan x100%, tidak berlaku jika acuan nol.",
                            "Bulan tidak tersedia tidak diperlakukan sebagai nol transaksi.",
                            "Perbandingan rentang dengan durasi berlainan perlu normalisasi per bulan berdata.",
                            "Filter global tetap mengatur grafik lama; perbandingan memakai histori upload.",
                        ]}).to_excel(writer, sheet_name="Metodologi", index=False)
                    jt_download_button_compat(
                        "⬇️ Download Laporan Perbandingan (Excel)",
                        data=buf.getvalue(),
                        file_name=f"SLA_Jumlah_Transaksi_{mode_name}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key_base=f"jt_xlsx_{mode_name}_v2",
                    )
                except Exception as exc:
                    st.warning(f"Ekspor Excel belum tersedia: {type(exc).__name__}. Gunakan CSV sebagai alternatif.")


        def jt_executive_note(a, b, lab_a, lab_b, extra=""):
            change, pct = jt_delta_data(a, b)
            if change is None:
                headline = "Perbandingan belum memiliki data yang cukup."
            elif change > 0:
                headline = f"Volume transaksi meningkat {jt_format_int(change)} transaksi ({jt_format_change_pct(pct)}) dibandingkan periode A."
            elif change < 0:
                headline = f"Volume transaksi menurun {jt_format_int(abs(change))} transaksi ({jt_format_change_pct(pct)}) dibandingkan periode A."
            else:
                headline = "Volume transaksi pada kedua periode sama."
            st.markdown(
                '<div class="jt-note"><div class="jt-note-head">✦ AUTOMATED EXECUTIVE INSIGHT</div>'
                f'<div>{jt_html.escape(headline)}</div>'
                f'<div class="jt-note-small">Pembanding: {jt_html.escape(str(lab_a))} vs '
                f'{jt_html.escape(str(lab_b))}. {jt_html.escape(extra)}</div></div>',
                unsafe_allow_html=True,
            )


        st.markdown("""
    <style>
    .jt-hero {
      margin: 28px 0 18px; padding: 25px 30px; border-radius: 22px;
      background: radial-gradient(circle at 90% 10%, rgba(36,210,205,.18), transparent 35%),
                  linear-gradient(120deg, #0a234b 0%, #0c3560 48%, #183c71 100%);
      box-shadow: 0 12px 35px rgba(7,31,63,.22);
      border: 1px solid rgba(78,190,255,.27); color: #f2f8ff;
    }
    .jt-eyebrow { color: #5ce0d4; font-size: 12px; letter-spacing: 2px; font-weight: 800; }
    .jt-hero h2 { margin: 5px 0 6px; font-size: clamp(23px, 3vw, 33px); color: #fff !important; }
    .jt-hero p { margin: 0; font-size: 14px; color: #c7ddf9; }
    .jt-kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; margin: 18px 0; }
    .jt-kpi { position: relative; overflow: hidden; min-height: 128px; border-radius: 18px;
      background: linear-gradient(135deg, #092341 0%, #15375c 100%);
      border: 1px solid rgba(123,192,235,.26); padding: 17px 16px; box-sizing: border-box;
      box-shadow: 0 8px 24px rgba(5,26,46,.17); color: #fff; }
    .jt-kpi:after { content:""; position:absolute; top:-55px; right:-40px; width:140px; height:140px;
      border-radius:50%; background:rgba(80,175,255,.11); }
    .jt-kpi-teal:after, .jt-kpi-positive:after { background:rgba(39,226,179,.14); }
    .jt-kpi-negative:after { background:rgba(255,150,93,.17); }
    .jt-kpi-label { font-size:10px; color:#98bfdf; font-weight:800; letter-spacing:1.1px; }
    .jt-kpi-period { font-size:12px; color:#d3e2f3; margin:10px 0 6px; min-height:17px; overflow-wrap:anywhere; }
    .jt-kpi-value { color:#fff; font-weight:850; font-size:clamp(20px,2.2vw,28px); overflow-wrap:anywhere; }
    .jt-kpi-teal .jt-kpi-value, .jt-kpi-positive .jt-kpi-value { color: #53efc8; }
    .jt-kpi-negative .jt-kpi-value { color:#ffb487; }
    .jt-note { border-radius:16px; margin:14px 0 15px; padding:18px 22px;
      border:1px solid rgba(80,169,234,.24); background:linear-gradient(100deg,#102e50,#103b55);
      color:#f0f8ff; font-size:15px; line-height:1.5; }
    .jt-note-head { color:#5ce0d4; font-size:11px; letter-spacing:1.1px; font-weight:850; margin-bottom:8px; }
    .jt-note-small { font-size:12px; color:#bbd1e6; margin-top:8px; }
    @media(max-width:980px) {.jt-kpi-grid {grid-template-columns:repeat(2,minmax(0,1fr));}}
    @media(max-width:510px) {.jt-kpi-grid {grid-template-columns:1fr;}.jt-hero{padding:20px;}}
    </style>
    """, unsafe_allow_html=True)

        st.markdown("""
    <div class="jt-hero">
      <div class="jt-eyebrow">ASDP • TRANSACTION INTELLIGENCE</div>
      <h2>Advanced Transaction Comparison</h2>
      <p>Analisis komparatif jumlah transaksi lintas tahun, lintas bulan, dan rentang periode.
         Semua grafik & laporan existing tetap dipertahankan.</p>
    </div>
    """, unsafe_allow_html=True)
        st.caption(
            "💡 Grafik di atas tetap mengikuti Filter Rentang Periode pada sidebar. "
            "Khusus modul perbandingan di bawah, opsi periodenya mencakup seluruh histori "
            "yang tersedia dalam file Excel terakhir sehingga bisa membandingkan lintas tahun."
        )

        # Membaca hanya kolom periode dari data asli (tidak mengubah dataset modul lain).
        if "PERIODE_DATETIME" in df_raw.columns:
            jt_period_dt = pd.to_datetime(df_raw["PERIODE_DATETIME"], errors="coerce")
        else:
            jt_period_dt = df_raw[periode_col].apply(parse_period_label_to_timestamp)

        jt_valid_periods = jt_period_dt.dropna()
        jt_invalid_count = int(len(jt_period_dt) - len(jt_valid_periods))

        if jt_valid_periods.empty:
            st.warning("Tidak tersedia data periode yang dapat dibandingkan. Periksa format PERIODE pada upload terakhir.")
        else:
            jt_period_months = jt_valid_periods.dt.to_period("M")
            jt_grouped = jt_period_months.value_counts(sort=False).sort_index()
            jt_counts = {p: int(count) for p, count in jt_grouped.items()}
            jt_period_options = sorted(jt_counts.keys())
            jt_year_options = sorted({p.year for p in jt_period_options})
            jt_latest = jt_period_options[-1]

            if jt_invalid_count:
                st.warning(f"{jt_format_int(jt_invalid_count)} baris memiliki periode tidak valid/kosong dan tidak digunakan dalam perbandingan.")

            jt_mode_year, jt_mode_month, jt_mode_range = st.tabs([
                "📆 Perbandingan Antar Tahun", "🗓️ Perbandingan Bulan & Tahun", "🔁 Perbandingan Rentang Periode"
            ])

            # ==========================================================================
            # MULTI-COMPARISON UPGRADE (v3): fleksibel 2, 3, atau lebih pembanding.
            # Existing helpers, Grafik Jumlah Transaksi, export CSV/Excel, dan tiga mode
            # tetap dipertahankan. Seluruh kalkulasi di bawah memakai jt_counts historis.
            # ==========================================================================
            JT_MULTI_PALETTE = (
                "#4F91FA", "#21CAB5", "#FFBA69", "#A78BFA", "#F472A1", "#8ECE76",
                "#22D3EE", "#FACC65", "#7CA4FC", "#E879F9", "#F08B6D", "#63D6BA",
            )


            def jt_color_at(position):
                return JT_MULTI_PALETTE[position % len(JT_MULTI_PALETTE)]


            JT_FIXED_YEAR_COLORS = {
                2022: "#F6C445",  # kuning
                2023: "#21CAB5",  # turquoise
                2024: "#5B8FF9",  # biru
                2025: "#A78BFA",  # ungu
                2026: "#F472A1",  # pink
                2027: "#8ECE76",  # hijau
                2028: "#22D3EE",  # cyan
                2029: "#F08B6D",  # coral
                2030: "#7DD3FC",  # sky
            }


            def jt_year_color(year, position=0):
                return JT_FIXED_YEAR_COLORS.get(int(year), jt_color_at(position))


            def jt_text_labels(values):
                labels = []
                for val in values:
                    if val is None or pd.isna(val):
                        labels.append("")
                    else:
                        labels.append(jt_format_int(int(val)))
                return labels


            def jt_download_button_compat(label, *, data, file_name, mime, key_base):
                """Kompatibilitas lintas versi Streamlit agar tombol download tidak crash."""
                try:
                    return st.download_button(
                        label,
                        data=data,
                        file_name=file_name,
                        mime=mime,
                        key=key_base,
                        use_container_width=True,
                    )
                except Exception:
                    # Fallback aman untuk versi Streamlit yang sensitif terhadap state / parameter tertentu.
                    fallback_label = f"{label} • {file_name}"
                    return st.download_button(
                        fallback_label,
                        data=data,
                        file_name=file_name,
                        mime=mime,
                    )


            def jt_num_or_dash(value):
                return "—" if value is None or pd.isna(value) else jt_format_int(value)


            def jt_growth_signed(growth):
                return "N/A (basis 0)" if growth is None else jt_format_change_pct(growth)


            def jt_multi_cards(records, baseline_name):
                """Empat KPI klasik untuk tepat dua periode; kartu adaptif saat 3+."""
                if len(records) == 2:
                    reference = next((r for r in records if r["name"] == baseline_name), records[0])
                    comparison = next((r for r in records if r["name"] != reference["name"]), records[1])
                    return jt_summary_cards(
                        reference["label"], comparison["label"],
                        reference["total"], comparison["total"],
                    )
                baseline = next((record for record in records if record["name"] == baseline_name), records[0])
                cards_html = []
                for i, record in enumerate(records):
                    delta, growth = jt_delta_data(baseline["total"], record["total"])
                    is_baseline = record["name"] == baseline["name"]
                    subtitle = "PERIODE ACUAN" if is_baseline else f"Δ {delta:+,} · {jt_growth_signed(growth)}"
                    subtitle = subtitle.replace(",", ".") if not is_baseline else subtitle
                    cards_html.append(
                        '<div class="jt-multi-card" style="border-top:3px solid ' + jt_color_at(i) + '">'
                        '<div class="jt-multi-label">' + jt_html.escape(str(record["name"])) + '</div>'
                        '<div class="jt-multi-period">' + jt_html.escape(str(record["label"])) + '</div>'
                        '<div class="jt-multi-value">' + jt_format_int(record["total"]) + '</div>'
                        '<div class="jt-multi-sub">' + jt_html.escape(subtitle) + '</div>'
                        '</div>'
                    )
                st.markdown('<div class="jt-multi-grid">' + ''.join(cards_html) + '</div>', unsafe_allow_html=True)


            def jt_multi_note(text, extra=""):
                st.markdown(
                    '<div class="jt-note"><div class="jt-note-head">✦ AUTOMATED EXECUTIVE INSIGHT</div>'
                    '<div>' + jt_html.escape(str(text)) + '</div>'
                    '<div class="jt-note-small">' + jt_html.escape(str(extra)) + '</div></div>',
                    unsafe_allow_html=True,
                )


            def jt_safe_percent_difference(base, comparison):
                if base is None or comparison is None:
                    return None, None
                diff = comparison - base
                if base == 0:
                    return diff, (0.0 if comparison == 0 else None)
                return diff, 100 * diff / base


            def jt_reset_invalid_choice(widget_key, available):
                if widget_key in st.session_state and st.session_state[widget_key] not in available:
                    del st.session_state[widget_key]


            st.markdown("""
        <style>
        .jt-multi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
         gap:12px;margin:16px 0 18px;}
        .jt-multi-card{background:linear-gradient(120deg,#092541,#154166);border-radius:16px;
         padding:19px 18px;min-height:112px;color:#fff;box-shadow:0 9px 25px rgba(8,33,60,.17);
         border-left:1px solid #365d7e;border-right:1px solid #365d7e;border-bottom:1px solid #365d7e;}
        .jt-multi-label{font-size:10px;letter-spacing:1px;color:#a9d1e7;font-weight:800;}
        .jt-multi-period{font-size:11px;color:#d5eaf5;margin:9px 0 6px;line-height:1.35;}
        .jt-multi-value{font-size:27px;font-weight:850;letter-spacing:.1px;color:#f9fcff;}
        .jt-multi-sub{font-size:11px;font-weight:700;color:#77e8cf;margin-top:8px;}
        .jt-section-heading{margin:18px 0 10px;padding:12px 15px;border-left:4px solid #16bea9;
         background:#eaf3f9;color:#183e5f;font-weight:850;border-radius:0 9px 9px 0;}
        .jt-data-caption{font-size:12px;color:#637c95;margin:8px 0 12px;}
        </style>
        """, unsafe_allow_html=True)

            # ==========================================
            # MODE 1 - TAHUN JAMAK (YoY multi-series)
            # ==========================================
            with jt_mode_year:
                st.markdown("#### Year-on-Year • Perbandingan Multi-Tahun")
                st.caption("Pilih dua, tiga, atau seluruh tahun yang tersedia. Tahun acuan dapat dipilih bebas.")
                jt_year_defaults = jt_year_options[-2:] if len(jt_year_options) > 1 else jt_year_options[:]
                jt_year_selected = st.multiselect(
                    "Pilih tahun yang akan dibandingkan",
                    jt_year_options,
                    default=jt_year_defaults,
                    key="jt_year_multi_v3",
                    help="Boleh memilih 2, 3, 4, dan seterusnya; tidak dibatasi pada dua tahun.",
                )
                jt_year_selected = sorted(set(jt_year_selected))
                if not jt_year_selected:
                    st.info("Pilih setidaknya satu tahun untuk menampilkan data; pilih dua atau lebih untuk membandingkan.")
                else:
                    jt_reset_invalid_choice("jt_year_basis_v3", jt_year_selected)
                    jt_yc1, jt_yc2 = st.columns([1, 1.25])
                    with jt_yc1:
                        jt_year_basis = st.selectbox("Tahun acuan (basis)", jt_year_selected,
                                                      key="jt_year_basis_v3")
                    with jt_yc2:
                        jt_align_months = st.checkbox(
                            "Samakan horizon bulan (YTD)", value=True, key="jt_align_months",
                            help="Horizon perbandingan diambil dari bulan terakhir terpendek di antara tahun terpilih. "
                                 "Bulan tanpa data tetap kosong, bukan dianggap nol.",
                        )
                    jt_last_by_year = {
                        year: max(p.month for p in jt_period_options if p.year == year)
                        for year in jt_year_selected
                    }
                    jt_end_month = min(jt_last_by_year.values()) if jt_align_months else 12
                    jt_month_labels = list(JT_MONTH_SHORT[:jt_end_month])
                    jt_label_suffix = f"Jan–{JT_MONTH_SHORT[jt_end_month-1]}" if jt_align_months else "Jan–Des (tersedia)"
                    jt_year_series = {
                        year: jt_months_series(jt_counts, year, jt_end_month) for year in jt_year_selected
                    }
                    jt_year_totals = {year: jt_count_sum(jt_year_series[year]) for year in jt_year_selected}
                    jt_year_coverages = {
                        year: sum(x is not None for x in jt_year_series[year]) for year in jt_year_selected
                    }
                    jt_year_records = [
                        {"name": str(year), "label": f"{year} • {jt_label_suffix}", "total": jt_year_totals[year]}
                        for year in jt_year_selected
                    ]
                    jt_multi_cards(jt_year_records, str(jt_year_basis))

                    if len(jt_year_selected) == 1:
                        st.info("Hanya satu tahun yang dipilih. Tambahkan tahun lain untuk melihat perbandingan YoY.")
                    if len(set(jt_year_coverages.values())) > 1 or any(
                        count < jt_end_month for count in jt_year_coverages.values()
                    ):
                        st.warning(
                            "Cakupan data per tahun berbeda. Bulan yang belum ada dalam file tidak dihitung "
                            "sebagai nol transaksi. Tinjau coverage sebelum menarik kesimpulan pertumbuhan."
                        )
                    if not jt_align_months and len(set(jt_last_by_year.values())) > 1:
                        st.info("Periode tahunan belum tentu setara karena bulan terakhir berbeda. "
                                "Aktifkan YTD untuk membandingkan horizon bulan yang sama.")

                    jt_year_figure = jt_go.Figure()
                    for i, year in enumerate(jt_year_selected):
                        values = jt_year_series[year]
                        year_color = jt_year_color(year, i)
                        jt_year_figure.add_trace(jt_go.Bar(
                            x=jt_month_labels, y=values, name=str(year),
                            marker_color=year_color,
                            text=jt_text_labels(values),
                            textposition="outside",
                            textfont=dict(size=11, color="#F8FCFF"),
                            cliponaxis=False,
                            hovertemplate=f"Tahun {year}<br>%{{x}}: %{{y:,.0f}} transaksi<extra></extra>",
                        ))
                    jt_plot_style(jt_year_figure, "Distribusi Transaksi Bulanan • Multi-Tahun", height=445)
                    jt_year_figure.update_layout(legend_title_text="Tahun")
                    st.plotly_chart(jt_year_figure, use_container_width=True, key="jt_year_chart")

                    jt_year_cumulative = jt_go.Figure()
                    for i, year in enumerate(jt_year_selected):
                        running = 0
                        vals = []
                        for count in jt_year_series[year]:
                            if count is None:
                                vals.append(None)
                            else:
                                running += int(count)
                                vals.append(running)
                        year_color = jt_year_color(year, i)
                        jt_year_cumulative.add_trace(jt_go.Scatter(
                            x=jt_month_labels, y=vals, name=str(year),
                            mode="lines+markers+text", connectgaps=False,
                            line=dict(color=year_color, width=3),
                            marker=dict(size=8, color=year_color),
                            text=jt_text_labels(vals), textposition="top center",
                            textfont=dict(size=10, color="#F8FCFF"),
                            hovertemplate=f"{year} • %{{x}}<br>Akumulasi: %{{y:,.0f}}<extra></extra>",
                        ))
                    jt_plot_style(jt_year_cumulative, "Tren Akumulasi Transaksi per Tahun", "Akumulasi transaksi", 370)
                    jt_year_cumulative.update_layout(legend_title_text="Tahun")
                    st.plotly_chart(jt_year_cumulative, use_container_width=True, key="jt_year_accumulation_v3")
                    st.caption("Warna tahun dibuat konsisten agar lebih mudah dibaca pada legend. Nilai transaksi ditampilkan langsung pada batang dan titik grafik.")

                    jt_year_rows = []
                    for m in range(1, jt_end_month + 1):
                        row = {"Bulan": JT_MONTH_NAMES[m-1]}
                        basis_val = jt_year_series[jt_year_basis][m-1]
                        for year in jt_year_selected:
                            count = jt_year_series[year][m-1]
                            row[f"Tahun {year}"] = count
                            if year != jt_year_basis:
                                diff, growth = jt_delta_data(basis_val, count)
                                row[f"Selisih {year} vs {jt_year_basis}"] = diff
                                row[f"Growth {year} vs {jt_year_basis} (%)"] = (
                                    round(growth, 2) if growth is not None else None
                                )
                        jt_year_rows.append(row)
                    jt_year_table = pd.DataFrame(jt_year_rows)
                    st.markdown("<div class='jt-section-heading'>Matriks Perbandingan Bulanan Semua Tahun</div>",
                                unsafe_allow_html=True)
                    st.dataframe(jt_year_table, hide_index=True, use_container_width=True)
                    jt_year_summary = []
                    for year in jt_year_selected:
                        diff, growth = jt_delta_data(jt_year_totals[jt_year_basis], jt_year_totals[year])
                        jt_year_summary.append({
                            "Tahun": year,
                            "Status": "ACUAN" if year == jt_year_basis else "PEMBANDING",
                            "Horizon": jt_label_suffix,
                            "Total Transaksi": jt_year_totals[year],
                            "Bulan Memiliki Data": jt_year_coverages[year],
                            "Total Bulan Horizon": jt_end_month,
                            f"Selisih vs {jt_year_basis}": diff,
                            f"Growth vs {jt_year_basis} (%)": round(growth, 2) if growth is not None else None,
                        })
                    jt_year_summary_df = pd.DataFrame(jt_year_summary)
                    st.markdown("<div class='jt-section-heading'>Executive Comparison • Tahun Terpilih</div>",
                                unsafe_allow_html=True)
                    st.dataframe(jt_year_summary_df, use_container_width=True, hide_index=True)
                    jt_best_year = max(jt_year_selected, key=lambda yr: jt_year_totals[yr])
                    jt_multi_note(
                        f"Dari {len(jt_year_selected)} tahun terpilih, tahun {jt_best_year} memiliki volume "
                        f"terbesar dengan {jt_format_int(jt_year_totals[jt_best_year])} transaksi. "
                        f"Tahun acuan adalah {jt_year_basis}.",
                        "Pertumbuhan dihitung terhadap tahun acuan. Data kosong dipisahkan dari nol; "
                        "total yang cakupannya berbeda tidak langsung sebanding.",
                    )
                    jt_export_buttons(jt_year_table, "Antar_Tahun_Multi", jt_year_summary,
                                      extra_sheets={"Ringkasan Perbandingan": jt_year_summary_df})

            # ==========================================
            # MODE 2 - BULAN & TAHUN JAMAK
            # ==========================================
            with jt_mode_month:
                st.markdown("#### Month-to-Month • Perbandingan Multi-Bulan & Multi-Tahun")
                st.caption("Pilih beberapa bulan dari tahun yang sama ataupun tahun berbeda.")
                jt_month_defaults = jt_period_options[-2:] if len(jt_period_options) >= 2 else jt_period_options[:]
                jt_selected_months = st.multiselect(
                    "Pilih bulan-tahun untuk dibandingkan",
                    jt_period_options,
                    default=jt_month_defaults,
                    format_func=jt_month_text,
                    key="jt_month_multi_v3",
                    help="Contoh: Januari 2024, Januari 2025, Januari 2026 atau gabungan bulan bebas.",
                )
                jt_selected_months = sorted(set(jt_selected_months))
                if not jt_selected_months:
                    st.info("Pilih setidaknya satu bulan-tahun dari histori transaksi yang tersedia.")
                else:
                    jt_reset_invalid_choice("jt_month_basis_v3", jt_selected_months)
                    jt_month_basis = st.selectbox(
                        "Bulan-tahun acuan (basis)", jt_selected_months,
                        format_func=jt_month_text, key="jt_month_basis_v3",
                    )
                    jt_month_records = [
                        {"name": str(period), "label": jt_month_text(period), "total": jt_counts[period]}
                        for period in jt_selected_months
                    ]
                    jt_multi_cards(jt_month_records, str(jt_month_basis))
                    if len(jt_selected_months) == 1:
                        st.info("Tambahkan bulan lain agar dapat melihat selisih dan pertumbuhan antar bulan.")

                    jt_month_fig = jt_go.Figure()
                    jt_month_colors = [jt_year_color(p.year, i) for i, p in enumerate(jt_selected_months)]
                    jt_month_fig.add_trace(jt_go.Bar(
                        x=[jt_month_text(p) for p in jt_selected_months],
                        y=[jt_counts[p] for p in jt_selected_months],
                        marker_color=jt_month_colors,
                        text=[jt_format_int(jt_counts[p]) for p in jt_selected_months],
                        textposition="outside", textfont=dict(size=11, color="#F8FCFF"),
                        cliponaxis=False, showlegend=False,
                        hovertemplate="%{x}<br>%{y:,.0f} transaksi<extra></extra>",
                    ))
                    jt_plot_style(jt_month_fig, "Perbandingan Langsung Bulan-Tahun Terpilih", height=410)
                    jt_month_fig.update_xaxes(tickangle=-30)
                    st.plotly_chart(jt_month_fig, use_container_width=True, key="jt_month_duel_chart")

                    # Momentum 6 bulan sebelumnya: mempertahankan grafik existing, diperluas N seri.
                    jt_momentum_fig = jt_go.Figure()
                    jt_momentum_rows = []
                    for i, period in enumerate(jt_selected_months):
                        periods = pd.period_range(end=period, periods=6, freq="M")
                        vals = [jt_counts.get(x) for x in periods]
                        jt_momentum_fig.add_trace(jt_go.Scatter(
                            x=[f"T-{5-j}" if j < 5 else "T" for j in range(6)],
                            y=vals, name=jt_month_text(period), mode="lines+markers+text",
                            line=dict(color=jt_year_color(period.year, i), width=3), marker=dict(size=8),
                            text=jt_text_labels(vals), textposition="top center",
                            textfont=dict(size=10, color="#F8FCFF"),
                            customdata=[jt_month_text(x) for x in periods],
                            hovertemplate="%{customdata}<br>%{y:,.0f} transaksi<extra></extra>",
                            connectgaps=False,
                        ))
                        for j, (p, val) in enumerate(zip(periods, vals)):
                            jt_momentum_rows.append({
                                "Pilihan": jt_month_text(period),
                                "Posisi": f"T-{5-j}" if j < 5 else "T",
                                "Periode": jt_month_text(p),
                                "Jumlah Transaksi": val,
                            })
                    jt_plot_style(jt_momentum_fig,
                                  "Momentum 6 Bulan • Setiap Pilihan Bulan-Tahun", height=400)
                    st.plotly_chart(jt_momentum_fig, use_container_width=True, key="jt_month_momentum_chart")
                    st.caption("T = bulan yang dipilih, T-1 = satu bulan sebelumnya. "
                               "Bulan yang belum tercatat pada file tetap kosong, tidak dikonversi ke nol.")

                    jt_month_rows = []
                    jt_basis_volume = jt_counts[jt_month_basis]
                    previous_value = None
                    for period in jt_selected_months:
                        val = jt_counts[period]
                        diff_basis, growth_basis = jt_delta_data(jt_basis_volume, val)
                        diff_previous, growth_previous = jt_delta_data(previous_value, val)
                        jt_month_rows.append({
                            "Bulan & Tahun": jt_month_text(period),
                            "Status": "ACUAN" if period == jt_month_basis else "PEMBANDING",
                            "Jumlah Transaksi": val,
                            "Selisih vs Acuan": diff_basis,
                            "Growth vs Acuan (%)": round(growth_basis, 2) if growth_basis is not None else None,
                            "Selisih vs Pilihan Sebelumnya": diff_previous,
                            "Growth vs Pilihan Sebelumnya (%)": (
                                round(growth_previous, 2) if growth_previous is not None else None
                            ),
                        })
                        previous_value = val
                    jt_month_table = pd.DataFrame(jt_month_rows)
                    st.markdown("<div class='jt-section-heading'>Matriks Perbandingan Semua Bulan Terpilih</div>",
                                unsafe_allow_html=True)
                    st.dataframe(jt_month_table, use_container_width=True, hide_index=True)
                    jt_top_month = max(jt_selected_months, key=lambda period: jt_counts[period])
                    jt_multi_note(
                        f"Dari {len(jt_selected_months)} bulan-tahun yang dipilih, "
                        f"volume tertinggi terdapat pada {jt_month_text(jt_top_month)} "
                        f"sebanyak {jt_format_int(jt_counts[jt_top_month])} transaksi.",
                        f"Basis pembanding: {jt_month_text(jt_month_basis)}. "
                        "Selisih terhadap pilihan sebelumnya mengikuti urutan kronologis.",
                    )
                    jt_export_buttons(
                        pd.DataFrame(jt_momentum_rows), "Antar_Bulan_Multi", jt_month_rows,
                        extra_sheets={"Matriks Bulan": jt_month_table},
                    )

            # ==========================================
            # MODE 3 - RENTANG PERIODE JAMAK
            # ==========================================
            with jt_mode_range:
                st.markdown("#### Period-to-Period • Multi-Rentang Periode Bebas")
                st.caption("Tentukan jumlah rentang, lalu tetapkan awal–akhir masing-masing. "
                           "Dapat membandingkan 2, 3, 4, atau lebih rentang sekaligus.")
                jt_latest_year = jt_latest.year
                jt_previous_year = jt_latest_year - 1
                jt_curr_year_periods = [p for p in jt_period_options if p.year == jt_latest_year]
                jt_prev_year_periods = [p for p in jt_period_options if p.year == jt_previous_year]
                jt_default_b_start = jt_curr_year_periods[0] if jt_curr_year_periods else jt_period_options[0]
                jt_default_b_end = jt_latest
                jt_default_a_start = jt_prev_year_periods[0] if jt_prev_year_periods else jt_period_options[0]
                jt_previous_ytd = [p for p in jt_prev_year_periods if p.month <= jt_latest.month]
                jt_default_a_end = jt_previous_ytd[-1] if jt_previous_ytd else (
                    jt_prev_year_periods[-1] if jt_prev_year_periods else jt_period_options[-1]
                )

                # Tanpa hard limit untuk jumlah perbandingan. Pengguna bisa menambah kapan pun.
                jt_n_ranges = int(st.number_input(
                    "Jumlah rentang periode yang ingin dibandingkan",
                    min_value=2, value=2, step=1, key="jt_range_count_v3",
                    help="Mulai dua rentang, tambah menjadi tiga, empat, dan seterusnya.",
                ))
                if jt_n_ranges > 20:
                    st.info("Banyak rentang dipilih. Grafik serta tabel akan lebih lebar; "
                            "gunakan mode layar lebar untuk hasil terbaik.")

                jt_ranges = []
                jt_invalid_ranges = []
                for i in range(jt_n_ranges):
                    range_label = f"Rentang {i+1}"
                    st.markdown(f"**{range_label}**" + (" • Basis awal" if i == 0 else ""))
                    if i == 0:
                        default_start, default_end = jt_default_a_start, jt_default_a_end
                    elif i == 1:
                        default_start, default_end = jt_default_b_start, jt_default_b_end
                    else:
                        offset = i - 2
                        default_year_index = max(0, len(jt_year_options) - 1 - offset)
                        default_year = jt_year_options[default_year_index]
                        year_available = [p for p in jt_period_options if p.year == default_year]
                        default_start, default_end = year_available[0], year_available[-1]
                    jtr_c1, jtr_c2 = st.columns(2)
                    with jtr_c1:
                        start = st.selectbox(
                            f"Mulai {range_label.lower()}", jt_period_options,
                            index=jt_period_options.index(default_start),
                            format_func=jt_month_text, key=f"jt_range_start_v3_{i}",
                        )
                    with jtr_c2:
                        end = st.selectbox(
                            f"Sampai {range_label.lower()}", jt_period_options,
                            index=jt_period_options.index(default_end),
                            format_func=jt_month_text, key=f"jt_range_end_v3_{i}",
                        )
                    if start > end:
                        jt_invalid_ranges.append(range_label)
                        continue
                    periods = list(pd.period_range(start=start, end=end, freq="M"))
                    values = [jt_counts.get(period) for period in periods]
                    months_with_data = sum(value is not None for value in values)
                    total = jt_count_sum(values)
                    jt_ranges.append({
                        "name": range_label,
                        "label": f"{jt_month_text(start)} – {jt_month_text(end)}",
                        "total": total,
                        "months": len(periods),
                        "observed": months_with_data,
                        "avg": (total / months_with_data) if months_with_data else None,
                        "periods": periods, "values": values,
                        "start": start, "end": end,
                    })

                if jt_invalid_ranges:
                    st.warning("Periode mulai harus sebelum atau sama dengan periode akhir pada: "
                               + ", ".join(jt_invalid_ranges) + ". Sesuaikan pilihan untuk menampilkan perbandingan.")
                else:
                    jt_range_names = [record["name"] for record in jt_ranges]
                    jt_reset_invalid_choice("jt_range_basis_v3", jt_range_names)
                    jt_range_basis_name = st.selectbox(
                        "Rentang acuan (basis)", jt_range_names, key="jt_range_basis_v3",
                    )
                    jt_range_basis = next(r for r in jt_ranges if r["name"] == jt_range_basis_name)
                    jt_multi_cards(jt_ranges, jt_range_basis_name)

                    jt_durations = {r["months"] for r in jt_ranges}
                    if len(jt_durations) > 1:
                        st.warning("Durasi rentang tidak sama. Selisih total kurang sebanding; "
                                   "gunakan rata-rata per bulan berdata untuk perbandingan yang dinormalisasi.")
                    jt_gaps = [r for r in jt_ranges if r["observed"] < r["months"]]
                    if jt_gaps:
                        st.info("Ada rentang dengan bulan tanpa data: " + ", ".join(
                            f'{r["name"]} ({r["observed"]}/{r["months"]} bulan)' for r in jt_gaps
                        ) + ". Bulan kosong tidak dianggap nol dan rata-rata hanya dihitung dari bulan berdata.")
                    overlap_pairs = [
                        f'{r1["name"]}–{r2["name"]}'
                        for i, r1 in enumerate(jt_ranges)
                        for r2 in jt_ranges[i+1:]
                        if r1["start"] <= r2["end"] and r2["start"] <= r1["end"]
                    ]
                    if overlap_pairs:
                        st.info("Rentang saling tumpang tindih: " + ", ".join(overlap_pairs[:10])
                                + (" dan lainnya." if len(overlap_pairs) > 10 else ".")
                                + " Bulan tumpang tindih muncul di masing-masing rentang.")

                    jtr_m1, jtr_m2, jtr_m3, jtr_m4 = st.columns(4)
                    jtr_m1.metric("Jumlah Rentang", str(len(jt_ranges)))
                    jtr_m2.metric("Bulan Acuan", f'{jt_range_basis["months"]} bulan')
                    jtr_m3.metric("Data Bulan Acuan", f'{jt_range_basis["observed"]}/{jt_range_basis["months"]}')
                    jtr_m4.metric("Rata-rata Acuan / Bulan", (
                        f'{jt_range_basis["avg"]:,.1f}' if jt_range_basis["avg"] is not None else "—"
                    ))

                    jt_relative_fig = jt_go.Figure()
                    jt_cum_fig = jt_go.Figure()
                    jt_detail_rows = []
                    for i, record in enumerate(jt_ranges):
                        jt_color = jt_color_at(i)
                        indices = list(range(1, len(record["periods"]) + 1))
                        labels = [jt_month_text(period) for period in record["periods"]]
                        jt_relative_fig.add_trace(jt_go.Scatter(
                            x=indices, y=record["values"], name=record["name"],
                            mode="lines+markers+text", line=dict(color=jt_color, width=3),
                            marker=dict(size=8), text=jt_text_labels(record["values"]),
                            textposition="top center", textfont=dict(size=10, color="#F8FCFF"),
                            customdata=labels,
                            hovertemplate="Bulan ke-%{x}<br>%{customdata}<br>%{y:,.0f} transaksi<extra></extra>",
                            connectgaps=False,
                        ))
                        running = 0
                        accumulated = []
                        for period, value, month_index in zip(record["periods"], record["values"], indices):
                            if value is None:
                                accumulated.append(None)
                            else:
                                running += int(value)
                                accumulated.append(running)
                            jt_detail_rows.append({
                                "Rentang": record["name"], "Label": record["label"],
                                "Bulan ke-": month_index, "Periode": jt_month_text(period),
                                "Jumlah Transaksi": value, "Akumulasi": accumulated[-1],
                            })
                        jt_cum_fig.add_trace(jt_go.Scatter(
                            x=indices, y=accumulated, name=record["name"],
                            mode="lines+markers+text", line=dict(color=jt_color, width=3),
                            marker=dict(size=7), text=jt_text_labels(accumulated),
                            textposition="top center", textfont=dict(size=10, color="#F8FCFF"), customdata=labels,
                            fill="tozeroy" if len(jt_ranges) <= 2 else None,
                            hovertemplate="%{customdata}<br>Akumulasi: %{y:,.0f}<extra></extra>",
                            connectgaps=False,
                        ))
                    jt_plot_style(jt_relative_fig,
                                  "Volume Transaksi • Posisi Bulan dalam Setiap Rentang", height=450)
                    jt_relative_fig.update_xaxes(title="Bulan ke-")
                    st.plotly_chart(jt_relative_fig, use_container_width=True,
                                    key="jt_range_relative_chart")

                    jt_plot_style(jt_cum_fig,
                                  "Akumulasi Volume Transaksi • Multi-Rentang", "Akumulasi transaksi", 410)
                    jt_cum_fig.update_xaxes(title="Bulan ke-")
                    st.plotly_chart(jt_cum_fig, use_container_width=True, key="jt_range_cum_chart")

                    jt_range_summary = []
                    for record in jt_ranges:
                        diff, growth = jt_delta_data(jt_range_basis["total"], record["total"])
                        avg_diff, avg_growth = jt_safe_percent_difference(jt_range_basis["avg"], record["avg"])
                        jt_range_summary.append({
                            "Rentang": record["name"], "Periode": record["label"],
                            "Status": "ACUAN" if record["name"] == jt_range_basis_name else "PEMBANDING",
                            "Durasi Kalender (bulan)": record["months"],
                            "Bulan dengan Data": record["observed"],
                            "Total Transaksi": record["total"],
                            "Rata-rata per Bulan Berdata": round(record["avg"], 2) if record["avg"] is not None else None,
                            "Selisih Total vs Acuan": diff,
                            "Growth Total vs Acuan (%)": round(growth, 2) if growth is not None else None,
                            "Selisih Rata-rata vs Acuan": round(avg_diff, 2) if avg_diff is not None else None,
                            "Growth Rata-rata vs Acuan (%)": (
                                round(avg_growth, 2) if avg_growth is not None else None
                            ),
                        })
                    jt_range_summary_df = pd.DataFrame(jt_range_summary)
                    st.markdown("<div class='jt-section-heading'>Matriks Executive Comparison • Semua Rentang</div>",
                                unsafe_allow_html=True)
                    st.dataframe(jt_range_summary_df, use_container_width=True, hide_index=True)

                    jt_max_span = max(r["months"] for r in jt_ranges)
                    jt_range_matrix_rows = []
                    for month_index in range(jt_max_span):
                        row = {"Bulan ke-": month_index + 1}
                        for record in jt_ranges:
                            name = record["name"]
                            row[f"Periode {name}"] = (
                                jt_month_text(record["periods"][month_index])
                                if month_index < record["months"] else None
                            )
                            row[f"Transaksi {name}"] = (
                                record["values"][month_index]
                                if month_index < record["months"] else None
                            )
                        jt_range_matrix_rows.append(row)
                    jt_range_matrix_df = pd.DataFrame(jt_range_matrix_rows)
                    st.markdown("<div class='jt-section-heading'>Matriks Bulan ke-Bulan Semua Rentang</div>",
                                unsafe_allow_html=True)
                    st.dataframe(jt_range_matrix_df, hide_index=True, use_container_width=True)
                    with st.expander("🔎 Detail panjang untuk audit seluruh rentang", expanded=False):
                        st.dataframe(pd.DataFrame(jt_detail_rows), hide_index=True, use_container_width=True)

                    jt_highest = max(jt_ranges, key=lambda record: record["total"])
                    jt_multi_note(
                        f"Dari {len(jt_ranges)} rentang, {jt_highest['name']} memiliki total terbesar "
                        f"({jt_format_int(jt_highest['total'])} transaksi). "
                        f"Acuan perbandingan: {jt_range_basis_name}.",
                        "Perhatikan durasi & coverage data tiap rentang; "
                        "bila tidak sama, pertumbuhan rata-rata per bulan lebih relevan daripada pertumbuhan total.",
                    )
                    jt_export_buttons(
                        jt_range_matrix_df, "Rentang_Periode_Multi", jt_range_summary,
                        extra_sheets={"Detail Semua Rentang": pd.DataFrame(jt_detail_rows),
                                      "Matriks Executive": jt_range_summary_df},
                    )

# ==========================================================
#            FITUR BARU: \U0001f4e5 DOWNLOAD POSTER (A4)
# ==========================================================

# ==========================================================
#                       SLA App
# ==========================================================
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import requests, io

# ==========================================================
#                       Helper Functions
# ==========================================================
def seconds_to_sla_format(seconds):
    """Konversi detik ke format SLA: 'Xd Yh Zm'"""
    if seconds is None:
        return "0d 0h 0m"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{days}d {hours}h {minutes}m"

# ==============================
# \U0001f449 Tambahan: simpan teks periode untuk Poster (global scope)
periode_info_text = f"Periode dari {start_periode} sampai {end_periode}"

# ==========================================================
# Poster A4 Generator (Gradient BG + Glassmorphism Card)
# ==========================================================
def generate_poster_A4(
    sla_text_dict, rata_proses_seconds, df_proses,
    image_url, periode_range_text,
    df_filtered, periode_col, selected_periode
):
    W, H = 2480, 3508

    # ---------- Gradient Background (biru \u2192 putih) ----------
    bg = Image.new("RGB", (W, H))
    draw_bg = ImageDraw.Draw(bg)
    for y in range(H):
        r = int(255 - (y / H) * 55)   # putih \u2192 biru lembut
        g = int(255 - (y / H) * 100)
        b = int(255 - (y / H) * 155)
        draw_bg.line([(0, y), (W, y)], fill=(r, g, b))

    draw = ImageDraw.Draw(bg)

    # ---------- Logo ASDP ----------
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "asdp_logo.png")
        logo_img = Image.open(logo_path).convert("RGBA")
        scale = (W * 0.15) / logo_img.width
        logo_img = logo_img.resize((int(logo_img.width*scale), int(logo_img.height*scale)), Image.Resampling.LANCZOS)
        bg.paste(logo_img, (2000, 80), logo_img)
    except:
        pass

    # ---------- Logo Danantara ----------
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "Danantara.png")
        logo_img = Image.open(logo_path).convert("RGBA")
        scale = (W * 0.2) / logo_img.width
        logo_img = logo_img.resize((int(logo_img.width*scale), int(logo_img.height*scale)), Image.Resampling.LANCZOS)
        bg.paste(logo_img, (80, 80), logo_img)
    except:
        pass

    # ---------- Logo Transformation (atas kiri bawah) ----------
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "Transformation.png")
        logo_img = Image.open(logo_path).convert("RGBA")
        scale = (W * 0.2) / logo_img.width
        logo_img = logo_img.resize((int(logo_img.width*scale), int(logo_img.height*scale)), Image.Resampling.LANCZOS)
        bg.paste(logo_img, (80, 3000), logo_img)
    except:
        pass

    # ---------- Judul ----------
    title_text = "SLA DOKUMEN PENAGIHAN"
    try:
        font_title = ImageFont.truetype("Anton-Regular.ttf", 200)
    except:
        font_title = ImageFont.load_default()
    bbox_title = draw.textbbox((0, 0), title_text, font=font_title)
    title_w = bbox_title[2] - bbox_title[0]
    title_h = bbox_title[3] - bbox_title[1]
    title_y = int(H * 0.10)
    draw.text(((W - title_w) // 2, title_y), title_text, fill="black", font=font_title)

    # ---------- Periode ----------
    max_width = int(W * 0.8)
    font_size = 140
    try:
        font_periode = ImageFont.truetype("Anton-Regular.ttf", font_size)
    except:
        font_periode = ImageFont.load_default()
    while True:
        bbox_periode = draw.textbbox((0, 0), periode_range_text, font=font_periode)
        periode_w = bbox_periode[2] - bbox_periode[0]
        periode_h = bbox_periode[3] - bbox_periode[1]
        if periode_w <= max_width or font_size <= 40:
            break
        font_size -= 10
        try:
            font_periode = ImageFont.truetype("Anton-Regular.ttf", font_size)
        except:
            font_periode = ImageFont.load_default()
    periode_y = title_y + title_h + int(H * 0.03)
    draw.text(((W - periode_w) // 2, periode_y), periode_range_text, fill="black", font=font_periode)

    # ---------- Garis Separator ----------
    line_y = periode_y + periode_h + 30
    margin_x = 150
    draw.line((margin_x, line_y, W - margin_x, line_y), fill="black", width=12)

    # ---------- Grafik SLA Proses ----------
    chart_img = None
    try:
        fig, ax = plt.subplots(figsize=(10, 4))
        values_hari = [rata_proses_seconds[col] / 86400 for col in rata_proses_seconds.index]
        ax.bar(rata_proses_seconds.index, values_hari, color='#75c8ff')
        ax.set_title("Rata-rata SLA per Proses (hari)")
        ax.set_ylabel("Hari")
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
        buf.seek(0); plt.close(fig)
        chart_img = Image.open(buf).convert("RGBA")
        max_chart_width = int(W * 0.65)
        scale = max_chart_width / chart_img.width
        chart_img = chart_img.resize(
            (int(chart_img.width * scale), int(chart_img.height * scale)),
            Image.Resampling.LANCZOS
        )
    except Exception as e:
        print("Gagal render chart:", e)

    # ---------- Render Tabel SLA ----------
    table_img = None
    try:
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.axis('off')
        tbl = ax.table(
            cellText=df_proses.values,
            colLabels=df_proses.columns,
            rowLabels=df_proses.index,
            loc='center'
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(12)
        tbl.scale(1.3, 1.3)
        tbl.auto_set_column_width([0, 1])
        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
        buf.seek(0); plt.close(fig)
        table_img = Image.open(buf).convert("RGBA")
        max_tbl_width = int(W * 0.30)
        scale = max_tbl_width / table_img.width
        table_img = table_img.resize(
            (int(table_img.width * scale), int(table_img.height * scale)),
            Image.Resampling.LANCZOS
        )
    except Exception as e:
        print("Gagal render tabel SLA:", e)

    # ---------- Glassmorphism Card ----------
    card_margin_x = 80
    card_top = line_y + 20
    content_height = max(chart_img.height if chart_img else 0, table_img.height if table_img else 0)
    card_bottom = card_top + content_height + 80
    card_box = (card_margin_x, card_top, W - card_margin_x, card_bottom)

    # Blur background dalam area card
    region = bg.crop(card_box).filter(ImageFilter.GaussianBlur(20))
    bg.paste(region, card_box)

    # Semi transparan overlay
    card_overlay = Image.new("RGBA", bg.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(card_overlay)
    overlay_draw.rounded_rectangle(
        card_box,
        radius=40,
        outline=(255, 255, 255, 200),
        width=4,
        fill=(255, 255, 255, 100)
    )
    bg = Image.alpha_composite(bg.convert("RGBA"), card_overlay)
    draw = ImageDraw.Draw(bg)

    if chart_img:
        pos_x = card_margin_x + 50
        pos_y = card_top + 40
        bg.paste(chart_img, (pos_x, pos_y), chart_img)
    if table_img:
        pos_x = W - table_img.width - card_margin_x - 50
        pos_y = card_top + 40
        bg.paste(table_img, (pos_x, pos_y), table_img)    # ---------- Kemudi + On Target ----------
    try:
        kemudi_path = os.path.join(os.path.dirname(__file__), "Kemudi.png")
        kemudi_img = Image.open(kemudi_path).convert("RGBA")
        target_width = int(W * 0.18)
        scale = target_width / kemudi_img.width
        kemudi_img = kemudi_img.resize((target_width, int(kemudi_img.height * scale)), Image.Resampling.LANCZOS)
        pos_x = W - card_margin_x - kemudi_img.width - 50
        pos_y = card_top + table_img.height + 30
        bg.paste(kemudi_img, (pos_x, pos_y), kemudi_img)
        font_target = ImageFont.truetype(os.path.join(os.path.dirname(__file__), "Anton-Regular.ttf"), 120)
        text = "ON TARGET"
        bbox = draw.textbbox((0, 0), text, font=font_target)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        text_x = pos_x + (kemudi_img.width - tw) // 2
        text_y = pos_y + kemudi_img.height + 1
        draw.text((text_x, text_y), text, font=font_target, fill=(0, 150, 0))
    except Exception as e:
        print("Gagal render Kemudi/On Target:", e)

    # ---------- Footer + Garis Tengah + Grafik & Tabel Jumlah Transaksi ----------
    try:
        footer_path = os.path.join(os.path.dirname(__file__), "Footer.png")
        footer_img = Image.open(footer_path).convert("RGBA")
        scale = W / footer_img.width
        footer_img = footer_img.resize((W, int(footer_img.height * scale)), Image.Resampling.LANCZOS)
        footer_y = H - footer_img.height

        # 1. Garis tengah
        overlay = Image.new("RGBA", bg.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        center_x = W // 2
        overlay_draw.line((center_x, card_bottom, center_x, H), fill="black", width=15)
        bg = Image.alpha_composite(bg, overlay)

        # 2. Grafik jumlah transaksi
        trans_img = None
        pos_y_trans = card_bottom + 50
        try:
            jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name='Jumlah')
            jumlah_transaksi = jumlah_transaksi.sort_values(
                by=periode_col,
                key=lambda x: pd.Categorical(x, categories=selected_periode, ordered=True)
            )
            fig_trans, ax_trans = plt.subplots(figsize=(8, 5))
            colors = plt.cm.viridis(range(len(jumlah_transaksi)))
            ax_trans.bar(jumlah_transaksi[periode_col], jumlah_transaksi['Jumlah'], color=colors)
            ax_trans.set_title("Jumlah Transaksi per Periode", fontsize=28, weight="bold")
            ax_trans.set_xlabel("Periode")
            ax_trans.set_ylabel("Jumlah")
            ax_trans.grid(axis='y', linestyle='--', alpha=0.6)
            for label in ax_trans.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')
            buf = io.BytesIO()
            fig_trans.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
            buf.seek(0); plt.close(fig_trans)
            trans_img = Image.open(buf).convert("RGBA")
            max_width = int(W * 0.40)
            max_height = H - card_bottom - footer_img.height - 400
            scale = min(max_width / trans_img.width, max_height / trans_img.height)
            trans_img = trans_img.resize((int(trans_img.width * scale), int(trans_img.height * scale)), Image.Resampling.LANCZOS)
            pos_x = 150
            bg.paste(trans_img, (pos_x, pos_y_trans), trans_img)
        except Exception as e:
            print("\u26a0\ufe0f Gagal render grafik jumlah transaksi:", e)

        # 2b. Tabel jumlah transaksi (lebih keren, dinaikkan sedikit)
        try:
            jumlah_transaksi = df_filtered.groupby(df_filtered[periode_col].astype(str)).size().reset_index(name='Jumlah')
            jumlah_transaksi = jumlah_transaksi.sort_values(
                by=periode_col,
                key=lambda x: pd.Categorical(x, categories=selected_periode, ordered=True)
            )
            total_row = pd.DataFrame({periode_col: ["TOTAL"], "Jumlah": [jumlah_transaksi["Jumlah"].sum()]})
            jumlah_transaksi = pd.concat([jumlah_transaksi, total_row], ignore_index=True)

            fig_tbl, ax_tbl = plt.subplots(figsize=(6, 4))
            ax_tbl.axis("off")
            table = ax_tbl.table(
                cellText=jumlah_transaksi.values,
                colLabels=jumlah_transaksi.columns,
                loc="center",
                cellLoc="center"
            )
            table.auto_set_font_size(False)
            table.set_fontsize(16)
            table.scale(1.5, 1.5)

            # Header style
            for j in range(len(jumlah_transaksi.columns)):
                cell = table[(0, j)]
                cell.set_fontsize(18)
                cell.set_text_props(weight="bold", color="white")
                cell.set_facecolor("#1f77b4")

            # Row styling
            for i in range(1, len(jumlah_transaksi) + 1):
                for j in range(len(jumlah_transaksi.columns)):
                    cell = table[(i, j)]
                    if i % 2 == 0:
                        cell.set_facecolor("#f2f2f2")
                    else:
                        cell.set_facecolor("#ffffff")
                    if jumlah_transaksi.iloc[i-1, 0] == "TOTAL":
                        cell.set_text_props(weight="bold", color="darkred")
                        cell.set_facecolor("#e6e6e6")

            buf = io.BytesIO()
            fig_tbl.savefig(buf, format="PNG", dpi=300, bbox_inches="tight", transparent=True)
            buf.seek(0); plt.close(fig_tbl)
            tbl_img = Image.open(buf).convert("RGBA")
            max_width = int(W * 0.40)
            scale = max_width / tbl_img.width
            tbl_img = tbl_img.resize((int(tbl_img.width * scale), int(tbl_img.height * scale)), Image.Resampling.LANCZOS)
            pos_x = 150
            if trans_img:
                pos_y = pos_y_trans + trans_img.height + 20  # lebih dekat ke grafik
            else:
                pos_y = pos_y_trans
            bg.paste(tbl_img, (pos_x, pos_y), tbl_img)
        except Exception as e:
            print("\u26a0\ufe0f Gagal render tabel jumlah transaksi:", e)

        # 3. Footer
        bg.paste(footer_img, (0, footer_y), footer_img)

        # 4. Captain Ferizy
        ferizy_path = os.path.join(os.path.dirname(__file__), "Captain Ferizy.png")
        ferizy_img = Image.open(ferizy_path).convert("RGBA")
        scale = (footer_img.height * 2) / ferizy_img.height
        ferizy_img = ferizy_img.resize((int(ferizy_img.width * scale), int(ferizy_img.height * scale)), Image.Resampling.LANCZOS)
        pos_x = W - ferizy_img.width
        pos_y = H - ferizy_img.height
        bg.paste(ferizy_img, (pos_x, pos_y), ferizy_img)

        # 5. Transformation (depan footer, kiri bawah)
        Transformation_path = os.path.join(os.path.dirname(__file__), "Transformation.png")
        Transformation_img = Image.open(Transformation_path).convert("RGBA")
        scale = (footer_img.height * 0.35) / Transformation_img.height
        Transformation_img = Transformation_img.resize((int(Transformation_img.width * scale), int(Transformation_img.height * scale)), Image.Resampling.LANCZOS)
        pos_x = 0
        pos_y = H - Transformation_img.height - 40
        bg.paste(Transformation_img, (pos_x, pos_y), Transformation_img)

    except Exception as e:
        print("\u26a0\ufe0f Gagal render Footer/Ferizy/Transformation:", e)

    out = io.BytesIO()
    bg.save(out, format="PNG")
    out.seek(0)
    return out


# =========================================
# [ADD] Konfigurasi file khusus Nilai Transaksi
# =========================================
NILAI_DATA_PATH = os.path.join("data", "nilai_transaksi.xlsx")
NILAI_GITHUB_PATH = "data/nilai_transaksi.xlsx"  # bisa ubah kalau mau folder lain


def download_nilai_xlsx_from_github() -> bytes | None:
    """Ambil file nilai_transaksi.xlsx dari GitHub (kalau ada secrets)."""
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    info = github_get_file_info(NILAI_GITHUB_PATH)
    if not info or "content" not in info:
        return None
    try:
        return base64.b64decode(info["content"].encode())
    except Exception:
        return None


def upload_nilai_xlsx_to_github(file_bytes: bytes, message="Update Nilai Transaksi (via tab Nilai)") -> dict | None:
    """Upload/overwrite file nilai_transaksi.xlsx ke GitHub."""
    return upload_file_to_github(file_bytes, path=NILAI_GITHUB_PATH, message=message)


@st.cache_data(show_spinner=False)
def _read_nilai_excel_bytes(xlsx_bytes: bytes) -> pd.DataFrame:
    """Read excel dari bytes (cache)."""
    return pd.read_excel(BytesIO(xlsx_bytes))


@st.cache_data(show_spinner=False)
def _read_nilai_excel_path(path: str, size: int, mtime: float) -> pd.DataFrame:
    """Read excel dari path (cache)."""
    return pd.read_excel(path)


def load_nilai_df() -> pd.DataFrame | None:
    """Load data nilai: GitHub -> lokal -> None."""
    # 1) GitHub
    content = download_nilai_xlsx_from_github()
    if content:
        try:
            return _read_nilai_excel_bytes(content)
        except Exception:
            pass

    # 2) Lokal
    if os.path.exists(NILAI_DATA_PATH):
        try:
            stat = os.stat(NILAI_DATA_PATH)
            return _read_nilai_excel_path(NILAI_DATA_PATH, stat.st_size, stat.st_mtime)
        except Exception:
            return None

    return None


def _parse_rupiah_series(s: pd.Series) -> pd.Series:
    """
    Parse kolom NILAI dari:
    - angka
    - '192.250.000' / 'Rp 192.250.000'
    Menjadi float.
    """
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() >= 0.7:
        return num

    def one(v):
        if v is None:
            return float("nan")
        txt = str(v).strip()
        if txt == "" or txt.lower() in {"nan", "none", "-", "null"}:
            return float("nan")
        txt = txt.upper().replace("RP", "").replace("RUPIAH", "").strip()
        txt = re.sub(r"\s+", "", txt)
        # format Indonesia: 192.250.000 -> remove dots
        txt = txt.replace(".", "")
        # kalau ada koma sebagai desimal (jarang untuk rupiah), ubah ke titik
        txt = txt.replace(",", ".")
        return pd.to_numeric(txt, errors="coerce")

    return s.apply(one)


def _detect_col(df: pd.DataFrame, keywords: list[str]) -> str | None:
    cols = list(df.columns)
    for c in cols:
        cu = re.sub(r"\s+", " ", str(c).strip().upper())
        if all(k in cu for k in keywords):
            return c
    for c in cols:
        cu = re.sub(r"\s+", " ", str(c).strip().upper())
        if any(k in cu for k in keywords):
            return c
    return None


# =========================================
# [ADD] TAB NILAI TRANSAKSI (upload hanya di tab ini)
# =========================================
# ==============================
# TAB NILAI TRANSAKSI (FULL)
# ==============================
# ==============================
# TAB NILAI TRANSAKSI (FULL + SAVE BUCKET + FILTER PERIODE)
# ==============================
# ==============================
# TAB NILAI TRANSAKSI (EXEC DASH + COMPARE YEAR + FAST)
# ==============================
# ==============================
# FULL TAB NILAI TRANSAKSI (WOW + FAST + YOY BUCKETS DYNAMIC)
# ==============================
if (not _SLA_LAZY_TABS) or bool(getattr(tab_nilai, "open", False)):
    with tab_nilai:
        import os
        import re
        import json
        import math
        import base64
        from io import BytesIO
        from typing import Optional, List, Dict

        import pandas as pd
        import matplotlib.pyplot as plt
        import streamlit as st

        # =========================
        # CONFIG
        # =========================
        DATA_PATH = "data/nilai_transaksi.xlsx"
        DATA_GITHUB_PATH = "data/nilai_transaksi.xlsx"
        BUCKET_PATH = "data/nilai_bucket.json"
        BUCKET_GITHUB_PATH = "data/nilai_bucket.json"

        os.makedirs("data", exist_ok=True)

        st.subheader("\U0001f4b0 Nilai Transaksi \u2014 Direksi Dashboard")

        # =========================
        # FORMATTERS
        # =========================
        def fmt_int(n: float | int) -> str:
            try:
                return f"{int(n):,}".replace(",", ".")
            except Exception:
                return "-"

        def fmt_rp(x: float) -> str:
            if x is None or (isinstance(x, float) and math.isnan(x)):
                return "-"
            return "Rp " + f"{x:,.0f}".replace(",", ".")

        def fmt_pct(x: float) -> str:
            if x is None or (isinstance(x, float) and math.isnan(x)):
                return "-"
            return f"{x:.1f}%".replace(".", ",")

        def pct_delta(curr: float, prev: Optional[float]) -> Optional[str]:
            if prev is None or prev == 0 or (isinstance(prev, float) and math.isnan(prev)):
                return None
            p = (curr - prev) / prev * 100.0
            sign = "+" if p >= 0 else ""
            return f"{sign}{p:.1f}%".replace(".", ",")

        # =========================
        # GITHUB HELPERS (expects existing functions)
        # github_get_file_info(path)
        # upload_file_to_github(content_bytes, path=..., message=...)
        # =========================
        def github_get_bytes(path: str) -> Optional[bytes]:
            if not (GITHUB_TOKEN and GITHUB_REPO):
                return None
            try:
                info = github_get_file_info(path)
                if not info or "content" not in info:
                    return None
                return base64.b64decode(info["content"].encode())
            except Exception:
                return None

        def github_put_bytes(path: str, content: bytes, message: str) -> bool:
            if not (GITHUB_TOKEN and GITHUB_REPO):
                return False
            try:
                res = upload_file_to_github(content, path=path, message=message)
                return bool(res)
            except Exception:
                return False

        # =========================
        # FAST IO
        # =========================
        @st.cache_data(show_spinner=False)
        def read_excel_cached(path: str, size: int, mtime: float) -> pd.DataFrame:
            return pd.read_excel(path)

        @st.cache_data(show_spinner=False)
        def read_excel_bytes(b: bytes) -> pd.DataFrame:
            return pd.read_excel(BytesIO(b))

        def load_local_df() -> Optional[pd.DataFrame]:
            if not os.path.exists(DATA_PATH):
                return None
            try:
                stat = os.stat(DATA_PATH)
                return read_excel_cached(DATA_PATH, stat.st_size, stat.st_mtime)
            except Exception:
                return None

        # =========================
        # COLUMN DETECT + PARSING
        # =========================
        def detect_col(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
            cols = list(df.columns)
            for c in cols:
                cu = re.sub(r"\s+", " ", str(c).strip().upper())
                if all(k in cu for k in keywords):
                    return c
            for c in cols:
                cu = re.sub(r"\s+", " ", str(c).strip().upper())
                if any(k in cu for k in keywords):
                    return c
            return None

        def parse_rupiah_vectorized(s: pd.Series) -> pd.Series:
            num = pd.to_numeric(s, errors="coerce")
            if num.notna().mean() >= 0.7:
                return num
            txt = s.astype(str).str.upper().str.strip()
            txt = txt.replace({"NAN": "", "NONE": "", "NULL": "", "-": ""})
            txt = txt.str.replace("RUPIAH", "", regex=False)
            txt = txt.str.replace("RP", "", regex=False)
            txt = txt.str.replace(r"\s+", "", regex=True)
            txt = txt.str.replace(".", "", regex=False)
            txt = txt.str.replace(",", "", regex=False)
            txt = txt.str.replace(r"[^0-9\-]", "", regex=True)
            return pd.to_numeric(txt, errors="coerce")

        def extract_year(period_s: pd.Series) -> pd.Series:
            s = period_s.astype(str).str.strip()
            dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
            year = dt.dt.year
            mask = year.isna()
            if mask.any():
                extracted = s[mask].str.extract(r"(\d{4})", expand=False)
                year.loc[mask] = pd.to_numeric(extracted, errors="coerce")
            return year

        @st.cache_data(show_spinner=False)
        def preprocess(df: pd.DataFrame, col_periode: str, col_nilai: str) -> pd.DataFrame:
            out = df.copy()
            out["__YEAR__"] = extract_year(out[col_periode])
            out["__NILAI_NUM__"] = parse_rupiah_vectorized(out[col_nilai])
            out = out.dropna(subset=["__YEAR__", "__NILAI_NUM__"]).copy()
            out["__YEAR__"] = out["__YEAR__"].astype(int)
            return out

        # =========================
        # BUCKETS (dynamic thresholds)
        # thresholds: [t1,t2,...] => 0\u2013t1, t1\u2013t2, ..., >tN
        # =========================
        def build_edges(thresholds: List[float]) -> List[float]:
            t = [float(x) for x in thresholds if x is not None and not math.isnan(float(x))]
            t = sorted(set([x for x in t if x > 0]))
            return [0.0] + t + [float("inf")]

        def build_labels(edges: List[float]) -> List[str]:
            labs: List[str] = []
            for i in range(len(edges) - 1):
                lo, hi = edges[i], edges[i + 1]
                if math.isinf(hi):
                    labs.append(f"> {lo:,.0f}".replace(",", "."))
                else:
                    labs.append(f"{lo:,.0f} \u2013 {hi:,.0f}".replace(",", "."))
            return labs

        def load_bucket_cfg() -> Dict:
            default = {"mode": "dynamic", "thresholds": [10e6, 50e6, 500e6]}
            if os.path.exists(BUCKET_PATH):
                try:
                    with open(BUCKET_PATH, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        if isinstance(cfg, dict) and isinstance(cfg.get("thresholds"), list):
                            return cfg
                except Exception:
                    pass
            b = github_get_bytes(BUCKET_GITHUB_PATH)
            if b:
                try:
                    cfg = json.loads(b.decode("utf-8"))
                    if isinstance(cfg, dict) and isinstance(cfg.get("thresholds"), list):
                        with open(BUCKET_PATH, "w", encoding="utf-8") as f:
                            json.dump(cfg, f, ensure_ascii=False, indent=2)
                        return cfg
                except Exception:
                    pass
            return default

        def save_bucket_cfg(thresholds: List[float]) -> None:
            thresholds = sorted(set([float(x) for x in thresholds if x is not None and float(x) > 0]))
            edges = build_edges(thresholds)
            payload = {
                "mode": "dynamic",
                "thresholds": thresholds,
                "edges": [("inf" if math.isinf(x) else x) for x in edges],
                "labels": build_labels(edges),
            }
            with open(BUCKET_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            if GITHUB_TOKEN and GITHUB_REPO:
                github_put_bytes(
                    BUCKET_GITHUB_PATH,
                    json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                    "Update Nilai Buckets (dynamic)",
                )

        # =========================
        # ADMIN UPLOAD + MANUAL SYNC
        # =========================
        left, right = st.columns([2, 1])
        with left:
            with st.expander("\U0001f4e4 Upload Data Nilai Transaksi (Admin Only)", expanded=is_admin):
                if not is_admin:
                    st.info("Hanya admin yang dapat upload.")
                    uploaded = None
                else:
                    uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"], key="nilai_upload_rewrite_v1")
                if is_admin and uploaded is not None:
                    b = uploaded.getvalue()
                    try:
                        df_now = read_excel_bytes(b)
                        st.session_state["nilai_raw_df"] = df_now
                        st.success(f"\u2705 Upload terbaca: {fmt_int(len(df_now))} baris")
                        st.dataframe(df_now.head(20), use_container_width=True)
                    except Exception as e:
                        st.error(f"Gagal baca Excel: {e}")
                        st.stop()

                    with open(DATA_PATH, "wb") as f:
                        f.write(b)

                    if GITHUB_TOKEN and GITHUB_REPO:
                        with st.spinner("Sync ke GitHub..."):
                            ok = github_put_bytes(DATA_GITHUB_PATH, b, "Update Nilai Transaksi (tab Nilai)")
                        if ok:
                            st.success("\u2705 Tersimpan lokal & tersinkron ke GitHub.")
                        else:
                            st.warning("\u26a0\ufe0f Tersimpan lokal, tapi gagal upload ke GitHub.")
                    else:
                        st.success("\u2705 Tersimpan lokal (GitHub tidak dikonfigurasi).")

                    st.cache_data.clear()
                    st.rerun()

        with right:
            st.caption("\u26a1 Fast mode: load local-first. GitHub sync manual.")
            if is_admin and (GITHUB_TOKEN and GITHUB_REPO):
                if st.button("\U0001f504 Sync dari GitHub", key="nilai_sync_rewrite_v1"):
                    with st.spinner("Mengambil file dari GitHub..."):
                        xlsx = github_get_bytes(DATA_GITHUB_PATH)
                        cfgb = github_get_bytes(BUCKET_GITHUB_PATH)

                    if xlsx:
                        df_now = read_excel_bytes(xlsx)
                        st.session_state["nilai_raw_df"] = df_now
                        with open(DATA_PATH, "wb") as f:
                            f.write(xlsx)

                    if cfgb:
                        try:
                            cfg = json.loads(cfgb.decode("utf-8"))
                            with open(BUCKET_PATH, "w", encoding="utf-8") as f:
                                json.dump(cfg, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass

                    st.cache_data.clear()
                    st.success("\u2705 Sync selesai.")
                    st.rerun()

        # =========================
        # LOAD DATA (SESSION -> LOCAL)
        # =========================
        df_raw = st.session_state.get("nilai_raw_df")
        if df_raw is None:
            df_raw = load_local_df()
        if df_raw is None or df_raw.empty:
            st.warning("Belum ada data Nilai Transaksi. Admin silakan upload di atas.")
            st.stop()

        st.caption(f"Loaded: {fmt_int(len(df_raw))} baris")

        # =========================
        # MAPPING KOLOM
        # =========================
        cols = list(df_raw.columns)
        auto_periode = detect_col(df_raw, ["PERIODE"]) or detect_col(df_raw, ["PERIOD"]) or cols[0]
        auto_nilai = (
            detect_col(df_raw, ["NILAI"])
            or detect_col(df_raw, ["AMOUNT"])
            or detect_col(df_raw, ["VALUE"])
            or detect_col(df_raw, ["NOMINAL"])
            or cols[0]
        )
        auto_vendor = detect_col(df_raw, ["VENDOR"]) or detect_col(df_raw, ["NAMA", "VENDOR"])
        auto_jenis = detect_col(df_raw, ["JENIS", "TRANSAKSI"]) or detect_col(df_raw, ["TRANSAKSI"])

        with st.expander("\u2699\ufe0f Mapping Kolom", expanded=False):
            col_periode = st.selectbox("Kolom PERIODE", cols, index=cols.index(auto_periode), key="map_periode_rewrite_v1")
            col_nilai = st.selectbox("Kolom NILAI", cols, index=cols.index(auto_nilai), key="map_nilai_rewrite_v1")
            col_vendor = st.selectbox(
                "Kolom VENDOR (opsional)",
                ["(none)"] + cols,
                index=(["(none)"] + cols).index(auto_vendor) if auto_vendor in cols else 0,
                key="map_vendor_rewrite_v1",
            )
            col_jenis = st.selectbox(
                "Kolom JENIS TRANSAKSI (opsional)",
                ["(none)"] + cols,
                index=(["(none)"] + cols).index(auto_jenis) if auto_jenis in cols else 0,
                key="map_jenis_rewrite_v1",
            )

        # =========================
        # PREPROCESS (CACHED)
        # =========================
        df = preprocess(df_raw, col_periode=col_periode, col_nilai=col_nilai)
        if df.empty:
            st.error("Tidak ada data valid setelah parsing YEAR/NILAI. Cek mapping & format data.")
            st.dataframe(df_raw.head(30), use_container_width=True)
            st.stop()

        years_all = sorted(df["__YEAR__"].unique().tolist())

        # =========================
        # GLOBAL FILTERS (apply to all)
        # =========================
        st.markdown("### \U0001f50e Filter Global (berlaku untuk semua tab)")
        gf1, gf2 = st.columns([1.2, 2.0])

        with gf1:
            years_global = st.multiselect(
                "Tahun",
                options=years_all,
                default=years_all[-3:] if len(years_all) >= 3 else years_all,
                key="global_years_rewrite_v1",
            )
        if not years_global:
            st.warning("Pilih minimal 1 tahun.")
            st.stop()

        df_global = df[df["__YEAR__"].isin([int(y) for y in years_global])].copy()

        with gf2:
            if col_jenis != "(none)" and col_jenis in df_global.columns:
                jenis_opts = sorted(df_global[col_jenis].dropna().astype(str).unique().tolist())
                jenis_selected = st.multiselect(
                    "Jenis Transaksi (multi)",
                    options=jenis_opts,
                    default=jenis_opts,
                    key="global_jenis_rewrite_v1",
                )
                if not jenis_selected:
                    st.warning("Pilih minimal 1 jenis transaksi.")
                    st.stop()
                df_global = df_global[df_global[col_jenis].astype(str).isin(jenis_selected)].copy()
            else:
                jenis_selected = None
                st.caption("Filter jenis transaksi nonaktif (mapping jenis belum dipilih).")

        if df_global.empty:
            st.warning("Tidak ada data untuk kombinasi filter global.")
            st.stop()

        # =========================
        # SUB-TABS
        # =========================
        tab_nilai_exec, tab_nilai_yoy, tab_nilai_vendor = st.tabs(
            ["\U0001f3c1 Executive Summary", "\U0001f4ca YoY Buckets & Analysis", "\U0001f3f7\ufe0f Vendor & Drilldown"]
        )

        # =====================================================
        # TAB 1: EXECUTIVE SUMMARY (Bucket multi OR Custom Range multi)
        # =====================================================
        with tab_nilai_exec:
            st.markdown("### \U0001f3af Executive Snapshot")

            cfg0 = load_bucket_cfg()
            thresholds0 = cfg0.get("thresholds", [10e6, 50e6, 500e6])
            edges0 = build_edges(thresholds0)
            labs0 = build_labels(edges0)

            dfx = df_global.copy()
            dfx["Bucket"] = pd.cut(dfx["__NILAI_NUM__"], bins=edges0, labels=labs0, right=False, include_lowest=True)

            c1, c2, c3 = st.columns([1.6, 1.6, 1.2])
            with c1:
                focus_mode = st.radio(
                    "Mode sorot",
                    options=["Bucket", "Custom Range (Rp)"],
                    horizontal=True,
                    key="exec_focus_mode_rewrite_v1",
                )
            with c2:
                quick_focus = st.selectbox(
                    "Quick focus",
                    options=["(none)", ">= 100 juta", ">= 250 juta", ">= 500 juta", ">= 1 Miliar"],
                    index=0,
                    key="exec_quick_focus_rewrite_v1",
                )
            with c3:
                show_insight = st.toggle("Insight otomatis", value=True, key="exec_insight_rewrite_v1")

            # ---- custom range multi helpers
            def _ensure_ranges_session(key: str, defaults: list[dict]) -> None:
                if key not in st.session_state:
                    st.session_state[key] = defaults

            def _clamp_nonneg(x: float) -> float:
                try:
                    return max(0.0, float(x))
                except Exception:
                    return 0.0

            focus_df = dfx.copy()
            focus_title = ""

            if focus_mode == "Bucket":
                focus_buckets = st.multiselect(
                    "Sorot bucket (multi)",
                    options=labs0,
                    default=[labs0[min(2, len(labs0) - 1)]],
                    key="exec_focus_buckets_rewrite_v1",
                )
                if not focus_buckets:
                    st.warning("Pilih minimal 1 bucket untuk sorotan.")
                    st.stop()
                focus_df = dfx[dfx["Bucket"].astype(str).isin([str(x) for x in focus_buckets])].copy()
                focus_title = " + ".join([str(x) for x in focus_buckets])

            else:
                st.markdown("#### \U0001f39a\ufe0f Sorot Range Custom (multi)")
                st.caption("Isi min\u2013max sendiri. Jika max \u221e \u2192 tanpa batas atas.")

                _default_ranges = [
                    {"min": 0.0, "max": 10_000_000.0},
                    {"min": 10_000_000.0, "max": 50_000_000.0},
                    {"min": 50_000_000.0, "max": 500_000_000.0},
                    {"min": 500_000_000.0, "max": None},
                ]
                _ensure_ranges_session("exec_custom_ranges_rewrite_v1", _default_ranges)

                r1, r2, r3 = st.columns([1, 1, 2])
                with r1:
                    if st.button("\u2795 Tambah range", key="exec_add_range_rewrite_v1"):
                        st.session_state["exec_custom_ranges_rewrite_v1"].append({"min": 0.0, "max": None})
                with r2:
                    if st.button("\u2796 Hapus terakhir", key="exec_del_range_rewrite_v1"):
                        if st.session_state["exec_custom_ranges_rewrite_v1"]:
                            st.session_state["exec_custom_ranges_rewrite_v1"] = st.session_state["exec_custom_ranges_rewrite_v1"][:-1]
                with r3:
                    if quick_focus != "(none)":
                        if quick_focus == ">= 100 juta":
                            st.session_state["exec_custom_ranges_rewrite_v1"] = [{"min": 100_000_000.0, "max": None}]
                        elif quick_focus == ">= 250 juta":
                            st.session_state["exec_custom_ranges_rewrite_v1"] = [{"min": 250_000_000.0, "max": None}]
                        elif quick_focus == ">= 500 juta":
                            st.session_state["exec_custom_ranges_rewrite_v1"] = [{"min": 500_000_000.0, "max": None}]
                        elif quick_focus == ">= 1 Miliar":
                            st.session_state["exec_custom_ranges_rewrite_v1"] = [{"min": 1_000_000_000.0, "max": None}]

                ranges_ui: list[dict] = []
                for i, rr in enumerate(st.session_state["exec_custom_ranges_rewrite_v1"], start=1):
                    cmin, cmax, cen = st.columns([1, 1, 1.1])
                    with cmin:
                        vmin = st.number_input(
                            f"Range {i} \u2014 Min (Rp)",
                            min_value=0.0,
                            value=float(rr.get("min") or 0.0),
                            step=1e6,
                            key=f"exec_rmin_rewrite_{i}_v1",
                        )
                    with cmax:
                        inf = st.checkbox("\u221e (tanpa max)", value=(rr.get("max") is None), key=f"exec_rinf_rewrite_{i}_v1")
                        if inf:
                            vmax = None
                        else:
                            vmax = st.number_input(
                                f"Range {i} \u2014 Max (Rp)",
                                min_value=0.0,
                                value=float(rr.get("max") or 0.0),
                                step=1e6,
                                key=f"exec_rmax_rewrite_{i}_v1",
                            )
                    with cen:
                        enabled = st.checkbox("Aktif", value=True, key=f"exec_ren_rewrite_{i}_v1")

                    ranges_ui.append(
                        {"min": _clamp_nonneg(vmin), "max": None if vmax is None else _clamp_nonneg(vmax), "enabled": bool(enabled)}
                    )

                ranges_active = []
                for rr in ranges_ui:
                    if not rr["enabled"]:
                        continue
                    lo = float(rr["min"])
                    hi = rr["max"]
                    if hi is not None and hi < lo:
                        lo, hi = hi, lo
                    ranges_active.append({"min": lo, "max": hi})

                if not ranges_active:
                    st.warning("Aktifkan minimal 1 range.")
                    st.stop()

                mask = pd.Series(False, index=focus_df.index)
                for rr in ranges_active:
                    lo, hi = rr["min"], rr["max"]
                    if hi is None:
                        mask = mask | (focus_df["__NILAI_NUM__"] >= lo)
                    else:
                        mask = mask | ((focus_df["__NILAI_NUM__"] >= lo) & (focus_df["__NILAI_NUM__"] <= hi))

                focus_df = focus_df[mask].copy()

                parts = []
                for rr in ranges_active:
                    lo, hi = rr["min"], rr["max"]
                    if hi is None:
                        parts.append(f">= {fmt_rp(lo)}")
                    else:
                        parts.append(f"{fmt_rp(lo)} \u2014 {fmt_rp(hi)}")
                focus_title = " + ".join(parts)

            st.markdown(f"**Sorotan aktif:** {focus_title}")

            # ---- overall KPI YoY (All)
            overall = (
                dfx.groupby("__YEAR__")["__NILAI_NUM__"]
                .agg(Transaksi="size", Total="sum", Rata2="mean")
                .reset_index()
                .rename(columns={"__YEAR__": "Tahun"})
                .sort_values("Tahun")
            )
            last_year = int(overall["Tahun"].max())
            prev_year = int(sorted(overall["Tahun"].unique())[-2]) if len(overall["Tahun"].unique()) >= 2 else None
            ov = overall.set_index("Tahun")

            cur_tx = float(ov.loc[last_year, "Transaksi"])
            cur_total = float(ov.loc[last_year, "Total"])
            cur_avg = float(ov.loc[last_year, "Rata2"])

            prev_tx = float(ov.loc[prev_year, "Transaksi"]) if (prev_year in ov.index) else None
            prev_total = float(ov.loc[prev_year, "Total"]) if (prev_year in ov.index) else None
            prev_avg = float(ov.loc[prev_year, "Rata2"]) if (prev_year in ov.index) else None

            st.markdown("#### \U0001f9fe KPI Utama (All Transactions)")
            k1, k2, k3 = st.columns(3)
            k1.metric(f"Jumlah Transaksi ({last_year})", fmt_int(cur_tx), delta=pct_delta(cur_tx, prev_tx))
            k2.metric(f"Total Nilai ({last_year})", fmt_rp(cur_total), delta=pct_delta(cur_total, prev_total))
            k3.metric(f"Rata-rata ({last_year})", fmt_rp(cur_avg), delta=pct_delta(cur_avg, prev_avg))

            st.markdown(f"#### \U0001f525 KPI Sorotan: **{focus_title}**")
            if focus_df.empty:
                st.info("Tidak ada data pada sorotan untuk filter global saat ini.")
            else:
                focus_kpi = (
                    focus_df.groupby("__YEAR__")["__NILAI_NUM__"]
                    .agg(Transaksi="size", Total="sum", Rata2="mean")
                    .reset_index()
                    .rename(columns={"__YEAR__": "Tahun"})
                    .sort_values("Tahun")
                )
                fk = focus_kpi.set_index("Tahun")

                cur_f_tx = float(fk.loc[last_year, "Transaksi"]) if (last_year in fk.index) else 0.0
                cur_f_total = float(fk.loc[last_year, "Total"]) if (last_year in fk.index) else 0.0
                cur_f_avg = float(fk.loc[last_year, "Rata2"]) if (last_year in fk.index) else float("nan")

                prev_f_tx = float(fk.loc[prev_year, "Transaksi"]) if (prev_year in fk.index) else None
                prev_f_total = float(fk.loc[prev_year, "Total"]) if (prev_year in fk.index) else None
                prev_f_avg = float(fk.loc[prev_year, "Rata2"]) if (prev_year in fk.index) else None

                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Transaksi (sorotan)", fmt_int(cur_f_tx), delta=pct_delta(cur_f_tx, prev_f_tx))
                b2.metric("Total Nilai (sorotan)", fmt_rp(cur_f_total), delta=pct_delta(cur_f_total, prev_f_total))
                b3.metric("Rata-rata (sorotan)", fmt_rp(cur_f_avg) if not pd.isna(cur_f_avg) else "-", delta=pct_delta(cur_f_avg, prev_f_avg))
                b4.metric("% share transaksi", fmt_pct((cur_f_tx / cur_tx * 100.0) if cur_tx else float("nan")))

                with st.expander("\U0001f4cb Tabel KPI Sorotan (YoY)", expanded=False):
                    show_focus = focus_kpi.copy()
                    show_focus["Total"] = show_focus["Total"].apply(lambda x: fmt_rp(float(x)))
                    show_focus["Rata2"] = show_focus["Rata2"].apply(lambda x: fmt_rp(float(x)) if not pd.isna(x) else "-")
                    st.dataframe(show_focus, use_container_width=True)

            st.markdown("#### \U0001f4c8 Tren YoY")
            fig1, ax1 = plt.subplots(figsize=(10, 4))
            ax1.plot(overall["Tahun"].astype(str), overall["Total"], marker="o")
            ax1.set_title("Total Nilai per Tahun")
            ax1.set_xlabel("Tahun")
            ax1.set_ylabel("Total Nilai (Rp)")
            ax1.grid(axis="y", linestyle="--", alpha=0.35)
            st.pyplot(fig1)

            fig2, ax2 = plt.subplots(figsize=(10, 4))
            ax2.bar(overall["Tahun"].astype(str), overall["Transaksi"])
            ax2.set_title("Jumlah Transaksi per Tahun")
            ax2.set_xlabel("Tahun")
            ax2.set_ylabel("Jumlah")
            ax2.grid(axis="y", linestyle="--", alpha=0.35)
            st.pyplot(fig2)

            if show_insight and len(overall) >= 2:
                st.markdown("#### \U0001f9e0 Insight Otomatis")
                top_year = overall.sort_values("Total", ascending=False).iloc[0]
                st.write(
                    f"- Tahun tertinggi (Total Nilai): **{int(top_year['Tahun'])}** ({fmt_rp(float(top_year['Total']))}).\n"
                    f"- Tahun terakhir **{last_year}**: Total {pct_delta(cur_total, prev_total) or 'n/a'} | Qty {pct_delta(cur_tx, prev_tx) or 'n/a'}."
                )

            with st.expander("\U0001f4cb Tabel KPI YoY (All)", expanded=False):
                show_overall = overall.copy()
                show_overall["Total"] = show_overall["Total"].apply(lambda x: fmt_rp(float(x)))
                show_overall["Rata2"] = show_overall["Rata2"].apply(lambda x: fmt_rp(float(x)))
                st.dataframe(show_overall, use_container_width=True)

        # =====================================================
        # TAB 2: YOY BUCKETS & ANALYSIS (uses global filters too)
        # =====================================================
        with tab_nilai_yoy:
            st.markdown("### \U0001f4ca Analisis YoY per Range Nilai (Custom)")

            cfg = load_bucket_cfg()
            base_thresholds = cfg.get("thresholds", [10e6, 50e6, 500e6])

            if "dyn_thresholds_yoy_rewrite_v1" not in st.session_state:
                st.session_state["dyn_thresholds_yoy_rewrite_v1"] = [float(x) for x in base_thresholds]

            with st.expander("\U0001f9e9 Editor Range (Tambah/Kurangi) + Simpan", expanded=True):
                st.caption("Threshold membentuk bucket: 0\u2013t1, t1\u2013t2, ..., >tN.")

                a1, a2, a3, a4 = st.columns([1, 1, 1.2, 1.8])
                if a1.button("\u2795 Tambah threshold", key="yoy_add_thr_rewrite_v1"):
                    last = st.session_state["dyn_thresholds_yoy_rewrite_v1"][-1] if st.session_state["dyn_thresholds_yoy_rewrite_v1"] else 10e6
                    st.session_state["dyn_thresholds_yoy_rewrite_v1"].append(float(last * 2))

                if a2.button("\u2796 Hapus terakhir", key="yoy_del_thr_rewrite_v1"):
                    if st.session_state["dyn_thresholds_yoy_rewrite_v1"]:
                        st.session_state["dyn_thresholds_yoy_rewrite_v1"] = st.session_state["dyn_thresholds_yoy_rewrite_v1"][:-1]

                if a3.button("\u21a9 Reset default", key="yoy_reset_thr_rewrite_v1"):
                    st.session_state["dyn_thresholds_yoy_rewrite_v1"] = [float(x) for x in base_thresholds]

                thresholds_ui: List[float] = []
                for i, v in enumerate(st.session_state["dyn_thresholds_yoy_rewrite_v1"], start=1):
                    thresholds_ui.append(
                        st.number_input(
                            f"Threshold {i} (Rp)",
                            min_value=0.0,
                            value=float(v),
                            step=1e6,
                            key=f"yoy_thr_input_rewrite_{i}_v1",
                        )
                    )

                thresholds_norm = sorted(set([float(x) for x in thresholds_ui if x is not None and float(x) > 0]))
                edges = build_edges(thresholds_norm)
                labs = build_labels(edges)

                st.write("Preview bucket:")
                st.write(labs)

                if is_admin:
                    if a4.button("\U0001f4be Simpan Bucket (Persisten)", key="yoy_save_thr_rewrite_v1"):
                        save_bucket_cfg(thresholds_norm)
                        st.session_state["dyn_thresholds_yoy_rewrite_v1"] = thresholds_norm
                        st.success("\u2705 Bucket tersimpan.")
                else:
                    st.info("Hanya admin yang bisa menyimpan. Anda tetap bisa mencoba sementara.")

            dfy = df_global.copy()
            dfy["Bucket"] = pd.cut(dfy["__NILAI_NUM__"], bins=edges, labels=labs, right=False, include_lowest=True)

            grp = (
                dfy.dropna(subset=["Bucket"])
                .groupby(["__YEAR__", "Bucket"])["__NILAI_NUM__"]
                .agg(Jumlah="size", Total="sum")
                .reset_index()
                .rename(columns={"__YEAR__": "Tahun"})
            )

            pivot_cnt = grp.pivot_table(index="Bucket", columns="Tahun", values="Jumlah", fill_value=0).reindex(labs)
            pivot_total = grp.pivot_table(index="Bucket", columns="Tahun", values="Total", fill_value=0.0).reindex(labs)

            st.markdown("#### \u2705 Jumlah Transaksi per Range (per Tahun)")
            st.dataframe(pivot_cnt, use_container_width=True)

            st.markdown("#### \u2705 Total Nilai per Range (per Tahun)")
            pivot_total_fmt = pivot_total.copy()
            for c in pivot_total_fmt.columns:
                pivot_total_fmt[c] = pivot_total_fmt[c].apply(lambda x: fmt_rp(float(x)))
            st.dataframe(pivot_total_fmt, use_container_width=True)

            st.markdown("#### \U0001f4cc % Share Quantity (per Range, per Tahun)")
            qty_share = pivot_cnt.div(pivot_cnt.sum(axis=0).replace(0, float("nan")), axis=1) * 100.0
            qty_share_fmt = qty_share.copy()
            for c in qty_share_fmt.columns:
                qty_share_fmt[c] = qty_share_fmt[c].apply(lambda x: fmt_pct(float(x)) if not pd.isna(x) else "-")
            st.dataframe(qty_share_fmt, use_container_width=True)

            st.markdown("#### \U0001f4cc % Share Nilai (per Range, per Tahun)")
            val_share = pivot_total.div(pivot_total.sum(axis=0).replace(0, float("nan")), axis=1) * 100.0
            val_share_fmt = val_share.copy()
            for c in val_share_fmt.columns:
                val_share_fmt[c] = val_share_fmt[c].apply(lambda x: fmt_pct(float(x)) if not pd.isna(x) else "-")
            st.dataframe(val_share_fmt, use_container_width=True)

            years_sorted = sorted(pivot_cnt.columns.tolist())
            x = list(range(len(years_sorted)))

            st.markdown("#### \U0001f4ca 100% Stacked \u2014 Komposisi Quantity")
            label_pct_qty = st.toggle("Tampilkan label % (Quantity)", value=False, key="yoy_label_qty_rewrite_v1")

            figq, axq = plt.subplots(figsize=(10, 5))
            bottom = [0.0] * len(years_sorted)
            for bucket in labs:
                vals = []
                for y in years_sorted:
                    v = float(qty_share.loc[bucket, y]) if (bucket in qty_share.index and y in qty_share.columns) else 0.0
                    vals.append(0.0 if math.isnan(v) else v)
                axq.bar(x, vals, bottom=bottom, label=str(bucket))
                if label_pct_qty:
                    for i, p in enumerate(vals):
                        if p >= 6.0:
                            axq.text(i, bottom[i] + p / 2, f"{p:.0f}%", ha="center", va="center", fontsize=8)
                bottom = [bottom[i] + vals[i] for i in range(len(vals))]

            axq.set_title("Komposisi % Jumlah Transaksi per Tahun (100% Stacked)")
            axq.set_xlabel("Tahun")
            axq.set_ylabel("% Quantity")
            axq.set_xticks(x)
            axq.set_xticklabels([str(y) for y in years_sorted])
            axq.set_ylim(0, 100)
            axq.grid(axis="y", linestyle="--", alpha=0.35)
            axq.legend(title="Bucket", bbox_to_anchor=(1.02, 1), loc="upper left")
            st.pyplot(figq)

            st.markdown("#### \U0001f4b0 100% Stacked \u2014 Komposisi Nilai")
            label_pct_val = st.toggle("Tampilkan label % (Nilai)", value=False, key="yoy_label_val_rewrite_v1")

            figv, axv = plt.subplots(figsize=(10, 5))
            bottom = [0.0] * len(years_sorted)
            for bucket in labs:
                vals = []
                for y in years_sorted:
                    v = float(val_share.loc[bucket, y]) if (bucket in val_share.index and y in val_share.columns) else 0.0
                    vals.append(0.0 if math.isnan(v) else v)
                axv.bar(x, vals, bottom=bottom, label=str(bucket))
                if label_pct_val:
                    for i, p in enumerate(vals):
                        if p >= 6.0:
                            axv.text(i, bottom[i] + p / 2, f"{p:.0f}%", ha="center", va="center", fontsize=8)
                bottom = [bottom[i] + vals[i] for i in range(len(vals))]

            axv.set_title("Komposisi % Total Nilai per Tahun (100% Stacked)")
            axv.set_xlabel("Tahun")
            axv.set_ylabel("% Nilai")
            axv.set_xticks(x)
            axv.set_xticklabels([str(y) for y in years_sorted])
            axv.set_ylim(0, 100)
            axv.grid(axis="y", linestyle="--", alpha=0.35)
            axv.legend(title="Bucket", bbox_to_anchor=(1.02, 1), loc="upper left")
            st.pyplot(figv)

            st.markdown("#### \U0001f9e0 Insight Bucket (ringkas)")
            try:
                last_y = max(years_sorted)
                top_qty_bucket = pivot_cnt[last_y].idxmax()
                top_val_bucket = pivot_total[last_y].idxmax()
                st.write(
                    f"- Tahun **{last_y}**: bucket **qty terbesar** = **{top_qty_bucket}** "
                    f"({fmt_int(int(pivot_cnt.loc[top_qty_bucket, last_y]))} transaksi; {fmt_pct(float(qty_share.loc[top_qty_bucket, last_y]))})."
                )
                st.write(
                    f"- Tahun **{last_y}**: bucket **nilai terbesar** = **{top_val_bucket}** "
                    f"({fmt_rp(float(pivot_total.loc[top_val_bucket, last_y]))}; {fmt_pct(float(val_share.loc[top_val_bucket, last_y]))})."
                )
            except Exception:
                pass

            with st.expander("\U0001f50e Detail groupby (opsional)", expanded=False):
                st.dataframe(grp.sort_values(["Tahun", "Bucket"]), use_container_width=True)

        # =====================================================
        # TAB 3: VENDOR (also uses global filters)
        # =====================================================
        with tab_nilai_vendor:
            st.markdown("### \U0001f3f7\ufe0f Vendor Spotlight")

            if col_vendor == "(none)":
                st.info("Pilih kolom vendor di Mapping Kolom untuk membuka analisis vendor.")
                st.stop()

            cfg = load_bucket_cfg()
            thresholds = cfg.get("thresholds", [10e6, 50e6, 500e6])
            edges = build_edges(thresholds)
            labs = build_labels(edges)

            dfv = df_global.copy()
            dfv["Bucket"] = pd.cut(dfv["__NILAI_NUM__"], bins=edges, labels=labs, right=False, include_lowest=True)

            c1, c2, c3 = st.columns([1.3, 1.0, 1.7])
            with c1:
                bucket_pick = st.selectbox("Bucket fokus", options=labs, index=min(2, len(labs) - 1), key="vendor_bucket_rewrite_v1")
            with c2:
                topn = st.number_input("Top N", min_value=5, max_value=50, value=10, step=5, key="vendor_topn_rewrite_v1")
            with c3:
                show_detail = st.toggle("Tampilkan detail baris (lebih berat)", value=False, key="vendor_detail_rewrite_v1")

            dv = dfv[dfv["Bucket"].astype(str) == str(bucket_pick)].copy()
            if dv.empty:
                st.warning("Tidak ada data untuk filter ini.")
                st.stop()

            top_vendor = (
                dv.groupby(dv[col_vendor].astype(str))["__NILAI_NUM__"]
                .agg(Total="sum", Transaksi="size")
                .reset_index()
                .sort_values("Total", ascending=False)
                .head(int(topn))
            )

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.bar(top_vendor[col_vendor].astype(str), top_vendor["Transaksi"])
            ax.set_title(f"Top Vendor \u2014 Jumlah Transaksi (Bucket {bucket_pick})")
            ax.set_xlabel("Vendor")
            ax.set_ylabel("Jumlah")
            ax.grid(axis="y", linestyle="--", alpha=0.35)
            for lab in ax.get_xticklabels():
                lab.set_rotation(25)
                lab.set_ha("right")
            st.pyplot(fig)

            show_vendor = top_vendor.copy()
            show_vendor["Total"] = show_vendor["Total"].apply(lambda x: fmt_rp(float(x)))
            st.dataframe(show_vendor, use_container_width=True)

            if show_detail:
                st.markdown("#### \U0001f50e Detail Baris (Filtered)")
                detail_cols = [c for c in [col_periode, col_vendor, col_nilai] if c in dv.columns]
                if col_jenis != "(none)" and col_jenis in dv.columns:
                    detail_cols.insert(1, col_jenis)
                detail_cols += ["__YEAR__", "__NILAI_NUM__", "Bucket"]
                st.dataframe(dv[detail_cols].sort_values("__NILAI_NUM__", ascending=False), use_container_width=True)
    

# ==========================================================
# Tab Report (Poster & PDF)
# ==========================================================
with tab_report:
    if _SLA_LAZY_TABS:
        tab_poster, tab_pdf = st.tabs(["\U0001f3a8 Poster", "\U0001f4c4 PDF"], on_change="rerun", key="sla_active_report_subtab")
    else:
        tab_poster, tab_pdf = st.tabs(["\U0001f3a8 Poster", "\U0001f4c4 PDF"])

if (not _SLA_LAZY_TABS) or (bool(getattr(tab_report, "open", False)) and bool(getattr(tab_poster, "open", False))):
    with tab_poster:
        st.subheader("\U0001f4e5 Download Poster")

        if st.button("\U0001f3a8 Generate Poster A4"):
            rata_proses_seconds = df_filtered[proses_grafik_cols].mean()
        
            df_proses = pd.DataFrame({
                "Rata-rata SLA": [
                    format_duration(rata_proses_seconds[col]) for col in rata_proses_seconds.index
                ]
            }, index=rata_proses_seconds.index)
        
            poster_buf = generate_poster_A4(
            {},
            rata_proses_seconds,
            df_proses,
            "Captain Ferizy.png",
            periode_info_text,
            df_filtered,
            periode_col,
            selected_periode
            )

            # Simpan sebagai bytes agar stabil di session_state pada rerun Streamlit.
            # Bytes dapat dipakai langsung baik oleh st.image maupun st.download_button.
            if hasattr(poster_buf, "getvalue"):
                poster_bytes = poster_buf.getvalue()
            elif isinstance(poster_buf, (bytes, bytearray)):
                poster_bytes = bytes(poster_buf)
            else:
                raise TypeError(
                    f"Format hasil poster tidak didukung: {type(poster_buf).__name__}"
                )

            st.session_state.poster_buf = poster_bytes
    
        if "poster_buf" in st.session_state:
            # Streamlit 2026 menghapus parameter deprecated `use_column_width`.
            # `width="stretch"` memberikan perilaku visual yang sama: preview
            # mengikuti lebar container tanpa mengubah isi/generator poster.
            st.image(
                st.session_state.poster_buf,
                caption="Preview Poster A4",
                width="stretch",
            )
            st.download_button(
                "\U0001f4be Download Poster (PNG, A4 - 300 DPI)",
                data=st.session_state.poster_buf,
                file_name="Poster_SLA_A4.png",
                mime="image/png"
            )

# =========================
# TAB ANALISIS DATA (BARU)
# =========================
def render_tab_analisis_data_v1(df_source: pd.DataFrame, periode_col="PERIODE_DATETIME", sla_col="SLA"):
    import numpy as np
    import pandas as pd
    import streamlit as st

    def safe_pct(a, b):
        if a is None or pd.isna(a) or a == 0:
            return np.nan
        return (b - a) / a * 100

    def filter_range(df, start_dt, end_dt):
        m = (df[periode_col] >= start_dt) & (df[periode_col] <= end_dt)
        return df.loc[m].copy()

    def ensure_sla_seconds_local(df):
        # kolom aman: tidak bentrok dengan tab lain
        col = "__SLA_SECONDS_ANALYSIS__"
        if col not in df.columns:
            df[col] = df[sla_col].apply(parse_sla)
        return df, col

    st.subheader("\U0001f4ca Analisis Data (Perbandingan 2 Periode)")

    if df_source is None or df_source.empty:
        st.warning("Data kosong.")
        return

    if periode_col not in df_source.columns:
        st.error(f"Kolom {periode_col} tidak ditemukan.")
        return

    df_base = df_source.dropna(subset=[periode_col]).copy()
    if df_base.empty:
        st.warning("Data periode kosong.")
        return

    labels = sorted(df_base[periode_col].dt.to_period("M").astype(str).unique().tolist())
    if not labels:
        st.warning("Tidak ada periode yang bisa dipilih.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Periode A (Baseline)**")
        startA = st.selectbox("Mulai A", labels, index=0, key="ana_startA")
        endA   = st.selectbox("Sampai A", labels, index=len(labels)-1, key="ana_endA")
    with c2:
        st.markdown("**Periode B (Pembanding)**")
        startB = st.selectbox("Mulai B", labels, index=0, key="ana_startB")
        endB   = st.selectbox("Sampai B", labels, index=len(labels)-1, key="ana_endB")

    startA_dt = pd.Period(startA).to_timestamp()
    endA_dt   = pd.Period(endA).to_timestamp() + pd.offsets.MonthEnd(0)
    startB_dt = pd.Period(startB).to_timestamp()
    endB_dt   = pd.Period(endB).to_timestamp() + pd.offsets.MonthEnd(0)

    if startA_dt > endA_dt or startB_dt > endB_dt:
        st.error("Rentang periode tidak valid.")
        return

    dfA = filter_range(df_base, startA_dt, endA_dt)
    dfB = filter_range(df_base, startB_dt, endB_dt)

    # ===== VOLUME TRANSAKSI =====
    totalA, totalB = len(dfA), len(dfB)
    d_total = totalB - totalA
    p_total = safe_pct(totalA, totalB)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Transaksi (A)", f"{totalA:,}")
    m2.metric(
        "Total Transaksi (B)",
        f"{totalB:,}",
        delta=f"{d_total:+,}" + ("" if np.isnan(p_total) else f" ({p_total:+.1f}%)")
    )

    # ===== SLA COMPARISON =====
    if sla_col not in df_base.columns:
        st.info(f"Kolom SLA '{sla_col}' tidak ada \u2192 analisis SLA tidak ditampilkan (hanya volume transaksi).")
        return

    dfA, sla_sec_col = ensure_sla_seconds_local(dfA)
    dfB, _ = ensure_sla_seconds_local(dfB)

    sA = dfA[sla_sec_col].dropna()
    sB = dfB[sla_sec_col].dropna()

    meanA = float(sA.mean()) if len(sA) else np.nan
    meanB = float(sB.mean()) if len(sB) else np.nan
    d_mean = meanB - meanA if np.isfinite(meanA) and np.isfinite(meanB) else np.nan
    p_mean = safe_pct(meanA, meanB) if np.isfinite(meanA) and np.isfinite(meanB) else np.nan

    m3.metric("Rata-rata SLA (A)", "-" if np.isnan(meanA) else seconds_to_sla_format(meanA))
    m4.metric(
        "Rata-rata SLA (B)",
        "-" if np.isnan(meanB) else seconds_to_sla_format(meanB),
        delta="-" if np.isnan(d_mean) else f"{seconds_to_sla_format(d_mean)}" + ("" if np.isnan(p_mean) else f" ({p_mean:+.1f}%)")
    )

    st.markdown("### Ringkasan (Nominal & %)")
    summary = pd.DataFrame([
        ["Transaksi", totalA, totalB, d_total, p_total],
        ["Mean SLA (detik)", meanA, meanB, d_mean, p_mean],
    ], columns=["Metrik", "A", "B", "\u0394 (B-A)", "\u0394 %"])

    st.dataframe(summary, use_container_width=True)

# =========================
# TAB ANALISIS DATA \u2014 FAST + EXECUTIVE DASHBOARD (Direksi)
# Update:
# - Warna font lebih kontras (lebih "kelihatan")
# - SLA ringkas: 2 desimal -> "3,22 hari"
# - KPI card & badge tetap aman (tidak ganggu fitur tab lain)
# =========================
# ============================================================
# FULL COPY-PASTE PACKAGE
# 1) HELPER FUNCTIONS (tempel di atas: with tab_analisis:)
# 2) TAB_ANALISIS (full)
# 3) BLOK POSTER EXECUTIVE SUMMARY (sudah include di tab_analisis)
#
# FIX UTAMA:
# - Layout poster dirapikan agar TIDAK TIMPANG TINDIH
# - Logo kiri/kanan aman (auto-fit)
# - Judul/subjudul/period/timestamp diposisikan ulang
# - Badge delta dipindah ke area yang aman
# - Chart diberi ruang lebih, label bulan diputar & diperkecil
# ============================================================

import io, os, re
import numpy as np
import pandas as pd
from datetime import datetime

# Logo (sesuai koreksi)
LOGO_LEFT_URL  = "https://raw.githubusercontent.com/firmanaditya90/SLA/main/Danantara.png"   # Danantara (kiri atas)
LOGO_RIGHT_URL = "https://raw.githubusercontent.com/firmanaditya90/SLA/main/asdp_logo.png"   # ASDP (kanan atas)

@st.cache_data(show_spinner=False)
def _fetch_image_bytes(url: str) -> bytes | None:
    """Download bytes gambar dari URL (cache biar cepat)."""
    try:
        import requests
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        return r.content
    except Exception:
        return None

def _id_num(x, nd=2, suffix=""):
    """Format angka Indonesia: 1234.56 -> 1.234,56"""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        s = f"{float(x):,.{nd}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        if nd == 0:
            s = s.split(",")[0]
        return s + suffix
    except Exception:
        return "-"

def _id_int(x):
    """Format integer Indonesia: 46530 -> 46.530"""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        return f"{int(x):,}".replace(",", ".")
    except Exception:
        return "-"

def _sla_short_days(seconds, nd=2):
    """Ringkas: '3,22 hari'"""
    if seconds is None or (isinstance(seconds, float) and np.isnan(seconds)):
        return "-"
    return _id_num(float(seconds) / 86400.0, nd=nd, suffix=" hari")

def _sla_long_id(seconds):
    """Detail: '3 hari 17 jam 41 menit'"""
    if seconds is None or (isinstance(seconds, float) and np.isnan(seconds)):
        return "-"
    sec = float(seconds)
    neg = sec < 0
    sec = abs(sec)
    d = int(sec // 86400)
    h = int((sec % 86400) // 3600)
    m = int((sec % 3600) // 60)
    parts = []
    if d: parts.append(f"{d} hari")
    if h: parts.append(f"{h} jam")
    if m or not parts: parts.append(f"{m} menit")
    s = " ".join(parts)
    return f"-{s}" if neg else s

def pct_change(a, b):
    if a is None or pd.isna(a) or a == 0:
        return np.nan
    return (b - a) / a * 100

def year_or_label(sel_periods, fallback):
    yrs = sorted({int(p.year) for p in sel_periods}) if sel_periods else []
    return str(yrs[0]) if len(yrs) == 1 else fallback

def build_auto_headline(totalA, totalB, meanA, meanB, p_total, d_total):
    """Headline otomatis untuk Direksi."""
    vol_dir = "naik" if d_total > 0 else ("turun" if d_total < 0 else "stabil")
    vol_part = f"Volume {vol_dir} {_id_num(abs(p_total),2,'%')}" if np.isfinite(p_total) else f"Volume {vol_dir}"

    if not (np.isfinite(meanA) and np.isfinite(meanB)):
        sla_part = "SLA: data belum lengkap"
    else:
        d = meanB - meanA
        sla_dir = "membaik" if d < 0 else ("memburuk" if d > 0 else "stabil")
        imp = (meanA - meanB) / meanA * 100 if meanA else np.nan
        sla_part = f"SLA {sla_dir} {_id_num(abs(imp),2,'%')}" if np.isfinite(imp) else f"SLA {sla_dir}"

    return f"{sla_part} \u2022 {vol_part}"

def make_exec_poster_png_v3(
    *,
    labelA, labelB,
    seriesA, seriesB,
    totalA, totalB, p_total, d_total,
    meanA, meanB,
    kpi_days, complianceB, coverageB,
    d_comp, d_cov,
    vol_month_df=None,   # columns: Bulan, seriesA, seriesB
    sla_month_df=None,   # columns: Bulan, seriesA, seriesB (hari)
    headline="",
    logo_left_bytes=None,    # Danantara (kiri atas)
    logo_right_bytes=None,   # ASDP (kanan atas)
    title="EXECUTIVE SUMMARY",
    subtitle="Analisis SLA & Transaksi",
):
    """
    POSTER FIXED LAYOUT (NO OVERLAP):
    - Header 3 baris: title/subtitle + timestamp/period
    - Logo kiri & kanan auto-fit dan tidak menimpa teks
    - Card grid rapi (4 + 4)
    - Chart grid rapi (2) dengan label bulan rotate supaya tidak bertabrakan
    """
    import matplotlib.pyplot as plt
    from PIL import Image
    import textwrap

    dpi = 200
    W, H = int(11.69 * dpi), int(8.27 * dpi)   # A4 landscape @200dpi \u2248 2338x1654
    fig = plt.figure(figsize=(W/dpi, H/dpi), dpi=dpi)
    fig.patch.set_facecolor("white")

    # =======================
    # BACKGROUND (gradient + accent)
    # =======================
    ax_bg = fig.add_axes([0, 0, 1, 1])
    ax_bg.axis("off")
    grad = np.linspace(0, 1, H).reshape(H, 1)
    top = np.array([18, 34, 84]) / 255.0        # navy
    bottom = np.array([255, 255, 255]) / 255.0  # white
    bg = bottom + (top - bottom) * (1 - grad)
    bg = np.repeat(bg, W, axis=1)
    ax_bg.imshow(bg, aspect="auto", extent=[0, 1, 0, 1])

    # Accent bars
    ax_bg.add_patch(plt.Rectangle((0.00, 0.92), 1.0, 0.08, color=(0.10,0.55,0.85,0.26), ec=(0,0,0,0)))
    ax_bg.add_patch(plt.Rectangle((0.00, 0.00), 1.0, 0.06, color=(0.00,0.70,0.55,0.18), ec=(0,0,0,0)))
    ax_bg.add_patch(plt.Circle((0.12, 0.52), 0.20, color=(1.0,0.55,0.0,0.07), ec=(0,0,0,0)))
    ax_bg.add_patch(plt.Circle((0.92, 0.46), 0.25, color=(0.00,0.70,0.55,0.10), ec=(0,0,0,0)))

    # =======================
    # LOGOS (dedicated safe zone)
    # =======================
    def _logo_ax(bytes_, x, y, w, h):
        if not bytes_:
            return
        try:
            im = Image.open(io.BytesIO(bytes_)).convert("RGBA")
            ax = fig.add_axes([x, y, w, h])
            ax.axis("off")
            ax.imshow(im)
        except Exception:
            pass

    # Left logo (Danantara) and right logo (ASDP)
    _logo_ax(logo_left_bytes,  0.02, 0.915, 0.10, 0.07)
    _logo_ax(logo_right_bytes, 0.88, 0.915, 0.10, 0.07)

    # =======================
    # HEADER TEXT (safe zone middle, no overlap with logos)
    # =======================
    axH = fig.add_axes([0.14, 0.915, 0.72, 0.07])
    axH.axis("off")
    axH.text(0.00, 0.72, title, fontsize=24, fontweight="bold", color=(1,1,1,0.96), va="center")
    axH.text(0.00, 0.22, subtitle, fontsize=10, fontweight="bold", color=(1,1,1,0.90), va="center")

    axHP = fig.add_axes([0.14, 0.875, 0.84, 0.04])
    axHP.axis("off")
    axHP.text(1.00, 0.50, datetime.now().strftime("%d %b %Y %H:%M"),
              ha="right", fontsize=8, color=(1,1,1,0.88), fontweight="bold")
    axHP.text(0.00, 0.50, f"Periode: {labelA} vs {labelB}",
              ha="left", fontsize=10, color=(1,1,1,0.92), fontweight="bold")

    # =======================
    # HEADLINE STRIP (wrap to avoid overflow)
    # =======================
    axHL = fig.add_axes([0.03, 0.83, 0.94, 0.055]); axHL.axis("off")
    axHL.add_patch(plt.Rectangle((0,0),1,1, facecolor=(1,1,1,0.86), edgecolor=(0,0,0,0.10)))
    htxt = headline if headline else "-"
    htxt = "\n".join(textwrap.wrap(htxt, width=70))
    axHL.text(0.02, 0.50, htxt, va="center", fontsize=14, fontweight="bold", color=(0.05,0.10,0.20,0.98))

    # =======================
    # CARD HELPER (fixed internal layout)
    # =======================
    def card(axpos, title, value, sub, badge=None, good=True):
        ax = fig.add_axes(axpos); ax.axis("off")
        ax.add_patch(plt.Rectangle((0,0),1,1, facecolor=(1,1,1,0.94), edgecolor=(0,0,0,0.13), linewidth=1.0))
        ax.text(0.05, 0.80, title, fontsize=8, fontweight="bold", color=(0.08,0.12,0.20,0.92))
        ax.text(0.05, 0.42, value, fontsize=12, fontweight="bold", color=(0.02,0.08,0.16,0.98))
        ax.text(0.05, 0.14, sub, fontsize=8, color=(0.08,0.12,0.20,0.72), fontweight="bold")

        if badge:
            fc = (0.05, 0.65, 0.50, 0.18) if good else (0.85, 0.20, 0.20, 0.16)
            tc = (0.02, 0.45, 0.34, 0.95) if good else (0.55, 0.10, 0.10, 0.95)
            # badge always top-right inside card
            ax.add_patch(plt.Rectangle((0.67, 0.70), 0.30, 0.22, facecolor=fc, edgecolor=(0,0,0,0.10)))
            ax.text(0.82, 0.81, badge, ha="center", va="center", fontsize=8, fontweight="bold", color=tc)

    # =======================
    # KPI VALUES
    # =======================
    vol_badge = f"{_id_int(d_total)} ({_id_num(p_total,2,'%')})" if np.isfinite(p_total) else _id_int(d_total)
    d_sla = (meanB - meanA) if (np.isfinite(meanA) and np.isfinite(meanB)) else np.nan
    d_sla_badge = (("\u2212" if d_sla < 0 else "+") + _sla_short_days(abs(d_sla),2)) if np.isfinite(d_sla) else "-"
    good_sla = True if (not np.isfinite(d_sla)) else (d_sla < 0)

    comp_val = _id_num(complianceB,2,"%") if np.isfinite(complianceB) else "-"
    cov_val  = _id_num(coverageB,2,"%") if np.isfinite(coverageB) else "-"
    comp_badge = _id_num(d_comp,2," poin") if np.isfinite(d_comp) else "-"
    cov_badge  = _id_num(d_cov,2," poin") if np.isfinite(d_cov) else "-"

    sla_word = "membaik" if (np.isfinite(d_sla) and d_sla < 0) else ("memburuk" if (np.isfinite(d_sla) and d_sla > 0) else "stabil")

    # =======================
    # CARD GRID POSITIONS (NO OVERLAP)
    # =======================
    # Row 1 (Ringkasan Utama)
    y1 = 0.69
    h1 = 0.12
    w = 0.225
    gap = 0.015
    xs = [0.03, 0.03+w+gap, 0.03+2*(w+gap), 0.03+3*(w+gap)]
    card([xs[0], y1, w, h1], f"Total Transaksi ({seriesA})", _id_int(totalA), "Baseline")
    card([xs[1], y1, w, h1], f"Total Transaksi ({seriesB})", _id_int(totalB), "Perubahan vs A", vol_badge, good=(d_total>=0))
    card([xs[2], y1, w, h1], f"Avg SLA ({seriesA})", _sla_short_days(meanA,2), _sla_long_id(meanA))
    card([xs[3], y1, w, h1], f"Avg SLA ({seriesB})", _sla_short_days(meanB,2), _sla_long_id(meanB), d_sla_badge, good=good_sla)

    # Executive Score label (separate line)
    axES = fig.add_axes([0.03, 0.63, 0.94, 0.05]); axES.axis("off")
    axES.text(0.00, 0.70, "Executive Score", fontsize=12, fontweight="bold", color=(0.02,0.08,0.16,0.95))
    axES.text(0.00, 0.35, f"Target KPI SLA: {_id_num(kpi_days,2,' hari')}", fontsize=10, color=(0.02,0.08,0.16,0.70), fontweight="bold")

    # Row 2 (Executive Score cards)
    y2 = 0.52
    h2 = 0.12
    card([xs[0], y2, w, h2], "Growth Volume", _id_num(p_total,2,"%") if np.isfinite(p_total) else "-", "\u0394 transaksi vs A", f"{_id_int(d_total)} trx", good=(d_total>=0))
    card([xs[1], y2, w, h2], "Perubahan SLA", sla_word, "Ringkas (hari)", d_sla_badge, good=good_sla)
    card([xs[2], y2, w, h2], f"KPI Compliance \u2264 {_id_num(kpi_days,2,' hari')}", comp_val, "\u0394 poin vs A", comp_badge, good=(d_comp>=0 if np.isfinite(d_comp) else True))
    card([xs[3], y2, w, h2], "Coverage SLA", cov_val, "Kualitas data SLA", cov_badge, good=(d_cov>=0 if np.isfinite(d_cov) else True))

    # =======================
    # CHARTS (bigger bottom margin, rotated labels)
    # =======================
    # Volume chart
    axV = fig.add_axes([0.05, 0.10, 0.44, 0.36])
    axV.set_title("Tren Volume (bulan)", fontsize=16, fontweight="bold", loc="left", color=(0.02,0.08,0.16,0.95))
    if isinstance(vol_month_df, pd.DataFrame) and "Bulan" in vol_month_df.columns and seriesA in vol_month_df.columns and seriesB in vol_month_df.columns:
        x = list(range(len(vol_month_df["Bulan"])))
        axV.plot(x, vol_month_df[seriesA].values, marker="o", linewidth=2.8, label=str(seriesA))
        axV.plot(x, vol_month_df[seriesB].values, marker="o", linewidth=2.8, label=str(seriesB))
        axV.set_xticks(x)
        axV.set_xticklabels(vol_month_df["Bulan"].tolist(), fontsize=9, rotation=35, ha="right")
        axV.grid(True, alpha=0.22)
        axV.legend(frameon=True, fontsize=11, loc="upper left")
    else:
        axV.text(0.5, 0.5, "Data tren volume tidak tersedia", ha="center", va="center", alpha=0.7)
        axV.axis("off")

    # SLA chart
    axT = fig.add_axes([0.53, 0.10, 0.44, 0.36])
    axT.set_title("Tren SLA (hari, bulan)", fontsize=16, fontweight="bold", loc="left", color=(0.02,0.08,0.16,0.95))
    if isinstance(sla_month_df, pd.DataFrame) and "Bulan" in sla_month_df.columns and seriesA in sla_month_df.columns and seriesB in sla_month_df.columns:
        x = list(range(len(sla_month_df["Bulan"])))
        axT.plot(x, sla_month_df[seriesA].values, marker="o", linewidth=2.8, label=str(seriesA))
        axT.plot(x, sla_month_df[seriesB].values, marker="o", linewidth=2.8, label=str(seriesB))
        axT.set_xticks(x)
        axT.set_xticklabels(sla_month_df["Bulan"].tolist(), fontsize=10, rotation=25, ha="right")
        axT.grid(True, alpha=0.22)
        axT.legend(frameon=True, fontsize=11, loc="upper right")
    else:
        axT.text(0.5, 0.5, "Data tren SLA tidak tersedia", ha="center", va="center", alpha=0.7)
        axT.axis("off")

    # =======================
    # FOOTER (safe zone)
    # =======================
    axF = fig.add_axes([0.03, 0.02, 0.94, 0.05]); axF.axis("off")
    axF.text(0.00, 0.50, "",
             fontsize=8, alpha=0.80, color=(0.02,0.08,0.16,0.80), fontweight="bold")
    axF.text(1.00, 0.20, "Sumber: Tab Analisis (hasil filter aktif)",
             fontsize=10, alpha=0.80, ha="right", color=(0.02,0.08,0.16,0.80), fontweight="bold")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.10)
    plt.close(fig)
    return buf.getvalue()

def make_exec_poster_pdf_from_png(png_bytes):
    """Convert PNG poster ke 1 halaman PDF (A4 landscape)."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    W, H = landscape(A4)
    margin = 18
    img = ImageReader(io.BytesIO(png_bytes))
    c.drawImage(img, margin, margin, width=W-2*margin, height=H-2*margin, preserveAspectRatio=True, anchor="c")
    c.showPage()
    c.save()
    return buf.getvalue()


# ============================================================
# TAB ANALISIS \u2014 FULL (tempel di: with tab_analisis:)
# ============================================================

if (not _SLA_LAZY_TABS) or bool(getattr(tab_analisis, "open", False)):
    with tab_analisis:
        import plotly.express as px

        st.markdown("## \U0001f4ca Analisis Data \u2014 Executive Dashboard")
        st.caption("Bandingkan **A vs B** (Tahun vs Tahun, Bulan vs Bulan, atau Rentang vs Rentang). Angka di sini mengikuti filter tab_analisis.")

        # Guard
        if "df_raw" not in locals() or df_raw is None or df_raw.empty:
            st.warning("Data kosong.")
            st.stop()
        if "periode_col" not in locals() or periode_col is None or periode_col not in df_raw.columns:
            st.error("Kolom periode (periode_col) tidak ditemukan.")
            st.stop()

        # Toggle filter scope
        use_sidebar_filter = st.toggle("Gunakan filter sidebar (df_filtered)", value=True, key="ana_usefilter_all_v3")
        df_base = df_filtered.copy() if (use_sidebar_filter and "df_filtered" in locals()) else df_raw.copy()
        if df_base is None or df_base.empty:
            st.warning("Data kosong (setelah filter).")
            st.stop()

        # -------------------------
        # Filter tambahan: Jenis Transaksi (multi-select) - ALL / 1 / banyak
        # -------------------------
        trx_col = None
        for _c in df_base.columns:
            _cu = re.sub(r"\s+", " ", str(_c).strip().upper())
            if _cu in {"JENIS TRANSAKSI", "JENIS_TRANSAKSI", "TRANSAKSI", "NAMA TRANSAKSI", "TYPE TRANSAKSI", "TIPE TRANSAKSI"}:
                trx_col = _c
                break
            if ("JENIS" in _cu and "TRANSAK" in _cu) or (_cu.endswith("TRANSAKSI")):
                trx_col = _c
                break

        if trx_col:
            trx_options = sorted([x for x in df_base[trx_col].dropna().astype(str).unique().tolist() if str(x).strip() != ""])
            trx_pick = st.multiselect(
                "Filter transaksi (pilih 1/lebih, atau ALL)",
                options=["ALL"] + trx_options,
                default=["ALL"],
                key="ana_trx_filter_v1"
            )
            if trx_pick and "ALL" not in trx_pick:
                df_base = df_base[df_base[trx_col].astype(str).isin(trx_pick)].copy()

        if df_base.empty:
            st.warning("Data kosong setelah filter transaksi.")
            st.stop()

        # Month names
        month_id = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
            7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }
        id_month = {v.lower(): k for k, v in month_id.items()}

        # CSS cards (kontras)
        st.markdown("""
<style>
.kpi-wrap{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:10px}
.kpi-card{
  border:1px solid rgba(49,51,63,.15);
  border-radius:16px;
  padding:14px 14px 12px;
  background:white;
  box-shadow:0 10px 22px rgba(0,0,0,.08);
}
.kpi-title{font-size:13px;color:rgba(15,23,42,.78);margin:0 0 6px 0;font-weight:700;text-align:center}
.kpi-value{font-size:38px;font-weight:900;line-height:1.1;margin:0;color:rgb(15,23,42);text-align:center}
.kpi-sub{font-size:12px;color:rgba(15,23,42,.70);margin-top:6px;font-weight:700;text-align:center}
.badge{
  display:inline-block;padding:5px 11px;border-radius:999px;
  font-size:12px;font-weight:900;margin-top:10px
}
.badge-up{background:rgba(16,185,129,.15);color:rgb(4,120,87)}
.badge-down{background:rgba(239,68,68,.15);color:rgb(153,27,27)}
.badge-flat{background:rgba(100,116,139,.16);color:rgb(30,41,59)}
.hero{
  border-radius:16px;padding:14px 16px;
  background:rgba(34,197,94,.10);
  border:1px solid rgba(34,197,94,.28);
  margin-top:12px;
  color:rgb(15,23,42);
  font-weight:750;
}
.hero b{font-weight:950}
.small-cap{color:rgba(15,23,42,.72);font-weight:750}
@media(max-width:1100px){
  .kpi-wrap{grid-template-columns:1fr}
}
</style>
""", unsafe_allow_html=True)

        def badge_class(delta):
            try:
                if delta is None or (isinstance(delta, float) and np.isnan(delta)):
                    return "badge-flat"
                if delta > 0:
                    return "badge-up"
                if delta < 0:
                    return "badge-down"
                return "badge-flat"
            except Exception:
                return "badge-flat"

        def safe_pct(a, b):
            if a is None or pd.isna(a) or a == 0:
                return np.nan
            return (b - a) / a * 100

        # -------------------------
        # Periode parsing -> PERIOD_M (Period[M])
        # -------------------------
        def to_period_month(x):
            if pd.isna(x):
                return pd.NaT
            if isinstance(x, pd.Period):
                return x.asfreq("M")
            if isinstance(x, (pd.Timestamp,)):
                return x.to_period("M")
            s = str(x).strip()
            if not s:
                return pd.NaT

            dt = pd.to_datetime(s, errors="coerce")
            if pd.notna(dt):
                return dt.to_period("M")

            m = re.search(r"(\d{4})[-/](\d{1,2})", s)
            if m:
                y = int(m.group(1)); mo = int(m.group(2))
                if 1 <= mo <= 12:
                    return pd.Period(f"{y}-{mo:02d}", freq="M")

            s_low = s.lower()
            for nama, mo in id_month.items():
                if nama in s_low:
                    y_m = re.search(r"(\d{4})", s_low)
                    if y_m:
                        y = int(y_m.group(1))
                        return pd.Period(f"{y}-{mo:02d}", freq="M")
            return pd.NaT

        if "PERIOD_M" not in df_base.columns:
            df_base["PERIOD_M"] = df_base[periode_col].apply(to_period_month)

        df_base = df_base.dropna(subset=["PERIOD_M"]).copy()
        if df_base.empty:
            st.warning("Data periode kosong.")
            st.stop()

        periods = sorted(df_base["PERIOD_M"].unique().tolist())
        years = sorted({int(p.year) for p in periods})

        def period_label(p: pd.Period):
            return f"{month_id[int(p.month)]} {int(p.year)}"

        period_labels = [period_label(p) for p in periods]
        label_to_period = {period_label(p): p for p in periods}

        # -------------------------
        # Mode Perbandingan
        # -------------------------
        st.markdown("### \u2699\ufe0f Mode Perbandingan")
        mode = st.radio(
            "Pilih mode",
            ["Tahun vs Tahun", "Bulan vs Bulan (tahun bebas)", "Rentang (A) vs Rentang (B)"],
            horizontal=True,
            key="ana_mode_all_v5"
        )

        colA, colB, colS = st.columns([1, 1, 1])
        with colS:
            st.markdown("**Metrik SLA**")

            # pilih kolom SLA (pakai daftar helper kalau ada)
            sla_candidates = []
            if "available_sla_cols" in globals() and isinstance(available_sla_cols, list):
                sla_candidates += [c for c in available_sla_cols if c in df_base.columns]

            # fallback kolom populer
            for c in ["KEUANGAN", "TOTAL WAKTU", "TOTAL_WAKTU", "SLA", "SLA (DETIK)", "SLA_DETIK", "SLA_HARI", "SLA HARI"]:
                if c in df_base.columns and c not in sla_candidates:
                    sla_candidates.append(c)

            sla_options = [c for c in sla_candidates if c in df_base.columns]
            if sla_options:
                default_idx = 0
                for prefer in ["KEUANGAN", "TOTAL WAKTU", "TOTAL_WAKTU", "SLA", "SLA (DETIK)", "SLA_DETIK"]:
                    if prefer in sla_options:
                        default_idx = sla_options.index(prefer)
                        break
                sla_pick = st.selectbox("Kolom SLA", sla_options, index=default_idx, key="ana_sla_pick_v5")
            else:
                sla_pick = None
                st.info("Kolom SLA tidak terdeteksi (SLA card & chart akan mengikuti kondisi data).")

        labelA = labelB = ""
        selA = []
        selB = []

        if mode == "Tahun vs Tahun":
            with colA:
                yearA = st.selectbox("Periode A \u2014 Tahun", years, index=0, key="ana_yearA_v5")
            with colB:
                yearB = st.selectbox("Periode B \u2014 Tahun", years, index=min(1, len(years) - 1), key="ana_yearB_v5")

            selA = [p for p in periods if int(p.year) == int(yearA)]
            selB = [p for p in periods if int(p.year) == int(yearB)]
            labelA, labelB = f"Tahun {yearA}", f"Tahun {yearB}"

        elif mode == "Bulan vs Bulan (tahun bebas)":
            with colA:
                mA = st.selectbox("Periode A \u2014 Bulan", period_labels, index=0, key="ana_monthA_v5")
            with colB:
                mB = st.selectbox("Periode B \u2014 Bulan", period_labels, index=min(1, len(period_labels) - 1), key="ana_monthB_v5")

            selA = [label_to_period[mA]]
            selB = [label_to_period[mB]]
            labelA, labelB = mA, mB

        else:  # range
            with colA:
                startA = st.selectbox("Periode A \u2014 Mulai", period_labels, index=0, key="ana_startA_v5")
                endA   = st.selectbox("Periode A \u2014 Sampai", period_labels, index=len(period_labels)-1, key="ana_endA_v5")
            with colB:
                startB = st.selectbox("Periode B \u2014 Mulai", period_labels, index=0, key="ana_startB_v5")
                endB   = st.selectbox("Periode B \u2014 Sampai", period_labels, index=len(period_labels)-1, key="ana_endB_v5")

            pA0 = label_to_period[startA]; pA1 = label_to_period[endA]
            pB0 = label_to_period[startB]; pB1 = label_to_period[endB]

            if pA0 > pA1: pA0, pA1 = pA1, pA0
            if pB0 > pB1: pB0, pB1 = pB1, pB0

            selA = [p for p in periods if pA0 <= p <= pA1]
            selB = [p for p in periods if pB0 <= p <= pB1]
            labelA = f"{period_label(selA[0])} \u2013 {period_label(selA[-1])}" if selA else "Periode A"
            labelB = f"{period_label(selB[0])} \u2013 {period_label(selB[-1])}" if selB else "Periode B"

        if not selA or not selB:
            st.warning("Pilihan periode A/B kosong. Silakan ubah pilihan.")
            st.stop()

        dfA = df_base[df_base["PERIOD_M"].isin(selA)].copy()
        dfB = df_base[df_base["PERIOD_M"].isin(selB)].copy()

        # -------------------------
        # KPI Target (ambil dari Tab Overview)
        # -------------------------
        try:
            kpi_days = load_kpi()
        except Exception:
            kpi_days = None
        kpi_sec = float(kpi_days) * 86400.0 if (kpi_days is not None and not pd.isna(kpi_days)) else None

        # -------------------------
        # SLA seconds: FIXED parsing (numeric dulu, baru parse_sla)
        # -------------------------
        has_sla = bool(sla_pick) and (sla_pick in df_base.columns)

        def ensure_sla_seconds_local(df):
            out_col = "__SLA_SECONDS_ANALYSIS__"
            if out_col in df.columns:
                return df, out_col

            if (not has_sla) or (sla_pick not in df.columns):
                df[out_col] = np.nan
                return df, out_col

            s = df[sla_pick]

            # 1) numeric langsung (kalau SLA sudah detik)
            num = pd.to_numeric(s, errors="coerce")

            # 2) non-numeric -> parse_sla (format teks)
            if "parse_sla" in globals():
                def _parse_if_needed(v, n):
                    if pd.notna(n):
                        return float(n)

                    if v is None:
                        return np.nan
                    vs = str(v).strip().lower()
                    if vs in {"", "nan", "none", "-", "null"}:
                        return np.nan

                    try:
                        sec = parse_sla(v)
                    except Exception:
                        sec = np.nan

                    # parse gagal -> NaN (hindari garis 0)
                    try:
                        if (sec == 0 or sec == 0.0) and vs not in {"0", "0.0"}:
                            return np.nan
                    except Exception:
                        pass

                    return float(sec) if pd.notna(sec) else np.nan

                df[out_col] = [_parse_if_needed(v, n) for v, n in zip(s.tolist(), num.tolist())]
            else:
                df[out_col] = num

            return df, out_col

        meanA = meanB = np.nan
        coverageA = coverageB = np.nan
        complianceA = complianceB = np.nan

        if has_sla:
            dfA, sla_sec_col = ensure_sla_seconds_local(dfA)
            dfB, _ = ensure_sla_seconds_local(dfB)

            sA_all = dfA[sla_sec_col]
            sB_all = dfB[sla_sec_col]
            validA = sA_all.dropna()
            validB = sB_all.dropna()

            meanA = float(validA.mean()) if len(validA) else np.nan
            meanB = float(validB.mean()) if len(validB) else np.nan

            coverageA = float(sA_all.notna().mean() * 100) if len(dfA) else np.nan
            coverageB = float(sB_all.notna().mean() * 100) if len(dfB) else np.nan

            if kpi_sec is not None:
                complianceA = float((validA <= kpi_sec).mean() * 100) if len(validA) else np.nan
                complianceB = float((validB <= kpi_sec).mean() * 100) if len(validB) else np.nan

        d_cov = coverageB - coverageA if (np.isfinite(coverageA) and np.isfinite(coverageB)) else np.nan

        # -------------------------
        # KPI Cards (Total Nilai dihapus)
        # -------------------------
        totalA, totalB = len(dfA), len(dfB)
        d_total = totalB - totalA
        p_total = safe_pct(totalA, totalB)

        d_sla = meanB - meanA if (np.isfinite(meanA) and np.isfinite(meanB)) else np.nan
        p_sla = safe_pct(meanA, meanB) if (np.isfinite(meanA) and np.isfinite(meanB)) else np.nan

        d_comp = complianceB - complianceA if (np.isfinite(complianceA) and np.isfinite(complianceB)) else np.nan
        p_comp = safe_pct(complianceA, complianceB) if (np.isfinite(complianceA) and np.isfinite(complianceB)) else np.nan

        badge_vol = f"{_id_int(d_total)} ({_id_num(p_total,2,'%')})" if np.isfinite(p_total) else _id_int(d_total)
        badge_sla = (("\u2212" if d_sla < 0 else "+") + _sla_short_days(abs(d_sla), 2) + (f" ({p_sla:+.1f}%)" if np.isfinite(p_sla) else "")) if np.isfinite(d_sla) else "-"
        badge_comp = (f"{d_comp:+.1f} pts" + (f" ({p_comp:+.1f}%)" if np.isfinite(p_comp) else "")) if np.isfinite(d_comp) else "-"

        trx_sub = f"{labelA}: {_id_int(totalA)} \u2022 {labelB}: {_id_int(totalB)}"
        if np.isfinite(p_total):
            trx_sub += f" \u2022 \u0394: {badge_vol}"

        if has_sla and np.isfinite(meanA) and np.isfinite(meanB):
            sla_sub = (
                f"{labelA}: {_sla_short_days(meanA,2)} | {seconds_to_sla_format(meanA)}<br/>"
                f"{labelB}: {_sla_short_days(meanB,2)} | {seconds_to_sla_format(meanB)}"
            )
        else:
            sla_sub = "Data SLA tidak tersedia / belum terbaca (cek pilihan kolom SLA)."

        if kpi_days is not None and has_sla and np.isfinite(complianceB):
            comp_sub = f"Target KPI {float(kpi_days):.2f} hari \u2022 {labelA}: {complianceA:.1f}% \u2022 {labelB}: {complianceB:.1f}%"
        elif kpi_days is not None:
            comp_sub = f"Target KPI {float(kpi_days):.2f} hari"
        else:
            comp_sub = "Target KPI belum diatur di Tab Overview."

        html_cards = f"""
    <div class="kpi-wrap">
      <div class="kpi-card">
        <p class="kpi-title">Jumlah Transaksi (A vs B)</p>
        <p class="kpi-value">{_id_int(totalB)}</p>
        <span class="badge {badge_class(d_total)}">{badge_vol}</span>
        <div class="kpi-sub">{trx_sub}</div>
      </div>

      <div class="kpi-card">
        <p class="kpi-title">Rata-rata SLA (A vs B)</p>
        <p class="kpi-value">{_sla_short_days(meanB,2) if (has_sla and np.isfinite(meanB)) else "-"}</p>
        <span class="badge {badge_class(-1 if (np.isfinite(d_sla) and d_sla<0) else (1 if (np.isfinite(d_sla) and d_sla>0) else 0))}">{badge_sla}</span>
        <div class="kpi-sub">{sla_sub}</div>
      </div>

      <div class="kpi-card">
        <p class="kpi-title">Success Rate vs Target KPI</p>
        <p class="kpi-value">{(f"{complianceB:.1f}%") if (has_sla and np.isfinite(complianceB)) else "-"}</p>
        <span class="badge {badge_class(d_comp)}">{badge_comp}</span>
        <div class="kpi-sub">{comp_sub}</div>
      </div>
    </div>
    """
        st.markdown(html_cards, unsafe_allow_html=True)

        # Highlight ringkas
        vol_dir = "naik" if d_total > 0 else ("turun" if d_total < 0 else "stabil")
        spot = f"\u2022 Volume transaksi <b>{vol_dir}</b>: {_id_int(totalA)} \u2192 {_id_int(totalB)} (\u0394 {badge_vol})."
        if has_sla and np.isfinite(d_sla):
            sla_dir = "membaik" if d_sla < 0 else ("memburuk" if d_sla > 0 else "stabil")
            spot += f" \u2022 SLA <b>{sla_dir}</b>: <b>{_sla_short_days(meanA,2)}</b> \u2192 <b>{_sla_short_days(meanB,2)}</b> (\u0394 {badge_sla})."
        if kpi_days is not None and has_sla and np.isfinite(complianceB):
            spot += f" \u2022 Dengan target KPI <b>{float(kpi_days):.2f} hari</b>, {labelB} memenuhi target sebesar <b>{complianceB:.1f}%</b>."
        st.markdown(f"<div class='hero'>{spot}</div>", unsafe_allow_html=True)

        # (opsional) debug SLA
        with st.expander("\U0001f9ea Debug SLA (cek pembacaan detik)", expanded=False):
            st.write("Kolom SLA dipilih:", sla_pick)
            if "__SLA_SECONDS_ANALYSIS__" in dfA.columns:
                st.write("Sample A (seconds):", dfA["__SLA_SECONDS_ANALYSIS__"].dropna().head(10).tolist())
            if "__SLA_SECONDS_ANALYSIS__" in dfB.columns:
                st.write("Sample B (seconds):", dfB["__SLA_SECONDS_ANALYSIS__"].dropna().head(10).tolist())

        # -------------------------
        # Diagram 1 & 2 (per bulan, sumbu X Jan\u2013Des, warna = periode A vs B)
        # -------------------------
        st.markdown("### \U0001f4c8 Grafik Perbandingan (per Bulan)")

        def year_or_label(sel_periods, fallback_tag):
            ys = sorted({int(p.year) for p in sel_periods})
            if len(ys) == 1:
                return f"Tahun {ys[0]}"
            return fallback_tag

        seriesA = year_or_label(selA, "A")
        seriesB = year_or_label(selB, "B")

        month_order = [month_id[m] for m in range(1, 13)]

        # Diagram 1: jumlah transaksi per bulan
        def trx_by_monthnum(df):
            if df.empty:
                return {}
            g = df.groupby("PERIOD_M").size().reset_index(name="trx")
            g["m"] = g["PERIOD_M"].apply(lambda p: int(p.month))
            return g.groupby("m")["trx"].sum().to_dict()

        A_trx = trx_by_monthnum(dfA)
        B_trx = trx_by_monthnum(dfB)

        vol_month = pd.DataFrame({
            "Bulan": month_order,
            seriesA: [float(A_trx.get(m, 0)) for m in range(1, 13)],
            seriesB: [float(B_trx.get(m, 0)) for m in range(1, 13)],
        })

        vol_long = vol_month.melt(id_vars=["Bulan"], var_name="Periode", value_name="Jumlah Transaksi")
        fig_trx = px.bar(
            vol_long,
            x="Bulan",
            y="Jumlah Transaksi",
            color="Periode",
            barmode="group",
            category_orders={"Bulan": month_order},
            title=f"Diagram 1 \u2014 Jumlah Transaksi per Bulan ({seriesA} vs {seriesB})"
        )
        fig_trx.update_layout(xaxis_title=None, yaxis_title="Jumlah Transaksi", legend_title=None, height=430)
        st.plotly_chart(fig_trx, use_container_width=True)

        # Diagram 2: rata-rata SLA per bulan (hari)
        sla_month = pd.DataFrame({"Bulan": month_order})
        if has_sla and "__SLA_SECONDS_ANALYSIS__" in dfA.columns and "__SLA_SECONDS_ANALYSIS__" in dfB.columns:
            def mean_sla_days_by_month(df, sec_col):
                if df.empty:
                    return {}
                d = df.copy()
                d = d[d[sec_col].notna()].copy()
                if d.empty:
                    return {}
                g = d.groupby("PERIOD_M")[sec_col].mean().reset_index(name="sec")
                g["m"] = g["PERIOD_M"].apply(lambda p: int(p.month))
                g["days"] = g["sec"] / 86400.0
                return g.groupby("m")["days"].mean().to_dict()

            A_days = mean_sla_days_by_month(dfA, "__SLA_SECONDS_ANALYSIS__")
            B_days = mean_sla_days_by_month(dfB, "__SLA_SECONDS_ANALYSIS__")

            sla_month[seriesA] = [float(A_days.get(m, np.nan)) for m in range(1, 13)]
            sla_month[seriesB] = [float(B_days.get(m, np.nan)) for m in range(1, 13)]

            sla_long = sla_month.melt(id_vars=["Bulan"], var_name="Periode", value_name="Rata-rata SLA (hari)")
            fig_sla = px.line(
                sla_long,
                x="Bulan",
                y="Rata-rata SLA (hari)",
                color="Periode",
                markers=True,
                category_orders={"Bulan": month_order},
                title=f"Diagram 2 \u2014 Rata-rata SLA per Bulan ({seriesA} vs {seriesB})"
            )
            fig_sla.update_layout(xaxis_title=None, yaxis_title="Rata-rata SLA (hari)", legend_title=None, height=430)
            st.plotly_chart(fig_sla, use_container_width=True)
        else:
            st.info("Diagram 2 (SLA) tidak ditampilkan karena kolom SLA belum tersedia/terdeteksi atau nilainya tidak terbaca.")
            sla_month[seriesA] = [np.nan] * 12
            sla_month[seriesB] = [np.nan] * 12

        # ============================================================
        # BLOK POSTER EXECUTIVE SUMMARY \u2014 FIXED LAYOUT (NO OVERLAP)
        # ============================================================
        st.markdown("---")
        st.markdown("### \U0001f5bc\ufe0f Poster Executive Summary (Analisis)")

        # (opsional) animasi di UI saja
        gif_url = "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"
        gif_bytes = _fetch_image_bytes(gif_url)
        if gif_bytes:
            st.image(gif_bytes, width=220)

        # Logo (kiri/kanan)
        logo_left_bytes = _fetch_image_bytes(LOGO_LEFT_URL) if "LOGO_LEFT_URL" in globals() else None
        logo_right_bytes = _fetch_image_bytes(LOGO_RIGHT_URL) if "LOGO_RIGHT_URL" in globals() else None

        c1, c2 = st.columns([1, 1])
        with c1:
            poster_title = st.text_input("Judul Poster", value="EXECUTIVE SUMMARY", key="ana_poster_title_v3")
        with c2:
            poster_subtitle = st.text_input("Sub Judul", value="Analisis SLA & Transaksi", key="ana_poster_subtitle_v3")

        headline = build_auto_headline(totalA, totalB, meanA, meanB, p_total, d_total) if "build_auto_headline" in globals() else ""

        @st.cache_data(show_spinner=False)
        def _gen_exec_poster_cached(payload: dict):
            png = make_exec_poster_png_v3(**payload)
            pdf = make_exec_poster_pdf_from_png(png)
            return png, pdf

        payload = dict(
            labelA=labelA, labelB=labelB,
            seriesA=seriesA, seriesB=seriesB,
            totalA=totalA, totalB=totalB, p_total=p_total, d_total=d_total,
            meanA=meanA, meanB=meanB,
            kpi_days=kpi_days, complianceB=complianceB, coverageB=coverageB,
            d_comp=d_comp, d_cov=d_cov,
            vol_month_df=vol_month,
            sla_month_df=sla_month,
            headline=headline,
            logo_left_bytes=logo_left_bytes,
            logo_right_bytes=logo_right_bytes,
            title=poster_title,
            subtitle=poster_subtitle,
        )

        png_bytes, pdf_bytes = _gen_exec_poster_cached(payload)

        st.image(png_bytes, caption="Preview Poster Executive Summary (layout sudah rapih & tidak overlap)", use_container_width=True)

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "\u2b07\ufe0f Download Poster PNG (WA)",
                data=png_bytes,
                file_name="Poster_Executive_Summary_Analisis.png",
                mime="image/png",
                use_container_width=True
            )
        with d2:
            st.download_button(
                "\u2b07\ufe0f Download Poster PDF (Email/Arsip)",
                data=pdf_bytes,
                file_name="Poster_Executive_Summary_Analisis.pdf",
                mime="application/pdf",
                use_container_width=True
            )


# =====================[ HELPERS PDF ]=====================
# ====================== IMPORTS ======================
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak
)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import io, matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ====================== LOGO ASSET PDF (LOCAL) ======================
# Logo PDF dibaca langsung dari folder yang sama dengan app.py.
# Resolver juga memeriksa current working directory dan nama file secara
# case-insensitive agar tetap stabil saat dijalankan lokal maupun Streamlit Cloud.
try:
    PDF_APP_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception:
    PDF_APP_DIR = os.getcwd()

PDF_LOGO_DANANTARA_NAME = "danantara.png"
PDF_LOGO_ASDP_NAME = "asdp_logo.png"


def _resolve_pdf_asset(filename):
    """Cari file aset PDF secara aman dan kembalikan absolute path-nya."""
    search_dirs = []
    for directory in (PDF_APP_DIR, os.getcwd()):
        directory = os.path.abspath(directory)
        if directory not in search_dirs:
            search_dirs.append(directory)

    # Pencarian nama persis terlebih dahulu.
    for directory in search_dirs:
        candidate = os.path.join(directory, filename)
        if os.path.isfile(candidate):
            return candidate

    # Fallback case-insensitive untuk Linux/Streamlit Cloud.
    target_lower = filename.lower()
    for directory in search_dirs:
        try:
            for entry in os.listdir(directory):
                if entry.lower() == target_lower:
                    candidate = os.path.join(directory, entry)
                    if os.path.isfile(candidate):
                        return candidate
        except OSError:
            continue

    searched = ", ".join(search_dirs)
    raise FileNotFoundError(
        f"Aset PDF '{filename}' tidak ditemukan. Folder yang diperiksa: {searched}"
    )


def _validate_pdf_logo_assets():
    """Pastikan kedua logo tersedia sebelum laporan PDF dibuat."""
    return {
        "danantara": _resolve_pdf_asset(PDF_LOGO_DANANTARA_NAME),
        "asdp": _resolve_pdf_asset(PDF_LOGO_ASDP_NAME),
    }

# ====================== STYLES ======================
_styles = getSampleStyleSheet()
_styles.add(ParagraphStyle(name="CoverTitle", fontName="Helvetica-Bold", fontSize=30, leading=34, alignment=1, spaceAfter=12))
_styles.add(ParagraphStyle(name="CoverSub",   fontName="Helvetica-Bold", fontSize=16, leading=20, alignment=1, spaceAfter=20))
_styles.add(ParagraphStyle(name="HeadingCenter", fontName="Helvetica-Bold", fontSize=20, leading=24, alignment=1, spaceAfter=12, textColor=colors.HexColor("#0f172a")))
_styles.add(ParagraphStyle(name="TOCItem", fontName="Helvetica", fontSize=13, leading=18, alignment=0, leftIndent=0))
_styles.add(ParagraphStyle(name="Narr", fontName="Helvetica", fontSize=11, leading=15, alignment=1, spaceBefore=8, spaceAfter=8))
_styles.add(ParagraphStyle(name="KPI", fontName="Helvetica-Bold", fontSize=12, leading=15, alignment=1, spaceAfter=10))
_styles.add(ParagraphStyle(name="SmallRight", fontName="Helvetica", fontSize=9, alignment=2))

# ====================== HELPERS ======================
def _img_reader(image_source):
    """Buat ImageReader ReportLab dari local path/bytes tanpa menelan error."""
    if isinstance(image_source, (bytes, bytearray)):
        return ImageReader(io.BytesIO(image_source))
    return ImageReader(str(image_source))


def _draw_pdf_logo(canvas, image_path, x, y, width, height, label="Logo"):
    """Gambar logo dengan aspect ratio terjaga dan error yang informatif."""
    try:
        canvas.drawImage(
            _img_reader(image_path),
            x,
            y,
            width=width,
            height=height,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
        return True
    except Exception as exc:
        print(
            f"[PDF LOGO ERROR] {label} gagal dimuat dari '{image_path}': "
            f"{type(exc).__name__}: {exc}"
        )
        return False

def _plot_to_rlimage(fig, w_cm=11, h_cm=6, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return RLImage(buf, width=w_cm*cm, height=h_cm*cm)

def _nice_table(data, colWidths=None, header_bg="#0ea5e9", align="CENTER"):
    tbl = Table(data, colWidths=colWidths, hAlign=align)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor(header_bg)),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,0),11),
        ("ALIGN",(0,0),(-1,0),"CENTER"),
        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
        ("FONTSIZE",(0,1),(-1,-1),10),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    return tbl

def _toc_row(title, page, dots_len=80):
    dots = "." * dots_len
    tbl = Table(
        [[Paragraph(title, _styles["TOCItem"]),
          Paragraph(dots, _styles["TOCItem"]),
          Paragraph(page, _styles["TOCItem"])]],
        colWidths=[12*cm, 11*cm, 1.5*cm],
        hAlign="CENTER"
    )
    tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("FONTSIZE",(0,0),(-1,-1),12),
    ]))
    return tbl

# ====================== NARRASI HELPERS ======================
def _narasi_overview(avg_days, kpi_target_days):
    if avg_days is None: return "Data KEUANGAN tidak tersedia."
    if kpi_target_days is None: return f"Rata-rata SLA KEUANGAN {avg_days:.2f} hari."
    status = "di bawah" if avg_days <= kpi_target_days else "di atas"
    return f"Rata-rata SLA KEUANGAN {avg_days:.2f} hari, {status} target KPI {kpi_target_days:.2f} hari."

def _narasi_top_bottom(series_days):
    if series_days is None or len(series_days)==0: return "Tidak ada data."
    s = pd.Series(series_days).dropna().sort_values()
    if s.empty: return "Tidak ada data."
    lo, hi = s.index[0], s.index[-1]
    return f"Proses tercepat: {lo} ({s.iloc[0]:.2f} hari). Terlama: {hi} ({s.iloc[-1]:.2f} hari)."

def _narasi_tren(df_days):
    desc=[]
    for col in df_days.columns:
        s = df_days[col].dropna()
        if len(s)>=2:
            delta = s.iloc[-1]-s.iloc[0]
            arah = "naik" if delta>0 else ("turun" if delta<0 else "stabil")
            desc.append(f"{col}: {arah} {abs(delta):.2f} hari")
    return "Ringkasan tren: " + "; ".join(desc) if desc else "Tren belum dapat dianalisis."

def _narasi_transaksi(trans_df):
    if trans_df.empty: return "Tidak ada data transaksi."
    peak = trans_df.loc[trans_df["Jumlah"].idxmax()]
    low  = trans_df.loc[trans_df["Jumlah"].idxmin()]
    mean = trans_df["Jumlah"].mean()
    return f"Rata-rata transaksi {mean:.1f}. Tertinggi {peak['Periode']} ({int(peak['Jumlah'])}), terendah {low['Periode']} ({int(low['Jumlah'])})."

# ====================== HEADER & FOOTER ======================
def _first_page(canvas, doc):
    """Logo cover PDF: Danantara kiri, ASDP kanan, dan ASDP utama di tengah."""
    canvas.saveState()
    pw, ph = landscape(A4)

    try:
        logos = _validate_pdf_logo_assets()

        _draw_pdf_logo(
            canvas,
            logos["danantara"],
            1.5 * cm,
            ph - 3.45 * cm,
            4.8 * cm,
            1.55 * cm,
            "Danantara - Cover",
        )

        _draw_pdf_logo(
            canvas,
            logos["asdp"],
            pw - 5.0 * cm,
            ph - 3.65 * cm,
            3.2 * cm,
            2.15 * cm,
            "ASDP - Cover Header",
        )

        _draw_pdf_logo(
            canvas,
            logos["asdp"],
            (pw - 5.4 * cm) / 2,
            ph - 9.35 * cm,
            5.4 * cm,
            4.0 * cm,
            "ASDP - Cover Center",
        )
    finally:
        canvas.restoreState()


def _later_pages(canvas, doc):
    """Logo header dan nomor halaman untuk seluruh halaman setelah cover."""
    canvas.saveState()
    pw, ph = landscape(A4)

    try:
        logos = _validate_pdf_logo_assets()

        _draw_pdf_logo(
            canvas,
            logos["danantara"],
            1.5 * cm,
            ph - 3.45 * cm,
            4.8 * cm,
            1.55 * cm,
            "Danantara - Header",
        )

        _draw_pdf_logo(
            canvas,
            logos["asdp"],
            pw - 5.0 * cm,
            ph - 3.65 * cm,
            3.2 * cm,
            2.15 * cm,
            "ASDP - Header",
        )

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawRightString(
            pw - 1.6 * cm,
            1.05 * cm,
            f"Halaman {doc.page}",
        )
    finally:
        canvas.restoreState()

# ====================== MAIN FUNCTION ======================
def generate_pdf_report_v6(df_ord, selected_periode, periode_col, available_sla_cols, proses_cols, kpi_target_days=None):
    # Fail-fast dengan pesan jelas jika file logo belum ikut ter-deploy.
    _validate_pdf_logo_assets()

    df = df_ord.copy()
    df[periode_col] = df[periode_col].astype(str)
    categories = [str(p) for p in selected_periode]
    df[periode_col] = pd.Categorical(df[periode_col], categories=categories, ordered=True)
    df_filt = df[df[periode_col].notna()].sort_values(periode_col)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=3.6*cm, bottomMargin=2*cm)
    story = []

    # === Cover
    story.append(Spacer(1, 7*cm))
    story.append(Paragraph("LAPORAN SLA VERIFIKASI DOKUMEN PENAGIHAN PT ASDP INDONESIA FERRY (PERSERO)", _styles["CoverTitle"]))
    if selected_periode:
        story.append(Paragraph(f"PERIODE: {str(selected_periode[0]).upper()} \u2013 {str(selected_periode[-1]).upper()}", _styles["CoverSub"]))
    story.append(PageBreak())

    # === TOC
    story.append(Paragraph("DAFTAR ISI", _styles["HeadingCenter"]))
    story.append(Spacer(1,0.6*cm))
    toc_map=[("OVERVIEW","3"),("SLA PER PROSES","4"),("SLA PER JENIS TRANSAKSI","5"),
             ("TREN SLA","6"),("JUMLAH TRANSAKSI","8"),("KESIMPULAN","9")]
    for t,p in toc_map:
        story.append(_toc_row(t,p,dots_len=70))
        story.append(Spacer(1,0.2*cm))
    story.append(PageBreak())

    # === Page 3: Overview
    story.append(Paragraph("OVERVIEW", _styles["HeadingCenter"]))
    total_trans = len(df_filt)
    avg_keu_days = None
    if "KEUANGAN" in df_filt.columns:
        avg_keu_days = float((df_filt["KEUANGAN"].mean()/86400.0).round(2))
    kpi_lines = [f"<b>JUMLAH TRANSAKSI</b>: {total_trans:,}"]
    if avg_keu_days: kpi_lines.append(f"<b>RATA-RATA SLA KEUANGAN</b>: {avg_keu_days:.2f} HARI")
    if kpi_target_days: kpi_lines.append(f"<b>TARGET KPI</b>: {kpi_target_days:.2f} HARI")
    story.append(Paragraph("<br/>".join(kpi_lines), _styles["KPI"]))
    if "KEUANGAN" in df_filt.columns:
        df_keu=df_filt.groupby(periode_col)["KEUANGAN"].mean().reindex(categories).reset_index()
        df_keu["SLA (hari)"]=(df_keu["KEUANGAN"]/86400.0).round(2)
        df_keu.rename(columns={periode_col:"Periode"}, inplace=True)
        tbl=_nice_table([["Periode","SLA (hari)"]]+df_keu[["Periode","SLA (hari)"]].astype(str).values.tolist(), colWidths=[4*cm,4*cm])
        fig,ax=plt.subplots(figsize=(7,4))
        ax.plot(df_keu["Periode"],df_keu["SLA (hari)"],marker="o",color="#0ea5e9")
        ax.tick_params(axis="x",rotation=45)
        if kpi_target_days: ax.axhline(y=kpi_target_days,ls="--",c="r")
        chart=_plot_to_rlimage(fig,w_cm=13,h_cm=7)
        pair=Table([[chart,tbl]],colWidths=[13*cm,8*cm],hAlign="CENTER")
        pair.setStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
        story.append(pair)
        story.append(Spacer(1,0.5*cm))
    story.append(PageBreak())
    
    # === Page 4: SLA PER PROSES
    story.append(Paragraph("SLA PER PROSES", _styles["HeadingCenter"]))
    valid_proc=[c for c in (proses_cols or []) if c in df_filt.columns]
    if valid_proc:
        dfp=(df_filt[valid_proc].mean()/86400.0).round(2)
        tbl=_nice_table([["Proses","SLA (hari)"]]+[[i,f"{v:.2f}"] for i,v in dfp.items()])
        fig,ax=plt.subplots(figsize=(7,4))
        ax.bar(dfp.index,dfp.values,color="#0ea5e9")
        ax.tick_params(axis="x",rotation=45)
        chart=_plot_to_rlimage(fig,w_cm=13,h_cm=7)

        # Layout \u2192 Grafik kiri, tabel kanan, sejajar atas
        pair=Table([[chart,tbl]],colWidths=[13*cm,8*cm],hAlign="CENTER")
        pair.setStyle([
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("VALIGN",(0,0),(-1,-1),"TOP"),   # <<< ini penting: sejajarkan ke atas
        ])
        story.append(pair)

        story.append(Spacer(1,0.5*cm))
        narasi_tbl=Table(
            [[Paragraph(_narasi_top_bottom(dfp),_styles["Narr"])]],
            colWidths=[21*cm],
            hAlign="CENTER"
        )
        story.append(narasi_tbl)
    story.append(PageBreak())

    # === Page 5: SLA PER JENIS TRANSAKSI
    story.append(Paragraph("SLA PER JENIS TRANSAKSI", _styles["HeadingCenter"]))
    jns_candidates=["JENIS_TRANSAKSI","JENIS TRANSAKSI","Jenis Transaksi","Jenis_Transaksi","jenis_transaksi"]
    jns_col=next((c for c in jns_candidates if c in df_filt.columns),None)
    main_sla="KEUANGAN" if "KEUANGAN" in df_filt.columns else (available_sla_cols[0] if available_sla_cols else None)
    if jns_col and main_sla:
        dfj=df_filt.groupby(jns_col)[main_sla].agg(["count","mean"]).reset_index()
        dfj["SLA (hari)"]=(dfj["mean"]/86400.0).round(2)
        dfj=dfj.sort_values("SLA (hari)",ascending=False)
        tbl=_nice_table([["Jenis Transaksi","Jumlah","SLA (hari)"]]+dfj[[jns_col,"count","SLA (hari)"]].astype(str).values.tolist())
        story.append(tbl)
        story.append(Spacer(1,0.5*cm))
        story.append(Paragraph(_narasi_top_bottom(pd.Series(dfj["SLA (hari)"].values,index=dfj[jns_col].values)),_styles["Narr"]))
    story.append(PageBreak())

    # === Page 6: TREN SLA (adaptif)
    story.append(Paragraph("TREN SLA", _styles["HeadingCenter"]))
    valid_sla=[c for c in (available_sla_cols or []) if c in df_filt.columns]
    if valid_sla:
        trend=df_filt.groupby(periode_col)[valid_sla].mean().reindex(categories)
        trend_days=(trend/86400.0).round(2)

        if len(valid_sla) <= 3:
            # --- Layout A: grafik kiri, tabel kanan ---
            data=[["Periode"]+valid_sla]+trend_days.reset_index().astype(str).values.tolist()
            tbl=_nice_table(data, colWidths=[4*cm]+[4*cm]*len(valid_sla))
            fig,ax=plt.subplots(figsize=(7,4))
            for c in valid_sla:
                ax.plot(trend_days.index.astype(str),trend_days[c],marker="o",label=c)
            ax.legend(fontsize=8)
            ax.tick_params(axis="x",rotation=45)
            chart=_plot_to_rlimage(fig,w_cm=13,h_cm=7)
            pair=Table([[chart,tbl]],colWidths=[13*cm,8*cm],hAlign="CENTER")
            pair.setStyle([
                ("LEFTPADDING",(0,0),(-1,-1),0),
                ("RIGHTPADDING",(0,0),(-1,-1),0),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
            ])
            story.append(pair)

        else:
            # --- Layout B: grafik atas, tabel bawah ---
            fig,ax=plt.subplots(figsize=(10,4))
            for c in valid_sla:
                ax.plot(trend_days.index.astype(str),trend_days[c],marker="o",label=c)
            ax.legend(fontsize=8,ncol=2)
            ax.tick_params(axis="x",rotation=45)
            story.append(_plot_to_rlimage(fig,w_cm=21,h_cm=8))
            story.append(Spacer(1,0.4*cm))

            data=[["Periode"]+valid_sla]+trend_days.reset_index().astype(str).values.tolist()
            col_w=[4*cm]+[ (21-4)/len(valid_sla)*cm ]*len(valid_sla)
            tbl=_nice_table(data, colWidths=col_w)
            tbl.setStyle([
                ("FONTSIZE",(0,0),(-1,-1),9),
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ])
            story.append(tbl)

        # --- Narasi ---
        story.append(Spacer(1,0.5*cm))
        narasi_tbl=Table([[Paragraph(_narasi_tren(trend_days),_styles["Narr"])]],
                         colWidths=[21*cm], hAlign="CENTER")
        story.append(narasi_tbl)

    story.append(PageBreak())

    # === Page 7: JUMLAH TRANSAKSI
    story.append(Paragraph("JUMLAH TRANSAKSI", _styles["HeadingCenter"]))
    trans=df_filt.groupby(periode_col).size().reindex(categories).reset_index(name="Jumlah").rename(columns={periode_col:"Periode"})
    tbl=_nice_table([["Periode","Jumlah"]]+trans.astype(str).values.tolist())
    fig,ax=plt.subplots(figsize=(7,4))
    ax.bar(trans["Periode"],trans["Jumlah"],color="#14b8a6"); ax.tick_params(axis="x",rotation=45)
    chart=_plot_to_rlimage(fig,w_cm=13,h_cm=7)
    pair=Table([[chart,tbl]],colWidths=[13*cm,8*cm],hAlign="CENTER")
    pair.setStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
    story.append(pair)
    story.append(Spacer(1,0.5*cm))
    narasi_tbl=Table([[Paragraph(_narasi_transaksi(trans),_styles["Narr"])]],colWidths=[21*cm],hAlign="CENTER")
    story.append(narasi_tbl)
    story.append(PageBreak())

    # === Page 8: KESIMPULAN
    story.append(Paragraph("KESIMPULAN", _styles["HeadingCenter"]))

    # rangkum otomatis dari halaman-halaman sebelumnya
    summary_parts = []
    if "KEUANGAN" in df_filt.columns:
        summary_parts.append(_narasi_overview(avg_keu_days, kpi_target_days))
    if 'valid_proc' in locals() and valid_proc:
        dfp_days = (df_filt[valid_proc].mean()/86400.0).round(2)
        summary_parts.append(_narasi_top_bottom(dfp_days))
    if 'valid_sla' in locals() and valid_sla:
        trend_days_all = (df_filt.groupby(periode_col)[valid_sla].mean()/86400.0).round(2).reindex(categories)
        summary_parts.append(_narasi_tren(trend_days_all))
    # transaksi
    summary_parts.append(_narasi_transaksi(trans.copy()))

    story.append(Paragraph(" ".join(summary_parts), _styles["Narr"]))

    # rekomendasi eye-catching (blok lebar)
    recs = [
        "Pertahankan proses yang sudah efisien.",
        "Prioritaskan perbaikan pada SLA terlama.",
        "Analisis akar masalah pada periode outlier.",
        "Optimalkan SDM saat puncak transaksi.",
        "Perkuat monitoring KPI (real-time alert).",
        "Evaluasi otomasi pada aktivitas manual."
    ]
    rec_tbl = _nice_table(
        [["REKOMENDASI PRIORITAS"]] + [[f"\u2022 {r}"] for r in recs],
        colWidths=[25.5*cm],
        header_bg="#0ea5e9",
        align="CENTER"
    )
    story.append(Spacer(1, 0.6*cm))
    story.append(rec_tbl)

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("Laporan ini dihasilkan otomatis oleh SLA Dashboard.", _styles["SmallRight"]))

    # Build PDF
    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_pages)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# ====================== STREAMLIT TAB: PDF v6 ======================
@st.cache_data(show_spinner=False, max_entries=6)
def _pdf_report_cached(source_version: str, periods: tuple, kpi_value, _filtered_df,
                       _period_col, _available_sla, _process_cols):
    """Generate full PDF only when report tab opens; same inputs reuse bytes."""
    return generate_pdf_report_v6(
        df_ord=_filtered_df,
        selected_periode=list(periods),
        periode_col=_period_col,
        available_sla_cols=list(_available_sla),
        proses_cols=list(_process_cols),
        kpi_target_days=kpi_value,
    )


if (not _SLA_LAZY_TABS) or (bool(getattr(tab_report, "open", False)) and bool(getattr(tab_pdf, "open", False))):
    with tab_pdf:
        st.subheader("\U0001f4d1 Laporan SLA")

        try:
            pdf_bytes = _pdf_report_cached(
                _sla_source_version,
                tuple(selected_periode),
                target_kpi_hari if 'target_kpi_hari' in globals() else None,
                df_filtered,
                periode_col,
                tuple(available_sla_cols),
                tuple(proses_grafik_cols),
            )

            st.download_button(
                "\u2b07\ufe0f Download Laporan PDF",
                data=pdf_bytes,
                file_name="LAPORAN_SLA_VERIFIKASI_DOKUMEN_PENAGIHAN.pdf",
                mime="application/pdf"
            )
            st.success("PDF siap diunduh \u2705")
        except Exception as e:
            import traceback
            st.error(f"Gagal membuat PDF: {type(e).__name__}: {e}")
            traceback.print_exc()

# ==========================================================
#  SELA v11 Core Intelligence (v10 voice & avatar preserved)
#  - Avatar wanita natural (ringan, CSS/SVG)
#  - Voice input via Web Speech API
#  - Voice output via Speech Synthesis
#  - Jawaban natural berbasis data aktif dashboard
# ==========================================================
import streamlit.components.v1 as components
import json
import pandas as pd
import numpy as np
import re


def _format_num_id(val):
    try:
        v = float(val)
        if abs(v) >= 1000:
            return f"{v:,.0f}".replace(",", ".")
        if float(v).is_integer():
            return str(int(v))
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(val)


def _format_days_text(days):
    try:
        d = float(days)
    except Exception:
        return "0 hari"
    if d < 0:
        d = 0
    total_seconds = int(round(d * 86400))
    dd = total_seconds // 86400
    hh = (total_seconds % 86400) // 3600
    mm = (total_seconds % 3600) // 60
    if dd > 0:
        return f"{dd} hari {hh} jam {mm} menit"
    if hh > 0:
        return f"{hh} jam {mm} menit"
    return f"{mm} menit"


def _safe_mode(series):
    try:
        mode = series.mode(dropna=True)
        return None if mode.empty else str(mode.iloc[0])
    except Exception:
        return None


def _choose_col(cols, candidates):
    norm = {str(c).strip().upper(): c for c in cols}
    for cand in candidates:
        if cand.upper() in norm:
            return norm[cand.upper()]
    for c in cols:
        cu = str(c).strip().upper()
        if any(k.upper() in cu for k in candidates):
            return c
    return None


def _sela_month_year_from_period(value):
    """Same canonical month/year as the global filter, including Indonesian labels."""
    parsed = parse_period_label_to_timestamp(value)
    empty = {"year": None, "month": None, "month_name": None, "month_key": None}
    if pd.isna(parsed):
        return empty
    months = ("Januari", "Februari", "Maret", "April", "Mei", "Juni",
              "Juli", "Agustus", "September", "Oktober", "November", "Desember")
    year, month = int(parsed.year), int(parsed.month)
    return {
        "year": str(year), "month": month, "month_name": months[month - 1],
        "month_key": f"{year:04d}-{month:02d}",
    }


def _sela_valid_average_days(values):
    """Return null for no valid SLA; never imply zero duration for missing values."""
    series = pd.to_numeric(values, errors="coerce")
    if not series.notna().any():
        return None
    return round(float(series.mean()) / 86400.0, 10)


@st.cache_data(show_spinner=False, max_entries=6)
def _sela_history_summary_cached(source_version: str, period_col: str, _raw_df: pd.DataFrame):
    """Monthly/annual historical aggregates; only runs when SELA is opened.

    Caching is keyed on the same file-version used by the dashboard. The raw frame
    is excluded from the cache hash since the source version invalidates it.
    No vendor names or transaction-level records are added to this cache output.
    """
    empty = {"history_month_stats": [], "history_year_stats": [], "total_rows": 0}
    if _raw_df is None or _raw_df.empty or period_col not in _raw_df.columns:
        return empty

    if "PERIODE_DATETIME" in _raw_df.columns:
        timestamps = pd.to_datetime(_raw_df["PERIODE_DATETIME"], errors="coerce")
    else:
        raw_labels = _raw_df[period_col].astype(str)
        lookup = {name: parse_period_label_to_timestamp(name) for name in raw_labels.unique()}
        timestamps = pd.to_datetime(raw_labels.map(lookup), errors="coerce")

    valid = timestamps.notna()
    if not bool(valid.any()):
        return empty

    months = timestamps.loc[valid].dt.strftime("%Y-%m")
    data = pd.DataFrame({"month_key": months.to_numpy()}, index=_raw_df.index[valid])
    stage_columns = [c for c in ("FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU")
                     if c in _raw_df.columns]
    for stage in stage_columns:
        # Reuse the same parser as the dashboard, so SLA numbers do not diverge.
        data[stage] = pd.to_numeric(_raw_df.loc[valid, stage].map(parse_sla), errors="coerce")

    month_rows = []
    for month_key, group in data.groupby("month_key", sort=True):
        row = {"month_key": str(month_key), "year": str(month_key)[:4],
               "month": int(str(month_key)[5:7]), "count": int(len(group))}
        for stage in stage_columns:
            good = group[stage].dropna()
            row[stage] = round(float(good.mean()) / 86400.0, 10) if len(good) else None
            row[f"{stage}_valid"] = int(len(good))
            row[f"{stage}_sum_seconds"] = float(good.sum())
        month_rows.append(row)

    # Aggregate from unrounded seconds, never average month averages.
    year_rows = []
    for year, group in data.groupby(data["month_key"].str[:4], sort=True):
        present_months = sorted(int(month[5:7]) for month in group["month_key"].unique())
        row = {"year": str(year), "count": int(len(group)),
               "months_present": present_months, "latest_month": max(present_months),
               "month_count": len(present_months)}
        for stage in stage_columns:
            good = group[stage].dropna()
            row[stage] = round(float(good.mean()) / 86400.0, 10) if len(good) else None
            row[f"{stage}_valid"] = int(len(good))
        year_rows.append(row)
    return {"history_month_stats": month_rows,
            "history_year_stats": year_rows,
            "total_rows": int(len(data))}


def _sela_rank_groups(df, name_col, limit=15):
    """Vectorized top groups: avoids Python iteration over 90k unique requests."""
    if name_col is None or name_col not in df.columns or df.empty:
        return []
    if "TOTAL WAKTU" in df.columns:
        aggregate = df.groupby(name_col, dropna=False, sort=False)["TOTAL WAKTU"].agg(
            ["size", "mean"]
        ).reset_index()
        aggregate["_avg"] = aggregate["mean"] / 86400.0
        aggregate = aggregate.sort_values(["_avg", "size"], ascending=[False, False],
                                          kind="stable", na_position="last").head(limit)
    else:
        aggregate = df.groupby(name_col, dropna=False, sort=False).size().reset_index(name="size")
        aggregate = aggregate.sort_values("size", ascending=False, kind="stable").head(limit)
    results = []
    for row in aggregate.to_dict("records"):
        entry = {"name": str(row[name_col]), "count": int(row["size"])}
        if "_avg" in row:
            entry["avg_sla_days"] = round(float(row["_avg"]), 10) if pd.notna(row["_avg"]) else None
        results.append(entry)
    return results


def _sela_grouped_process_snapshot(df, period_key, name_col, sla_cols, limit):
    """Materialize only the highest-volume group summaries via vectorized groupby."""
    if period_key not in df.columns or name_col not in df.columns:
        return []
    relevant = df.dropna(subset=[period_key])
    if relevant.empty:
        return []
    keys = [period_key, name_col]
    grouped = relevant.groupby(keys, dropna=False, sort=False)
    amounts = grouped.size().rename("_count").to_frame()
    if sla_cols:
        means = grouped[sla_cols].mean()
        amounts = amounts.join(means)
    amounts = amounts.sort_values("_count", ascending=False, kind="stable").head(limit).reset_index()
    results = []
    for row in amounts.to_dict("records"):
        item = {"name": str(row[name_col]), "count": int(row["_count"])}
        if period_key == "_year_sela":
            item["year"] = str(row[period_key])
        else:
            item["month_key"] = str(row[period_key])
            item.update(_sela_month_year_from_period(row[period_key]))
        for c in sla_cols:
            v = row.get(c)
            item[c] = round(float(v) / 86400.0, 10) if v is not None and pd.notna(v) else None
        results.append(item)
    return results


def build_sela_payload(df_filtered, periode_col: str):
    payload = {
        "meta": {
            "assistant_name": "SELA",
            "version": "v13-boardroom",
        },
        "metrics": {},
        "period_stats": [],
        "year_stats": [],
        "transaction_stats": [],
        "vendor_stats": [],
        "nomor_stats": [],
        "proses_stats": [],
        "process_year_stats": [],
        "process_month_stats": [],
        "process_period_stats": [],
        "process_transaction_year_stats": [],
        "process_transaction_month_stats": [],
        "process_vendor_year_stats": [],
        "process_vendor_month_stats": [],
        "sample_records": [],
        "history_month_stats": [],
        "history_year_stats": [],
        "history_total_rows": 0,
    }

    if df_filtered is None or not isinstance(df_filtered, pd.DataFrame) or df_filtered.empty:
        payload["meta"]["status"] = "empty"
        return payload

    df = df_filtered.copy()
    cols = list(df.columns)
    trx_col = _choose_col(cols, ["JENIS TRANSAKSI", "JENIS_TRANSAKSI", "TRANSAKSI"])
    vendor_col = _choose_col(cols, ["NAMA VENDOR", "VENDOR", "NAMA CABANG", "CABANG"])
    nomor_col = _choose_col(cols, ["NOMOR PERMOHONAN", "NO PERMOHONAN", "NO. PERMOHONAN", "NOMOR REQUEST", "REQUEST NUMBER"])
    nilai_col = _choose_col(cols, ["NILAI TRANSAKSI", "NILAI", "AMOUNT", "TOTAL NILAI"])

    sla_candidates = ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]
    sla_cols = [c for c in sla_candidates if c in df.columns]

    for c in sla_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # convert SLA to days helper series
    days_map = {}
    for c in sla_cols:
        days_map[c] = df[c] / 86400.0

    total_rows = int(len(df))
    total_sla_average = days_map.get("TOTAL WAKTU", pd.Series(dtype=float)).mean()
    total_sla_days = float(total_sla_average) if pd.notna(total_sla_average) else None
    period_values = df[periode_col].dropna().astype(str).tolist() if periode_col in df.columns else []
    period_first = period_values[0] if period_values else "-"
    period_last = period_values[-1] if period_values else "-"
    period_mode = _safe_mode(df[periode_col].astype(str)) if periode_col in df.columns else None

    # period stats
    if periode_col in df.columns:
        grp_p = df.groupby(periode_col, dropna=False)
        period_rows = []
        for p, g in grp_p:
            row = {
                "periode": str(p),
                "count": int(len(g)),
            }
            _my = _sela_month_year_from_period(p)
            row.update(_my)
            if "TOTAL WAKTU" in g.columns:
                row["avg_sla_days"] = round(float(pd.to_numeric(g["TOTAL WAKTU"], errors="coerce").mean() / 86400.0), 10) if len(g) else 0
            period_rows.append(row)
        # Chronological ordering is required for accurate growth and last period.
        period_rows.sort(key=lambda item: (item.get("month_key") or "9999-99", item["periode"]))
        payload["period_stats"] = period_rows

        # derive years
        year_map = {}
        for r in period_rows:
            m = re.search(r"(20\d{2})", r["periode"])
            if m:
                y = m.group(1)
                year_map.setdefault(y, {"year": y, "count": 0, "sum_sla": 0.0, "n_sla": 0})
                year_map[y]["count"] += r["count"]
        if year_map:
            # use raw df for better avg
            tmp = df.copy()
            tmp["_year_sela"] = tmp[periode_col].astype(str).str.extract(r"(20\d{2})")
            for y, g in tmp.dropna(subset=["_year_sela"]).groupby("_year_sela"):
                item = year_map.setdefault(str(y), {"year": str(y), "count": 0, "sum_sla": 0.0, "n_sla": 0})
                item["count"] = int(len(g))
                if "TOTAL WAKTU" in g.columns:
                    item["avg_sla_days"] = round(float(pd.to_numeric(g["TOTAL WAKTU"], errors="coerce").mean() / 86400.0), 10)
            payload["year_stats"] = sorted(year_map.values(), key=lambda x: x["year"])

        # intelligent process aggregates for SELA natural filtering.
        def _sela_process_avg_row(g):
            item = {"count": int(len(g))}
            for c in sla_cols:
                if c in g.columns:
                    s = pd.to_numeric(g[c], errors="coerce")
                    item[c] = round(float(s.mean() / 86400.0), 10) if s.notna().any() else None
            return item

        tmp_proc = df.copy()
        tmp_proc["_year_sela"] = tmp_proc[periode_col].astype(str).str.extract(r"(20\d{2})")
        # Fast vectorized lookup: parse each distinct label once, not each Excel row.
        _labels_sela = tmp_proc[periode_col].astype(str)
        _period_lookup_sela = {
            label: _sela_month_year_from_period(label) for label in _labels_sela.unique()
        }
        tmp_proc["_month_key_sela"] = _labels_sela.map(
            {k: v["month_key"] for k, v in _period_lookup_sela.items()}
        )
        tmp_proc["_month_name_sela"] = _labels_sela.map(
            {k: v["month_name"] for k, v in _period_lookup_sela.items()}
        )
        tmp_proc["_month_num_sela"] = _labels_sela.map(
            {k: v["month"] for k, v in _period_lookup_sela.items()}
        )

        process_year_rows = []
        for y, g in tmp_proc.dropna(subset=["_year_sela"]).groupby("_year_sela"):
            item = {"year": str(y)}
            item.update(_sela_process_avg_row(g))
            process_year_rows.append(item)
        payload["process_year_stats"] = sorted(process_year_rows, key=lambda x: x["year"])

        process_period_rows = []
        for p, g in df.groupby(periode_col, dropna=False):
            item = {"periode": str(p)}
            item.update(_sela_month_year_from_period(p))
            item.update(_sela_process_avg_row(g))
            process_period_rows.append(item)
        payload["process_period_stats"] = sorted(
            process_period_rows, key=lambda item: (item.get("month_key") or "9999-99", item["periode"])
        )

        process_month_rows = []
        month_ready = tmp_proc.dropna(subset=["_month_key_sela"]).copy()
        if not month_ready.empty:
            for mk, g in month_ready.groupby("_month_key_sela", dropna=False):
                item = {
                    "month_key": str(mk),
                    "year": str(g["_year_sela"].dropna().iloc[0]) if g["_year_sela"].notna().any() else None,
                    "month": int(g["_month_num_sela"].dropna().iloc[0]) if g["_month_num_sela"].notna().any() else None,
                    "month_name": str(g["_month_name_sela"].dropna().iloc[0]) if g["_month_name_sela"].notna().any() else None,
                    "periode": str(g[periode_col].dropna().astype(str).iloc[0]) if g[periode_col].notna().any() else str(mk),
                }
                item.update(_sela_process_avg_row(g))
                process_month_rows.append(item)
        payload["process_month_stats"] = sorted(process_month_rows, key=lambda x: x.get("month_key") or "")

        if trx_col and trx_col in tmp_proc.columns:
            payload["process_transaction_year_stats"] = _sela_grouped_process_snapshot(
                tmp_proc, "_year_sela", trx_col, sla_cols, limit=500)
            payload["process_transaction_month_stats"] = _sela_grouped_process_snapshot(
                tmp_proc, "_month_key_sela", trx_col, sla_cols, limit=800)

        if vendor_col and vendor_col in tmp_proc.columns:
            payload["process_vendor_year_stats"] = _sela_grouped_process_snapshot(
                tmp_proc, "_year_sela", vendor_col, sla_cols, limit=500)
            payload["process_vendor_month_stats"] = _sela_grouped_process_snapshot(
                tmp_proc, "_month_key_sela", vendor_col, sla_cols, limit=800)

    # Top lists maintain their existing 15-item maximum, now using vectorized aggregation.
    payload["transaction_stats"] = _sela_rank_groups(df, trx_col, limit=15)
    payload["vendor_stats"] = _sela_rank_groups(df, vendor_col, limit=15)
    payload["nomor_stats"] = _sela_rank_groups(df, nomor_col, limit=15)

    # Bottleneck ranks operational stages only; TOTAL WAKTU remains accessible
    # for queries but is never itself called a workflow bottleneck.
    proses = []
    operational_stages = {"FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN"}
    for c in ["FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU"]:
        if c in df.columns:
            average = _sela_valid_average_days(df[c])
            valid_rows = int(pd.to_numeric(df[c], errors="coerce").notna().sum())
            proses.append({"name": c, "avg_sla_days": average,
                           "valid_count": valid_rows, "is_stage": c in operational_stages})
    proses.sort(key=lambda item: (item["avg_sla_days"] is None,
                                 -(item["avg_sla_days"] or 0)))
    payload["proses_stats"] = proses

    # sample records \u06a9\u0648\u0686\u06a9
    sample_cols = [c for c in [periode_col, nomor_col, trx_col, vendor_col, "FUNGSIONAL", "VENDOR", "KEUANGAN", "PERBENDAHARAAN", "TOTAL WAKTU", nilai_col] if c]
    sample_cols = [c for c in sample_cols if c in df.columns]
    if sample_cols:
        sdf = df[sample_cols].head(80).copy()
        for c in sla_cols:
            if c in sdf.columns:
                sdf[c] = pd.to_numeric(sdf[c], errors="coerce").fillna(0).div(86400).round(2)
        payload["sample_records"] = json.loads(sdf.to_json(orient="records", force_ascii=False))

    last_count = payload["period_stats"][-1]["count"] if payload["period_stats"] else total_rows
    prev_count = payload["period_stats"][-2]["count"] if len(payload["period_stats"]) > 1 else None
    growth = None
    if prev_count and prev_count != 0:
        growth = round(((last_count - prev_count) / prev_count) * 100, 2)

    top_trx = payload["transaction_stats"][0] if payload["transaction_stats"] else None
    top_vendor = payload["vendor_stats"][0] if payload["vendor_stats"] else None
    top_nomor = payload["nomor_stats"][0] if payload["nomor_stats"] else None
    bottleneck = next((row for row in payload["proses_stats"]
                       if row.get("is_stage") and row.get("valid_count", 0) > 0
                       and row["avg_sla_days"] is not None), None)
    total_nilai = None
    if nilai_col and nilai_col in df.columns:
        try:
            total_nilai = float(pd.to_numeric(df[nilai_col], errors="coerce").sum())
        except Exception:
            total_nilai = None

    payload["metrics"] = {
        "transaction_count": total_rows,
        "avg_sla_days": round(total_sla_days, 10) if total_sla_days is not None else None,
        "period_first": str(period_rows[0]["periode"]) if payload["period_stats"] else (period_first or "-"),
        "period_last": str(period_rows[-1]["periode"]) if payload["period_stats"] else (period_last or "-"),
        "period_mode": period_mode or "-",
        "latest_growth_pct": growth,
        "latest_count": last_count,
        "prev_count": prev_count,
        "top_transaction": top_trx,
        "top_vendor": top_vendor,
        "top_nomor": top_nomor,
        "bottleneck": bottleneck,
        "total_nilai": total_nilai,
        "currency_label": "Rp" if total_nilai is not None else None,
    }
    payload["meta"].update({
        "trx_col": trx_col,
        "vendor_col": vendor_col,
        "nomor_col": nomor_col,
        "periode_col": periode_col,
        "nilai_col": nilai_col,
        "status": "ok",
    })
    return payload



@st.cache_data(show_spinner=False, max_entries=8)
def _sela_active_payload_cached(source_version: str, selected_keys: tuple,
                                period_col: str, _active_df: pd.DataFrame):
    """Re-use SELA v11 aggregates on repeated tab toggles and widget changes."""
    return build_sela_payload(_active_df, period_col)


def render_sela_widget(df_filtered, periode_col: str,
                       source_version: str = "", period_keys: tuple = (),
                       raw_history: pd.DataFrame | None = None):
    if source_version:
        payload = _sela_active_payload_cached(source_version, tuple(period_keys),
                                              periode_col, df_filtered)
    else:
        payload = build_sela_payload(df_filtered, periode_col)

    if raw_history is not None and source_version:
        historical = _sela_history_summary_cached(source_version, periode_col, raw_history)
        payload["history_month_stats"] = historical["history_month_stats"]
        payload["history_year_stats"] = historical["history_year_stats"]
        payload["history_total_rows"] = historical["total_rows"]

    # Prevent Excel-derived strings from terminating the inline <script> element.
    # Text is also rendered using DOM textContent in addMsg, never as HTML.
    data_json = json.dumps(payload, ensure_ascii=False)
    data_json = (data_json.replace("<", "\\u003c")
                         .replace(">", "\\u003e")
                         .replace("&", "\\u0026")
                         .replace("\u2028", "\\u2028")
                         .replace("\u2029", "\\u2029"))

    html = """
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    :root{
      --bg1:#07111f;
      --bg2:#0b2034;
      --bg3:#17314a;
      --card:rgba(255,255,255,.08);
      --line:rgba(255,255,255,.14);
      --text:#eef6ff;
      --muted:#a8bdd2;
      --accent:#34d399;
      --accent2:#60a5fa;
      --pink:#f472b6;
      --warning:#fbbf24;
    }
    *{box-sizing:border-box}
    body{margin:0;background:transparent;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:var(--text)}
    .sela-root{
      width:100%;
      min-height:1240px;
      border-radius:28px;
      border:1px solid rgba(255,255,255,.08);
      background:
        radial-gradient(circle at top left, rgba(96,165,250,.18), transparent 30%),
        radial-gradient(circle at bottom right, rgba(52,211,153,.18), transparent 28%),
        linear-gradient(145deg,var(--bg2),var(--bg1) 56%,#081321 100%);
      box-shadow:0 24px 64px rgba(0,0,0,.45);
      overflow:hidden;
    }
    .head{display:flex;justify-content:space-between;align-items:flex-start;padding:22px 24px 16px 24px;border-bottom:1px solid var(--line);gap:16px;flex-wrap:wrap}
    .brand{display:flex;gap:14px;align-items:center;min-width:0}
    .logo{
      width:56px;height:56px;border-radius:18px;background:linear-gradient(135deg,#60a5fa,#34d399);display:flex;align-items:center;justify-content:center;
      font-weight:800;font-size:26px;color:#fff;box-shadow:0 12px 24px rgba(52,211,153,.28)
    }
    .title{font-size:28px;font-weight:800;line-height:1.1;margin:0}
    .subtitle{color:var(--muted);font-size:15px;max-width:720px;margin-top:6px}
    .head-tags{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
    .tag{padding:10px 16px;border:1px solid rgba(96,165,250,.4);border-radius:999px;background:rgba(9,31,51,.72);font-size:12px;font-weight:700;color:#d7ebff;letter-spacing:.03em}
    .content{padding:22px;display:grid;grid-template-columns:minmax(300px,340px) minmax(0,1fr);gap:20px;align-items:start}
    .panel{background:var(--card);border:1px solid var(--line);border-radius:24px;backdrop-filter:blur(10px)}
    .avatar-panel{padding:18px;display:flex;flex-direction:column;gap:14px;min-height:960px}
    .hero-stage{position:relative;flex:1;min-height:500px;border-radius:24px;background:linear-gradient(180deg,rgba(96,165,250,.12),rgba(255,255,255,.02));overflow:hidden;border:1px solid rgba(255,255,255,.08)}
    .hero-stage::before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 50% 28%, rgba(96,165,250,.18), transparent 42%),radial-gradient(circle at 50% 80%, rgba(52,211,153,.15), transparent 30%);pointer-events:none}
    .hero-stage::after{content:"";position:absolute;inset:14px;border-radius:22px;border:1px solid rgba(255,255,255,.06);pointer-events:none}
    .avatar-wrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:20px}
    .female-avatar{position:relative;width:min(100%,290px);height:min(100%,430px);display:flex;align-items:center;justify-content:center;transition:transform .18s ease, filter .18s ease}
    .avatar-halo{position:absolute;inset:auto 50% 12px auto;transform:translateX(50%);width:230px;height:230px;border-radius:50%;background:radial-gradient(circle, rgba(52,211,153,.16), transparent 68%);filter:blur(10px);animation:pulse 3.8s ease-in-out infinite}
    .avatar-card{position:relative;width:100%;height:100%;border-radius:28px;overflow:hidden;background:linear-gradient(180deg, rgba(7,17,31,.85), rgba(9,20,37,.98));box-shadow:0 18px 50px rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.08)}
    .avatar-photo{width:100%;height:100%;object-fit:cover;display:block;filter:saturate(1.05) contrast(1.04) brightness(1.01)}
    .lip-sync-mouth{position:absolute;left:50%;top:49.7%;transform:translate(-50%,-50%) scaleY(var(--mouth-open,.20)) scaleX(var(--mouth-wide,1));width:43px;height:20px;border-radius:0 0 26px 26px;background:radial-gradient(ellipse at 50% 16%,#f2a0b2 0 8%,#b94b66 22%,#64172d 72%);box-shadow:0 2px 8px rgba(0,0,0,.30), inset 0 3px 2px rgba(255,218,225,.34), inset 0 -7px 8px rgba(50,4,20,.55);opacity:.82;z-index:3;transition:transform .055s linear, width .08s linear, opacity .12s ease;will-change:transform,width}
    .lip-sync-mouth::before{content:"";position:absolute;left:4px;right:4px;top:-2px;height:5px;border-radius:999px;background:linear-gradient(90deg,transparent,#c9697c,transparent);opacity:.82}
    .lip-sync-mouth::after{content:"";position:absolute;left:9px;right:9px;top:5px;height:3px;border-radius:999px;background:rgba(255,230,235,.55);filter:blur(.2px)}
    .female-avatar.speaking .lip-sync-mouth{opacity:.97}
    .female-avatar.listening .lip-sync-mouth{--mouth-open:.16;--mouth-wide:.92;opacity:.74}
    .avatar-overlay{position:absolute;inset:0;background:linear-gradient(180deg, rgba(7,17,31,.05) 0%, rgba(7,17,31,.00) 35%, rgba(7,17,31,.35) 100%)}
    .avatar-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(96,165,250,.07) 1px, transparent 1px),linear-gradient(90deg, rgba(96,165,250,.07) 1px, transparent 1px);background-size:28px 28px;mask-image:linear-gradient(to bottom, rgba(0,0,0,.0), rgba(0,0,0,.8) 25%, rgba(0,0,0,.9) 75%, rgba(0,0,0,0))}
    .avatar-label{position:absolute;left:16px;right:16px;bottom:16px;padding:11px 14px;border-radius:16px;background:rgba(9,20,37,.72);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.08);color:#dff3ff;font-size:13px;line-height:1.4}
    .avatar-label strong{display:block;font-size:14px;color:#ffffff;margin-bottom:2px}
    .female-avatar.listening{transform:scale(1.012)}
    .female-avatar.listening .avatar-card{box-shadow:0 0 0 1px rgba(96,165,250,.25),0 18px 50px rgba(24,119,242,.22)}
    .female-avatar.listening .avatar-halo{background:radial-gradient(circle, rgba(96,165,250,.28), transparent 68%)}
    .female-avatar.speaking{transform:translateY(-2px)}
    .female-avatar.speaking .avatar-card{box-shadow:0 0 0 1px rgba(52,211,153,.26),0 20px 56px rgba(34,197,94,.24)}
    .female-avatar.speaking .avatar-halo{background:radial-gradient(circle, rgba(52,211,153,.28), transparent 68%)}
    .wavebar-wrap{display:flex;justify-content:center;gap:6px;padding-top:8px}
    .wavebar{width:6px;height:10px;border-radius:999px;background:linear-gradient(180deg,#60a5fa,#34d399);opacity:.68;animation:wave 1.25s ease-in-out infinite}
    .wavebar:nth-child(2){animation-delay:.1s}.wavebar:nth-child(3){animation-delay:.2s}.wavebar:nth-child(4){animation-delay:.3s}.wavebar:nth-child(5){animation-delay:.4s}
    .right-panel{padding:18px;display:grid;grid-template-rows:auto auto auto auto 1fr auto;gap:16px;min-height:960px}
    .speech{padding:16px 18px;border-radius:18px;background:linear-gradient(180deg,rgba(18,30,48,.95),rgba(23,37,62,.88));border:1px solid rgba(255,255,255,.08);line-height:1.55;font-size:15px;box-shadow:inset 0 1px 0 rgba(255,255,255,.05)}
    .metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
    .metric{padding:14px;border-radius:18px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);min-height:92px}
    .metric .label{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#b8cde0;margin-bottom:8px}
    .metric .value{font-size:26px;font-weight:800;line-height:1.1}
    .metric .sub{font-size:12px;color:#aac2d8;margin-top:6px;line-height:1.35}
    .selectors{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:10px;align-items:center}
    .selectors select,.chat-input{width:100%;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);border-radius:14px;color:#eef6ff;padding:12px 14px;font-size:14px;outline:none}
    .btn{border:none;border-radius:14px;padding:12px 15px;font-weight:700;font-size:14px;cursor:pointer;transition:.18s ease;background:rgba(255,255,255,.08);color:#eef6ff;border:1px solid rgba(255,255,255,.12)}
    .btn:hover{transform:translateY(-1px)}
    .btn.primary{background:linear-gradient(135deg,#34d399,#22c55e);color:#052e22;box-shadow:0 10px 24px rgba(34,197,94,.25)}
    .btn.secondary{background:linear-gradient(135deg,#60a5fa,#3b82f6);color:white}
    .btn.dark{background:rgba(15,23,42,.88)}
    .chips{display:flex;flex-wrap:wrap;gap:10px}
    .chip{padding:10px 14px;border-radius:999px;border:1px solid rgba(52,211,153,.45);background:rgba(15,23,42,.88);color:#e8f5ff;font-size:13px;font-weight:700;cursor:pointer}
    .chip:hover{background:rgba(52,211,153,.16)}
    .chatbox{min-height:185px;max-height:260px;overflow:auto;padding-right:4px;display:flex;flex-direction:column;gap:12px}
    .msg{max-width:88%;padding:12px 14px;border-radius:18px;line-height:1.5;font-size:14px;box-shadow:0 8px 18px rgba(0,0,0,.08)}
    .msg.user{align-self:flex-end;background:linear-gradient(135deg,#2563eb,#0ea5e9);border-bottom-right-radius:6px}
    .msg.bot{align-self:flex-start;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.08);border-bottom-left-radius:6px}
    .msg small{display:block;color:#c7d9ea;margin-top:6px}
    .composer{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px;align-items:center}
    .footer-note{font-size:12px;color:#9eb7cb;line-height:1.45}
    .statusline{font-size:12px;color:#bfd8eb}
    .hero-caption{padding:14px 16px;border-radius:16px;background:rgba(8,20,35,.72);border:1px solid rgba(255,255,255,.08);color:#deefff;font-size:13px;line-height:1.5;box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}
    .advisor-shell{border-radius:22px;background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.04));border:1px solid rgba(255,255,255,.08);padding:16px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
    .advisor-topbar{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap;margin-bottom:14px}
    .advisor-kicker{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#7dd3fc;font-weight:800;margin-bottom:5px}
    .advisor-title{font-size:20px;font-weight:800;color:#ffffff}
    .advisor-subtitle{font-size:13px;color:#b5c9db;line-height:1.5;margin-top:4px;max-width:760px}
    .advisor-pill-wrap{display:flex;gap:8px;flex-wrap:wrap}
    .advisor-pill{padding:8px 12px;border-radius:999px;background:rgba(15,23,42,.78);border:1px solid rgba(96,165,250,.22);font-size:11px;font-weight:800;color:#d9ebff;letter-spacing:.04em}
    .advisor-tabs{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
    .advisor-tab{border:none;border-radius:14px;padding:10px 14px;font-weight:800;font-size:13px;cursor:pointer;background:rgba(15,23,42,.72);color:#dbeafe;border:1px solid rgba(255,255,255,.08);transition:.18s ease}
    .advisor-tab.active,.advisor-tab:hover{background:linear-gradient(135deg,rgba(52,211,153,.22),rgba(96,165,250,.22));border-color:rgba(52,211,153,.34);transform:translateY(-1px)}
    .advisor-panel{border-radius:18px;background:rgba(4,12,24,.42);border:1px solid rgba(255,255,255,.06);padding:14px}
    .advisor-status{font-size:12px;color:#98b6cd;margin-bottom:12px;line-height:1.5}
    .advisor-body{display:none}
    .advisor-body.active{display:block}
    .advisor-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px}
    .viz-card{grid-column:span 6;border-radius:18px;background:linear-gradient(180deg,rgba(15,31,54,.94),rgba(11,24,42,.94));border:1px solid rgba(255,255,255,.07);padding:14px;box-shadow:0 14px 28px rgba(0,0,0,.16)}
    .viz-card.wide{grid-column:span 12}
    .viz-card.third{grid-column:span 4}
    .viz-title{font-size:14px;font-weight:800;color:#fff;margin-bottom:4px}
    .viz-subtitle{font-size:12px;color:#9fbed4;margin-bottom:12px}
    .insight-banner{padding:14px 16px;border-radius:16px;background:linear-gradient(135deg,rgba(34,197,94,.16),rgba(59,130,246,.14));border:1px solid rgba(52,211,153,.2);font-size:13px;line-height:1.6;color:#eaf6ff}
    .insight-list{margin:10px 0 0 0;padding-left:18px;color:#d7e9f8;font-size:13px;line-height:1.6}
    .mini-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
    .mini-kpi{padding:14px;border-radius:16px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08)}
    .mini-kpi .k{font-size:11px;letter-spacing:.05em;color:#9fb7ca;text-transform:uppercase;margin-bottom:6px}
    .mini-kpi .v{font-size:22px;font-weight:800;color:#fff;line-height:1.15}
    .mini-kpi .s{font-size:12px;color:#bcd0e0;margin-top:6px;line-height:1.45}
    .bars{height:220px;display:flex;align-items:flex-end;gap:10px;padding-top:8px}
    .bar-item{flex:1;display:flex;flex-direction:column;align-items:center;gap:7px;min-width:0}
    .bar-col-wrap{width:100%;height:150px;display:flex;align-items:flex-end;justify-content:center}
    .bar-col{width:100%;max-width:56px;border-radius:14px 14px 6px 6px;background:linear-gradient(180deg,#60a5fa,#22c55e);position:relative;box-shadow:0 10px 24px rgba(52,211,153,.16)}
    .bar-col.secondary{background:linear-gradient(180deg,#a78bfa,#f472b6)}
    .bar-value{font-size:11px;color:#dff1ff;font-weight:800;white-space:nowrap}
    .bar-label{font-size:11px;color:#96b3c9;text-align:center;line-height:1.3;min-height:30px}
    .hbars{display:flex;flex-direction:column;gap:10px}
    .hrow{display:grid;grid-template-columns:150px minmax(0,1fr) 100px;gap:10px;align-items:center}
    .hlabel{font-size:12px;color:#dcecff;font-weight:700}
    .htrack{height:14px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;border:1px solid rgba(255,255,255,.05)}
    .hfill{height:100%;border-radius:999px;background:linear-gradient(90deg,#f59e0b,#f472b6,#60a5fa)}
    .hval{font-size:12px;color:#c8dbee;text-align:right;font-weight:700}
    .legend-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
    .legend-item{display:inline-flex;align-items:center;gap:8px;font-size:11px;color:#cfe3f4;font-weight:700}
    .legend-swatch{width:12px;height:12px;border-radius:4px}
    .premium-table-wrap{overflow:auto;border-radius:16px;border:1px solid rgba(255,255,255,.07);background:rgba(10,18,32,.58)}
    table.premium-table{width:100%;border-collapse:collapse;min-width:640px}
    .premium-table thead th{position:sticky;top:0;background:linear-gradient(180deg,#10233d,#0c1a2f);color:#dff0ff;padding:12px 14px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;text-align:left;border-bottom:1px solid rgba(255,255,255,.08)}
    .premium-table tbody td{padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.05);font-size:13px;color:#eef7ff;vertical-align:top}
    .premium-table tbody tr:nth-child(even){background:rgba(255,255,255,.03)}
    .rank-pill{display:inline-flex;align-items:center;justify-content:center;min-width:28px;height:28px;border-radius:999px;background:linear-gradient(135deg,#60a5fa,#34d399);font-size:12px;font-weight:800;color:#062033}
    .poster-board{border-radius:22px;padding:20px;background:radial-gradient(circle at top left,rgba(52,211,153,.16),transparent 24%),radial-gradient(circle at top right,rgba(96,165,250,.14),transparent 26%),linear-gradient(145deg,#0b1d34,#081423 58%,#0b1728);border:1px solid rgba(255,255,255,.08);box-shadow:0 20px 45px rgba(0,0,0,.28)}
    .poster-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;flex-wrap:wrap;margin-bottom:16px}
    .poster-brand{font-size:12px;letter-spacing:.16em;color:#7dd3fc;font-weight:800;text-transform:uppercase}
    .poster-title{font-size:28px;line-height:1.15;font-weight:800;color:#fff;max-width:640px}
    .poster-note{font-size:13px;color:#b7cde0;line-height:1.5;margin-top:6px;max-width:720px}
    .poster-badges{display:flex;gap:8px;flex-wrap:wrap}
    .poster-badge{padding:8px 12px;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);font-size:11px;font-weight:800;color:#d9ebff}
    .poster-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px}
    .poster-block{grid-column:span 4;border-radius:18px;padding:16px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08)}
    .poster-block.wide{grid-column:span 6}
    .poster-block.full{grid-column:span 12}
    .poster-block .t{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#9fc3dc;margin-bottom:8px}
    .poster-block .n{font-size:24px;font-weight:800;color:#fff;line-height:1.15}
    .poster-block .d{font-size:13px;color:#dcecff;line-height:1.55;margin-top:8px}
    .poster-actions{margin:0;padding-left:18px;color:#e9f6ff;font-size:13px;line-height:1.65}
    .poster-actions li{margin-bottom:6px}
    .poster-foot{margin-top:12px;font-size:11px;color:#9eb7cb;line-height:1.5}
    @keyframes blink{0%,46%,48%,100%{transform:scaleY(0)}47%{transform:scaleY(1)}}
    @keyframes wave{0%,100%{height:10px;opacity:.45}50%{height:28px;opacity:1}}
    @keyframes talkMouth{0%{height:7px;width:42px;border-radius:0 0 24px 24px}28%{height:22px;width:34px;border-radius:4px 4px 22px 22px}55%{height:12px;width:46px;border-radius:0 0 26px 26px}78%{height:26px;width:31px;border-radius:4px 4px 20px 20px}100%{height:8px;width:42px;border-radius:0 0 24px 24px}}
    @keyframes pulse{0%,100%{transform:translateX(-50%) scale(1);opacity:.75}50%{transform:translateX(-50%) scale(1.08);opacity:1}}
    @media (max-width: 1180px){.content{grid-template-columns:1fr}.avatar-panel,.right-panel{min-height:unset}.hero-stage{min-height:430px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.mini-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.selectors{grid-template-columns:1fr 1fr}.composer{grid-template-columns:1fr 1fr}.btn.send{grid-column:span 2}.viz-card,.viz-card.third,.poster-block,.poster-block.wide{grid-column:span 12}}
    @media (max-width: 720px){.title{font-size:22px}.head{padding:18px}.content{padding:16px}.metrics,.mini-kpis{grid-template-columns:1fr}.selectors{grid-template-columns:1fr}.composer{grid-template-columns:1fr}.female-avatar{transform:scale(.92)}.hrow{grid-template-columns:1fr}.poster-title{font-size:22px}.bars{gap:8px}.bar-label{min-height:42px}}

/* SELA v14 Premium Virtual Human: minimal personal-assistant look.
   All analytics, voice, exports and boardroom outputs are preserved. */
.sela-root {
  min-height:0; border-radius:26px;
  background:linear-gradient(180deg,#0b1524 0%,#0c1726 100%);
  border:1px solid #22374b;
  box-shadow:0 22px 56px rgba(13,27,44,.16);
}
.head {padding:18px 22px;gap:14px;background:linear-gradient(110deg,#0f1b2d,#102033);border-bottom:1px solid #213449}
.brand{gap:14px}
.logo{width:40px;height:40px;flex-shrink:0;border-radius:50%;font-size:20px;background:linear-gradient(135deg,#55dbc8,#60a2ff);box-shadow:0 10px 24px rgba(54,153,198,.18)}
.title{font-size:22px;font-weight:760;letter-spacing:-.03em}
.subtitle{font-size:12px;line-height:1.52;color:#a8bfd2;max-width:720px}
.head-tags{gap:6px;max-width:420px;justify-content:flex-end}
.tag{padding:6px 9px;font-size:9px;font-weight:700;letter-spacing:.04em;background:rgba(255,255,255,.02);border:1px solid #2e4c68;color:#bdd8ea}
.content{padding:14px;grid-template-columns:minmax(182px,208px) minmax(0,1fr);gap:14px;align-items:stretch}
.panel{border-radius:20px;border-color:#26384d;background:linear-gradient(180deg,#122033,#101b2d);backdrop-filter:none;box-shadow:none}
.avatar-panel{min-height:0;padding:12px 10px 12px 12px;gap:10px;align-self:start;position:relative;overflow:hidden}
.hero-stage{min-height:318px;height:318px;flex:none;border-radius:18px;background:radial-gradient(circle at 50% 18%,rgba(91,177,255,.18),transparent 36%),linear-gradient(180deg,#16283b,#0d1625)}
.hero-stage::before{opacity:.22}
.hero-stage::after{display:none}
.avatar-wrap{padding:6px 8px 0}
.female-avatar{width:min(100%,188px);height:296px;margin:0 auto}
.avatar-card{border-radius:18px;box-shadow:none;background:transparent;overflow:visible}
.avatar-label{left:8px;right:8px;bottom:8px;border-radius:12px;padding:8px 10px;font-size:10px;line-height:1.35;background:rgba(8,18,31,.64);backdrop-filter:blur(8px)}
.avatar-label strong{font-size:11px}
.wavebar-wrap{padding-top:2px}
.hero-caption{max-height:92px;overflow:auto;padding:11px;font-size:11px;line-height:1.5;border-radius:14px;background:#0e1a2a;color:#d0e0ed;scrollbar-width:thin}
.right-panel{display:flex;flex-direction:column;gap:12px;padding:14px;min-height:0}
.speech{padding:13px 14px;font-size:12px;line-height:1.55;max-height:86px;overflow:auto;background:#0c1727;border:1px solid #263f58;box-shadow:none;scrollbar-width:thin;border-radius:16px}
.metrics{gap:9px}
.metric{padding:12px;border-radius:16px;background:linear-gradient(180deg,#17283d,#18283a);min-height:82px;border-color:#304559}
.metric .label{font-size:10px;color:#9bb4c9;letter-spacing:.065em;margin-bottom:7px}
.metric .value{font-size:22px;font-weight:750;color:#f2f7fe}
.metric .sub{font-size:10px;margin-top:6px;color:#a8bed0}
.selectors{gap:8px;align-items:center}
.selectors select,.chat-input{background:#0d1828;border-color:#31465c;border-radius:14px;padding:10px 12px;font-size:12px}
.btn{padding:10px 12px;border-radius:14px;font-size:12px;box-shadow:none!important;transform:none!important}
.btn.primary{background:#2cbfa7;color:#082d2a}
.btn.secondary{background:#3178c6;color:#fff}
.btn.dark{background:#122035;color:#d8e9f8}
.chips{gap:6px}
.chip{padding:7px 10px;font-size:11px;border-radius:999px;font-weight:650;background:#0f2034;border-color:#31516c;color:#d4e6f2}
.chip:hover{background:#17405a}
.advisor-shell{padding:14px;border-radius:20px;background:linear-gradient(180deg,#142538,#132234);border-color:#294056;box-shadow:none}
.advisor-topbar{margin-bottom:12px}
.advisor-kicker{color:#61cbbd;font-size:10px;letter-spacing:.14em}
.advisor-title{font-size:18px;letter-spacing:-.02em;font-weight:750}
.advisor-subtitle{font-size:11px;margin-top:4px}
.advisor-pill-wrap{gap:5px}
.advisor-pill{padding:6px 8px;font-size:9px;background:#0c1a2d;border-color:#314b63}
.advisor-tabs{margin-bottom:12px;gap:6px;flex-wrap:wrap}
.advisor-tab{font-size:11px;padding:8px 12px;border-radius:999px;background:#0f1f33;border-color:#31455b;font-weight:650}
.advisor-tab.active,.advisor-tab:hover{background:#1f5b68;border-color:#347a7e;color:#e9ffff;transform:none}
.advisor-panel{padding:12px;border-radius:16px;background:#0f1b2b}
.advisor-status{font-size:11px;line-height:1.5;color:#aec5d6;margin-bottom:11px}
.viz-card{border-radius:13px;padding:12px;background:#16273c;box-shadow:none}
.viz-title{font-size:13px}
.viz-subtitle{font-size:11px}
.insight-banner{border-radius:12px;font-size:12px;background:#173548}
.insight-list{font-size:12px}
.mini-kpi{padding:12px;border-radius:12px;background:#1b3047}
.mini-kpi .v{font-size:19px}
.poster-board{box-shadow:none;background:#10223a}
.msg{font-size:12px;padding:10px 12px;border-radius:16px;max-width:96%}
.chatbox{min-height:110px;max-height:158px;gap:8px}
.composer{position:sticky;bottom:0;z-index:3;background:#101b2d;padding:8px 0 4px}
.statusline,.footer-note{font-size:10px}
/* Boardroom one-click outputs */
.boardroom-tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:2px 0 13px;padding:10px 11px;background:#0d1a2a;border:1px solid #284259;border-radius:16px}
.boardroom-label{font-size:11px;color:#91bad2;font-weight:800;letter-spacing:.06em;margin-right:3px}
.boardroom-action{display:inline-flex;align-items:center;gap:7px;padding:8px 11px;background:#14273b;border:1px solid #35536a;color:#e4f3fc;font-weight:650;font-size:11px;border-radius:999px;cursor:pointer;transition:background .12s}
.boardroom-action:hover{background:#225372}
.boardroom-action.primary{background:#1c716d;border-color:#258b82;color:#effffb}
.boardroom-hint{font-size:10px;color:#9db8c9;margin:0 0 9px}
.briefing-preview{padding:20px;border-radius:15px;background:#f8fafc;color:#182a3d;box-shadow:0 12px 27px rgba(0,0,0,.1)}
.briefing-header{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;border-bottom:2px solid #dde6ee;padding-bottom:12px;margin-bottom:16px}
.briefing-eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.14em;color:#227b86;font-weight:800}
.briefing-header h3{font-size:21px;color:#122c47;letter-spacing:-.025em;margin:4px 0 6px}
.briefing-desc{font-size:11px;color:#567087;line-height:1.45}
.briefing-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:15px}
.briefing-kpi{background:#edf4f7;border-radius:11px;padding:12px;min-width:0}
.briefing-kpi span{display:block;font-size:10px;text-transform:uppercase;color:#60798e;font-weight:700;margin-bottom:5px}
.briefing-kpi strong{display:block;font-size:17px;color:#12334e;line-height:1.25;overflow-wrap:anywhere}
.briefing-section{background:white;border:1px solid #e1e8ef;border-radius:12px;padding:14px;margin-bottom:12px}
.briefing-section h4{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#2b5874;margin:0 0 9px}
.briefing-section p,.briefing-section li{font-size:11px;color:#385066;line-height:1.5;margin:0}
.briefing-section ol{padding-left:17px;margin:0}
.briefing-chart{width:100%;max-height:230px;display:block}
.briefing-foot{font-size:10px;color:#70899b;padding-top:9px;border-top:1px solid #e2e8ef}
@media(max-width:1180px){
  .content{grid-template-columns:minmax(0,1fr)}
  .avatar-panel{display:grid;grid-template-columns:150px minmax(0,1fr);gap:12px;align-items:center}
  .hero-stage{height:220px;min-height:220px;grid-row:span 2}
  .female-avatar{height:200px;width:142px}
  .avatar-wrap{padding:6px}
  .avatar-label{font-size:9px}
  .wavebar-wrap{justify-content:start}
  .hero-caption{max-height:120px}
  .right-panel{min-height:0}
}
@media(max-width:720px){
  .head{padding:15px}.title{font-size:20px}
  .content{padding:10px}
  .avatar-panel{grid-template-columns:minmax(0,1fr)}
  .hero-stage{height:210px;min-height:210px}
  .female-avatar{height:190px;width:132px}
  .avatar-wrap{display:flex;justify-content:center}
  .avatar-label{max-height:66px;overflow:hidden;padding:5px 6px;font-size:8px;line-height:1.2}
  .avatar-label strong{font-size:9px}
  .metrics{grid-template-columns:repeat(2,minmax(0,1fr))}
  .metric .value{font-size:18px}
  .briefing-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .boardroom-tools{gap:6px}
  .boardroom-action{font-size:10px;padding:8px}
}

  
/* SELA v17 smooth-talking expression layers: same portrait, pre-composited lightweight eye/lip details.
   All effects are composited on the client; no camera, network, ML model or new backend job. */
.avatar-face-scene{position:relative;isolation:isolate;width:100%;height:100%;overflow:hidden;
  transform-origin:50% 42%;animation:selaBreath 6.4s ease-in-out infinite;will-change:transform}
.avatar-face-scene>.avatar-photo{width:100%;height:100%;object-fit:cover;display:block}
.avatar-expression{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
  pointer-events:none;user-select:none;opacity:0;z-index:2;will-change:opacity}
.sela-mouth-shape{transition:opacity .065s linear;backface-visibility:hidden}
.sela-blink.blinking{animation:selaEyeBlink .185s ease-in-out forwards}
/* Hide the old artificial full-pink mouth, keep original DOM for backward compatibility. */
.lip-sync-mouth{display:none!important}
.avatar-face-scene::after{content:"";pointer-events:none;position:absolute;inset:0;
 background:linear-gradient(180deg,transparent 57%,rgba(5,17,31,.11) 100%);z-index:3}
@keyframes selaEyeBlink{0%,14%{opacity:0}43%,58%{opacity:1}100%{opacity:0}}
@keyframes selaBreath{0%,100%{transform:translate3d(0,0,0) scale(1)}
  28%{transform:translate3d(.6px,-1.4px,0) scale(1.004)}
  55%{transform:translate3d(-.6px,-.1px,0) scale(1.008)}
  78%{transform:translate3d(.45px,1px,0) scale(1.003)}}
.female-avatar.listening .avatar-face-scene{animation-duration:5.3s}
.female-avatar.speaking .avatar-face-scene{animation-duration:4.1s}
/* v17: restrained head micro-motion; face/eye/lip layers move as one scene. */
.avatar-card{transform-origin:50% 44%;animation:selaHeadMicro 7.1s ease-in-out infinite}
.female-avatar.speaking .avatar-card{animation:selaHeadTalking 3.4s ease-in-out infinite}
.female-avatar.listening .avatar-card{animation-duration:5.2s}
@keyframes selaHeadMicro{0%,100%{transform:rotate(-.35deg) translateY(0)}32%{transform:rotate(.4deg) translateY(-1px)}68%{transform:rotate(-.15deg) translateY(.8px)}}
@keyframes selaHeadTalking{0%,100%{transform:rotate(-.4deg) translateY(0)}24%{transform:rotate(.3deg) translateY(-1.3px)}55%{transform:rotate(.65deg) translateY(.7px)}78%{transform:rotate(-.2deg) translateY(-.6px)}}
.sela-mouth-demo{margin:0 auto;padding:7px 11px;border:1px solid rgba(58,214,181,.33);border-radius:999px;
  background:rgba(19,66,76,.55);color:#c4f9ed;font-size:10px;font-weight:750;cursor:pointer;transition:background .15s ease}
.sela-mouth-demo:hover{background:rgba(30,112,119,.7)}
.sela-face-status{font-size:10px;font-weight:800;text-align:center;letter-spacing:.09em;color:#9eb7c7;min-height:13px}
.female-avatar.speaking~.sela-face-status{color:#61dac0}
@media(prefers-reduced-motion:reduce){.avatar-card{animation:none!important}}

@media(prefers-reduced-motion:reduce){
  .avatar-face-scene{animation:none!important;will-change:auto}
  .sela-blink.blinking{animation-duration:.12s}
  .sela-mouth-shape{transition:none}
}

/* === SELA v18 CINEMATIC STAGE. No data/analytics/report code is modified. === */
html,body{width:100%;height:100%;min-height:0;margin:0;overflow:hidden!important;background:transparent!important}
.sela-root{position:fixed!important;inset:0!important;width:100%!important;height:100dvh!important;
  min-height:0!important;border:0!important;box-shadow:none!important;background:transparent!important;
  border-radius:0!important;overflow:visible!important;pointer-events:none!important;z-index:70!important}
.head{display:none!important}
.content,.right-panel{display:contents!important}
.avatar-panel{position:fixed!important;z-index:40!important;right:26px!important;bottom:143px!important;
  width:clamp(183px,17.4vw,238px)!important;height:clamp(211px,33vh,282px)!important;
  padding:0!important;margin:0!important;border:0!important;box-shadow:none!important;
  background:transparent!important;overflow:visible!important;display:block!important;pointer-events:auto!important}
.hero-stage{width:100%!important;height:100%!important;min-height:0!important;max-height:none!important;
  border:none!important;border-radius:25px!important;overflow:hidden!important;
  background:linear-gradient(160deg,rgba(10,31,54,.22),rgba(9,23,43,.1))!important}
.hero-stage:before,.hero-stage:after{display:none!important}
.avatar-wrap{inset:0!important;padding:0!important}
.female-avatar{width:100%!important;height:100%!important;max-width:none!important;transform:none!important}
.avatar-card{width:100%!important;height:100%!important;border-radius:24px!important;
  border:1px solid rgba(134,216,240,.25)!important;box-shadow:0 19px 49px rgba(4,24,47,.28)!important;
  overflow:hidden!important;background:#0b1a2d!important}
.avatar-face-scene{width:100%!important;height:100%!important}
.avatar-label,.hero-caption,.wavebar-wrap,.sela-mouth-demo{display:none!important}
/* Move only speaking visemes; eyelid location is unchanged. */
.avatar-expression.sela-mouth-shape{transform:translateX(7px)!important}
.sela-face-status{position:absolute!important;bottom:8px!important;left:50%!important;
  transform:translateX(-50%)!important;min-width:94px!important;max-width:90%!important;
  padding:5px 10px!important;border:1px solid rgba(119,221,217,.27)!important;border-radius:999px!important;
  background:rgba(5,25,42,.78)!important;color:#a6eee2!important;text-align:center!important;
  white-space:nowrap!important;font-size:9px!important;letter-spacing:.1em!important;z-index:43!important;
  box-shadow:0 4px 14px rgba(0,0,0,.19)!important}
.speech,.metrics,.footer-note{display:none!important}
.selectors{position:fixed!important;z-index:42!important;right:25px!important;bottom:104px!important;
  display:flex!important;gap:6px!important;align-items:center!important;justify-content:center!important;
  width:clamp(200px,21vw,272px)!important;padding:7px!important;border-radius:17px!important;
  border:1px solid rgba(119,185,224,.22)!important;background:rgba(10,27,47,.92)!important;
  box-shadow:0 12px 25px rgba(6,19,38,.19)!important;pointer-events:auto!important}
.selectors select,.selectors #checkMicBtn{display:none!important}
.selectors .btn{padding:9px 10px!important;border-radius:11px!important;min-height:36px!important;
  font-size:11px!important;flex:1!important;white-space:nowrap!important}
.selectors #testVoiceBtn{background:#174a68!important;color:#ecfbff!important}
.selectors #stopVoiceBtn{background:#152c44!important;color:#d7eafb!important}
.selectors #cineMoreBtn{flex:0 0 37px!important;background:#11263e!important}
.selectors.is-expanded{flex-wrap:wrap!important}
.selectors.is-expanded select,.selectors.is-expanded #checkMicBtn{display:inline-flex!important;max-width:100%!important;
  flex:1 1 100%!important;font-size:11px!important}
.selectors .sela-mouth-demo{display:none!important}
.selectors.is-expanded .sela-mouth-demo{display:inline-flex!important;justify-content:center!important;
  flex:1 1 100%!important;padding:8px 10px!important;font-size:11px!important;min-height:34px!important}
.chips{display:none!important;position:fixed!important;z-index:80!important;right:25px!important;
  bottom:205px!important;width:min(330px,calc(100vw - 34px))!important;max-height:250px!important;
  padding:13px!important;overflow-y:auto!important;pointer-events:auto!important;
  background:#102239!important;border:1px solid rgba(110,188,225,.3)!important;
  border-radius:17px!important;box-shadow:0 24px 64px rgba(5,14,32,.32)!important}
.chips.is-expanded{display:flex!important;gap:8px!important}
.chips .chip{font-size:11px!important}
.composer{position:fixed!important;z-index:42!important;right:25px!important;bottom:31px!important;
  display:grid!important;grid-template-columns:minmax(0,1fr) auto auto!important;align-items:center!important;
  width:clamp(255px,28vw,380px)!important;min-height:61px!important;gap:6px!important;
  padding:8px!important;border-radius:18px!important;background:rgba(10,26,44,.96)!important;
  border:1px solid rgba(94,177,218,.26)!important;box-shadow:0 18px 42px rgba(2,13,30,.25)!important;
  pointer-events:auto!important}
.composer input{width:100%!important;min-width:0!important;font-size:12px!important;padding:10px!important}
.composer .btn{padding:9px 11px!important;min-height:38px!important;font-size:12px!important;grid-column:auto!important}
.statusline{position:fixed!important;bottom:6px!important;right:30px!important;z-index:42!important;
  max-width:370px!important;text-align:right!important;color:#527c94!important;font-size:10px!important;
  pointer-events:none!important;overflow:hidden!important;white-space:nowrap!important;text-overflow:ellipsis!important}
.chatbox{display:none!important}
.chatbox.is-expanded{display:flex!important;position:fixed!important;z-index:105!important;
  top:50%!important;left:50%!important;transform:translate(-50%,-50%)!important;
  width:min(610px,calc(100vw - 30px))!important;height:min(380px,65dvh)!important;
  max-height:none!important;min-height:0!important;overflow-y:auto!important;padding:18px!important;
  border:1px solid #35516e!important;border-radius:20px!important;background:#102038!important;
  box-shadow:0 25px 80px rgba(0,0,0,.38)!important;pointer-events:auto!important}
/* Cinematic center dialog, hidden until SELA has a question or a user opens a report. */
.advisor-shell{display:none!important;position:fixed!important;z-index:90!important;
  left:calc(50% - 100px)!important;top:50%!important;transform:translate(-50%,-50%)!important;
  width:min(880px,calc(100vw - 360px))!important;min-width:490px!important;
  max-height:calc(100dvh - 56px)!important;overflow:auto!important;pointer-events:auto!important;
  margin:0!important;padding:22px!important;border:1px solid rgba(108,178,220,.39)!important;
  border-radius:24px!important;background:linear-gradient(160deg,#0e223b,#101d30)!important;
  box-shadow:0 32px 100px rgba(5,16,33,.53)!important}
.advisor-shell.is-open{display:block!important}
.advisor-topbar{padding-right:35px!important}
.advisor-title{font-size:20px!important}
.advisor-shell .advisor-tab{border-radius:999px!important}
.advisor-shell .advisor-panel{background:rgba(4,13,29,.48)!important}
.cine-shade{position:fixed;inset:0;z-index:60;display:none;background:rgba(6,18,35,.40);
  backdrop-filter:blur(3px);pointer-events:auto}
.cine-shade.is-open{display:block}
.cine-text-answer{display:none;position:fixed;z-index:90;top:50%;left:calc(50% - 100px);
  transform:translate(-50%,-50%);width:min(680px,calc(100vw - 360px));min-width:490px;
  max-height:calc(100dvh - 60px);overflow:auto;border:1px solid rgba(116,202,226,.38);
  border-radius:25px;background:linear-gradient(155deg,#102a48,#102036);color:#f0f8ff;
  box-shadow:0 32px 100px rgba(5,15,32,.5);padding:25px;pointer-events:auto}
.cine-text-answer.is-open{display:block}
.cine-minihead{display:flex;gap:11px;align-items:center;margin-bottom:18px}
.cine-mini-avatar{display:grid;place-items:center;background:linear-gradient(130deg,#4be0cc,#5b9deb);
  border-radius:14px;width:44px;height:44px;color:#05263b;font-size:22px;font-weight:900}
.cine-minihead strong{display:block;font-size:16px;font-weight:800}
.cine-minihead span{display:block;font-size:11px;color:#a3c8da;margin-top:3px}
.cine-answer-message{white-space:pre-wrap;font-size:15px;line-height:1.85;overflow-wrap:anywhere;color:#e0f4ff;
  border-left:3px solid #56d6c6;padding:2px 0 2px 19px}
.cine-answer-actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:19px;padding-top:13px;border-top:1px solid rgba(255,255,255,.1)}
.cine-subtitle{position:fixed;z-index:110;left:calc((100vw - 305px) / 2);bottom:24px;
  transform:translateX(-50%);width:min(730px,calc(100vw - 360px));min-height:0;
  display:none;justify-content:center;align-items:center;text-align:center;pointer-events:none}
.cine-subtitle.is-visible{display:flex}
.cine-subtitle span{display:inline-block;padding:10px 17px;border-radius:13px;
  background:rgba(4,10,19,.91);color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.55);
  box-shadow:0 8px 23px rgba(0,0,0,.25);font-size:17px;font-weight:720;line-height:1.65;
  letter-spacing:.01em;max-width:100%;overflow-wrap:anywhere}
.cine-answer-close{position:absolute;top:14px;right:14px;z-index:101;display:grid;place-items:center;
  width:35px;height:35px;border-radius:999px;border:1px solid rgba(138,194,229,.28);
  background:#112d47;color:#ecfbff;font-size:20px;cursor:pointer}
.cine-answer-close:hover{background:#16486b}
.cine-microcopy{font-size:12px;color:#95bdcf;margin-top:13px;line-height:1.5}
.cine-control-btn{border-radius:999px;padding:9px 14px;color:#e9f9ff;background:#153651;
  border:1px solid #3d6e83;font-weight:720;cursor:pointer;font-size:12px}
.cine-control-btn:hover{background:#205879}
/* Ignore the cumbersome original panel until a question is asked; never drop its data or events. */
@media(max-width:1040px){
 .cine-text-answer,.advisor-shell{left:44%!important;width:min(680px,calc(100vw - 285px))!important;
   min-width:0!important;max-height:calc(100dvh - 50px)!important}
 .cine-subtitle{left:calc((100vw - 270px)/2);width:calc(100vw - 295px)}
 .avatar-panel{right:14px!important;bottom:140px!important;width:195px!important;height:224px!important}
 .selectors{right:13px!important;bottom:98px!important;width:220px!important}
 .composer{right:13px!important;bottom:28px!important;width:270px!important}
 .statusline{right:18px!important}
 .chips{right:13px!important}
}
@media(max-width:690px){
 .avatar-panel{right:12px!important;bottom:114px!important;width:124px!important;height:155px!important}
 .avatar-card{border-radius:17px!important}
 .selectors{right:12px!important;bottom:77px!important;width:183px!important;padding:5px!important}
 .selectors .btn{padding:7px!important;font-size:9px!important;min-height:29px!important}
 .composer{right:12px!important;bottom:12px!important;width:min(300px,calc(100vw - 22px))!important;
   min-height:55px!important;grid-template-columns:minmax(0,1fr) auto auto!important}
 .composer .btn{padding:9px!important;font-size:10px!important;min-height:32px!important}
 .composer input{font-size:11px!important}
 .statusline{display:none!important}
 .chips{bottom:152px!important;right:12px!important}
 .cine-text-answer,.advisor-shell{left:50%!important;top:39%!important;
   width:calc(100vw - 24px)!important;min-width:0!important;max-height:61dvh!important;
   padding:17px!important;border-radius:19px!important}
 .advisor-shell .advisor-topbar{padding-right:30px!important}
 .cine-answer-message{font-size:13px;line-height:1.65}
 .cine-subtitle{left:50%;width:calc(100vw - 24px);bottom:80px}
 .cine-subtitle span{font-size:13px;line-height:1.45;padding:7px 12px}
}
@media(prefers-reduced-motion:reduce){.cine-shade,.cine-subtitle{transition:none!important}}

</style>
</head>
<body>
  <div class="cine-shade" id="cineShade" aria-hidden="true"></div>
  <section class="cine-text-answer" id="cineTextAnswer" role="region" aria-label="Jawaban SELA">
    <button type="button" class="cine-answer-close" id="cineCloseText" title="Tutup jawaban">×</button>
    <div class="cine-minihead"><div class="cine-mini-avatar">✦</div><div><strong>SELA menjawab</strong><span>Personal assistant · berdasarkan data aktif</span></div></div>
    <div class="cine-answer-message" id="cineTextBody"></div>
    <div class="cine-answer-actions">
      <button class="cine-control-btn" type="button" id="cineShowReport">Tampilkan grafik / tabel</button>
      <button class="cine-control-btn" type="button" id="cineCopyAnswer">Salin jawaban</button>
      <button class="cine-control-btn" type="button" id="cineHistoryBtn">Riwayat percakapan</button>
    </div>
    <div class="cine-microcopy">Data diambil dari analisis SELA. Filter dashboard dan laporan existing tidak berubah.</div>
  </section>
  <div class="cine-subtitle" id="cineSubtitle" aria-live="polite" aria-atomic="true"><span id="cineSubtitleText"></span></div>
  <div class="sela-root">
    <div class="head">
      <div class="brand">
        <div class="logo">S</div>
        <div>
          <div class="title">SELA v18 · Cinematic Personal Assistant</div>
          <div class="subtitle">Asisten pribadi virtual yang minimalis, modern, dan responsif. Semua kemampuan analisis, suara, insight visual, dan boardroom output tetap tersedia.</div>
        </div>
      </div>
      <div class="head-tags">
        <div class="tag">DATA CONNECTED</div>
        <div class="tag">VOICE READY</div>
        <div class="tag">LIP SYNC</div>
        <div class="tag">SMART FILTER</div>
        <div class="tag">HISTORY VERIFIED</div>
        <div class="tag">PREMIUM HUMAN</div>
      </div>
    </div>

    <div class="content">
      <div class="panel avatar-panel">
        <div class="hero-stage">
          <div class="avatar-wrap">
            <div id="femaleAvatar" class="female-avatar">
              <div class="avatar-halo"></div>
              <div class="avatar-card">
                <div class="avatar-face-scene" id="selaFaceScene" aria-label="SELA dengan gerakan wajah natural">
                  <img class="avatar-photo" src="data:image/webp;base64,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" alt="SELA virtual human" />
                  <img id="selaBlinkOverlay" class="avatar-expression sela-blink" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABD4AAAWoCAYAAABaHwE/AABQzElEQVR42uzdebBs7XoQ9Od5V/fe57sXq6wSNKWgQCBACYFMTAmGQBShwqQMQSYhYQgYDYMFCEGmQpCEeShiSAgChSikGB0IYYoyVSRSIEMQxVhUGMTS4t57zt6738c/1lq9115nde/e55zv5jsfv19l3bW6d++9e3f3e/K9z/O8zxsBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP9/e3BAAgAAACDo/+t2BCoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMBJjoyG6B6MJfoAAAAASUVORK5CYII=" alt="" aria-hidden="true" />
                  <img id="selaMouthSoft" class="avatar-expression sela-mouth-shape" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABD4AAAWoCAYAAABaHwE/AACuh0lEQVR42uz935JbW3bv+f3GmHMBmST31un2cTjCEfaL+dIv4SfwQ/iqH8oXtiN843b7nD4qSaWq2ptMYM0xfDHmWlhAZpLc/yRV9/cjUSSTmUhgAVmq+cP4IwEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAv5X/H6haOXpKwwVJAAAAAElFTkSuQmCC" alt="" aria-hidden="true" />
                  <img id="selaMouthMedium" class="avatar-expression sela-mouth-shape" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABD4AAAWoCAYAAABaHwE/AACxoUlEQVR42uz9WZIkSZbu+X3nMIuqmrtH5kURLjUGAjaGR2wCK+hF4Am7AjVREwjoRqOmrqqMrAx3M1VhPng4zCKiamY+RETWQPf/o8rycHMzHUTVI5M/PYMEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP5L+f8BrapG5rsNZ9YAAAAASUVORK5CYII=" alt="" aria-hidden="true" />
                  <img id="selaMouthOpen" class="avatar-expression sela-mouth-shape" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABD4AAAWoCAYAAABaHwE/AACzeUlEQVR42uz92ZZjy5be+X1zmi0A7hF7n4ZJiqyqLBZLqqeqS72EnkAPoSs9lcbQkERqqEgmWZnn5NldhDuwzKYupq0GjUezm2yq/r/BYER4AwcWEDuPfZiNBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD4d+X/A+CDDhSVUAHgAAAAAElFTkSuQmCC" alt="" aria-hidden="true" />
                  <img id="selaMouthRound" class="avatar-expression sela-mouth-shape" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABD4AAAWoCAYAAABaHwE/AACysUlEQVR42uz923IkyZbm+X1rqZo7gIjMvat3dQ97hhwORSjsESHfiJd8CT4BH4JXfCpeUYSkUKa6uquqax8yMwLuprp4sVTNzB1ABCIPdej+/7qzIgIBOPxgyJ36+TpIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA8M/K/wec6Ka4+jLDzgAAAABJRU5ErkJggg==" alt="" aria-hidden="true" />
                </div>
                <div class="lip-sync-mouth" aria-hidden="true"></div>
                <div class="avatar-overlay"></div>
                <div class="avatar-grid"></div>
                <div class="avatar-label"><strong>SELA \u2022 Virtual Human</strong>Ekspresi wajah: kedipan natural, gerak kepala halus, serta empat bentuk bibir saat SELA berbicara. Analisis dan laporan tetap lengkap.</div>
              </div>
            </div>
          </div>
        </div>
        <div class="wavebar-wrap"><div class="wavebar"></div><div class="wavebar"></div><div class="wavebar"></div><div class="wavebar"></div><div class="wavebar"></div></div>
        <button type="button" class="sela-mouth-demo" id="selaMouthDemoBtn" title="Uji gerakan bibir, kepala, dan napas selama 6 detik tanpa suara">▶ Demo Ekspresi · 6 dtk</button>
        <div id="selaFaceStatus" class="sela-face-status" aria-live="polite">● SIAP</div>
        <div class="hero-caption" id="heroCaption">Halo, saya SELA. Saya siap membantu Anda membaca SLA, tren transaksi, bottleneck, growth, vendor, nomor permohonan, dan menyiapkan output eksekutif secara cepat.</div>
      </div>

      <div class="panel right-panel">
        <div id="speechBubble" class="speech">Halo, saya SELA. Silakan bicara atau ketik pertanyaan Anda. Saya akan menjawab secara natural seperti asisten pribadi, dan bila diperlukan menampilkan insight dalam bentuk grafik, tabel, poster, atau briefing boardroom.</div>

        <div class="metrics">
          <div class="metric"><div class="label">Transaksi Aktif</div><div id="metricCount" class="value">0</div><div class="sub" id="metricPeriod">-</div></div>
          <div class="metric"><div class="label">Rata-rata SLA</div><div id="metricSLA" class="value">0 hari</div><div class="sub" id="metricBottleneck">Bottleneck: -</div></div>
          <div class="metric"><div class="label">Growth Terakhir</div><div id="metricGrowth" class="value">-</div><div class="sub" id="metricGrowthSub">Dibanding periode sebelumnya</div></div>
          <div class="metric"><div class="label">Prioritas Utama</div><div id="metricTopTrx" class="value" style="font-size:18px">-</div><div class="sub" id="metricTopVendor">Vendor: -</div></div>
        </div>

        <div class="selectors">
          <select id="voiceSelect"></select>
          <button id="checkMicBtn" class="btn dark">Cek Mic</button>
          <button id="testVoiceBtn" class="btn secondary">Uji Suara</button>
          <button id="stopVoiceBtn" class="btn dark">Stop</button>
          <button type="button" id="cineMoreBtn" class="btn dark" title="Pertanyaan cepat dan pengaturan suara">⋯</button>
        </div>

        <div class="chips" id="quickChips">
          <button class="chip" data-question="Buatkan ringkasan direksi">Ringkasan Direksi</button>
          <button class="chip" data-question="Jenis transaksi apa yang SLA-nya paling lama?">Top SLA</button>
          <button class="chip" data-question="Bagaimana growth transaksi?">Growth</button>
          <button class="chip" data-question="Apa bottleneck utamanya?">Bottleneck</button>
          <button class="chip" data-question="Vendor mana yang paling lambat?">Vendor Lambat</button>
          <button class="chip" data-question="Nomor permohonan mana yang perlu dipantau?">Nomor Permohonan</button>
          <button class="chip" data-question="Apa rekomendasi perbaikannya?">Rekomendasi</button>
          <button class="chip" data-question="Bandingkan jumlah transaksi tahun 2024, 2025, dan 2026">Multi-Tahun</button>
          <button class="chip" data-question="Bandingkan SLA Keuangan tahun 2024, 2025, dan 2026">SLA Multi-Tahun</button>
          <button class="chip" data-question="Bagaimana bottleneck tiap tahapan proses?">Tahapan Bottleneck</button>
          <button class="chip" data-question="Tampilkan grafik eksekutif transaksi dan SLA">Grafik</button>
          <button class="chip" data-question="Tampilkan tabel prioritas transaksi dan vendor">Tabel</button>
          <button class="chip" data-question="Buatkan poster eksekutif SLA">Poster</button>
          <button class="chip" data-question="Tampilkan briefing BOD satu halaman">Briefing BOD</button>
        </div>

        <div class="advisor-shell">
          <button type="button" class="cine-answer-close" id="cineCloseReport" title="Tutup panel">×</button>
          <div class="advisor-topbar">
            <div>
              <div class="advisor-kicker">SELA Premium Workspace</div>
              <div class="advisor-title">Personal Assistant Workspace</div>
              <div class="advisor-subtitle">Ajukan pertanyaan seperti ke asisten pribadi, lalu gunakan insight, grafik, tabel, poster, dan briefing tanpa mengubah dashboard utama.</div>
            </div>
            <div class="advisor-pill-wrap">
              <div class="advisor-pill">FAST RENDER</div>
              <div class="advisor-pill">DATA DRIVEN</div>
              <div class="advisor-pill">BOARD-READY</div>
            </div>
          </div>
          <div class="advisor-tabs">
            <button class="advisor-tab active" data-tab="overview">Insight</button>
            <button class="advisor-tab" data-tab="charts">Grafik</button>
            <button class="advisor-tab" data-tab="tables">Tabel</button>
            <button class="advisor-tab" data-tab="poster">Poster</button>
            <button class="advisor-tab" data-tab="briefing">Boardroom</button>
          </div>
          <div class="boardroom-tools" aria-label="Unduh hasil analisis SELA">
            <span class="boardroom-label">BOARDROOM OUTPUT</span>
            <button type="button" class="boardroom-action primary" data-export="poster" title="Simpan poster 1600 x 1000 pixel">Poster PNG</button>
            <button type="button" class="boardroom-action" data-export="chartpng" title="Simpan grafik menjadi gambar PNG">Grafik PNG</button>
            <button type="button" class="boardroom-action" data-export="svg" title="Simpan grafik vektor siap presentasi">Grafik SVG</button>
            <button type="button" class="boardroom-action" data-export="csv" title="Unduh tabel prioritas, bisa dibuka di Excel">Tabel CSV</button>
            <button type="button" class="boardroom-action" data-export="html" title="Briefing satu halaman, bisa dibuka offline">Briefing HTML</button>
            <button type="button" class="boardroom-action" data-export="pdf" title="Cetak briefing satu halaman atau simpan sebagai PDF">Cetak / PDF</button>
          </div>
          <div class="advisor-panel">
            <div class="advisor-status" id="advisorStatus">Workspace Executive Advisor siap digunakan. Ketik pertanyaan atau klik chip cepat, lalu saya akan menampilkan insight visual yang paling relevan.</div>
            <div id="advisorOverview" class="advisor-body active"></div>
            <div id="advisorCharts" class="advisor-body"></div>
            <div id="advisorTables" class="advisor-body"></div>
            <div id="advisorPoster" class="advisor-body"></div>
            <div id="advisorBriefing" class="advisor-body"></div>
          </div>
        </div>

        <div id="chatbox" class="chatbox"></div>

        <div class="composer">
          <input id="textInput" class="chat-input" type="text" placeholder="Tanya SELA..." />
          <button id="micBtn" class="btn primary">🎙️ Bicara</button>
          <button id="sendBtn" class="btn send secondary">Kirim</button>
        </div>
        <div class="statusline" id="statusLine">Status: SELA siap membantu. Anda bisa bicara atau mengetik.</div>
        <div class="footer-note">SELA akan menjawab berdasarkan data yang sedang aktif. Jika datanya belum tersedia di dashboard, saya akan memberi tahu secara jujur.</div>
      </div>
    </div>
  </div>

  <script>
    const payload = ___SELA_PAYLOAD___;
    const metrics = payload.metrics || {};
    const periodStats = payload.period_stats || [];
    const yearStats = payload.year_stats || [];
    const trxStats = payload.transaction_stats || [];
    const vendorStats = payload.vendor_stats || [];
    const nomorStats = payload.nomor_stats || [];
    const prosesStats = payload.proses_stats || [];
    const processYearStats = payload.process_year_stats || [];
    const processMonthStats = payload.process_month_stats || [];
    const processPeriodStats = payload.process_period_stats || [];
    const processTransactionYearStats = payload.process_transaction_year_stats || [];
    const processTransactionMonthStats = payload.process_transaction_month_stats || [];
    const processVendorYearStats = payload.process_vendor_year_stats || [];
    const processVendorMonthStats = payload.process_vendor_month_stats || [];
    const records = payload.sample_records || [];
    const historyYears = payload.history_year_stats || [];
    const historyMonths = payload.history_month_stats || [];
    // Keep legacy quick questions; adapt new examples to the years actually uploaded.
    const exampleYears = historyYears.map(item => String(item.year)).sort().slice(-3);
    if(exampleYears.length >= 2){
      const yearLabel = exampleYears.join(', ');
      document.querySelectorAll('.chip').forEach(button => {
        const q = button.dataset.question || '';
        if(q.startsWith('Bandingkan jumlah transaksi tahun '))
          button.dataset.question = 'Bandingkan jumlah transaksi tahun ' + yearLabel;
        if(q.startsWith('Bandingkan SLA Keuangan tahun '))
          button.dataset.question = 'Bandingkan SLA Keuangan tahun ' + yearLabel;
      });
    }

    const speechBubble = document.getElementById('speechBubble');
    const heroCaption = document.getElementById('heroCaption');
    const statusLine = document.getElementById('statusLine');
    const chatbox = document.getElementById('chatbox');
    const textInput = document.getElementById('textInput');
    const micBtn = document.getElementById('micBtn');
    const sendBtn = document.getElementById('sendBtn');
    const checkMicBtn = document.getElementById('checkMicBtn');
    const testVoiceBtn = document.getElementById('testVoiceBtn');
    const stopVoiceBtn = document.getElementById('stopVoiceBtn');
    const femaleAvatar = document.getElementById('femaleAvatar');
    const lipSyncMouth = document.querySelector('.lip-sync-mouth');
    const voiceSelect = document.getElementById('voiceSelect');
    const advisorOverview = document.getElementById('advisorOverview');
    const advisorCharts = document.getElementById('advisorCharts');
    const advisorTables = document.getElementById('advisorTables');
    const advisorPoster = document.getElementById('advisorPoster');
    const advisorBriefing = document.getElementById('advisorBriefing');
    const advisorStatus = document.getElementById('advisorStatus');
    const advisorBodies = document.querySelectorAll('.advisor-body');
    const advisorTabs = document.querySelectorAll('.advisor-tab');

    function fmtNum(n){
      if(n === null || n === undefined || Number.isNaN(Number(n))) return '-';
      return new Intl.NumberFormat('id-ID').format(Number(n));
    }
    function fmtPct(n){
      if(n === null || n === undefined || Number.isNaN(Number(n))) return '-';
      const v = Number(n);
      return (v > 0 ? '+' : '') + v.toLocaleString('id-ID', {maximumFractionDigits:2, minimumFractionDigits:2}) + '%';
    }
    function fmtDays(d){
      if(d === null || d === undefined || Number.isNaN(Number(d))) return '-';
      const v = Number(d);
      const totalSec = Math.round(v * 86400);
      const day = Math.floor(totalSec/86400);
      const hr = Math.floor((totalSec%86400)/3600);
      const mn = Math.floor((totalSec%3600)/60);
      if(day > 0) return `${day} hari ${hr} jam ${mn} menit`;
      if(hr > 0) return `${hr} jam ${mn} menit`;
      return `${mn} menit`;
    }
    function normalize(s){ return String(s||'').toLowerCase().trim(); }
    function addMsg(role, text){
      const div = document.createElement('div');
      div.className = `msg ${role === 'user' ? 'user' : 'bot'}`;
      const content = document.createElement('span');
      content.textContent = String(text == null ? '' : text);
      content.style.whiteSpace = 'pre-wrap';
      const author = document.createElement('small');
      author.textContent = role === 'bot' ? 'SELA' : 'Anda';
      div.appendChild(content);
      div.appendChild(author);
      chatbox.appendChild(div);
      chatbox.scrollTop = chatbox.scrollHeight;
    }
    function setBubble(text){ speechBubble.textContent = text; heroCaption.textContent = text; }
    // SELA v16: irregular eyelid motion and word-aware, restrained lip expressions.
    // Browser speech boundary callbacks are approximate; never claim phoneme-perfect sync.
    const blinkOverlay = document.getElementById('selaBlinkOverlay');
    const faceScene = document.getElementById('selaFaceScene');
    const mouthSprites = [
      document.getElementById('selaMouthSoft'),
      document.getElementById('selaMouthMedium'),
      document.getElementById('selaMouthOpen'),
      document.getElementById('selaMouthRound')
    ];
    const mouthDemoBtn = document.getElementById('selaMouthDemoBtn');
    const faceStatus = document.getElementById('selaFaceStatus');
    let blinkTimer = null;
    let mouthAnimFrame = null;
    let mouthSpeaking = false;
    let mouthDemoTimer = null;
    let mouthStartAt = 0;
    let mouthChangeAt = 0;
    let mouthTargetShape = 0;
    let mouthFrameIndex = 0;
    let mouthText = '';
    let lastWordCueAt = 0;
    let lastWordCue = '';
    let speakingGeneration = 0;
    const shapeOpacity = [0,0,0,0];
    const expressionSequence = [1,2,1,3,2,4,2,1,0,1,3,2,1,4,2,0,2,3,1,0];

    function selaBlinkNow(){
      if(!blinkOverlay || document.hidden) return;
      blinkOverlay.classList.remove('blinking');
      // Restart the keyframe without calculating layout across the whole dashboard.
      void blinkOverlay.offsetWidth;
      blinkOverlay.classList.add('blinking');
    }
    function scheduleSelaBlink(){
      if(blinkTimer) window.clearTimeout(blinkTimer);
      // Natural timing: 2.7-6.5s, with occasional double blink.
      blinkTimer = window.setTimeout(() => {
        if(!document.hidden){
          selaBlinkNow();
          if(Math.random() < .15) window.setTimeout(selaBlinkNow, 260);
        }
        scheduleSelaBlink();
      }, 2700 + Math.random() * 3800);
    }
    scheduleSelaBlink();
    document.addEventListener('visibilitychange', () => {
      if(!document.hidden) scheduleSelaBlink();
    });
    // SELA v17: visible mouth visemes with continuous timing fallback.
    // Word boundaries help approximate speech, but are NOT required to animate.
    function selaSetMouth(value){
      // Compatibility with v16 callers: 0=closed, 0..1 maps to available visemes.
      const v = Math.max(0, Math.min(1, Number(value) || 0));
      mouthTargetShape = v <= .07 ? 0 : v < .30 ? 1 : v < .54 ? 2 : v < .79 ? 3 : 4;
      if(!mouthAnimFrame) mouthAnimFrame = requestAnimationFrame(animateMouth);
    }
    function selectWordViseme(word){
      const w = String(word || '').toLowerCase();
      if(w.indexOf('o') >= 0 || w.indexOf('u') >= 0) return 4;
      if(w.indexOf('a') >= 0) return 3;
      if(w.indexOf('e') >= 0 || w.indexOf('i') >= 0) return 2;
      return 1;
    }
    function startSmoothMouth(text){
      mouthSpeaking = true;
      mouthStartAt = performance.now();
      mouthChangeAt = mouthStartAt - 1;
      mouthFrameIndex = 0;
      lastWordCueAt = 0;
      lastWordCue = '';
      mouthText = String(text || '');
      mouthTargetShape = 1;
      if(faceStatus) faceStatus.textContent = '● BERBICARA';
      if(!mouthAnimFrame) mouthAnimFrame = requestAnimationFrame(animateMouth);
    }
    function stopSmoothMouth(){
      mouthSpeaking = false;
      mouthTargetShape = 0;
      lastWordCueAt = 0;
      if(!mouthAnimFrame && shapeOpacity.some(v => v > .01)){
        mouthAnimFrame = requestAnimationFrame(animateMouth);
      }
      if(!mouthAnimFrame){
        mouthSprites.forEach(img => {if(img) img.style.opacity='0';});
      }
      if(faceStatus) faceStatus.textContent = '● SIAP';
    }
    function cueMouthBoundary(text){
      // Browser boundary events can be missing or intermittent; fallback continues.
      lastWordCue = String(text || '').slice(0,40);
      lastWordCueAt = performance.now();
      mouthTargetShape = selectWordViseme(lastWordCue);
      mouthChangeAt = lastWordCueAt + 80;
    }
    function animateMouth(ts){
      mouthAnimFrame = null;
      if(!mouthSprites[0]) return;
      if(document.hidden){
        // Do not render frames while tab is hidden. Resume when visible.
        return;
      }
      if(mouthSpeaking && ts >= mouthChangeAt){
        const pattern = expressionSequence[mouthFrameIndex % expressionSequence.length];
        const elapsed = Math.max(0, ts - mouthStartAt);
        const wordFresh = lastWordCueAt && ts-lastWordCueAt < 260;
        let next = wordFresh && mouthFrameIndex % 2 === 0 ? selectWordViseme(lastWordCue) : pattern;
        // Brief closures at phrase boundaries make it feel less mechanical.
        if((mouthFrameIndex % 13 === 12) || (mouthFrameIndex % 19 === 18)) next=0;
        if(elapsed < 140) next=1;
        mouthTargetShape = next;
        mouthFrameIndex++;
        mouthChangeAt = ts + 105 + (mouthFrameIndex % 3)*21 + Math.random()*22;
      }
      let active=false;
      for(let i=0;i<mouthSprites.length;i++){
        const img=mouthSprites[i];
        if(!img) continue;
        const goal=mouthTargetShape === i+1 ? 1 : 0;
        // Fade old mouth promptly to avoid two visemes overlapping as a dark patch.
        shapeOpacity[i] += (goal-shapeOpacity[i])*(goal ? .46 : .78);
        if(Math.abs(shapeOpacity[i]-goal)<.004) shapeOpacity[i]=goal;
        img.style.opacity=String(shapeOpacity[i]);
        if(shapeOpacity[i]>.008 || (mouthSpeaking && goal>0)) active=true;
      }
      if(mouthSpeaking || active) mouthAnimFrame=requestAnimationFrame(animateMouth);
    }
    function setAvatarState(state){
      femaleAvatar.classList.remove('speaking','listening');
      if(state) femaleAvatar.classList.add(state);
      if(state === 'speaking') startSmoothMouth();
      else {
        stopSmoothMouth();
        if(state === 'listening' && faceStatus) faceStatus.textContent='● MENDENGARKAN';
      }
    }
    function selaDemoExpressions(){
      // Standalone QA, not a fake audible response: explicitly labels silent animation.
      if(mouthDemoTimer){clearTimeout(mouthDemoTimer);mouthDemoTimer=null;}
      speakingGeneration++;
      if('speechSynthesis' in window) window.speechSynthesis.cancel();
      setAvatarState('speaking');
      mouthText = 'Halo saya SELA. Saya siap membantu analisis SLA dan laporan Anda.';
      if(faceStatus) faceStatus.textContent = '● DEMO ANIMASI';
      if(mouthDemoBtn) mouthDemoBtn.textContent = '● Demo berjalan…';
      statusLine.textContent='Status: demo ekspresi 6 detik (tanpa suara).';
      mouthDemoTimer=setTimeout(()=>{
        mouthDemoTimer=null;
        setAvatarState('');
        if(mouthDemoBtn) mouthDemoBtn.textContent='▶ Demo Ekspresi · 6 dtk';
        statusLine.textContent='Status: demo selesai. Klik Uji Suara untuk mencoba bicara sungguhan.';
      },6000);
    }

    function populateMetrics(){
      document.getElementById('metricCount').textContent = fmtNum(metrics.transaction_count || 0);
      document.getElementById('metricPeriod').textContent = `${metrics.period_first || '-'} s.d. ${metrics.period_last || '-'}`;
      document.getElementById('metricSLA').textContent = fmtDays(metrics.avg_sla_days || 0);
      document.getElementById('metricBottleneck').textContent = `Bottleneck: ${(metrics.bottleneck && metrics.bottleneck.name) ? metrics.bottleneck.name : '-'}`;
      document.getElementById('metricGrowth').textContent = fmtPct(metrics.latest_growth_pct);
      document.getElementById('metricTopTrx').textContent = (metrics.top_transaction && metrics.top_transaction.name) ? metrics.top_transaction.name : '-';
      document.getElementById('metricTopVendor').textContent = `Vendor: ${(metrics.top_vendor && metrics.top_vendor.name) ? metrics.top_vendor.name : '-'}`;
      if(metrics.latest_count && metrics.prev_count){
        document.getElementById('metricGrowthSub').textContent = `${fmtNum(metrics.prev_count)} \u2192 ${fmtNum(metrics.latest_count)} transaksi`;
      }
    }

    // Voices
    let availableVoices = [];
    function loadVoices(){
      if(!('speechSynthesis' in window)) return;
      availableVoices = window.speechSynthesis.getVoices() || [];
      const preferred = availableVoices.filter(v => /id|indonesia/i.test(v.lang + ' ' + v.name));
      const femaleHints = (preferred.length ? preferred : availableVoices).filter(v => /female|zira|siti|gadis|woman|indonesia/i.test(v.name.toLowerCase()) || /id/i.test(v.lang.toLowerCase()));
      const list = femaleHints.length ? femaleHints : (preferred.length ? preferred : availableVoices);
      voiceSelect.innerHTML = '';
      list.forEach((v, idx) => {
        const opt = document.createElement('option');
        opt.value = v.name; opt.textContent = `${v.name} (${v.lang})`;
        if(idx === 0) opt.selected = true;
        voiceSelect.appendChild(opt);
      });
      if(!list.length){
        const opt = document.createElement('option');
        opt.textContent = 'Voice browser default';
        voiceSelect.appendChild(opt);
      }
    }
    if('speechSynthesis' in window){
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
    function pickVoice(){
      const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
      const chosen = voiceSelect.value;
      return voices.find(v => v.name === chosen) || voices.find(v => /id|indonesia/i.test(v.lang + ' ' + v.name)) || null;
    }
    function speak(text){
      // Keep browser-native Indonesian speech. Start expression on the same user action
      // even when some Chrome voices do not emit the first onboundary/onstart promptly.
      if(mouthDemoTimer){clearTimeout(mouthDemoTimer);mouthDemoTimer=null;}
      if(mouthDemoBtn) mouthDemoBtn.textContent='▶ Demo Ekspresi · 6 dtk';
      if(!('speechSynthesis' in window)){
        setAvatarState('');
        statusLine.textContent='Status: suara browser tidak tersedia. Anda dapat mencoba Demo Ekspresi.';
        return;
      }
      const sequence=++speakingGeneration;
      window.speechSynthesis.cancel();
      const utt=new SpeechSynthesisUtterance(String(text || ''));
      utt.lang='id-ID';
      const voice=pickVoice();
      try { if(voice) utt.voice=voice; }
      catch(err) { /* Keep browser default voice if the selected voice is unsupported. */ }
      utt.rate=.98;
      utt.pitch=1.12;
      utt.volume=1;
      let started=false;
      let finished=false;
      setAvatarState('speaking');
      mouthText=utt.text;
      cineStartSubtitle(utt.text);
      statusLine.textContent='Status: SELA menyiapkan suara dan ekspresi.';
      utt.onstart=()=>{
        if(sequence!==speakingGeneration) return;
        started=true;
        if(!mouthSpeaking) setAvatarState('speaking');
        mouthText=utt.text;
        statusLine.textContent='Status: SELA sedang berbicara.';
      };
      utt.onboundary=(event)=>{
        if(sequence!==speakingGeneration || !event) return;
        const at=Math.max(0,Number(event.charIndex || 0));
        const raw=String(utt.text).slice(at);
        const word=raw.split(/[^A-Za-z0-9]+/)[0] || '';
        cueMouthBoundary(word);
        cineSubtitleBoundary(at);
      };
      utt.onpause=()=>{
        if(sequence!==speakingGeneration) return;
        mouthTargetShape=0;
        if(faceStatus) faceStatus.textContent='● JEDA';
      };
      utt.onresume=()=>{
        if(sequence!==speakingGeneration) return;
        if(faceStatus) faceStatus.textContent='● BERBICARA';
      };
      const done=(error)=>{
        if(sequence!==speakingGeneration || finished) return;
        finished=true;
        setAvatarState('');
        cineStopSubtitle();
        statusLine.textContent=error ?
          'Status: suara tidak tersedia atau terhenti. Coba Uji Suara / pilih voice lain.' :
          'Status: SELA siap membantu pertanyaan berikutnya.';
      };
      utt.onend=()=>done(false);
      utt.onerror=()=>done(true);
      try{
        window.speechSynthesis.speak(utt);
        // Fail gracefully for browser policies: never animate indefinitely without speech.
        setTimeout(()=>{
          if(sequence!==speakingGeneration || finished || started) return;
          if(!window.speechSynthesis.speaking && !window.speechSynthesis.pending){
            done(true);
          }
        }, 2800);
      }catch(err){done(true);}
    }

    function topByName(arr, name){
      return arr.find(x => normalize(x.name) === normalize(name));
    }
    function periodByName(name){
      return periodStats.find(x => normalize(x.periode) === normalize(name));
    }
    function extractYear(text){ const m = String(text).match(/(20\\d{2})/); return m ? m[1] : null; }
    const MONTH_DEFS = [
      ['januari','jan','january'], ['februari','feb','february'], ['maret','mar','march'], ['april','apr'], ['mei','may'], ['juni','jun','june'],
      ['juli','jul','july'], ['agustus','agus','agt','agu','august','aug'], ['september','sep','sept'], ['oktober','okt','october','oct'], ['november','nov'], ['desember','des','december','dec']
    ];
    const MONTH_NAMES_ID = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];
    function extractMonthYear(text){
      const lower = normalize(text);
      const year = extractYear(text);
      if(!year) return null;
      let month = null;
      for(let i=0;i<MONTH_DEFS.length;i++){
        for(const label of MONTH_DEFS[i]){
          const re = new RegExp('(^|[^a-z])' + label + '([^a-z]|$)', 'i');
          if(re.test(lower)){ month = i + 1; break; }
        }
        if(month) break;
      }
      if(!month){
        const patterns = [/20\\d{2}[^0-9]([01]?\\d)/, /([01]?\\d)[^0-9]20\\d{2}/];
        for(const pat of patterns){
          const m = lower.match(pat);
          if(m){ const cand = Number(m[1]); if(cand >= 1 && cand <= 12){ month = cand; break; } }
        }
      }
      if(!month) return null;
      return {year: String(year), month, monthName: MONTH_NAMES_ID[month-1], monthKey: `${year}-${String(month).padStart(2,'0')}`};
    }
    function findMentionedPeriod(text){
      const lower = normalize(text);
      const item = periodStats.find(p => lower.includes(normalize(p.periode)));
      return item || null;
    }
    function findNaturalMonthRow(text, source){
      const my = extractMonthYear(text);
      if(!my) return null;
      const arr = source || processMonthStats;
      return arr.find(p => p.month_key === my.monthKey) || arr.find(p => String(p.year) === my.year && Number(p.month) === Number(my.month)) || null;
    }
    function findMentionedTransaction(text){
      const lower = normalize(text);
      return trxStats.find(t => lower.includes(normalize(t.name)));
    }
    function findMentionedVendor(text){
      const lower = normalize(text);
      return vendorStats.find(t => lower.includes(normalize(t.name)));
    }
    function findMentionedNomor(text){
      const lower = normalize(text);
      return nomorStats.find(t => lower.includes(normalize(t.name)));
    }

    function detectProcess(text){
      const q = normalize(text);
      if(/total\\s*waktu|sla\\s*total|total sla|keseluruhan/.test(q)) return 'TOTAL WAKTU';
      if(/perbendaharaan|treasury/.test(q)) return 'PERBENDAHARAAN';
      if(/keuangan|finance/.test(q)) return 'KEUANGAN';
      if(/fungsional|fungsi|user/.test(q)) return 'FUNGSIONAL';
      if(/sla\\s+vendor|proses\\s+vendor|vendor\\s+periode|vendor\\s+tahun|vendor\\s+20\\d{2}/.test(q)) return 'VENDOR';
      return null;
    }
    function prettyProcessName(p){
      if(!p) return '-';
      return p.replace('TOTAL WAKTU','Total Waktu').replace('PERBENDAHARAAN','Perbendaharaan').replace('KEUANGAN','Keuangan').replace('FUNGSIONAL','Fungsional').replace('VENDOR','Vendor');
    }
    function findMonthYearPeriod(text){
      const explicit = findMentionedPeriod(text);
      if(explicit) return explicit;
      return findNaturalMonthRow(text, processMonthStats) || findNaturalMonthRow(text, processPeriodStats) || null;
    }
    function describeMonth(myRow){
      if(!myRow) return '';
      if(myRow.month_name && myRow.year) return `${myRow.month_name} ${myRow.year}`;
      return myRow.periode || myRow.month_key || 'periode yang diminta';
    }
    function answerProcessSLA(q){
      const process = detectProcess(q);
      if(!process || !/sla|berapa|rata|waktu|durasi/.test(q)) return null;
      const year = extractYear(q);
      const monthInfo = extractMonthYear(q);
      const monthRow = findMonthYearPeriod(q);
      const trxObj = findMentionedTransaction(q);
      const vendorObj = findMentionedVendor(q);

      // Month-level answer takes priority over year-level answer.
      if(monthInfo && trxObj){
        const row = processTransactionMonthStats.find(x => x.month_key === monthInfo.monthKey && normalize(x.name) === normalize(trxObj.name));
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Untuk jenis transaksi ${trxObj.name} pada ${monthInfo.monthName} ${monthInfo.year}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      if(monthInfo && vendorObj && !/sla\\s+vendor/.test(q)){
        const row = processVendorMonthStats.find(x => x.month_key === monthInfo.monthKey && normalize(x.name) === normalize(vendorObj.name));
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Untuk vendor ${vendorObj.name} pada ${monthInfo.monthName} ${monthInfo.year}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      if(monthInfo || monthRow){
        const row = monthRow || processMonthStats.find(x => x.month_key === monthInfo.monthKey);
        if(row && row[process] !== undefined && row[process] !== null){
          const periodLabel = monthInfo ? `${monthInfo.monthName} ${monthInfo.year}` : describeMonth(row);
          const extra = row['TOTAL WAKTU'] !== undefined && process !== 'TOTAL WAKTU' ? ` Sebagai pembanding, rata-rata Total Waktu pada periode tersebut adalah ${fmtDays(row['TOTAL WAKTU'])}.` : '';
          return `${naturalLead()} Rata-rata SLA ${prettyProcessName(process)} untuk periode ${periodLabel} adalah ${fmtDays(row[process])}, dihitung dari ${fmtNum(row.count)} transaksi.${extra}`;
        }
        if(monthInfo){
          return `Saya belum menemukan data SLA ${prettyProcessName(process)} untuk periode ${monthInfo.monthName} ${monthInfo.year} pada filter aktif.`;
        }
      }

      if(year && trxObj){
        const row = processTransactionYearStats.find(x => String(x.year) === String(year) && normalize(x.name) === normalize(trxObj.name));
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Untuk jenis transaksi ${trxObj.name} pada tahun ${year}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      if(year && vendorObj && !/sla\\s+vendor/.test(q)){
        const row = processVendorYearStats.find(x => String(x.year) === String(year) && normalize(x.name) === normalize(vendorObj.name));
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Untuk vendor ${vendorObj.name} pada tahun ${year}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      if(year){
        const row = processYearStats.find(x => String(x.year) === String(year));
        if(row && row[process] !== undefined && row[process] !== null){
          const extra = row['TOTAL WAKTU'] !== undefined && process !== 'TOTAL WAKTU' ? ` Sebagai pembanding, rata-rata Total Waktu pada tahun tersebut adalah ${fmtDays(row['TOTAL WAKTU'])}.` : '';
          return `${naturalLead()} Rata-rata SLA ${prettyProcessName(process)} untuk tahun ${year} adalah ${fmtDays(row[process])}, dihitung dari ${fmtNum(row.count)} transaksi.${extra}`;
        }
        return `Saya belum menemukan data SLA ${prettyProcessName(process)} untuk tahun ${year} pada filter aktif.`;
      }
      const periodObj = findMentionedPeriod(q);
      if(periodObj){
        const row = processPeriodStats.find(x => normalize(x.periode) === normalize(periodObj.periode)) || periodObj;
        if(row && row[process] !== undefined && row[process] !== null){
          return `${naturalLead()} Pada periode ${row.periode}, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(row[process])} dari ${fmtNum(row.count)} transaksi.`;
        }
      }
      const rowAll = prosesStats.find(x => normalize(x.name) === normalize(process));
      if(rowAll){
        if(rowAll.avg_sla_days === null || rowAll.avg_sla_days === undefined){
          return `Belum tersedia durasi SLA ${prettyProcessName(process)} yang valid pada filter aktif.`;
        }
        return `${naturalLead()} Pada seluruh data aktif, rata-rata SLA ${prettyProcessName(process)} adalah ${fmtDays(rowAll.avg_sla_days)} dari ${fmtNum(rowAll.valid_count)} baris dengan SLA valid.`;
      }
      return null;
    }

    function naturalLead(){
      const leads = [
        'Baik, saya bantu jelaskan ya.',
        'Siap, saya bacakan hasil analisisnya ya.',
        'Oke, dari data yang sedang aktif saya lihat seperti ini.',
        'Tentu, saya rangkum secara singkat ya.',
        'Baik, berdasarkan data yang tersedia hasilnya seperti ini.'
      ];
      return leads[Math.floor(Math.random() * leads.length)];
    }
    function recommendationText(){
      const topTrx = metrics.top_transaction;
      const bottleneck = metrics.bottleneck;
      let rec = [];
      if(topTrx){
        rec.push(`Prioritaskan evaluasi jenis transaksi ${topTrx.name} karena rata-rata SLA-nya mencapai ${fmtDays(topTrx.avg_sla_days || 0)}.`);
      }
      if(bottleneck){
        rec.push(`Lakukan pendalaman pada proses ${bottleneck.name} karena saat ini menjadi bottleneck terbesar dengan rata-rata ${fmtDays(bottleneck.avg_sla_days || 0)}.`);
      }
      if(metrics.latest_growth_pct !== null && metrics.latest_growth_pct !== undefined){
        if(Number(metrics.latest_growth_pct) > 0){
          rec.push(`Karena volume transaksi terakhir tumbuh ${fmtPct(metrics.latest_growth_pct)}, monitoring kapasitas proses dan aging dokumen perlu diperketat.`);
        } else if(Number(metrics.latest_growth_pct) < 0){
          rec.push(`Walau volume transaksi turun ${fmtPct(metrics.latest_growth_pct)}, percepatan SLA tetap perlu dijaga agar perbaikan kinerja konsisten.`);
        }
      }
      return rec.join(' ');
    }

    // SELA v11: deterministic evidence layer based on source-versioned monthly aggregates.
    // No external API calls; no dependency added; historical comparison never changes global filters.
    function selaMentionedYears(text){
      const raw = String(text);
      const matches = raw.match(/(?:19|20)[0-9]{2}/g) || [];
      const years = [...new Set(matches)].sort();
      const span = raw.match(/((?:19|20)[0-9]{2})[ ]*(?:sampai|hingga|s[.]?d[.]?|[-–])[ ]*((?:19|20)[0-9]{2})/i);
      if(span){
        const start = Number(span[1]), end = Number(span[2]);
        if(end >= start && end-start <= 30){
          const available = historyYears.map(y => String(y.year));
          return available.filter(y => Number(y) >= start && Number(y) <= end);
        }
      }
      return years;
    }
    function selaIsComparison(text){
      return /(bandingkan|perbandingan|dibandingkan|dibanding|versus| vs |komparasi|compare|sampai|hingga|antar tahun)/i.test(text);
    }
    function selaMetric(text){
      if(/(jumlah|total|volume)[ ]+transaksi/.test(text)) return 'count';
      const detected = detectProcess(text);
      if(detected && /(sla|durasi|waktu|rata|proses)/i.test(text)) return detected;
      return /(sla|durasi|rata-rata waktu)/i.test(text) ? 'TOTAL WAKTU' : 'count';
    }
    function selaEvidence(scope, n){
      return `\nDasar data: ${scope}; ${fmtNum(n)} transaksi dari file unggahan. SLA (jika ditampilkan) dihitung dari durasi valid.`;
    }
    function selaCleanNumber(num){
      return (num == null || !Number.isFinite(Number(num))) ? null : Number(num);
    }
    function selaMonthYearMentions(text){
      const found = [];
      const q = normalize(text);
      MONTH_DEFS.forEach((variants, index) => {
        variants.forEach(label => {
          const rx = new RegExp('(?:^|[^a-z])' + label + '[ -]+((?:19|20)[0-9]{2})(?![0-9])', 'g');
          for(const match of q.matchAll(rx)){
            found.push(`${match[1]}-${String(index+1).padStart(2,'0')}`);
          }
        });
      });
      for(const m of q.matchAll(/((?:19|20)[0-9]{2})[-/]([01]?[0-9])/g)){
        const month = Number(m[2]);
        if(month >= 1 && month <= 12) found.push(`${m[1]}-${String(month).padStart(2,'0')}`);
      }
      return [...new Set(found)].sort();
    }
    function selaAggregateYear(year, horizon, metric){
      const months = historyMonths.filter(m => String(m.year) === String(year) && m.month <= horizon);
      if(!months.length) return null;
      const total = months.reduce((acc, m) => acc + Number(m.count || 0), 0);
      const coverage = new Set(months.map(m => Number(m.month))).size;
      const missing = Array.from({length:horizon}, (_, i) => i + 1)
                           .filter(month => !months.some(m => Number(m.month) === month));
      if(metric === 'count') return {year, value:total, count:total, coverage, missing};
      const n = months.reduce((acc, m) => acc + Number(m[metric + '_valid'] || 0), 0);
      const s = months.reduce((acc, m) => acc + Number(m[metric + '_sum_seconds'] || 0), 0);
      return {year, value:n ? s/n/86400 : null, count:total, valid:n, coverage, missing};
    }
    function selaCompareYears(text){
      if(!selaIsComparison(text)) return null;
      const years = selaMentionedYears(text);
      if(years.length < 2) return null;
      const metric = selaMetric(text);
      const validYears = years.map(year => historyYears.find(y => String(y.year) === year));
      const absent = years.filter((year, i) => !validYears[i]);
      if(absent.length){
        return `Belum tersedia data untuk tahun ${absent.join(', ')} pada file yang diunggah. Tahun tersedia: ${historyYears.map(y=>y.year).join(', ') || '-'}.`;
      }
      const horizon = Math.min(...validYears.map(y => Number(y.latest_month || 12)));
      const snapshots = years.map(year => selaAggregateYear(year, horizon, metric));
      if(snapshots.some(s => !s)) return 'Data perbandingan belum memadai untuk tahun yang dipilih.';
      const title = metric === 'count' ? 'Jumlah transaksi' : `Rata-rata SLA ${prettyProcessName(metric)}`;
      const pieces = snapshots.map(s => `${s.year}: ${metric==='count' ? fmtNum(s.value)+' transaksi' : fmtDays(s.value)} (data ${s.coverage}/${horizon} bulan${metric!=='count' ? ', SLA valid '+fmtNum(s.valid) : ''})`);
      const gaps = snapshots.filter(s => s.missing.length > 0);
      let answer = `${title} untuk horizon Januari–${MONTH_NAMES_ID[horizon-1]}: ${pieces.join('; ')}.`;
      const base = snapshots[0];
      if(base.value !== null){
        const comparisons = snapshots.slice(1).map(s => {
          if(s.value === null) return `${s.year}: data SLA valid tidak tersedia`;
          const difference = s.value - base.value;
          const growth = base.value === 0 ? null : difference/base.value*100;
          const direction = difference > 0 ? 'naik' : difference < 0 ? 'turun' : 'tetap';
          return `${s.year} vs ${base.year}: ${direction} ${metric==='count' ? fmtNum(Math.abs(difference))+' transaksi' : fmtDays(Math.abs(difference))}${growth === null ? '' : ' ('+fmtPct(growth)+')'}`;
        });
        answer += ` Perbandingan terhadap ${base.year}: ${comparisons.join('; ')}.`;
      }
      if(metric !== 'count'){
        const available = snapshots.filter(s => s.value !== null);
        if(available.length){
          const fastest = available.reduce((best, s) => s.value < best.value ? s : best);
          answer += ` SLA rata-rata paling cepat di antara tahun terpilih adalah ${fastest.year} (${fmtDays(fastest.value)}).`;
        }
      } else {
        const best = snapshots.reduce((best, s) => s.value > best.value ? s : best);
        answer += ` Volume terbesar terdapat pada ${best.year} (${fmtNum(best.value)} transaksi).`;
      }
      if(gaps.length) answer += ' Perhatian: ada bulan yang tidak tersedia pada ' + gaps.map(s => s.year).join(', ') + '; bulan kosong tidak dianggap nol.';
      answer += selaEvidence(`histori seluruh unggahan, horizon Jan–${MONTH_NAMES_ID[horizon-1]}, tahun ${years.join(', ')}`,
                             snapshots.reduce((a,s)=>a+s.count,0));
      return answer;
    }
    function selaCompareMonths(text){
      if(!selaIsComparison(text)) return null;
      const keys = selaMonthYearMentions(text);
      if(keys.length < 2) return null;
      const rows = keys.map(key => historyMonths.find(row => row.month_key === key));
      const missing = keys.filter((key, index) => !rows[index]);
      if(missing.length){
        return `Data periode ${missing.join(', ')} belum ada di histori unggahan. Tidak saya anggap sebagai nol transaksi.`;
      }
      const metric = selaMetric(text);
      const vals = rows.map(row => ({
        label: `${MONTH_NAMES_ID[Number(row.month)-1]} ${row.year}`,
        count: Number(row.count || 0),
        value: metric === 'count' ? Number(row.count || 0) : selaCleanNumber(row[metric]),
        valid: metric === 'count' ? Number(row.count || 0) : Number(row[metric+'_valid'] || 0)
      }));
      let response = `Perbandingan ${metric === 'count' ? 'jumlah transaksi' : 'SLA '+prettyProcessName(metric)}: ` +
        vals.map(v => `${v.label}: ${metric === 'count' ? fmtNum(v.value)+' transaksi' : fmtDays(v.value)} (n=${fmtNum(v.valid)})`).join('; ') + '.';
      const first = vals[0];
      if(first.value !== null && first.value !== 0){
        response += ' Perubahan terhadap '+ first.label + ': ' + vals.slice(1).map(v =>
          `${v.label} ${v.value === null ? 'tidak tersedia' : fmtPct((v.value-first.value)/first.value*100)}`
        ).join('; ') + '.';
      }
      return response + selaEvidence('histori unggahan untuk '+vals.map(v=>v.label).join(', '), vals.reduce((n,v)=>n+v.count,0));
    }
    function selaHistoricalSingle(text){
      const q = normalize(text);
      const years = selaMentionedYears(q);
      const metric = selaMetric(q);
      const wantsNumbers = /(jumlah transaksi|total transaksi|volume transaksi|sla|durasi|rata-rata waktu)/.test(q);
      if(!wantsNumbers || years.length !== 1) return null;
      // Keep existing transaction/vendor-specific drilldowns on their own route.
      if(findMentionedTransaction(q) || findMentionedVendor(q) || findMentionedNomor(q)) return null;
      const monthKeys = selaMonthYearMentions(q);
      if(monthKeys.length === 1){
        const row = historyMonths.find(m => m.month_key === monthKeys[0]);
        if(!row) return `Periode ${monthKeys[0]} belum tersedia pada histori upload.`;
        const value = metric === 'count' ? row.count : row[metric];
        return `${MONTH_NAMES_ID[Number(row.month)-1]} ${row.year}: ${metric==='count'?'jumlah transaksi':'rata-rata SLA '+prettyProcessName(metric)} adalah ${metric==='count'?fmtNum(value)+' transaksi':fmtDays(value)}.` +
               selaEvidence('histori unggahan '+row.month_key, row.count);
      }
      const row = historyYears.find(item => String(item.year) === years[0]);
      if(!row) return `Tahun ${years[0]} tidak ditemukan pada histori unggahan.`;
      const value = metric === 'count' ? row.count : row[metric];
      return `${row.year}: ${metric==='count'?'jumlah transaksi':'rata-rata SLA '+prettyProcessName(metric)} adalah ${metric==='count'?fmtNum(value)+' transaksi':fmtDays(value)} (cakupan ${row.month_count}/12 bulan).` +
             selaEvidence('histori unggahan tahun '+row.year, row.count);
    }
    function selaStageBreakdown(text){
      const q = normalize(text);
      const request = /(bottleneck|tahapan|proses paling lama)/.test(q);
      const detail = /(tiap|semua|masing|detail|rincian|setiap)/.test(q);
      if(!request || !detail) return null;
      const stages = prosesStats.filter(p => p.is_stage && p.avg_sla_days !== null && p.avg_sla_days !== undefined && p.valid_count > 0);
      if(!stages.length) return 'Belum tersedia SLA tahapan proses yang valid pada filter aktif.';
      const points = stages.map(s => `${prettyProcessName(s.name)}: ${fmtDays(s.avg_sla_days)} (n=${fmtNum(s.valid_count)})`);
      const first = stages[0];
      return `Urutan SLA tiap tahapan proses berdasarkan rata-rata terbesar: ${points.join('; ')}. ` +
             `Tahap paling lama adalah ${prettyProcessName(first.name)}. TOTAL WAKTU tidak dihitung sebagai tahap karena merupakan durasi keseluruhan.` +
             selaEvidence(`filter aktif ${metrics.period_first}–${metrics.period_last}`, Number(metrics.transaction_count || 0));
    }
    function selaHistoricalBottleneck(text){
      const q = normalize(text);
      if(!/(bottleneck|proses paling lama|hambatan)/.test(q)) return null;
      const years = selaMentionedYears(q);
      if(years.length !== 1) return null;
      const monthKeys = selaMonthYearMentions(q);
      const src = monthKeys.length === 1
        ? historyMonths.find(m => m.month_key === monthKeys[0])
        : historyYears.find(y => String(y.year) === years[0]);
      if(!src) return `Data bottleneck untuk ${monthKeys[0] || years[0]} tidak tersedia di histori upload.`;
      const stages = ['FUNGSIONAL','VENDOR','KEUANGAN','PERBENDAHARAAN']
          .filter(name => src[name] !== null && src[name] !== undefined && src[name+'_valid'] > 0)
          .map(name => ({name, avg: Number(src[name]), valid: Number(src[name+'_valid'])}));
      if(!stages.length) return 'Data tahapan SLA valid belum tersedia pada periode tersebut.';
      stages.sort((a,b) => b.avg-a.avg);
      return `Bottleneck historis ${monthKeys.length ? monthKeys[0] : years[0]} adalah ${prettyProcessName(stages[0].name)} dengan rata-rata ${fmtDays(stages[0].avg)}. `+
             `Rincian: ${stages.map(p=>prettyProcessName(p.name)+' '+fmtDays(p.avg)).join('; ')}. ` +
             `TOTAL WAKTU tidak dianggap tahap proses.` +
             selaEvidence(`histori unggahan ${monthKeys[0] || years[0]}`, Number(src.count || 0));
    }
    function selaQuestionRouter(text){
      const stageDetail = selaStageBreakdown(text);
      if(stageDetail) return stageDetail;
      if(!historyMonths.length) return null;
      return selaHistoricalBottleneck(text) || selaCompareMonths(text) ||
             selaCompareYears(text) || selaHistoricalSingle(text);
    }

    function answer(text){
      const q = normalize(text);
      if(!q) return 'Silakan sampaikan pertanyaannya ya, saya siap membantu.';
      if(payload.meta.status === 'empty') return 'Saat ini belum ada data aktif yang bisa saya baca. Silakan upload atau aktifkan data terlebih dahulu.';

      const v11Answer = selaQuestionRouter(q);
      if(v11Answer) return v11Answer;

      const processAnswer = answerProcessSLA(q);
      if(processAnswer) return processAnswer;

      if(/halo|hai|selamat|pagi|siang|sore|malam/.test(q)){
        return 'Halo, saya SELA. Senang bisa membantu Anda. Silakan tanyakan apa saja terkait jumlah transaksi, SLA, vendor, bottleneck, growth, nomor permohonan, atau minta saya buatkan ringkasan Direksi.';
      }
      if(/siapa kamu|kamu siapa|nama kamu/.test(q)){
        return 'Saya SELA, asisten virtual wanita untuk SLA Payment Analyzer. Saya membaca data yang sedang aktif dan membantu menjelaskannya secara natural.';
      }
      if(/ringkasan direksi|executive|direksi|summary/.test(q)){
        const parts = [];
        parts.push(`${naturalLead()} Pada data aktif terdapat ${fmtNum(metrics.transaction_count || 0)} transaksi dengan rata-rata SLA total ${fmtDays(metrics.avg_sla_days)}.`);
        if(metrics.top_transaction) parts.push(`Jenis transaksi yang paling perlu menjadi perhatian adalah ${metrics.top_transaction.name} dengan rata-rata SLA ${fmtDays(metrics.top_transaction.avg_sla_days || 0)}.`);
        if(metrics.bottleneck) parts.push(`Bottleneck terbesar saat ini berada pada proses ${metrics.bottleneck.name} dengan rata-rata ${fmtDays(metrics.bottleneck.avg_sla_days || 0)}.`);
        if(metrics.latest_growth_pct !== null && metrics.latest_growth_pct !== undefined) parts.push(`Secara volume, transaksi terakhir ${Number(metrics.latest_growth_pct) >= 0 ? 'naik' : 'turun'} ${fmtPct(metrics.latest_growth_pct).replace('+','')} dibanding periode sebelumnya.`);
        parts.push(recommendationText());
        return parts.join(' ');
      }
      if(/rekomendasi|saran|apa yang harus diperbaiki|tindak lanjut/.test(q)){
        return `${naturalLead()} ${recommendationText() || 'Secara umum, fokuskan perbaikan pada proses dengan SLA terbesar dan lakukan pemantauan rutin terhadap transaksi prioritas.'}`;
      }
      if(/growth|pertumbuhan|naik|turun|dibanding periode sebelumnya|perbandingan periode/.test(q)){
        if(metrics.latest_growth_pct === null || metrics.latest_growth_pct === undefined){
          return 'Saat ini saya belum bisa menghitung growth karena data periodenya belum cukup untuk dibandingkan.';
        }
        const dir = Number(metrics.latest_growth_pct) >= 0 ? 'naik' : 'turun';
        let ans = `${naturalLead()} Jumlah transaksi pada periode terakhir ${dir} ${fmtPct(metrics.latest_growth_pct).replace('+','')} dibanding periode sebelumnya, dari ${fmtNum(metrics.prev_count || 0)} menjadi ${fmtNum(metrics.latest_count || 0)} transaksi.`;
        const latestPeriod = periodStats[periodStats.length-1];
        if(latestPeriod) ans += ` Periode terakhir yang terbaca adalah ${latestPeriod.periode}.`;
        return ans;
      }
      if(/berapa jumlah transaksi|total transaksi|jumlah transaksi/.test(q)){
        const p = findMentionedPeriod(q) || findMonthYearPeriod(q);
        const year = extractYear(q);
        if(p) return `${naturalLead()} Pada periode ${describeMonth(p)}, jumlah transaksinya sebanyak ${fmtNum(p.count)} transaksi.`;
        if(year){
          const y = yearStats.find(x => String(x.year) === String(year));
          if(y) return `${naturalLead()} Untuk tahun ${year}, total transaksi yang tercatat sebanyak ${fmtNum(y.count)} transaksi dengan rata-rata SLA ${fmtDays(y.avg_sla_days || 0)}.`;
        }
        return `${naturalLead()} Total transaksi aktif saat ini adalah ${fmtNum(metrics.transaction_count || 0)} transaksi, dengan cakupan periode ${metrics.period_first || '-'} sampai ${metrics.period_last || '-'}.`;
      }
      if(/sla total|rata-rata sla|sla keseluruhan|berapa sla/.test(q)){
        const p = findMentionedPeriod(q) || findMonthYearPeriod(q);
        const tr = findMentionedTransaction(q);
        const vd = findMentionedVendor(q);
        const nm = findMentionedNomor(q);
        if(p && p.avg_sla_days !== undefined) return `${naturalLead()} Pada periode ${describeMonth(p)}, rata-rata SLA totalnya adalah ${fmtDays(p.avg_sla_days)}.`;
        if(tr) return `${naturalLead()} Untuk jenis transaksi ${tr.name}, rata-rata SLA totalnya adalah ${fmtDays(tr.avg_sla_days || 0)} dengan volume ${fmtNum(tr.count || 0)} transaksi.`;
        if(vd) return `${naturalLead()} Untuk vendor ${vd.name}, rata-rata SLA totalnya adalah ${fmtDays(vd.avg_sla_days || 0)} dari ${fmtNum(vd.count || 0)} transaksi.`;
        if(nm) return `${naturalLead()} Untuk nomor permohonan ${nm.name}, rata-rata SLA totalnya adalah ${fmtDays(nm.avg_sla_days || 0)} dari ${fmtNum(nm.count || 0)} transaksi.`;
        return `${naturalLead()} Rata-rata SLA total seluruh data aktif saat ini adalah ${fmtDays(metrics.avg_sla_days || 0)}.`;
      }
      if(/jenis transaksi|transaksi apa yang paling lama|top sla|paling lambat/.test(q)){
        if(metrics.top_transaction){
          return `${naturalLead()} Jenis transaksi yang SLA-nya paling tinggi saat ini adalah ${metrics.top_transaction.name} dengan rata-rata ${fmtDays(metrics.top_transaction.avg_sla_days || 0)} dan volume ${fmtNum(metrics.top_transaction.count || 0)} transaksi.`;
        }
        return 'Saat ini saya belum menemukan data jenis transaksi yang cukup untuk dianalisis.';
      }
      if(/vendor|cabang/.test(q)){
        if(metrics.top_vendor){
          return `${naturalLead()} Vendor yang paling perlu dipantau saat ini adalah ${metrics.top_vendor.name} dengan rata-rata SLA ${fmtDays(metrics.top_vendor.avg_sla_days || 0)} dari ${fmtNum(metrics.top_vendor.count || 0)} transaksi.`;
        }
        return 'Saat ini data vendor/cabang belum tersedia atau belum cukup untuk dianalisis.';
      }
      if(/nomor permohonan|permohonan mana|request number|no permohonan/.test(q)){
        if(metrics.top_nomor){
          return `${naturalLead()} Nomor permohonan yang paling perlu dipantau saat ini adalah ${metrics.top_nomor.name} dengan rata-rata SLA ${fmtDays(metrics.top_nomor.avg_sla_days || 0)} dari ${fmtNum(metrics.top_nomor.count || 0)} transaksi.`;
        }
        return 'Saat ini saya belum menemukan kolom nomor permohonan pada data aktif.';
      }
      if(/bottleneck|kendala utama|proses paling lama|hambatan/.test(q)){
        if(metrics.bottleneck){
          return `${naturalLead()} Bottleneck terbesar saat ini berada pada proses ${metrics.bottleneck.name} dengan rata-rata SLA ${fmtDays(metrics.bottleneck.avg_sla_days || 0)}.`;
        }
        return 'Saat ini saya belum dapat menentukan bottleneck karena data SLA proses belum lengkap.';
      }
      if(/bandingkan.*20\\d{2}.*20\\d{2}|perbandingan.*20\\d{2}.*20\\d{2}/.test(q)){
        const years = text.match(/20\\d{2}/g) || [];
        if(years.length >= 2){
          const y1 = yearStats.find(y => String(y.year) === years[0]);
          const y2 = yearStats.find(y => String(y.year) === years[1]);
          if(y1 && y2){
            const diff = y1.count ? ((y2.count - y1.count) / y1.count * 100) : null;
            return `${naturalLead()} Pada tahun ${y1.year} terdapat ${fmtNum(y1.count)} transaksi, sedangkan tahun ${y2.year} terdapat ${fmtNum(y2.count)} transaksi. Perubahannya ${diff === null ? '-' : fmtPct(diff).replace('+','')} dengan rata-rata SLA masing-masing ${fmtDays(y1.avg_sla_days || 0)} dan ${fmtDays(y2.avg_sla_days || 0)}.`;
          }
        }
      }
      if(/nilai transaksi|nominal|amount/.test(q)){
        if(metrics.total_nilai !== null && metrics.total_nilai !== undefined){
          return `${naturalLead()} Total nilai transaksi pada data aktif adalah Rp ${fmtNum(metrics.total_nilai)}.`;
        }
        return 'Maaf, saat ini data nilai transaksi belum tersedia pada dataset aktif.';
      }
      if(/semua yang saya tanyakan|bisa jawab apa saja|apa yang bisa kamu jawab/.test(q)){
        return 'Saya bisa membantu menjawab pertanyaan terkait jumlah transaksi, perbandingan tahun atau periode, rata-rata SLA total, SLA per jenis transaksi, vendor/cabang paling lambat, nomor permohonan yang perlu dipantau, bottleneck proses, growth transaksi, nilai transaksi jika tersedia, serta membuat ringkasan Direksi dan rekomendasi perbaikan.';
      }
      return `${naturalLead()} Berdasarkan data aktif, terdapat ${fmtNum(metrics.transaction_count || 0)} transaksi dengan rata-rata SLA total ${fmtDays(metrics.avg_sla_days || 0)}. ${metrics.top_transaction ? `Jenis transaksi prioritas saat ini adalah ${metrics.top_transaction.name}. ` : ''}${metrics.bottleneck ? `Bottleneck terbesarnya berada pada proses ${metrics.bottleneck.name}. ` : ''}Jika ingin, Anda bisa bertanya lebih spesifik seperti \u201cberapa SLA Vendor tahun 2025\u201d, \u201cSLA Keuangan Juni 2026\u201d, \u201cvendor mana paling lambat\u201d, atau \u201cbuatkan ringkasan Direksi\u201d.`;
    }


    function escHtml(value){
      return String(value == null ? '' : value)
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
    }
    function shortLabel(text, maxLen){
      const s = String(text == null ? '' : text);
      return s.length > (maxLen || 18) ? s.slice(0, (maxLen || 18) - 1) + '…' : s;
    }
    function topProcessStages(){
      return (prosesStats || []).filter(p => p.is_stage && p.avg_sla_days !== null && p.avg_sla_days !== undefined);
    }
    function buildExecutiveActions(){
      const actions = [];
      if(metrics.bottleneck && metrics.bottleneck.name){
        actions.push(`Fokus percepatan pada tahap ${prettyProcessName(metrics.bottleneck.name)} karena saat ini menjadi bottleneck utama dengan SLA rata-rata ${fmtDays(metrics.bottleneck.avg_sla_days || 0)}.`);
      }
      if(metrics.top_transaction && metrics.top_transaction.name){
        actions.push(`Prioritaskan evaluasi jenis transaksi ${metrics.top_transaction.name} karena memiliki SLA rata-rata paling tinggi di data aktif.`);
      }
      if(metrics.top_vendor && metrics.top_vendor.name){
        actions.push(`Lakukan monitoring vendor/cabang ${metrics.top_vendor.name} karena berada pada daftar prioritas utama dari sisi SLA.`);
      }
      if(metrics.latest_growth_pct !== null && metrics.latest_growth_pct !== undefined){
        actions.push(`Pantau perubahan volume transaksi terbaru (${fmtPct(metrics.latest_growth_pct)} dibanding periode sebelumnya) agar kapasitas proses tetap seimbang.`);
      }
      return actions.slice(0, 4);
    }
    function buildInsightHighlights(){
      const rows = [];
      rows.push(`Cakupan data aktif saat ini ${escHtml(metrics.period_first || '-')} sampai ${escHtml(metrics.period_last || '-')}, dengan ${fmtNum(metrics.transaction_count || 0)} transaksi.`);
      rows.push(`Rata-rata SLA total berada pada ${fmtDays(metrics.avg_sla_days || 0)}${metrics.bottleneck && metrics.bottleneck.name ? ` dan bottleneck terbesar berada pada ${prettyProcessName(metrics.bottleneck.name)}` : ''}.`);
      if(metrics.top_transaction && metrics.top_transaction.name){
        rows.push(`Jenis transaksi prioritas utama adalah ${escHtml(metrics.top_transaction.name)} dengan SLA rata-rata ${fmtDays(metrics.top_transaction.avg_sla_days || 0)}.`);
      }
      if(metrics.top_vendor && metrics.top_vendor.name){
        rows.push(`Vendor/cabang yang paling perlu dipantau saat ini adalah ${escHtml(metrics.top_vendor.name)}.`);
      }
      return rows;
    }
    function renderOverviewBody(question, answerText){
      const actions = buildExecutiveActions();
      const highlights = buildInsightHighlights();
      const recent = (periodStats || []).slice(-4);
      const trendCards = recent.map(item => `
        <div class="mini-kpi">
          <div class="k">${escHtml(item.periode || '-')}</div>
          <div class="v">${fmtNum(item.count || 0)}</div>
          <div class="s">SLA ${fmtDays(item.avg_sla_days || 0)}</div>
        </div>`).join('');
      advisorOverview.innerHTML = `
        <div class="advisor-grid">
          <div class="viz-card wide">
            <div class="insight-banner"><strong>Executive Narrative</strong><br>${escHtml(answerText || 'SELA siap menyusun insight eksekutif berdasarkan data aktif. Gunakan chip cepat atau ajukan pertanyaan spesifik.').replace(/\\n/g,'<br>')}</div>
            <ul class="insight-list">${highlights.map(x => `<li>${escHtml(x)}</li>`).join('')}</ul>
          </div>
          <div class="viz-card wide">
            <div class="viz-title">Snapshot Periode Terakhir</div>
            <div class="viz-subtitle">Ringkasan empat periode terbaru dari data aktif</div>
            <div class="mini-kpis">${trendCards || '<div class="mini-kpi"><div class="k">Info</div><div class="v">-</div><div class="s">Belum ada periode yang bisa diringkas.</div></div>'}</div>
          </div>
          <div class="viz-card third">
            <div class="viz-title">Transaksi Aktif</div>
            <div class="viz-subtitle">Volume pada filter aktif</div>
            <div class="mini-kpi"><div class="k">Total</div><div class="v">${fmtNum(metrics.transaction_count || 0)}</div><div class="s">${escHtml(metrics.period_first || '-')} s.d. ${escHtml(metrics.period_last || '-')}</div></div>
          </div>
          <div class="viz-card third">
            <div class="viz-title">Rata-rata SLA</div>
            <div class="viz-subtitle">Keseluruhan proses</div>
            <div class="mini-kpi"><div class="k">SLA</div><div class="v">${fmtDays(metrics.avg_sla_days || 0)}</div><div class="s">Bottleneck: ${escHtml(metrics.bottleneck && metrics.bottleneck.name ? prettyProcessName(metrics.bottleneck.name) : '-')}</div></div>
          </div>
          <div class="viz-card third">
            <div class="viz-title">Prioritas Utama</div>
            <div class="viz-subtitle">Fokus eksekusi singkat</div>
            <ul class="insight-list">${actions.map(a => `<li>${escHtml(a)}</li>`).join('') || '<li>Belum ada rekomendasi khusus.</li>'}</ul>
          </div>
        </div>`;
    }
    function renderChartsBody(){
      const recent = (periodStats || []).slice(-8);
      const maxCount = Math.max(1, ...recent.map(item => Number(item.count || 0)));
      const bars = recent.map((item, idx) => `
        <div class="bar-item">
          <div class="bar-value">${fmtNum(item.count || 0)}</div>
          <div class="bar-col-wrap"><div class="bar-col ${idx % 2 ? 'secondary' : ''}" style="height:${Math.max(10, Math.round((Number(item.count || 0) / maxCount) * 100))}%"></div></div>
          <div class="bar-label">${escHtml(shortLabel(item.periode || '-', 14))}</div>
        </div>`).join('');
      const stages = topProcessStages();
      const maxStage = Math.max(1, ...stages.map(item => Number(item.avg_sla_days || 0)));
      const hbars = stages.map(item => `
        <div class="hrow">
          <div class="hlabel">${escHtml(prettyProcessName(item.name))}</div>
          <div class="htrack"><div class="hfill" style="width:${Math.max(10, Math.round((Number(item.avg_sla_days || 0) / maxStage) * 100))}%"></div></div>
          <div class="hval">${fmtDays(item.avg_sla_days || 0)}</div>
        </div>`).join('');
      const years = (historyYears || []).slice(-5);
      const yearLegendColors = ['#fbbf24','#60a5fa','#34d399','#a78bfa','#f472b6'];
      const yearBars = years.map((row, idx) => ({row, color: yearLegendColors[idx % yearLegendColors.length]}));
      const maxYear = Math.max(1, ...yearBars.map(item => Number(item.row.count || 0)));
      advisorCharts.innerHTML = `
        <div class="advisor-grid">
          <div class="viz-card">
            <div class="viz-title">Tren Jumlah Transaksi</div>
            <div class="viz-subtitle">Delapan periode terakhir pada filter aktif</div>
            <div class="bars">${bars || '<div class="bar-label">Belum ada data periode.</div>'}</div>
          </div>
          <div class="viz-card">
            <div class="viz-title">Perbandingan SLA per Tahapan Proses</div>
            <div class="viz-subtitle">Semakin panjang bar, semakin tinggi SLA rata-ratanya</div>
            <div class="hbars">${hbars || '<div class="bar-label">Belum ada data SLA per tahapan.</div>'}</div>
          </div>
          <div class="viz-card wide">
            <div class="viz-title">Perbandingan Volume Historis per Tahun</div>
            <div class="viz-subtitle">Histori upload lintas tahun — legend dibuat kontras agar tahun mudah dibaca</div>
            <div class="legend-row">${yearBars.map(item => `<span class="legend-item"><span class="legend-swatch" style="background:${item.color}"></span>${escHtml(item.row.year)}</span>`).join('')}</div>
            <div class="bars">${yearBars.map(item => `
              <div class="bar-item">
                <div class="bar-value">${fmtNum(item.row.count || 0)}</div>
                <div class="bar-col-wrap"><div class="bar-col" style="background:${item.color};height:${Math.max(10, Math.round((Number(item.row.count || 0) / maxYear) * 100))}%"></div></div>
                <div class="bar-label">Tahun ${escHtml(item.row.year)}</div>
              </div>`).join('') || '<div class="bar-label">Belum ada histori tahunan.</div>'}
            </div>
          </div>
        </div>`;
    }
    function renderTablesBody(){
      const trxRows = (trxStats || []).slice(0, 8).map((row, idx) => `
        <tr><td><span class="rank-pill">${idx+1}</span></td><td>${escHtml(row.name || '-')}</td><td>${fmtNum(row.count || 0)}</td><td>${fmtDays(row.avg_sla_days || 0)}</td></tr>`).join('');
      const vendorRows = (vendorStats || []).slice(0, 8).map((row, idx) => `
        <tr><td><span class="rank-pill">${idx+1}</span></td><td>${escHtml(row.name || '-')}</td><td>${fmtNum(row.count || 0)}</td><td>${fmtDays(row.avg_sla_days || 0)}</td></tr>`).join('');
      const sampleRows = (records || []).slice(0, 8).map((row, idx) => {
        const periode = payload.meta && payload.meta.periode_col ? row[payload.meta.periode_col] : '';
        const nomor = payload.meta && payload.meta.nomor_col ? row[payload.meta.nomor_col] : '';
        const transaksi = payload.meta && payload.meta.trx_col ? row[payload.meta.trx_col] : '';
        const vendor = payload.meta && payload.meta.vendor_col ? row[payload.meta.vendor_col] : '';
        const total = row['TOTAL WAKTU'];
        return `<tr><td>${idx+1}</td><td>${escHtml(periode || '-')}</td><td>${escHtml(shortLabel(nomor || '-', 20))}</td><td>${escHtml(shortLabel(transaksi || '-', 22))}</td><td>${escHtml(shortLabel(vendor || '-', 22))}</td><td>${fmtDays(total)}</td></tr>`;
      }).join('');
      advisorTables.innerHTML = `
        <div class="advisor-grid">
          <div class="viz-card">
            <div class="viz-title">Top Jenis Transaksi</div>
            <div class="viz-subtitle">Peringkat berdasarkan SLA rata-rata tertinggi pada data aktif</div>
            <div class="premium-table-wrap"><table class="premium-table"><thead><tr><th>Rank</th><th>Jenis Transaksi</th><th>Volume</th><th>Rata-rata SLA</th></tr></thead><tbody>${trxRows || '<tr><td colspan="4">Belum ada data jenis transaksi.</td></tr>'}</tbody></table></div>
          </div>
          <div class="viz-card">
            <div class="viz-title">Top Vendor / Cabang</div>
            <div class="viz-subtitle">Entitas dengan SLA rata-rata paling tinggi</div>
            <div class="premium-table-wrap"><table class="premium-table"><thead><tr><th>Rank</th><th>Vendor / Cabang</th><th>Volume</th><th>Rata-rata SLA</th></tr></thead><tbody>${vendorRows || '<tr><td colspan="4">Belum ada data vendor/cabang.</td></tr>'}</tbody></table></div>
          </div>
          <div class="viz-card wide">
            <div class="viz-title">Preview Data Operasional</div>
            <div class="viz-subtitle">Delapan baris pertama dari data aktif untuk validasi cepat</div>
            <div class="premium-table-wrap"><table class="premium-table"><thead><tr><th>No</th><th>Periode</th><th>Nomor Permohonan</th><th>Jenis Transaksi</th><th>Vendor / Cabang</th><th>TOTAL WAKTU</th></tr></thead><tbody>${sampleRows || '<tr><td colspan="6">Belum ada sample record.</td></tr>'}</tbody></table></div>
          </div>
        </div>`;
    }
    function renderPosterBody(answerText){
      const actions = buildExecutiveActions();
      const stages = topProcessStages().slice(0, 4);
      advisorPoster.innerHTML = `
        <div class="poster-board">
          <div class="poster-head">
            <div>
              <div class="poster-brand">ASDP • SLA Executive Advisor</div>
              <div class="poster-title">SLA Executive Poster — Snapshot ${escHtml(metrics.period_first || '-')} sampai ${escHtml(metrics.period_last || '-')}</div>
              <div class="poster-note">Poster ini dihasilkan langsung oleh SELA berdasarkan data yang sedang aktif pada dashboard, tanpa mengubah angka sumber. Cocok digunakan sebagai bahan briefing cepat atau executive preview.</div>
            </div>
            <div class="poster-badges">
              <span class="poster-badge">${fmtNum(metrics.transaction_count || 0)} TRANSAKSI</span>
              <span class="poster-badge">SLA ${fmtDays(metrics.avg_sla_days || 0)}</span>
              <span class="poster-badge">GROWTH ${fmtPct(metrics.latest_growth_pct)}</span>
            </div>
          </div>
          <div class="poster-grid">
            <div class="poster-block"><div class="t">Volume Aktif</div><div class="n">${fmtNum(metrics.transaction_count || 0)}</div><div class="d">Cakupan data aktif ${escHtml(metrics.period_first || '-')} s.d. ${escHtml(metrics.period_last || '-')}.</div></div>
            <div class="poster-block"><div class="t">Rata-rata SLA</div><div class="n">${fmtDays(metrics.avg_sla_days || 0)}</div><div class="d">Menggambarkan durasi total rata-rata pada seluruh transaksi aktif.</div></div>
            <div class="poster-block"><div class="t">Bottleneck</div><div class="n">${escHtml(metrics.bottleneck && metrics.bottleneck.name ? prettyProcessName(metrics.bottleneck.name) : '-')}</div><div class="d">${metrics.bottleneck && metrics.bottleneck.avg_sla_days !== undefined ? 'Rata-rata SLA ' + fmtDays(metrics.bottleneck.avg_sla_days || 0) : 'Belum ada data bottleneck.'}</div></div>
            <div class="poster-block wide"><div class="t">Prioritas Transaksi & Vendor</div><div class="n">${escHtml(metrics.top_transaction && metrics.top_transaction.name ? metrics.top_transaction.name : '-')}</div><div class="d">Vendor prioritas: ${escHtml(metrics.top_vendor && metrics.top_vendor.name ? metrics.top_vendor.name : '-')}. ${metrics.top_transaction && metrics.top_transaction.avg_sla_days !== undefined ? 'SLA transaksi prioritas: ' + fmtDays(metrics.top_transaction.avg_sla_days || 0) + '.' : ''}</div></div>
            <div class="poster-block wide"><div class="t">Executive Narrative</div><div class="d">${escHtml(answerText || 'SELA siap menyusun narasi eksekutif berdasarkan pertanyaan Anda.').replace(/\\n/g,'<br>')}</div></div>
            <div class="poster-block full"><div class="t">Tahapan SLA</div><div class="legend-row">${stages.map((item, idx) => `<span class="legend-item"><span class="legend-swatch" style="background:${['#60a5fa','#34d399','#fbbf24','#f472b6'][idx % 4]}"></span>${escHtml(prettyProcessName(item.name))}: ${fmtDays(item.avg_sla_days || 0)}</span>`).join('') || '<span class="legend-item">Belum ada data tahapan.</span>'}</div></div>
            <div class="poster-block full"><div class="t">Rekomendasi Aksi</div><ol class="poster-actions">${actions.map(item => `<li>${escHtml(item)}</li>`).join('') || '<li>Belum ada rekomendasi.</li>'}</ol></div>
          </div>
          <div class="poster-foot">Dasar data: filter aktif ${escHtml(metrics.period_first || '-')} s.d. ${escHtml(metrics.period_last || '-')}; ${fmtNum(metrics.transaction_count || 0)} transaksi. Poster ini hanya menampilkan visualisasi ringkas, sementara laporan utama aplikasi tetap menjadi referensi detail.</div>
        </div>`;
    }
    function setAdvisorTab(name){
      advisorTabs.forEach(btn => btn.classList.toggle('active', btn.dataset.tab === name));
      advisorBodies.forEach(body => body.classList.toggle('active', body.id === 'advisor' + name.charAt(0).toUpperCase() + name.slice(1)));
    }
    function inferAdvisorMode(question){
      const q = normalize(question);
      if(/(briefing|boardroom|satu halaman|bod|dekom)/.test(q)) return 'briefing';
      if(/poster|infografik|ringkasan direksi|executive poster|executive advisor/.test(q)) return 'poster';
      if(/tabel|table|daftar|list|top vendor|top transaksi|nomor permohonan/.test(q)) return 'tables';
      if(/grafik|chart|bagan|tren|trend|visual/.test(q)) return 'charts';
      return 'overview';
    }
    function refreshAdvisor(mode, question, answerText){
      // Render only the requested visual. Hidden panels remain lazy for a fast response.
      const safeMode = ['overview','charts','tables','poster','briefing'].includes(mode) ? mode : 'overview';
      if(safeMode === 'overview') renderOverviewBody(question, answerText);
      else if(safeMode === 'charts') renderChartsBody();
      else if(safeMode === 'tables') renderTablesBody();
      else if(safeMode === 'poster') renderPosterBody(answerText);
      else renderBriefingBody();
      setAdvisorTab(safeMode);
      const captions = {
        overview:'Insight eksekutif telah diringkas pada panel Insight.',
        charts:'Grafik eksekutif telah ditampilkan pada panel Grafik.',
        tables:'Tabel prioritas telah ditampilkan pada panel Tabel.',
        poster:'Poster eksekutif telah ditampilkan pada panel Poster.',
        briefing:'Boardroom Briefing satu halaman siap diperiksa dan diekspor.'
      };
      advisorStatus.textContent = captions[safeMode] + ' Data sumber tetap mengikuti dashboard aktif dan seluruh fitur utama aplikasi tetap dipertahankan.';
      requestAnimationFrame(selaAutoResize);
    }
    // SELA lives inside a Streamlit iframe: keep height synchronized with real content.
    // Safe fallback: components.html(scrolling=True) still allows access if host ignores messages.
    let selaLastReportedHeight = 0;
    function selaAutoResize(){
      if(window.parent === window) return;
      const root = document.querySelector('.sela-root');
      if(!root) return;
      // Measure content, not iframe viewport, to prevent a resize feedback loop.
      const desired = Math.ceil(root.scrollHeight + 24);
      if(!Number.isFinite(desired) || Math.abs(desired-selaLastReportedHeight) < 24) return;
      selaLastReportedHeight = desired;
      window.parent.postMessage({isStreamlitMessage:true,
                    type:'streamlit:setFrameHeight', height:desired}, '*');
    }
    if(typeof ResizeObserver !== 'undefined'){
      const selaSizeObserver = new ResizeObserver(() => requestAnimationFrame(selaAutoResize));
      selaSizeObserver.observe(document.body);
    }
    window.addEventListener('load', () => requestAnimationFrame(selaAutoResize));
    // SELA v13 Boardroom Output: browser-native exports, no network or heavy dependency.
    let boardroomQuestion = '';
    let boardroomAnswer = '';
    const boardroomColors = {'2022':'#edb841','2023':'#25b9a5','2024':'#4d8fdd','2025':'#9b82df','2026':'#db6a9d'};
    function boardroomYearColor(label, index){
      const year = String(label).match(/20[0-9]{2}/);
      return year && boardroomColors[year[0]] ? boardroomColors[year[0]] : ['#257f95','#2bb7a5','#8a79cc','#e7b859','#c36f90'][index%5];
    }
    function boardroomBaseName(){
      const clean = String(metrics.period_first || 'Data') + '_' + String(metrics.period_last || 'Terakhir');
      return 'ASDP_SELA_Boardroom_' + clean.replace(/[^0-9a-zA-Z_-]+/g,'_').slice(0,72);
    }
    function boardroomScope(){
      return String(metrics.period_first || '-') + ' – ' + String(metrics.period_last || '-');
    }
    function boardroomSeries(){
      const question = boardroomQuestion || '';
      const metric = selaMetric(normalize(question));
      const unit = metric === 'count' ? 'transaksi' : 'hari';
      const multiYears = selaMentionedYears(question);
      const multiMonths = selaMonthYearMentions(question);
      if(multiYears.length >= 2){
        const available = multiYears.filter(y => historyYears.some(item=>String(item.year) === String(y)));
        if(available.length >= 2){
          const latest = available.map(y=>historyYears.find(item=>String(item.year)===String(y)));
          const horizon = Math.min(...latest.map(x=>Number(x.latest_month || 12)));
          return {title:metric==='count'?'Perbandingan volume multi-tahun':'Perbandingan SLA multi-tahun',
            subtitle:'Horizon sebanding Januari–'+MONTH_NAMES_ID[horizon-1]+' • histori unggahan', unit,
            data:available.map(y=>{
              const row=selaAggregateYear(y,horizon,metric);
              return {label:y,value:row?row.value:null};
            }).filter(x=>x.value!==null && Number.isFinite(Number(x.value)))};
        }
      }
      if(multiMonths.length >= 2){
        const rows=multiMonths.map(key=>historyMonths.find(row=>row.month_key===key)).filter(Boolean);
        return {title:metric==='count'?'Perbandingan volume antar bulan':'Perbandingan SLA antar bulan',
          subtitle:'Histori periode yang diminta • hanya periode tersedia',unit,
          data:rows.map(row=>({label:MONTH_NAMES_ID[Number(row.month)-1].slice(0,3)+' '+row.year,
            value:metric==='count'?Number(row.count || 0):row[metric]}))
            .filter(x=>x.value!==null && x.value!==undefined && Number.isFinite(Number(x.value)))};
      }
      if(multiYears.length===1 && historyMonths.some(r=>String(r.year)===String(multiYears[0]))){
        const year=String(multiYears[0]);
        const rows=historyMonths.filter(r=>String(r.year)===year).sort((a,b)=>Number(a.month)-Number(b.month));
        return {title:metric==='count'?'Volume transaksi '+year:'SLA '+prettyProcessName(metric)+' '+year,
          subtitle:'Histori unggahan tahun '+year+' • periode tersedia',unit,
          data:rows.map(row=>({label:MONTH_NAMES_ID[Number(row.month)-1].slice(0,3),
            value:metric==='count'?Number(row.count || 0):row[metric]}))
            .filter(x=>x.value!==null && x.value!==undefined && Number.isFinite(Number(x.value)))};
      }
      const rows=(periodStats || []).slice(-8);
      const slaByMonth=new Map((processMonthStats || []).map(row=>[row.month_key,row]));
      return {title:metric==='count'?'Tren volume transaksi':'Tren SLA '+prettyProcessName(metric),
        subtitle:'Periode aktif: '+boardroomScope(),unit,
        data:rows.map(row=>({label:String(row.periode || '-'),value:metric==='count'
          ? Number(row.count || 0)
          : ((slaByMonth.get(row.month_key) || {})[metric] ?? (metric==='TOTAL WAKTU' ? row.avg_sla_days : null))}))
          .filter(x=>x.value!==null && x.value!==undefined && Number.isFinite(Number(x.value)))};
    }
    function boardroomSvg(){
      const series=boardroomSeries();
      const data=series.data.slice(-12);
      const width=1040, height=500, left=78, right=32, top=118, baseline=386;
      const chartW=width-left-right, chartH=baseline-top;
      const max=Math.max(1,...data.map(row=>Number(row.value)))*1.16;
      const colors=data.map((row,i)=>boardroomYearColor(row.label,i));
      const barW=data.length ? Math.min(64,(chartW/data.length)*0.56) : 64;
      const axis=[0,1,2,3,4].map(i=>{
        const y=baseline-i*chartH/4;
        const value=max*i/4;
        const label=series.unit==='transaksi' ? fmtNum(Math.round(value)) : fmtNum(Math.round(value*100)/100);
        return `<line x1="${left}" y1="${y}" x2="${width-right}" y2="${y}" stroke="#dde7ef" stroke-width="1"/><text x="${left-14}" y="${y+4}" text-anchor="end" font-size="13" fill="#6b849a">${escHtml(label)}</text>`;
      }).join('');
      const bars=data.map((row,i)=>{
        const x=left+chartW*(i+.5)/data.length;
        const barH=Math.max(2,(Number(row.value)/max)*chartH);
        const y=baseline-barH;
        const display=series.unit==='transaksi' ? fmtNum(row.value):Number(row.value).toLocaleString('id-ID',{maximumFractionDigits:2});
        const short=shortLabel(row.label,16);
        return `<rect x="${(x-barW/2).toFixed(2)}" y="${y.toFixed(2)}" width="${barW}" height="${barH.toFixed(2)}" rx="7" fill="${colors[i]}"/>
          <text x="${x.toFixed(2)}" y="${Math.max(top-8,y-9).toFixed(2)}" text-anchor="middle" font-size="14" fill="#15354d" font-weight="700">${escHtml(display)}</text>
          <text x="${x.toFixed(2)}" y="${baseline+24}" text-anchor="middle" font-size="12" fill="#4a667f">${escHtml(short)}</text>`;
      }).join('');
      return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="Grafik SELA Boardroom">
        <rect width="${width}" height="${height}" rx="24" fill="#f8fafc"/>
        <rect x="0" y="0" width="${width}" height="9" fill="#249c97"/>
        <text x="55" y="53" font-size="12" font-weight="700" letter-spacing="2" fill="#247f88">ASDP  ·  SELA BOARDROOM</text>
        <text x="55" y="87" font-size="26" font-weight="800" fill="#152e48">${escHtml(series.title)}</text>
        <text x="55" y="107" font-size="13" fill="#638199">${escHtml(series.subtitle)}</text>
        ${axis}${bars}
        <text x="55" y="461" font-size="12" fill="#5f7d95">Sumber: data transaksi yang telah diunggah · ${escHtml(boardroomScope())}</text>
        <text x="${width-55}" y="461" text-anchor="end" font-size="12" fill="#247f88">SELA EXECUTIVE ASSISTANT</text>
      </svg>`;
    }
    function boardroomDownloadBlob(blob,name){
      const url=URL.createObjectURL(blob);
      const a=document.createElement('a');
      a.href=url;a.download=name;a.style.display='none';
      document.body.appendChild(a);a.click();a.remove();
      window.setTimeout(()=>URL.revokeObjectURL(url),4000);
    }
    function boardroomDownloadText(text,type,name){
      boardroomDownloadBlob(new Blob([text],{type:type}),name);
    }
    function boardroomExportSvg(){
      boardroomDownloadText(boardroomSvg(),'image/svg+xml;charset=utf-8',boardroomBaseName()+'_Grafik.svg');
      advisorStatus.textContent='Grafik SVG telah disiapkan untuk diunduh.';
    }
    function boardroomExportChartPng(){
      const svg=boardroomSvg();
      const img=new Image();
      const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml;charset=utf-8'}));
      img.onload=()=>{
        try{
          const canvas=document.createElement('canvas');canvas.width=1560;canvas.height=750;
          const ctx=canvas.getContext('2d');ctx.fillStyle='#f8fafc';ctx.fillRect(0,0,1560,750);
          ctx.drawImage(img,0,0,1560,750);
          canvas.toBlob(blob=>{if(blob)boardroomDownloadBlob(blob,boardroomBaseName()+'_Grafik.png');},'image/png');
          advisorStatus.textContent='Grafik PNG telah disiapkan untuk diunduh.';
        }catch(err){advisorStatus.textContent='Grafik PNG belum bisa disimpan. Gunakan format SVG sebagai alternatif.';}
        URL.revokeObjectURL(url);
      };
      img.onerror=()=>{URL.revokeObjectURL(url);advisorStatus.textContent='Grafik PNG belum bisa dibuat. Silakan gunakan SVG.';};
      img.src=url;
    }
    function boardroomCsvEscape(value){
      let string=String(value===null||value===undefined?'':value);
      if(/^[=+@-]/.test(string.trim()))string="'"+string;
      return '"'+string.replace(/"/g,'""')+'"';
    }
    function boardroomExportCsv(){
      const rows=[['Kategori','Peringkat','Entitas','Jumlah Transaksi','Rata-rata SLA (hari)','Periode Aktif']];
      [['Jenis Transaksi',trxStats],['Vendor/Cabang',vendorStats]].forEach(([kind,items])=>{
        (items || []).forEach((row,i)=>rows.push([kind,i+1,row.name || '-',Number(row.count || 0),
          row.avg_sla_days===null||row.avg_sla_days===undefined?'':Number(row.avg_sla_days).toFixed(6),boardroomScope()]));
      });
      const csv='\\ufeff'+rows.map(row=>row.map(boardroomCsvEscape).join(';')).join('\\r\\n');
      boardroomDownloadText(csv,'text/csv;charset=utf-8',boardroomBaseName()+'_Prioritas.csv');
      advisorStatus.textContent='Tabel prioritas CSV telah disiapkan untuk diunduh (kompatibel dengan Excel).';
    }
    function boardroomCanvasText(ctx,text,x,y,maxWidth,font,color){
      ctx.font=font;ctx.fillStyle=color;
      let out=String(text||'');
      if(ctx.measureText(out).width>maxWidth){
        while(out.length>1&&ctx.measureText(out+'…').width>maxWidth)out=out.slice(0,-1);
        out+='…';
      }
      ctx.fillText(out,x,y);
    }
    function boardroomWrap(ctx,text,x,y,width,lineHeight,maxLines,font,color){
      ctx.font=font;ctx.fillStyle=color;
      const words=String(text||'').split(/\\s+/);let line='',lineNo=0;
      for(const word of words){
        const cand=line?line+' '+word:word;
        if(ctx.measureText(cand).width<=width){line=cand;continue;}
        if(line){boardroomCanvasText(ctx,line,x,y+lineNo*lineHeight,width,font,color);lineNo++;if(lineNo>=maxLines)return lineNo;}
        line=word;
      }
      if(line&&lineNo<maxLines){boardroomCanvasText(ctx,line,x,y+lineNo*lineHeight,width,font,color);lineNo++;}
      return lineNo;
    }
    function boardroomRounded(ctx,x,y,w,h,r,color){
      ctx.fillStyle=color;ctx.beginPath();
      if(typeof ctx.roundRect==='function')ctx.roundRect(x,y,w,h,r);
      else ctx.rect(x,y,w,h);
      ctx.fill();
    }
    function boardroomExportPosterPng(){
      // Canvas export keeps confidential dashboard data local inside the browser.
      const canvas=document.createElement('canvas');canvas.width=1600;canvas.height=1000;
      const ctx=canvas.getContext('2d');
      ctx.fillStyle='#f6f9fc';ctx.fillRect(0,0,1600,1000);
      boardroomRounded(ctx,0,0,1600,260,0,'#132b45');
      boardroomRounded(ctx,75,66,64,64,19,'#2cae9d');
      boardroomCanvasText(ctx,'S',96,111,30,'800 34px Arial','#ffffff');
      boardroomCanvasText(ctx,'ASDP · INTELLIGENT PAYMENT PERFORMANCE',162,79,1210,'700 19px Arial','#a5e1dd');
      boardroomCanvasText(ctx,'SELA BOARDROOM BRIEF',75,163,1450,'800 51px Arial','#ffffff');
      boardroomCanvasText(ctx,boardroomScope(),75,212,1400,'400 22px Arial','#c1d9eb');
      const cards=[['TOTAL TRANSAKSI',fmtNum(metrics.transaction_count || 0)],['RATA-RATA SLA',fmtDays(metrics.avg_sla_days)],['GROWTH TERAKHIR',fmtPct(metrics.latest_growth_pct)],['BOTTLENECK',prettyProcessName(metrics.bottleneck?.name || '-')]];
      cards.forEach((card,i)=>{
        const x=75+i*367;
        boardroomRounded(ctx,x,298,345,139,19,'#ffffff');
        boardroomCanvasText(ctx,card[0],x+20,335,300,'700 16px Arial','#5d8198');
        boardroomCanvasText(ctx,card[1],x+20,397,306,i===1?'800 22px Arial':'800 30px Arial','#173550');
      });
      boardroomRounded(ctx,75,472,850,384,20,'#ffffff');
      boardroomCanvasText(ctx,'INSIGHT OPERASIONAL',103,516,780,'700 18px Arial','#278b86');
      const highlights=buildInsightHighlights().slice(0,4);
      let next=557;
      highlights.forEach((h,i)=>{
        ctx.fillStyle='#25b3a3';ctx.beginPath();ctx.arc(112,next-5,5,0,Math.PI*2);ctx.fill();
        const lines=boardroomWrap(ctx,h,136,next,742,25,3,'400 19px Arial','#35526a');
        next+=Math.max(2,lines)*25+18;
      });
      boardroomRounded(ctx,949,472,576,384,20,'#e5f4f3');
      boardroomCanvasText(ctx,'PRIORITAS TINDAKAN',977,516,510,'700 18px Arial','#268983');
      let ay=560;
      buildExecutiveActions().slice(0,3).forEach((a,i)=>{
        boardroomRounded(ctx,977,ay-24,33,33,10,'#bbdfda');
        boardroomCanvasText(ctx,String(i+1),987,ay,20,'800 18px Arial','#1c6e66');
        const lines=boardroomWrap(ctx,a,1024,ay-2,470,24,3,'400 17px Arial','#2c5265');
        ay+=Math.max(lines,2)*24+24;
      });
      ctx.strokeStyle='#d8e4ed';ctx.beginPath();ctx.moveTo(75,899);ctx.lineTo(1525,899);ctx.stroke();
      boardroomCanvasText(ctx,'Sumber: file transaksi aktif · Perhitungan identik dengan dashboard SELA',75,932,1360,'400 16px Arial','#67859b');
      boardroomCanvasText(ctx,'SELA EXECUTIVE ASSISTANT',75,965,1380,'700 15px Arial','#2f8c89');
      canvas.toBlob(blob=>{if(blob)boardroomDownloadBlob(blob,boardroomBaseName()+'_Poster.png');},'image/png');
      advisorStatus.textContent='Poster PNG beresolusi 1600×1000 telah disiapkan untuk diunduh.';
    }
    function boardroomBriefBody(){
      const actions=buildExecutiveActions();
      const insights=buildInsightHighlights();
      return `<section class="briefing-preview">
        <header class="briefing-header"><div><div class="briefing-eyebrow">ASDP · SELA Executive Assistant</div>
          <h3>Boardroom Briefing</h3><div class="briefing-desc">Ringkasan kinerja pembayaran · ${escHtml(boardroomScope())}</div></div>
          <div class="briefing-eyebrow">ONE-PAGE BRIEF</div></header>
        <div class="briefing-grid">
          <div class="briefing-kpi"><span>Total Transaksi</span><strong>${fmtNum(metrics.transaction_count || 0)}</strong></div>
          <div class="briefing-kpi"><span>Rata-rata SLA</span><strong>${fmtDays(metrics.avg_sla_days)}</strong></div>
          <div class="briefing-kpi"><span>Growth Terakhir</span><strong>${fmtPct(metrics.latest_growth_pct)}</strong></div>
          <div class="briefing-kpi"><span>Bottleneck</span><strong>${escHtml(prettyProcessName(metrics.bottleneck?.name || '-'))}</strong></div>
        </div>
        <div class="briefing-section"><h4>Visual Performance</h4>${boardroomSvg().replace(/width="1040" height="500"/,'class="briefing-chart" width="1040" height="500"')}</div>
        <div class="briefing-section"><h4>Executive Highlights</h4><ol>${insights.slice(0,3).map(item=>`<li>${escHtml(item)}</li>`).join('')}</ol></div>
        <div class="briefing-section"><h4>Management Action</h4><ol>${actions.slice(0,3).map(item=>`<li>${escHtml(item)}</li>`).join('')||'<li>Belum terdapat rekomendasi spesifik dari data aktif.</li>'}</ol></div>
        <div class="briefing-foot">Basis: ${fmtNum(metrics.transaction_count || 0)} transaksi, filter ${escHtml(boardroomScope())}. Grafik historis, bila diminta, menggunakan histori unggahan. Output ini merupakan ringkasan pendamping dan tidak menggantikan laporan utama aplikasi.</div>
      </section>`;
    }
    function renderBriefingBody(){
      advisorBriefing.innerHTML=boardroomBriefBody();
    }
    function boardroomDocument(){
      // Offline, printable A4 landscape; no requests to external services.
      const preview=boardroomBriefBody();
      return `<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
        <title>ASDP SELA Boardroom Briefing</title><style>
        *{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#f0f4f7;color:#18324a}
        .briefing-preview{padding:25px;max-width:1160px;margin:24px auto;border-radius:16px;background:#fff}
        .briefing-header{display:flex;justify-content:space-between;border-bottom:2px solid #dce5ec;padding-bottom:12px;margin-bottom:14px}
        .briefing-eyebrow{text-transform:uppercase;letter-spacing:1.5px;color:#267b83;font-weight:800;font-size:10px}
        h3{font-size:26px;margin:4px 0 6px}.briefing-desc,.briefing-foot{font-size:11px;color:#607b90}
        .briefing-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px}
        .briefing-kpi{background:#edf4f7;border-radius:9px;padding:12px}.briefing-kpi span{display:block;font-size:10px;color:#657f90;font-weight:700}
        .briefing-kpi strong{display:block;font-size:18px;color:#16334f;margin-top:5px}
        .briefing-section{border:1px solid #dfe8ef;border-radius:10px;padding:12px;margin-bottom:10px;page-break-inside:avoid}
        .briefing-section h4{text-transform:uppercase;letter-spacing:1px;color:#2c6676;font-size:11px;margin:0 0 6px}
        .briefing-section li{font-size:10px;line-height:1.45;margin-bottom:4px}
        .briefing-section ol{margin:0;padding-left:18px}.briefing-chart{display:block;width:100%;max-height:220px}
        .briefing-foot{margin-top:12px;border-top:1px solid #e3ebf2;padding-top:8px}
        @page{size:A4 landscape;margin:10mm}
        @media print{body{background:#fff}.briefing-preview{padding:0;max-width:none;margin:0;border-radius:0}
          .briefing-chart{max-height:185px}.briefing-section{margin-bottom:7px;padding:8px}.briefing-grid{margin-bottom:8px}
          h3{font-size:22px}.briefing-kpi{padding:9px}}
      
  </style></head><body>${preview}</body></html>`;
    }
    function boardroomExportHtml(){
      boardroomDownloadText(boardroomDocument(),'text/html;charset=utf-8',boardroomBaseName()+'_Boardroom_Brief.html');
      advisorStatus.textContent='Executive Briefing HTML satu halaman siap diunduh. File dapat dibuka offline lalu dicetak ke PDF.';
    }
    function boardroomPrintPdf(){
      // User-initiated print dialog: choose "Save as PDF"; avoids extra PDF libraries.
      const popup=window.open('','_blank');
      if(!popup){
        advisorStatus.textContent='Pop-up cetak diblokir browser. Gunakan Unduh Briefing HTML lalu pilih Print / Save as PDF.';
        return;
      }
      popup.document.open();popup.document.write(boardroomDocument());popup.document.close();
      popup.focus();
      let didPrint=false;
      const goPrint=()=>{
        if(didPrint)return;
        didPrint=true;
        try{popup.print();}catch(err){advisorStatus.textContent='Gunakan Ctrl+P pada tab briefing untuk menyimpan PDF.';}
      };
      popup.addEventListener('load',goPrint,{once:true});
      window.setTimeout(()=>{if(!popup.closed&&popup.document.readyState==='complete')goPrint();},700);
      advisorStatus.textContent='Jendela cetak dibuka. Pilih tujuan "Save as PDF" untuk menyimpan laporan satu halaman.';
    }
    function boardroomHandleExport(type){
      try{
        if(type==='poster')return boardroomExportPosterPng();
        if(type==='svg')return boardroomExportSvg();
        if(type==='chartpng')return boardroomExportChartPng();
        if(type==='csv')return boardroomExportCsv();
        if(type==='html')return boardroomExportHtml();
        if(type==='pdf')return boardroomPrintPdf();
      }catch(err){
        advisorStatus.textContent='Ekspor belum berhasil: '+String(err?.message || err)+'. Format lain masih tersedia.';
      }
    }

    // v18: comic-style responses and film subtitles, opt-in only when SELA is open.
    const cineShade = document.getElementById('cineShade');
    const cineTextAnswer = document.getElementById('cineTextAnswer');
    const cineTextBody = document.getElementById('cineTextBody');
    const cineSubtitle = document.getElementById('cineSubtitle');
    const cineSubtitleText = document.getElementById('cineSubtitleText');
    const cineMoreBtn = document.getElementById('cineMoreBtn');
    const cineShortcutPanel = document.getElementById('quickChips');
    const cineVoiceControls = document.querySelector('.selectors');
    const cineReport = document.querySelector('.advisor-shell');
    let cineLastQuestion = '';
    let cineLastAnswer = '';
    let cineLastMode = 'overview';
    let cineSubtitleToken = 0;
    let cineSubtitleInterval = null;
    let cineSubtitleWords = [];
    let cineSubtitleCursor = 0;
    let cineLastBoundaryAt = 0;
    let cineSubtitleDismiss = null;
    function cineHideSubtitle(){
      cineSubtitleToken++;
      if(cineSubtitleInterval){clearInterval(cineSubtitleInterval);cineSubtitleInterval=null;}
      if(cineSubtitleDismiss){clearTimeout(cineSubtitleDismiss);cineSubtitleDismiss=null;}
      cineSubtitle.classList.remove('is-visible');
      cineSubtitleText.textContent='';
    }
    function cineSubtitleAt(charIndex){
      if(!cineSubtitleWords.length) return;
      const loc = Math.max(0,Number(charIndex)||0);
      let idx=0;
      for(let i=0;i<cineSubtitleWords.length;i++){
        if(cineSubtitleWords[i].start<=loc) idx=i;
        else break;
      }
      cineSubtitleCursor=idx;
      cineSubtitleText.textContent=cineSubtitleWords.slice(Math.max(0,idx-2),Math.min(cineSubtitleWords.length,idx+9))
        .map(w=>w.word).join(' ');
      cineSubtitle.classList.add('is-visible');
    }
    function cineStartSubtitle(text){
      cineHideSubtitle();
      const raw=String(text||'').replace(/\\s+/g,' ').trim();
      cineSubtitleWords=[...raw.matchAll(/\\S+/g)].map(m=>({word:m[0],start:m.index}));
      if(!cineSubtitleWords.length) return;
      cineSubtitleAt(0);
      const token=cineSubtitleToken;
      cineLastBoundaryAt=0;
      cineSubtitleInterval=setInterval(()=>{
        if(token!==cineSubtitleToken){clearInterval(cineSubtitleInterval);cineSubtitleInterval=null;return;}
        if(cineLastBoundaryAt && performance.now()-cineLastBoundaryAt<750) return;
        cineSubtitleCursor=Math.min(cineSubtitleWords.length-1,cineSubtitleCursor+1);
        cineSubtitleAt(cineSubtitleWords[cineSubtitleCursor].start);
      },310);
    }
    function cineSubtitleBoundary(charIndex){
      cineLastBoundaryAt=performance.now();
      cineSubtitleAt(charIndex);
    }
    function cineStopSubtitle(){
      if(cineSubtitleInterval){clearInterval(cineSubtitleInterval);cineSubtitleInterval=null;}
      if(cineSubtitleDismiss) clearTimeout(cineSubtitleDismiss);
      const token=cineSubtitleToken;
      cineSubtitleDismiss=setTimeout(()=>{
        if(token===cineSubtitleToken) cineHideSubtitle();
      },1250);
    }
    function cineCloseAnswer(){
      cineTextAnswer.classList.remove('is-open');
      cineReport.classList.remove('is-open');
      chatbox.classList.remove('is-expanded');
      cineShade.classList.remove('is-open');
      cineShade.setAttribute('aria-hidden','true');
      // Audio keeps playing independently; Stop button remains available.
    }
    function cineOpenAnswer(mode,question,answerText){
      cineLastQuestion=String(question||'');
      cineLastAnswer=String(answerText||'');
      cineLastMode=mode;
      cineCloseAnswer();
      cineShade.classList.add('is-open');
      cineShade.setAttribute('aria-hidden','false');
      if(mode==='overview'){
        cineTextBody.textContent=cineLastAnswer;
        cineTextAnswer.classList.add('is-open');
      }else{
        cineReport.classList.add('is-open');
      }
    }
    function cineShowVisual(mode){
      const question=cineLastQuestion || 'Tampilkan informasi eksekutif';
      const answerText=cineLastAnswer || 'SELA menampilkan ringkasan data aktif.';
      const selected=['overview','charts','tables','poster','briefing'].includes(mode)?mode:'charts';
      refreshAdvisor(selected,question,answerText);
      cineOpenAnswer(selected,question,answerText);
    }
    function cineOpenHistory(){
      cineCloseAnswer();
      cineShade.classList.add('is-open');
      chatbox.classList.add('is-expanded');
      chatbox.scrollTop=chatbox.scrollHeight;
    }
    function handleQuestion(question){
      const q = String(question || '').trim();
      if(!q) return;
      addMsg('user', q);
      statusLine.textContent = 'Status: SELA sedang menganalisis pertanyaan Anda.';
      setAvatarState('listening');
      queueMicrotask(() => {
        const result = answer(q);
        const isDataQuestion = /(transaksi|sla|vendor|cabang|nomor permohonan|periode|tahun|bottleneck|growth|pertumbuhan|ringkasan|direksi|rekomendasi|proses)/i.test(q);
        const hasEvidence = result.includes('Dasar data:');
        let ans = (isDataQuestion && !hasEvidence && payload.meta.status !== 'empty')
          ? result + selaEvidence(`filter aktif ${metrics.period_first || '-'}–${metrics.period_last || '-'}`,
                                  Number(metrics.transaction_count || 0))
          : result;
        const advisorMode = inferAdvisorMode(q);
        if(advisorMode === 'charts' && !/grafik|chart|bagan/i.test(ans)) ans += '\\n\\nSaya juga menampilkan grafik eksekutif pada workspace advisor.';
        if(advisorMode === 'tables' && !/tabel|table|daftar/i.test(ans)) ans += '\\n\\nSaya juga menampilkan tabel prioritas pada workspace advisor.';
        if(advisorMode === 'poster' && !/poster/i.test(ans)) ans += '\\n\\nSaya juga menampilkan poster eksekutif pada workspace advisor.';
        addMsg('bot', ans);
        boardroomQuestion = q;
        boardroomAnswer = ans;
        if(advisorMode !== 'overview') refreshAdvisor(advisorMode, q, ans);
        setBubble(ans);
        cineOpenAnswer(advisorMode, q, ans);
        speak(ans);
      });
      textInput.value = '';
    }

    // mic
    let recognizer = null;
    let recognizing = false;
    function setupRecognizer(){
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if(!SR){
        statusLine.textContent = 'Status: browser ini belum mendukung pengenalan suara. Gunakan Chrome atau Edge, atau pakai input teks.';
        return null;
      }
      recognizer = new SR();
      recognizer.lang = 'id-ID';
      recognizer.interimResults = false;
      recognizer.maxAlternatives = 1;
      recognizer.onstart = () => {recognizing = true; setAvatarState('listening'); micBtn.textContent='\u23f9\ufe0f Stop'; statusLine.textContent='Status: SELA sedang mendengarkan...'; setBubble('Saya sedang mendengarkan. Silakan bicara dengan jelas ya.'); };
      recognizer.onerror = (e) => {recognizing = false; micBtn.textContent='🎙️ Bicara'; setAvatarState(''); statusLine.textContent = 'Status: mic belum masuk. Pastikan izin microphone di browser sudah Allow, lalu coba lagi. Detail: ' + e.error; setBubble('Saya belum menangkap suara. Coba klik Mic lagi, izinkan microphone, atau gunakan input teks.'); };
      recognizer.onend = () => {recognizing = false; micBtn.textContent='🎙️ Bicara'; if(!window.speechSynthesis.speaking){ setAvatarState(''); statusLine.textContent='Status: selesai mendengarkan, saya siap untuk pertanyaan berikutnya.'; } };
      recognizer.onresult = (event) => { const text = event.results && event.results[0] && event.results[0][0] ? event.results[0][0].transcript : ''; handleQuestion(text); };
      return recognizer;
    }

    micBtn.addEventListener('click', () => {
      if(!recognizer) setupRecognizer();
      if(!recognizer) return;
      try{
        if(!recognizing) recognizer.start(); else recognizer.stop();
      }catch(err){
        statusLine.textContent = 'Status: mic belum bisa digunakan. Coba refresh browser atau izinkan microphone.';
      }
    });
    checkMicBtn.addEventListener('click', () => {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if(SR){
        statusLine.textContent = 'Status: fitur microphone tersedia di browser. Jika belum masuk, pastikan izin microphone = Allow.';
        setBubble('Fitur mic tersedia. Sekarang coba klik tombol Bicara, lalu ucapkan pertanyaannya dengan jelas.');
      } else {
        statusLine.textContent = 'Status: browser ini belum mendukung microphone Web Speech API.';
        setBubble('Browser ini belum mendukung pengenalan suara. Silakan gunakan Chrome atau Edge, atau ketik pertanyaan Anda.');
      }
    });
    testVoiceBtn.addEventListener('click', () => {
      const txt = 'Halo, saya SELA. Suara saya sudah aktif dan siap membantu Anda.';
      setBubble(txt); speak(txt);
    });
    stopVoiceBtn.addEventListener('click', () => {
      speakingGeneration++;
      if('speechSynthesis' in window) window.speechSynthesis.cancel();
      if(mouthDemoTimer){clearTimeout(mouthDemoTimer);mouthDemoTimer=null;}
      if(mouthDemoBtn) mouthDemoBtn.textContent='▶ Demo Ekspresi · 6 dtk';
      setAvatarState('');
      cineHideSubtitle();
      statusLine.textContent = 'Status: suara dihentikan.';
    });
    if(mouthDemoBtn) mouthDemoBtn.addEventListener('click', selaDemoExpressions);
    document.addEventListener('visibilitychange', () => {
      if(!document.hidden && (mouthSpeaking || shapeOpacity.some(v=>v>.01)) && !mouthAnimFrame){
        mouthAnimFrame=requestAnimationFrame(animateMouth);
      }
    });
    sendBtn.addEventListener('click', () => handleQuestion(textInput.value));
    textInput.addEventListener('keydown', (e) => { if(e.key === 'Enter') handleQuestion(textInput.value); });
    document.querySelectorAll('.chip').forEach(btn => btn.addEventListener('click', () => handleQuestion(btn.dataset.question)));
    advisorTabs.forEach(btn => btn.addEventListener('click', () => {
      const mode = btn.dataset.tab || 'overview';
      refreshAdvisor(mode, boardroomQuestion, boardroomAnswer || speechBubble.textContent || '');
      if(!cineReport.classList.contains('is-open')) cineOpenAnswer(mode, boardroomQuestion, boardroomAnswer || '');
    }));
    document.querySelectorAll('.boardroom-action').forEach(btn =>
      btn.addEventListener('click', () => boardroomHandleExport(btn.dataset.export)));
    document.getElementById('cineCloseText').addEventListener('click',cineCloseAnswer);
    document.getElementById('cineCloseReport').addEventListener('click',cineCloseAnswer);
    cineShade.addEventListener('click',cineCloseAnswer);
    document.getElementById('cineShowReport').addEventListener('click',()=>cineShowVisual('charts'));
    document.getElementById('cineHistoryBtn').addEventListener('click',cineOpenHistory);
    document.getElementById('cineCopyAnswer').addEventListener('click',()=>{
      const text=cineLastAnswer||'';
      if(navigator.clipboard&&navigator.clipboard.writeText){
        navigator.clipboard.writeText(text).then(()=>{statusLine.textContent='Status: jawaban tersalin.';})
        .catch(()=>{statusLine.textContent='Status: gunakan pilih teks dan salin.';});
      }
    });
    // Keep the v17 silent expression demo reachable from the advanced options.
    if(mouthDemoBtn) cineVoiceControls.appendChild(mouthDemoBtn);
    cineMoreBtn.addEventListener('click',()=>{
      const next=!cineShortcutPanel.classList.contains('is-expanded');
      cineShortcutPanel.classList.toggle('is-expanded',next);
      cineVoiceControls.classList.toggle('is-expanded',next);
      cineMoreBtn.setAttribute('aria-expanded',String(next));
      cineMoreBtn.textContent=next?'×':'⋯';
    });
    document.addEventListener('keydown',(e)=>{
      if(e.key==='Escape'){cineCloseAnswer();cineShortcutPanel.classList.remove('is-expanded');cineVoiceControls.classList.remove('is-expanded');}
    });

    populateMetrics();
    // v18 remains visually idle until a question is asked, avoiding unnecessary visual rendering.
    addMsg('bot', 'Halo, saya SELA. Senang bisa membantu Anda. Silakan ketik atau ucapkan pertanyaan. Setelah Anda bertanya, saya akan menjawab dan menyiapkan teks, tabel, grafik, poster, atau Boardroom sesuai kebutuhan.');
  </script>
</body>
</html>
    """

    components.html(
        html.replace("___SELA_PAYLOAD___", data_json),
        height=960,  # Native dialog CSS expands the iframe to the viewport.
        scrolling=False,  # Cinematic panels manage their own scroll; prevent nested scrollbars.
    )


# PANGGIL SELA HANYA SAAT DIBUKA (lazy, cached, tidak mengganggu dashboard).
# Perbedaan penting dari launcher v14: ST.BUTTON, bukan HTML <a href="?...">.
# Native Streamlit dialog muncul di TAB YANG SAMA; tidak mengubah URL dan tidak
# menciptakan tab baru. Tombol X pada dialog menutup asisten secara normal.

def _sela_launch_body():
    # Scope the cinematic dialog to SELA only. Keep regular Streamlit tabs intact.
    st.markdown('<div id="sela_v18_dialog_marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown("""
    <style>
    /* SELA v18: the dialog is a transparent full-screen stage; the assistant is
       docked inside its iframe, while reports appear in the center of the SAME tab. */
    div[data-testid="stDialog"]:has(#sela_v18_dialog_marker) [role="dialog"],
    [role="dialog"]:has(#sela_v18_dialog_marker) {
      position:fixed!important; inset:0!important;
      transform:none!important; margin:0!important;
      width:100vw!important; max-width:100vw!important;
      height:100dvh!important; max-height:100dvh!important;
      padding:0!important; overflow:visible!important;
      border:0!important; border-radius:0!important;
      background:transparent!important; box-shadow:none!important;
    }
    div[data-testid="stDialog"]:has(#sela_v18_dialog_marker) iframe,
    [role="dialog"]:has(#sela_v18_dialog_marker) iframe {
      position:fixed!important; inset:0!important;
      width:100vw!important; height:100dvh!important;
      max-height:100dvh!important; border:0!important;
      background:transparent!important; z-index:1!important;
    }
    div[data-testid="stDialog"]:has(#sela_v18_dialog_marker)
      [data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stDialog"]:has(#sela_v18_dialog_marker)
      [data-testid="stVerticalBlock"],
    div[data-testid="stDialog"]:has(#sela_v18_dialog_marker)
      [data-testid="stElementContainer"] {
      padding:0!important; margin:0!important; min-height:0!important;
    }
    div[data-testid="stDialog"]:has(#sela_v18_dialog_marker) button[aria-label="Close"],
    div[data-testid="stDialog"]:has(#sela_v18_dialog_marker) button[aria-label="Close dialog"],
    [role="dialog"]:has(#sela_v18_dialog_marker) button[aria-label="Close"],
    [role="dialog"]:has(#sela_v18_dialog_marker) button[aria-label="Close dialog"] {
      position:fixed!important;top:14px!important;right:17px!important;
      z-index:10000!important; color:#eef8ff!important;
      background:#132a42!important;border:1px solid #466781!important;
      border-radius:999px!important;
    }
    /* Disable the dark full-screen overlay, not the panel controls. */
    div[data-testid="stDialog"]:has(#sela_v18_dialog_marker) ~ div {
      box-shadow:none;
    }
    @media(max-width:700px){
      div[data-testid="stDialog"]:has(#sela_v18_dialog_marker) button[aria-label="Close"] {
        top:8px!important;right:8px!important;
      }
    }
    </style>
    """, unsafe_allow_html=True)
    render_sela_widget(
        df_filtered, periode_col,
        source_version=_sla_source_version,
        period_keys=tuple(selected_periode),
        raw_history=_sela_full_history_source,
    )

if callable(getattr(st, "dialog", None)):
    @st.dialog("SELA • Cinematic Assistant", width="large")
    def _sela_open_dialog():
        # Dialog scoped to its own fragment, without re-rendering the entire app
        # for chat/voice clicks inside the embedded SELA widget.
        _sela_launch_body()
else:
    # Compatibility fallback for older Streamlit, still in the SAME Chrome tab.
    def _sela_open_dialog():
        st.info("SELA dibuka pada halaman ini. Scroll ke panel asisten di bawah.")
        _sela_launch_body()

try:
    _sela_fab_host = st.container(key="sela_floating_launcher_v15")
except TypeError:
    # Keyed containers were introduced after older Streamlit versions.
    _sela_fab_host = st.container()
with _sela_fab_host:
    _sela_fab_clicked = st.button(
        "SELA", key="sela_fab_button_v15",
        help="✦ SELA Premium AI — buka asisten pribadi dalam popup, tanpa tab baru.",
    )

if _sela_fab_clicked or _sela_sidebar_clicked:
    _sela_open_dialog()

# Performance-safe user settings preservation for dynamic tabs.
if _SLA_LAZY_TABS:
    _snapshot = st.session_state.setdefault('_sla_saved_widget_values', {})
    for _key in list(st.session_state.keys()):
        if _key not in ('_sla_saved_widget_values', 'sla_active_main_tab', 'sla_active_report_subtab') \
                and _key.startswith(('jt_', 'jtm_', 'trx_', 'ana_', 'global_', 'map_', 'nilai_', 'periode_')):
            _value = st.session_state[_key]
            if isinstance(_value, (str, bool, int, float, list, tuple)):
                _snapshot[_key] = _value

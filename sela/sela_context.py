# sela/sela_context.py
import pandas as pd
import numpy as np

def build_context(df: pd.DataFrame, periode_col: str, sla_cols: list[str]) -> dict:
    """
    Context ringan: angka-angka penting untuk dijawab cepat.
    Tidak simpan dataframe besar di memory chat.
    """
    ctx = {}
    ctx["rows"] = int(len(df))

    # periode
    if periode_col in df.columns and len(df) > 0:
        periods = df[periode_col].dropna().astype(str).unique().tolist()
        ctx["periode_min"] = periods[0] if periods else None
        ctx["periode_max"] = periods[-1] if periods else None
    else:
        ctx["periode_min"] = None
        ctx["periode_max"] = None

    # SLA averages (detik)
    ctx["sla_avg_sec"] = {}
    for c in sla_cols:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            ctx["sla_avg_sec"][c] = float(s.mean()) if s.notna().any() else np.nan

    # kolom populer (kalau ada)
    for col in ["JENIS TRANSAKSI", "NAMA VENDOR"]:
        if col in df.columns:
            ctx[f"has_{col}"] = True
        else:
            ctx[f"has_{col}"] = False

    return ctx

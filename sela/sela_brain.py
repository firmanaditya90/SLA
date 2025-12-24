# sela/sela_brain.py
import re
import numpy as np
import pandas as pd

def _sec_to_hari(sec):
    if sec is None or (isinstance(sec, float) and np.isnan(sec)):
        return None
    return float(sec) / 86400.0

def _fmt_hari(x, nd=2):
    if x is None:
        return "-"
    s = f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} hari"

def answer_sela(question: str, df: pd.DataFrame, ctx: dict, periode_col: str, sla_cols: list[str]) -> dict:
    """
    Return dict: {reply: str, intent: str, data: optional}
    Ringan: prioritaskan jawaban dari ctx dulu.
    """
    q = (question or "").strip().lower()
    if not q:
        return {"intent": "empty", "reply": "Tanya aku apa aja soal SLA ya 🙂 Misal: 'rata-rata SLA keuangan?' atau 'vendor terlama siapa?'"}

    # 1) Greeting / small talk
    if any(k in q for k in ["halo", "hai", "pagi", "siang", "malam", "assalam"]):
        pmin, pmax = ctx.get("periode_min"), ctx.get("periode_max")
        pr = f"Data yang sedang aktif: {pmin} s/d {pmax}." if pmin and pmax else "Aku siap bantu baca data SLA kamu."
        return {"intent": "greet", "reply": f"Halo! Aku SELA 🤖✨ {pr} Tanyakan apa yang mau kamu cek."}

    # 2) Rata-rata SLA (keuangan/total/vendor/dll)
    m = re.search(r"rata[\s-]*rata.*(keuangan|total|vendor|fungsional|perbendaharaan)", q)
    if m:
        key = m.group(1).upper()
        if key == "TOTAL":
            key = "TOTAL WAKTU"
        if key in ctx.get("sla_avg_sec", {}):
            days = _sec_to_hari(ctx["sla_avg_sec"][key])
            return {"intent": "avg_sla", "reply": f"Rata-rata SLA **{key}** pada periode aktif adalah **{_fmt_hari(days)}**."}
        return {"intent": "avg_sla", "reply": f"Aku belum nemu kolom **{key}** di data aktif. Coba cek nama kolom SLA yang tersedia ya."}

    # 3) “Periode berapa yang paling lama?” (butuh groupby)
    if "periode" in q and ("terlama" in q or "tertinggi" in q or "paling lama" in q):
        if periode_col not in df.columns:
            return {"intent": "missing", "reply": "Kolom periode tidak ditemukan di data, jadi aku belum bisa bandingin per periode."}
        target = "TOTAL WAKTU" if "total" in q else ("KEUANGAN" if "keuangan" in q else None)
        if not target or target not in df.columns:
            return {"intent": "missing", "reply": "Sebutkan mau bandingkan SLA apa ya? Misal: 'periode terlama SLA keuangan'."}

        g = df.groupby(df[periode_col].astype(str))[target].mean()
        g = pd.to_numeric(g, errors="coerce").dropna()
        if g.empty:
            return {"intent": "no_data", "reply": "Aku belum dapat angka SLA yang valid untuk dibandingkan per periode."}
        p = g.idxmax()
        days = _sec_to_hari(float(g.loc[p]))
        return {"intent": "max_period", "reply": f"Periode dengan SLA **{target}** terlama adalah **{p}** dengan rata-rata **{_fmt_hari(days)}**."}

    # 4) Vendor terlama (kalau ada)
    if ("vendor" in q) and ("terlama" in q or "terburuk" in q or "paling lama" in q):
        if "NAMA VENDOR" not in df.columns:
            return {"intent": "missing", "reply": "Di data aktif belum ada kolom **NAMA VENDOR**, jadi aku belum bisa bikin ranking vendor."}
        target = "VENDOR" if "VENDOR" in sla_cols else ("TOTAL WAKTU" if "TOTAL WAKTU" in sla_cols else None)
        if not target or target not in df.columns:
            return {"intent": "missing", "reply": "Aku belum nemu kolom SLA yang bisa dipakai untuk analisis vendor (contoh: VENDOR / TOTAL WAKTU)."}

        g = df.groupby("NAMA VENDOR")[target].mean()
        g = pd.to_numeric(g, errors="coerce").dropna()
        if g.empty:
            return {"intent": "no_data", "reply": "Data SLA vendor kosong / belum terbaca."}
        worst = g.idxmax()
        days = _sec_to_hari(float(g.loc[worst]))
        return {"intent": "vendor_worst", "reply": f"Vendor dengan SLA **{target}** terlama adalah **{worst}** dengan rata-rata **{_fmt_hari(days)}**."}

    # 5) fallback: bantu “tanya yang benar”
    tips = [
        "• 'rata-rata SLA keuangan?'",
        "• 'periode terlama SLA total waktu?'",
        "• 'vendor terlama siapa?'",
        "• 'berapa jumlah transaksi?'",
    ]
    if "jumlah transaksi" in q or "berapa transaksi" in q:
        return {"intent": "count", "reply": f"Jumlah transaksi pada periode aktif adalah **{ctx.get('rows', 0):,}**."}

    return {"intent": "fallback", "reply": "Aku bisa bantu, tapi biar tepat coba tanya seperti ini:\n" + "\n".join(tips)}

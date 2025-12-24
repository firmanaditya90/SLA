# sela/sela_ui.py
import streamlit as st
from sela.sela_context import build_context
from sela.sela_brain import answer_sela

def render_sela_panel(df_filtered, periode_col, sla_cols):
    st.markdown("## 🤖 SELA — Asisten Analis SLA")
    st.caption("Aku jawab cepat dari data yang sedang kamu filter. Tanyakan apa saja soal SLA, periode, vendor, transaksi.")

    # memory ringan
    if "sela_chat" not in st.session_state:
        st.session_state["sela_chat"] = []

    ctx = build_context(df_filtered, periode_col, sla_cols)

    # tampilkan chat history
    for msg in st.session_state["sela_chat"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # input
    q = st.chat_input("Tulis pertanyaan… (contoh: rata-rata SLA keuangan?)")
    if q:
        st.session_state["sela_chat"].append({"role": "user", "content": q})

        out = answer_sela(q, df_filtered, ctx, periode_col, sla_cols)
        reply = out["reply"]

        with st.chat_message("assistant"):
            st.markdown(reply)

        st.session_state["sela_chat"].append({"role": "assistant", "content": reply})

    # tombol kecil
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧹 Bersihkan chat"):
            st.session_state["sela_chat"] = []
            st.rerun()
    with c2:
        st.caption("Mode: cepat (rule + insight)")

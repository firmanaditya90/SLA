# 📊 SLA Payment Analyzer

Aplikasi web berbasis **Streamlit** untuk menghitung dan menganalisis SLA pembayaran berdasarkan data Excel.

## 🚀 Fitur
- Upload file Excel (`.xlsx`)
- Otomatis parsing SLA format:
  - `"SLA X days HH:MM:SS"`
  - `"SLA HH:MM:SS"`
- Hitung rata-rata SLA per proses
- Rekap berdasarkan **Jenis Transaksi** dan **Nama Vendor**
- Filter berdasarkan **Periode**
- Download hasil rekap dalam Excel

## 📂 Struktur Data yang Dibutuhkan
Minimal kolom:
- `PERIODE`
- `JENIS TRANSAKSI`
- `NAMA VENDOR`
- Kolom SLA: `FUNGSIONAL`, `VENDOR`, `KEUANGAN`, `PERBENDAHARAAN`, `TOTAL` (opsional)

## 🛠 Cara Deploy di Streamlit Cloud
1. **Fork / Clone** repo ini ke akun GitHub kamu.
2. Buka [Streamlit Cloud](https://share.streamlit.io) → login dengan GitHub.
3. Klik **New App** → pilih repo, branch `main`, file `app.py`.
4. Klik **Deploy** → aplikasi siap digunakan.

## 📄 Lisensi
MIT License

# 🚩 Am I The Red Flag? — Assessment Simulator

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Deployment-Vercel%20%7C%20VPS-black.svg?logo=vercel)](https://vercel.com/)

**Am I The Red Flag?** adalah aplikasi web simulator interaktif berbasis kecerdasan buatan (AI) untuk menguji respon psikologis, kedewasaan emosional, dan etika komunikasi seseorang dalam menghadapi berbagai skenario dinamika sosial sehari-hari.

Pengguna akan berinteraksi melalui obrolan langsung (roleplay chat) dengan karakter AI dalam 3 babak situasi penuh tekanan, kemudian di akhir sesi menerima evaluasi kepribadian mendalam berupa skor *red flag*, gelar julukan karakter, analisis kekuatan/kelemahan respon, hingga kartu identitas hasil asesmen yang dapat diunduh langsung sebagai gambar.

---

## 📑 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Teknologi & Tech Stack](#-teknologi--tech-stack)
- [Struktur Proyek](#-struktur-proyek)
- [Prasyarat Sistem](#-prasyarat-sistem)
- [Panduan Instalasi](#-panduan-instalasi)
- [Konfigurasi Environment (.env)](#-konfigurasi-environment-env)
- [Cara Menjalankan Aplikasi](#-cara-menjalankan-aplikasi)
  - [1. Menjalankan di Lokal (Development)](#1-menjalankan-di-lokal-development)
  - [2. Menjalankan untuk Production](#2-menjalankan-untuk-production)
  - [3. Deployment ke Vercel](#3-deployment-ke-vercel)
- [Daftar Endpoint API](#-daftar-endpoint-api)
- [Troubleshooting & FAQ](#-troubleshooting--faq)

---

## ✨ Fitur Utama

1. **3 Babak Skenario Dinamis Realistis**:
   - **Bab 1 (Hubungan Personal):** Menghadapi konflik dengan pasangan setelah insiden tanpa kabar/ghosting.
   - **Bab 2 (Krisis Profesional):** Mengelola kepanikan rekan kerja di tengah tenggat waktu menjelang rapat dewan direksi.
   - **Bab 3 (Tekanan Sosial / Etika Finansial):** Merespon permintaan pinjaman uang mendadak dari teman lama dengan latar belakang sensitif.
2. **Generasi Skenario Berbasis AI (OpenRouter)**:
   - Skenario dapat dibuat secara dinamis menggunakan model AI terkini (`google/gemini-3.1-flash-lite`), dengan mekanisme *fallback scenario* otomatis jika terjadi kendala koneksi API.
3. **Sistem Evaluasi Psikologis Komprehensif**:
   - Penghitungan skor Red Flag (0–100%).
   - Predikat julukan karakter unik (contoh: *The Diplomat*, *The Gaslighter*, *The Boundary Builder*).
   - Analisis mendalam poin *Red Flag* vs *Green Flag* yang ditunjukkan pengguna.
   - Ulasan evaluasi per babak serta saran langkah perbaikan diri konkret.
4. **Ekspor ID Card Hasil Asesmen**:
   - Hasil evaluasi dapat langsung diunduh menjadi gambar kartu hasil (menggunakan library `html2canvas`).
5. **Otentikasi Google Sign-In & Sistem Kuota**:
   - Login instan menggunakan Google Identity Services (GIS) dan session token aman berbasis JWT.
   - Pembatasan kuota permainan (default: 3x sesi permainan per pengguna) untuk kontrol penggunaan API.
6. **Dashboard & Riwayat Permainan**:
   - Melacak histori sesi asesmen sebelumnya beserta statistik hasil tes.
7. **Statistik Kunjungan**:
   - Pencatatan otomatis *total views* dan *unique visitors* berbasis IP dan fingerprint perangkat.
8. **Desain Mobile-First & Responsif**:
   - Tampilan modern dengan *glassmorphism*, dark/vibrant styling, dan sinkronisasi tinggi layar visual (`--app-height`) untuk mencegah masalah keyboard pada perangkat mobile.

---

## 🛠 Teknologi & Tech Stack

### Backend
- **Bahasa**: [Python 3.10+](https://www.python.org/)
- **Framework Web**: [FastAPI](https://fastapi.tiangolo.com/) (kinerja tinggi, asynchronous)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **ORM & Database**:
  - [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
  - **SQLite**: Database default tanpa konfigurasi tambahan (`redflag.db`)
  - **MySQL**: Didukung untuk kebutuhan production menggunakan driver `PyMySQL` dan `cryptography`
- **Keamanan & Otentikasi**:
  - `PyJWT` (HS256 JWT Token)
  - `google-auth` (Verifikasi token Google OAuth 2.0 di server)
- **AI Integration**:
  - [OpenRouter API](https://openrouter.ai/) (Model default: `google/gemini-3.1-flash-lite`) via library `requests`

### Frontend
- **Arsitektur**: Single Page Application (SPA) murni tanpa framework berat (Vanilla JavaScript ES6+, HTML5, CSS3).
- **Tipografi**: Google Fonts (*Plus Jakarta Sans*, *Inter*).
- **Library Tambahan**:
  - [html2canvas](https://html2canvas.hertzen.com/) (Generate kartu evaluasi ke format gambar)
  - [Google Identity Services (GSI)](https://developers.google.com/identity/gsi/web) (Google Sign-In)

### Deployment & DevOps
- **Vercel Serverless Ready**: Dilengkapi dengan konfigurasi [`vercel.json`](file:///d:/ami-redflag/vercel.json) dan entrypoint [`api/index.py`](file:///d:/ami-redflag/api/index.py).

---

## 📁 Struktur Proyek

```text
ami-redflag/
├── api/
│   └── index.py             # Entrypoint serverless untuk deployment ke Vercel
├── static/
│   ├── css/
│   │   └── style.css        # Styling lengkap UI aplikasi (design tokens, layout, animasi)
│   ├── js/
│   │   └── app.js           # Logika interaktif frontend (chat loop, state, auth, render)
│   ├── favicon.svg          # Favicon resmi aplikasi
│   └── index.html           # File markup HTML utama
├── auth.py                  # Logika otentikasi Google OAuth2 & helper JWT session
├── database.py              # Definisi model database SQLAlchemy & inisialisasi koneksi
├── main.py                  # Core backend FastAPI, routing API, prompt AI, & evaluator
├── requirements.txt         # Daftar pustaka & dependensi Python
├── vercel.json              # Konfigurasi rewrite & routing Vercel
├── .env.example             # Template variabel environment
└── README.md                # Dokumentasi proyek
```

---

## 📋 Prasyarat Sistem

Sebelum memulai instalasi, pastikan perangkat Anda telah terpasang:
- **Python** versi `3.10` atau yang lebih baru ([Unduh Python](https://www.python.org/downloads/))
- **Git** (Opsional, untuk clone repository)
- **Koneksi Internet** (Untuk instalasi package dan request ke API OpenRouter)
- **Akun OpenRouter** untuk mendapatkan API Key ([Daftar di OpenRouter](https://openrouter.ai/))

---

## 🚀 Panduan Instalasi

### 1. Clone atau Unduh Repository
```bash
git clone https://github.com/username/ami-redflag.git
cd ami-redflag
```
*(Atau buka folder direktori proyek ini langsung di terminal).*

### 2. Buat Virtual Environment (Sangat Disarankan)

**Di Windows (Command Prompt / PowerShell):**
```bash
python -m venv venv
venv\Scripts\activate
```

**Di macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Pasang Dependensi
Pastikan environment aktif, lalu jalankan:
```bash
pip install -r requirements.txt
```

---

## ⚙ Konfigurasi Environment (.env)

Salin file template [`.env.example`](file:///d:/ami-redflag/.env.example) menjadi `.env`:

**Di Windows:**
```bash
copy .env.example .env
```

**Di macOS / Linux:**
```bash
cp .env.example .env
```

Buka file `.env` yang baru dibuat dan sesuaikan variabel konfigurasi berikut:

```ini
# [WAJIB] Kunci API OpenRouter untuk fitur AI Chat & Evaluasi
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# [OPSIONAL] Google Client ID untuk mengaktifkan fitur Login Google
# Dapatkan dari Google Cloud Console -> Credentials -> OAuth 2.0 Client ID
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

# [WAJIB] Kunci rahasia untuk tanda tangan sesi JWT pengguna
SECRET_KEY=ganti_dengan_string_acak_rahasia_dan_panjang_12345

# [OPSIONAL] Konfigurasi Database MySQL
# Jika dibiarkan kosong, aplikasi otomatis menggunakan SQLite lokal (redflag.db)
DB_HOST=
DB_NAME=
DB_USERNAME=
DB_PASSWORD=
DB_PORT=3306
```

> [!TIP]
> **Mode SQLite Otomatis:** Anda tidak perlu menginstall database MySQL untuk mencobanya di komputer lokal. Cukup kosongkan `DB_HOST`, dan sistem akan langsung membuat file database lokal SQLite bernama `redflag.db`.

---

## 💻 Cara Menjalankan Aplikasi

### 1. Menjalankan di Lokal (Development)

Jalankan perintah Uvicorn berikut dari direktori root proyek:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
atau menggunakan modul python:
```bash
python -m uvicorn main:app --reload --port 8000
```

Buka browser Anda dan navigasikan ke:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

Dokumentasi interaktif Swagger UI dari FastAPI dapat diakses di:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

### 2. Menjalankan untuk Production (Self-Hosted VPS / Docker)

Gunakan *multi-workers* untuk melayani trafik produksi:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

### 3. Deployment ke Vercel

Proyek ini sudah dilengkapi konfigurasi serverless untuk Vercel:
1. Pasang [Vercel CLI](https://vercel.com/docs/cli): `npm i -g vercel`
2. Jalankan perintah:
   ```bash
   vercel
   ```
3. Tambahkan Environment Variables pada dashboard Vercel:
   - `OPENROUTER_API_KEY`
   - `SECRET_KEY`
   - `GOOGLE_CLIENT_ID`
   - `DB_HOST`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`, `DB_PORT` (Gunakan provider cloud MySQL seperti PlanetScale, Aiven, atau TiDB Cloud, karena filesystem SQLite bersifat *ephemeral/read-only* pada serverless lambdas).

---

## 🔌 Daftar Endpoint API

| Metode | Endpoint | Keterangan | Autentikasi |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Melayani halaman utama web (`static/index.html`) | Publik |
| `POST` | `/api/auth/google` | Verifikasi token login Google dan menerbitkan JWT token sesi | Publik |
| `GET` | `/api/auth/me` | Mengambil data profil dan sisa kuota user yang sedang login | Bearer JWT |
| `POST` | `/api/auth/logout` | Menghapus status sesi pengguna | Bearer JWT |
| `GET` | `/api/user/history` | Mengambil histori riwayat sesi asesmen pengguna | Bearer JWT |
| `POST` | `/api/stats/visit` | Mencatat kunjungan dan tracking visitor unik website | Publik |
| `GET` | `/api/stats` | Melihat total kunjungan & pengunjung unik | Publik |
| `POST` | `/api/generate-scenarios` | Menghasilkan skenario dinamis 3 babak berbasis profil pengguna | Bearer JWT / Publik |
| `POST` | `/api/chat` | Mengirim respon chat dan menerima tanggapan roleplay dari karakter AI | Bearer JWT / Publik |
| `POST` | `/api/evaluate` | Menghitung skor red flag, kategori, analisis perilaku & julukan | Bearer JWT / Publik |

---

## ❓ Troubleshooting & FAQ

<details>
<summary><b>1. Error: <code>401 Unauthorized: Silakan login dengan akun Google</code></b></summary>
Beberapa fitur (seperti memulai sesi obrolan yang tercatat dan menyimpan histori) memerlukan login. Pastikan Anda sudah login menggunakan Google atau pastikan token tersimpan di browser.
</details>

<details>
<summary><b>2. Error: <code>API Key OpenRouter tidak valid atau kuota habis</code></b></summary>
Pastikan Anda sudah mengisi <code>OPENROUTER_API_KEY</code> di file <code>.env</code> dengan benar dan akun OpenRouter Anda memiliki saldo/kredit aktif untuk memproses chat completion.
</details>

<details>
<summary><b>3. Bagaimana cara reset kuota percobaan bermain?</b></summary>
Secara default setiap user mendapatkan 3 kuota percobaan (<code>max_trials = 3</code>). Anda dapat mereset kuota langsung melalui database pada tabel <code>users</code> dengan mengupdate kolom <code>trial_used = 0</code>.
</details>

<details>
<summary><b>4. Tombol Google Sign-in tidak merespon di localhost</b></summary>
Pastikan Client ID di Google Cloud Console telah mendaftarkan <code>http://localhost:8000</code> dan <code>http://127.0.0.1:8000</code> di bagian <i>Authorized JavaScript origins</i>.
</details>

---

## 📄 Lisensi

Proyek ini dirilis di bawah lisensi [MIT](LICENSE). Silakan gunakan dan kembangkan secara bebas untuk keperluan edukasi maupun eksperimen personal.

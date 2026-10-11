# 🌊 Neptune Aquaculture Copilot

**Sistem Monitoring Tambak Resilien dengan AI Agent & Hybrid Edge Fallback**

Neptune Aquaculture Copilot adalah solusi *Internet of Things* (IoT) dan kecerdasan buatan (AI) yang dirancang untuk mencegah kematian massal komoditas di tambak pesisir. Sistem ini mengubah data telemetri mentah menjadi diagnosis biologis yang presisi dan mengamankan kolam dari risiko infrastruktur internet yang tidak stabil (titik kegagalan tunggal) melalui arsitektur *Hybrid Edge Fallback*.

---

## 🎥 Demonstrasi Proyek
> **Catatan untuk Reviewer:** 
> Video demonstrasi sistem (skenario Normal & Edge Fallback) dapat diakses melalui tautan berikut:
> **[👉 Klik di sini untuk melihat Video Demo (Google Drive) ](https://drive.google.com/drive/folders/1f-D58fvnegFORL6ABDzmfkvestOG9eQd?usp=drive_link)**

---

## ✨ Fitur Utama

1. **RAG-Powered Multivariable Diagnostic:** Menganalisis 5 parameter air secara bersamaan (Suhu, pH, DO, Nitrit, Secchi) menggunakan IBM Langflow, Astra DB (SOP Knowledge Base), dan Groq LLM untuk memberikan diagnosis akurat tanpa halusinasi.
2. **Hybrid Edge Fallback (Resilient IoT):** Jika koneksi *cloud* terputus, sistem lokal (*edge*) akan mengambil alih secara otonom untuk memastikan aktuator darurat (aerator/kincir) tetap aktif.
3. **Dwi-Modalitas HITL via Telegram:** Interaksi *Human-in-the-Loop* yang memungkinkan petambak menerima peringatan darurat dan berkonsultasi langsung dengan AI Copilot melalui Telegram.
4. **Stress-Test Simulator:** Lingkungan pengujian terintegrasi untuk mensimulasikan transmisi data sensor normal dan anomali jaringan.

---

## 🏗️ Arsitektur Sistem & Alur Kerja

`Sensor IoT → Edge/Local Gateway → IBM Langflow Orchestrator (Astra DB + Groq) → Telegram HITL → Tindakan Petambak`

*Jika koneksi internet gagal, alur otomatis terpotong di `Edge Gateway` yang akan mengeksekusi *Local Fallback Rules* tanpa bergantung pada AI Cloud.*

### Tech Stack
* **AI Orchestration:** IBM Langflow
* **LLM Engine:** Groq (Llama 3 / Qwen)
* **Vector & Memory Database:** DataStax Astra DB
* **Runtime / IoT Bridge:** Python 3.10+ (dengan `hitl_simulator.py`)
* **Deployment:** Docker Compose

---

## 🚀 Panduan Instalasi & Persiapan

### 1. Prasyarat Sistem
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) sudah terinstal dan berjalan.
* [Python 3.10+](https://www.python.org/downloads/) terinstal.
* Token Bot Telegram dan API Key terkait (Langflow, Groq).

### 2. Kloning Repositori & Setup Environment
```bash
git clone https://github.com/Alrumi08/Neptune-aquakulture-Copilot.git
cd Neptune-aquakulture-Copilot

# Buat file konfigurasi environment
cp .env.example .env
```
Isi variabel pada file `.env` yang baru saja dibuat:
```env
TELEGRAM_TOKEN=token_bot_telegram_anda
TELEGRAM_CHAT_ID=id_chat_telegram_anda
LANGFLOW_API_KEY=api_key_langflow_anda
```

### 3. Menjalankan Server IBM Langflow
Jalankan Docker Compose untuk mengangkat *container* Langflow:
```bash
docker compose up -d
```
1. Buka browser dan akses `http://localhost:7860`.
2. Impor file `WorkFlow_Neptune.json` ke dalam workspace Langflow.
3. Pastikan komponen Astra DB dan LLM sudah terkoneksi dengan kredensial yang valid.

---

## 🧪 Skenario Pengujian (Simulator)

Proyek ini dilengkapi dengan skrip `hitl_simulator.py` untuk menguji dua skenario utama di lapangan.

### Skenario 1: Cloud AI Normal (Koneksi Internet Lancar)
Skenario ini mensimulasikan kondisi di mana data sensor berhasil dikirim ke Langflow, diproses oleh AI, dan diteruskan ke Telegram.
1. Buka file `hitl_simulator.py`.
2. Pastikan variabel simulasi diatur ke `False`:
   ```python
   SIMULASI_INTERNET_PUTUS = False
   ```
3. Jalankan simulator:
   ```bash
   python hitl_simulator.py
   ```
4. **Hasil:** Sistem akan mencetak log respons 200 OK dari Langflow, dan bot Telegram akan mengirimkan diagnosis AI kepada petambak.

### Skenario 2: Hybrid Edge Fallback (Koneksi Internet Putus)
Skenario ini mensimulasikan kondisi ketika tambak kehilangan sinyal internet atau Langflow mengalami *timeout*.
1. Buka file `hitl_simulator.py`.
2. Ubah variabel simulasi menjadi `True` untuk memutus jalur *cloud* secara buatan:
   ```python
   SIMULASI_INTERNET_PUTUS = True
   ```
3. Jalankan ulang simulator:
   ```bash
   python hitl_simulator.py
   ```
4. **Hasil:** Terminal akan menampilkan log kegagalan koneksi (*timeout/offline*). Dalam hitungan detik, fungsi `trigger_edge_fallback()` mengambil alih, mencetak peringatan aktivasi aerator lokal, dan mengirim notifikasi darurat (jika SMS/jaringan seluler dasar masih disimulasikan hidup).
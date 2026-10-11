import json
import os
import time
import requests

# =============================================================================
# KONFIGURASI TELEGRAM BOT
# =============================================================================
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =============================================================================
# KONFIGURASI HYBRID EDGE FALLBACK
# =============================================================================
# Ganti ke False untuk menguji jalur Cloud Online normal.
SIMULASI_INTERNET_PUTUS = False

# Endpoint & autentikasi Langflow
LANGFLOW_ENDPOINT = "http://localhost:7860/api/v1/run/480767cf-89bb-47b8-8a80-50316bb8f0bd"
LANGFLOW_API_KEY  = os.getenv("LANGFLOW_API_KEY")
LANGFLOW_TIMEOUT  = 10  # detik

# Data telemetri darurat yang dikirim ke Langflow / dicek secara lokal
TELEMETRI_DARURAT = {
    "suhu":   33.4,
    "ph":     8.9,
    "do":     2.2,
    "nitrit": 1.2,
    "secchi": 18,
}

# =============================================================================
# HYBRID EDGE FALLBACK — FUNGSI INTI
# =============================================================================

def trigger_edge_fallback(telemetri: dict):
    """
    Dijalankan saat jaringan internet mati sepenuhnya.
    Menggantikan notifikasi Telegram dengan aksi aktuator fisik lokal.
    """
    print("\n" + "!" * 70)
    print("  [EDGE FALLBACK OFFLINE] -- KONEKSI CLOUD TERPUTUS")
    print("  Sistem berpindah ke mode darurat lokal (offline).")
    print("!" * 70)
    print("\n  Data Telemetri Terdeteksi Lokal:")
    print(f"    Suhu   : {telemetri.get('suhu')} C")
    print(f"    pH     : {telemetri.get('ph')}")
    print(f"    DO     : {telemetri.get('do')} mg/L")
    print(f"    Nitrit : {telemetri.get('nitrit')} mg/L")
    print(f"    Secchi : {telemetri.get('secchi')} cm")
    print()
    print("  [AKTUATOR FISIK -- EKSEKUSI OTOMATIS LOKAL]")
    print("  +----------------------------------------------------------------+")
    print("  |  [SIRINE DARURAT]  : BEEP! BEEP! BEEP! BEEP! BEEP!            |")
    print("  |  [Smart Feeder]    : DIKUNCI -> OFF (100% pakan dihentikan)    |")
    print("  |  [Kincir Air]      : DINYALAKAN -> 100% (aerasi maksimum)      |")
    print("  +----------------------------------------------------------------+")
    print()
    print("  [!] Notifikasi Telegram TIDAK DAPAT dikirim -- jaringan offline.")
    print("  [v] Protokol keselamatan fisik berhasil dijalankan secara lokal.")
    print("!" * 70 + "\n")


def kirim_ke_langflow(telemetri: dict) -> tuple[bool, str]:
    """
    1. Cek konektivitas internet via Telegram API.
    2. Kirim telemetri ke Langflow dengan header x-api-key.
    3. Parse teks keputusan AI dari respons Langflow.

    Returns:
        (True,  teks_keputusan) -> internet hidup, lanjut ke alur HITL Telegram.
        (False, "")             -> internet mati, jalankan edge fallback.
    """
    # --- Simulasi paksa internet putus ---
    if SIMULASI_INTERNET_PUTUS:
        print("\n[HYBRID GATEWAY] Flag SIMULASI_INTERNET_PUTUS=True -> memaksa jalur Edge Fallback.")
        trigger_edge_fallback(telemetri)
        return False, ""

    # --- Cek konektivitas internet via Telegram API ---
    print("\n[HYBRID GATEWAY] Memeriksa konektivitas internet...")
    try:
        cek = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
            timeout=5
        )
        cek.raise_for_status()
        print("[CLOUD ONLINE] Internet tersedia (Telegram API terjangkau).")
    except requests.exceptions.RequestException as e:
        print(f"[CLOUD ONLINE] GAGAL - Internet tidak tersedia: {e}")
        print("[HYBRID GATEWAY] Tidak ada koneksi -> mengalihkan ke Edge Fallback.")
        trigger_edge_fallback(telemetri)
        return False, ""

    # --- Kirim ke Langflow dengan header autentikasi ---
    print("[HYBRID GATEWAY] Mengirim telemetri ke Langflow AI...")
    headers = {
        "x-api-key": LANGFLOW_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "input_value": json.dumps(telemetri, ensure_ascii=False),
        "output_type": "chat",
        "input_type":  "chat"
    }
    teks_keputusan = ""
    try:
        response = requests.post(
            LANGFLOW_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=LANGFLOW_TIMEOUT
        )
        response.raise_for_status()
        print(f"[LANGFLOW AI] Respons diterima (HTTP {response.status_code}).")

        # Parse teks keputusan dari struktur respons Langflow
        data = response.json()
        try:
            teks_keputusan = (
                data["outputs"][0]["outputs"][0]
                    ["results"]["message"]["text"]
            )
            print(f"[LANGFLOW AI] Keputusan: {teks_keputusan[:120]}...")
        except (KeyError, IndexError):
            print("[LANGFLOW AI] Respons 200 OK namun struktur output tidak dikenali.")

    except requests.exceptions.RequestException as e:
        print(f"[LANGFLOW AI] Tidak tersedia ({e}) -- HITL Telegram tetap berjalan.")

    # Internet hidup -> lanjut ke HITL Telegram
    return True, teks_keputusan


# =============================================================================
# FUNGSI KOMUNIKASI TELEGRAM
# =============================================================================
def kirim_telegram(pesan: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": pesan,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[ERROR KIRIM TELEGRAM]: {e}")

def get_last_update_id():
    """Mengambil ID pesan terakhir agar pesan lama tidak terbaca ulang."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=5).json()
        updates = res.get("result", [])
        if updates:
            return updates[-1]["update_id"]
    except Exception:
        pass
    return 0

def dengarkan_konfirmasi_telegram(last_id: int, timeout_detik: int = 90) -> bool:
    """Mendengarkan keputusan petambak ('iya' / 'tidak') dari Telegram."""
    print(f"\n[TELEGRAM]: Menunggu keputusan petambak dari Telegram ({timeout_detik} detik)...")
    start_time = time.time()
    offset = last_id + 1

    kata_setuju = ["iya", "ya", "ok", "oke", "setuju", "acc", "gas", "y", "boleh"]
    kata_tolak = ["tidak", "gak", "enggak", "batal", "tolak", "jangan", "stop", "n"]

    while time.time() - start_time < timeout_detik:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=3"
        try:
            res = requests.get(url, timeout=8).json()
            for update in res.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                teks_mentah = msg.get("text", "")

                if chat_id == str(TELEGRAM_CHAT_ID) and teks_mentah:
                    # Normalisasi pesan: hapus tanda baca, garis miring, dan spasi
                    teks = (
                        teks_mentah.lower()
                        .replace("'", "")
                        .replace('"', "")
                        .replace("/", "")
                        .replace("!", "")
                        .replace(".", "")
                        .strip()
                    )
                    print(f" -> [RESPON TELEGRAM DITERIMA]: \"{teks_mentah}\"")

                    if any(teks == k or k in teks.split() for k in kata_setuju):
                        kirim_telegram("✅ *[AKSI DIIZINKAN]*\n\nPersetujuan diterima. Aplikasi bahan kimia resmi dijadwalkan ke teknisi tambak!")
                        return True
                    elif any(teks == k or k in teks.split() for k in kata_tolak):
                        kirim_telegram("❌ *[AKSI DILARANG]*\n\nPenolakan dicatat. Tindakan kimiawi dibatalkan total. Aerasi otonom tetap berjalan.")
                        return False
                    else:
                        kirim_telegram("⚠️ Mohon balas dengan kata *iya* untuk mengizinkan atau *tidak* untuk melarang.")
        except Exception:
            pass
        time.sleep(1)

    print("[TIMEOUT]: Waktu habis. Tindakan kimiawi otomatis dibatalkan demi keamanan.")
    kirim_telegram("⏱️ *[TIMEOUT]*\n\nWaktu tunggu habis tanpa respon. Tindakan kimiawi dibatalkan otomatis demi keselamatan ekosistem.")
    return False


# =============================================================================
# MESIN LOGIKA KEPUTUSAN AI (EVALUASI TELEMETRI)
# =============================================================================
def evaluasi_kondisi_tambak(sensor: dict) -> dict:
    """
    Mesin aturan deterministik berbasis SOP akuakultur
    (merefleksikan model Langflow AI Co-Pilot).
    """
    suhu = sensor.get("suhu", 29.0)
    do = sensor.get("do", 5.5)
    ph = sensor.get("ph", 7.8)

    otonom = []
    hitl = []
    keparahan = "NORMAL"
    ringkasan = f"Parameter perairan stabil (Suhu: {suhu}°C, DO: {do} mg/L, pH: {ph})."

    # Evaluasi Ambang Batas Kritis / Waspada
    if do < 3.0 or suhu > 33.0 or ph < 6.8:
        keparahan = "KRITIS"
        ringkasan = f"Kondisi KRITIS: Suhu {suhu}°C, DO {do} mg/L, dan pH {ph} memicu risiko stres akut & hipoksia!"

        otonom.append({
            "status": "Nyalakan 100% kincir air dan blower aerasi dasar",
            "alasan": f"DO {do} mg/L berada di bawah ambang batas kritis (< 3.0 mg/L)."
        })
        otonom.append({
            "status": "Kunci Smart Feeder (Matikan Pakan 100%)",
            "alasan": "Pemberian pakan saat DO kritis meningkatkan beban dekomposisi organik."
        })
        if suhu > 32.5:
            otonom.append({
                "status": "Aktifkan pompa sirkulasi air bawah",
                "alasan": "Mengurangi stratifikasi panas kolom air."
            })

        hitl.append({
            "pesan_wa": f"Suhu {suhu}°C & DO drop ke {do} mg/L (pH {ph}). Kincir telah dimaksimalkan otomatis. Mohon izin tebar kapur dolomit 10 ppm & oksigen granul darurat?",
            "menunggu_konfirmasi": True
        })

    elif do < 4.5 or suhu > 31.5 or ph < 7.2:
        keparahan = "WASPADA"
        ringkasan = f"Status WASPADA: Terjadi fluktuasi parameter (Suhu: {suhu}°C, DO: {do} mg/L, pH: {ph})."

        otonom.append({
            "status": "Tingkatkan putaran kincir air 50% dan kurangi pakan 30%",
            "alasan": "DO mulai menurun di bawah angka optimal (4.5 mg/L)."
        })
    else:
        keparahan = "NORMAL"

    return {
        "mode": "analisis_sensor",
        "tingkat_keparahan": keparahan,
        "ringkasan": ringkasan,
        "Aksi_Otonom": otonom,
        "Human_in_the_Loop": hitl,
        "rujukan_sop": ["SOP KUALITAS AIR & KESELAMATAN BIOTA"]
    }


# =============================================================================
# SIMULATOR MONITORING (LOOP 24 JAM)
# =============================================================================
def jalankan_monitoring_kontinu():
    # Daftar aliran data sensor simulasi waktu nyata
    urutan_skenario = [
        {"waktu": "08:00 WIB", "data": {"suhu": 28.5, "do": 5.8, "ph": 7.9}, "desc": "Kondisi Pagi Hari (Normal)"},
        {"waktu": "11:30 WIB", "data": {"suhu": 31.8, "do": 4.8, "ph": 7.6}, "desc": "Menjelang Siang Hari (Normal Menghangat)"},
        {"waktu": "14:15 WIB", "data": {"suhu": 33.8, "do": 2.7, "ph": 6.3, "nitrit": 1.2, "secchi": 18}, "desc": "Panas Terik Ekstrem & Hipoksia Akut (KRITIS!)"},
        {"waktu": "16:00 WIB", "data": {"suhu": 30.2, "do": 5.2, "ph": 7.5}, "desc": "Pasca Intervensi (Kembali Stabil)"}
    ]

    print("\n" + "=" * 70)
    print("       AI CO-PILOT Neptune - SISTEM MONITORING")
    print("=" * 70)
    print("Status Sistem : AKTIF (Mendengarkan data sensor setiap 6 detik)...")
    print("Tekan Ctrl + C di terminal untuk menghentikan monitoring.\n")

    for siklus, skenario in enumerate(urutan_skenario, start=1):
        sensor = skenario["data"]
        waktu = skenario["waktu"]
        keterangan = skenario["desc"]

        print(f"\n[SIKLUS {siklus}] Pukul {waktu} | Deskripsi: {keterangan}")
        print(f"Data Sensor Masuk -> Suhu: {sensor['suhu']} C | DO: {sensor['do']} mg/L | pH: {sensor['ph']}")

        keputusan = evaluasi_kondisi_tambak(sensor)
        keparahan = keputusan["tingkat_keparahan"]

        if keparahan == "NORMAL":
            print(f"Status Lingkungan : \033[92m{keparahan}\033[0m")
            print(f"Ringkasan Log     : {keputusan['ringkasan']}")
            print("Status Telegram   : Mode hening (tidak ada anomali, tidak mengganggu pengguna).")

        elif keparahan == "WASPADA":
            print(f"Status Lingkungan : \033[93m{keparahan}\033[0m")
            print(f"Ringkasan Log     : {keputusan['ringkasan']}")
            print("Aksi Otonom       :")
            for a in keputusan["Aksi_Otonom"]:
                print(f"  -> {a['status']} ({a['alasan']})")
            print("Status Telegram   : Dicatat di log internal tanpa perlu otorisasi darurat.")

        elif keparahan == "KRITIS":
            print(f"Status Lingkungan : \033[91m{keparahan} (ANOMALI MELEWATI AMBANG BATAS!)\033[0m")
            print(f"Ringkasan Log     : {keputusan['ringkasan']}")

            # 1. Jalankan Aktuator Otonom Langsung
            print("\n>>> MEMICU AKSI OTONOM MESIN TAMBAK:")
            for a in keputusan["Aksi_Otonom"]:
                print(f"  [AKTIF] {a['status']}")

            # 2. Hybrid Gateway: coba cloud dulu, fallback ke edge jika gagal
            cloud_ok, rekomendasi_ai = kirim_ke_langflow(sensor)

            if cloud_ok:
                # --- JALUR CLOUD ONLINE: lanjutkan alur HITL Telegram ---
                hitl = keputusan["Human_in_the_Loop"][0]
                last_id = get_last_update_id()

                # Sertakan rekomendasi Langflow AI jika berhasil di-parse
                blok_ai = (
                    f"\n\n🤖 *Rekomendasi AI (Langflow):*\n_{rekomendasi_ai}_"
                    if rekomendasi_ai else ""
                )

                pesan_alert = (
                    f"🚨 *[PERINGATAN KRITIS TAMBAK]*\n\n"
                    f"⏰ Waktu: {waktu}\n"
                    f"🌡️ Suhu: {sensor['suhu']}°C | DO: {sensor['do']} mg/L | pH: {sensor['ph']}\n\n"
                    f"⚠️ *Kondisi:* {keputusan['ringkasan']}\n\n"
                    f"🛠️ *Sistem Otomatis:* Kincir darurat 100% AKTIF, Feeder DIMATIKAN.\n\n"
                    f"📋 *Usulan Tindakan Kimia:*\n_{hitl['pesan_wa']}_"
                    f"{blok_ai}\n\n"
                    f"👉 Balas *iya* untuk izinkan eksekusi.\n"
                    f"👉 Balas *tidak* untuk batalkan."
                )

                kirim_telegram(pesan_alert)
                print("\n[CLOUD ONLINE] Notifikasi darurat berhasil dikirim ke HP petambak via Telegram!")

                # Tunggu otorisasi dua arah dari Telegram
                izin = dengarkan_konfirmasi_telegram(last_id, timeout_detik=90)

                if izin:
                    print("\n[EKSEKUSI LAPANGAN]: Persetujuan valid diterima! Penebaran dolomit sedang berlangsung.")
                else:
                    print("\n[EKSEKUSI LAPANGAN]: Petambak menolak tindakan kimiawi. Hanya aerasi darurat yang berjalan.")
            # else: edge fallback sudah dijalankan di dalam kirim_ke_langflow()

        print("-" * 70)
        print("Menunggu pembacaan telemetri berikutnya...")
        time.sleep(6)

    print("\n[SELESAI] Simulasi seluruh rangkaian waktu budidaya selesai dijalankan dengan sempurna.")

if __name__ == "__main__":
    jalankan_monitoring_kontinu()
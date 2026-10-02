# Panduan Deployment Produksi Cloud (AbsensiAI)

Panduan lengkap untuk mengunggah (*upload*) dan menjalankan aplikasi **AbsensiAI** ke server produksi (Cloud Hosting) secara publik agar dapat diakses dari internet dengan aman.

---

## 🔒 1. Keamanan & Persiapan Sebelum Upload ke GitHub

File `.gitignore` sudah otomatis disiapkan untuk melindungi file kredensial Anda. **JANGAN PERNAH** meng-upload file `serviceAccountKey.json` ke repository GitHub publik!

### Inisialisasi Git dan Push ke GitHub:

Buka terminal di folder project:
```bash
git init
git add .
git commit -m "feat: initial production-ready AbsensiAI commit"
```

Buat repository baru di [GitHub](https://github.com/new) (bisa *Public* atau *Private*), lalu hubungkan dan push:
```bash
git branch -M main
git remote add origin https://github.com/USERNAME-ANDA/NAMA-REPO-ANDA.git
git push -u origin main
```

---

## 🚀 2. Opsi Deployment Cloud Terpopuler

### Opsi A: Render.com (Sangat Direkomendasikan - Gratis & Otomatis HTTPS)

Render menyediakan tier gratis dan otomatis mengaktifkan sertifikat SSL/HTTPS (wajib untuk akses kamera webcam).

1. Daftar / Masuk ke [Render.com](https://render.com/).
2. Klik tombol **New +** > Pilih **Web Service**.
3. Hubungkan akun GitHub Anda dan pilih repository **AbsensiAI**.
4. Isi konfigurasi berikut:
   * **Name**: `absensi-ai-sekolah` (atau nama pilihan Anda)
   * **Region**: `Singapore` (terdekat dengan Indonesia untuk latensi rendah)
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
5. Masuk ke bagian **Environment Variables** (Variabel Lingkungan):
   * `ENVIRONMENT` = `production`
   * `SECRET_KEY` = *(Klik tombol 'Generate' atau ketik string acak yang panjang)*
   * `BATAS_JAM_MASUK` = `07:15`
   * `FIREBASE_CREDENTIALS_JSON` = **(Buka file `serviceAccountKey.json` di komputer Anda, copy SELURUH isinya dari `{` sampai `}`, lalu paste di sini)**
6. Klik **Create Web Service**.
7. Tunggu build selesai (~2-3 menit). Aplikasi Anda akan langsung aktif dengan alamat HTTPS:
   👉 `https://absensi-ai-sekolah.onrender.com`

---

### Opsi B: Railway.app (1-Click Deployment)

1. Buka [Railway.app](https://railway.app/).
2. Klik **New Project** > **Deploy from GitHub repo**.
3. Pilih repository Anda.
4. Klik **Add Variables**:
   * Tambahkan `ENVIRONMENT` = `production`
   * Tambahkan `SECRET_KEY` = `kunci-rahasia-acak-anda`
   * Tambahkan `FIREBASE_CREDENTIALS_JSON` = *(Isi teks json kredensial Firebase Anda)*
5. Di tab **Settings**, klik **Generate Domain** untuk mendapatkan URL publik HTTPS.

---

### Opsi C: Deployment Docker / VPS (Ubuntu / Debian / Nginx)

Jika Anda menyewa VPS pribadi (DigitalOcean, AWS EC2, Linode, Biznet, dll.):

#### 1. Jalankan Menggunakan Docker:
```bash
# Clone repo
git clone https://github.com/USERNAME-ANDA/NAMA-REPO-ANDA.git
cd NAMA-REPO-ANDA

# Taruh file serviceAccountKey.json di folder project
nano serviceAccountKey.json

# Jalankan dengan Docker Compose
docker compose up -d --build
```

#### 2. Konfigurasi Nginx Reverse Proxy & SSL Gratis (Certbot):
Agar kamera dapat berfungsi di domain publik Anda, wajib memasang SSL:

```nginx
server {
    server_name absensi.sekolahanda.sch.id;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Pasang SSL Let's Encrypt:
```bash
sudo certbot --nginx -d absensi.sekolahanda.sch.id
```

---

## 📷 3. Catatan Penting Mengenai Kamera Web (HTTPS)

> [!IMPORTANT]
> Semua browser modern (Google Chrome, Mozilla Firefox, Microsoft Edge, Safari) membatasi akses webcam (`navigator.mediaDevices.getUserMedia`) **hanya pada domain yang memiliki protokol aman HTTPS** (atau `localhost`).
> 
> Jika Anda mengakses aplikasi menggunakan alamat IP HTTP mentah (misal: `http://103.xxx.xxx.xxx:5000`), peramban akan **menolak izin kamera**. Pastikan aplikasi selalu diakses melalui alamat berawalan `https://`.

---

## 🧪 4. Menguji Health Check di Cloud

Setelah di-deploy, Anda dapat mengecek status server dan koneksi Firebase kapan saja di:
👉 `https://DOMAIN-ANDA/health`

Contoh respons jika sukses:
```json
{
  "status": "healthy",
  "environment": "production",
  "firebase": {
    "connected": true,
    "is_mock": false
  },
  "timestamp": "2026-10-02T15:30:00"
}
```

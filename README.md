# Sistem Absensi Siswa AI Face Recognition & Firebase Firestore

Aplikasi absensi siswa berbasis web yang mengombinasikan **Python Flask**, **AI Face Recognition (OpenCV)**, dan **Firebase Firestore** sebagai database cloud.

---

## 📁 1. Struktur Folder Project

```
AbsensiAI/
├── app.py                      # Server Flask dengan WSGI Production & ProxyFix
├── firebase_config.py          # Koneksi Firebase Firestore Cloud & Fallback
├── requirements.txt            # Dependensi (Flask, Gunicorn, Waitress, OpenCV)
├── serviceAccountKey.json.example # Contoh struktur file kredensial Firebase
├── .env.example                # Template variabel lingkungan produksi
├── .gitignore                  # Perlindungan file rahasia & cache
├── Procfile                    # Skrip start Gunicorn untuk Render / Railway
├── render.yaml                 # Blueprint 1-click deploy Render
├── Dockerfile                  # Konfigurasi container Docker production
├── docker-compose.yml          # Orkestrasi Docker container
├── DEPLOYMENT.md               # Panduan lengkap upload & deploy cloud
├── README.md                   # Dokumentasi umum proyek
│
├── face/                       # Modul AI Pengenalan Wajah
│   ├── detect.py               # Deteksi wajah & validasi 1 wajah
│   └── recognize.py            # Ekstraksi encoding 128-d & pencocokan wajah
│
├── templates/                  # Tampilan Antarmuka Web (HTML)
│   ├── base.html               # Layout induk (Bootstrap 5, FontAwesome)
│   ├── login.html              # Halaman Login Multi-Role (Admin & Siswa)
│   ├── dashboard.html          # Dashboard Siswa & Riwayat Absensi Pribadi
│   ├── attendance.html         # Halaman Kamera Pemindai Absensi Real-Time
│   └── admin.html              # Panel Admin (Data Siswa, Daftar Wajah, Laporan)
│
└── static/                     # Aset Web Frontend
    ├── css/
    │   └── style.css           # Styling custom & animasi laser scan
    └── js/
        └── main.js             # Skrip interaksi client-side
```

> 📖 **Ingin Upload ke Cloud?** Baca panduan lengkapnya di [**DEPLOYMENT.md**](file:///c:/Users/lab3_33/Documents/AbsensiAI/DEPLOYMENT.md).

---

## ⚙️ 2. Persyaratan & Teknologi

* **Backend**: Python 3.10 / 3.11, Flask
* **AI Computer Vision**: OpenCV (`opencv-python`), NumPy, Pillow, Face-Recognition
* **Database**: Firebase Firestore (`firebase-admin`)
* **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5.3, FontAwesome 6, SweetAlert2

---

## 🔑 3. Konfigurasi Firebase Firestore

1. Buka [Firebase Console](https://console.firebase.google.com/).
2. Buat proyek baru atau pilih proyek yang sudah ada.
3. Masuk ke menu **Build > Firestore Database** dan aktifkan Firestore (pilih mode produksi atau mode tes).
4. Buat kunci Service Account:
   * Masuk ke **Project Settings** (ikon gerigi) > **Service accounts**.
   * Klik tombol **Generate new private key** (Hasilkan kunci privat baru).
   * File `.json` akan terunduh ke komputer Anda.
5. Ubah nama file yang diunduh menjadi **`serviceAccountKey.json`** dan letakkan tepat di folder utama project ini (`AbsensiAI/serviceAccountKey.json`).

> **Catatan Kemudahan:**
> Jika file `serviceAccountKey.json` belum dipasang, aplikasi **tetap dapat berjalan langsung** menggunakan *Local Firestore Simulator* (`local_firestore.json`), sehingga Anda dapat langsung mencoba dan mendemokan seluruh fitur tanpa hambatan!

### Struktur Koleksi Firestore:
* `users`: `user_id`, `nama`, `email`, `password`, `role` (`admin`/`siswa`), `student_id`
* `students`: `student_id`, `nama`, `kelas`, `nis`, `face_encoding`
* `attendance`: `attendance_id`, `student_id`, `nama`, `tanggal`, `waktu`, `status`

---

## 🚀 4. Cara Instalasi & Menjalankan

### Langkah 1: Buka Terminal / PowerShell di Folder Project
```powershell
cd c:\Users\lab3_33\Documents\AbsensiAI
```

### Langkah 2: Buat & Aktifkan Virtual Environment (Direkomendasikan)
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Langkah 3: Install Dependensi
```powershell
pip install -r requirements.txt
```

### Langkah 4: Jalankan Server Flask
```powershell
python app.py
```

### Langkah 5: Buka di Browser
Akses URL: **`http://127.0.0.1:5000`**

---

## 👥 5. Akun Demo Bawaan

| Role | Email | Password | Keterangan |
|---|---|---|---|
| **Admin** | `admin@sekolah.sch.id` | `admin` | Akses penuh dashboard, kelola siswa & daftarkan wajah |
| **Siswa 1** | `ahmad@sekolah.sch.id` | `siswa` | Siswa Ahmad Dahlan (XII RPL 1) |
| **Siswa 2** | `siti@sekolah.sch.id` | `siswa` | Siswa Siti Nurhaliza (XII RPL 2) |

---

## 💡 6. Alur Penggunaan Fitur

1. **Pendaftaran Wajah Siswa (Admin)**:
   * Login sebagai Admin (`admin@sekolah.sch.id`).
   * Di tab **Data Siswa**, klik tombol **Daftarkan Wajah** pada siswa yang diinginkan.
   * Kamera akan aktif. Posisikan wajah di dalam kotak pemindai, lalu klik **Ambil & Simpan Wajah AI**.
   * AI akan mengekstrak 128-vektor embedding wajah dan menyimpannya ke Firestore.

2. **Absensi Siswa Menggunakan Kamera**:
   * Buka menu **Absensi Wajah / Scan Absensi** (`/attendance`).
   * Siswa menghadap ke kamera laptop/webcam.
   * Kamera memverifikasi wajah siswa dengan data di Firestore:
     - Jika wajah cocok dan belum absen: Kehadiran otomatis tercatat (**Hadir** jika sebelum 07:15, **Terlambat** jika setelah 07:15).
     - Jika mencoba absen dua kali di hari yang sama: Sistem menolak dan menampilkan peringatan sudah absen.
     - Jika terdeteksi lebih dari satu orang: Sistem meminta hanya satu wajah di depan kamera.

3. **Laporan Kehadiran (Admin)**:
   * Di panel Admin, buka tab **Laporan Absensi Per Tanggal**.
   * Pilih tanggal untuk melihat rekap kehadiran, jam masuk, dan status masing-masing siswa.

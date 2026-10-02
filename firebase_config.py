import os
import json
import logging
from datetime import datetime

import base64

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Jalur kunci Firebase Service Account & Variabel Lingkungan Cloud
FIREBASE_KEY_PATH = os.environ.get("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
FIREBASE_CREDENTIALS_JSON = os.environ.get("FIREBASE_CREDENTIALS_JSON", "").strip()
FIREBASE_CREDENTIALS_BASE64 = os.environ.get("FIREBASE_CREDENTIALS_BASE64", "").strip()
IS_PRODUCTION = os.environ.get("ENVIRONMENT", "").lower() in ["production", "prod"] or os.environ.get("FLASK_ENV", "").lower() == "production"

# Inisialisasi Firebase Admin
db = None
IS_MOCK = False

def _init_firebase():
    global db, IS_MOCK
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        cred = None

        # 1. Prioritas Pertama: Membaca langsung dari Environment Variable JSON (Standar Cloud Hosting)
        if FIREBASE_CREDENTIALS_JSON:
            try:
                cert_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
                cred = credentials.Certificate(cert_dict)
                logger.info("Firebase: Berhasil memuat kredensial dari FIREBASE_CREDENTIALS_JSON")
            except Exception as e:
                logger.error(f"Format JSON pada FIREBASE_CREDENTIALS_JSON tidak valid: {e}")

        # 2. Prioritas Kedua: Membaca dari Environment Variable Base64
        elif FIREBASE_CREDENTIALS_BASE64:
            try:
                decoded_json = base64.b64decode(FIREBASE_CREDENTIALS_BASE64).decode('utf-8')
                cert_dict = json.loads(decoded_json)
                cred = credentials.Certificate(cert_dict)
                logger.info("Firebase: Berhasil memuat kredensial dari FIREBASE_CREDENTIALS_BASE64")
            except Exception as e:
                logger.error(f"Format Base64 pada FIREBASE_CREDENTIALS_BASE64 tidak valid: {e}")

        # 3. Prioritas Ketiga: Membaca dari File fisik (misal serviceAccountKey.json)
        elif os.path.exists(FIREBASE_KEY_PATH):
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            logger.info(f"Firebase: Berhasil memuat kredensial dari file '{FIREBASE_KEY_PATH}'")

        # Inisialisasi Firebase Client jika kredensial valid
        if cred:
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            db = firestore.client()
            logger.info("Firebase Firestore Cloud: Terhubung & Siap Digunakan.")
            IS_MOCK = False
            return
        else:
            if IS_PRODUCTION:
                error_msg = (
                    "FATAL ERROR: Aplikasi berjalan di lingkungan PRODUCTION tetapi kredensial Firebase tidak ditemukan! "
                    "Harap set Environment Variable 'FIREBASE_CREDENTIALS_JSON' di dashboard hosting Anda."
                )
                logger.critical(error_msg)
            else:
                logger.warning(
                    f"Kredensial Firebase tidak ditemukan (file '{FIREBASE_KEY_PATH}' atau env var 'FIREBASE_CREDENTIALS_JSON'). "
                    "Berjalan dalam mode Simulasi Lokal (local_firestore.json) untuk kemudahan pengujian."
                )
            IS_MOCK = True

    except Exception as e:
        logger.error(f"Gagal inisialisasi Firebase: {e}. Mengalihkan ke mode lokal.")
        IS_MOCK = True

_init_firebase()


# =====================================================================
# Simulator Lokal untuk pengujian instan jika serviceAccountKey.json belum ada
# =====================================================================
MOCK_FILE = "local_firestore.json"

def _load_mock_data():
    if os.path.exists(MOCK_FILE):
        try:
            with open(MOCK_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    
    # Data awal default
    default_data = {
        "users": {
            "admin_1": {
                "user_id": "admin_1",
                "nama": "Administrator",
                "email": "admin@sekolah.sch.id",
                "password": "admin", # Demo password
                "role": "admin"
            },
            "siswa_1": {
                "user_id": "siswa_1",
                "nama": "Ahmad Dahlan",
                "email": "ahmad@sekolah.sch.id",
                "password": "siswa", # Demo password
                "role": "siswa",
                "student_id": "std_1"
            },
            "siswa_2": {
                "user_id": "siswa_2",
                "nama": "Siti Nurhaliza",
                "email": "siti@sekolah.sch.id",
                "password": "siswa", # Demo password
                "role": "siswa",
                "student_id": "std_2"
            }
        },
        "students": {
            "std_1": {
                "student_id": "std_1",
                "nama": "Ahmad Dahlan",
                "kelas": "XII RPL 1",
                "nis": "1001",
                "face_encoding": None
            },
            "std_2": {
                "student_id": "std_2",
                "nama": "Siti Nurhaliza",
                "kelas": "XII RPL 2",
                "nis": "1002",
                "face_encoding": None
            }
        },
        "attendance": {}
    }
    _save_mock_data(default_data)
    return default_data

def _save_mock_data(data):
    with open(MOCK_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


# =====================================================================
# Fungsi Abstraksi CRUD untuk Firestore & Local Fallback
# =====================================================================

def get_db_status():
    return {
        "is_mock": IS_MOCK,
        "key_path": FIREBASE_KEY_PATH,
        "connected": db is not None and not IS_MOCK
    }

def get_user_by_email(email):
    """Mencari data user berdasarkan email"""
    if not IS_MOCK and db:
        users_ref = db.collection('users')
        docs = users_ref.where('email', '==', email.strip().lower()).limit(1).stream()
        for doc in docs:
            d = doc.to_dict()
            d['user_id'] = doc.id
            return d
        return None
    else:
        data = _load_mock_data()
        for uid, user in data.get('users', {}).items():
            if user.get('email', '').strip().lower() == email.strip().lower():
                user['user_id'] = uid
                return user
        return None

def create_user(user_id, nama, email, password, role="siswa", student_id=None):
    """Menambahkan user baru"""
    user_data = {
        "nama": nama,
        "email": email.strip().lower(),
        "password": password,
        "role": role
    }
    if student_id:
        user_data["student_id"] = student_id

    if not IS_MOCK and db:
        db.collection('users').document(user_id).set(user_data)
    else:
        data = _load_mock_data()
        user_data['user_id'] = user_id
        data['users'][user_id] = user_data
        _save_mock_data(data)
    return user_data

def get_all_students():
    """Mengambil semua daftar siswa"""
    students = []
    if not IS_MOCK and db:
        docs = db.collection('students').stream()
        for doc in docs:
            d = doc.to_dict()
            d['student_id'] = doc.id
            students.append(d)
    else:
        data = _load_mock_data()
        for sid, s in data.get('students', {}).items():
            s['student_id'] = sid
            students.append(s)
    return students

def get_student(student_id):
    """Mengambil data siswa tertentu berdasarkan student_id"""
    if not IS_MOCK and db:
        doc = db.collection('students').document(student_id).get()
        if doc.exists:
            d = doc.to_dict()
            d['student_id'] = doc.id
            return d
        return None
    else:
        data = _load_mock_data()
        s = data.get('students', {}).get(student_id)
        if s:
            s['student_id'] = student_id
        return s

def add_student(student_id, nama, kelas, nis, face_encoding=None):
    """Menambahkan siswa baru ke database"""
    student_data = {
        "nama": nama,
        "kelas": kelas,
        "nis": str(nis),
        "face_encoding": face_encoding
    }
    if not IS_MOCK and db:
        db.collection('students').document(student_id).set(student_data)
    else:
        data = _load_mock_data()
        student_data['student_id'] = student_id
        data['students'][student_id] = student_data
        _save_mock_data(data)
    return student_data

def update_student_face(student_id, face_encoding):
    """Memperbarui face encoding siswa"""
    if not IS_MOCK and db:
        db.collection('students').document(student_id).update({
            "face_encoding": face_encoding
        })
    else:
        data = _load_mock_data()
        if student_id in data.get('students', {}):
            data['students'][student_id]['face_encoding'] = face_encoding
            _save_mock_data(data)

def record_attendance(student_id, nama, tanggal, waktu, status):
    """
    Menyimpan data absensi ke Firestore collection 'attendance'
    Mencegah absensi ganda pada tanggal yang sama.
    """
    # Cek apakah sudah absen pada tanggal ini
    existing = check_attendance_today(student_id, tanggal)
    if existing:
        return False, f"Siswa {nama} sudah melakukan absensi pada {tanggal} pukul {existing.get('waktu')} (Status: {existing.get('status')})."

    attendance_id = f"{student_id}_{tanggal.replace('-', '')}"
    att_data = {
        "attendance_id": attendance_id,
        "student_id": student_id,
        "nama": nama,
        "tanggal": tanggal,
        "waktu": waktu,
        "status": status,
        "created_at": datetime.now().isoformat()
    }

    if not IS_MOCK and db:
        db.collection('attendance').document(attendance_id).set(att_data)
    else:
        data = _load_mock_data()
        data['attendance'][attendance_id] = att_data
        _save_mock_data(data)

    return True, att_data

def check_attendance_today(student_id, tanggal):
    """Cek apakah siswa sudah absen pada tanggal tertentu"""
    if not IS_MOCK and db:
        docs = db.collection('attendance') \
                 .where('student_id', '==', student_id) \
                 .where('tanggal', '==', tanggal) \
                 .limit(1).stream()
        for doc in docs:
            return doc.to_dict()
        return None
    else:
        data = _load_mock_data()
        for att_id, att in data.get('attendance', {}).items():
            if att.get('student_id') == student_id and att.get('tanggal') == tanggal:
                return att
        return None

def get_attendance_history(student_id=None, tanggal=None):
    """
    Mengambil riwayat absensi.
    Dapat difilter berdasarkan student_id (untuk role siswa) atau tanggal (untuk laporan admin).
    """
    records = []
    if not IS_MOCK and db:
        query = db.collection('attendance')
        if student_id:
            query = query.where('student_id', '==', student_id)
        if tanggal:
            query = query.where('tanggal', '==', tanggal)
        
        docs = query.stream()
        for doc in docs:
            d = doc.to_dict()
            records.append(d)
    else:
        data = _load_mock_data()
        for att_id, att in data.get('attendance', {}).items():
            if student_id and att.get('student_id') != student_id:
                continue
            if tanggal and att.get('tanggal') != tanggal:
                continue
            records.append(att)
    
    # Urutkan berdasarkan tanggal & waktu menurun (terbaru di atas)
    records.sort(key=lambda x: (x.get('tanggal', ''), x.get('waktu', '')), reverse=True)
    return records

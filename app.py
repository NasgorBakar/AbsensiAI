import os
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix

# Import modul lokal
import firebase_config as fb
from face.detect import base64_to_image, detect_faces
from face.recognize import extract_face_encoding, find_best_match, DEFAULT_THRESHOLD

app = Flask(__name__)

# Konfigurasi Keamanan Production
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# Dukungan Reverse Proxy (Nginx, Render, Railway, Cloud Run, Docker)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Waktu batas jam masuk sekolah (format HH:MM, dapat diset via environment variable)
BATAS_JAM_MASUK = os.environ.get("BATAS_JAM_MASUK", "07:15")


# =====================================================================
# Middleware / Decorator Auth
# =====================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user'].get('role') != 'admin':
            flash("Akses ditolak. Halaman khusus Administrator.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# =====================================================================
# Route Halaman Web
# =====================================================================

@app.route('/')
def index():
    if 'user' in session:
        if session['user'].get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = fb.get_user_by_email(email)
        if user and user.get('password') == password:
            session['user'] = {
                'user_id': user.get('user_id'),
                'nama': user.get('nama'),
                'email': user.get('email'),
                'role': user.get('role'),
                'student_id': user.get('student_id')
            }
            flash(f"Selamat datang, {user.get('nama')}!", "success")
            if user.get('role') == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('student_dashboard'))
        else:
            flash("Email atau password tidak sesuai.", "danger")

    db_status = fb.get_db_status()
    return render_template('login.html', db_status=db_status)


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Anda berhasil logout.", "info")
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def student_dashboard():
    user = session['user']
    if user.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))

    today_str = datetime.now().strftime("%Y-%m-%d")
    student_id = user.get('student_id')
    
    # Ambil riwayat absensi siswa
    history = fb.get_attendance_history(student_id=student_id)
    
    # Status absensi hari ini
    today_attendance = fb.check_attendance_today(student_id, today_str) if student_id else None

    # Ambil info student
    student_info = fb.get_student(student_id) if student_id else None

    return render_template('dashboard.html', 
                           user=user, 
                           student=student_info,
                           today_attendance=today_attendance,
                           history=history,
                           today_date=today_str)


@app.route('/attendance')
@login_required
def attendance():
    user = session['user']
    today_str = datetime.now().strftime("%Y-%m-%d")
    student_id = user.get('student_id')
    
    already_attended = False
    today_att = None
    if student_id:
        today_att = fb.check_attendance_today(student_id, today_str)
        if today_att:
            already_attended = True

    return render_template('attendance.html', 
                           user=user, 
                           already_attended=already_attended,
                           today_att=today_att,
                           today_date=today_str)


@app.route('/admin')
@admin_required
def admin_dashboard():
    user = session['user']
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Ambil semua siswa
    all_students = fb.get_all_students()
    
    # Ambil absensi hari ini
    today_records = fb.get_attendance_history(tanggal=today_str)
    
    # Hitung statistik
    total_students = len(all_students)
    present_count = len(today_records)
    late_count = sum(1 for r in today_records if r.get('status') == 'Terlambat')
    on_time_count = sum(1 for r in today_records if r.get('status') == 'Hadir')
    absent_count = max(0, total_students - present_count)

    db_status = fb.get_db_status()

    return render_template('admin.html',
                           user=user,
                           students=all_students,
                           today_records=today_records,
                           total_students=total_students,
                           present_count=present_count,
                           late_count=late_count,
                           on_time_count=on_time_count,
                           absent_count=absent_count,
                           today_date=today_str,
                           db_status=db_status)


# =====================================================================
# API Endpoints untuk Face Recognition & Absensi
# =====================================================================

@app.route('/api/attendance/scan', methods=['POST'])
@login_required
def api_scan_attendance():
    """
    Endpoint untuk absensi kamera:
    1. Menerima gambar kamera base64.
    2. Deteksi wajah (validasi hanya 1 wajah).
    3. Ekstrak encoding wajah.
    4. Cocokkan dengan data siswa di Firestore.
    5. Jika cocok:
       - Cek apakah sudah absen hari ini (cegah 2x).
       - Tentukan status (Hadir/Terlambat).
       - Simpan ke Firestore collection 'attendance'.
    """
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"success": False, "message": "Data gambar kamera tidak ditemukan."}), 400

    try:
        # 1. Konversi base64 ke format gambar
        bgr_image, rgb_image = base64_to_image(data['image'])

        # 2. Deteksi wajah (validasi tepat 1 wajah)
        valid, face_locations, msg = detect_faces(rgb_image)
        if not valid:
            return jsonify({"success": False, "message": msg}), 400

        # 3. Ekstrak face encoding
        candidate_encoding, enc_msg = extract_face_encoding(rgb_image, face_locations)
        if not candidate_encoding:
            return jsonify({"success": False, "message": enc_msg}), 400

        # 4. Ambil semua siswa terdaftar yang memiliki face_encoding
        students = fb.get_all_students()
        students_with_face = [s for s in students if s.get('face_encoding') is not None]

        if not students_with_face:
            return jsonify({
                "success": False, 
                "message": "Belum ada wajah siswa yang didaftarkan di sistem. Hubungi Admin."
            }), 404

        # 5. Cocokkan wajah dengan threshold
        best_match, distance = find_best_match(candidate_encoding, students_with_face, threshold=DEFAULT_THRESHOLD)

        if not best_match:
            return jsonify({
                "success": False,
                "message": f"Wajah tidak cocok dengan data siswa manapun (Skor jarak: {distance:.2f}, ambang batas: {DEFAULT_THRESHOLD})."
            }), 404

        # Siswa yang sedang login (jika siswa) harus cocok dengan wajah yang dipindai
        current_user = session['user']
        if current_user.get('role') == 'siswa' and current_user.get('student_id'):
            if current_user.get('student_id') != best_match.get('student_id'):
                return jsonify({
                    "success": False,
                    "message": f"Wajah terdeteksi milik {best_match.get('nama')}, tetapi Anda login sebagai {current_user.get('nama')}. Absensi ditolak!"
                }), 403

        # 6. Cek waktu dan tentukan status Hadir/Terlambat
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        hour_min_str = now.strftime("%H:%M")

        status = "Terlambat" if hour_min_str > BATAS_JAM_MASUK else "Hadir"

        # 7. Simpan absensi ke Firebase (mencegah absen dua kali)
        success, res = fb.record_attendance(
            student_id=best_match.get('student_id'),
            nama=best_match.get('nama'),
            tanggal=today_str,
            waktu=time_str,
            status=status
        )

        if not success:
            return jsonify({"success": False, "message": res}), 409

        return jsonify({
            "success": True,
            "message": f"Absensi berhasil dicatat! Halo, {best_match.get('nama')}.",
            "data": {
                "nama": best_match.get('nama'),
                "student_id": best_match.get('student_id'),
                "kelas": best_match.get('kelas'),
                "tanggal": today_str,
                "waktu": time_str,
                "status": status,
                "similarity_distance": round(distance, 3)
            }
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Terjadi kesalahan pada sistem: {str(e)}"}), 500


@app.route('/api/face/register', methods=['POST'])
@admin_required
def api_register_face():
    """
    Endpoint untuk Admin mendaftarkan wajah siswa:
    1. Menerima student_id dan gambar kamera base64.
    2. Deteksi wajah (tepat 1 wajah).
    3. Buat face encoding.
    4. Simpan ke Firestore collection 'students'.
    """
    data = request.get_json()
    if not data or 'image' not in data or 'student_id' not in data:
        return jsonify({"success": False, "message": "Parameter tidak lengkap."}), 400

    student_id = data['student_id']
    student = fb.get_student(student_id)
    if not student:
        return jsonify({"success": False, "message": "Data siswa tidak ditemukan."}), 404

    try:
        bgr_image, rgb_image = base64_to_image(data['image'])
        valid, face_locations, msg = detect_faces(rgb_image)
        if not valid:
            return jsonify({"success": False, "message": msg}), 400

        encoding, enc_msg = extract_face_encoding(rgb_image, face_locations)
        if not encoding:
            return jsonify({"success": False, "message": enc_msg}), 400

        # Simpan ke Firestore
        fb.update_student_face(student_id, encoding)

        return jsonify({
            "success": True,
            "message": f"Wajah siswa {student.get('nama')} berhasil didaftarkan!",
            "student_id": student_id
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Gagal mendaftarkan wajah: {str(e)}"}), 500


@app.route('/api/students/add', methods=['POST'])
@admin_required
def api_add_student():
    """Menambahkan data siswa baru dan akun login siswa"""
    nama = request.form.get('nama', '').strip()
    kelas = request.form.get('kelas', '').strip()
    nis = request.form.get('nis', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', 'siswa123').strip()

    if not nama or not kelas or not nis or not email:
        flash("Semua field wajib diisi!", "danger")
        return redirect(url_for('admin_dashboard'))

    student_id = f"std_{nis}"
    user_id = f"user_{nis}"

    # Simpan data student
    fb.add_student(student_id, nama, kelas, nis)
    
    # Buat akun user siswa
    fb.create_user(user_id, nama, email, password, role="siswa", student_id=student_id)

    flash(f"Siswa {nama} ({nis}) berhasil ditambahkan!", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/api/reports/filter', methods=['GET'])
@admin_required
def api_reports_filter():
    """Mengambil laporan absensi berdasarkan tanggal untuk admin"""
    tanggal = request.args.get('tanggal')
    records = fb.get_attendance_history(tanggal=tanggal)
    return jsonify({"success": True, "records": records})


@app.route('/health')
def health_check():
    """Health check endpoint untuk cloud monitoring / platform probes"""
    status = fb.get_db_status()
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "firebase": {
            "connected": status.get("connected", False),
            "is_mock": status.get("is_mock", True)
        }
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    is_debug = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1']
    is_prod = os.environ.get('ENVIRONMENT', '').lower() in ['production', 'prod']

    if is_prod:
        # Jalankan menggunakan production WSGI server Waitress jika tersedia
        try:
            import waitress
            print(f" * Server Absensi AI berjalan (PRODUCTION - Waitress) di port {port}")
            waitress.serve(app, host='0.0.0.0', port=port)
        except ImportError:
            print(f" * Server Absensi AI berjalan di http://0.0.0.0:{port} (Debug: False)")
            app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print(f" * Server Absensi AI berjalan di http://127.0.0.1:{port} (Debug: {is_debug})")
        app.run(host='0.0.0.0', port=port, debug=is_debug)

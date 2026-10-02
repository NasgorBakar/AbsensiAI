import cv2
import numpy as np

try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False

from face.detect import detect_faces

# Default threshold toleransi kecocokan wajah (jarak euclid)
DEFAULT_THRESHOLD = 0.5

def extract_face_encoding(rgb_image, face_locations=None):
    """
    Mengekstrak embedding/encoding wajah 128-dimensi dari gambar.
    Mengembalikan list of float (dapat disimpan di Firestore) atau None jika gagal.
    """
    if face_locations is None:
        valid, face_locations, msg = detect_faces(rgb_image)
        if not valid:
            return None, msg

    if not face_locations:
        return None, "Wajah tidak ditemukan untuk di-encode."

    if FACE_REC_AVAILABLE:
        encodings = face_recognition.face_encodings(rgb_image, known_face_locations=face_locations)
        if len(encodings) > 0:
            return encodings[0].tolist(), "Berhasil mengekstrak face encoding."
        return None, "Gagal membuat face encoding."
    else:
        # Engine OpenCV HOG Descriptor (Histogram of Oriented Gradients)
        # Menghasilkan vektor fitur 128-dimensi yang tahan terhadap variasi pencahayaan
        top, right, bottom, left = face_locations[0]
        h, w, _ = rgb_image.shape
        top = max(0, top)
        left = max(0, left)
        bottom = min(h, bottom)
        right = min(w, right)
        
        face_crop = rgb_image[top:bottom, left:right]
        if face_crop.size == 0:
            return None, "Ukuran crop wajah tidak valid."

        gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY)
        # Histogram Equalization untuk normalisasi pencahayaan
        equalized = cv2.equalizeHist(gray_crop)
        resized = cv2.resize(equalized, (64, 64))

        # Ekstraksi HOG
        hog = cv2.HOGDescriptor((64, 64), (16, 16), (8, 8), (8, 8), 9)
        feats = hog.compute(resized).flatten()

        # Pooling ke 128 dimensi
        chunk_size = len(feats) // 128
        vec = [float(np.mean(feats[i * chunk_size:(i + 1) * chunk_size])) for i in range(128)]
        vec = np.array(vec, dtype=np.float32)

        # Normalisasi L2 Unit Vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist(), "Berhasil mengekstrak face encoding (OpenCV HOG-128)."

def calculate_distance(encoding1, encoding2):
    """
    Menghitung jarak Euclidean antara dua vektor encoding wajah.
    Nilai lebih kecil berarti lebih mirip / cocok.
    """
    vec1 = np.array(encoding1, dtype=np.float64)
    vec2 = np.array(encoding2, dtype=np.float64)
    
    # Jika ukuran dimensi berbeda karena perubahan engine, sesuaikan
    min_len = min(len(vec1), len(vec2))
    vec1 = vec1[:min_len]
    vec2 = vec2[:min_len]

    return float(np.linalg.norm(vec1 - vec2))

def find_best_match(candidate_encoding, registered_students, threshold=DEFAULT_THRESHOLD):
    """
    Mencari siswa terdaftar yang paling cocok dengan candidate_encoding.
    
    registered_students: list of dict atau dict student_id -> {
       'student_id': str,
       'nama': str,
       'face_encoding': list
    }
    
    Mengembalikan:
      best_match (dict atau None): data siswa jika jarak <= threshold
      best_distance (float): nilai jarak terkecil
    """
    if not candidate_encoding or not registered_students:
        return None, 1.0

    best_match = None
    best_distance = 1.0

    for student in registered_students:
        stored_encoding = student.get('face_encoding')
        if not stored_encoding:
            continue
        
        dist = calculate_distance(candidate_encoding, stored_encoding)
        if dist < best_distance:
            best_distance = dist
            if dist <= threshold:
                best_match = student

    return best_match, best_distance

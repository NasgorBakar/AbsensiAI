import cv2
import numpy as np
import base64
import io
from PIL import Image

# Coba import face_recognition jika terinstall
try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False

face_cascade = None
try:
    if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'):
        haar_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(haar_cascade_path)
except Exception:
    pass

def base64_to_image(base64_string):
    """
    Mengonversi string base64 (dari kamera web) menjadi format gambar OpenCV (BGR) dan RGB
    """
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    
    img_data = base64.b64decode(base64_string)
    pil_image = Image.open(io.BytesIO(img_data)).convert('RGB')
    rgb_image = np.array(pil_image)
    bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    return bgr_image, rgb_image

def detect_faces(rgb_image):
    """
    Mendeteksi wajah pada gambar.
    Mengembalikan:
      valid (bool): True jika deteksi valid
      faces (list): daftar bounding boxes [(top, right, bottom, left), ...]
      message (str): pesan status deteksi
    """
    if FACE_REC_AVAILABLE:
        # Gunakan face_recognition HOG detector
        face_locations = face_recognition.face_locations(rgb_image)
    else:
        # Gunakan OpenCV Haar Cascade
        gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
        detected = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(60, 60)
        )
        # Konversi (x, y, w, h) ke format (top, right, bottom, left)
        face_locations = []
        for (x, y, w, h) in detected:
            top = y
            right = x + w
            bottom = y + h
            left = x
            face_locations.append((top, right, bottom, left))

    count = len(face_locations)

    if count == 0:
        return False, [], "Wajah tidak terdeteksi! Pastikan wajah Anda terlihat jelas di depan kamera."
    elif count > 1:
        return False, face_locations, f"Terdeteksi {count} wajah! Pastikan hanya 1 siswa di depan kamera."
    
    return True, face_locations, "Wajah berhasil terdeteksi."

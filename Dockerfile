# Menggunakan base image Python 3.11 slim resmi
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    ENVIRONMENT=production

# Install dependensi sistem yang dibutuhkan untuk pemrosesan citra
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Direktori kerja
WORKDIR /app

# Copy requirements dan install dependensi Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code ke dalam container
COPY . .

# Ekspose port
EXPOSE 5000

# Perintah menjalankan server production Gunicorn
CMD exec gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120

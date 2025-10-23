# Dockerfile

# AŞAMA 1: Yapı Aşaması (Kütüphaneleri Kurmak ve Optimize Etmek)
FROM python:3.11-alpine AS builder

# KRİTİK GÜNCELLEME: scikit-learn, numpy ve psycopg2 gibi kütüphaneleri derlemek için gerekli sistem paketlerini kur.
# build-base: GCC, G++ ve make içerir (C/C++ derleyicileri)
# gfortran: Scipy ve Numpy için gereklidir
# libpq: Psycopg2 için
RUN apk add --no-cache \
    build-base \
    gfortran \
    libpq \
    musl-dev

# Çalışma dizinini ayarla
WORKDIR /app

# Gerekli paketleri kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# AŞAMA 2: Çalıştırma Aşaması (Son Uygulama Görüntüsü)
# Yeni, minimalist bir temel görüntü kullan.
FROM python:3.11-alpine

# Gerekli runtime kütüphanelerini kur (psycopg2'nin çalışması için)
RUN apk add --no-cache libpq libgomp libstdc++
# Çalışma dizinini ayarla
WORKDIR /app

# Yapı aşamasından optimize edilmiş Python paketlerini kopyala (Kütüphaneler)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# KRİTİK EKLENTİ: Gunicorn gibi çalıştırılabilir dosyaları kopyala
# Bu, CMD komutunun 'gunicorn'u bulmasını sağlar.
COPY --from=builder /usr/local/bin /usr/local/bin

# Uygulama kodunu kopyala
COPY . .

# Uygulamanın çalışacağı portu belirt (Sadece bilgilendirme)
EXPOSE 8080

# Gunicorn kütüphanesini kullanarak uygulamayı başlat
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
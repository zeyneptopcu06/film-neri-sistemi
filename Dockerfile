# ----------------------
# AŞAMA 1: Builder
# ----------------------
FROM python:3.11-alpine AS builder

# UTF-8 ve locale ayarları
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Gerekli paketler
RUN apk add --no-cache \
    build-base \
    gfortran \
    libpq \
    musl-dev \
    gettext \
    icu-data-full

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------
# AŞAMA 2: Runtime
# ----------------------
FROM python:3.11-alpine

# Gerekli runtime paketleri
RUN apk add --no-cache libpq libgomp libstdc++

# Locale ayarları
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

WORKDIR /app

# Builder'dan paketleri kopyala
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Uygulama dosyalarını kopyala
COPY . .

EXPOSE 5000

# Render veya Docker için PORT değişkenini kullan
CMD ["sh", "-c", "gunicorn --workers 1 --bind 0.0.0.0:${PORT:-5000} app:app --timeout 300"]

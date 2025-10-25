FROM python:3.11-alpine AS builder

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN apk add --no-cache \
    build-base \
    gfortran \
    libpq \
    musl-dev

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# AŞAMA 2
FROM python:3.11-alpine

RUN apk add --no-cache libpq libgomp libstdc++

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

EXPOSE 5000

# Render için PORT değişkenini kullan
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} app:app --timeout 300"]
# simulasyon_begeni.py

import psycopg2
from psycopg2 import sql
import random
import names 
import datetime
import os
from werkzeug.security import generate_password_hash  # ✅ werkzeug hashleme eklendi

# --- AYARLAR ---
EKLEME_SAYISI = 10         # Her kullanıcı için eklenecek film sayısı
SIMULE_KULLANICI_SAYISI = 50 # Veritabanına kaç yeni simüle kullanıcı eklenecek
SABIT_SIFRE = "Sifre123"   # TÜM SİMÜLE KULLANICILAR İÇİN SABİT ŞİFRE (Hashlenmemiş)

def connect_db():
    """Veritabanı bağlantısını kurar ve autocommit modunu açar."""
    try:
        database_url = os.environ.get("DATABASE_URL")
        
        if database_url:
            conn = psycopg2.connect(database_url)
            print("Veritabanına başarıyla bağlandı (DATABASE_URL kullanıldı).")
        else:
            DB_HOST = os.environ.get("DB_HOST", "db") 
            DB_NAME = os.environ.get("DB_NAME", "film_onerileri")
            DB_USER = os.environ.get("DB_USER", "postgres")
            DB_PASSWORD = os.environ.get("DB_PASSWORD", "1234")
            
            conn = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
            )
            print(f"Veritabanına başarıyla bağlandı (Ayrı değişkenler kullanıldı: Host={DB_HOST}).")

        conn.autocommit = True
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(f"HATA: Veritabanı bağlantısı kurulamadı: {e}")
        return None, None


# --- 1. KULLANICI EKLEME FONKSİYONU (TABLO: kullanicilar) ---
def add_simulated_users(cursor, count):
    """Veritabanına rastgele kullanıcılar ekler (Gmail adresleri, hashlenmiş sabit şifre)."""
    print(f"\n--- {count} Adet Simüle Kullanıcı Ekleniyor ---")
    print(f"📧 E-posta formatı: @gmail.com")
    print(f"🔑 Tüm kullanıcıların giriş şifresi: '{SABIT_SIFRE}' (hashlenmiş olarak kaydedilir)")

    # ✅ Şifre hashleme (Flask ile uyumlu)
    hashed_password = generate_password_hash(SABIT_SIFRE)

    # Mevcut kullanıcı adlarını ve e-postalarını çekeriz
    existing_usernames = set()
    existing_emails = set()
    try:
        cursor.execute("SELECT username, email FROM kullanicilar;") 
        for row in cursor.fetchall():
            existing_usernames.add(row[0])
            existing_emails.add(row[1])
    except:
        pass

    batch_insert_values = []
    eklenen_sayi = 0
    current_time = datetime.datetime.now()
    
    while eklenen_sayi < count:
        first_name = names.get_first_name().lower()
        last_name = names.get_last_name().lower()
        username = f"{first_name}_{last_name}_{random.randint(100, 999)}"
        email = f"{first_name}.{last_name}{random.randint(100, 999)}@gmail.com"
        
        # Kullanıcı adı ve e-posta benzersiz ise ekle
        if username not in existing_usernames and email not in existing_emails:
            batch_insert_values.append((email, hashed_password, current_time, username))
            existing_usernames.add(username)
            existing_emails.add(email)
            eklenen_sayi += 1

    if batch_insert_values:
        # Her bir kaydı tek tek ekle (ON CONFLICT ile)
        insert_query = """
            INSERT INTO kullanicilar (email, sifre, created_at, username) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (email) DO NOTHING;
        """
        
        eklenen = 0
        for values in batch_insert_values:
            cursor.execute(insert_query, values)
            eklenen += 1
        
        print(f"✅ {eklenen} adet yeni simüle kullanıcı eklendi.")
        print(f"   Şifreler veritabanına hashlenmiş (werkzeug) olarak kaydedildi.")


# --- 2. BEĞENİ SİMÜLASYON FONKSİYONU (TABLO: favoriler) ---
def add_random_favorites(cursor, films_per_user):
    """Her kullanıcıya rastgele beğeni ekler (favoriler tablosuna)."""

    print(f"\n--- Rastgele Beğeni Ekleme Başladı (Her kullanıcı için {films_per_user} film) ---")

    # 1. Tüm Kullanıcı ID'lerini Çek
    cursor.execute("SELECT id FROM kullanicilar;") 
    user_ids = [row[0] for row in cursor.fetchall()]
    if not user_ids:
        print("UYARI: Hiç kullanıcı bulunamadı.")
        return

    # 2. Tüm Film ID'lerini Çek
    cursor.execute("SELECT film_id FROM filmler WHERE fragman_url IS NOT NULL;") 
    film_ids = [row[0] for row in cursor.fetchall()]
    if len(film_ids) < films_per_user:
        print(f"UYARI: Yeterli ({films_per_user}) film bulunamadı. Eklenen film sayısı: {len(film_ids)}")
        return

    batch_insert_values = []

    for user_id in user_ids:
        # Mevcut beğenilen filmleri kontrol et
        cursor.execute("SELECT film_id FROM favoriler WHERE kullanici_id = %s;", (user_id,))
        mevcut_begeni_ids = {row[0] for row in cursor.fetchall()}

        secilebilir_filmler = list(set(film_ids) - mevcut_begeni_ids)
        secim_sayisi = min(films_per_user, len(secilebilir_filmler))

        if secim_sayisi > 0:
            rastgele_film_ids = random.sample(secilebilir_filmler, secim_sayisi)

            for film_id in rastgele_film_ids:
                batch_insert_values.append((user_id, film_id))

    # 3. Toplu Ekleme
    if batch_insert_values:
        insert_query = """
            INSERT INTO favoriler (kullanici_id, film_id) 
            VALUES (%s, %s) 
            ON CONFLICT (kullanici_id, film_id) DO NOTHING;
        """
        
        eklenen = 0
        for values in batch_insert_values:
            cursor.execute(insert_query, values)
            eklenen += 1
        
        print(f"✅ Toplam {eklenen} adet rastgele beğeni eklendi.")
    else:
        print("Yeni beğeni eklenmedi.")


def main_simulasyon():
    conn, cursor = connect_db()
    if not conn:
        return
        
    try:
        # A) KULLANICILARI EKLE
        add_simulated_users(cursor, SIMULE_KULLANICI_SAYISI)
        
        # B) RASTGELE BEĞENİLERİ EKLE
        add_random_favorites(cursor, EKLEME_SAYISI)
        
        print("\n" + "="*60)
        print("✅ SİMÜLASYON TAMAMLANDI!")
        print("="*60)
        print(f"📧 E-posta formatı: [isim].[soyisim][sayı]@gmail.com")
        print(f"🔑 Giriş Şifresi: {SABIT_SIFRE}")
        print(f"👥 Toplam Kullanıcı: {SIMULE_KULLANICI_SAYISI}")
        print(f"🎬 Her Kullanıcı İçin Film: {EKLEME_SAYISI}")
        print("="*60)
        
    except psycopg2.Error as e:
        print(f"\nVERİTABANI HATASI (PostgreSQL): {e}")
        print("Lütfen 'kullanicilar' ve 'favoriler' tablolarının mevcut ve doğru kurulduğundan emin olun.")
    except Exception as e:
        print(f"\nGENEL HATA: {e}")
        
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("\nVeritabanı bağlantısı kapatıldı.")


if __name__ == "__main__":
    main_simulasyon()

# simulasyon_begeni.py

import psycopg2
from psycopg2 import sql
import random
import names 
import string
import datetime
import os # <-- BU SATIRI EKLEYİN!


# --- AYARLAR ---
EKLEME_SAYISI = 10         # Her kullanıcı için eklenecek film sayısı
SIMULE_KULLANICI_SAYISI = 50 # Veritabanına kaç yeni simüle kullanıcı eklenecek

def connect_db():
    """Veritabanı bağlantısını kurar ve autocommit modunu açar."""
    try:
        database_url = os.environ.get("DATABASE_URL")
        
        if database_url:
            # 1. Yöntem: Tek DATABASE_URL kullan
            conn = psycopg2.connect(database_url)
            print("Veritabanına başarıyla bağlandı (DATABASE_URL kullanıldı).")
        else:
            # 2. Yöntem: Ayrı ayrı değişkenleri kullan (fallback)
            # Eğer ortam değişkenleri ayarlanmamışsa varsayılan değerleri kullanır
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
        print("Veritabanına başarıyla bağlandı.")
        return conn, cursor
    except Exception as e:
        print(f"HATA: Veritabanı bağlantısı kurulamadı: {e}")
        return None, None

def generate_random_password(length=10):
    """Basit rastgele şifre üretir."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))


# --- 1. KULLANICI EKLEME FONKSİYONU (TABLO: kullanicilar) ---
def add_simulated_users(cursor, count):
    """Veritabanına rastgele kullanıcılar ekler."""
    print(f"\n--- {count} Adet Simüle Kullanıcı Ekleniyor ---")
    
    # Mevcut kullanıcı adlarını ve e-postalarını çekeriz (ÇAKışmayı önlemek için)
    existing_usernames = set()
    existing_emails = set()
    try:
        cursor.execute("SELECT username, email FROM kullanicilar;") 
        for row in cursor.fetchall():
            existing_usernames.add(row[0])
            existing_emails.add(row[1])
    except:
        # Tablo yoksa veya hata varsa ana hata yönetimine bırakılır
        pass

    batch_insert_values = []
    eklenen_sayi = 0
    current_time = datetime.datetime.now()
    
    while eklenen_sayi < count:
        username_base = names.get_first_name().lower()
        # Kullanıcı adının benzersizliğini sağlamak için rastgele sayı ekleyelim
        username = f"{username_base}_{random.randint(100, 9999)}"
        email = f"{username}@simulasyon.com"
        sifre_hash = generate_random_password(20) # Örn: 20 karakterlik şifre hash'i
        
        # Kullanıcı adı ve e-posta benzersiz ise ekle
        if username not in existing_usernames and email not in existing_emails:
            batch_insert_values.append((email, sifre_hash, current_time, username))
            existing_usernames.add(username)
            existing_emails.add(email)
            eklenen_sayi += 1

    if batch_insert_values:
        # Sütun sırası: email, sifre, created_at, username
        insert_query = """
            INSERT INTO kullanicilar (email, sifre, created_at, username) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (email) DO NOTHING;
        """
        # Toplu ekleme için psycopg2.extras.execute_values kullanmak daha performanslıdır
        # Ancak Psycopg2 kütüphanesi ile toplu ekleme yapılmadığı için,
        # her bir kaydı ayrı ayrı eklemek yerine, tek bir sorguda göndermeye çalışacağız.
        
        # Psycopg2 ile toplu ekleme için (execute_values kullanmadan):
        values = ','.join(cursor.mogrify("(%s, %s, %s, %s)", item).decode('utf-8') for item in batch_insert_values)
        
        final_query = sql.SQL(insert_query.replace("(%s, %s, %s, %s)", values, 1))
        
        cursor.execute(final_query)
        print(f"✅ {eklenen_sayi} adet yeni simüle kullanıcı eklendi.")


# --- 2. BEĞENİ SİMÜLASYON FONKSİYONU (TABLO: favoriler) ---
def add_random_favorites(cursor, films_per_user):
    """Her kullanıcıya rastgele beğeni ekler (favoriler tablosuna)."""

    print(f"\n--- Rastgele Beğeni Ekleme Başladı (Her kullanıcı için {films_per_user} film) ---")

    # 1. Tüm Kullanıcı ID'lerini Çek (Sütun adı: id)
    cursor.execute("SELECT id FROM kullanicilar;") 
    user_ids = [row[0] for row in cursor.fetchall()]
    if not user_ids:
        print("UYARI: Hiç kullanıcı bulunamadı.")
        return

    # 2. Tüm Film ID'lerini Çek (Yeterli veriyi sağlamak için)
    # Film tablosu adının "filmler" ve ID sütununun "film_id" olduğunu varsayıyorum.
    cursor.execute("SELECT film_id FROM filmler WHERE fragman_url IS NOT NULL;") 
    film_ids = [row[0] for row in cursor.fetchall()]
    if len(film_ids) < films_per_user:
        print(f"UYARI: Yeterli ({films_per_user}) film bulunamadı. Eklenen film sayısı: {len(film_ids)}")
        return

    batch_insert_values = []

    for user_id in user_ids:
        # Mevcut beğenilen filmleri kontrol et (Sütun adları: kullanici_id, film_id)
        cursor.execute("SELECT film_id FROM favoriler WHERE kullanici_id = %s;", (user_id,))
        mevcut_begeni_ids = {row[0] for row in cursor.fetchall()}

        secilebilir_filmler = list(set(film_ids) - mevcut_begeni_ids)
        secim_sayisi = min(films_per_user, len(secilebilir_filmler))

        if secim_sayisi > 0:
            rastgele_film_ids = random.sample(secilebilir_filmler, secim_sayisi)

            # (kullanici_id, film_id) çiftlerini ekle
            for film_id in rastgele_film_ids:
                batch_insert_values.append((user_id, film_id))

    # 3. Toplu Ekleme
    if batch_insert_values:
        # Psycopg2 ile toplu ekleme için (execute_values kullanmadan):
        values = ','.join(cursor.mogrify("(%s, %s)", (uid, fid)).decode('utf-8') for uid, fid in batch_insert_values)
        
        insert_query = sql.SQL("""
            INSERT INTO favoriler (kullanici_id, film_id) 
            VALUES {} 
            ON CONFLICT (kullanici_id, film_id) DO NOTHING;
        """).format(sql.SQL(values))
        
        cursor.execute(insert_query)
        print(f"✅ Toplam {len(batch_insert_values)} adet rastgele beğeni eklendi.")
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
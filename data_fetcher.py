import requests
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch
import os
import sys
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# --- SABİT AYARLAR (ÇEKİM MİKTARLARI KESİN OLARAK DÜŞÜRÜLDÜ) ---
TMDB_API_KEY = "e56d77228a887a715c264cbc5000b8c9"
API_TIMEOUT = 20
MAX_PAGES_EN = 30           # 250'den 30'a düşürüldü
MAX_PAGES_TR = 50           # 400'den 50'ye düşürüldü
MAX_PAGES_NOW_PLAYING = 10  # 100'den 10'a düşürüldü
MAX_PAGES_GLOBAL = 30       # Yeni global limit (eskiden 100)
MAX_WORKERS = 20
BATCH_SIZE = 200

# --- HIZ OPTİMİZASYONU: TOPLU KONTROL ---
def check_existing_movies(cursor, tmdb_ids):
    """Birden fazla filmi tek sorguda kontrol eder."""
    if not tmdb_ids:
        return set()
    try:
        cursor.execute(
            "SELECT tmdb_id FROM filmler WHERE tmdb_id = ANY(%s) AND fragman_url IS NOT NULL",
            (list(tmdb_ids),)
        )
        return {row[0] for row in cursor.fetchall()}
    except Exception as e:
        print(f"❌ Toplu kontrol hatası: {e}", file=sys.stderr)
        return set()

# --- YARDIMCI VERİ EKLEME (CACHE İLE) ---
_cache = {"turler": {}, "oyuncular": {}, "yonetmenler": {}}

def insert_data_cached(cursor, data, table_name, column_name):
    """Cache kullanarak gereksiz DB sorgularını önler."""
    if not data:
        return None
    
    # Cache'de var mı kontrol et
    if data in _cache[table_name]:
        return _cache[table_name][data]
    
    pk_name = (
        "tur_id" if table_name == "turler"
        else "oyuncu_id" if table_name == "oyuncular"
        else "yonetmen_id"
    )
    
    try:
        cursor.execute(
            sql.SQL("SELECT {} FROM {} WHERE {} = %s").format(
                sql.Identifier(pk_name),
                sql.Identifier(table_name),
                sql.Identifier(column_name),
            ),
            (data,),
        )
        record = cursor.fetchone()
        if record:
            _cache[table_name][data] = record[0]
            return record[0]
        
        cursor.execute(
            sql.SQL("INSERT INTO {} ({}) VALUES (%s) RETURNING {}").format(
                sql.Identifier(table_name),
                sql.Identifier(column_name),
                sql.Identifier(pk_name),
            ),
            (data,),
        )
        pk_id = cursor.fetchone()[0]
        _cache[table_name][data] = pk_id
        return pk_id
    except Exception:
        return None

# --- API'DEN FİLM LİSTESİ ÇEKME ---
def fetch_movies(api_key, endpoint, max_pages_to_fetch):
    """Film listesini çeker."""
    all_movies = []
    try:
        first_url = f"https://api.themoviedb.org/3/movie/{endpoint}?api_key={api_key}&language=tr-TR&page=1"
        response = requests.get(first_url, timeout=API_TIMEOUT)
        response.raise_for_status()
        first_page_data = response.json()
        total_pages = min(first_page_data.get("total_pages", 1), max_pages_to_fetch)
        all_movies.extend(first_page_data.get("results", []))

        for page_number in range(2, total_pages + 1):
            url = f"https://api.themoviedb.org/3/movie/{endpoint}?api_key={api_key}&language=tr-TR&page={page_number}"
            response = requests.get(url, timeout=API_TIMEOUT)
            response.raise_for_status()
            movies = response.json().get("results", [])
            if not movies:
                break
            all_movies.extend(movies)
            if page_number % 10 == 0:
                print(f"✅ {endpoint}: Sayfa {page_number}/{total_pages} (Toplam: {len(all_movies)})")
    except Exception as e:
        print(f"❌ {endpoint} hatası: {e}", file=sys.stderr)
    return all_movies

def fetch_discover_movies(api_key, language_code, max_pages_to_fetch, sort_by):
    """Discover API'den film çeker."""
    all_movies = []
    try:
        print(f"--- DISCOVER ({language_code.upper()}) - {sort_by} ---")
        for page_number in range(1, max_pages_to_fetch + 1):
            url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&language=tr-TR&sort_by={sort_by}&with_original_language={language_code}&page={page_number}"
            response = requests.get(url, timeout=API_TIMEOUT)
            response.raise_for_status()
            movies = response.json().get("results", [])
            if not movies:
                break
            all_movies.extend(movies)
            if page_number % 10 == 0: # 20'den 10'a düşürüldü
                print(f"✅ DISCOVER ({language_code.upper()}): Sayfa {page_number}/{max_pages_to_fetch} (Toplam: {len(all_movies)})")
    except Exception as e:
        print(f"❌ DISCOVER ({language_code.upper()}) hatası: {e}", file=sys.stderr)
    return all_movies

# --- PARALEL FİLM DETAY ÇEKME ---
def fetch_single_movie_data(movie_id, api_key):
    """Tek bir filmin tüm detaylarını çeker (paralel çalışacak)."""
    try:
        # Tek istekte hem detay hem credits hem videos (3 istek → 1 istek)
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=tr-TR&append_to_response=credits,videos"
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Fragman URL
        videos = data.get("videos", {}).get("results", [])
        trailer_url = next(
            (f"https://www.youtube.com/embed/{v['key']}" 
             for v in videos if v.get("type") == "Trailer" and v.get("site") == "YouTube"),
            None
        )
        
        return {
            "movie_id": movie_id,
            "details": data,
            "credits": data.get("credits", {}),
            "trailer_url": trailer_url
        }
    except Exception:
        return None

# --- ANA FONKSİYON ---
def main():
    conn = None
    cursor = None
    try:
        # --- VERİTABANI BAĞLANTISI ---
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url)
        else:
            DB_HOST = os.environ.get("DB_HOST", "db")
            DB_NAME = os.environ.get("DB_NAME", "film_onerileri")
            DB_USER = os.environ.get("DB_USER", "postgres")
            DB_PASSWORD = os.environ.get("DB_PASSWORD", "1234")
            conn = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, client_encoding='utf8'
            )

        conn.autocommit = False
        cursor = conn.cursor()
        print("✅ Veritabanına bağlanıldı.")

        # --- FİLM LİSTELERİNİ ÇEKME ---
        print("\n📥 Film listeleri çekiliyor (Kısıtlı Mod)...")
        movie_lists = [
            # TR FİLMLER (50 sayfa x 4 kategori = 4000 girdi)
            ("tr_top_rated", fetch_discover_movies(TMDB_API_KEY, "tr", MAX_PAGES_TR, "vote_average.desc")),
            ("tr_popular", fetch_discover_movies(TMDB_API_KEY, "tr", MAX_PAGES_TR, "popularity.desc")),
            ("tr_vote_count", fetch_discover_movies(TMDB_API_KEY, "tr", MAX_PAGES_TR, "vote_count.desc")),
            ("tr_new_releases", fetch_discover_movies(TMDB_API_KEY, "tr", MAX_PAGES_TR, "release_date.desc")),
            
            # EN FİLMLER (30 sayfa x 4 kategori = 2400 girdi)
            ("en_top_rated", fetch_discover_movies(TMDB_API_KEY, "en", MAX_PAGES_EN, "vote_average.desc")),
            ("en_popular", fetch_discover_movies(TMDB_API_KEY, "en", MAX_PAGES_EN, "popularity.desc")),
            ("en_vote_count", fetch_discover_movies(TMDB_API_KEY, "en", MAX_PAGES_EN, "vote_count.desc")),
            ("en_new_releases", fetch_discover_movies(TMDB_API_KEY, "en", MAX_PAGES_EN, "release_date.desc")),
            
            # GÜNCEL VİZYON FİLMLERİ (10 sayfa = 200 girdi)
            ("now_playing", fetch_movies(TMDB_API_KEY, "now_playing", MAX_PAGES_NOW_PLAYING)),
            
            # GLOBAL TOP/POPÜLER (30 sayfa x 2 kategori = 1200 girdi)
            ("top_rated_global", fetch_movies(TMDB_API_KEY, "top_rated", MAX_PAGES_GLOBAL)),
            ("popular_global", fetch_movies(TMDB_API_KEY, "popular", MAX_PAGES_GLOBAL)),
        ]

        # --- BENZERSIZ FİLM ID'LERİNİ TOPLA ---
        all_movie_ids = set()
        for category, movies in movie_lists:
            all_movie_ids.update(movie.get("id") for movie in movies if movie.get("id"))
        
        print(f"\n✅ Toplam benzersiz film: {len(all_movie_ids)}")

        # --- DB'DE OLANLARDAN AYIKLA ---
        existing_ids = check_existing_movies(cursor, all_movie_ids)
        to_fetch = list(all_movie_ids - existing_ids)
        print(f"✅ Zaten işlenmiş: {len(existing_ids)}, İşlenecek: {len(to_fetch)}")

        if not to_fetch:
            print("✅ Tüm filmler güncel!")
            return

        # --- PARALEL DETAY ÇEKME ---
        print(f"\n⚡ {len(to_fetch)} film detayı {MAX_WORKERS} thread ile paralel çekiliyor...")
        all_movie_data = []
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_single_movie_data, mid, TMDB_API_KEY): mid for mid in to_fetch}
            
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                if result:
                    all_movie_data.append(result)
                if i % 100 == 0:
                    print(f"  → {i}/{len(to_fetch)} film çekildi...")

        print(f"✅ {len(all_movie_data)} film detayı başarıyla çekildi.")

        # --- VERİTABANINA TOPLU KAYDETME ---
        print("\n💾 Veritabanına kaydediliyor...")
        total_saved = 0
        
        for batch_start in range(0, len(all_movie_data), BATCH_SIZE):
            batch = all_movie_data[batch_start:batch_start + BATCH_SIZE]
            
            for movie_data in batch:
                try:
                    details = movie_data["details"]
                    credits = movie_data["credits"]
                    trailer_url = movie_data["trailer_url"]
                    movie_id = movie_data["movie_id"]
                    
                    # FİLTRELER YUMUŞATILDI
                    ozet = details.get("overview")
                    afis_url_path = details.get("poster_path")
                    imdb_puani = details.get("vote_average") or 0
                    vote_count = details.get("vote_count") or 0
                    release_date_str = details.get("release_date")
                    
                    # Sadece kritik alanlar kontrol ediliyor
                    if not afis_url_path or not release_date_str:
                        continue
                    
                    # Özet yoksa "Özet bulunmuyor" yaz (atlamak yerine)
                    if not ozet:
                        ozet = "Özet bilgisi mevcut değil."
                    
                    # Puan filtresi yumuşatıldı (1.0 → 0.5, 5 oy → 1 oy)
                    if imdb_puani < 0.5 or vote_count < 1:
                        continue
                    
                    try:
                        release_date = date.fromisoformat(release_date_str)
                    except:
                        continue
                    
                    baslik = details.get("title") or "Bilinmiyor"
                    afis_url = f"https://image.tmdb.org/t/p/w500{afis_url_path}"
                    
                    # Film ekle
                    cursor.execute(
                        """
                        INSERT INTO filmler (tmdb_id, baslik, ozet, afis_url, imdb_puani, release_date, fragman_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (tmdb_id) DO UPDATE
                        SET baslik = EXCLUDED.baslik, ozet = EXCLUDED.ozet, afis_url = EXCLUDED.afis_url,
                            imdb_puani = EXCLUDED.imdb_puani, release_date = EXCLUDED.release_date, fragman_url = EXCLUDED.fragman_url
                        RETURNING film_id;
                        """,
                        (movie_id, baslik, ozet, afis_url, imdb_puani, release_date, trailer_url),
                    )
                    film_id = cursor.fetchone()[0]
                    
                    # İlişkisel veriler
                    if film_id:
                        # Türler
                        cursor.execute("DELETE FROM film_turleri WHERE film_id = %s", (film_id,))
                        for genre in details.get("genres", []):
                            tur_id = insert_data_cached(cursor, genre.get("name"), "turler", "ad")
                            if tur_id:
                                cursor.execute(
                                    "INSERT INTO film_turleri (film_id, tur_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                    (film_id, tur_id)
                                )
                        
                        # Yönetmenler
                        cursor.execute("DELETE FROM film_yonetmenleri WHERE film_id = %s", (film_id,))
                        for crew in credits.get("crew", []):
                            if crew.get("job") == "Director":
                                yonetmen_id = insert_data_cached(cursor, crew.get("name"), "yonetmenler", "ad")
                                if yonetmen_id:
                                    cursor.execute(
                                        "INSERT INTO film_yonetmenleri (film_id, yonetmen_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                        (film_id, yonetmen_id)
                                    )
                        
                        # Oyuncular
                        cursor.execute("DELETE FROM film_oyunculari WHERE film_id = %s", (film_id,))
                        for cast_member in credits.get("cast", [])[:5]:
                            oyuncu_id = insert_data_cached(cursor, cast_member.get("name"), "oyuncular", "ad")
                            if oyuncu_id:
                                cursor.execute(
                                    "INSERT INTO film_oyunculari (film_id, oyuncu_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                    (film_id, oyuncu_id)
                                )
                        
                        total_saved += 1
                
                except Exception as e:
                    print(f"❌ Film kayıt hatası (ID: {movie_data.get('movie_id')}): {e}", file=sys.stderr)
                    continue
            
            # Her batch sonrası commit
            conn.commit()
            print(f"  → {total_saved} film kaydedildi...")

        print(f"\n✅ İşlem tamamlandı! Toplam kaydedilen: {total_saved} film")

    except Exception as e:
        print(f"❌ KRİTİK HATA: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("Veritabanı bağlantısı kapatıldı.")

if __name__ == "__main__":
    main()

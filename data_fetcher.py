import requests
import psycopg2
from psycopg2 import sql
import time
import random
import os
import sys  # <-- Hata çıktısını almak için KRİTİK EKLENTİ
from datetime import date  # Tarih nesneleriyle çalışmak için ekledik (Veri tipi hatasını önlemek için)

# --- SABİT AYARLAR ---
TMDB_API_KEY = "e56d77228a887a715c264cbc5000b8c9"
API_TIMEOUT = 30
API_DELAY = 0.3
MAX_PAGES_EN = 40
MAX_PAGES_TR = 60


# --- HIZ OPTİMİZASYONU: FİLMİN TAM İŞLENİP İŞLENMEDİĞİNİ KONTROL EDER ---
def check_if_fully_fetched(cursor, tmdb_id):
    """Filmin veritabanında var olup olmadığını ve tam işlenip işlenmediğini kontrol eder."""
    try:
        cursor.execute(
            """
            SELECT film_id, fragman_url 
            FROM filmler 
            WHERE tmdb_id = %s;
            """,
            (tmdb_id,),
        )
        result = cursor.fetchone()
        if result and result[1] is not None:
            return True, result[0]
        return False, result[0] if result else None
    except Exception as e:
        print(f"❌ DB Kontrol hatası (tmdb_id: {tmdb_id}): {e}", file=sys.stderr)
        return False, None


# --- YARDIMCI VERİ EKLEME FONKSİYONU ---
def insert_data(conn, cursor, data, table_name, column_name):
    if not data:
        return None
    pk_name = (
        "tur_id"
        if table_name == "turler"
        else "oyuncu_id" if table_name == "oyuncular" else "yonetmen_id"
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
            return record[0]
        cursor.execute(
            sql.SQL("INSERT INTO {} ({}) VALUES (%s) RETURNING {}").format(
                sql.Identifier(table_name),
                sql.Identifier(column_name),
                sql.Identifier(pk_name),
            ),
            (data,),
        )
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"❌ DB Veri Ekleme Hatası (Tablo: {table_name}, Veri: {data}): {e}", file=sys.stderr)
        return None


# --- API'DEN FİLM LİSTESİ ÇEKME FONKSİYONLARI ---
def fetch_movies(api_key, endpoint, max_pages_to_fetch):
    all_movies = []
    try:
        first_url = f"https://api.themoviedb.org/3/movie/{endpoint}?api_key={api_key}&language=tr-TR&page=1"
        response = requests.get(first_url, timeout=API_TIMEOUT)
        response.raise_for_status()
        first_page_data = response.json()
        total_pages = first_page_data.get("total_pages", 1)
        pages_to_fetch = min(total_pages, max_pages_to_fetch)
        all_movies.extend(first_page_data.get("results", []))

        for page_number in range(2, pages_to_fetch + 1):
            url = f"https://api.themoviedb.org/3/movie/{endpoint}?api_key={api_key}&language=tr-TR&page={page_number}"
            response = requests.get(url, timeout=API_TIMEOUT)
            response.raise_for_status()
            movies = response.json().get("results", [])
            if not movies:
                break
            all_movies.extend(movies)
            print(
                f"✅ {endpoint} filmler: Sayfa {page_number}/{pages_to_fetch} - Film Sayısı: {len(movies)} (Toplam: {len(all_movies)})"
            )
            time.sleep(API_DELAY)

    except requests.exceptions.RequestException as req_e:
        print(f"❌ API Çekme Hatası ({endpoint}): {req_e}", file=sys.stderr)
    except Exception as e:
        print(f"❌ {endpoint} filmler çekme genel hatası: {e}", file=sys.stderr)
    return all_movies


def fetch_discover_movies(api_key, language_code, max_pages_to_fetch, sort_by):
    all_movies = []
    try:
        print(
            f"--- DISCOVER ({language_code.upper()} DİLİ) --- Sıralama: {sort_by} | Maksimum Sayfa: {max_pages_to_fetch}"
        )
        first_url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&language=tr-TR&sort_by={sort_by}&with_original_language={language_code}&page=1"
        response = requests.get(first_url, timeout=API_TIMEOUT)
        response.raise_for_status()
        first_page_data = response.json()
        total_pages = first_page_data.get("total_pages", 1)
        pages_to_fetch = min(total_pages, max_pages_to_fetch)
        all_movies.extend(first_page_data.get("results", []))

        time.sleep(API_DELAY)

        for page_number in range(2, pages_to_fetch + 1):
            url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&language=tr-TR&sort_by={sort_by}&with_original_language={language_code}&page={page_number}"
            response = requests.get(url, timeout=API_TIMEOUT)
            response.raise_for_status()
            movies = response.json().get("results", [])
            if not movies:
                break
            all_movies.extend(movies)
            print(
                f"✅ DISCOVER ({language_code.upper()} DİLİ): Sayfa {page_number}/{pages_to_fetch} - Film Sayısı: {len(movies)} (Toplam: {len(all_movies)})"
            )
            time.sleep(API_DELAY)

    except requests.exceptions.RequestException as req_e:
        print(f"❌ API Çekme Hatası (DISCOVER {language_code.upper()} DİLİ - {sort_by}): {req_e}", file=sys.stderr)
    except Exception as e:
        print(f"❌ DISCOVER ({language_code.upper()} DİLİ) çekme genel hatası ({sort_by}): {e}", file=sys.stderr)
    return all_movies


def fetch_movie_details_combined(movie_id, api_key):
    try:
        url_combined = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=tr-TR&append_to_response=credits"
        response = requests.get(url_combined, timeout=API_TIMEOUT)
        response.raise_for_status()
        combined_data = response.json()
        return combined_data, combined_data.get("credits", {})
    except requests.exceptions.RequestException as req_e:
        print(f"❌ Film Detayları API Hatası (ID: {movie_id}): {req_e}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"❌ Film Detayları Genel Hatası (ID: {movie_id}): {e}", file=sys.stderr)
        return None, None


def fetch_movie_trailer(movie_id, api_key):
    try:
        url_videos = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={api_key}"
        response = requests.get(url_videos, timeout=API_TIMEOUT)
        response.raise_for_status()
        videos = response.json().get("results", [])
        selected_video = next(
            (
                v
                for v in videos
                if v.get("type") == "Trailer" and v.get("site") == "YouTube"
            ),
            None,
        )
        return (
            f"https://www.youtube.com/embed/{selected_video['key']}"
            if selected_video
            else None
        )
    except requests.exceptions.RequestException:
        return None
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
            print("Veritabanı bağlantısı DATABASE_URL ortam değişkeni kullanılarak yapılıyor.")
            conn = psycopg2.connect(database_url)
        else:
            DB_HOST = os.environ.get("DB_HOST", "db")
            DB_NAME = os.environ.get("DB_NAME", "film_onerileri")
            DB_USER = os.environ.get("DB_USER", "postgres")
            DB_PASSWORD = os.environ.get("DB_PASSWORD", "1234")

            print(f"Veritabanı bağlantısı ayrı değişkenlerle yapılıyor (Host: {DB_HOST}).")
            conn = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, client_encoding='utf8'
            )

        conn.autocommit = True
        cursor = conn.cursor()
        print("✅ Veritabanına bağlanıldı. (Autocommit modu aktif)")

        # --- FİLM LİSTELERİNİ ÇEKME ---
        movie_lists = [
            ("tr_top_rated", fetch_discover_movies(TMDB_API_KEY, "tr", MAX_PAGES_TR, "vote_average.desc")),
            ("tr_popular", fetch_discover_movies(TMDB_API_KEY, "tr", MAX_PAGES_TR, "popularity.desc")),
            ("tr_vote_count", fetch_discover_movies(TMDB_API_KEY, "tr", MAX_PAGES_TR, "vote_count.desc")),
            ("tr_new_releases", fetch_discover_movies(TMDB_API_KEY, "tr", MAX_PAGES_TR, "release_date.desc")),
            ("en_top_rated", fetch_discover_movies(TMDB_API_KEY, "en", MAX_PAGES_EN, "vote_average.desc")),
            ("en_popular", fetch_discover_movies(TMDB_API_KEY, "en", MAX_PAGES_EN, "popularity.desc")),
            ("en_vote_count", fetch_discover_movies(TMDB_API_KEY, "en", MAX_PAGES_EN, "vote_count.desc")),
            ("en_new_releases", fetch_discover_movies(TMDB_API_KEY, "en", MAX_PAGES_EN, "release_date.desc")),
            ("now_playing_global", fetch_movies(TMDB_API_KEY, "now_playing", max_pages_to_fetch=30)),
        ]

        # --- FİLM DETAYLARINI ÇEKME VE DB'YE KAYDETME ---
        total_movies_processed = 0

        for category, movies in movie_lists:
            print(f"\n--- {category.upper()} KATEGORİSİ İŞLENİYOR ({len(movies)} film) ---")

            for movie in movies:
                movie_id = movie.get("id")
                if not movie_id:
                    continue

                is_fetched, existing_film_id = check_if_fully_fetched(cursor, movie_id)
                if is_fetched:
                    continue
                film_id = existing_film_id

                # Detayları Çek
                details, credits = fetch_movie_details_combined(movie_id, TMDB_API_KEY)
                trailer_url = fetch_movie_trailer(movie_id, TMDB_API_KEY)

                if not details or not credits:
                    continue

                ozet = details.get("overview")
                afis_url_path = details.get("poster_path")
                imdb_puani = details.get("vote_average") or 0
                vote_count = details.get("vote_count") or 0
                release_date_str = details.get("release_date")

                release_date = None
                if release_date_str and release_date_str.count('-') == 2:
                    try:
                        release_date = date.fromisoformat(release_date_str)
                    except ValueError:
                        release_date = None

                # KRİTİK FİLTRELER
                if not ozet or not afis_url_path or not release_date:
                    continue
                if imdb_puani < 1.0 or vote_count < 5:
                    continue

                time.sleep(API_DELAY)

                try:
                    baslik = details.get("title") or "Başlık yok"
                    afis_url = f"https://image.tmdb.org/t/p/w500{afis_url_path}"

                    # Filmi ekle/güncelle
                    cursor.execute(
                        """
                        INSERT INTO filmler (tmdb_id, baslik, ozet, afis_url, imdb_puani, release_date, fragman_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (tmdb_id) DO UPDATE
                        SET baslik = EXCLUDED.baslik,
                            ozet = EXCLUDED.ozet,
                            afis_url = EXCLUDED.afis_url,
                            imdb_puani = EXCLUDED.imdb_puani,
                            release_date = EXCLUDED.release_date,
                            fragman_url = EXCLUDED.fragman_url
                        RETURNING film_id;
                        """,
                        (
                            movie_id,
                            baslik,
                            ozet,
                            afis_url,
                            imdb_puani,
                            release_date,
                            trailer_url,
                        ),
                    )

                    film_id_row = cursor.fetchone()
                    film_id = film_id_row[0] if film_id_row else None

                    # İlişkisel tablolar
                    if film_id:
                        # Türler
                        cursor.execute("DELETE FROM film_turleri WHERE film_id = %s", (film_id,))
                        for genre in details.get("genres", []):
                            tur_id = insert_data(conn, cursor, genre.get("name"), "turler", "ad")
                            if tur_id:
                                cursor.execute("INSERT INTO film_turleri (film_id, tur_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (film_id, tur_id))

                        # Yönetmenler
                        cursor.execute("DELETE FROM film_yonetmenleri WHERE film_id = %s", (film_id,))
                        for crew in credits.get("crew", []):
                            if crew.get("job") == "Director":
                                yonetmen_id = insert_data(conn, cursor, crew.get("name"), "yonetmenler", "ad")
                                if yonetmen_id:
                                    cursor.execute("INSERT INTO film_yonetmenleri (film_id, yonetmen_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (film_id, yonetmen_id))

                        # Oyuncular
                        cursor.execute("DELETE FROM film_oyunculari WHERE film_id = %s", (film_id,))
                        for cast_member in credits.get("cast", [])[:5]:
                            oyuncu_id = insert_data(conn, cursor, cast_member.get("name"), "oyuncular", "ad")
                            if oyuncu_id:
                                cursor.execute("INSERT INTO film_oyunculari (film_id, oyuncu_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (film_id, oyuncu_id))

                        total_movies_processed += 1
                        print(f"-> Başarıyla işlendi: {baslik} (Toplam: {total_movies_processed})")

                    else:
                        print(f"❌ UYARI: Film ID {movie_id} için film_id elde edilemedi. Kayıt atlandı.", file=sys.stderr)
                        continue

                except psycopg2.Error as db_e:
                    print(f"❌ KRİTİK DB KAYIT HATASI ({movie_id} - {baslik}): {db_e}", file=sys.stderr)
                    continue

                except Exception as e:
                    print(f"❌ Film İşleme (Beklenmedik) Hatası ({movie_id} - {baslik}): {e}", file=sys.stderr)
                    continue

        print(f"\n✅ Veri çekme ve kaydetme tamamlandı. Toplam işlenen film: {total_movies_processed}")

    except psycopg2.Error as db_e_genel:
        print(f"❌ KRİTİK BAĞLANTI HATASI (PostgreSQL): {db_e_genel}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ KRİTİK GENEL HATA: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn and cursor:
            try:
                cursor.close()
                conn.close()
                print("Veritabanı bağlantısı kapatıldı.")
            except Exception as close_e:
                print(f"❌ Bağlantı kapatılırken hata oluştu: {close_e}", file=sys.stderr)


if __name__ == "__main__":
    main()

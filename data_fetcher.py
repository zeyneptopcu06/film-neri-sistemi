import requests
import psycopg2
from psycopg2 import sql
import time
import random
import os # <-- BU SATIRI EKLEYİN!
# --- BAĞLANTI BİLGİLERİ (LÜTFEN KONTROL EDİN) ---
TMDB_API_KEY = "e56d77228a887a715c264cbc5000b8c9"  # Kendi anahtarınızı girin
API_TIMEOUT = 30
API_DELAY = 0.3
MAX_PAGES_EN = 40  # İngilizce filmler için max sayfa
MAX_PAGES_TR = 60  # Türkçe filmler için max sayfa


# --- HIZ OPTİMİZASYONU: FİLMİN TAM İŞLENİP İŞLENMEDİĞİNİ KONTROL EDER ---
def check_if_fully_fetched(cursor, tmdb_id):
    """Filmin veritabanında var olup olmadığını ve tam işlenip işlenmediğini kontrol eder."""
    try:
        # Fragman URL'si varsa, filmin tamamen işlendiği varsayılır (optimizasyon).
        cursor.execute(
            """
            SELECT film_id, fragman_url 
            FROM filmler 
            WHERE tmdb_id = %s;
            """,
            (tmdb_id,),
        )
        result = cursor.fetchone()

        # Film mevcutsa VE fragman_url'si NULL değilse, atla.
        if result and result[1] is not None:
            return True, result[0]

        return False, result[0] if result else None

    except Exception as e:
        print(f"Kontrol hatası: {e}")
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
        # autocommit=True olduğu için conn.rollback() ihtiyacı yoktur
        return cursor.fetchone()[0]
    except Exception as e:
        return None


# --- API'DEN FİLM LİSTESİ ÇEKME FONKSİYONLARI (Aynı Kaldı) ---


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
                f"{endpoint} filmler: Sayfa {page_number}/{pages_to_fetch} - Film Sayısı: {len(movies)} (Toplam: {len(all_movies)})"
            )
            time.sleep(API_DELAY)

    except Exception as e:
        print(f"{endpoint} filmler çekme hatası: {e}")
    return all_movies


def fetch_discover_movies(api_key, language_code, max_pages_to_fetch, sort_by):
    all_movies = []
    try:
        first_url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&language=tr-TR&sort_by={sort_by}&with_original_language={language_code}&page=1"
        response = requests.get(first_url, timeout=API_TIMEOUT)
        response.raise_for_status()
        first_page_data = response.json()
        total_pages = first_page_data.get("total_pages", 1)
        pages_to_fetch = min(total_pages, max_pages_to_fetch)
        all_movies.extend(first_page_data.get("results", []))
        print(
            f"--- DISCOVER ({language_code.upper()} DİLİ) --- Sıralama: {sort_by} | Çekilecek Sayfa: {pages_to_fetch}"
        )
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
                f"DISCOVER ({language_code.upper()} DİLİ): Sayfa {page_number}/{pages_to_fetch} - Film Sayısı: {len(movies)} (Toplam: {len(all_movies)})"
            )
            time.sleep(API_DELAY)

    except Exception as e:
        print(f"DISCOVER ({language_code.upper()} DİLİ) çekme hatası ({sort_by}): {e}")
    return all_movies


def fetch_movie_details_combined(movie_id, api_key):
    try:
        url_combined = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=tr-TR&append_to_response=credits"
        response = requests.get(url_combined, timeout=API_TIMEOUT)
        response.raise_for_status()
        combined_data = response.json()
        return combined_data, combined_data.get("credits", {})
    except Exception as e:
        return None, None


def fetch_movie_trailer(movie_id, api_key):
    try:
        url_videos = (
            f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={api_key}"
        )
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
    except Exception as e:
        return None


# --- ANA FONKSİYON ---


def main():
    try:
        database_url = os.environ.get("DATABASE_URL")
        
        if database_url:
            # 1. Yöntem: Tek DATABASE_URL kullan
            print("Veritabanı bağlantısı DATABASE_URL ortam değişkeni kullanılarak yapılıyor.")
            conn = psycopg2.connect(database_url)
        else:
            # 2. Yöntem: Ayrı ayrı değişkenleri kullan (eski mantık/fallback)
            DB_HOST = os.environ.get("DB_HOST", "db") 
            DB_NAME = os.environ.get("DB_NAME", "film_onerileri")
            DB_USER = os.environ.get("DB_USER", "postgres")
            DB_PASSWORD = os.environ.get("DB_PASSWORD", "1234")
            
            print(f"Veritabanı bağlantısı ayrı değişkenlerle yapılıyor (Host: {DB_HOST}).")
            conn = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
            )
        conn.autocommit = True
        cursor = conn.cursor()
        print("Veritabanına bağlanıldı. (Autocommit modu aktif: Hata önleme)")

        # main() fonksiyonunun içindeki movie_lists:
        movie_lists = [
            # ----------------------------------------------------
            # ⭐ TÜRKÇE ODAKLI ÇEKİMLER (4 TEMEL ÇEŞİTLİLİK ÖLÇÜTÜ) ⭐
            # ----------------------------------------------------
            # 1. EN KALİTELİ (IMDB PUANI)
            (
                "tr_top_rated",
                fetch_discover_movies(
                    TMDB_API_KEY,
                    "tr",
                    max_pages_to_fetch=MAX_PAGES_TR,
                    sort_by="vote_average.desc",
                ),
            ),
            # 2. EN POPÜLER (GÜNCEL İLGİ)
            (
                "tr_popular",
                fetch_discover_movies(
                    TMDB_API_KEY,
                    "tr",
                    max_pages_to_fetch=MAX_PAGES_TR,
                    sort_by="popularity.desc",
                ),
            ),
            # 3. EN ÇOK İZLENEN (OY SAYISI) - Geniş kitleye ulaşmış filmleri yakalar
            (
                "tr_vote_count",
                fetch_discover_movies(
                    TMDB_API_KEY,
                    "tr",
                    max_pages_to_fetch=MAX_PAGES_TR,
                    sort_by="vote_count.desc",
                ),
            ),
            # 4. EN YENİ (YIL ÇEŞİTLİLİĞİ) - Henüz puanı oturmamış güncel filmleri yakalar
            (
                "tr_new_releases",
                fetch_discover_movies(
                    TMDB_API_KEY,
                    "tr",
                    max_pages_to_fetch=MAX_PAGES_TR,
                    sort_by="release_date.desc",
                ),
            ),
            # ----------------------------------------------------
            # ⭐ İNGİLİZCE ODAKLI ÇEKİMLER (4 TEMEL ÇEŞİTLİLİK ÖLÇÜTÜ) ⭐
            # ----------------------------------------------------
            # 1. EN KALİTELİ (IMDB PUANI)
            (
                "en_top_rated",
                fetch_discover_movies(
                    TMDB_API_KEY,
                    "en",
                    max_pages_to_fetch=MAX_PAGES_EN,
                    sort_by="vote_average.desc",
                ),
            ),
            # 2. EN POPÜLER (GÜNCEL İLGİ)
            (
                "en_popular",
                fetch_discover_movies(
                    TMDB_API_KEY,
                    "en",
                    max_pages_to_fetch=MAX_PAGES_EN,
                    sort_by="popularity.desc",
                ),
            ),
            # 3. EN ÇOK İZLENEN (OY SAYISI)
            (
                "en_vote_count",
                fetch_discover_movies(
                    TMDB_API_KEY,
                    "en",
                    max_pages_to_fetch=MAX_PAGES_EN,
                    sort_by="vote_count.desc",
                ),
            ),
            # 4. EN YENİ (YIL ÇEŞİTLİLİĞİ)
            (
                "en_new_releases",
                fetch_discover_movies(
                    TMDB_API_KEY,
                    "en",
                    max_pages_to_fetch=MAX_PAGES_EN,
                    sort_by="release_date.desc",
                ),
            ),
            # ----------------------------------------------------
            # ⭐ GÜNCEL VİZYON LİSTESİ (Tüm dillerden güncel ilgi) ⭐
            # ----------------------------------------------------
            # Now Playing, TMDB'nin en genel ve sık güncellenen listesidir.
            (
                "now_playing_global",
                fetch_movies(TMDB_API_KEY, "now_playing", max_pages_to_fetch=30),
            ),
        ]
        for category, movies in movie_lists:
            print(
                f"\n--- {category.upper()} KATEGORİSİ İŞLENİYOR ({len(movies)} film) ---"
            )

            for movie in movies:
                movie_id = movie.get("id")
                if not movie_id:
                    continue

                # ⭐ HIZ OPTİMİZASYONU: Zaten işlenmiş filmleri atla! ⭐
                is_fetched, existing_film_id = check_if_fully_fetched(cursor, movie_id)

                if is_fetched:
                    continue
                film_id = existing_film_id # Eğer mevcut ID varsa kullan, yoksa None olsun.
                # YENİ VEYA EKSİK FİLMLER İÇİN NORMAL İŞLEM BAŞLAR
                details, credits = fetch_movie_details_combined(movie_id, TMDB_API_KEY)
                trailer_url = fetch_movie_trailer(movie_id, TMDB_API_KEY)

                if not details or not credits:
                    continue

                # Afiş, Özet, Puan, Oy Sayısı ve Yayın Tarihi bilgisi çekme
                ozet = details.get("overview")
                afis_url_path = details.get("poster_path")
                imdb_puani = details.get("vote_average") or 0
                vote_count = details.get("vote_count") or 0
                release_date = details.get("release_date")  # Yayın tarihi çekildi

                # ⭐ VERİ KALİTESİ FİLTRESİ (Yayın Tarihi Eklendi) ⭐

                # 1. Özet, Afiş URL yolu VEYA Yayın Tarihi yoksa filmi atla
                if not ozet or not afis_url_path or not release_date:
                    continue

                # 2. IMDb puanı 1.0'dan küçük VEYA oy sayısı 5'ten az ise atla
                if imdb_puani < 1.0 or vote_count < 5:
                    continue

                # FİLTREDEN GEÇEN FİLMLER İÇİN DEVAM

                time.sleep(API_DELAY)

                try:
                    baslik = details.get("title") or "Başlık yok"
                    afis_url = f"https://image.tmdb.org/t/p/w500{afis_url_path}"

                    # 1. ADIM: FİLMİ ANA TABLOYA EKLE/GÜNCELLE ve film_id'yi DÖNDÜR
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

                    if film_id_row:
                        film_id = film_id_row[0]
                    else:
                        cursor.execute(
                            "SELECT film_id FROM filmler WHERE tmdb_id=%s", (movie_id,)
                        )
                        film_id_final = cursor.fetchone()
                        if film_id_final:
                            film_id = film_id_final[0]

                    # 2. ADIM: İLİŞKİSEL VERİLERİ SADECE film_id VARSA EKLE!
                    if film_id:

                        # TÜR EKLEME
                        cursor.execute(
                            "DELETE FROM film_turleri WHERE film_id = %s", (film_id,)
                        )
                        for genre in details.get("genres", []):
                            tur_id = insert_data(
                                conn, cursor, genre.get("name"), "turler", "ad"
                            )
                            if tur_id:
                                cursor.execute(
                                    "INSERT INTO film_turleri (film_id, tur_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                    (film_id, tur_id),
                                )

                        # YÖNETMEN EKLEME
                        cursor.execute(
                            "DELETE FROM film_yonetmenleri WHERE film_id = %s",
                            (film_id,),
                        )
                        for crew in credits.get("crew", []):
                            if crew.get("job") == "Director":
                                yonetmen_id = insert_data(
                                    conn, cursor, crew.get("name"), "yonetmenler", "ad"
                                )
                                if yonetmen_id:
                                    cursor.execute(
                                        "INSERT INTO film_yonetmenleri (film_id, yonetmen_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                        (film_id, yonetmen_id),
                                    )

                        # OYUNCU EKLEME
                        cursor.execute(
                            "DELETE FROM film_oyunculari WHERE film_id = %s", (film_id,)
                        )
                        for cast_member in credits.get("cast", [])[:5]:
                            oyuncu_id = insert_data(
                                conn, cursor, cast_member.get("name"), "oyuncular", "ad"
                            )
                            if oyuncu_id:
                                cursor.execute(
                                    "INSERT INTO film_oyunculari (film_id, oyuncu_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                    (film_id, oyuncu_id),
                                )
                    else:
                        print(
                            f"UYARI: Film ID {movie_id} için film_id elde edilemedi. Kayıt atlandı."
                        )
                        continue

                except Exception as e:
                    print(f"Film işleme hatası ({movie_id} - {baslik}): {e}")
                    continue

        print("\n✅ Veri çekme ve kaydetme tamamlandı.")

    except Exception as e:
        print(f"Genel hata: {e}")
    finally:
        if "conn" in locals() and conn:
            cursor.close()
            conn.close()
            print("Veritabanı bağlantısı kapatıldı.")


if __name__ == "__main__":
    main()

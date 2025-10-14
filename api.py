from flask import Flask, jsonify, request, render_template, session
from flask_cors import CORS
import bcrypt
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from collections import defaultdict
from recommender_core import get_recommendations, initialize_recommendation_system, df_final
import pandas as pd
from functools import wraps
from flask import session, redirect, url_for
import os
from flask_mail import Mail, Message


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('giris_sayfasi'))
        return f(*args, **kwargs)
    return decorated_function

# Veritabanı bilgileri
DB_NAME = "film_onerileri"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"

def get_connection():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
        return conn
    except psycopg2.DatabaseError as e:
        print(f"Veritabanına bağlanılamadı: {e}")
        return None

def get_id_by_email(email):
    conn = get_connection()
    if not conn:
        return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM kullanicilar WHERE email = %s", (email,))
        user_id = cursor.fetchone()
        return user_id[0] if user_id else None
    except Exception as e:
        print(f"Kullanıcı ID çekme hatası: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_popular_movies_from_db(conn, cursor, limit=10):
    try:
        cursor.execute("SELECT film_id, baslik, afis_url FROM filmler ORDER BY imdb_puani DESC LIMIT %s", (limit,))
        movies = cursor.fetchall()
        popular_movies = [{"film_id": movie[0], "title": movie[1], "poster_url": movie[2]} for movie in movies]
        return popular_movies
    except Exception as e:
        print(f"Popüler filmler çekme hatası: {e}")
        return []

def get_movie_by_id_from_db(conn, cursor, movie_id):
    try:
        cursor.execute("SELECT baslik, afis_url FROM filmler WHERE film_id = %s", (movie_id,))
        movie = cursor.fetchone()
        if movie:
            return {"title": movie[0], "poster_url": movie[1]}
    except Exception as e:
        print(f"Film çekme hatası: {e}")
    return None

def get_movie_id_by_title_from_db(conn, cursor, title):
    try:
        cursor.execute("SELECT film_id, baslik FROM filmler WHERE LOWER(baslik) LIKE %s LIMIT 1", (f'%{title.lower()}%',))
        movie = cursor.fetchone()
        if movie:
            return {"film_id": movie[0], "baslik": movie[1]}
    except Exception as e:
        print(f"Başlığa göre film ID çekme hatası: {e}")
    return {"film_id": None, "baslik": None}


app = Flask(__name__)
CORS(app)
app.secret_key = 'senin-cok-gizli-anahtarın-buraya-gelsin'
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='topcuzeynep445@gmail.com',
    MAIL_PASSWORD='mfoa hdcj dpzm ctgb',  # Gmail için “Uygulama şifresi” kullan
    MAIL_DEFAULT_SENDER=('Filma Destek', 'gmail_adresin@gmail.com')
)

mail = Mail(app)
# HTML sayfaları
@app.route("/")
def home():
    if 'email' not in session:
        return redirect(url_for('giris_sayfasi'))
    return render_template("index.html")

@app.route('/favorites')
def favorites():
    if 'email' not in session:
        return redirect(url_for('giris_sayfasi'))
    return render_template('favorites.html')

@app.route('/movie-detail')
def movie_detail():
    if 'email' not in session:
        return redirect(url_for('giris_sayfasi'))
    movie_id = request.args.get('id')
    email = session.get('email')
    return render_template('movie-detail.html', movie_id=movie_id, email=email)


@app.route('/search')
def search():
    if 'email' not in session:
        return redirect(url_for('giris_sayfasi'))
    email = session.get('email')
    return render_template('search.html', email=email)

@app.route("/kayit")
def kayit_sayfasi():
    return render_template("kayit.html")

@app.route("/giris")
def giris_sayfasi():
    return render_template("giris.html")

# API rotaları
@app.route("/api/popular_movies")
def popular_movies():
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        movies = get_popular_movies_from_db(conn, cursor, limit=20)
        cursor.close()
        conn.close()
        return jsonify(movies)
    return jsonify({"error": "Veritabanı bağlantı hatası"}), 500

@app.route("/api/search/<string:title>")
def search_movie(title):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        movie = get_movie_id_by_title_from_db(conn, cursor, title)
        cursor.close()
        conn.close()
        if movie["film_id"]:
            return jsonify(movie)
        return jsonify({"film_id": None, "baslik": None})
    return jsonify({"error": "Veritabanı bağlantı hatası"}), 500

@app.route("/api/movies/<int:movie_id>")
def get_movie_by_id(movie_id):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        movie = get_movie_by_id_from_db(conn, cursor, movie_id)
        cursor.close()
        conn.close()
        if movie:
            return jsonify(movie)
        return jsonify({"error": "Film bulunamadı"}), 404
    return jsonify({"error": "Veritabanı bağlantı hatası"}), 500

@app.route("/api/kayit", methods=["POST"])
def kayit():
    data = request.get_json()
    email = data.get("email")
    sifre = data.get("sifre")
    username = data.get("username")

    if not email or not sifre or not username:
        return jsonify({"hata": "E-posta, şifre ve kullanıcı adı gerekli."}), 400

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM kullanicilar WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({"hata": "Bu e-posta zaten kayıtlı."}), 409

            hashed_sifre = bcrypt.generate_password_hash(sifre).decode('utf-8')
            cursor.execute(
                "INSERT INTO kullanicilar (email, sifre, username) VALUES (%s, %s, %s)",
                (email, hashed_sifre, username)
            )
            conn.commit()
            return jsonify({"mesaj": "Kayıt başarıyla tamamlandı!"}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"hata": f"Bir hata oluştu: {e}"}), 500
        finally:
            cursor.close()
            conn.close()
    return jsonify({"hata": "Veritabanı bağlantı hatası"}), 500

@app.route("/api/giris", methods=["POST"])
def giris():
    data = request.get_json()
    email = data.get("email")
    sifre = data.get("sifre")
    remember = data.get("remember", False)

    if not email or not sifre:
        return jsonify({"hata": "E-posta ve şifre gerekli."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"hata": "Veritabanı bağlantı hatası"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT sifre FROM kullanicilar WHERE email = %s", (email,))
        result = cursor.fetchone()
        
        if not result:
            # E-posta bulunamadı
            return jsonify({"hata": "E-posta adresi bulunamadı."}), 404

        stored_sifre = result[0]
        if not bcrypt.check_password_hash(stored_sifre, sifre):
            # Şifre yanlış
            return jsonify({"hata": "Şifre hatalı."}), 401

        # Başarılı giriş
        session['email'] = email
        session.permanent = bool(remember)
        return jsonify({"mesaj": "Giriş başarılı!"}), 200

    except Exception as e:
        return jsonify({"hata": f"Sunucu hatası: {e}"}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop('email', None)
    return jsonify({"mesaj": "Çıkış başarılı."}), 200

@app.route("/api/user_status")
def user_status():
    if 'email' in session:
        user_email = session['email']
        conn = get_connection()
        
        if conn:
            cursor = conn.cursor()
            try:
                # ✅ user_id de çekilecek
                cursor.execute(
                    "SELECT id, username FROM kullanicilar WHERE email = %s", 
                    (user_email,)
                )
                
                user_record = cursor.fetchone()
                
                if user_record:
                    user_id = user_record[0]
                    username = user_record[1]
                    return jsonify({
                        "logged_in": True,
                        "user_id": user_id,  # ✅ user_id eklendi
                        "email": user_email, 
                        "username": username
                    })
                else:
                    return jsonify({
                        "logged_in": True, 
                        "email": user_email, 
                        "username": "Bilinmeyen Kullanıcı"
                    })

            except Exception as e:
                print(f"User status DB hatası: {e}") 
                return jsonify({
                    "logged_in": True, 
                    "email": user_email, 
                    "username": "Hata: Kullanıcı Çekilemedi"
                })
            finally:
                cursor.close()
                conn.close()
        
        return jsonify({
            "logged_in": True, 
            "email": user_email, 
            "username": "Bağlantı Hatası"
        })
    else:
        return jsonify({"logged_in": False})

@app.route("/api/add_to_favorites", methods=["POST"])
def add_to_favorites():
    if 'email' not in session:
        return jsonify({"hata": "Giriş yapmalısınız."}), 401

    data = request.get_json()
    film_id = data.get("film_id")

    if not film_id:
        return jsonify({"hata": "Film ID gerekli."}), 400

    kullanici_id = get_id_by_email(session['email'])
    if not kullanici_id:
        return jsonify({"hata": "Kullanıcı bulunamadı."}), 404

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO favoriler (kullanici_id, film_id) VALUES (%s, %s)", (kullanici_id, film_id))
            conn.commit()
            return jsonify({"mesaj": "Film favorilere eklendi."}), 201
        except psycopg2.IntegrityError:
            conn.rollback()
            return jsonify({"hata": "Film zaten favorilerinizde."}), 409
        except Exception as e:
            conn.rollback()
            return jsonify({"hata": f"Bir hata oluştu: {e}"}), 500
        finally:
            cursor.close()
            conn.close()
    return jsonify({"hata": "Veritabanı bağlantı hatası"}), 500

@app.route("/api/get_favorites")
def get_favorites():
    if 'email' not in session:
        return jsonify({"hata": "Giriş yapmalısınız."}), 401
    
    kullanici_id = get_id_by_email(session['email'])
    if not kullanici_id:
        return jsonify({"hata": "Kullanıcı bulunamadı."}), 404
    
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT f.film_id, f.baslik, f.afis_url
                FROM favoriler fav
                JOIN filmler f ON fav.film_id = f.film_id
                WHERE fav.kullanici_id = %s;
            """, (kullanici_id,))
            favorites = cursor.fetchall()
            
            favorite_movies = [
                {"film_id": movie[0], "title": movie[1], "poster_url": movie[2]}
                for movie in favorites
            ]
            return jsonify(favorite_movies), 200
        except Exception as e:
            return jsonify({"hata": f"Favori filmler alınırken bir hata oluştu: {e}"}), 500
        finally:
            cursor.close()
            conn.close()
    return jsonify({"hata": "Veritabanı bağlantı hatası"}), 500

@app.route("/api/remove_from_favorites", methods=["POST"])
def remove_from_favorites():
    if 'email' not in session:
        return jsonify({"hata": "Giriş yapmalısınız."}), 401

    data = request.get_json()
    film_id = data.get("film_id")

    if not film_id:
        return jsonify({"hata": "Film ID gerekli."}), 400

    kullanici_id = get_id_by_email(session['email'])
    if not kullanici_id:
        return jsonify({"hata": "Kullanıcı bulunamadı."}), 404

    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM favoriler WHERE kullanici_id = %s AND film_id = %s", (kullanici_id, film_id))
            conn.commit()
            return jsonify({"mesaj": "Film favorilerden kaldırıldı."}), 200
        except Exception as e:
            conn.rollback()
            return jsonify({"hata": f"Bir hata oluştu: {e}"}), 500
        finally:
            cursor.close()
            conn.close()
    return jsonify({"hata": "Veritabanı bağlantı hatası"}), 500

# ✅ YENİ VERSİYON - EXCLUDE PARAMETRELİ
@app.route("/api/latest_movies")
def latest_movies():
    exclude_param = request.args.get('exclude', '')
    exclude_ids = [int(x) for x in exclude_param.split(',') if x.strip().isdigit()]
    
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Veritabanı bağlantı hatası"}), 500

    cursor = conn.cursor()
    try:
        if exclude_ids:
            cursor.execute("""
                SELECT film_id, baslik, afis_url, release_date
                FROM filmler 
                WHERE release_date IS NOT NULL
                AND film_id != ALL(%s)
                ORDER BY release_date DESC, imdb_puani DESC 
                LIMIT 20
            """, (exclude_ids,))
        else:
            cursor.execute("""
                SELECT film_id, baslik, afis_url, release_date
                FROM filmler 
                WHERE release_date IS NOT NULL
                ORDER BY release_date DESC, imdb_puani DESC 
                LIMIT 20
            """)
        
        movies = cursor.fetchall()

        result = []
        for m in movies:
            release_date = m[3]
            year = release_date.year if release_date else None
            result.append({
                "film_id": m[0],
                "title": m[1],
                "poster_url": m[2],
                "year": year
            })

        return jsonify(result)
    finally:
        cursor.close()
        conn.close()

@app.route("/api/now_playing")
def now_playing():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT film_id, baslik, afis_url, release_date
            FROM filmler
            WHERE release_date IS NOT NULL
            ORDER BY release_date DESC
            LIMIT 20
        """)
        movies = cursor.fetchall()
        return jsonify([{"film_id": m[0], "title": m[1], "poster_url": m[2], "release_date": m[3]} for m in movies])
    finally:
        cursor.close()
        conn.close()

@app.route("/api/genres")
def get_genres():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Veritabanı bağlantı hatası"}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT tur_id, ad FROM turler ORDER BY ad")
        genres = cursor.fetchall()
        result = [{"tur_id": g[0], "ad": g[1]} for g in genres]
        return jsonify(result)
    except Exception as e:
        print(f"Türler çekme hatası: {e}")
        return jsonify({"error": "Türler çekme hatası"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/movie_details/<int:movie_id>')
def movie_details(movie_id):
    conn = get_connection()
    if conn is None:
        return jsonify({"hata": "Veritabanı bağlantısı hatası"}), 500

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            SELECT 
                f.baslik, 
                f.ozet, 
                f.afis_url, 
                f.imdb_puani, 
                f.release_date,
                f.fragman_url  -- ⭐ FRAGMAN BİLGİSİ BURAYA EKLENDİ ⭐
            FROM 
                filmler f 
            WHERE 
                f.film_id = %s
        """, (movie_id,))
        movie = cursor.fetchone()

        if not movie:
            return jsonify({"hata": "Film bulunamadı"}), 404

        # --- Türleri Çek ---
        cursor.execute("""
            SELECT t.ad FROM film_turleri ft 
            JOIN turler t ON ft.tur_id = t.tur_id 
            WHERE ft.film_id = %s
        """, (movie_id,))
        genres = [row['ad'] for row in cursor.fetchall()]

        # --- Oyuncuları Çek ---
        cursor.execute("""
            SELECT o.ad FROM film_oyunculari fo 
            JOIN oyuncular o ON fo.oyuncu_id = o.oyuncu_id 
            WHERE fo.film_id = %s
            LIMIT 5
        """, (movie_id,))
        cast = [row['ad'] for row in cursor.fetchall()]

        # --- Yönetmenleri Çek ---
        cursor.execute("""
            SELECT y.ad FROM film_yonetmenleri fy 
            JOIN yonetmenler y ON fy.yonetmen_id = y.yonetmen_id 
            WHERE fy.film_id = %s
        """, (movie_id,))
        directors = [row['ad'] for row in cursor.fetchall()]

        movie['turler'] = genres
        movie['cast'] = cast
        movie['yonetmenler'] = ', '.join(directors) if directors else 'Bilinmiyor'
        
        # Eğer 'fragman_url' None ise veya yoksa (API'de bu kontrolü yapıyoruz)
        # JavaScript tarafı bunu güvenli bir şekilde işleyecektir.
        
        return jsonify(movie), 200

    except Exception as e:
        print(f"Film detayları çekilirken hata oluştu: {e}")
        return jsonify({"hata": "Sunucu hatası. Detaylar çekilemedi."}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/filter_movies")
def filter_movies():
    query = request.args.get('query', '')
    year = request.args.get('year', '')
    genre = request.args.get('genre', '')
    imdb_rating = request.args.get('imdb_rating', '')

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Veritabanı bağlantı hatası"}), 500
    
    cursor = conn.cursor()
    try:
        if genre:
            base_query = """
                SELECT DISTINCT f.film_id, f.baslik, f.afis_url, f.imdb_puani, f.release_date
                FROM filmler f
                INNER JOIN film_turleri ft ON f.film_id = ft.film_id
                WHERE ft.tur_id = %s
            """
            params = [int(genre)]
        else:
            base_query = """
                SELECT DISTINCT f.film_id, f.baslik, f.afis_url, f.imdb_puani, f.release_date
                FROM filmler f
                WHERE 1=1
            """
            params = []
        
        if query:
            base_query += " AND LOWER(f.baslik) LIKE %s"
            params.append(f'%{query.lower()}%')
        
        if year:
            base_query += " AND EXTRACT(YEAR FROM f.release_date) = %s"
            params.append(int(year))

        if imdb_rating:
            try:
                imdb_rating = float(imdb_rating)
                base_query += " AND f.imdb_puani >= %s"
                params.append(imdb_rating)
            except ValueError:
                print(f"Hata: Geçersiz IMDb puanı değeri: {imdb_rating}")
        
        base_query += " ORDER BY f.imdb_puani DESC NULLS LAST"
        
        cursor.execute(base_query, tuple(params))
        movies = cursor.fetchall()
        
        result = []
        for m in movies:
            release_date = m[4]
            year_val = release_date.year if release_date else None
            result.append({
                "film_id": m[0],
                "title": m[1],
                "poster_url": m[2],
                "rating": float(m[3]) if m[3] else None,
                "year": year_val
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Filtreleme hatası: {e}")
        return jsonify({"error": f"Filtreleme hatası: {e}"}), 500
    finally:
        cursor.close()
        conn.close()


# ✅ YENİ VERSİYON - EXCLUDE PARAMETRELİ
@app.route("/api/recommendations")
def get_user_recommendations():
    exclude_param = request.args.get('exclude', '')
    exclude_ids = [int(x) for x in exclude_param.split(',') if x.strip().isdigit()]
    
    if 'email' not in session:
        return jsonify([]), 200
    
    user_id = get_id_by_email(session['email'])
    if not user_id:
        return jsonify([]), 200

    conn = get_connection()
    if not conn:
        return jsonify({"hata": "Veritabanı bağlantı hatası"}), 500

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("SELECT film_id FROM favoriler WHERE kullanici_id = %s", (user_id,))
        watched = cur.fetchall()
        watched_ids = [w["film_id"] for w in watched]

        if not watched_ids:
            return jsonify([]), 200

        cur.execute("""
            SELECT DISTINCT kullanici_id
            FROM favoriler
            WHERE film_id = ANY(%s) AND kullanici_id != %s
        """, (watched_ids, user_id))
        similar_users = cur.fetchall()
        similar_ids = [u["kullanici_id"] for u in similar_users]

        if not similar_ids:
            return jsonify([]), 200

        all_exclude_ids = list(set(watched_ids + exclude_ids))
        
        cur.execute("""
            SELECT DISTINCT film_id
            FROM favoriler
            WHERE kullanici_id = ANY(%s) AND film_id != ALL(%s)
            LIMIT 20
        """, (similar_ids, all_exclude_ids))
        recs = cur.fetchall()
        rec_ids = [r["film_id"] for r in recs]

        if not rec_ids:
            return jsonify([]), 200

        cur.execute("""
            SELECT film_id, baslik, afis_url, imdb_puani, release_date
            FROM filmler
            WHERE film_id = ANY(%s)
            ORDER BY imdb_puani DESC
        """, (rec_ids,))
        movies = cur.fetchall()
        
        result = []
        for movie in movies:
            result.append({
                'film_id': movie['film_id'],
                'title': movie['baslik'],
                'poster_url': movie['afis_url'],
                'rating': float(movie['imdb_puani']) if movie['imdb_puani'] else None,
                'year': movie['release_date'].year if movie['release_date'] else None
            })
        
        return jsonify(result), 200

    except Exception as e:
        print(f"Recommendations API hatası: {e}")
        return jsonify([]), 200
    finally:
        cur.close()
        conn.close()

@app.route('/api/similar_movies/<int:movie_id>')
def get_similar_movies_ml(movie_id):
    """🎯 ML tabanlı öneri sistemi - Film detay sayfası için"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Film bilgilerini al
        cursor.execute("SELECT baslik, tmdb_id FROM filmler WHERE film_id = %s", (movie_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'error': 'Film bulunamadı'}), 404

        film_adi, current_tmdb_id = result
        print(f"🔍 '{film_adi}' için ML önerileri hesaplanıyor...")

        # Önceki önerileri exclude etmek için set oluştur
        exclude_ids = {int(current_tmdb_id)}

        # Önerileri al
        oneriler_df = get_recommendations(film_adi, exclude_tmdb_ids=exclude_ids, top_n=15)
        oneriler_df = oneriler_df.drop_duplicates(subset=['tmdb_id'])

        if oneriler_df.empty:
            conn.close()
            print("⚠️ Öneri sistemi bu film için öneri üretemedi.")
            return jsonify([])

        similar_movies = []
        for _, row in oneriler_df.iterrows():
            tmdb_id = row.get('tmdb_id')
            if not tmdb_id or pd.isna(tmdb_id) or int(tmdb_id) == int(current_tmdb_id):
                continue

            cursor.execute("""
                SELECT film_id, baslik, afis_url, imdb_puani 
                FROM filmler 
                WHERE tmdb_id = %s
            """, (int(tmdb_id),))
            movie_data = cursor.fetchone()

            if movie_data:
                similar_movies.append({
                    'id': movie_data[0],
                    'baslik': movie_data[1],
                    'afis_url': movie_data[2],
                    'imdb_puani': movie_data[3]
                })

        conn.close()
        print(f"✅ {len(similar_movies)} geçerli öneri bulundu.")
        return jsonify(similar_movies)

    except Exception as e:
        print(f"❌ ML öneri hatası: {e}")
        return jsonify({'error': str(e)}), 500

# ✅ YENİ VERSİYON - EXCLUDE PARAMETRELİ
@app.route("/api/recommendations_by_genre")
def get_recommendations_by_genre():
    exclude_param = request.args.get('exclude', '')
    exclude_ids = [int(x) for x in exclude_param.split(',') if x.strip().isdigit()]
    
    if 'email' not in session:
        return jsonify([]), 200
    
    user_id = get_id_by_email(session['email'])
    if not user_id:
        return jsonify([]), 200

    conn = get_connection()
    if not conn:
        return jsonify([]), 200

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT DISTINCT t.tur_id, t.ad, COUNT(*) as genre_count
            FROM favoriler fav
            JOIN film_turleri ft ON fav.film_id = ft.film_id
            JOIN turler t ON ft.tur_id = t.tur_id
            WHERE fav.kullanici_id = %s
            GROUP BY t.tur_id, t.ad
            ORDER BY genre_count DESC
            LIMIT 3
        """, (user_id,))
        
        favorite_genres = cur.fetchall()
        
        if not favorite_genres:
            return jsonify([]), 200
        
        genre_ids = [g['tur_id'] for g in favorite_genres]
        
        cur.execute("""
            SELECT film_id FROM favoriler WHERE kullanici_id = %s
        """, (user_id,))
        watched_ids = [row['film_id'] for row in cur.fetchall()]
        
        all_exclude_ids = list(set(watched_ids + exclude_ids)) if exclude_ids else watched_ids
        
        cur.execute("""
            SELECT DISTINCT f.film_id, f.baslik, f.afis_url, f.imdb_puani, f.release_date
            FROM filmler f
            JOIN film_turleri ft ON f.film_id = ft.film_id
            WHERE ft.tur_id = ANY(%s)
            AND f.film_id != ALL(%s)
            ORDER BY f.imdb_puani DESC NULLS LAST
            LIMIT 20
        """, (genre_ids, all_exclude_ids if all_exclude_ids else [0]))
        
        movies = cur.fetchall()
        
        result = []
        for movie in movies:
            result.append({
                'film_id': movie['film_id'],
                'title': movie['baslik'],
                'poster_url': movie['afis_url'],
                'rating': float(movie['imdb_puani']) if movie['imdb_puani'] else None,
                'year': movie['release_date'].year if movie['release_date'] else None
            })
        
        return jsonify(result), 200

    except Exception as e:
        print(f"Genre recommendations API hatası: {e}")
        return jsonify([]), 200
    finally:
        cur.close()
        conn.close()

# ✅ YENİ VERSİYON - EXCLUDE PARAMETRELİ
@app.route("/api/explore")
def explore_random_movies():
    exclude_param = request.args.get('exclude', '')
    exclude_ids = [int(x) for x in exclude_param.split(',') if x.strip().isdigit()]
    
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Veritabanı bağlantı hatası"}), 500

    cursor = conn.cursor()
    
    RANDOM_LIMIT = 20 
    
    try:
        if exclude_ids:
            cursor.execute("""
                SELECT film_id, baslik, afis_url
                FROM filmler
                WHERE afis_url IS NOT NULL 
                AND baslik IS NOT NULL 
                AND film_id != ALL(%s)
                ORDER BY RANDOM() 
                LIMIT %s
            """, (exclude_ids, RANDOM_LIMIT))
        else:
            cursor.execute("""
                SELECT film_id, baslik, afis_url
                FROM filmler
                WHERE afis_url IS NOT NULL AND baslik IS NOT NULL 
                ORDER BY RANDOM() 
                LIMIT %s
            """, (RANDOM_LIMIT,))
        
        movies = cursor.fetchall()
        random_movies = [
            {"film_id": movie[0], "title": movie[1], "poster_url": movie[2]} 
            for movie in movies
        ]
        return jsonify(random_movies)
    except Exception as e:
        print(f"Explore API hatası: {e}")
        return jsonify({"error": "Rastgele filmler alınamadı"}), 500
    finally:
        cursor.close()
        conn.close()
# api.py dosyanıza bu endpoint'leri ekleyin:

@app.route('/person-movies')
def person_movies_page():
    """Kişiye özel film listesi sayfası"""
    person_name = request.args.get('name')
    person_type = request.args.get('type')  # 'actor' veya 'director'
    return render_template('person-movies.html', person_name=person_name, person_type=person_type)

@app.route('/api/movies_by_actor/<string:actor_name>')
def get_movies_by_actor(actor_name):
    """Belirli bir oyuncunun filmlerini getir"""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Veritabanı bağlantı hatası"}), 500
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT DISTINCT f.film_id, f.baslik, f.afis_url, f.imdb_puani, f.release_date
            FROM filmler f
            JOIN film_oyunculari fo ON f.film_id = fo.film_id
            JOIN oyuncular o ON fo.oyuncu_id = o.oyuncu_id
            WHERE LOWER(o.ad) = LOWER(%s)
            ORDER BY f.imdb_puani DESC NULLS LAST
            LIMIT 50
        """, (actor_name,))
        
        movies = cursor.fetchall()
        
        result = []
        for movie in movies:
            result.append({
                'film_id': movie['film_id'],
                'title': movie['baslik'],
                'poster_url': movie['afis_url'],
                'rating': float(movie['imdb_puani']) if movie['imdb_puani'] else None,
                'year': movie['release_date'].year if movie['release_date'] else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Oyuncuya göre film çekme hatası: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/movies_by_director/<string:director_name>')
def get_movies_by_director(director_name):
    """Belirli bir yönetmenin filmlerini getir"""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Veritabanı bağlantı hatası"}), 500
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT DISTINCT f.film_id, f.baslik, f.afis_url, f.imdb_puani, f.release_date
            FROM filmler f
            JOIN film_yonetmenleri fy ON f.film_id = fy.film_id
            JOIN yonetmenler y ON fy.yonetmen_id = y.yonetmen_id
            WHERE LOWER(y.ad) = LOWER(%s)
            ORDER BY f.imdb_puani DESC NULLS LAST
            LIMIT 50
        """, (director_name,))
        
        movies = cursor.fetchall()
        
        result = []
        for movie in movies:
            result.append({
                'film_id': movie['film_id'],
                'title': movie['baslik'],
                'poster_url': movie['afis_url'],
                'rating': float(movie['imdb_puani']) if movie['imdb_puani'] else None,
                'year': movie['release_date'].year if movie['release_date'] else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Yönetmene göre film çekme hatası: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
# ============================================
# YORUM SİSTEMİ API ENDPOINT'LERİ
# ============================================

from flask import session, jsonify # Gerekli importlar

# Yorumları getir (Kullanıcının beğeni durumunu da kontrol eder)
@app.route('/api/yorumlar/<int:film_id>', methods=['GET'])
def yorumlar_getir(film_id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Giriş yapmış kullanıcının ID'sini al
        current_user_id = None
        if 'email' in session:
            # NOT: Bu sorgu, kullanicilar tablonuzdaki user_id'ye karşılık gelen email'i kullanmalıdır.
            cursor.execute("SELECT id FROM kullanicilar WHERE email = %s", (session['email'],))
            user_record = cursor.fetchone()
            if user_record:
                current_user_id = user_record[0]

        # 2. Ana Yorum Sorgusu
        cursor.execute("""
            SELECT y.id, y.user_id, y.yorum, y.tarih, y.begeni_sayisi, k.username
            FROM yorumlar y
            JOIN kullanicilar k ON y.user_id = k.id
            WHERE y.film_id = %s
            ORDER BY y.tarih DESC
        """, (film_id,))
        
        columns = [desc[0] for desc in cursor.description]
        yorumlar_list = []
        
        for row in cursor.fetchall():
            yorum = dict(zip(columns, row))
            # Tarih/Saat formatı düzeltmesi (Çözüm 3 için)
            if yorum.get('tarih'):
                 # Tarih objesini ISO formatında veya timestamp olarak döndürmek JS için en iyisidir
                 # JSON'a çevrildiğinde otomatik olarak string olur. (Burada bir değişiklik yapmaya gerek yok, JS'te formatlanır.)
                 pass

            yorum['kullanici_begendi'] = False # Varsayılan olarak beğenilmedi

            # 3. Eğer kullanıcı giriş yapmışsa, beğeni durumunu kontrol et
            if current_user_id:
                # yorum_begenileri tablosunu kontrol et
                cursor.execute(
                    "SELECT 1 FROM yorum_begenileri WHERE user_id = %s AND yorum_id = %s",
                    (current_user_id, yorum['id'])
                )
                if cursor.fetchone():
                    yorum['kullanici_begendi'] = True # Beğenilmiş!
            
            yorumlar_list.append(yorum)
        
        cursor.close()
        conn.close()
        
        print(f"✅ {len(yorumlar_list)} yorum getirildi - Film ID: {film_id}")
        return jsonify(yorumlar_list), 200
        
    except Exception as e:
        print(f"❌ Yorumlar getirme hatası: {e}")
        if conn:
            conn.close()
        return jsonify({'error': 'Yorumlar getirilemedi'}), 500

# Yorum ekle
@app.route('/api/yorum_ekle/<int:film_id>', methods=['POST'])
def yorum_ekle(film_id):
    print(f"\n{'='*50}")
    print(f"🎬 Yorum Ekleme - Film ID: {film_id}")
    
    if 'email' not in session:
        print("❌ Session'da email yok!")
        return jsonify({'error': 'Giriş yapmalısınız'}), 401
    
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        print(f"📝 Yorum: '{text[:50]}...'")
        
        if not text:
            return jsonify({'error': 'Yorum boş olamaz'}), 400
        
        if len(text) > 500:
            return jsonify({'error': 'Yorum 500 karakterden uzun olamaz'}), 400
        
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Veritabanı bağlantı hatası'}), 500
        
        cursor = conn.cursor()
        
        # Kullanıcı ID al
        cursor.execute("SELECT id FROM kullanicilar WHERE email = %s", (session['email'],))
        user_record = cursor.fetchone()
        
        if not user_record:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
        
        user_id = user_record[0]
        print(f"✅ Kullanıcı ID: {user_id}")
        
        # Yorum ekle (begeni_sayisi default 0)
        cursor.execute("""
            INSERT INTO yorumlar (user_id, film_id, yorum, begeni_sayisi, tarih)
            VALUES (%s, %s, %s, 0, NOW())
        """, (user_id, film_id, text))
        
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Yorum eklendi!")
        print(f"{'='*50}\n")
        
        return jsonify({'message': 'Yorum başarıyla eklendi!'}), 201
        
    except Exception as e:
        print(f"❌ HATA: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print(f"{'='*50}\n")
        return jsonify({'error': f'Yorum eklenemedi: {str(e)}'}), 500


# Yorum sil
@app.route('/api/yorum_sil/<int:yorum_id>', methods=['DELETE'])
def yorum_sil(yorum_id):
    if 'email' not in session:
        return jsonify({'error': 'Giriş yapmalısınız'}), 401
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Kullanıcı ID al
        cursor.execute("SELECT id FROM kullanicilar WHERE email = %s", (session['email'],))
        user_record = cursor.fetchone()
        
        if not user_record:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
        
        user_id = user_record[0]
        
        # Yorum sahibi mi kontrol et
        cursor.execute("SELECT user_id FROM yorumlar WHERE id = %s", (yorum_id,))
        yorum = cursor.fetchone()
        
        if not yorum:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Yorum bulunamadı'}), 404
        
        if yorum[0] != user_id:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Bu yorumu silme yetkiniz yok'}), 403
        
        # Yorumu sil
        cursor.execute("DELETE FROM yorumlar WHERE id = %s", (yorum_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Yorum silindi: ID={yorum_id}")
        return jsonify({'message': 'Yorum silindi'}), 200
        
    except Exception as e:
        print(f"❌ Yorum silme hatası: {e}")
        return jsonify({'error': 'Yorum silinemedi'}), 500


# Yorum düzenle
@app.route('/api/yorum_duzenle/<int:yorum_id>', methods=['PUT'])
def yorum_duzenle(yorum_id):
    if 'email' not in session:
        return jsonify({'error': 'Giriş yapmalısınız'}), 401
    
    try:
        data = request.get_json()
        yeni_text = data.get('text', '').strip()
        
        if not yeni_text:
            return jsonify({'error': 'Yorum boş olamaz'}), 400
        
        if len(yeni_text) > 500:
            return jsonify({'error': 'Yorum 500 karakterden uzun olamaz'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Kullanıcı ID al
        cursor.execute("SELECT id FROM kullanicilar WHERE email = %s", (session['email'],))
        user_record = cursor.fetchone()
        
        if not user_record:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
        
        user_id = user_record[0]
        
        # Yorum sahibi mi kontrol et
        cursor.execute("SELECT user_id FROM yorumlar WHERE id = %s", (yorum_id,))
        yorum = cursor.fetchone()
        
        if not yorum:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Yorum bulunamadı'}), 404
        
        if yorum[0] != user_id:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Bu yorumu düzenleme yetkiniz yok'}), 403
        
        # Yorumu güncelle (tarih güncellenmesin, sadece yorum metni)
        cursor.execute("""
            UPDATE yorumlar 
            SET yorum = %s
            WHERE id = %s
        """, (yeni_text, yorum_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Yorum güncellendi: ID={yorum_id}")
        return jsonify({'message': 'Yorum güncellendi'}), 200
        
    except Exception as e:
        print(f"❌ Yorum güncelleme hatası: {e}")
        return jsonify({'error': 'Yorum güncellenemedi'}), 500


# Yorum beğen/beğeniyi kaldır (Toggle Mantığı)
@app.route('/api/yorum_begeni/<int:yorum_id>', methods=['POST'])
def yorum_begeni(yorum_id):
    """Yorumu beğen/beğeniyi kaldır (Toggle)"""
    if 'email' not in session:
        return jsonify({'error': 'Giriş yapmalısınız'}), 401
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Kullanıcı ID Al
        cursor.execute("SELECT id FROM kullanicilar WHERE email = %s", (session['email'],))
        user_record = cursor.fetchone()
        
        if not user_record:
            return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
        
        user_id = user_record[0]
        
        # 1. Kullanıcının daha önce bu yorumu beğenip beğenmediğini kontrol et
        cursor.execute(
            "SELECT id FROM yorum_begenileri WHERE user_id = %s AND yorum_id = %s", 
            (user_id, yorum_id)
        )
        begeni_kaydi = cursor.fetchone()
        
        mesaj = ""
        is_liked = False
        
        if begeni_kaydi:
            # Beğeni varsa: Beğeniyi Kaldır (DELETE)
            cursor.execute(
                "DELETE FROM yorum_begenileri WHERE id = %s", 
                (begeni_kaydi[0],)
            )
            
            # Yorumun genel beğeni sayısını azalt
            cursor.execute(
                "UPDATE yorumlar SET begeni_sayisi = begeni_sayisi - 1 WHERE id = %s", 
                (yorum_id,)
            )
            mesaj = "Beğeni kaldırıldı"
            is_liked = False # Yeni durum: Beğenilmedi
        else:
            # Beğeni yoksa: Beğeniyi Ekle (INSERT)
            cursor.execute(
                "INSERT INTO yorum_begenileri (user_id, yorum_id, tarih) VALUES (%s, %s, NOW())", 
                (user_id, yorum_id)
            )
            
            # Yorumun genel beğeni sayısını artır
            cursor.execute(
                "UPDATE yorumlar SET begeni_sayisi = begeni_sayisi + 1 WHERE id = %s", 
                (yorum_id,)
            )
            mesaj = "Beğenildi"
            is_liked = True # Yeni durum: Beğenildi
            
        conn.commit()
        
        # 2. Güncel beğeni sayısını al ve döndür
        cursor.execute("SELECT begeni_sayisi FROM yorumlar WHERE id = %s", (yorum_id,))
        result = cursor.fetchone()
        
        if not result:
             # Yorum silinmiş olabilir, rollback yapmaya gerek yok
            return jsonify({'error': 'Yorum bulunamadı'}), 404
            
        yeni_begeni = result[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': mesaj,
            'begeni_sayisi': yeni_begeni,
            'is_liked': is_liked # Frontend'in simgeyi güncellemesi için kritik
        }), 200
        
    except Exception as e:
        print(f"❌ Beğeni/Beğeni Kaldırma Hatası: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': 'İşlem sırasında bir hata oluştu'}), 500
    
from itsdangerous import URLSafeTimedSerializer

s = URLSafeTimedSerializer(app.secret_key)
from datetime import timedelta

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # 30 gün kalıcı

@app.route("/api/forgot_password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"hata": "E-posta adresi gerekli."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"hata": "Veritabanı bağlantı hatası."}), 500

    cursor = conn.cursor()
    try:
        # Kullanıcı var mı kontrol et
        cursor.execute("SELECT id FROM kullanicilar WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"hata": "Bu e-posta adresiyle kayıtlı kullanıcı bulunamadı."}), 404

        # Token oluştur
        token = s.dumps(email, salt="password-reset-salt")

        # Şifre sıfırlama linki oluştur
        reset_url = f"http://localhost:5000/sifre_sifirla/{token}"

        # Mail gönder
        msg = Message("🔑 Şifre Sıfırlama Talebi", recipients=[email])
        msg.body = f"""
Merhaba,
Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:
{reset_url}

Bu bağlantı 30 dakika boyunca geçerlidir.
Eğer bu talebi siz oluşturmadıysanız, bu e-postayı dikkate almayabilirsiniz.
"""
        mail.send(msg)

        return jsonify({"mesaj": "Şifre sıfırlama bağlantısı e-posta adresinize gönderildi."}), 200

    except Exception as e:
        return jsonify({"hata": f"Sunucu hatası: {e}"}), 500
    finally:
        cursor.close()
        conn.close()
@app.route("/sifre_sifirla/<token>", methods=["GET", "POST"])
def sifre_sifirla(token):
    try:
        email = s.loads(token, salt="password-reset-salt", max_age=1800)  # 30 dakika
    except Exception:
        return "Token geçersiz veya süresi dolmuş.", 400

    if request.method == "GET":
        # HTML sayfası göster
        return render_template("sifre_sifirla.html", email=email)

    # POST - yeni şifre al
    data = request.get_json()
    yeni_sifre = data.get("sifre")

    if not yeni_sifre:
        return jsonify({"hata": "Yeni şifre gerekli."}), 400

    hashed = bcrypt.generate_password_hash(yeni_sifre).decode('utf-8')

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE kullanicilar SET sifre = %s WHERE email = %s", (hashed, email))
        conn.commit()
        return jsonify({"mesaj": "Şifre başarıyla güncellendi."}), 200
    except Exception as e:
        return jsonify({"hata": f"Bir hata oluştu: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    initialize_recommendation_system()
    app.run(debug=True)

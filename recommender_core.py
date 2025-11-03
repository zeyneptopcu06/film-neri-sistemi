import pandas as pd
from sqlalchemy import create_engine
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from functools import reduce
import numpy as np
import os
import pickle
from pathlib import Path

DATABASE_URL = os.environ.get('DATABASE_URL')
CACHE_DIR = Path("/tmp/rec_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Global değişkenler - lazy loading için
_tfidf_matrix = None
_df_final = None
_indices = None
_tfidf_vectorizer = None

def get_db_engine():
    """SQLAlchemy engine ile veritabanı bağlantısı kurar."""
    if not DATABASE_URL:
        print("HATA: DATABASE_URL ortam değişkeni bulunamadı.")
        return None
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
        return engine
    except Exception as e:
        print(f"Veritabanı engine oluşturulamadı: {e}")
        return None


def fetch_data_from_db():
    """Veritabanından filmleri ve ilişkili tüm verileri çeker."""
    engine = get_db_engine()
    if engine is None:
        return None, None, None, None

    try:
        query_main = """
        SELECT film_id, tmdb_id, baslik, ozet, imdb_puani
        FROM filmler
        WHERE ozet IS NOT NULL AND imdb_puani IS NOT NULL;
        """
        df_filmler = pd.read_sql(query_main, engine)

        query_genres = "SELECT ft.film_id, t.ad FROM film_turleri ft JOIN turler t ON ft.tur_id = t.tur_id;"
        df_turler = pd.read_sql(query_genres, engine)

        query_cast = "SELECT fo.film_id, o.ad FROM film_oyunculari fo JOIN oyuncular o ON fo.oyuncu_id = o.oyuncu_id;"
        df_oyunculari = pd.read_sql(query_cast, engine)

        query_director = "SELECT fy.film_id, y.ad FROM film_yonetmenleri fy JOIN yonetmenler y ON fy.yonetmen_id = y.yonetmen_id;"
        df_yonetmenler = pd.read_sql(query_director, engine)

        engine.dispose()  # Bağlantıyı kapat
        return df_filmler, df_turler, df_oyunculari, df_yonetmenler

    except Exception as e:
        print(f"Veritabanı sorgu hatası: {e}") 
        return None, None, None, None


def create_soup(x):
    """
    Filmin özelliklerini dengeli şekilde birleştirir.
    İYİLEŞTİRME: Türlere ve kaliteye daha fazla ağırlık verildi.
    """
    cast_list = [name.replace(" ", "") for name in str(x["cast_str"]).split() if name]
    director_list = [name.replace(" ", "") for name in str(x["director_str"]).split() if name]

    cast_str = " ".join(cast_list[:4])
    director_str = " ".join(director_list)

    # İYİLEŞTİRME: Ağırlıklar optimize edildi
    weighted_summary = (str(x["ozet"]) + " ") * 2        # 3'ten 2'ye düşürüldü
    weighted_director = (director_str + " ") * 3
    weighted_genres = (str(x["genres_str"]) + " ") * 4  # 2'den 4'e artırıldı ⬆️

    return f"{weighted_summary} {weighted_director} {weighted_genres} {cast_str}"


def load_or_compute_data():
    """Cache'den yükler veya hesaplar - Bellek optimizasyonlu."""
    global _tfidf_matrix, _df_final, _indices, _tfidf_vectorizer
    
    cache_file = CACHE_DIR / "rec_data_v2.pkl"  # v2 - yeni cache versiyonu
    
    # Cache varsa yükle
    if cache_file.exists():
        try:
            print("📦 Cache'den yükleniyor...")
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                _tfidf_matrix = data['tfidf_matrix']
                _df_final = data['df_final']
                _indices = data['indices']
                _tfidf_vectorizer = data['tfidf_vectorizer']
            print(f"✅ Cache yüklendi! ({len(_df_final)} film)")
            return True
        except Exception as e:
            print(f"⚠️ Cache okuma hatası: {e}")
    
    # Hesapla
    print("🔄 Veriler hesaplanıyor...")
    df_filmler, df_turler, df_oyunculari, df_yonetmenler = fetch_data_from_db()
    
    if df_filmler is None or df_filmler.empty:
        print("❌ Veri yüklenemedi!")
        return False

    print(f"Veritabanından çekilen film sayısı: {len(df_filmler)}")

    # Gruplandırma
    df_turler_grup = df_turler.groupby("film_id")["ad"].apply(lambda x: " ".join(x)).reset_index().rename(columns={"ad":"genres_str"})
    df_oyuncular_grup = df_oyunculari.groupby("film_id")["ad"].apply(lambda x: " ".join(x)).reset_index().rename(columns={"ad":"cast_str"})
    df_yonetmenler_grup = df_yonetmenler.groupby("film_id")["ad"].apply(lambda x: " ".join(x)).reset_index().rename(columns={"ad":"director_str"})

    # Belleği temizle
    del df_turler, df_oyunculari, df_yonetmenler

    data_frames = [df_filmler, df_turler_grup, df_oyuncular_grup, df_yonetmenler_grup]
    _df_final = reduce(lambda left,right: pd.merge(left, right, on="film_id", how="left"), data_frames)
    _df_final = _df_final.fillna("")
    _df_final["soup"] = _df_final.apply(create_soup, axis=1)

    # Belleği temizle
    del data_frames, df_filmler, df_turler_grup, df_oyuncular_grup, df_yonetmenler_grup

    print("✅ Özellik birleştirme tamamlandı.")

    # TF-IDF (sparse matrix kullanıyor - bellek dostu)
    _tfidf_vectorizer = TfidfVectorizer(
        stop_words="english", 
        max_features=3000,
        ngram_range=(1, 2), 
        min_df=2,
        dtype=np.float32
    )
    _tfidf_matrix = _tfidf_vectorizer.fit_transform(_df_final["soup"])
    print(f"TF-IDF Matris Boyutu: {_tfidf_matrix.shape}")

    _df_final = _df_final.reset_index(drop=True)
    _indices = pd.Series(_df_final.index, index=_df_final["baslik"])

    # Soup sütununu sil (artık gerekli değil)
    _df_final = _df_final.drop(columns=['soup'])

    # Cache'e kaydet
    try:
        print("💾 Cache'e kaydediliyor...")
        with open(cache_file, 'wb') as f:
            pickle.dump({
                'tfidf_matrix': _tfidf_matrix,
                'df_final': _df_final,
                'indices': _indices,
                'tfidf_vectorizer': _tfidf_vectorizer
            }, f)
        print("✅ Cache kaydedildi!")
    except Exception as e:
        print(f"⚠️ Cache kaydetme hatası: {e}")

    print(f"✅ Öneri sistemi hazır! ({len(_df_final)} film)")
    return True


def get_data():
    """Lazy loading - sadece gerektiğinde yükle."""
    global _tfidf_matrix, _df_final, _indices
    
    if _df_final is None:
        load_or_compute_data()
    
    return _tfidf_matrix, _df_final, _indices


def get_recommendations(title, exclude_tmdb_ids=None, top_n=5, max_per_genre=3):
    """
    Bellek optimizasyonlu öneri fonksiyonu.
    İYİLEŞTİRME: Skor hesaplaması ve max_per_genre değiştirildi.
    """
    tfidf_matrix, df_final, indices = get_data()
    
    if exclude_tmdb_ids is None:
        exclude_tmdb_ids = set()

    try:
        idx = indices[title]
    except KeyError:
        return pd.DataFrame()

    source_movie = df_final.iloc[idx]
    source_tmdb_id = int(source_movie["tmdb_id"])
    source_genres = set(str(source_movie["genres_str"]).split())
    exclude_tmdb_ids = exclude_tmdb_ids.union({source_tmdb_id})

    # Sadece bu film için cosine similarity hesapla
    source_vector = tfidf_matrix[idx:idx+1]
    sim_scores = cosine_similarity(source_vector, tfidf_matrix).flatten()
    
    # En yüksek 500'ü al
    top_indices = np.argpartition(sim_scores, -501)[-501:]
    top_indices = top_indices[np.argsort(-sim_scores[top_indices])]
    
    # İlk indexi atla (kendisi)
    top_indices = top_indices[1:]
    
    candidates_df = df_final.iloc[top_indices].copy()
    candidates_df["similarity_score"] = sim_scores[top_indices]
    
    candidates_df = candidates_df[~candidates_df["tmdb_id"].isin(exclude_tmdb_ids)]
    candidates_df = candidates_df.drop_duplicates(subset=["tmdb_id", "baslik"])

    if candidates_df.empty:
        return pd.DataFrame()

    candidates_df["genre_similarity"] = candidates_df["genres_str"].apply(
        lambda g: len(set(str(g).split()) & source_genres) / max(len(set(str(g).split()) | source_genres), 1)
    )
    candidates_df["quality_score"] = candidates_df["imdb_puani"] / 10.0
    
    # İYİLEŞTİRME: Skor ağırlıkları optimize edildi
    candidates_df["final_score"] = (
        candidates_df["similarity_score"]*0.40 +     # 0.6'dan 0.50'ye
        candidates_df["genre_similarity"]*0.40 +     # 0.25'ten 0.30'a ⬆️
        candidates_df["quality_score"]*0.20          # 0.15'ten 0.20'ye ⬆️
    )

    selected_movies = []
    genre_count = {}
    for _, row in candidates_df.sort_values("final_score", ascending=False).iterrows():
        movie_genres = set(str(row["genres_str"]).split())
        if max_per_genre is not None and any(genre_count.get(g,0) >= max_per_genre for g in movie_genres):
            continue

        selected_movies.append(row)
        for g in movie_genres:
            genre_count[g] = genre_count.get(g,0)+1
        exclude_tmdb_ids.add(int(row["tmdb_id"]))

        if len(selected_movies) >= top_n:
            break

    if len(selected_movies) < top_n:
        print(f"⚠️ Uyarı: Sadece {len(selected_movies)} öneri bulundu.")

    return pd.DataFrame(selected_movies).head(top_n)


def get_recommendations_by_genre(user_favorite_genres, exclude_tmdb_ids=None, top_n=15):
    """
    Türe göre öneri.
    İYİLEŞTİRME: Skor ağırlıkları optimize edildi.
    """
    _, df_final, _ = get_data()
    
    if exclude_tmdb_ids is None:
        exclude_tmdb_ids = set()

    def has_favorite_genre(genres_str):
        movie_genres = set(str(genres_str).split())
        return len(movie_genres & set(user_favorite_genres)) > 0

    candidates = df_final[df_final["genres_str"].apply(has_favorite_genre)].copy()
    candidates = candidates[~candidates["tmdb_id"].isin(exclude_tmdb_ids)]

    if len(candidates) == 0:
        return pd.DataFrame()

    def calculate_match_score(genres_str):
        movie_genres = set(str(genres_str).split())
        match_count = len(movie_genres & set(user_favorite_genres))
        return match_count / len(user_favorite_genres) if len(user_favorite_genres) > 0 else 0

    candidates["genre_match_score"] = candidates["genres_str"].apply(calculate_match_score)
    candidates["quality_score"] = candidates["imdb_puani"] / 10.0
    
    # İYİLEŞTİRME: Kaliteye biraz daha ağırlık
    candidates["final_score"] = candidates["genre_match_score"]*0.65 + candidates["quality_score"]*0.35  # 0.70/0.30'dan 0.65/0.35'e

    candidates = candidates.sort_values("final_score", ascending=False)
    selected = []
    genre_count = {}
    for _, row in candidates.iterrows():
        if len(selected) >= top_n:
            break
        movie_genres = set(str(row["genres_str"]).split())
        genre_overlap = sum(genre_count.get(g,0) for g in movie_genres)
        if genre_overlap < 3:
            selected.append(row)
            for g in movie_genres:
                genre_count[g] = genre_count.get(g,0)+1

    result_df = pd.DataFrame(selected)
    if len(result_df) == 0:
        return result_df

    return result_df[["tmdb_id","baslik","imdb_puani","genres_str","final_score"]].head(top_n)


def initialize_recommendation_system():
    """Öneri sistemini başlatır (opsiyonel - lazy loading otomatik çalışır)."""
    return load_or_compute_data()


def clear_cache():
    """Cache'i temizler."""
    cache_file = CACHE_DIR / "rec_data_v2.pkl"
    if cache_file.exists():
        cache_file.unlink()
        print("🗑️ Cache temizlendi!")
    
    # Eski cache'i de temizle
    old_cache = CACHE_DIR / "rec_data.pkl"
    if old_cache.exists():
        old_cache.unlink()
        print("🗑️ Eski cache temizlendi!")
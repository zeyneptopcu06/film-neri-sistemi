import pandas as pd
import psycopg2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from functools import reduce
import numpy as np
import os

DATABASE_URL = os.environ.get('DATABASE_URL')

# --- 1. ADIM: VERİ ÇEKME FONKSİYONU ---
def get_db_connection():
    """DATABASE_URL kullanarak veritabanı bağlantısı kurar."""
    if not DATABASE_URL:
        print("HATA: DATABASE_URL ortam değişkeni bulunamadı. Bağlantı kurulamıyor.")
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL, client_encoding='utf8')
        return conn
    except psycopg2.DatabaseError as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None


def fetch_data_from_db():
    """Veritabanından filmleri ve ilişkili tüm verileri çeker."""
    
    conn = get_db_connection()
    
    if conn is None:
        return None, None, None, None

    try:
        query_main = """
        SELECT film_id, tmdb_id, baslik, ozet, imdb_puani
        FROM filmler
        WHERE ozet IS NOT NULL AND imdb_puani IS NOT NULL;
        """
        df_filmler = pd.read_sql(query_main, conn)

        query_genres = "SELECT ft.film_id, t.ad FROM film_turleri ft JOIN turler t ON ft.tur_id = t.tur_id;"
        df_turler = pd.read_sql(query_genres, conn)

        query_cast = "SELECT fo.film_id, o.ad FROM film_oyunculari fo JOIN oyuncular o ON fo.oyuncu_id = o.oyuncu_id;"
        df_oyunculari = pd.read_sql(query_cast, conn)

        query_director = "SELECT fy.film_id, y.ad FROM film_yonetmenleri fy JOIN yonetmenler y ON fy.yonetmen_id = y.yonetmen_id;"
        df_yonetmenler = pd.read_sql(query_director, conn)

        conn.close()
        return df_filmler, df_turler, df_oyunculari, df_yonetmenler

    except Exception as e:
        print(f"Veritabanı bağlantı/sorgu hatası: {e}") 
        if conn: 
            conn.close()
        return None, None, None, None


def create_soup(x):
    """
    Filmin özelliklerini dengeli şekilde birleştirir.
    """
    cast_list = [name.replace(" ", "") for name in x["cast_str"].split() if name]
    director_list = [name.replace(" ", "") for name in x["director_str"].split() if name]

    cast_str = " ".join(cast_list[:4])  # İlk 4 oyuncu
    director_str = " ".join(director_list)

    # AĞIRLIKLANDIRMA:
    weighted_summary = (x["ozet"] + " ") * 3
    weighted_director = (director_str + " ") * 3
    weighted_genres = (x["genres_str"] + " ") * 2

    return f"{weighted_summary} {weighted_director} {weighted_genres} {cast_str}"


# --- 2. ADIM: VERİ HAZIRLIK ---

df_filmler, df_turler, df_oyunculari, df_yonetmenler = fetch_data_from_db()

if df_filmler is None:
    print("Veritabanı bağlantısı kurulamadığı için uygulama kapatılıyor.")
    exit() 

if df_filmler.empty:
    print("Veritabanından çekilen film sayısı 0 olduğu için uygulama kapatılıyor.")
    exit()

print(f"Veritabanından çekilen film sayısı: {len(df_filmler)}")

# Gruplandırma ve birleştirme
df_turler_grup = (
    df_turler.groupby("film_id")["ad"]
    .apply(lambda x: " ".join(x))
    .reset_index()
    .rename(columns={"ad": "genres_str"})
)

df_oyuncular_grup = (
    df_oyunculari.groupby("film_id")["ad"]
    .apply(lambda x: " ".join(x))
    .reset_index()
    .rename(columns={"ad": "cast_str"})
)

df_yonetmenler_grup = (
    df_yonetmenler.groupby("film_id")["ad"]
    .apply(lambda x: " ".join(x))
    .reset_index()
    .rename(columns={"ad": "director_str"})
)

data_frames = [df_filmler, df_turler_grup, df_oyuncular_grup, df_yonetmenler_grup]

df_final = reduce(
    lambda left, right: pd.merge(left, right, on="film_id", how="left"), data_frames
)
df_final = df_final.fillna("")

df_final["soup"] = df_final.apply(create_soup, axis=1)

print("✅ Özellik birleştirme tamamlandı.")

# --- 3. ADIM: VEKTÖRLEŞTİRME ---

tfidf = TfidfVectorizer(
    stop_words="english", max_features=15000, ngram_range=(1, 2), min_df=2
)

tfidf_matrix = tfidf.fit_transform(df_final["soup"])
print(f"TF-IDF Matris Boyutu: {tfidf_matrix.shape}")

cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
print(f"✅ Cosine Similarity Boyutu: {cosine_sim.shape}")

df_final = df_final.reset_index(drop=True)
indices = pd.Series(df_final.index, index=df_final["baslik"])


# --- 4. ADIM: ÖNERİ FONKSİYONU ---
def get_recommendations(
    title,
    cosine_sim=cosine_sim,
    df_final=df_final,
    indices=indices,
    exclude_tmdb_ids=None,
    top_n=5,
    max_per_genre=2,
):
    if exclude_tmdb_ids is None:
        exclude_tmdb_ids = set()

    try:
        idx = indices[title]
    except KeyError:
        return pd.DataFrame()

    source_movie = df_final.iloc[idx]
    source_tmdb_id = int(source_movie["tmdb_id"])
    source_genres = set(source_movie["genres_str"].split())

    exclude_tmdb_ids = exclude_tmdb_ids.union({source_tmdb_id})

    # Benzer filmleri al
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:501]  # 500 benzer film havuzu

    candidates_df = df_final.iloc[[i[0] for i in sim_scores]].copy()
    candidates_df = candidates_df[~candidates_df["tmdb_id"].isin(exclude_tmdb_ids)]
    candidates_df = candidates_df.drop_duplicates(subset=["tmdb_id", "baslik"])

    if candidates_df.empty:
        return pd.DataFrame()

    # Genre ve kalite skoru
    candidates_df["genre_similarity"] = candidates_df["genres_str"].apply(
        lambda g: len(set(g.split()) & source_genres)
        / max(len(set(g.split()) | source_genres), 1)
    )
    candidates_df["quality_score"] = candidates_df["imdb_puani"] / 10.0
    candidates_df["similarity_score"] = [
        sim_scores[i][1] for i in range(len(candidates_df))
    ]

    candidates_df["final_score"] = (
        candidates_df["similarity_score"] * 0.6
        + candidates_df["genre_similarity"] * 0.25
        + candidates_df["quality_score"] * 0.15
    )

    # Seçim
    selected_movies = []
    genre_count = {}

    for _, row in candidates_df.sort_values("final_score", ascending=False).iterrows():
        movie_genres = set(row["genres_str"].split())
        if max_per_genre is not None and any(
            genre_count.get(g, 0) >= max_per_genre for g in movie_genres
        ):
            continue

        selected_movies.append(row)
        for g in movie_genres:
            genre_count[g] = genre_count.get(g, 0) + 1
        exclude_tmdb_ids.add(int(row["tmdb_id"]))

        if len(selected_movies) >= top_n:
            break

    if len(selected_movies) < top_n:
        print(f"⚠️ Uyarı: Sadece {len(selected_movies)} öneri bulundu.")

    return pd.DataFrame(selected_movies).head(top_n)


def get_recommendations_by_genre(user_favorite_genres, exclude_tmdb_ids=None, top_n=15):
    """
    TÜRE GÖRE ÖNERİLER - Kullanıcının favori türlerine göre film önerir.
    """
    if exclude_tmdb_ids is None:
        exclude_tmdb_ids = set()

    def has_favorite_genre(genres_str):
        movie_genres = set(genres_str.split())
        return len(movie_genres & set(user_favorite_genres)) > 0

    candidates = df_final[df_final["genres_str"].apply(has_favorite_genre)].copy()
    candidates = candidates[~candidates["tmdb_id"].isin(exclude_tmdb_ids)]

    if len(candidates) == 0:
        return pd.DataFrame()

    def calculate_match_score(genres_str):
        movie_genres = set(genres_str.split())
        match_count = len(movie_genres & set(user_favorite_genres))
        return match_count / len(user_favorite_genres) if len(user_favorite_genres) > 0 else 0

    candidates["genre_match_score"] = candidates["genres_str"].apply(calculate_match_score)
    candidates["quality_score"] = candidates["imdb_puani"] / 10.0

    candidates["final_score"] = (
        candidates["genre_match_score"] * 0.70 + candidates["quality_score"] * 0.30
    )

    candidates = candidates.sort_values("final_score", ascending=False)
    selected = []
    genre_count = {}

    for _, row in candidates.iterrows():
        if len(selected) >= top_n:
            break

        movie_genres = set(row["genres_str"].split())
        genre_overlap = sum(genre_count.get(g, 0) for g in movie_genres)

        if genre_overlap < 3:
            selected.append(row)
            for g in movie_genres:
                genre_count[g] = genre_count.get(g, 0) + 1

    result_df = pd.DataFrame(selected)
    if len(result_df) == 0:
        return result_df

    return result_df[["tmdb_id", "baslik", "imdb_puani", "genres_str", "final_score"]].head(top_n)


def initialize_recommendation_system():
    """Öneri sistemini başlatır - Uygulama başlangıcında çağrılır."""
    global cosine_sim, df_final, indices

    print("🔄 Öneri sistemi başlatılıyor...")

    df_filmler, df_turler, df_oyunculari, df_yonetmenler = fetch_data_from_db()

    if df_filmler is None:
        print("❌ Veritabanı bağlantısı başarısız!")
        return False

    df_turler_grup = (
        df_turler.groupby("film_id")["ad"]
        .apply(lambda x: " ".join(x))
        .reset_index()
        .rename(columns={"ad": "genres_str"})
    )
    df_oyuncular_grup = (
        df_oyunculari.groupby("film_id")["ad"]
        .apply(lambda x: " ".join(x))
        .reset_index()
        .rename(columns={"ad": "cast_str"})
    )
    df_yonetmenler_grup = (
        df_yonetmenler.groupby("film_id")["ad"]
        .apply(lambda x: " ".join(x))
        .reset_index()
        .rename(columns={"ad": "director_str"})
    )

    data_frames = [df_filmler, df_turler_grup, df_oyuncular_grup, df_yonetmenler_grup]
    df_final = reduce(
        lambda left, right: pd.merge(left, right, on="film_id", how="left"), data_frames
    )
    df_final = df_final.fillna("")
    df_final["soup"] = df_final.apply(create_soup, axis=1)

    tfidf = TfidfVectorizer(
        stop_words="english", max_features=15000, ngram_range=(1, 2), min_df=2
    )

    tfidf_matrix = tfidf.fit_transform(df_final["soup"])
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    df_final = df_final.reset_index(drop=True)
    indices = pd.Series(df_final.index, index=df_final["baslik"])

    print(f"✅ Öneri sistemi hazır! ({len(df_final)} film)")
    return True
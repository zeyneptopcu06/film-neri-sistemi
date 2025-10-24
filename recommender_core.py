import pandas as pd
import psycopg2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from functools import reduce
import numpy as np
import os # Ortam değişkenlerini okumak için eklendi

DATABASE_URL = os.environ.get('DATABASE_URL')



# --- 1. ADIM: VERİ ÇEKME FONKSİYONU ---
def get_db_connection():
    """DATABASE_URL kullanarak veritabanı bağlantısı kurar."""
    if not DATABASE_URL:
        print("HATA: DATABASE_URL ortam değişkeni bulunamadı. Bağlantı kurulamıyor.")
        return None
    try:
        # psycopg2, tek bir bağlantı dizesini (DATABASE_URL) kabul eder.
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.DatabaseError as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None


def fetch_data_from_db():
    """Veritabanından filmleri ve ilişkili tüm verileri çeker."""
    
    # KRİTİK DÜZELTME: Yeni bağlantı fonksiyonunu kullan
    conn = get_db_connection()
    
    if conn is None:
        return None, None, None, None # Bağlantı kurulamadı

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
        # Uygulama loglarında bu hatanın görünmesi için print bırakıldı
        print(f"Veritabanı bağlantı/sorgu hatası: {e}") 
        if conn: conn.close()
        return None, None, None, None



def create_soup(x):
    """
    Filmin özelliklerini dengeli şekilde birleştirir.
    Hata düzeltmesi: Artık birleştirilmiş (grup) sütun adlarını kullanıyoruz.
    """
    # DÜZELTME: x["cast"] yerine x["cast_str"] kullanıldı
    cast_list = [name.replace(" ", "") for name in x["cast_str"].split() if name]
    # DÜZELTME: x["director"] yerine x["director_str"] kullanıldı
    director_list = [name.replace(" ", "") for name in x["director_str"].split() if name]

    cast_str = " ".join(cast_list[:4])  # İlk 4 oyuncu yeterli
    director_str = " ".join(director_list)

    # İYİLEŞTİRİLMİŞ AĞIRLIKLANDIRMA:
    weighted_summary = (x["ozet"] + " ") * 3
    weighted_director = (director_str + " ") * 3
    # DÜZELTME: x["genres"] yerine x["genres_str"] kullanıldı
    weighted_genres = (x["genres_str"] + " ") * 2

    return f"{weighted_summary} {weighted_director} {weighted_genres} {cast_str}"


# --- 2. ADIM: VERİ HAZIRLIK ---

# İSİM DÜZELTME: df_oyuncular yerine df_oyunculari kullanıldı
df_filmler, df_turler, df_oyunculari, df_yonetmenler = fetch_data_from_db()

if df_filmler is None:
    # Eğer veritabanı bağlantısı kurulamadıysa, uygulamayı sonlandır
    print("Veritabanı bağlantısı kurulamadığı için uygulama kapatılıyor.")
    exit() 

if df_filmler.empty:
    print("Veritabanından çekilen film sayısı 0 olduğu için uygulama kapatılıyor.")
    exit()

print(f"Veritabanından çekilen film sayısı: {len(df_filmler)}")


# Hata düzeltmesi: .rename(columns) aşamasında yeni ve tutarlı sütun adları kullanıldı.
df_turler_grup = (
    df_turler.groupby("film_id")["ad"]
    .apply(lambda x: " ".join(x))
    .reset_index()
    .rename(columns={"ad": "genres_str"}) # 'genres' yerine 'genres_str' kullanıldı
)
df_oyuncular_grup = (
    df_oyunculari.groupby("film_id")["ad"] # df_oyuncular yerine df_oyunculari kullanıldı
    .apply(lambda x: " ".join(x))
    .reset_index()
    .rename(columns={"ad": "cast_str"}) # 'cast' yerine 'cast_str' kullanıldı
)
df_yonetmenler_grup = (
    df_yonetmenler.groupby("film_id")["ad"]
    .apply(lambda x: " ".join(x))
    .reset_index()
    .rename(columns={"ad": "director_str"}) # 'director' yerine 'director_str' kullanıldı
)

# Yeni sütun adlarını kullanmak için df_oyuncular'daki isim hatası düzeltildi
data_frames = [df_filmler, df_turler_grup, df_oyuncular_grup, df_yonetmenler_grup]

# Hata düzeltmesi: Boş değerler (NaN) yerine boş string ('' ) atandı.
# Bu, .apply(create_soup) içinde .split() metodunun hata vermesini engeller.
df_final = reduce(
    lambda left, right: pd.merge(left, right, on="film_id", how="left"), data_frames
)
df_final = df_final.fillna("") 

# Bu satır artık doğru çalışmalı:
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

df_final = df_final.reset_index()
indices = pd.Series(df_final.index, index=df_final["baslik"])
# --- 4. ADIM: İYİLEŞTİRİLMİŞ ÖNERİ FONKSİYONU ---
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
    source_genres = set(source_movie["genres"].split())

    exclude_tmdb_ids = exclude_tmdb_ids.union({source_tmdb_id})

    # Benzer filmleri al - havuzu genişlettik
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:501]  # 500 benzer film havuzu

    candidates_df = df_final.iloc[[i[0] for i in sim_scores]].copy()
    candidates_df = candidates_df[~candidates_df["tmdb_id"].isin(exclude_tmdb_ids)]
    candidates_df = candidates_df.drop_duplicates(subset=["tmdb_id", "baslik"])

    if candidates_df.empty:
        return pd.DataFrame()

    # Genre ve kalite skoru
    candidates_df["genre_similarity"] = candidates_df["genres"].apply(
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

    # --- Seçim ---
    selected_movies = []
    genre_count = {}

    for _, row in candidates_df.sort_values("final_score", ascending=False).iterrows():
        movie_genres = set(row["genres"].split())
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
        print(
            f"⚠️ Uyarı: Sadece {len(selected_movies)} öneri bulundu, yeterli film yok."
        )

    return pd.DataFrame(selected_movies).head(top_n)


def get_recommendations_by_genre(user_favorite_genres, exclude_tmdb_ids=None, top_n=15):
    """
    TÜRE GÖRE ÖNERİLER - Kullanıcının favori türlerine göre film önerir.

    Args:
        user_favorite_genres: Liste - Kullanıcının favori türleri ['Drama', 'Crime', ...]
        exclude_tmdb_ids: Set - Dışlanacak film ID'leri
        top_n: Kaç film döndürülecek
    """
    if exclude_tmdb_ids is None:
        exclude_tmdb_ids = set()

    # Favori türleri içeren filmleri filtrele
    def has_favorite_genre(genres_str):
        movie_genres = set(genres_str.split())
        return len(movie_genres & set(user_favorite_genres)) > 0

    candidates = df_final[df_final["genres"].apply(has_favorite_genre)].copy()

    # Dışlanacak filmleri çıkar
    candidates = candidates[~candidates["tmdb_id"].isin(exclude_tmdb_ids)]

    if len(candidates) == 0:
        return pd.DataFrame()

    # Tür eşleşme skoru hesapla
    def calculate_match_score(genres_str):
        movie_genres = set(genres_str.split())
        match_count = len(movie_genres & set(user_favorite_genres))
        return (
            match_count / len(user_favorite_genres)
            if len(user_favorite_genres) > 0
            else 0
        )

    candidates["genre_match_score"] = candidates["genres"].apply(calculate_match_score)
    candidates["quality_score"] = candidates["imdb_puani"] / 10.0

    # Final skor: %70 Tür Eşleşmesi, %30 Kalite
    candidates["final_score"] = (
        candidates["genre_match_score"] * 0.70 + candidates["quality_score"] * 0.30
    )

    # ÇEŞİTLİLİK KONTROLÜ - Aynı türden maksimum 3 film
    candidates = candidates.sort_values("final_score", ascending=False)
    selected = []
    genre_count = {}

    for _, row in candidates.iterrows():
        if len(selected) >= top_n:
            break

        movie_genres = set(row["genres"].split())
        genre_overlap = sum(genre_count.get(g, 0) for g in movie_genres)

        if genre_overlap < 3:  # Maksimum 3 aynı türden
            selected.append(row)
            for g in movie_genres:
                genre_count[g] = genre_count.get(g, 0) + 1

    result_df = pd.DataFrame(selected)
    if len(result_df) == 0:
        return result_df

    return result_df[["tmdb_id", "baslik", "imdb_puani", "genres", "final_score"]].head(
        top_n
    )


# --- MODÜLLEŞTİRME ---


def initialize_recommendation_system():
    """Öneri sistemini başlatır - Uygulama başlangıcında çağrılır."""
    global cosine_sim, df_final, indices

    print("🔄 Öneri sistemi başlatılıyor...")

    df_filmler, df_turler, df_oyuncular, df_yonetmenler = fetch_data_from_db()

    if df_filmler is None:
        print("❌ Veritabanı bağlantısı başarısız!")
        return False

    df_turler_grup = (
        df_turler.groupby("film_id")["ad"]
        .apply(lambda x: " ".join(x))
        .reset_index()
        .rename(columns={"ad": "genres"})
    )
    df_oyuncular_grup = (
        df_oyuncular.groupby("film_id")["ad"]
        .apply(lambda x: " ".join(x))
        .reset_index()
        .rename(columns={"ad": "cast"})
    )
    df_yonetmenler_grup = (
        df_yonetmenler.groupby("film_id")["ad"]
        .apply(lambda x: " ".join(x))
        .reset_index()
        .rename(columns={"ad": "director"})
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

    df_final = df_final.reset_index()
    indices = pd.Series(df_final.index, index=df_final["baslik"])

    print(f"✅ Öneri sistemi hazır! ({len(df_final)} film)")
    return True


def display_recommendation_with_similarity(title, recommendations_df):
    """
    Önerileri görsel benzerlik çubukları ile gösterir.
    """
    print(f"\n{'='*100}")
    print(f"🎬 KAYNAK FİLM: {title}")
    print(f"{'='*100}\n")

    if len(recommendations_df) == 0:
        print("❌ Öneri bulunamadı!\n")
        return

    # Kaynak filmin bilgilerini al
    source_movie = df_final[df_final["baslik"] == title].iloc[0]
    print(f"📌 Türler: {source_movie['genres']}")
    print(f"⭐ IMDb: {source_movie['imdb_puani']}/10\n")
    print(f"{'─'*100}\n")

    for idx, row in recommendations_df.iterrows():
        film_name = row["baslik"][:40]

        # Skorları yüzdeye çevir
        content_pct = int(row["similarity_score"] * 100)
        genre_pct = int(row["genre_similarity"] * 100)
        final_pct = int(row["final_score"] * 100)

        # Görsel çubuklar
        content_bar = "█" * (content_pct // 5) + "░" * (20 - content_pct // 5)
        genre_bar = "█" * (genre_pct // 5) + "░" * (20 - genre_pct // 5)
        final_bar = "█" * (final_pct // 5) + "░" * (20 - final_pct // 5)

        # Film türlerini al
        film_genres = df_final[df_final["baslik"] == row["baslik"]]["genres"].values
        genres_str = film_genres[0] if len(film_genres) > 0 else "Bilinmiyor"

        print(f"{idx+1:2d}. {film_name:<42} ⭐ {row['imdb_puani']:.1f}/10")
        print(f"    └─ Türler: {genres_str[:50]}")
        print(f"    └─ İçerik Benzerliği  [{content_bar}] {content_pct}%")
        print(f"    └─ Tür Benzerliği     [{genre_bar}] {genre_pct}%")
        print(f"    └─ TOPLAM SKOR        [{final_bar}] {final_pct}%")

        # Benzerlik yorumu
        if final_pct >= 50:
            print(f"    └─ 💚 ÇOK BENZER - Kesinlikle izlemeli!")
        elif final_pct >= 40:
            print(f"    └─ 💙 BENZER - İzlemeye değer")
        elif final_pct >= 30:
            print(f"    └─ 💛 ORTA - Deneyebilirsin")
        else:
            print(f"    └─ 🤍 FARKLI - İlginç alternatif")

        print()

    print(f"{'='*100}\n")
    print("\n" + "=" * 100)
    print("🎬 ÖNERİ SİSTEMİ TEST RAPORU")
    print("=" * 100)

    # TEST 1: Farklı türlerden filmler
    test_cases = [
        ("Yeşil Yol", "Drama + Fantastik"),
        ("Başlangıç", "Bilim Kurgu + Aksiyon"),
        ("Kara Şövalye", "Aksiyon + Suç"),
        ("Forrest Gump", "Drama + Romantik"),
        ("Matrix", "Bilim Kurgu + Aksiyon"),
    ]

    for movie_title, genre_info in test_cases:
        print(f"\n{'─'*100}")
        print(f"📽️  KAYNAK FİLM: {movie_title} ({genre_info})")
        print(f"{'─'*100}")

        try:
            result = get_recommendations(movie_title, top_n=10)

            if len(result) > 0:
                # Tür çeşitliliğini analiz et
                all_genres = []
                for genres_str in result["baslik"].apply(
                    lambda x: (
                        df_final[df_final["baslik"] == x]["genres"].values[0]
                        if len(df_final[df_final["baslik"] == x]) > 0
                        else ""
                    )
                ):
                    all_genres.extend(genres_str.split())

                from collections import Counter

                genre_dist = Counter(all_genres)

                print(f"\n✅ {len(result)} öneri bulundu\n")
                print(
                    f"{'Sıra':<5} {'Film Adı':<45} {'IMDb':<6} {'İçerik':<8} {'Tür':<6} {'Final':<6}"
                )
                print("─" * 100)

                for idx, row in result.iterrows():
                    print(
                        f"{idx+1:<5} {row['baslik'][:44]:<45} {row['imdb_puani']:<6.1f} "
                        f"{row['similarity_score']:<8.3f} {row['genre_similarity']:<6.3f} {row['final_score']:<6.3f}"
                    )

                print(f"\n📊 TÜR DAĞILIMI:")
                for genre, count in genre_dist.most_common(5):
                    print(f"   • {genre}: {count} film")

                # ÇEŞİTLİLİK SKORU hesapla
                unique_genres = len(genre_dist)
                total_films = len(result)
                diversity_score = unique_genres / (
                    total_films * 2
                )  # Her filmde ortalama 2 tür var
                print(f"\n🎯 ÇEŞİTLİLİK SKORU: {diversity_score:.2%}")

                if diversity_score > 0.6:
                    print("   ✅ Çok iyi çeşitlilik!")
                elif diversity_score > 0.4:
                    print("   ⚠️  Orta çeşitlilik")
                else:
                    print("   ❌ Düşük çeşitlilik - Aynı türler tekrar ediyor")

            else:
                print("❌ Öneri bulunamadı!")

        except Exception as e:
            print(f"❌ HATA: {e}")

    # TEST 2: Exclude Mekanizması Testi
    print(f"\n\n{'='*100}")
    print("🔒 EXCLUDE MEKANİZMASI TESTİ")
    print("=" * 100)

    test_movie = "Yeşil Yol"
    print(f"\n1️⃣  Exclude OLMADAN:")
    result1 = get_recommendations(test_movie, top_n=5)
    print(result1[["baslik", "final_score"]].to_string(index=False))

    # İlk 2 filmin TMDB ID'lerini al
    if len(result1) >= 2:
        exclude_ids = set(result1["tmdb_id"].head(2).tolist())
        print(f"\n2️⃣  Exclude İLE (İlk 2 film dışlandı: {exclude_ids}):")
        result2 = get_recommendations(test_movie, exclude_tmdb_ids=exclude_ids, top_n=5)
        print(result2[["baslik", "final_score"]].to_string(index=False))

        # Kontrolü yap
        if not any(tmdb_id in exclude_ids for tmdb_id in result2["tmdb_id"]):
            print("\n✅ Exclude mekanizması ÇALIŞIYOR!")
        else:
            print("\n❌ Exclude mekanizması ÇALIŞMIYOR!")

    # TEST 3: Türe Göre Öneriler
    print(f"\n\n{'='*100}")
    print("🎭 TÜRE GÖRE ÖNERİLER TESTİ")
    print("=" * 100)

    favorite_genres = ["Drama", "Suç"]
    print(f"\nKullanıcının Favori Türleri: {favorite_genres}")

    genre_recommendations = get_recommendations_by_genre(
        user_favorite_genres=favorite_genres, top_n=10
    )

    if len(genre_recommendations) > 0:
        print(f"\n✅ {len(genre_recommendations)} öneri bulundu\n")
        print(f"{'Film Adı':<45} {'Türler':<30} {'IMDb':<6} {'Skor':<6}")
        print("─" * 100)

        for _, row in genre_recommendations.iterrows():
            print(
                f"{row['baslik'][:44]:<45} {row['genres'][:29]:<30} "
                f"{row['imdb_puani']:<6.1f} {row['final_score']:<6.3f}"
            )

        # Tür kontrolü
        correct_genre_count = 0
        for genres_str in genre_recommendations["genres"]:
            movie_genres = set(genres_str.split())
            if any(fav in movie_genres for fav in favorite_genres):
                correct_genre_count += 1

        print(
            f"\n📊 Türü Eşleşen Filmler: {correct_genre_count}/{len(genre_recommendations)} "
            f"({correct_genre_count/len(genre_recommendations)*100:.0f}%)"
        )

        if correct_genre_count == len(genre_recommendations):
            print("✅ Tüm öneriler doğru türlerden!")
        else:
            print("⚠️  Bazı öneriler istenmeyen türlerden")

    print("\n" + "=" * 100)
    print("✅ TEST TAMAMLANDI")
    print("=" * 100)

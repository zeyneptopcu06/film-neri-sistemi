// common.js dosyasından gelen global değişkenler: 
// userFavorites, checkUserStatus, createMovieCard, updateAllLikeButtons

// ============================================
// ANA SAYFA - SADECE ANA SAYFAYA ÖZEL FONKSİYONLAR
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Ana Sayfa Elementleri
    const popularList = document.getElementById('popular-list'); 
    const latestList = document.getElementById('latest-list'); 
    const recommendList = document.getElementById('recommend-list');
    const genreRecommendList = document.getElementById('genre-recommend-list');
    const exploreList = document.getElementById('random-explore-list');

    // -------------------------------------------------------------------
    // YARDIMCI YÜKLEME FONKSİYONLARI
    // -------------------------------------------------------------------

    // Popüler Filmleri Çekme
    async function fetchAndDisplayPopularMovies() {
        if (!popularList) return [];
        try {
            popularList.innerHTML = 'Yükleniyor...';
            const response = await fetch('/api/popular_movies');
            const popularMovies = await response.json();
            
            popularList.innerHTML = '';
            const shownIds = [];
            
            popularMovies.forEach(movie => {
                const isFavorite = userFavorites.includes(Number(movie.film_id));
                const card = createMovieCard(movie, isFavorite); 
                popularList.appendChild(card);
                shownIds.push(movie.film_id);
            });
            updateAllLikeButtons();
            
            console.log('✅ Popüler filmler yüklendi:', shownIds.length, 'film');
            return shownIds;
        } catch (error) {
            console.error('Popüler filmler çekme hatası:', error);
            if (popularList) {
                popularList.textContent = 'Popüler filmler yüklenirken bir hata oluştu.';
            }
            return [];
        }
    }

    // En Son Çıkan Filmleri Çekme
    async function fetchLatestMovies(excludeIds = new Set()) {
        if (!latestList) return [];
        try {
            latestList.innerHTML = 'Yükleniyor...';
            
            const excludeParam = Array.from(excludeIds).join(',');
            const url = excludeParam ? `/api/latest_movies?exclude=${excludeParam}` : '/api/latest_movies';
            
            console.log('🔍 Latest movies isteği:', url);
            
            const response = await fetch(url);
            const movies = await response.json();
            latestList.innerHTML = '';

            if (movies.length === 0) {
                latestList.innerHTML = `<p class="no-movies">Yeni çıkan film bulunamadı.</p>`;
                return [];
            }

            const shownIds = [];
            movies.forEach(movie => {
                const isFavorite = userFavorites.includes(Number(movie.film_id));
                const card = createMovieCard(movie, isFavorite); 
                latestList.appendChild(card);
                shownIds.push(movie.film_id);
            });

            updateAllLikeButtons();
            console.log('✅ Yeni filmler yüklendi:', shownIds.length, 'film (Exclude:', excludeIds.size, ')');
            return shownIds;
        } catch (error) {
            console.error("Yeni filmler çekme hatası:", error);
            if (latestList) {
                latestList.innerHTML = `<p class="error-message">Yeni filmler yüklenirken hata oluştu.</p>`;
            }
            return [];
        }
    }

    // Kişisel Önerileri Çekme
    async function fetchAndDisplayRecommendations(excludeIds = new Set()) {
        if (!recommendList) return [];

        try {
            recommendList.innerHTML = 'Yükleniyor...';
            
            const excludeParam = Array.from(excludeIds).join(',');
            const url = excludeParam ? `/api/recommendations?exclude=${excludeParam}` : '/api/recommendations';
            
            console.log('🔍 Recommendations isteği:', url);
            
            const response = await fetch(url);
            const recommendedMovies = await response.json();

            recommendList.innerHTML = '';

            if (recommendedMovies.length === 0) {
                console.log('ℹ️ Kişisel öneri yok - bölüm gizli kalacak');
                return [];
            }

            // Film varsa göster
            const scrollContainer = recommendList.parentElement;
            const heading = scrollContainer?.previousElementSibling;
            
            if (scrollContainer) scrollContainer.style.display = 'flex';
            if (heading && heading.tagName === 'H2') heading.style.display = 'block';

            const shownIds = [];
            recommendedMovies.forEach(movie => {
                const isFavorite = userFavorites.includes(Number(movie.film_id));
                const card = createMovieCard(movie, isFavorite);
                recommendList.appendChild(card);
                shownIds.push(movie.film_id);
            });

            updateAllLikeButtons();
            console.log('✅ Öneriler yüklendi ve gösterildi:', shownIds.length, 'film');
            return shownIds;
        } catch (error) {
            console.error('Önerilen filmler çekme hatası:', error);
            return [];
        }
    }

    // Tür Bazlı Önerileri Çekme
    async function fetchAndDisplayGenreRecommendations(excludeIds = new Set()) {
        if (!genreRecommendList) return [];

        try {
            genreRecommendList.innerHTML = 'Yükleniyor...';
            
            const excludeParam = Array.from(excludeIds).join(',');
            const url = excludeParam ? `/api/recommendations_by_genre?exclude=${excludeParam}` : '/api/recommendations_by_genre';
            
            console.log('🔍 Genre recommendations isteği:', url);
            
            const response = await fetch(url);
            const recommendedMovies = await response.json();

            genreRecommendList.innerHTML = '';

            if (recommendedMovies.length === 0) {
                console.log('ℹ️ Tür bazlı öneri yok - bölüm gizli kalacak');
                return [];
            }

            // Film varsa göster
            const scrollContainer = genreRecommendList.parentElement;
            const heading = scrollContainer?.previousElementSibling;
            
            if (scrollContainer) scrollContainer.style.display = 'flex';
            if (heading && heading.tagName === 'H2') heading.style.display = 'block';

            const shownIds = [];
            recommendedMovies.forEach(movie => {
                const isFavorite = userFavorites.includes(Number(movie.film_id));
                const card = createMovieCard(movie, isFavorite);
                genreRecommendList.appendChild(card);
                shownIds.push(movie.film_id);
            });

            updateAllLikeButtons();
            console.log('✅ Tür önerileri yüklendi ve gösterildi:', shownIds.length, 'film');
            return shownIds;
        } catch (error) {
            console.error('Tür bazlı öneriler çekme hatası:', error);
            return [];
        }
    }

    // Keşfet/Rastgele Filmleri Çekme
    async function fetchAndDisplayExploreSection(excludeIds = new Set()) {
        if (!exploreList) return [];
        
        try {
            exploreList.innerHTML = 'Yükleniyor...';
            
            const excludeParam = Array.from(excludeIds).join(',');
            const url = excludeParam ? `/api/explore?exclude=${excludeParam}` : '/api/explore';
            
            console.log('🔍 Explore isteği:', url);
            
            const response = await fetch(url);
            
            if (!response.ok) {
                 throw new Error(`HTTP hata kodu: ${response.status}`);
            }
            
            const randomMovies = await response.json();

            exploreList.innerHTML = '';
            const shownIds = [];
            
            randomMovies.forEach(movie => {
                const isFavorite = userFavorites.includes(Number(movie.film_id));
                const card = createMovieCard(movie, isFavorite);
                exploreList.appendChild(card);
                shownIds.push(movie.film_id);
            });
            
            updateAllLikeButtons();
            console.log('✅ Keşfet filmleri yüklendi:', shownIds.length, 'film (Exclude:', excludeIds.size, ')');
            return shownIds;
            
        } catch (error) {
            console.error('Keşfet Filmleri yükleme hatası:', error);
            if (exploreList) {
                exploreList.innerHTML = `<p class="error-text">Filmler yüklenemedi. Lütfen tekrar deneyin.</p>`;
            }
            return [];
        }
    }

    // -------------------------------------------------------------------
    // SAYFA BAŞLATMA
    // -------------------------------------------------------------------

    async function initializePage() {
        console.log('🔄 Ana Sayfa başlatılıyor...');

        // Öneri bölümlerini baştan gizle (yeni kullanıcılar için)
        const recommendContainer = document.getElementById('recommend-list')?.parentElement;
        const recommendHeading = recommendContainer?.previousElementSibling;
        const genreContainer = document.getElementById('genre-recommend-list')?.parentElement;
        const genreHeading = genreContainer?.previousElementSibling;
        
        if (recommendContainer) recommendContainer.style.display = 'none';
        if (recommendHeading) recommendHeading.style.display = 'none';
        if (genreContainer) genreContainer.style.display = 'none';
        if (genreHeading) genreHeading.style.display = 'none';

        // Gösterilen film ID'lerini toplayan Set
        const shownMovieIds = new Set();

        // Sırayla çek ve ID'leri topla
        if (popularList) {
            const popularIds = await fetchAndDisplayPopularMovies();
            popularIds.forEach(id => shownMovieIds.add(id));
        }
        
        if (latestList) {
            const latestIds = await fetchLatestMovies(shownMovieIds);
            latestIds.forEach(id => shownMovieIds.add(id));
        }
        
        if (exploreList) {
            await fetchAndDisplayExploreSection(shownMovieIds);
        }
        
        if (recommendList) {
            const recommendIds = await fetchAndDisplayRecommendations(shownMovieIds);
            recommendIds.forEach(id => shownMovieIds.add(id));
        }
        
        if (genreRecommendList) {
            const genreIds = await fetchAndDisplayGenreRecommendations(shownMovieIds);
            genreIds.forEach(id => shownMovieIds.add(id));
        }

        console.log('✅ Ana Sayfa başlatma tamamlandı. Toplam benzersiz film:', shownMovieIds.size);
    }

    // Yatay Kaydırma Butonları
    document.querySelectorAll('.scroll-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const scrollContainer = document.getElementById(targetId);
            const scrollAmount = 300;

            if (scrollContainer) {
                if (btn.classList.contains('left')) {
                    scrollContainer.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
                } else {
                    scrollContainer.scrollBy({ left: scrollAmount, behavior: 'smooth' });
                }
            }
        });
    });

    // Sayfa Yüklemesini Başlat
    initializePage();
});
// ============================================
// ARAMA SAYFASI - SADECE ARAMA SAYFASINA ÖZEL
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-form');
    const searchBox = document.getElementById('search-box');
    const searchButton = document.getElementById('search-button');
    const yearFilter = document.getElementById('year-select');
    const genreFilter = document.getElementById('genre-select');
    const imdbFilter = document.getElementById('imdb-select');
    const resultsTitle = document.getElementById('search-results-title') || document.getElementById('results-title');
    const searchResults = document.getElementById('search-results');

    let genresLoaded = false;

    // Türleri yükleme
    async function loadGenres() {
        if (genresLoaded || !genreFilter) return;
        
        try {
            const response = await fetch('/api/genres');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const genres = await response.json();
            const currentValue = genreFilter.value;
            
            genreFilter.innerHTML = '<option value="">Tür Seç</option>';
            
            if (Array.isArray(genres) && genres.length > 0) {
                genres.forEach(genre => {
                    const option = document.createElement('option');
                    option.value = genre.tur_id;
                    option.textContent = genre.ad;
                    genreFilter.appendChild(option);
                });
                
                if (currentValue) genreFilter.value = currentValue;
                genresLoaded = true;
            }
        } catch (error) {
            console.error('Türler yüklenirken hata:', error);
            showToast('Türler yüklenemedi', false);
        }
    }

    // Yılları yükleme
    function loadYears() {
        if (!yearFilter) return;
        
        const currentValue = yearFilter.value;
        const currentYear = new Date().getFullYear();
        yearFilter.innerHTML = '<option value="">Yıl Seç</option>';
        
        for (let year = currentYear; year >= 1900; year--) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearFilter.appendChild(option);
        }
        
        if (currentValue) yearFilter.value = currentValue;
    }

    // IMDB puanlarını doldurma
    function loadImdbRatings() {
        if (!imdbFilter) return;
        
        const currentValue = imdbFilter.value;
        imdbFilter.innerHTML = '<option value="">Min. IMDb Puanı</option>';
        
        for (let rating = 9; rating >= 5; rating--) {
            const option = document.createElement('option');
            option.value = rating;
            option.textContent = `Min. ${rating}.0 Puan`;
            imdbFilter.appendChild(option);
        }
        
        if (currentValue) imdbFilter.value = currentValue;
    }

    // Arama ve filtreleme fonksiyonu
    async function searchMovieAndGetRecommendations(event) {
        if (event) event.preventDefault();

        const query = searchBox ? searchBox.value.trim() : '';
        const year = yearFilter ? yearFilter.value : '';
        const genre = genreFilter ? genreFilter.value : '';
        const imdbRating = imdbFilter ? imdbFilter.value : '';

        if (!query && !year && !genre && !imdbRating) {
            showToast('Lütfen en az bir arama kriteri girin.', false);
            return;
        }

        if (resultsTitle) resultsTitle.textContent = 'Aranıyor...';
        if (searchResults) searchResults.innerHTML = '<p style="text-align: center; padding: 20px;">Yükleniyor...</p>';

        try {
            const params = new URLSearchParams();
            if (query) params.append('query', query);
            if (year) params.append('year', year);
            if (genre) params.append('genre', genre);
            if (imdbRating) params.append('imdb_rating', imdbRating);

            const response = await fetch(`/api/filter_movies?${params.toString()}`);
            
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();

            // Arama kutusunu ve filtreleri temizle
            if (searchBox) searchBox.value = '';
            if (yearFilter) yearFilter.value = '';
            if (genreFilter) genreFilter.value = '';
            if (imdbFilter) imdbFilter.value = '';

            if (data.length > 0) {
                // Başlık oluştur
                let titleParts = [];
                if (query) titleParts.push(`"${query}"`);
                if (year) titleParts.push(`${year} yılındaki`);
                if (genre && genreFilter) {
                    const selectedOption = genreFilter.querySelector(`option[value="${genre}"]`);
                    if (selectedOption) titleParts.push(`${selectedOption.textContent} türündeki`);
                }
                if (imdbRating) titleParts.push(`Min. ${Number(imdbRating).toFixed(1)} IMDb puanlı`);
                
                const title = titleParts.length > 0 
                    ? `${titleParts.join(' ')} filmler (${data.length} sonuç)` 
                    : `${data.length} Film Bulundu`;
                
                if (resultsTitle) resultsTitle.textContent = title;
                
                if (searchResults) {
                    searchResults.innerHTML = '';
                    data.forEach(movie => {
                        const isFavorite = userFavorites.includes(Number(movie.film_id));
                        const card = createMovieCard(movie, isFavorite);
                        searchResults.appendChild(card);
                    });
                }
                
                updateAllLikeButtons();
            } else {
                // Film bulunamadı
                let searchCriteria = [];
                if (query) searchCriteria.push(`"${query}"`);
                if (year) searchCriteria.push(`${year} yılı`);
                if (genre && genreFilter) {
                    const selectedOption = genreFilter.querySelector(`option[value="${genre}"]`);
                    if (selectedOption) searchCriteria.push(`${selectedOption.textContent} türü`);
                }
                if (imdbRating) searchCriteria.push(`Min. ${Number(imdbRating).toFixed(1)} IMDb`);
                
                const criteriaText = searchCriteria.length > 0 ? ` (${searchCriteria.join(', ')})` : '';
                
                if (resultsTitle) resultsTitle.textContent = `Film Bulunamadı${criteriaText}`;
                if (searchResults) {
                    searchResults.innerHTML = '<p class="no-results" style="text-align: center; padding: 40px; color: #666;">Aradığınız kriterlere uygun film bulunamadı.</p>';
                }
            }
        } catch (error) {
            console.error('Arama hatası:', error);
            if (resultsTitle) resultsTitle.textContent = 'Arama sırasında bir hata oluştu';
            if (searchResults) {
                searchResults.innerHTML = '<p class="error-message" style="text-align: center; padding: 40px; color: #f44336;">Arama sırasında bir hata oluştu. Lütfen tekrar deneyin.</p>';
            }
            showToast('Arama sırasında bir hata oluştu', false);
        }
    }

    // Event Listeners
    if (searchForm) {
        searchForm.addEventListener('submit', searchMovieAndGetRecommendations);
    }
    
    if (searchButton) {
        searchButton.addEventListener('click', (e) => {
            e.preventDefault();
            searchMovieAndGetRecommendations();
        });
    }
    
    if (searchBox) {
        searchBox.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchMovieAndGetRecommendations();
            }
        });
    }

    // Sayfa yüklendiğinde çalışacak fonksiyonlar
    async function initializePage() {
        console.log('🔄 Arama Sayfası başlatılıyor...');
        
        await checkUserStatus();
        
        // Filtreleri yükle
        await loadGenres();
        loadYears();
        loadImdbRatings();
        
        // URL parametrelerini kontrol et
        const urlParams = new URLSearchParams(window.location.search);
        const urlQuery = urlParams.get('q');
        const urlYear = urlParams.get('year');
        const urlGenre = urlParams.get('genre');
        const urlImdb = urlParams.get('imdb_rating');
        
        // Eğer URL'de parametre varsa, formu doldur ve arama yap
        if (urlQuery || urlYear || urlGenre || urlImdb) {
            if (urlQuery && searchBox) searchBox.value = urlQuery;
            if (urlYear && yearFilter) yearFilter.value = urlYear;
            if (urlGenre && genreFilter) genreFilter.value = urlGenre;
            if (urlImdb && imdbFilter) imdbFilter.value = urlImdb;
            
            // Kısa bir gecikme ile arama yap (filtrelerin yüklenmesini bekle)
            setTimeout(() => {
                searchMovieAndGetRecommendations();
            }, 300);
        }
        
        console.log('✅ Arama Sayfası başlatma tamamlandı.');
    }

    initializePage();
});
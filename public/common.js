// ============================================
// ORTAK FONKSİYONLAR - TÜM SAYFALARDA KULLANILIR
// ============================================

// Global değişkenler
let userFavorites = JSON.parse(localStorage.getItem('userFavorites')) || []; 
let isUserLoggedIn = false;
let genresLoaded = false; // Türlerin tekrar yüklenmesini önlemek için

// Favorileri localStorage'a kaydetme
function saveFavoritesToStorage() {
    localStorage.setItem('userFavorites', JSON.stringify(userFavorites));
}

// Toast Bildirim Kutusu
function showToast(message, isSuccess = true) {
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 1000;
            display: flex; flex-direction: column; gap: 10px;
        `;
        document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.style.cssText = `
        background-color: ${isSuccess ? '#4caf50' : '#f44336'};
        color: white; padding: 16px; border-radius: 4px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); max-width: 300px;
        opacity: 0; transform: translateX(100%); transition: opacity 0.3s, transform 0.3s;
        display: flex; justify-content: space-between; align-items: center;
    `;
    
    toast.innerHTML = `
        <span>${message}</span>
        <button style="background: none; border: none; color: white; cursor: pointer; margin-left: 10px;">&times;</button>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    }, 10);
    
    const closeButton = toast.querySelector('button');
    closeButton.addEventListener('click', () => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    });
    
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
}

// Film Kartı Oluşturma
function createMovieCard(movie, isFavorite = false) {
    const card = document.createElement('div');
    card.className = 'movie-card';
    
    const filmId = movie.film_id || movie.id || null;
    
    const posterUrl = movie.poster_url || movie.afis_url || '/static/placeholder.jpg'; 
    const movieTitle = movie.title || movie.baslik || 'Bilinmeyen Film';

    card.innerHTML = `
        <img src="${posterUrl}" alt="${movieTitle}" onerror="this.src='/static/placeholder.jpg'">
        <h3>${movieTitle}</h3>
        <button 
            class="like-button ${isFavorite ? 'liked' : ''}" 
            data-movie-title="${movieTitle}"
            data-movie-id="${filmId}">
            <i class="fas fa-heart"></i>
        </button>
    `;
    
    card.addEventListener('click', (e) => {
        if (!e.target.closest('.like-button') && filmId) {
            window.location.href = `/movie-detail?id=${filmId}`;
        }
    });

    return card;
}

// Tüm Beğen Butonlarını Güncelleme
function updateAllLikeButtons() {
    document.querySelectorAll('.like-button').forEach(button => {
        const movieId = Number(button.dataset.movieId);
        if (!movieId) return;

        if (userFavorites.includes(movieId)) {
            button.classList.add('liked');
        } else {
            button.classList.remove('liked');
        }
    });
}

// Favorilere Ekleme/Kaldırma
async function toggleFavorite(movieTitle, likeButton) {
    if (!isUserLoggedIn) {
        showToast('Favorilere eklemek için giriş yapmalısınız.', false);
        return;
    }

    try {
        let filmId = Number(likeButton.dataset.movieId);

        if (!filmId) {
            const searchResponse = await fetch(`/api/search/${encodeURIComponent(movieTitle)}`);
            const searchData = await searchResponse.json();
            filmId = Number(searchData.film_id);
            if (!filmId) {
                showToast('Film ID bulunamadı.', false);
                return;
            }
            likeButton.dataset.movieId = filmId;
        }

        let response;
        if (likeButton.classList.contains('liked')) {
            response = await fetch('/api/remove_from_favorites', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ film_id: filmId })
            });
            const data = await response.json();
            if (response.ok && data.mesaj) {
                showToast(data.mesaj, true);
                userFavorites = userFavorites.filter(id => id !== filmId);
                saveFavoritesToStorage();
                likeButton.classList.remove('liked');
                updateAllLikeButtons();
            } else {
                showToast(data.hata || 'Favori kaldırma işlemi başarısız.', false);
            }
        } else {
            response = await fetch('/api/add_to_favorites', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ film_id: filmId })
            });
            const data = await response.json();
            if (response.ok && data.mesaj) {
                showToast(data.mesaj, true);
                if (!userFavorites.includes(filmId)) {
                    userFavorites.push(filmId);
                }
                saveFavoritesToStorage();
                likeButton.classList.add('liked');
                updateAllLikeButtons();
            } else {
                showToast(data.hata || 'Favori ekleme işlemi başarısız.', false);
            }
        }
    } catch (error) {
        console.error('Favori işlemi hatası:', error);
        showToast('İşlem sırasında bir hata oluştu.', false);
    }
}


// ============================================
// FİLTRE DOLDURMA İŞLEVLERİ (Search.js'ten Taşındı)
// ============================================

// Türleri yükleme
async function loadGenres() {
    const genreFilter = document.getElementById('genre-select');
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
    const yearFilter = document.getElementById('year-select');
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
    const imdbFilter = document.getElementById('imdb-select');
    if (!imdbFilter) return;
    
    const currentValue = imdbFilter.value;
    imdbFilter.innerHTML = '<option value="">Min. IMDb Puanı</option>';
    
    for (let rating = 9; rating >= 5; rating--) {
        const option = document.createElement('option');
        const displayRating = rating.toFixed(1);
        option.value = rating;
        option.textContent = `Min. ${displayRating} Puan`;
        imdbFilter.appendChild(option);
    }
    
    if (currentValue) imdbFilter.value = currentValue;
}

// Kullanıcı Oturum Kontrolü
async function checkUserStatus() {
    try {
        const response = await fetch('/api/user_status');
        const data = await response.json();
        
        const authLinks = document.querySelector('.auth-links');
        const userInfo = document.querySelector('.user-info');
        const welcomeMessage = document.getElementById('welcome-message');
        const userInitialAvatar = document.getElementById('user-initial-avatar'); 

        if (data.logged_in) {
            isUserLoggedIn = true; 
            
            if (authLinks) authLinks.classList.add('hidden');
            if (userInfo) userInfo.classList.remove('hidden');
            
            const userEmail = data.email || '';
            const userNameDisplay = data.username 
                                     || userEmail.split('@')[0] 
                                     || 'Kullanıcı'; 
            
            const firstInitial = userNameDisplay.charAt(0).toUpperCase();

            if (welcomeMessage) {
                welcomeMessage.textContent = `Hoş geldin, ${userNameDisplay}!`;
            }
            
            if (userInitialAvatar) {
                userInitialAvatar.textContent = firstInitial;
                userInitialAvatar.classList.remove('hidden'); 
            }
            
            await fetchUserFavorites();
            updateAllLikeButtons();
        } else {
            isUserLoggedIn = false;
            if (authLinks) authLinks.classList.remove('hidden');
            if (userInfo) userInfo.classList.add('hidden');
            userFavorites = [];
            saveFavoritesToStorage();
            
            if (userInitialAvatar) {
                userInitialAvatar.textContent = ''; 
            }
        }
    } catch (error) {
        console.error('Kullanıcı durumu kontrol hatası:', error);
    }
}

// Kullanıcının Favorilerini Çekme
async function fetchUserFavorites() {
    if (!isUserLoggedIn) {
        userFavorites = [];
        saveFavoritesToStorage();
        return;
    }

    try {
        const response = await fetch('/api/get_favorites');
        const data = await response.json();

        if (response.ok && Array.isArray(data)) {
            userFavorites = data.map(f => Number(f.film_id));
            saveFavoritesToStorage();
        } else {
            userFavorites = [];
            saveFavoritesToStorage();
        }
    } catch (error) {
        console.error("Favoriler alınamadı:", error);
        userFavorites = [];
        saveFavoritesToStorage();
    }
}

// Beğenme/Kaldırma Event Listener (Global)
document.addEventListener('click', (e) => {
    const likeButton = e.target.closest('.like-button');
    if (likeButton) {
        e.preventDefault();
        e.stopPropagation();
        const movieCard = likeButton.closest('.movie-card');
        let movieTitle = likeButton.dataset.movieTitle;
        
        if (!movieTitle) {
            const detailHeader = likeButton.closest('.movie-detail');
            if (detailHeader) {
                const titleElement = detailHeader.querySelector('.movie-title');
                if (titleElement) {
                    movieTitle = titleElement.textContent.trim().split('(')[0].trim();
                }
            }
        }
        
        if (!movieTitle && movieCard) {
            const titleElement = movieCard.querySelector('h3');
            if (titleElement) {
                movieTitle = titleElement.textContent;
            }
        }
        
        if (movieTitle) {
            toggleFavorite(movieTitle, likeButton);
        }
    }
});

// ⭐ DOMContentLoaded EVENT LISTENER (Çıkış, Favoriler, Arama ve Dropdown Kontrolü)
document.addEventListener('DOMContentLoaded', () => {
    const logoutLink = document.getElementById('logout-link');
    const favoritesLink = document.getElementById('favorites-link');
    
    // ------------------------------------------------------------------
    // 1. ARAMA YÖNLENDİRME İŞLEVİ (Tüm sayfalarda arama çubuğu için)
    // ------------------------------------------------------------------
    
    // Elementleri doğru ID'lerle seçin
    const searchForm = document.getElementById('global-search-form') || document.getElementById('search-form'); 
    const searchInput = document.getElementById('search-box'); 
    const yearFilter = document.getElementById('year-select');
    const genreFilter = document.getElementById('genre-select');
    const imdbFilter = document.getElementById('imdb-select');

    if (searchForm) {
        // Form submit edildiğinde, tüm parametrelerle arama sayfasına yönlendir
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const query = searchInput ? searchInput.value.trim() : '';
            const year = yearFilter ? yearFilter.value : '';
            const genre = genreFilter ? genreFilter.value : '';
            const imdbRating = imdbFilter ? imdbFilter.value : '';

            // En az bir kriter varsa yönlendir
            if (query || year || genre || imdbRating) {
                const params = new URLSearchParams();
                if (query) params.append('q', query);
                if (year) params.append('year', year);
                if (genre) params.append('genre', genre);
                if (imdbRating) params.append('imdb_rating', imdbRating);
                
                // Yönlendirme, search.js'in çalıştığı sayfayı tetikleyecektir.
                window.location.href = `/search?${params.toString()}`;
            } else {
                showToast('Lütfen arama veya filtre kriteri giriniz.', false);
            }
        });
    }

    // ⭐ 2. FİLTRELERİ DOLDURMA ⭐
    loadGenres();
    loadYears();
    loadImdbRatings();

    // ------------------------------------------------------------------
    // 3. AVATAR DROPDOWN KONTROLÜ
    // ------------------------------------------------------------------
    const userAvatar = document.getElementById('user-initial-avatar');
    const dropdownMenu = document.getElementById('user-dropdown-menu');
    
    if (userAvatar && dropdownMenu) {
        userAvatar.addEventListener('click', (e) => {
            dropdownMenu.classList.toggle('show-dropdown');
            e.stopPropagation(); 
        });
    }

    document.addEventListener('click', (e) => {
        if (dropdownMenu && dropdownMenu.classList.contains('show-dropdown')) {
            if (!e.target.closest('.user-info')) {
                dropdownMenu.classList.remove('show-dropdown');
            }
        }
    });

    // ------------------------------------------------------------------
    // 4. ÇIKIŞ VE FAVORİ LİNKLERİ
    // ------------------------------------------------------------------
    if (logoutLink) {
        logoutLink.addEventListener('click', async (e) => {
            e.preventDefault();
            if (dropdownMenu) dropdownMenu.classList.remove('show-dropdown'); 
            
            try {
                await fetch('/api/logout', { method: 'POST' });
                isUserLoggedIn = false;
                userFavorites = [];
                saveFavoritesToStorage();
                showToast('Başarıyla çıkış yapıldı.', true);
                setTimeout(() => {
                    location.reload();
                }, 500);
            } catch (error) {
                console.error('Çıkış hatası:', error);
                showToast('Çıkış işlemi başarısız.', false);
            }
        });
    }
    
    if (favoritesLink) {
        favoritesLink.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = '/favorites';
        });
    }

    // Sayfa başlatma (Kullanıcı durumunu kontrol et)
    checkUserStatus(); 
});
// ============================================
// DETAY SAYFASI - DÜZELTILMIŞ YORUM VE BEĞENİ SISTEMI
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const detailContent = document.getElementById('detail-content');
    let currentMovieId = null;
    let currentUserId = null; 

    // URL'den film ID'sini al
    function getMovieIdFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('id');
    }

    // Kullanıcı durumunu kontrol et
    async function checkCurrentUser() {
        try {
            const response = await fetch('/api/user_status');
            const data = await response.json();
            if (data.logged_in) {
                currentUserId = data.user_id;
                console.log('✅ Kullanıcı bilgileri:', {
                    user_id: data.user_id,
                    email: data.email,
                    username: data.username
                });
            }
        } catch (error) {
            console.error('Kullanıcı durumu kontrol hatası:', error);
        }
    }

    // Film detaylarını yükle
    async function loadMovieDetails() {
        currentMovieId = getMovieIdFromURL();
        
        if (!currentMovieId) {
            detailContent.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h2>Film bulunamadı</h2>
                    <p>Lütfen geçerli bir film seçin</p>
                    <a href="/" class="back-home-btn">Ana Sayfaya Dön</a>
                </div>
            `;
            return;
        }

        detailContent.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <p>Film detayları yükleniyor...</p>
            </div>
        `;

        try {
            const response = await fetch(`/api/movie_details/${currentMovieId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const movie = await response.json();
            const isFavorite = userFavorites.includes(Number(currentMovieId));

            if (movie && movie.baslik) {
                renderMovieDetails(movie, isFavorite);
                await loadComments(currentMovieId);
                await loadSimilarMovies(currentMovieId);
                setupTrailerModal();
            } else {
                detailContent.innerHTML = `
                    <div class="error-state">
                        <i class="fas fa-film"></i>
                        <h2>Film detayları bulunamadı</h2>
                        <p>Bu filmin detayları mevcut değil</p>
                        <a href="/" class="back-home-btn">Ana Sayfaya Dön</a>
                    </div>
                `;
            }

        } catch (error) {
            console.error('Film detayı çekme hatası:', error);
            detailContent.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-circle"></i>
                    <h2>Yükleme hatası</h2>
                    <p>Film detayları yüklenirken bir hata oluştu</p>
                    <button onclick="location.reload()" class="retry-btn">Tekrar Dene</button>
                </div>
            `;
        }
    }

    // Film detaylarını render et
    function renderMovieDetails(movie, isFavorite) {
        const castHtml = Array.isArray(movie.cast) && movie.cast.length > 0
            ? movie.cast.map(actor =>
                `<a href="/person-movies?name=${encodeURIComponent(actor)}&type=actor" class="cast-member clickable">${actor}</a>`
            ).join('')
            : '<span class="no-info">Oyuncu bilgisi bulunmuyor</span>';

        const turlerText = Array.isArray(movie.turler) && movie.turler.length > 0
            ? movie.turler.join(', ')
            : 'Bilinmiyor';

        const yonetmenlerHtml = movie.yonetmenler
            ? movie.yonetmenler.split(', ').map(director =>
                `<a href="/person-movies?name=${encodeURIComponent(director)}&type=director" class="director-link clickable">${director}</a>`
            ).join(', ')
            : 'Bilinmiyor';

        const imdbPuan = movie.imdb_puani ? movie.imdb_puani + '/10' : 'N/A';
        const yil = movie.release_date ? new Date(movie.release_date).getFullYear() : 'N/A';

        let fragmanButtonHtml = '';
        const fragmanURL = movie.fragman_url || movie.trailer_url;

        if (fragmanURL) {
            fragmanButtonHtml = `
                <div class="trailer-section">
                    <button id="openTrailerBtn" class="trailer-btn" data-trailer-url="${fragmanURL}">
                        <i class="fas fa-play-circle"></i> Fragmanı İzle
                    </button>
                </div>
            `;
        }

        const detailHtml = `
            <div class="movie-detail">
                <div class="detail-header">
                    <div class="detail-poster">
                        <img src="${movie.afis_url || '/static/placeholder.jpg'}"
                             alt="${movie.baslik} Poster"
                             onerror="this.src='/static/placeholder.jpg'">
                        
                        ${fragmanButtonHtml}
                        <button class="favorite-btn like-button ${isFavorite ? 'liked' : ''}"
                            data-movie-title="${movie.baslik}"
                            data-movie-id="${currentMovieId}">
                            <i class="fas fa-heart"></i>
                        </button>
                    </div>
                    
                    <div class="detail-info-wrapper">
                        <div class="detail-basic-info">
                            <h1 class="movie-title">${movie.baslik} <span class="movie-year">(${yil})</span></h1>
                            
                            <div class="movie-meta">
                                <div class="meta-item">
                                    <i class="fas fa-star"></i>
                                    <span class="imdb-rating">IMDb ${imdbPuan}</span>
                                </div>
                                <div class="meta-item">
                                    <i class="fas fa-film"></i>
                                    <span>${turlerText}</span>
                                </div>
                                <div class="meta-item">
                                    <i class="fas fa-user-tie"></i>
                                    <span>${yonetmenlerHtml}</span>
                                </div>
                            </div>
                        </div>

                        <div class="overview-section">
                            <h2><i class="fas fa-align-left"></i> Özet</h2>
                            <div class="overview-text">
                                ${movie.ozet || '<p class="no-info">Bu filme ait özet bilgisi bulunmamaktadır.</p>'}
                            </div>
                        </div>

                        <div class="cast-section">
                            <h2><i class="fas fa-users"></i> Oyuncular</h2>
                            <div class="cast-grid">
                                ${castHtml}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- YORUMLAR BÖLÜMÜ -->
                <div class="comments-section">
                    <h2><i class="fas fa-comments"></i> Yorumlar</h2>
                    
                    ${currentUserId ? `
                    <div class="comment-form">
                        <textarea id="yorum-text" placeholder="Yorumunuzu yazın... (max 500 karakter)" maxlength="500"></textarea>
                        <button id="yorum-ekle-btn" class="submit-comment-btn">
                            <i class="fas fa-paper-plane"></i> Yorum Ekle
                        </button>
                    </div>
                    ` : `
                    <div class="login-prompt">
                        <p>Yorum yapmak için <a href="/login">giriş yapın</a></p>
                    </div>
                    `}
                    
                    <div id="yorum-listesi" class="comments-list">
                        <p class="loading-text">Yorumlar yükleniyor...</p>
                    </div>
                </div>

                <!-- BENZERİ FİLMLER BÖLÜMÜ -->
                <div id="similar-movies-section" class="similar-movies-section">
                    <h2><i class="fas fa-film"></i> Benzer Filmler</h2>
                    <div id="similar-movies-container" class="loading-state">
                        <div class="loading-spinner"></div>
                        <p>Benzer filmler yükleniyor...</p>
                    </div>
                </div>
            </div>

            <!-- FRAGMAN MODAL -->
            <div id="trailerModal" class="modal">
                <div class="modal-content">
                    <span class="close-button">&times;</span>
                    <div id="modal-video-container" class="video-container"></div>
                </div>
            </div>
        `;

        detailContent.innerHTML = detailHtml;
        updateAllLikeButtons();
    }

    // Yorumları yükleme
    async function loadComments(movieId) {
        const yorumListesi = document.getElementById('yorum-listesi');
        if (!yorumListesi) return;

        yorumListesi.innerHTML = '<p class="loading-text">Yorumlar yükleniyor...</p>';

        try {
            const res = await fetch(`/api/yorumlar/${movieId}`);
            if (!res.ok) throw new Error('Yorumlar yüklenemedi');
            
            const yorumlar = await res.json();

            if (yorumlar.length === 0) {
                yorumListesi.innerHTML = '<p class="no-comments">Henüz yorum yok. İlk yorumu siz ekleyin!</p>';
                return;
            }

            yorumListesi.innerHTML = yorumlar.map(y => {
                const isOwner = y.user_id === currentUserId;
                const likedClass = y.kullanici_begendi ? 'begendi' : 'begenilmedi';
                const likedData = y.kullanici_begendi ? 'true' : 'false';
                
                const formattedDate = y.tarih ? new Date(y.tarih).toLocaleString('tr-TR', { 
                    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
                }) : 'Bilinmiyor';

                const likeButtonHtml = currentUserId ? `
                    <button class="begeni-butonu" data-yorum-id="${y.id}" data-liked="${likedData}">
                        <span class="begeni-simgesi ${likedClass}">
                            <i class="fas fa-heart"></i>
                        </span>
                        <span class="begeni-sayisi">${y.begeni_sayisi || 0}</span>
                    </button>
                ` : `
                    <span class="begeni-butonu disabled-begeni">
                        <span class="begeni-simgesi ${likedClass}" title="Beğenmek için giriş yapın">
                            <i class="fas fa-heart"></i>
                        </span>
                        <span class="begeni-sayisi">${y.begeni_sayisi || 0}</span>
                    </span>
                `;

                return `
                    <div class="yorum-card" data-yorum-id="${y.id}">
                        <div class="yorum-header">
                            <p class="yorum-user">
                                <strong>${y.username || 'Anonim'}</strong> 
                                <span class="yorum-date">${formattedDate}</span>
                            </p>
                            <div class="begeni-alani">
                                ${likeButtonHtml}
                            </div>
                        </div>

                        <p class="yorum-text">${y.yorum || y.text}</p>
                        
                        ${isOwner ? `
                        <div class="yorum-actions">
                            <button class="yorum-edit-btn" data-yorum-id="${y.id}">
                                <i class="fas fa-edit"></i> Düzenle
                            </button>
                            <button class="yorum-delete-btn" data-yorum-id="${y.id}">
                                <i class="fas fa-trash"></i> Sil
                            </button>
                        </div>` : ''}
                    </div>
                `;
            }).join('');

        } catch (error) {
            console.error('Yorumlar yüklenirken hata:', error);
            yorumListesi.innerHTML = '<p class="error-text">Yorumlar yüklenemedi.</p>';
        }
    }
    
    // Yorum beğeni toggle
    async function begeniToggle(button) {
        const yorumId = button.dataset.yorumId;
        let isLiked = button.dataset.liked === 'true';

        const begeniSimge = button.querySelector('.begeni-simgesi');
        const begeniSayisi = button.querySelector('.begeni-sayisi');

        button.disabled = true;

        try {
            const response = await fetch(`/api/yorum_begeni/${yorumId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.status === 401) {
                alert("Bu işlemi yapmak için lütfen giriş yapın.");
                return;
            }

            const data = await response.json();

            if (response.ok) {
                begeniSayisi.textContent = data.begeni_sayisi;
                isLiked = data.is_liked;

                if (isLiked) {
                    begeniSimge.classList.remove('begenilmedi');
                    begeniSimge.classList.add('begendi');
                } else {
                    begeniSimge.classList.remove('begendi');
                    begeniSimge.classList.add('begenilmedi');
                }

                button.dataset.liked = isLiked ? 'true' : 'false';

            } else {
                alert(`Hata: ${data.error}`);
            }

        } catch (error) {
            console.error('Beğeni işlemi sırasında bir hata oluştu:', error);
            alert('İşlem sırasında bir hata oluştu.');
        } finally {
            button.disabled = false;
        }
    }

    // ✅ OLAY DİNLEYİCİLERİ (EVENT DELEGATION)
    // DETAİL SAYFASI İÇİN ÖZEL EVENT LISTENER (TÜM DETAIL-CONTENT)
    document.body.addEventListener('click', async (e) => {
        
        // ✅ FİLM BEĞENİ İŞLEMİ - EN ÖNCELİKLİ (Benzer filmler dahil)
        const likeButton = e.target.closest('.like-button');
        if (likeButton && detailContent.contains(likeButton)) {
            e.preventDefault();
            e.stopPropagation();
            
            const movieId = likeButton.dataset.movieId;
            const movieTitle = likeButton.dataset.movieTitle;
            
            console.log('🎬 Detay sayfası - Film beğeni:', {movieId, movieTitle});
            
            // main.js'teki toggleFavorite fonksiyonunu kullan
            if (typeof toggleFavorite === 'function') {
                await toggleFavorite(movieTitle, likeButton);
            } 
            // Ya da lokal fonksiyonu kullan
            else {
                console.log('⚠️ Global toggleFavorite yok, lokal fonksiyon kullanılıyor');
                await handleMovieLike(movieId, movieTitle);
            }
            return; // Diğer işlemlere geçme
        }
        
        // Aşağıdaki işlemler sadece detailContent içindeyse çalışsın
        if (!detailContent.contains(e.target)) return;
        
        // Yorum ekleme
        if (e.target.id === 'yorum-ekle-btn' || e.target.closest('#yorum-ekle-btn')) {
            e.preventDefault();
            const textArea = document.getElementById('yorum-text');
            const text = textArea.value.trim();
            
            if (!text) {
                alert('Yorum boş olamaz!');
                return;
            }
            
            if (text.length > 500) {
                alert('Yorum 500 karakterden uzun olamaz.');
                return;
            }

            try {
                const res = await fetch(`/api/yorum_ekle/${currentMovieId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ text: text })
                });

                const data = await res.json();
                
                if (res.ok) {
                    textArea.value = '';
                    await loadComments(currentMovieId);
                } else {
                    alert(data.error || 'Yorum eklenirken bir hata oluştu');
                }
            } catch (error) {
                alert('Yorum eklenirken bir hata oluştu');
            }
        }
        
        // Yorum silme
        else if (e.target.classList.contains('yorum-delete-btn') || e.target.closest('.yorum-delete-btn')) {
            const btn = e.target.closest('.yorum-delete-btn');
            const yorumId = btn.dataset.yorumId;
            
            if (!confirm('Bu yorumu silmek istediğinizden emin misiniz?')) return;

            try {
                const res = await fetch(`/api/yorum_sil/${yorumId}`, {method: 'DELETE'});
                if (res.ok) {
                    await loadComments(currentMovieId);
                } else {
                    alert('Yorum silinemedi');
                }
            } catch (error) {
                alert('Yorum silinirken bir hata oluştu');
            }
        }

        // Yorum düzenleme
        else if (e.target.classList.contains('yorum-edit-btn') || e.target.closest('.yorum-edit-btn')) {
            const btn = e.target.closest('.yorum-edit-btn');
            const yorumCard = btn.closest('.yorum-card');
            const yorumId = btn.dataset.yorumId;
            const currentText = yorumCard.querySelector('.yorum-text').innerText;
            
            const newText = prompt('Yorumu düzenle (max 500 karakter)', currentText);
            if (!newText || newText === currentText) return;

            if (newText.length > 500) {
                alert('Yorum 500 karakterden uzun olamaz.');
                return;
            }

            try {
                const res = await fetch(`/api/yorum_duzenle/${yorumId}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: newText})
                });
                
                if (res.ok) {
                    await loadComments(currentMovieId);
                } else {
                    alert('Yorum güncellenemedi');
                }
            } catch (error) {
                alert('Yorum güncellenirken bir hata oluştu');
            }
        }
        
        // Yorum beğeni işlemi
        else if (e.target.closest('.begeni-butonu:not(.disabled-begeni)')) {
            const button = e.target.closest('.begeni-butonu');
            if (currentUserId) {
                begeniToggle(button);
            } else {
                alert('Bu yorumu beğenmek için giriş yapmalısınız!');
            }
        }
    }); // document.body listener sonu

    // Benzer filmleri yükle
    async function loadSimilarMovies(movieId) {
        const container = document.getElementById('similar-movies-container');
        
        try {
            const response = await fetch(`/api/similar_movies/${movieId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const similarMovies = await response.json();
            
            if (similarMovies && similarMovies.length > 0) {
                renderSimilarMovies(similarMovies);
            } else {
                container.innerHTML = `
                    <div class="no-similar-movies">
                        <i class="fas fa-info-circle"></i>
                        <p>Benzer film önerisi bulunamadı.</p>
                    </div>
                `;
            }
            
        } catch (error) {
            console.error('Benzer filmler yüklenirken hata:', error);
            container.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Benzer filmler yüklenemedi.</p>
                </div>
            `;
        }
    }

    // Benzer filmleri render et (standart kart tasarımıyla)
function renderSimilarMovies(movies) {
    const container = document.getElementById('similar-movies-container');
    if (!container) return;

    const grid = document.createElement('div');
    grid.className = 'similar-movies-grid';

    movies.forEach(movie => {
        const isFavorite = userFavorites.includes(Number(movie.id));
        const card = createMovieCard({
            id: movie.id,
            baslik: movie.baslik,
            afis_url: movie.afis_url
        }, isFavorite);

        grid.appendChild(card);
    });

    container.innerHTML = '';
    container.appendChild(grid);

    updateAllLikeButtons();
}


    // Fragman modal fonksiyonları
    function setupTrailerModal() {
        const openBtn = document.getElementById('openTrailerBtn');
        const modal = document.getElementById('trailerModal');
        const closeButton = document.querySelector('.close-button');
        const modalVideoContainer = document.getElementById('modal-video-container');

        if (!openBtn) return;

        openBtn.addEventListener('click', () => {
            const url = openBtn.getAttribute('data-trailer-url');
            
            if (url) {
                let embedUrl = url;
                if (url.includes('youtube.com/watch')) {
                    const videoId = url.split('v=')[1];
                    const ampersandPosition = videoId.indexOf('&');
                    const cleanVideoId = ampersandPosition !== -1 ? videoId.substring(0, ampersandPosition) : videoId;
                    embedUrl = `https://www.youtube.com/embed/${cleanVideoId}?autoplay=1`;
                } else if (url.includes('youtu.be/')) {
                    const videoId = url.split('youtu.be/')[1];
                    embedUrl = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
                }

                modalVideoContainer.innerHTML = `
                    <iframe 
                        src="${embedUrl}"  
                        frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen>
                    </iframe>
                `;
                modal.style.display = "flex";
            }
        });

        function closeModal() {
            modal.style.display = "none";
            modalVideoContainer.innerHTML = '';
        }

        if (closeButton) {
            closeButton.onclick = closeModal;
        }

        window.onclick = function(event) {
            if (event.target == modal) {
                closeModal();
            }
        }
    }

    // ✅ FİLM BEĞENİ FONKSİYONU (main.js ile uyumlu)
    async function handleMovieLike(movieId, movieTitle, button) {
        if (!currentUserId) {
            alert('Beğenmek için giriş yapmalısınız!');
            return;
        }

        try {
            const isLiked = button.classList.contains('liked');
            
            if (isLiked) {
                // Favoriden çıkar
                const response = await fetch('/api/remove_from_favorites', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ film_id: movieId })
                });

                const data = await response.json();
                
                if (response.ok && data.mesaj) {
                    console.log('✅ Favoriden çıkarıldı:', movieTitle);
                    
                    // userFavorites listesini güncelle
                    if (typeof userFavorites !== 'undefined') {
                        userFavorites = userFavorites.filter(id => id !== Number(movieId));
                        if (typeof saveFavoritesToStorage === 'function') {
                            saveFavoritesToStorage();
                        }
                    }
                    
                    button.classList.remove('liked');
                    updateLikeButtonsLocal();
                    showNotification(`❌ ${movieTitle} favorilerden çıkarıldı`);
                } else {
                    alert(data.hata || 'Favori kaldırma işlemi başarısız.');
                }
                
            } else {
                // Favoriye ekle
                const response = await fetch('/api/add_to_favorites', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ film_id: movieId })
                });

                const data = await response.json();
                
                if (response.ok && data.mesaj) {
                    console.log('✅ Favoriye eklendi:', movieTitle);
                    
                    // userFavorites listesini güncelle
                    if (typeof userFavorites !== 'undefined') {
                        if (!userFavorites.includes(Number(movieId))) {
                            userFavorites.push(Number(movieId));
                        }
                        if (typeof saveFavoritesToStorage === 'function') {
                            saveFavoritesToStorage();
                        }
                    }
                    
                    button.classList.add('liked');
                    updateLikeButtonsLocal();
                    showNotification(`✅ ${movieTitle} favorilere eklendi`);
                } else {
                    alert(data.hata || 'Favori ekleme işlemi başarısız.');
                }
            }
            
        } catch (error) {
            console.error('Beğeni hatası:', error);
            alert('Bir hata oluştu');
        }
    }

    // Lokal buton güncelleme
    function updateLikeButtonsLocal() {
        if (typeof userFavorites === 'undefined') return;
        
        document.querySelectorAll('.like-button').forEach(button => {
            const movieId = parseInt(button.dataset.movieId);
            if (userFavorites.includes(movieId)) {
                button.classList.add('liked');
            } else {
                button.classList.remove('liked');
            }
        });
    }

    // Basit bildirim
    function showNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #333;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }

    // Sayfa başlatma
    async function initializePage() {
        console.log('🔄 Detay Sayfası başlatılıyor...');
        
        if (typeof checkUserStatus === 'function') {
            await checkUserStatus();
        }
        
        await checkCurrentUser();
        await loadMovieDetails();
        
        console.log('✅ Detay Sayfası başlatma tamamlandı.');
    }

    initializePage();
});
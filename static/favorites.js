// ============================================
// FAVORİLER SAYFASI - SADECE FAVORİLER SAYFASINA ÖZEL
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const favoritesContainer = document.getElementById('favorites-container');
    const noFavoritesMessage = document.getElementById('no-favorites-message');

    // Favorileri getir ve göster
    async function fetchAndDisplayFavorites() {
        if (!isUserLoggedIn) {
            noFavoritesMessage.textContent = 'Favorilerinizi görmek için giriş yapmalısınız.';
            noFavoritesMessage.classList.remove('hidden');
            favoritesContainer.innerHTML = '';
            return;
        }
        
        try {
            const response = await fetch('/api/get_favorites');
            const favorites = await response.json();
            
            favoritesContainer.innerHTML = '';
            
            if (!response.ok) {
                showToast(favorites.hata || 'Favoriler yüklenirken hata oluştu.', false);
                noFavoritesMessage.textContent = favorites.hata || 'Favoriler yüklenirken hata oluştu.';
                noFavoritesMessage.classList.remove('hidden');
            } else if (favorites.length === 0) {
                noFavoritesMessage.textContent = 'Henüz favori filminiz yok.';
                noFavoritesMessage.classList.remove('hidden');
            } else {
                noFavoritesMessage.classList.add('hidden');
                favorites.forEach(movie => {
                    const isFavorite = true; // Favoriler sayfasında zaten hepsi favori
                    const card = createMovieCard(movie, isFavorite);
                    favoritesContainer.appendChild(card);
                });
                updateAllLikeButtons();
            }
        } catch (error) {
            console.error('Favori filmler çekme hatası:', error);
            showToast('Favoriler yüklenirken bir hata oluştu.', false);
            noFavoritesMessage.textContent = 'Favoriler yüklenirken bir hata oluştu.';
            noFavoritesMessage.classList.remove('hidden');
        }
    }

    // Sayfa yüklendiğinde çalışacak fonksiyonlar
    async function initializePage() {
        console.log('🔄 Favoriler Sayfası başlatılıyor...');
        await checkUserStatus();
        await fetchAndDisplayFavorites();
        console.log('✅ Favoriler Sayfası başlatma tamamlandı.');
    }

    initializePage();
});
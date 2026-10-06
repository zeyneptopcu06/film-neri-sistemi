# 🎬 Film Öneri Sistemi

Bu proje, kullanıcılara seçilen filme benzer filmler önermek için geliştirilmiş web tabanlı bir film öneri sistemidir. Uygulama Python Flask, PostgreSQL, Docker ve içerik tabanlı öneri sistemi mantığı kullanılarak geliştirilmiştir.

## 📌 Proje Hakkında

Film Öneri Sistemi; film türü, açıklama, oyuncu ve yönetmen gibi bilgileri değerlendirerek benzer filmleri önermeyi amaçlar.

Bu proje ile backend geliştirme, veritabanı yönetimi, öneri sistemi mantığı ve Docker kullanımı üzerine pratik yapılmıştır.

## ✨ Özellikler

- Kullanıcı kayıt ve giriş işlemleri
- Film listeleme
- Film detay sayfası
- Benzer film önerileri
- Favori film ekleme ve görüntüleme
- PostgreSQL veritabanı kullanımı
- Docker ve Docker Compose desteği
- HTML, CSS ve JavaScript ile kullanıcı arayüzü

## 🧠 Öneri Sistemi Mantığı

Projede içerik tabanlı öneri sistemi kullanılmıştır. Film açıklaması, türü, oyuncuları ve yönetmeni gibi bilgiler değerlendirilerek filmler arasındaki benzerlik hesaplanır.

Amaç, kullanıcının seçtiği filme içerik olarak benzeyen filmleri önermektir.

## 🛠️ Kullanılan Teknolojiler

**Backend:** Python, Flask  
**Veritabanı:** PostgreSQL, SQL  
**Öneri Sistemi:** TF-IDF, içerik tabanlı filtreleme, benzerlik hesaplama  
**Frontend:** HTML, CSS, JavaScript, Jinja Templates  
**Araçlar:** Docker, Docker Compose, Git, GitHub, VS Code

## 📁 Proje Yapısı

- `app.py`: Ana Flask uygulaması
- `recommender_core.py`: Öneri sistemi algoritması
- `data_fetcher.py`: Film verilerini çekme işlemleri
- `docker-compose.yml`: Docker servis ayarları
- `Dockerfile`: Uygulama container ayarları
- `requirements.txt`: Python bağımlılıkları
- `templates/`: HTML sayfaları
- `static/`: CSS, JavaScript ve statik dosyalar

## ⚙️ Ortam Değişkenleri

Gizli bilgiler GitHub’a yüklenmemelidir. Bu yüzden `.env` dosyası repoda bulunmaz.

Projeyi kendi bilgisayarınızda çalıştırmak için proje klasöründe `.env` dosyası oluşturup gerekli bilgileri ekleyebilirsiniz.

Örnek değişkenler:

- `DATABASE_URL`
- `TMDB_API_KEY`
- `FLASK_SECRET_KEY`
- `SENDER_EMAIL`
- `SENDER_PASSWORD`

## 🚀 Kurulum ve Çalıştırma

Projeyi klonlayın:

```bash
git clone https://github.com/zeyneptopcu06/film-neri-sistemi.git
cd film-neri-sistemi

Docker ile çalıştırın:
docker-compose up --build

Uygulama çalıştıktan sonra tarayıcıdan şu adrese gidin:
http://localhost:8080

📚 Bu Projede Kazanılan Deneyimler
Bu proje ile şu konularda pratik yapılmıştır:
- Flask ile web uygulaması geliştirme
- PostgreSQL veritabanı kullanımı
- Film öneri sistemi mantığı
- İçerik tabanlı filtreleme
- Kullanıcı kayıt/giriş işlemleri
- Favori film sistemi
- Docker ile uygulama çalıştırma
- Ortam değişkenleriyle gizli bilgileri yönetme
- Git ve GitHub ile proje paylaşımı
👩‍💻 Geliştirici
Zeynep Topçu
Bilgisayar Mühendisliği Mezunu
GitHub: zeyneptopcu06

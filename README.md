## 📁 Proje Yapısı

```text
film-neri-sistemi/
├── app.py                  # Ana Flask uygulaması
├── recommender_core.py     # Öneri sistemi algoritması
├── data_fetcher.py         # Film verilerini çekme işlemleri
├── docker-compose.yml      # Docker servis ayarları
├── Dockerfile              # Uygulama container ayarları
├── requirements.txt        # Python bağımlılıkları
├── runtime.txt             # Çalışma ortamı ayarı
├── run_project.ps1         # Windows hızlı başlatma dosyası
├── templates/              # HTML sayfaları
├── static/                 # CSS, JavaScript ve statik dosyalar
└── README.md

⚙️ Ortam Değişkenleri
Gizli bilgiler GitHub’a yüklenmemelidir. Bu yüzden .env dosyası repoda bulunmaz.
Projeyi kendi bilgisayarınızda çalıştırmak için proje klasöründe .env dosyası oluşturup aşağıdaki değişkenleri kendi bilgilerinizle doldurabilirsiniz:
DATABASE_URL=your_database_url
TMDB_API_KEY=your_tmdb_api_key
FLASK_SECRET_KEY=your_secret_key
SENDER_EMAIL=your_email@example.com
SENDER_PASSWORD=your_app_password

.env dosyası sadece yerel bilgisayarda bulunmalıdır ve GitHub’a gönderilmemelidir.

🚀 Kurulum ve Çalıştırma
1. Projeyi Klonlama
git clone https://github.com/zeyneptopcu06/film-neri-sistemi.git
cd film-neri-sistemi

2. Ortam Değişkenlerini Ayarlama
Proje klasöründe .env dosyası oluşturun ve gerekli bilgileri ekleyin.
3. Docker ile Çalıştırma
docker-compose up --build

Uygulama çalıştıktan sonra tarayıcıdan şu adrese gidin:
http://localhost:8080

💻 Docker Olmadan Çalıştırma
Docker kullanmadan çalıştırmak isterseniz:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py

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
Bu proje, yazılım geliştirme portföyümde yer alan Python, Flask, PostgreSQL, Docker ve öneri sistemi becerilerimi gösteren bir projedir.

G

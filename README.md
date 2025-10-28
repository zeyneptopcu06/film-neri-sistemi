# 🎬 Film Öneri Sistemi: Tam Yığın (Full-Stack) Uygulama


## ✨ Proje Hakkında

Bu proje, kullanıcılara **ortak beğenilen filmlere** ve filmlerin **içerik benzerliklerine** dayalı olarak kişiselleştirilmiş ve akıllı film önerileri sunan tam yığın (full-stack) bir web uygulamasıdır. Python, JavaScript ve Docker teknolojilerini entegre ederek kolayca kurulabilir ve ölçeklenebilir bir çözüm sağlar.

---

## 💾 Veri Kaynağı

Projede kullanılan film verileri, **The Movie Database (TMDB)** platformundan çekilmiş ve yerel veritabanına kaydedilmiştir. Bu veriler, karmaşık öneri algoritmamızın temelini oluşturur.

---

## 🛠️ Teknolojiler

| Kategori | Teknoloji | Açıklama |
| :--- | :--- | :--- |
| **Backend & Algoritma** | Python, Flask | Ana uygulama mantığı ve RESTful API servisi. |
| **Veri Toplama** | TMDB API | Film meta verilerini çekmek için harici kaynak. |
| **Konteynerleştirme** | Docker, Docker Compose | Uygulama ve veritabanı servislerini izole ve taşınabilir hale getirme. |
| **Veritabanı** | PostgreSQL / SQLite | Uygulama verilerini depolama. |
| **Frontend** | HTML/CSS/JavaScript (Jinja) | Kullanıcı arayüzü ve sunum katmanı. |

---

## 📂 Proje Yapısı

| Dosya/Dizin Adı | Açıklama |
| :--- | :--- |
| `app.py` | Ana **Flask** uygulama dosyası. API rotalarını, veritabanı bağlantısını ve uygulama mantığını içerir. |
| `recommender_core.py` | **Öneri Algoritması İş Mantığı.** Film tavsiyelerini hesaplayan temel algoritmaları barındırır. |
| `docker-compose.yml` | Uygulama, Veritabanı ve diğer servislerin tek komutla kurulup bağlanmasını sağlar. |
| `requirements.txt` | Projenin çalışması için gerekli tüm **Python** kütüphane bağımlılıklarını listeler. |
| `data_fetcher.py` | Uygulamanın ihtiyacı olan verileri (filmler, kullanıcılar vb.) veritabanından çeker. |
| `Dockerfile` | Uygulama backend'inin çalışması için gereken ortamı tanımlar. |
| `templates/` | HTML şablonlarının (**Jinja2**) bulunduğu dizin. |
| `static/` | CSS, JavaScript, görseller gibi **frontend** kaynaklarının bulunduğu dizin. |
| `.env` | Ortam değişkenlerinin (Veritabanı URL'si, portlar vb.) saklandığı yapılandırma dosyası. |
| `run_project.ps1` | **Windows/PowerShell kullanıcıları için tek tıkla başlatma betiği.** |

---

## ⚙️ Kurulum ve Çalıştırma

Projenin başarıyla çalıştırılması için aşağıdaki adımları takip edin. **Docker** kullanımı, en hızlı ve sorunsuz kurulum yöntemidir.

### 1. Ön Koşullar

Projeyi çalıştırmak için sisteminizde sadece aşağıdaki araçlar kurulu olmalıdır:

* **Git**
* **Docker Desktop** (İçinde Docker Compose dahildir)

### 2. Projeyi Klonlama

Terminal (Komut İstemi, PowerShell veya WSL) üzerinden projeyi klonlayın ve dizine girin:
```bash
git clone [GITHUB_REPO_ADRESİNİZİ_BURAYA_YAZIN]
cd film-oneri-sistemi-dizini
```
### 3. Uygulamayı Başlatma Yöntemleri
Yöntem 1: Docker ile Çalıştırma (Tavsiye Edilen) 🐳

Bu yöntem, tüm bağımlılıkları, Python ortamını ve veritabanı servisini otomatik olarak kurar ve çalıştırır.

Projenin kök dizinindeyken aşağıdaki komutu çalıştırın:
```bash
docker-compose up --build
```
Yöntem 2: run_project.ps1 ile Başlatma (Windows Hızlı Başlatma) 💻

Eğer Windows kullanıyorsanız ve PowerShell üzerinden hızlıca başlatmak istiyorsanız, bu betik sanal ortamı kurar, bağımlılıkları yükler ve uygulamayı tek bir komutla başlatır:
```bash

.\run_project.ps1
```
### 4. Uygulamaya Erişim

Her iki yöntemde de servisler başarıyla başlatıldıktan sonra, uygulamaya belirlenen port üzerinden erişebilirsiniz.

Tarayıcınızı açın ve aşağıdaki adrese gidin:
```bash

http://localhost:8080
```



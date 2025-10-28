# run_project.ps1
# =============================================
# =============================================
# 2. Git ile son değişiklikleri çek
Write-Host "Git güncelleniyor..."
git pull origin main

# =============================================
# 3. Docker container'ları başlat
Write-Host "Docker container'lar başlatılıyor..."
docker-compose up -d

# =============================================
# 4. Uygulama hazır olunca tarayıcıyı aç
Start-Sleep -Seconds 5  # Container açılması için kısa bekleme
Write-Host "Tarayıcı açılıyor..."
Start-Process "http://localhost:8080"

Write-Host "Proje çalıştırıldı ✅"

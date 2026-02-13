# 🚀 GitHub'a Push Rehberi

## Mevcut Durum
✅ Git repository başlatıldı
✅ Tüm değişiklikler commit edildi
⏳ GitHub'a push edilmesi gerekiyor

## GitHub'a Push Adımları

### Senaryo 1: Mevcut GitHub Repo'ya Bağlanma

Eğer diğer PC'de zaten bir GitHub repo varsa:

```powershell
# 1. Remote ekle (GitHub repo URL'ni kullan)
git remote add origin https://github.com/KULLANICI_ADI/REPO_ADI.git

# 2. Mevcut branch'i kontrol et
git branch -M main

# 3. Push et
git push -u origin main
```

### Senaryo 2: Yeni GitHub Repo Oluşturma

1. GitHub'da yeni repo oluştur: https://github.com/new
2. Repo adı: `Leta-Takip` (veya istediğin isim)
3. Public veya Private seç
4. **README, .gitignore, license EKLEME** (zaten var)

Sonra:

```powershell
# 1. Remote ekle
git remote add origin https://github.com/KULLANICI_ADI/Leta-Takip.git

# 2. Branch'i main yap
git branch -M main

# 3. Push et
git push -u origin main
```

### Senaryo 3: Mevcut Repo'yu Güncelleme

Eğer diğer PC'deki repo zaten var ve sadece güncellemek istiyorsan:

```powershell
# 1. Remote ekle (eğer yoksa)
git remote add origin https://github.com/KULLANICI_ADI/REPO_ADI.git

# 2. Mevcut remote'u kontrol et
git remote -v

# 3. Diğer PC'deki değişiklikleri çek (eğer varsa)
git pull origin main --allow-unrelated-histories

# 4. Push et
git push -u origin main
```

## Diğer PC'de Güncelleme

Diğer PC'de şunları yap:

```powershell
# 1. Proje klasörüne git
cd "C:\Users\<Kullanıcı>\Projects\Leta-Takip-main\Leta-Takip-main"

# 2. Mevcut değişiklikleri commit et (eğer varsa)
git add .
git commit -m "Yerel değişiklikler"

# 3. GitHub'dan çek
git pull origin main

# 4. Çakışma varsa çöz, sonra push et
git push origin main
```

## Önemli Notlar

⚠️ **Veritabanı ve veriler push edilmez** (.gitignore'da)
- `*.db` dosyaları
- `veriler/` klasörü
- `build/`, `dist/` klasörleri

✅ **Push edilenler:**
- `leta_app.py` (ana kod)
- `requirements.txt` (bağımlılıklar)
- `Leta_Pipeline_Final.spec` (build config)
- `installer/`, `scripts/` (setup dosyaları)
- Dokümantasyon dosyaları

## Hızlı Komutlar

```powershell
# Durum kontrolü
git status

# Değişiklikleri göster
git diff

# Commit geçmişi
git log --oneline

# Remote kontrolü
git remote -v
```

## Sorun Giderme

### "fatal: remote origin already exists"
```powershell
git remote remove origin
git remote add origin https://github.com/KULLANICI_ADI/REPO_ADI.git
```

### "Updates were rejected"
```powershell
# Önce pull yap, sonra push
git pull origin main --rebase
git push origin main
```

### "Authentication failed"
- GitHub Personal Access Token kullan
- Veya SSH key kullan

---

**Sonraki Adım:** GitHub repo URL'ni al ve yukarıdaki komutları çalıştır!


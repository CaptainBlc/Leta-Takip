# 🔄 Diğer PC'de Güncelleme Rehberi

## Hızlı Güncelleme

Diğer PC'de şu komutları çalıştır:

```powershell
# 1. Proje klasörüne git
cd "C:\Users\<Kullanıcı>\Projects\Leta-Takip-main\Leta-Takip-main"

# 2. Develop branch'ına geç (eğer değilse)
git checkout develop

# 3. GitHub'dan en son değişiklikleri çek
git pull origin develop

# 4. Bağımlılıkları güncelle (eğer requirements.txt değiştiyse)
pip install -r requirements.txt
```

## İlk Kurulum (Eğer repo yoksa)

```powershell
# 1. Proje klasörüne git
cd "C:\Users\<Kullanıcı>\Projects"

# 2. Repo'yu klonla
git clone https://github.com/CaptainBlc/Leta-Takip.git Leta-Takip-main

# 3. Develop branch'ına geç
cd Leta-Takip-main
git checkout develop

# 4. Bağımlılıkları yükle
pip install -r requirements.txt

# 5. Test et
python leta_app.py
```

## Çakışma Durumunda

Eğer yerel değişiklikler varsa:

```powershell
# 1. Yerel değişiklikleri commit et
git add .
git commit -m "Yerel değişiklikler"

# 2. Pull yap (rebase ile)
git pull origin develop --rebase

# 3. Çakışma varsa çöz, sonra:
git add .
git rebase --continue

# 4. Push et
git push origin develop
```

## Branch Durumu Kontrolü

```powershell
# Hangi branch'tesin?
git branch

# Tüm branch'ları göster
git branch -a

# Remote branch'ları göster
git branch -r
```

## Önemli Notlar

⚠️ **Veritabanı ve veriler push edilmez**
- Veritabanı: `%LOCALAPPDATA%\LetaYonetim\leta_data.db`
- Veriler: `veriler/` klasörü

✅ **Güncellenenler:**
- `leta_app.py` - Ana kod (modül yapısı kaldırıldı)
- `requirements.txt` - Bağımlılıklar
- `Leta_Pipeline_Final.spec` - Build config
- Dokümantasyon dosyaları

## Sorun Giderme

### "fatal: couldn't find remote ref develop"
```powershell
# Remote branch'ları güncelle
git fetch origin

# Develop branch'ını oluştur ve takip et
git checkout -b develop origin/develop
```

### "Your branch is behind"
```powershell
# Pull yap
git pull origin develop
```

### "Authentication failed"
- GitHub Personal Access Token kullan
- Veya SSH key kullan

---

**Son Güncelleme:** 2026-01-24
**Branch:** develop


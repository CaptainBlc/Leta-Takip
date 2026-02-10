# 🚀 Proje Taşıma Rehberi

Bu rehber, Leta Takip projesini başka bir PC'ye taşımak için gereken adımları içerir.

## 📦 Taşınması Gereken Dosyalar

### ✅ ZORUNLU DOSYALAR (Mutlaka Taşı)

1. **Ana Kaynak Dosyaları:**
   - `leta_app.py` - Ana uygulama dosyası
   - `Leta_Pipeline_Final.spec` - PyInstaller spec dosyası
   - `requirements.txt` - Python bağımlılıkları

2. **Klasörler:**
   - `veriler/` - Excel ve DOCX veri dosyaları (ÖNEMLİ!)
   - `installer/` - Setup dosyaları (opsiyonel)
   - `scripts/` - Build scriptleri (opsiyonel)
   - `BeniOku dosyaları/` - Dokümantasyon (opsiyonel)

3. **Dokümantasyon:**
   - `KULLANIM_KILAVUZU.txt` - Kullanım kılavuzu

### ⚠️ TAŞINMAMASI GEREKEN DOSYALAR

- `build/` - Build geçici dosyaları (otomatik oluşur)
- `dist/` - Build çıktıları (yeniden build alınabilir)
- `__pycache__/` - Python cache dosyaları (otomatik oluşur)
- `*.pyc` - Python bytecode dosyaları (otomatik oluşur)
- `leta_modules/` - Artık kullanılmıyor (kod `leta_app.py` içinde)

## 🔧 Yeni PC'de Kurulum Adımları

### 1. Python Kurulumu
```bash
# Python 3.12.x kurulu olmalı
python --version
```

### 2. Proje Klasörünü Kopyala
- Tüm proje klasörünü yeni PC'ye kopyala
- Önerilen konum: `C:\Users\<KullanıcıAdı>\Projects\Leta-Takip-main\`

### 3. Python Bağımlılıklarını Yükle
```powershell
cd "C:\Users\<KullanıcıAdı>\Projects\Leta-Takip-main\Leta-Takip-main"
pip install -r requirements.txt
```

### 4. Cursor'da Projeyi Aç
- Cursor'ı aç
- File > Open Folder
- Proje klasörünü seç: `Leta-Takip-main\Leta-Takip-main`

### 5. Test Et
```powershell
python leta_app.py
```

## 📝 Önemli Notlar

### Veritabanı Konumu
- Uygulama veritabanı **OS veri klasöründe** saklanır:
  - Windows: `%LOCALAPPDATA%\LetaYonetim\leta_data.db`
  - macOS: `~/Library/Application Support/LetaYonetim/leta_data.db`
  - Linux: `~/.local/share/LetaYonetim/leta_data.db`

### Portable Mod
- Eğer veritabanını EXE yanında tutmak istersen:
  - Proje klasöründe `portable_mode.txt` dosyası oluştur (içi boş olabilir)
  - Veritabanı `leta_data.db` olarak proje klasöründe saklanır

### Veri Taşıma
- Eski PC'den veritabanını kopyalamak için:
  1. Eski PC'de: `%LOCALAPPDATA%\LetaYonetim\leta_data.db` dosyasını bul
  2. Yeni PC'de aynı konuma kopyala
  3. Veya portable mod kullan ve `leta_data.db` dosyasını proje klasörüne kopyala

## 🔨 Build Alma (Yeni PC'de)

### Windows Build
```powershell
cd "C:\Users\<KullanıcıAdı>\Projects\Leta-Takip-main\Leta-Takip-main"
pyinstaller --noconfirm --clean Leta_Pipeline_Final.spec
```

### Setup Dosyası Oluşturma
```powershell
# Inno Setup gerekli
.\scripts\build_setup.ps1
```

## ✅ Kontrol Listesi

- [ ] Python 3.12.x kurulu
- [ ] Proje klasörü kopyalandı
- [ ] `requirements.txt` bağımlılıkları yüklendi
- [ ] Cursor'da proje açıldı
- [ ] `python leta_app.py` çalıştı
- [ ] `veriler/` klasörü mevcut
- [ ] (Opsiyonel) Eski veritabanı kopyalandı

## 🆘 Sorun Giderme

### "No module named 'ttkbootstrap'"
```powershell
pip install ttkbootstrap==1.10.1
```

### "No module named 'pandas'"
```powershell
pip install pandas openpyxl
```

### Veritabanı Bulunamıyor
- İlk çalıştırmada otomatik oluşturulur
- Veya portable mod kullan

### Build Hataları
- `pyinstaller` kurulu olmalı: `pip install pyinstaller`
- Tüm bağımlılıklar yüklü olmalı

## 📞 İletişim

Sorun yaşarsan:
1. Hata mesajını kontrol et
2. `leta_error.log` dosyasını incele (veri klasöründe)
3. Cursor'ın AI asistanını kullan

---

**Son Güncelleme:** 2026-01-24
**Versiyon:** v1.3


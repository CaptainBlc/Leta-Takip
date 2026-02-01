# 🤖 Cursor AI Bağlam Dosyası

Bu dosya, Cursor AI asistanının projenin mevcut durumunu anlaması için oluşturulmuştur.

## 📋 Proje Özeti

**Proje Adı:** Leta Aile ve Çocuk - Seans & Borç Takip Sistemi  
**Versiyon:** v1.3  
**Ana Dosya:** `leta_app.py` (10,775 satır)  
**GitHub Repo:** https://github.com/CaptainBlc/Leta-Takip  
**Aktif Branch:** `develop`

## 🏗️ Mimari Yapı

### Önemli Değişiklik (v1.3)
- **Modül yapısı kaldırıldı**: `leta_modules/` klasörü artık kullanılmıyor
- **Tüm kod tek dosyada**: Tüm fonksiyonlar `leta_app.py` içinde toplandı
- **Neden?**: Modül import'ları sürekli hata veriyordu, tek dosyada daha stabil

### Dosya Yapısı
```
leta_app.py              # Ana uygulama (TÜM KOD BURADA)
requirements.txt         # Python bağımlılıkları
Leta_Pipeline_Final.spec # PyInstaller build config
veriler/                 # Excel/DOCX veri dosyaları (gitignore'da)
```

## 🔧 Teknik Detaylar

### Kullanılan Teknolojiler
- **Python 3.12.x**
- **Tkinter + ttkbootstrap** (UI framework)
- **SQLite3** (Veritabanı)
- **Pandas** (Excel işlemleri)
- **PyInstaller** (Build)

### Veritabanı Konumu
- **Windows:** `%LOCALAPPDATA%\LetaYonetim\leta_data.db`
- **macOS:** `~/Library/Application Support/LetaYonetim/leta_data.db`
- **Linux:** `~/.local/share/LetaYonetim/leta_data.db`
- **Portable Mod:** Proje klasöründe `portable_mode.txt` varsa, veritabanı proje klasöründe

### Önemli Fonksiyonlar (leta_app.py içinde)
- `connect_db()` - Veritabanı bağlantısı
- `init_db()` - Veritabanı tablolarını oluştur
- `migrate_database_data()` - Eski verileri yeni yapıya taşı
- `hesapla_personel_ucreti()` - Personel ücret hesaplama
- `get_ogrenci_personel_ucreti()` - Öğrenci-personel bazlı ücret
- `DataPipeline` class - Veri senkronizasyon sistemi

## 🐛 Bilinen Sorunlar ve Çözümler

### 1. Font Hatası (ÇÖZÜLDÜ)
- **Sorun:** `ttk.Button` widget'ında `font` parametresi desteklenmiyor
- **Çözüm:** Tüm `font` parametreleri kaldırıldı
- **Lokasyon:** `leta_app.py` içinde tüm `ttk.Button` tanımlamaları

### 2. Modül Import Hataları (ÇÖZÜLDÜ)
- **Sorun:** `leta_modules` import'ları sürekli hata veriyordu
- **Çözüm:** Tüm modül kodları `leta_app.py` içine taşındı
- **Not:** `leta_modules/` klasörü artık kullanılmıyor, silinebilir

### 3. Database Migration (ÇÖZÜLDÜ)
- **Sorun:** `hizmet_bedeli` sütunu bazı tablolarda yok
- **Çözüm:** `migrate_database_data()` fonksiyonu sütun varlığını kontrol ediyor

## 📝 Son Yapılan Değişiklikler

### v1.3 (2026-01-24)
- ✅ Modül yapısı kaldırıldı, tüm kod `leta_app.py` içinde
- ✅ Font hatası düzeltildi
- ✅ Syntax ve indentation hataları düzeltildi
- ✅ Try-except blokları düzeltildi
- ✅ GitHub'a push edildi (develop branch)

### Önceki Versiyonlar
- v1.2: Pipeline sistemi eklendi
- v1.1: Temel özellikler
- v1.0: İlk stabil versiyon

## 🚀 Build ve Dağıtım

### Windows Build
```powershell
pyinstaller --noconfirm --clean Leta_Pipeline_Final.spec
```

### Setup Dosyası
```powershell
.\scripts\build_setup.ps1
```

## 🔄 Git Workflow

- **Ana Branch:** `develop` (aktif geliştirme)
- **Production Branch:** `main` (stabil versiyonlar)
- **Commit Mesajları:** Detaylı ve açıklayıcı olmalı

## 💡 Geliştirme Notları

### Kod Stili
- Tüm kod `leta_app.py` içinde (modül yapısı yok)
- Fonksiyonlar kategorilere ayrılmış (Yardımcı, Veritabanı, Fiyatlandırma, vb.)
- Type hints kullanılıyor (`str`, `int`, `float`, vb.)

### Veri Akışı
1. **Ana Kaynak:** `seans_takvimi` tablosu
2. **Pipeline Sistemi:** `DataPipeline` class ile otomatik senkronizasyon
3. **İlgili Tablolar:** `records`, `kasa_hareketleri`, `odeme_hareketleri`, vb.

### Önemli Tablolar
- `seans_takvimi` - Ana seans kayıtları
- `danisanlar` - Danışan/öğrenci bilgileri
- `personel_ucret_takibi` - Personel ücret takibi
- `ogrenci_personel_fiyatlandirma` - Öğrenci-personel bazlı fiyatlandırma
- `kasa_hareketleri` - Kasa defteri

## 🎯 Gelecek Geliştirmeler

- [ ] Kod modülerleştirme (şu an tek dosya, ileride modüllere ayrılabilir)
- [ ] Unit testler
- [ ] Daha detaylı hata yönetimi
- [ ] Performans optimizasyonları

## 📞 Yardım

Sorun yaşarsan:
1. `leta_error.log` dosyasını kontrol et
2. Git commit geçmişine bak
3. Bu dosyayı Cursor'a göster

---

**Son Güncelleme:** 2026-01-24  
**Cursor AI için hazırlandı**


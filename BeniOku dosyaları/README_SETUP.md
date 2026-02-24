# Leta Yönetim Paneli (v1.0) - Kurulum Kılavuzu

## Sistem Gereksinimleri
- Windows 10/11 (Setup/EXE ile)
- macOS (Apple Silicon / Intel) veya Linux (Python ile ya da ilgili build ile)
- 64-bit işletim sistemi (önerilir)

## Kurulum Yöntemleri

### Yöntem 1: Setup Dosyası ile Kurulum (Önerilen)

1. `installer` klasöründeki `Leta_Yonetim_Setup_v1_0.exe` dosyasını çalıştırın
2. Kurulum sihirbazını takip edin
3. Program otomatik olarak masaüstüne kısayol oluşturacaktır

### Yöntem 2: Manuel Kurulum

1. `dist` klasöründeki `Leta_Yonetim_Paneli_v1_0.exe` dosyasını bir klasöre kopyalayın
2. EXE’yi çalıştırın

### macOS / Linux (Kaynak kod ile çalıştırma)

1. Python 3.10+ kurun
2. Bu klasörde terminal açın
3. Kurulum:
   - `python -m pip install -r requirements.txt`
4. Çalıştırma:
   - `python leta_app.py`

### macOS / Linux (Build alma)

- macOS:
  - `bash scripts/build_macos.sh 1.0`
  - çıktı: `dist/Leta_Yonetim_Paneli_v1_0.app`
- macOS (DMG):
  - `bash scripts/build_macos_dmg.sh 1.0`
  - çıktı: `dist/Leta_Yonetim_Paneli_v1_0_1.0.dmg`
- Linux:
  - `bash scripts/build_linux.sh 1.0`
  - çıktı: `dist/Leta_Yonetim_Paneli_v1_0`
- Linux (AppImage):
  - `bash scripts/build_linux_appimage.sh 1.0`
  - çıktı: `dist/Leta_Yonetim_Paneli_v1_0_1.0_x86_64.AppImage`

### macOS / Linux (Setup/Installer)

- macOS (PKG):
  - `bash scripts/build_macos_pkg.sh 1.0`
  - çıktı: `dist/Leta_Yonetim_Paneli_v1_0_1.0.pkg`
- Linux (.deb + .rpm):
  - `bash scripts/build_linux_packages.sh 1.0`
  - çıktı: `dist/` altında `.deb` ve `.rpm`

## Yeni PC’de ilk açılışta ne olur? (Önemli)
- Uygulama veriyi Program Files içine yazmaz.
- Veriler otomatik olarak şuraya gider:
  - Windows: `%LOCALAPPDATA%\LetaYonetim\`
  - macOS: `~/Library/Application Support/LetaYonetim/`
  - Linux: `~/.local/share/LetaYonetim/` (veya `$XDG_DATA_HOME/LetaYonetim/`)
  - `leta_data.db` (veritabanı)
  - `Yedekler\` (yedekler)
  - `leta_error.log` (hata günlüğü)

### İlk kurulum akışı (DB temizken)
1. Program açılır
2. Giriş ekranında **GİRİŞ** kapalı olur
3. **“İLK KURULUM (Kurum Müdürü Oluştur)”** ile ilk kullanıcı oluşturulur
4. Sonrasında çalışanlar **KAYIT OL** ile kendi hesabını açar (varsayılan: Eğitim Görevlisi)

## Setup Dosyası Oluşturma (Geliştirici)

### Otomatik (Windows - PowerShell Script ile)

1. `scripts/build_setup.ps1` dosyasını çalıştırın
2. Script otomatik olarak:
   - EXE dosyasını oluşturacak
   - Setup dosyasını oluşturacak (Inno Setup yüklüyse)

### Manuel

1. **EXE Oluşturma:**
   ```bash
   pyinstaller --clean Leta_Yonetim_Final.spec
   ```

2. **Setup Oluşturma:**
   - Inno Setup Compiler'ı indirin: https://jrsoftware.org/isdl.php
   - `installer\Leta_Setup_v1_0.iss` dosyasını Inno Setup ile açın
   - "Build > Compile" menüsünden derleyin
   - Setup dosyası `installer` klasöründe `Leta_Yonetim_Setup_v1_0.exe` olarak oluşacaktır

## Kullanım

### İlk Giriş
- İlk açılışta **Kurum Müdürü** hesabını siz oluşturursunuz (İlk Kurulum).

### Özellikler
- ✅ Yeni seans kaydı ekleme
- ✅ Borç sorgulama ve listeleme
- ✅ Ödeme ekleme (sağ tık menüsü)
- ✅ Kayıt silme
- ✅ Excel'e aktarma
- ✅ Otomatik yedekleme
- ✅ Haftalık ders/ücret takip
- ✅ Kasa defteri (günlük giren/çıkan)

### Ödeme Ekleme
1. Tabloda bir kayda sağ tıklayın
2. "Ödeme Ekle" seçeneğini seçin
3. Ödenen miktarı girin
4. Sistem otomatik olarak borcu güncelleyecektir

## Sorun Giderme

### Program açılmıyor
- Windows Defender veya antivirüs programını kontrol edin (Windows)
- macOS’ta: “Güvenlik” uyarısı çıkarsa uygulamaya izin verin
- Linux’ta: dosyaya çalıştırma izni verin (`chmod +x dist/Leta_Yonetim_Paneli_v1_0`)

### Veritabanı hatası
- Veri klasörünü kontrol edin:
  - Windows: `%LOCALAPPDATA%\LetaYonetim\`
  - macOS: `~/Library/Application Support/LetaYonetim/`
  - Linux: `~/.local/share/LetaYonetim/` (veya `$XDG_DATA_HOME/LetaYonetim/`)
- `Yedekler` klasöründen son yedeği geri yükleyin

### Excel aktarma hatası
- Microsoft Excel veya LibreOffice yüklü olmalıdır
- Alternatif olarak CSV formatı kullanılabilir (gelecek güncellemede)

## Yedekleme

Program her açılışta otomatik yedek alır. Yedekler veri klasörü içindeki `Yedekler/` klasöründe saklanır.
Son 10 yedek tutulur, eski yedekler otomatik silinir.

## Destek

Sorunlar için lütfen geliştirici ile iletişime geçin.

## Dağıtım (Windows/macOS/Linux)

- Detaylı dağıtım notları: `BeniOku dosyaları/README_DAGITIM.md`

## 📚 Dokümantasyon

### Kullanıcı İçin
- **KULLANIM_KILAVUZU.txt** - Temel kullanım rehberi
- **PIPELINE_KULLANICI_KILAVUZU.md** - Yeni pipeline sistemi hakkında

### Geliştirici İçin
- **PIPELINE_SISTEMI.md** - Pipeline mimarisi ve API dokümantasyonu
- **SORUNLAR_VE_COZUMLER.md** - Tespit edilen sorunlar ve çözümler
- **README_DAGITIM.md** - Dağıtım süreci

## 🆕 Yeni Özellik: Data Pipeline Sistemi (v1.1)

Leta Takip artık **Event-Driven Architecture** ile çalışıyor!

### Ne Değişti?
- ✅ **Seans kaydı** eklendiğinde tüm ilgili tablolar otomatik güncellenir
- ✅ **Ödeme** eklendiğinde kasa defteri otomatik senkronize olur
- ✅ **Kayıt silindiğinde** cascade silme ile tüm bağlı veriler temizlenir

### Pipeline Akışları
1. **SEANS_KAYIT:** records → seans_takvimi → kasa_hareketleri → oda_doluluk
2. **ODEME:** odeme_hareketleri → records → kasa_hareketleri → seans_takvimi
3. **SILME:** Cascade silme (tüm bağlı tablolar)

**Detaylı bilgi:** `BeniOku dosyaları/PIPELINE_SISTEMI.md`

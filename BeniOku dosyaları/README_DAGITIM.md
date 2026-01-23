# Leta – Dağıtım (Windows / macOS / Linux)

Bu doküman “build aldım, ama kullanıcıya profesyonel şekilde nasıl dağıtacağım?” sorusunu çözer.

## Windows (EXE + Setup)

- EXE + Setup üretmek için:
  - `scripts/build_setup.ps1` çalıştırın
- Çıktılar:
  - `dist\Leta_Yonetim_Paneli_v1_0.exe`
  - `installer\Leta_Yonetim_Setup_v1_0.exe`

## macOS (APP + DMG)

### 1) Build (APP)

- `bash build_macos.sh 1.0`
- `bash scripts/build_macos.sh 1.0`
- Çıktı: `dist/Leta_Yonetim_Paneli_v1_0.app`

### 2) DMG

- `bash scripts/build_macos_dmg.sh 1.0`
- Çıktı: `dist/Leta_Yonetim_Paneli_v1_0_1.0.dmg`

### 2b) PKG (Installer)

- `bash scripts/build_macos_pkg.sh 1.0`
- Çıktı: `dist/Leta_Yonetim_Paneli_v1_0_1.0.pkg`

### 3) Gatekeeper (İmzalama + Notarization) – Önerilen

macOS’ta “Bilinmeyen geliştirici” uyarısını temiz çözmenin yolu:
- Apple Developer hesabı
- Code Signing sertifikası
- Notarization

Özet akış:
- `.app` için imzala → `codesign`
- Notarization gönder → `notarytool`
- Staple → `stapler`

Not: Bu adımlar macOS üzerinde yapılır.

## Linux (Binary + AppImage)

### 1) Build (tek dosya binary)

- `bash scripts/build_linux.sh 1.0`
- Çıktı: `dist/Leta_Yonetim_Paneli_v1_0`

### 2) AppImage

- `bash scripts/build_linux_appimage.sh 1.0`
- Çıktı: `dist/Leta_Yonetim_Paneli_v1_0_1.0_x86_64.AppImage`

### 3) Linux “Setup/Installer”: .deb + .rpm

- `bash scripts/build_linux_packages.sh 1.0`
- Çıktılar: `dist/` altında `.deb` ve `.rpm`

## Linux (.deb / .rpm) – Opsiyonel

Bu repo şu an AppImage’e hazır. `.deb/.rpm` isterseniz iki yol var:

- **Kolay**: `fpm` ile paketleme
- **Temiz**: Debian/RedHat native paket yapısı (postinst, desktop entry, icon, permissions)

İsterseniz sonraki adım olarak `.deb/.rpm` için tam otomatik script ekleyebilirim.



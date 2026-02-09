# Leta Takip - Güncel Build ve Kurulum Rehberi

Bu doküman **güncel koddan** Windows ve macOS build alma akışını anlatır.

---

## 1) Hızlı Özet (En Güvenli Yol)

### Windows (lokal)
```powershell
# Repo kökünde
.\scripts\build_setup.ps1 -Version 1.3
```

### macOS (lokal)
```bash
# Repo kökünde
bash scripts/build_macos.sh 1.3
bash scripts/build_macos_dmg.sh 1.3
bash scripts/build_macos_pkg.sh 1.3
```

### Her iki platformu tek yerden (GitHub Actions)
```powershell
# Windows'tan tetikleme (gh yüklü ise)
.\scripts\build_all_auto.ps1 -Version 1.3
```

---

## 2) Ön Gereksinimler

## Windows
- Python 3.10+
- `pip install -r requirements.txt`
- Inno Setup 6+
- PowerShell

## macOS
- Python 3.10+
- `pip install -r requirements.txt`
- Xcode Command Line Tools (`xcode-select --install`)
- `pkgbuild`, `productbuild`, `hdiutil` (macOS ile gelir)

---

## 3) Windows Build (Güncel Koddan)

Script: `scripts/build_setup.ps1`

Bu script:
1. Eski `dist/build` kalıntılarını temizler,
2. `Leta_Pipeline_Final.spec` ile PyInstaller build alır,
3. Inno Setup üzerinden güncel setup EXE üretir.

Komut:
```powershell
.\scripts\build_setup.ps1 -Version 1.3
```

Beklenen çıktı:
- `dist/Leta_Takip_Setup_v1_3.exe`

---

## 4) macOS Build (Güncel Koddan)

Kullanılan scriptler:
- `scripts/build_macos.sh` → `.app`
- `scripts/build_macos_dmg.sh` → `.dmg`
- `scripts/build_macos_pkg.sh` → `.pkg`

Komutlar:
```bash
bash scripts/build_macos.sh 1.3
bash scripts/build_macos_dmg.sh 1.3
bash scripts/build_macos_pkg.sh 1.3
```

Beklenen çıktılar (dist altında):
- `Leta_Pipeline_v1_3.app`
- `Leta_Takip_1.3.dmg`
- `Leta_Pipeline_v1_3_1.3.pkg` (isim sürüme göre değişebilir)

> Not: macOS artifact üretimi yalnızca macOS üzerinde mümkündür.

---

## 5) CI/CD ile Windows + macOS Güncel Build

Workflow dosyaları:
- `.github/workflows/build-all-platforms.yml`
- `.github/workflows/build-release.yml`

Yöntem:
1. Versiyon belirle (ör: `1.3`).
2. Workflow'u manual tetikle.
3. Build tamamlanınca artifact'leri indir.

`gh` örnekleri:
```bash
gh workflow run build-all-platforms.yml -f version=1.3
gh run list --workflow=build-all-platforms.yml
gh run download <run-id>
```

---

## 6) Güncel Build Aldığını Doğrulama Checklist'i

- [ ] `git status` temiz (istenmeyen local değişiklik yok)
- [ ] Build öncesi:
  ```bash
  python -m compileall script/app_ui.py script/pipeline.py leta_app.py
  ```
- [ ] Build script başarıyla bitti
- [ ] Çıktı dosyası tarih/saati son build ile aynı
- [ ] Uygulama açılıp kritik ekranlar test edildi (Seans, Kasa, Ücret Takibi)

---

## 7) Sık Sorunlar

### Windows: Inno Setup bulunamadı
Inno Setup kurup yeniden deneyin.

### macOS: pkgbuild/productbuild bulunamadı
`xcode-select --install` çalıştırın.

### Build eski koddan alınmış görünüyor
- Build öncesi `git rev-parse --short HEAD` ile commit hash alın.
- Build sonrası uygulama hakkında ekranı/versiyon bilgisini hash'e göre doğrulayın.


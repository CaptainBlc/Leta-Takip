# GitHub Repo Düzeni ve Push Rehberi

Bu dosya, repoyu güncel **script/** sistemi ve workflow’larla düzenleyip push etmeniz için kısa rehberdir.

---

## 1. Repo yapısı (güncel)

- **Ana uygulama:** `script/` (giriş: `script/main.py`; modüller: `core/`, `app_ui.py`, ` pipeline.py`)
- **Build:** `Leta_Pipeline_Final.spec` (Windows onefile), `Leta_Pipeline_Mac.spec` (macOS .app)
- **Eski monolit:** `archive/leta_app_legacy.py` (artık kullanılmıyor)
- **Kurulum script’leri:** `installer/` (Windows .iss, macOS DMG/PKG)

---

## 2. Push öncesi kontrol listesi

- [ ] Tüm değişiklikler commit edildi
- [ ] `script/`, `installer/`, `.github/workflows/`, `Leta_Pipeline_*.spec` güncel
- [ ] `requirements.txt` güncel
- [ ] Gereksiz dosya (build/, dist/, __pycache__) commit’te yok (.gitignore’da olmalı)

---

## 3. Push adımları

```bash
# Repo kökünde
git status
git add .
# Gereksizleri ekleme: build/, dist/, __pycache__/
git add script/ installer/ .github/ Leta_Pipeline_Final.spec Leta_Pipeline_Mac.spec
git add archive/ README* TAŞINACAK_DOSYALAR.txt GITHUB_REPO_DÜZENİ.md
git add requirements.txt requirements-dev.txt
git status
git commit -m "build: script/ sistemi, macOS .app + DMG, Windows Setup, workflow güncellemesi"
git push origin develop
# veya main
git push origin main
```

---

## 4. Workflow’lar (Actions)

- **build-release.yml**  
  - Tetiklenir: `develop` veya `main` push, veya manuel (workflow_dispatch).  
  - **macOS:** `Leta_Pipeline_Mac.spec` → .app, sonra DMG. Artifact: `Leta_Takip_macOS_v1.3` (.app + .dmg).  
  - **Windows:** `Leta_Pipeline_Final.spec` → EXE, Inno Setup → Setup. Artifact: `Leta_Takip_Windows_v1.3` (.exe + Setup).

- **build-all-platforms.yml**  
  - Tetiklenir: `v*` tag push veya manuel (version input).  
  - Aynı build’ler + tag varsa **Release** oluşturur; macOS ve Windows artifact’ları release’e eklenir.

---

## 5. Kullanıcı (özellikle macOS) – güncel sürüme erişim

1. **GitHub repo** → **Actions** sekmesi.
2. Son başarılı **Build Leta Takip (Release)** veya **Build All Platforms** çalıştırmasını aç.
3. **Artifacts** bölümünden:
   - **macOS:** `Leta_Takip_macOS_v1.3` indir → ZIP’i aç → `Leta_Takip_1.3.dmg` (veya .app) ile kur.
   - **Windows:** `Leta_Takip_Windows_v1.3` indir → `Leta_Takip_Setup_v1_3.exe` ile kur.

Tag’li release varsa: Repo **Releases** sayfasından ilgili sürümü seçip macOS/Windows installer’ları oradan indirebilir.

---

## 6. Özet

- Repo güncel haliyle **script/** ve iki spec ile build alıyor.
- macOS kullanıcısı Actions artifact’larından veya Release’ten **DMG** (veya .app) ile en güncel sürüme erişir.
- Windows kullanıcısı **Setup (EXE)** ile aynı güncel sürüme erişir.

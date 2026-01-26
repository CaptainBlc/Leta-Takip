# Mac Setup Dosyaları Oluşturma Rehberi

## 🍎 Mac Setup Dosyaları Nasıl Oluşturulur?

Mac setup dosyaları oluşturmak için **macOS** gereklidir çünkü `pkgbuild`, `productbuild`, `hdiutil` gibi araçlar sadece macOS'ta bulunur.

---

## 📋 Yöntem 1: Mac'te Manuel Oluşturma

### Adım 1: Mac Build Alın

Önce PyInstaller ile Mac .app dosyası oluşturun:

```bash
cd Leta-Takip-main
pyinstaller --noconfirm --clean Leta_Pipeline_Final.spec
```

Bu işlem `dist/Leta_Pipeline_v1_3.app` dosyasını oluşturur.

### Adım 2: PKG Installer Oluşturun

```bash
# Script'i çalıştırılabilir yapın
chmod +x installer/Leta_Setup_Mac_PKG.sh

# PKG oluşturun
./installer/Leta_Setup_Mac_PKG.sh 1.3
```

**Çıktı:** `dist/Leta_Pipeline_v1_3_1.3.pkg`

### Adım 3: DMG Installer Oluşturun

```bash
# Script'i çalıştırılabilir yapın
chmod +x installer/Leta_Setup_Mac_DMG.sh

# DMG oluşturun
./installer/Leta_Setup_Mac_DMG.sh 1.3
```

**Çıktı:** `dist/Leta_Takip_1.3.dmg`

---

## 🚀 Yöntem 2: GitHub Actions ile Otomatik (Önerilen)

Mac'iniz yoksa, GitHub Actions ile otomatik oluşturabilirsiniz:

### Adım 1: GitHub Repo'ya Push Edin

```bash
git add .
git commit -m "Mac setup dosyaları için hazırlık"
git push
```

### Adım 2: GitHub Actions'ı Tetikleyin

1. GitHub repo'nuzda **Actions** sekmesine gidin
2. **"Build All Platforms"** workflow'unu seçin
3. **"Run workflow"** butonuna tıklayın
4. Version: `1.3` girin
5. **"Run workflow"** butonuna tıklayın

### Adım 3: Dosyaları İndirin

Workflow tamamlandığında:
1. **Actions** sekmesinde workflow'u açın
2. **"macos-installers"** artifact'ını indirin
3. İçinde `.app`, `.pkg` ve `.dmg` dosyaları olacak

---

## 📦 Oluşturulan Dosyalar

### PKG Installer
- **Dosya:** `Leta_Pipeline_v1_3_1.3.pkg`
- **Kullanım:** Standart macOS kurulum deneyimi
- **Kurulum:** Applications klasörüne otomatik kurulum

### DMG Installer
- **Dosya:** `Leta_Takip_1.3.dmg`
- **Kullanım:** Drag & drop kurulum
- **Kurulum:** Kullanıcı .app dosyasını Applications'a sürükler

---

## ⚠️ Gereksinimler

### Mac'te Manuel Oluşturma İçin:
- ✅ macOS işletim sistemi
- ✅ Xcode Command Line Tools (`xcode-select --install`)
- ✅ Python 3.11+
- ✅ PyInstaller
- ✅ Tüm Python bağımlılıkları

### GitHub Actions İçin:
- ✅ GitHub hesabı
- ✅ Repo'ya push yetkisi
- ✅ Actions özelliği aktif

---

## 🔧 Sorun Giderme

### "pkgbuild bulunamadı" hatası:
```bash
xcode-select --install
```

### "Permission denied" hatası:
```bash
chmod +x installer/*.sh
```

### Build hatası:
- Python bağımlılıklarını kontrol edin: `pip install -r requirements.txt`
- PyInstaller'ın güncel olduğundan emin olun: `pip install --upgrade pyinstaller`

---

## 📞 Destek

Sorunlar için proje yöneticisine başvurun.



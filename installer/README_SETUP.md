# Leta Takip - Setup Dosyaları

Bu klasör Windows ve macOS için kurulum dosyalarını içerir.

## 📦 Windows Setup (Inno Setup)

### Gereksinimler
- [Inno Setup](https://jrsoftware.org/isdl.php) (ücretsiz)
- Windows işletim sistemi
- `dist/Leta_Pipeline_v1_3.exe` dosyası (PyInstaller build)

### Kullanım

1. **Inno Setup'ı yükleyin:**
   - https://jrsoftware.org/isdl.php adresinden indirin
   - Kurulum sırasında "Inno Setup Preprocessor" seçeneğini işaretleyin

2. **Setup dosyasını derleyin:**
   - `Leta_Setup_Windows.iss` dosyasını Inno Setup ile açın
   - `Build > Compile` menüsünden derleyin
   - Veya komut satırından:
     ```powershell
     "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" Leta_Setup_Windows.iss
     ```

3. **Çıktı:**
   - `../dist/Leta_Takip_Setup_v1_3.exe` dosyası oluşturulur

### Özellikler
- ✅ Modern kurulum sihirbazı
- ✅ Türkçe dil desteği
- ✅ Masaüstü kısayolu (opsiyonel)
- ✅ Başlangıç menüsü kısayolu
- ✅ Kullanım kılavuzu dahil
- ✅ Otomatik kaldırma desteği

---

## 🍎 macOS Setup (PKG & DMG)

### Gereksinimler
- macOS işletim sistemi
- Xcode Command Line Tools
- `dist/Leta_Pipeline_v1_3.app` dosyası (PyInstaller build)

### PKG Installer

1. **Script'i çalıştırılabilir yapın:**
   ```bash
   chmod +x installer/Leta_Setup_Mac_PKG.sh
   ```

2. **PKG oluşturun:**
   ```bash
   cd Leta-Takip-main
   ./installer/Leta_Setup_Mac_PKG.sh 1.3
   ```

3. **Çıktı:**
   - `dist/Leta_Pipeline_v1_3_1.3.pkg` dosyası oluşturulur

### DMG Installer

1. **Script'i çalıştırılabilir yapın:**
   ```bash
   chmod +x installer/Leta_Setup_Mac_DMG.sh
   ```

2. **DMG oluşturun:**
   ```bash
   cd Leta-Takip-main
   ./installer/Leta_Setup_Mac_DMG.sh 1.3
   ```

3. **Çıktı:**
   - `dist/Leta_Takip_1.3.dmg` dosyası oluşturulur

### Özellikler

**PKG:**
- ✅ Standart macOS kurulum deneyimi
- ✅ Applications klasörüne otomatik kurulum
- ✅ Kullanım kılavuzu dahil

**DMG:**
- ✅ Drag & drop kurulum
- ✅ Applications linki dahil
- ✅ Kullanıcı dostu arayüz

---

## 🔧 Build Sırası

1. **PyInstaller ile executable oluştur:**
   ```bash
   # Windows
   pyinstaller --noconfirm --clean Leta_Pipeline_Final.spec
   
   # macOS
   pyinstaller --noconfirm --clean Leta_Pipeline_Final.spec
   ```

2. **Setup dosyasını oluştur:**
   ```bash
   # Windows (Inno Setup ile)
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\Leta_Setup_Windows.iss
   
   # macOS PKG
   ./installer/Leta_Setup_Mac_PKG.sh 1.3
   
   # macOS DMG
   ./installer/Leta_Setup_Mac_DMG.sh 1.3
   ```

---

## 📝 Notlar

- Windows setup dosyası için Inno Setup 6+ önerilir
- macOS setup dosyaları sadece macOS'ta oluşturulabilir
- Her iki platform için de önce PyInstaller build alınmalıdır
- Version numarası script parametresi olarak verilebilir

---

## 🐛 Sorun Giderme

### Windows
- **"ISCC.exe bulunamadı" hatası:** Inno Setup'ın kurulu olduğu yolu kontrol edin
- **"EXE dosyası bulunamadı" hatası:** Önce PyInstaller build alınmalı

### macOS
- **"pkgbuild bulunamadı" hatası:** Xcode Command Line Tools yükleyin:
  ```bash
  xcode-select --install
  ```
- **"Permission denied" hatası:** Script'i çalıştırılabilir yapın:
  ```bash
  chmod +x installer/*.sh
  ```

---

## 📞 Destek

Sorunlar için proje yöneticisine başvurun.


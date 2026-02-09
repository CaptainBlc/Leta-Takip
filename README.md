# Leta Takip

Seans ve ödeme takip uygulaması (Leta Aile ve Çocuk).  
Güncel sürüm: **script/** yapısı (Python 3.11+, Tkinter, ttkbootstrap, SQLite).

---

## En güncel sürüme erişim (kurulum)

### macOS kullanıcıları

1. Bu repoda **Actions** sekmesine gidin.
2. Son başarılı **"Build Leta Takip (Release)"** veya **"Build All Platforms"** çalıştırmasını açın.
3. **Artifacts** bölümünden **Leta_Takip_macOS_v1.3** indirin (ZIP).
4. ZIP’i açın; **Leta_Takip_1.3.dmg** (veya **Leta_Pipeline_v1_3.app**) ile kurulumu yapın.
5. DMG’yi açıp uygulamayı **Applications** klasörüne sürükleyin.

**Sürüm etiketli release varsa:** Repo ana sayfasında **Releases** → ilgili sürüm → macOS DMG/APP indirin.

### Windows kullanıcıları

1. **Actions** → son başarılı build → **Leta_Takip_Windows_v1.3** artifact’ını indirin.
2. **Leta_Takip_Setup_v1_3.exe** ile kurulumu çalıştırın.

---

## Kaynaktan çalıştırma

```bash
# Bağımlılıklar
pip install -r requirements.txt

# Uygulama (repo kökünden)
python script/main.py

# veya script dizininden
cd script && python main.py
```

---

## Repo düzeni ve build

- **Giriş noktası:** `script/main.py`
- **Build:** Windows → `Leta_Pipeline_Final.spec` (onefile EXE). macOS → `Leta_Pipeline_Mac.spec` (.app, DMG/PKG için).
- **Detay:** `GITHUB_REPO_DÜZENİ.md`, `TAŞINACAK_DOSYALAR.txt`, `installer/README_SETUP.md`.

---

© Leta Aile ve Çocuk

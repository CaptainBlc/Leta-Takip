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

### Windows kullanıcıları

1. **Actions** → son başarılı build → **Leta_Takip_Windows_v1.3** artifact’ını indirin.
2. **Leta_Takip_Setup_v1_3.exe** ile kurulumu çalıştırın.

---

## Kaynaktan çalıştırma

```bash
pip install -r requirements.txt
python script/main.py
```

---

## Build

- **Giriş noktası:** `script/main.py`
- **Windows:** `pyinstaller --noconfirm --clean Leta_Pipeline_Final.spec`
- **macOS:** `pyinstaller --noconfirm --clean Leta_Pipeline_Mac.spec`
- **Kurulum scriptleri:** `installer/`

---

## Repo düzeni

- `script/` → aktif uygulama kodu
- `installer/` → Windows/macOS installer scriptleri
- `scripts/` → yardımcı build/test scriptleri
- `legacy/` → eski/monolitik yapı ve tarihsel dökümanlar

---

© Leta Aile ve Çocuk

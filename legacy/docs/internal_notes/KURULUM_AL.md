# Kurulum Al – Yarın Setup Yapıp Test Etmek İçin

Bu rehber, yarın **Leta Takip** kurulum dosyasını (setup) oluşturup test etmeniz için adımları özetler.

---

## Gereksinimler (Bu bilgisayarda olmalı)

1. **Python 3.10+** – [python.org](https://www.python.org/downloads/)
2. **pip** – Python ile gelir
3. **PyInstaller** – EXE oluşturmak için  
   ```powershell
   pip install pyinstaller
   ```
4. **Inno Setup 6** (setup .exe için) – [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)  
   Kurulumda varsayılan yolu kullanın: `C:\Program Files (x86)\Inno Setup 6\`

Proje bağımlılıkları (EXE içine girecek):

```powershell
pip install -r requirements.txt
pip install tkcalendar
```

---

## Tek komutla build (Önerilen)

Proje kök klasöründe (Leta-Takip) PowerShell açıp:

```powershell
.\scripts\build_setup.ps1
```

Bu script:

1. **PyInstaller** ile `leta_app.py` → `dist\Leta_Pipeline_v1_3.exe` oluşturur (2–3 dk).
2. **Inno Setup** varsa `dist\Leta_Takip_Setup_v1_3.exe` kurulum dosyasını oluşturur.

Çıktılar:

- `dist\Leta_Pipeline_v1_3.exe` – Tek başına çalışan uygulama (her zaman oluşur)
- `dist\Leta_Takip_Setup_v1_3.exe` – Kurulum sihirbazı (Inno Setup kuruluysa oluşur)

---

## Adım adım (Script kullanmadan)

### 1) EXE oluştur

```powershell
cd C:\Users\Pc\Desktop\Leta_Takip\Leta-Takip
pyinstaller --noconfirm --clean Leta_Pipeline_Final.spec
```

Kontrol: `dist\Leta_Pipeline_v1_3.exe` dosyası oluşmalı.

### 2) Setup oluştur (Inno Setup kuruluysa)

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\Leta_Setup_Windows.iss
```

Kontrol: `dist\Leta_Takip_Setup_v1_3.exe` oluşmalı.

---

## Yarın test etmek için

1. **Setup ile test**
   - `dist\Leta_Takip_Setup_v1_3.exe` dosyasını çalıştırın.
   - Kurulumu tamamlayın (klasör: `C:\Program Files\LetaTakip` veya seçtiğiniz yer).
   - “Kurulum bitince uygulamayı çalıştır” seçeneği işaretliyse uygulama açılır.
   - Giriş ekranı, seans takip, danışan listesi vb. kısa bir kullanım testi yapın.

2. **Sadece EXE ile test**
   - `dist\Leta_Pipeline_v1_3.exe` dosyasına çift tıklayın.
   - Aynı şekilde giriş ve temel işlevleri test edin.

---

## Sık karşılaşılan durumlar

| Durum | Çözüm |
|--------|--------|
| “EXE dosyası oluşturulamadı” | `pip install -r requirements.txt` ve `pip install pyinstaller tkcalendar` yapın. Sonra `.\scripts\build_setup.ps1` tekrar çalıştırın. |
| “Inno Setup bulunamadı” | EXE yine oluşur; setup için [Inno Setup](https://jrsoftware.org/isdl.php) kurun ve script’i tekrar çalıştırın. |
| “Leta_Pipeline_v1_3.exe bulunamadı” (Inno hatası) | Önce 1. adımı (PyInstaller) çalıştırıp `dist\Leta_Pipeline_v1_3.exe` oluştuğundan emin olun. |
| Uygulama açılmıyor / hata veriyor | `dist\Leta_Pipeline_v1_3.exe`’yi PowerShell’den çalıştırıp konsoldaki hata mesajını not alın. |

---

## Özet

- **Yarın yapmanız gereken:** Proje klasöründe `.\scripts\build_setup.ps1` çalıştırıp ardından `dist\Leta_Takip_Setup_v1_3.exe` ile kurulum ve uygulama testi.
- **Dosya konumları:** EXE ve setup ikisi de `dist\` klasöründe oluşur.

İyi testler.

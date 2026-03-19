# Leta Takip

**Özel eğitim ve danışmanlık kurumları için masaüstü operasyon paneli** — seans planlama, borç/ödeme, kasa defteri ve personel ücret takibini tek uygulamada toplar.  
Veriler yalnızca kurumun kendi bilgisayarında, **yerel SQLite** veritabanında tutulur; arayüz **Tkinter** ve **ttkbootstrap** ile geliştirilmiştir.

*Desktop ops center for education and counseling practices — sessions, billing, cash ledger, and staff payouts. Local-first SQLite; Tkinter + ttkbootstrap.*

[![Build All Platforms](https://github.com/CaptainBlc/Leta-Takip/actions/workflows/build-all-platforms.yml/badge.svg)](https://github.com/CaptainBlc/Leta-Takip/actions/workflows/build-all-platforms.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)

---

## Gizlilik ve veri

- Bu depoda **gerçek danışan, kurum veya mali kayıt bulunmaz**; yalnızca uygulama kaynak kodu ve kurulum/dağıtım dosyaları yer alır.
- Çalışma zamanında oluşan veritabanı, yedekler ve kurumsal dosyalar **bilgisayarda yerel olarak** saklanır; bunları repoya eklemeyin (ör. `*.db`, `Yedekler/`, `veriler/` zaten `.gitignore` ile dışarıda).

---

## Öne çıkanlar

| Alan | Özet |
|------|------|
| **Seans** | Tarih, saat, oda ve uzman bazında planlama ve kayıt |
| **Muhasebe** | Borç/kalan, ödemeler, haftalık alındı / alınmadı |
| **Kasa** | Günlük gelir–gider ve raporlanabilir kasa |
| **Personel** | Seans bazlı hakediş ve ödeme durumu |
| **Yedekleme** | Açılışta otomatik yedek; sınırlı sayıda yedek tutma (rotasyon) |
| **Akıllı varsayılanlar** | Danışan ve uzman seçimine göre tutar/oda önerileri |

---

## Teknoloji özeti

- Python 3.11 · Tkinter, ttkbootstrap, tkcalendar · SQLite · pandas / openpyxl / ReportLab  
- Paketleme: PyInstaller, Inno Setup (Windows), macOS DMG/PKG betikleri  
- CI: GitHub Actions (etiket veya manuel tetikleme ile derleme)

---

## Hızlı başlangıç

### Kurulum (son kullanıcı)

1. [Releases](https://github.com/CaptainBlc/Leta-Takip/releases) sayfasından güncel **Windows** kurulum paketini indirin.  
2. Kurulum sihirbazını tamamlayıp uygulamayı başlatın.

Diğer platformlar ve kurulum ayrıntıları: [installer/README_SETUP](installer/README_SETUP.md).

### Kaynak koddan çalıştırma (geliştirici)

```bash
git clone https://github.com/CaptainBlc/Leta-Takip.git
cd Leta-Takip
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python -m script.main
```

İsteğe bağlı araçlar: `pip install -r requirements-dev.txt`

---

## Depo özeti

| Yol | Açıklama |
|-----|----------|
| `script/` | Uygulama: giriş noktası, arayüz, iş mantığı ve `core/` altyapısı |
| `scripts/` | Çoklu platform derleme ve yardımcı betikler |
| `installer/` | Windows/macOS kurulum tanımları |
| `packaging/linux/` | Linux masaüstü girişi |
| `KULLANIM_KILAVUZU.txt` | Son kullanıcı için kısa kullanım özeti |

Ek Türkçe teknik notlar geliştiriciler için `BeniOku dosyaları/` altında tutulmaktadır (kurulum, dağıtım, mimari); **herhangi bir kuruma özel veri içermez**.

---

## Derleme

- [`.github/workflows/build-all-platforms.yml`](.github/workflows/build-all-platforms.yml)  
- Yerel Windows: `scripts/build_setup.ps1` (Inno Setup gerekir)

---

## Geri bildirim

Hata bildirimlerinde işletim sistemi ve tekrarlanabilir adımları paylaşmanız yardımcı olur. **Ekran görüntüsü veya log eklerken kurum/danışan bilgisi içermediğinden emin olun.**

---

## Lisans

[MIT](LICENSE)

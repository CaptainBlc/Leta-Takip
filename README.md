# Leta Takip

**Özel eğitim merkezleri ve danışmanlık ofisleri için masaüstü yönetim paneli** — seans planlama, borç/ödeme, kasa defteri ve personel ücret takibini tek yerden yönetir. Veriler yerelde **SQLite** ile saklanır; arayüz **Tkinter** ve **ttkbootstrap** ile hazırlanmıştır.

*Desktop management app for therapy / education centers — session scheduling, billing, cash ledger, and staff compensation. Local-first SQLite; Tkinter + ttkbootstrap UI.*

[![Build All Platforms](https://github.com/CaptainBlc/Leta-Takip/actions/workflows/build-all-platforms.yml/badge.svg)](https://github.com/CaptainBlc/Leta-Takip/actions/workflows/build-all-platforms.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)

---

## Öne çıkanlar

| Alan | Ne sunuyor? |
|------|-------------|
| **Seans** | Tarih, saat, oda ve terapist bazında planlama ve kayıt |
| **Muhasebe** | Danışan borç/kalan, ödeme girişleri, haftalık alındı/alınmadı |
| **Kasa** | Günlük giren–çıkan, raporlanabilir kasa yapısı |
| **Personel** | Seans başı hakediş ve ödeme durumu |
| **Yedekleme** | Açılışta otomatik yedek, eski yedekleri temizleme |
| **Pipeline** | Danışan + terapist kombinasyonuna göre akıllı fiyat önerileri (`script/pipeline.py`) |

---

## Teknolojiler

- **Dil:** Python 3.11 (3.10+ uyumlu)
- **Arayüz:** Tkinter, ttkbootstrap, tkcalendar
- **Veri:** SQLite (pandas/openpyxl ile rapor/Excel; ReportLab ile PDF)
- **Dağıtım:** PyInstaller (`Leta_Pipeline_Final.spec`), Inno Setup (Windows), macOS DMG/PKG betikleri
- **CI:** GitHub Actions — `v*` etiketi veya manuel tetikleme ile Windows yapıları

---

## Hızlı başlangıç

### Son kullanıcı (kurulum)

1. [Releases](https://github.com/CaptainBlc/Leta-Takip/releases) üzerinden güncel **Windows** kurulum paketini indirin (ör. `Leta_Takip_Setup_v*.exe`).
2. Kurulumu tamamlayıp masaüstü kısayolundan başlatın.

macOS / Linux ve gelişmiş kurulum: [README_DAGITIM](BeniOku%20dosalar%C4%B1/README_DAGITIM.md) ve [installer/README_SETUP](installer/README_SETUP.md).

### Geliştirici

```bash
git clone https://github.com/CaptainBlc/Leta-Takip.git
cd Leta-Takip
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python -m script.main
```

İsteğe bağlı geliştirme araçları: `pip install -r requirements-dev.txt`

---

## Depo yapısı

| Yol | İçerik |
|-----|--------|
| `script/` | Uygulama kodu: `main.py` (giriş), `app_ui.py` (arayüz), `pipeline.py` (olay tabanlı veri akışı), `core/` (DB, yedek, log, platform, güvenlik vb.) |
| `scripts/` | Derleme betikleri (Windows/Linux/macOS), test ve örnek PDF üretimi |
| `installer/` | Inno Setup (`.iss`), macOS DMG/PKG kabuk betikleri |
| `packaging/linux/` | Linux masaüstü girişi ve paketleme yardımcıları |
| `BeniOku dosyaları/` | Dağıtım, pipeline, kurulum ve mimari notları (Türkçe dokümantasyon indeksi aşağıda) |
| `KULLANIM_KILAVUZU.txt` | Son kullanıcı için kısa kullanım özeti |
| `cocuk_takip_formu_pdf_ornegi.py` | Örnek çocuk takip formu PDF üretimi (tek dosya yardımcı script) |

---

## Dokümantasyon (seçilmiş)

- **Dağıtım:** [README_DAGITIM](BeniOku%20dosalar%C4%B1/README_DAGITIM.md)  
- **Kurulum / setup:** [README_SETUP (BeniOku)](BeniOku%20dosalar%C4%B1/README_SETUP.md) · [installer/README_SETUP](installer/README_SETUP.md)  
- **Pipeline:** [PIPELINE_SISTEMI](BeniOku%20dosalar%C4%B1/PIPELINE_SISTEMI.md) · [PIPELINE_KULLANICI_KILAVUZU](BeniOku%20dosalar%C4%B1/PIPELINE_KULLANICI_KILAVUZU.md)  
- **Sistem özeti:** [SISTEM_ACIKLAMALARI](BeniOku%20dosalar%C4%B1/SISTEM_ACIKLAMALARI.md)

Tam liste için `BeniOku dosyaları/` klasörüne göz atın.

---

## Build ve sürüm

- Workflow: [.github/workflows/build-all-platforms.yml](.github/workflows/build-all-platforms.yml)
- `v*` biçiminde etiket iterek veya **Actions** üzerinden **workflow dispatch** ile derleme alınabilir.
- Yerel Windows derlemesi için: `scripts/build_setup.ps1` (Inno Setup gerekir).

---

## Katkı ve geri bildirim

Sorun bildirirken işletim sistemi, tekrar adımları ve mümkünse log/ekran görüntüsü eklemeniz çözümü hızlandırır.

---

## Lisans

Bu proje [MIT](LICENSE) lisansı ile sunulmaktadır.

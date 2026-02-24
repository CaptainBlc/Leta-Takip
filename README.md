## Leta Takip

[![Build All Platforms](https://github.com/CaptainBlc/Leta-Takip/actions/workflows/build-all-platforms.yml/badge.svg)](https://github.com/CaptainBlc/Leta-Takip/actions/workflows/build-all-platforms.yml)

Leta Takip; özel eğitim merkezleri, danışmanlık ofisleri ve benzeri kurumlar için geliştirilmiş, **seans / borç / kasa / personel ücret takibi** yapan masaüstü bir uygulamadır.  
Modern arayüzü `ttkbootstrap` ile Tkinter üzerinde çalışır ve verilerini yerel SQLite veritabanında saklar.

---

## Özellikler

- **Seans Takibi**: Tarih, saat, oda ve terapist bazında seans planlama
- **Borç ve Ödeme Yönetimi**: Danışan bazlı borç/kalan tutar takibi, ödeme girişleri
- **Kasa Defteri**: Günlük giren–çıkan hareketleri, raporlanabilir kasa yapısı
- **Personel Ücret Takibi**: Seans başı hakediş hesaplama ve ödeme durumları
- **Otomatik Yedekleme**: Açılışta otomatik yedek alma ve eski yedekleri temizleme
- **Akıllı Fiyatlama (Pipeline)**: Danışan + terapist kombinasyonuna göre akıllı hizmet bedeli önerileri

---

## Kurulum ve Çalıştırma

### Son Kullanıcı (Önerilen)

- **Windows**:
  - GitHub **Releases** sekmesinden en güncel `Leta_Takip_Setup_v1_3.exe` dosyasını indirin.
  - Setup’ı çalıştırın, kurulumu tamamlayın.
  - Masaüstündeki kısayoldan uygulamayı açın.

macOS ve Linux için detaylı dağıtım notları: `BeniOku dosyaları/README_DAGITIM.md`

### Geliştirici Kurulumu

Gereksinimler:
- Python 3.11 (veya uyumlu 3.10+)
- `git`

Adımlar:

```bash
git clone https://github.com/CaptainBlc/Leta-Takip.git
cd Leta-Takip
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Uygulamayı geliştirme modunda çalıştırmak için:

```bash
python -m script.main
```

---

## Proje Yapısı (özet)

- `script/`
  - `main.py` – Uygulamanın giriş noktası
  - `app_ui.py` – Tkinter + ttkbootstrap arayüzü (App sınıfı)
  - `pipeline.py` – Event-driven data pipeline (seans, borç, kasa, personel akışları)
  - `core/` – Veritabanı, yedekleme, loglama, ikonlar, platform uyarlamaları vb.
- `BeniOku dosyaları/`
  - `README_SETUP.md` – Kurulum/dağıtım dokümantasyonu
  - `README_DAGITIM.md` – Platform bazlı dağıtım detayları
- `.github/workflows/`
  - GitHub Actions CI/CD tanımları (Windows/macOS build ve release)
- `requirements.txt`, `requirements-dev.txt`
  - Çalışma ve geliştirme bağımlılıkları

---

## Build ve Release

Projede otomatik build almak için GitHub Actions kullanılır:

- **Windows**: PyInstaller ile tek dosya `.exe` ve isteğe bağlı Setup oluşturma
- **macOS**: `.app` ve `.dmg` üretimi
- (İsteğe bağlı) Linux paketleri – legacy script’ler üzerinden

Workflow detayları için `.github/workflows/` klasörüne bakabilirsiniz.

---

## Katkıda Bulunma

Şu an proje öncelikli olarak gerçek kurumsal kullanımlar için geliştiriliyor.  
Issue veya öneri açarken mümkün olduğunca:

- Kullandığınız işletim sistemini,
- Hatanın tekrar üretim adımlarını,
- Varsa log veya ekran görüntüsünü

eklemeniz, geri dönüş sürecini hızlandıracaktır.


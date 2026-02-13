# 🤖 Gemini AI İçin Sistem Durumu Prompt'u

Bu dosya Gemini AI ile sohbet ederken sistemin mevcut durumunu anlatmak için hazırlanmıştır.

---

## 📝 Gemini'ye Göndereceğin Prompt (Kopyala-Yapıştır)

```
Merhaba Gemini! Ben Leta Takip adında bir Python uygulaması üzerinde çalışıyorum ve sana sistemin mevcut durumunu anlatmak istiyorum. Bu bilgilerle birlikte gelecekte bana daha iyi yardımcı olabilirsin.

## PROJE BİLGİLERİ

**Proje Adı:** Leta Aile ve Çocuk - Seans & Borç Takip Sistemi
**Versiyon:** v1.4 (Enterprise Grade + Predictive Dashboard)
**Ana Dosya:** leta_app.py (yaklaşık 15,022 satır - monolitik yapı)
**Dil:** Python 3.12+
**UI Framework:** ttkbootstrap (Tkinter tabanlı modern UI)
**Veritabanı:** SQLite3

## MİMARİ YAPI

### Önemli Not:
- **Monolitik Yapı:** Tüm kod tek bir dosyada (leta_app.py)
- **Neden Monolitik?** Modül yapısı import hatalarına yol açıyordu, tek dosyada daha stabil
- **Data Pipeline Architecture:** Event-driven mimari ile tüm tablolar birbirinden haberdar

### Ana Sınıf: DataPipeline
Sistemin kalbi olan `DataPipeline` sınıfı var. Bu sınıf:
- Seans kayıtları eklerken tüm ilgili tabloları otomatik günceller
- Ödeme eklerken kasa, borç takibi, seans durumu gibi tüm tabloları senkronize eder
- Kayıt silerken cascade silme yapar (tüm bağlı kayıtlar temizlenir)

**Örnek Kullanım:**
```python
pipeline = DataPipeline(conn, kullanici_id)
seans_id = pipeline.seans_kayit(
    tarih="2026-01-28",
    saat="14:00",
    danisan_adi="AHMET YILMAZ",
    terapist="Pervin Hoca",
    hizmet_bedeli=3500.0,
    alinan_ucret=1000.0,
    notlar="İlk seans",
    oda="Oda 1"
)
```

Bu tek çağrı şunları otomatik yapar:
- records tablosuna kayıt
- seans_takvimi tablosuna kayıt
- kasa_hareketleri tablosuna giriş (eğer ödeme varsa)
- odeme_hareketleri tablosuna kayıt
- cocuk_gunluk_takip tablosuna otomatik kayıt
- personel_ucret_takibi tablosuna otomatik kayıt
- pricing_policy tablosunu günceller (gelecek seanslar için)
- danisanlar.balance güncellenir

## VERİTABANI YAPISI

### Ana Tablolar:
1. **seans_takvimi** - ANA KAYNAK (Source of Truth)
   - Her seans kaydının merkezi kaydı
   - record_id ile records tablosuna bağlı

2. **records** - Seans detayları ve borç takibi
   - hizmet_bedeli, alinan_ucret, kalan_borc
   - seans_id ile seans_takvimi'ne bağlı

3. **danisanlar** - Danışan bilgileri
   - ad_soyad, telefon, email, balance
   - Aktif/pasif durumu

4. **kasa_hareketleri** - Kasa defteri
   - Gelir/gider kayıtları
   - record_id ve seans_id ile bağlı

5. **odeme_hareketleri** - Ödeme geçmişi
   - Her ödeme kaydı
   - record_id ile bağlı

6. **personel_ucret_takibi** - Personel ücret takibi
   - Her seans için personel ücreti
   - seans_id ile bağlı

7. **cocuk_gunluk_takip** - Çocuk günlük oda-personel takibi
   - Hangi çocuk hangi odada hangi personel ile çalıştı
   - seans_id ile bağlı

8. **pricing_policy** - Fiyatlandırma politikası
   - student_id, teacher_name, price
   - Gelecek seanslar için otomatik fiyat atama
   - Fiyatlandırma güncellendiğinde otomatik güncellenir

9. **ogrenci_personel_fiyatlandirma** - Öğrenci-Personel bazlı fiyatlandırma
   - ogrenci_id, personel_adi, seans_ucreti, baslangic_tarihi, bitis_tarihi, zam_orani
   - Fiyatlandırma penceresinden güncellenir
   - pricing_policy ile senkronize çalışır

10. **haftalik_seans_programi** - Haftalık program
    - personel_adi, gun, saat, ogrenci_adi, oda_adi
    - Otomatik oda seçimi için kullanılır

11. **users** - Kullanıcı yönetimi
    - kullanici_adi, sifre (hash), yetki, terapist_adi, access_role

12. **audit_trail** - Sistem denetim izi (Enterprise Feature)
    - action_type, entity_type, entity_id, kullanici_id, details (JSON), olusturma_tarihi
    - Tüm kritik işlemler buraya kaydedilir
    - Smart Logs UI'ında görüntülenir

## ÖNEMLİ ÖZELLİKLER

### 1. Smart Defaults (Akıllı Varsayılanlar) - Zero-Effort UI
- Kullanıcı danışan ve terapist seçtiğinde, sistem otomatik olarak:
  - `pricing_policy` veya `ogrenci_personel_fiyatlandirma`'dan fiyatı çeker ve "Hizmet Bedeli" alanını doldurur
  - `haftalik_seans_programi`'nden odayı bulur ve "Oda" alanını doldurur
  - Oda çakışması kontrolü yapar, varsa alternatif odalar önerir
- Kullanıcı sadece "Kaydet" butonuna basması yeterli
- **ÖNEMLİ:** Seans kayıt edildiğinde `seans_alindi=0` ve `durum="planlandi"` olarak başlar - kullanıcı manuel olarak seans durumunu belirler

### 2. Yetki Sistemi
- **Kurum Müdürü:** 
  - Tüm verilere erişim
  - Sistem Günlüğü (Smart Logs) görüntüleme
  - Tüm dashboard metrikleri
- **Eğitim Görevlisi:** 
  - Sadece kendi terapist adına veriler
  - Personel Cüzdanı görüntüleme (kendi bakiyesi)
  - Sistem Günlüğü görüntüleme YOK
- **Normal Kullanıcı:** Sadece kendi seansları

### 3. Veri İçe Aktarma
- 3 ayrı Excel template'i:
  - Danışanlar Template
  - Haftalık Seans Takvimi Template
  - Seans Ücret Takip Template

### 4. PDF Raporlama
- BEP (Bireysel Eğitim Programı) raporları
- Onam Formu raporları
- Çocuk Takip Bilgi Formu raporları
- Türkçe karakter desteği (Segoe UI / DejaVu Sans)

### 5. Enterprise Dashboard (Executive Summary)
- **Operasyonel Metrikler:** Bugün beklenen/tamamlanan seanslar
- **Finansal Metrikler:** Bugün kasa giren, beklenen toplam alacak
- **Kırmızı Liste:** Ödemesi geciken danışanlar (öncelik seviyeleri: kritik/yüksek/orta)
- **Devamsızlık Alarmı:** Üst üste 3+ seans gelmeyen danışanlar

### 6. Personel Cüzdanı
- Terapistlerin kendi bakiyelerini görebilmesi
- Beklemede ve ödenen hak edişlerin özeti
- Sadece Eğitim Görevlisi için görünür

### 7. Smart Logs (Sistem Günlüğü)
- Tüm kritik işlemlerin audit trail'i
- Tarih, kullanıcı ve işlem tipi bazlı filtreleme
- Sadece Kurum Müdürü için görünür

## TEKNİK DETAYLAR

### UI Katmanı
- **ttkbootstrap** kullanılıyor (modern görünüm)
- **Önemli:** ttk.Button widget'larında `font` parametresi kullanılmıyor (hata veriyor)
- Tek root window yaklaşımı (stabilite için)

### Veritabanı Konumu
- Windows: `%LOCALAPPDATA%\LetaYonetim\leta_data.db`
- macOS: `~/Library/Application Support/LetaYonetim/leta_data.db`
- Linux: `~/.local/share/LetaYonetim/leta_data.db`
- Portable mod: Proje klasöründe `portable_mode.txt` varsa, veritabanı proje klasöründe

### Bağımlılıklar
- pandas (Excel işlemleri)
- ttkbootstrap (UI)
- reportlab (PDF oluşturma)
- openpyxl (Excel formatlama)

## SON YAPILAN DEĞİŞİKLİKLER

### Enterprise Grade Transformation (28 Ocak 2026)
1. ✅ **Veri Hattı Mutlak Hakimiyeti:** UI'dan kritik SQL işlemleri temizlendi, tüm işlemler DataPipeline üzerinden
2. ✅ **Zero-Effort UI:** Akıllı varsayılanlar (`get_smart_defaults`) - otomatik fiyat ve oda doldurma
3. ✅ **Finansal Keskinlik:** Audit Trail sistemi eklendi, tüm finansal işlemler izleniyor
4. ✅ **Executive Dashboard:** Operasyonel, finansal ve kritik metrikler (Kırmızı Liste, Devamsızlık Alarmı)

### Predictive Dashboard & Smart Audit (29 Ocak 2026)
5. ✅ **Genişletilmiş Dashboard:** Devamsızlık alarmı (3+ seans gelmeyenler) ve geliştirilmiş kırmızı liste (öncelik seviyeleri)
6. ✅ **Personel Cüzdanı:** Terapistlerin kendi bakiyelerini görebilmesi (`get_personel_cuzdan`)
7. ✅ **Smart Logs:** Kurum Müdürü için detaylı sistem günlüğü (Ayarlar sekmesinde)

### Son Düzeltmeler (29 Ocak 2026 - Bugün)
8. ✅ **Seans Durumu Kontrolü:** Seans kayıt edildiğinde otomatik "alındı" işaretleme KALDIRILDI - kullanıcı manuel belirliyor
9. ✅ **Fiyatlandırma Mantığı:** Fiyatlandırma penceresi düzeltildi - `pricing_policy` ve gelecek seansların `hizmet_bedeli` otomatik güncelleniyor
10. ✅ **Otomatik Tablo Yenilenme:** Tüm güncellemelerden sonra tablolar otomatik yenileniyor (kullanıcı manuel yenileme yapmak zorunda değil)
11. ✅ **"Yakında Eklenecek" Mesajları:** Tüm placeholder mesajlar gerçek fonksiyonlarla değiştirildi (Danışan düzenleme, fiyatlandırma, detaylı bilgi, veli düzenleme, şifre düzenleme)

## ÖNEMLİ KURALLAR

1. **UI'dan SQL Temizliği:** UI fonksiyonlarında (kayit_ekle, odeme_ekle, kayit_sil) direkt SQL sorguları YOK. Tüm işlemler DataPipeline üzerinden yapılıyor.

2. **seans_takvimi Ana Kaynak:** Her zaman seans_takvimi tablosu ana kaynak. Diğer tablolar bu tabloya bağlı.

3. **Atomic Transactions:** Her pipeline işlemi tek bir transaction içinde. Hata olursa rollback yapılır.

4. **Cascade Silme:** Bir seans silindiğinde, tüm bağlı kayıtlar (personel_ucret_takibi, cocuk_gunluk_takip, odeme_hareketleri, kasa_hareketleri, records) otomatik silinir.

5. **Otomatik Senkronizasyon:** Manuel "Senkronize Et" butonları yok. Her işlem otomatik senkronize ediliyor.

6. **Otomatik Tablo Yenilenme:** Tüm güncellemelerden sonra (ödeme ekleme, seans durumu güncelleme, fiyatlandırma güncelleme) ilgili tablolar otomatik yenileniyor. Kullanıcı manuel yenileme yapmak zorunda değil.

7. **Seans Durumu Kontrolü:** Seans kayıt edildiğinde `seans_alindi=0` ve `durum="planlandi"` olarak başlar. Kullanıcı seans durumunu manuel olarak belirler (Seans Takip sekmesinde çift tıklayarak).

8. **Fiyatlandırma Güncelleme:** Fiyatlandırma penceresinden yapılan güncellemeler hem `ogrenci_personel_fiyatlandirma` hem de `pricing_policy` tablosuna yansır. Ayrıca gelecek seansların (planlanmış) `hizmet_bedeli` otomatik güncellenir.

## SENDEN İSTEYECEKLERİM

Gelecekte sana kod değişikliği, yeni özellik ekleme veya hata düzeltme konusunda sorular sorduğumda:
- Bu mimari yapıyı göz önünde bulundur
- DataPipeline sınıfını kullanmayı öner
- UI katmanında direkt SQL sorguları önerme
- Tek dosya monolitik yapıyı koru
- Türkçe karakter desteğini unutma
- Otomatik tablo yenilenme özelliğini koru
- Seans durumunun kullanıcı tarafından belirlenmesi gerektiğini unutma (otomatik "alındı" işaretleme yapma)
- Fiyatlandırma güncellemelerinin hem `ogrenci_personel_fiyatlandirma` hem de `pricing_policy` tablosuna yansıması gerektiğini unutma

## ÖNEMLİ NOTLAR

### Seans Durumu Mantığı
- Seans kayıt edildiğinde: `seans_alindi=0`, `ucret_alindi=0`, `durum="planlandi"`
- Kullanıcı seans durumunu manuel olarak belirler (Seans Takip sekmesinde çift tıklayarak)
- Otomatik "alındı" işaretleme YOK

### Fiyatlandırma Mantığı
- Fiyatlandırma güncellendiğinde:
  1. `ogrenci_personel_fiyatlandirma` tablosuna kaydedilir
  2. `pricing_policy` tablosuna da yansıtılır
  3. Gelecek seansların (planlanmış) `hizmet_bedeli` otomatik güncellenir
  4. Tablolar otomatik yenilenir

### Tablo Yenilenme
- Tüm güncellemelerden sonra ilgili tablolar otomatik yenilenir
- `kayitlari_listele()` fonksiyonu otomatik çağrılır
- Kullanıcı manuel yenileme yapmak zorunda değil

Şimdilik bu kadar. Sorularım olduğunda bu bilgileri referans alacağım. Teşekkürler!
```

---

## 💡 Kullanım Önerileri

### Senaryo 1: Yeni Özellik Ekleme
```
Gemini, yukarıdaki prompt'u gönderdikten sonra:

"Şimdi sisteme yeni bir özellik eklemek istiyorum: [özellik açıklaması]. 
DataPipeline mimarisine uygun şekilde nasıl ekleyebilirim?"
```

### Senaryo 2: Hata Düzeltme
```
"Şu hatayı alıyorum: [hata mesajı]. 
Sistemin mevcut yapısına göre nasıl düzeltebilirim?"
```

### Senaryo 3: Kod İyileştirme
```
"Şu fonksiyonu iyileştirmek istiyorum: [fonksiyon adı]. 
DataPipeline sistemine uygun mu, değilse nasıl düzeltebilirim?"
```

---

## 📌 Önemli Notlar

1. **Her Yeni Sohbette:** Eğer Gemini bağlamı kaybederse, bu prompt'u tekrar gönderebilirsin.

2. **Güncellemeler:** Sistemde önemli değişiklikler olduğunda bu prompt'u güncelle.

3. **Spesifik Sorular:** Genel prompt'tan sonra spesifik sorular sorabilirsin.

4. **Kod Örnekleri:** Gemini'den kod örnekleri istediğinde, mevcut kod yapısını referans almasını söyle.

---

## 🔄 Prompt'u Güncelleme

Sistemde önemli değişiklikler olduğunda bu prompt'u şu şekilde güncelle:

1. **Yeni Özellik Eklendi:** "SON YAPILAN DEĞİŞİKLİKLER" bölümüne ekle
2. **Yeni Tablo Eklendi:** "VERİTABANI YAPISI" bölümüne ekle
3. **Mimari Değişti:** "MİMARİ YAPI" bölümünü güncelle
4. **Yeni Kural:** "ÖNEMLİ KURALLAR" bölümüne ekle

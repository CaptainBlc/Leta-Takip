# Leta Takip Sistemi - Detaylı Açıklamalar

## 📋 İçindekiler
1. [Personel Ücret Talep Formu](#1-personel-ücret-talep-formu)
2. [Çocuk Günlük Takip Mantığı](#2-çocuk-günlük-takip-mantığı)
3. [Yetki Sistemi](#3-yetki-sistemi)
4. [Veri İçe Aktarma - 3 Ayrı Template](#4-veri-içe-aktarma---3-ayrı-template)

---

## 1. Personel Ücret Talep Formu

### 📍 Konum
**ÜCRET TAKİBİ** tabı → **Personel Ücret Takibi** sayfası → **"📝 Personel Ücret Talep Formu"** butonu

### 🎯 Amaç
Personel (terapist/hoca) belirli bir tarih aralığındaki ücretlerini talep etmek için kullanılır.

### 🔄 Nasıl Çalışır?
1. **Personel Seçimi:** Dropdown'dan personel seçilir
2. **Tarih Aralığı:** Başlangıç ve bitiş tarihi girilir (varsayılan: ayın ilk günü - bugün)
3. **Özet Hesapla:** Butona tıklanınca seçilen tarih aralığındaki beklemede ücretler hesaplanır
4. **Talep Oluştur:** Onaylandığında `personel_ucret_talepleri` tablosuna kayıt oluşturulur

### 📊 Veritabanı
- **Tablo:** `personel_ucret_talepleri`
- **Durum:** `beklemede` → `onaylandi` → `odendi`
- **İlişkili Tablo:** `personel_ucret_takibi` (her seans için ücret kaydı)

### 💡 Kullanım Senaryosu
Örnek: Arif Hoca Ocak ayı ücretlerini talep etmek istiyor:
1. Personel: "Arif Hoca" seçilir
2. Başlangıç: "2026-01-01", Bitiş: "2026-01-31"
3. "Özet Hesapla" → Sistem Ocak ayındaki tüm seanslarını ve toplam ücretini gösterir
4. "Talep Oluştur" → Talep kaydı oluşturulur, kurum müdürü onaylayabilir

---

## 2. Çocuk Günlük Takip Mantığı

### 🎯 Amaç
Her çocuğun günlük olarak hangi odada, hangi personel ile çalıştığını takip etmek.

### 📊 Veri Yapısı
**Tablo:** `cocuk_gunluk_takip`
- `cocuk_id`: Çocuğun ID'si (danisanlar tablosundan)
- `tarih`: Seans tarihi (YYYY-MM-DD)
- `oda_adi`: Çalışılan oda
- `personel_adi`: Çalışan personel/terapist
- `seans_id`: İlgili seans kaydının ID'si (seans_takvimi tablosundan)

### 🔄 Otomatik Oluşturma
**Pipeline Sistemi:** Bir seans kaydı eklendiğinde otomatik olarak `cocuk_gunluk_takip` tablosuna kayıt eklenir.

**Akış:**
```
Seans Kaydı Ekle
    ↓
seans_takvimi tablosuna kayıt
    ↓
cocuk_gunluk_takip tablosuna otomatik kayıt
    (cocuk_id, tarih, oda, personel, seans_id)
```

### 📋 Kullanım Senaryoları

#### Senaryo 1: Günlük Rapor
**Soru:** "Bugün hangi çocuklar hangi odalarda çalıştı?"
- Tarih filtresine bugünün tarihi girilir
- Sonuç: Tüm çocuklar, odalar ve personeller listelenir

#### Senaryo 2: Çocuk Bazlı Takip
**Soru:** "Ahmet bu ay hangi odalarda çalıştı?"
- Çocuk filtresine "AHMET YILMAZ" girilir
- Sonuç: Ahmet'in tüm seansları, odalar ve personeller gösterilir

#### Senaryo 3: Oda Bazlı Takip
**Soru:** "Oda 1'de bugün kimler çalıştı?"
- Oda filtresine "Oda 1" girilir
- Sonuç: Oda 1'de çalışan tüm çocuklar ve personeller

### 🔗 İlişkiler
- **Çocuk:** `cocuk_gunluk_takip.cocuk_id` → `danisanlar.id`
- **Seans:** `cocuk_gunluk_takip.seans_id` → `seans_takvimi.id`
- **Personel:** `cocuk_gunluk_takip.personel_adi` → `settings.therapist_name`

### 💡 Örnek Veri
```
Çocuk: AHMET YILMAZ
Tarih: 2026-01-28
Oda: Oda 1
Personel: Pervin Hoca
Seans ID: 123
```

Bu kayıt şu anlama gelir:
- Ahmet, 28 Ocak 2026'da Oda 1'de Pervin Hoca ile çalışmış
- Bu seansın detayları `seans_takvimi` tablosunda ID=123 ile bulunabilir

---

## 3. Yetki Sistemi

### 🎯 Amaç
Kullanıcıların sistemdeki erişim seviyelerini ve yetkilerini yönetmek.

### 👥 Yetki Seviyeleri

#### 1. **Kurum Müdürü** (`kurum_muduru`)
**En yüksek yetki seviyesi**

**Erişebildiği Modüller:**
- ✅ Tüm seans kayıtları (tüm personellerin)
- ✅ Tüm danışanlar
- ✅ Kasa Defteri (tüm gelir/giderler)
- ✅ Personel Ücret Takibi (tüm personellerin)
- ✅ Ayarlar (terapist ekleme, oda yönetimi, sistem sıfırlama)
- ✅ Kullanıcı Yönetimi
- ✅ Veri İçe Aktarma
- ✅ Logo Yükleme/Değiştirme

**Kısıtlamalar:** Yok

---

#### 2. **Eğitim Görevlisi** (`egitim_gorevlisi`)
**Orta seviye yetki**

**Erişebildiği Modüller:**
- ✅ Kendi seans kayıtları (sadece kendi terapist adına)
- ✅ Kendi danışanları (kendi seanslarında çalıştığı)
- ✅ Kasa Defteri (sadece kendi seanslarından gelen gelirler)
- ✅ Kendi Personel Ücret Takibi
- ✅ Çocuk Günlük Takip (sadece kendi personel adına)

**Kısıtlamalar:**
- ❌ Ayarlar modülüne erişemez
- ❌ Sistem sıfırlama yapamaz
- ❌ Diğer personellerin verilerini göremez
- ❌ Kullanıcı yönetimi yapamaz

**Otomatik Filtreleme:**
- Tüm listelerde `WHERE terapist = kullanici_terapist` filtresi otomatik uygulanır
- Sadece kendi seanslarını görür ve düzenleyebilir

---

#### 3. **Normal Kullanıcı** (`normal`)
**En düşük yetki seviyesi**

**Erişebildiği Modüller:**
- ✅ Kendi seans kayıtları (sadece kendi terapist adına)
- ✅ Kendi danışanları
- ✅ Kasa Defteri (sadece kendi seanslarından gelen gelirler)

**Kısıtlamalar:**
- ❌ Personel Ücret Takibi yapamaz
- ❌ Ayarlar modülüne erişemez
- ❌ Sistem yönetimi yapamaz

---

### 🔐 Yetki Kontrolü

#### Kod İçinde Kontrol
```python
# Örnek: Ayarlar tabına erişim
if self.kullanici_yetki == "kurum_muduru":
    # Ayarlar tabını göster
else:
    # Ayarlar tabını gizle

# Örnek: Veri filtreleme
if self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
    # Sadece kendi terapist adına filtrele
    WHERE terapist = self.kullanici_terapist
```

#### Veritabanı Yapısı
**Tablo:** `users`
- `id`: Kullanıcı ID'si
- `kullanici_adi`: Giriş kullanıcı adı
- `sifre`: Hash'lenmiş şifre
- `ad_soyad`: Kullanıcının adı
- `yetki`: `kurum_muduru` | `egitim_gorevlisi` | `normal`
- `terapist_adi`: Kullanıcının bağlı olduğu terapist (eğitim görevlisi için)

---

### 📊 Yetki Matrisi

| Özellik | Kurum Müdürü | Eğitim Görevlisi | Normal |
|---------|--------------|------------------|--------|
| Tüm Seansları Görme | ✅ | ❌ | ❌ |
| Kendi Seanslarını Görme | ✅ | ✅ | ✅ |
| Seans Ekleme | ✅ | ✅ (sadece kendi) | ✅ (sadece kendi) |
| Ödeme Ekleme | ✅ | ✅ (sadece kendi) | ✅ (sadece kendi) |
| Kasa Defteri | ✅ (tümü) | ✅ (sadece kendi) | ✅ (sadece kendi) |
| Personel Ücret Takibi | ✅ | ✅ (sadece kendi) | ❌ |
| Ayarlar | ✅ | ❌ | ❌ |
| Kullanıcı Yönetimi | ✅ | ❌ | ❌ |
| Sistem Sıfırlama | ✅ | ❌ | ❌ |
| Veri İçe Aktarma | ✅ | ❌ | ❌ |

---

### 🔄 Yetki Değişikliği
**Sadece Kurum Müdürü yapabilir:**
1. AYARLAR tabına git
2. Kullanıcı Yönetimi bölümüne git
3. Kullanıcıyı seç ve düzenle
4. Yetki seviyesini değiştir

---

## 4. Veri İçe Aktarma - 3 Ayrı Template

### 🎯 Amaç
Eski verileri sisteme aktarmak için 3 farklı Excel template'i kullanılır.

### 📥 Template'ler

#### Template 1: Danışanlar
**Kullanım:** Danışan bilgilerini toplu olarak sisteme eklemek için

**Sütunlar:**
- Ad Soyad
- Telefon
- Email
- Doğum Tarihi (YYYY-MM-DD)
- Veli Adı
- Veli Telefon
- Adres

**Örnek Kullanım:**
```
AHMET YILMAZ | 05551234567 | ahmet@example.com | 2015-01-15 | VELİ ADI | 05559876543 | Adres bilgisi
```

---

#### Template 2: Haftalık Seans Takvimi
**Kullanım:** Haftalık program verilerini sisteme aktarmak için

**Sütunlar:**
- Hafta Başlangıç Tarihi (YYYY-MM-DD) - Pazartesi tarihi
- Gün (Pazartesi, Salı, Çarşamba, vb.)
- Saat (HH:MM)
- Personel Adı
- Öğrenci Adı
- Oda Adı
- Notlar

**Örnek Kullanım:**
```
2026-01-27 | Pazartesi | 09:00 | Pervin Hoca | AHMET YILMAZ | Oda 1 | Haftalık program
2026-01-27 | Pazartesi | 10:00 | Arif Hoca | MEHMET DEMİR | Oda 2 |
```

**Not:** Bu template `haftalik_seans_programi` tablosuna veri ekler. Bu veriler daha sonra otomatik oda seçiminde kullanılır.

---

#### Template 3: Seans Ücret Takip
**Kullanım:** Geçmiş seans kayıtlarını ve ücret bilgilerini sisteme aktarmak için

**Sütunlar:**
- Tarih (YYYY-MM-DD)
- Danışan Adı
- Terapist
- Hizmet Bedeli
- Alınan Ücret
- Kalan Borç
- Oda
- Notlar

**Örnek Kullanım:**
```
2026-01-28 | AHMET YILMAZ | Pervin Hoca | 3500 | 1000 | 2500 | Oda 1 | İlk seans
2026-01-29 | MEHMET DEMİR | Arif Hoca | 3000 | 3000 | 0 | Oda 2 | Tam ödeme
```

**Not:** Bu template Pipeline sistemi üzerinden çalışır. Her satır için:
- `seans_takvimi` tablosuna kayıt eklenir
- `records` tablosuna kayıt eklenir
- `cocuk_gunluk_takip` tablosuna otomatik kayıt eklenir
- `personel_ucret_takibi` tablosuna otomatik kayıt eklenir
- İlk ödeme varsa `kasa_hareketleri` ve `odeme_hareketleri` tablolarına kayıt eklenir

---

### 🔄 İçe Aktarma Süreci

1. **Template İndir:** İstediğiniz template'i indirin (3 ayrı buton)
2. **Excel'de Doldur:** Template'i açın, örnek satırları silin, kendi verilerinizi girin
3. **Dosya Seç:** "Dosya Seç" butonu ile doldurduğunuz Excel dosyasını seçin
4. **Önizleme:** "Önizleme Göster" butonu ile verilerinizi kontrol edin
5. **İçe Aktar:** "Verileri İçe Aktar" butonu ile verileri sisteme aktarın

### ⚠️ Önemli Notlar

- **Danışan Adı Eşleştirmesi:** Seans Ücret Takip template'inde danışan adları tam olarak eşleşmeli (büyük/küçük harf duyarlı değil)
- **Tarih Formatı:** Tüm tarihler YYYY-MM-DD formatında olmalı (örn: 2026-01-28)
- **Tekrar Kayıt:** Aynı danışan zaten varsa, yeni kayıt eklenmez (atlanır)
- **Toplu İşlem:** Seans Ücret Takip template'i ile yüzlerce kayıt tek seferde aktarılabilir

---

## 📝 Notlar

- **Otomatik Filtreleme:** Eğitim görevlisi ve normal kullanıcılar için tüm sorgular otomatik olarak `terapist = kullanici_terapist` filtresi ile çalışır
- **Güvenlik:** Yetki kontrolü hem UI seviyesinde (butonlar gizlenir) hem de veritabanı seviyesinde (WHERE filtresi) yapılır
- **Varsayılan:** Yeni kullanıcılar varsayılan olarak `normal` yetkisi ile oluşturulur
- **Anlaşılır Sütun İsimleri:** Tüm tablolarda teknik terimler ("Kayıt ID", "Seans ID") yerine anlaşılır isimler ("İlgili Kayıt", "Seans Bilgisi") kullanılır

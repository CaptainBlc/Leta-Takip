# 🚀 Gelecek Özellikler Planı

## 📅 Tarih: 29 Ocak 2026

---

## 🎯 Genel Bakış

Bu dokümantasyon, Leta Takip sistemine eklenmesi planlanan gelecek özellikleri içerir. Bu özellikler şu an için **planlama aşamasındadır** ve kullanıcı talebi doğrultusunda önceliklendirilecektir.

---

## 1. 📊 Tahminleme ve Erken Uyarı (Predictive Analytics)

### 1.1 Devamsızlık Alarmı

**Amaç:** Bir öğrenci üst üste 3 seansa gelmediğinde Dashboard'da uyarı göster.

**Özellikler:**
- Dashboard'da "Kritik" bölümüne eklenir
- Öğrenci adı, son seans tarihi, devamsızlık sayısı gösterilir
- "Veli Arayın" butonu ile hızlı aksiyon
- Otomatik SMS/Email bildirimi (opsiyonel)

**Teknik Detaylar:**
- `seans_takvimi` tablosundan son 3 seans kontrolü
- `seans_alindi=0` olan kayıtlar sayılır
- Dashboard `get_dashboard_data()` metoduna eklenir

**Öncelik:** Yüksek

---

### 1.2 Bakiye Öngörüsü (Burn Rate)

**Amaç:** Mevcut seans sıklığına bakarak, öğrencinin içerdeki parasının kaç gün sonra biteceğini hesapla.

**Özellikler:**
- Dashboard'da "Kredi Bitmek Üzere" uyarısı
- 1 hafta önceden uyarı verir
- Hesaplama: `(Kalan Borç) / (Haftalık Ortalama Seans Ücreti) = Gün Sayısı`
- Öğrenci adı, kalan bakiye, tahmini bitiş tarihi gösterilir

**Teknik Detaylar:**
- `records` tablosundan kalan borç
- Son 30 günün seans sıklığı ve ücret ortalaması
- Dashboard `get_dashboard_data()` metoduna eklenir

**Öncelik:** Orta

---

## 2. 🔍 Dijital Arşiv ve Evrensel Arama (Smart Search)

### 2.1 Global Search (Spotlight)

**Amaç:** Uygulamanın üst köşesine bir "Spotlight" arama çubuğu ekle.

**Özellikler:**
- Tek bir arama kutusu ile tüm verilerde arama
- Arama kapsamı:
  - Danışan adı
  - Veli adı
  - Notlar (seans notları, danışan notları)
  - Geçmiş seanslar
- Sonuçlar popup içinde kategorize gösterilir:
  - Danışanlar (3 sonuç)
  - Seanslar (5 sonuç)
  - Notlar (3 sonuç)
- Her sonuç için hızlı erişim butonu

**Teknik Detaylar:**
- SQLite FTS5 (Full-Text Search) kullanılabilir
- Veya basit LIKE sorguları ile arama
- UI: Ana pencere üst kısmına arama kutusu
- Kısayol: `Ctrl+F` veya `Ctrl+K`

**Öncelik:** Orta

---

### 2.2 Evrak Takibi

**Amaç:** Danışanlar tablosuna "Rapor Bitiş Tarihi" ekle ve Dashboard'da liste göster.

**Özellikler:**
- `danisanlar` tablosuna yeni kolonlar:
  - `rapor_baslangic_tarihi` (TEXT)
  - `rapor_bitis_tarihi` (TEXT)
  - `rapor_tipi` (TEXT) - "RAM Raporu", "Sevk", vb.
- Dashboard'da "Süresi Dolan Belgeler" listesi
- Her belge için:
  - Öğrenci adı
  - Belge tipi
  - Bitiş tarihi
  - Kalan gün sayısı
- Renk kodlu gösterim:
  - 🔴 Süresi dolmuş (>0 gün geçmiş)
  - 🟠 1 hafta içinde dolacak
  - 🟡 1 ay içinde dolacak

**Teknik Detaylar:**
- `danisanlar` tablosuna migration ile kolonlar eklenir
- Dashboard `get_dashboard_data()` metoduna eklenir
- UI: Ana sayfa Dashboard panelinde gösterilir

**Öncelik:** Düşük

---

## 3. 🔒 Sistem Sağlığı ve Güvenlik (Infrastructure)

### 3.1 Auto-Cloud Backup

**Amaç:** Program her kapandığında yerel yedeğin bir kopyasını şifreli olarak Google Drive veya Dropbox'a yükle.

**Özellikler:**
- Kullanıcı API key girdiyse aktif olur
- Her kapanışta otomatik yedekleme
- Şifreli yedekleme (AES-256)
- Yedekleme geçmişi (son 10 yedek)
- Manuel yedekleme butonu

**Teknik Detaylar:**
- Google Drive API veya Dropbox API kullanılır
- `pydrive` veya `dropbox` Python kütüphaneleri
- Şifreleme: `cryptography` kütüphanesi
- Ayarlar: `settings` tablosuna `cloud_backup_enabled`, `cloud_provider`, `cloud_api_key` kolonları

**Öncelik:** Düşük

---

### 3.2 Role Based UI Masking

**Amaç:** Audit Trail var ama güvenliği UI'da da sıkılaştır.

**Özellikler:**
- "Eğitim Görevlisi"nin Dashboard'unda:
  - Kurumun toplam cirosu görünmesin
  - Sadece kendi başarı metrikleri görünsün
- "Normal Kullanıcı" için:
  - Sadece kendi seansları görünsün
  - Finansal bilgiler hiç görünmesin
- "Kurum Müdürü" için:
  - Tüm verilere erişim

**Teknik Detaylar:**
- `get_dashboard_data()` metoduna `kullanici_yetki` parametresi eklenir
- SQL sorgularında `WHERE` koşulları eklenir
- UI'da butonlar ve menüler gizlenir/gösterilir

**Öncelik:** Orta

---

## 📋 Öncelik Sıralaması

1. **Yüksek Öncelik:**
   - Devamsızlık Alarmı
   - Role Based UI Masking

2. **Orta Öncelik:**
   - Bakiye Öngörüsü (Burn Rate)
   - Global Search (Spotlight)

3. **Düşük Öncelik:**
   - Evrak Takibi
   - Auto-Cloud Backup

---

## 🔧 Teknik Gereksinimler

### Yeni Kütüphaneler:
- `cryptography` - Şifreleme için (Auto-Cloud Backup)
- `pydrive` veya `dropbox` - Cloud backup için (opsiyonel)

### Veritabanı Değişiklikleri:
- `danisanlar` tablosuna yeni kolonlar (Evrak Takibi)
- `settings` tablosuna cloud backup ayarları (Auto-Cloud Backup)

### UI Değişiklikleri:
- Ana pencere üst kısmına arama kutusu (Global Search)
- Dashboard panelinde yeni bölümler (Devamsızlık, Bakiye Öngörüsü, Evrak Takibi)

---

## 📝 Notlar

- Bu özellikler şu an için **planlama aşamasındadır**
- Kullanıcı talebi doğrultusunda önceliklendirilecektir
- Her özellik için ayrı bir branch oluşturulabilir
- Test edilmeden production'a alınmayacaktır

---

## 🎯 Sonraki Adımlar

1. Kullanıcıdan öncelik onayı al
2. İlk özellik için detaylı tasarım yap
3. Kod geliştirme
4. Test
5. Production'a alma

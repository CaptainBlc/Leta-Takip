# Pipeline Sistemi - Hızlı Başlangıç

## 🚀 Ne Değişti?

Artık **seans kaydı**, **ödeme ekleme** ve **kayıt silme** işlemleri yaparken, sistemdeki **tüm ilgili tablolar otomatik güncellenecek**!

---

## ✨ Kullanıcı Perspektifi

### Önceki Durum ❌
- Seans kaydı eklenince sadece "SEANS TAKİP" güncelleniyordu
- Ödeme eklenince kasaya manuel işlem gerekiyordu
- Kayıt silinince bazen eski veriler kalıyordu

### Şimdiki Durum ✅
- **Seans kaydı eklenince:**
  - ✅ Seans Takip tablosu güncellenir
  - ✅ Seans Takvimi güncellenir
  - ✅ İlk ödeme varsa Kasa'ya otomatik eklenir
  - ✅ Oda doluluk bilgisi güncellenir

- **Ödeme eklenince:**
  - ✅ Borç otomatik hesaplanır
  - ✅ Kasa'ya "Giren" olarak kaydedilir
  - ✅ Ödeme geçmişi kaydedilir
  - ✅ Borç tamamen ödendiyse Seans Takvimi işaretlenir

- **Kayıt silinince:**
  - ✅ Seans Takvimi'nden silinir
  - ✅ Tüm ödemeler silinir
  - ✅ Kasa kayıtları silinir
  - ✅ Hiçbir eski veri kalmaz

---

## 📊 Örnek Kullanım

### 1️⃣ Yeni Seans Kaydı

**Adımlar:**
1. SEANS TAKİP sekmesine git
2. Tarih: **24.01.2026**
3. Danışan: **AHMET YILMAZ**
4. Terapist: **Pervin Hoca**
5. Bedel: **1500 TL**
6. Alınan: **500 TL** (ilk ödeme)
7. Not: **İlk seans**
8. **KAYDET** butonuna bas

**Otomatik olarak yapılanlar:**
```
✅ Seans kaydı oluşturuldu!

• Records: #123
• Seans Takvimi: Eklendi
• Kasa: Eklendi (500 TL giren)
• Oda: Seçilmedi
```

**Kontrol:**
- Menü → **Muhasebe** → **Kasa Defteri** → Bugün 500 TL giren olarak görünecek
- Menü → **Seans Takvimi** → **Günlük Takvim** → Seans görünecek
- **SEANS TAKİP** → Ahmet Yılmaz'ın 1000 TL borcu görünecek

---

### 2️⃣ Ödeme Ekleme

**Adımlar:**
1. SEANS TAKİP'te **Ahmet Yılmaz** kaydını seç
2. Sağ tık → **Ödeme Ekle**
3. Tarih: **24.01.2026**
4. Ödeme Şekli: **Nakit**
5. Eklenen ödeme: **500 TL**
6. **KAYDET**

**Otomatik olarak yapılanlar:**
```
✅ Ödeme kaydedildi!

• Eklenen: 500 TL
• Kalan Borç: 500 TL

İlgili tablolar güncellendi:
✓ Ödeme Hareketleri
✓ Records
✓ Kasa Defteri (Giren)
```

**Kontrol:**
- Kasa'ya 500 TL daha eklenecek (Toplam 1000 TL giren)
- Ahmet Yılmaz'ın borcu 500 TL'ye düşecek

---

### 3️⃣ Kayıt Silme

**Adımlar:**
1. SEANS TAKİP'te **Ahmet Yılmaz** kaydını seç
2. Sağ tık → **Kaydı Sil**
3. Onay ver

**Otomatik olarak yapılanlar:**
```
✅ Kayıt silindi!

Silinen veriler:
✓ Ana Kayıt (records)
✓ Seans Takvimi
✓ Ödeme Hareketleri
✓ Kasa Kayıtları
```

**Kontrol:**
- Seans Takip'te kayıt görünmeyecek
- Seans Takvimi'nde görünmeyecek
- Kasa'dan ilgili kayıtlar silinecek

---

## 🎯 Önemli Bilgiler

### Veri Güvenliği
- Tüm işlemler **transaction** ile yapılır
- Hata olursa **hiçbir değişiklik kaydedilmez** (rollback)
- Eski sistem yedekleri hala çalışıyor

### Performans
- Pipeline sistemi çok hızlıdır (< 100ms)
- Aynı anda birden fazla kullanıcı kullanabilir
- Veritabanı kilitlenmesi riski yoktur

### Geriye Dönük Uyumluluk
- **Eski kayıtlar etkilenmez**
- Sadece yeni kayıtlar için pipeline çalışır
- Eski UI tamamen aynı çalışıyor

---

## ❓ Sık Sorulan Sorular

### S: Eski kayıtlarım ne olacak?
**C:** Eski kayıtlarınız olduğu gibi kalacak. Pipeline sadece yeni işlemler için çalışır.

### S: Yanlışlıkla silersem geri alabilir miyim?
**C:** Silmeden önce onay penceresi çıkar. Yanlışlıkla silmişseniz "Yedekler" klasöründen geri yükleyebilirsiniz.

### S: Kasa ile Seans Takip'teki tutarlar uyuşmazsa?
**C:** Bu artık mümkün değil! Pipeline her ödemeyi otomatik kasaya ekler, manuel işlem gerekmiyor.

### S: Pipeline hatası olursa verilerim kaybolur mu?
**C:** Hayır! Hata olursa hiçbir değişiklik kaydedilmez (rollback). Verileriniz güvende.

### S: Eski sisteme dönebilir miyim?
**C:** Evet, yedekler klasöründen eski veritabanını geri yükleyebilirsiniz.

---

## 🛠️ Sorun Giderme

### Problem: "Pipeline hatası" mesajı alıyorum
**Çözüm:**
1. Programı kapat ve tekrar aç
2. Veri klasörü → `leta_error.log` dosyasına bak
3. Gerekirse yedeklerden geri yükle

### Problem: Kasa ve Seans Takip tutarları farklı görünüyor
**Çözüm:**
1. Menü → **Dosya İşlemleri** → **Excel'e Aktar**
2. Her iki raporu da al ve karşılaştır
3. Fark varsa sistem yöneticisine göster

### Problem: Sildiğim kayıt hala görünüyor
**Çözüm:**
1. **Yenile** butonuna bas
2. Hala görünüyorsa programı kapat/aç
3. Sorun devam ederse `leta_error.log` dosyasını kontrol et

---

## 📞 Destek

Sorularınız için:
- Hata günlüğü: `%LOCALAPPDATA%\LetaYonetim\leta_error.log`
- Kullanım kılavuzu: Program içi **Yardım** → **Kullanım Kılavuzu**

---

**Pipeline Sistemi v1.0**  
© 2026 Leta Aile ve Çocuk


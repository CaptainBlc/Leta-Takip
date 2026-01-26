# Leta Takip - Data Pipeline Sistemi

## 🎯 Amaç

**Event-Driven Architecture** ile tüm veritabanı tablolarının birbirinden haberdar olduğu, senkronize bir sistem.

Kullanıcı bir işlem yaptığında (seans kaydı, ödeme, silme), sistemdeki **TÜM ilgili tablolar otomatik olarak güncellenir**.

---

## 🏗️ Mimari

### Pipeline Class: `DataPipeline`

Her işlem için tek bir pipeline instance oluşturulur ve tüm ilgili tabloları günceller.

```python
from leta_app import DataPipeline

conn = sqlite3.connect("leta_data.db")
kullanici_id = 1  # Mevcut kullanıcı

pipeline = DataPipeline(conn, kullanici_id)
```

---

## 📊 Pipeline Akışları

### 1️⃣ SEANS KAYIT Pipeline

**Akış:**
```
records → seans_takvimi → kasa_hareketleri (ilk ödeme varsa) → oda_doluluk
```

**Kullanım:**
```python
record_id = pipeline.seans_kayit(
    tarih="2026-01-24",
    saat="14:00",
    danisan_adi="AHMET YILMAZ",
    terapist="Pervin Hoca",
    hizmet_bedeli=1500.0,
    alinan_ucret=500.0,
    notlar="İlk seans",
    oda="Oda 1"
)
```

**Otomatik yapılanlar:**
- ✅ `records` tablosuna kayıt eklenir (record_id)
- ✅ `seans_takvimi` tablosuna kayıt eklenir (seans_id) ve record ile bağlanır
- ✅ İlk ödeme varsa `kasa_hareketleri` tablosuna "giren" kaydı eklenir
- ✅ İlk ödeme varsa `odeme_hareketleri` tablosuna kayıt eklenir
- ✅ Oda seçilmişse oda doluluk bilgisi güncellenir (log)
- ✅ Transaction commit edilir

**Hata durumunda:** Rollback yapılır, hiçbir tablo değişmez.

---

### 2️⃣ ÖDEME EKLEME Pipeline

**Akış:**
```
odeme_hareketleri → records (borç güncelle) → kasa_hareketleri → seans_takvimi (ücret_alindi)
```

**Kullanım:**
```python
basarili = pipeline.odeme_ekle(
    record_id=123,
    tutar=500.0,
    tarih="2026-01-24",
    odeme_sekli="Nakit",
    aciklama="Kısmi ödeme"
)
```

**Otomatik yapılanlar:**
- ✅ `records` tablosunda `alinan_ucret` ve `kalan_borc` güncellenir
- ✅ `odeme_hareketleri` tablosuna tahsilat kaydı eklenir
- ✅ `kasa_hareketleri` tablosuna "giren" kaydı eklenir
- ✅ Borç tamamen ödendiyse `seans_takvimi` tablosunda `ucret_alindi=1` işaretlenir
- ✅ Transaction commit edilir

**Hata durumunda:** Rollback yapılır, hiçbir tablo değişmez.

---

### 3️⃣ KAYIT SİLME Pipeline (Cascade)

**Akış:**
```
records silme → seans_takvimi sil → kasa_hareketleri sil → odeme_hareketleri sil
```

**Kullanım:**
```python
basarili = pipeline.kayit_sil(record_id=123)
```

**Otomatik yapılanlar:**
- ✅ `seans_takvimi` tablosundan bağlı kayıt silinir
- ✅ `odeme_hareketleri` tablosundan tüm ödeme kayıtları silinir
- ✅ `kasa_hareketleri` tablosundan tüm kasa kayıtları silinir
- ✅ `records` tablosundan ana kayıt silinir
- ✅ Transaction commit edilir

**Hata durumunda:** Rollback yapılır, hiçbir tablo değişmez.

---

## 🔍 Pipeline Loglama

Her pipeline işlemi detaylı log tutar. Debugging ve monitoring için kullanılabilir.

```python
pipeline = DataPipeline(conn, kullanici_id)
record_id = pipeline.seans_kayit(...)

# Log'ları konsola yazdır
print(pipeline.get_log())
```

**Örnek log çıktısı:**
```
[PIPELINE 2026-01-24 14:30:15] SEANS_KAYIT | record_id=123 | AHMET YILMAZ / Pervin Hoca
[PIPELINE 2026-01-24 14:30:15] SEANS_CREATE | seans_id=456 oluşturuldu | Oda: Oda 1
[PIPELINE 2026-01-24 14:30:15] SEANS_LINK | record_id=123 ↔ seans_id=456
[PIPELINE 2026-01-24 14:30:15] KASA_GIREN | +500.0 TL | AHMET YILMAZ (Pervin Hoca) - İlk ödeme
[PIPELINE 2026-01-24 14:30:15] ODA_UPDATE | Tarih: 2026-01-24 14:00 | Oda: Oda 1 | Durum: dolu
```

---

## 🎨 UI Entegrasyonu

Pipeline sistemi mevcut UI fonksiyonlarına entegre edilmiştir:

### Seans Kayıt Ekranı
```python
def kayit_ekle(self):
    # ... input validasyonları ...
    
    conn = self.veritabani_baglan()
    pipeline = DataPipeline(conn, self.kullanici[0])
    
    record_id = pipeline.seans_kayit(
        tarih=self._tarih_db(),
        saat=saat,
        danisan_adi=danisan,
        terapist=terapist,
        hizmet_bedeli=bedel,
        alinan_ucret=alinan,
        notlar=notlar,
        oda=oda,
    )
    
    conn.close()
```

### Ödeme Ekleme Dialog
```python
def _save():
    conn = self.veritabani_baglan()
    pipeline = DataPipeline(conn, self.kullanici[0])
    
    basarili = pipeline.odeme_ekle(
        record_id=rid,
        tutar=ek,
        tarih=tahsil_tarih,
        odeme_sekli=odeme_sekli,
        aciklama=aciklama,
    )
    
    conn.close()
```

### Kayıt Silme
```python
def kayit_sil(self):
    conn = self.veritabani_baglan()
    pipeline = DataPipeline(conn, self.kullanici[0])
    
    basarili = pipeline.kayit_sil(record_id=rid)
    
    conn.close()
```

---

## ✅ Avantajlar

### 1. **Veri Tutarlılığı**
- Tüm tablolar her zaman senkronize
- Manuel senkronizasyon hatası riski yok
- Transaction desteği ile atomik işlemler

### 2. **Bakım Kolaylığı**
- Tüm iş mantığı tek yerde (`DataPipeline` class)
- Yeni tablo eklendiğinde tek yerden güncelleme
- Debug ve test etmesi kolay

### 3. **Hata Yönetimi**
- Hata durumunda otomatik rollback
- Detaylı loglama
- Exception handling

### 4. **Genişletilebilirlik**
- Yeni pipeline akışları kolayca eklenebilir
- Event-based mimariye hazır
- Webhook/notification sistemi eklenebilir

---

## 📈 İleride Eklenebilecek Özellikler

### 1. Event Listeners
```python
pipeline.on_seans_kayit(lambda record_id: send_notification())
pipeline.on_odeme_ekle(lambda record_id, tutar: update_statistics())
```

### 2. Oda Çakışma Kontrolü
```python
def _check_oda_cakisma(self, tarih: str, saat: str, oda: str) -> bool:
    """Aynı tarih/saat/oda'da başka seans var mı?"""
    self.cur.execute(
        "SELECT COUNT(*) FROM seans_takvimi WHERE tarih=? AND saat=? AND oda=?",
        (tarih, saat, oda)
    )
    return int(self.cur.fetchone()[0]) > 0
```

### 3. Webhook/Bildirim Sistemi
```python
def _send_notification(self, event: str, data: dict):
    """Seans kaydı/ödeme alındığında SMS/Email gönder"""
    requests.post("https://api.sms.com/send", json=data)
```

### 4. İstatistik Otomasyonu
```python
def _update_statistics(self, terapist: str, tutar: float):
    """Her ödeme geldiğinde terapist istatistiklerini güncelle"""
    # Aylık gelir, seans sayısı, ortalama ücret vb.
```

---

## 🧪 Test Senaryoları

### Senaryo 1: Tam Akış (Seans Kaydı → Ödeme → Silme)
```python
import sqlite3
from leta_app import DataPipeline

conn = sqlite3.connect(":memory:")
# ... init_db() çalıştır ...

pipeline = DataPipeline(conn, kullanici_id=1)

# 1. Seans kaydı
record_id = pipeline.seans_kayit(
    tarih="2026-01-24",
    saat="14:00",
    danisan_adi="TEST DANISAN",
    terapist="Test Hoca",
    hizmet_bedeli=1000.0,
    alinan_ucret=300.0,
    notlar="Test seansı",
    oda="Test Oda"
)
assert record_id is not None
print(f"✅ Seans kaydı: record_id={record_id}")

# 2. Ödeme ekle
basarili = pipeline.odeme_ekle(
    record_id=record_id,
    tutar=500.0,
    tarih="2026-01-24",
    odeme_sekli="Nakit",
)
assert basarili == True
print("✅ Ödeme eklendi: 500 TL")

# 3. Kontrol: Borç 200 TL olmalı
cur = conn.cursor()
cur.execute("SELECT kalan_borc FROM records WHERE id=?", (record_id,))
kalan = float(cur.fetchone()[0])
assert kalan == 200.0
print(f"✅ Kalan borç doğru: {kalan} TL")

# 4. Kaydı sil
basarili = pipeline.kayit_sil(record_id=record_id)
assert basarili == True
print("✅ Kayıt silindi")

# 5. Kontrol: Tüm tablolardan silinmiş olmalı
cur.execute("SELECT COUNT(*) FROM records WHERE id=?", (record_id,))
assert cur.fetchone()[0] == 0
cur.execute("SELECT COUNT(*) FROM seans_takvimi WHERE record_id=?", (record_id,))
assert cur.fetchone()[0] == 0
cur.execute("SELECT COUNT(*) FROM kasa_hareketleri WHERE record_id=?", (record_id,))
assert cur.fetchone()[0] == 0
print("✅ Tüm tablolardan silindi (cascade)")

conn.close()
print("\n🎉 TÜM TESTLER BAŞARILI!")
```

---

## 📚 API Referansı

### `DataPipeline.__init__(conn, kullanici_id=None)`
- **conn**: `sqlite3.Connection` - Veritabanı bağlantısı
- **kullanici_id**: `int | None` - İşlemi yapan kullanıcı ID'si

### `DataPipeline.seans_kayit(...)`
- **Returns**: `int | None` - record_id veya hata durumunda None
- **Raises**: `Exception` - Veritabanı hatası

### `DataPipeline.odeme_ekle(...)`
- **Returns**: `bool` - Başarılı: True, Hata: False

### `DataPipeline.kayit_sil(record_id)`
- **Returns**: `bool` - Başarılı: True, Hata: False

### `DataPipeline.get_log()`
- **Returns**: `str` - Pipeline log'larını multiline string olarak döndürür

---

## 🔧 Troubleshooting

### Problem: Pipeline commit etmiyor
**Çözüm:** Connection'ın autocommit kapalı olduğundan emin olun. Pipeline kendi commit/rollback yönetimini yapar.

### Problem: Log'lar görünmüyor
**Çözüm:** `pipeline.get_log()` çağrıldıktan sonra konsola `print()` yapın veya log dosyasına yazın.

### Problem: Eski kayıtlarda pipeline çalışmıyor
**Çözüm:** Eski kayıtlar için `_sync_from_record_to_seans()` gibi eski fonksiyonlar kullanılabilir. Yeni kayıtlar için pipeline otomatik çalışır.

---

## 👨‍💻 Geliştirici Notları

- Pipeline sınıfı stateless'tır, her işlem için yeni instance oluşturun
- Connection'ı her işlemden sonra kapatın (`conn.close()`)
- Exception handling UI katmanında yapılır, pipeline sadece raise eder
- Log seviyesi production'da düşürülebilir (şimdilik debug level)

---

## 📄 Lisans

Bu pipeline sistemi Leta Takip projesinin bir parçasıdır.
© 2026 Leta Aile ve Çocuk - Tüm hakları saklıdır.


# Leta Takip - Opsiyonel Özellikler Dokümantasyonu

## 🎯 Yeni Eklenen Özellikler (v1.2)

Bu dokümanda Pipeline sistemine eklenen 3 opsiyonel özellik açıklanmaktadır:

1. **Oda Çakışma Kontrolü**
2. **Event Listeners (Webhook Sistemi)**
3. **SMS/Email Bildirim Sistemi**

---

## 1️⃣ Oda Çakışma Kontrolü

### Ne İşe Yarar?

Aynı tarih/saat/oda'da **iki farklı seans atamasını engeller**.

### Nasıl Çalışır?

```python
pipeline = DataPipeline(conn, kullanici_id=1)

# Otomatik kontrol (varsayılan: aktif)
record_id = pipeline.seans_kayit(
    tarih="2026-01-24",
    saat="14:00",
    oda="Oda 1",
    # ... diğer parametreler ...
)
# Çakışma varsa ValueError fırlatır

# Manuel kontrol için pasif et
record_id = pipeline.seans_kayit(
    # ... parametreler ...
    check_oda_cakisma=False  # Kontrolü devre dışı bırak
)
```

### API

```python
def check_oda_cakismasi(
    tarih: str,           # YYYY-MM-DD
    saat: str,            # HH:MM
    oda: str,             # Oda adı
    exclude_record_id: int | None = None  # Bu kaydı hariç tut
) -> tuple[bool, str]:
    """
    Returns:
        (çakışma_var: bool, mesaj: str)
    """
```

### Örnek Kullanım

```python
# Kontrol et
cakisma_var, mesaj = pipeline.check_oda_cakismasi(
    tarih="2026-01-24",
    saat="14:00",
    oda="Oda 1"
)

if cakisma_var:
    print(mesaj)
    # ⚠️ ODA ÇAKIŞMASI!
    # Oda: Oda 1
    # Tarih: 2026-01-24
    # Saat: 14:00 - 14:45
    # 
    # Bu saatte başka seans var:
    # • AHMET YILMAZ / Pervin Hoca
    # • Saat: 14:00 - 14:45
```

### Seans Süresi

Varsayılan seans süresi **45 dakika**. Değiştirmek için:

```python
# leta_app.py içinde check_oda_cakismasi() fonksiyonunda:
seans_sure = timedelta(minutes=45)  # Bu satırı değiştir
```

### UI Entegrasyonu

```python
def kayit_ekle(self):
    try:
        pipeline = DataPipeline(conn, kullanici_id)
        record_id = pipeline.seans_kayit(...)
    except ValueError as e:
        # Oda çakışması mesajını göster
        messagebox.showerror("Oda Çakışması", str(e))
        return
```

---

## 2️⃣ Event Listeners (Webhook Sistemi)

### Ne İşe Yarar?

Pipeline'daki her işlem (seans kaydı, ödeme, silme) için **custom callback fonksiyonları** çalıştırılabilir.

### Kullanım Senaryoları

- **Dashboard güncelleme**: Her ödeme alındığında grafiği güncelle
- **Webhook gönderme**: Üçüncü parti sistemlere bildirim
- **Loglama**: Detaylı audit log sistemi
- **Notification**: SMS/Email tetikleyici

### API

```python
def on(event: str, callback: callable):
    """
    Event listener ekle
    
    Events:
        - "seans_kayit"
        - "odeme_ekle"
        - "kayit_sil"
        - "oda_cakisma"
    """
```

### Örnek: Ödeme Alındığında Bildirim Gönder

```python
def odeme_alindi_handler(data):
    """Ödeme alındığında çağrılır"""
    print(f"✅ ÖDEME ALINDI!")
    print(f"Danışan: {data['danisan_adi']}")
    print(f"Tutar: {data['tutar']} TL")
    print(f"Kalan: {data['kalan_borc']} TL")
    
    # Borç tamamen ödendiyse SMS gönder
    if data['tam_odendi']:
        send_sms("+905551234567", "Borcunuz tamamen ödenmiştir!")

# Listener kaydet
pipeline = DataPipeline(conn, kullanici_id=1)
pipeline.on("odeme_ekle", odeme_alindi_handler)

# Ödeme ekle (handler otomatik çalışır)
pipeline.odeme_ekle(record_id=123, tutar=500, ...)
```

### Örnek: Dashboard Güncelleme

```python
def dashboard_guncelle(data):
    """Her işlemde dashboard'u güncelle"""
    if "record_id" in data:
        update_charts()
        refresh_statistics()

pipeline.on("seans_kayit", dashboard_guncelle)
pipeline.on("odeme_ekle", dashboard_guncelle)
pipeline.on("kayit_sil", dashboard_guncelle)
```

### Örnek: Webhook Gönderme

```python
import requests

def webhook_gonder(data):
    """Üçüncü parti API'ye POST gönder"""
    try:
        response = requests.post(
            "https://api.example.com/webhook",
            json=data,
            timeout=5
        )
        print(f"Webhook gönderildi: {response.status_code}")
    except Exception as e:
        print(f"Webhook hatası: {e}")

pipeline.on("seans_kayit", webhook_gonder)
```

### Event Data Yapısı

#### seans_kayit event:
```python
{
    "record_id": 123,
    "seans_id": 456,
    "tarih": "2026-01-24",
    "saat": "14:00",
    "danisan_adi": "AHMET YILMAZ",
    "terapist": "Pervin Hoca",
    "hizmet_bedeli": 1500.0,
    "alinan_ucret": 500.0,
    "kalan_borc": 1000.0,
    "oda": "Oda 1"
}
```

#### odeme_ekle event:
```python
{
    "record_id": 123,
    "seans_id": 456,
    "danisan_adi": "AHMET YILMAZ",
    "terapist": "Pervin Hoca",
    "tutar": 500.0,
    "alinan_toplam": 1000.0,
    "kalan_borc": 500.0,
    "odeme_sekli": "Nakit",
    "tam_odendi": False
}
```

#### kayit_sil event:
```python
{
    "record_id": 123,
    "seans_id": 456,
    "danisan_adi": "AHMET YILMAZ",
    "terapist": "Pervin Hoca",
    "hizmet_bedeli": 1500.0,
    "silinen_odeme_sayisi": 2,
    "silinen_kasa_sayisi": 2
}
```

#### oda_cakisma event:
```python
{
    "tarih": "2026-01-24",
    "saat": "14:00",
    "oda": "Oda 1",
    "danisan": "AHMET YILMAZ",
    "mesaj": "⚠️ ODA ÇAKIŞMASI! ..."
}
```

---

## 3️⃣ SMS/Email Bildirim Sistemi

### Ne İşe Yarar?

Danışanlara veya personele **otomatik SMS/Email bildirimleri** gönderir.

### Şablon Implementasyon

Bu sistem **şablon** olarak hazırlanmıştır. Gerçek kullanım için **SMS/Email API entegrasyonu** gerekir.

### API

```python
def send_notification(
    notification_type: str,  # "seans_hatirlatma" | "odeme_alindi" | "borc_hatirlatma"
    recipient: str,          # Telefon (SMS) veya Email
    message: str,            # Mesaj içeriği
    method: str = "sms"      # "sms" | "email"
) -> bool
```

### Örnek: Ödeme Alındı Bildirimi

```python
def odeme_alindi_handler(data):
    if data['tam_odendi']:
        pipeline.send_notification(
            notification_type="odeme_alindi",
            recipient="+905551234567",  # Danışan telefonu
            message=f"Sayın {data['danisan_adi']}, {data['tutar']} TL ödemeniz alınmıştır. Borcunuz tamamen ödenmiştir. Teşekkürler!",
            method="sms"
        )

pipeline.on("odeme_ekle", odeme_alindi_handler)
```

### Örnek: Seans Hatırlatma

```python
def seans_hatirlatma_gonder(data):
    """Seansın 1 saat öncesinde SMS gönder"""
    pipeline.send_notification(
        notification_type="seans_hatirlatma",
        recipient="+905551234567",
        message=f"Sayın {data['danisan_adi']}, {data['tarih']} {data['saat']} seansınız için hatırlatma. Görüşmek üzere!",
        method="sms"
    )

pipeline.on("seans_kayit", seans_hatirlatma_gonder)
```

### Örnek: Borç Hatırlatma

```python
def borc_hatirlatma_gonder(danisan_adi: str, kalan_borc: float, telefon: str):
    pipeline.send_notification(
        notification_type="borc_hatirlatma",
        recipient=telefon,
        message=f"Sayın {danisan_adi}, {kalan_borc} TL borcunuz bulunmaktadır. En kısa sürede ödeme yapmanızı rica ederiz.",
        method="sms"
    )
```

### SMS API Entegrasyonları

#### Twilio (Uluslararası)
```python
from twilio.rest import Client

def _send_sms(self, phone: str, message: str) -> bool:
    try:
        account_sid = "YOUR_ACCOUNT_SID"
        auth_token = "YOUR_AUTH_TOKEN"
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=message,
            from_='+15017122661',  # Twilio numaranız
            to=phone
        )
        return True
    except Exception as e:
        self._log("ERROR", f"Twilio SMS failed: {e}")
        return False
```

#### NetGSM (Türkiye)
```python
import requests

def _send_sms(self, phone: str, message: str) -> bool:
    try:
        url = "https://api.netgsm.com.tr/sms/send/get"
        params = {
            "usercode": "YOUR_USERNAME",
            "password": "YOUR_PASSWORD",
            "gsmno": phone,
            "message": message,
            "msgheader": "YOUR_HEADER"
        }
        response = requests.get(url, params=params)
        return response.text.startswith("00")
    except Exception as e:
        self._log("ERROR", f"NetGSM SMS failed: {e}")
        return False
```

### Email API Entegrasyonları

#### SMTP (Yerleşik)
```python
import smtplib
from email.mime.text import MIMEText

def _send_email(self, email: str, message: str) -> bool:
    try:
        msg = MIMEText(message)
        msg['Subject'] = 'Leta Aile ve Çocuk - Bildirim'
        msg['From'] = 'noreply@leta.com'
        msg['To'] = email
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('your_email@gmail.com', 'your_password')
            server.send_message(msg)
        return True
    except Exception as e:
        self._log("ERROR", f"SMTP email failed: {e}")
        return False
```

#### SendGrid
```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def _send_email(self, email: str, message: str) -> bool:
    try:
        message = Mail(
            from_email='noreply@leta.com',
            to_emails=email,
            subject='Leta Aile ve Çocuk - Bildirim',
            plain_text_content=message
        )
        sg = SendGridAPIClient('YOUR_API_KEY')
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        self._log("ERROR", f"SendGrid email failed: {e}")
        return False
```

---

## 🔧 Kurulum Talimatları

### 1. Gerekli Kütüphaneler

#### SMS için (Twilio)
```bash
pip install twilio
```

#### SMS için (NetGSM)
```bash
pip install requests  # (zaten yüklü olabilir)
```

#### Email için (SendGrid)
```bash
pip install sendgrid
```

### 2. API Anahtarları

Gerekli API anahtarlarını environment variables veya config dosyasında saklayın:

```python
# config.py
TWILIO_ACCOUNT_SID = "AC..."
TWILIO_AUTH_TOKEN = "..."
NETGSM_USERNAME = "..."
NETGSM_PASSWORD = "..."
SENDGRID_API_KEY = "SG..."
```

### 3. Örnek Tam Entegrasyon

```python
# leta_app.py içinde kayit_ekle() fonksiyonu

def kayit_ekle(self):
    # ... input validasyonları ...
    
    conn = self.veritabani_baglan()
    kullanici_id = self.kullanici[0] if self.kullanici else None
    
    pipeline = DataPipeline(conn, kullanici_id)
    
    # Event listeners ekle
    def on_seans_kayit(data):
        print(f"✅ Seans kaydedildi: {data['danisan_adi']}")
        # İsterseniz bildirim gönderin
    
    pipeline.on("seans_kayit", on_seans_kayit)
    
    # Seans kaydı yap (oda çakışması kontrolü otomatik)
    try:
        record_id = pipeline.seans_kayit(...)
    except ValueError as e:
        # Oda çakışması
        messagebox.showerror("Hata", str(e))
        return
    
    conn.close()
```

---

## 🧪 Test Senaryoları

### Test 1: Oda Çakışma Kontrolü

```python
import sqlite3
from leta_app import DataPipeline

conn = sqlite3.connect(":memory:")
# ... init_db() ...

pipeline = DataPipeline(conn, kullanici_id=1)

# İlk seans
record1 = pipeline.seans_kayit(
    tarih="2026-01-24",
    saat="14:00",
    oda="Oda 1",
    danisan_adi="AHMET",
    terapist="Pervin Hoca",
    hizmet_bedeli=1000,
    alinan_ucret=0
)
print(f"✅ İlk seans: record_id={record1}")

# İkinci seans (çakışma olacak)
try:
    record2 = pipeline.seans_kayit(
        tarih="2026-01-24",
        saat="14:15",  # 15 dk sonra (45 dk içinde çakışma)
        oda="Oda 1",
        danisan_adi="MEHMET",
        terapist="Çağlar Hoca",
        hizmet_bedeli=1000,
        alinan_ucret=0
    )
    print("❌ Çakışma engellenmedi!")
except ValueError as e:
    print(f"✅ Çakışma engellendi: {e}")

conn.close()
```

### Test 2: Event Listeners

```python
def log_handler(data):
    print(f"[EVENT] {data}")

pipeline = DataPipeline(conn, kullanici_id=1)
pipeline.on("seans_kayit", log_handler)
pipeline.on("odeme_ekle", log_handler)

# Seans kaydı (handler tetiklenir)
record_id = pipeline.seans_kayit(...)
# [EVENT] {'record_id': 123, 'danisan_adi': 'AHMET', ...}

# Ödeme (handler tetiklenir)
pipeline.odeme_ekle(record_id=123, tutar=500, ...)
# [EVENT] {'record_id': 123, 'tutar': 500, ...}
```

### Test 3: SMS/Email Bildirimi

```python
# Mock test (gerçek API olmadan)
pipeline = DataPipeline(conn, kullanici_id=1)

basarili = pipeline.send_notification(
    notification_type="odeme_alindi",
    recipient="+905551234567",
    message="Test mesajı",
    method="sms"
)

if basarili:
    print("✅ Bildirim gönderildi (mock)")
```

---

## 📊 Özet

| Özellik | Durum | Gerekli Entegrasyon |
|---------|-------|---------------------|
| **Oda Çakışma Kontrolü** | ✅ Hazır | Yok (out-of-the-box) |
| **Event Listeners** | ✅ Hazır | Yok (callback fonksiyonları) |
| **SMS Bildirimi** | 🔧 Şablon | Twilio/NetGSM API |
| **Email Bildirimi** | 🔧 Şablon | SMTP/SendGrid API |

---

## 🚀 Sonraki Adımlar

1. **SMS/Email API seç** (Twilio, NetGSM, SendGrid, vb.)
2. **API anahtarları al** (ücretsiz deneme hesapları var)
3. **`_send_sms()` ve `_send_email()` fonksiyonlarını** gerçek API ile değiştir
4. **Test et** (küçük grupla)
5. **Production'a al**

---

**Güncelleme:** 24 Ocak 2026  
**Versiyon:** v1.2 (Opsiyonel Özellikler)  
© 2026 Leta Aile ve Çocuk


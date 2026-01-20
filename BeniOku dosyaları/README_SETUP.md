# Leta Yönetim Sistemi - Kurulum Kılavuzu

## Sistem Gereksinimleri
- Windows 7 veya üzeri
- 64-bit işletim sistemi (önerilir)

## Kurulum Yöntemleri

### Yöntem 1: Setup Dosyası ile Kurulum (Önerilen)

1. `installer` klasöründeki `Leta_Yonetim_Setup_v4.0.exe` dosyasını çalıştırın
2. Kurulum sihirbazını takip edin
3. Program otomatik olarak masaüstüne kısayol oluşturacaktır

### Yöntem 2: Manuel Kurulum

1. `dist` klasöründeki tüm dosyaları bir klasöre kopyalayın (örn: `C:\Leta Yönetim`)
2. `Leta_Yonetim_Final.exe` dosyasını çalıştırın
3. İlk açılışta veritabanı otomatik oluşturulacaktır

## Setup Dosyası Oluşturma

### Otomatik (Batch Script ile)

1. `build_setup.bat` dosyasını çalıştırın
2. Script otomatik olarak:
   - EXE dosyasını oluşturacak
   - Setup dosyasını oluşturacak (Inno Setup yüklüyse)

### Manuel

1. **EXE Oluşturma:**
   ```bash
   pyinstaller --clean Leta_Yonetim_Final.spec
   ```

2. **Setup Oluşturma:**
   - Inno Setup Compiler'ı indirin: https://jrsoftware.org/isdl.php
   - `setup.iss` dosyasını Inno Setup ile açın
   - "Build > Compile" menüsünden derleyin
   - Setup dosyası `installer` klasöründe oluşacaktır

## Kullanım

### İlk Giriş
- Kullanıcı adı: `admin`
- Şifre: `1234`

### Özellikler
- ✅ Yeni seans kaydı ekleme
- ✅ Borç sorgulama ve listeleme
- ✅ Ödeme ekleme (sağ tık menüsü)
- ✅ Kayıt silme
- ✅ Excel'e aktarma
- ✅ Otomatik yedekleme

### Ödeme Ekleme
1. Tabloda bir kayda sağ tıklayın
2. "Ödeme Ekle" seçeneğini seçin
3. Ödenen miktarı girin
4. Sistem otomatik olarak borcu güncelleyecektir

## Sorun Giderme

### Program açılmıyor
- Windows Defender veya antivirüs programını kontrol edin
- Programı yönetici olarak çalıştırmayı deneyin

### Veritabanı hatası
- Program klasöründe yazma izni olduğundan emin olun
- `Yedekler` klasöründen son yedeği geri yükleyin

### Excel aktarma hatası
- Microsoft Excel veya LibreOffice yüklü olmalıdır
- Alternatif olarak CSV formatı kullanılabilir (gelecek güncellemede)

## Yedekleme

Program her açılışta otomatik yedek alır. Yedekler `Yedekler` klasöründe saklanır.
Son 10 yedek tutulur, eski yedekler otomatik silinir.

## Destek

Sorunlar için lütfen geliştirici ile iletişime geçin.


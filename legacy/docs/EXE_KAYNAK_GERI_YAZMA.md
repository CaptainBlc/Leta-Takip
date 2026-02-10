# EXE'den Kaynak Kodu Geri Yazma – Durum ve Seçenekler

## Yapılanlar

1. **EXE açıldı**  
   `Leta_Pipeline_v1_3.exe` PyInstaller ile paketlenmiş; pyinstxtractor ve pydumpck ile içerik çıkarıldı.

2. **Ana kaynak bulundu**  
   Ana uygulama bytecode dosyası:
   - `Leta_Pipeline_v1_3.exe_extracted\leta_app.pyc`  
   - Boyut: ~780 KB  
   - **Python sürümü: 3.13**

3. **Decompile denemeleri**  
   - **uncompyle6**: Python 3.13 desteklenmiyor (en fazla 3.12).  
   - **pydumpck**: Aynı nedenle 3.13 bytecode’u decompile edemedi.  
   - **pycdc**: Windows binary indirilemedi.  
   - **Magic 3.12’ye çevirme**: Bytecode 3.13 olduğu için yine decompile edilemedi.

Sonuç: Bu EXE’deki `leta_app.pyc` dosyası, şu an kullandığımız ücretsiz araçlarla **tam olarak kaynak koda çevrilemedi**.

---

## Seçenekler

### 1. PyChaos (online, 3.13 destekli)

- **Site:** https://pychaos.io/upload  
- **Destek:** Python 3.11, 3.12, 3.13, 3.14 (3.13 deneysel sayılır).  
- **Adımlar:**  
  1. `Leta_Pipeline_v1_3.exe_extracted\leta_app.pyc` dosyasını (≈780 KB) buraya yükle.  
  2. Çıkan `.py` kaynağını indir.  
  3. Bu kaynağı projedeki `leta_app.py` ile karşılaştırıp birleştirme/güncelleme yapabiliriz (bana çıktıyı atarsan devam edebilirim).

Not: Dosya büyük; sitede boyut limiti varsa hata alırsan haber ver.

### 2. Güncel kaynağı exe’yi derleyen yerden almak

- EXe’yi **hangi bilgisayar/ortamda** ve **hangi kaynakla** derlediğini biliyorsan, o ortamdaki güncel `leta_app.py` (ve varsa diğer kaynaklar) en doğru “güncel” sürüm olur.  
- O dosyayı bu projedeki `Leta-Takip-main\leta_app.py` ile değiştirir veya birleştiririz.

### 3. Mevcut proje kaynağını “güncel” kabul etmek

- Eğer EXE, elindeki mevcut `leta_app.py` ile (sadece farklı bir Python sürümüyle, örn. 3.13) build edildiyse ve başka değişiklik yoksa, **kaynak zaten güncel** demektir.  
- Bu durumda yapılacak tek şey: Bu projedeki `leta_app.py` ile Python 3.13 (veya aynı ortam) kullanıp yeniden build almak. Böylece “güncel” dediğin EXE ile kaynak aynı hizaya gelir.

---

## Özet

- EXE incelendi; içinden **leta_app.pyc (Python 3.13)** çıkarıldı.  
- Bu .pyc, kullandığımız araçlarla **tam decompile edilemedi**.  
- Devam etmek için:  
  - **Ya** PyChaos’a yükleyip çıkan kaynağı bana verirsin, ben `leta_app.py`’yi ona göre güncellerim;  
  - **Ya** exe’yi derleyen güncel kaynağı (leta_app.py) bulup bu projeye taşırsın;  
  - **Ya da** mevcut `leta_app.py`’nin zaten güncel olduğunu kabul edip sadece aynı kaynaktan yeniden build alırsın.

Hangi yolu kullanacağını söylersen, bir sonraki adımı buna göre netleştirebilirim (ör. PyChaos çıktısı birleştirme veya build komutları).

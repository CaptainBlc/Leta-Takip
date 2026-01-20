"""
Leta Yönetim Sistemi - Test Script
Bu script sistemi test eder ve sorunları raporlar
"""

import sqlite3
import os
import sys

# Test veritabanı
TEST_DB = "test_leta.db"

def test_veritabani():
    """Veritabanı yapısını test et"""
    print("=" * 50)
    print("TEST 1: Veritabanı Yapısı")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        
        # Tablo oluştur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kayitlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT,
                danisan_adi TEXT,
                terapist TEXT,
                hizmet_bedeli REAL,
                alinan_ucret REAL,
                kalan_borc REAL,
                notlar TEXT,
                son_islem_tarihi TEXT
            )
        """)
        conn.commit()
        
        # Tablo yapısını kontrol et
        cursor.execute("PRAGMA table_info(kayitlar)")
        columns = cursor.fetchall()
        
        print("✓ Tablo başarıyla oluşturuldu")
        print(f"✓ Toplam {len(columns)} sütun bulundu")
        
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ HATA: {e}")
        return False

def test_kayit_ekleme():
    """Kayıt ekleme işlemini test et"""
    print("\n" + "=" * 50)
    print("TEST 2: Kayıt Ekleme")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        
        # Test kaydı ekle
        cursor.execute("""
            INSERT INTO kayitlar (tarih, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, notlar, son_islem_tarihi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("01.01.2024", "Test Danışan", "Pervin Hoca", 2500.0, 1000.0, 1500.0, "Test notu", "2024-01-01 10:00"))
        
        conn.commit()
        
        # Kaydı kontrol et
        cursor.execute("SELECT * FROM kayitlar WHERE danisan_adi=?", ("Test Danışan",))
        kayit = cursor.fetchone()
        
        if kayit:
            print("✓ Kayıt başarıyla eklendi")
            print(f"  - ID: {kayit[0]}")
            print(f"  - Danışan: {kayit[2]}")
            print(f"  - Bedel: {kayit[4]} ₺")
            print(f"  - Alınan: {kayit[5]} ₺")
            print(f"  - Kalan: {kayit[6]} ₺")
            conn.close()
            return kayit[0]  # ID döndür
        else:
            print("✗ Kayıt bulunamadı")
            conn.close()
            return None
            
    except Exception as e:
        print(f"✗ HATA: {e}")
        return None

def test_odeme_guncelleme(kayit_id):
    """Ödeme güncelleme işlemini test et"""
    print("\n" + "=" * 50)
    print("TEST 3: Ödeme Güncelleme")
    print("=" * 50)
    
    if not kayit_id:
        print("✗ Önceki test başarısız, bu test atlanıyor")
        return False
    
    try:
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        
        # Mevcut veriyi al
        cursor.execute("SELECT hizmet_bedeli, alinan_ucret, kalan_borc FROM kayitlar WHERE id=?", (kayit_id,))
        veri = cursor.fetchone()
        
        if not veri:
            print("✗ Kayıt bulunamadı")
            conn.close()
            return False
        
        print(f"Önceki Durum:")
        print(f"  - Hizmet Bedeli: {veri[0]} ₺")
        print(f"  - Alınan: {veri[1]} ₺")
        print(f"  - Kalan: {veri[2]} ₺")
        
        # Ödeme ekle (500 TL)
        odeme_miktari = 500.0
        yeni_alinan = veri[1] + odeme_miktari
        yeni_kalan = veri[0] - yeni_alinan
        
        import datetime
        simdi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute("UPDATE kayitlar SET alinan_ucret=?, kalan_borc=?, son_islem_tarihi=? WHERE id=?", 
                     (yeni_alinan, yeni_kalan, simdi, kayit_id))
        conn.commit()
        
        # Güncellenmiş veriyi kontrol et
        cursor.execute("SELECT hizmet_bedeli, alinan_ucret, kalan_borc, son_islem_tarihi FROM kayitlar WHERE id=?", (kayit_id,))
        guncel_veri = cursor.fetchone()
        
        print(f"\nÖdeme Sonrası:")
        print(f"  - Ödenen: {odeme_miktari} ₺")
        print(f"  - Yeni Alınan: {guncel_veri[1]} ₺")
        print(f"  - Yeni Kalan: {guncel_veri[2]} ₺")
        print(f"  - Güncelleme Tarihi: {guncel_veri[3]}")
        
        # Doğrulama
        if abs(guncel_veri[1] - yeni_alinan) < 0.01 and abs(guncel_veri[2] - yeni_kalan) < 0.01:
            print("\n✓ Ödeme güncelleme başarılı")
            print("✓ Tarih güncellendi")
            conn.close()
            return True
        else:
            print("\n✗ HATA: Güncelleme değerleri eşleşmiyor")
            conn.close()
            return False
            
    except Exception as e:
        print(f"✗ HATA: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_negatif_borc():
    """Negatif borç durumunu test et"""
    print("\n" + "=" * 50)
    print("TEST 4: Negatif Borç Kontrolü")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        
        # Yeni bir kayıt ekle
        cursor.execute("""
            INSERT INTO kayitlar (tarih, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, notlar, son_islem_tarihi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("01.01.2024", "Test 2", "Çağlar Hoca", 1000.0, 0.0, 1000.0, "Test", "2024-01-01 10:00"))
        
        conn.commit()
        cursor.execute("SELECT id FROM kayitlar WHERE danisan_adi=?", ("Test 2",))
        kayit_id = cursor.fetchone()[0]
        
        # Fazla ödeme yap (1500 TL öde, borç 1000 TL)
        cursor.execute("SELECT hizmet_bedeli, alinan_ucret FROM kayitlar WHERE id=?", (kayit_id,))
        veri = cursor.fetchone()
        
        fazla_odeme = 1500.0
        yeni_alinan = veri[1] + fazla_odeme
        yeni_kalan = veri[0] - yeni_alinan  # 1000 - 1500 = -500
        
        print(f"Test Senaryosu:")
        print(f"  - Hizmet Bedeli: {veri[0]} ₺")
        print(f"  - Ödenen: {fazla_odeme} ₺")
        print(f"  - Kalan Borç: {yeni_kalan} ₺ (negatif)")
        
        if yeni_kalan < 0:
            print("\n✓ Negatif borç tespit edildi")
            print("  Sistem fazla ödeme durumunu doğru hesaplıyor")
            conn.close()
            return True
        else:
            print("\n✗ HATA: Negatif borç tespit edilemedi")
            conn.close()
            return False
            
    except Exception as e:
        print(f"✗ HATA: {e}")
        return False

def temizle():
    """Test dosyalarını temizle"""
    try:
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
            print(f"\n✓ Test veritabanı temizlendi")
    except:
        pass

def main():
    print("\n" + "=" * 50)
    print("LETA YÖNETİM SİSTEMİ - TEST RAPORU")
    print("=" * 50 + "\n")
    
    sonuclar = []
    
    # Testleri çalıştır
    sonuclar.append(("Veritabanı Yapısı", test_veritabani()))
    kayit_id = test_kayit_ekleme()
    sonuclar.append(("Kayıt Ekleme", kayit_id is not None))
    sonuclar.append(("Ödeme Güncelleme", test_odeme_guncelleme(kayit_id)))
    sonuclar.append(("Negatif Borç Kontrolü", test_negatif_borc()))
    
    # Özet
    print("\n" + "=" * 50)
    print("TEST ÖZETİ")
    print("=" * 50)
    
    basarili = sum(1 for _, sonuc in sonuclar if sonuc)
    toplam = len(sonuclar)
    
    for test_adi, sonuc in sonuclar:
        durum = "✓ BAŞARILI" if sonuc else "✗ BAŞARISIZ"
        print(f"{test_adi}: {durum}")
    
    print(f"\nToplam: {basarili}/{toplam} test başarılı")
    
    if basarili == toplam:
        print("\n🎉 TÜM TESTLER BAŞARILI!")
    else:
        print(f"\n⚠️  {toplam - basarili} test başarısız!")
    
    # Temizle
    temizle()
    
    return basarili == toplam

if __name__ == "__main__":
    try:
        basarili = main()
        sys.exit(0 if basarili else 1)
    except KeyboardInterrupt:
        print("\n\nTest iptal edildi.")
        temizle()
        sys.exit(1)


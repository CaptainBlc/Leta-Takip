"""
Leta Takip - Eski Veri Migration Script
Eski veritabanından yeni sisteme veri aktarımı için kullanılır.
"""

import sqlite3
import datetime
import os
import sys

def migrate_eski_veriler(eski_db_yolu: str, yeni_db_yolu: str = None) -> dict:
    """
    Eski veritabanından yeni sisteme veri aktar.
    
    Args:
        eski_db_yolu: Eski veritabanı dosya yolu
        yeni_db_yolu: Yeni veritabanı dosya yolu (None ise mevcut DB kullanılır)
    
    Returns:
        dict: Migration sonuçları
    """
    if not os.path.exists(eski_db_yolu):
        return {"success": False, "error": f"Eski veritabanı bulunamadı: {eski_db_yolu}"}
    
    # Yeni DB yolu belirlenmediyse mevcut DB'yi kullan
    if yeni_db_yolu is None:
        # leta_app.py'deki db_path() fonksiyonunu taklit et
        if getattr(sys, "frozen", False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        yeni_db_yolu = os.path.join(app_dir, "leta_data.db")
    
    results = {
        "success": True,
        "migrated_tables": {},
        "errors": []
    }
    
    try:
        eski_conn = sqlite3.connect(eski_db_yolu)
        eski_cur = eski_conn.cursor()
        
        yeni_conn = sqlite3.connect(yeni_db_yolu)
        yeni_cur = yeni_conn.cursor()
        
        # Migration log tablosunu oluştur
        yeni_cur.execute("""
            CREATE TABLE IF NOT EXISTS migration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_adi TEXT NOT NULL,
                migration_tarihi TEXT NOT NULL,
                kayit_sayisi INTEGER DEFAULT 0,
                durum TEXT DEFAULT 'tamamlandi',
                hata_mesaji TEXT,
                detay TEXT
            )
        """)
        
        migration_tarihi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Danışanlar migration
        try:
            eski_cur.execute("SELECT * FROM danisanlar")
            danisanlar = eski_cur.fetchall()
            
            migrated_count = 0
            for row in danisanlar:
                try:
                    # Eski tablo yapısına göre uyarlama yapılabilir
                    yeni_cur.execute("""
                        INSERT OR IGNORE INTO danisanlar 
                        (ad_soyad, telefon, email, adres, dogum_tarihi, veli_adi, veli_telefon, notlar, olusturma_tarihi, aktif)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row[1] if len(row) > 1 else "",  # ad_soyad
                        row[2] if len(row) > 2 else "",  # telefon
                        row[3] if len(row) > 3 else "",  # email
                        row[4] if len(row) > 4 else "",  # adres
                        row[5] if len(row) > 5 else "",  # dogum_tarihi
                        row[6] if len(row) > 6 else "",  # veli_adi
                        row[7] if len(row) > 7 else "",  # veli_telefon
                        row[8] if len(row) > 8 else "",  # notlar
                        row[9] if len(row) > 9 else migration_tarihi,  # olusturma_tarihi
                        1  # aktif
                    ))
                    migrated_count += 1
                except Exception as e:
                    results["errors"].append(f"Danışan migration hatası (ID: {row[0]}): {e}")
            
            yeni_cur.execute("""
                INSERT INTO migration_log 
                (migration_adi, migration_tarihi, kayit_sayisi, durum, detay)
                VALUES (?, ?, ?, 'tamamlandi', ?)
            """, ("danisanlar", migration_tarihi, migrated_count, f"{migrated_count} danışan aktarıldı"))
            
            results["migrated_tables"]["danisanlar"] = migrated_count
        except Exception as e:
            results["errors"].append(f"Danışanlar tablosu migration hatası: {e}")
        
        # 2. Seans Takvimi migration
        try:
            eski_cur.execute("SELECT * FROM seans_takvimi")
            seanslar = eski_cur.fetchall()
            
            migrated_count = 0
            for row in seanslar:
                try:
                    yeni_cur.execute("""
                        INSERT OR IGNORE INTO seans_takvimi
                        (tarih, saat, danisan_adi, terapist, oda, durum, seans_alindi, ucret_alindi, ucret_tutar, notlar, olusturma_tarihi)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row[1] if len(row) > 1 else "",  # tarih
                        row[2] if len(row) > 2 else "",  # saat
                        row[3] if len(row) > 3 else "",  # danisan_adi
                        row[4] if len(row) > 4 else "",  # terapist
                        row[5] if len(row) > 5 else "",  # oda
                        row[6] if len(row) > 6 else "planlandi",  # durum
                        row[7] if len(row) > 7 else 0,  # seans_alindi
                        row[8] if len(row) > 8 else 0,  # ucret_alindi
                        row[9] if len(row) > 9 else 0,  # ucret_tutar
                        row[10] if len(row) > 10 else "",  # notlar
                        row[11] if len(row) > 11 else migration_tarihi  # olusturma_tarihi
                    ))
                    migrated_count += 1
                except Exception as e:
                    results["errors"].append(f"Seans migration hatası (ID: {row[0]}): {e}")
            
            yeni_cur.execute("""
                INSERT INTO migration_log 
                (migration_adi, migration_tarihi, kayit_sayisi, durum, detay)
                VALUES (?, ?, ?, 'tamamlandi', ?)
            """, ("seans_takvimi", migration_tarihi, migrated_count, f"{migrated_count} seans aktarıldı"))
            
            results["migrated_tables"]["seans_takvimi"] = migrated_count
        except Exception as e:
            results["errors"].append(f"Seans takvimi tablosu migration hatası: {e}")
        
        # 3. Records migration
        try:
            eski_cur.execute("SELECT * FROM records")
            records = eski_cur.fetchall()
            
            migrated_count = 0
            for row in records:
                try:
                    yeni_cur.execute("""
                        INSERT OR IGNORE INTO records
                        (tarih, saat, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, seans_id, notlar, olusturma_tarihi)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row[1] if len(row) > 1 else "",  # tarih
                        row[2] if len(row) > 2 else "",  # saat
                        row[3] if len(row) > 3 else "",  # danisan_adi
                        row[4] if len(row) > 4 else "",  # terapist
                        float(row[5]) if len(row) > 5 and row[5] else 0,  # hizmet_bedeli
                        float(row[6]) if len(row) > 6 and row[6] else 0,  # alinan_ucret
                        float(row[7]) if len(row) > 7 and row[7] else 0,  # kalan_borc
                        row[8] if len(row) > 8 else None,  # seans_id
                        row[9] if len(row) > 9 else "",  # notlar
                        row[10] if len(row) > 10 else migration_tarihi  # olusturma_tarihi
                    ))
                    migrated_count += 1
                except Exception as e:
                    results["errors"].append(f"Record migration hatası (ID: {row[0]}): {e}")
            
            yeni_cur.execute("""
                INSERT INTO migration_log 
                (migration_adi, migration_tarihi, kayit_sayisi, durum, detay)
                VALUES (?, ?, ?, 'tamamlandi', ?)
            """, ("records", migration_tarihi, migrated_count, f"{migrated_count} record aktarıldı"))
            
            results["migrated_tables"]["records"] = migrated_count
        except Exception as e:
            results["errors"].append(f"Records tablosu migration hatası: {e}")
        
        # 4. Kasa Hareketleri migration
        try:
            eski_cur.execute("SELECT * FROM kasa_hareketleri")
            kasa_hareketleri = eski_cur.fetchall()
            
            migrated_count = 0
            for row in kasa_hareketleri:
                try:
                    yeni_cur.execute("""
                        INSERT OR IGNORE INTO kasa_hareketleri
                        (tarih, tip, aciklama, tutar, odeme_sekli, record_id, seans_id, olusturma_tarihi)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row[1] if len(row) > 1 else "",  # tarih
                        row[2] if len(row) > 2 else "giren",  # tip
                        row[3] if len(row) > 3 else "",  # aciklama
                        float(row[4]) if len(row) > 4 and row[4] else 0,  # tutar
                        row[5] if len(row) > 5 else "",  # odeme_sekli
                        row[6] if len(row) > 6 else None,  # record_id
                        row[7] if len(row) > 7 else None,  # seans_id
                        row[8] if len(row) > 8 else migration_tarihi  # olusturma_tarihi
                    ))
                    migrated_count += 1
                except Exception as e:
                    results["errors"].append(f"Kasa hareketi migration hatası (ID: {row[0]}): {e}")
            
            yeni_cur.execute("""
                INSERT INTO migration_log 
                (migration_adi, migration_tarihi, kayit_sayisi, durum, detay)
                VALUES (?, ?, ?, 'tamamlandi', ?)
            """, ("kasa_hareketleri", migration_tarihi, migrated_count, f"{migrated_count} kasa hareketi aktarıldı"))
            
            results["migrated_tables"]["kasa_hareketleri"] = migrated_count
        except Exception as e:
            results["errors"].append(f"Kasa hareketleri tablosu migration hatası: {e}")
        
        yeni_conn.commit()
        eski_conn.close()
        yeni_conn.close()
        
        results["success"] = True
        
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Genel migration hatası: {e}")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Kullanım: python migration_eski_veriler.py <eski_db_yolu> [yeni_db_yolu]")
        sys.exit(1)
    
    eski_db = sys.argv[1]
    yeni_db = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("🔄 Eski veri migration başlatılıyor...")
    print(f"Eski DB: {eski_db}")
    print(f"Yeni DB: {yeni_db or 'Mevcut DB'}")
    print()
    
    results = migrate_eski_veriler(eski_db, yeni_db)
    
    if results["success"]:
        print("✅ Migration tamamlandı!")
        print()
        print("Aktarılan Tablolar:")
        for table, count in results["migrated_tables"].items():
            print(f"  • {table}: {count} kayıt")
        print()
        if results["errors"]:
            print("⚠️ Hatalar:")
            for error in results["errors"]:
                print(f"  • {error}")
    else:
        print("❌ Migration başarısız!")
        print()
        print("Hatalar:")
        for error in results["errors"]:
            print(f"  • {error}")


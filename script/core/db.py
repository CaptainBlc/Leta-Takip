import sqlite3
from pathlib import Path

DB_PATH = Path("leta.db")


def _ensure_minimum_schema(conn: sqlite3.Connection) -> None:
    """Login/register ve temel UI akışlarının ihtiyaç duyduğu minimum şema."""
    cur = conn.cursor()

    # Kullanıcı yönetimi
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'egitim_gorevlisi',
            access_role TEXT DEFAULT 'egitim_gorevlisi',
            title_role TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            therapist_name TEXT,
            created_at TEXT,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
        """
    )

    # Terapist/ayar listeleri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            therapist_name TEXT UNIQUE,
            is_active INTEGER DEFAULT 1
        )
        """
    )

    # Danışan temel tablosu
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS danisanlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            telefon TEXT DEFAULT '',
            email TEXT DEFAULT '',
            veli_adi TEXT DEFAULT '',
            veli_telefon TEXT DEFAULT '',
            dogum_tarihi TEXT DEFAULT '',
            adres TEXT DEFAULT '',
            notlar TEXT DEFAULT '',
            olusturma_tarihi TEXT,
            aktif INTEGER DEFAULT 1,
            balance REAL DEFAULT 0
        )
        """
    )

    # Refactor modüllerinin kullandığı tablolar
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS seans_takvimi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            saat TEXT,
            danisan_adi TEXT,
            terapist TEXT,
            oda TEXT,
            durum TEXT DEFAULT 'planlandi',
            notlar TEXT DEFAULT '',
            hizmet_bedeli REAL DEFAULT 0,
            odeme_sekli TEXT DEFAULT '',
            seans_alindi INTEGER DEFAULT 0,
            ucret_alindi INTEGER DEFAULT 0,
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER,
            record_id INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            saat TEXT,
            danisan_adi TEXT,
            terapist TEXT,
            hizmet_bedeli REAL DEFAULT 0,
            alinan_ucret REAL DEFAULT 0,
            kalan_borc REAL DEFAULT 0,
            seans_alindi INTEGER DEFAULT 0,
            notlar TEXT DEFAULT '',
            olusturma_tarihi TEXT,
            seans_id INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS odeme_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER,
            tutar REAL DEFAULT 0,
            tarih TEXT,
            odeme_sekli TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kasa_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            tip TEXT,
            aciklama TEXT,
            tutar REAL DEFAULT 0,
            odeme_sekli TEXT DEFAULT '',
            gider_kategorisi TEXT DEFAULT '',
            record_id INTEGER,
            seans_id INTEGER,
            olusturan_kullanici_id INTEGER,
            olusturma_tarihi TEXT
        )
        """
    )

    # Fiyatlandırma ve ücret takip modülleri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ogrenci_personel_fiyatlandirma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER NOT NULL,
            personel_adi TEXT NOT NULL,
            seans_ucreti REAL NOT NULL,
            baslangic_tarihi TEXT,
            bitis_tarihi TEXT,
            aktif INTEGER DEFAULT 1,
            zam_orani REAL DEFAULT 0,
            zam_uygulama_tarihi TEXT,
            olusturma_tarihi TEXT,
            guncelleme_tarihi TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fiyat_ogrenci ON ogrenci_personel_fiyatlandirma(ogrenci_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fiyat_personel ON ogrenci_personel_fiyatlandirma(personel_adi)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS personel_ucret_takibi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_adi TEXT NOT NULL,
            seans_id INTEGER,
            tarih TEXT NOT NULL,
            seans_ucreti REAL NOT NULL,
            personel_ucreti REAL NOT NULL,
            ucret_orani REAL DEFAULT 0,
            odeme_durumu TEXT DEFAULT 'beklemede',
            odeme_tarihi TEXT,
            aciklama TEXT,
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_personel_ucret_personel ON personel_ucret_takibi(personel_adi)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cocuk_gunluk_takip (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cocuk_id INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            oda_adi TEXT,
            personel_adi TEXT NOT NULL,
            seans_id INTEGER,
            notlar TEXT,
            olusturma_tarihi TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cocuk_gunluk_tarih ON cocuk_gunluk_takip(tarih)")

    # Fiyat politikası (otomatik ücret)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pricing_policy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            teacher_name TEXT,
            price REAL NOT NULL,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(student_id, teacher_name)
        )
        """
    )

    # Audit trail / sistem logları
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_trail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            kullanici_id INTEGER,
            details TEXT,
            ip_address TEXT,
            olusturma_tarihi TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_tarih ON audit_trail(olusturma_tarihi)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sistem_gunlugu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            olay TEXT,
            aciklama TEXT,
            olusturma_tarihi TEXT
        )
        """
    )


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_minimum_schema(conn)
    conn.commit()
    return conn


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_minimum_schema(conn)

    # Geriye dönük legacy tablolar (eski scriptler için)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS seanslar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            saat TEXT,
            danisan TEXT NOT NULL,
            terapist TEXT NOT NULL,
            ucret REAL DEFAULT 0,
            alinan REAL DEFAULT 0,
            kalan REAL DEFAULT 0,
            notlar TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kayitlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seans_id INTEGER,
            tarih TEXT NOT NULL,
            danisan TEXT NOT NULL,
            terapist TEXT,
            ucret REAL DEFAULT 0,
            alinan REAL DEFAULT 0,
            kalan_borc REAL DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kasa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            tip TEXT CHECK(tip IN ('giren','cikan')) NOT NULL,
            aciklama TEXT,
            tutar REAL DEFAULT 0
        )
        """
    )

    conn.commit()
    conn.close()

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

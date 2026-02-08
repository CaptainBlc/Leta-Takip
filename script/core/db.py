import sqlite3
from pathlib import Path

DB_PATH = Path("leta.db")


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect_db()
    cur = conn.cursor()

    # SEANSLAR
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

    # KAYITLAR (BORÇ / TAKİP)
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

    # KASA
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

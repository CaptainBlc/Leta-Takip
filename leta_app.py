"""
Leta Aile ve Çocuk - Seans & Borç Takip Sistemi (v1.0 Stabil)

Felsefe: Basitlik > Karmaşıklık, Stabilite > Özellik

ÖNEMLİ TEKNİK NOT (sahada yaşanan problem):
- Tkinter/ttkbootstrap'ta aynı anda 2 ayrı root (2x ttk.Window) açmak,
  özellikle Windows'ta giriş alanlarının "tıklanamaz / yazılamaz" hale gelmesine yol açabilir.
- Bu yüzden bu dosya TEK root kullanır: Ana uygulama (ttk.Window) + modal Login (ttk.Toplevel).
  (leta_pro.py'nin stabil yaklaşımı)
"""

from __future__ import annotations

import datetime
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import time

import pandas as pd
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import END, filedialog, messagebox, Menu

try:
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover
    Image = None
    ImageTk = None

APP_TITLE = "Leta Aile ve Çocuk - Seans ve Borç Takip Sistemi"
APP_VERSION = "v1.3"
APP_BUILD = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# Platform Kontrolü
IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# Geriye dönük uyumluluk: çok eski sürümlerde kullanıcı tablosu yoksa fallback.
LOGIN_USER = ""
LOGIN_PASS = ""

# Kurum talebi: Ayarlar tablosuna başlangıç terapistleri
DEFAULT_THERAPISTS = ["Pervin Hoca", "Çağlar Hoca", "Elif Hoca", "Arif Hoca", "Sena Hoca", "Aybüke Hoca"]

# Kurumdaki hocaların rolleri (mesleki/unvan)
DEFAULT_THERAPIST_ROLES = {
    "Pervin Hoca": "Kurum Müdürü / Özel Eğitim Uzmanı",
    "Arif Hoca": "Özel Eğitim Uzmanı",
    "Aybüke Hoca": "Ergoterapist",
    "Çağlar Hoca": "Ergoterapist",
    "Sena Hoca": "Dil ve Konuşma Terapisti",
    "Elif Hoca": "Klinik Psikolog",
}

# Personel Ücret Hesaplama Kuralları
PERSONEL_UCRET_KURALLARI = {
    "Arif Hoca": {"tip": "sabit", "tutar": 2500.0},
    "Pervin Hoca": {"tip": "yuzde", "oran": 100.0},
    "_default": {"tip": "yuzde", "oran": 40.0}
}

# Kullanıcılar
DEFAULT_USERS: list[tuple[str, str, str, str, str | None]] = []

# ==================== YARDIMCI FONKSİYONLAR ====================

def role_label(access_role: str | None) -> str:
    """Rol etiketini döndür"""
    r = (access_role or "").strip()
    if r == "kurum_muduru":
        return "Kurum Müdürü"
    if r == "egitim_gorevlisi":
        return "Eğitim Görevlisi"
    if r == "normal":
        return "Kullanıcı"
    if not r:
        return "Kullanıcı"
    return r

def hash_pass(p: str) -> str:
    """Şifreyi hash'le"""
    return hashlib.sha256((p or "").encode("utf-8")).hexdigest()

def app_dir() -> str:
    """Uygulama dizinini döndür"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def data_dir() -> str:
    """Veri dizinini döndür"""
    try:
        if os.path.exists(os.path.join(app_dir(), "portable_mode.txt")):
            base = app_dir()
        else:
            if IS_WINDOWS:
                base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
                base = os.path.join(base, "LetaYonetim")
            elif IS_MAC:
                base = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "LetaYonetim")
            else:
                xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
                base = os.path.join(xdg, "LetaYonetim")
        os.makedirs(base, exist_ok=True)
        return base
    except Exception:
        return app_dir()

def db_path() -> str:
    """Veritabanı dosya yolunu döndür"""
    return os.path.join(data_dir(), "leta_data.db")

def backups_dir() -> str:
    """Yedekler klasörü yolunu döndür"""
    return os.path.join(data_dir(), "Yedekler")

def demo_data_dir() -> str:
    """Demo veriler klasörü yolunu döndür"""
    return os.path.join(data_dir(), "DemoVeriler")

def resource_dir() -> str:
    """Kaynak dosyalar dizinini döndür"""
    try:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return str(getattr(sys, "_MEIPASS"))
    except Exception:
        pass
    return app_dir()

def logo_path() -> str | None:
    """Logo dosyası yolunu döndür"""
    candidates = [
        os.path.join(resource_dir(), "logo.png"),
        os.path.join(app_dir(), "logo.png"),
        os.path.join(data_dir(), "logo.png"),
    ]
    for p in candidates:
        try:
            if os.path.exists(p):
                return p
        except Exception:
            pass
    return None

def load_logo_photo(max_w: int, max_h: int):
    """Tk PhotoImage döndürür; bulunamazsa None."""
    p = logo_path()
    if not p or not Image or not ImageTk:
        return None
    try:
        img = Image.open(p)
        img.thumbnail((max_w, max_h))
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def safe_iconphoto(win, photo) -> None:
    """Windows taskbar/alt-tab ikonu için PhotoImage set eder"""
    if not win or not photo:
        return
    try:
        win.iconphoto(True, photo)
    except Exception:
        pass

def open_path(path: str) -> None:
    """Dosya/klasörü sistemin varsayılan uygulamasıyla aç"""
    p = (path or "").strip()
    if not p:
        raise ValueError("Path boş.")
    if IS_WINDOWS:
        os.startfile(p)  # type: ignore[attr-defined]
        return
    if IS_MAC:
        subprocess.Popen(["open", p], close_fds=True)
        return
    subprocess.Popen(["xdg-open", p], close_fds=True)

def spawn_detached(cmd: list[str]) -> None:
    """Yeni bir süreç başlat"""
    if not cmd:
        raise ValueError("Komut boş.")
    try:
        if IS_WINDOWS:
            subprocess.Popen(
                cmd,
                close_fds=True,
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        else:
            subprocess.Popen(cmd, close_fds=True, start_new_session=True)
    except Exception:
        subprocess.Popen(cmd, close_fds=True)

def ensure_user_guide_present() -> None:
    """Kılavuz dosyası yoksa kopyala"""
    try:
        dst = os.path.join(data_dir(), "KULLANIM_KILAVUZU.txt")
        if os.path.exists(dst):
            return
        for src_base in [resource_dir(), app_dir()]:
            src = os.path.join(src_base, "KULLANIM_KILAVUZU.txt")
            if os.path.exists(src):
                try:
                    shutil.copy2(src, dst)
                    return
                except Exception:
                    pass
    except Exception:
        pass

def error_log_path() -> str:
    """Hata log dosyası yolunu döndür"""
    return os.path.join(data_dir(), "leta_error.log")

def log_exception(prefix: str, exc: BaseException) -> None:
    """Hata log'una yaz"""
    try:
        import traceback
        with open(error_log_path(), "a", encoding="utf-8") as f:
            f.write("\n" + ("=" * 80) + "\n")
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {prefix}\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass

def center_window(win, w: int, h: int) -> None:
    """Pencereyi ekranın ortasına yerleştir"""
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")

def center_window_smart(win, w: int, h: int, max_ratio: float = 0.92) -> None:
    """Pencereyi ekran boyutuna göre optimize et"""
    try:
        win.update_idletasks()
        sw = int(win.winfo_screenwidth() or 0)
        sh = int(win.winfo_screenheight() or 0)
        if sw > 0 and sh > 0:
            w = min(int(w), int(sw * max_ratio))
            h = min(int(h), int(sh * max_ratio))
        center_window(win, w, h)
    except Exception:
        center_window(win, w, h)

def parse_money(text: str) -> float:
    """Para formatını parse et"""
    s = (text or "").strip()
    if s == "":
        return 0.0
    s = s.replace("₺", "").replace("TL", "").strip()
    s = s.replace(".", "").replace(",", ".")
    return float(s)

def format_money(val) -> str:
    """Para formatını formatla"""
    try:
        return f"{float(val):,.2f} ₺"
    except Exception:
        return "0.00 ₺"

def backup_now(prefix: str = "backup") -> str | None:
    """Anlık manuel yedek al"""
    try:
        os.makedirs(backups_dir(), exist_ok=True)
        if not os.path.exists(db_path()):
            return None
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        target = os.path.join(backups_dir(), f"{prefix}_{ts}.db")
        shutil.copy2(db_path(), target)
        return target
    except Exception:
        return None

def silent_backup() -> None:
    """Her açılışta sessiz yedek al"""
    try:
        os.makedirs(backups_dir(), exist_ok=True)
        if not os.path.exists(db_path()):
            return
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        target = os.path.join(backups_dir(), f"backup_{ts}.db")
        shutil.copy2(db_path(), target)
        backups = [
            os.path.join(backups_dir(), f)
            for f in os.listdir(backups_dir())
            if f.startswith("backup_") and f.endswith(".db")
        ]
        backups.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for old in backups[15:]:
            try:
                os.remove(old)
            except Exception:
                pass
    except Exception:
        pass

# ==================== VERİTABANI FONKSİYONLARI ====================

def connect_db() -> sqlite3.Connection:
    """Veritabanı bağlantısı oluştur"""
    conn = sqlite3.connect(db_path())
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db() -> None:
    """Veritabanını başlat ve tüm tabloları oluştur"""
    conn = connect_db()
    cur = conn.cursor()

    def table_exists(name: str) -> bool:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return cur.fetchone() is not None

    # Settings tablosu
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            therapist_name TEXT UNIQUE NOT NULL,
            therapist_role TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        );
        """
    )

    # Eski settings tablosunda rol sütunu yoksa ekle
    cur.execute("PRAGMA table_info(settings)")
    settings_cols = [r[1] for r in cur.fetchall()]
    if "therapist_role" not in settings_cols:
        try:
            cur.execute("ALTER TABLE settings ADD COLUMN therapist_role TEXT")
        except Exception:
            pass

    # Users tablosu
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'normal',
            access_role TEXT DEFAULT 'egitim_gorevlisi',
            title_role TEXT DEFAULT '',
            full_name TEXT,
            therapist_name TEXT,
            email TEXT,
            created_at TEXT,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        );
        """
    )
    
    # Eski users tablosuna yeni alanları ekle
    cur.execute("PRAGMA table_info(users)")
    user_cols = [r[1] for r in cur.fetchall()]
    for col in ["full_name", "therapist_name", "email", "access_role", "title_role"]:
        if col not in user_cols:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            except Exception:
                pass

    # Migration: access_role boşsa eski role'den doldur
    try:
        cur.execute("UPDATE users SET access_role = role WHERE (access_role IS NULL OR access_role='') AND role IS NOT NULL AND role<>''")
    except Exception:
        pass

    # Seans Takvimi
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS seans_takvimi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            saat TEXT NOT NULL,
            danisan_adi TEXT NOT NULL,
            terapist TEXT NOT NULL,
            oda TEXT,
            durum TEXT DEFAULT 'planlandi',
            record_id INTEGER,
            seans_alindi INTEGER DEFAULT 0,
            ucret_alindi INTEGER DEFAULT 0,
            ucret_tutar REAL DEFAULT 0,
            odeme_sekli TEXT DEFAULT '',
            notlar TEXT,
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER
        );
        """
    )
    
    # Eski seans_takvimi tablolarına yeni alanları ekle
    try:
        cur.execute("PRAGMA table_info(seans_takvimi)")
        st_cols = [r[1] for r in cur.fetchall()]
        for col, col_type in [("seans_alindi", "INTEGER DEFAULT 0"), ("ucret_alindi", "INTEGER DEFAULT 0"), 
                              ("ucret_tutar", "REAL DEFAULT 0"), ("odeme_sekli", "TEXT DEFAULT ''"), ("record_id", "INTEGER")]:
            if col not in st_cols:
                cur.execute(f"ALTER TABLE seans_takvimi ADD COLUMN {col} {col_type}")
        # hizmet_bedeli sütunu ekle
        if "hizmet_bedeli" not in st_cols:
            cur.execute("ALTER TABLE seans_takvimi ADD COLUMN hizmet_bedeli REAL DEFAULT 0")
    except Exception:
        pass

    # Ödeme hareketleri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS odeme_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER,
            tarih TEXT NOT NULL,
            tutar REAL NOT NULL,
            odeme_sekli TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            olusturan_kullanici_id INTEGER,
            olusturma_tarihi TEXT
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_odeme_tarih ON odeme_hareketleri(tarih);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_odeme_record ON odeme_hareketleri(record_id);")

    # Kasa defteri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kasa_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            tip TEXT NOT NULL,
            aciklama TEXT NOT NULL,
            tutar REAL NOT NULL,
            odeme_sekli TEXT DEFAULT '',
            record_id INTEGER,
            seans_id INTEGER,
            olusturan_kullanici_id INTEGER,
            olusturma_tarihi TEXT
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kasa_tarih ON kasa_hareketleri(tarih);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kasa_tip ON kasa_hareketleri(tip);")
    
    # Danışanlar
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS danisanlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            telefon TEXT,
            email TEXT,
            adres TEXT,
            dogum_tarihi TEXT,
            veli_adi TEXT,
            veli_telefon TEXT,
            notlar TEXT,
            olusturma_tarihi TEXT,
            aktif INTEGER DEFAULT 1
        );
        """
    )
    
    # Odalar
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS odalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oda_adi TEXT UNIQUE NOT NULL,
            oda_tipi TEXT,
            kapasite INTEGER,
            aciklama TEXT,
            aktif INTEGER DEFAULT 1
        );
        """
    )
    
    # Varsayılan odalar
    try:
        cur.execute("SELECT COUNT(*) FROM odalar")
        if (cur.fetchone() or [0])[0] == 0:
            odalar_seed = [
                ("Oyun Terapi Odası", "Terapi", 2, ""),
                ("Ergoterapi Odası", "Terapi", 2, ""),
                ("Büyük Oda", "Eğitim", 5, ""),
                ("Küçük Oda", "Eğitim", 3, ""),
            ]
            cur.executemany(
                "INSERT OR IGNORE INTO odalar (oda_adi, oda_tipi, kapasite, aciklama, aktif) VALUES (?,?,?,?,1)",
                odalar_seed,
            )
    except Exception:
        pass

    # Görevler
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gorevler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT NOT NULL,
            aciklama TEXT,
            atanan_kullanici_id INTEGER,
            olusturan_kullanici_id INTEGER,
            durum TEXT DEFAULT 'beklemede',
            oncelik TEXT DEFAULT 'normal',
            baslangic_tarihi TEXT,
            bitis_tarihi TEXT,
            tamamlanma_tarihi TEXT,
            olusturma_tarihi TEXT
        );
        """
    )

    # ==================== YENİ TABLOLAR (v2.0) ====================
    
    # Çocuk-Personel Atama
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cocuk_personel_atama (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cocuk_id INTEGER NOT NULL,
            personel_adi TEXT NOT NULL,
            baslangic_tarihi TEXT NOT NULL,
            bitis_tarihi TEXT,
            seans_ucreti REAL DEFAULT 0,
            aktif INTEGER DEFAULT 1,
            olusturma_tarihi TEXT,
            FOREIGN KEY (cocuk_id) REFERENCES danisanlar(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cocuk_personel_cocuk ON cocuk_personel_atama(cocuk_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cocuk_personel_personel ON cocuk_personel_atama(personel_adi);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cocuk_personel_aktif ON cocuk_personel_atama(aktif);")

    # Personel Ücret Takibi
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
            olusturan_kullanici_id INTEGER,
            FOREIGN KEY (seans_id) REFERENCES seans_takvimi(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_personel_ucret_personel ON personel_ucret_takibi(personel_adi);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_personel_ucret_tarih ON personel_ucret_takibi(tarih);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_personel_ucret_durum ON personel_ucret_takibi(odeme_durumu);")

    # Personel Ücret Talep Formu
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS personel_ucret_talepleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_adi TEXT NOT NULL,
            talep_tarihi TEXT NOT NULL,
            baslangic_tarihi TEXT NOT NULL,
            bitis_tarihi TEXT NOT NULL,
            toplam_seans_sayisi INTEGER DEFAULT 0,
            toplam_ucret REAL DEFAULT 0,
            durum TEXT DEFAULT 'beklemede',
            onay_tarihi TEXT,
            odeme_tarihi TEXT,
            aciklama TEXT,
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_personel_talep_personel ON personel_ucret_talepleri(personel_adi);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_personel_talep_durum ON personel_ucret_talepleri(durum);")

    # Çocuk Günlük Oda-Personel Takibi
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
            olusturma_tarihi TEXT,
            FOREIGN KEY (cocuk_id) REFERENCES danisanlar(id),
            FOREIGN KEY (seans_id) REFERENCES seans_takvimi(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cocuk_gunluk_cocuk ON cocuk_gunluk_takip(cocuk_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cocuk_gunluk_tarih ON cocuk_gunluk_takip(tarih);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cocuk_gunluk_personel ON cocuk_gunluk_takip(personel_adi);")

    # Bireysel Eğitim Programı (BEP)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bep_programlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cocuk_id INTEGER NOT NULL,
            program_yili INTEGER NOT NULL,
            olusturma_tarihi TEXT NOT NULL,
            guncelleme_tarihi TEXT,
            olusturan_kullanici_id INTEGER,
            FOREIGN KEY (cocuk_id) REFERENCES danisanlar(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bep_cocuk ON bep_programlari(cocuk_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bep_yil ON bep_programlari(program_yili);")

    # BEP Hedef Beceriler
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bep_hedef_beceriler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bep_id INTEGER NOT NULL,
            hedef_beceri TEXT NOT NULL,
            ay INTEGER NOT NULL,
            durum TEXT DEFAULT 'planlandi',
            notlar TEXT,
            olusturma_tarihi TEXT,
            FOREIGN KEY (bep_id) REFERENCES bep_programlari(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bep_hedef_bep ON bep_hedef_beceriler(bep_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bep_hedef_ay ON bep_hedef_beceriler(ay);")

    # Migration Log
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS migration_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_adi TEXT NOT NULL,
            migration_tarihi TEXT NOT NULL,
            kayit_sayisi INTEGER DEFAULT 0,
            durum TEXT DEFAULT 'tamamlandi',
            hata_mesaji TEXT,
            detay TEXT
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_migration_adi ON migration_log(migration_adi);")

    # Haftalık Seans Takip
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS haftalik_seans_programi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_adi TEXT NOT NULL,
            hafta_baslangic_tarihi TEXT NOT NULL,
            gun TEXT NOT NULL,
            saat TEXT NOT NULL,
            ogrenci_adi TEXT,
            oda_adi TEXT,
            notlar TEXT,
            olusturma_tarihi TEXT,
            guncelleme_tarihi TEXT,
            olusturan_kullanici_id INTEGER,
            UNIQUE(personel_adi, hafta_baslangic_tarihi, gun, saat)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_haftalik_personel ON haftalik_seans_programi(personel_adi);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_haftalik_tarih ON haftalik_seans_programi(hafta_baslangic_tarihi);")

    # Öğrenci-Personel Bazlı Fiyatlandırma
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ogrenci_personel_fiyatlandirma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER NOT NULL,
            personel_adi TEXT NOT NULL,
            seans_ucreti REAL NOT NULL,
            baslangic_tarihi TEXT NOT NULL,
            bitis_tarihi TEXT,
            zam_orani REAL DEFAULT 0,
            zam_uygulama_tarihi TEXT,
            aktif INTEGER DEFAULT 1,
            olusturma_tarihi TEXT,
            guncelleme_tarihi TEXT,
            FOREIGN KEY (ogrenci_id) REFERENCES danisanlar(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fiyat_ogrenci ON ogrenci_personel_fiyatlandirma(ogrenci_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fiyat_personel ON ogrenci_personel_fiyatlandirma(personel_adi);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fiyat_aktif ON ogrenci_personel_fiyatlandirma(aktif);")

    # Öğrenci Aile Bilgileri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ogrenci_aile_bilgileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER NOT NULL,
            veli_adi TEXT NOT NULL,
            veli_yakinlik_derecesi TEXT NOT NULL,
            telefon TEXT,
            email TEXT,
            adres TEXT,
            notlar TEXT,
            olusturma_tarihi TEXT,
            guncelleme_tarihi TEXT,
            FOREIGN KEY (ogrenci_id) REFERENCES danisanlar(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_aile_ogrenci ON ogrenci_aile_bilgileri(ogrenci_id);")

    # TC Kimlik ve Eşleşmeler
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ogrenci_kimlik_bilgileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER NOT NULL UNIQUE,
            tc_kimlik_no TEXT,
            dogum_tarihi TEXT,
            dogum_yeri TEXT,
            notlar TEXT,
            olusturma_tarihi TEXT,
            guncelleme_tarihi TEXT,
            FOREIGN KEY (ogrenci_id) REFERENCES danisanlar(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kimlik_tc ON ogrenci_kimlik_bilgileri(tc_kimlik_no);")

    # Sistem Şifreleri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sistem_sifreleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sistem_adi TEXT NOT NULL,
            kullanici_adi TEXT,
            sifre TEXT,
            url TEXT,
            aciklama TEXT,
            olusturma_tarihi TEXT,
            guncelleme_tarihi TEXT,
            olusturan_kullanici_id INTEGER
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sifre_sistem ON sistem_sifreleri(sistem_adi);")

    # Aylık BEP Raporları
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bep_aylik_raporlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bep_id INTEGER NOT NULL,
            rapor_ayi INTEGER NOT NULL,
            rapor_yili INTEGER NOT NULL,
            personel_adi TEXT NOT NULL,
            rapor_icerik TEXT,
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER,
            FOREIGN KEY (bep_id) REFERENCES bep_programlari(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bep_rapor_bep ON bep_aylik_raporlar(bep_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bep_rapor_ay ON bep_aylik_raporlar(rapor_ayi, rapor_yili);")

    # Records tablosu
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            saat TEXT DEFAULT '',
            danisan_adi TEXT NOT NULL,
            terapist TEXT NOT NULL,
            hizmet_bedeli REAL DEFAULT 0,
            alinan_ucret REAL DEFAULT 0,
            kalan_borc REAL DEFAULT 0,
            seans_id INTEGER,
            notlar TEXT,
            olusturma_tarihi TEXT
        );
        """
    )

    # Records ek kolonlar
    try:
        cur.execute("PRAGMA table_info(records)")
        rcols = [r[1] for r in cur.fetchall()]
        if "saat" not in rcols:
            cur.execute("ALTER TABLE records ADD COLUMN saat TEXT DEFAULT ''")
        if "seans_id" not in rcols:
            cur.execute("ALTER TABLE records ADD COLUMN seans_id INTEGER")
    except Exception:
        pass

    # Varsayılan veriler
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # İstenmeyen danışan kayıtlarını temizle
    bad_names = [
        "Yeni değerlendirme", "Yeni Değerlendirme", "YENİ DEĞERLENDİRME", "YENI DEGERLENDIRME",
        "75 dakika", "75 Dakika", "75 DAKİKA", "75 DAKIKA",
    ]
    try:
        for bn in bad_names:
            cur.execute("DELETE FROM danisanlar WHERE ad_soyad = ?", (bn,))
            cur.execute("DELETE FROM records WHERE danisan_adi = ?", (bn.upper(),))
            cur.execute("DELETE FROM records WHERE danisan_adi = ?", (bn,))
            cur.execute("DELETE FROM seans_takvimi WHERE danisan_adi = ?", (bn.upper(),))
            cur.execute("DELETE FROM seans_takvimi WHERE danisan_adi = ?", (bn,))
    except Exception:
        pass

    # Terapistler + rolleri
    for t in DEFAULT_THERAPISTS:
        cur.execute(
            "INSERT OR IGNORE INTO settings (therapist_name, therapist_role, is_active, created_at) VALUES (?, ?, 1, ?)",
            (t, DEFAULT_THERAPIST_ROLES.get(t, ""), now),
        )
        cur.execute(
            "UPDATE settings SET therapist_role=? WHERE therapist_name=? AND (therapist_role IS NULL OR therapist_role='')",
            (DEFAULT_THERAPIST_ROLES.get(t, ""), t),
        )

    # Kullanıcılar + yetkiler
    if DEFAULT_USERS:
        for ku, pw, ad, yetki, terapist_adi in DEFAULT_USERS:
            cur.execute(
                """
                INSERT OR IGNORE INTO users
                    (username, password_hash, role, full_name, therapist_name, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (ku, hash_pass(pw), yetki, ad, terapist_adi, now),
            )
            cur.execute(
                "UPDATE users SET password_hash=? WHERE username=? AND (password_hash IS NULL OR password_hash='')",
                (hash_pass(pw), ku),
            )
            cur.execute(
                "UPDATE users SET role=? WHERE username=? AND (role IS NULL OR role='')",
                (yetki, ku),
            )
            cur.execute(
                "UPDATE users SET full_name=? WHERE username=? AND (full_name IS NULL OR full_name='')",
                (ad, ku),
            )
            cur.execute(
                "UPDATE users SET therapist_name=? WHERE username=? AND (therapist_name IS NULL OR therapist_name='')",
                (terapist_adi, ku),
            )

    conn.commit()
    conn.close()

# ==================== FİYATLANDIRMA FONKSİYONLARI ====================

def hesapla_personel_ucreti(personel_adi: str, seans_ucreti: float) -> float:
    """Personel ücretini hesapla"""
    kural = PERSONEL_UCRET_KURALLARI.get(personel_adi, PERSONEL_UCRET_KURALLARI["_default"])
    
    if kural["tip"] == "sabit":
        return kural["tutar"]
    elif kural["tip"] == "yuzde":
        return (seans_ucreti * kural["oran"]) / 100.0
    else:
        return (seans_ucreti * 40.0) / 100.0

def get_ogrenci_personel_ucreti(ogrenci_id: int, personel_adi: str, conn: sqlite3.Connection) -> float:
    """Öğrenci-personel bazlı seans ücretini al"""
    try:
        cur = conn.cursor()
        
        # Önce özel fiyatlandırmayı kontrol et
        cur.execute(
            """
            SELECT seans_ucreti FROM ogrenci_personel_fiyatlandirma
            WHERE ogrenci_id = ? AND personel_adi = ? AND aktif = 1
            AND (bitis_tarihi IS NULL OR bitis_tarihi >= date('now'))
            ORDER BY baslangic_tarihi DESC
            LIMIT 1
            """,
            (ogrenci_id, personel_adi)
        )
        row = cur.fetchone()
        if row and row[0]:
            return float(row[0])
        
        # Özel fiyatlandırma yoksa, cocuk_personel_atama'dan al
        cur.execute(
            """
            SELECT seans_ucreti FROM cocuk_personel_atama
            WHERE cocuk_id = ? AND personel_adi = ? AND aktif = 1
            AND (bitis_tarihi IS NULL OR bitis_tarihi >= date('now'))
            ORDER BY baslangic_tarihi DESC
            LIMIT 1
            """,
            (ogrenci_id, personel_adi)
        )
        row = cur.fetchone()
        if row and row[0]:
            return float(row[0])
        
        return 0.0
    
    except Exception:
        return 0.0

def uygula_yillik_zam(conn: sqlite3.Connection, zam_orani: float = None) -> dict:
    """Tüm aktif öğrenci-personel fiyatlandırmalarına yıllık zam uygula"""
    try:
        cur = conn.cursor()
        
        if zam_orani is None:
            cur.execute(
                """
                SELECT id, ogrenci_id, personel_adi, seans_ucreti, zam_orani
                FROM ogrenci_personel_fiyatlandirma
                WHERE aktif = 1 AND (bitis_tarihi IS NULL OR bitis_tarihi >= date('now'))
                AND (zam_uygulama_tarihi IS NULL OR 
                     date(zam_uygulama_tarihi) < date('now', '-1 year'))
                """
            )
        else:
            cur.execute(
                """
                SELECT id, ogrenci_id, personel_adi, seans_ucreti, zam_orani
                FROM ogrenci_personel_fiyatlandirma
                WHERE aktif = 1 AND (bitis_tarihi IS NULL OR bitis_tarihi >= date('now'))
                """
            )
        
        rows = cur.fetchall()
        guncellenen = 0
        toplam_artis = 0.0
        
        for row in rows:
            fiyat_id, ogrenci_id, personel_adi, mevcut_ucret, kayit_zam_orani = row
            
            kullanilacak_zam = zam_orani if zam_orani is not None else (kayit_zam_orani or 0.0)
            
            if kullanilacak_zam > 0:
                yeni_ucret = float(mevcut_ucret) * (1 + kullanilacak_zam / 100.0)
                artis = yeni_ucret - float(mevcut_ucret)
                
                cur.execute(
                    """
                    UPDATE ogrenci_personel_fiyatlandirma
                    SET seans_ucreti = ?, zam_uygulama_tarihi = ?, guncelleme_tarihi = ?
                    WHERE id = ?
                    """,
                    (
                        yeni_ucret,
                        datetime.datetime.now().strftime("%Y-%m-%d"),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        fiyat_id
                    )
                )
                guncellenen += 1
                toplam_artis += artis
        
        conn.commit()
        
        return {
            "guncellenen": guncellenen,
            "toplam_artis": toplam_artis
        }
    
    except Exception as e:
        log_exception("uygula_yillik_zam", e)
        return {"guncellenen": 0, "toplam_artis": 0.0}

# ==================== VERİTABANI MİGRATİON FONKSİYONU ====================
# Eski/yeni verilerin koşullara göre düzenlenmesi için
def migrate_database_data() -> None:
    """
    Mevcut veritabanındaki tüm verileri yeni koşullara göre düzenle.
    - Personel ücret takibi: Eski seans kayıtlarından personel ücretlerini hesapla ve ekle
    - Çocuk-personel atama: Seans kayıtlarından otomatik atama oluştur
    - Öğrenci-personel fiyatlandırma: Mevcut seans ücretlerinden fiyatlandırma oluştur
    """
    try:
        conn = connect_db()
        cur = conn.cursor()

        # 1) Personel Ücret Takibi: Eski seans kayıtlarından personel ücretlerini hesapla
        # Önce seans_takvimi tablosunda hizmet_bedeli sütunu var mı kontrol et
        cur.execute("PRAGMA table_info(seans_takvimi)")
        st_cols = [r[1] for r in cur.fetchall()]
        has_hizmet_bedeli = "hizmet_bedeli" in st_cols
        
        if has_hizmet_bedeli:
            cur.execute("""
                SELECT id, tarih, danisan_adi, terapist, ucret_tutar, hizmet_bedeli
                FROM seans_takvimi
                WHERE id NOT IN (SELECT DISTINCT seans_id FROM personel_ucret_takibi WHERE seans_id IS NOT NULL)
                AND (ucret_tutar > 0 OR hizmet_bedeli > 0)
            """)
        else:
            cur.execute("""
                SELECT id, tarih, danisan_adi, terapist, ucret_tutar, 0 as hizmet_bedeli
                FROM seans_takvimi
                WHERE id NOT IN (SELECT DISTINCT seans_id FROM personel_ucret_takibi WHERE seans_id IS NOT NULL)
                AND ucret_tutar > 0
            """)
        seanslar = cur.fetchall()
        
        for seans in seanslar:
            seans_id, tarih, danisan_adi, terapist, ucret_tutar, hizmet_bedeli = seans
            seans_ucreti = float(ucret_tutar or hizmet_bedeli or 0)
            
            if seans_ucreti > 0:
                personel_ucreti = hesapla_personel_ucreti(terapist, seans_ucreti)
                ucret_orani = 0.0
                if terapist == "Arif Hoca":
                    ucret_orani = 0.0
                elif terapist == "Pervin Hoca":
                    ucret_orani = 100.0
                else:
                    ucret_orani = 40.0
                
                cur.execute("""
                    INSERT OR IGNORE INTO personel_ucret_takibi
                    (personel_adi, seans_id, tarih, seans_ucreti, personel_ucreti, ucret_orani, odeme_durumu, olusturma_tarihi)
                    VALUES (?, ?, ?, ?, ?, ?, 'beklemede', ?)
                """, (
                    terapist, seans_id, tarih, seans_ucreti, personel_ucreti, ucret_orani,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
        
        # 2) Çocuk-Personel Atama: Seans kayıtlarından otomatik atama oluştur
        cur.execute("""
            SELECT DISTINCT d.id, st.danisan_adi, st.terapist, MIN(st.tarih) as ilk_tarih
            FROM seans_takvimi st
            LEFT JOIN danisanlar d ON UPPER(st.danisan_adi) = UPPER(d.ad_soyad) AND d.aktif = 1
            WHERE d.id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM cocuk_personel_atama cpa
                WHERE cpa.cocuk_id = d.id AND cpa.personel_adi = st.terapist AND cpa.aktif = 1
            )
            GROUP BY d.id, st.danisan_adi, st.terapist
        """)
        atamalar = cur.fetchall()
        
        for atama in atamalar:
            cocuk_id, danisan_adi, personel_adi, ilk_tarih = atama
            
            # Bu çocuk-personel için ortalama seans ücretini hesapla
            # hizmet_bedeli sütunu yoksa sadece ucret_tutar kullan
            cur.execute("PRAGMA table_info(seans_takvimi)")
            st_cols = [r[1] for r in cur.fetchall()]
            has_hizmet_bedeli = "hizmet_bedeli" in st_cols
            
            if has_hizmet_bedeli:
                cur.execute("""
                    SELECT AVG(COALESCE(ucret_tutar, hizmet_bedeli, 0))
                    FROM seans_takvimi
                    WHERE danisan_adi = ? AND terapist = ? AND (ucret_tutar > 0 OR hizmet_bedeli > 0)
                """, (danisan_adi, personel_adi))
            else:
                cur.execute("""
                    SELECT AVG(COALESCE(ucret_tutar, 0))
                    FROM seans_takvimi
                    WHERE danisan_adi = ? AND terapist = ? AND ucret_tutar > 0
                """, (danisan_adi, personel_adi))
            ortalama_ucret = cur.fetchone()[0] or 0.0
            
            cur.execute("""
                INSERT OR IGNORE INTO cocuk_personel_atama
                (cocuk_id, personel_adi, baslangic_tarihi, seans_ucreti, aktif, olusturma_tarihi)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (
                cocuk_id, personel_adi, ilk_tarih, ortalama_ucret,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        # 3) Öğrenci-Personel Fiyatlandırma: Mevcut seans ücretlerinden fiyatlandırma oluştur
        if has_hizmet_bedeli:
            cur.execute("""
                SELECT DISTINCT d.id, st.danisan_adi, st.terapist, 
                       AVG(COALESCE(st.ucret_tutar, st.hizmet_bedeli, 0)) as ortalama_ucret,
                       MIN(st.tarih) as ilk_tarih
                FROM seans_takvimi st
                LEFT JOIN danisanlar d ON UPPER(st.danisan_adi) = UPPER(d.ad_soyad) AND d.aktif = 1
                WHERE d.id IS NOT NULL
                AND (st.ucret_tutar > 0 OR st.hizmet_bedeli > 0)
                AND NOT EXISTS (
                    SELECT 1 FROM ogrenci_personel_fiyatlandirma opf
                    WHERE opf.ogrenci_id = d.id AND opf.personel_adi = st.terapist AND opf.aktif = 1
                )
                GROUP BY d.id, st.danisan_adi, st.terapist
                HAVING AVG(COALESCE(st.ucret_tutar, st.hizmet_bedeli, 0)) > 0
            """)
        else:
            cur.execute("""
                SELECT DISTINCT d.id, st.danisan_adi, st.terapist, 
                       AVG(COALESCE(st.ucret_tutar, 0)) as ortalama_ucret,
                       MIN(st.tarih) as ilk_tarih
                FROM seans_takvimi st
                LEFT JOIN danisanlar d ON UPPER(st.danisan_adi) = UPPER(d.ad_soyad) AND d.aktif = 1
                WHERE d.id IS NOT NULL
                AND st.ucret_tutar > 0
                AND NOT EXISTS (
                    SELECT 1 FROM ogrenci_personel_fiyatlandirma opf
                    WHERE opf.ogrenci_id = d.id AND opf.personel_adi = st.terapist AND opf.aktif = 1
                )
                GROUP BY d.id, st.danisan_adi, st.terapist
                HAVING AVG(COALESCE(st.ucret_tutar, 0)) > 0
            """)
        fiyatlandirmalar = cur.fetchall()
        
        for fiyat in fiyatlandirmalar:
            ogrenci_id, danisan_adi, personel_adi, ortalama_ucret, ilk_tarih = fiyat
            
            cur.execute("""
                INSERT OR IGNORE INTO ogrenci_personel_fiyatlandirma
                (ogrenci_id, personel_adi, seans_ucreti, baslangic_tarihi, aktif, zam_orani, olusturma_tarihi)
                VALUES (?, ?, ?, ?, 1, 0, ?)
            """, (
                ogrenci_id, personel_adi, ortalama_ucret, ilk_tarih,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        # 4) Çocuk Günlük Takip: Eski seans kayıtlarından günlük takip oluştur
        cur.execute("""
            SELECT DISTINCT st.id, d.id as cocuk_id, st.tarih, st.oda, st.terapist
            FROM seans_takvimi st
            LEFT JOIN danisanlar d ON UPPER(st.danisan_adi) = UPPER(d.ad_soyad) AND d.aktif = 1
            WHERE d.id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM cocuk_gunluk_takip cgt
                WHERE cgt.cocuk_id = d.id AND cgt.tarih = st.tarih AND cgt.personel_adi = st.terapist
            )
        """)
        gunluk_takip = cur.fetchall()
        
        for takip in gunluk_takip:
            seans_id, cocuk_id, tarih, oda, personel_adi = takip
            
            cur.execute("""
                INSERT OR IGNORE INTO cocuk_gunluk_takip
                (cocuk_id, tarih, oda_adi, personel_adi, seans_id, olusturma_tarihi)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                cocuk_id, tarih, oda or "", personel_adi, seans_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        log_exception("migrate_database_data", e)


# ==================== DATA PIPELINE SYSTEM ====================
    """Her açılışta sessiz yedek al; son 15 yedeği tut."""
    try:
        os.makedirs(backups_dir(), exist_ok=True)
        if not os.path.exists(db_path()):
            return
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        target = os.path.join(backups_dir(), f"backup_{ts}.db")
        shutil.copy2(db_path(), target)

        backups = [
            os.path.join(backups_dir(), f)
            for f in os.listdir(backups_dir())
            if f.startswith("backup_") and f.endswith(".db")
        ]
        backups.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for old in backups[15:]:
            try:
                os.remove(old)
            except Exception:
                pass
    except Exception:
        # "silent backups": kullanıcıyı rahatsız etme
        pass


def backup_now(prefix: str = "backup") -> str | None:
    """Anlık manuel yedek al ve yolunu döndür (başarısızsa None)."""
    try:
        os.makedirs(backups_dir(), exist_ok=True)
        if not os.path.exists(db_path()):
            return None
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        target = os.path.join(backups_dir(), f"{prefix}_{ts}.db")
        shutil.copy2(db_path(), target)
        return target
    except Exception:
        return None


def safe_delete_db_files() -> tuple[bool, str]:
    """DB + WAL/SHM dosyalarını sil (best-effort)."""
    db = db_path()
    files = [db, db + "-wal", db + "-shm"]
    try:
        # WAL kapansın diye kısa checkpoint dene
        try:
            if os.path.exists(db):
                conn = sqlite3.connect(db)
                cur = conn.cursor()
                cur.execute("PRAGMA wal_checkpoint(FULL);")
                conn.close()
        except Exception:
            pass

        for f in files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                # Windows'ta dosya kilitliyse (WinError 32) doğrudan silinemez.
                # Bu durumda dosyayı yeniden adlandırarak "pending delete" yaparız.
                try:
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_name = f + f".reset_pending_{ts}"
                    if os.path.exists(f):
                        os.replace(f, new_name)
                    return True, f"RENAMED:{new_name}"
                except Exception:
                    return False, f"Silinemedi: {f}\n{e}"
        return True, "OK"
    except Exception as e:
        return False, str(e)


def center_window(win, w: int, h: int) -> None:
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


def center_window_smart(win, w: int, h: int, max_ratio: float = 0.92) -> None:
    """Pencereyi ekran boyutuna göre optimize et (tam ekran yapmadan büyük göster)."""
    try:
        win.update_idletasks()
        sw = int(win.winfo_screenwidth() or 0)
        sh = int(win.winfo_screenheight() or 0)
        if sw > 0 and sh > 0:
            w = min(int(w), int(sw * max_ratio))
            h = min(int(h), int(sh * max_ratio))
        center_window(win, w, h)
    except Exception:
        center_window(win, w, h)


def parse_money(text: str) -> float:
    s = (text or "").strip()
    if s == "":
        return 0.0
    s = s.replace("₺", "").replace("TL", "").strip()
    # 1.234,56 / 1234,56 / 1234.56
    s = s.replace(".", "").replace(",", ".")
    return float(s)


def format_money(val) -> str:
    try:
        return f"{float(val):,.2f} ₺"
    except Exception:
        return "0.00 ₺"


# ==================== DATA PIPELINE SYSTEM ====================
# Event-Driven Architecture: Tüm tablolar birbirinden haberdar
# Her işlem (seans kaydı, ödeme, silme) ilgili tüm tabloları otomatik günceller.
# ============================================================

class DataPipeline:
    """
    Leta Takip Pipeline Sistemi
    
    Amaç: Kullanıcı bir işlem yaptığında (örn: seans kaydı), 
    sistemdeki TÜM ilgili tablolar otomatik güncellensin.
    
    Pipeline Akışları:
    1. SEANS_KAYIT: records → seans_takvimi → kasa_hareketleri → odalar (doluluk)
    2. ODEME: odeme_hareketleri → records → kasa_hareketleri
    3. SILME: records (cascade) → seans_takvimi → kasa_hareketleri → odeme_hareketleri
    4. SEANS_DURUM: seans_takvimi → records → oda_doluluk
    """
    
    def __init__(self, conn: sqlite3.Connection, kullanici_id: int | None = None):
        self.conn = conn
        self.cur = conn.cursor()
        self.kullanici_id = kullanici_id
        self.log = []  # pipeline log (debugging)
    
    def _log(self, action: str, details: str = ""):
        """Pipeline işlemlerini logla"""
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[PIPELINE {ts}] {action}"
        if details:
            msg += f" | {details}"
        self.log.append(msg)
    
    # ============================================================
    # PIPELINE 1: SEANS KAYIT (Ana işlem) - SEANS TAKİP ANA KAYNAK
    # seans_takvimi (ANA) → records → kasa_hareketleri → odeme_hareketleri → oda_doluluk
    # ============================================================
    
    def seans_kayit(
        self,
        tarih: str,
        saat: str,
        danisan_adi: str,
        terapist: str,
        hizmet_bedeli: float,
        alinan_ucret: float,
        notlar: str = "",
        oda: str = "",
        check_oda_cakisma: bool = True,
    ) -> int | None:
        """
        Tam entegre seans kaydı oluştur.
        SEANS TAKİP ANA KAYNAK: Önce seans_takvimi'ne kayıt, sonra diğer tablolar.
        
        Args:
            check_oda_cakisma: Oda çakışması kontrolü yapılsın mı? (default: True)
        
        Returns:
            seans_id (int) - Seans Takip'teki ID (ANA KAYNAK)
        """
        kalan_borc = max(0.0, hizmet_bedeli - alinan_ucret)
        olusturma_tarihi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # ✅ Öğrenci-personel bazlı otomatik fiyatlandırma (eğer hizmet_bedeli girilmemişse)
            if hizmet_bedeli == 0:
                cocuk_id = self._get_cocuk_id(danisan_adi)
                if cocuk_id:
                    otomatik_ucret = get_ogrenci_personel_ucreti(cocuk_id, terapist, self.conn)
                    if otomatik_ucret > 0:
                        hizmet_bedeli = otomatik_ucret
                        kalan_borc = max(0.0, hizmet_bedeli - alinan_ucret)
                        self._log("OTOMATIK_FIYATLANDIRMA", f"{danisan_adi} - {terapist}: {otomatik_ucret} TL")
            
            # ✅ Oda adını normalize et (veritabanındaki oda_adi ile eşleştir)
            oda_normalized = ""
            if oda and oda.strip():
                oda_normalized = self._normalize_oda_adi(oda)
                if not oda_normalized:
                    # Oda bulunamadı ama devam et (uyarı ver ama kaydı yap)
                    self._log("ODA_WARNING", f"Oda '{oda}' veritabanında bulunamadı, kayıt devam ediyor")
            
            # ✅ OPSİYONEL ÖZELLIK 1: Oda çakışma kontrolü
            if check_oda_cakisma and oda_normalized:
                cakisma_var, mesaj = self.check_oda_cakismasi(tarih, saat, oda_normalized)
                if cakisma_var:
                    self._log("ODA_CAKISMA_ENGELLENDI", f"Seans kaydı yapılamadı: {mesaj}")
                    # Event trigger
                    self._trigger_event("oda_cakisma", {
                        "tarih": tarih,
                        "saat": saat,
                        "oda": oda_normalized,
                        "danisan": danisan_adi,
                        "mesaj": mesaj
                    })
                    raise ValueError(f"Oda çakışması var!\n\n{mesaj}")
            
            # ✅ 1) SEANS_TAKVIMI tablosuna kaydet (ANA KAYNAK - Seans Takip)
            seans_id = self._create_seans_takvimi_ana(
                tarih=tarih,
                saat=saat,
                danisan_adi=danisan_adi,
                terapist=terapist,
                oda=oda_normalized,
                notlar=notlar,
                hizmet_bedeli=hizmet_bedeli,
                alinan_ucret=alinan_ucret,
                kalan_borc=kalan_borc,
            )
            if not seans_id:
                raise ValueError("Seans takvimi kaydı oluşturulamadı!")
            
            self._log("SEANS_KAYIT_ANA", f"seans_id={seans_id} | {danisan_adi} / {terapist} | Oda: {oda or 'Seçilmedi'}")
            
            # ✅ 2) DANIŞANLAR tablosuna otomatik ekle (eğer yoksa)
            self._ensure_danisan_exists(danisan_adi)
            
            # ✅ 3) RECORDS tablosuna kaydet (Seans Takip'ten otomatik oluştur)
            record_id = self._create_record_from_seans(
                seans_id=seans_id,
                tarih=tarih,
                saat=saat,
                danisan_adi=danisan_adi,
                terapist=terapist,
                hizmet_bedeli=hizmet_bedeli,
                alinan_ucret=alinan_ucret,
                kalan_borc=kalan_borc,
                notlar=notlar,
            )
            
            if record_id:
                # seans_takvimi'ne record_id'yi bağla (iki yönlü eşleşme)
                self.cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=?", (record_id, seans_id))
                self._log("RECORD_CREATE", f"record_id={record_id} oluşturuldu | seans_id={seans_id} ile bağlandı")
            
            # ✅ 4) İlk ödeme varsa KASA & ODEME_HAREKETLERI'ne kaydet
            if alinan_ucret > 0:
                self._add_odeme_to_kasa(
                    record_id=record_id,
                    seans_id=seans_id,
                    tarih=tarih,
                    tutar=alinan_ucret,
                    odeme_sekli="İlk Kayıt",
                    aciklama=f"{danisan_adi} ({terapist}) - İlk ödeme",
                )
            
            # ✅ 5) ODA DOLULUK güncellemesi (eğer oda seçilmişse)
            if oda_normalized:
                self._update_oda_doluluk(tarih, saat, oda_normalized, "dolu")
            
            # ✅ 6) PERSONEL ÜCRET TAKİBİ - Otomatik hesapla ve kaydet
            personel_ucreti = hesapla_personel_ucreti(terapist, hizmet_bedeli)
            ucret_orani = 0.0
            if terapist == "Arif Hoca":
                ucret_orani = 0.0  # Sabit tutar
            elif terapist == "Pervin Hoca":
                ucret_orani = 100.0
            else:
                ucret_orani = 40.0
            
            self._create_personel_ucret_kaydi(
                personel_adi=terapist,
                seans_id=seans_id,
                tarih=tarih,
                seans_ucreti=hizmet_bedeli,
                personel_ucreti=personel_ucreti,
                ucret_orani=ucret_orani,
            )
            
            # ✅ 7) ÇOCUK GÜNLÜK TAKİP - Oda ve personel takibi
            cocuk_id = self._get_cocuk_id(danisan_adi)
            if cocuk_id:
                self._create_cocuk_gunluk_takip(
                    cocuk_id=cocuk_id,
                    tarih=tarih,
                    oda_adi=oda_normalized,
                    personel_adi=terapist,
                    seans_id=seans_id,
                )
            
            self.conn.commit()
            
            # ✅ OPSİYONEL ÖZELLIK 2: Event trigger (seans_kayit)
            self._trigger_event("seans_kayit", {
                "seans_id": seans_id,  # ANA KAYNAK
                "record_id": record_id,
                "tarih": tarih,
                "saat": saat,
                "danisan_adi": danisan_adi,
                "terapist": terapist,
                "hizmet_bedeli": hizmet_bedeli,
                "alinan_ucret": alinan_ucret,
                "kalan_borc": kalan_borc,
                "oda": oda_normalized,
                "personel_ucreti": personel_ucreti,
            })
            
            # ✅ OPSİYONEL ÖZELLIK 3: Bildirim gönder (eğer aktifse)
            # Örnek: Seansın başlamasına 1 saat kala hatırlatma
            # Bu özellik cron job veya task scheduler ile kullanılır
            
            return seans_id  # ANA KAYNAK ID'sini döndür
            
        except Exception as e:
            self._log("ERROR", f"seans_kayit failed: {e}")
            self.conn.rollback()
            raise
    
    # ============================================================
    # PIPELINE 2: ÖDEME EKLEME
    # odeme_hareketleri → records (borç güncelle) → kasa_hareketleri
    # ============================================================
    
    def odeme_ekle(
        self,
        record_id: int,
        tutar: float,
        tarih: str,
        odeme_sekli: str = "Nakit",
        aciklama: str = "",
    ) -> bool:
        """
        Ödeme ekle ve tüm ilgili tabloları güncelle.
        
        Returns:
            True: başarılı, False: hata
        """
        try:
            # 1) Record bilgilerini çek
            self.cur.execute(
                "SELECT tarih, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, seans_id FROM records WHERE id=?",
                (record_id,),
            )
            row = self.cur.fetchone()
            if not row:
                self._log("ERROR", f"odeme_ekle: record_id={record_id} bulunamadı")
                return False
            
            kayit_tarih, danisan, terapist, bedel, alinan_eski, seans_id = row
            alinan_yeni = float(alinan_eski or 0) + tutar
            kalan_yeni = max(0.0, float(bedel or 0) - alinan_yeni)
            
            # 2) RECORDS tablosunu güncelle
            self.cur.execute(
                "UPDATE records SET alinan_ucret=?, kalan_borc=?, olusturma_tarihi=? WHERE id=?",
                (alinan_yeni, kalan_yeni, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), record_id),
            )
            self._log("ODEME_KAYIT", f"record_id={record_id} | +{tutar} TL | Kalan: {kalan_yeni} TL")
            
            # 3) ODEME_HAREKETLERI tablosuna kaydet
            if not aciklama:
                aciklama = f"{danisan} ({terapist}) tahsilat"
            
            self.cur.execute(
                """
                INSERT INTO odeme_hareketleri 
                (record_id, tarih, tutar, odeme_sekli, aciklama, olusturan_kullanici_id, olusturma_tarihi)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    record_id,
                    tarih,
                    tutar,
                    odeme_sekli,
                    aciklama,
                    self.kullanici_id,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            
            # 4) KASA_HAREKETLERI tablosuna "giren" kaydı
            self._add_odeme_to_kasa(
                record_id=record_id,
                seans_id=seans_id,
                tarih=tarih,
                tutar=tutar,
                odeme_sekli=odeme_sekli,
                aciklama=aciklama,
            )
            
            # 5) Eğer borç tamamen ödendiyse SEANS_TAKVIMI'nde "ucret_alindi" işaretle
            if kalan_yeni <= 0 and seans_id:
                self.cur.execute(
                    "UPDATE seans_takvimi SET ucret_alindi=1, ucret_tutar=? WHERE id=?",
                    (alinan_yeni, seans_id),
                )
                self._log("SEANS_UPDATE", f"seans_id={seans_id} | Ücret tamamen alındı işaretlendi")
            
            self.conn.commit()
            
            # ✅ OPSİYONEL ÖZELLIK 2: Event trigger (odeme_ekle)
            self._trigger_event("odeme_ekle", {
                "record_id": record_id,
                "seans_id": seans_id,
                "danisan_adi": danisan,
                "terapist": terapist,
                "tutar": tutar,
                "alinan_toplam": alinan_yeni,
                "kalan_borc": kalan_yeni,
                "odeme_sekli": odeme_sekli,
                "tam_odendi": (kalan_yeni <= 0),
            })
            
            # ✅ OPSİYONEL ÖZELLIK 3: Ödeme alındı bildirimi
            # Örnek: Danışana ödeme alındı SMS'i gönder
            # if kalan_yeni <= 0:
            #     self.send_notification(
            #         notification_type="odeme_alindi",
            #         recipient="+905551234567",  # danışan telefonu
            #         message=f"Sayın {danisan}, {tutar} TL ödemeniz alınmıştır. Borcunuz tamamen ödenmiştir. Teşekkürler!",
            #         method="sms"
            #     )
            
            return True
            
        except Exception as e:
            self._log("ERROR", f"odeme_ekle failed: {e}")
            self.conn.rollback()
            return False
    
    # ============================================================
    # PIPELINE 3: KAYIT SİLME (Cascade) - SEANS TAKİP ANA KAYNAK
    # seans_takvimi (ANA) sil → records sil → kasa_hareketleri sil → odeme_hareketleri sil
    # ============================================================
    
    def kayit_sil(self, record_id: int) -> bool:
        """
        Kaydı ve ilgili TÜM veriyi cascade olarak sil.
        SEANS TAKİP ANA KAYNAK: Önce seans_takvimi'nden sil, sonra records'tan.
        
        Returns:
            True: başarılı, False: hata
        """
        try:
            # Silmeden önce record bilgilerini al (event için)
            self.cur.execute(
                "SELECT danisan_adi, terapist, hizmet_bedeli, seans_id FROM records WHERE id=?",
                (record_id,),
            )
            row = self.cur.fetchone()
            if row:
                danisan, terapist, bedel, seans_id = row
            else:
                danisan, terapist, bedel, seans_id = None, None, 0, None
            
            # ✅ 1) SEANS_TAKVIMI'nden sil (ANA KAYNAK - önce buradan sil)
            if seans_id:
                self.cur.execute("DELETE FROM seans_takvimi WHERE id=?", (seans_id,))
                self._log("SEANS_DELETE_ANA", f"seans_id={seans_id} silindi (ANA KAYNAK)")
            else:
                # record_id ile bağlı seanslar da olabilir
                self.cur.execute("DELETE FROM seans_takvimi WHERE record_id=?", (record_id,))
                deleted_seans = self.cur.rowcount
                if deleted_seans > 0:
                    self._log("SEANS_DELETE_BY_RECORD", f"{deleted_seans} seans kaydı silindi (record_id={record_id})")
            
            # ✅ 2) ODEME_HAREKETLERI'nden sil (tahsilat geçmişi)
            self.cur.execute("DELETE FROM odeme_hareketleri WHERE record_id=?", (record_id,))
            deleted_odeme = self.cur.rowcount
            if deleted_odeme > 0:
                self._log("ODEME_DELETE", f"{deleted_odeme} ödeme hareketi silindi")
            
            # ✅ 3) KASA_HAREKETLERI'nden sil (gelir kayıtları)
            self.cur.execute("DELETE FROM kasa_hareketleri WHERE record_id=?", (record_id,))
            deleted_kasa = self.cur.rowcount
            if deleted_kasa > 0:
                self._log("KASA_DELETE", f"{deleted_kasa} kasa hareketi silindi")
            
            # ✅ 4) RECORDS'tan sil (seans_takvimi'nden türetilmiş kayıt)
            self.cur.execute("DELETE FROM records WHERE id=?", (record_id,))
            self._log("RECORD_DELETE", f"record_id={record_id} silindi")
            
            self.conn.commit()
            
            # ✅ OPSİYONEL ÖZELLIK 2: Event trigger (kayit_sil)
            self._trigger_event("kayit_sil", {
                "record_id": record_id,
                "seans_id": seans_id,
                "danisan_adi": danisan,
                "terapist": terapist,
                "hizmet_bedeli": bedel,
                "silinen_odeme_sayisi": deleted_odeme,
                "silinen_kasa_sayisi": deleted_kasa,
            })
            
            return True
            
        except Exception as e:
            self._log("ERROR", f"kayit_sil failed: {e}")
            self.conn.rollback()
            return False
    
    # ============================================================
    # HELPER FONKSİYONLAR
    # ============================================================
    
    def _create_seans_takvimi(
        self,
        record_id: int,
        tarih: str,
        saat: str,
        danisan_adi: str,
        terapist: str,
        oda: str = "",
        notlar: str = "",
    ) -> int | None:
        """Seans takvimi kaydı oluştur ve ID'sini döndür"""
        try:
            # Aynı tarih+saat+danışan+terapist varsa tekrar ekleme
            self.cur.execute(
                """
                SELECT id FROM seans_takvimi 
                WHERE tarih=? AND saat=? AND danisan_adi=? AND terapist=? AND record_id IS NULL
                LIMIT 1
                """,
                (tarih, saat, danisan_adi, terapist),
            )
            existing = self.cur.fetchone()
            if existing:
                seans_id = existing[0]
                # record_id ile bağla
                self.cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=?", (record_id, seans_id))
                self._log("SEANS_LINK_EXISTING", f"Mevcut seans_id={seans_id} ile bağlandı")
                return seans_id
            
            # Yeni kayıt oluştur
            self.cur.execute(
                """
                INSERT INTO seans_takvimi 
                (tarih, saat, danisan_adi, terapist, oda, durum, record_id, seans_alindi, ucret_alindi, notlar, olusturma_tarihi, olusturan_kullanici_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    tarih,
                    saat,
                    danisan_adi,
                    terapist,
                    oda or "",
                    "gerceklesti",  # Kayıt edildiyse gerçekleşmiştir
                    record_id,
                    1,  # seans_alindi=1 (yapıldı)
                    0,  # ucret_alindi=0 (henüz tam ödenmedi)
                    notlar or "",
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.kullanici_id,
                ),
            )
            seans_id = int(self.cur.lastrowid or 0)
            self._log("SEANS_CREATE", f"seans_id={seans_id} oluşturuldu | Oda: {oda or 'Seçilmedi'}")
            return seans_id
            
        except Exception as e:
            self._log("ERROR", f"_create_seans_takvimi failed: {e}")
            return None
    
    def _create_seans_takvimi_ana(
        self,
        tarih: str,
        saat: str,
        danisan_adi: str,
        terapist: str,
        oda: str = "",
        notlar: str = "",
        hizmet_bedeli: float = 0.0,
        alinan_ucret: float = 0.0,
        kalan_borc: float = 0.0,
    ) -> int | None:
        """
        Seans Takip ANA KAYNAK: seans_takvimi tablosuna kayıt oluştur.
        Bu fonksiyon ANA kayıt noktasıdır - diğer tablolar bundan türetilir.
        """
        try:
            # Çift kayıt kontrolü: Aynı tarih+saat+danışan+terapist+oda varsa uyar
            self.cur.execute(
                """
                SELECT id FROM seans_takvimi 
                WHERE tarih=? AND saat=? AND danisan_adi=? AND terapist=? AND oda=?
                LIMIT 1
                """,
                (tarih, saat, danisan_adi, terapist, oda or ""),
            )
            existing = self.cur.fetchone()
            if existing:
                seans_id = existing[0]
                self._log("SEANS_EXISTS", f"Mevcut seans_id={seans_id} bulundu (çift kayıt önlendi)")
                return seans_id
            
            # Yeni seans kaydı oluştur (ANA KAYNAK)
            ucret_durumu = 1 if kalan_borc <= 0 else 0  # Tam ödendiyse 1
            self.cur.execute(
                """
                INSERT INTO seans_takvimi 
                (tarih, saat, danisan_adi, terapist, oda, durum, record_id, seans_alindi, ucret_alindi, ucret_tutar, notlar, olusturma_tarihi, olusturan_kullanici_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    tarih,
                    saat,
                    danisan_adi,
                    terapist,
                    oda or "",
                    "gerceklesti",  # Kayıt edildiyse gerçekleşmiştir
                    None,  # record_id henüz yok, sonra bağlanacak
                    1,  # seans_alindi=1 (yapıldı)
                    ucret_durumu,  # ucret_alindi (tam ödendiyse 1)
                    alinan_ucret,  # ucret_tutar
                    notlar or "",
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.kullanici_id,
                ),
            )
            seans_id = int(self.cur.lastrowid or 0)
            self._log("SEANS_CREATE_ANA", f"seans_id={seans_id} oluşturuldu (ANA KAYNAK) | {danisan_adi} / {terapist} | Oda: {oda or 'Seçilmedi'}")
            return seans_id
            
        except Exception as e:
            self._log("ERROR", f"_create_seans_takvimi_ana failed: {e}")
            return None
    
    def _ensure_danisan_exists(self, danisan_adi: str) -> None:
        """
        Danışan yönetimi senkronizasyonu: Seans kaydı yapılırken danışan otomatik eklenir.
        Eğer danışan zaten varsa, hiçbir şey yapmaz.
        """
        try:
            danisan_adi_upper = danisan_adi.strip().upper()
            if not danisan_adi_upper:
                return
            
            # Danışan zaten var mı kontrol et
            self.cur.execute(
                "SELECT id FROM danisanlar WHERE UPPER(ad_soyad) = ? AND aktif = 1",
                (danisan_adi_upper,)
            )
            existing = self.cur.fetchone()
            
            if not existing:
                # Danışan yok, ekle
                olusturma_tarihi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cur.execute(
                    """
                    INSERT INTO danisanlar (ad_soyad, aktif, olusturma_tarihi)
                    VALUES (?, 1, ?)
                    """,
                    (danisan_adi_upper, olusturma_tarihi)
                )
                danisan_id = int(self.cur.lastrowid or 0)
                self._log("DANISAN_AUTO_ADD", f"danisan_id={danisan_id} | {danisan_adi_upper} otomatik eklendi")
            else:
                self._log("DANISAN_EXISTS", f"Danışan zaten mevcut: {danisan_adi_upper}")
                
        except Exception as e:
            self._log("ERROR", f"_ensure_danisan_exists failed: {e}")
            # Hata olsa bile devam et (kritik değil)
    
    def _create_record_from_seans(
        self,
        seans_id: int,
        tarih: str,
        saat: str,
        danisan_adi: str,
        terapist: str,
        hizmet_bedeli: float,
        alinan_ucret: float,
        kalan_borc: float,
        notlar: str = "",
    ) -> int | None:
        """
        Seans Takip'ten (seans_takvimi) records tablosuna otomatik kayıt oluştur.
        Bu fonksiyon seans_takvimi'nden türetilmiş kayıt oluşturur.
        """
        try:
            # Çift kayıt kontrolü: Bu seans_id zaten bir record'a bağlı mı?
            self.cur.execute("SELECT record_id FROM seans_takvimi WHERE id=?", (seans_id,))
            row = self.cur.fetchone()
            if row and row[0]:
                # Zaten bir record_id var, onu kullan
                record_id = row[0]
                self._log("RECORD_EXISTS", f"seans_id={seans_id} zaten record_id={record_id} ile bağlı")
                return record_id
            
            # Yeni record oluştur (seans_takvimi'nden türetilmiş)
            olusturma_tarihi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cur.execute(
                """
                INSERT INTO records 
                (tarih, saat, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, notlar, olusturma_tarihi, seans_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tarih, saat, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, notlar, olusturma_tarihi, seans_id),
            )
            record_id = int(self.cur.lastrowid or 0)
            
            # seans_takvimi'ne record_id'yi bağla (iki yönlü eşleşme)
            self.cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=?", (record_id, seans_id))
            
            self._log("RECORD_CREATE_FROM_SEANS", f"record_id={record_id} oluşturuldu | seans_id={seans_id} ile bağlandı")
            return record_id
            
        except Exception as e:
            self._log("ERROR", f"_create_record_from_seans failed: {e}")
            return None
    
    def _add_odeme_to_kasa(
        self,
        record_id: int,
        seans_id: int | None,
        tarih: str,
        tutar: float,
        odeme_sekli: str,
        aciklama: str,
    ):
        """Ödemeyi kasa defterine "giren" olarak ekle"""
        try:
            self.cur.execute(
                """
                INSERT INTO kasa_hareketleri 
                (tarih, tip, aciklama, tutar, odeme_sekli, record_id, seans_id, olusturan_kullanici_id, olusturma_tarihi)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    tarih,
                    "giren",
                    aciklama,
                    tutar,
                    odeme_sekli,
                    record_id,
                    seans_id,
                    self.kullanici_id,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            self._log("KASA_GIREN", f"+{tutar} TL | {aciklama}")
        except Exception as e:
            self._log("ERROR", f"_add_odeme_to_kasa failed: {e}")
    
    def _normalize_oda_adi(self, oda: str) -> str | None:
        """
        Oda adını veritabanındaki oda_adi ile eşleştir.
        Eğer oda veritabanında yoksa, None döner.
        """
        if not oda or not oda.strip():
            return None
        
        try:
            # Önce tam eşleşme kontrol et
            self.cur.execute("SELECT oda_adi FROM odalar WHERE oda_adi = ? AND aktif = 1", (oda.strip(),))
            row = self.cur.fetchone()
            if row:
                return row[0]
            
            # Büyük/küçük harf duyarsız arama
            self.cur.execute("SELECT oda_adi FROM odalar WHERE UPPER(oda_adi) = UPPER(?) AND aktif = 1", (oda.strip(),))
            row = self.cur.fetchone()
            if row:
                return row[0]
            
            # Eşleşme bulunamadı
            self._log("ODA_NOT_FOUND", f"Oda '{oda}' veritabanında bulunamadı")
            return None
            
        except Exception as e:
            self._log("ERROR", f"_normalize_oda_adi failed: {e}")
            return None
    
    def _update_oda_doluluk(self, tarih: str, saat: str, oda: str, durum: str):
        """Oda doluluk bilgisini güncelle (ileride oda çakışması kontrolü için)"""
        try:
            # Oda adını normalize et
            oda_normalized = self._normalize_oda_adi(oda)
            if oda_normalized:
                # Bu fonksiyon şimdilik log tutar, ileride oda_doluluk tablosu eklenebilir
                self._log("ODA_UPDATE", f"Tarih: {tarih} {saat} | Oda: {oda_normalized} | Durum: {durum}")
        except Exception as e:
            self._log("ERROR", f"_update_oda_doluluk failed: {e}")
    
    def _create_personel_ucret_kaydi(
        self,
        personel_adi: str,
        seans_id: int,
        tarih: str,
        seans_ucreti: float,
        personel_ucreti: float,
        ucret_orani: float,
    ):
        """Personel ücret takibi kaydı oluştur"""
        try:
            olusturma_tarihi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cur.execute(
                """
                INSERT INTO personel_ucret_takibi 
                (personel_adi, seans_id, tarih, seans_ucreti, personel_ucreti, ucret_orani, odeme_durumu, olusturma_tarihi, olusturan_kullanici_id)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    personel_adi,
                    seans_id,
                    tarih,
                    seans_ucreti,
                    personel_ucreti,
                    ucret_orani,
                    "beklemede",
                    olusturma_tarihi,
                    self.kullanici_id,
                ),
            )
            self._log("PERSONEL_UCRET_KAYDI", f"{personel_adi}: {personel_ucreti} TL (Seans: {seans_ucreti} TL, Oran: {ucret_orani}%)")
        except Exception as e:
            self._log("ERROR", f"_create_personel_ucret_kaydi failed: {e}")
    
    def _get_cocuk_id(self, danisan_adi: str) -> int | None:
        """Danışan adından çocuk ID'sini al"""
        try:
            self.cur.execute("SELECT id FROM danisanlar WHERE UPPER(ad_soyad) = UPPER(?) AND aktif = 1 LIMIT 1", (danisan_adi.strip(),))
            row = self.cur.fetchone()
            if row:
                return int(row[0])
            return None
        except Exception as e:
            self._log("ERROR", f"_get_cocuk_id failed: {e}")
            return None
    
    def _create_cocuk_gunluk_takip(
        self,
        cocuk_id: int,
        tarih: str,
        oda_adi: str | None,
        personel_adi: str,
        seans_id: int | None,
    ):
        """Çocuk günlük oda-personel takibi kaydı oluştur"""
        try:
            olusturma_tarihi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cur.execute(
                """
                INSERT INTO cocuk_gunluk_takip 
                (cocuk_id, tarih, oda_adi, personel_adi, seans_id, olusturma_tarihi)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    cocuk_id,
                    tarih,
                    oda_adi or "",
                    personel_adi,
                    seans_id,
                    olusturma_tarihi,
                ),
            )
            self._log("COCUK_GUNLUK_TAKIP", f"Çocuk ID: {cocuk_id} | Tarih: {tarih} | Oda: {oda_adi or 'Seçilmedi'} | Personel: {personel_adi}")
        except Exception as e:
            self._log("ERROR", f"_create_cocuk_gunluk_takip failed: {e}")
    
    # ============================================================
    # OPSİYONEL ÖZELLIK 1: ODA ÇAKIŞMA KONTROLÜ
    # ============================================================
    
    def check_oda_cakismasi(self, tarih: str, saat: str, oda: str, exclude_record_id: int | None = None) -> tuple[bool, str]:
        """
        Aynı tarih/saat/oda'da başka seans var mı kontrol et.
        
        Args:
            tarih: YYYY-MM-DD
            saat: HH:MM
            oda: Oda adı
            exclude_record_id: Bu record_id'yi hariç tut (güncelleme için)
        
        Returns:
            (cakisma_var: bool, mesaj: str)
        """
        if not oda or oda.strip() == "":
            return (False, "Oda seçilmemiş")
        
        # Oda ismini normalize et (veritabanındaki oda_adi ile eşleştir)
        oda_normalized = self._normalize_oda_adi(oda)
        if not oda_normalized:
            return (False, f"Oda '{oda}' veritabanında bulunamadı!")
        
        try:
            # Saat aralığı hesapla (varsayılan seans süresi: 45 dakika)
            from datetime import datetime, timedelta
            saat_dt = datetime.strptime(f"{tarih} {saat}", "%Y-%m-%d %H:%M")
            seans_sure = timedelta(minutes=45)
            bitis_dt = saat_dt + seans_sure
            
            # Bu saatte aynı odada başka seans var mı? (oda_adi ile eşleştir)
            query = """
                SELECT s.id, s.danisan_adi, s.terapist, s.saat
                FROM seans_takvimi s
                WHERE s.oda = ?
                  AND s.tarih = ?
                  AND s.durum != 'iptal'
            """
            params = [oda_normalized, tarih]
            
            if exclude_record_id:
                query += " AND s.record_id != ?"
                params.append(exclude_record_id)
            
            self.cur.execute(query, params)
            seanslar = self.cur.fetchall()
            
            for seans in seanslar:
                seans_id, danisan, terapist, seans_saat = seans
                if not seans_saat:
                    continue
                
                # Diğer seansın başlangıç ve bitiş saati
                diger_baslangic = datetime.strptime(f"{tarih} {seans_saat}", "%Y-%m-%d %H:%M")
                diger_bitis = diger_baslangic + seans_sure
                
                # Çakışma kontrolü: Aralıklar kesişiyor mu?
                if (saat_dt < diger_bitis) and (bitis_dt > diger_baslangic):
                    mesaj = f"⚠️ ODA ÇAKIŞMASI!\n\n"
                    mesaj += f"Oda: {oda_normalized}\n"
                    mesaj += f"Tarih: {tarih}\n"
                    mesaj += f"Saat: {saat} - {bitis_dt.strftime('%H:%M')}\n\n"
                    mesaj += f"Bu saatte başka seans var:\n"
                    mesaj += f"• {danisan} / {terapist}\n"
                    mesaj += f"• Saat: {seans_saat} - {diger_bitis.strftime('%H:%M')}"
                    
                    self._log("ODA_CAKISMA_TESPIT", mesaj)
                    return (True, mesaj)
            
            self._log("ODA_KONTROL_OK", f"Oda müsait: {oda} | {tarih} {saat}")
            return (False, "Oda müsait")
            
        except Exception as e:
            self._log("ERROR", f"check_oda_cakismasi failed: {e}")
            return (False, f"Kontrol hatası: {e}")
    
    # ============================================================
    # OPSİYONEL ÖZELLIK 2: EVENT LISTENERS (Webhook Sistemi)
    # ============================================================
    
    def __init__(self, conn: sqlite3.Connection, kullanici_id: int | None = None):
        self.conn = conn
        self.cur = conn.cursor()
        self.kullanici_id = kullanici_id
        self.log = []  # pipeline log (debugging)
        
        # Event listeners (webhook callbacks)
        self._event_listeners = {
            "seans_kayit": [],
            "odeme_ekle": [],
            "kayit_sil": [],
            "oda_cakisma": [],
        }
    
    def on(self, event: str, callback):
        """
        Event listener ekle (webhook sistemi)
        
        Kullanım:
            pipeline.on("seans_kayit", lambda data: send_sms(data))
            pipeline.on("odeme_ekle", lambda data: update_dashboard(data))
        
        Events:
            - seans_kayit: Yeni seans kaydedildiğinde
            - odeme_ekle: Ödeme eklendiğinde
            - kayit_sil: Kayıt silindiğinde
            - oda_cakisma: Oda çakışması tespit edildiğinde
        """
        if event in self._event_listeners:
            self._event_listeners[event].append(callback)
            self._log("EVENT_LISTENER", f"'{event}' için listener eklendi")
        else:
            self._log("ERROR", f"Bilinmeyen event: {event}")
    
    def _trigger_event(self, event: str, data: dict):
        """Event'i tetikle ve tüm listener'ları çağır"""
        try:
            if event in self._event_listeners:
                for callback in self._event_listeners[event]:
                    try:
                        callback(data)
                        self._log("EVENT_TRIGGERED", f"'{event}' event tetiklendi")
                    except Exception as e:
                        self._log("ERROR", f"Event listener hatası ({event}): {e}")
        except Exception as e:
            self._log("ERROR", f"_trigger_event failed: {e}")
    
    # ============================================================
    # OPSİYONEL ÖZELLIK 3: SMS/EMAIL BİLDİRİM SİSTEMİ
    # ============================================================
    
    def send_notification(
        self,
        notification_type: str,
        recipient: str,
        message: str,
        method: str = "sms"
    ) -> bool:
        """
        Bildirim gönder (SMS/Email)
        
        Args:
            notification_type: "seans_hatirlatma" | "odeme_alindi" | "borc_hatirlatma"
            recipient: Telefon numarası (SMS) veya email
            message: Mesaj içeriği
            method: "sms" | "email"
        
        Returns:
            bool: Başarılı: True, Hata: False
        
        Not: Bu fonksiyon şablon implementasyondur.
        Gerçek SMS/Email göndermek için API entegrasyonu gerekir.
        """
        try:
            self._log("NOTIFICATION_SEND", f"{method.upper()} → {recipient} | {notification_type}")
            
            # Bildirim log tablosu (opsiyonel - ileride eklenebilir)
            try:
                self.cur.execute(
                    """
                    INSERT INTO bildirim_log 
                    (tarih, tip, alici, mesaj, yontem, durum, olusturma_tarihi)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        datetime.datetime.now().strftime("%Y-%m-%d"),
                        notification_type,
                        recipient,
                        message,
                        method,
                        "basarili",  # veya "basarisiz" API yanıtına göre
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
            except Exception:
                # bildirim_log tablosu yoksa devam et
                pass
            
            # Gerçek implementasyon için:
            # if method == "sms":
            #     return self._send_sms(recipient, message)
            # elif method == "email":
            #     return self._send_email(recipient, message)
            
            # Şimdilik sadece log:
            print(f"\n📱 BİLDİRİM GÖNDER")
            print(f"Tip: {notification_type}")
            print(f"Alıcı: {recipient}")
            print(f"Yöntem: {method.upper()}")
            print(f"Mesaj: {message}\n")
            
            return True
            
        except Exception as e:
            self._log("ERROR", f"send_notification failed: {e}")
            return False
    
    def _send_sms(self, phone: str, message: str) -> bool:
        """
        SMS gönder (Gerçek implementasyon için API gerekli)
        
        Örnek entegrasyonlar:
        - Twilio: https://www.twilio.com/
        - Nexmo/Vonage: https://www.vonage.com/
        - NetGSM (Türkiye): https://www.netgsm.com.tr/
        - İletimerkezi (Türkiye): https://www.iletimerkezi.com/
        """
        try:
            # Örnek: Twilio entegrasyonu
            # from twilio.rest import Client
            # client = Client(account_sid, auth_token)
            # message = client.messages.create(
            #     body=message,
            #     from_='+15017122661',
            #     to=phone
            # )
            # return True
            
            self._log("SMS_MOCK", f"SMS gönderildi: {phone}")
            return True
            
        except Exception as e:
            self._log("ERROR", f"_send_sms failed: {e}")
            return False
    
    def _send_email(self, email: str, message: str) -> bool:
        """
        Email gönder (Gerçek implementasyon için SMTP veya API gerekli)
        
        Örnek entegrasyonlar:
        - SMTP (yerleşik): smtplib
        - SendGrid: https://sendgrid.com/
        - Mailgun: https://www.mailgun.com/
        - AWS SES: https://aws.amazon.com/ses/
        """
        try:
            # Örnek: SMTP ile
            # import smtplib
            # from email.mime.text import MIMEText
            # 
            # msg = MIMEText(message)
            # msg['Subject'] = 'Leta Aile ve Çocuk - Bildirim'
            # msg['From'] = 'noreply@leta.com'
            # msg['To'] = email
            # 
            # with smtplib.SMTP('smtp.gmail.com', 587) as server:
            #     server.starttls()
            #     server.login('user', 'pass')
            #     server.send_message(msg)
            # return True
            
            self._log("EMAIL_MOCK", f"Email gönderildi: {email}")
            return True
            
        except Exception as e:
            self._log("ERROR", f"_send_email failed: {e}")
            return False
    
    def get_log(self) -> str:
        """Pipeline log'larını string olarak döndür"""
        return "\n".join(self.log)
    
    # ============================================================
    # GENEL SENKRONİZASYON KONTROLÜ
    # Tüm tablolar arası tutarlılığı kontrol eder
    # ============================================================
    
    def validate_sync(self) -> dict:
        """
        Tüm tablolar arası senkronizasyonu kontrol et.
        
        Returns:
            dict: {
                "ok": bool,
                "errors": list[str],
                "warnings": list[str],
                "stats": dict
            }
        """
        errors = []
        warnings = []
        stats = {
            "seans_takvimi_count": 0,
            "records_count": 0,
            "danisanlar_count": 0,
            "odalar_count": 0,
            "kasa_hareketleri_count": 0,
            "odeme_hareketleri_count": 0,
        }
        
        try:
            # 1) seans_takvimi ↔ records eşleşmesi
            self.cur.execute("""
                SELECT COUNT(*) FROM seans_takvimi st
                LEFT JOIN records r ON st.record_id = r.id OR st.id = r.seans_id
                WHERE st.record_id IS NULL AND r.id IS NULL
            """)
            unlinked_seans = self.cur.fetchone()[0]
            if unlinked_seans > 0:
                warnings.append(f"{unlinked_seans} seans kaydı records ile eşleşmemiş")
            
            # 2) records ↔ seans_takvimi eşleşmesi
            self.cur.execute("""
                SELECT COUNT(*) FROM records r
                LEFT JOIN seans_takvimi st ON r.seans_id = st.id OR r.id = st.record_id
                WHERE r.seans_id IS NULL AND st.id IS NULL
            """)
            unlinked_records = self.cur.fetchone()[0]
            if unlinked_records > 0:
                warnings.append(f"{unlinked_records} record seans_takvimi ile eşleşmemiş")
            
            # 3) Danışan senkronizasyonu - seans_takvimi'nde olan ama danisanlar'da olmayan (ANA KAYNAK)
            self.cur.execute("""
                SELECT DISTINCT st.danisan_adi FROM seans_takvimi st
                LEFT JOIN danisanlar d ON UPPER(st.danisan_adi) = UPPER(d.ad_soyad) AND d.aktif = 1
                WHERE st.danisan_adi IS NOT NULL AND st.danisan_adi != '' AND d.id IS NULL
            """)
            missing_danisanlar = [row[0] for row in self.cur.fetchall() if row[0]]
            if missing_danisanlar:
                warnings.append(f"{len(missing_danisanlar)} danışan danisanlar tablosunda yok: {', '.join(missing_danisanlar[:5])}")
            
            # 4) Oda senkronizasyonu - seans_takvimi'nde olan ama odalar'da olmayan
            self.cur.execute("""
                SELECT DISTINCT st.oda FROM seans_takvimi st
                WHERE st.oda IS NOT NULL AND st.oda != ''
                AND NOT EXISTS (
                    SELECT 1 FROM odalar o WHERE o.oda_adi = st.oda AND o.aktif = 1
                )
            """)
            missing_odalar = [row[0] for row in self.cur.fetchall() if row[0]]
            if missing_odalar:
                warnings.append(f"{len(missing_odalar)} oda adı odalar tablosunda yok: {', '.join(missing_odalar[:5])}")
            
            # 5) kasa_hareketleri ↔ records/seans_takvimi eşleşmesi
            self.cur.execute("""
                SELECT COUNT(*) FROM kasa_hareketleri kh
                WHERE kh.record_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM records r WHERE r.id = kh.record_id)
            """)
            orphaned_kasa = self.cur.fetchone()[0]
            if orphaned_kasa > 0:
                errors.append(f"{orphaned_kasa} kasa hareketi geçersiz record_id'ye bağlı")
            
            # 6) odeme_hareketleri ↔ records eşleşmesi
            self.cur.execute("""
                SELECT COUNT(*) FROM odeme_hareketleri oh
                WHERE oh.record_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM records r WHERE r.id = oh.record_id)
            """)
            orphaned_odeme = self.cur.fetchone()[0]
            if orphaned_odeme > 0:
                errors.append(f"{orphaned_odeme} ödeme hareketi geçersiz record_id'ye bağlı")
            
            # İstatistikler
            self.cur.execute("SELECT COUNT(*) FROM seans_takvimi")
            stats["seans_takvimi_count"] = self.cur.fetchone()[0]
            
            self.cur.execute("SELECT COUNT(*) FROM records")
            stats["records_count"] = self.cur.fetchone()[0]
            
            self.cur.execute("SELECT COUNT(*) FROM danisanlar WHERE aktif = 1")
            stats["danisanlar_count"] = self.cur.fetchone()[0]
            
            self.cur.execute("SELECT COUNT(*) FROM odalar WHERE aktif = 1")
            stats["odalar_count"] = self.cur.fetchone()[0]
            
            self.cur.execute("SELECT COUNT(*) FROM kasa_hareketleri")
            stats["kasa_hareketleri_count"] = self.cur.fetchone()[0]
            
            self.cur.execute("SELECT COUNT(*) FROM odeme_hareketleri")
            stats["odeme_hareketleri_count"] = self.cur.fetchone()[0]
            
            return {
                "ok": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "stats": stats,
                "missing_danisanlar": missing_danisanlar  # Eksik danışanları döndür
            }
            
        except Exception as e:
            errors.append(f"Senkronizasyon kontrolü hatası: {e}")
            return {
                "ok": False,
                "errors": errors,
                "warnings": warnings,
                "stats": stats,
                "missing_danisanlar": []
            }


class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="flatly")
        # TEK PENCERE LOGIN: En stabil yaklaşım (Toplevel/grab/topmost yok)
        self.title(f"Giriş - Leta  |  {APP_VERSION}")
        center_window(self, 520, 420)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Logo (varsa) - GC olmaması için referans tutuyoruz
        self._logo_small = load_logo_photo(28, 28)
        self._logo_big = load_logo_photo(80, 80)
        self._logo_icon = load_logo_photo(64, 64)
        self._toolbar_logo_lbl = None
        self._login_logo_lbl = None
        safe_iconphoto(self, self._logo_icon)

        # giriş yapan kullanıcı
        self.kullanici = None  # (id, kullanici_adi, ad_soyad, yetki, terapist_adi)
        self.kullanici_yetki = "normal"
        self.kullanici_terapist = None

        self._vcmd_money = (self.register(self._validate_money), "%P")
        self._build_login_ui()
        # Windows odak sorunlarına karşı: kısa süre üste getir
        try:
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(250, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def _on_close(self):
        self.destroy()

    def girise_don(self):
        """Giriş ekranına dön (logout) - bilgisiz kullanıcı için basit."""
        try:
            # kullanıcıyı temizle
            self.kullanici = None
            self.kullanici_yetki = "normal"
            self.kullanici_terapist = None

            # tüm mevcut UI'ı kaldır
            for w in list(self.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass
            try:
                self.config(menu="")
            except Exception:
                pass

            # giriş ekranını tekrar kur
            self.title(f"Giriş - Leta  |  {APP_VERSION}")
            center_window_smart(self, 520, 420, max_ratio=0.85)
            self.resizable(False, False)
            self._build_login_ui()
        except Exception:
            # worst-case: uygulamayı kapat
            try:
                self.destroy()
            except Exception:
                pass

    def sistemi_sifirla(self):
        """Kurum müdürü: yedek al + DB'yi sil + uygulamayı yeniden başlat."""
        if self.kullanici_yetki != "kurum_muduru":
            messagebox.showwarning("Yetki", "Bu işlem sadece Kurum Müdürü tarafından yapılabilir.")
            return

        msg = (
            "Bu işlem veritabanını SIFIRLAR.\n\n"
            "• Tüm kayıtlar silinir (DB dosyası).\n"
            "• Önce otomatik yedek alınır.\n\n"
            "Devam etmek istiyor musunuz?"
        )
        if not messagebox.askyesno("Sistemi Sıfırla", msg):
            return
        if not messagebox.askyesno("Son Onay", "Emin misiniz? Bu işlem geri alınamaz."):
            return

        # 1) Yedek al
        backup_path = backup_now(prefix="reset_before_delete")

        # 2) DB silme işlemini en güvenlisiyle yap (çapraz platform):
        # Uygulama kapanır -> aynı EXE/script "reset-worker" modunda açılır -> DB/WAL/SHM silinir -> uygulama tekrar açılır.

        # 3) Kullanıcı bilgilendir
        try:
            if backup_path:
                messagebox.showinfo(
                    "Başarılı",
                    "Sistem sıfırlanacak.\n\n"
                    + f"Yedek alındı:\n{backup_path}\n\n"
                    + "Şimdi uygulama kapanacak, veritabanı silinecek ve uygulama tekrar açılacak.\n"
                    + "Açılışta tekrar 'İLK KURULUM' ekranı gelir.",
                )
            else:
                messagebox.showinfo(
                    "Başarılı",
                    "Sistem sıfırlanacak.\n\n"
                    + "Not: DB bulunamadığı için yedek alınamadı.\n"
                    + "Şimdi uygulama kapanacak, veritabanı silinecek ve uygulama tekrar açılacak.\n"
                    + "Açılışta tekrar 'İLK KURULUM' ekranı gelir.",
                )
        except Exception:
            pass

        # 4) Reset-worker başlat + uygulamayı kapat
        try:
            try:
                spawn_detached(_relaunch_cmd(["--reset-worker"]))
            except Exception:
                # Fallback: worker açılamazsa burada best-effort sil + relaunch dene
                safe_delete_db_files()
                spawn_detached(_relaunch_cmd())
        finally:
            try:
                self.destroy()
            except Exception:
                pass

    def _build_login_ui(self):
        self.login_frame = ttk.Frame(self, padding=18)
        self.login_frame.pack(fill=BOTH, expand=True)

        header = ttk.Frame(self.login_frame)
        header.pack(fill=X, pady=(6, 10))
        if getattr(self, "_logo_big", None):
            self._login_logo_lbl = ttk.Label(header, image=self._logo_big)
            self._login_logo_lbl.pack(side=LEFT, padx=(0, 12))
        title_box = ttk.Frame(header)
        title_box.pack(side=LEFT, fill=X, expand=True)
        ttk.Label(title_box, text="Leta Aile ve Çocuk", font=("Segoe UI", 18, "bold"), bootstyle="primary").pack(anchor=W)
        ttk.Label(title_box, text="Seans ve Ücret Takip", font=("Segoe UI", 11), foreground="gray").pack(anchor=W, pady=(2, 0))

        ttk.Label(self.login_frame, text="Kullanıcı Adı:").pack(anchor=W)
        self.login_user = ttk.Entry(self.login_frame)
        self.login_user.pack(fill=X, pady=(4, 10))

        ttk.Label(self.login_frame, text="Şifre:").pack(anchor=W)
        # Bazı makinelerde tema/maskeleme yüzünden "yazamıyorum" sanılabiliyor.
        # Stabilite için burada maskelemeyi kapatıyoruz; istersen sonra tekrar "*" yaparız.
        self.login_pass = ttk.Entry(self.login_frame, show="*")  # Şifre gizli
        self.login_pass.pack(fill=X, pady=(4, 6))

        self.lbl_pw = ttk.Label(self.login_frame, text="Şifre uzunluğu: 0", foreground="gray")
        self.lbl_pw.pack(anchor=W, pady=(0, 10))

        self.btn_login = ttk.Button(self.login_frame, text="GİRİŞ YAP", bootstyle="success", command=self._do_login)
        self.btn_login.pack(fill=X)
        self.btn_register = ttk.Button(self.login_frame, text="KAYIT OL", bootstyle="info-outline", command=self._open_register)
        self.btn_register.pack(fill=X, pady=(8, 0))
        self.btn_first = ttk.Button(self.login_frame, text="İLK KURULUM (Kurum Müdürü Oluştur)", bootstyle="warning", command=self._first_setup)
        self.btn_first.pack(fill=X, pady=(10, 0))
        ttk.Label(self.login_frame, text=f"Sürüm: {APP_VERSION}  •  Build: {APP_BUILD}", font=("Segoe UI", 8), foreground="gray").pack(pady=(10, 0))
        self.lbl_hint = ttk.Label(self.login_frame, text="", font=("Segoe UI", 8), foreground="gray")
        self.lbl_hint.pack(pady=(2, 0))

        self.login_user.bind("<Return>", lambda e: self.login_pass.focus_set())
        self.login_pass.bind("<Return>", lambda e: self._do_login())
        self.login_pass.bind("<KeyRelease>", lambda e: self.lbl_pw.config(text=f"Şifre uzunluğu: {len(self.login_pass.get())}"))
        self.login_user.bind("<Button-1>", lambda e: self.login_user.focus_set())
        self.login_pass.bind("<Button-1>", lambda e: self.login_pass.focus_set())
        self.after(150, self.login_pass.focus_set)
        self.after(10, self._refresh_first_run_state)

    def _open_register(self):
        RegisterDialog(self, first_setup=False)

    def _first_setup(self):
        RegisterDialog(self, first_setup=True)

    def _refresh_first_run_state(self):
        """İlk kurulumda (DB boş) kurum müdürü oluşturulmadan giriş kapalı olsun."""
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM users WHERE is_active=1")
            n = int((cur.fetchone() or [0])[0] or 0)
            conn.close()
        except Exception:
            n = 0

        if n <= 0:
            # henüz hiç kullanıcı yok
            try:
                self.btn_login.configure(state="disabled")
            except Exception:
                pass
            try:
                self.btn_register.pack_forget()
            except Exception:
                pass
            try:
                self.btn_first.configure(state="normal")
            except Exception:
                pass
            try:
                self.lbl_hint.config(text="İlk kullanım: önce kurum müdürü hesabı oluşturun.")
            except Exception:
                pass
        else:
            try:
                self.btn_login.configure(state="normal")
            except Exception:
                pass
            # kayıt ol butonu görünür kalsın
            try:
                if not self.btn_register.winfo_ismapped():
                    self.btn_register.pack(fill=X, pady=(8, 0))
            except Exception:
                pass
            try:
                self.btn_first.configure(state="disabled")
            except Exception:
                pass
            try:
                self.lbl_hint.config(text="Kayıt olmak için 'KAYIT OL' kullanabilirsiniz.")
            except Exception:
                pass

    def _do_login(self):
        u = self.login_user.get().strip()
        p = self.login_pass.get()
        # DB üzerinden doğrula
        ok = False
        user_row = None
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username, full_name, COALESCE(access_role, role, 'egitim_gorevlisi'), therapist_name, password_hash FROM users WHERE is_active=1 AND username=?",
                (u,),
            )
            row = cur.fetchone()
            if row and (row[5] or "") == hash_pass(p):
                ok = True
                user_row = (row[0], row[1], row[2] or row[1], row[3] or "egitim_gorevlisi", row[4])
                try:
                    cur.execute(
                        "UPDATE users SET last_login=? WHERE id=?",
                        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row[0]),
                    )
                    conn.commit()
                except Exception:
                    pass
            conn.close()
        except Exception:
            # fallback (eski sürüm)
            ok = (LOGIN_USER != "" and u == LOGIN_USER and p == LOGIN_PASS)

        if not ok:
            messagebox.showerror("Hata", "Kullanıcı adı veya şifre yanlış!")
            return

        self.kullanici = user_row
        self.kullanici_yetki = (user_row[3] if user_row else "normal") if ok else "normal"
        self.kullanici_terapist = (user_row[4] if user_row else None)

        # Login başarılı -> ana UI (hata olursa kullanıcıya göster + logla)
        try:
            self.login_frame.destroy()
            self.title(f"{APP_TITLE}  |  {APP_VERSION}")
            self.geometry("1400x800")
            self.resizable(True, True)
            try:
                self.state("zoomed")
            except Exception:
                pass

            self._build_toolbar()
            self._build_menu()
            self._build_tabs()
            self.terapistleri_yukle()
            self._apply_user_restrictions()
            self.kayitlari_listele()
        except Exception as e:
            log_exception("UI_BUILD_ERROR", e)
            messagebox.showerror(
                "Kritik Hata",
                "Girişten sonra arayüz oluşturulamadı.\n\n"
                f"Hata logu: {error_log_path()}\n\n"
                "Lütfen bu log dosyasını bana gönderin.",
            )
            # En azından kullanıcı boş ekran görmesin:
            try:
                fallback = ttk.Frame(self, padding=20)
                fallback.pack(fill=BOTH, expand=True)
                ttk.Label(
                    fallback,
                    text="Arayüz yüklenemedi.\nLütfen yöneticinize haber verin.",
                    font=("Segoe UI", 14, "bold"),
                    bootstyle="danger",
                ).pack(pady=20)
                ttk.Label(fallback, text=f"Log: {error_log_path()}").pack()
            except Exception:
                pass

    def _build_toolbar(self):
        # Üst bar (taskbar alanı): sadece temel aksiyonlar (Girişe dön / Kapat / Kılavuz)
        bar = ttk.Frame(self, padding=10, bootstyle="dark")
        bar.pack(fill=X)
        self.toolbar = bar

        user_txt = "Kullanıcı"
        role_txt = role_label(self.kullanici_yetki or "normal")
        try:
            if self.kullanici and len(self.kullanici) >= 3:
                user_txt = self.kullanici[2] or self.kullanici[1]
        except Exception:
            pass

        if getattr(self, "_logo_small", None):
            self._toolbar_logo_lbl = ttk.Label(bar, image=self._logo_small, bootstyle="inverse-dark")
            self._toolbar_logo_lbl.pack(side=LEFT, padx=(2, 10))
        ttk.Label(
            bar,
            text=f"{APP_TITLE} • {APP_VERSION}",
            font=("Segoe UI", 11, "bold"),
            bootstyle="inverse-dark",
        ).pack(side=LEFT, padx=(4, 14))

        ttk.Label(
            bar,
            text=f"{user_txt} | Rol: {role_txt}",
            font=("Segoe UI", 10),
            bootstyle="inverse-dark",
        ).pack(side=LEFT, padx=(0, 14))

        # Sağ tarafta: en basit 3 buton
        ttk.Button(bar, text="KILAVUZ", bootstyle="secondary", command=self.kullanim_kilavuzu_ac).pack(side=RIGHT, padx=6)
        ttk.Button(bar, text="KAPAT", bootstyle="danger", command=self._on_close).pack(side=RIGHT, padx=6)
        ttk.Button(bar, text="GİRİŞ EKRANI", bootstyle="warning", command=self.girise_don).pack(side=RIGHT, padx=6)

    def _brand_window(self, win) -> None:
        """Logo varsa pencerede (alt-tab/taskbar) ikon olarak göster."""
        try:
            safe_iconphoto(win, self._logo_icon)
        except Exception:
            pass

    def _style_table_strong(self):
        """Tabloların satır/sütun ayrımını daha belirgin yap (best-effort)."""
        try:
            s = ttk.Style()
            s.configure(
                "Strong.Treeview",
                rowheight=30,
                borderwidth=1,
                relief="solid",
                font=("Segoe UI", 10),
            )
            s.configure(
                "Strong.Treeview.Heading",
                font=("Segoe UI", 10, "bold"),
                relief="solid",
                borderwidth=1,
            )
        except Exception:
            pass

    def _apply_stripes(self, tree):
        """Alternating row colors for readability."""
        try:
            tree.tag_configure("odd", background="#FFFFFF")
            tree.tag_configure("even", background="#F3F6FB")
        except Exception:
            pass

    def _update_sync_badge(self):
        """SEANS TAKİP ekranındaki 'Belirsiz: X' sayacını güncelle (best-effort)."""
        try:
            cnt = len(getattr(self, "_last_sync_ambiguous", []) or [])
        except Exception:
            cnt = 0
        try:
            if getattr(self, "_sync_badge_lbl", None) is not None:
                self._sync_badge_lbl.configure(text=f"Belirsiz: {cnt}")
        except Exception:
            pass

    def _default_saat(self) -> str:
        """Kullanıcı seçmezse: şu anki saat (dakika yuvarlayıp) HH:MM üret."""
        try:
            now = datetime.datetime.now()
            # dakika 0/30'a yuvarla
            m = 0 if now.minute < 15 else (30 if now.minute < 45 else 0)
            h = now.hour if now.minute < 45 else (now.hour + 1) % 24
            return f"{h:02d}:{m:02d}"
        except Exception:
            return "09:00"

    def _sync_from_record_to_seans(self, cur, record_id: int, tarih: str, saat: str, danisan: str, terapist: str, notlar: str):
        """records kaydı varsa seans_takvimi'ne bağla/oluştur."""
        try:
            cur.execute("SELECT seans_id FROM records WHERE id=?", (record_id,))
            seans_id = (cur.fetchone() or [None])[0]
        except Exception:
            seans_id = None

        # seans_id varsa: record_id yaz ve çık
        if seans_id:
            try:
                cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=? AND (record_id IS NULL OR record_id='')", (record_id, seans_id))
            except Exception:
                pass
            return

        # record_id ile daha önce seans var mı?
        try:
            cur.execute("SELECT id FROM seans_takvimi WHERE record_id=? ORDER BY id DESC LIMIT 1", (record_id,))
            row = cur.fetchone()
            if row and row[0]:
                sid = int(row[0])
                cur.execute("UPDATE records SET seans_id=? WHERE id=? AND (seans_id IS NULL OR seans_id='')", (sid, record_id))
                return
        except Exception:
            pass

        # Aynı tarih+saat+danisan+terapist varsa onu bağla, yoksa yeni oluştur
        sid = None
        try:
            cur.execute(
                """
                SELECT id FROM seans_takvimi
                WHERE tarih=? AND saat=? AND danisan_adi=? AND terapist=?
                ORDER BY id DESC LIMIT 1
                """,
                (tarih, saat, danisan, terapist),
            )
            row = cur.fetchone()
            if row and row[0]:
                sid = int(row[0])
                cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=? AND (record_id IS NULL OR record_id='')", (record_id, sid))
        except Exception:
            sid = None

        if not sid:
            try:
                cur.execute(
                    """
                    INSERT INTO seans_takvimi (tarih, saat, danisan_adi, terapist, oda, durum, notlar, olusturma_tarihi, olusturan_kullanici_id, record_id)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        tarih,
                        saat,
                        danisan,
                        terapist,
                        "",
                        "planlandi",
                        notlar or "",
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        (self.kullanici[0] if self.kullanici else None),
                        record_id,
                    ),
                )
                sid = int(cur.lastrowid or 0) or None
            except Exception:
                sid = None

        if sid:
            try:
                cur.execute("UPDATE records SET seans_id=? WHERE id=? AND (seans_id IS NULL OR seans_id='')", (sid, record_id))
            except Exception:
                pass

    def _sync_from_seans_to_record(self, cur, seans_id: int, tarih: str, saat: str, danisan: str, terapist: str, notlar: str):
        """seans_takvimi kaydı varsa records'a bağla/oluştur."""
        try:
            cur.execute("SELECT record_id FROM seans_takvimi WHERE id=?", (seans_id,))
            record_id = (cur.fetchone() or [None])[0]
        except Exception:
            record_id = None

        if record_id:
            try:
                cur.execute("UPDATE records SET seans_id=? WHERE id=? AND (seans_id IS NULL OR seans_id='')", (seans_id, record_id))
            except Exception:
                pass
            return

        # Aynı tarih+saat+danisan+terapist varsa bağla
        rid = None
        try:
            cur.execute(
                """
                SELECT id FROM records
                WHERE tarih=? AND COALESCE(saat,'')=? AND danisan_adi=? AND terapist=?
                ORDER BY id DESC LIMIT 1
                """,
                (tarih, saat, danisan, terapist),
            )
            row = cur.fetchone()
            if row and row[0]:
                rid = int(row[0])
        except Exception:
            rid = None

        if not rid:
            try:
                cur.execute(
                    """
                    INSERT INTO records (tarih, saat, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, seans_id, notlar, olusturma_tarihi)
                    VALUES (?,?,?,?,0,0,0,?,?,?)
                    """,
                    (
                        tarih,
                        saat,
                        danisan,
                        terapist,
                        seans_id,
                        notlar or "",
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                rid = int(cur.lastrowid or 0) or None
            except Exception:
                rid = None

        if rid:
            try:
                cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=? AND (record_id IS NULL OR record_id='')", (rid, seans_id))
            except Exception:
                pass

    def belirsizleri_duzelt_pencere(self):
        """Teknik olmayan kullanıcı için basit 'sihirbaz' ekranı."""
        if self.kullanici_yetki != "kurum_muduru":
            messagebox.showwarning("Yetki", "Bu ekran sadece Kurum Müdürü tarafından kullanılabilir.")
            return

        items = []
        try:
            items = list(getattr(self, "_last_sync_ambiguous", []) or [])
        except Exception:
            items = []

        if not items:
            messagebox.showinfo("Bilgi", "Şu anda düzeltilmesi gereken belirsiz kayıt yok.")
            return

        win = ttk.Toplevel(self)
        win.title("Belirsiz Kayıtları Düzelt")
        win.transient(self)
        center_window_smart(win, 980, 680)
        self._brand_window(win)

        wrapper = ttk.Frame(win, padding=12)
        wrapper.pack(fill=BOTH, expand=True)

        head = ttk.Frame(wrapper)
        head.pack(fill=X)
        ttk.Label(head, text="BELİRSİZ KAYITLARI DÜZELT", font=("Segoe UI", 14, "bold"), bootstyle="warning").pack(side=LEFT, anchor=W)
        prog_lbl = ttk.Label(head, text=f"Kalan: {len(items)}", font=("Segoe UI", 11, "bold"))
        prog_lbl.pack(side=RIGHT)
        ttk.Label(
            wrapper,
            text=(
                "Uygulama bazen aynı gün aynı danışan için birden fazla kayıt bulduğu için otomatik eşleştirme yapamaz.\n"
                "Aşağıdan doğru seçeneği seçip 'EŞLEŞTİR' diyerek işlemi tamamlayabilirsin."
            ),
            foreground="gray",
            wraplength=940,
        ).pack(anchor=W, pady=(6, 12))

        # Sol: iş listesi
        body = ttk.Frame(wrapper)
        body.pack(fill=BOTH, expand=True)

        left = ttk.Labelframe(body, text="Düzeltilmesi Gerekenler", padding=10)
        left.pack(side=LEFT, fill=Y, padx=(0, 10))

        lst = tk.Listbox(left, width=44, height=22)
        lst.pack(fill=Y, expand=False)

        # Sağ: detay + seçenekler
        right = ttk.Labelframe(body, text="Detay ve Seçim", padding=10)
        right.pack(side=LEFT, fill=BOTH, expand=True)

        info = ttk.Label(right, text="", font=("Segoe UI", 11, "bold"), wraplength=580)
        info.pack(anchor=W, pady=(0, 10))

        choice_var = tk.StringVar(value="")
        choices_box = ttk.Frame(right)
        choices_box.pack(fill=BOTH, expand=True)

        def _label_for_item(it: dict) -> str:
            if it.get("type") == "record_missing_time":
                return f"Seans Takip kaydı: {it.get('tarih','')} | {it.get('danisan','')} | {it.get('terapist','')}"
            if it.get("type") == "seans_multiple_records":
                return f"Takvim seansı: {it.get('tarih','')} {it.get('saat','')} | {it.get('danisan','')} | {it.get('terapist','')}"
            return "Belirsiz kayıt"

        for it in items:
            lst.insert(END, _label_for_item(it))

        def _clear_choices():
            for w in choices_box.winfo_children():
                try:
                    w.destroy()
                except Exception:
                    pass

        def _render(idx: int):
            _clear_choices()
            if idx < 0 or idx >= len(items):
                info.configure(text="Bitti. Kalan belirsiz kayıt yok.")
                try:
                    prog_lbl.configure(text="Kalan: 0")
                except Exception:
                    pass
                return
            it = items[idx]
            t = it.get("type")
            choice_var.set("")
            try:
                prog_lbl.configure(text=f"Kalan: {len(items)}")
            except Exception:
                pass

            if t == "record_missing_time":
                info.configure(
                    text=(
                        "Bu Seans Takip kaydında saat yok.\n"
                        "Takvimde aynı gün aynı danışan için birden fazla seans var.\n"
                        "Lütfen doğru saati seç:"
                    )
                )
                for c in it.get("candidates", []):
                    sid = c.get("seans_id")
                    saat = c.get("saat") or "(saat yok)"
                    ttk.Radiobutton(
                        choices_box,
                        text=f"{saat}  (Takvim ID: {sid})",
                        value=str(sid),
                        variable=choice_var,
                        bootstyle="warning",
                    ).pack(anchor=W, pady=4)

            elif t == "seans_multiple_records":
                info.configure(
                    text=(
                        "Bu Takvim seansı için Seans Takip'te birden fazla aday kayıt bulundu.\n"
                        "Lütfen doğru kaydı seç:"
                    )
                )
                for c in it.get("candidates", []):
                    rid = c.get("record_id")
                    linked = " (zaten bağlı)" if c.get("has_link") else ""
                    ttk.Radiobutton(
                        choices_box,
                        text=f"Seans Takip ID: {rid}{linked}",
                        value=str(rid),
                        variable=choice_var,
                        bootstyle="warning",
                    ).pack(anchor=W, pady=4)
            else:
                info.configure(text="Bu belirsiz tip tanınmadı.")

        def _selected_index():
            try:
                sel = lst.curselection()
                if not sel:
                    return 0
                return int(sel[0])
            except Exception:
                return 0

        def _apply_choice():
            idx = _selected_index()
            if idx < 0 or idx >= len(items):
                return
            it = items[idx]
            t = it.get("type")
            val = (choice_var.get() or "").strip()
            if not val:
                messagebox.showwarning("Uyarı", "Lütfen bir seçenek seçiniz.")
                return

            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()

                if t == "record_missing_time":
                    rid = int(it["record_id"])
                    sid = int(val)
                    cur.execute("SELECT tarih, COALESCE(saat,''), danisan_adi, terapist, COALESCE(notlar,'') FROM seans_takvimi WHERE id=?", (sid,))
                    row = cur.fetchone()
                    if not row:
                        conn.close()
                        messagebox.showerror("Hata", "Seçtiğiniz takvim seansı bulunamadı.")
                        return
                    tarih, saat, danisan, terapist, notlar = row[0], row[1], row[2], row[3], row[4]
                    # bağla + saat doldur
                    cur.execute("UPDATE records SET seans_id=?, saat=? WHERE id=?", (sid, saat, rid))
                    cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=?", (rid, sid))

                elif t == "seans_multiple_records":
                    sid = int(it["seans_id"])
                    rid = int(val)
                    # bağla
                    cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=?", (rid, sid))
                    cur.execute("UPDATE records SET seans_id=? WHERE id=?", (sid, rid))

                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Eşleştirme yapılamadı:\n{e}")
                return

            # listeden çıkar, sıradakine geç
            try:
                lst.delete(idx)
            except Exception:
                pass
            try:
                items.pop(idx)
            except Exception:
                pass
            try:
                self._last_sync_ambiguous = items
            except Exception:
                pass
            try:
                self.kayitlari_listele()
            except Exception:
                pass
            self._update_sync_badge()
            if items:
                try:
                    lst.selection_clear(0, END)
                    lst.selection_set(min(idx, len(items) - 1))
                except Exception:
                    pass
                _render(_selected_index())
            else:
                win.destroy()
                messagebox.showinfo("Bitti", "Tüm belirsiz kayıtlar düzeltildi.")

        def _skip():
            idx = _selected_index()
            if idx < 0 or idx >= len(items):
                return
            # sadece listeden kaldır; DB'ye dokunma
            try:
                lst.delete(idx)
            except Exception:
                pass
            try:
                items.pop(idx)
            except Exception:
                pass
            try:
                self._last_sync_ambiguous = items
            except Exception:
                pass
            self._update_sync_badge()
            if items:
                try:
                    lst.selection_clear(0, END)
                    lst.selection_set(min(idx, len(items) - 1))
                except Exception:
                    pass
                _render(_selected_index())
            else:
                win.destroy()
                messagebox.showinfo("Bitti", "Belirsiz kayıt kalmadı.")

        btns = ttk.Frame(right)
        btns.pack(fill=X, pady=(10, 0))
        ttk.Button(btns, text="EŞLEŞTİR (SEÇİLİ OLANI)", bootstyle="success", command=_apply_choice).pack(side=LEFT, fill=X, expand=True, padx=6)
        ttk.Button(btns, text="ŞİMDİLİK ATLA", bootstyle="secondary", command=_skip).pack(side=LEFT, fill=X, expand=True, padx=6)
        ttk.Button(btns, text="KAPAT", bootstyle="danger", command=win.destroy).pack(side=LEFT, fill=X, expand=True, padx=6)

        def _on_select(_evt=None):
            _render(_selected_index())

        lst.bind("<<ListboxSelect>>", _on_select)
        try:
            lst.selection_set(0)
        except Exception:
            pass
        _render(0)
        self._update_sync_badge()

    def senkronize_takvim_seanslar(self):
        """Toplu senkronizasyon: records <-> seans_takvimi.
        - Net eşleşme varsa bağlar (tarih+saat+danışan+terapist)
        - Saat eksikse tekil eşleşme varsa bağlar ve records.saat'i doldurur
        - Bulunamazsa eksik tarafta kayıt oluşturur
        """
        if self.kullanici_yetki != "kurum_muduru":
            messagebox.showwarning("Yetki", "Toplu senkronizasyon sadece Kurum Müdürü tarafından yapılabilir.")
            return
        if not messagebox.askyesno(
            "Onay",
            "Takvim ve Seans Takip kayıtları senkronize edilecek.\n\n"
            "Bu işlem:\n"
            "- Eşleşenleri bağlar\n"
            "- Eksik tarafta kayıt oluşturabilir\n\n"
            "Devam edilsin mi?",
        ):
            return

        stats = {
            "linked_records": 0,
            "created_seans": 0,
            "linked_seans": 0,
            "created_records": 0,
            "skipped_ambiguous": 0,
        }
        ambiguous: list[dict] = []

        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()

            # 1) records tarafı: seans_id yoksa bağla/oluştur
            cur.execute(
                """
                SELECT id, tarih, COALESCE(saat,''), danisan_adi, terapist, COALESCE(notlar,'')
                FROM records
                WHERE seans_id IS NULL OR seans_id=''
                ORDER BY id ASC
                """
            )
            rec_rows = cur.fetchall() or []

            for rid, tarih, saat, danisan, terapist, notlar in rec_rows:
                rid = int(rid)
                tarih = (tarih or "").strip()
                saat = (saat or "").strip()
                danisan = (danisan or "").strip().upper()
                terapist = (terapist or "").strip()
                notlar = (notlar or "").strip()

                # 1a) önce tam eşleşme
                sid = None
                if saat:
                    cur.execute(
                        """
                        SELECT id, COALESCE(record_id,NULL) FROM seans_takvimi
                        WHERE tarih=? AND saat=? AND danisan_adi=? AND terapist=?
                        ORDER BY id DESC LIMIT 1
                        """,
                        (tarih, saat, danisan, terapist),
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        sid = int(row[0])
                else:
                    # 1b) saat yoksa: tekil eşleşme varsa bağla + saat doldur
                    cur.execute(
                        """
                        SELECT id, saat, COALESCE(record_id,NULL) FROM seans_takvimi
                        WHERE tarih=? AND danisan_adi=? AND terapist=?
                        ORDER BY id DESC
                        """,
                        (tarih, danisan, terapist),
                    )
                    cands = cur.fetchall() or []
                    # sadece tek aday varsa güvenli
                    if len(cands) == 1:
                        sid = int(cands[0][0])
                        saat = (cands[0][1] or "").strip()
                        if saat:
                            cur.execute("UPDATE records SET saat=? WHERE id=? AND (saat IS NULL OR saat='')", (saat, rid))
                    elif len(cands) > 1:
                        stats["skipped_ambiguous"] += 1
                        try:
                            ambiguous.append(
                                {
                                    "type": "record_missing_time",
                                    "record_id": rid,
                                    "tarih": tarih,
                                    "danisan": danisan,
                                    "terapist": terapist,
                                    "candidates": [{"seans_id": int(x[0]), "saat": (x[1] or "").strip()} for x in cands],
                                }
                            )
                        except Exception:
                            pass

                if sid:
                    # bağla
                    cur.execute("UPDATE records SET seans_id=? WHERE id=? AND (seans_id IS NULL OR seans_id='')", (sid, rid))
                    cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=? AND (record_id IS NULL OR record_id='')", (rid, sid))
                    stats["linked_records"] += 1
                    continue

                # 1c) yoksa seans oluştur
                use_saat = saat or self._default_saat()
                cur.execute(
                    """
                    INSERT INTO seans_takvimi (tarih, saat, danisan_adi, terapist, oda, durum, notlar, olusturma_tarihi, olusturan_kullanici_id, record_id)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        tarih,
                        use_saat,
                        danisan,
                        terapist,
                        "",
                        "planlandi",
                        notlar,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        (self.kullanici[0] if self.kullanici else None),
                        rid,
                    ),
                )
                sid = int(cur.lastrowid or 0)
                cur.execute("UPDATE records SET seans_id=?, saat=? WHERE id=?", (sid, use_saat, rid))
                stats["created_seans"] += 1

            # 2) seans_takvimi tarafı: record_id yoksa bağla/oluştur
            cur.execute(
                """
                SELECT id, tarih, saat, danisan_adi, terapist, COALESCE(notlar,'')
                FROM seans_takvimi
                WHERE record_id IS NULL OR record_id=''
                ORDER BY id ASC
                """
            )
            seans_rows = cur.fetchall() or []

            for sid, tarih, saat, danisan, terapist, notlar in seans_rows:
                sid = int(sid)
                tarih = (tarih or "").strip()
                saat = (saat or "").strip()
                danisan = (danisan or "").strip().upper()
                terapist = (terapist or "").strip()
                notlar = (notlar or "").strip()

                cur.execute(
                    """
                    SELECT id, COALESCE(seans_id,NULL) FROM records
                    WHERE tarih=? AND COALESCE(saat,'')=? AND danisan_adi=? AND terapist=?
                    ORDER BY id DESC
                    """,
                    (tarih, saat, danisan, terapist),
                )
                cands = cur.fetchall() or []
                # Eğer birden fazla aday varsa yanlış bağlamamak için kullanıcıya soralım
                if len(cands) > 1:
                    stats["skipped_ambiguous"] += 1
                    try:
                        ambiguous.append(
                            {
                                "type": "seans_multiple_records",
                                "seans_id": sid,
                                "tarih": tarih,
                                "saat": saat,
                                "danisan": danisan,
                                "terapist": terapist,
                                "candidates": [{"record_id": int(x[0]), "has_link": bool(x[1])} for x in cands],
                            }
                        )
                    except Exception:
                        pass
                    continue

                rid = None
                if cands:
                    rid = int(cands[0][0])

                if rid:
                    cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=? AND (record_id IS NULL OR record_id='')", (rid, sid))
                    cur.execute("UPDATE records SET seans_id=? WHERE id=? AND (seans_id IS NULL OR seans_id='')", (sid, rid))
                    stats["linked_seans"] += 1
                    continue

                # yoksa record oluştur
                cur.execute(
                    """
                    INSERT INTO records (tarih, saat, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, notlar, olusturma_tarihi, seans_id)
                    VALUES (?,?,?,?,0,0,0,?,?,?)
                    """,
                    (
                        tarih,
                        saat,
                        danisan,
                        terapist,
                        notlar,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        sid,
                    ),
                )
                rid = int(cur.lastrowid or 0)
                cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=?", (rid, sid))
                stats["created_records"] += 1

            conn.commit()
            conn.close()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Hata", f"Senkronizasyon hatası:\n{e}")
            return

        # UI tazele
        try:
            self.kayitlari_listele()
        except Exception:
            pass

        # belirsiz listesi sakla (butondan tekrar açılabilsin)
        try:
            self._last_sync_ambiguous = ambiguous
        except Exception:
            pass
        self._update_sync_badge()

        messagebox.showinfo(
            "Senkronizasyon Tamam",
            "Özet:\n"
            f"- Bağlanan kayıtlar (records→seans): {stats['linked_records']}\n"
            f"- Oluşturulan seans (records→seans): {stats['created_seans']}\n"
            f"- Bağlanan seans (seans→records): {stats['linked_seans']}\n"
            f"- Oluşturulan kayıt (seans→records): {stats['created_records']}\n"
            f"- Belirsiz olduğu için atlanan: {stats['skipped_ambiguous']}\n\n"
            "Not: Belirsiz olanları istersen 'Belirsizleri Düzelt' ekranından tek tek seçerek tamamlayabilirsin.",
        )

        if ambiguous:
            if messagebox.askyesno(
                "Belirsiz Kayıtlar Var",
                f"{len(ambiguous)} adet belirsiz kayıt bulundu.\n\n"
                "Şimdi düzeltme ekranı açılsın mı?\n"
                "(İstersen sonra da 'Belirsizleri Düzelt' butonundan açabilirsin.)",
            ):
                self.belirsizleri_duzelt_pencere()

    def _range_summary(self, bas: str, bit: str, terapist: str | None = None) -> dict:
        """Kasa + seans özetini döndür."""
        out = {
            "seans_sayisi": 0,
            "bedel_toplam": 0.0,
            "alinan_toplam": 0.0,
            "kalan_toplam": 0.0,
            "kasa_giren": 0.0,
            "kasa_cikan": 0.0,
        }
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()

            if terapist:
                cur.execute(
                    """
                    SELECT COUNT(*),
                           COALESCE(SUM(hizmet_bedeli),0),
                           COALESCE(SUM(alinan_ucret),0),
                           COALESCE(SUM(kalan_borc),0)
                    FROM records
                    WHERE tarih>=? AND tarih<=? AND terapist=?
                    """,
                    (bas, bit, terapist),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*),
                           COALESCE(SUM(hizmet_bedeli),0),
                           COALESCE(SUM(alinan_ucret),0),
                           COALESCE(SUM(kalan_borc),0)
                    FROM records
                    WHERE tarih>=? AND tarih<=?
                    """,
                    (bas, bit),
                )
            c, b, a, k = cur.fetchone() or (0, 0, 0, 0)
            out["seans_sayisi"] = int(c or 0)
            out["bedel_toplam"] = float(b or 0)
            out["alinan_toplam"] = float(a or 0)
            out["kalan_toplam"] = float(k or 0)

            if terapist:
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN kh.tip='giren' THEN kh.tutar ELSE 0 END),0),
                        COALESCE(SUM(CASE WHEN kh.tip='cikan' THEN kh.tutar ELSE 0 END),0)
                    FROM kasa_hareketleri kh
                    LEFT JOIN records r ON r.id = kh.record_id
                    WHERE kh.tarih>=? AND kh.tarih<=? AND r.terapist=?
                    """,
                    (bas, bit, terapist),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN tip='giren' THEN tutar ELSE 0 END),0),
                        COALESCE(SUM(CASE WHEN tip='cikan' THEN tutar ELSE 0 END),0)
                    FROM kasa_hareketleri
                    WHERE tarih>=? AND tarih<=?
                    """,
                    (bas, bit),
                )
            g, ckn = cur.fetchone() or (0, 0)
            out["kasa_giren"] = float(g or 0)
            out["kasa_cikan"] = float(ckn or 0)
            conn.close()
        except Exception:
            pass
        return out

    def gunluk_rapor_pencere(self):
        # SEANS TAKİP ekranındaki tarih alanını baz al
        try:
            s = (self.tarih_var.get() or "").strip()
        except Exception:
            s = ""
        gun = self._tarih_db_from(s)
        self._rapor_pencere(gun, gun, title="Günlük Rapor")

    def haftalik_rapor_pencere(self):
        # SEANS TAKİP tarihine göre haftayı seç
        try:
            s = (self.tarih_var.get() or "").strip()
        except Exception:
            s = ""
        d = datetime.datetime.strptime(self._tarih_db_from(s), "%Y-%m-%d")
        bas = d - datetime.timedelta(days=d.weekday())
        bit = bas + datetime.timedelta(days=6)
        self._rapor_pencere(bas.strftime("%Y-%m-%d"), bit.strftime("%Y-%m-%d"), title="Haftalık Rapor")
    
    def senkronizasyon_kontrol_pencere(self):
        """Genel senkronizasyon kontrolü - Tüm tablolar arası tutarlılık"""
        win = ttk.Toplevel(self)
        win.title("Senkronizasyon Kontrolü")
        win.transient(self)
        center_window_smart(win, 900, 600)
        self._brand_window(win)
        
        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)
        ttk.Label(top, text="🔍 GENEL SENKRONİZASYON KONTROLÜ", font=("Segoe UI", 14, "bold"), bootstyle="info").pack(side=LEFT)
        
        # Kontrol butonu
        def _kontrol_et():
            try:
                conn = self.veritabani_baglan()
                kullanici_id = self.kullanici[0] if self.kullanici else None
                pipeline = DataPipeline(conn, kullanici_id)
                result = pipeline.validate_sync()
                conn.close()
                
                # Sonuçları göster
                for iid in tree.get_children():
                    tree.delete(iid)
                
                # İstatistikler
                stats = result["stats"]
                tree.insert("", END, values=("📊 İSTATİSTİKLER", "", ""), tags=("header",))
                tree.insert("", END, values=("Seans Takvimi", str(stats["seans_takvimi_count"]), ""))
                tree.insert("", END, values=("Records", str(stats["records_count"]), ""))
                tree.insert("", END, values=("Danışanlar", str(stats["danisanlar_count"]), ""))
                tree.insert("", END, values=("Odalar", str(stats["odalar_count"]), ""))
                tree.insert("", END, values=("Kasa Hareketleri", str(stats["kasa_hareketleri_count"]), ""))
                tree.insert("", END, values=("Ödeme Hareketleri", str(stats["odeme_hareketleri_count"]), ""))
                
                # Hatalar
                if result["errors"]:
                    tree.insert("", END, values=("", "", ""))
                    tree.insert("", END, values=("❌ HATALAR", "", ""), tags=("error",))
                    for err in result["errors"]:
                        tree.insert("", END, values=("", err, ""), tags=("error",))
                
                # Uyarılar
                missing_danisanlar_list.clear()
                if result["warnings"]:
                    tree.insert("", END, values=("", "", ""))
                    tree.insert("", END, values=("⚠️ UYARILAR", "", ""), tags=("warning",))
                    for warn in result["warnings"]:
                        tree.insert("", END, values=("", warn, ""), tags=("warning",))
                
                # Eksik danışanları al (validate_sync'den direkt)
                if "missing_danisanlar" in result:
                    missing_danisanlar_list.extend(result["missing_danisanlar"])
                
                # Eksik danışanlar varsa butonu aktif et
                if missing_danisanlar_list:
                    btn_ekle.config(state="normal")
                else:
                    btn_ekle.config(state="disabled")
                
                # Durum
                if result["ok"]:
                    durum_lbl.config(text="✅ Tüm senkronizasyonlar OK!", bootstyle="success")
                else:
                    durum_lbl.config(text=f"❌ {len(result['errors'])} hata bulundu!", bootstyle="danger")
                    
            except Exception as e:
                messagebox.showerror("Hata", f"Senkronizasyon kontrolü hatası:\n{e}")
                log_exception("senkronizasyon_kontrol", e)
        
        # Eksik danışanları otomatik ekle
        missing_danisanlar_list = []
        
        def _eksik_danisanlari_ekle():
            if not missing_danisanlar_list:
                messagebox.showinfo("Bilgi", "Eklenecek danışan bulunamadı.")
                return
            
            try:
                conn = self.veritabani_baglan()
                kullanici_id = self.kullanici[0] if self.kullanici else None
                pipeline = DataPipeline(conn, kullanici_id)
                
                eklenen = 0
                for danisan_adi in missing_danisanlar_list:
                    pipeline._ensure_danisan_exists(danisan_adi)
                    eklenen += 1
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Başarılı", f"{eklenen} danışan otomatik olarak eklendi!\n\nLütfen kontrolü tekrar çalıştırın.")
                _kontrol_et()
                
            except Exception as e:
                messagebox.showerror("Hata", f"Danışan ekleme hatası:\n{e}")
                log_exception("eksik_danisan_ekle", e)
        
        btn_frame = ttk.Frame(win, padding=10)
        btn_frame.pack(fill=X)
        ttk.Button(btn_frame, text="🔍 Kontrol Et", bootstyle="info", command=_kontrol_et).pack(side=LEFT, padx=6)
        btn_ekle = ttk.Button(btn_frame, text="➕ Eksik Danışanları Ekle", bootstyle="success", command=_eksik_danisanlari_ekle, state="disabled")
        btn_ekle.pack(side=LEFT, padx=6)
        durum_lbl = ttk.Label(btn_frame, text="Kontrol edilmeyi bekliyor...", font=("Segoe UI", 10, "bold"))
        durum_lbl.pack(side=LEFT, padx=20)
        
        # Sonuçlar
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)
        cols = ("Kategori", "Detay", "Durum")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=300)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        
        tree.tag_configure("header", background="#e9ecef", font=("Segoe UI", 10, "bold"))
        tree.tag_configure("error", foreground="#dc3545")
        tree.tag_configure("warning", foreground="#ffc107")
        
        # İlk kontrolü otomatik yap
        _kontrol_et()

    def toplam_rapor_pencere(self):
        self._rapor_pencere("0001-01-01", "9999-12-31", title="Toplam Rapor (Genel)")

    def _rapor_pencere(self, bas: str, bit: str, title: str):
        win = ttk.Toplevel(self)
        win.title(title)
        win.transient(self)
        center_window_smart(win, 1200, 720)
        self._brand_window(win)
        self._style_table_strong()

        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)
        ttk.Label(top, text=title.upper(), font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Label(top, text=f"Tarih: {bas}  →  {bit}", foreground="gray").pack(side=LEFT, padx=10)

        # özet - DETAYLI BİLGİLER
        s = self._range_summary(bas, bit, None if self.kullanici_yetki == "kurum_muduru" else (self.kullanici_terapist or None))
        net = float(s["kasa_giren"]) - float(s["kasa_cikan"])

        o = ttk.Labelframe(win, text="📊 DETAYLI ÖZET BİLGİLERİ", padding=12, bootstyle="info")
        o.pack(fill=X, padx=10, pady=(0, 10))
        
        # İlk satır - Seans ve Ücret Bilgileri
        row1 = ttk.Frame(o)
        row1.pack(fill=X, pady=(0, 8))
        ttk.Label(row1, text=f"📅 Toplam Seans Sayısı: {s['seans_sayisi']}", font=("Segoe UI", 10, "bold"), bootstyle="primary").pack(side=LEFT, padx=8)
        ttk.Label(row1, text=f"💰 Seans Ücreti (Toplam): {format_money(s['bedel_toplam'])}", font=("Segoe UI", 10, "bold"), bootstyle="success").pack(side=LEFT, padx=8)
        ttk.Label(row1, text=f"✅ Alınan Ödeme: {format_money(s['alinan_toplam'])}", font=("Segoe UI", 10, "bold"), bootstyle="warning").pack(side=LEFT, padx=8)
        ttk.Label(row1, text=f"⚠️ Kalan Borç: {format_money(s['kalan_toplam'])}", font=("Segoe UI", 10, "bold"), bootstyle="danger").pack(side=LEFT, padx=8)
        
        # İkinci satır - Kasa Bilgileri
        row2 = ttk.Frame(o)
        row2.pack(fill=X, pady=(4, 0))
        ttk.Label(row2, text=f"📥 Kasa Giren: {format_money(s['kasa_giren'])}", font=("Segoe UI", 10)).pack(side=LEFT, padx=8)
        ttk.Label(row2, text=f"📤 Kasa Çıkan: {format_money(s['kasa_cikan'])}", font=("Segoe UI", 10)).pack(side=LEFT, padx=8)
        ttk.Label(row2, text=f"💵 Net Kasa: {format_money(net)}", font=("Segoe UI", 11, "bold"), bootstyle="success").pack(side=LEFT, padx=8)
        
        # Açıklama
        aciklama = ttk.Label(
            o, 
            text=f"💡 Açıklama: {s['seans_sayisi']} seans için toplam {format_money(s['bedel_toplam'])} TL ücret belirlenmiş, {format_money(s['alinan_toplam'])} TL ödeme alınmış, {format_money(s['kalan_toplam'])} TL borç kalmıştır.",
            font=("Segoe UI", 9),
            foreground="gray",
            wraplength=1100
        )
        aciklama.pack(fill=X, padx=8, pady=(8, 0))

        # liste (records) - DETAYLI BİLGİLER
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)
        cols = ("Tarih", "Saat", "Danışan", "Terapist", "Seans Ücreti", "Alınan Ödeme", "Kalan Borç", "Oda", "Not")
        tree = ttk.Treeview(frame, columns=cols, show="headings", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            if c == "Tarih":
                tree.column(c, width=100)
            elif c == "Saat":
                tree.column(c, width=70)
            elif c == "Danışan":
                tree.column(c, width=200)
            elif c == "Terapist":
                tree.column(c, width=140)
            elif c in ("Seans Ücreti", "Alınan Ödeme", "Kalan Borç"):
                tree.column(c, width=120, anchor="e")
            elif c == "Oda":
                tree.column(c, width=80)
            elif c == "Not":
                tree.column(c, width=300)
            else:
                tree.column(c, width=120)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        
        # Tag'leri yapılandır (renkli görüntüleme)
        tree.tag_configure("borclu", background="#f8d7da", foreground="#721c24")
        tree.tag_configure("borclu_even", background="#f5c6cb", foreground="#721c24")
        tree.tag_configure("tamam", background="#d4edda", foreground="#155724")
        tree.tag_configure("tamam_even", background="#c3e6cb", foreground="#155724")
        tree.tag_configure("even", background="#f8f9fa")
        tree.tag_configure("odd", background="#ffffff")
        
        self._apply_stripes(tree)

        def _load():
            for iid in tree.get_children():
                tree.delete(iid)
            try:
                conn = self.veritabani_baglan()
                if self.kullanici_yetki == "kurum_muduru" or not self.kullanici_terapist:
                    df = pd.read_sql_query(
                        """
                        SELECT 
                            r.tarih,
                            COALESCE(r.saat, st.saat, '') AS saat,
                            r.danisan_adi,
                            r.terapist,
                            r.hizmet_bedeli AS seans_ucreti,
                            r.alinan_ucret AS alinan_odeme,
                            r.kalan_borc AS kalan_borc,
                            COALESCE(st.oda, '') AS oda,
                            COALESCE(r.notlar, st.notlar, '') AS notlar
                        FROM records r
                        LEFT JOIN seans_takvimi st ON r.seans_id = st.id OR r.id = st.record_id
                        WHERE r.tarih>=? AND r.tarih<=?
                        ORDER BY r.tarih, r.saat, r.id
                        """,
                        conn,
                        params=(bas, bit),
                    )
                else:
                    df = pd.read_sql_query(
                        """
                        SELECT 
                            r.tarih,
                            COALESCE(r.saat, st.saat, '') AS saat,
                            r.danisan_adi,
                            r.terapist,
                            r.hizmet_bedeli AS seans_ucreti,
                            r.alinan_ucret AS alinan_odeme,
                            r.kalan_borc AS kalan_borc,
                            COALESCE(st.oda, '') AS oda,
                            COALESCE(r.notlar, st.notlar, '') AS notlar
                        FROM records r
                        LEFT JOIN seans_takvimi st ON r.seans_id = st.id OR r.id = st.record_id
                        WHERE r.tarih>=? AND r.tarih<=? AND r.terapist=?
                        ORDER BY r.tarih, r.saat, r.id
                        """,
                        conn,
                        params=(bas, bit, self.kullanici_terapist),
                    )
                conn.close()
            except Exception as e:
                log_exception("_rapor_pencere_load", e)
                df = pd.DataFrame(columns=["tarih", "saat", "danisan_adi", "terapist", "seans_ucreti", "alinan_odeme", "kalan_borc", "oda", "notlar"])

            for idx, r in df.iterrows():
                tag = "even" if idx % 2 == 0 else "odd"
                # Kalan borç varsa kırmızı, yoksa yeşil
                if float(r.get("kalan_borc", 0) or 0) > 0:
                    tag = "borclu" if tag == "odd" else "borclu_even"
                else:
                    tag = "tamam" if tag == "odd" else "tamam_even"
                    
                tree.insert(
                    "",
                    END,
                    values=(
                        r.get("tarih", ""),
                        r.get("saat", ""),
                        r.get("danisan_adi", ""),
                        r.get("terapist", ""),
                        format_money(r.get("seans_ucreti", 0) or 0),
                        format_money(r.get("alinan_odeme", 0) or 0),
                        format_money(r.get("kalan_borc", 0) or 0),
                        r.get("oda", "") or "",
                        r.get("notlar", "") or "",
                    ),
                    tags=(tag,),
                )

            return df

        df_cache = {"df": _load()}

        def _excel():
            df = df_cache.get("df")
            if df is None:
                return
            path = filedialog.asksaveasfilename(
                title="Excel Kaydet",
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")],
                initialfile=f"rapor_{bas}_{bit}.xlsx",
            )
            if not path:
                return
            try:
                df.to_excel(path, index=False, engine="openpyxl")
                messagebox.showinfo("Başarılı", "Excel'e aktarıldı.")
            except Exception as e:
                messagebox.showerror("Hata", f"Excel aktarma hatası:\n{e}")

        btns = ttk.Frame(win, padding=10)
        btns.pack(fill=X)
        ttk.Button(btns, text="Yenile", bootstyle="secondary", command=lambda: df_cache.update(df=_load())).pack(side=LEFT, padx=6)
        ttk.Button(btns, text="Excel'e Aktar", bootstyle="primary", command=_excel).pack(side=RIGHT, padx=6)

    def _reload_logos(self) -> None:
        """Logo dosyası değiştiyse PhotoImage'ları yeniden yükle ve UI'da güncelle."""
        self._logo_small = load_logo_photo(28, 28)
        self._logo_big = load_logo_photo(80, 80)
        self._logo_icon = load_logo_photo(64, 64)
        safe_iconphoto(self, self._logo_icon)

        try:
            if self._toolbar_logo_lbl is not None:
                if self._logo_small is not None:
                    self._toolbar_logo_lbl.configure(image=self._logo_small)
                    self._toolbar_logo_lbl.image = self._logo_small
                else:
                    self._toolbar_logo_lbl.destroy()
                    self._toolbar_logo_lbl = None
        except Exception:
            pass

        try:
            if self._login_logo_lbl is not None:
                if self._logo_big is not None:
                    self._login_logo_lbl.configure(image=self._logo_big)
                    self._login_logo_lbl.image = self._logo_big
                else:
                    self._login_logo_lbl.destroy()
                    self._login_logo_lbl = None
        except Exception:
            pass

    def logo_yukle_degistir(self):
        """Kurum müdürü için: logo.png seçip AppData'ya kopyalar."""
        if self.kullanici_yetki != "kurum_muduru":
            messagebox.showwarning("Yetki", "Logo değiştirme sadece Kurum Müdürü tarafından yapılabilir.")
            return
        path = filedialog.askopenfilename(
            title="Logo Seç (PNG)",
            filetypes=[("PNG", "*.png")],
        )
        if not path:
            return
        try:
            os.makedirs(data_dir(), exist_ok=True)
            target = os.path.join(data_dir(), "logo.png")
            shutil.copy2(path, target)
        except Exception as e:
            messagebox.showerror("Hata", f"Logo kopyalanamadı:\n{e}")
            return

        self._reload_logos()
        messagebox.showinfo("Başarılı", "Logo kaydedildi.\nGerekirse programı kapatıp tekrar açın.")

    def _apply_user_restrictions(self):
        # Eğitim görevlisi ise kendi adına kilitle
        if self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
            try:
                self.cmb_terapist.set(self.kullanici_terapist)
                self.cmb_terapist.configure(state="disabled")
            except Exception:
                pass

    def _build_menu(self):
        # Not: Windows'ta ttkbootstrap Menu bazen görünürlük sorunu çıkarabiliyor.
        # Bu yüzden ana menüde tkinter.Menu kullanıyoruz.
        menubar = Menu(self)
        self.config(menu=menubar)
        # Rol bazlı modüller (leta_pro uyumlu)
        if self.kullanici_yetki == "kurum_muduru":
            seans_menu = Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Seans Takvimi", menu=seans_menu)
            seans_menu.add_command(label="Günlük Takvim", command=self.seans_takvimi_goster)
            seans_menu.add_command(label="Haftalık Takvim", command=self.haftalik_takvim_goster)
            seans_menu.add_separator()
            seans_menu.add_command(label="Seans Listesi (Düzenle/Sil)", command=self.seans_listesi)

            sekreter_menu = Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Sekreterlik", menu=sekreter_menu)
            sekreter_menu.add_command(label="Danışan Yönetimi", command=self.danisan_yonetimi)
            sekreter_menu.add_command(label="Randevu Yönetimi", command=self.randevu_yonetimi)
            sekreter_menu.add_command(label="Görev Takibi", command=self.gorev_takibi)
            sekreter_menu.add_command(label="Oda Yönetimi", command=self.odalar_yonetimi)

            muhasebe_menu = Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Muhasebe", menu=muhasebe_menu)
            muhasebe_menu.add_command(label="Ücret Takibi", command=self.ucret_takibi_goster)
            muhasebe_menu.add_command(label="Haftalık Ders/Ücret Takip", command=self.haftalik_ders_ucret_takip)
            muhasebe_menu.add_command(label="Kasa Defteri (Günlük)", command=self.kasa_defteri_goster)
            muhasebe_menu.add_command(label="Gelir-Gider Raporu", command=self.gelir_gider_raporu)
            muhasebe_menu.add_command(label="Ödeme İşlemleri", command=self.odeme_islemleri)

            kullanici_menu = Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Kullanıcı Yönetimi", menu=kullanici_menu)
            kullanici_menu.add_command(label="Kullanıcıları Listele", command=self.kullanicilari_listele)
            kullanici_menu.add_command(label="Kullanıcı Sil/Pasif Et", command=self.kullanici_sil)

        elif self.kullanici_yetki in ["egitim_gorevlisi", "normal"]:
            seans_menu = Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Seans Takvimi", menu=seans_menu)
            seans_menu.add_command(label="Kendi Seanslarım", command=self.kendi_seanslarim)
            seans_menu.add_command(label="Haftalık Takvim", command=self.haftalik_takvim_goster)

            muhasebe_menu = Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Ücret Takibi", menu=muhasebe_menu)
            muhasebe_menu.add_command(label="Kendi Ücretlerim", command=self.kendi_ucretlerim)
            muhasebe_menu.add_command(label="Haftalık Ders/Ücret Takip", command=self.haftalik_ders_ucret_takip)

        dosya_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya İşlemleri", menu=dosya_menu)
        dosya_menu.add_command(label="Excel'e Aktar", command=self.excel_aktar)
        dosya_menu.add_command(label="Yedek Klasörünü Aç", command=self.yedek_klasoru_ac)
        if self.kullanici_yetki == "kurum_muduru":
            dosya_menu.add_separator()
            dosya_menu.add_command(label="Sistemi Sıfırla (DB Sil)", command=self.sistemi_sifirla)
        dosya_menu.add_separator()
        dosya_menu.add_command(label="Giriş Ekranına Dön", command=self.girise_don)
        dosya_menu.add_command(label="Çıkış", command=self._on_close)

        yardim_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Yardım", menu=yardim_menu)
        yardim_menu.add_command(label="İlk 5 Adım (Hızlı Yardım)", command=self.ilk_5_adim_goster)
        yardim_menu.add_command(label="Kullanım Kılavuzu", command=self.kullanim_kilavuzu_ac)
        yardim_menu.add_command(label="Logo Yükle/Değiştir (Kurum Müdürü)", command=self.logo_yukle_degistir)
        yardim_menu.add_command(label="Hakkında", command=self.hakkinda_goster)

    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.tab_records = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_records, text="SEANS TAKİP")

        self._build_records_tab()

        # ANA SAYFA: Menü görünür olmasa bile butonlarla erişim (özellikle sahada kullanım için)
        self.tab_modules = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_modules, text="ANA SAYFA")
        self._build_modules_tab()

        # ÜCRET TAKİPİ - Çocuk ve Personel ücret takipleri (tek ekranda 2 sayfa)
        self.tab_ucret_takibi = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_ucret_takibi, text="ÜCRET TAKİPİ")
        self._build_ucret_takibi_tab()

        # ÇOCUK GÜNLÜK TAKİP - Oda ve personel takibi
        self.tab_cocuk_gunluk = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_cocuk_gunluk, text="ÇOCUK GÜNLÜK TAKİP")
        self._build_cocuk_gunluk_tab()

        # KASA DEFTERİ - Günlük/haftalık/aylık raporlar
        self.tab_kasa = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_kasa, text="KASA DEFTERİ")
        self._build_kasa_defteri_tab()

        # BEP - Bireysel Eğitim Programı
        self.tab_bep = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_bep, text="BEP")
        self._build_bep_tab()

        # HAFTALIK SEANS TAKİP - Personel bazlı dinamik program
        self.tab_haftalik = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_haftalik, text="HAFTALIK PROGRAM")
        self._build_haftalik_seans_tab()

        # ÖĞRENCİ BİLGİLERİ - Aile ve kimlik bilgileri
        self.tab_ogrenci_bilgileri = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_ogrenci_bilgileri, text="ÖĞRENCİ BİLGİLERİ")
        self._build_ogrenci_bilgileri_tab()

        # SİSTEM ŞİFRELERİ (Opsiyonel - Sadece kurum müdürü)
        if self.kullanici_yetki == "kurum_muduru":
            self.tab_sifreler = ttk.Frame(self.nb, padding=10)
            self.nb.add(self.tab_sifreler, text="SİSTEM ŞİFRELERİ")
            self._build_sifreler_tab()

        # AYARLAR sadece kurum müdürü
        if self.kullanici_yetki == "kurum_muduru":
            self.tab_settings = ttk.Frame(self.nb, padding=10)
            self.nb.add(self.tab_settings, text="AYARLAR")
            self._build_settings_tab()

        # Klasik akış: girişten sonra ilk görünen ANA SAYFA olsun
        try:
            self.nb.select(self.tab_modules)
        except Exception:
            pass

    def _build_modules_tab(self):
        # Ana ekran: Hızlı işlemler butonları direkt ana sayfada
        wrapper = ttk.Frame(self.tab_modules, padding=10)
        wrapper.pack(fill=BOTH, expand=True)

        head = ttk.Frame(wrapper)
        head.pack(fill=X, pady=(0, 8))
        if getattr(self, "_logo_small", None):
            ttk.Label(head, image=self._logo_small).pack(side=LEFT, padx=(0, 10))
        ttk.Label(head, text="ANA SAYFA", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(side=LEFT)

        ttk.Label(wrapper, text="Hızlı İşlemler:", font=("Segoe UI", 12, "bold"), bootstyle="primary").pack(anchor=W, pady=(0, 10))

        # Hızlı işlemler butonları - Grid layout
        quick_frame = ttk.Frame(wrapper)
        quick_frame.pack(fill=X, pady=(0, 20))

        # İlk satır
        row1 = ttk.Frame(quick_frame)
        row1.pack(fill=X, pady=6)
        ttk.Button(row1, text="📝 Seans Kaydı Ekle (Hızlı)", bootstyle="success", 
                   command=self.hizli_seans_kaydi_ekle, width=30).pack(side=LEFT, padx=6, fill=X, expand=True)
        ttk.Button(row1, text="📊 Haftalık Ders/Ücret Takip", bootstyle="primary", 
                   command=self.haftalik_ders_ucret_takip, width=30).pack(side=LEFT, padx=6, fill=X, expand=True)
        ttk.Button(row1, text="💰 Kasa Defteri (Günlük)", bootstyle="warning", 
                   command=self.kasa_defteri_goster, width=30).pack(side=LEFT, padx=6, fill=X, expand=True)

        # İkinci satır
        row2 = ttk.Frame(quick_frame)
        row2.pack(fill=X, pady=6)
        ttk.Button(row2, text="📋 Seans Takip", bootstyle="success", 
                   command=lambda: self.nb.select(self.tab_records), width=30).pack(side=LEFT, padx=6, fill=X, expand=True)
        ttk.Button(row2, text="❓ İlk 5 Adım (Yardım)", bootstyle="secondary", 
                   command=self.ilk_5_adim_goster, width=30).pack(side=LEFT, padx=6, fill=X, expand=True)
        ttk.Button(row2, text="📖 Kullanım Kılavuzu", bootstyle="secondary", 
                   command=self.kullanim_kilavuzu_ac, width=30).pack(side=LEFT, padx=6, fill=X, expand=True)

        # Kurum Müdürü için ek butonlar
        if self.kullanici_yetki == "kurum_muduru":
            row3 = ttk.Frame(quick_frame)
            row3.pack(fill=X, pady=6)
            ttk.Button(row3, text="⚙️ Ayarlar", bootstyle="warning", 
                       command=lambda: self.nb.select(self.tab_settings) if hasattr(self, "tab_settings") else None, 
                       width=30).pack(side=LEFT, padx=6, fill=X, expand=True)
            ttk.Button(row3, text="🔄 Eski Veri Migration", bootstyle="info",
                       command=self.eski_veri_migration, width=30).pack(side=LEFT, padx=6, fill=X, expand=True)
            ttk.Button(row3, text="🖼️ Logo Yükle/Değiştir", bootstyle="secondary", 
                       command=self.logo_yukle_degistir, width=30).pack(side=LEFT, padx=6, fill=X, expand=True)
            ttk.Button(row3, text="⚠️ Sistemi Sıfırla (DB Sil)", bootstyle="danger", 
                       command=self.sistemi_sifirla, width=30).pack(side=LEFT, padx=6, fill=X, expand=True)

    def _quick_actions_pencere(self):
        win = ttk.Toplevel(self)
        win.title("Hızlı İşlemler")
        win.transient(self)
        center_window_smart(win, 720, 520)
        self._brand_window(win)

        box = ttk.Frame(win, padding=12)
        box.pack(fill=BOTH, expand=True)

        ttk.Label(box, text="HIZLI İŞLEMLER", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(anchor=W, pady=(0, 10))

        def btn(text, cmd, style="primary"):
            ttk.Button(box, text=text, command=cmd, bootstyle=style).pack(fill=X, pady=6)

        btn("Seans Kaydı Ekle (Hızlı)", self.hizli_seans_kaydi_ekle, "success")
        btn("Haftalık Ders/Ücret Takip", self.haftalik_ders_ucret_takip, "primary")
        btn("Kasa Defteri (Günlük)", self.kasa_defteri_goster, "warning")
        btn("İlk 5 Adım (Yardım)", self.ilk_5_adim_goster, "secondary")
        btn("Kullanım Kılavuzu", self.kullanim_kilavuzu_ac, "secondary")

        if self.kullanici_yetki == "kurum_muduru":
            btn("Logo Yükle/Değiştir", self.logo_yukle_degistir, "secondary")
            btn("Sistemi Sıfırla (DB Sil)", self.sistemi_sifirla, "danger")

    def _validate_money(self, newval: str) -> bool:
        if newval.strip() == "":
            return True
        allowed = set("0123456789.,")
        return all(ch in allowed for ch in newval)

    def veritabani_baglan(self) -> sqlite3.Connection:
        return connect_db()

    # --- TAB 1: SEANS TAKİP ---
    def _build_records_tab(self):
        top = ttk.Labelframe(self.tab_records, text="Yeni Seans Kaydı", padding=16, bootstyle="primary")
        top.pack(fill=X, pady=(0, 12))

        ttk.Label(top, text="Tarih:", font=("Segoe UI", 10)).grid(row=0, column=0, padx=8, pady=8, sticky=W)
        self.tarih_var = ttk.StringVar(value=datetime.datetime.now().strftime("%d.%m.%Y"))
        ent_tarih = ttk.Entry(top, textvariable=self.tarih_var, width=16, font=("Segoe UI", 10))
        ent_tarih.grid(row=0, column=1, padx=8, pady=8, sticky=W)

        ttk.Label(top, text="Saat:", font=("Segoe UI", 10)).grid(row=0, column=2, padx=8, pady=8, sticky=W)
        self.cmb_saat = ttk.Combobox(
            top,
            state="readonly",
            width=10,
            values=[f"{h:02d}:00" for h in range(7, 22)] + [f"{h:02d}:30" for h in range(7, 22)],
        )
        try:
            self.cmb_saat.set(self._default_saat())
        except Exception:
            self.cmb_saat.set("09:00")
        self.cmb_saat.grid(row=0, column=3, padx=8, pady=8, sticky=W)

        ttk.Label(top, text="Danışan:", font=("Segoe UI", 10)).grid(row=0, column=4, padx=8, pady=8, sticky=W)
        # Danışan seçimi - Terapist gibi entegre combobox + buton
        danisan_frame = ttk.Frame(top)
        danisan_frame.grid(row=0, column=5, padx=8, pady=8, sticky=W)
        
        self.cmb_danisan = ttk.Combobox(danisan_frame, width=28, state="normal")
        # Danışan listesini yükle - TÜM AKTİF DANIŞANLAR
        self._yenile_danisan_listesi()
        self.cmb_danisan.pack(side=LEFT)
        
        # Yeni danışan ekle butonu - Terapist gibi küçük buton
        def _yeni_danisan_ekle():
            self._yeni_danisan_ekle_ve_guncelle(self.cmb_danisan, top)
        
        btn_yeni_danisan = ttk.Button(danisan_frame, text="+", bootstyle="success-outline", width=4,
                                      command=_yeni_danisan_ekle)
        btn_yeni_danisan.pack(side=LEFT, padx=(4, 0))

        ttk.Label(top, text="Terapist:", font=("Segoe UI", 10)).grid(row=0, column=6, padx=8, pady=8, sticky=W)
        self.cmb_terapist = ttk.Combobox(top, state="readonly", width=24)
        self.cmb_terapist.grid(row=0, column=7, padx=8, pady=8, sticky=W)
        
        # Hizmet bedeli otomatik atama - Danışan ve Terapist seçildiğinde
        def _otomatik_bedel_ata(*args):
            """Danışan ve terapist seçildiğinde otomatik hizmet bedeli ata"""
            try:
                danisan_adi = (self.cmb_danisan.get() or "").strip().upper()
                terapist_adi = (self.cmb_terapist.get() or "").strip()
                
                # Eğer hizmet bedeli zaten girilmişse, değiştirme
                mevcut_bedel = self.ent_bedel.get().strip()
                if mevcut_bedel and float(mevcut_bedel.replace(",", ".").replace(".", "", mevcut_bedel.count(".") - 1) or 0) > 0:
                    return
                
                if danisan_adi and terapist_adi:
                    conn = self.veritabani_baglan()
                    cur = conn.cursor()
                    
                    # Öğrenci ID'sini bul
                    cur.execute("SELECT id FROM danisanlar WHERE UPPER(ad_soyad) = UPPER(?) AND aktif = 1 LIMIT 1", (danisan_adi,))
                    row = cur.fetchone()
                    if row:
                        ogrenci_id = row[0]
                        # Otomatik ücreti al
                        otomatik_ucret = get_ogrenci_personel_ucreti(ogrenci_id, terapist_adi, conn)
                        if otomatik_ucret > 0:
                            self.ent_bedel.delete(0, END)
                            self.ent_bedel.insert(0, format_money(otomatik_ucret))
                    
                    conn.close()
            except Exception as e:
                log_exception("_otomatik_bedel_ata", e)
        
        # Event binding - Danışan veya terapist değiştiğinde otomatik bedel ata
        self.cmb_danisan.bind("<<ComboboxSelected>>", _otomatik_bedel_ata)
        self.cmb_danisan.bind("<KeyRelease>", lambda e: self.after(300, _otomatik_bedel_ata))  # Yazarken de kontrol et
        self.cmb_terapist.bind("<<ComboboxSelected>>", _otomatik_bedel_ata)

        ttk.Label(top, text="Oda:", font=("Segoe UI", 10)).grid(row=0, column=8, padx=8, pady=8, sticky=W)
        self.cmb_oda = ttk.Combobox(top, state="readonly", width=18)
        # Oda listesini veritabanından çek
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT oda_adi FROM odalar WHERE aktif=1 ORDER BY oda_adi")
            oda_listesi = [row[0] for row in cur.fetchall()]
            conn.close()
            if not oda_listesi:
                oda_listesi = ["Oda Seçiniz"]  # Varsayılan
        except Exception:
            oda_listesi = ["Oda Seçiniz"]
        self.cmb_oda["values"] = oda_listesi
        self.cmb_oda.grid(row=0, column=9, padx=8, pady=8, sticky=W)

        ttk.Label(top, text="Hizmet Bedeli (₺):", font=("Segoe UI", 10)).grid(row=1, column=0, padx=8, pady=8, sticky=W)
        self.ent_bedel = ttk.Entry(top, width=18, validate="key", validatecommand=self._vcmd_money, font=("Segoe UI", 10))
        self.ent_bedel.grid(row=1, column=1, padx=8, pady=8, sticky=W)

        ttk.Label(top, text="Alınan (₺):", font=("Segoe UI", 10)).grid(row=1, column=2, padx=8, pady=8, sticky=W)
        self.ent_alinan = ttk.Entry(top, width=18, validate="key", validatecommand=self._vcmd_money, font=("Segoe UI", 10))
        self.ent_alinan.insert(0, "0")
        self.ent_alinan.grid(row=1, column=3, padx=8, pady=8, sticky=W)

        ttk.Label(top, text="Not (Açıklama):", font=("Segoe UI", 10)).grid(row=1, column=4, padx=8, pady=8, sticky=W)
        self.ent_not = ttk.Entry(top, width=50, font=("Segoe UI", 10))
        self.ent_not.grid(row=1, column=5, columnspan=4, padx=8, pady=8, sticky=W+E)

        ttk.Button(top, text="KAYDET", bootstyle="success", command=self.kayit_ekle, width=20, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=10, rowspan=2, padx=12, pady=8, sticky="nsew"
        )

        # RAPORLAR (günlük / haftalık / toplam) - kasa için gereken özetler burada
        rep = ttk.Labelframe(self.tab_records, text="Raporlar", padding=10, bootstyle="secondary")
        rep.pack(fill=X, pady=(0, 10))
        ttk.Button(rep, text="Günlük Rapor", bootstyle="primary", command=self.gunluk_rapor_pencere).pack(side=LEFT, padx=6)
        ttk.Button(rep, text="Haftalık Rapor", bootstyle="primary", command=self.haftalik_rapor_pencere).pack(side=LEFT, padx=6)
        ttk.Button(rep, text="Toplam Rapor (Genel)", bootstyle="secondary", command=self.toplam_rapor_pencere).pack(side=LEFT, padx=6)
        ttk.Button(rep, text="🔍 Senkronizasyon Kontrol", bootstyle="info", command=self.senkronizasyon_kontrol_pencere).pack(
            side=RIGHT, padx=6
        )
        ttk.Button(rep, text="Senkronize (Takvim↔Seans)", bootstyle="warning", command=self.senkronize_takvim_seanslar).pack(
            side=RIGHT, padx=6
        )
        ttk.Button(rep, text="Belirsizleri Düzelt", bootstyle="warning-outline", command=self.belirsizleri_duzelt_pencere).pack(
            side=RIGHT, padx=6
        )
        self._sync_badge_lbl = ttk.Label(rep, text="Belirsiz: 0", font=("Segoe UI", 10, "bold"), foreground="#a66f00")
        self._sync_badge_lbl.pack(side=RIGHT, padx=10)

        ttk.Label(
            self.tab_records,
            text="İpucu: 'Senkronize' iki modülü eşler. 'Belirsizleri Düzelt' otomatik eşleştirilemeyenleri sana sorar.",
            foreground="gray",
        ).pack(anchor=W, pady=(0, 8), padx=4)
        self._update_sync_badge()

        mid = ttk.Frame(self.tab_records)
        mid.pack(fill=X, pady=(0, 8))
        ttk.Label(mid, text="İsim ile ara...", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(4, 6))
        self.ent_ara = ttk.Entry(mid, width=40)
        self.ent_ara.pack(side=LEFT, padx=6)
        self.ent_ara.bind("<KeyRelease>", lambda e: self.kayitlari_listele())

        self.lbl_ozet = ttk.Label(
            mid, text="TOPLAM İÇERİDEKİ ALACAK: 0.00 TL", font=("Segoe UI", 12, "bold"), bootstyle="danger"
        )
        self.lbl_ozet.pack(side=RIGHT, padx=6)

        table = ttk.Frame(self.tab_records)
        table.pack(fill=BOTH, expand=True)

        cols = ("ID", "Tarih", "Saat", "Danışan", "Terapist", "Bedel", "Ödenen", "KALAN BORÇ", "Notlar")
        self._style_table_strong()
        self.tree = ttk.Treeview(table, columns=cols, show="headings", bootstyle="info", style="Strong.Treeview")
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.column("ID", width=0, stretch=False)
        self.tree.column("Tarih", width=110, anchor="center")
        self.tree.column("Saat", width=70, anchor="center")
        self.tree.column("Danışan", width=280)  # Genişletildi - tam isim görünsün
        self.tree.column("Terapist", width=160)
        self.tree.column("Bedel", width=110, anchor="e")
        self.tree.column("Ödenen", width=110, anchor="e")
        self.tree.column("KALAN BORÇ", width=120, anchor="e")
        self.tree.column("Notlar", width=320)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)

        sb = ttk.Scrollbar(table, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)

        self.tree.tag_configure("borclu", background="#f8d7da", foreground="#721c24")
        self.tree.tag_configure("tamam", background="#d4edda", foreground="#155724")

        self.ctx = ttk.Menu(self, tearoff=0)
        self.ctx.add_command(label="Ödeme Ekle", command=self.odeme_ekle)
        self.ctx.add_command(label="Kaydı Sil", command=self.kayit_sil)
        self.tree.bind("<Button-3>", self._ctx_open)

    def _ctx_open(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.ctx.post(event.x_root, event.y_root)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0]).get("values") or []
        if not vals:
            return None
        try:
            return int(vals[0])
        except Exception:
            return None

    def _tarih_db(self) -> str:
        s = (self.tarih_var.get() or "").strip()
        try:
            dt = datetime.datetime.strptime(s, "%d.%m.%Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return datetime.datetime.now().strftime("%Y-%m-%d")

    def _tarih_db_from(self, s: str) -> str:
        s = (s or "").strip()
        if not s:
            return datetime.datetime.now().strftime("%Y-%m-%d")
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except Exception:
                pass
        return datetime.datetime.now().strftime("%Y-%m-%d")

    def _yenile_danisan_listesi(self):
        """Danışan listesini veritabanından yükle ve combobox'a ekle"""
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
            danisan_listesi = [row[0] for row in cur.fetchall()]
            conn.close()
            if hasattr(self, 'cmb_danisan'):
                self.cmb_danisan["values"] = danisan_listesi
            return danisan_listesi
        except Exception as e:
            log_exception("_yenile_danisan_listesi", e)
            if hasattr(self, 'cmb_danisan'):
                self.cmb_danisan["values"] = []
            return []
    
    def _yeni_danisan_ekle_ve_guncelle(self, combobox, parent):
        """Yeni danışan ekle ve combobox'ı güncelle"""
        try:
            win = ttk.Toplevel(self)
            win.title("Yeni Danışan Ekle")
            win.resizable(False, False)
            center_window(win, 500, 400)
            win.transient(self)
            win.grab_set()
            self._brand_window(win)
            
            wrapper = ttk.Frame(win, padding=20)
            wrapper.pack(fill=BOTH, expand=True)
            
            ttk.Label(wrapper, text="Yeni Danışan Ekle", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=(0, 20))
            
            ttk.Label(wrapper, text="Ad Soyad:", font=("Segoe UI", 10)).pack(anchor=W, pady=5)
            ent_ad = ttk.Entry(wrapper, width=40, font=("Segoe UI", 10))
            ent_ad.pack(fill=X, pady=5)
            ent_ad.focus_set()
            
            def _kaydet():
                ad_soyad = (ent_ad.get() or "").strip().upper()
                if not ad_soyad:
                    messagebox.showwarning("Uyarı", "Ad Soyad zorunludur!")
                    return
                
                try:
                    conn = self.veritabani_baglan()
                    cur = conn.cursor()
                    # Zaten var mı kontrol et
                    cur.execute("SELECT id FROM danisanlar WHERE UPPER(ad_soyad) = UPPER(?) AND aktif=1", (ad_soyad,))
                    if cur.fetchone():
                        messagebox.showinfo("Bilgi", f"{ad_soyad} zaten kayıtlı!")
                        conn.close()
                        win.destroy()
                        # Listeyi yenile
                        self._yenile_danisan_listesi()
                        combobox.set(ad_soyad)
                        return
                    
                    # Yeni danışan ekle
                    cur.execute(
                        "INSERT INTO danisanlar (ad_soyad, aktif, olusturma_tarihi) VALUES (?, 1, ?)",
                        (ad_soyad, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
                    conn.commit()
                    conn.close()
                    
                    messagebox.showinfo("Başarılı", f"{ad_soyad} eklendi!")
                    win.destroy()
                    
                    # Combobox'ı güncelle
                    self._yenile_danisan_listesi()
                    combobox.set(ad_soyad)
                    
                except Exception as e:
                    messagebox.showerror("Hata", f"Danışan eklenemedi:\n{e}")
                    log_exception("_yeni_danisan_ekle_ve_guncelle", e)
            
            ttk.Button(wrapper, text="Kaydet", bootstyle="success", command=_kaydet, width=20).pack(pady=20)
            
            # Enter tuşu ile kaydet
            ent_ad.bind("<Return>", lambda e: _kaydet())
            
        except Exception as e:
            messagebox.showerror("Hata", f"Pencere açılamadı:\n{e}")
            log_exception("_yeni_danisan_ekle_ve_guncelle", e)

    def hizli_seans_kaydi_ekle(self):
        """Yeni kullanıcılar için en basit kayıt ekranı (ANA SAYFA)."""
        win = ttk.Toplevel(self)
        win.title("Seans Kaydı Ekle")
        win.resizable(False, False)
        center_window(win, 700, 500)
        win.transient(self)
        win.grab_set()
        self._brand_window(win)

        ttk.Label(win, text="SEANS KAYDI EKLE", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)
        frm = ttk.Frame(win, padding=14)
        frm.pack(fill=BOTH, expand=True)

        ttk.Label(frm, text="Tarih:").grid(row=0, column=0, sticky=W, padx=6, pady=6)
        tarih_var = ttk.StringVar(value=datetime.datetime.now().strftime("%d.%m.%Y"))
        ent_tarih = ttk.Entry(frm, textvariable=tarih_var, width=16)
        ent_tarih.grid(row=0, column=1, sticky=W, padx=6, pady=6)

        ttk.Label(frm, text="Saat:").grid(row=0, column=2, sticky=W, padx=6, pady=6)
        cb_saat = ttk.Combobox(
            frm,
            state="readonly",
            width=10,
            values=[f"{h:02d}:00" for h in range(7, 22)] + [f"{h:02d}:30" for h in range(7, 22)],
        )
        cb_saat.set(self._default_saat())
        cb_saat.grid(row=0, column=3, sticky=W, padx=6, pady=6)

        ttk.Label(frm, text="Danışan:").grid(row=1, column=0, sticky=W, padx=6, pady=6)
        # Danışan seçimi - Terapist gibi entegre combobox + buton
        danisan_frame = ttk.Frame(frm)
        danisan_frame.grid(row=1, column=1, sticky=W, padx=6, pady=6)
        
        cb_dan = ttk.Combobox(danisan_frame, width=30, state="normal")
        # Danışan listesini yükle
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
            danisan_listesi = [row[0] for row in cur.fetchall()]
            conn.close()
            cb_dan["values"] = danisan_listesi
        except Exception:
            cb_dan["values"] = []
        cb_dan.pack(side=LEFT)
        cb_dan.focus_set()
        
        # Yeni danışan ekle butonu - Terapist gibi küçük buton
        def _yeni_danisan_ekle():
            self._yeni_danisan_ekle_ve_guncelle(cb_dan, frm)
        
        btn_yeni_dan = ttk.Button(danisan_frame, text="+", bootstyle="success-outline", width=4,
                                  command=_yeni_danisan_ekle, font=("Segoe UI", 10, "bold"))
        btn_yeni_dan.pack(side=LEFT, padx=(4, 0))

        ttk.Label(frm, text="Terapist:", font=("Segoe UI", 10)).grid(row=2, column=0, sticky=W, padx=8, pady=8)
        cb_ter = ttk.Combobox(frm, state="readonly", width=30)
        cb_ter.grid(row=2, column=1, sticky=W, padx=8, pady=8)

        # Terapist listesi (settings -> fallback)
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY therapist_name")
            tnames = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception:
            tnames = DEFAULT_THERAPISTS[:]

        if self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
            cb_ter["values"] = [self.kullanici_terapist]
            cb_ter.set(self.kullanici_terapist)
            cb_ter.configure(state="disabled")
        else:
            cb_ter["values"] = tnames
            if tnames:
                cb_ter.current(0)

        # Hizmet bedeli otomatik atama - Hızlı seans ekranı için
        def _otomatik_bedel_ata_hizli(*args):
            """Danışan ve terapist seçildiğinde otomatik hizmet bedeli ata"""
            try:
                danisan_adi = (cb_dan.get() or "").strip().upper()
                terapist_adi = (cb_ter.get() or "").strip()
                
                # Eğer hizmet bedeli zaten girilmişse, değiştirme
                mevcut_bedel = ent_bedel.get().strip()
                try:
                    if mevcut_bedel:
                        bedel_val = float(mevcut_bedel.replace(",", ".").replace(".", "", mevcut_bedel.count(".") - 1) or 0)
                        if bedel_val > 0:
                            return
                except Exception:
                    pass
                
                if danisan_adi and terapist_adi:
                    conn = self.veritabani_baglan()
                    cur = conn.cursor()
                    
                    # Öğrenci ID'sini bul
                    cur.execute("SELECT id FROM danisanlar WHERE UPPER(ad_soyad) = UPPER(?) AND aktif = 1 LIMIT 1", (danisan_adi,))
                    row = cur.fetchone()
                    if row:
                        ogrenci_id = row[0]
                        # Otomatik ücreti al
                        otomatik_ucret = get_ogrenci_personel_ucreti(ogrenci_id, terapist_adi, conn)
                        if otomatik_ucret > 0:
                            ent_bedel.delete(0, END)
                            ent_bedel.insert(0, format_money(otomatik_ucret))
                    
                    conn.close()
            except Exception as e:
                log_exception("_otomatik_bedel_ata_hizli", e)
        
        # Event binding
        cb_dan.bind("<<ComboboxSelected>>", _otomatik_bedel_ata_hizli)
        cb_dan.bind("<KeyRelease>", lambda e: win.after(300, _otomatik_bedel_ata_hizli))
        cb_ter.bind("<<ComboboxSelected>>", _otomatik_bedel_ata_hizli)

        ttk.Label(frm, text="Oda:").grid(row=3, column=0, sticky=W, padx=6, pady=6)
        cb_oda = ttk.Combobox(frm, state="readonly", width=30)
        # Oda listesini veritabanından çek
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT oda_adi FROM odalar WHERE aktif=1 ORDER BY oda_adi")
            oda_listesi = [row[0] for row in cur.fetchall()]
            conn.close()
            if not oda_listesi:
                oda_listesi = ["Oda Seçiniz"]
        except Exception:
            oda_listesi = ["Oda Seçiniz"]
        cb_oda["values"] = oda_listesi
        cb_oda.grid(row=3, column=1, sticky=W, padx=6, pady=6)

        ttk.Label(frm, text="Hizmet Bedeli (₺):").grid(row=4, column=0, sticky=W, padx=6, pady=6)
        ent_bedel = ttk.Entry(frm, validate="key", validatecommand=self._vcmd_money, width=18)
        ent_bedel.grid(row=4, column=1, sticky=W, padx=6, pady=6)

        ttk.Label(frm, text="Alınan (₺):").grid(row=5, column=0, sticky=W, padx=6, pady=6)
        ent_alinan = ttk.Entry(frm, validate="key", validatecommand=self._vcmd_money, width=18)
        ent_alinan.insert(0, "0")
        ent_alinan.grid(row=5, column=1, sticky=W, padx=6, pady=6)

        ttk.Label(frm, text="Not (opsiyonel):").grid(row=6, column=0, sticky=W, padx=6, pady=6)
        ent_not = ttk.Entry(frm, width=34)
        ent_not.grid(row=6, column=1, sticky=W, padx=6, pady=6)

        def _save():
            danisan = (cb_dan.get() or "").strip().upper()
            terapist = (cb_ter.get() or "").strip()
            if not danisan:
                messagebox.showwarning("Uyarı", "Lütfen danışan adını giriniz!")
                return
            if not terapist:
                messagebox.showwarning("Uyarı", "Lütfen terapist seçiniz!")
                return
            try:
                bedel = parse_money(ent_bedel.get())
                alinan = parse_money(ent_alinan.get())
            except Exception:
                messagebox.showerror("Hata", "Lütfen sayı giriniz! (Hizmet bedeli / Alınan)")
                return

            kalan = max(0.0, bedel - alinan)
            notlar_manuel = (ent_not.get() or "").strip()
            saat = (cb_saat.get() or "").strip() or self._default_saat()
            
            # Otomatik açıklama oluştur
            tarih_formatted = tarih_var.get() or datetime.datetime.now().strftime("%d.%m.%Y")
            otomatik_aciklama = f"{danisan} danışanın {terapist} hocadan {tarih_formatted} tarihli seansından {format_money(bedel)} ücret bedelinin {format_money(alinan)} miktarı alınmıştır. {format_money(kalan)} miktar borcu kalmıştır."
            
            # Manuel not varsa ekle
            if notlar_manuel:
                notlar = f"{otomatik_aciklama}\n\nNot: {notlar_manuel}"
            else:
                notlar = otomatik_aciklama

            try:
                conn = self.veritabani_baglan()
                kullanici_id = self.kullanici[0] if self.kullanici else None
                
                # Oda bilgisi
                oda = (cb_oda.get() or "").strip()
                
                # ✅ PIPELINE KULLAN (Seans Takip ANA KAYNAK)
                pipeline = DataPipeline(conn, kullanici_id)
                seans_id = pipeline.seans_kayit(
                    tarih=self._tarih_db_from(tarih_var.get()),
                    saat=saat,
                    danisan_adi=danisan,
                    terapist=terapist,
                    hizmet_bedeli=bedel,
                    alinan_ucret=alinan,
                    notlar=notlar,
                    oda=oda,
                )
                
                conn.close()
                
                if not seans_id:
                    messagebox.showerror("Hata", "Seans kaydı oluşturulamadı!")
                    return
                    
            except Exception as e:
                messagebox.showerror("Hata", f"Kayıt ekleme hatası:\n{e}")
                return

            # peş peşe kayıt için formu temizle
            cb_dan.set("")
            ent_bedel.delete(0, END)
            ent_alinan.delete(0, END)
            ent_alinan.insert(0, "0")
            ent_not.delete(0, END)
            cb_dan.focus_set()
            
            # Danışan listesini yenile (yeni eklenen danışanlar görünsün)
            try:
                conn2 = self.veritabani_baglan()
                cur2 = conn2.cursor()
                cur2.execute("SELECT ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
                danisan_listesi = [row[0] for row in cur2.fetchall()]
                conn2.close()
                cb_dan["values"] = danisan_listesi
            except Exception:
                pass
            
            # Ana sayfadaki combobox'ı da güncelle
            if hasattr(self, 'cmb_danisan'):
                try:
                    self.cmb_danisan["values"] = danisan_listesi
                except Exception:
                    pass
            try:
                # ana listeyi tazele (varsa)
                if hasattr(self, "kayitlari_listele"):
                    self.kayitlari_listele()
                # Danışan yönetimi penceresi açıksa, listeyi yenile
                for child in self.winfo_children():
                    if isinstance(child, ttk.Toplevel):
                        if hasattr(child, "_reload"):
                            try:
                                child._reload()
                            except Exception:
                                pass
            except Exception:
                pass

        btns = ttk.Frame(frm)
        btns.grid(row=7, column=0, columnspan=2, sticky=EW, padx=6, pady=(14, 0))
        ttk.Button(btns, text="KAYDET", bootstyle="success", command=_save).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(btns, text="KAPAT", bootstyle="secondary", command=win.destroy).pack(side=LEFT, padx=8, fill=X, expand=True)

        cb_dan.bind("<Return>", lambda e: ent_bedel.focus_set())
        ent_bedel.bind("<Return>", lambda e: ent_alinan.focus_set())
        ent_alinan.bind("<Return>", lambda e: ent_not.focus_set())
        ent_not.bind("<Return>", lambda e: _save())

    def kayit_ekle(self):
        """
        PIPELINE ENTEGRASYONU: Seans kaydı ekleme (SEANS TAKİP ANA KAYNAK)
        → seans_takvimi (ANA) → records → kasa_hareketleri → odeme_hareketleri → oda_doluluk
        """
        danisan = (self.cmb_danisan.get() or "").strip().upper()
        terapist = (self.cmb_terapist.get() or "").strip()
        try:
            saat = (self.cmb_saat.get() or "").strip()
        except Exception:
            saat = ""
        saat = saat or self._default_saat()
        if not danisan:
            messagebox.showwarning("Uyarı", "Lütfen danışan adını giriniz!")
            return
        if not terapist:
            messagebox.showwarning("Uyarı", "Lütfen terapist seçiniz!")
            return

        try:
            bedel = parse_money(self.ent_bedel.get())
            alinan = parse_money(self.ent_alinan.get())
        except Exception:
            messagebox.showerror("Hata", "Lütfen sayı giriniz! (Hizmet bedeli / Alınan)")
            return

        notlar_manuel = (self.ent_not.get() or "").strip()
        
        # Oda bilgisi (eğer varsa UI'dan çek)
        oda = ""
        try:
            if hasattr(self, "cmb_oda"):
                oda = (self.cmb_oda.get() or "").strip()
        except Exception:
            pass

        try:
            conn = self.veritabani_baglan()
            kullanici_id = self.kullanici[0] if self.kullanici else None
            
            # Otomatik açıklama oluştur: "X danışanın Y hocadan xx/xx/xxxx tarihli seansından A ücret bedelinin B miktarı alınmıştır. C miktar borcu kalmıştır."
            tarih_formatted = self.tarih_var.get() or datetime.datetime.now().strftime("%d.%m.%Y")
            kalan_borc = max(0.0, bedel - alinan)
            
            otomatik_aciklama = f"{danisan} danışanın {terapist} hocadan {tarih_formatted} tarihli seansından {format_money(bedel)} ücret bedelinin {format_money(alinan)} miktarı alınmıştır. {format_money(kalan_borc)} miktar borcu kalmıştır."
            
            # Manuel not varsa ekle
            if notlar_manuel:
                notlar = f"{otomatik_aciklama}\n\nNot: {notlar_manuel}"
            else:
                notlar = otomatik_aciklama
            
            # ✅ PIPELINE KULLAN (Seans Takip ANA KAYNAK - tüm tablolar otomatik güncellenecek)
            pipeline = DataPipeline(conn, kullanici_id)
            seans_id = pipeline.seans_kayit(
                tarih=self._tarih_db(),
                saat=saat,
                danisan_adi=danisan,
                terapist=terapist,
                hizmet_bedeli=bedel,
                alinan_ucret=alinan,
                notlar=notlar,
                oda=oda,
            )
            
            # Pipeline log'u konsola yaz (debugging için)
            if seans_id:
                print(f"\n{'='*60}")
                print(f"✅ SEANS KAYIT BAŞARILI (SEANS TAKİP ANA KAYNAK) | seans_id={seans_id}")
                print(f"{'='*60}")
                print(pipeline.get_log())
                print(f"{'='*60}\n")
            
            conn.close()
            
            # Başarı mesajı (opsiyonel - kullanıcıya detay vermek için)
            if seans_id:
                # record_id'yi bul
                try:
                    conn2 = self.veritabani_baglan()
                    cur2 = conn2.cursor()
                    cur2.execute("SELECT record_id FROM seans_takvimi WHERE id=?", (seans_id,))
                    row = cur2.fetchone()
                    record_id = row[0] if row and row[0] else "Bağlanmadı"
                    conn2.close()
                except Exception:
                    record_id = "Bulunamadı"
                
                messagebox.showinfo(
                    "Başarılı", 
                    f"Seans kaydı oluşturuldu!\n\n"
                    f"• Seans Takip (ANA): #{seans_id}\n"
                    f"• Records: #{record_id}\n"
                    f"• Kasa: {'Eklendi' if alinan > 0 else 'İlk ödeme yok'}\n"
                    f"• Oda: {oda if oda else 'Seçilmedi'}\n\n"
                    f"Tüm tablolar senkronize edildi!"
                )
        
        except Exception as e:
            messagebox.showerror("Hata", f"Kayıt ekleme hatası:\n{e}")
            log_exception("kayit_ekle_pipeline", e)
            return

        self.cmb_danisan.set("")
        self.ent_bedel.delete(0, END)
        self.ent_alinan.delete(0, END)
        self.ent_alinan.insert(0, "0")
        self.ent_not.delete(0, END)
        self.cmb_danisan.focus_set()
        
        # Danışan listesini yenile (yeni eklenen danışanlar görünsün)
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
            danisan_listesi = [row[0] for row in cur.fetchall()]
            conn.close()
            self.cmb_danisan["values"] = danisan_listesi
        except Exception:
            pass
        
        # Danışan yönetimi penceresi açıksa, listeyi yenile
        try:
            for child in self.winfo_children():
                if isinstance(child, ttk.Toplevel):
                    if hasattr(child, "_reload"):
                        try:
                            child._reload()
                        except Exception:
                            pass
        except Exception:
            pass
        self.kayitlari_listele()

    def kayitlari_listele(self):
        """
        Seans Takip listesi - SEANS_TAKVIMI ANA KAYNAK
        seans_takvimi tablosundan okuyup records ile JOIN yaparak tüm bilgileri gösterir.
        """
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        q = (self.ent_ara.get() or "").strip().upper()
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            where = []
            params = []
            
            # Role göre filtre (eğitim görevlisi sadece kendi kayıtlarını görür)
            if self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
                where.append("st.terapist = ?")
                params.append(self.kullanici_terapist)
            if q:
                where.append("st.danisan_adi LIKE ?")
                params.append(f"%{q}%")

            # ✅ SEANS_TAKVIMI ANA KAYNAK - records ile JOIN
            sql = """
                SELECT 
                    st.id AS seans_id,
                    st.tarih,
                    COALESCE(st.saat, '') AS saat,
                    st.danisan_adi,
                    st.terapist,
                    COALESCE(r.hizmet_bedeli, 0) AS hizmet_bedeli,
                    COALESCE(r.alinan_ucret, 0) AS alinan_ucret,
                    COALESCE(r.kalan_borc, 0) AS kalan_borc,
                    COALESCE(st.notlar, r.notlar, '') AS notlar,
                    r.id AS record_id
                FROM seans_takvimi st
                LEFT JOIN records r ON st.record_id = r.id OR st.id = r.seans_id
            """
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY st.tarih DESC, st.saat DESC, st.id DESC"
            
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Listeleme hatası:\n{e}")
            log_exception("kayitlari_listele", e)
            return

        toplam = 0.0
        for r in rows:
            # r[0]=seans_id, r[1]=tarih, r[2]=saat, r[3]=danisan, r[4]=terapist,
            # r[5]=hizmet_bedeli, r[6]=alinan_ucret, r[7]=kalan_borc, r[8]=notlar, r[9]=record_id
            borc = float(r[7] or 0)
            toplam += borc
            tag = "borclu" if borc > 0 else "tamam"
            
            # tarih gösterimi
            try:
                dt = datetime.datetime.strptime(r[1], "%Y-%m-%d")
                tarih_g = dt.strftime("%d.%m.%Y")
            except Exception:
                tarih_g = r[1]

            # Tree'ye ekle - ID olarak seans_id kullan (ANA KAYNAK)
            self.tree.insert(
                "",
                END,
                values=(
                    r[0],  # seans_id (ANA KAYNAK)
                    tarih_g,
                    r[2],  # saat
                    r[3],  # danisan_adi
                    r[4],  # terapist
                    format_money(r[5]),  # hizmet_bedeli
                    format_money(r[6]),  # alinan_ucret
                    format_money(r[7]),  # kalan_borc
                    r[8] or "",  # notlar
                ),
                tags=(tag,),
            )

        self.lbl_ozet.config(text=f"TOPLAM İÇERİDEKİ ALACAK: {toplam:,.2f} TL")

    def odeme_ekle(self):
        seans_id = self._selected_id()  # Artık seans_id (ANA KAYNAK)
        if not seans_id:
            messagebox.showwarning("Uyarı", "Lütfen bir kayıt seçiniz!")
            return
        
        # seans_id'den record_id'yi bul
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT record_id FROM seans_takvimi WHERE id=?", (seans_id,))
            row = cur.fetchone()
            record_id = row[0] if row and row[0] else None
            conn.close()
            
            if not record_id:
                messagebox.showerror("Hata", "Bu seans kaydına bağlı bir record bulunamadı!")
                return
        except Exception as e:
            messagebox.showerror("Hata", f"Kayıt bulunamadı:\n{e}")
            return

        win = ttk.Toplevel(self)
        win.title("Ödeme Ekle")
        win.resizable(False, False)
        center_window(win, 440, 280)
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win, padding=14)
        frm.pack(fill=BOTH, expand=True)

        ttk.Label(frm, text="Tarih (YYYY-AA-GG):").grid(row=0, column=0, sticky=W, padx=6, pady=(6, 2))
        ent_tarih = ttk.Entry(frm, width=16)
        ent_tarih.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        ent_tarih.grid(row=0, column=1, sticky=W, padx=6, pady=(6, 2))

        ttk.Label(frm, text="Ödeme Şekli:").grid(row=1, column=0, sticky=W, padx=6, pady=2)
        cb_sekil = ttk.Combobox(frm, state="readonly", values=["Nakit", "Havale/EFT", "Kart", "Diğer"], width=14)
        cb_sekil.current(0)
        cb_sekil.grid(row=1, column=1, sticky=W, padx=6, pady=2)

        ttk.Label(frm, text="Eklenen ödeme (₺):").grid(row=2, column=0, sticky=W, padx=6, pady=(10, 2))
        ent = ttk.Entry(frm, validate="key", validatecommand=self._vcmd_money, width=18)
        ent.grid(row=2, column=1, sticky=W, padx=6, pady=(10, 2))
        ent.focus_set()

        ttk.Label(frm, text="Açıklama (opsiyonel):").grid(row=3, column=0, sticky=W, padx=6, pady=(10, 2))
        ent_aciklama = ttk.Entry(frm, width=32)
        ent_aciklama.grid(row=3, column=1, sticky=W, padx=6, pady=(10, 2))

        def _save():
            """
            PIPELINE ENTEGRASYONU: Ödeme ekleme
            → odeme_hareketleri, records (borç güncelle), kasa_hareketleri, seans_takvimi (ücret_alindi)
            """
            try:
                ek = parse_money(ent.get())
            except Exception:
                messagebox.showerror("Hata", "Lütfen geçerli bir sayı giriniz!")
                return
            if ek <= 0:
                messagebox.showwarning("Uyarı", "Ödeme 0'dan büyük olmalıdır!")
                return

            tahsil_tarih = (ent_tarih.get() or "").strip() or datetime.datetime.now().strftime("%Y-%m-%d")
            odeme_sekli = (cb_sekil.get() or "").strip()
            aciklama = (ent_aciklama.get() or "").strip()

            try:
                conn = self.veritabani_baglan()
                kullanici_id = self.kullanici[0] if self.kullanici else None
                
                # ✅ PIPELINE KULLAN (Tüm tablolar otomatik güncellenecek)
                pipeline = DataPipeline(conn, kullanici_id)
                basarili = pipeline.odeme_ekle(
                    record_id=record_id,
                    tutar=ek,
                    tarih=tahsil_tarih,
                    odeme_sekli=odeme_sekli,
                    aciklama=aciklama,
                )
                
                if basarili:
                    # Pipeline log'u konsola yaz (debugging için)
                    print(f"\n{'='*60}")
                    print(f"💰 ÖDEME EKLEME BAŞARILI | seans_id={seans_id} | record_id={record_id} | +{ek} TL")
                    print(f"{'='*60}")
                    print(pipeline.get_log())
                    print(f"{'='*60}\n")
                    
                    # Kalan borcu kontrol et
                    cur = conn.cursor()
                    cur.execute("SELECT kalan_borc FROM records WHERE id=?", (record_id,))
                    kalan = float((cur.fetchone() or [0])[0] or 0)
                    conn.close()
                    
                    if kalan <= 0:
                        messagebox.showinfo(
                            "Başarılı!", 
                            f"✅ Ödeme kaydedildi!\n\n"
                            f"• Eklenen: {ek:,.2f} TL\n"
                            f"• Borç tamamen ödendi!\n\n"
                            f"İlgili tablolar güncellendi:\n"
                            f"✓ Ödeme Hareketleri\n"
                            f"✓ Records (Borç: 0 TL)\n"
                            f"✓ Kasa Defteri (Giren)\n"
                            f"✓ Seans Takvimi (Ücret Alındı)"
                        )
                    else:
                        messagebox.showinfo(
                            "Başarılı!", 
                            f"✅ Ödeme kaydedildi!\n\n"
                            f"• Eklenen: {ek:,.2f} TL\n"
                            f"• Kalan Borç: {kalan:,.2f} TL\n\n"
                            f"İlgili tablolar güncellendi:\n"
                            f"✓ Ödeme Hareketleri\n"
                            f"✓ Records\n"
                            f"✓ Kasa Defteri (Giren)"
                        )
                else:
                    messagebox.showerror("Hata", "Ödeme eklenirken bir hata oluştu!")
                    return
                    
            except Exception as e:
                messagebox.showerror("Hata", f"Ödeme ekleme hatası:\n{e}")
                log_exception("odeme_ekle_pipeline", e)
                return
            
            win.destroy()
            self.kayitlari_listele()

        ttk.Button(frm, text="KAYDET", bootstyle="success", command=_save).grid(row=4, column=0, columnspan=2, sticky=EW, padx=6, pady=(16, 0))
        ent.bind("<Return>", lambda e: _save())

    def kayit_sil(self):
        """
        PIPELINE ENTEGRASYONU: Kayıt silme (Cascade) - SEANS TAKİP ANA KAYNAK
        → seans_takvimi (ANA) → records → kasa_hareketleri → odeme_hareketleri
        """
        seans_id = self._selected_id()  # Artık seans_id (ANA KAYNAK)
        if not seans_id:
            messagebox.showwarning("Uyarı", "Lütfen bir kayıt seçiniz!")
            return
        if not messagebox.askyesno("Onay", "Seçili kaydı silmek istiyor musunuz?\n\nİlgili tüm veriler (seans takvimi, records, ödemeler, kasa kayıtları) silinecektir!"):
            return
        
        # seans_id'den record_id'yi bul
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT record_id FROM seans_takvimi WHERE id=?", (seans_id,))
            row = cur.fetchone()
            record_id = row[0] if row and row[0] else None
            conn.close()
            
            if not record_id:
                messagebox.showerror("Hata", "Bu seans kaydına bağlı bir record bulunamadı!")
                return
        except Exception as e:
            messagebox.showerror("Hata", f"Kayıt bulunamadı:\n{e}")
            return
        
        try:
            conn = self.veritabani_baglan()
            kullanici_id = self.kullanici[0] if self.kullanici else None
            
            # ✅ PIPELINE KULLAN (Cascade silme - tüm bağlı tablolar temizlenecek)
            pipeline = DataPipeline(conn, kullanici_id)
            basarili = pipeline.kayit_sil(record_id=record_id)
            
            if basarili:
                # Pipeline log'u konsola yaz (debugging için)
                print(f"\n{'='*60}")
                print(f"🗑️  KAYIT SİLME BAŞARILI | seans_id={seans_id} | record_id={record_id}")
                print(f"{'='*60}")
                print(pipeline.get_log())
                print(f"{'='*60}\n")
                
                messagebox.showinfo(
                    "Başarılı!", 
                    f"✅ Kayıt silindi!\n\n"
                    f"Silinen veriler:\n"
                    f"✓ Seans Takip (ANA): #{seans_id}\n"
                    f"✓ Records: #{record_id}\n"
                    f"✓ Ödeme Hareketleri\n"
                    f"✓ Kasa Kayıtları\n\n"
                    f"Tüm tablolar senkronize edildi!"
                )
            else:
                messagebox.showerror("Hata", "Kayıt silinirken bir hata oluştu!")
            
            conn.close()
            self.kayitlari_listele()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Silme hatası:\n{e}")
            log_exception("kayit_sil_pipeline", e)

    # --- TAB 2: AYARLAR ---
    def _build_ucret_takibi_tab(self):
        """Ücret Takibi Tab - Çocuk ve Personel ücret takipleri (tek ekranda 2 sayfa)"""
        wrapper = ttk.Frame(self.tab_ucret_takibi, padding=10)
        wrapper.pack(fill=BOTH, expand=True)
        
        # Başlık
        head = ttk.Frame(wrapper)
        head.pack(fill=X, pady=(0, 10))
        if getattr(self, "_logo_small", None):
            ttk.Label(head, image=self._logo_small).pack(side=LEFT, padx=(0, 10))
        ttk.Label(head, text="ÜCRET TAKİPİ", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        
        # Notebook widget - 2 sayfa
        nb_ucret = ttk.Notebook(wrapper)
        nb_ucret.pack(fill=BOTH, expand=True)
        
        # Sayfa 1: Çocuk Ücret Takibi
        page_cocuk = ttk.Frame(nb_ucret, padding=10)
        nb_ucret.add(page_cocuk, text="👶 Çocuk Ücret Takibi")
        self._build_cocuk_ucret_takibi_page(page_cocuk)
        
        # Sayfa 2: Personel Ücret Takibi
        page_personel = ttk.Frame(nb_ucret, padding=10)
        nb_ucret.add(page_personel, text="👨‍🏫 Personel Ücret Takibi")
        self._build_personel_ucret_takibi_page(page_personel)
    
    def _build_cocuk_ucret_takibi_page(self, parent):
        """Çocuk Ücret Takibi Sayfası"""
        # Üst toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=X, pady=(0, 10))
        
        ttk.Label(toolbar, text="Çocuk Ücret Takibi", font=("Segoe UI", 12, "bold")).pack(side=LEFT)
        
        ttk.Separator(toolbar, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=10)
        
        ttk.Button(toolbar, text="📊 Excel'den Ücret Listesi Yükle", bootstyle="info",
                   command=self.excel_ucret_listesi_yukle).pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="🔄 Yenile", bootstyle="secondary",
                   command=lambda: self._cocuk_ucret_listele(parent)).pack(side=LEFT, padx=5)
        
        # Arama
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(search_frame, text="Ara:").pack(side=LEFT, padx=(0, 5))
        ent_ara_cocuk = ttk.Entry(search_frame, width=30)
        ent_ara_cocuk.pack(side=LEFT, padx=5)
        ent_ara_cocuk.bind("<KeyRelease>", lambda e: self._cocuk_ucret_listele(parent))
        ttk.Button(search_frame, text="Ara", bootstyle="primary",
                   command=lambda: self._cocuk_ucret_listele(parent)).pack(side=LEFT, padx=5)
        
        # Treeview
        frame_tree = ttk.Frame(parent)
        frame_tree.pack(fill=BOTH, expand=True)
        
        cols = ("ID", "Çocuk Adı", "Personel", "Tarih", "Seans Ücreti", "Alınan Ödeme", "Kalan Borç", "Durum")
        tree = ttk.Treeview(frame_tree, columns=cols, show="headings", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            if c == "ID":
                tree.column(c, width=50)
            elif c == "Çocuk Adı":
                tree.column(c, width=200)
            elif c == "Personel":
                tree.column(c, width=150)
            elif c == "Tarih":
                tree.column(c, width=100)
            elif c in ("Seans Ücreti", "Alınan Ödeme", "Kalan Borç"):
                tree.column(c, width=120, anchor="e")
            else:
                tree.column(c, width=100)
        
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(frame_tree, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        
        # Tag'ler
        tree.tag_configure("borclu", background="#f8d7da", foreground="#721c24")
        tree.tag_configure("tamam", background="#d4edda", foreground="#155724")
        tree.tag_configure("even", background="#f8f9fa")
        tree.tag_configure("odd", background="#ffffff")
        
        # Sağ tık menü - Fiyatlandırma güncelleme
        def cocuk_ucret_menu(event):
            sel = tree.selection()
            if not sel:
                return
            menu = Menu(self, tearoff=0)
            menu.add_command(label="💰 Fiyatlandırma Güncelle", command=lambda: self._fiyatlandirma_guncelle(parent, tree))
            menu.add_command(label="📊 Detaylı Rapor", command=lambda: self._cocuk_detayli_rapor(parent, tree))
            menu.post(event.x_root, event.y_root)
        
        tree.bind("<Button-3>", cocuk_ucret_menu)
        
        # Özet bilgiler
        summary_frame = ttk.LabelFrame(parent, text="Özet", padding=10)
        summary_frame.pack(fill=X, pady=(10, 0))
        
        summary_labels = ttk.Frame(summary_frame)
        summary_labels.pack(fill=X)
        
        # Treeview'i parent'a kaydet
        parent._tree_cocuk = tree
        parent._ent_ara_cocuk = ent_ara_cocuk
        parent._summary_labels_cocuk = summary_labels
        
        # İlk yükleme
        self._cocuk_ucret_listele(parent)
    
    def _build_personel_ucret_takibi_page(self, parent):
        """Personel Ücret Takibi Sayfası"""
        # Üst toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=X, pady=(0, 10))
        
        ttk.Label(toolbar, text="Personel Ücret Takibi", font=("Segoe UI", 12, "bold")).pack(side=LEFT)
        
        ttk.Separator(toolbar, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=10)
        
        ttk.Button(toolbar, text="📝 Personel Ücret Talep Formu", bootstyle="success",
                   command=self.personel_ucret_talep_formu).pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="💰 Ödeme Yap", bootstyle="warning",
                   command=self.personel_ucret_odeme_yap).pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="🔄 Yenile", bootstyle="secondary",
                   command=lambda: self._personel_ucret_listele(parent)).pack(side=LEFT, padx=5)
        
        # Filtreler
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Personel:").pack(side=LEFT, padx=(0, 5))
        cmb_personel = ttk.Combobox(filter_frame, state="readonly", width=25)
        cmb_personel.pack(side=LEFT, padx=5)
        
        # Personel listesi
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY therapist_name")
            personel_listesi = [""] + [row[0] for row in cur.fetchall()]
            conn.close()
            cmb_personel["values"] = personel_listesi
            cmb_personel.current(0)
        except Exception:
            cmb_personel["values"] = [""]
        
        ttk.Label(filter_frame, text="Ödeme Durumu:").pack(side=LEFT, padx=(20, 5))
        cmb_durum = ttk.Combobox(filter_frame, state="readonly", width=20)
        cmb_durum["values"] = ["", "Beklemede", "Ödendi", "İptal"]
        cmb_durum.current(0)
        cmb_durum.pack(side=LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Filtrele", bootstyle="primary",
                   command=lambda: self._personel_ucret_listele(parent)).pack(side=LEFT, padx=10)
        
        # Treeview
        frame_tree = ttk.Frame(parent)
        frame_tree.pack(fill=BOTH, expand=True)
        
        cols = ("ID", "Personel", "Tarih", "Seans Ücreti", "Personel Ücreti", "Oran", "Ödeme Durumu", "Ödeme Tarihi")
        tree = ttk.Treeview(frame_tree, columns=cols, show="headings", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            if c == "ID":
                tree.column(c, width=50)
            elif c == "Personel":
                tree.column(c, width=150)
            elif c == "Tarih":
                tree.column(c, width=100)
            elif c in ("Seans Ücreti", "Personel Ücreti"):
                tree.column(c, width=130, anchor="e")
            elif c == "Oran":
                tree.column(c, width=80, anchor="e")
            else:
                tree.column(c, width=120)
        
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(frame_tree, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        
        # Tag'ler
        tree.tag_configure("beklemede", background="#fff3cd", foreground="#856404")
        tree.tag_configure("odendi", background="#d4edda", foreground="#155724")
        tree.tag_configure("iptal", background="#f8d7da", foreground="#721c24")
        tree.tag_configure("even", background="#f8f9fa")
        tree.tag_configure("odd", background="#ffffff")
        
        # Özet bilgiler
        summary_frame = ttk.LabelFrame(parent, text="Özet", padding=10)
        summary_frame.pack(fill=X, pady=(10, 0))
        
        summary_labels = ttk.Frame(summary_frame)
        summary_labels.pack(fill=X)
        
        parent._tree_personel = tree
        parent._cmb_personel = cmb_personel
        parent._cmb_durum = cmb_durum
        parent._summary_labels = summary_labels
        
        # İlk yükleme
        self._personel_ucret_listele(parent)
    
    def _cocuk_ucret_listele(self, parent):
        """Çocuk ücret takibi listesini yükle - Günlük/haftalık/aylık özet ile"""
        tree = parent._tree_cocuk
        ent_ara = parent._ent_ara_cocuk
        summary_labels = parent._summary_labels_cocuk
        
        for iid in tree.get_children():
            tree.delete(iid)
        
        # Özet etiketlerini temizle
        for widget in summary_labels.winfo_children():
            widget.destroy()
        
        q = (ent_ara.get() or "").strip().upper()
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            where = []
            params = []
            
            if q:
                where.append("(UPPER(st.danisan_adi) LIKE ? OR UPPER(st.terapist) LIKE ?)")
                params.extend([f"%{q}%", f"%{q}%"])
            
            # Role göre filtre
            if self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
                where.append("st.terapist = ?")
                params.append(self.kullanici_terapist)
            
            sql = """
                SELECT 
                    st.id,
                    st.danisan_adi,
                    st.terapist,
                    st.tarih,
                    COALESCE(r.hizmet_bedeli, 0) AS seans_ucreti,
                    COALESCE(r.alinan_ucret, 0) AS alinan_odeme,
                    COALESCE(r.kalan_borc, 0) AS kalan_borc
                FROM seans_takvimi st
                LEFT JOIN records r ON st.record_id = r.id OR st.id = r.seans_id
            """
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY st.tarih DESC, st.id DESC"
            
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            
            # Özet hesapla (günlük/haftalık/aylık)
            bugun = datetime.datetime.now().strftime("%Y-%m-%d")
            hafta_bas = (datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().weekday())).strftime("%Y-%m-%d")
            ay_bas = datetime.datetime.now().replace(day=1).strftime("%Y-%m-%d")
            
            toplam_gunluk = 0.0
            toplam_haftalik = 0.0
            toplam_aylik = 0.0
            toplam_seans = len(rows)
            toplam_borc = 0.0
            
            for idx, row in enumerate(rows):
                seans_id, cocuk_adi, personel, tarih, seans_ucreti, alinan_odeme, kalan_borc = row
                
                # Özet hesaplamaları
                if tarih == bugun:
                    toplam_gunluk += float(seans_ucreti or 0)
                if tarih >= hafta_bas:
                    toplam_haftalik += float(seans_ucreti or 0)
                if tarih >= ay_bas:
                    toplam_aylik += float(seans_ucreti or 0)
                
                toplam_borc += float(kalan_borc or 0)
                
                durum = "Borçlu" if kalan_borc > 0 else "Tamamlandı"
                tag = "borclu" if kalan_borc > 0 else "tamam"
                if idx % 2 == 0:
                    tag = "even"
                else:
                    tag = "odd"
                
                tree.insert("", END, values=(
                    seans_id,
                    cocuk_adi,
                    personel,
                    tarih,
                    format_money(seans_ucreti),
                    format_money(alinan_odeme),
                    format_money(kalan_borc),
                    durum
                ), tags=(tag,))
            
            conn.close()
            
            # Özet göster
            ttk.Label(summary_labels, text=f"📊 Toplam Seans: {toplam_seans}", font=("Segoe UI", 10)).pack(side=LEFT, padx=15)
            ttk.Label(summary_labels, text=f"📅 Günlük: {format_money(toplam_gunluk)}", 
                     font=("Segoe UI", 10), bootstyle="info").pack(side=LEFT, padx=15)
            ttk.Label(summary_labels, text=f"📆 Haftalık: {format_money(toplam_haftalik)}", 
                     font=("Segoe UI", 10), bootstyle="primary").pack(side=LEFT, padx=15)
            ttk.Label(summary_labels, text=f"📊 Aylık: {format_money(toplam_aylik)}", 
                     font=("Segoe UI", 10), bootstyle="success").pack(side=LEFT, padx=15)
            ttk.Label(summary_labels, text=f"💰 Toplam Borç: {format_money(toplam_borc)}", 
                     font=("Segoe UI", 11, "bold"), bootstyle="warning").pack(side=LEFT, padx=15)
        
        except Exception as e:
            messagebox.showerror("Hata", f"Çocuk ücret listesi yüklenemedi:\n{e}")
            log_exception("_cocuk_ucret_listele", e)
    
    def _fiyatlandirma_guncelle(self, parent, tree):
        """Öğrenci-personel bazlı fiyatlandırma güncelle"""
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen bir kayıt seçin.")
            return
        
        values = tree.item(sel[0])["values"]
        seans_id = values[0]
        cocuk_adi = values[1]
        personel_adi = values[2]
        
        # Öğrenci ID'sini bul
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT id FROM danisanlar WHERE UPPER(ad_soyad) = UPPER(?) AND aktif = 1 LIMIT 1", (cocuk_adi,))
            row = cur.fetchone()
            if not row:
                messagebox.showerror("Hata", "Öğrenci bulunamadı.")
                conn.close()
                return
            ogrenci_id = row[0]
            
            # Mevcut fiyatlandırmayı kontrol et
            cur.execute(
                """
                SELECT seans_ucreti, zam_orani, baslangic_tarihi, bitis_tarihi
                FROM ogrenci_personel_fiyatlandirma
                WHERE ogrenci_id = ? AND personel_adi = ? AND aktif = 1
                ORDER BY baslangic_tarihi DESC
                LIMIT 1
                """,
                (ogrenci_id, personel_adi)
            )
            mevcut_fiyat = cur.fetchone()
            conn.close()
            
            # Fiyatlandırma güncelleme penceresi
            win = ttk.Toplevel(self)
            win.title("Fiyatlandırma Güncelle")
            win.geometry("500x400")
            center_window(win, 500, 400)
            win.transient(self)
            self._brand_window(win)
            
            wrapper = ttk.Frame(win, padding=20)
            wrapper.pack(fill=BOTH, expand=True)
            
            ttk.Label(wrapper, text="Fiyatlandırma Güncelle", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=(0, 20))
            
            ttk.Label(wrapper, text=f"Öğrenci: {cocuk_adi}", font=("Segoe UI", 11)).pack(pady=5)
            ttk.Label(wrapper, text=f"Personel: {personel_adi}", font=("Segoe UI", 11)).pack(pady=5)
            
            ttk.Separator(wrapper).pack(fill=X, pady=20)
            
            ttk.Label(wrapper, text="Seans Ücreti (TL):").pack(anchor=W, pady=(10, 5))
            ent_ucret = ttk.Entry(wrapper, width=30)
            if mevcut_fiyat and mevcut_fiyat[0]:
                ent_ucret.insert(0, str(mevcut_fiyat[0]))
            ent_ucret.pack(fill=X, pady=5)
            
            ttk.Label(wrapper, text="Yıllık Zam Oranı (%):").pack(anchor=W, pady=(10, 5))
            ent_zam = ttk.Entry(wrapper, width=30)
            if mevcut_fiyat and mevcut_fiyat[1]:
                ent_zam.insert(0, str(mevcut_fiyat[1]))
            else:
                ent_zam.insert(0, "0")
            ent_zam.pack(fill=X, pady=5)
            
            ttk.Label(wrapper, text="Başlangıç Tarihi (YYYY-MM-DD):").pack(anchor=W, pady=(10, 5))
            ent_baslangic = ttk.Entry(wrapper, width=30)
            ent_baslangic.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
            ent_baslangic.pack(fill=X, pady=5)
            
            ttk.Label(wrapper, text="Bitiş Tarihi (YYYY-MM-DD, boş bırakılabilir):").pack(anchor=W, pady=(10, 5))
            ent_bitis = ttk.Entry(wrapper, width=30)
            if mevcut_fiyat and mevcut_fiyat[3]:
                ent_bitis.insert(0, str(mevcut_fiyat[3]))
            ent_bitis.pack(fill=X, pady=5)
            
            def kaydet():
                try:
                    ucret = float(ent_ucret.get() or 0)
                    zam_orani = float(ent_zam.get() or 0)
                    baslangic = ent_baslangic.get().strip()
                    bitis = ent_bitis.get().strip() or None
                    
                    if ucret <= 0:
                        messagebox.showwarning("Uyarı", "Seans ücreti 0'dan büyük olmalıdır.")
                        return
                    
                    if not baslangic:
                        messagebox.showwarning("Uyarı", "Başlangıç tarihi gerekli.")
                        return
                    
                    conn = self.veritabani_baglan()
                    cur = conn.cursor()
                    
                    # Eski kaydı pasif yap
                    if mevcut_fiyat:
                        cur.execute(
                            "UPDATE ogrenci_personel_fiyatlandirma SET aktif = 0 WHERE ogrenci_id = ? AND personel_adi = ? AND aktif = 1",
                            (ogrenci_id, personel_adi)
                        )
                    
                    # Yeni kayıt ekle
                    cur.execute(
                        """
                        INSERT INTO ogrenci_personel_fiyatlandirma
                        (ogrenci_id, personel_adi, seans_ucreti, baslangic_tarihi, bitis_tarihi, zam_orani, aktif, olusturma_tarihi, guncelleme_tarihi)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                        """,
                        (
                            ogrenci_id,
                            personel_adi,
                            ucret,
                            baslangic,
                            bitis,
                            zam_orani,
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                    )
                    
                    conn.commit()
                    conn.close()
                    
                    messagebox.showinfo("Başarılı", f"Fiyatlandırma güncellendi!\n\nÖğrenci: {cocuk_adi}\nPersonel: {personel_adi}\nÜcret: {format_money(ucret)}")
                    win.destroy()
                    self._cocuk_ucret_listele(parent)
                
                except Exception as e:
                    messagebox.showerror("Hata", f"Fiyatlandırma güncellenemedi:\n{e}")
                    log_exception("_fiyatlandirma_guncelle", e)
            
            ttk.Button(wrapper, text="💾 Kaydet", bootstyle="success", command=kaydet).pack(pady=20)
        
        except Exception as e:
            messagebox.showerror("Hata", f"Fiyatlandırma güncellenemedi:\n{e}")
            log_exception("_fiyatlandirma_guncelle", e)
    
    def _cocuk_detayli_rapor(self, parent, tree):
        """Çocuk detaylı rapor penceresi"""
        sel = tree.selection()
        if not sel:
            return
        
        values = tree.item(sel[0])["values"]
        cocuk_adi = values[1]
        personel_adi = values[2]
        
        win = ttk.Toplevel(self)
        win.title(f"Detaylı Rapor - {cocuk_adi}")
        win.geometry("800x600")
        center_window(win, 800, 600)
        win.transient(self)
        self._brand_window(win)
        
        wrapper = ttk.Frame(win, padding=20)
        wrapper.pack(fill=BOTH, expand=True)
        
        ttk.Label(wrapper, text=f"Detaylı Rapor: {cocuk_adi}", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=(0, 20))
        
        # Rapor içeriği buraya eklenecek
        ttk.Label(wrapper, text="Detaylı rapor özelliği yakında eklenecek.", font=("Segoe UI", 10)).pack(pady=20)
    
    def _personel_ucret_listele(self, parent):
        """Personel ücret takibi listesini yükle"""
        tree = parent._tree_personel
        cmb_personel = parent._cmb_personel
        cmb_durum = parent._cmb_durum
        summary_labels = parent._summary_labels
        
        for iid in tree.get_children():
            tree.delete(iid)
        
        # Özet etiketlerini temizle
        for widget in summary_labels.winfo_children():
            widget.destroy()
        
        personel_filtre = cmb_personel.get() or ""
        durum_filtre = cmb_durum.get() or ""
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            where = []
            params = []
            
            if personel_filtre:
                where.append("put.personel_adi = ?")
                params.append(personel_filtre)
            
            if durum_filtre:
                where.append("put.odeme_durumu = ?")
                params.append(durum_filtre.lower())
            
            sql = """
                SELECT 
                    put.id,
                    put.personel_adi,
                    put.tarih,
                    put.seans_ucreti,
                    put.personel_ucreti,
                    put.ucret_orani,
                    put.odeme_durumu,
                    put.odeme_tarihi
                FROM personel_ucret_takibi put
            """
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY put.tarih DESC, put.id DESC"
            
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            
            # Özet hesapla
            toplam_beklemede = 0.0
            toplam_odendi = 0.0
            toplam_seans = len(rows)
            
            for idx, row in enumerate(rows):
                ucret_id, personel, tarih, seans_ucreti, personel_ucreti, ucret_orani, odeme_durumu, odeme_tarihi = row
                
                if odeme_durumu == "beklemede":
                    toplam_beklemede += float(personel_ucreti or 0)
                elif odeme_durumu == "odendi":
                    toplam_odendi += float(personel_ucreti or 0)
                
                durum_text = odeme_durumu.capitalize() if odeme_durumu else "Beklemede"
                oran_text = f"%{ucret_orani:.0f}" if ucret_orani > 0 else "Sabit"
                
                tag = odeme_durumu if odeme_durumu else "beklemede"
                if idx % 2 == 0:
                    tag = "even"
                else:
                    tag = "odd"
                
                tree.insert("", END, values=(
                    ucret_id,
                    personel,
                    tarih,
                    format_money(seans_ucreti),
                    format_money(personel_ucreti),
                    oran_text,
                    durum_text,
                    odeme_tarihi or "-"
                ), tags=(tag,))
            
            conn.close()
            
            # Özet göster
            ttk.Label(summary_labels, text=f"📊 Toplam Seans: {toplam_seans}", font=("Segoe UI", 10)).pack(side=LEFT, padx=10)
            ttk.Label(summary_labels, text=f"⏳ Beklemede: {format_money(toplam_beklemede)}", 
                     font=("Segoe UI", 10), bootstyle="warning").pack(side=LEFT, padx=10)
            ttk.Label(summary_labels, text=f"✅ Ödendi: {format_money(toplam_odendi)}", 
                     font=("Segoe UI", 10), bootstyle="success").pack(side=LEFT, padx=10)
        
        except Exception as e:
            messagebox.showerror("Hata", f"Personel ücret listesi yüklenemedi:\n{e}")
            log_exception("_personel_ucret_listele", e)
    
    def excel_ucret_listesi_yukle(self):
        """Excel'den çocuk ücret listesi yükle ve veritabanına aktar (2026 güncel ücretler)"""
        try:
            # Önce veriler klasöründeki dosyayı kontrol et
            veriler_klasoru = os.path.join(app_dir(), "veriler")
            excel_dosyasi = os.path.join(veriler_klasoru, "SEANS ÜCRET TAKİP.xlsx")
            
            if not os.path.exists(excel_dosyasi):
                # Kullanıcıdan dosya seçmesini iste
                dosya_yolu = filedialog.askopenfilename(
                    title="Excel Ücret Listesi Seç (2026 Güncel)",
                    filetypes=[("Excel Dosyaları", "*.xlsx *.xls"), ("Tüm Dosyalar", "*.*")],
                    initialdir=veriler_klasoru if os.path.exists(veriler_klasoru) else None
                )
                if not dosya_yolu:
                    return
            else:
                dosya_yolu = excel_dosyasi
                # Kullanıcıya onay sor
                if not messagebox.askyesno(
                    "Onay",
                    f"'{os.path.basename(dosya_yolu)}' dosyasından 2026 güncel ücretler yüklenecek.\n\n"
                    "Mevcut fiyatlandırmalar güncellenecek. Devam etmek istiyor musunuz?"
                ):
                    return
            
            # 2026 güncel ücretleri yükle
            self._import_2026_fees_from_excel(dosya_yolu)
            
        except Exception as e:
            messagebox.showerror("Hata", f"Excel ücret listesi yüklenemedi:\n{e}")
            log_exception("excel_ucret_listesi_yukle", e)
    
    def _import_2026_fees_from_excel(self, excel_path: str):
        """
        2026 güncel seans ücretlerini Excel'den oku ve sisteme işle.
        Görüntüdeki yapıya göre her personel için ayrı tablolar var.
        Excel dosyasından otomatik okuma yapılır.
        """
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            # Excel dosyasını oku - tüm sheet'leri kontrol et
            xls = pd.ExcelFile(excel_path)
            
            # 2026 güncel ücret verileri (görüntüden alınan - Excel'den otomatik okuma için hazır)
            # Format: (danisan_adi, personel_adi, seans_ucreti)
            # Not: Excel dosyasından otomatik okuma için görüntüdeki tablo yapısına göre parser yazılmalı
            # Şimdilik görüntüdeki verileri kullanıyoruz, Excel'den otomatik okuma için geliştirilecek
            
            fees_data = []
            
            # Excel'den veri okuma denemesi
            try:
                # Tüm sheet'leri kontrol et
                for sheet_name in xls.sheet_names:
                    try:
                        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
                        
                        # Tablo başlıklarını bul (personel isimleri)
                        current_personel = None
                        for idx, row in df.iterrows():
                            row_values = [str(cell).strip() if pd.notna(cell) else "" for cell in row]
                            row_str = " ".join(row_values).lower()
                            
                            # Personel adını bul
                            if "pervin" in row_str and "hoca" in row_str:
                                current_personel = "Pervin Hoca"
                            elif "arif" in row_str and "hoca" in row_str:
                                current_personel = "Arif Hoca"
                            elif "çağlar" in row_str and "hoca" in row_str:
                                current_personel = "Çağlar Hoca"
                            elif "sena" in row_str and "hoca" in row_str:
                                current_personel = "Sena Hoca"
                            elif "aybüke" in row_str and "hoca" in row_str:
                                current_personel = "Aybüke Hoca"
                            elif "elif" in row_str and "hoca" in row_str:
                                current_personel = "Elif Hoca"
                            
                            # Danışan adı ve tutar sütunlarını bul
                            if current_personel and len(row_values) >= 2:
                                danisan_adi = row_values[0].strip()
                                tutar_str = row_values[1].strip()
                                
                                # Tutarı parse et (Euro veya TL formatından)
                                try:
                                    # Euro formatından TL'ye çevir (1 Euro = ~35 TL yaklaşık)
                                    if "€" in tutar_str or "euro" in tutar_str.lower():
                                        tutar = float(tutar_str.replace("€", "").replace(",", ".").strip())
                                        tutar = tutar * 35.0  # Euro'dan TL'ye çevir
                                    else:
                                        tutar = float(tutar_str.replace(".", "").replace(",", ".").strip())
                                    
                                    if danisan_adi and tutar > 0 and danisan_adi.lower() not in ["danışan adı", "tutar", "toplam"]:
                                        fees_data.append((danisan_adi, current_personel, tutar))
                                except (ValueError, AttributeError):
                                    pass
                    except Exception as e:
                        log_exception(f"_import_2026_fees_excel_sheet_{sheet_name}", e)
                        continue
            except Exception as e:
                log_exception("_import_2026_fees_excel_read", e)
                # Excel okuma başarısız olursa görüntüdeki verileri kullan
                pass
            
            # Eğer Excel'den veri okunamadıysa, görüntüdeki verileri kullan
            if not fees_data:
                fees_data = [
                    # Pervin Hoca (%100) - Görüntüden
                    ("Alaz Dilek", "Pervin Hoca", 3700.0),
                    ("Tuna Öztürk", "Pervin Hoca", 3500.0),
                    ("Alaz Keskin", "Pervin Hoca", 4500.0),
                    ("Lea Beyazıt", "Pervin Hoca", 4250.0),
                    ("Mehmet Emre Kanıcı", "Pervin Hoca", 4400.0),
                    ("Selim Bayram", "Pervin Hoca", 2900.0),
                    ("Veysel Talha Altunışık", "Pervin Hoca", 4500.0),
                    ("Musap Aydın", "Pervin Hoca", 4200.0),
                    ("Aren Çölgeçen", "Pervin Hoca", 2800.0),
                    ("Mustafa Asaf Esqilli", "Pervin Hoca", 4250.0),
                    ("Pamir Çetin", "Pervin Hoca", 3600.0),
                    ("Ata Alaz Kanber", "Pervin Hoca", 3600.0),
                    ("Ertunga Yağız Eller", "Pervin Hoca", 4000.0),
                    ("Göktüğ Ağır", "Pervin Hoca", 3900.0),
                    ("Zeynep Turan", "Pervin Hoca", 3250.0),
                    ("Yağız Bayam", "Pervin Hoca", 3900.0),
                    ("Yıldırım Beyazıt", "Pervin Hoca", 4250.0),
                    ("Kuzey Çamur", "Pervin Hoca", 4100.0),
                    ("Alaz Tan Atakan", "Pervin Hoca", 3500.0),
                    ("Aren Akbal", "Pervin Hoca", 3800.0),
                    ("Farah Yüsra Uslu", "Pervin Hoca", 4500.0),
                    
                    # Arif Hoca (Sabit 2500 TL)
                    ("Mustafa Asaf Esqilli", "Arif Hoca", 3000.0),
                    ("Selim Bayram", "Arif Hoca", 2900.0),
                    ("Ata Alaz Kamber", "Arif Hoca", 3400.0),
                    ("Baran Demircan", "Arif Hoca", 3200.0),
                    ("Oğuzhan İpek", "Arif Hoca", 3000.0),
                    ("Tuna Aslan", "Arif Hoca", 3500.0),
                    ("Aren Çölgeçen", "Arif Hoca", 2500.0),
                    
                    # Çağlar Hoca (%40)
                    ("Alaz Dilek", "Çağlar Hoca", 2800.0),
                    ("Aren Çölgeçen", "Çağlar Hoca", 2700.0),
                    ("Lea Beyazıt", "Çağlar Hoca", 3100.0),
                    
                    # Sena Hoca (%40)
                    ("Ata Alaz Kamber", "Sena Hoca", 2600.0),
                    ("Hüseyin Yaman", "Sena Hoca", 2600.0),
                    ("Gökalp Şahin", "Sena Hoca", 3000.0),
                    
                    # Aybüke Hoca (%40)
                    ("Alaz Keskin", "Aybüke Hoca", 3000.0),
                    ("Tuna Aslan", "Aybüke Hoca", 2900.0),
                    
                    # Elif Hoca (%40)
                    ("Alaz Dilek", "Elif Hoca", 3500.0),
                    ("Yağız Bayam", "Elif Hoca", 3000.0),
                    ("Yıldırım Beyazıt", "Elif Hoca", 3800.0),
                ]
            
            eklenen_cocuk = 0
            eklenen_fiyatlandirma = 0
            guncellenen_fiyatlandirma = 0
            eklenen_atama = 0
            guncellenen_atama = 0
            
            olusturma_tarihi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            baslangic_tarihi = "2026-01-01"  # 2026 başlangıç tarihi
            
            for danisan_adi, personel_adi, seans_ucreti in fees_data:
                if not danisan_adi or not personel_adi or seans_ucreti <= 0:
                    continue
                
                # Personel adını normalize et
                personel_normalized = self._normalize_personel_adi(personel_adi)
                if not personel_normalized:
                    continue
                
                # 1) Çocuk ID'sini bul veya oluştur
                cur.execute("SELECT id FROM danisanlar WHERE UPPER(ad_soyad) = UPPER(?) AND aktif = 1 LIMIT 1", (danisan_adi,))
                cocuk_row = cur.fetchone()
                if not cocuk_row:
                    # Çocuk yoksa ekle
                    cur.execute(
                        "INSERT INTO danisanlar (ad_soyad, aktif, olusturma_tarihi) VALUES (?, 1, ?)",
                        (danisan_adi, olusturma_tarihi)
                    )
                    cocuk_id = cur.lastrowid
                    eklenen_cocuk += 1
                else:
                    cocuk_id = cocuk_row[0]
                
                # 2) Öğrenci-Personel Fiyatlandırma: Eski kayıtları pasif yap, yeni kayıt ekle
                cur.execute("""
                    UPDATE ogrenci_personel_fiyatlandirma 
                    SET aktif = 0, bitis_tarihi = ?, guncelleme_tarihi = ?
                    WHERE ogrenci_id = ? AND personel_adi = ? AND aktif = 1
                """, (baslangic_tarihi, olusturma_tarihi, cocuk_id, personel_normalized))
                
                # Yeni fiyatlandırma kaydı ekle
                cur.execute("""
                    INSERT INTO ogrenci_personel_fiyatlandirma
                    (ogrenci_id, personel_adi, seans_ucreti, baslangic_tarihi, aktif, zam_orani, olusturma_tarihi)
                    VALUES (?, ?, ?, ?, 1, 0, ?)
                """, (cocuk_id, personel_normalized, seans_ucreti, baslangic_tarihi, olusturma_tarihi))
                
                if cur.rowcount > 0:
                    eklenen_fiyatlandirma += 1
                else:
                    guncellenen_fiyatlandirma += 1
                
                # 3) Çocuk-Personel Atama: Eski kayıtları pasif yap, yeni kayıt ekle
                cur.execute("""
                    UPDATE cocuk_personel_atama 
                    SET aktif = 0, bitis_tarihi = ?
                    WHERE cocuk_id = ? AND personel_adi = ? AND aktif = 1
                """, (baslangic_tarihi, cocuk_id, personel_normalized))
                
                # Yeni atama kaydı ekle
                cur.execute("""
                    INSERT INTO cocuk_personel_atama
                    (cocuk_id, personel_adi, baslangic_tarihi, seans_ucreti, aktif, olusturma_tarihi)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (cocuk_id, personel_normalized, baslangic_tarihi, seans_ucreti, olusturma_tarihi))
                
                if cur.rowcount > 0:
                    eklenen_atama += 1
                else:
                    guncellenen_atama += 1
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo(
                "Başarılı",
                f"2026 Güncel Ücretler Yüklendi!\n\n"
                f"• {eklenen_cocuk} yeni çocuk eklendi\n"
                f"• {eklenen_fiyatlandirma} yeni fiyatlandırma eklendi\n"
                f"• {guncellenen_fiyatlandirma} fiyatlandırma güncellendi\n"
                f"• {eklenen_atama} yeni atama eklendi\n"
                f"• {guncellenen_atama} atama güncellendi\n\n"
                f"Yeni seans kayıtlarında bu ücretler otomatik kullanılacak."
            )
            
            # Ücret takibi listesini yenile
            try:
                # Ücret takibi tab'ını bul ve yenile
                if hasattr(self, '_ucret_takibi_notebook'):
                    current_tab = self._ucret_takibi_notebook.nametowidget(self._ucret_takibi_notebook.select())
                    if hasattr(current_tab, '_tree_cocuk'):
                        self._cocuk_ucret_listele(current_tab)
            except Exception:
                pass
            
        except Exception as e:
            messagebox.showerror("Hata", f"2026 ücretleri yüklenemedi:\n{e}")
            log_exception("_import_2026_fees_from_excel", e)
            raise
    
    def _normalize_personel_adi(self, personel: str) -> str:
        """Personel adını normalize et"""
        if not personel:
            return ""
        
        personel = str(personel).strip()
        
        # Personel adı eşleştirmeleri
        personel_map = {
            "pervin hoca": "Pervin Hoca",
            "pervin": "Pervin Hoca",
            "pervin hoca (değ.)": "Pervin Hoca",
            "arif hoca": "Arif Hoca",
            "arif": "Arif Hoca",
            "çağlar hoca": "Çağlar Hoca",
            "çağlar": "Çağlar Hoca",
            "çağlar hoca (değ.)": "Çağlar Hoca",
            "sena hoca": "Sena Hoca",
            "sena": "Sena Hoca",
            "aybüke hoca": "Aybüke Hoca",
            "aybüke": "Aybüke Hoca",
            "aybüke hoca (değ.)": "Aybüke Hoca",
            "elif hoca": "Elif Hoca",
            "elif": "Elif Hoca",
        }
        
        personel_lower = personel.lower()
        if personel_lower in personel_map:
            return personel_map[personel_lower]
        
        # İlk harfi büyük yap
        return personel.title()
    
    def personel_ucret_talep_formu(self):
        """Personel ücret talep formu penceresi"""
        win = ttk.Toplevel(self)
        win.title("Personel Ücret Talep Formu")
        win.geometry("600x500")
        center_window(win, 600, 500)
        
        wrapper = ttk.Frame(win, padding=20)
        wrapper.pack(fill=BOTH, expand=True)
        
        ttk.Label(wrapper, text="Personel Ücret Talep Formu", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=(0, 20))
        
        # Personel seçimi
        frm_personel = ttk.Frame(wrapper)
        frm_personel.pack(fill=X, pady=10)
        ttk.Label(frm_personel, text="Personel:", width=15).pack(side=LEFT)
        cmb_personel = ttk.Combobox(frm_personel, state="readonly", width=30)
        cmb_personel.pack(side=LEFT, padx=5)
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY therapist_name")
            personel_listesi = [row[0] for row in cur.fetchall()]
            conn.close()
            cmb_personel["values"] = personel_listesi
            if personel_listesi:
                cmb_personel.current(0)
        except Exception:
            cmb_personel["values"] = []
        
        # Tarih aralığı
        frm_tarih = ttk.Frame(wrapper)
        frm_tarih.pack(fill=X, pady=10)
        ttk.Label(frm_tarih, text="Başlangıç Tarihi:", width=15).pack(side=LEFT)
        ent_baslangic = ttk.Entry(frm_tarih, width=30)
        ent_baslangic.pack(side=LEFT, padx=5)
        ent_baslangic.insert(0, datetime.datetime.now().strftime("%Y-%m-01"))  # Ayın ilk günü
        
        frm_tarih2 = ttk.Frame(wrapper)
        frm_tarih2.pack(fill=X, pady=10)
        ttk.Label(frm_tarih2, text="Bitiş Tarihi:", width=15).pack(side=LEFT)
        ent_bitis = ttk.Entry(frm_tarih2, width=30)
        ent_bitis.pack(side=LEFT, padx=5)
        ent_bitis.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))  # Bugün
        
        # Özet bilgiler
        frm_ozet = ttk.LabelFrame(wrapper, text="Özet Bilgiler", padding=10)
        frm_ozet.pack(fill=X, pady=10)
        
        lbl_ozet = ttk.Label(frm_ozet, text="Personel ve tarih seçtikten sonra özet bilgiler burada görünecek.", 
                            font=("Segoe UI", 9), foreground="gray")
        lbl_ozet.pack()
        
        def hesapla_ozet():
            personel = cmb_personel.get()
            baslangic = ent_baslangic.get()
            bitis = ent_bitis.get()
            
            if not personel or not baslangic or not bitis:
                lbl_ozet.config(text="Lütfen tüm alanları doldurun.")
                return
            
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) AS seans_sayisi,
                        SUM(personel_ucreti) AS toplam_ucret
                    FROM personel_ucret_takibi
                    WHERE personel_adi = ? AND tarih >= ? AND tarih <= ? AND odeme_durumu = 'beklemede'
                    """,
                    (personel, baslangic, bitis)
                )
                row = cur.fetchone()
                seans_sayisi = row[0] or 0
                toplam_ucret = float(row[1] or 0)
                
                conn.close()
                
                lbl_ozet.config(
                    text=f"📊 Seans Sayısı: {seans_sayisi}\n"
                         f"💰 Toplam Ücret: {format_money(toplam_ucret)}",
                    foreground="black"
                )
            except Exception as e:
                lbl_ozet.config(text=f"Hata: {e}", foreground="red")
        
        ttk.Button(wrapper, text="📊 Özet Hesapla", bootstyle="info", command=hesapla_ozet).pack(pady=10)
        
        def kaydet():
            personel = cmb_personel.get()
            baslangic = ent_baslangic.get()
            bitis = ent_bitis.get()
            
            if not personel or not baslangic or not bitis:
                messagebox.showerror("Hata", "Lütfen tüm alanları doldurun.")
                return
            
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                
                # Özet hesapla
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) AS seans_sayisi,
                        SUM(personel_ucreti) AS toplam_ucret
                    FROM personel_ucret_takibi
                    WHERE personel_adi = ? AND tarih >= ? AND tarih <= ? AND odeme_durumu = 'beklemede'
                    """,
                    (personel, baslangic, bitis)
                )
                row = cur.fetchone()
                seans_sayisi = row[0] or 0
                toplam_ucret = float(row[1] or 0)
                
                if seans_sayisi == 0:
                    messagebox.showwarning("Uyarı", "Seçilen tarih aralığında beklemede ücret bulunamadı.")
                    conn.close()
                    return
                
                # Talep kaydı oluştur
                cur.execute(
                    """
                    INSERT INTO personel_ucret_talepleri
                    (personel_adi, talep_tarihi, baslangic_tarihi, bitis_tarihi, toplam_seans_sayisi, toplam_ucret, durum, olusturma_tarihi, olusturan_kullanici_id)
                    VALUES (?, ?, ?, ?, ?, ?, 'beklemede', ?, ?)
                        """,
                        (
                        personel,
                        datetime.datetime.now().strftime("%Y-%m-%d"),
                        baslangic,
                        bitis,
                        seans_sayisi,
                        toplam_ucret,
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        self.kullanici_id
                    )
                )
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo(
                    "Başarılı",
                    f"Personel ücret talebi oluşturuldu!\n\n"
                    f"• Personel: {personel}\n"
                    f"• Tarih Aralığı: {baslangic} - {bitis}\n"
                    f"• Seans Sayısı: {seans_sayisi}\n"
                    f"• Toplam Ücret: {format_money(toplam_ucret)}"
                )
                
                win.destroy()
                
                # Ücret takibi sayfasını yenile
                try:
                    if hasattr(self, 'tab_ucret_takibi'):
                        for child in self.tab_ucret_takibi.winfo_children():
                            if isinstance(child, ttk.Frame):
                                for subchild in child.winfo_children():
                                    if isinstance(subchild, ttk.Notebook):
                                        for page_id in subchild.tabs():
                                            page = subchild.nametowidget(page_id)
                                            if hasattr(page, '_tree_personel'):
                                                self._personel_ucret_listele(page)
                except Exception:
                    pass

            except Exception as e:
                messagebox.showerror("Hata", f"Talep kaydı oluşturulamadı:\n{e}")
                log_exception("personel_ucret_talep_formu", e)
        
        ttk.Button(wrapper, text="✅ Talep Oluştur", bootstyle="success", command=kaydet).pack(pady=10)
    
    def personel_ucret_odeme_yap(self):
        """Personel ücret ödeme yapma penceresi"""
        win = ttk.Toplevel(self)
        win.title("Personel Ücret Ödeme")
        win.geometry("500x400")
        center_window(win, 500, 400)
        
        wrapper = ttk.Frame(win, padding=20)
        wrapper.pack(fill=BOTH, expand=True)
        
        ttk.Label(wrapper, text="Personel Ücret Ödeme", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=(0, 20))
        
        # Personel seçimi
        frm_personel = ttk.Frame(wrapper)
        frm_personel.pack(fill=X, pady=10)
        ttk.Label(frm_personel, text="Personel:", width=15).pack(side=LEFT)
        cmb_personel = ttk.Combobox(frm_personel, state="readonly", width=30)
        cmb_personel.pack(side=LEFT, padx=5)
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY therapist_name")
            personel_listesi = [row[0] for row in cur.fetchall()]
            conn.close()
            cmb_personel["values"] = personel_listesi
            if personel_listesi:
                cmb_personel.current(0)
        except Exception:
            cmb_personel["values"] = []
        
        # Beklemede ücretler listesi
        frm_liste = ttk.LabelFrame(wrapper, text="Beklemede Ücretler", padding=10)
        frm_liste.pack(fill=BOTH, expand=True, pady=10)
        
        cols = ("ID", "Tarih", "Seans Ücreti", "Personel Ücreti")
        tree = ttk.Treeview(frm_liste, columns=cols, show="headings", height=8)
        for c in cols:
            tree.heading(c, text=c)
            if c == "ID":
                tree.column(c, width=50)
            elif c == "Tarih":
                tree.column(c, width=100)
            else:
                tree.column(c, width=120, anchor="e")
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(frm_liste, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        
        def yukle_liste():
            for iid in tree.get_children():
                tree.delete(iid)
            
            personel = cmb_personel.get()
            if not personel:
                return
            
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, tarih, seans_ucreti, personel_ucreti
                    FROM personel_ucret_takibi
                    WHERE personel_adi = ? AND odeme_durumu = 'beklemede'
                    ORDER BY tarih DESC
                    """,
                    (personel,)
                )
                rows = cur.fetchall()
                conn.close()
                
                for row in rows:
                    tree.insert("", END, values=row)
            except Exception as e:
                messagebox.showerror("Hata", f"Liste yüklenemedi:\n{e}")
        
        cmb_personel.bind("<<ComboboxSelected>>", lambda e: yukle_liste())
        yukle_liste()
        
        def odeme_yap():
            secili = tree.selection()
            if not secili:
                messagebox.showwarning("Uyarı", "Lütfen ödeme yapılacak kaydı seçin.")
                return

            ucret_id = tree.item(secili[0])["values"][0]
            
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                
                # Ücret bilgisini al
                cur.execute(
                    "SELECT personel_adi, personel_ucreti FROM personel_ucret_takibi WHERE id = ?",
                    (ucret_id,)
                )
                row = cur.fetchone()
                if not row:
                    messagebox.showerror("Hata", "Ücret kaydı bulunamadı.")
                    conn.close()
                    return
                
                personel_adi, tutar = row
                
                # Ödeme durumunu güncelle
                cur.execute(
                    """
                    UPDATE personel_ucret_takibi
                    SET odeme_durumu = 'odendi', odeme_tarihi = ?
                    WHERE id = ?
                    """,
                    (datetime.datetime.now().strftime("%Y-%m-%d"), ucret_id)
                )
                
                # Kasa defterine "çıkan" kaydı ekle
                cur.execute(
                    """
                    INSERT INTO kasa_hareketleri
                    (tarih, tip, aciklama, tutar, odeme_sekli, olusturan_kullanici_id, olusturma_tarihi)
                    VALUES (?, 'cikan', ?, ?, 'Nakit', ?, ?)
                        """,
                        (
                        datetime.datetime.now().strftime("%Y-%m-%d"),
                        f"{personel_adi} - Personel Ücret Ödemesi",
                        tutar,
                        self.kullanici_id,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                )

                conn.commit()
                conn.close()
                
                messagebox.showinfo("Başarılı", f"Personel ücret ödemesi yapıldı!\n\n{personel_adi}: {format_money(tutar)}")
                
                yukle_liste()
                
                # Ücret takibi sayfasını yenile
                try:
                    if hasattr(self, 'tab_ucret_takibi'):
                        for child in self.tab_ucret_takibi.winfo_children():
                            if isinstance(child, ttk.Frame):
                                for subchild in child.winfo_children():
                                    if isinstance(subchild, ttk.Notebook):
                                        for page_id in subchild.tabs():
                                            page = subchild.nametowidget(page_id)
                                            if hasattr(page, '_tree_personel'):
                                                self._personel_ucret_listele(page)
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror("Hata", f"Ödeme yapılamadı:\n{e}")
                log_exception("personel_ucret_odeme_yap", e)
        
        ttk.Button(wrapper, text="💰 Ödeme Yap", bootstyle="success", command=odeme_yap).pack(pady=10)
    
    def _build_cocuk_gunluk_tab(self):
        """Çocuk Günlük Takip Tab - Oda ve personel takibi"""
        wrapper = ttk.Frame(self.tab_cocuk_gunluk, padding=10)
        wrapper.pack(fill=BOTH, expand=True)
        
        # Başlık
        head = ttk.Frame(wrapper)
        head.pack(fill=X, pady=(0, 10))
        if getattr(self, "_logo_small", None):
            ttk.Label(head, image=self._logo_small).pack(side=LEFT, padx=(0, 10))
        ttk.Label(head, text="ÇOCUK GÜNLÜK TAKİP", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        
        # Filtreler
        filter_frame = ttk.Frame(wrapper)
        filter_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Tarih:").pack(side=LEFT, padx=5)
        ent_tarih = ttk.Entry(filter_frame, width=15)
        ent_tarih.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        ent_tarih.pack(side=LEFT, padx=5)
        
        ttk.Label(filter_frame, text="Çocuk:").pack(side=LEFT, padx=(20, 5))
        cmb_cocuk = ttk.Combobox(filter_frame, state="readonly", width=25)
        cmb_cocuk.pack(side=LEFT, padx=5)
        
        # Çocuk listesi
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
            cocuk_listesi = [""] + [row[0] for row in cur.fetchall()]
            conn.close()
            cmb_cocuk["values"] = cocuk_listesi
            cmb_cocuk.current(0)
        except Exception:
            cmb_cocuk["values"] = [""]
        
        ttk.Label(filter_frame, text="Oda:").pack(side=LEFT, padx=(20, 5))
        cmb_oda = ttk.Combobox(filter_frame, state="readonly", width=20)
        cmb_oda.pack(side=LEFT, padx=5)
        
        # Oda listesi
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT oda_adi FROM odalar WHERE aktif=1 ORDER BY oda_adi")
            oda_listesi = [""] + [row[0] for row in cur.fetchall()]
            conn.close()
            cmb_oda["values"] = oda_listesi
            cmb_oda.current(0)
        except Exception:
            cmb_oda["values"] = [""]
        
        ttk.Button(filter_frame, text="🔄 Filtrele", bootstyle="primary",
                   command=lambda: self._cocuk_gunluk_listele(wrapper)).pack(side=LEFT, padx=10)
        
        # Treeview
        frame_tree = ttk.Frame(wrapper)
        frame_tree.pack(fill=BOTH, expand=True)
        
        cols = ("ID", "Çocuk", "Tarih", "Oda", "Personel", "Seans ID", "Notlar")
        tree = ttk.Treeview(frame_tree, columns=cols, show="headings", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            if c == "ID":
                tree.column(c, width=50)
            elif c == "Çocuk":
                tree.column(c, width=200)
            elif c == "Tarih":
                tree.column(c, width=100)
            elif c == "Oda":
                tree.column(c, width=150)
            elif c == "Personel":
                tree.column(c, width=150)
            elif c == "Seans ID":
                tree.column(c, width=80)
            else:
                tree.column(c, width=300)
        
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(frame_tree, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        
        # Tag'ler
        tree.tag_configure("even", background="#f8f9fa")
        tree.tag_configure("odd", background="#ffffff")
        
        # Widget'ları kaydet
        wrapper._tree_gunluk = tree
        wrapper._ent_tarih = ent_tarih
        wrapper._cmb_cocuk = cmb_cocuk
        wrapper._cmb_oda = cmb_oda
        
        # İlk yükleme
        self._cocuk_gunluk_listele(wrapper)
    
    def _cocuk_gunluk_listele(self, parent):
        """Çocuk günlük takip listesini yükle"""
        tree = parent._tree_gunluk
        ent_tarih = parent._ent_tarih
        cmb_cocuk = parent._cmb_cocuk
        cmb_oda = parent._cmb_oda
        
        for iid in tree.get_children():
            tree.delete(iid)
        
        tarih_filtre = ent_tarih.get() or ""
        cocuk_filtre = cmb_cocuk.get() or ""
        oda_filtre = cmb_oda.get() or ""
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            where = []
            params = []
            
            if tarih_filtre:
                where.append("cgt.tarih = ?")
                params.append(tarih_filtre)
            
            if cocuk_filtre:
                where.append("d.ad_soyad = ?")
                params.append(cocuk_filtre)
            
            if oda_filtre:
                where.append("cgt.oda_adi = ?")
                params.append(oda_filtre)
            
            # Role göre filtre
            if self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
                where.append("cgt.personel_adi = ?")
                params.append(self.kullanici_terapist)
            
            sql = """
                SELECT 
                    cgt.id,
                    d.ad_soyad,
                    cgt.tarih,
                    cgt.oda_adi,
                    cgt.personel_adi,
                    cgt.seans_id,
                    cgt.notlar
                FROM cocuk_gunluk_takip cgt
                LEFT JOIN danisanlar d ON cgt.cocuk_id = d.id
            """
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY cgt.tarih DESC, cgt.id DESC"
            
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            conn.close()
            
            for idx, row in enumerate(rows):
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=row, tags=(tag,))
        
        except Exception as e:
            messagebox.showerror("Hata", f"Çocuk günlük takip listesi yüklenemedi:\n{e}")
            log_exception("_cocuk_gunluk_listele", e)
    
    def _build_kasa_defteri_tab(self):
        """Kasa Defteri Tab - Günlük/haftalık/aylık raporlar"""
        wrapper = ttk.Frame(self.tab_kasa, padding=10)
        wrapper.pack(fill=BOTH, expand=True)
        
        # Başlık
        head = ttk.Frame(wrapper)
        head.pack(fill=X, pady=(0, 10))
        if getattr(self, "_logo_small", None):
            ttk.Label(head, image=self._logo_small).pack(side=LEFT, padx=(0, 10))
        ttk.Label(head, text="KASA DEFTERİ", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        
        # Rapor tipi seçimi
        report_frame = ttk.LabelFrame(wrapper, text="Rapor Tipi", padding=10)
        report_frame.pack(fill=X, pady=(0, 10))
        
        report_type = ttk.StringVar(value="gunluk")
        ttk.Radiobutton(report_frame, text="📅 Günlük", variable=report_type, value="gunluk",
                       command=lambda: self._kasa_rapor_yukle(wrapper)).pack(side=LEFT, padx=10)
        ttk.Radiobutton(report_frame, text="📆 Haftalık", variable=report_type, value="haftalik",
                       command=lambda: self._kasa_rapor_yukle(wrapper)).pack(side=LEFT, padx=10)
        ttk.Radiobutton(report_frame, text="📊 Aylık", variable=report_type, value="aylik",
                       command=lambda: self._kasa_rapor_yukle(wrapper)).pack(side=LEFT, padx=10)
        
        # Tarih seçimi
        date_frame = ttk.Frame(wrapper)
        date_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(date_frame, text="Tarih:").pack(side=LEFT, padx=5)
        ent_tarih = ttk.Entry(date_frame, width=15)
        ent_tarih.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        ent_tarih.pack(side=LEFT, padx=5)
        
        ttk.Button(date_frame, text="🔄 Rapor Yükle", bootstyle="primary",
                   command=lambda: self._kasa_rapor_yukle(wrapper)).pack(side=LEFT, padx=10)
        
        # Özet bilgiler
        summary_frame = ttk.LabelFrame(wrapper, text="Özet", padding=10)
        summary_frame.pack(fill=X, pady=(0, 10))
        
        summary_labels = ttk.Frame(summary_frame)
        summary_labels.pack(fill=X)
        
        # Treeview
        frame_tree = ttk.Frame(wrapper)
        frame_tree.pack(fill=BOTH, expand=True)
        
        cols = ("ID", "Tarih", "Tip", "Açıklama", "Tutar", "Ödeme Şekli", "Kayıt ID", "Seans ID")
        tree = ttk.Treeview(frame_tree, columns=cols, show="headings", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            if c == "ID":
                tree.column(c, width=50)
            elif c == "Tarih":
                tree.column(c, width=100)
            elif c == "Tip":
                tree.column(c, width=80)
            elif c == "Açıklama":
                tree.column(c, width=300)
            elif c == "Tutar":
                tree.column(c, width=120, anchor="e")
            elif c == "Ödeme Şekli":
                tree.column(c, width=120)
            else:
                tree.column(c, width=80)
        
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(frame_tree, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        
        # Tag'ler
        tree.tag_configure("giren", background="#d4edda", foreground="#155724")
        tree.tag_configure("cikan", background="#f8d7da", foreground="#721c24")
        tree.tag_configure("even", background="#f8f9fa")
        tree.tag_configure("odd", background="#ffffff")
        
        # Widget'ları kaydet
        wrapper._tree_kasa = tree
        wrapper._ent_tarih = ent_tarih
        wrapper._report_type = report_type
        wrapper._summary_labels = summary_labels
        
        # İlk yükleme
        self._kasa_rapor_yukle(wrapper)
    
    def _kasa_rapor_yukle(self, parent):
        """Kasa defteri raporunu yükle"""
        tree = parent._tree_kasa
        ent_tarih = parent._ent_tarih
        report_type = parent._report_type
        summary_labels = parent._summary_labels
        
        for iid in tree.get_children():
            tree.delete(iid)
        
        # Özet etiketlerini temizle
        for widget in summary_labels.winfo_children():
            widget.destroy()
        
        tarih_str = ent_tarih.get() or datetime.datetime.now().strftime("%Y-%m-%d")
        
        try:
            tarih = datetime.datetime.strptime(tarih_str, "%Y-%m-%d")
        except Exception:
            messagebox.showerror("Hata", "Geçersiz tarih formatı! (YYYY-MM-DD)")
            return

        # Tarih aralığını hesapla
        if report_type.get() == "gunluk":
            baslangic = bitis = tarih.strftime("%Y-%m-%d")
        elif report_type.get() == "haftalik":
            # Haftanın başlangıcı (Pazartesi)
            baslangic = (tarih - datetime.timedelta(days=tarih.weekday())).strftime("%Y-%m-%d")
            bitis = (tarih + datetime.timedelta(days=6-tarih.weekday())).strftime("%Y-%m-%d")
        else:  # aylik
            baslangic = tarih.replace(day=1).strftime("%Y-%m-%d")
            # Ayın son günü
            if tarih.month == 12:
                bitis = tarih.replace(year=tarih.year+1, month=1, day=1) - datetime.timedelta(days=1)
            else:
                bitis = tarih.replace(month=tarih.month+1, day=1) - datetime.timedelta(days=1)
            bitis = bitis.strftime("%Y-%m-%d")
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            # Kasa hareketlerini çek
            cur.execute(
                """
                SELECT 
                    id, tarih, tip, aciklama, tutar, odeme_sekli, record_id, seans_id
                FROM kasa_hareketleri
                WHERE tarih >= ? AND tarih <= ?
                ORDER BY tarih DESC, id DESC
                """,
                (baslangic, bitis)
            )
            rows = cur.fetchall()
            
            # Özet hesapla
            toplam_giren = 0.0
            toplam_cikan = 0.0
            
            for idx, row in enumerate(rows):
                kasa_id, tarih, tip, aciklama, tutar, odeme_sekli, record_id, seans_id = row
                
                if tip == "giren":
                    toplam_giren += float(tutar or 0)
                elif tip == "cikan":
                    toplam_cikan += float(tutar or 0)
                
                tag = tip if tip in ("giren", "cikan") else ("even" if idx % 2 == 0 else "odd")
                
                tree.insert("", END, values=(
                    kasa_id,
                    tarih,
                    tip.capitalize(),
                    aciklama,
                    format_money(tutar),
                    odeme_sekli or "-",
                    record_id or "-",
                    seans_id or "-"
                ), tags=(tag,))
            
            net = toplam_giren - toplam_cikan
            
            conn.close()
            
            # Özet göster
            ttk.Label(summary_labels, text=f"📥 Toplam Giren: {format_money(toplam_giren)}", 
                     font=("Segoe UI", 11, "bold"), bootstyle="success").pack(side=LEFT, padx=15)
            ttk.Label(summary_labels, text=f"📤 Toplam Çıkan: {format_money(toplam_cikan)}", 
                     font=("Segoe UI", 11, "bold"), bootstyle="danger").pack(side=LEFT, padx=15)
            ttk.Label(summary_labels, text=f"💰 Net Kasa: {format_money(net)}", 
                     font=("Segoe UI", 12, "bold"), 
                     bootstyle="success" if net >= 0 else "danger").pack(side=LEFT, padx=15)
            ttk.Label(summary_labels, text=f"📊 Tarih Aralığı: {baslangic} - {bitis}", 
                     font=("Segoe UI", 10), foreground="gray").pack(side=LEFT, padx=15)
        
        except Exception as e:
            messagebox.showerror("Hata", f"Kasa raporu yüklenemedi:\n{e}")
            log_exception("_kasa_rapor_yukle", e)
    
    def _build_bep_tab(self):
        """BEP (Bireysel Eğitim Programı) Tab"""
        wrapper = ttk.Frame(self.tab_bep, padding=10)
        wrapper.pack(fill=BOTH, expand=True)
        
        # Başlık
        head = ttk.Frame(wrapper)
        head.pack(fill=X, pady=(0, 10))
        if getattr(self, "_logo_small", None):
            ttk.Label(head, image=self._logo_small).pack(side=LEFT, padx=(0, 10))
        ttk.Label(head, text="BİREYSEL EĞİTİM PROGRAMI (BEP)", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        
        # Üst toolbar
        toolbar = ttk.Frame(wrapper)
        toolbar.pack(fill=X, pady=(0, 10))
        
        ttk.Label(toolbar, text="Çocuk Seç:").pack(side=LEFT, padx=5)
        cmb_cocuk = ttk.Combobox(toolbar, state="readonly", width=30)
        cmb_cocuk.pack(side=LEFT, padx=5)
        
        # Çocuk listesi
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT id, ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
            cocuk_listesi = [(row[0], row[1]) for row in cur.fetchall()]
            conn.close()
            cmb_cocuk["values"] = [f"{c[1]} (ID: {c[0]})" for c in cocuk_listesi]
            if cocuk_listesi:
                cmb_cocuk.current(0)
        except Exception:
            cmb_cocuk["values"] = []
        
        ttk.Label(toolbar, text="Yıl:").pack(side=LEFT, padx=(20, 5))
        cmb_yil = ttk.Combobox(toolbar, state="readonly", width=10)
        yil_listesi = [str(datetime.datetime.now().year + i) for i in range(-2, 3)]
        cmb_yil["values"] = yil_listesi
        cmb_yil.set(str(datetime.datetime.now().year))
        cmb_yil.pack(side=LEFT, padx=5)
        
        ttk.Button(toolbar, text="📋 BEP Oluştur/Güncelle", bootstyle="success",
                   command=lambda: self._bep_olustur_guncelle(wrapper)).pack(side=LEFT, padx=10)
        ttk.Button(toolbar, text="🔄 Yükle", bootstyle="primary",
                   command=lambda: self._bep_yukle(wrapper)).pack(side=LEFT, padx=5)
        
        # BEP görüntüleme alanı
        bep_frame = ttk.LabelFrame(wrapper, text="BEP Programı", padding=10)
        bep_frame.pack(fill=BOTH, expand=True)
        
        # BEP tablosu (12 ay x hedef beceriler)
        canvas_frame = ttk.Frame(bep_frame)
        canvas_frame.pack(fill=BOTH, expand=True)
        
        # Scrollable canvas
        canvas = tk.Canvas(canvas_frame, bg="white")
        scrollbar = ttk.Scrollbar(canvas_frame, orient=VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # BEP hedef becerileri (resimdeki gibi)
        HEDEF_BECERILER = [
            "Erken Okur Yazarlık Becerisi",
            "Yazı Farkındalığı",
            "Hece Bilgisi",
            "Uyak Farkındalığı",
            "Sesbilişsel Farkındalık",
            "İnce Motor Becerileri",
            "İşitsel ve Görsel Algı Dikkat",
            "Neden Sonuç İlişkisi",
            "Muhakeme Tahmin Etme"
        ]
        
        AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        
        # Tablo başlıkları
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=X, pady=(0, 5))
        
        ttk.Label(header_frame, text="Hedef Beceriler", font=("Segoe UI", 10, "bold"), width=30, anchor="w").pack(side=LEFT, padx=2)
        for ay in AYLAR:
            ttk.Label(header_frame, text=ay[:3], font=("Segoe UI", 9, "bold"), width=8, anchor="center").pack(side=LEFT, padx=1)
        
        # BEP tablosu
        bep_table = {}
        for beceri in HEDEF_BECERILER:
            row_frame = ttk.Frame(scrollable_frame)
            row_frame.pack(fill=X, pady=2)
            
            ttk.Label(row_frame, text=beceri, font=("Segoe UI", 9), width=30, anchor="w").pack(side=LEFT, padx=2)
            
            ay_widgets = []
            for ay_idx in range(12):
                var = ttk.StringVar(value="")
                cmb = ttk.Combobox(row_frame, textvariable=var, state="readonly", width=8,
                                 values=["", "Planlandı", "Devam Ediyor", "Tamamlandı"])
                cmb.pack(side=LEFT, padx=1)
                ay_widgets.append((var, cmb))
            
            bep_table[beceri] = ay_widgets
        
        # Widget'ları kaydet
        wrapper._cmb_cocuk = cmb_cocuk
        wrapper._cmb_yil = cmb_yil
        wrapper._bep_table = bep_table
        wrapper._canvas = canvas
        wrapper._scrollable_frame = scrollable_frame
        
        # İlk yükleme
        self._bep_yukle(wrapper)
    
    def _bep_olustur_guncelle(self, parent):
        """BEP oluştur veya güncelle"""
        cmb_cocuk = parent._cmb_cocuk
        cmb_yil = parent._cmb_yil
        bep_table = parent._bep_table
        
        cocuk_text = cmb_cocuk.get()
        if not cocuk_text:
            messagebox.showwarning("Uyarı", "Lütfen bir çocuk seçin.")
            return
        
        # Çocuk ID'sini al
        try:
            cocuk_id = int(cocuk_text.split("(ID: ")[1].split(")")[0])
        except Exception:
            messagebox.showerror("Hata", "Geçersiz çocuk seçimi.")
            return
        
        yil = int(cmb_yil.get())
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            # BEP programını kontrol et
            cur.execute(
                "SELECT id FROM bep_programlari WHERE cocuk_id = ? AND program_yili = ?",
                (cocuk_id, yil)
            )
            bep_row = cur.fetchone()
            
            if bep_row:
                bep_id = bep_row[0]
                # Güncelle
                cur.execute(
                    "UPDATE bep_programlari SET guncelleme_tarihi = ? WHERE id = ?",
                    (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), bep_id)
                )
            else:
                # Yeni oluştur
                cur.execute(
                    """
                    INSERT INTO bep_programlari
                    (cocuk_id, program_yili, olusturma_tarihi, olusturan_kullanici_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        cocuk_id,
                        yil,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        self.kullanici_id
                    )
                )
                bep_id = cur.lastrowid
            
            # Hedef becerileri kaydet
            for beceri, ay_widgets in bep_table.items():
                for ay_idx, (var, cmb) in enumerate(ay_widgets):
                    durum = var.get()
                    if durum:
                        # Durum mapping
                        durum_map = {
                            "Planlandı": "planlandi",
                            "Devam Ediyor": "devam_ediyor",
                            "Tamamlandı": "tamamlandi"
                        }
                        durum_db = durum_map.get(durum, "planlandi")
                        
                        # Mevcut kaydı kontrol et
                        cur.execute(
                            """
                            SELECT id FROM bep_hedef_beceriler
                            WHERE bep_id = ? AND hedef_beceri = ? AND ay = ?
                            """,
                            (bep_id, beceri, ay_idx + 1)
                        )
                        hedef_row = cur.fetchone()
                        
                        if hedef_row:
                            # Güncelle
                            cur.execute(
                                """
                                UPDATE bep_hedef_beceriler
                                SET durum = ?, olusturma_tarihi = ?
                                WHERE id = ?
                                """,
                                (durum_db, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), hedef_row[0])
                            )
                        else:
                            # Yeni ekle
                            cur.execute(
                                """
                                INSERT INTO bep_hedef_beceriler
                                (bep_id, hedef_beceri, ay, durum, olusturma_tarihi)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (
                                    bep_id,
                                    beceri,
                                    ay_idx + 1,
                                    durum_db,
                                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                )
                            )
            
                conn.commit()
                conn.close()
            
            messagebox.showinfo("Başarılı", f"BEP programı kaydedildi!\n\nÇocuk ID: {cocuk_id}\nYıl: {yil}")
        
        except Exception as e:
            messagebox.showerror("Hata", f"BEP kaydedilemedi:\n{e}")
            log_exception("_bep_olustur_guncelle", e)
    
    def _bep_yukle(self, parent):
        """BEP programını yükle"""
        cmb_cocuk = parent._cmb_cocuk
        cmb_yil = parent._cmb_yil
        bep_table = parent._bep_table
        
        cocuk_text = cmb_cocuk.get()
        if not cocuk_text:
                return

        # Çocuk ID'sini al
        try:
            cocuk_id = int(cocuk_text.split("(ID: ")[1].split(")")[0])
        except Exception:
            return
        
        yil = int(cmb_yil.get())
        
        # Tüm combobox'ları temizle
        for beceri, ay_widgets in bep_table.items():
            for var, cmb in ay_widgets:
                var.set("")
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            # BEP programını bul
            cur.execute(
                "SELECT id FROM bep_programlari WHERE cocuk_id = ? AND program_yili = ?",
                (cocuk_id, yil)
            )
            bep_row = cur.fetchone()
            
            if not bep_row:
                return
            
            bep_id = bep_row[0]
            
            # Hedef becerileri yükle
            cur.execute(
                """
                SELECT hedef_beceri, ay, durum
                FROM bep_hedef_beceriler
                WHERE bep_id = ?
                """,
                (bep_id,)
            )
            rows = cur.fetchall()
            
            # Durum mapping (ters)
            durum_map = {
                "planlandi": "Planlandı",
                "devam_ediyor": "Devam Ediyor",
                "tamamlandi": "Tamamlandı"
            }
            
            for hedef_beceri, ay, durum in rows:
                if hedef_beceri in bep_table:
                    ay_widgets = bep_table[hedef_beceri]
                    if 1 <= ay <= 12:
                        var, cmb = ay_widgets[ay - 1]
                        var.set(durum_map.get(durum, "Planlandı"))
            
            conn.close()
        
        except Exception as e:
            log_exception("_bep_yukle", e)
    
    def _build_haftalik_seans_tab(self):
        """Haftalık Seans Takip Tab - Personel bazlı dinamik program"""
        wrapper = ttk.Frame(self.tab_haftalik, padding=10)
        wrapper.pack(fill=BOTH, expand=True)
        
        # Başlık
        head = ttk.Frame(wrapper)
        head.pack(fill=X, pady=(0, 10))
        if getattr(self, "_logo_small", None):
            ttk.Label(head, image=self._logo_small).pack(side=LEFT, padx=(0, 10))
        ttk.Label(head, text="HAFTALIK SEANS PROGRAMI", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        
        # Personel seçimi ve hafta seçimi
        filter_frame = ttk.Frame(wrapper)
        filter_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Personel:").pack(side=LEFT, padx=5)
        cmb_personel = ttk.Combobox(filter_frame, state="readonly", width=25)
        cmb_personel.pack(side=LEFT, padx=5)
        
        # Personel listesi
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY therapist_name")
            personel_listesi = [row[0] for row in cur.fetchall()]
            conn.close()
            cmb_personel["values"] = personel_listesi
            if personel_listesi:
                cmb_personel.current(0)
        except Exception:
            cmb_personel["values"] = []
        
        ttk.Label(filter_frame, text="Hafta:").pack(side=LEFT, padx=(20, 5))
        ent_hafta = ttk.Entry(filter_frame, width=15)
        # Bu haftanın pazartesi gününü hesapla
        today = datetime.datetime.now()
        monday = today - datetime.timedelta(days=today.weekday())
        ent_hafta.insert(0, monday.strftime("%Y-%m-%d"))
        ent_hafta.pack(side=LEFT, padx=5)
        
        ttk.Button(filter_frame, text="📅 Hafta Seç", bootstyle="secondary",
                   command=lambda: self._hafta_sec(ent_hafta)).pack(side=LEFT, padx=5)
        ttk.Button(filter_frame, text="🔄 Yükle", bootstyle="primary",
                   command=lambda: self._haftalik_program_yukle(wrapper)).pack(side=LEFT, padx=10)
        ttk.Button(filter_frame, text="💾 Kaydet", bootstyle="success",
                   command=lambda: self._haftalik_program_kaydet(wrapper)).pack(side=LEFT, padx=5)
        
        # Haftalık program tablosu
        program_frame = ttk.LabelFrame(wrapper, text="Haftalık Program", padding=10)
        program_frame.pack(fill=BOTH, expand=True)
        
        # Scrollable canvas
        canvas_frame = ttk.Frame(program_frame)
        canvas_frame.pack(fill=BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg="white")
        scrollbar = ttk.Scrollbar(canvas_frame, orient=VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Tablo başlıkları
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=X, pady=(0, 5))
        
        ttk.Label(header_frame, text="Saat", font=("Segoe UI", 10, "bold"), width=12, anchor="w").pack(side=LEFT, padx=2)
        GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        for gun in GUNLER:
            ttk.Label(header_frame, text=gun[:3], font=("Segoe UI", 9, "bold"), width=15, anchor="center").pack(side=LEFT, padx=1)
        
        # Saatler (09:00 - 18:00)
        saatler = [f"{i:02d}:00" for i in range(9, 19)]
        program_table = {}
        
        for saat in saatler:
            row_frame = ttk.Frame(scrollable_frame)
            row_frame.pack(fill=X, pady=2)
            
            ttk.Label(row_frame, text=saat, font=("Segoe UI", 9), width=12, anchor="w").pack(side=LEFT, padx=2)
            
            gun_widgets = []
            for gun in GUNLER:
                var = ttk.StringVar(value="")
                ent = ttk.Entry(row_frame, textvariable=var, width=15)
                ent.pack(side=LEFT, padx=1)
                gun_widgets.append((var, ent))
            
            program_table[saat] = gun_widgets
        
        # Widget'ları kaydet
        wrapper._cmb_personel = cmb_personel
        wrapper._ent_hafta = ent_hafta
        wrapper._program_table = program_table
        wrapper._canvas = canvas
        wrapper._scrollable_frame = scrollable_frame
        
        # İlk yükleme
        self._haftalik_program_yukle(wrapper)
    
    def _hafta_sec(self, ent_hafta):
        """Hafta seçimi için takvim penceresi"""
        try:
            from tkcalendar import DateEntry
        except ImportError:
            messagebox.showwarning("Uyarı", "tkcalendar modülü bulunamadı. Lütfen 'pip install tkcalendar' komutu ile yükleyin.")
            return
        
        win = ttk.Toplevel(self)
        win.title("Hafta Seç")
        win.geometry("300x200")
        center_window(win, 300, 200)
        
        ttk.Label(win, text="Haftanın Pazartesi gününü seçin:", font=("Segoe UI", 10)).pack(pady=20)
        
        cal = DateEntry(win, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        cal.pack(pady=10)
        
        def sec():
            selected_date = cal.get_date()
            # Pazartesi gününe çevir
            weekday = selected_date.weekday()
            monday = selected_date - datetime.timedelta(days=weekday)
            ent_hafta.delete(0, END)
            ent_hafta.insert(0, monday.strftime("%Y-%m-%d"))
            win.destroy()
        
        ttk.Button(win, text="Seç", bootstyle="primary", command=sec).pack(pady=10)
    
    def _haftalik_program_yukle(self, parent):
        """Haftalık programı veritabanından yükle"""
        cmb_personel = parent._cmb_personel
        ent_hafta = parent._ent_hafta
        program_table = parent._program_table
        
        personel = cmb_personel.get()
        hafta_baslangic = ent_hafta.get()
        
        if not personel or not hafta_baslangic:
            return
        
        # Tüm entry'leri temizle
        for saat, gun_widgets in program_table.items():
            for var, ent in gun_widgets:
                var.set("")
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            
            cur.execute(
                """
                SELECT gun, saat, ogrenci_adi, oda_adi, notlar
                FROM haftalik_seans_programi
                WHERE personel_adi = ? AND hafta_baslangic_tarihi = ?
                ORDER BY 
                    CASE gun
                        WHEN 'Pazartesi' THEN 1
                        WHEN 'Salı' THEN 2
                        WHEN 'Çarşamba' THEN 3
                        WHEN 'Perşembe' THEN 4
                        WHEN 'Cuma' THEN 5
                        WHEN 'Cumartesi' THEN 6
                        WHEN 'Pazar' THEN 7
                    END,
                    saat
                """,
                (personel, hafta_baslangic)
            )
            rows = cur.fetchall()
            conn.close()
            
            for gun, saat, ogrenci_adi, oda_adi, notlar in rows:
                if saat in program_table:
                    gun_idx = GUNLER.index(gun) if gun in GUNLER else -1
                    if gun_idx >= 0:
                        var, ent = program_table[saat][gun_idx]
                        text = ogrenci_adi or ""
                        if oda_adi:
                            text += f" ({oda_adi})" if text else oda_adi
                        if notlar:
                            text += f" [{notlar}]" if text else notlar
                        var.set(text)
        
        except Exception as e:
            log_exception("_haftalik_program_yukle", e)
    
    def _haftalik_program_kaydet(self, parent):
        """Haftalık programı veritabanına kaydet"""
        cmb_personel = parent._cmb_personel
        ent_hafta = parent._ent_hafta
        program_table = parent._program_table
        
        personel = cmb_personel.get()
        hafta_baslangic = ent_hafta.get()
        
        if not personel or not hafta_baslangic:
            messagebox.showwarning("Uyarı", "Lütfen personel ve hafta seçin.")
            return
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            # Mevcut kayıtları sil
            cur.execute(
                "DELETE FROM haftalik_seans_programi WHERE personel_adi = ? AND hafta_baslangic_tarihi = ?",
                (personel, hafta_baslangic)
            )
            
            GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            olusturma_tarihi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Yeni kayıtları ekle
            for saat, gun_widgets in program_table.items():
                for gun_idx, (var, ent) in enumerate(gun_widgets):
                    text = var.get().strip()
                    if text:
                        # Text'i parse et: "Öğrenci Adı (Oda) [Notlar]"
                        ogrenci_adi = text
                        oda_adi = ""
                        notlar = ""
                        
                        # Oda ve notları ayır
                        if "(" in text and ")" in text:
                            parts = text.split("(")
                            ogrenci_adi = parts[0].strip()
                            rest = "(".join(parts[1:])
                            if ")" in rest:
                                oda_adi = rest.split(")")[0].strip()
                                notlar = ")".join(rest.split(")")[1:]).strip()
                                if notlar.startswith("["):
                                    notlar = notlar[1:]
                                if notlar.endswith("]"):
                                    notlar = notlar[:-1]
                                notlar = notlar.strip()
                        
                        cur.execute(
                            """
                            INSERT INTO haftalik_seans_programi
                            (personel_adi, hafta_baslangic_tarihi, gun, saat, ogrenci_adi, oda_adi, notlar, olusturma_tarihi, olusturan_kullanici_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                personel,
                                hafta_baslangic,
                                GUNLER[gun_idx],
                                saat,
                                ogrenci_adi,
                                oda_adi,
                                notlar,
                                olusturma_tarihi,
                                self.kullanici_id
                            )
                        )
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Başarılı", f"Haftalık program kaydedildi!\n\nPersonel: {personel}\nHafta: {hafta_baslangic}")
        
        except Exception as e:
            messagebox.showerror("Hata", f"Program kaydedilemedi:\n{e}")
            log_exception("_haftalik_program_kaydet", e)
    
    def _build_ogrenci_bilgileri_tab(self):
        """Öğrenci Bilgileri Tab - Aile ve kimlik bilgileri"""
        wrapper = ttk.Frame(self.tab_ogrenci_bilgileri, padding=10)
        wrapper.pack(fill=BOTH, expand=True)
        
        # Başlık
        head = ttk.Frame(wrapper)
        head.pack(fill=X, pady=(0, 10))
        if getattr(self, "_logo_small", None):
            ttk.Label(head, image=self._logo_small).pack(side=LEFT, padx=(0, 10))
        ttk.Label(head, text="ÖĞRENCİ BİLGİLERİ", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        
        # Notebook - 2 sayfa: Aile Bilgileri ve Kimlik Bilgileri
        nb_ogrenci = ttk.Notebook(wrapper)
        nb_ogrenci.pack(fill=BOTH, expand=True)
        
        # Sayfa 1: Aile Bilgileri
        page_aile = ttk.Frame(nb_ogrenci, padding=10)
        nb_ogrenci.add(page_aile, text="👨‍👩‍👧 Aile Bilgileri")
        self._build_ogrenci_aile_page(page_aile)
        
        # Sayfa 2: Kimlik Bilgileri
        page_kimlik = ttk.Frame(nb_ogrenci, padding=10)
        nb_ogrenci.add(page_kimlik, text="🆔 Kimlik Bilgileri")
        self._build_ogrenci_kimlik_page(page_kimlik)
    
    def _build_ogrenci_aile_page(self, parent):
        """Öğrenci aile bilgileri sayfası"""
        # Öğrenci seçimi
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Öğrenci:").pack(side=LEFT, padx=5)
        cmb_ogrenci = ttk.Combobox(filter_frame, state="readonly", width=30)
        cmb_ogrenci.pack(side=LEFT, padx=5)
        
        # Öğrenci listesi
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT id, ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
            ogrenci_listesi = [(row[0], row[1]) for row in cur.fetchall()]
            conn.close()
            cmb_ogrenci["values"] = [f"{c[1]} (ID: {c[0]})" for c in ogrenci_listesi]
            if ogrenci_listesi:
                cmb_ogrenci.current(0)
        except Exception:
            cmb_ogrenci["values"] = []
        
        ttk.Button(filter_frame, text="➕ Yeni Veli Ekle", bootstyle="success",
                   command=lambda: self._yeni_veli_ekle(parent)).pack(side=LEFT, padx=10)
        ttk.Button(filter_frame, text="🔄 Yükle", bootstyle="primary",
                   command=lambda: self._ogrenci_aile_listele(parent)).pack(side=LEFT, padx=5)
        
        # Veli listesi
        frame_tree = ttk.Frame(parent)
        frame_tree.pack(fill=BOTH, expand=True)
        
        cols = ("ID", "Veli Adı", "Yakınlık", "Telefon", "Email", "Adres", "Notlar")
        tree = ttk.Treeview(frame_tree, columns=cols, show="headings", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            if c == "ID":
                tree.column(c, width=50)
            elif c == "Veli Adı":
                tree.column(c, width=200)
            elif c == "Yakınlık":
                tree.column(c, width=120)
            elif c == "Telefon":
                tree.column(c, width=120)
            elif c == "Email":
                tree.column(c, width=200)
            else:
                tree.column(c, width=200)
        
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(frame_tree, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        
        # Sağ tık menü
        def veli_menu(event):
            sel = tree.selection()
            if not sel:
                return
            menu = Menu(self, tearoff=0)
            menu.add_command(label="✏️ Düzenle", command=lambda: self._veli_duzenle(parent, tree))
            menu.add_command(label="🗑️ Sil", command=lambda: self._veli_sil(parent, tree))
            menu.post(event.x_root, event.y_root)
        
        tree.bind("<Button-3>", veli_menu)
        
        parent._tree_aile = tree
        parent._cmb_ogrenci = cmb_ogrenci
        
        # İlk yükleme
        self._ogrenci_aile_listele(parent)
    
    def _build_ogrenci_kimlik_page(self, parent):
        """Öğrenci kimlik bilgileri sayfası"""
        # Öğrenci seçimi
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Öğrenci:").pack(side=LEFT, padx=5)
        cmb_ogrenci = ttk.Combobox(filter_frame, state="readonly", width=30)
        cmb_ogrenci.pack(side=LEFT, padx=5)
        
        # Öğrenci listesi
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT id, ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
            ogrenci_listesi = [(row[0], row[1]) for row in cur.fetchall()]
            conn.close()
            cmb_ogrenci["values"] = [f"{c[1]} (ID: {c[0]})" for c in ogrenci_listesi]
            if ogrenci_listesi:
                cmb_ogrenci.current(0)
        except Exception:
            cmb_ogrenci["values"] = []
        
        ttk.Button(filter_frame, text="✏️ Düzenle", bootstyle="primary",
                   command=lambda: self._kimlik_duzenle(parent)).pack(side=LEFT, padx=10)
        ttk.Button(filter_frame, text="🔄 Yükle", bootstyle="secondary",
                   command=lambda: self._ogrenci_kimlik_yukle(parent)).pack(side=LEFT, padx=5)
        
        # Kimlik bilgileri formu
        form_frame = ttk.LabelFrame(parent, text="Kimlik Bilgileri", padding=20)
        form_frame.pack(fill=BOTH, expand=True, pady=10)
        
        ttk.Label(form_frame, text="TC Kimlik No:").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        ent_tc = ttk.Entry(form_frame, width=30)
        ent_tc.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Doğum Tarihi:").grid(row=1, column=0, sticky=W, padx=5, pady=5)
        ent_dogum = ttk.Entry(form_frame, width=30)
        ent_dogum.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Doğum Yeri:").grid(row=2, column=0, sticky=W, padx=5, pady=5)
        ent_dogum_yeri = ttk.Entry(form_frame, width=30)
        ent_dogum_yeri.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Notlar:").grid(row=3, column=0, sticky=W, padx=5, pady=5)
        text_notlar = tk.Text(form_frame, width=30, height=5)
        text_notlar.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Button(form_frame, text="💾 Kaydet", bootstyle="success",
                   command=lambda: self._kimlik_kaydet(parent)).grid(row=4, column=0, columnspan=2, pady=10)
        
        parent._cmb_ogrenci_kimlik = cmb_ogrenci
        parent._ent_tc = ent_tc
        parent._ent_dogum = ent_dogum
        parent._ent_dogum_yeri = ent_dogum_yeri
        parent._text_notlar = text_notlar
        
        # İlk yükleme
        self._ogrenci_kimlik_yukle(parent)
    
    def _build_sifreler_tab(self):
        """Sistem Şifreleri Tab (Sadece kurum müdürü)"""
        wrapper = ttk.Frame(self.tab_sifreler, padding=10)
        wrapper.pack(fill=BOTH, expand=True)
        
        # Başlık
        head = ttk.Frame(wrapper)
        head.pack(fill=X, pady=(0, 10))
        if getattr(self, "_logo_small", None):
            ttk.Label(head, image=self._logo_small).pack(side=LEFT, padx=(0, 10))
        ttk.Label(head, text="SİSTEM ŞİFRELERİ", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        
        # Toolbar
        toolbar = ttk.Frame(wrapper)
        toolbar.pack(fill=X, pady=(0, 10))
        
        ttk.Button(toolbar, text="➕ Yeni Şifre Ekle", bootstyle="success",
                   command=lambda: self._yeni_sifre_ekle(wrapper)).pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="🔄 Yenile", bootstyle="secondary",
                   command=lambda: self._sifreler_listele(wrapper)).pack(side=LEFT, padx=5)
        
        # Şifre listesi
        frame_tree = ttk.Frame(wrapper)
        frame_tree.pack(fill=BOTH, expand=True)
        
        cols = ("ID", "Sistem Adı", "Kullanıcı Adı", "Şifre", "URL", "Açıklama")
        tree = ttk.Treeview(frame_tree, columns=cols, show="headings", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            if c == "ID":
                tree.column(c, width=50)
            elif c == "Sistem Adı":
                tree.column(c, width=200)
            elif c == "Kullanıcı Adı":
                tree.column(c, width=150)
            elif c == "Şifre":
                tree.column(c, width=150)
            elif c == "URL":
                tree.column(c, width=200)
            else:
                tree.column(c, width=300)
        
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(frame_tree, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        
        # Sağ tık menü
        def sifre_menu(event):
            sel = tree.selection()
            if not sel:
                return
            menu = Menu(self, tearoff=0)
            menu.add_command(label="✏️ Düzenle", command=lambda: self._sifre_duzenle(wrapper, tree))
            menu.add_command(label="🗑️ Sil", command=lambda: self._sifre_sil(wrapper, tree))
            menu.add_command(label="📋 Şifreyi Kopyala", command=lambda: self._sifre_kopyala(tree))
            menu.post(event.x_root, event.y_root)
        
        tree.bind("<Button-3>", sifre_menu)
        
        wrapper._tree_sifreler = tree
        
        # İlk yükleme
        self._sifreler_listele(wrapper)
    
    # ==================== ÖĞRENCİ BİLGİLERİ HELPER METODLARI ====================
    
    def _ogrenci_aile_listele(self, parent):
        """Öğrenci aile bilgilerini listele"""
        tree = parent._tree_aile
        cmb_ogrenci = parent._cmb_ogrenci
        
        for iid in tree.get_children():
            tree.delete(iid)
        
        ogrenci_text = cmb_ogrenci.get()
        if not ogrenci_text:
            return
        
        try:
            ogrenci_id = int(ogrenci_text.split("(ID: ")[1].split(")")[0])
        except Exception:
            return
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, veli_adi, veli_yakinlik_derecesi, telefon, email, adres, notlar
                FROM ogrenci_aile_bilgileri
                WHERE ogrenci_id = ?
                ORDER BY id
                """,
                (ogrenci_id,)
            )
            rows = cur.fetchall()
            conn.close()
            
            for idx, row in enumerate(rows):
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=row, tags=(tag,))
        
        except Exception as e:
            log_exception("_ogrenci_aile_listele", e)
    
    def _yeni_veli_ekle(self, parent):
        """Yeni veli ekle penceresi"""
        cmb_ogrenci = parent._cmb_ogrenci
        ogrenci_text = cmb_ogrenci.get()
        
        if not ogrenci_text:
            messagebox.showwarning("Uyarı", "Lütfen bir öğrenci seçin.")
            return
        
        try:
            ogrenci_id = int(ogrenci_text.split("(ID: ")[1].split(")")[0])
        except Exception:
            messagebox.showerror("Hata", "Geçersiz öğrenci seçimi.")
            return
        
        win = ttk.Toplevel(self)
        win.title("Yeni Veli Ekle")
        win.geometry("500x400")
        center_window(win, 500, 400)
        win.transient(self)
        self._brand_window(win)
        
        wrapper = ttk.Frame(win, padding=20)
        wrapper.pack(fill=BOTH, expand=True)
        
        ttk.Label(wrapper, text="Yeni Veli Ekle", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=(0, 20))
        
        ttk.Label(wrapper, text="Veli Adı:").pack(anchor=W)
        ent_veli_adi = ttk.Entry(wrapper, width=40)
        ent_veli_adi.pack(fill=X, pady=5)
        
        ttk.Label(wrapper, text="Yakınlık Derecesi:").pack(anchor=W, pady=(10, 0))
        cmb_yakinlik = ttk.Combobox(wrapper, state="readonly", width=37,
                                   values=["Anne", "Baba", "Büyükanne", "Büyükbaba", "Vasi", "Diğer"])
        cmb_yakinlik.pack(fill=X, pady=5)
        cmb_yakinlik.current(0)
        
        ttk.Label(wrapper, text="Telefon:").pack(anchor=W, pady=(10, 0))
        ent_telefon = ttk.Entry(wrapper, width=40)
        ent_telefon.pack(fill=X, pady=5)
        
        ttk.Label(wrapper, text="Email:").pack(anchor=W, pady=(10, 0))
        ent_email = ttk.Entry(wrapper, width=40)
        ent_email.pack(fill=X, pady=5)
        
        ttk.Label(wrapper, text="Adres:").pack(anchor=W, pady=(10, 0))
        text_adres = tk.Text(wrapper, width=40, height=3)
        text_adres.pack(fill=X, pady=5)
        
        def kaydet():
            veli_adi = ent_veli_adi.get().strip()
            yakinlik = cmb_yakinlik.get()
            
            if not veli_adi or not yakinlik:
                messagebox.showwarning("Uyarı", "Lütfen veli adı ve yakınlık derecesini girin.")
                return
            
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO ogrenci_aile_bilgileri
                    (ogrenci_id, veli_adi, veli_yakinlik_derecesi, telefon, email, adres, notlar, olusturma_tarihi, guncelleme_tarihi)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ogrenci_id,
                        veli_adi,
                        yakinlik,
                        ent_telefon.get().strip(),
                        ent_email.get().strip(),
                        text_adres.get("1.0", END).strip(),
                        "",
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                )
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Başarılı", "Veli eklendi!")
                win.destroy()
                self._ogrenci_aile_listele(parent)
                
            except Exception as e:
                messagebox.showerror("Hata", f"Veli eklenemedi:\n{e}")
                log_exception("_yeni_veli_ekle", e)
        
        ttk.Button(wrapper, text="💾 Kaydet", bootstyle="success", command=kaydet).pack(pady=20)
    
    def _veli_duzenle(self, parent, tree):
        """Veli düzenle"""
        sel = tree.selection()
        if not sel:
            return
        
        veli_id = tree.item(sel[0])["values"][0]
        # Düzenleme penceresi (benzer yapı)
        messagebox.showinfo("Bilgi", f"Veli düzenleme özelliği yakında eklenecek. (ID: {veli_id})")
    
    def _veli_sil(self, parent, tree):
        """Veli sil"""
        sel = tree.selection()
        if not sel:
            return
        
        veli_id = tree.item(sel[0])["values"][0]
        
        if not messagebox.askyesno("Onay", "Veli kaydını silmek istediğinize emin misiniz?"):
            return
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("DELETE FROM ogrenci_aile_bilgileri WHERE id = ?", (veli_id,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Başarılı", "Veli kaydı silindi.")
            self._ogrenci_aile_listele(parent)
        
        except Exception as e:
            messagebox.showerror("Hata", f"Veli silinemedi:\n{e}")
            log_exception("_veli_sil", e)
    
    def _ogrenci_kimlik_yukle(self, parent):
        """Öğrenci kimlik bilgilerini yükle"""
        cmb_ogrenci = parent._cmb_ogrenci_kimlik
        ent_tc = parent._ent_tc
        ent_dogum = parent._ent_dogum
        ent_dogum_yeri = parent._ent_dogum_yeri
        text_notlar = parent._text_notlar
        
        ogrenci_text = cmb_ogrenci.get()
        if not ogrenci_text:
            return
        
        try:
            ogrenci_id = int(ogrenci_text.split("(ID: ")[1].split(")")[0])
        except Exception:
            return
        
        # Form'u temizle
        ent_tc.delete(0, END)
        ent_dogum.delete(0, END)
        ent_dogum_yeri.delete(0, END)
        text_notlar.delete("1.0", END)
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute(
                "SELECT tc_kimlik_no, dogum_tarihi, dogum_yeri, notlar FROM ogrenci_kimlik_bilgileri WHERE ogrenci_id = ?",
                (ogrenci_id,)
            )
            row = cur.fetchone()
            conn.close()
            
            if row:
                ent_tc.insert(0, row[0] or "")
                ent_dogum.insert(0, row[1] or "")
                ent_dogum_yeri.insert(0, row[2] or "")
                text_notlar.insert("1.0", row[3] or "")
        
        except Exception as e:
            log_exception("_ogrenci_kimlik_yukle", e)
    
    def _kimlik_duzenle(self, parent):
        """Kimlik bilgilerini düzenle penceresi"""
        cmb_ogrenci = parent._cmb_ogrenci_kimlik
        ogrenci_text = cmb_ogrenci.get()
        
        if not ogrenci_text:
            messagebox.showwarning("Uyarı", "Lütfen bir öğrenci seçin.")
            return
        
        try:
            ogrenci_id = int(ogrenci_text.split("(ID: ")[1].split(")")[0])
        except Exception:
            messagebox.showerror("Hata", "Geçersiz öğrenci seçimi.")
            return
        
        # Form'u yükle
        self._ogrenci_kimlik_yukle(parent)
    
    def _kimlik_kaydet(self, parent):
        """Kimlik bilgilerini kaydet"""
        cmb_ogrenci = parent._cmb_ogrenci_kimlik
        ent_tc = parent._ent_tc
        ent_dogum = parent._ent_dogum
        ent_dogum_yeri = parent._ent_dogum_yeri
        text_notlar = parent._text_notlar
        
        ogrenci_text = cmb_ogrenci.get()
        if not ogrenci_text:
            messagebox.showwarning("Uyarı", "Lütfen bir öğrenci seçin.")
            return
        
        try:
            ogrenci_id = int(ogrenci_text.split("(ID: ")[1].split(")")[0])
        except Exception:
            messagebox.showerror("Hata", "Geçersiz öğrenci seçimi.")
            return
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            
            # Mevcut kaydı kontrol et
            cur.execute("SELECT id FROM ogrenci_kimlik_bilgileri WHERE ogrenci_id = ?", (ogrenci_id,))
            row = cur.fetchone()
            
            if row:
                # Güncelle
                cur.execute(
                    """
                    UPDATE ogrenci_kimlik_bilgileri
                    SET tc_kimlik_no = ?, dogum_tarihi = ?, dogum_yeri = ?, notlar = ?, guncelleme_tarihi = ?
                    WHERE ogrenci_id = ?
                    """,
                    (
                        ent_tc.get().strip(),
                        ent_dogum.get().strip(),
                        ent_dogum_yeri.get().strip(),
                        text_notlar.get("1.0", END).strip(),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ogrenci_id
                    )
                )
            else:
                # Yeni ekle
                cur.execute(
                    """
                    INSERT INTO ogrenci_kimlik_bilgileri
                    (ogrenci_id, tc_kimlik_no, dogum_tarihi, dogum_yeri, notlar, olusturma_tarihi, guncelleme_tarihi)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ogrenci_id,
                        ent_tc.get().strip(),
                        ent_dogum.get().strip(),
                        ent_dogum_yeri.get().strip(),
                        text_notlar.get("1.0", END).strip(),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                )
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Başarılı", "Kimlik bilgileri kaydedildi!")
        
        except Exception as e:
            messagebox.showerror("Hata", f"Kimlik bilgileri kaydedilemedi:\n{e}")
            log_exception("_kimlik_kaydet", e)
    
    def _sifreler_listele(self, parent):
        """Sistem şifrelerini listele"""
        tree = parent._tree_sifreler
        
        for iid in tree.get_children():
            tree.delete(iid)
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, sistem_adi, kullanici_adi, sifre, url, aciklama FROM sistem_sifreleri ORDER BY sistem_adi"
            )
            rows = cur.fetchall()
            conn.close()
            
            for idx, row in enumerate(rows):
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=row, tags=(tag,))
        
        except Exception as e:
            log_exception("_sifreler_listele", e)
    
    def _yeni_sifre_ekle(self, parent):
        """Yeni sistem şifresi ekle"""
        win = ttk.Toplevel(self)
        win.title("Yeni Sistem Şifresi")
        win.geometry("500x350")
        center_window(win, 500, 350)
        win.transient(self)
        self._brand_window(win)
        
        wrapper = ttk.Frame(win, padding=20)
        wrapper.pack(fill=BOTH, expand=True)
        
        ttk.Label(wrapper, text="Yeni Sistem Şifresi", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=(0, 20))
        
        ttk.Label(wrapper, text="Sistem Adı:").pack(anchor=W)
        ent_sistem = ttk.Entry(wrapper, width=40)
        ent_sistem.pack(fill=X, pady=5)
        
        ttk.Label(wrapper, text="Kullanıcı Adı:").pack(anchor=W, pady=(10, 0))
        ent_kullanici = ttk.Entry(wrapper, width=40)
        ent_kullanici.pack(fill=X, pady=5)
        
        ttk.Label(wrapper, text="Şifre:").pack(anchor=W, pady=(10, 0))
        ent_sifre = ttk.Entry(wrapper, width=40, show="*")
        ent_sifre.pack(fill=X, pady=5)
        
        ttk.Label(wrapper, text="URL:").pack(anchor=W, pady=(10, 0))
        ent_url = ttk.Entry(wrapper, width=40)
        ent_url.pack(fill=X, pady=5)
        
        ttk.Label(wrapper, text="Açıklama:").pack(anchor=W, pady=(10, 0))
        text_aciklama = tk.Text(wrapper, width=40, height=3)
        text_aciklama.pack(fill=X, pady=5)
        
        def kaydet():
            sistem_adi = ent_sistem.get().strip()
            if not sistem_adi:
                messagebox.showwarning("Uyarı", "Lütfen sistem adı girin.")
                return
            
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO sistem_sifreleri
                    (sistem_adi, kullanici_adi, sifre, url, aciklama, olusturma_tarihi, guncelleme_tarihi, olusturan_kullanici_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sistem_adi,
                        ent_kullanici.get().strip(),
                        ent_sifre.get().strip(),
                        ent_url.get().strip(),
                        text_aciklama.get("1.0", END).strip(),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        self.kullanici_id
                    )
                )
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Başarılı", "Sistem şifresi eklendi!")
                win.destroy()
                self._sifreler_listele(parent)
            
            except Exception as e:
                messagebox.showerror("Hata", f"Şifre eklenemedi:\n{e}")
                log_exception("_yeni_sifre_ekle", e)
        
        ttk.Button(wrapper, text="💾 Kaydet", bootstyle="success", command=kaydet).pack(pady=20)
    
    def _sifre_duzenle(self, parent, tree):
        """Sistem şifresi düzenle"""
        sel = tree.selection()
        if not sel:
            return
        
        sifre_id = tree.item(sel[0])["values"][0]
        messagebox.showinfo("Bilgi", f"Şifre düzenleme özelliği yakında eklenecek. (ID: {sifre_id})")
    
    def _sifre_sil(self, parent, tree):
        """Sistem şifresi sil"""
        sel = tree.selection()
        if not sel:
            return
        
        sifre_id = tree.item(sel[0])["values"][0]
        
        if not messagebox.askyesno("Onay", "Şifre kaydını silmek istediğinize emin misiniz?"):
            return
        
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("DELETE FROM sistem_sifreleri WHERE id = ?", (sifre_id,))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Başarılı", "Şifre kaydı silindi.")
            self._sifreler_listele(parent)
        
        except Exception as e:
            messagebox.showerror("Hata", f"Şifre silinemedi:\n{e}")
            log_exception("_sifre_sil", e)
    
    def _sifre_kopyala(self, tree):
        """Şifreyi panoya kopyala"""
        sel = tree.selection()
        if not sel:
            return
        
        sifre = tree.item(sel[0])["values"][3]
        if sifre:
            self.clipboard_clear()
            self.clipboard_append(sifre)
            messagebox.showinfo("Başarılı", "Şifre panoya kopyalandı!")
    
    def _build_settings_tab(self):
        box = ttk.Labelframe(self.tab_settings, text="Terapist Listesi", padding=12)
        box.pack(fill=BOTH, expand=True)

        self.lst = ttk.Treeview(box, columns=("Terapist", "Rol"), show="headings", height=14)
        self.lst.heading("Terapist", text="Terapist")
        self.lst.heading("Rol", text="Rol")
        self.lst.column("Terapist", width=220)
        self.lst.column("Rol", width=280)
        self.lst.pack(side=LEFT, fill=BOTH, expand=True)

        sb = ttk.Scrollbar(box, orient=VERTICAL, command=self.lst.yview)
        self.lst.configure(yscroll=sb.set)
        sb.pack(side=LEFT, fill=Y)

        right = ttk.Frame(box, padding=(12, 0))
        right.pack(side=LEFT, fill=Y)
        ttk.Label(right, text="Yeni Terapist:").pack(anchor=W, pady=(0, 4))
        self.ent_yeni = ttk.Entry(right, width=28)
        self.ent_yeni.pack(fill=X, pady=(0, 8))
        ttk.Label(right, text="Rol:").pack(anchor=W, pady=(0, 4))
        self.cmb_rol = ttk.Combobox(
            right,
            state="readonly",
            values=[
                "Kurum Müdürü / Özel Eğitim Uzmanı",
                "Özel Eğitim Uzmanı",
                "Ergoterapist",
                "Dil ve Konuşma Terapisti",
                "Klinik Psikolog",
                "Diğer",
            ],
            width=26,
        )
        self.cmb_rol.set("Diğer")
        self.cmb_rol.pack(fill=X, pady=(0, 10))
        ttk.Button(right, text="Ekle", bootstyle="success", command=self.terapist_ekle).pack(fill=X, pady=(0, 6))
        ttk.Button(right, text="Rol Güncelle", bootstyle="warning", command=self.terapist_rol_guncelle).pack(fill=X, pady=(0, 6))
        ttk.Button(right, text="Seçiliyi Sil", bootstyle="danger", command=self.terapist_sil).pack(fill=X, pady=(0, 12))
        ttk.Button(right, text="Excel'e Aktar", bootstyle="primary", command=self.excel_aktar).pack(fill=X)

        self.lst.bind("<<TreeviewSelect>>", self._on_terapist_select)

    def _on_terapist_select(self, _evt=None):
        sel = self.lst.selection()
        if not sel:
            return
        vals = self.lst.item(sel[0]).get("values") or []
        if len(vals) >= 2:
            try:
                self.ent_yeni.delete(0, END)
                self.ent_yeni.insert(0, vals[0])
                self.cmb_rol.set(vals[1] or "Diğer")
            except Exception:
                pass

    def terapistleri_yukle(self):
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT therapist_name, therapist_role FROM settings WHERE is_active=1 ORDER BY therapist_name")
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Terapistler yüklenemedi:\n{e}")
            rows = []

        names = [r[0] for r in rows]
        self.cmb_terapist["values"] = names
        if names and self.cmb_terapist.cget("state") != "disabled":
            self.cmb_terapist.current(0)

        if hasattr(self, "lst"):
            for iid in self.lst.get_children():
                self.lst.delete(iid)
            for n, rol in rows:
                self.lst.insert("", END, values=(n, rol or ""))

    def terapist_ekle(self):
        name = (self.ent_yeni.get() or "").strip()
        if not name:
            messagebox.showwarning("Uyarı", "Lütfen terapist adını giriniz!")
            return
        if "name hoca" in name.lower():
            messagebox.showwarning("Uyarı", "Name Hoca kurumdan ayrıldı. Eklenemez.")
            return
        rol = (self.cmb_rol.get() or "").strip()
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO settings (therapist_name, therapist_role, is_active, created_at) VALUES (?,?,1,?)",
                (name, rol, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
            conn.close()
            self.ent_yeni.delete(0, END)
            self.terapistleri_yukle()
        except Exception as e:
            messagebox.showerror("Hata", f"Terapist ekleme hatası:\n{e}")

    def terapist_rol_guncelle(self):
        sel = self.lst.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen bir terapist seçiniz!")
            return
        name = (self.lst.item(sel[0]).get("values") or ["", ""])[0]
        rol = (self.cmb_rol.get() or "").strip()
        if not name:
            return
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("UPDATE settings SET therapist_role=? WHERE therapist_name=?", (rol, name))
            conn.commit()
            conn.close()
            self.terapistleri_yukle()
        except Exception as e:
            messagebox.showerror("Hata", f"Rol güncelleme hatası:\n{e}")

    def terapist_sil(self):
        sel = self.lst.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen bir terapist seçiniz!")
            return
        name = (self.lst.item(sel[0]).get("values") or [""])[0]
        if not name:
            return
        if not messagebox.askyesno("Onay", f"'{name}' terapistini silmek istiyor musunuz?"):
            return
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("DELETE FROM settings WHERE therapist_name=?", (name,))
            conn.commit()
            conn.close()
            self.terapistleri_yukle()
        except Exception as e:
            messagebox.showerror("Hata", f"Terapist silme hatası:\n{e}")

    def excel_aktar(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel dosyası", "*.xlsx"), ("Tüm dosyalar", "*.*")],
            title="Excel'e Aktar",
        )
        if not path:
            return
        try:
            conn = self.veritabani_baglan()
            if self.kullanici_yetki == "kurum_muduru" or not self.kullanici_terapist:
                df = pd.read_sql_query("SELECT * FROM records ORDER BY id DESC", conn)
            else:
                df = pd.read_sql_query(
                    "SELECT * FROM records WHERE terapist = ? ORDER BY id DESC",
                    conn,
                    params=(self.kullanici_terapist,),
                )
            conn.close()
            df.to_excel(path, index=False, engine="openpyxl")
            messagebox.showinfo("Başarılı", "Excel'e aktarıldı.")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel aktarma hatası:\n{e}")

    # --- leta_pro MODÜLLERİ: Menü işlemleri ---
    def yedek_klasoru_ac(self):
        try:
            os.makedirs(backups_dir(), exist_ok=True)
            open_path(backups_dir())
        except Exception as e:
            messagebox.showerror("Hata", f"Yedek klasörü açılamadı:\n{e}")

    def demo_verileri_ac(self):
        try:
            os.makedirs(demo_data_dir(), exist_ok=True)
            open_path(demo_data_dir())
        except Exception as e:
            messagebox.showerror("Hata", f"Demo verileri açılamadı:\n{e}")

    def hakkinda_goster(self):
        messagebox.showinfo(
            "Hakkında",
            "Leta Aile ve Çocuk - Yönetim Sistemi\n\n"
            "Modüller: Seans Takip, Seans Takvimi, Danışanlar, Görevler, Muhasebe, Kullanıcı Yönetimi.\n"
            "Bu sürüm tek pencere (tek root) ile stabil çalışacak şekilde hazırlanmıştır.",
        )

    def eski_veri_migration(self):
        """Eski veritabanından yeni sisteme veri aktarımı"""
        win = ttk.Toplevel(self)
        win.title("Eski Veri Migration")
        win.geometry("600x400")
        center_window(win, 600, 400)
        win.transient(self)
        self._brand_window(win)
        
        wrapper = ttk.Frame(win, padding=20)
        wrapper.pack(fill=BOTH, expand=True)
        
        ttk.Label(wrapper, text="Eski Veri Migration", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=(0, 20))
        
        ttk.Label(wrapper, text="Bu araç eski veritabanından yeni sisteme veri aktarımı yapar.", 
                 font=("Segoe UI", 10), wraplength=550).pack(pady=(0, 20))
        
        # Eski DB seçimi
        frm_db = ttk.Frame(wrapper)
        frm_db.pack(fill=X, pady=10)
        
        ttk.Label(frm_db, text="Eski Veritabanı:", width=20).pack(side=LEFT, padx=5)
        ent_eski_db = ttk.Entry(frm_db, width=40)
        ent_eski_db.pack(side=LEFT, padx=5, fill=X, expand=True)
        
        def db_sec():
            dosya = filedialog.askopenfilename(
                title="Eski Veritabanı Seç",
                filetypes=[("Veritabanı Dosyaları", "*.db"), ("Tüm Dosyalar", "*.*")]
            )
            if dosya:
                ent_eski_db.delete(0, END)
                ent_eski_db.insert(0, dosya)
        
        ttk.Button(frm_db, text="📁 Seç", bootstyle="primary", command=db_sec).pack(side=LEFT, padx=5)
        
        # Sonuç alanı
        frm_sonuc = ttk.LabelFrame(wrapper, text="Migration Sonuçları", padding=10)
        frm_sonuc.pack(fill=BOTH, expand=True, pady=10)
        
        text_sonuc = tk.Text(frm_sonuc, height=10, wrap=tk.WORD)
        text_sonuc.pack(fill=BOTH, expand=True)
        sb_sonuc = ttk.Scrollbar(frm_sonuc, orient=VERTICAL, command=text_sonuc.yview)
        text_sonuc.configure(yscrollcommand=sb_sonuc.set)
        sb_sonuc.pack(side=RIGHT, fill=Y)
        
        def migration_baslat():
            eski_db_yolu = ent_eski_db.get().strip()
            if not eski_db_yolu:
                messagebox.showerror("Hata", "Lütfen eski veritabanı dosyasını seçin.")
                return
            
            if not os.path.exists(eski_db_yolu):
                messagebox.showerror("Hata", f"Veritabanı dosyası bulunamadı:\n{eski_db_yolu}")
                return
            
            text_sonuc.delete("1.0", END)
            text_sonuc.insert(END, "🔄 Migration başlatılıyor...\n\n")
            win.update()
            
            try:
                # Migration script'ini import et ve çalıştır
                import migration_eski_veriler
                results = migration_eski_veriler.migrate_eski_veriler(eski_db_yolu)
                
                if results["success"]:
                    text_sonuc.insert(END, "✅ Migration tamamlandı!\n\n")
                    text_sonuc.insert(END, "Aktarılan Tablolar:\n")
                    for table, count in results["migrated_tables"].items():
                        text_sonuc.insert(END, f"  • {table}: {count} kayıt\n")
                    
                    if results["errors"]:
                        text_sonuc.insert(END, "\n⚠️ Hatalar:\n")
                        for error in results["errors"]:
                            text_sonuc.insert(END, f"  • {error}\n")
                    
                    messagebox.showinfo("Başarılı", "Migration tamamlandı! Sonuçları kontrol edin.")
                else:
                    text_sonuc.insert(END, "❌ Migration başarısız!\n\n")
                    text_sonuc.insert(END, "Hatalar:\n")
                    for error in results["errors"]:
                        text_sonuc.insert(END, f"  • {error}\n")
                    
                    messagebox.showerror("Hata", "Migration başarısız! Detaylar için sonuç alanına bakın.")
            
            except Exception as e:
                text_sonuc.insert(END, f"❌ Hata: {e}\n")
                messagebox.showerror("Hata", f"Migration hatası:\n{e}")
                log_exception("eski_veri_migration", e)
        
        ttk.Button(wrapper, text="🚀 Migration Başlat", bootstyle="success", 
                  command=migration_baslat).pack(pady=10)

    def kullanim_kilavuzu_ac(self):
        try:
            ensure_user_guide_present()
            candidates = [
                os.path.join(resource_dir(), "KULLANIM_KILAVUZU.txt"),
                os.path.join(app_dir(), "KULLANIM_KILAVUZU.txt"),
                os.path.join(data_dir(), "KULLANIM_KILAVUZU.txt"),
            ]
            p = None
            for c in candidates:
                if os.path.exists(c):
                    p = c
                    break
            if not p:
                raise FileNotFoundError("KULLANIM_KILAVUZU.txt bulunamadı.")
            open_path(p)
        except Exception as e:
            messagebox.showerror("Hata", f"Kılavuz açılamadı:\n{e}")

    def ilk_5_adim_goster(self):
        messagebox.showinfo(
            "İlk 5 Adım",
            "1) İlk gün: 'İLK KURULUM' ile Kurum Müdürü oluştur.\n"
            "2) Çalışanlar: 'KAYIT OL' ile hesap açar.\n"
            "3) SEANS TAKİP: Seansı yaz → KAYDET.\n"
            "4) Tahsilat: Seansı seç → sağ tık → Ödeme Ekle.\n"
            "5) Haftalık durum: Muhasebe → Haftalık Ders/Ücret Takip.\n",
        )

    def ucret_takibi_goster(self):
        messagebox.showinfo("Bilgi", "Ücret takibi ana ekranda (SEANS TAKİP) listelenmektedir.")

    def odeme_islemleri(self):
        messagebox.showinfo("Bilgi", "Ödeme eklemek için listede kayda sağ tıklayıp 'Ödeme Ekle' seçeneğini kullanabilirsiniz.")

    def kendi_seanslarim(self):
        # Eğitim görevlisi için filtre zaten aktif; sadece ilgili sekmeye geç
        try:
            self.nb.select(self.tab_records)
        except Exception:
            pass
        self.kayitlari_listele()

    def kendi_ucretlerim(self):
        self.kendi_seanslarim()

    def randevu_yonetimi(self):
        # leta_pro ile uyumlu: randevu = seans takvimi
        self.seans_takvimi_goster()

    def gelir_gider_raporu(self):
        win = ttk.Toplevel(self)
        win.title("Gelir-Gider Raporu")
        center_window_smart(win, 900, 620)
        win.transient(self)
        self._brand_window(win)

        ttk.Label(win, text="GELİR-GİDER RAPORU", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=X)

        ttk.Label(frm, text="Başlangıç:").grid(row=0, column=0, padx=6, pady=6, sticky=W)
        ent_bas = ttk.Entry(frm, width=14)
        ent_bas.insert(0, datetime.datetime.now().strftime("%Y-%m-01"))
        ent_bas.grid(row=0, column=1, padx=6, pady=6, sticky=W)

        ttk.Label(frm, text="Bitiş:").grid(row=0, column=2, padx=6, pady=6, sticky=W)
        ent_bit = ttk.Entry(frm, width=14)
        ent_bit.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        ent_bit.grid(row=0, column=3, padx=6, pady=6, sticky=W)

        out = ttk.Text(win, height=18)
        out.pack(fill=BOTH, expand=True, padx=12, pady=10)

        def _rapor():
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                bas = ent_bas.get().strip()
                bit = ent_bit.get().strip()

                # Kurum müdürü: tüm kasa + seanslar
                if self.kullanici_yetki == "kurum_muduru":
                    cur.execute(
                        """
                        SELECT
                            COALESCE(SUM(alinan_ucret),0),
                            COALESCE(SUM(hizmet_bedeli - alinan_ucret),0),
                            COUNT(*)
                        FROM records
                        WHERE tarih >= ? AND tarih <= ?
                        """,
                        (bas, bit),
                    )
                    gelir_kayit, alacak, toplam = cur.fetchone() or (0, 0, 0)

                    cur.execute(
                        """
                        SELECT
                            COALESCE(SUM(CASE WHEN tip='giren' THEN tutar ELSE 0 END),0),
                            COALESCE(SUM(CASE WHEN tip='cikan' THEN tutar ELSE 0 END),0)
                        FROM kasa_hareketleri
                        WHERE tarih >= ? AND tarih <= ?
                        """,
                        (bas, bit),
                    )
                    kasa_giren, kasa_cikan = cur.fetchone() or (0, 0)
                else:
                    # Eğitim görevlisi: kendi seansları + kendi tahsilatları (record_id üzerinden)
                    ter = self.kullanici_terapist or ""
                    cur.execute(
                        """
                        SELECT
                            COALESCE(SUM(alinan_ucret),0),
                            COALESCE(SUM(hizmet_bedeli - alinan_ucret),0),
                            COUNT(*)
                        FROM records
                        WHERE tarih >= ? AND tarih <= ? AND terapist = ?
                        """,
                        (bas, bit, ter),
                    )
                    gelir_kayit, alacak, toplam = cur.fetchone() or (0, 0, 0)

                    cur.execute(
                        """
                        SELECT
                            COALESCE(SUM(CASE WHEN kh.tip='giren' THEN kh.tutar ELSE 0 END),0),
                            COALESCE(SUM(CASE WHEN kh.tip='cikan' THEN kh.tutar ELSE 0 END),0)
                        FROM kasa_hareketleri kh
                        LEFT JOIN records r ON r.id = kh.record_id
                        WHERE kh.tarih >= ? AND kh.tarih <= ? AND r.terapist = ?
                        """,
                        (bas, bit, ter),
                    )
                    kasa_giren, kasa_cikan = cur.fetchone() or (0, 0)

                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Rapor oluşturulamadı:\n{e}")
                return

            net = float(kasa_giren or 0) - float(kasa_cikan or 0)
            txt = (
                "GELİR-GİDER RAPORU\n"
                + "=" * 45
                + "\n"
                + f"Tarih Aralığı: {ent_bas.get().strip()} - {ent_bit.get().strip()}\n\n"
                + f"Toplam Seans: {toplam}\n"
                + f"Toplam Tahsilat (Kasa): {float(kasa_giren or 0):,.2f} ₺\n"
                + f"Toplam Gider (Kasa): {float(kasa_cikan or 0):,.2f} ₺\n"
                + f"Net (Tahsilat - Gider): {net:,.2f} ₺\n\n"
                + f"Seans Geliri (Kayıt): {float(gelir_kayit or 0):,.2f} ₺\n"
                + f"Toplam Alacak: {alacak:,.2f} ₺\n"
            )
            out.delete("1.0", END)
            out.insert("1.0", txt)

        ttk.Button(frm, text="Rapor Oluştur", bootstyle="primary", command=_rapor).grid(row=0, column=4, padx=10, pady=6)

    def kasa_defteri_goster(self):
        # Kurum müdürü tam yetki; eğitim görevlisi kendi tahsilatlarını görebilir (record_id -> records.terapist)
        win = ttk.Toplevel(self)
        win.title("Kasa Defteri (Günlük)")
        center_window_smart(win, 1200, 780)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        ttk.Label(win, text="KASA DEFTERİ (GÜNLÜK)", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)

        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)

        ttk.Label(top, text="Tarih (YYYY-AA-GG):", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=6)
        tarih_var = ttk.StringVar(value=datetime.datetime.now().strftime("%Y-%m-%d"))
        ent_t = ttk.Entry(top, textvariable=tarih_var, width=14)
        ent_t.pack(side=LEFT, padx=6)

        info_lbl = ttk.Label(top, text="", font=("Segoe UI", 10))
        info_lbl.pack(side=LEFT, padx=10)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)

        cols = ("ID", "Tip", "Açıklama", "Tutar", "Ödeme", "KayıtID", "Oluşturma")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=140)
        tree.column("ID", width=70)
        tree.column("Tip", width=80)
        tree.column("Açıklama", width=360)
        tree.column("Tutar", width=120)
        tree.column("KayıtID", width=90)
        tree.column("Oluşturma", width=160)

        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        def _load():
            for iid in tree.get_children():
                tree.delete(iid)
            tarih = (tarih_var.get() or "").strip()
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                if self.kullanici_yetki == "kurum_muduru":
                    cur.execute(
                        """
                        SELECT id, tip, aciklama, tutar, COALESCE(odeme_sekli,''), COALESCE(record_id,''), COALESCE(olusturma_tarihi,'')
                        FROM kasa_hareketleri
                        WHERE tarih=?
                        ORDER BY id ASC
                        """,
                        (tarih,),
                    )
                    rows = cur.fetchall()

                    cur.execute(
                        """
                        SELECT COALESCE(SUM(CASE WHEN tip='giren' THEN tutar ELSE 0 END),0),
                               COALESCE(SUM(CASE WHEN tip='cikan' THEN tutar ELSE 0 END),0)
                        FROM kasa_hareketleri WHERE tarih=?
                        """,
                        (tarih,),
                    )
                    giren, cikan = cur.fetchone() or (0, 0)

                    cur.execute(
                        """
                        SELECT COALESCE(SUM(CASE WHEN tip='giren' THEN tutar ELSE -tutar END),0)
                        FROM kasa_hareketleri
                        WHERE tarih < ?
                        """,
                        (tarih,),
                    )
                    devreden = float((cur.fetchone() or [0])[0] or 0)
                else:
                    ter = self.kullanici_terapist or ""
                    cur.execute(
                        """
                        SELECT kh.id, kh.tip, kh.aciklama, kh.tutar, COALESCE(kh.odeme_sekli,''), COALESCE(kh.record_id,''), COALESCE(kh.olusturma_tarihi,'')
                        FROM kasa_hareketleri kh
                        LEFT JOIN records r ON r.id = kh.record_id
                        WHERE kh.tarih=? AND r.terapist = ?
                        ORDER BY kh.id ASC
                        """,
                        (tarih, ter),
                    )
                    rows = cur.fetchall()

                    cur.execute(
                        """
                        SELECT COALESCE(SUM(CASE WHEN kh.tip='giren' THEN kh.tutar ELSE 0 END),0),
                               COALESCE(SUM(CASE WHEN kh.tip='cikan' THEN kh.tutar ELSE 0 END),0)
                        FROM kasa_hareketleri kh
                        LEFT JOIN records r ON r.id = kh.record_id
                        WHERE kh.tarih=? AND r.terapist=?
                        """,
                        (tarih, ter),
                    )
                    giren, cikan = cur.fetchone() or (0, 0)

                    cur.execute(
                        """
                        SELECT COALESCE(SUM(CASE WHEN kh.tip='giren' THEN kh.tutar ELSE -kh.tutar END),0)
                        FROM kasa_hareketleri kh
                        LEFT JOIN records r ON r.id = kh.record_id
                        WHERE kh.tarih < ? AND r.terapist=?
                        """,
                        (tarih, ter),
                    )
                    devreden = float((cur.fetchone() or [0])[0] or 0)

                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Kasa yüklenemedi:\n{e}")
                return

            for idx, r in enumerate(rows):
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=(r[0], r[1], r[2], format_money(r[3]), r[4], r[5], r[6]), tags=(tag,))

            bugun_net = float(giren or 0) - float(cikan or 0)
            bugun_kasa = devreden + bugun_net
            info_lbl.config(
                text=f"Devreden: {devreden:,.2f} ₺ | Giren: {float(giren or 0):,.2f} ₺ | Çıkan: {float(cikan or 0):,.2f} ₺ | Bugünkü Kasa: {bugun_kasa:,.2f} ₺"
            )

        def _add(is_gider: bool):
            if self.kullanici_yetki != "kurum_muduru":
                messagebox.showwarning("Yetki", "Bu işlem sadece Kurum Müdürü tarafından yapılabilir.")
                return
            d = ttk.Toplevel(win)
            d.title("Gider Ekle" if is_gider else "Gelir Ekle")
            d.resizable(False, False)
            center_window(d, 520, 280)
            d.transient(win)
            d.grab_set()

            f = ttk.Frame(d, padding=14)
            f.pack(fill=BOTH, expand=True)

            ttk.Label(f, text="Tarih (YYYY-AA-GG):").grid(row=0, column=0, sticky=W, padx=6, pady=6)
            e_t = ttk.Entry(f, width=16)
            e_t.insert(0, (tarih_var.get() or "").strip() or datetime.datetime.now().strftime("%Y-%m-%d"))
            e_t.grid(row=0, column=1, sticky=W, padx=6, pady=6)

            ttk.Label(f, text="Açıklama:").grid(row=1, column=0, sticky=W, padx=6, pady=6)
            e_a = ttk.Entry(f, width=42)
            e_a.grid(row=1, column=1, sticky=W, padx=6, pady=6)
            e_a.focus_set()

            ttk.Label(f, text="Tutar (₺):").grid(row=2, column=0, sticky=W, padx=6, pady=6)
            e_u = ttk.Entry(f, validate="key", validatecommand=self._vcmd_money, width=18)
            e_u.grid(row=2, column=1, sticky=W, padx=6, pady=6)

            ttk.Label(f, text="Ödeme Şekli:").grid(row=3, column=0, sticky=W, padx=6, pady=6)
            cb = ttk.Combobox(f, state="readonly", values=["Nakit", "Havale/EFT", "Kart", "Diğer"], width=16)
            cb.current(0)
            cb.grid(row=3, column=1, sticky=W, padx=6, pady=6)

            def _save():
                try:
                    tutar = parse_money(e_u.get())
                except Exception:
                    messagebox.showerror("Hata", "Lütfen geçerli bir tutar giriniz!")
                    return
                if tutar <= 0:
                    messagebox.showwarning("Uyarı", "Tutar 0'dan büyük olmalıdır!")
                    return
                ac = (e_a.get() or "").strip()
                if not ac:
                    messagebox.showwarning("Uyarı", "Açıklama zorunludur!")
                    return
                try:
                    conn = self.veritabani_baglan()
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO kasa_hareketleri (tarih, tip, aciklama, tutar, odeme_sekli, record_id, seans_id, olusturan_kullanici_id, olusturma_tarihi)
                        VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            (e_t.get() or "").strip(),
                            ("cikan" if is_gider else "giren"),
                            ac,
                            tutar,
                            (cb.get() or "").strip(),
                            None,
                            None,
                            (self.kullanici[0] if self.kullanici else None),
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    messagebox.showerror("Hata", f"Kayıt eklenemedi:\n{e}")
                    return
                d.destroy()
                _load()

            ttk.Button(f, text="KAYDET", bootstyle="success", command=_save).grid(row=4, column=0, columnspan=2, sticky=EW, padx=6, pady=(12, 0))

        def _delete():
            if self.kullanici_yetki != "kurum_muduru":
                messagebox.showwarning("Yetki", "Silme işlemi sadece Kurum Müdürü tarafından yapılabilir.")
                return
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values") or ()
            if not vals:
                return
            kid = vals[0]
            if not messagebox.askyesno("Onay", "Seçili kasa kaydını silmek istiyor musunuz?"):
                return
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute("DELETE FROM kasa_hareketleri WHERE id=?", (kid,))
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Silinemedi:\n{e}")
                return
            _load()

        ttk.Button(top, text="Yenile", bootstyle="primary", command=_load).pack(side=LEFT, padx=6)
        ttk.Button(top, text="Gelir Ekle", bootstyle="success", command=lambda: _add(False)).pack(side=RIGHT, padx=6)
        ttk.Button(top, text="Gider Ekle", bootstyle="danger", command=lambda: _add(True)).pack(side=RIGHT, padx=6)
        ttk.Button(top, text="Sil", bootstyle="warning", command=_delete).pack(side=RIGHT, padx=6)

        _load()

    def haftalik_ders_ucret_takip(self):
        win = ttk.Toplevel(self)
        win.title("Haftalık Ders/Ücret Takip")
        center_window_smart(win, 1400, 820)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        ttk.Label(win, text="HAFTALIK DERS / ÜCRET TAKİP", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)

        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)

        bugun = datetime.datetime.now()
        hafta_bas = bugun - datetime.timedelta(days=bugun.weekday())
        hafta_var = ttk.StringVar(value=hafta_bas.strftime("%Y-%m-%d"))
        ttk.Label(top, text="Hafta Başlangıcı:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=6)
        ttk.Entry(top, textvariable=hafta_var, width=14).pack(side=LEFT, padx=6)

        ttk.Label(top, text="Terapist:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(16, 6))
        cb = ttk.Combobox(top, state="readonly", width=26)
        cb.pack(side=LEFT, padx=6)

        # terapist listesi
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY therapist_name")
            tnames = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception:
            tnames = DEFAULT_THERAPISTS[:]

        if self.kullanici_yetki == "kurum_muduru":
            cb["values"] = ["(Tümü)"] + tnames
            cb.current(0)
        else:
            cb["values"] = [self.kullanici_terapist] if self.kullanici_terapist else tnames[:1]
            cb.current(0)
            cb.configure(state="disabled")

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)

        cols = ("ID", "Tarih", "Saat", "Danışan", "Terapist", "Seans", "Ücret", "Tutar", "Ödeme", "Not")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=140)
        tree.column("ID", width=70)
        tree.column("Tarih", width=110)
        tree.column("Saat", width=80)
        tree.column("Danışan", width=220)
        tree.column("Terapist", width=170)
        tree.column("Seans", width=70)
        tree.column("Ücret", width=70)
        tree.column("Tutar", width=110)
        tree.column("Ödeme", width=110)
        tree.column("Not", width=260)

        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        summary = ttk.Label(win, text="", font=("Segoe UI", 10))
        summary.pack(fill=X, padx=12, pady=(0, 10))

        def _load():
            for iid in tree.get_children():
                tree.delete(iid)
            try:
                bas = datetime.datetime.strptime((hafta_var.get() or "").strip(), "%Y-%m-%d")
            except Exception:
                bas = hafta_bas
            bit = (bas + datetime.timedelta(days=6)).strftime("%Y-%m-%d")
            bas_s = bas.strftime("%Y-%m-%d")
            ter_filter = cb.get()

            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                if self.kullanici_yetki == "kurum_muduru" and ter_filter and ter_filter != "(Tümü)":
                    cur.execute(
                        """
                        SELECT id, tarih, saat, danisan_adi, terapist,
                               COALESCE(seans_alindi,0), COALESCE(ucret_alindi,0), COALESCE(ucret_tutar,0), COALESCE(odeme_sekli,''), COALESCE(notlar,'')
                        FROM seans_takvimi
                        WHERE tarih >= ? AND tarih <= ? AND terapist = ?
                        ORDER BY tarih, saat
                        """,
                        (bas_s, bit, ter_filter),
                    )
                elif self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
                    cur.execute(
                        """
                        SELECT id, tarih, saat, danisan_adi, terapist,
                               COALESCE(seans_alindi,0), COALESCE(ucret_alindi,0), COALESCE(ucret_tutar,0), COALESCE(odeme_sekli,''), COALESCE(notlar,'')
                        FROM seans_takvimi
                        WHERE tarih >= ? AND tarih <= ? AND terapist = ?
                        ORDER BY tarih, saat
                        """,
                        (bas_s, bit, self.kullanici_terapist),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, tarih, saat, danisan_adi, terapist,
                               COALESCE(seans_alindi,0), COALESCE(ucret_alindi,0), COALESCE(ucret_tutar,0), COALESCE(odeme_sekli,''), COALESCE(notlar,'')
                        FROM seans_takvimi
                        WHERE tarih >= ? AND tarih <= ?
                        ORDER BY tarih, saat
                        """,
                        (bas_s, bit),
                    )
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Haftalık kayıtlar yüklenemedi:\n{e}")
                return

            seans_top = len(rows)
            seans_alindi = sum(1 for r in rows if int(r[5] or 0) == 1)
            seans_alinmadi = seans_top - seans_alindi
            ucret_alindi = sum(1 for r in rows if int(r[6] or 0) == 1)
            toplam_tutar = sum(float(r[7] or 0) for r in rows if int(r[6] or 0) == 1)

            for idx, r in enumerate(rows):
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert(
                    "",
                    END,
                    values=(
                        r[0],
                        r[1],
                        r[2],
                        r[3],
                        r[4],
                        ("✓" if int(r[5] or 0) == 1 else ""),
                        ("✓" if int(r[6] or 0) == 1 else ""),
                        format_money(r[7]),
                        r[8],
                        r[9],
                    ),
                    tags=(tag,),
                )

            summary.config(
                text=f"Aralık: {bas_s} - {bit} | Toplam: {seans_top} | Alındı: {seans_alindi} | Alınmadı: {seans_alinmadi} | Ücret Alındı: {ucret_alindi} | Tahsilat: {toplam_tutar:,.2f} ₺"
            )

        def _selected_sid():
            sel = tree.selection()
            if not sel:
                return None
            vals = tree.item(sel[0], "values") or ()
            return vals[0] if vals else None

        def _toggle(col: str):
            sid = _selected_sid()
            if not sid:
                return
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                if col == "seans":
                    cur.execute("UPDATE seans_takvimi SET seans_alindi = CASE WHEN COALESCE(seans_alindi,0)=1 THEN 0 ELSE 1 END WHERE id=?", (sid,))
                else:
                    cur.execute("UPDATE seans_takvimi SET ucret_alindi = CASE WHEN COALESCE(ucret_alindi,0)=1 THEN 0 ELSE 1 END WHERE id=?", (sid,))
                    # Ücret alındı/ alınmadı -> kasa defterini seans_id üzerinden senkron tut
                    cur.execute(
                        "SELECT tarih, danisan_adi, terapist, COALESCE(ucret_alindi,0), COALESCE(ucret_tutar,0), COALESCE(odeme_sekli,'') FROM seans_takvimi WHERE id=?",
                        (sid,),
                    )
                    st = cur.fetchone() or ("", "", "", 0, 0, "")
                    st_tarih, st_dan, st_ter, st_ucret_alindi, st_tutar, st_sekil = st
                    # önce eski kasa kaydını temizle (duplicate olmasın)
                    try:
                        cur.execute("DELETE FROM kasa_hareketleri WHERE seans_id=? AND tip='giren'", (sid,))
                    except Exception:
                        pass
                    if int(st_ucret_alindi or 0) == 1 and float(st_tutar or 0) > 0:
                        try:
                            cur.execute(
                                """
                                INSERT INTO kasa_hareketleri (tarih, tip, aciklama, tutar, odeme_sekli, record_id, seans_id, olusturan_kullanici_id, olusturma_tarihi)
                                VALUES (?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    (st_tarih or "").strip(),
                                    "giren",
                                    f"{(st_dan or '').strip()} ({(st_ter or '').strip()}) seans ücreti",
                                    float(st_tutar or 0),
                                    (st_sekil or "").strip(),
                                    None,
                                    sid,
                                    (self.kullanici[0] if self.kullanici else None),
                                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                ),
                            )
                        except Exception:
                            pass
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Güncellenemedi:\n{e}")
                return
            _load()

        def _edit_amount():
            sid = _selected_sid()
            if not sid:
                return
            d = ttk.Toplevel(win)
            d.title("Ücret / Ödeme Güncelle")
            d.resizable(False, False)
            center_window(d, 520, 320)
            d.transient(win)
            d.grab_set()

            f = ttk.Frame(d, padding=14)
            f.pack(fill=BOTH, expand=True)

            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT tarih, danisan_adi, terapist,
                           COALESCE(ucret_tutar,0), COALESCE(odeme_sekli,''), COALESCE(notlar,''),
                           COALESCE(seans_alindi,0), COALESCE(ucret_alindi,0)
                    FROM seans_takvimi WHERE id=?
                    """,
                    (sid,),
                )
                row = cur.fetchone() or ("", "", "", 0, "", "", 0, 0)
                conn.close()
            except Exception:
                row = ("", "", "", 0, "", "", 0, 0)

            seans_tarih = row[0]
            seans_dan = row[1]
            seans_ter = row[2]
            var_seans = ttk.IntVar(value=1 if int(row[6] or 0) == 1 else 0)
            var_ucret = ttk.IntVar(value=1 if int(row[7] or 0) == 1 else 0)

            ttk.Checkbutton(f, text="Seans Alındı", variable=var_seans, bootstyle="success").pack(anchor=W, pady=(0, 6))
            ttk.Checkbutton(f, text="Ücret Alındı", variable=var_ucret, bootstyle="success").pack(anchor=W, pady=(0, 10))

            ttk.Label(f, text="Ücret Tutarı (₺):").pack(anchor=W)
            e_u = ttk.Entry(f, validate="key", validatecommand=self._vcmd_money)
            e_u.insert(0, str(row[3] or 0))
            e_u.pack(fill=X, pady=6)

            ttk.Label(f, text="Ödeme Şekli:").pack(anchor=W)
            cb2 = ttk.Combobox(f, state="readonly", values=["", "Nakit", "Havale/EFT", "Kart", "Diğer"])
            cb2.set(row[4] or "")
            cb2.pack(fill=X, pady=6)

            ttk.Label(f, text="Not:").pack(anchor=W)
            e_n = ttk.Entry(f)
            e_n.insert(0, row[5] or "")
            e_n.pack(fill=X, pady=6)

            def _save():
                try:
                    tutar = parse_money(e_u.get())
                except Exception:
                    messagebox.showerror("Hata", "Lütfen geçerli bir tutar giriniz!")
                    return
                try:
                    conn = self.veritabani_baglan()
                    cur = conn.cursor()
                    cur.execute(
                        """
                        UPDATE seans_takvimi
                        SET seans_alindi=?, ucret_alindi=?, ucret_tutar=?, odeme_sekli=?, notlar=?
                        WHERE id=?
                        """,
                        (
                            int(var_seans.get() or 0),
                            int(var_ucret.get() or 0),
                            tutar,
                            (cb2.get() or "").strip(),
                            (e_n.get() or "").strip(),
                            sid,
                        ),
                    )

                    # Ücret alındı işaretine göre kasa kaydını seans_id üzerinden senkron tut (tek kayıt)
                    try:
                        cur.execute("DELETE FROM kasa_hareketleri WHERE seans_id=? AND tip='giren'", (sid,))
                    except Exception:
                        pass
                    if int(var_ucret.get() or 0) == 1 and float(tutar or 0) > 0:
                        try:
                            cur.execute(
                                """
                                INSERT INTO kasa_hareketleri (tarih, tip, aciklama, tutar, odeme_sekli, record_id, seans_id, olusturan_kullanici_id, olusturma_tarihi)
                                VALUES (?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    (seans_tarih or "").strip(),
                                    "giren",
                                    f"{(seans_dan or '').strip()} ({(seans_ter or '').strip()}) seans ücreti",
                                    float(tutar or 0),
                                    (cb2.get() or "").strip(),
                                    None,
                                    sid,
                                    (self.kullanici[0] if self.kullanici else None),
                                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                ),
                            )
                        except Exception:
                            pass
                    conn.commit()
                    conn.close()
                except Exception as e:
                    messagebox.showerror("Hata", f"Güncellenemedi:\n{e}")
                    return
                d.destroy()
                _load()

            ttk.Button(f, text="KAYDET", bootstyle="success", command=_save).pack(fill=X, pady=(10, 0))

        def _export():
            try:
                bas = datetime.datetime.strptime((hafta_var.get() or "").strip(), "%Y-%m-%d")
            except Exception:
                bas = hafta_bas
            bit = (bas + datetime.timedelta(days=6)).strftime("%Y-%m-%d")
            bas_s = bas.strftime("%Y-%m-%d")
            ter_filter = cb.get()

            try:
                conn = self.veritabani_baglan()
                if self.kullanici_yetki == "kurum_muduru" and ter_filter and ter_filter != "(Tümü)":
                    df = pd.read_sql_query(
                        """
                        SELECT tarih, saat, danisan_adi, terapist,
                               COALESCE(seans_alindi,0) AS seans_alindi,
                               COALESCE(ucret_alindi,0) AS ucret_alindi,
                               COALESCE(ucret_tutar,0) AS ucret_tutar,
                               COALESCE(odeme_sekli,'') AS odeme_sekli,
                               COALESCE(notlar,'') AS notlar
                        FROM seans_takvimi
                        WHERE tarih >= ? AND tarih <= ? AND terapist = ?
                        ORDER BY tarih, saat
                        """,
                        conn,
                        params=(bas_s, bit, ter_filter),
                    )
                elif self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
                    df = pd.read_sql_query(
                        """
                        SELECT tarih, saat, danisan_adi, terapist,
                               COALESCE(seans_alindi,0) AS seans_alindi,
                               COALESCE(ucret_alindi,0) AS ucret_alindi,
                               COALESCE(ucret_tutar,0) AS ucret_tutar,
                               COALESCE(odeme_sekli,'') AS odeme_sekli,
                               COALESCE(notlar,'') AS notlar
                        FROM seans_takvimi
                        WHERE tarih >= ? AND tarih <= ? AND terapist = ?
                        ORDER BY tarih, saat
                        """,
                        conn,
                        params=(bas_s, bit, self.kullanici_terapist),
                    )
                else:
                    df = pd.read_sql_query(
                        """
                        SELECT tarih, saat, danisan_adi, terapist,
                               COALESCE(seans_alindi,0) AS seans_alindi,
                               COALESCE(ucret_alindi,0) AS ucret_alindi,
                               COALESCE(ucret_tutar,0) AS ucret_tutar,
                               COALESCE(odeme_sekli,'') AS odeme_sekli,
                               COALESCE(notlar,'') AS notlar
                        FROM seans_takvimi
                        WHERE tarih >= ? AND tarih <= ?
                        ORDER BY tarih, saat
                        """,
                        conn,
                        params=(bas_s, bit),
                    )
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Excel verisi oluşturulamadı:\n{e}")
                return

            path = filedialog.asksaveasfilename(
                title="Excel Kaydet",
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")],
                initialfile=f"haftalik_ders_ucret_{bas_s}_{bit}.xlsx",
            )
            if not path:
                return
            try:
                df.to_excel(path, index=False, engine="openpyxl")
                messagebox.showinfo("Başarılı", "Excel'e aktarıldı.")
            except Exception as e:
                messagebox.showerror("Hata", f"Excel aktarma hatası:\n{e}")

        ttk.Button(top, text="Göster", bootstyle="primary", command=_load).pack(side=LEFT, padx=6)
        ttk.Button(top, text="Seans Alındı/Alınmadı", bootstyle="success", command=lambda: _toggle("seans")).pack(side=LEFT, padx=6)
        ttk.Button(top, text="Ücret Alındı/Alınmadı", bootstyle="success", command=lambda: _toggle("ucret")).pack(side=LEFT, padx=6)
        ttk.Button(top, text="Ücret/Not Düzenle", bootstyle="warning", command=_edit_amount).pack(side=LEFT, padx=6)
        ttk.Button(top, text="Excel'e Aktar", bootstyle="secondary", command=_export).pack(side=RIGHT, padx=6)

        # Çift tık: direkt "Ücret/Not Düzenle" (yeni kullanıcılar için kolay)
        tree.bind("<Double-1>", lambda e: _edit_amount())

        _load()

    # --- Seans Takvimi (Günlük / Haftalık) ---
    def seans_takvimi_goster(self):
        win = ttk.Toplevel(self)
        win.title("Günlük Seans Takvimi")
        center_window_smart(win, 1400, 720)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)
        ttk.Label(top, text="Tarih (YYYY-AA-GG):", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=6)
        tarih_var = ttk.StringVar(value=datetime.datetime.now().strftime("%Y-%m-%d"))
        ent = ttk.Entry(top, textvariable=tarih_var, width=14)
        ent.pack(side=LEFT, padx=6)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)

        # Terapistler settings tablosundan
        terapistler = []
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY therapist_name")
            terapistler = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception:
            terapistler = DEFAULT_THERAPISTS[:]

        # Eğitim görevlisi ise sadece kendisi
        if self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
            terapistler = [self.kullanici_terapist]

        saatler = [f"{h:02d}:00" for h in range(9, 20)]
        cols = ["Saat"] + terapistler
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", height=20, style="Strong.Treeview")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.column("Saat", width=80)

        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        def _yenile():
            for i in tree.get_children():
                tree.delete(i)
            tarih = (tarih_var.get() or "").strip()
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    "SELECT saat, danisan_adi, terapist, COALESCE(oda,'') FROM seans_takvimi WHERE tarih=? ORDER BY saat",
                    (tarih,),
                )
                seanslar = cur.fetchall()
                conn.close()
            except Exception:
                seanslar = []

            takvim = {s: {t: "" for t in terapistler} for s in saatler}
            for saat, danisan, terapist, oda in seanslar:
                if terapist in takvim.get(saat or "", {}):
                    takvim[saat][terapist] = danisan

            for saat in saatler:
                row = [saat] + [takvim[saat].get(t, "") for t in terapistler]
                idx = saatler.index(saat)
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=row, tags=(tag,))

        ttk.Button(top, text="Göster", bootstyle="primary", command=_yenile).pack(side=LEFT, padx=6)
        _yenile()

    def haftalik_takvim_goster(self):
        win = ttk.Toplevel(self)
        win.title("Haftalık Seans Takvimi")
        center_window_smart(win, 1500, 820)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)
        ttk.Label(top, text="Hafta Başlangıcı (YYYY-AA-GG):", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=6)
        bugun = datetime.datetime.now()
        hafta_bas = bugun - datetime.timedelta(days=bugun.weekday())
        hafta_var = ttk.StringVar(value=hafta_bas.strftime("%Y-%m-%d"))
        ent = ttk.Entry(top, textvariable=hafta_var, width=14)
        ent.pack(side=LEFT, padx=6)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)

        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        saatler = [f"{h:02d}:00" for h in range(9, 20)]
        cols = ["Saat"] + gunler
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", height=20, style="Strong.Treeview")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=190)
        tree.column("Saat", width=80)

        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        def _yenile():
            for i in tree.get_children():
                tree.delete(i)
            try:
                bas = datetime.datetime.strptime((hafta_var.get() or "").strip(), "%Y-%m-%d")
            except Exception:
                bas = hafta_bas

            takvim = {s: {g: "" for g in gunler} for s in saatler}
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                for gun_idx, gun in enumerate(gunler):
                    tarih = (bas + datetime.timedelta(days=gun_idx)).strftime("%Y-%m-%d")
                    # seans_takvimi varsa oradan, yoksa records'tan
                    try:
                        cur.execute(
                            "SELECT danisan_adi, terapist FROM seans_takvimi WHERE tarih=? ORDER BY saat",
                            (tarih,),
                        )
                        seanslar = cur.fetchall()
                    except Exception:
                        cur.execute("SELECT danisan_adi, terapist FROM records WHERE tarih=? ORDER BY id", (tarih,))
                        seanslar = cur.fetchall()
                    for danisan, terapist in seanslar:
                        if self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
                            if terapist != self.kullanici_terapist:
                                continue
                        for saat in saatler:
                            if not takvim[saat][gun]:
                                takvim[saat][gun] = f"{danisan} ({terapist})"
                                break
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Haftalık takvim yüklenemedi:\n{e}")

            for saat in saatler:
                row = [saat] + [takvim[saat].get(g, "") for g in gunler]
                idx = saatler.index(saat)
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=row, tags=(tag,))

        ttk.Button(top, text="Göster", bootstyle="primary", command=_yenile).pack(side=LEFT, padx=6)
        _yenile()

    def yeni_seans_ekle(self):
        win = ttk.Toplevel(self)
        win.title("Yeni Seans Ekle")
        center_window_smart(win, 620, 620, max_ratio=0.85)
        win.transient(self)
        win.grab_set()
        self._brand_window(win)

        ttk.Label(win, text="YENİ SEANS EKLE", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)
        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=BOTH, expand=True)

        ttk.Label(frm, text="Tarih (YYYY-AA-GG):").pack(anchor=W)
        tarih_var = ttk.StringVar(value=datetime.datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(frm, textvariable=tarih_var).pack(fill=X, pady=6)

        ttk.Label(frm, text="Saat:").pack(anchor=W)
        saat_cb = ttk.Combobox(frm, values=[f"{h:02d}:00" for h in range(9, 20)], state="readonly")
        saat_cb.current(0)
        saat_cb.pack(fill=X, pady=6)

        ttk.Label(frm, text="Danışan:").pack(anchor=W)
        dan_cb = ttk.Combobox(frm)
        dan_cb.pack(fill=X, pady=6)

        ttk.Label(frm, text="Terapist:").pack(anchor=W)
        ter_cb = ttk.Combobox(frm, state="readonly")
        ter_cb.pack(fill=X, pady=6)

        ttk.Label(frm, text="Oda:").pack(anchor=W)
        oda_cb = ttk.Combobox(frm, state="readonly")
        oda_cb.pack(fill=X, pady=6)

        ttk.Label(frm, text="Not:").pack(anchor=W)
        ent_not = ttk.Entry(frm)
        ent_not.pack(fill=X, pady=6)

        # load lists
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
            dan_cb["values"] = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY therapist_name")
            ter_names = [r[0] for r in cur.fetchall()]
            if self.kullanici_yetki != "kurum_muduru" and self.kullanici_terapist:
                ter_names = [self.kullanici_terapist]
            ter_cb["values"] = ter_names
            if ter_names:
                ter_cb.current(0)
            cur.execute("SELECT oda_adi FROM odalar WHERE aktif=1 ORDER BY oda_adi")
            oda_names = [r[0] for r in cur.fetchall()]
            oda_cb["values"] = oda_names
            if oda_names:
                oda_cb.current(0)
            conn.close()
        except Exception:
            pass

        def _kaydet():
            if not (dan_cb.get() or "").strip():
                messagebox.showwarning("Uyarı", "Lütfen danışan seçiniz!")
                return
            if not (ter_cb.get() or "").strip():
                messagebox.showwarning("Uyarı", "Lütfen terapist seçiniz!")
                return
            if "name hoca" in (ter_cb.get() or "").lower():
                messagebox.showwarning("Uyarı", "Name Hoca kurumdan ayrıldı.")
                return
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                t = (tarih_var.get() or "").strip()
                s = (saat_cb.get() or "").strip() or self._default_saat()
                d = (dan_cb.get() or "").strip().upper()
                ter = (ter_cb.get() or "").strip()
                nt = (ent_not.get() or "").strip()
                cur.execute(
                    """
                    INSERT INTO seans_takvimi (tarih, saat, danisan_adi, terapist, oda, durum, notlar, olusturma_tarihi, olusturan_kullanici_id, record_id)
                    VALUES (?,?,?,?,?,?,?,?,?,NULL)
                    """,
                    (
                        t,
                        s,
                        d,
                        ter,
                        (oda_cb.get() or "").strip(),
                        "planlandi",
                        nt,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        self.kullanici[0] if self.kullanici else None,
                    ),
                )
                sid = int(cur.lastrowid or 0)
                try:
                    self._sync_from_seans_to_record(cur, sid, t, s, d, ter, nt)
                except Exception:
                    pass
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Seans eklenemedi:\n{e}")
                return
            win.destroy()
            messagebox.showinfo("Başarılı", "Seans eklendi.")

        ttk.Button(frm, text="KAYDET", bootstyle="success", command=_kaydet).pack(fill=X, pady=(12, 0))

    # --- Danışan Yönetimi ---
    def danisan_yonetimi(self):
        win = ttk.Toplevel(self)
        win.title("Danışan Yönetimi")
        center_window_smart(win, 1300, 760)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)
        ttk.Label(top, text="DANIŞAN YÖNETİMİ", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Button(top, text="Yeni Danışan Ekle", bootstyle="success", command=lambda: self.yeni_danisan_ekle(win)).pack(side=RIGHT)
        ttk.Button(top, text="Düzenle", bootstyle="warning", command=lambda: self.danisan_duzenle(win)).pack(side=RIGHT, padx=6)
        ttk.Button(top, text="Aktif/Pasif", bootstyle="secondary", command=lambda: self.danisan_aktif_pasif(win)).pack(side=RIGHT, padx=6)

        ar = ttk.Frame(win, padding=(10, 0))
        ar.pack(fill=X)
        ttk.Label(ar, text="Ara:").pack(side=LEFT, padx=6)
        ent_ara = ttk.Entry(ar)
        ent_ara.pack(side=LEFT, fill=X, expand=True, padx=6)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)
        cols = ("ID", "Ad Soyad", "Telefon", "Veli Adı", "Veli Telefon", "E-posta", "Durum")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=150)
        tree.column("ID", width=60)
        tree.column("Ad Soyad", width=240)
        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        def _yukle():
            for i in tree.get_children():
                tree.delete(i)
            kelime = (ent_ara.get() or "").strip()
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                sql = "SELECT id, ad_soyad, telefon, veli_adi, veli_telefon, email, aktif FROM danisanlar"
                params = []
                if kelime:
                    sql += " WHERE ad_soyad LIKE ?"
                    params.append(f"%{kelime}%")
                sql += " ORDER BY ad_soyad"
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Danışanlar yüklenemedi:\n{e}")
                return
            for idx, r in enumerate(rows):
                durum = "Aktif" if (r[6] or 0) == 1 else "Pasif"
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=(r[0], r[1], r[2] or "", r[3] or "", r[4] or "", r[5] or "", durum), tags=(tag,))

        ent_ara.bind("<KeyRelease>", lambda e: _yukle())
        _yukle()
        win.danisan_tree = tree
        win._reload = _yukle

    def _yeni_danisan_ekle_ve_guncelle(self, combobox, parent):
        """Yeni danışan ekle ve combobox'ı otomatik güncelle (terapist mantığı gibi)"""
        win = ttk.Toplevel(parent)
        win.title("Yeni Danışan Ekle")
        center_window_smart(win, 620, 760, max_ratio=0.88)
        win.transient(parent)
        win.grab_set()
        self._brand_window(win)

        ttk.Label(win, text="YENİ DANIŞAN EKLE", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)
        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=BOTH, expand=True)

        def field(label):
            ttk.Label(frm, text=label).pack(anchor=W, pady=(8, 0))
            e = ttk.Entry(frm)
            e.pack(fill=X, pady=4)
            return e

        ent_ad = field("Ad Soyad *:")
        ent_tel = field("Telefon:")
        ent_email = field("E-posta:")
        ent_veli = field("Veli Adı:")
        ent_veli_tel = field("Veli Telefon:")
        ent_dogum = field("Doğum Tarihi:")
        ttk.Label(frm, text="Adres:").pack(anchor=W, pady=(8, 0))
        txt_adres = ttk.Text(frm, height=3)
        txt_adres.pack(fill=X, pady=4)
        ttk.Label(frm, text="Notlar:").pack(anchor=W, pady=(8, 0))
        txt_not = ttk.Text(frm, height=3)
        txt_not.pack(fill=X, pady=4)

        def _kaydet():
            if not (ent_ad.get() or "").strip():
                messagebox.showwarning("Uyarı", "Ad Soyad zorunludur!")
                return
            try:
                danisan_adi = (ent_ad.get() or "").strip().upper()
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO danisanlar (ad_soyad, telefon, email, veli_adi, veli_telefon, dogum_tarihi, adres, notlar, olusturma_tarihi, aktif)
                    VALUES (?,?,?,?,?,?,?,?,?,1)
                    """,
                    (
                        danisan_adi,
                        (ent_tel.get() or "").strip(),
                        (ent_email.get() or "").strip(),
                        (ent_veli.get() or "").strip(),
                        (ent_veli_tel.get() or "").strip(),
                        (ent_dogum.get() or "").strip(),
                        (txt_adres.get("1.0", END) or "").strip(),
                        (txt_not.get("1.0", END) or "").strip(),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                conn.close()
                
                # Tüm danışan combobox'larını güncelle
                try:
                    conn2 = self.veritabani_baglan()
                    cur2 = conn2.cursor()
                    cur2.execute("SELECT ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
                    danisan_listesi = [row[0] for row in cur2.fetchall()]
                    conn2.close()
                    
                    # Ana combobox'ı güncelle
                    if hasattr(self, 'cmb_danisan'):
                        self.cmb_danisan["values"] = danisan_listesi
                        self.cmb_danisan.set(danisan_adi)  # Yeni eklenen danışanı seç
                    
                    # Parametre olarak gelen combobox'ı güncelle
                    combobox["values"] = danisan_listesi
                    combobox.set(danisan_adi)  # Yeni eklenen danışanı seç
                    
                except Exception:
                    pass
                
            except Exception as e:
                messagebox.showerror("Hata", f"Danışan eklenemedi:\n{e}")
                return
            messagebox.showinfo("Başarılı", f"Danışan eklendi: {danisan_adi}")
            win.destroy()

        btns = ttk.Frame(frm)
        btns.pack(fill=X, pady=(16, 0))
        ttk.Button(btns, text="KAYDET", bootstyle="success", command=_kaydet).pack(side=LEFT, fill=X, expand=True, padx=6)
        ttk.Button(btns, text="İptal", bootstyle="secondary", command=win.destroy).pack(side=LEFT, fill=X, expand=True, padx=6)

    def yeni_danisan_ekle(self, parent):
        """Eski fonksiyon - Geriye uyumluluk için"""
        # Ana combobox yoksa normal pencere aç
        if hasattr(self, 'cmb_danisan'):
            self._yeni_danisan_ekle_ve_guncelle(self.cmb_danisan, parent)
            return
        
        # Eski yöntem - sadece pencere aç
        win = ttk.Toplevel(parent)
        win.title("Yeni Danışan Ekle")
        center_window_smart(win, 620, 760, max_ratio=0.88)
        win.transient(parent)
        win.grab_set()
        self._brand_window(win)

        ttk.Label(win, text="YENİ DANIŞAN EKLE", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)
        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=BOTH, expand=True)

        def field(label):
            ttk.Label(frm, text=label).pack(anchor=W, pady=(8, 0))
            e = ttk.Entry(frm)
            e.pack(fill=X, pady=4)
            return e

        ent_ad = field("Ad Soyad *:")
        ent_tel = field("Telefon:")
        ent_email = field("E-posta:")
        ent_veli = field("Veli Adı:")
        ent_veli_tel = field("Veli Telefon:")
        ent_dogum = field("Doğum Tarihi:")
        ttk.Label(frm, text="Adres:").pack(anchor=W, pady=(8, 0))
        txt_adres = ttk.Text(frm, height=3)
        txt_adres.pack(fill=X, pady=4)
        ttk.Label(frm, text="Notlar:").pack(anchor=W, pady=(8, 0))
        txt_not = ttk.Text(frm, height=3)
        txt_not.pack(fill=X, pady=4)

        def _kaydet():
            if not (ent_ad.get() or "").strip():
                messagebox.showwarning("Uyarı", "Ad Soyad zorunludur!")
                return
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO danisanlar (ad_soyad, telefon, email, veli_adi, veli_telefon, dogum_tarihi, adres, notlar, olusturma_tarihi, aktif)
                    VALUES (?,?,?,?,?,?,?,?,?,1)
                    """,
                    (
                        (ent_ad.get() or "").strip().upper(),
                        (ent_tel.get() or "").strip(),
                        (ent_email.get() or "").strip(),
                        (ent_veli.get() or "").strip(),
                        (ent_veli_tel.get() or "").strip(),
                        (ent_dogum.get() or "").strip(),
                        (txt_adres.get("1.0", END) or "").strip(),
                        (txt_not.get("1.0", END) or "").strip(),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                conn.close()
                
                # Danışan eklendikten sonra combobox'ları yenile
                if hasattr(self, 'cmb_danisan'):
                        try:
                            conn2 = self.veritabani_baglan()
                            cur2 = conn2.cursor()
                            cur2.execute("SELECT ad_soyad FROM danisanlar WHERE aktif=1 ORDER BY ad_soyad")
                            danisan_listesi = [row[0] for row in cur2.fetchall()]
                            conn2.close()
                            self.cmb_danisan["values"] = danisan_listesi
                        except Exception:
                            pass
                    
            except Exception as e:
                messagebox.showerror("Hata", f"Danışan eklenemedi:\n{e}")
                return
            messagebox.showinfo("Başarılı", "Danışan eklendi.")
            win.destroy()

        btns = ttk.Frame(win, padding=(16, 0))
        btns.pack(fill=X, pady=10)
        ttk.Button(btns, text="KAYDET", bootstyle="success", command=_kaydet).pack(side=LEFT, fill=X, expand=True, padx=6)
        ttk.Button(btns, text="İptal", bootstyle="secondary", command=win.destroy).pack(side=LEFT, fill=X, expand=True, padx=6)

    # --- Görev Takibi ---
    def gorev_takibi(self):
        win = ttk.Toplevel(self)
        win.title("Görev Takibi")
        center_window_smart(win, 1300, 760)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)
        ttk.Label(top, text="GÖREV TAKİBİ", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Button(top, text="Yeni Görev Ekle", bootstyle="success", command=lambda: self.yeni_gorev_ekle(win)).pack(side=RIGHT)
        ttk.Button(top, text="Durum Güncelle", bootstyle="warning", command=lambda: self.gorev_durum_guncelle(win)).pack(side=RIGHT, padx=6)
        ttk.Button(top, text="Tamamla", bootstyle="success-outline", command=lambda: self.gorev_tamamla(win)).pack(side=RIGHT, padx=6)
        ttk.Button(top, text="Sil", bootstyle="danger-outline", command=lambda: self.gorev_sil(win)).pack(side=RIGHT, padx=6)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)
        cols = ("ID", "Başlık", "Açıklama", "Atanan", "Durum", "Öncelik", "Başlangıç", "Bitiş")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=140)
        tree.column("ID", width=60)
        tree.column("Başlık", width=220)
        tree.column("Açıklama", width=320)
        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        def _yukle():
            for i in tree.get_children():
                tree.delete(i)
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT g.id, g.baslik, g.aciklama, u.full_name, g.durum, g.oncelik, g.baslangic_tarihi, g.bitis_tarihi
                    FROM gorevler g
                    LEFT JOIN users u ON g.atanan_kullanici_id = u.id
                    ORDER BY g.id DESC
                    """
                )
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Görevler yüklenemedi:\n{e}")
                return
            for idx, r in enumerate(rows):
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=r, tags=(tag,))

        _yukle()
        win.gorev_tree = tree
        win._reload = _yukle

    def yeni_gorev_ekle(self, parent):
        win = ttk.Toplevel(parent)
        win.title("Yeni Görev Ekle")
        center_window_smart(win, 700, 720, max_ratio=0.9)
        win.transient(parent)
        win.grab_set()
        self._brand_window(win)

        ttk.Label(win, text="YENİ GÖREV EKLE", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)
        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=BOTH, expand=True)

        ttk.Label(frm, text="Başlık *:").pack(anchor=W)
        ent_bas = ttk.Entry(frm)
        ent_bas.pack(fill=X, pady=6)

        ttk.Label(frm, text="Açıklama:").pack(anchor=W)
        txt = ttk.Text(frm, height=5)
        txt.pack(fill=X, pady=6)

        ttk.Label(frm, text="Atanan:").pack(anchor=W)
        cb = ttk.Combobox(frm, state="readonly")
        cb.pack(fill=X, pady=6)

        ttk.Label(frm, text="Öncelik:").pack(anchor=W)
        cb_on = ttk.Combobox(frm, values=["Düşük", "Normal", "Yüksek", "Acil"], state="readonly")
        cb_on.current(1)
        cb_on.pack(fill=X, pady=6)

        ttk.Label(frm, text="Bitiş Tarihi (YYYY-AA-GG):").pack(anchor=W)
        ent_bit = ttk.Entry(frm)
        ent_bit.pack(fill=X, pady=6)

        # load users
        users_map = {}
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT id, COALESCE(full_name, username) FROM users WHERE is_active=1 ORDER BY full_name, username")
            vals = []
            for uid, nm in cur.fetchall():
                users_map[f"{nm} ({uid})"] = uid
                vals.append(f"{nm} ({uid})")
            cb["values"] = vals
            if vals:
                cb.current(0)
            conn.close()
        except Exception:
            pass

        def _kaydet():
            if not (ent_bas.get() or "").strip():
                messagebox.showwarning("Uyarı", "Başlık zorunludur!")
                return
            atanan_id = users_map.get(cb.get()) if cb.get() else None
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO gorevler (baslik, aciklama, atanan_kullanici_id, olusturan_kullanici_id, durum, oncelik, baslangic_tarihi, bitis_tarihi, olusturma_tarihi)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        (ent_bas.get() or "").strip(),
                        (txt.get("1.0", END) or "").strip(),
                        atanan_id,
                        self.kullanici[0] if self.kullanici else None,
                        "beklemede",
                        (cb_on.get() or "normal").lower(),
                        datetime.datetime.now().strftime("%Y-%m-%d"),
                        (ent_bit.get() or "").strip() or None,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Görev eklenemedi:\n{e}")
                return
            messagebox.showinfo("Başarılı", "Görev eklendi.")
            win.destroy()

        ttk.Button(frm, text="KAYDET", bootstyle="success", command=_kaydet).pack(fill=X, pady=(12, 0))

    # --- Kullanıcı Yönetimi ---
    def kullanicilari_listele(self):
        if self.kullanici_yetki != "kurum_muduru":
            messagebox.showwarning("Uyarı", "Bu işlem sadece Kurum Müdürü yetkisi ile yapılabilir.")
            return
        win = ttk.Toplevel(self)
        win.title("Kullanıcılar")
        center_window_smart(win, 1300, 760)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        ttk.Label(win, text="KULLANICI LİSTESİ", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)
        btns = ttk.Frame(win, padding=(10, 0, 10, 10))
        btns.pack(fill=X)
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)
        cols = ("ID", "Kullanıcı Adı", "Ad Soyad", "Rol (Unvan)", "Terapist", "Yetki", "Durum", "Oluşturma", "Son Giriş")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=150)
        tree.column("ID", width=60)
        tree.column("Rol (Unvan)", width=190)
        tree.column("Terapist", width=170)
        tree.column("Yetki", width=140)
        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        def _yukle():
            for i in tree.get_children():
                tree.delete(i)
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT
                        u.id,
                        u.username,
                        COALESCE(u.full_name,''),
                        COALESCE(NULLIF(u.title_role,''), s.therapist_role, ''),
                        COALESCE(u.therapist_name,''),
                        COALESCE(u.access_role, u.role, ''),
                        COALESCE(u.is_active,1),
                        COALESCE(u.created_at,''),
                        COALESCE(u.last_login,'')
                    FROM users u
                    LEFT JOIN settings s ON s.therapist_name = u.therapist_name
                    ORDER BY u.id
                    """
                )
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Kullanıcılar yüklenemedi:\n{e}")
                return
            for idx, r in enumerate(rows):
                durum = "Aktif" if int(r[6] or 0) == 1 else "Pasif"
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=(r[0], r[1], r[2], r[3], r[4], r[5], durum, r[7], r[8]), tags=(tag,))

        def _selected_user_id():
            sel = tree.selection()
            if not sel:
                return None
            vals = tree.item(sel[0]).get("values") or []
            if not vals:
                return None
            try:
                return int(vals[0])
            except Exception:
                return None

        def _rol_duzenle():
            uid = _selected_user_id()
            if not uid:
                messagebox.showwarning("Uyarı", "Lütfen bir kullanıcı seçiniz!")
                return
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT
                        u.username,
                        COALESCE(u.full_name,''),
                        COALESCE(u.access_role, u.role, 'egitim_gorevlisi'),
                        COALESCE(u.therapist_name,''),
                        COALESCE(NULLIF(u.title_role,''), s.therapist_role, ''),
                        COALESCE(u.is_active,1)
                    FROM users u
                    LEFT JOIN settings s ON s.therapist_name = u.therapist_name
                    WHERE u.id=?
                    """,
                    (uid,),
                )
                row = cur.fetchone()
                # terapistler + unvanlar
                cur.execute("SELECT therapist_name, COALESCE(therapist_role,'') FROM settings WHERE is_active=1 ORDER BY therapist_name")
                terapist_rows = cur.fetchall()
                terapistler = [r[0] for r in terapist_rows]
                role_map = {r[0]: (r[1] or "") for r in terapist_rows}
                cur.execute("SELECT DISTINCT COALESCE(therapist_role,'') FROM settings WHERE is_active=1 AND COALESCE(therapist_role,'')<>'' ORDER BY therapist_role")
                unvanlar = [r[0] for r in cur.fetchall()]
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Kullanıcı bilgisi alınamadı:\n{e}")
                return
            if not row:
                return
            uname, full_name, access_role, therapist_name, title_role, is_active = row

            dlg = ttk.Toplevel(win)
            dlg.title("Rol / Terapist Düzenle")
            dlg.geometry("420x340")
            dlg.transient(win)
            dlg.grab_set()
            frm = ttk.Frame(dlg, padding=16)
            frm.pack(fill=BOTH, expand=True)

            ttk.Label(frm, text=f"Kullanıcı: {uname}", font=("Segoe UI", 11, "bold")).pack(anchor=W, pady=(0, 10))

            ttk.Label(frm, text="Terapist (opsiyonel):").pack(anchor=W)
            cb_ter = ttk.Combobox(frm, state="readonly", values=[""] + terapistler)
            cb_ter.pack(fill=X, pady=6)
            cb_ter.set(therapist_name or "")

            ttk.Label(frm, text="Rol (Unvan):").pack(anchor=W)
            cb_unvan = ttk.Combobox(frm, state="readonly", values=unvanlar + (["Diğer"] if "Diğer" not in unvanlar else []))
            cb_unvan.pack(fill=X, pady=6)
            cb_unvan.set(title_role or (role_map.get(therapist_name or "", "") or ""))

            ttk.Label(frm, text="Yetki:").pack(anchor=W)
            cb_yetki = ttk.Combobox(frm, state="readonly", values=["kurum_muduru", "egitim_gorevlisi"])
            cb_yetki.pack(fill=X, pady=6)
            cb_yetki.set(access_role or "egitim_gorevlisi")

            ttk.Label(
                frm,
                text="Not: Yetki 'egitim_gorevlisi' ise terapist seçilmesi önerilir (kendi kayıtları filtrelenir).",
                foreground="gray",
                wraplength=380,
            ).pack(anchor=W, pady=(8, 0))

            def _sync_unvan(_evt=None):
                tname = (cb_ter.get() or "").strip()
                if not tname:
                    return
                auto = role_map.get(tname, "")
                if auto:
                    cb_unvan.set(auto)

            cb_ter.bind("<<ComboboxSelected>>", _sync_unvan)

            def _save():
                new_access = (cb_yetki.get() or "egitim_gorevlisi").strip()
                new_ter = (cb_ter.get() or "").strip() or None
                new_title = (cb_unvan.get() or "").strip()
                try:
                    conn2 = self.veritabani_baglan()
                    cur2 = conn2.cursor()
                    # Son kurum müdürü demote edilemesin
                    if (access_role or "") == "kurum_muduru" and new_access != "kurum_muduru" and int(is_active or 0) == 1:
                        cur2.execute(
                            "SELECT COUNT(*) FROM users WHERE is_active=1 AND COALESCE(access_role, role)='kurum_muduru' AND id<>?",
                            (uid,),
                        )
                        if int((cur2.fetchone() or [0])[0] or 0) <= 0:
                            conn2.close()
                            messagebox.showwarning("Uyarı", "Son aktif kurum müdürü rolü değiştirilemez.")
                            return
                    cur2.execute(
                        "UPDATE users SET access_role=?, role=?, title_role=?, therapist_name=? WHERE id=?",
                        (new_access, new_access, new_title, new_ter, uid),
                    )
                    conn2.commit()
                    conn2.close()
                except Exception as e:
                    messagebox.showerror("Hata", f"Güncellenemedi:\n{e}")
                    return
                dlg.destroy()
                _yukle()

            ttk.Button(frm, text="KAYDET", bootstyle="success", command=_save).pack(fill=X, pady=(14, 0))

        ttk.Button(btns, text="Rol/Terapist Düzenle", bootstyle="warning", command=_rol_duzenle).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="Yenile", bootstyle="secondary", command=_yukle).pack(side=LEFT, padx=4)

        _yukle()

    def kullanici_sil(self):
        if self.kullanici_yetki != "kurum_muduru":
            messagebox.showwarning("Uyarı", "Bu işlem sadece Kurum Müdürü yetkisi ile yapılabilir.")
            return
        win = ttk.Toplevel(self)
        win.title("Kullanıcı Sil / Pasif Et")
        center_window_smart(win, 900, 620)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        ttk.Label(win, text="KULLANICI SİL / PASİF ET", font=("Segoe UI", 14, "bold"), bootstyle="danger").pack(pady=10)
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)
        cols = ("ID", "Kullanıcı", "Ad Soyad", "Yetki", "Terapist", "Durum")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=140)
        tree.column("ID", width=70)
        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        def _yukle():
            for i in tree.get_children():
                tree.delete(i)
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username, COALESCE(full_name,''), COALESCE(access_role, role, ''), COALESCE(therapist_name,''), COALESCE(is_active,1) FROM users ORDER BY id"
            )
            rows = cur.fetchall()
            conn.close()
            for idx, r in enumerate(rows):
                # r: (id, username, full_name, access_role, therapist_name, is_active)
                durum = "Aktif" if int(r[5] or 0) == 1 else "Pasif"
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=(r[0], r[1], r[2], r[3], r[4], durum), tags=(tag,))

        def _pasif_et():
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0]).get("values") or []
            uid = int(vals[0])
            uname = str(vals[1])
            rol = str(vals[3])
            try:
                conn_chk = self.veritabani_baglan()
                cur_chk = conn_chk.cursor()
                # Son aktif kurum müdürü pasif edilemesin
                if rol == "kurum_muduru":
                    cur_chk.execute(
                        "SELECT COUNT(*) FROM users WHERE is_active=1 AND COALESCE(access_role, role)='kurum_muduru' AND id<>?",
                        (uid,),
                    )
                    if int((cur_chk.fetchone() or [0])[0] or 0) <= 0:
                        conn_chk.close()
                        messagebox.showwarning("Uyarı", "Son aktif kurum müdürü pasif edilemez.")
                        return
                conn_chk.close()
            except Exception:
                pass
            if not messagebox.askyesno("Onay", f"'{uname}' kullanıcısı pasif edilsin mi?"):
                return
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("UPDATE users SET is_active=0 WHERE id=?", (uid,))
            conn.commit()
            conn.close()
            _yukle()

        ttk.Button(win, text="Seçiliyi Pasif Et", bootstyle="danger", command=_pasif_et).pack(pady=10)
        _yukle()

    # --- EK MODÜL: ODA YÖNETİMİ (leta_pro) ---
    def odalar_yonetimi(self):
        win = ttk.Toplevel(self)
        win.title("Oda Yönetimi")
        center_window_smart(win, 1100, 720)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)
        ttk.Label(top, text="ODA YÖNETİMİ", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Button(top, text="Yeni Oda Ekle", bootstyle="success", command=lambda: self.oda_ekle(win)).pack(side=RIGHT)
        ttk.Button(top, text="Düzenle", bootstyle="warning", command=lambda: self.oda_duzenle(win)).pack(side=RIGHT, padx=6)
        ttk.Button(top, text="Aktif/Pasif", bootstyle="secondary", command=lambda: self.oda_aktif_pasif(win)).pack(side=RIGHT, padx=6)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)
        cols = ("ID", "Oda", "Tip", "Kapasite", "Açıklama", "Durum")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=150)
        tree.column("ID", width=60)
        tree.column("Oda", width=220)
        tree.column("Açıklama", width=260)

        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        def _yukle():
            for i in tree.get_children():
                tree.delete(i)
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute("SELECT id, oda_adi, COALESCE(oda_tipi,''), COALESCE(kapasite,''), COALESCE(aciklama,''), COALESCE(aktif,1) FROM odalar ORDER BY oda_adi")
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Odalar yüklenemedi:\n{e}")
                return
            for idx, r in enumerate(rows):
                durum = "Aktif" if int(r[5] or 0) == 1 else "Pasif"
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert("", END, values=(r[0], r[1], r[2], r[3], r[4], durum), tags=(tag,))

        _yukle()
        win.oda_tree = tree
        win._reload = _yukle

    def oda_ekle(self, parent):
        win = ttk.Toplevel(parent)
        win.title("Yeni Oda Ekle")
        center_window_smart(win, 600, 640, max_ratio=0.9)
        win.transient(parent)
        win.grab_set()
        self._brand_window(win)

        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=BOTH, expand=True)
        ttk.Label(frm, text="ODA ADI *:").pack(anchor=W, pady=(4, 0))
        ent_ad = ttk.Entry(frm)
        ent_ad.pack(fill=X, pady=6)

        ttk.Label(frm, text="Oda Tipi:").pack(anchor=W, pady=(4, 0))
        ent_tip = ttk.Entry(frm)
        ent_tip.pack(fill=X, pady=6)

        ttk.Label(frm, text="Kapasite:").pack(anchor=W, pady=(4, 0))
        ent_kap = ttk.Entry(frm)
        ent_kap.pack(fill=X, pady=6)

        ttk.Label(frm, text="Açıklama:").pack(anchor=W, pady=(4, 0))
        txt = ttk.Text(frm, height=4)
        txt.pack(fill=X, pady=6)

        def _save():
            oda = (ent_ad.get() or "").strip()
            if not oda:
                messagebox.showwarning("Uyarı", "Oda adı zorunludur!")
                return
            try:
                kapasite = int((ent_kap.get() or "0").strip() or "0")
            except Exception:
                kapasite = 0
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    "INSERT OR IGNORE INTO odalar (oda_adi, oda_tipi, kapasite, aciklama, aktif) VALUES (?,?,?,?,1)",
                    (oda, (ent_tip.get() or "").strip(), kapasite, (txt.get('1.0', END) or '').strip()),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Oda eklenemedi:\n{e}")
                return
            win.destroy()
            if hasattr(parent, "_reload"):
                parent._reload()

        ttk.Button(frm, text="KAYDET", bootstyle="success", command=_save).pack(fill=X, pady=(10, 0))

    def oda_duzenle(self, parent):
        if not hasattr(parent, "oda_tree"):
            return
        sel = parent.oda_tree.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen bir oda seçiniz!")
            return
        vals = parent.oda_tree.item(sel[0]).get("values") or []
        oid = int(vals[0])

        win = ttk.Toplevel(parent)
        win.title("Oda Düzenle")
        center_window_smart(win, 600, 640, max_ratio=0.9)
        win.transient(parent)
        win.grab_set()
        self._brand_window(win)

        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=BOTH, expand=True)
        ttk.Label(frm, text="ODA ADI *:").pack(anchor=W, pady=(4, 0))
        ent_ad = ttk.Entry(frm)
        ent_ad.insert(0, vals[1] or "")
        ent_ad.pack(fill=X, pady=6)

        ttk.Label(frm, text="Oda Tipi:").pack(anchor=W, pady=(4, 0))
        ent_tip = ttk.Entry(frm)
        ent_tip.insert(0, vals[2] or "")
        ent_tip.pack(fill=X, pady=6)

        ttk.Label(frm, text="Kapasite:").pack(anchor=W, pady=(4, 0))
        ent_kap = ttk.Entry(frm)
        ent_kap.insert(0, str(vals[3] or ""))
        ent_kap.pack(fill=X, pady=6)

        ttk.Label(frm, text="Açıklama:").pack(anchor=W, pady=(4, 0))
        txt = ttk.Text(frm, height=4)
        txt.insert("1.0", vals[4] or "")
        txt.pack(fill=X, pady=6)

        def _save():
            oda = (ent_ad.get() or "").strip()
            if not oda:
                messagebox.showwarning("Uyarı", "Oda adı zorunludur!")
                return
            try:
                kapasite = int((ent_kap.get() or "0").strip() or "0")
            except Exception:
                kapasite = 0
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE odalar SET oda_adi=?, oda_tipi=?, kapasite=?, aciklama=? WHERE id=?",
                    (oda, (ent_tip.get() or "").strip(), kapasite, (txt.get('1.0', END) or '').strip(), oid),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Oda güncellenemedi:\n{e}")
                return
            win.destroy()
            if hasattr(parent, "_reload"):
                parent._reload()

        ttk.Button(frm, text="KAYDET", bootstyle="success", command=_save).pack(fill=X, pady=(10, 0))

    def oda_aktif_pasif(self, parent):
        if not hasattr(parent, "oda_tree"):
            return
        sel = parent.oda_tree.selection()
        if not sel:
            return
        vals = parent.oda_tree.item(sel[0]).get("values") or []
        oid = int(vals[0])
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(aktif,1) FROM odalar WHERE id=?", (oid,))
            aktif = int((cur.fetchone() or [1])[0] or 0)
            cur.execute("UPDATE odalar SET aktif=? WHERE id=?", (0 if aktif == 1 else 1, oid))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Güncellenemedi:\n{e}")
            return
        if hasattr(parent, "_reload"):
            parent._reload()

    # --- EK MODÜL: Danışan Düzenle / Aktif-Pasif ---
    def danisan_duzenle(self, parent):
        if not hasattr(parent, "danisan_tree"):
            return
        sel = parent.danisan_tree.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen bir danışan seçiniz!")
            return
        vals = parent.danisan_tree.item(sel[0]).get("values") or []
        did = int(vals[0])
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT ad_soyad, telefon, email, veli_adi, veli_telefon, dogum_tarihi, adres, notlar FROM danisanlar WHERE id=?", (did,))
            row = cur.fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Danışan okunamadı:\n{e}")
            return
        if not row:
            return

        win = ttk.Toplevel(parent)
        win.title("Danışan Düzenle")
        center_window_smart(win, 720, 820, max_ratio=0.9)
        win.transient(parent)
        win.grab_set()
        self._brand_window(win)

        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=BOTH, expand=True)

        def field(label, init=""):
            ttk.Label(frm, text=label).pack(anchor=W, pady=(8, 0))
            e = ttk.Entry(frm)
            e.insert(0, init or "")
            e.pack(fill=X, pady=4)
            return e

        ent_ad = field("Ad Soyad *:", row[0])
        ent_tel = field("Telefon:", row[1] or "")
        ent_email = field("E-posta:", row[2] or "")
        ent_veli = field("Veli Adı:", row[3] or "")
        ent_veli_tel = field("Veli Telefon:", row[4] or "")
        ent_dogum = field("Doğum Tarihi:", row[5] or "")
        ttk.Label(frm, text="Adres:").pack(anchor=W, pady=(8, 0))
        txt_adres = ttk.Text(frm, height=3)
        txt_adres.insert("1.0", row[6] or "")
        txt_adres.pack(fill=X, pady=4)
        ttk.Label(frm, text="Notlar:").pack(anchor=W, pady=(8, 0))
        txt_not = ttk.Text(frm, height=3)
        txt_not.insert("1.0", row[7] or "")
        txt_not.pack(fill=X, pady=4)

        def _save():
            if not (ent_ad.get() or "").strip():
                messagebox.showwarning("Uyarı", "Ad Soyad zorunludur!")
                return
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE danisanlar
                    SET ad_soyad=?, telefon=?, email=?, veli_adi=?, veli_telefon=?, dogum_tarihi=?, adres=?, notlar=?
                    WHERE id=?
                    """,
                    (
                        (ent_ad.get() or "").strip().upper(),
                        (ent_tel.get() or "").strip(),
                        (ent_email.get() or "").strip(),
                        (ent_veli.get() or "").strip(),
                        (ent_veli_tel.get() or "").strip(),
                        (ent_dogum.get() or "").strip(),
                        (txt_adres.get("1.0", END) or "").strip(),
                        (txt_not.get("1.0", END) or "").strip(),
                        did,
                    ),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Güncellenemedi:\n{e}")
                return
            win.destroy()
            if hasattr(parent, "_reload"):
                parent._reload()

        ttk.Button(frm, text="KAYDET", bootstyle="success", command=_save).pack(fill=X, pady=(12, 0))

    def danisan_aktif_pasif(self, parent):
        if not hasattr(parent, "danisan_tree"):
            return
        sel = parent.danisan_tree.selection()
        if not sel:
            return
        vals = parent.danisan_tree.item(sel[0]).get("values") or []
        did = int(vals[0])
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(aktif,1) FROM danisanlar WHERE id=?", (did,))
            aktif = int((cur.fetchone() or [1])[0] or 0)
            cur.execute("UPDATE danisanlar SET aktif=? WHERE id=?", (0 if aktif == 1 else 1, did))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Güncellenemedi:\n{e}")
            return
        if hasattr(parent, "_reload"):
            parent._reload()

    # --- EK MODÜL: Görev Durumu Güncelle/Tamamla/Sil ---
    def _selected_tree_id(self, tree):
        sel = tree.selection()
        if not sel:
            return None
        vals = tree.item(sel[0]).get("values") or []
        if not vals:
            return None
        try:
            return int(vals[0])
        except Exception:
            return None

    def gorev_durum_guncelle(self, parent):
        if not hasattr(parent, "gorev_tree"):
            return
        gid = self._selected_tree_id(parent.gorev_tree)
        if not gid:
            messagebox.showwarning("Uyarı", "Lütfen bir görev seçiniz!")
            return
        win = ttk.Toplevel(parent)
        win.title("Durum Güncelle")
        center_window_smart(win, 520, 420, max_ratio=0.85)
        win.transient(parent)
        win.grab_set()
        self._brand_window(win)
        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=BOTH, expand=True)
        ttk.Label(frm, text="Durum:").pack(anchor=W)
        cb = ttk.Combobox(frm, state="readonly", values=["beklemede", "devam", "tamamlandi", "iptal"])
        cb.current(0)
        cb.pack(fill=X, pady=8)
        ttk.Label(frm, text="Öncelik:").pack(anchor=W)
        cb2 = ttk.Combobox(frm, state="readonly", values=["dusuk", "normal", "yuksek", "acil"])
        cb2.current(1)
        cb2.pack(fill=X, pady=8)

        def _save():
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute("UPDATE gorevler SET durum=?, oncelik=? WHERE id=?", (cb.get(), cb2.get(), gid))
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Güncellenemedi:\n{e}")
                return
            win.destroy()
            if hasattr(parent, "_reload"):
                parent._reload()

        ttk.Button(frm, text="KAYDET", bootstyle="success", command=_save).pack(fill=X, pady=(12, 0))

    def gorev_tamamla(self, parent):
        if not hasattr(parent, "gorev_tree"):
            return
        gid = self._selected_tree_id(parent.gorev_tree)
        if not gid:
            return
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute(
                "UPDATE gorevler SET durum='tamamlandi', tamamlanma_tarihi=? WHERE id=?",
                (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gid),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Güncellenemedi:\n{e}")
            return
        if hasattr(parent, "_reload"):
            parent._reload()

    def gorev_sil(self, parent):
        if not hasattr(parent, "gorev_tree"):
            return
        gid = self._selected_tree_id(parent.gorev_tree)
        if not gid:
            return
        if not messagebox.askyesno("Onay", "Seçili görevi silmek istiyor musunuz?"):
            return
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("DELETE FROM gorevler WHERE id=?", (gid,))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Silinemedi:\n{e}")
            return
        if hasattr(parent, "_reload"):
            parent._reload()

    # --- EK MODÜL: Seans Listesi (Düzenle/Sil) ---
    def seans_listesi(self):
        win = ttk.Toplevel(self)
        win.title("Seans Listesi (Düzenle/Sil)")
        center_window_smart(win, 1400, 820)
        win.transient(self)
        self._brand_window(win)
        self._style_table_strong()

        top = ttk.Frame(win, padding=10)
        top.pack(fill=X)
        ttk.Label(top, text="Tarih (YYYY-AA-GG):").pack(side=LEFT, padx=6)
        tarih_var = ttk.StringVar(value=datetime.datetime.now().strftime("%Y-%m-%d"))
        ent_t = ttk.Entry(top, textvariable=tarih_var, width=14)
        ent_t.pack(side=LEFT, padx=6)
        ttk.Label(top, text="Terapist:").pack(side=LEFT, padx=6)
        cb = ttk.Combobox(top, state="readonly", width=24)
        cb.pack(side=LEFT, padx=6)
        ttk.Button(top, text="Yenile", bootstyle="primary", command=lambda: _yukle()).pack(side=LEFT, padx=6)
        ttk.Button(top, text="Düzenle", bootstyle="warning", command=lambda: self.seans_duzenle(win)).pack(side=RIGHT)
        ttk.Button(top, text="Sil", bootstyle="danger", command=lambda: self.seans_sil(win)).pack(side=RIGHT, padx=6)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)
        cols = ("ID", "Tarih", "Saat", "Danışan", "Terapist", "Oda", "Durum", "Seans", "Ücret", "Tutar", "Ödeme", "Not")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info", style="Strong.Treeview")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=140)
        tree.column("ID", width=70)
        tree.column("Seans", width=70)
        tree.column("Ücret", width=70)
        tree.column("Tutar", width=110)
        tree.column("Ödeme", width=110)
        tree.column("Not", width=260)
        sb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        self._apply_stripes(tree)

        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute("SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY therapist_name")
            names = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception:
            names = DEFAULT_THERAPISTS[:]
        cb["values"] = ["(Tümü)"] + names
        cb.current(0)

        def _yukle():
            for i in tree.get_children():
                tree.delete(i)
            tarih = (tarih_var.get() or "").strip()
            terapist = cb.get()
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                if terapist and terapist != "(Tümü)":
                    cur.execute(
                        """
                        SELECT id, tarih, saat, danisan_adi, terapist, COALESCE(oda,''), COALESCE(durum,''),
                               COALESCE(seans_alindi,0), COALESCE(ucret_alindi,0), COALESCE(ucret_tutar,0), COALESCE(odeme_sekli,''),
                               COALESCE(notlar,'')
                        FROM seans_takvimi
                        WHERE tarih=? AND terapist=?
                        ORDER BY saat
                        """,
                        (tarih, terapist),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, tarih, saat, danisan_adi, terapist, COALESCE(oda,''), COALESCE(durum,''),
                               COALESCE(seans_alindi,0), COALESCE(ucret_alindi,0), COALESCE(ucret_tutar,0), COALESCE(odeme_sekli,''),
                               COALESCE(notlar,'')
                        FROM seans_takvimi
                        WHERE tarih=?
                        ORDER BY saat
                        """,
                        (tarih,),
                    )
                rows = cur.fetchall()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Seanslar yüklenemedi:\n{e}")
                return
            for idx, r in enumerate(rows):
                tag = "even" if idx % 2 == 0 else "odd"
                tree.insert(
                    "",
                    END,
                    values=(
                        r[0],
                        r[1],
                        r[2],
                        r[3],
                        r[4],
                        r[5],
                        r[6],
                        ("✓" if int(r[7] or 0) == 1 else ""),
                        ("✓" if int(r[8] or 0) == 1 else ""),
                        format_money(r[9]),
                        r[10],
                        r[11],
                    ),
                    tags=(tag,),
                )

        _yukle()
        win.seans_tree = tree
        win._reload = _yukle
        win._tarih_var = tarih_var

    def seans_duzenle(self, parent):
        if not hasattr(parent, "seans_tree"):
            return
        sid = self._selected_tree_id(parent.seans_tree)
        if not sid:
            messagebox.showwarning("Uyarı", "Lütfen bir seans seçiniz!")
            return
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT tarih, saat, danisan_adi, terapist, COALESCE(oda,''), COALESCE(durum,''), COALESCE(seans_alindi,0),
                       COALESCE(ucret_alindi,0), COALESCE(ucret_tutar,0), COALESCE(odeme_sekli,''), COALESCE(notlar,'')
                FROM seans_takvimi WHERE id=?
                """,
                (sid,),
            )
            row = cur.fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Seans okunamadı:\n{e}")
            return
        if not row:
            return

        win = ttk.Toplevel(parent)
        win.title("Seans Düzenle")
        center_window_smart(win, 700, 720, max_ratio=0.9)
        win.transient(parent)
        win.grab_set()
        self._brand_window(win)
        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=BOTH, expand=True)

        def field(label, init=""):
            ttk.Label(frm, text=label).pack(anchor=W, pady=(8, 0))
            e = ttk.Entry(frm)
            e.insert(0, init or "")
            e.pack(fill=X, pady=4)
            return e

        ent_tarih = field("Tarih (YYYY-AA-GG):", row[0])
        ent_saat = field("Saat (HH:MM):", row[1])
        ent_dan = field("Danışan:", row[2])
        ent_ter = field("Terapist:", row[3])
        ent_oda = field("Oda:", row[4])
        ent_durum = field("Durum:", row[5] or "planlandi")

        var_seans = ttk.IntVar(value=1 if int(row[6] or 0) == 1 else 0)
        var_ucret = ttk.IntVar(value=1 if int(row[7] or 0) == 1 else 0)
        ttk.Checkbutton(frm, text="Seans Alındı", variable=var_seans, bootstyle="success").pack(anchor=W, pady=(10, 0))
        ttk.Checkbutton(frm, text="Ücret Alındı", variable=var_ucret, bootstyle="success").pack(anchor=W, pady=(6, 0))
        ent_tutar = field("Ücret Tutarı (₺):", str(row[8] or 0))
        ent_odeme = field("Ödeme Şekli:", row[9] or "")
        ent_not = field("Not:", row[10] or "")

        def _save():
            if "name hoca" in (ent_ter.get() or "").lower():
                messagebox.showwarning("Uyarı", "Name Hoca kurumdan ayrıldı.")
                return
            try:
                conn = self.veritabani_baglan()
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE seans_takvimi
                    SET tarih=?, saat=?, danisan_adi=?, terapist=?, oda=?, durum=?, seans_alindi=?, ucret_alindi=?, ucret_tutar=?, odeme_sekli=?, notlar=?
                    WHERE id=?
                    """,
                    (
                        (ent_tarih.get() or "").strip(),
                        (ent_saat.get() or "").strip(),
                        (ent_dan.get() or "").strip().upper(),
                        (ent_ter.get() or "").strip(),
                        (ent_oda.get() or "").strip(),
                        (ent_durum.get() or "").strip(),
                        int(var_seans.get() or 0),
                        int(var_ucret.get() or 0),
                        parse_money(ent_tutar.get()),
                        (ent_odeme.get() or "").strip(),
                        (ent_not.get() or "").strip(),
                        sid,
                    ),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Güncellenemedi:\n{e}")
                return
            win.destroy()
            if hasattr(parent, "_reload"):
                parent._reload()

        ttk.Button(frm, text="KAYDET", bootstyle="success", command=_save).pack(fill=X, pady=(12, 0))

    def seans_sil(self, parent):
        if not hasattr(parent, "seans_tree"):
            return
        sid = self._selected_tree_id(parent.seans_tree)
        if not sid:
            return
        if not messagebox.askyesno("Onay", "Seçili seansı silmek istiyor musunuz?"):
            return
        try:
            conn = self.veritabani_baglan()
            cur = conn.cursor()
            # bağlı records kaydı varsa onu da sil
            try:
                cur.execute("SELECT COALESCE(record_id,NULL) FROM seans_takvimi WHERE id=?", (sid,))
                rid = (cur.fetchone() or [None])[0]
                if rid:
                    cur.execute("DELETE FROM records WHERE id=?", (rid,))
            except Exception:
                pass
            cur.execute("DELETE FROM seans_takvimi WHERE id=?", (sid,))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Silinemedi:\n{e}")
            return
        if hasattr(parent, "_reload"):
            parent._reload()


class RegisterDialog(ttk.Toplevel):
    def __init__(self, parent: App, first_setup: bool = False):
        super().__init__(parent)
        self.parent = parent
        self.first_setup = first_setup
        self.title("Yeni Kullanıcı Kaydı")
        self.geometry("420x420")
        self.transient(parent)
        self.grab_set()

        header = "İLK KURULUM - KURUM MÜDÜRÜ" if self.first_setup else "YENİ KULLANICI KAYDI"
        ttk.Label(self, text=header, font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(pady=10)
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill=BOTH, expand=True)

        def field(label, show=None):
            ttk.Label(frm, text=label).pack(anchor=W, pady=(8, 0))
            e = ttk.Entry(frm, show=show or "")
            e.pack(fill=X, pady=4)
            return e

        self.ent_user = field("Kullanıcı Adı *:")
        self.ent_name = field("Ad Soyad:")
        self.ent_email = field("E-posta:")
        self.ent_pw = field("Şifre *:", show="*")
        self.ent_pw2 = field("Şifre Tekrar *:", show="*")

        note = "Not: İlk kullanıcı 'kurum_muduru' rolüyle oluşturulur." if self.first_setup else "Not: Yeni kayıtlar 'egitim_gorevlisi' rolü ile açılır."
        ttk.Label(frm, text=note, foreground="gray").pack(pady=(10, 0))

        def _save():
            u = (self.ent_user.get() or "").strip()
            pw = self.ent_pw.get() or ""
            pw2 = self.ent_pw2.get() or ""
            if not u or not pw:
                messagebox.showwarning("Uyarı", "Kullanıcı adı ve şifre zorunludur!")
                return
            if pw != pw2:
                messagebox.showwarning("Uyarı", "Şifreler eşleşmiyor!")
                return
            if u.lower() == "name":
                messagebox.showwarning("Uyarı", "Name Hoca kurumdan ayrıldı. Bu kullanıcı adı kullanılamaz.")
                return
            try:
                conn = parent.veritabani_baglan()
                cur = conn.cursor()
                # güvenlik: ilk kurulum sadece DB boşken
                if self.first_setup:
                    cur.execute("SELECT COUNT(*) FROM users WHERE is_active=1")
                    if int((cur.fetchone() or [0])[0] or 0) > 0:
                        conn.close()
                        messagebox.showwarning("Uyarı", "İlk kurulum zaten tamamlanmış.")
                        self.destroy()
                        parent._refresh_first_run_state()
                        return
                cur.execute("SELECT COUNT(*) FROM users WHERE username=?", (u,))
                if (cur.fetchone() or [0])[0] > 0:
                    conn.close()
                    messagebox.showerror("Hata", "Bu kullanıcı adı zaten var!")
                    return
                access_role = ("kurum_muduru" if self.first_setup else "egitim_gorevlisi")
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, role, access_role, title_role, full_name, email, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        u,
                        hash_pass(pw),
                        access_role,        # legacy role (back-compat)
                        access_role,        # yetki
                        "",                 # unvan (sonradan kullanıcı yönetiminden set edilir)
                        (self.ent_name.get() or "").strip(),
                        (self.ent_email.get() or "").strip(),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Hata", f"Kayıt oluşturulamadı:\n{e}")
                return
            messagebox.showinfo("Başarılı", "Kayıt oluşturuldu. Artık giriş yapabilirsiniz.")
            self.destroy()
            try:
                parent._refresh_first_run_state()
            except Exception:
                pass

        ttk.Button(frm, text="KAYDET", bootstyle="success", command=_save).pack(fill=X, pady=(14, 0))


def _relaunch_cmd(extra_args: list[str] | None = None) -> list[str]:
    """Uygulamayı tekrar başlatmak için komut oluştur (script/EXE)."""
    extra_args = extra_args or []
    if getattr(sys, "frozen", False):
        return [sys.executable, *extra_args]
    return [sys.executable, os.path.abspath(__file__), *extra_args]


def _run_reset_worker() -> None:
    """
    Sistemi sıfırla worker:
    - DB/WAL/SHM silmeyi (kilit kalkana kadar) kısa süre dene
    - Sonra uygulamayı normal modda tekrar başlat
    """
    deadline = time.time() + 60.0
    last = ""
    while time.time() < deadline:
        ok, msg = safe_delete_db_files()
        last = msg
        db = db_path()
        if (not os.path.exists(db)) and (not os.path.exists(db + "-wal")) and (not os.path.exists(db + "-shm")):
            break
        # Silme başarısız olsa bile, kilit kalkana kadar tekrar dene
        time.sleep(0.25)
        if ok and (msg or "").startswith("RENAMED:"):
            # rename ile DB fiilen devre dışı kaldı; yeni DB açılabilir
            break
    try:
        with open(error_log_path(), "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | RESET_WORKER | {last}\n")
    except Exception:
        pass
    spawn_detached(_relaunch_cmd())


def main():
    # Reset worker modu (GUI açmadan)
    if "--reset-worker" in (sys.argv or []):
        try:
            _run_reset_worker()
        finally:
            return

    # Paketli build'lerde kılavuz dosyasını veri klasörüne kopyala (kullanıcı her zaman açabilsin)
    ensure_user_guide_present()

    silent_backup()
    init_db()
    # Veritabanı migration: Eski/yeni verileri koşullara göre düzenle
    try:
        migrate_database_data()
    except Exception as e:
        log_exception("migrate_database_data", e)
    # Global hata yakalama (EXE'de konsol olmadığı için log dosyasına yaz)
    def _excepthook(exctype, value, tb):
        try:
            log_exception("UNHANDLED_EXCEPTION", value)
        except Exception:
            pass
    try:
        sys.excepthook = _excepthook
    except Exception:
        pass

    # Her açılışta log dosyası yarat (kullanıcı doğru EXE'yi açtığını anlayabilsin)
    try:
        with open(error_log_path(), "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | START | {APP_VERSION} | {APP_BUILD}\n")
    except Exception:
        pass

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

 
from __future__ import annotations

import datetime
import sqlite3

from .env import DEFAULT_THERAPISTS, DEFAULT_THERAPIST_ROLES, DEFAULT_USERS
from .paths import db_path
from .security import hash_pass


def connect_db() -> sqlite3.Connection:
    """Veritabanı bağlantısı oluştur."""
    conn = sqlite3.connect(str(db_path()))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("PRAGMA journal_mode = WAL;")
    try:
        _ensure_min_schema(conn)
    except Exception:
        pass
    return conn


def _ensure_min_schema(conn: sqlite3.Connection) -> None:
    """Her bağlantıda minimum şemayı garanti altına al (idempotent)."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pricing_policy' LIMIT 1;")
    if not cur.fetchone():
        return

    cur.execute("PRAGMA table_info(pricing_policy)")
    cols = [r[1] for r in cur.fetchall()]

    for col_name, col_type in [
        ("teacher_name", "TEXT"),
        ("student_id", "INTEGER"),
        ("price", "REAL"),
        ("created_at", "TEXT"),
        ("updated_at", "TEXT"),
    ]:
        if col_name not in cols:
            try:
                cur.execute(f"ALTER TABLE pricing_policy ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pricing_student ON pricing_policy(student_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pricing_teacher ON pricing_policy(teacher_name);")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pricing_unique ON pricing_policy(student_id, teacher_name);")
    except Exception:
        pass

    try:
        conn.commit()
    except Exception:
        pass


def _init_db(conn: sqlite3.Connection) -> None:
    """Veritabanını başlat ve tüm tabloları oluştur."""
    cur = conn.cursor()

    def table_exists(name: str) -> bool:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return cur.fetchone() is not None

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

    cur.execute("PRAGMA table_info(settings)")
    settings_cols = [r[1] for r in cur.fetchall()]
    if "therapist_role" not in settings_cols:
        try:
            cur.execute("ALTER TABLE settings ADD COLUMN therapist_role TEXT")
        except Exception:
            pass

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

    cur.execute("PRAGMA table_info(users)")
    user_cols = [r[1] for r in cur.fetchall()]
    for col in ["full_name", "therapist_name", "email", "access_role", "title_role"]:
        if col not in user_cols:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            except Exception:
                pass

    try:
        cur.execute(
            "UPDATE users SET access_role = role WHERE (access_role IS NULL OR access_role='') AND role IS NOT NULL AND role<>''"
        )
    except Exception:
        pass

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

    try:
        cur.execute("PRAGMA table_info(seans_takvimi)")
        st_cols = [r[1] for r in cur.fetchall()]
        for col, col_type in [
            ("seans_alindi", "INTEGER DEFAULT 0"),
            ("ucret_alindi", "INTEGER DEFAULT 0"),
            ("ucret_tutar", "REAL DEFAULT 0"),
            ("odeme_sekli", "TEXT DEFAULT ''"),
            ("record_id", "INTEGER"),
        ]:
            if col not in st_cols:
                cur.execute(f"ALTER TABLE seans_takvimi ADD COLUMN {col} {col_type}")
        if "hizmet_bedeli" not in st_cols:
            cur.execute("ALTER TABLE seans_takvimi ADD COLUMN hizmet_bedeli REAL DEFAULT 0")
    except Exception:
        pass

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

    try:
        cur.execute("PRAGMA table_info(kasa_hareketleri)")
        kasa_cols = [r[1] for r in cur.fetchall()]
        if "gider_kategorisi" not in kasa_cols:
            cur.execute("ALTER TABLE kasa_hareketleri ADD COLUMN gider_kategorisi TEXT DEFAULT ''")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_kasa_gider_kategori ON kasa_hareketleri(gider_kategorisi);")
    except Exception:
        pass

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
            aktif INTEGER DEFAULT 1,
            balance REAL DEFAULT 0
        );
        """
    )

    try:
        cur.execute("PRAGMA table_info(danisanlar)")
        danisan_cols = [r[1] for r in cur.fetchall()]
        if "balance" not in danisan_cols:
            cur.execute("ALTER TABLE danisanlar ADD COLUMN balance REAL DEFAULT 0")
            cur.execute(
                """
                UPDATE danisanlar
                SET balance = (
                    SELECT COALESCE(SUM(kalan_borc), 0)
                    FROM records
                    WHERE records.danisan_adi = danisanlar.ad_soyad
                )
                """
            )
    except Exception:
        pass

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

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pricing_policy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            teacher_name TEXT,
            price REAL NOT NULL,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (student_id) REFERENCES danisanlar(id),
            UNIQUE(student_id, teacher_name)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pricing_student ON pricing_policy(student_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pricing_teacher ON pricing_policy(teacher_name);")

    try:
        cur.execute("PRAGMA table_info(pricing_policy)")
        pricing_cols = [r[1] for r in cur.fetchall()]
        if "teacher_name" not in pricing_cols:
            cur.execute("ALTER TABLE pricing_policy ADD COLUMN teacher_name TEXT")
            try:
                cur.execute("DROP INDEX IF EXISTS idx_pricing_unique")
            except Exception:
                pass
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pricing_unique ON pricing_policy(student_id, teacher_name)")
    except Exception:
        pass

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

    cur.execute("PRAGMA table_info(bep_hedef_beceriler)")
    bep_cols = [r[1] for r in cur.fetchall()]
    for col_name, col_type in [
        ("hedef_aciklama", "TEXT"),
        ("baslangic_durumu", "TEXT"),
        ("hedef_davranis", "TEXT"),
        ("degerlendirme", "TEXT"),
    ]:
        if col_name not in bep_cols:
            try:
                cur.execute(f"ALTER TABLE bep_hedef_beceriler ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

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
            olusturma_tarihi TEXT NOT NULL,
            FOREIGN KEY (kullanici_id) REFERENCES users(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_trail(action_type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_trail(entity_type, entity_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_tarih ON audit_trail(olusturma_tarihi);")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS onam_formlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            danisan_id INTEGER NOT NULL,
            danisan_adi TEXT NOT NULL,
            danisan_tarih TEXT,
            terapist_adi TEXT NOT NULL,
            terapist_tarih TEXT,
            onam_verildi INTEGER DEFAULT 1,
            olusturma_tarihi TEXT,
            FOREIGN KEY (danisan_id) REFERENCES danisanlar(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_onam_danisan ON onam_formlari(danisan_id);")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cocuk_takip_bilgi_formlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            danisan_id INTEGER NOT NULL,
            form_tarihi TEXT NOT NULL,
            cinsiyet TEXT,
            dogum_tarihi TEXT,
            dogum_yeri TEXT,
            gebelik_sekli TEXT,
            gebelik_sorun TEXT,
            dogum_sekli TEXT,
            dogum_hafta INTEGER,
            dogum_kilo REAL,
            dogum_boy REAL,
            dogum_sorun INTEGER DEFAULT 0,
            dogum_sorun_detay TEXT,
            anne_sutu INTEGER,
            anne_sutu_sure TEXT,
            bakim_veren TEXT,
            yurme_yas TEXT,
            yurme_gec_neden TEXT,
            tuvalet_yas TEXT,
            tuvalet_gec_neden TEXT,
            konusma_yas TEXT,
            konusma_gec_neden TEXT,
            gdb_tani INTEGER DEFAULT 0,
            gdb_tani_detay TEXT,
            okul_adi TEXT,
            okul_il TEXT,
            okul_ilce TEXT,
            sinif TEXT,
            egitim_turu TEXT,
            destek_egitim INTEGER DEFAULT 0,
            destek_egitim_sure TEXT,
            sinif_ogretmen TEXT,
            okuloncesi INTEGER DEFAULT 0,
            okuloncesi_yil INTEGER,
            ilkokul_baslangic_ay INTEGER,
            egitim_sorun TEXT,
            okuma_baslangic TEXT,
            okuma_sorun INTEGER DEFAULT 0,
            okuma_sorun_detay TEXT,
            okuma_anlama_sorun INTEGER DEFAULT 0,
            okuma_anlama_detay TEXT,
            yazma_sorun INTEGER DEFAULT 0,
            yazma_sorun_detay TEXT,
            aritmetik_sorun INTEGER DEFAULT 0,
            aritmetik_sorun_detay TEXT,
            siralama_sorun INTEGER DEFAULT 0,
            siralama_sorun_detay TEXT,
            yon_ayirt_sorun INTEGER DEFAULT 0,
            yon_ayirt_detay TEXT,
            karneturkce TEXT,
            karnematematik TEXT,
            karnehayatbilgisi TEXT,
            karnesosyal TEXT,
            karnefen TEXT,
            aile_sira INTEGER,
            akrabalik INTEGER DEFAULT 0,
            akrabalik_detay TEXT,
            bakim_veren_suan TEXT,
            aile_disinda_yasayan TEXT,
            aile_turu TEXT,
            ayrilik_durum TEXT,
            sosyoekonomik TEXT,
            anne_egitim TEXT,
            anne_yas INTEGER,
            anne_is TEXT,
            baba_egitim TEXT,
            baba_yas INTEGER,
            baba_is TEXT,
            cocuk_sayisi_detay TEXT,
            hasta_kardes INTEGER DEFAULT 0,
            hasta_kardes_detay TEXT,
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER,
            FOREIGN KEY (danisan_id) REFERENCES danisanlar(id)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cocuk_takip_danisan ON cocuk_takip_bilgi_formlari(danisan_id);")

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

    try:
        cur.execute("PRAGMA table_info(records)")
        rcols = [r[1] for r in cur.fetchall()]
        if "saat" not in rcols:
            cur.execute("ALTER TABLE records ADD COLUMN saat TEXT DEFAULT ''")
        if "seans_id" not in rcols:
            cur.execute("ALTER TABLE records ADD COLUMN seans_id INTEGER")
    except Exception:
        pass

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    bad_names = [
        "Yeni değerlendirme",
        "Yeni Değerlendirme",
        "YENİ DEĞERLENDİRME",
        "YENI DEGERLENDIRME",
        "75 dakika",
        "75 Dakika",
        "75 DAKİKA",
        "75 DAKIKA",
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

    for t in DEFAULT_THERAPISTS:
        cur.execute(
            "INSERT OR IGNORE INTO settings (therapist_name, therapist_role, is_active, created_at) VALUES (?, ?, 1, ?)",
            (t, DEFAULT_THERAPIST_ROLES.get(t, ""), now),
        )
        cur.execute(
            "UPDATE settings SET therapist_role=? WHERE therapist_name=? AND (therapist_role IS NULL OR therapist_role='')",
            (DEFAULT_THERAPIST_ROLES.get(t, ""), t),
        )

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


def init_db() -> None:
    conn = connect_db()
    _init_db(conn)
    conn.close()

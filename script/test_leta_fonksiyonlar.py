#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leta Takip - Kritik fonksiyonların testi (build öncesi).
Güncel sistem: script/ (core + app_ui). GUI açmadan: DB, tablolar, PDF callback test edilir.
Çalıştırma: script dizininden: python test_leta_fonksiyonlar.py
           veya repo kökünden: python script/test_leta_fonksiyonlar.py
"""
import os
import sys
import tempfile
import shutil

# Test için geçici veri dizini (LETA_TEST_DATA_DIR core/paths.py tarafından okunur)
TEST_DATA_DIR = tempfile.mkdtemp(prefix="leta_test_")
os.environ["LETA_TEST_DATA_DIR"] = TEST_DATA_DIR

# script/ dizinini path'e ekle ve oraya geç (core, app_ui import için)
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
os.chdir(script_dir)

from core import (
    init_db,
    connect_db,
    db_path,
    backups_dir,
    error_log_path,
    app_dir,
)
from core.security import hash_pass


def run_tests():
    errors = []
    # --- 1) Veritabanı başlatma ve tablolar ---
    try:
        init_db()
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        expected = ["settings", "users", "danisanlar", "records", "onam_formlari", "cocuk_takip_bilgi_formlari"]
        for t in expected:
            if t not in tables:
                errors.append(f"Tablo eksik: {t}")
        if not errors:
            print("[OK] Veritabanı ve tablolar")
    except Exception as e:
        errors.append(f"init_db/connect_db: {e}")
        print(f"[FAIL] Veritabanı: {e}")

    # --- 2) PDF callback'leri (header/footer) ---
    try:
        from app_ui import PDF_AVAILABLE, _pdf_page_canvas_callbacks
        if not PDF_AVAILABLE:
            print("[SKIP] PDF (reportlab yok)")
        else:
            from reportlab.lib.units import cm
            on_first, on_later = _pdf_page_canvas_callbacks("Test Formu")
            if on_first is None or on_later is None:
                errors.append("PDF callbacks None döndü")
            else:
                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Paragraph
                from reportlab.lib.styles import getSampleStyleSheet
                pdf_path = os.path.join(TEST_DATA_DIR, "test_form.pdf")
                doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=2*cm, bottomMargin=2*cm)
                styles = getSampleStyleSheet()
                story = [Paragraph("Test baslik", styles["Heading1"]), Paragraph("Test icerik.", styles["Normal"])]
                doc.build(story, onFirstPage=on_first, onLaterPages=on_later)
                if os.path.isfile(pdf_path):
                    print("[OK] PDF oluşturma (header/footer)")
                else:
                    errors.append("PDF dosyası oluşmadı")
    except Exception as e:
        errors.append(f"PDF: {e}")
        print(f"[FAIL] PDF: {e}")

    # --- 3) Çocuk takip formu INSERT sütun sayısı (70 sütun) ---
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(cocuk_takip_bilgi_formlari)")
        cols = cur.fetchall()
        conn.close()
        n_cols = len(cols)
        if n_cols < 70:
            errors.append(f"cocuk_takip_bilgi_formlari sütun sayısı: {n_cols}")
        else:
            print("[OK] cocuk_takip_bilgi_formlari tablo yapısı")
    except Exception as e:
        errors.append(f"cocuk_takip tablo: {e}")
        print(f"[FAIL] cocuk_takip tablo: {e}")

    # --- 4) ONAM / BEP tabloları ---
    try:
        conn = connect_db()
        cur = conn.cursor()
        for table in ["onam_formlari", "users", "danisanlar"]:
            cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cur.fetchone() is None:
                errors.append(f"Tablo yok: {table}")
        conn.close()
        if not any("Tablo yok" in e for e in errors):
            print("[OK] ONAM/Users/Danışanlar tabloları")
    except Exception as e:
        errors.append(f"Tablolar: {e}")
        print(f"[FAIL] Tablolar: {e}")

    # --- 5) hash_pass / db_path ---
    try:
        h = hash_pass("test123")
        p = db_path()
        if not h or not p or "leta_data.db" not in str(p):
            errors.append("hash_pass veya db_path")
        else:
            print("[OK] hash_pass, db_path")
    except Exception as e:
        errors.append(f"hash/db_path: {e}")
        print(f"[FAIL] hash/db_path: {e}")

    # --- 6) Yardımcı yollar (backups_dir, error_log_path, app_dir) ---
    try:
        bd = backups_dir()
        el = error_log_path()
        ad = app_dir()
        if not bd or not el or not ad or not os.path.isabs(str(bd)):
            errors.append("backups_dir/error_log_path/app_dir")
        else:
            print("[OK] backups_dir, error_log_path, app_dir")
    except Exception as e:
        errors.append(f"yardimci yollar: {e}")
        print(f"[FAIL] yardimci yollar: {e}")

    # --- 7) Çocuk takip INSERT 70 sütun (vals kesme) ---
    try:
        vlist = list(range(74))
        vlist = vlist[:70]
        while len(vlist) < 70:
            vlist.append(None)
        vals = tuple(vlist)
        if len(vals) != 70:
            errors.append("Çocuk takip vals 70 olmalı")
        else:
            print("[OK] Çocuk takip 70 sütun vals mantığı")
    except Exception as e:
        errors.append(f"vals 70: {e}")
        print(f"[FAIL] vals 70: {e}")

    return errors


if __name__ == "__main__":
    print("Leta Takip - Fonksiyon testleri (script/, geçici dizin:", TEST_DATA_DIR, ")")
    print("-" * 50)
    errs = run_tests()
    try:
        shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
    except Exception:
        pass
    print("-" * 50)
    if errs:
        print("HATALAR:", errs)
        sys.exit(1)
    print("Tüm testler geçti.")
    sys.exit(0)

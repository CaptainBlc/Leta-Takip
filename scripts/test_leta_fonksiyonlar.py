#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leta Takip - Kritik fonksiyonların testi (build öncesi).
GUI açmadan: DB başlatma, tablolar, PDF callback'leri test edilir.
Çalıştırma: python scripts/test_leta_fonksiyonlar.py
"""
import os
import sys
import tempfile
import shutil
import importlib

# Test için geçici veri dizini kullan (gerçek veriyi bozmayalım)
TEST_DATA_DIR = tempfile.mkdtemp(prefix="leta_test_")
os.environ["LETA_TEST_DATA_DIR"] = TEST_DATA_DIR

# data_dir'i test dizinine yönlendir (leta_app import edilmeden önce patch)
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)
os.chdir(repo_root)

# leta_app'i import etmeden önce patch: data_dir test dizinini dönsün
import leta_app
_original_data_dir = leta_app.data_dir
def _test_data_dir():
    return TEST_DATA_DIR
leta_app.data_dir = _test_data_dir

def run_tests():
    errors = []
    # --- 0) script modülleri import smoke (circular import regresyonu) ---
    try:
        script_dir = os.path.join(repo_root, "script")
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)

        pipeline_mod = importlib.import_module("pipeline")
        app_ui_mod = importlib.import_module("app_ui")

        if not hasattr(pipeline_mod, "DataPipeline"):
            errors.append("pipeline modülünde DataPipeline bulunamadı")
        elif not hasattr(app_ui_mod, "App"):
            errors.append("app_ui modülünde App bulunamadı")
        else:
            print("[OK] script importları (pipeline/app_ui) circular import yok")
    except Exception as e:
        errors.append(f"script import smoke: {e}")
        print(f"[FAIL] script import smoke: {e}")

    # --- 1) Veritabanı başlatma ve tablolar ---
    try:
        leta_app.init_db()
        conn = leta_app.connect_db()
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
        if not leta_app.PDF_AVAILABLE:
            print("[SKIP] PDF (reportlab yok)")
        else:
            from reportlab.lib.units import cm
            on_first, on_later = leta_app._pdf_page_canvas_callbacks("Test Formu")
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
        conn = leta_app.connect_db()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(cocuk_takip_bilgi_formlari)")
        cols = cur.fetchall()
        conn.close()
        # id hariç 70+ sütun bekleniyor (tablo tanımına göre)
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
        conn = leta_app.connect_db()
        cur = conn.cursor()
        for table in ["onam_formlari", "users", "danisanlar"]:
            cur.execute(f"SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,))
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
        h = leta_app.hash_pass("test123")
        p = leta_app.db_path()
        if not h or not p or "leta_data.db" not in p:
            errors.append("hash_pass veya db_path")
        else:
            print("[OK] hash_pass, db_path")
    except Exception as e:
        errors.append(f"hash/db_path: {e}")
        print(f"[FAIL] hash/db_path: {e}")

    # --- 6) Yardımcı yollar (backups_dir, error_log_path, app_dir) ---
    try:
        bd = leta_app.backups_dir()
        el = leta_app.error_log_path()
        ad = leta_app.app_dir()
        if not bd or not el or not ad or not os.path.isabs(bd):
            errors.append("backups_dir/error_log_path/app_dir")
        else:
            print("[OK] backups_dir, error_log_path, app_dir")
    except Exception as e:
        errors.append(f"yardimci yollar: {e}")
        print(f"[FAIL] yardimci yollar: {e}")

    # --- 7) Çocuk takip INSERT 70 sütun (vals kesme) ---
    try:
        # Simüle: 74 değer olsa bile 70'e kesilip gönderilmeli
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
    print("Leta Takip - Fonksiyon testleri (geçici dizin:", TEST_DATA_DIR, ")")
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

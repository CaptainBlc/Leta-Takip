#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leta Takip - Kritik senaryo testleri (GUI açmadan).
Çalıştırma: repo kökünden `PYTHONPATH=script python script/test_leta_fonksiyonlar.py`
"""

import os
import sys
import tempfile
import shutil

TEST_DATA_DIR = tempfile.mkdtemp(prefix="leta_test_")
os.environ["LETA_TEST_DATA_DIR"] = TEST_DATA_DIR

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
os.chdir(script_dir)

from core import init_db, connect_db, db_path, backups_dir, error_log_path, app_dir
from core.security import hash_pass
from pipeline import DataPipeline


def _ok(msg: str):
    print(f"[OK] {msg}")


def _fail(errors, msg: str):
    errors.append(msg)
    print(f"[FAIL] {msg}")


def test_schema(errors):
    required_tables = [
        "users", "settings", "danisanlar", "seans_takvimi", "records",
        "kasa_hareketleri", "odeme_hareketleri", "pricing_policy", "audit_trail",
    ]
    try:
        init_db()
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}
        conn.close()
        missing = [t for t in required_tables if t not in tables]
        if missing:
            _fail(errors, f"Eksik tablolar: {missing}")
        else:
            _ok("Veritabanı temel şema")
    except Exception as e:
        _fail(errors, f"schema: {e}")


def test_pipeline_seans_odeme(errors):
    try:
        conn = connect_db()
        p = DataPipeline(conn, kullanici_id=1)

        sid = p.seans_kayit(
            tarih="2026-01-01",
            saat="10:00",
            danisan_adi="Oğuzhan İpek",
            terapist="Arif Hoca",
            hizmet_bedeli=1000,
            alinan_ucret=250,
            notlar="test",
            oda="A1",
            check_oda_cakisma=False,
        )
        if not sid:
            conn.close()
            _fail(errors, f"seans_kayit başarısız: {p.get_last_error()}")
            return

        cur = conn.cursor()
        cur.execute("SELECT id, seans_id, kalan_borc FROM records WHERE seans_id=?", (sid,))
        row = cur.fetchone()
        if not row:
            conn.close()
            _fail(errors, "records satırı oluşturulmadı")
            return

        rid, seans_id, kalan = row
        if int(seans_id or 0) != int(sid) or float(kalan or 0) != 750.0:
            conn.close()
            _fail(errors, f"ilk kalan borç hatalı: {row}")
            return

        ok = p.odeme_ekle(record_id=rid, tutar=300, tarih="2026-01-01", odeme_sekli="Nakit", aciklama="test odeme")
        if not ok:
            conn.close()
            _fail(errors, f"odeme_ekle başarısız: {p.get_last_error()}")
            return

        cur.execute("SELECT kalan_borc, alinan_ucret FROM records WHERE id=?", (rid,))
        kalan2, alinan2 = cur.fetchone() or (None, None)
        conn.close()
        if float(kalan2 or 0) != 450.0 or float(alinan2 or 0) != 550.0:
            _fail(errors, f"ödeme sonrası değerler hatalı: kalan={kalan2}, alinan={alinan2}")
        else:
            _ok("Pipeline seans + ödeme senaryosu")
    except Exception as e:
        _fail(errors, f"pipeline seans/odeme: {e}")


def test_turkish_name_dashboard(errors):
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO records (tarih, saat, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, seans_alindi, notlar, olusturma_tarihi, seans_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("2026-01-02", "11:00", "Göktuğ Ağır", "Arif Hoca", 500, 300, 200, 1, "", "2026-01-02 11:00:00", None),
                ("2026-01-03", "11:00", "Goktug Agir", "Arif Hoca", 400, 200, 200, 1, "", "2026-01-03 11:00:00", None),
            ],
        )
        conn.commit()

        p = DataPipeline(conn, kullanici_id=1)
        data = p.get_dashboard_data()
        borclular = data.get("borclular") or []
        conn.close()

        matched = [b for b in borclular if "goktug agir" in (b.get("danisan_adi", "").lower().replace("ğ", "g").replace("ı", "i").replace("ö", "o"))]
        if not matched:
            _fail(errors, "Türkçe karakterli borçlu dashboard'da bulunamadı")
            return
        toplam = sum(float(x.get("kalan_borc", 0) or 0) for x in matched)
        if toplam < 400:
            _fail(errors, f"Türkçe isim borç birikimi hatalı: {toplam}")
        else:
            _ok("Dashboard Türkçe isim borç toplama")
    except Exception as e:
        _fail(errors, f"turkish dashboard: {e}")


def test_pdf_callbacks(errors):
    try:
        import app_ui
        if not getattr(app_ui, "PDF_AVAILABLE", False):
            print("[SKIP] PDF (reportlab mevcut değil)")
            return

        on_first, on_later = app_ui._pdf_page_canvas_callbacks("Test Formu")
        if on_first is None or on_later is None:
            _fail(errors, "PDF callback None döndü")
            return

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet

        pdf_path = os.path.join(TEST_DATA_DIR, "test_form.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
        styles = getSampleStyleSheet()
        story = [Paragraph("Test", styles["Heading1"]), Paragraph("Icerik", styles["Normal"])]
        doc.build(story, onFirstPage=on_first, onLaterPages=on_later)

        if os.path.isfile(pdf_path):
            _ok("PDF callback + oluşturma")
        else:
            _fail(errors, "PDF dosyası oluşmadı")
    except Exception as e:
        _fail(errors, f"pdf callbacks: {e}")


def test_helpers(errors):
    try:
        h = hash_pass("test123")
        p = db_path()
        bd = backups_dir()
        el = error_log_path()
        ad = app_dir()
        if not h or "leta_data.db" not in str(p):
            _fail(errors, "hash_pass/db_path geçersiz")
            return
        if not os.path.isabs(str(bd)) or not el or not ad:
            _fail(errors, "path helper değerleri geçersiz")
            return
        _ok("Helper fonksiyonları")
    except Exception as e:
        _fail(errors, f"helpers: {e}")


def run_all_tests():
    errors = []
    test_schema(errors)
    test_pipeline_seans_odeme(errors)
    test_turkish_name_dashboard(errors)
    test_pdf_callbacks(errors)
    test_helpers(errors)
    return errors


if __name__ == "__main__":
    print("Leta Takip - Kritik senaryo testleri")
    print("Geçici veri dizini:", TEST_DATA_DIR)
    print("-" * 60)
    errs = run_all_tests()
    print("-" * 60)
    try:
        shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
    except Exception:
        pass

    if errs:
        print("HATALAR:")
        for e in errs:
            print(" -", e)
        sys.exit(1)

    print("Tüm test senaryoları geçti.")
    sys.exit(0)

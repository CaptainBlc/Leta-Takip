from __future__ import annotations

# Circular-import dayanıklılığı: yanlışlıkla modül içinde
# `from pipeline import DataPipeline` çağrılırsa ImportError oluşmasın.
DataPipeline = None  # type: ignore[assignment]

import datetime
import json
import sqlite3
import unicodedata
from typing import Any, Dict, List

from core.logging_utils import log_exception
from core.money import hesapla_personel_ucreti


class DataPipeline:
    """
    UI'nın beklediği stable API katmanı.
    DB şeması: core/db.py içindeki tablolarla uyumlu olmalı.
    """

    def __init__(self, conn: sqlite3.Connection, kullanici_id: int | None = None):
        self.conn = conn
        self.cur = conn.cursor()
        self.kullanici_id = kullanici_id
        self._listeners: Dict[str, List] = {}
        self._log_lines: List[str] = []

    # ---------- utils ----------
    def _now(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _today(self) -> str:
        return datetime.date.today().strftime("%Y-%m-%d")

    def _safe_float(self, x: Any) -> float:
        try:
            return float(str(x).replace(",", "."))
        except Exception:
            return 0.0

    def _normalize_name(self, value: str) -> str:
        v = " ".join((value or "").strip().upper().split())
        if not v:
            return ""
        try:
            v = "".join(
                ch for ch in unicodedata.normalize("NFKD", v)
                if not unicodedata.combining(ch)
            )
        except Exception:
            pass
        return v


    def table_exists(self, name: str) -> bool:
        try:
            self.cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                (name,),
            )
            return self.cur.fetchone() is not None
        except Exception:
            return False

    # UI bazı yerlerde _table_exists diye çağırmış olabilir (kırılmasın)
    def _table_exists(self, name: str) -> bool:
        return self.table_exists(name)

    def _log(self, msg: str) -> None:
        self._log_lines.append(f"{self._now()} | {msg}")

    def get_log(self) -> str:
        return "\n".join(self._log_lines[-500:])

    def _audit(self, action_type: str, entity_type: str, entity_id: int | None = None, details: dict | None = None) -> None:
        if not self.table_exists("audit_trail"):
            return
        try:
            self.cur.execute(
                """
                INSERT INTO audit_trail (action_type, entity_type, entity_id, kullanici_id, details, olusturma_tarihi)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    action_type,
                    entity_type,
                    entity_id,
                    self.kullanici_id,
                    json.dumps(details or {}, ensure_ascii=False),
                    self._now(),
                ),
            )
        except Exception:
            pass

    # ---------- events ----------
    def on(self, event: str, fn) -> None:
        self._listeners.setdefault(event, []).append(fn)

    def _trigger_event(self, event: str, payload: Any = None) -> None:
        for fn in self._listeners.get(event, []):
            try:
                fn(payload)
            except Exception:
                pass

    # ---------- core helpers ----------
    def _ensure_danisan_exists(self, danisan_upper: str) -> int | None:
        if not self.table_exists("danisanlar"):
            return None
        try:
            hedef = self._normalize_name(danisan_upper)
            self.cur.execute("SELECT id, ad_soyad FROM danisanlar")
            for row in self.cur.fetchall() or []:
                rid = int(row[0]) if row and row[0] is not None else None
                ad = self._normalize_name(str(row[1] or ""))
                if rid and ad == hedef:
                    return rid

            kayit_adi = " ".join((danisan_upper or "").strip().split())
            self.cur.execute(
                """
                INSERT INTO danisanlar
                (ad_soyad, telefon, email, veli_adi, veli_telefon, dogum_tarihi, adres, notlar, olusturma_tarihi, aktif, balance)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (kayit_adi, "", "", "", "", "", "", "", self._now(), 1, 0),
            )
            return int(self.cur.lastrowid or 0) or None
        except Exception as e:
            log_exception("pipeline.ensure_danisan", e)
            return None

    def _get_cocuk_id(self, danisan_upper: str) -> int | None:
        if not self.table_exists("danisanlar"):
            return None
        try:
            hedef = self._normalize_name(danisan_upper)
            self.cur.execute("SELECT id, ad_soyad FROM danisanlar")
            for row in self.cur.fetchall() or []:
                rid = int(row[0]) if row and row[0] is not None else None
                if rid and self._normalize_name(str(row[1] or "")) == hedef:
                    return rid
            return None
        except Exception:
            return None

    def _add_kasa(
        self,
        tarih: str,
        tip: str,
        aciklama: str,
        tutar: float,
        odeme_sekli: str = "",
        gider_kategorisi: str = "",
        record_id: int | None = None,
        seans_id: int | None = None,
    ) -> None:
        if not self.table_exists("kasa_hareketleri"):
            return
        try:
            self.cur.execute(
                """
                INSERT INTO kasa_hareketleri
                (tarih, tip, aciklama, tutar, odeme_sekli, gider_kategorisi, record_id, seans_id, olusturan_kullanici_id, olusturma_tarihi)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    tarih,
                    tip,
                    aciklama,
                    float(tutar or 0),
                    odeme_sekli,
                    gider_kategorisi,
                    record_id,
                    seans_id,
                    self.kullanici_id,
                    self._now(),
                ),
            )
        except Exception as e:
            log_exception("pipeline.kasa_insert", e)

    # ---------- API: Seans ----------
    def check_oda_cakismasi(self, tarih: str, saat: str, oda: str) -> bool:
        if not self.table_exists("seans_takvimi"):
            return False
        try:
            self.cur.execute(
                """
                SELECT COUNT(*)
                FROM seans_takvimi
                WHERE tarih=? AND COALESCE(saat,'')=? AND COALESCE(oda,'')=? AND COALESCE(durum,'')!='iptal'
                """,
                (tarih, saat, oda),
            )
            return int((self.cur.fetchone() or [0])[0] or 0) > 0
        except Exception:
            return False

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
        skip_pricing_update: bool = False,
        ensure_danisan: bool = True,
    ) -> int | None:
        danisan_clean = (danisan_adi or "").strip()
        terapist = (terapist or "").strip()
        tarih = (tarih or "").strip()
        saat = (saat or "").strip()
        oda = (oda or "").strip()
        notlar = (notlar or "").strip()

        hb = self._safe_float(hizmet_bedeli)
        au = self._safe_float(alinan_ucret)

        if not tarih or not danisan_clean or not terapist:
            return None

        try:
            self.conn.execute("BEGIN")

            cocuk_id = self._get_cocuk_id(danisan_clean)
            if ensure_danisan and cocuk_id is None:
                cocuk_id = self._ensure_danisan_exists(danisan_clean)

            if check_oda_cakisma and oda and self.check_oda_cakismasi(tarih, saat, oda):
                self.conn.rollback()
                return None

            kalan = max(0.0, hb - au)

            seans_id = None
            if self.table_exists("seans_takvimi"):
                self.cur.execute(
                    """
                    INSERT INTO seans_takvimi
                    (tarih, saat, danisan_adi, terapist, oda, durum, notlar,
                     hizmet_bedeli, odeme_sekli, seans_alindi, ucret_alindi,
                     olusturma_tarihi, olusturan_kullanici_id, record_id)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        tarih,
                        saat,
                        danisan_clean,
                        terapist,
                        oda,
                        "planlandi",
                        notlar,
                        hb,
                        "",
                        0,
                        1 if au > 0 else 0,
                        self._now(),
                        self.kullanici_id,
                        None,
                    ),
                )
                seans_id = int(self.cur.lastrowid or 0) or None

            record_id = None
            if self.table_exists("records"):
                self.cur.execute(
                    """
                    INSERT INTO records
                    (tarih, saat, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, seans_alindi, notlar, olusturma_tarihi, seans_id)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (tarih, saat, danisan_clean, terapist, hb, au, kalan, 0, notlar, self._now(), seans_id),
                )
                record_id = int(self.cur.lastrowid or 0) or None

            if seans_id and record_id and self.table_exists("seans_takvimi"):
                try:
                    self.cur.execute("UPDATE seans_takvimi SET record_id=? WHERE id=?", (record_id, seans_id))
                except Exception:
                    pass

            # ödeme geldiyse odeme_hareketleri + kasa
            if au > 0 and record_id:
                if self.table_exists("odeme_hareketleri"):
                    self.cur.execute(
                        """
                        INSERT INTO odeme_hareketleri
                        (record_id, tutar, tarih, odeme_sekli, aciklama, olusturma_tarihi, olusturan_kullanici_id)
                        VALUES (?,?,?,?,?,?,?)
                        """,
                        (record_id, au, tarih, "", "Seans Tahsilatı", self._now(), self.kullanici_id),
                    )
                self._add_kasa(
                    tarih,
                    "giren",
                    f"Seans Tahsilat: {danisan_clean}/{terapist}",
                    au,
                    "",
                    "Seans",
                    record_id,
                    seans_id,
                )

            # personel hakedişi oluştur
            if seans_id and hb > 0 and self.table_exists("personel_ucret_takibi"):
                try:
                    personel_ucreti = self._safe_float(hesapla_personel_ucreti(terapist, hb))
                    kural = "sabit" if terapist == "Arif Hoca" else ("yuzde100" if terapist == "Pervin Hoca" else "yuzde40")
                    ucret_orani = 100.0 if terapist == "Pervin Hoca" else (0.0 if terapist == "Arif Hoca" else 40.0)
                    self.cur.execute(
                        """
                        INSERT OR IGNORE INTO personel_ucret_takibi
                        (personel_adi, seans_id, tarih, seans_ucreti, personel_ucreti, ucret_orani, odeme_durumu, aciklama, olusturma_tarihi, olusturan_kullanici_id)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                        """,
                        (terapist, seans_id, tarih, hb, personel_ucreti, ucret_orani, "beklemede", f"Kural:{kural}", self._now(), self.kullanici_id),
                    )
                except Exception as e:
                    log_exception("pipeline.personel_ucret_insert", e)

            self._audit("seans_kayit", "seans_takvimi", seans_id, {
                "record_id": record_id,
                "danisan_adi": danisan_clean,
                "terapist": terapist,
                "hizmet_bedeli": hb,
                "alinan_ucret": au,
            })
            self.conn.commit()
            self._trigger_event("seans_created", {"seans_id": seans_id, "record_id": record_id})
            return seans_id

        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.seans_kayit", e)
            return None

    def seans_durum_guncelle(
        self,
        seans_id: int,
        seans_alindi: bool | None = None,
        ucret_alindi: bool | None = None,
        ucret_tutar: float | None = None,
        odeme_sekli: str | None = None,
    ) -> bool:
        if not self.table_exists("seans_takvimi"):
            return False
        try:
            self.conn.execute("BEGIN")
            self.cur.execute(
                "SELECT COALESCE(seans_alindi,0), COALESCE(ucret_alindi,0), COALESCE(hizmet_bedeli,0), COALESCE(record_id,0) FROM seans_takvimi WHERE id=?",
                (seans_id,),
            )
            row = self.cur.fetchone()
            if not row:
                self.conn.rollback()
                return False

            sa0, ua0, hb0, rid0 = row
            rid = int(rid0 or 0) or None

            if seans_alindi is None:
                seans_alindi = not bool(int(sa0 or 0))
            if ucret_alindi is None:
                ucret_alindi = not bool(int(ua0 or 0))

            hb = self._safe_float(hb0)
            if ucret_tutar is not None:
                hb = self._safe_float(ucret_tutar)

            self.cur.execute(
                "UPDATE seans_takvimi SET seans_alindi=?, ucret_alindi=?, hizmet_bedeli=?, odeme_sekli=? WHERE id=?",
                (1 if seans_alindi else 0, 1 if ucret_alindi else 0, hb, (odeme_sekli or ""), seans_id),
            )

            if rid and self.table_exists("records"):
                self.cur.execute("SELECT COALESCE(alinan_ucret,0) FROM records WHERE id=?", (rid,))
                au = self._safe_float((self.cur.fetchone() or [0])[0])
                kalan = max(0.0, hb - au)
                self.cur.execute(
                    "UPDATE records SET hizmet_bedeli=?, kalan_borc=?, seans_alindi=? WHERE id=?",
                    (hb, kalan, 1 if seans_alindi else 0, rid),
                )

            self._audit("kayit_sil", "seans_takvimi", seans_id, {"record_id": record_id})
            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.seans_durum_guncelle", e)
            return False

    def kayit_sil(self, seans_id: int) -> bool:
        try:
            self.conn.execute("BEGIN")

            record_id = None
            if self.table_exists("seans_takvimi"):
                self.cur.execute("SELECT COALESCE(record_id,0) FROM seans_takvimi WHERE id=?", (seans_id,))
                record_id = int((self.cur.fetchone() or [0])[0] or 0) or None

            if self.table_exists("kasa_hareketleri"):
                try:
                    self.cur.execute("DELETE FROM kasa_hareketleri WHERE seans_id=?", (seans_id,))
                    if record_id is not None:
                        self.cur.execute("DELETE FROM kasa_hareketleri WHERE record_id=?", (record_id,))
                except Exception:
                    pass

            if record_id is not None and self.table_exists("odeme_hareketleri"):
                try:
                    self.cur.execute("DELETE FROM odeme_hareketleri WHERE record_id=?", (record_id,))
                except Exception:
                    pass

            if record_id is not None and self.table_exists("records"):
                self.cur.execute("DELETE FROM records WHERE id=?", (record_id,))

            if self.table_exists("seans_takvimi"):
                self.cur.execute("DELETE FROM seans_takvimi WHERE id=?", (seans_id,))

            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.kayit_sil", e)
            return False

    # ---------- API: Ödeme / Borç ----------
    def odeme_ekle(self, record_id: int, tutar: float, tarih: str, odeme_sekli: str, aciklama: str = "") -> bool:
        tutar = self._safe_float(tutar)
        if tutar <= 0 or not self.table_exists("records"):
            return False
        try:
            self.conn.execute("BEGIN")

            self.cur.execute(
                "SELECT COALESCE(hizmet_bedeli,0), COALESCE(alinan_ucret,0), COALESCE(seans_id,0), danisan_adi, terapist FROM records WHERE id=?",
                (record_id,),
            )
            row = self.cur.fetchone()
            if not row:
                self.conn.rollback()
                return False

            hb, au, seans_id, danisan, terapist = row
            hb = self._safe_float(hb)
            au = self._safe_float(au)
            seans_id = int(seans_id or 0) or None

            yeni_au = au + tutar
            kalan = max(0.0, hb - yeni_au)
            self.cur.execute("UPDATE records SET alinan_ucret=?, kalan_borc=? WHERE id=?", (yeni_au, kalan, record_id))

            if self.table_exists("odeme_hareketleri"):
                self.cur.execute(
                    """
                    INSERT INTO odeme_hareketleri
                    (record_id, tutar, tarih, odeme_sekli, aciklama, olusturma_tarihi, olusturan_kullanici_id)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (record_id, tutar, tarih, odeme_sekli, aciklama, self._now(), self.kullanici_id),
                )

            self._add_kasa(tarih, "giren", f"Ödeme: {danisan}/{terapist}", tutar, odeme_sekli, "Tahsilat", record_id, seans_id)

            if seans_id and self.table_exists("seans_takvimi"):
                self.cur.execute("UPDATE seans_takvimi SET ucret_alindi=1 WHERE id=?", (seans_id,))

            self._audit("odeme_ekle", "records", record_id, {"tutar": tutar, "odeme_sekli": odeme_sekli, "seans_id": seans_id})
            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.odeme_ekle", e)
            return False

    def eski_borc_ekle(self, danisan_adi: str, tutar: float, tarih: str | None = None, aciklama: str = "Devir Borç") -> int | None:
        if tarih is None or str(tarih).strip() == "":
            tarih = self._today()
        else:
            tarih = str(tarih).strip()

        danisan_clean = (danisan_adi or "").strip()
        tutar = self._safe_float(tutar)
        if not danisan_upper or tutar <= 0:
            return None
        try:
            self.conn.execute("BEGIN")
            self._ensure_danisan_exists(danisan_upper)

            rid = None
            if self.table_exists("records"):
                self.cur.execute(
                    """
                    INSERT INTO records
                    (tarih, saat, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, seans_alindi, notlar, olusturma_tarihi, seans_id)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (tarih, "", danisan_upper, "", tutar, 0, tutar, 1, aciklama, self._now(), None),
                )
                rid = int(self.cur.lastrowid or 0) or None

            self.conn.commit()
            return rid
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.eski_borc_ekle", e)
            return None

    # ---------- API: Kasa ----------
    def add_manual_kasa_entry(self, tarih: str, tip: str, aciklama: str, tutar: float, odeme_sekli: str = "", gider_kategorisi: str = "") -> bool:
        try:
            self.conn.execute("BEGIN")
            self._add_kasa(tarih, tip, aciklama, self._safe_float(tutar), odeme_sekli, gider_kategorisi)
            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.add_manual_kasa_entry", e)
            return False

    # UI bazı yerlerde bunu arıyor
    def kasa_hareket_sil(self, hareket_id: int) -> bool:
        try:
            hareket_id = int(hareket_id)
        except Exception:
            return False
        if not self.table_exists("kasa_hareketleri"):
            return False
        try:
            self.conn.execute("BEGIN")
            self.cur.execute("DELETE FROM kasa_hareketleri WHERE id=?", (hareket_id,))
            if self.table_exists("sistem_gunlugu"):
                self.cur.execute(
                    "INSERT INTO sistem_gunlugu (tarih, olay, aciklama, olusturma_tarihi) VALUES (?,?,?,?)",
                    (self._today(), "KASA_SIL", f"Kasa hareketi silindi: id={hareket_id}", self._now()),
                )
            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.kasa_hareket_sil", e)
            return False

    # app_ui bazı yerlerde bu ismi çağırıyor (geriye dönük uyumluluk)
    def kasa_hareketi_sil(self, hareket_id: int) -> bool:
        return self.kasa_hareket_sil(hareket_id)

    def personel_avans_ver(self, personel_adi: str, tutar: float, tarih: str | None = None, aciklama: str = "Personel Avans") -> bool:
        if tarih is None or str(tarih).strip() == "":
            tarih = self._today()
        else:
            tarih = str(tarih).strip()

        personel_adi_u = (personel_adi or "").strip().upper()
        if not personel_adi_u:
            return False

        tutar = self._safe_float(tutar)
        if tutar <= 0:
            return False

        try:
            self.conn.execute("BEGIN")

            # kasa: çıkan
            self._add_kasa(
                tarih=tarih,
                tip="cikan",
                aciklama=f"{personel_adi_u} - AVANS - {aciklama}",
                tutar=tutar,
                odeme_sekli="",
                gider_kategorisi="Personel",
                record_id=None,
                seans_id=None,
            )

            # sistem günlüğü: tablo varsa yaz
            if self.table_exists("sistem_gunlugu"):
                self.cur.execute(
                    "INSERT INTO sistem_gunlugu (tarih, olay, aciklama, olusturma_tarihi) VALUES (?,?,?,?)",
                    (tarih, "PERSONEL_AVANS", f"{personel_adi_u} - {tutar}", self._now()),
                )

            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.personel_avans_ver", e)
            return False

    # ---------- API: Dashboard / defaults ----------
    def get_dashboard_data(self) -> dict:
        out = {
            "operasyonel": {"bugun_toplam_seans": 0, "bugun_beklenen_seans": 0, "bugun_tamamlanan_seans": 0},
            "finansal": {"bugun_kasa_giren": 0.0, "beklenen_toplam_alacak": 0.0, "toplam_borc": 0.0},
            "kritik": [],
            "borclular": [],
        }
        today = self._today()

        if self.table_exists("seans_takvimi"):
            try:
                self.cur.execute(
                    "SELECT COUNT(*) FROM seans_takvimi WHERE tarih=? AND COALESCE(durum,'')!='iptal'",
                    (today,),
                )
                out["operasyonel"]["bugun_toplam_seans"] = int((self.cur.fetchone() or [0])[0] or 0)
            except Exception:
                pass

        if self.table_exists("kasa_hareketleri"):
            try:
                self.cur.execute(
                    "SELECT COALESCE(SUM(tutar),0) FROM kasa_hareketleri WHERE tarih=? AND COALESCE(tip,'')='giren'",
                    (today,),
                )
                out["finansal"]["bugun_kasa_giren"] = float((self.cur.fetchone() or [0])[0] or 0.0)
            except Exception as e:
                log_exception("get_dashboard_data_kasa", e)

        if self.table_exists("records"):
            try:
                self.cur.execute("SELECT COALESCE(SUM(kalan_borc),0) FROM records WHERE COALESCE(kalan_borc,0)>0")
                toplam = float((self.cur.fetchone() or [0])[0] or 0.0)
                out["finansal"]["toplam_borc"] = toplam
                out["finansal"]["beklenen_toplam_alacak"] = toplam
            except Exception:
                pass


        if self.table_exists("records"):
            try:
                self.cur.execute(
                    """
                    SELECT UPPER(TRIM(danisan_adi)) AS danisan_adi,
                           COALESCE(SUM(COALESCE(kalan_borc,0)),0) AS kalan_borc,
                           COUNT(*) AS acik_kayit
                    FROM records
                    WHERE COALESCE(kalan_borc,0) > 0
                    GROUP BY UPPER(TRIM(danisan_adi))
                    ORDER BY kalan_borc DESC
                    LIMIT 10
                    """
                )
                out["borclular"] = [
                    {
                        "danisan_adi": r[0] or "",
                        "kalan_borc": self._safe_float(r[1]),
                        "acik_kayit": int(r[2] or 0),
                    }
                    for r in (self.cur.fetchall() or [])
                ]
            except Exception as e:
                log_exception("get_dashboard_data_borclular", e)

        return out

    def get_smart_defaults(self, danisan_adi: str = "", terapist_adi: str = "", tarih: str = "", saat: str = "") -> dict:
        out = {
            "price": 0.0,
            "hizmet_bedeli": None,
            "odeme_sekli": "",
            "oda": "",
        }
        danisan = self._normalize_name(danisan_adi)
        terapist = " ".join((terapist_adi or "").strip().split())
        if not danisan or not terapist:
            return out
        try:
            ogrenci_id = self._get_cocuk_id(danisan)
            if ogrenci_id and self.table_exists("pricing_policy"):
                self.cur.execute(
                    """
                    SELECT COALESCE(price,0)
                    FROM pricing_policy
                    WHERE student_id=? AND TRIM(COALESCE(teacher_name,''))=?
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT 1
                    """,
                    (ogrenci_id, terapist),
                )
                row = self.cur.fetchone()
                if row and self._safe_float(row[0]) > 0:
                    out["price"] = self._safe_float(row[0])
                    out["hizmet_bedeli"] = out["price"]
                    return out

            if ogrenci_id and self.table_exists("ogrenci_personel_fiyatlandirma"):
                self.cur.execute(
                    """
                    SELECT COALESCE(seans_ucreti,0)
                    FROM ogrenci_personel_fiyatlandirma
                    WHERE ogrenci_id=? AND TRIM(COALESCE(personel_adi,''))=? AND COALESCE(aktif,1)=1
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (ogrenci_id, terapist),
                )
                row = self.cur.fetchone()
                if row and self._safe_float(row[0]) > 0:
                    out["price"] = self._safe_float(row[0])
                    out["hizmet_bedeli"] = out["price"]
                    return out

            if self.table_exists("records"):
                self.cur.execute(
                    """
                    SELECT AVG(COALESCE(hizmet_bedeli,0))
                    FROM records
                    WHERE UPPER(TRIM(danisan_adi))=? AND TRIM(COALESCE(terapist,''))=?
                      AND COALESCE(hizmet_bedeli,0)>0
                    """,
                    (danisan, terapist),
                )
                avg_row = self.cur.fetchone()
                avg_price = self._safe_float((avg_row or [0])[0])
                if avg_price > 0:
                    out["price"] = avg_price
                    out["hizmet_bedeli"] = avg_price
            return out
        except Exception as e:
            log_exception("pipeline.get_smart_defaults", e)
            return out

    def get_price_for_danisan_terapist(self, danisan_adi: str, terapist_adi: str) -> float:
        """UI compatibility: danışan+terapist için otomatik hizmet bedelini döndürür."""
        try:
            defaults = self.get_smart_defaults(danisan_adi=danisan_adi, terapist_adi=terapist_adi, tarih=self._today(), saat="09:00")
            return self._safe_float(defaults.get("price", 0))
        except Exception:
            return 0.0

    def validate_sync(self) -> dict:
        # UI burada result["stats"]["seans_takvimi_count"] gibi anahtarlar bekliyor (KeyError fix)
        tables = {
            "seans_takvimi": self.table_exists("seans_takvimi"),
            "records": self.table_exists("records"),
            "kasa_hareketleri": self.table_exists("kasa_hareketleri"),
            "odeme_hareketleri": self.table_exists("odeme_hareketleri"),
        }

        stats: dict[str, Any] = {"missing_tables": [k for k, v in tables.items() if not v]}

        def _count(tbl: str) -> int:
            if not self.table_exists(tbl):
                return 0
            try:
                self.cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                return int((self.cur.fetchone() or [0])[0] or 0)
            except Exception:
                return 0

        stats["seans_takvimi_count"] = _count("seans_takvimi")
        stats["records_count"] = _count("records")
        stats["kasa_hareketleri_count"] = _count("kasa_hareketleri")
        stats["odeme_hareketleri_count"] = _count("odeme_hareketleri")

        return {"tables": tables, "stats": stats}

    # ---------- API: Personel ----------
    def personel_harici_islem(self, personel: str, tutar: float, islem_turu: str = "Gider", aciklama: str = "") -> bool:
        # app_ui bunu çağırıyor; kasa + log
        tutar = self._safe_float(tutar)
        personel_u = (personel or "").strip().upper()
        if tutar <= 0 or not personel_u:
            return False

        islem = str(islem_turu or "").strip().lower()
        tip = "cikan" if islem in {"gider", "avans", "maaş ödemesi", "maas odemesi", "prim", "yol/yemek", "yol", "yemek"} else "giren"
        try:
            self.conn.execute("BEGIN")
            self._add_kasa(
                tarih=self._today(),
                tip=tip,
                aciklama=f"{personel_u} - {aciklama or 'Personel İşlem'}",
                tutar=tutar,
                odeme_sekli="",
                gider_kategorisi="Personel",
                record_id=None,
                seans_id=None,
            )
            if self.table_exists("sistem_gunlugu"):
                self.cur.execute(
                    "INSERT INTO sistem_gunlugu (tarih, olay, aciklama, olusturma_tarihi) VALUES (?,?,?,?)",
                    (self._today(), "PERSONEL_ISLEM", f"{personel_u} {tip} {tutar} | {aciklama}", self._now()),
                )
            self._audit("personel_islem", "kasa_hareketleri", None, {"personel": personel_u, "tip": tip, "tutar": tutar, "islem_turu": islem_turu})
            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.personel_harici_islem", e)
            return False

    def get_personel_cuzdan(self, personel_adi: str) -> dict:
        """Personel için bekleyen/ödenen hakediş özetini döndürür."""
        personel = (personel_adi or "").strip()
        out = {
            "beklemede_toplam": 0.0,
            "odendi_toplam": 0.0,
            "toplam_hak_edis": 0.0,
        }
        if not personel or not self.table_exists("personel_ucret_takibi"):
            return out
        try:
            self.cur.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN COALESCE(odeme_durumu,'')='beklemede' THEN COALESCE(personel_ucreti,0) ELSE 0 END),0) AS beklemede,
                    COALESCE(SUM(CASE WHEN COALESCE(odeme_durumu,'')='odendi' THEN COALESCE(personel_ucreti,0) ELSE 0 END),0) AS odendi,
                    COALESCE(SUM(COALESCE(personel_ucreti,0)),0) AS toplam
                FROM personel_ucret_takibi
                WHERE TRIM(personel_adi)=?
                """,
                (personel,),
            )
            row = self.cur.fetchone() or (0, 0, 0)
            out["beklemede_toplam"] = self._safe_float(row[0])
            out["odendi_toplam"] = self._safe_float(row[1])
            out["toplam_hak_edis"] = self._safe_float(row[2])
            return out
        except Exception as e:
            log_exception("pipeline.get_personel_cuzdan", e)
            return out

    def personel_ucret_odeme_kasa_entegrasyonu(self, personel_adi: str, tutar: float, ucret_takibi_id: int | None = None) -> bool:
        """Personel ücret ödemesini kayda geçirir: put.odendi + kasa(cikan)."""
        try:
            self.conn.execute("BEGIN")

            personel = (personel_adi or "").strip().upper()
            tutar_val = self._safe_float(tutar)

            if ucret_takibi_id and self.table_exists("personel_ucret_takibi"):
                self.cur.execute(
                    "SELECT personel_adi, COALESCE(personel_ucreti,0), COALESCE(odeme_durumu,'beklemede') FROM personel_ucret_takibi WHERE id=?",
                    (ucret_takibi_id,),
                )
                row = self.cur.fetchone()
                if not row:
                    self.conn.rollback()
                    return False
                personel = (row[0] or personel).strip().upper()
                tutar_val = self._safe_float(row[1] if row[1] is not None else tutar_val)
                self.cur.execute(
                    "UPDATE personel_ucret_takibi SET odeme_durumu='odendi', odeme_tarihi=? WHERE id=?",
                    (self._today(), ucret_takibi_id),
                )

            if not personel or tutar_val <= 0:
                self.conn.rollback()
                return False

            self._add_kasa(
                tarih=self._today(),
                tip="cikan",
                aciklama=f"Personel Ücret Ödemesi: {personel}",
                tutar=tutar_val,
                odeme_sekli="",
                gider_kategorisi="Personel",
                record_id=None,
                seans_id=None,
            )

            if self.table_exists("sistem_gunlugu"):
                self.cur.execute(
                    "INSERT INTO sistem_gunlugu (tarih, olay, aciklama, olusturma_tarihi) VALUES (?,?,?,?)",
                    (self._today(), "PERSONEL_UCRET_ODEME", f"personel={personel} tutar={tutar_val} ucret_takibi_id={ucret_takibi_id}", self._now()),
                )

            self._audit("personel_ucret_odeme", "personel_ucret_takibi", ucret_takibi_id, {"personel": personel, "tutar": tutar_val})
            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.personel_ucret_odeme_kasa_entegrasyonu", e)
            return False


    def toplu_odeme_al(self, danisan_adi: str, tutar: float, aciklama: str = "Toplu Ödeme / Peşinat") -> bool:
        """Danışanın açık borçlarına toplu tahsilat uygular ve kasa/ödeme hareketi üretir."""
        danisan = (danisan_adi or "").strip().upper()
        tutar = self._safe_float(tutar)
        if not danisan or tutar <= 0 or not self.table_exists("records"):
            return False

        try:
            self.conn.execute("BEGIN")
            kalan_odeme = tutar
            today = self._today()

            self.cur.execute(
                """
                SELECT id, COALESCE(kalan_borc,0), COALESCE(alinan_ucret,0), COALESCE(hizmet_bedeli,0), COALESCE(seans_id,0), terapist
                FROM records
                WHERE UPPER(TRIM(danisan_adi))=? AND COALESCE(kalan_borc,0)>0
                ORDER BY tarih ASC, id ASC
                """,
                (danisan,),
            )
            borclar = self.cur.fetchall()
            if not borclar:
                self.conn.rollback()
                return False

            for rid, kalan_borc, alinan_ucret, hizmet_bedeli, seans_id_raw, terapist in borclar:
                if kalan_odeme <= 0:
                    break
                kalan_borc = self._safe_float(kalan_borc)
                if kalan_borc <= 0:
                    continue
                odenecek = min(kalan_odeme, kalan_borc)
                yeni_alinan = self._safe_float(alinan_ucret) + odenecek
                yeni_kalan = max(0.0, self._safe_float(hizmet_bedeli) - yeni_alinan)

                self.cur.execute(
                    "UPDATE records SET alinan_ucret=?, kalan_borc=? WHERE id=?",
                    (yeni_alinan, yeni_kalan, rid),
                )

                if self.table_exists("odeme_hareketleri"):
                    self.cur.execute(
                        """
                        INSERT INTO odeme_hareketleri
                        (record_id, tutar, tarih, odeme_sekli, aciklama, olusturma_tarihi, olusturan_kullanici_id)
                        VALUES (?,?,?,?,?,?,?)
                        """,
                        (rid, odenecek, today, "", aciklama, self._now(), self.kullanici_id),
                    )

                seans_id = int(seans_id_raw or 0) or None
                self._add_kasa(
                    tarih=today,
                    tip="giren",
                    aciklama=f"Toplu Ödeme: {danisan}/{(terapist or '').strip()}",
                    tutar=odenecek,
                    odeme_sekli="",
                    gider_kategorisi="Tahsilat",
                    record_id=int(rid),
                    seans_id=seans_id,
                )

                if seans_id and self.table_exists("seans_takvimi") and yeni_kalan <= 0:
                    self.cur.execute("UPDATE seans_takvimi SET ucret_alindi=1 WHERE id=?", (seans_id,))

                kalan_odeme -= odenecek

            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.toplu_odeme_al", e)
            return False

    # ---------- API: Danışan ----------
    def danisan_durum_guncelle(self, danisan_id: int, aktif: bool) -> bool:
        if not self.table_exists("danisanlar"):
            return False
        try:
            self.cur.execute("UPDATE danisanlar SET aktif=? WHERE id=?", (1 if aktif else 0, danisan_id))
            self.conn.commit()
            return True
        except Exception as e:
            log_exception("pipeline.danisan_durum_guncelle", e)
            return False

    def oda_durum_guncelle(self, oda_id: int, aktif: bool) -> bool:
        if not self.table_exists("odalar"):
            return False
        try:
            self.cur.execute("UPDATE odalar SET aktif=? WHERE id=?", (1 if aktif else 0, oda_id))
            if self.table_exists("sistem_gunlugu"):
                self.cur.execute(
                    "INSERT INTO sistem_gunlugu (tarih, olay, aciklama, olusturma_tarihi) VALUES (?,?,?,?)",
                    (self._today(), "ODA_DURUM", f"oda_id={oda_id} aktif={1 if aktif else 0}", self._now()),
                )
            self.conn.commit()
            return True
        except Exception as e:
            log_exception("pipeline.oda_durum_guncelle", e)
            return False

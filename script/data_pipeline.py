from __future__ import annotations

import datetime
import sqlite3
from typing import Any, Dict, List

from core.logging_utils import log_exception


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

    def _normalize_danisan_name(self, name: str) -> str:
        return " ".join((name or "").strip().upper().split())

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
        danisan_upper = self._normalize_danisan_name(danisan_upper)
        try:
            self.cur.execute(
                "SELECT id FROM danisanlar WHERE UPPER(TRIM(ad_soyad))=? LIMIT 1",
                (danisan_upper,),
            )
            row = self.cur.fetchone()
            if row and row[0]:
                return int(row[0])

            self.cur.execute(
                """
                INSERT INTO danisanlar
                (ad_soyad, telefon, email, veli_adi, veli_telefon, dogum_tarihi, adres, notlar, olusturma_tarihi, aktif, balance)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (danisan_upper, "", "", "", "", "", "", "", self._now(), 1, 0),
            )
            return int(self.cur.lastrowid or 0) or None
        except Exception as e:
            log_exception("pipeline.ensure_danisan", e)
            return None

    def _get_cocuk_id(self, danisan_upper: str) -> int | None:
        if not self.table_exists("danisanlar"):
            return None
        danisan_upper = self._normalize_danisan_name(danisan_upper)
        try:
            self.cur.execute(
                "SELECT id FROM danisanlar WHERE UPPER(TRIM(ad_soyad))=? LIMIT 1",
                (danisan_upper,),
            )
            row = self.cur.fetchone()
            return int(row[0]) if row and row[0] is not None else None
        except Exception:
            return None

    def _recalculate_danisan_balance(self, danisan_adi: str) -> None:
        if not self.table_exists("danisanlar") or not self.table_exists("records"):
            return
        danisan_adi = self._normalize_danisan_name(danisan_adi)
        try:
            self.cur.execute(
                """
                UPDATE danisanlar
                SET balance = (
                    SELECT COALESCE(SUM(kalan_borc), 0)
                    FROM records
                    WHERE danisan_adi = ?
                )
                WHERE ad_soyad = ?
                """,
                (danisan_adi, danisan_adi),
            )
        except Exception:
            pass

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
        danisan_upper = self._normalize_danisan_name(danisan_adi)
        terapist = (terapist or "").strip()
        tarih = (tarih or "").strip()
        saat = (saat or "").strip()
        oda = (oda or "").strip()
        notlar = (notlar or "").strip()

        hb = self._safe_float(hizmet_bedeli)
        au = self._safe_float(alinan_ucret)

        if not tarih or not danisan_upper or not terapist:
            return None

        try:
            self.conn.execute("BEGIN")

            cocuk_id = self._get_cocuk_id(danisan_upper)
            if ensure_danisan and cocuk_id is None:
                cocuk_id = self._ensure_danisan_exists(danisan_upper)

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
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        tarih,
                        saat,
                        danisan_upper,
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
                    (tarih, saat, danisan_upper, terapist, hb, au, kalan, 0, notlar, self._now(), seans_id),
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
                    f"Seans Tahsilat: {danisan_upper}/{terapist}",
                    au,
                    "",
                    "Seans",
                    record_id,
                    seans_id,
                )

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

        danisan_upper = self._normalize_danisan_name(danisan_adi)
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
        return self.kasa_hareketi_sil(hareket_id)

    def kasa_hareketi_sil(self, kasa_id: int) -> bool:
        try:
            kasa_id = int(kasa_id)
        except Exception:
            return False
        if not self.table_exists("kasa_hareketleri"):
            return False
        try:
            self.conn.execute("BEGIN")
            self.cur.execute(
                """
                SELECT tarih, tip, aciklama, tutar, odeme_sekli, record_id, seans_id
                FROM kasa_hareketleri
                WHERE id=?
                """,
                (kasa_id,),
            )
            row = self.cur.fetchone()
            if not row:
                self.conn.rollback()
                return False

            tarih, tip, aciklama, tutar, odeme_sekli, record_id, seans_id = row

            self.cur.execute("DELETE FROM kasa_hareketleri WHERE id=?", (kasa_id,))

            if tip == "giren" and record_id and self.table_exists("records"):
                try:
                    self.cur.execute(
                        "SELECT hizmet_bedeli, alinan_ucret, kalan_borc FROM records WHERE id=?",
                        (record_id,),
                    )
                    rec_row = self.cur.fetchone()
                    if rec_row:
                        bedel, alinan_eski, _kalan_eski = rec_row
                        alinan_yeni = max(0.0, float(alinan_eski or 0) - float(tutar or 0))
                        kalan_yeni = max(0.0, float(bedel or 0) - alinan_yeni)
                        self.cur.execute(
                            "UPDATE records SET alinan_ucret=?, kalan_borc=? WHERE id=?",
                            (alinan_yeni, kalan_yeni, record_id),
                        )
                        if self.table_exists("danisanlar"):
                            self.cur.execute("SELECT danisan_adi FROM records WHERE id=?", (record_id,))
                            danisan_row = self.cur.fetchone()
                            if danisan_row:
                                danisan = danisan_row[0]
                                self._recalculate_danisan_balance(danisan)
                except Exception as e:
                    log_exception("pipeline.kasa_hareketi_sil_update", e)

            if self.table_exists("sistem_gunlugu"):
                self.cur.execute(
                    "INSERT INTO sistem_gunlugu (tarih, olay, aciklama, olusturma_tarihi) VALUES (?,?,?,?)",
                    (self._today(), "KASA_SIL", f"Kasa hareketi silindi: id={kasa_id}", self._now()),
                )

            self.conn.commit()
            self._log(
                f"KASA_SIL | id={kasa_id} | tip={tip} | tutar={tutar} | rec={record_id} | seans={seans_id} | {aciklama} | {odeme_sekli}"
            )
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.kasa_hareketi_sil", e)
            return False

    def personel_ucret_odeme_kasa_entegrasyonu(
        self,
        personel_adi: str,
        tutar: float,
        ucret_takibi_id: int | None = None,
        odeme_sekli: str = "Nakit",
    ) -> bool:
        if not self.table_exists("kasa_hareketleri"):
            return False
        try:
            bugun = self._today()
            olusturma_tarihi = self._now()
            self.cur.execute(
                """
                INSERT INTO kasa_hareketleri
                (tarih, tip, aciklama, tutar, odeme_sekli, gider_kategorisi, olusturan_kullanici_id, olusturma_tarihi)
                VALUES (?, 'çıkan', ?, ?, ?, 'Maaş', ?, ?)
                """,
                (
                    bugun,
                    f"{personel_adi} - Personel Ücret Ödemesi",
                    float(tutar or 0),
                    odeme_sekli,
                    self.kullanici_id,
                    olusturma_tarihi,
                ),
            )
            self.conn.commit()
            self._log(
                f"PERSONEL_UCRET_KASA | personel={personel_adi} | tutar={tutar} | ucret_takibi_id={ucret_takibi_id}"
            )
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.personel_ucret_odeme_kasa_entegrasyonu", e)
            return False

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

            try:
                self.cur.execute(
                    """
                    SELECT danisan_adi, COALESCE(SUM(kalan_borc), 0) AS toplam
                    FROM records
                    WHERE COALESCE(kalan_borc, 0) > 0
                    GROUP BY danisan_adi
                    ORDER BY toplam DESC
                    LIMIT 10
                    """
                )
                rows = self.cur.fetchall() or []
                out["borclular"] = [
                    {"danisan_adi": r[0], "kalan_borc": float(r[1] or 0)} for r in rows
                ]
            except Exception as e:
                log_exception("get_dashboard_data_borclular", e)

        return out

    def get_personel_cuzdan(self, personel_adi: str) -> dict:
        result = {
            "personel_adi": personel_adi,
            "beklemede_toplam": 0.0,
            "odendi_toplam": 0.0,
            "beklemede_sayisi": 0,
            "odendi_sayisi": 0,
            "toplam_hak_edis": 0.0,
        }
        if not self.table_exists("personel_ucret_takibi"):
            return result
        try:
            self.cur.execute(
                """
                SELECT COALESCE(SUM(personel_ucreti), 0), COUNT(*)
                FROM personel_ucret_takibi
                WHERE personel_adi = ? AND odeme_durumu = 'beklemede'
                """,
                (personel_adi,),
            )
            row = self.cur.fetchone()
            if row:
                result["beklemede_toplam"] = float(row[0] or 0)
                result["beklemede_sayisi"] = int(row[1] or 0)

            self.cur.execute(
                """
                SELECT COALESCE(SUM(personel_ucreti), 0), COUNT(*)
                FROM personel_ucret_takibi
                WHERE personel_adi = ? AND odeme_durumu = 'odendi'
                """,
                (personel_adi,),
            )
            row = self.cur.fetchone()
            if row:
                result["odendi_toplam"] = float(row[0] or 0)
                result["odendi_sayisi"] = int(row[1] or 0)

            result["toplam_hak_edis"] = result["beklemede_toplam"] + result["odendi_toplam"]
            return result
        except Exception as e:
            log_exception("pipeline.get_personel_cuzdan", e)
            return result

    def get_smart_defaults(self, danisan_adi: str = "", terapist_adi: str = "", tarih: str = "", saat: str = "") -> dict:
        # UI burada "price" bekliyor (KeyError fix)
        return {
            "price": 0.0,
            "hizmet_bedeli": None,
            "odeme_sekli": "",
            "oda": "",
        }

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

        tip = "cikan" if str(islem_turu).lower().startswith("g") else "giren"
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
            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.personel_harici_islem", e)
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
            self.conn.commit()
            self._log(f"ODA_DURUM | oda_id={oda_id} | aktif={aktif}")
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.oda_durum_guncelle", e)
            return False

    def toplu_odeme_al(
        self,
        danisan_adi: str,
        tutar: float,
        odeme_sekli: str = "Nakit",
        aciklama: str = "Toplu Ödeme",
    ) -> bool:
        if not self.table_exists("records") or not self.table_exists("kasa_hareketleri"):
            return False
        try:
            tarih_db = self._today()
            ts = self._now()
            tutar = self._safe_float(tutar)
            danisan_adi = self._normalize_danisan_name(danisan_adi)
            if tutar <= 0:
                return False

            self.cur.execute(
                """
                INSERT INTO records
                (tarih, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, notlar, olusturma_tarihi)
                VALUES (?, ?, 'KASA', 0, ?, ?, ?, ?)
                """,
                (tarih_db, danisan_adi, tutar, -tutar, aciklama, ts),
            )
            record_id = self.cur.lastrowid

            self.cur.execute(
                """
                INSERT INTO kasa_hareketleri
                (tarih, tip, aciklama, tutar, odeme_sekli, record_id, olusturan_kullanici_id, olusturma_tarihi)
                VALUES (?, 'giren', ?, ?, ?, ?, ?, ?)
                """,
                (
                    tarih_db,
                    f"{danisan_adi} - {aciklama}",
                    tutar,
                    odeme_sekli,
                    record_id,
                    self.kullanici_id,
                    ts,
                ),
            )

            self._recalculate_danisan_balance(danisan_adi)
            self.conn.commit()
            return True
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            log_exception("pipeline.toplu_odeme_al", e)
            return False

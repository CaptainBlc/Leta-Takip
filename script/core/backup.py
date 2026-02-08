from __future__ import annotations

import datetime
import os
import shutil
import sqlite3
from pathlib import Path

from .paths import data_dir, db_path


def backups_dir() -> Path:
    return data_dir() / "Yedekler"


def _backup_mirror_dirs() -> list[Path]:
    """Ek yedek klasörleri (lokal bozulmaya karşı ikinci lokasyon)."""
    out: list[Path] = []
    env = os.environ.get("LETA_BACKUP_MIRROR", "").strip()
    if env:
        try:
            out.append(Path(env).expanduser())
        except Exception:
            pass

    try:
        # platform bağımsız güvenli varsayılan: home altı ayrı klasör
        out.append(Path.home() / "LetaYonetim_BackupMirror")
    except Exception:
        pass
    return out


def _db_integrity_ok(path: Path) -> bool:
    try:
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        row = cur.fetchone()
        conn.close()
        return bool(row and str(row[0]).lower() == "ok")
    except Exception:
        return False


def _copy_to_mirrors(src: Path) -> None:
    for mdir in _backup_mirror_dirs():
        try:
            mdir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(mdir / src.name))
        except Exception:
            pass


def backup_now(prefix: str = "backup") -> str | None:
    try:
        bdir = backups_dir()
        bdir.mkdir(parents=True, exist_ok=True)

        src = db_path()
        if not src.exists():
            return None

        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        dst = bdir / f"{prefix}_{ts}.db"
        shutil.copy2(str(src), str(dst))

        # Mirror'a da yaz (lokal dizin bozulmasına karşı)
        _copy_to_mirrors(dst)

        # Rotasyon
        backups = sorted(bdir.glob(f"{prefix}_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[30:]:
            try:
                old.unlink()
            except Exception:
                pass

        return str(dst)
    except Exception:
        return None


def silent_backup() -> None:
    """Açılışta sessiz yedek: integrity OK ise yedekle + mirror kopya."""
    try:
        src = db_path()
        if not src.exists():
            return

        # Kaynak DB bozuk görünüyorsa yine de dokunmadan çık (durumu kötüleştirmeyelim)
        if not _db_integrity_ok(src):
            return

        bdir = backups_dir()
        bdir.mkdir(parents=True, exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        dst = bdir / f"backup_{ts}.db"
        shutil.copy2(str(src), str(dst))
        _copy_to_mirrors(dst)

        backups = sorted(bdir.glob("backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[30:]:
            try:
                old.unlink()
            except Exception:
                pass
    except Exception:
        pass

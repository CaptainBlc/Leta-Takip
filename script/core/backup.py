from __future__ import annotations
import datetime
import shutil
from .paths import data_dir, db_path


def backups_dir():
    return data_dir() / "Yedekler"


def silent_backup() -> None:
    try:
        bdir = backups_dir()
        bdir.mkdir(parents=True, exist_ok=True)

        src = db_path()
        if not src.exists():
            return

        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        dst = bdir / f"backup_{ts}.db"
        shutil.copy2(str(src), str(dst))

        backups = sorted(bdir.glob("backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[15:]:
            try:
                old.unlink()
            except Exception:
                pass
    except Exception:
        pass

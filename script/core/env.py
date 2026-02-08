from __future__ import annotations
import datetime

APP_TITLE = "Leta Takip"
APP_VERSION = "v2.0"
APP_BUILD = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# Personel ücret kuralları (örnek)
PERSONEL_UCRET_KURALLARI = {
    "_default": {"tip": "yuzde", "oran": 40.0},
}

DEFAULT_THERAPISTS: list[str] = []

# Opsiyonel seed verileri (boş bırakılabilir)
DEFAULT_THERAPIST_ROLES: dict[str, str] = {}
DEFAULT_USERS: list[tuple[str, str, str, str, str | None]] = []

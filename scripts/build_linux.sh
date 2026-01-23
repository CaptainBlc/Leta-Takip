#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.0}"
APP_NAME="Leta_Yonetim_Paneli_v1_0"

echo "== Leta Linux build (v${VERSION}) =="

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt -r requirements-dev.txt

rm -rf dist build

# Linux'ta tek dosya (onefile) dağıtım kolaylığı sağlar.
# Kılavuz dosyasını bundle içine ekliyoruz.
python3 -m PyInstaller \
  --clean --noconfirm \
  --onefile --windowed \
  --name "${APP_NAME}" \
  --add-data "KULLANIM_KILAVUZU.txt:." \
  "leta_app.py"

echo "OK -> dist/${APP_NAME}"


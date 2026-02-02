#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.3}"
APP_NAME="Leta_Pipeline_v${VERSION//./_}"

echo "== Leta macOS build (v${VERSION}) =="

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt -r requirements-dev.txt

rm -rf dist build

# macOS'ta --windowed çıktısı .app bundle üretir (onedir).
# Kılavuz dosyasını bundle içine ekliyoruz.
python3 -m PyInstaller \
  --clean --noconfirm \
  --windowed \
  --name "${APP_NAME}" \
  --add-data "KULLANIM_KILAVUZU.txt:." \
  "leta_app.py"

echo "OK -> dist/${APP_NAME}.app"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.3}"
APP_NAME="Leta_Pipeline_v${VERSION//./_}_linux"

echo "== Leta Linux build (v${VERSION}) =="

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt -r requirements-dev.txt

rm -rf dist build

# Güncel giriş noktası: script/main.py
python3 -m PyInstaller \
  --clean --noconfirm \
  --onefile --windowed \
  --name "${APP_NAME}" \
  --add-data "script/assets/KULLANIM_KILAVUZU.txt:assets" \
  "script/main.py"

echo "OK -> dist/${APP_NAME}"

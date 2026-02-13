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

# Güncel akış: spec dosyası script/main.py giriş noktasını kullanır.
python3 -m PyInstaller --noconfirm --clean Leta_Pipeline_Mac.spec

echo "OK -> dist/${APP_NAME}.app"

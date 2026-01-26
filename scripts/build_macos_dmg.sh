#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.0}"
APP_NAME="Leta_Yonetim_Paneli_v1_0"
DMG_NAME="${APP_NAME}_${VERSION}.dmg"

echo "== Leta macOS DMG (v${VERSION}) =="

bash "${SCRIPT_DIR}/build_macos.sh" "${VERSION}"

STAGE_DIR="dist_dmg_stage"
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}"

cp -R "dist/${APP_NAME}.app" "${STAGE_DIR}/"

# Basit DMG (hdiutil macOS ile birlikte gelir)
rm -f "dist/${DMG_NAME}"
hdiutil create -volname "Leta Yonetim" -srcfolder "${STAGE_DIR}" -ov -format UDZO "dist/${DMG_NAME}"

echo "OK -> dist/${DMG_NAME}"


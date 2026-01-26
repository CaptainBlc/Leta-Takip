#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.0}"
APP_NAME="Leta_Yonetim_Paneli_v1_0"
IDENTIFIER="com.leta.yonetim.paneli"

echo "== Leta macOS PKG (v${VERSION}) =="

bash "${SCRIPT_DIR}/build_macos.sh" "${VERSION}"

# Not: Bu script macOS üzerinde çalıştırılmalıdır (pkgbuild/productbuild macOS aracıdır).
if ! command -v pkgbuild >/dev/null 2>&1; then
  echo "pkgbuild bulunamadı. Bu script macOS'ta çalışır." >&2
  exit 1
fi

STAGE="dist_pkg_stage_macos"
rm -rf "${STAGE}"
mkdir -p "${STAGE}/Applications"
cp -R "dist/${APP_NAME}.app" "${STAGE}/Applications/"

PKG_COMPONENT="dist/${APP_NAME}_${VERSION}_component.pkg"
PKG_FINAL="dist/${APP_NAME}_${VERSION}.pkg"

rm -f "${PKG_COMPONENT}" "${PKG_FINAL}"

pkgbuild \
  --root "${STAGE}" \
  --identifier "${IDENTIFIER}" \
  --version "${VERSION}" \
  "${PKG_COMPONENT}"

productbuild \
  --package "${PKG_COMPONENT}" \
  "${PKG_FINAL}"

echo "OK -> ${PKG_FINAL}"



#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.0}"
APP_NAME="leta-yonetim-paneli"
BIN_NAME="Leta_Yonetim_Paneli_v1_0"

echo "== Leta Linux packages (.deb/.rpm) v${VERSION} =="

# 1) Önce Linux binary build al (PyInstaller onefile)
bash "${SCRIPT_DIR}/build_linux.sh" "${VERSION}"

if [ ! -f "dist/${BIN_NAME}" ]; then
  echo "Beklenen binary bulunamadı: dist/${BIN_NAME}" >&2
  exit 1
fi

# 2) Staging: paket içine girecek dosyaları hazırlıyoruz
STAGE="dist_pkg_stage"
rm -rf "${STAGE}"
mkdir -p "${STAGE}/opt/leta" "${STAGE}/usr/bin" "${STAGE}/usr/share/applications" "${STAGE}/usr/share/icons/hicolor/256x256/apps"

cp "dist/${BIN_NAME}" "${STAGE}/opt/leta/leta"
chmod +x "${STAGE}/opt/leta/leta"

cp "packaging/linux/packaging/leta.desktop" "${STAGE}/usr/share/applications/leta.desktop"
cp "packaging/linux/packaging/leta-yonetim-paneli.sh" "${STAGE}/usr/bin/${APP_NAME}"
chmod +x "${STAGE}/usr/bin/${APP_NAME}"

# İkon opsiyonel: logo.png varsa kullan
if [ -f "logo.png" ]; then
  cp "logo.png" "${STAGE}/usr/share/icons/hicolor/256x256/apps/leta.png"
fi

# Kılavuz opsiyonel: paket içine koy (uygulama ayrıca data_dir'e kopyalıyor)
if [ -f "KULLANIM_KILAVUZU.txt" ]; then
  mkdir -p "${STAGE}/opt/leta"
  cp "KULLANIM_KILAVUZU.txt" "${STAGE}/opt/leta/KULLANIM_KILAVUZU.txt"
fi

# 3) fpm ile .deb ve .rpm üret
# Gereksinimler:
#  - Ruby + fpm (gem)
#  - rpm paketi (rpmbuild) -> .rpm için gerekebilir
if ! command -v fpm >/dev/null 2>&1; then
  cat >&2 <<'EOF'
fpm bulunamadı.
Kurulum örneği (Ubuntu/Debian):
  sudo apt-get update
  sudo apt-get install -y ruby ruby-dev build-essential rpm
  sudo gem install --no-document fpm
EOF
  exit 1
fi

mkdir -p dist

fpm -s dir -t deb \
  -n "${APP_NAME}" \
  -v "${VERSION}" \
  --description "Leta Yönetim Paneli" \
  --license "Proprietary" \
  --maintainer "Leta" \
  -C "${STAGE}" \
  .

fpm -s dir -t rpm \
  -n "${APP_NAME}" \
  -v "${VERSION}" \
  --description "Leta Yönetim Paneli" \
  --license "Proprietary" \
  --maintainer "Leta" \
  -C "${STAGE}" \
  .

echo "OK -> dist/ (deb/rpm çıktılarını burada göreceksin)"



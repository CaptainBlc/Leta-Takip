#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.3}"
APP_NAME="Leta_Pipeline_v${VERSION//./_}_linux"
ARCH="${ARCH:-x86_64}"

echo "== Leta Linux AppImage (v${VERSION}) =="

bash "${SCRIPT_DIR}/build_linux.sh" "${VERSION}"

APPDIR="AppDir"
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin" "${APPDIR}/usr/share/applications" "${APPDIR}/usr/share/icons/hicolor/256x256/apps"

cp "dist/${APP_NAME}" "${APPDIR}/usr/bin/${APP_NAME}"
chmod +x "${APPDIR}/usr/bin/${APP_NAME}"

cat > "${APPDIR}/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/Leta_Yonetim_Paneli_v1_0" "$@"
EOF
sed -i "s#Leta_Yonetim_Paneli_v1_0#${APP_NAME}#g" "${APPDIR}/AppRun"
chmod +x "${APPDIR}/AppRun"

cat > "${APPDIR}/usr/share/applications/leta.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Leta Takip
Exec=${APP_NAME}
Icon=leta
Categories=Office;
Terminal=false
EOF

# İkon opsiyonel: logo.png varsa kullan
if [ -f "logo.png" ]; then
  cp "logo.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/leta.png"
fi

# appimagetool indir (Linux)
TOOL="./appimagetool.AppImage"
if [ ! -f "${TOOL}" ]; then
  if command -v curl >/dev/null 2>&1; then
    curl -L -o "${TOOL}" "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "${TOOL}" "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
  else
    echo "curl/wget bulunamadı. appimagetool indirmek için curl veya wget kurun." >&2
    exit 1
  fi
  chmod +x "${TOOL}"
fi

OUT="dist/${APP_NAME}_${VERSION}_${ARCH}.AppImage"
rm -f "${OUT}"
"${TOOL}" "${APPDIR}" "${OUT}"

echo "OK -> ${OUT}"

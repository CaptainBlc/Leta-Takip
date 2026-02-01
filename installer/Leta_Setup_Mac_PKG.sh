#!/usr/bin/env bash
# Leta Takip - macOS PKG Installer Builder
# Kullanım: ./Leta_Setup_Mac_PKG.sh [version]
# Örnek: ./Leta_Setup_Mac_PKG.sh 1.3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.3}"
APP_NAME="Leta_Pipeline_v1_3"
IDENTIFIER="com.leta.takip"
DISPLAY_NAME="Leta Takip"

echo "=========================================="
echo "  Leta Takip macOS PKG Builder v${VERSION}"
echo "=========================================="
echo ""

# macOS kontrolü
if [[ "$(uname)" != "Darwin" ]]; then
  echo "❌ HATA: Bu script sadece macOS'ta çalışır!"
  exit 1
fi

# Gerekli araçlar kontrolü
if ! command -v pkgbuild >/dev/null 2>&1; then
  echo "❌ HATA: pkgbuild bulunamadı. Xcode Command Line Tools yüklü olmalı."
  exit 1
fi

if ! command -v productbuild >/dev/null 2>&1; then
  echo "❌ HATA: productbuild bulunamadı. Xcode Command Line Tools yüklü olmalı."
  exit 1
fi

# PyInstaller build kontrolü
if [ ! -f "dist/${APP_NAME}.app/Contents/MacOS/${APP_NAME}" ]; then
  echo "⚠️  UYARI: ${APP_NAME}.app bulunamadı!"
  echo "📦 Önce PyInstaller build alınmalı:"
  echo "   pyinstaller --noconfirm --clean Leta_Pipeline_Final.spec"
  echo ""
  read -p "Devam etmek istiyor musunuz? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

echo "📦 PKG oluşturuluyor..."
echo ""

# Geçici dizin
STAGE_DIR="dist_pkg_stage_macos"
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}/Applications"

# .app dosyasını kopyala
if [ -d "dist/${APP_NAME}.app" ]; then
  cp -R "dist/${APP_NAME}.app" "${STAGE_DIR}/Applications/"
  echo "✅ ${APP_NAME}.app kopyalandı"
else
  echo "❌ HATA: dist/${APP_NAME}.app bulunamadı!"
  exit 1
fi

# Kullanım kılavuzunu ekle
if [ -f "KULLANIM_KILAVUZU.txt" ]; then
  mkdir -p "${STAGE_DIR}/Applications/${APP_NAME}.app/Contents/Resources"
  cp "KULLANIM_KILAVUZU.txt" "${STAGE_DIR}/Applications/${APP_NAME}.app/Contents/Resources/"
  echo "✅ Kullanım kılavuzu eklendi"
fi

# PKG dosya yolları
PKG_COMPONENT="dist/${APP_NAME}_${VERSION}_component.pkg"
PKG_FINAL="dist/${APP_NAME}_${VERSION}.pkg"

rm -f "${PKG_COMPONENT}" "${PKG_FINAL}"

# Component PKG oluştur
echo "🔨 Component PKG oluşturuluyor..."
pkgbuild \
  --root "${STAGE_DIR}" \
  --identifier "${IDENTIFIER}" \
  --version "${VERSION}" \
  --install-location "/" \
  --scripts "${SCRIPT_DIR}/macos_scripts" 2>/dev/null || \
pkgbuild \
  --root "${STAGE_DIR}" \
  --identifier "${IDENTIFIER}" \
  --version "${VERSION}" \
  --install-location "/" \
  "${PKG_COMPONENT}"

echo "✅ Component PKG oluşturuldu: ${PKG_COMPONENT}"

# Distribution XML oluştur
DIST_XML="dist/${APP_NAME}_${VERSION}_distribution.xml"
cat > "${DIST_XML}" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>${DISPLAY_NAME} ${VERSION}</title>
    <organization>com.leta</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false" rootVolumeOnly="true"/>
    <welcome file="welcome.html" mime-type="text/html"/>
    <license file="license.html" mime-type="text/html"/>
    <conclusion file="conclusion.html" mime-type="text/html"/>
    <pkg-ref id="${IDENTIFIER}"/>
    <options customize="never" require-scripts="false"/>
    <choices-outline>
        <line choice="default">
            <line choice="${IDENTIFIER}"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="${IDENTIFIER}" visible="false">
        <pkg-ref id="${IDENTIFIER}"/>
    </choice>
    <pkg-ref id="${IDENTIFIER}" version="${VERSION}" onConclusion="none">${PKG_COMPONENT}</pkg-ref>
</installer-gui-script>
EOF

# Final PKG oluştur
echo "🔨 Final PKG oluşturuluyor..."
productbuild \
  --distribution "${DIST_XML}" \
  --package-path "dist" \
  --resources "${SCRIPT_DIR}/macos_resources" 2>/dev/null || \
productbuild \
  --distribution "${DIST_XML}" \
  --package-path "dist" \
  "${PKG_FINAL}"

# Temizlik
rm -rf "${STAGE_DIR}" "${PKG_COMPONENT}" "${DIST_XML}"

echo ""
echo "=========================================="
echo "✅ PKG başarıyla oluşturuldu!"
echo "=========================================="
echo "📦 Dosya: ${PKG_FINAL}"
echo "📊 Boyut: $(du -h "${PKG_FINAL}" | cut -f1)"
echo ""
echo "🚀 Kurulum için:"
echo "   open ${PKG_FINAL}"
echo ""


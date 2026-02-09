#!/usr/bin/env bash
# Leta Takip - macOS DMG Installer Builder
# Kullanım: ./Leta_Setup_Mac_DMG.sh [version]
# Örnek: ./Leta_Setup_Mac_DMG.sh 1.3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${1:-1.3}"
APP_NAME="Leta_Pipeline_v${VERSION//./_}"
DMG_NAME="Leta_Takip_${VERSION}.dmg"
VOLUME_NAME="Leta Takip ${VERSION}"

echo "=========================================="
echo "  Leta Takip macOS DMG Builder v${VERSION}"
echo "=========================================="
echo ""

# macOS kontrolü
if [[ "$(uname)" != "Darwin" ]]; then
  echo "❌ HATA: Bu script sadece macOS'ta çalışır!"
  exit 1
fi

# Gerekli araçlar kontrolü
if ! command -v hdiutil >/dev/null 2>&1; then
  echo "❌ HATA: hdiutil bulunamadı."
  exit 1
fi

# PyInstaller build kontrolü (.app macOS'ta Leta_Pipeline_Mac.spec ile oluşturulur)
if [ ! -d "dist/${APP_NAME}.app" ]; then
  detected_app=""
  for app in dist/*.app; do
    if [ -d "$app" ]; then
      if [ -n "${detected_app}" ]; then
        detected_app=""
        break
      fi
      detected_app="$app"
    fi
  done
  if [ -n "${detected_app}" ]; then
    APP_NAME="$(basename "${detected_app}" .app)"
    echo "⚠️  UYARI: dist/${APP_NAME}.app yerine mevcut bundle bulundu: ${detected_app}"
  else
    echo "❌ HATA: dist/${APP_NAME}.app bulunamadı!"
    echo "📦 macOS için önce: pyinstaller --noconfirm --clean Leta_Pipeline_Mac.spec"
    if [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${CI:-}" ]; then
      exit 1
    fi
    read -p "Devam etmek istiyor musunuz? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
  fi
fi

echo "📦 DMG oluşturuluyor..."
echo ""

# Geçici dizin
STAGE_DIR="dist_dmg_stage"
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}"

# .app dosyasını kopyala
if [ -d "dist/${APP_NAME}.app" ]; then
  cp -R "dist/${APP_NAME}.app" "${STAGE_DIR}/"
  echo "✅ ${APP_NAME}.app kopyalandı"
else
  echo "❌ HATA: dist/${APP_NAME}.app bulunamadı!"
  exit 1
fi

# Kullanım kılavuzunu ekle (script/assets veya repo kökü)
if [ -f "script/assets/KULLANIM_KILAVUZU.txt" ]; then
  cp "script/assets/KULLANIM_KILAVUZU.txt" "${STAGE_DIR}/"
  echo "✅ Kullanım kılavuzu eklendi"
elif [ -f "KULLANIM_KILAVUZU.txt" ]; then
  cp "KULLANIM_KILAVUZU.txt" "${STAGE_DIR}/"
  echo "✅ Kullanım kılavuzu eklendi"
fi

# Applications klasörüne sembolik link oluştur (drag & drop için)
ln -s /Applications "${STAGE_DIR}/Applications"
echo "✅ Applications linki oluşturuldu"

# Eski DMG'i sil
rm -f "dist/${DMG_NAME}"

# DMG oluştur
echo "🔨 DMG oluşturuluyor..."
hdiutil create \
  -volname "${VOLUME_NAME}" \
  -srcfolder "${STAGE_DIR}" \
  -ov \
  -format UDZO \
  -fs HFS+ \
  "dist/${DMG_NAME}"

# DMG'i optimize et (opsiyonel)
if command -v hdiutil >/dev/null 2>&1; then
  echo "🔧 DMG optimize ediliyor..."
  hdiutil convert "dist/${DMG_NAME}" \
    -format UDZO \
    -o "dist/${DMG_NAME}.tmp" \
    -imagekey zlib-level=9
  mv "dist/${DMG_NAME}.tmp" "dist/${DMG_NAME}"
fi

# Temizlik
rm -rf "${STAGE_DIR}"

echo ""
echo "=========================================="
echo "✅ DMG başarıyla oluşturuldu!"
echo "=========================================="
echo "📦 Dosya: dist/${DMG_NAME}"
echo "📊 Boyut: $(du -h "dist/${DMG_NAME}" | cut -f1)"
echo ""
echo "🚀 Kurulum için:"
echo "   open dist/${DMG_NAME}"
echo ""
echo "💡 Kullanıcılar DMG'i açıp ${APP_NAME}.app'i"
echo "   Applications klasörüne sürükleyebilir."
echo ""

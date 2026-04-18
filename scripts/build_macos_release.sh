#!/usr/bin/env bash
# PyInstaller → MechKeys.app + zip + DMG (tek indirilebilir dosya: .dmg)
# DMG istemezsen: SKIP_DMG=1 ./scripts/build_macos_release.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARCH="$(uname -m)"
OUT_NAME="MechKeys-macos-${ARCH}"
DIST="${ROOT}/dist"
APP="${DIST}/MechKeys.app"

echo "==> Bağımlılıklar (geçici venv)"
rm -rf .build-venv
python3 -m venv .build-venv
# shellcheck disable=SC1091
source .build-venv/bin/activate
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt pyinstaller

echo "==> PyInstaller"
PYI_ARGS=(
  run.py
  --windowed
  --name MechKeys
  --osx-bundle-identifier com.mechkeys.app
  --collect-submodules pygame
  --hidden-import AppKit
  --hidden-import Foundation
  --hidden-import objc
  --hidden-import PyObjCTools
  --noconfirm
  --clean
)

if [[ -d "${ROOT}/sounds" ]] && compgen -G "${ROOT}/sounds/*.wav" > /dev/null; then
  echo "    (sounds/ klasörü .app içine ekleniyor)"
  PYI_ARGS+=(--add-data "sounds:sounds")
fi

pyinstaller "${PYI_ARGS[@]}"

echo "==> ZIP (ditto)"
cd "$DIST"
rm -f "${OUT_NAME}.zip"
ditto -c -k --keepParent MechKeys.app "${OUT_NAME}.zip"
echo "    ${DIST}/${OUT_NAME}.zip"

if [[ "${SKIP_DMG:-}" != "1" ]]; then
  echo "==> DMG (tek dosya dağıtımı — diğer uygulamalardaki .dmg gibi)"
  rm -f "${OUT_NAME}.dmg"
  hdiutil create -volname "MechKeys" -srcfolder MechKeys.app -ov -format UDZO \
    -imagekey zlib-level=9 "${OUT_NAME}.dmg"
  echo "    ${DIST}/${OUT_NAME}.dmg"
fi

deactivate 2>/dev/null || true
echo "==> Bitti. İlk çalıştırmada ses yoksa: mechkeys-download-sounds veya sounds/ ile yeniden derle."

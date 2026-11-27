#!/usr/bin/env bash
# Turns dist/Hoplet.app (from PyInstaller) into dist/Hoplet-macOS-<arch>.dmg,
# a disk image with the app and a shortcut to drag it into Applications.
# Run from the repository root after: pyinstaller packaging/hoplet.spec --noconfirm
set -euo pipefail

ARCH="$(uname -m)"                       # arm64 (Apple silicon) or x86_64 (Intel)
[ "$ARCH" = "x86_64" ] && ARCH=intel
STAGE=build/dmg
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R dist/Hoplet.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"

OUT="dist/Hoplet-macOS-$ARCH.dmg"
rm -f "$OUT"
hdiutil create -volname Hoplet -srcfolder "$STAGE" -ov -format UDZO "$OUT"
echo "Built $OUT"

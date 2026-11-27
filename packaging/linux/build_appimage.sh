#!/usr/bin/env bash
# Turns dist/Hoplet/ (from PyInstaller) into dist/Hoplet-x86_64.AppImage.
# Run from the repository root after: pyinstaller packaging/hoplet.spec --noconfirm
set -euo pipefail

APPDIR=build/Hoplet.AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib"
cp -a dist/Hoplet "$APPDIR/usr/lib/hoplet"
cp src/hoplet/assets/icons/app.png "$APPDIR/hoplet.png"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/hoplet/Hoplet" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/hoplet.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Hoplet
Comment=A tiny desktop friend who reminds you to move
Exec=Hoplet
Icon=hoplet
Terminal=false
Categories=Utility;
EOF

TOOL=build/appimagetool
if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
# --appimage-extract-and-run: works without FUSE (e.g. on CI machines).
ARCH=x86_64 "$TOOL" --appimage-extract-and-run "$APPDIR" dist/Hoplet-x86_64.AppImage
echo "Built dist/Hoplet-x86_64.AppImage"

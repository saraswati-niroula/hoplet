# PyInstaller recipe for the standalone Hoplet app (no Python needed by users).
#
#   pip install ".[app]"
#   pyinstaller packaging/hoplet.spec --noconfirm
#
# Output: dist/Hoplet/ (Windows, Linux) or dist/Hoplet.app (macOS).
# The .github/workflows/apps.yml workflow turns that into the downloads:
# Hoplet-Setup.exe, Hoplet.dmg and Hoplet.AppImage.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT / "src"))
from hoplet import __version__  # noqa: E402

ICON = str(ROOT / "src" / "hoplet" / "assets" / "icons" / "app.png")  # converted by Pillow

a = Analysis(
    [str(ROOT / "packaging" / "hoplet_app.py")],
    pathex=[str(ROOT / "src")],
    datas=collect_data_files("hoplet"),           # messages.json, app icon
    # Hoplet only uses QtCore/QtGui/QtWidgets; keep the download small.
    excludes=["tkinter", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick",
              "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtPdf",
              "PySide6.QtConcurrent"],
    noarchive=False,
)
# Qt's own UI translations (~7 MB) are unused: Hoplet's text is its own.
a.datas = [d for d in a.datas if "translations" not in Path(d[0]).parts]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Hoplet",
    console=False,              # no terminal window on Windows/macOS
    icon=ICON,
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="Hoplet", upx=False)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Hoplet.app",
        icon=ICON,
        bundle_identifier="io.github.hoplet",
        version=__version__,
        info_plist={
            "CFBundleName": "Hoplet",
            "CFBundleDisplayName": "Hoplet",
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "LSUIElement": True,                  # menu-bar app: no Dock icon
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "MIT License",
        },
    )

"""Test setup: headless Qt and throwaway home/config folders, so tests never
touch the real settings, autostart entries or cache of whoever runs them."""
import os
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="hoplet-tests-"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# Linux uses XDG_*, Windows APPDATA/LOCALAPPDATA, macOS the home folder.
for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "APPDATA", "LOCALAPPDATA"):
    os.environ[var] = str(TMP / var.lower())
os.environ["HOME"] = os.environ["USERPROFILE"] = str(TMP / "home")

from PySide6.QtWidgets import QApplication  # noqa: E402

from hoplet import autostart  # noqa: E402

if sys.platform == "win32":
    # The Run key lives in the real registry: use a throwaway value name.
    autostart.RUN_VALUE = "Hoplet-tests"

APP = QApplication.instance() or QApplication(sys.argv[:1])

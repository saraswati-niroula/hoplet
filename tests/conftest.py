"""Test setup: headless Qt and throwaway XDG folders, so tests never touch the
real settings, autostart entries or cache of whoever runs them."""
import os
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="hoplet-tests-"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
    os.environ[var] = str(TMP / var.lower())

from PySide6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication(sys.argv[:1])

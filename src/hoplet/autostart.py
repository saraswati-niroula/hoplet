"""Desktop integration via freedesktop .desktop files (GNOME, KDE, XFCE, ...):

* an app-menu launcher in ~/.local/share/applications/
* an optional login autostart entry in ~/.config/autostart/

Both run the app with the same Python interpreter that's running now, so they
work for pipx, pip --user, virtualenvs and development installs alike.
"""
from __future__ import annotations

import logging
import shlex
import sys
from pathlib import Path

from .paths import APP_ICON, APP_ID, APPLICATIONS_DIR, AUTOSTART_DIR

log = logging.getLogger(__name__)

AUTOSTART_FILE = AUTOSTART_DIR / f"{APP_ID}.desktop"
LAUNCHER_FILE = APPLICATIONS_DIR / f"{APP_ID}.desktop"


def command() -> str:
    """Exec= line that starts the app with the current interpreter."""
    return f"{shlex.quote(sys.executable)} -m hoplet"


def desktop_entry(autostart: bool) -> str:
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=Hoplet",
        "Comment=A tiny desktop friend who reminds you to move",
        f"Exec={command()}",
        f"Icon={APP_ICON}",
        "Terminal=false",
        "Categories=Utility;",
        "Keywords=health;break;reminder;stretch;posture;",
        "StartupNotify=false",
    ]
    if autostart:
        lines += ["X-GNOME-Autostart-enabled=true", "X-GNOME-Autostart-Delay=10"]
    return "\n".join(lines) + "\n"


def _write(path: Path, text: str) -> None:
    try:
        if path.exists() and path.read_text(encoding="utf-8") == text:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        log.info("Wrote %s", path)
    except OSError as exc:
        log.warning("Could not write %s (%s)", path, exc)


def _remove(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
            log.info("Removed %s", path)
    except OSError as exc:
        log.warning("Could not remove %s (%s)", path, exc)


def is_enabled() -> bool:
    return AUTOSTART_FILE.exists()


def set_enabled(enabled: bool) -> None:
    if enabled:
        _write(AUTOSTART_FILE, desktop_entry(autostart=True))
    else:
        _remove(AUTOSTART_FILE)


def install_launcher() -> None:
    """Make the app show up in the Activities / app menu."""
    _write(LAUNCHER_FILE, desktop_entry(autostart=False))


def sync(autostart_enabled: bool) -> None:
    """Called at startup: keeps both entries pointing at this installation."""
    install_launcher()
    set_enabled(autostart_enabled)


def remove_all() -> list[Path]:
    removed = [p for p in (AUTOSTART_FILE, LAUNCHER_FILE) if p.exists()]
    for path in removed:
        _remove(path)
    return removed

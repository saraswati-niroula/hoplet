"""Desktop integration: an app-menu launcher and an optional start-at-login entry.

* Linux:   freedesktop .desktop files (GNOME, KDE, XFCE, ...)
           ~/.local/share/applications/hoplet.desktop  (app menu)
           ~/.config/autostart/hoplet.desktop          (login)
* Windows: a Start Menu shortcut, and a value under
           HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run (login)
* macOS:   a LaunchAgent, ~/Library/LaunchAgents/io.github.hoplet.plist (login);
           no app-menu entry (start it with `hoplet` from a terminal)

Everything starts this same installation: for pip/pipx/dev installs, the
Python interpreter that's running now with `-m hoplet`; for the standalone
apps (packaging/), the app itself. On Windows the installer owns the Start
Menu shortcut, so the app doesn't make one.
"""
from __future__ import annotations

import logging
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from . import paths
from .paths import APP_ICON, APP_ID, CACHE_DIR, DATA_DIR

log = logging.getLogger(__name__)


def _gui_python() -> str:
    """On Windows, pythonw.exe runs without opening a console window."""
    exe = Path(sys.executable)
    if paths.IS_WINDOWS:
        windowless = exe.with_name("pythonw.exe")
        if windowless.exists():
            return str(windowless)
    return str(exe)


def app_command() -> list[str]:
    """Program and arguments that start this installation of Hoplet."""
    if paths.IS_FROZEN:
        # An AppImage runs from a temporary mount; $APPIMAGE is the real file.
        return [os.environ.get("APPIMAGE") or sys.executable]
    return [_gui_python(), "-m", "hoplet"]


def command() -> str:
    """app_command() as a single command line."""
    program, *args = app_command()
    if paths.IS_WINDOWS:
        return " ".join([f'"{program}"', *args])
    return " ".join(shlex.quote(part) for part in (program, *args))


def _write(path: Path, data: str | bytes) -> None:
    try:
        raw = data.encode("utf-8") if isinstance(data, str) else data
        if path.exists() and path.read_bytes() == raw:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
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


# ================================================================== Linux
if paths.IS_LINUX:
    AUTOSTART_FILE: Path | None = paths.AUTOSTART_DIR / f"{APP_ID}.desktop"
    LAUNCHER_FILE: Path | None = paths.APPLICATIONS_DIR / f"{APP_ID}.desktop"

    def _icon() -> Path:
        """The AppImage's own files vanish when it exits, so menu entries
        need a copy of the icon that stays put."""
        if not paths.IS_FROZEN:
            return APP_ICON
        kept = DATA_DIR / "hoplet.png"
        try:
            if not kept.exists() or kept.read_bytes() != APP_ICON.read_bytes():
                kept.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(APP_ICON, kept)
        except OSError as exc:
            log.warning("Could not copy the icon (%s)", exc)
        return kept

    def desktop_entry(autostart: bool) -> str:
        lines = [
            "[Desktop Entry]",
            "Type=Application",
            "Name=Hoplet",
            "Comment=A tiny desktop friend who reminds you to move",
            f"Exec={command()}",
            f"Icon={_icon()}",
            "Terminal=false",
            "Categories=Utility;",
            "Keywords=health;break;reminder;stretch;posture;",
            "StartupNotify=false",
        ]
        if autostart:
            lines += ["X-GNOME-Autostart-enabled=true", "X-GNOME-Autostart-Delay=10"]
        return "\n".join(lines) + "\n"

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

# ================================================================ Windows
elif paths.IS_WINDOWS:
    import winreg

    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    RUN_VALUE = "Hoplet"                     # tests point this at a throwaway name
    AUTOSTART_FILE = None
    LAUNCHER_FILE = paths.START_MENU_DIR / "Hoplet.lnk"
    ICON_FILE = CACHE_DIR / "hoplet.ico"

    def is_enabled() -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.QueryValueEx(key, RUN_VALUE)
            return True
        except OSError:
            return False

    def set_enabled(enabled: bool) -> None:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                if enabled:
                    winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, command())
                elif is_enabled():
                    winreg.DeleteValue(key, RUN_VALUE)
        except OSError as exc:
            log.warning("Could not update the login entry (%s)", exc)

    def _make_icon() -> str:
        """Windows shortcuts need an .ico; convert the bundled PNG (best effort)."""
        try:
            from PySide6.QtGui import QImage
            if not ICON_FILE.exists():
                ICON_FILE.parent.mkdir(parents=True, exist_ok=True)
                QImage(str(APP_ICON)).scaled(256, 256).save(str(ICON_FILE), "ICO")
            return str(ICON_FILE) if ICON_FILE.exists() else ""
        except Exception:                    # noqa: BLE001 - an icon is a nicety
            return ""

    def install_launcher() -> None:
        """Start Menu shortcut, made once with PowerShell (no extra dependencies).
        The standalone app's installer makes its own, so skip it there."""
        if paths.IS_FROZEN or LAUNCHER_FILE.exists():
            return

        def q(value) -> str:                 # PowerShell single-quoted string
            return "'" + str(value).replace("'", "''") + "'"

        icon = _make_icon()
        script = "; ".join(line for line in [
            f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut({q(LAUNCHER_FILE)})",
            f"$s.TargetPath = {q(_gui_python())}",
            "$s.Arguments = '-m hoplet'",
            f"$s.WorkingDirectory = {q(Path.home())}",
            "$s.Description = 'A tiny desktop friend who reminds you to move'",
            f"$s.IconLocation = {q(icon)}" if icon else "",
            "$s.Save()",
        ] if line)
        try:
            LAUNCHER_FILE.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           check=True, capture_output=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            log.info("Wrote %s", LAUNCHER_FILE)
        except (OSError, subprocess.SubprocessError) as exc:
            log.warning("Could not create the Start Menu shortcut (%s)", exc)

# ================================================================== macOS
else:
    AUTOSTART_FILE = paths.LAUNCH_AGENTS_DIR / "io.github.hoplet.plist"
    LAUNCHER_FILE = None

    def launch_agent() -> bytes:
        return plistlib.dumps({
            "Label": "io.github.hoplet",
            "ProgramArguments": app_command(),
            "RunAtLoad": True,
            "ProcessType": "Interactive",
        })

    def is_enabled() -> bool:
        return AUTOSTART_FILE.exists()

    def set_enabled(enabled: bool) -> None:
        if enabled:
            _write(AUTOSTART_FILE, launch_agent())
        else:
            _remove(AUTOSTART_FILE)

    def install_launcher() -> None:
        """No app-menu entry on macOS for a pip/pipx install."""


# ============================================================ all systems
def sync(autostart_enabled: bool) -> None:
    """Called at startup: keeps the entries pointing at this installation."""
    install_launcher()
    set_enabled(autostart_enabled)


def remove_all() -> list[str]:
    """Remove the launcher and login entry; returns what was removed."""
    removed = []
    if is_enabled():
        set_enabled(False)
        removed.append(str(AUTOSTART_FILE) if AUTOSTART_FILE else "login entry (registry Run key)")
    if LAUNCHER_FILE and LAUNCHER_FILE.exists():
        _remove(LAUNCHER_FILE)
        removed.append(str(LAUNCHER_FILE))
    return removed

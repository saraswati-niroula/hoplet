"""Hoplet — a little hopping companion who reminds you to move.

    hoplet                      start (lives in the system tray)
    hoplet --show-now           appear a couple of seconds after starting
    hoplet --interval-seconds 20    (testing) visit every 20 seconds
    hoplet --export-character DIR   write the placeholder art as a template
    hoplet --uninstall          remove menu/autostart entries and cached files
"""
from __future__ import annotations

import argparse
import ctypes
import logging
import logging.handlers
import os
import shutil
import signal
import sys
from pathlib import Path

from . import __version__


def prepare_platform() -> None:
    """GNOME/KDE on Wayland don't let apps position their own windows or stay
    on top, so run through XWayland (xcb) instead. Must happen before
    QApplication is created."""
    on_wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or "WAYLAND_DISPLAY" in os.environ
    if on_wayland and "QT_QPA_PLATFORM" not in os.environ and os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    if os.environ.get("QT_QPA_PLATFORM", "xcb").startswith("xcb"):
        try:
            ctypes.CDLL("libxcb-cursor.so.0")
        except OSError:
            sys.exit("Hoplet needs the libxcb-cursor0 system library. Install it with:\n"
                     "    sudo apt install libxcb-cursor0        (Debian/Ubuntu)\n"
                     "    sudo dnf install xcb-util-cursor       (Fedora)\n"
                     "    sudo pacman -S xcb-util-cursor         (Arch)")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="hoplet", description="Hoplet: a little hopping companion who reminds you to move.")
    parser.add_argument("--version", action="version", version=f"hoplet {__version__}")
    parser.add_argument("--show-now", action="store_true", help="appear shortly after start")
    parser.add_argument("--interval-seconds", type=int, metavar="N",
                        help="testing: visit every N seconds instead of the configured interval")
    parser.add_argument("--verbose", "-v", action="store_true", help="debug logging")
    parser.add_argument("--export-character", type=Path, metavar="DIR",
                        help="write the placeholder character's frames to DIR as a starting "
                             "template for your own art, then exit")
    parser.add_argument("--gender", choices=("girl", "boy"), default="girl",
                        help="with --export-character (default: girl)")
    parser.add_argument("--theme", default="sakura", help="with --export-character (default: sakura)")
    parser.add_argument("--uninstall", action="store_true",
                        help="remove Hoplet's menu entry, autostart entry and cache, then exit "
                             "(your settings and custom art are kept)")
    return parser.parse_args(argv)


def setup_logging(verbose: bool) -> None:
    from .paths import LOG_FILE
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=256_000, backupCount=1, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")


def export_character(out_dir: Path, gender: str, theme_key: str) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    from . import placeholder_art
    from .themes import THEMES
    if theme_key not in THEMES:
        sys.exit(f"Unknown theme {theme_key!r}. Choose from: {', '.join(THEMES)}")
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841
    placeholder_art.generate(out_dir.expanduser().resolve(), gender, THEMES[theme_key])
    print(f"Wrote the {gender} character ({THEMES[theme_key].name}) to {out_dir}")
    return 0


def uninstall() -> int:
    from . import autostart
    from .paths import CACHE_DIR, CONFIG_DIR, DATA_DIR
    for path in autostart.remove_all():
        print(f"removed {path}")
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
        print(f"removed {CACHE_DIR}")
    print("\nKept your settings and custom art (delete them yourself if you like):")
    print(f"  {CONFIG_DIR}\n  {DATA_DIR}")
    print("\nTo remove the program itself:  pipx uninstall hoplet   (or: pip uninstall hoplet)")
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.export_character:
        return export_character(args.export_character, args.gender, args.theme)
    if args.uninstall:
        return uninstall()

    setup_logging(args.verbose)
    prepare_platform()

    from PySide6.QtCore import QDir, QLockFile, QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from . import autostart, character_assets
    from .animation_manager import AnimationLibrary
    from .character import CharacterWindow
    from .message_manager import MessageManager
    from .paths import APP_ICON
    from .reminder_scheduler import ReminderScheduler
    from .settings import Settings
    from .settings_dialog import SettingsDialog
    from .themes import get_theme
    from .tray import Tray

    app = QApplication(sys.argv[:1])
    app.setApplicationName("hoplet")
    app.setApplicationDisplayName("Hoplet")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("hoplet")
    app.setWindowIcon(QIcon(str(APP_ICON)))
    app.setQuitOnLastWindowClosed(False)          # we live in the tray

    lock = QLockFile(QDir.temp().filePath(f"hoplet-{os.getuid()}.lock"))
    if not lock.tryLock(100):
        logging.info("Hoplet is already running.")
        return 0

    log = logging.getLogger("hoplet")
    log.info("Hoplet %s on Qt platform %s", __version__, app.platformName())

    settings = Settings.load()
    autostart.sync(settings.autostart)     # menu entry + autostart point at this install

    def load_look():
        """(animation library, theme, tray icon) for the current settings."""
        theme = get_theme(settings.theme)
        folder = character_assets.character_dir(settings.character, theme)
        log.info("Character: %s (%s), theme: %s", settings.character_name, settings.character, theme.name)
        return (AnimationLibrary(folder, settings.character_scale), theme,
                character_assets.icon(settings.character, theme))

    messages = MessageManager()
    messages.name = settings.character_name
    library, theme, tray_icon = load_look()
    character = CharacterWindow(library, theme, messages, settings)
    scheduler = ReminderScheduler(settings, args.interval_seconds)

    # ------------------------------------------------------------- wiring
    def on_reminder_due() -> None:
        log.info("Visit time! Here comes %s~", settings.character_name)
        if not character.appear(messages.reminder()):
            scheduler.reminder_finished("dismissed")

    scheduler.reminder_due.connect(on_reminder_due)
    character.finished.connect(scheduler.reminder_finished)

    dialog_ref: list[SettingsDialog] = []

    def open_settings() -> None:
        if dialog_ref:                      # already open: bring it forward
            dialog_ref[0].raise_()
            dialog_ref[0].activateWindow()
            return
        dialog = SettingsDialog(settings)
        dialog_ref.append(dialog)
        dialog.preview_requested.connect(scheduler.trigger_now)
        old_look = (settings.character, settings.theme, settings.character_scale)
        if dialog.exec():
            dialog.apply_to(settings)
            settings.save()
            autostart.set_enabled(settings.autostart)
            messages.name = settings.character_name
            if (settings.character, settings.theme, settings.character_scale) != old_look:
                library, theme, icon = load_look()
                character.set_look(library, theme)
                if tray:
                    tray.set_icon(icon)
            scheduler.apply_settings()
            if tray:
                tray.set_paused(not settings.reminders_enabled)
            log.info("Settings saved")
        dialog_ref.clear()

    def set_paused(paused: bool) -> None:
        settings.reminders_enabled = not paused
        settings.save()
        scheduler.apply_settings()
        if tray:
            tray.refresh()

    character.settings_requested.connect(open_settings)
    character.quit_requested.connect(app.quit)

    tray = None
    if Tray.available():
        tray = Tray(scheduler.status_text, tray_icon)
        tray.show_now.connect(scheduler.trigger_now)
        tray.pause_toggled.connect(set_paused)
        tray.settings_requested.connect(open_settings)
        tray.quit_requested.connect(app.quit)
        scheduler.changed.connect(tray.refresh)
        tray.set_paused(not settings.reminders_enabled)
        tray.show()
    else:
        log.warning("No system tray available. Right-click the character for Settings/Quit, "
                    "or stop Hoplet with: pkill -f 'python.* -m hoplet'")

    scheduler.start()
    log.info(scheduler.status_text())
    if args.show_now or tray is None:
        QTimer.singleShot(1500, scheduler.trigger_now)

    # Let Ctrl+C in a terminal quit cleanly (Python only sees signals when it runs).
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    heartbeat = QTimer(interval=500)
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start()

    return app.exec()

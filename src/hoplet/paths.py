"""Central place for all filesystem locations used by the app.

Nothing is written inside the installed package. Each OS gets its usual
locations:

  Linux (XDG base directories)
    ~/.config/hoplet/settings.json      your preferences
    ~/.config/hoplet/messages.json      optional: your own lines
    ~/.local/share/hoplet/characters/   optional: your own art
    ~/.cache/hoplet/                    generated art + log

  Windows
    %APPDATA%\\Hoplet\\                  settings.json, messages.json, characters\\
    %LOCALAPPDATA%\\Hoplet\\Cache\\        generated art + log

  macOS
    ~/Library/Application Support/Hoplet/   settings.json, messages.json, characters/
    ~/Library/Caches/Hoplet/                generated art + log
"""
import os
import sys
from pathlib import Path

APP_ID = "hoplet"

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"
APP_ICON = ASSETS_DIR / "icons" / "app.png"
DEFAULT_MESSAGES_FILE = ASSETS_DIR / "messages.json"

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = not (IS_WINDOWS or IS_MAC)


def _env_dir(var: str, fallback: Path) -> Path:
    value = os.environ.get(var)
    return Path(value) if value and os.path.isabs(value) else fallback


if IS_WINDOWS:
    _roaming = _env_dir("APPDATA", Path.home() / "AppData" / "Roaming")
    _local = _env_dir("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    CONFIG_DIR = DATA_DIR = _roaming / "Hoplet"
    CACHE_DIR = _local / "Hoplet" / "Cache"
    START_MENU_DIR = _roaming / "Microsoft" / "Windows" / "Start Menu" / "Programs"
elif IS_MAC:
    CONFIG_DIR = DATA_DIR = Path.home() / "Library" / "Application Support" / "Hoplet"
    CACHE_DIR = Path.home() / "Library" / "Caches" / "Hoplet"
    LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
else:
    CONFIG_DIR = _env_dir("XDG_CONFIG_HOME", Path.home() / ".config") / APP_ID
    DATA_DIR = _env_dir("XDG_DATA_HOME", Path.home() / ".local" / "share") / APP_ID
    CACHE_DIR = _env_dir("XDG_CACHE_HOME", Path.home() / ".cache") / APP_ID
    AUTOSTART_DIR = _env_dir("XDG_CONFIG_HOME", Path.home() / ".config") / "autostart"
    APPLICATIONS_DIR = _env_dir("XDG_DATA_HOME", Path.home() / ".local" / "share") / "applications"

SETTINGS_FILE = CONFIG_DIR / "settings.json"
USER_MESSAGES_FILE = CONFIG_DIR / "messages.json"
CUSTOM_CHARACTERS_DIR = DATA_DIR / "characters"
LOG_FILE = CACHE_DIR / "companion.log"

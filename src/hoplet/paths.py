"""Central place for all filesystem locations used by the app.

Follows the XDG base directory spec, so nothing is written inside the
installed package:

  ~/.config/hoplet/settings.json    your preferences
  ~/.config/hoplet/messages.json    optional: your own lines
  ~/.local/share/hoplet/characters/ optional: your own art
  ~/.cache/hoplet/                  generated art + log
"""
import os
from pathlib import Path

APP_ID = "hoplet"

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"
APP_ICON = ASSETS_DIR / "icons" / "app.png"
DEFAULT_MESSAGES_FILE = ASSETS_DIR / "messages.json"


def _xdg(var: str, fallback: str) -> Path:
    value = os.environ.get(var)
    return Path(value) if value and os.path.isabs(value) else Path.home() / fallback


CONFIG_DIR = _xdg("XDG_CONFIG_HOME", ".config") / APP_ID
DATA_DIR = _xdg("XDG_DATA_HOME", ".local/share") / APP_ID
CACHE_DIR = _xdg("XDG_CACHE_HOME", ".cache") / APP_ID

SETTINGS_FILE = CONFIG_DIR / "settings.json"
USER_MESSAGES_FILE = CONFIG_DIR / "messages.json"
CUSTOM_CHARACTERS_DIR = DATA_DIR / "characters"
LOG_FILE = CACHE_DIR / "companion.log"

AUTOSTART_DIR = _xdg("XDG_CONFIG_HOME", ".config") / "autostart"
APPLICATIONS_DIR = _xdg("XDG_DATA_HOME", ".local/share") / "applications"

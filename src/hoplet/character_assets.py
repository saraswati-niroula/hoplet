"""Finds the art for the chosen character.

Lookup order for gender "girl" / "boy":
  1. ~/.local/share/hoplet/characters/<gender>/animations.json
     -> your own art (theme then
     only colors the speech bubble and settings window)
  2. the procedurally drawn placeholder in the chosen theme, generated once
     into ~/.cache/hoplet/ and reused afterwards
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap

from . import placeholder_art
from .paths import APP_ICON, CACHE_DIR, CUSTOM_CHARACTERS_DIR
from .themes import Theme

log = logging.getLogger(__name__)

GENDERS = placeholder_art.GENDERS


def custom_dir(gender: str) -> Path | None:
    folder = CUSTOM_CHARACTERS_DIR / gender
    return folder if (folder / "animations.json").exists() else None


def character_dir(gender: str, theme: Theme) -> Path:
    custom = custom_dir(gender)
    if custom:
        return custom
    folder = CACHE_DIR / f"placeholder-v{placeholder_art.VERSION}" / f"{gender}-{theme.key}"
    if not (folder / "animations.json").exists():
        log.info("Drawing the %s character in %s…", gender, theme.name)
        placeholder_art.generate(folder, gender, theme)
    return folder


def icon(gender: str, theme: Theme) -> QIcon:
    path = character_dir(gender, theme) / "icon.png"
    return QIcon(str(path if path.exists() else APP_ICON))


def preview(gender: str, theme: Theme, height: int = 150) -> QPixmap:
    """A quick still of the character for the settings window."""
    custom = custom_dir(gender)
    if custom:
        frames = sorted(custom.glob("idle/*.png"))
        pix = QPixmap(str(frames[0])) if frames else QPixmap()
    else:
        look = placeholder_art.Look(gender, theme)
        pix = QPixmap.fromImage(placeholder_art.render(placeholder_art.Pose(), look))
    return pix.scaledToHeight(height, placeholder_art.Qt.TransformationMode.SmoothTransformation) \
        if not pix.isNull() else pix

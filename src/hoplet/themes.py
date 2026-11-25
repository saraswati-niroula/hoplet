"""Color themes. Each theme is a handful of base colors; every UI color
(bubble, buttons, settings window, placeholder outfit) is derived from them.

Add a theme by adding one entry to THEMES — nothing else needs to change.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor

from .paths import CACHE_DIR


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    main: str      # outfit / primary color
    deep: str      # outlines, strong accents
    light: str     # soft backgrounds
    accent: str    # bows, hair ties, sparkles
    text: str      # readable text color

    # ------------------------------------------------------------ helpers
    def c(self, name: str) -> QColor:
        return QColor(getattr(self, name))

    def mix(self, a: str, b: str, t: float) -> str:
        """Blend two theme colors (or hex strings); t=0 -> a, t=1 -> b."""
        ca = QColor(getattr(self, a, a))
        cb = QColor(getattr(self, b, b))
        r = round(ca.red() + (cb.red() - ca.red()) * t)
        g = round(ca.green() + (cb.green() - ca.green()) * t)
        bl = round(ca.blue() + (cb.blue() - ca.blue()) * t)
        return QColor(r, g, bl).name()

    @property
    def button(self) -> str:
        return self.mix("main", "deep", 0.35)

    @property
    def button_text(self) -> str:
        """White on darker buttons, theme text on light ones (e.g. yellow)."""
        col = QColor(self.button)
        lum = 0.2126 * col.redF() + 0.7152 * col.greenF() + 0.0722 * col.blueF()
        return "#FFFFFF" if lum < 0.62 else self.text

    @property
    def strong(self) -> str:
        """Readable colored text (titles, secondary button labels)."""
        return QColor(self.deep).darker(118).name()

    @property
    def bubble_bg(self) -> str:
        return self.mix("light", "#FFFFFF", 0.65)

    @property
    def soft_border(self) -> str:
        return self.mix("main", "#FFFFFF", 0.45)

    # -------------------------------------------------------------- styles
    def bubble_qss(self) -> str:
        return f"""
        QLabel#text {{ color: {self.text}; font-size: 11pt; font-weight: 600; }}
        QPushButton {{ border-radius: 13px; padding: 6px 12px; font-size: 10pt; font-weight: 700; }}
        QPushButton#ok {{ background: {self.button}; color: {self.button_text}; border: 2px solid {self.deep}; }}
        QPushButton#ok:hover {{ background: {self.mix('main', 'deep', 0.55)}; }}
        QPushButton#ok:pressed {{ background: {self.deep}; }}
        QPushButton#snooze {{ background: {self.mix('light', '#FFFFFF', 0.4)}; color: {self.strong};
                              border: 2px solid {self.soft_border}; }}
        QPushButton#snooze:hover {{ background: {self.light}; }}
        QPushButton#snooze:pressed {{ background: {self.mix('light', 'main', 0.3)}; }}
        """

    def dialog_qss(self) -> str:
        icons = self.ui_icons().as_posix()
        sub = self.mix("text", "#FFFFFF", 0.4)
        return f"""
        QDialog {{ background: {self.mix('light', '#FFFFFF', 0.55)}; }}
        QLabel, QCheckBox, QGroupBox {{ color: {self.text}; font-size: 10pt; }}
        QLabel#title {{ font-size: 15pt; font-weight: 800; color: {self.strong}; }}
        QLabel#subtitle {{ color: {sub}; }}
        QLabel#preview {{ background: {self.bubble_bg}; border: 2px solid {self.soft_border}; border-radius: 12px; }}
        QGroupBox {{ border: 2px solid {self.soft_border}; border-radius: 12px; margin-top: 12px;
                     padding: 10px 8px 6px 8px; font-weight: 700; background: #FFFFFF; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}
        QComboBox, QSpinBox, QTimeEdit, QLineEdit {{ border: 2px solid {self.soft_border}; border-radius: 8px;
                     padding: 3px 6px; background: white; color: {self.text}; min-width: 110px; }}
        QComboBox::drop-down {{ border: none; width: 22px; }}
        QComboBox::down-arrow {{ image: url({icons}/down.svg); width: 10px; height: 6px; }}
        QComboBox QAbstractItemView {{ border: 2px solid {self.soft_border}; background: white; color: {self.text};
                     selection-background-color: {self.light}; selection-color: {self.text}; }}
        QSpinBox::up-button, QTimeEdit::up-button {{ subcontrol-position: top right; border: none; width: 20px; }}
        QSpinBox::down-button, QTimeEdit::down-button {{ subcontrol-position: bottom right; border: none; width: 20px; }}
        QSpinBox::up-arrow, QTimeEdit::up-arrow {{ image: url({icons}/up.svg); width: 10px; height: 6px; }}
        QSpinBox::down-arrow, QTimeEdit::down-arrow {{ image: url({icons}/down.svg); width: 10px; height: 6px; }}
        QCheckBox::indicator, QGroupBox::indicator {{ width: 15px; height: 15px; border: 2px solid {self.main};
                     border-radius: 5px; background: white; }}
        QCheckBox::indicator:checked, QGroupBox::indicator:checked {{ background: {self.button};
                     border-color: {self.deep}; image: url({icons}/check.svg); }}
        QPushButton {{ border-radius: 12px; padding: 7px 16px; font-weight: 700; }}
        QPushButton#save {{ background: {self.button}; color: {self.button_text}; border: 2px solid {self.deep}; }}
        QPushButton#save:hover {{ background: {self.mix('main', 'deep', 0.55)}; }}
        QPushButton#plain {{ background: {self.mix('light', '#FFFFFF', 0.4)}; color: {self.strong};
                     border: 2px solid {self.soft_border}; }}
        QPushButton#plain:hover {{ background: {self.light}; }}
        """

    def ui_icons(self) -> Path:
        """Small themed SVGs (arrows, check mark) referenced by the stylesheets."""
        folder = CACHE_DIR / "ui" / self.key
        svgs = {
            "up.svg": f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6">'
                      f'<path d="M1 5 L5 1 L9 5" fill="none" stroke="{self.strong}" stroke-width="1.8" '
                      f'stroke-linecap="round" stroke-linejoin="round"/></svg>',
            "down.svg": f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6">'
                        f'<path d="M1 1 L5 5 L9 1" fill="none" stroke="{self.strong}" stroke-width="1.8" '
                        f'stroke-linecap="round" stroke-linejoin="round"/></svg>',
            "check.svg": f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">'
                         f'<path d="M2.5 6.5 L5 9 L9.5 3.5" fill="none" stroke="{self.button_text}" '
                         f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        }
        for name, svg in svgs.items():
            path = folder / name
            if not path.exists() or path.read_text() != svg:
                folder.mkdir(parents=True, exist_ok=True)
                path.write_text(svg)
        return folder


THEMES: dict[str, Theme] = {t.key: t for t in (
    Theme("sakura", "Sakura pink", main="#FF9EBB", deep="#E0708F", light="#FFE2EC", accent="#FF6F9C", text="#5A3D55"),
    Theme("mint", "Fresh mint", main="#86D9C0", deep="#3EA889", light="#DDF5EC", accent="#2FBF94", text="#2C4A42"),
    Theme("lavender", "Lavender", main="#BCA6F2", deep="#8B6CD8", light="#EDE6FD", accent="#9C7BEA", text="#43375E"),
    Theme("sky", "Sky blue", main="#90C8F2", deep="#4A93CF", light="#E1F0FC", accent="#4FA6EC", text="#2C4259"),
    Theme("peach", "Peach", main="#FFB48C", deep="#E07F52", light="#FFEBDF", accent="#FF8A57", text="#5A3D30"),
    Theme("sunny", "Sunny yellow", main="#FFD36E", deep="#D9A12A", light="#FFF4D6", accent="#FFB627", text="#574522"),
)}
DEFAULT_THEME = "sakura"


def get_theme(key: str) -> Theme:
    return THEMES.get(key) or THEMES[DEFAULT_THEME]

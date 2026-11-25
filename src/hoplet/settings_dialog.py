"""A small, friendly settings window."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, QTime, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QTimeEdit, QVBoxLayout,
)

from . import character_assets
from .paths import APP_ICON
from .settings import INTERVAL_CHOICES, SIZE_CHOICES, Settings
from .themes import THEMES, get_theme


def swatch(theme) -> QIcon:
    """Three little dots showing a theme's colors."""
    pix = QPixmap(46, 16)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    for i, color in enumerate((theme.main, theme.deep, theme.light)):
        p.setPen(QPen(QColor(theme.deep), 1.2))
        p.setBrush(QColor(color))
        p.drawEllipse(QRectF(1 + i * 15, 1, 14, 14))
    p.end()
    return QIcon(pix)


class SettingsDialog(QDialog):
    preview_requested = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hoplet Settings")
        self.setWindowIcon(QIcon(str(APP_ICON)))
        self.setMinimumWidth(400)

        self.title = QLabel(objectName="title")
        self.subtitle = QLabel(objectName="subtitle")

        # --- look
        self.name = QLineEdit(maxLength=24, placeholderText="Hoplet")
        self.name.setText(settings.character_name)
        self.character = QComboBox()
        for key, label in character_assets.GENDERS.items():
            self.character.addItem(label, key)
        self.theme = QComboBox()
        self.theme.setIconSize(QSize(46, 16))
        for theme in THEMES.values():
            self.theme.addItem(swatch(theme), theme.name, theme.key)
        self.size = QComboBox()
        for label, scale in SIZE_CHOICES.items():
            self.size.addItem(label, scale)
        self.preview = QLabel(objectName="preview")
        self.preview.setFixedSize(132, 162)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        look_box = QGroupBox("Look")
        look_form = QFormLayout()
        look_form.addRow("Name", self.name)
        look_form.addRow("Character", self.character)
        look_form.addRow("Color theme", self.theme)
        look_form.addRow("Size", self.size)
        look_row = QHBoxLayout(look_box)
        look_row.addLayout(look_form, 1)
        look_row.addWidget(self.preview)

        # --- reminders
        self.enabled = QCheckBox("Reminders enabled")
        self.interval = QComboBox()
        for minutes in INTERVAL_CHOICES:
            self.interval.addItem(f"Every {minutes} minutes", minutes)
        if settings.interval_minutes not in INTERVAL_CHOICES:   # custom value from JSON
            self.interval.addItem(f"Every {settings.interval_minutes} minutes", settings.interval_minutes)
        self.snooze = QSpinBox(minimum=1, maximum=60, suffix=" min")
        self.display = QSpinBox(minimum=10, maximum=300, singleStep=5, suffix=" sec")

        rem_box = QGroupBox("Reminders")
        form = QFormLayout(rem_box)
        form.addRow(self.enabled)
        form.addRow("Remind me", self.interval)
        form.addRow("Snooze for", self.snooze)
        form.addRow("Stay on screen", self.display)

        # --- working hours
        self.hours_box = QGroupBox("Only during working hours", checkable=True)
        self.start = QTimeEdit(displayFormat="HH:mm")
        self.end = QTimeEdit(displayFormat="HH:mm")
        hours = QHBoxLayout(self.hours_box)
        hours.addWidget(QLabel("From"))
        hours.addWidget(self.start)
        hours.addWidget(QLabel("to"))
        hours.addWidget(self.end)
        hours.addStretch()

        self.autostart = QCheckBox("Start automatically when I log in")

        # --- buttons
        preview = QPushButton("Preview now", objectName="plain")
        preview.setToolTip("Shows a visit with your saved settings")
        cancel = QPushButton("Cancel", objectName="plain")
        save = QPushButton("Save", objectName="save")
        save.setDefault(True)
        preview.clicked.connect(self.preview_requested)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addWidget(preview)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(look_box)
        layout.addWidget(rem_box)
        layout.addWidget(self.hours_box)
        layout.addWidget(self.autostart)
        layout.addSpacing(6)
        layout.addLayout(buttons)

        # --- load values
        self.character.setCurrentIndex(self.character.findData(settings.character))
        self.theme.setCurrentIndex(self.theme.findData(settings.theme))
        nearest = min(SIZE_CHOICES.values(), key=lambda s: abs(s - settings.character_scale))
        self.size.setCurrentIndex(self.size.findData(nearest))
        self.interval.setCurrentIndex(self.interval.findData(settings.interval_minutes))
        self.enabled.setChecked(settings.reminders_enabled)
        self.snooze.setValue(settings.snooze_minutes)
        self.display.setValue(settings.display_seconds)
        self.hours_box.setChecked(settings.working_hours_enabled)
        self.start.setTime(QTime.fromString(settings.work_start, "HH:mm"))
        self.end.setTime(QTime.fromString(settings.work_end, "HH:mm"))
        self.autostart.setChecked(settings.autostart)

        self.name.textChanged.connect(self._refresh_look)
        self.character.currentIndexChanged.connect(self._refresh_look)
        self.theme.currentIndexChanged.connect(self._refresh_look)
        self._refresh_look()

    def _refresh_look(self) -> None:
        """Live preview: restyle the window and redraw the character."""
        theme = get_theme(self.theme.currentData())
        gender = self.character.currentData()
        self.setStyleSheet(theme.dialog_qss())
        name = " ".join(self.name.text().split()) or "Hoplet"
        self.title.setText(f"{name} {'♡' if gender == 'girl' else '☆'}")
        self.subtitle.setText(f"How often should {name} come say hi?")
        self.preview.setPixmap(character_assets.preview(gender, theme, 150))

    def apply_to(self, settings: Settings) -> None:
        settings.character_name = self.name.text()
        settings.character = self.character.currentData()
        settings.theme = self.theme.currentData()
        settings.character_scale = float(self.size.currentData())
        settings.reminders_enabled = self.enabled.isChecked()
        settings.interval_minutes = int(self.interval.currentData())
        settings.snooze_minutes = self.snooze.value()
        settings.display_seconds = self.display.value()
        settings.working_hours_enabled = self.hours_box.isChecked()
        settings.work_start = self.start.time().toString("HH:mm")
        settings.work_end = self.end.time().toString("HH:mm")
        settings.autostart = self.autostart.isChecked()
        settings.validate()

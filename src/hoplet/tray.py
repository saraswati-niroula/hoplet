"""System tray icon (shown via the AppIndicator extension on Ubuntu GNOME)."""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon



class Tray(QObject):
    show_now = Signal()
    pause_toggled = Signal(bool)     # True = paused
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, status_provider, icon: QIcon, parent=None):
        super().__init__(parent)
        self._status_provider = status_provider
        self.icon = QSystemTrayIcon(icon, self)
        self.icon.setToolTip("Hoplet")

        menu = QMenu()
        self._status = QAction("…", menu, enabled=False)
        menu.addAction(self._status)
        menu.addSeparator()
        menu.addAction("Show reminder now", self.show_now.emit)
        self._pause = QAction("Pause reminders", menu, checkable=True)
        self._pause.toggled.connect(self.pause_toggled)
        menu.addAction(self._pause)
        menu.addAction("Settings…", self.settings_requested.emit)
        menu.addSeparator()
        menu.addAction("Quit", self.quit_requested.emit)
        self._menu = menu                    # keep a reference (Qt doesn't own it)
        self.icon.setContextMenu(menu)

        # AppIndicator doesn't reliably emit aboutToShow, so refresh periodically.
        self._refresh_timer = QTimer(self, interval=30_000)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start()

    @staticmethod
    def available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        self.refresh()
        self.icon.show()

    def set_icon(self, icon: QIcon) -> None:
        self.icon.setIcon(icon)

    def set_paused(self, paused: bool) -> None:
        self._pause.blockSignals(True)
        self._pause.setChecked(paused)
        self._pause.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        text = self._status_provider()
        self._status.setText(text)
        self.icon.setToolTip(f"Hoplet — {text}")

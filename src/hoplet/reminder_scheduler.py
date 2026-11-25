"""Decides *when* the companion should appear.

Uses wall-clock deadlines checked by a light polling QTimer instead of a single
long timer, so it behaves sensibly across suspend/resume and working hours:

* After a reminder (or "Okay"), the next one is `interval` minutes later.
* Snooze schedules one `snooze` minutes later.
* Outside working hours nothing fires; the first reminder of the day comes one
  interval after work starts (you haven't been sitting for an hour at 9:00).
* If the machine was asleep for a while, that counts as a break and the
  countdown restarts.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal

from .settings import Settings

log = logging.getLogger(__name__)

POLL_MS = 5_000
SLEEP_GAP = timedelta(minutes=3)   # a poll gap longer than this = machine was asleep


class ReminderScheduler(QObject):
    reminder_due = Signal()
    changed = Signal()             # next_due / paused state changed (for the tray)

    def __init__(self, settings: Settings, interval_override_s: int | None = None):
        super().__init__()
        self.settings = settings
        self._override = interval_override_s      # debug: seconds instead of minutes
        self.next_due: datetime | None = None
        self._busy = False                         # character currently on screen
        self._last_poll = datetime.now()
        self._timer = QTimer(self, interval=POLL_MS)
        self._timer.timeout.connect(self._poll)

    # ---------------------------------------------------------------- control
    def start(self) -> None:
        self._schedule(self._interval())
        self._timer.start()

    def trigger_now(self) -> None:
        """Make her appear right away (tray "Show reminder now")."""
        if not self._busy:
            self._fire()

    def reminder_finished(self, outcome: str) -> None:
        self._busy = False
        if outcome == "snoozed":
            self._schedule(timedelta(minutes=self.settings.snooze_minutes))
        else:
            self._schedule(self._interval())

    def apply_settings(self) -> None:
        """Called after the settings dialog was saved."""
        if self._busy:
            return
        interval = self._interval()
        now = datetime.now()
        # Re-enabled after a pause (deadline already passed), or the interval
        # got shorter: count from now.
        if self.next_due is None or self.next_due <= now or self.next_due - now > interval:
            self._schedule(interval)
        else:
            self.changed.emit()

    @property
    def paused(self) -> bool:
        return not self.settings.reminders_enabled

    def status_text(self) -> str:
        if self.paused:
            return "Reminders paused"
        if self._busy:
            return f"{self.settings.character_name} is here now!"
        if self.next_due is None:
            return "Waiting…"
        now = datetime.now()
        if not self.settings.in_working_hours(now):
            return f"Off duty until {self.settings.work_start}"
        return f"{self.settings.character_name} will visit at {self.next_due:%H:%M}"

    # -------------------------------------------------------------- internals
    def _interval(self) -> timedelta:
        if self._override:
            return timedelta(seconds=self._override)
        return timedelta(minutes=self.settings.interval_minutes)

    def _schedule(self, delay: timedelta) -> None:
        self.next_due = datetime.now() + delay
        log.debug("Next reminder at %s", self.next_due)
        self.changed.emit()

    def _poll(self) -> None:
        now = datetime.now()
        gap, self._last_poll = now - self._last_poll, now
        if self._busy or self.paused or self.next_due is None:
            return

        if gap > SLEEP_GAP:
            log.info("Woke up after %s; restarting the countdown", gap)
            self._schedule(self._interval())
            return

        if not self.settings.in_working_hours(now):
            work_start = self.settings.next_work_start(now)
            if self.next_due < work_start:
                self.next_due = work_start + self._interval()
                self.changed.emit()
            return

        if now >= self.next_due:
            self._fire()

    def _fire(self) -> None:
        self._busy = True
        self.changed.emit()
        self.reminder_due.emit()

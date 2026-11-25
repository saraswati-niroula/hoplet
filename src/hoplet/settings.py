"""User preferences, persisted as JSON in config/settings.json."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from datetime import datetime, time, timedelta
from pathlib import Path

from .paths import SETTINGS_FILE
from .themes import DEFAULT_THEME, THEMES

GENDERS = ("girl", "boy")

log = logging.getLogger(__name__)

INTERVAL_CHOICES = (30, 45, 60, 90)
SIZE_CHOICES = {"Small": 0.8, "Medium": 1.0, "Large": 1.25}


@dataclass
class Settings:
    reminders_enabled: bool = True
    interval_minutes: int = 60
    snooze_minutes: int = 5
    display_seconds: int = 40
    autostart: bool = True
    working_hours_enabled: bool = False
    work_start: str = "09:00"
    work_end: str = "18:00"
    character_scale: float = 1.0
    character: str = "girl"          # "girl" or "boy"
    character_name: str = "Hoplet"   # what your companion is called
    theme: str = "sakura"            # key in themes.THEMES

    # ------------------------------------------------------------------ io
    @classmethod
    def load(cls, path: Path = SETTINGS_FILE) -> "Settings":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            settings = cls()
            settings.save(path)
            return settings
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Could not read %s (%s); using defaults", path, exc)
            return cls()

        known = {f.name for f in fields(cls)}
        settings = cls(**{k: v for k, v in data.items() if k in known})
        settings.validate()
        return settings

    def save(self, path: Path = SETTINGS_FILE) -> None:
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)  # atomic: never leaves a half-written file

    def copy(self) -> "Settings":
        return Settings(**asdict(self))

    # ------------------------------------------------------------ validation
    def validate(self) -> None:
        self.reminders_enabled = bool(self.reminders_enabled)
        self.autostart = bool(self.autostart)
        self.working_hours_enabled = bool(self.working_hours_enabled)
        self.interval_minutes = _clamp_int(self.interval_minutes, 1, 24 * 60, 60)
        self.snooze_minutes = _clamp_int(self.snooze_minutes, 1, 120, 5)
        self.display_seconds = _clamp_int(self.display_seconds, 10, 300, 40)
        try:
            self.character_scale = min(2.0, max(0.5, float(self.character_scale)))
        except (TypeError, ValueError):
            self.character_scale = 1.0
        self.character_name = " ".join(str(self.character_name or "").split())[:24] or "Hoplet"
        if self.character not in GENDERS:
            self.character = "girl"
        if self.theme not in THEMES:
            self.theme = DEFAULT_THEME
        for attr, default in (("work_start", "09:00"), ("work_end", "18:00")):
            try:
                _parse_time(getattr(self, attr))
            except (TypeError, ValueError):
                setattr(self, attr, default)

    # --------------------------------------------------------- working hours
    @property
    def start_time(self) -> time:
        return _parse_time(self.work_start)

    @property
    def end_time(self) -> time:
        return _parse_time(self.work_end)

    def in_working_hours(self, now: datetime) -> bool:
        if not self.working_hours_enabled:
            return True
        start, end, t = self.start_time, self.end_time, now.time()
        if start == end:
            return True
        if start < end:
            return start <= t < end
        return t >= start or t < end  # overnight shift, e.g. 22:00-06:00

    def next_work_start(self, now: datetime) -> datetime:
        """The next moment working hours begin (strictly after `now`)."""
        candidate = datetime.combine(now.date(), self.start_time)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate


def _parse_time(value: str) -> time:
    hours, minutes = str(value).split(":")
    return time(int(hours), int(minutes))


def _clamp_int(value, lo: int, hi: int, default: int) -> int:
    try:
        return min(hi, max(lo, int(value)))
    except (TypeError, ValueError):
        return default

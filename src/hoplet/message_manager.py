"""Loads the character's lines and picks them at random.

The bundled assets/messages.json is used unless you create your own
~/.config/hoplet/messages.json (same format; any category
you include replaces the bundled one). Each category is a list of strings;
`{name}` is replaced with your companion's name and `{minutes}` (snooze
lines) with the snooze time.
"""
from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from .paths import DEFAULT_MESSAGES_FILE, USER_MESSAGES_FILE

log = logging.getLogger(__name__)

_DEFAULTS: dict[str, list[str]] = {
    "reminders": ["Time to stand up and stretch!"],
    "encouragements": ["Yay! Great job!"],
    "snooze": ["Okay~ I'll be back in {minutes} minutes!"],
    "goodbyes": ["Bye for now~"],
    "pats": ["Hehe~"],
}


class MessageManager:
    def __init__(self, path: Path | None = None):
        self._messages = {k: list(v) for k, v in _DEFAULTS.items()}
        self._last: dict[str, str] = {}
        self.name = "Hoplet"
        if path is None:
            self._load(DEFAULT_MESSAGES_FILE)
            if USER_MESSAGES_FILE.exists():
                self._load(USER_MESSAGES_FILE)
        else:
            self._load(path)

    def _load(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for category, lines in data.items():
                lines = [str(line) for line in lines if str(line).strip()]
                if lines:
                    self._messages[category] = lines
        except (OSError, json.JSONDecodeError, AttributeError, TypeError) as exc:
            log.warning("Could not load messages from %s (%s); using defaults", path, exc)

    def pick(self, category: str) -> str:
        """Random line from a category, avoiding an immediate repeat."""
        options = self._messages.get(category) or _DEFAULTS.get(category) or ["..."]
        if len(options) > 1 and category in self._last:
            options = [m for m in options if m != self._last[category]] or options
        choice = random.choice(options)
        self._last[category] = choice
        return self._fill(choice)

    def _fill(self, line: str, **values) -> str:
        values.setdefault("name", self.name)
        try:
            return line.format_map(_Blank(values))
        except (ValueError, IndexError, AttributeError):   # stray braces etc.
            return line

    def reminder(self) -> str:
        return self.pick("reminders")

    def encouragement(self) -> str:
        return self.pick("encouragements")

    def goodbye(self) -> str:
        return self.pick("goodbyes")

    def pat(self) -> str:
        return self.pick("pats")

    def snooze(self, minutes: int) -> str:
        options = self._messages.get("snooze") or _DEFAULTS["snooze"]
        if len(options) > 1 and "snooze" in self._last:
            options = [m for m in options if m != self._last["snooze"]] or options
        line = random.choice(options)
        self._last["snooze"] = line
        return self._fill(line, minutes=minutes)


class _Blank(dict):
    """Unknown {placeholders} are left as they are."""

    def __missing__(self, key):
        return "{" + key + "}"

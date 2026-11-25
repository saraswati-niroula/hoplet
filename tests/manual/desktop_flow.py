#!/usr/bin/env python3
"""Manual test: drives the real character window on your desktop through every
interaction (Okay, snooze, timeout, drag, pat, hover). Needs a graphical session;
keep your hands off the mouse for about a minute.

    python tests/manual/desktop_flow.py [screenshot_dir]
    TEST_CHARACTER=boy TEST_THEME=mint python tests/manual/desktop_flow.py

Runs each visit scenario with shortened timings and checks the outcome the
scheduler would receive. Optionally saves window grabs for visual checks.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from hoplet import character_assets  # noqa: E402
from hoplet.animation_manager import AnimationLibrary  # noqa: E402
from hoplet.themes import get_theme  # noqa: E402
from hoplet.character import CharacterWindow, Outcome, State  # noqa: E402
from hoplet.message_manager import MessageManager  # noqa: E402
from hoplet.settings import Settings  # noqa: E402

app = QApplication(sys.argv)
shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
settings = Settings(display_seconds=10, snooze_minutes=5)
theme = get_theme(os.environ.get("TEST_THEME", "sakura"))
gender = os.environ.get("TEST_CHARACTER", "girl")
char = CharacterWindow(AnimationLibrary(character_assets.character_dir(gender, theme)), theme,
                       MessageManager(), settings)
outcomes = []
char.finished.connect(outcomes.append)
failures = []


def wait(seconds):
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def wait_until(cond, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        wait(0.05)
    return False


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        failures.append(name)


def grab(name):
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
        char.grab().save(str(shots / f"{name}.png"))


def enter():
    outcomes.clear()
    t0 = time.monotonic()
    check("appear() accepted", char.appear("Stretch your shoulders!"))
    check("appear() rejected while visible", not char.appear("again"))
    grab("1_entering")
    ok = wait_until(lambda: char.bubble.isVisible() and char.state in (State.REMIND, State.IDLE), 8)
    check("hopped in and shows bubble", ok, f"({time.monotonic() - t0:.1f}s)")
    check("bubble has buttons", char.bubble.ok_button.isVisible() and char.bubble.snooze_button.isVisible())
    check("snooze label", char.bubble.snooze_button.text() == "Remind me in 5 minutes",
          repr(char.bubble.snooze_button.text()))
    geo = char.geometry()
    screen = char.screen().availableGeometry()
    check("on screen near bottom", screen.contains(geo.center()) and abs(geo.bottom() - screen.bottom()) <= 3,
          f"window={geo.getRect()} screen={screen.getRect()}")


def finish(expected, timeout=8):
    ok = wait_until(lambda: outcomes, timeout)
    check(f"outcome {expected}", ok and outcomes[0] == expected, str(outcomes))
    check("hidden afterwards", not char.isVisible() and char.state is State.HIDDEN)


# 1. Okay, let's go! -> HAPPY -> LEAVE
enter()
wait(1.0)
grab("2_remind")
xid = int(char.winId())
info = subprocess.run(["xwininfo", "-id", hex(xid), "-shape"], capture_output=True, text=True).stdout
attrs = subprocess.run(["xwininfo", "-id", hex(xid)], capture_output=True, text=True).stdout
check("override-redirect window", "Override Redirect State: yes" in attrs)
extent = [line.strip() for line in info.splitlines() if "Window shape extents" in line]
check("X shape mask applied (click-through)", bool(extent) and f"{char.width()}x{char.height()}+0+0" not in extent[0],
      extent[0] if extent else "no shape")
char.bubble.ok_button.click()
wait(0.3)
check("HAPPY after Okay", char.state is State.HAPPY, str(char.state))
check("encouragement shown without buttons", not char.bubble.ok_button.isVisible())
wait(0.4)
grab("3_happy")
finish(Outcome.ACKNOWLEDGED)

# 2. Snooze
enter()
QTest.mouseClick(char.bubble.snooze_button, Qt.MouseButton.LeftButton)   # real mouse event
wait(0.2)
check("lingers after snooze", char.state is not State.LEAVE and char.bubble.isVisible()
      and not char.bubble.snooze_button.isVisible(), str(char.state))
grab("4_snooze_lingering")
wait(char.SNOOZE_LINGER_SECONDS)
check("LEAVE after snooze linger", char.state is State.LEAVE, str(char.state))
finish(Outcome.SNOOZED)

# 3. Drag + pat, then timeout
enter()
start = char.pos()
sprite_pt = QPoint(char.width() // 2, char.height() - 80)
QTest.mousePress(char, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, sprite_pt)
for i in range(1, 11):
    # positions are window-local and the window follows the mouse, so convert
    # the desired global position into the window's current coordinates
    target_global = start + sprite_pt + QPoint(-15 * i, -6 * i)
    QTest.mouseMove(char, target_global - char.pos())
    wait(0.02)
QTest.mouseRelease(char, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + sprite_pt + QPoint(-150, -60) - char.pos())
wait(0.1)
moved = char.pos() - start
check("drag moves the character", abs(moved.x() + 150) <= 20 and abs(moved.y() + 60) <= 20, f"moved {moved.toTuple()}")
QTest.mouseClick(char, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, sprite_pt)
wait(0.15)
check("click = happy pat", char.state is State.HAPPY, str(char.state))
t0 = time.monotonic()
finish(Outcome.TIMED_OUT, timeout=20)
print(f"      timed out after ~{time.monotonic() - t0:.1f}s more (display_seconds=10)")

# 4. Mouse parked on her: she waits, but only up to the grace period
char.HOVER_GRACE_SECONDS = 5
char._cursor_over_me = lambda: True
enter()
t0 = time.monotonic()
finish(Outcome.TIMED_OUT, timeout=25)
elapsed = time.monotonic() - t0
check("hover delays leaving but is capped", 14 <= elapsed <= 19, f"left after {elapsed:.1f}s (10s + 5s grace)")

print("\nALL PASSED" if not failures else f"\nFAILED: {failures}")
sys.exit(1 if failures else 0)

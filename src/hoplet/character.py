"""The floating desktop character: a frameless, transparent, always-on-top window.

Behaviour is a small state machine:

    HIDDEN -> ENTER (hops in) -> REMIND (waves, bubble with buttons)
           -> IDLE  (waits; occasionally WALKs a few hops)
           -> HAPPY (on "Okay") -> LEAVE (hops off-screen) -> HIDDEN

Sprite frames give the pose; motion (hop arcs, squash & stretch, breathing,
crossfades between clips) is added procedurally on top so that even a few
frames look smooth.
"""
from __future__ import annotations

import logging
import math
import random
from collections import deque
from enum import Enum, auto

from PySide6.QtCore import QElapsedTimer, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QCursor, QGuiApplication, QPainter, QPainterPath, QPen,
    QPixmap, QRegion, QTransform,
)
from PySide6.QtWidgets import QLabel, QMenu, QPushButton, QVBoxLayout, QWidget

from .animation_manager import (
    ENTER, HAPPY, IDLE, LEAVE, REMIND, WALK, AnimationLibrary, AnimationPlayer,
)
from .message_manager import MessageManager
from .settings import Settings
from .themes import Theme

log = logging.getLogger(__name__)

NO_PEN = QPen(Qt.PenStyle.NoPen)


class State(Enum):
    HIDDEN = auto()
    ENTER = auto()
    IDLE = auto()
    WALK = auto()
    REMIND = auto()
    HAPPY = auto()
    LEAVE = auto()


class Outcome:
    """Why a visit ended; passed to the scheduler."""
    ACKNOWLEDGED = "acknowledged"
    SNOOZED = "snoozed"
    TIMED_OUT = "timed_out"
    DISMISSED = "dismissed"


# ====================================================================== bubble
class SpeechBubble(QWidget):
    ok_clicked = Signal()
    snooze_clicked = Signal()

    WIDTH = 270
    TAIL = 14
    RADIUS = 18

    def __init__(self, parent: QWidget, theme: Theme):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)
        self.tail_x = self.WIDTH / 2

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14 + self.TAIL)
        layout.setSpacing(7)

        self.label = QLabel(objectName="text", wordWrap=True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.ok_button = QPushButton("Okay, let's go!", objectName="ok")
        self.snooze_button = QPushButton(objectName="snooze")
        for button in (self.ok_button, self.snooze_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            layout.addWidget(button)
        self.ok_button.clicked.connect(self.ok_clicked)
        self.snooze_button.clicked.connect(self.snooze_clicked)
        self.set_theme(theme)
        self.hide()

    def set_theme(self, theme: Theme) -> None:
        self.setStyleSheet(theme.bubble_qss())
        self._fill = QColor(theme.bubble_bg)
        self._border = QColor(theme.main)
        shadow = QColor(theme.text)
        shadow.setAlpha(35)
        self._shadow = shadow
        self.update()

    def show_reminder(self, text: str, snooze_minutes: int) -> None:
        unit = "minute" if snooze_minutes == 1 else "minutes"
        self.snooze_button.setText(f"Remind me in {snooze_minutes} {unit}")
        self._show(text, buttons=True)

    def show_text(self, text: str) -> None:
        self._show(text, buttons=False)

    def _show(self, text: str, buttons: bool) -> None:
        self.label.setText(text)
        self.ok_button.setVisible(buttons)
        self.snooze_button.setVisible(buttons)
        self.layout().activate()
        self.setFixedHeight(self.layout().totalHeightForWidth(self.WIDTH))
        self.show()
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(self.rect()).adjusted(3, 2, -3, -2 - self.TAIL)

        path = QPainterPath()
        path.addRoundedRect(body, self.RADIUS, self.RADIUS)
        tail = QPainterPath(QPointF(self.tail_x - 11, body.bottom() - 1))
        tail.quadTo(QPointF(self.tail_x - 2, body.bottom() + 4),
                    QPointF(self.tail_x + 2, body.bottom() + self.TAIL))
        tail.quadTo(QPointF(self.tail_x + 6, body.bottom() + 3),
                    QPointF(self.tail_x + 12, body.bottom() - 1))
        tail.closeSubpath()
        path = path.united(tail)

        p.setPen(NO_PEN)
        p.setBrush(self._shadow)                      # soft shadow
        p.drawPath(path.translated(0, 2))
        p.setBrush(self._fill)
        p.setPen(QPen(self._border, 2.5))
        p.drawPath(path)
        p.end()


# =================================================================== character
class CharacterWindow(QWidget):
    finished = Signal(str)            # Outcome value, emitted after she's gone
    settings_requested = Signal()
    quit_requested = Signal()

    BUBBLE_AREA = 200    # space above her head reserved for the bubble
    HEADROOM = 50        # how high she may hop above her standing position
    BOTTOM_PAD = 2
    HOP_HEIGHT_TRAVEL = 42
    HOP_LENGTH = 115     # px per hop when travelling
    REMIND_WAVE_SECONDS = 4.0
    HAPPY_SECONDS = 2.6
    SNOOZE_LINGER_SECONDS = 5.0
    FADE_SECONDS = 0.16
    HOVER_GRACE_SECONDS = 20

    def __init__(self, library: AnimationLibrary, theme: Theme, messages: MessageManager,
                 settings: Settings):
        super().__init__(None)
        self.messages = messages
        self.settings = settings
        self._pending_look: tuple[AnimationLibrary, Theme] | None = None

        # --- window setup: frameless, transparent, above everything, no focus.
        # X11BypassWindowManagerHint (override-redirect) lets us place the
        # window partly off-screen for the hop-in and keeps it above normal
        # windows on GNOME/XWayland without ever stealing keyboard focus.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.X11BypassWindowManagerHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_X11DoNotAcceptFocus)
        self.setWindowTitle("Hoplet")

        self.bubble = SpeechBubble(self, theme)
        self.bubble.ok_clicked.connect(self._on_ok)
        self.bubble.snooze_clicked.connect(self._on_snooze)

        # --- animation state
        self.state = State.HIDDEN
        self._clock = QElapsedTimer()
        self._clock.start()
        self.t = 0.0
        self._last_t = 0.0
        self._state_t = 0.0
        self._tick_timer = QTimer(self, interval=16, timerType=Qt.TimerType.PreciseTimer)
        self._tick_timer.timeout.connect(self._tick)

        self._x = 0.0
        self._y = 0.0
        self._y_off = 0.0
        self._squash = 0.0
        self._direction = -1
        self._hop: dict | None = None
        self._hop_queue: deque[float] = deque()
        self._hop_clip = ENTER
        self._hop_height = 0.0
        self._hop_done = None
        self._fade_from: QPixmap | None = None
        self._fade_t0 = 0.0
        self._mirror_cache: dict[int, QPixmap] = {}

        self._visit = 0                # invalidates stale delayed callbacks
        self._next_wander = 0.0
        self._display_deadline = 0.0
        self._hard_deadline = 0.0
        self._reminder_active = False
        self._hovered = False
        self._press_pos = None
        self._drag_offset = None
        self._dragging = False

        self._set_library(library)

    # ================================================================ public
    @property
    def is_busy(self) -> bool:
        return self.state is not State.HIDDEN

    def appear(self, message: str) -> bool:
        """Hop onto the screen and show `message`. False if already visible."""
        if self.is_busy:
            return False
        if self._pending_look:
            library, theme = self._pending_look
            self._pending_look = None
            self._set_library(library)
            self.bubble.set_theme(theme)

        self._visit += 1
        avail = self._screen_geometry()
        self._y = avail.bottom() + 1 - self.height()
        self._x = float(avail.right() + 10)           # start just off the right edge
        margin = 30 + random.randint(0, 140)
        target = avail.right() - margin - self.width() + (self.width() - self.sprite_w) / 2

        self.bubble.hide()
        self._update_mask()
        self.move(round(self._x), round(self._y))
        self._message = message
        self._set_state(State.ENTER)
        self.show()
        self.raise_()
        self._last_t = self._now()
        self._tick_timer.start()
        self._hop_to(target, ENTER, self.HOP_HEIGHT_TRAVEL, self._on_entered)
        return True

    def leave_now(self) -> None:
        """Politely leave (used by the tray / context menu)."""
        if self.state in (State.HIDDEN, State.LEAVE):
            return
        self._leave(Outcome.DISMISSED, self.messages.goodbye())

    def set_look(self, library: AnimationLibrary, theme: Theme) -> None:
        """Swap character art and colors. If she's on screen right now, the
        change is applied on her next visit (no mid-visit costume change)."""
        if self.is_busy:
            self._pending_look = (library, theme)
        else:
            self._set_library(library)
            self.bubble.set_theme(theme)

    # ========================================================== state logic
    def _on_entered(self) -> None:
        self._set_state(State.REMIND)
        self._reminder_active = True
        self.bubble.show_reminder(self._message, self.settings.snooze_minutes)
        self._layout_bubble()
        self._display_deadline = self.t + self.settings.display_seconds
        # She waits while you're pointing at her, but never forever (e.g. a
        # mouse left resting where she happened to land).
        self._hard_deadline = self._display_deadline + self.HOVER_GRACE_SECONDS
        self._schedule_wander()

    def _on_ok(self) -> None:
        if not self._reminder_active:
            return
        self._reminder_active = False
        self._cancel_hops()
        self.bubble.show_text(self.messages.encouragement())
        self._layout_bubble()
        self._set_state(State.HAPPY)
        self._hop_to(self._x, HAPPY, 26, None, count=2)
        self._later(self.HAPPY_SECONDS, lambda: self._leave(Outcome.ACKNOWLEDGED, None))

    def _on_snooze(self) -> None:
        if not self._reminder_active:
            return
        # Linger a moment so the "see you in N minutes" line can be read
        # before she hops away (it stays in the bubble while she leaves).
        self._reminder_active = False
        self._cancel_hops()
        text = self.messages.snooze(self.settings.snooze_minutes)
        self.bubble.show_text(text)
        self._layout_bubble()
        self._set_state(State.IDLE)
        self._next_wander = self.t + self.SNOOZE_LINGER_SECONDS + 1   # no wandering off mid-goodbye
        self._later(self.SNOOZE_LINGER_SECONDS, lambda: self._leave(Outcome.SNOOZED, text))

    def _on_display_timeout(self) -> None:
        self._leave(Outcome.TIMED_OUT, self.messages.goodbye())

    def _leave(self, outcome: str, text: str | None) -> None:
        if self.state is State.LEAVE:
            return
        self._reminder_active = False
        self._cancel_hops()
        self._outcome = outcome
        if text:
            self.bubble.show_text(text)
            self._layout_bubble()
        else:
            self.bubble.hide()
            self._update_mask()

        avail = self._screen_geometry()
        centre = self._x + self.width() / 2
        if centre > avail.center().x():
            target = avail.right() + 20 + (self.width() - self.sprite_w) / 2
        else:
            target = avail.left() - self.width() - 20 + (self.width() - self.sprite_w) / 2
        self._set_state(State.LEAVE)
        self._hop_to(target, LEAVE, 38, self._on_left, hop_length=self.HOP_LENGTH * 1.15)

    def _on_left(self) -> None:
        self._tick_timer.stop()
        self.bubble.hide()
        self.hide()
        self._visit += 1
        self._set_state(State.HIDDEN)
        log.debug("Visit finished: %s", self._outcome)
        self.finished.emit(self._outcome)

    # -------------------------------------------------------------- wander
    def _schedule_wander(self) -> None:
        self._next_wander = self.t + random.uniform(7.0, 13.0)

    def _maybe_wander(self) -> None:
        if (self.state not in (State.IDLE, State.REMIND) or self._hovered
                or self._dragging or self.t < self._next_wander):
            return
        avail = self._screen_geometry()
        lo = avail.left() + 10
        hi = avail.right() - self.width() - 10
        target = self._x + random.choice((-1, 1)) * random.uniform(50, 170)
        target = min(hi, max(lo, target))
        if abs(target - self._x) < 30:
            self._schedule_wander()
            return
        self._set_state(State.WALK)
        self._hop_to(target, WALK, 12, self._end_walk, hop_length=60)

    def _end_walk(self) -> None:
        self._set_state(State.IDLE)
        self._schedule_wander()

    def _pat(self) -> None:
        """Clicked (not dragged) while hanging around: a happy little hop."""
        if self.state not in (State.IDLE, State.REMIND):
            return
        self._set_state(State.HAPPY)
        self._hop_to(self._x, HAPPY, 20, self._end_walk, count=1)

    # ============================================================ animation
    def _set_state(self, state: State) -> None:
        self.state = state
        self._state_t = self.t
        clip = {
            State.ENTER: ENTER, State.IDLE: IDLE, State.WALK: WALK,
            State.REMIND: REMIND, State.HAPPY: HAPPY, State.LEAVE: LEAVE,
        }.get(state, IDLE)
        self._play(clip)

    def _play(self, clip: str, restart: bool = False) -> None:
        previous = self.player.frame if self.isVisible() else None
        if self.player.play(clip, restart) and previous is not None:
            self._fade_from, self._fade_t0 = previous, self.t   # crossfade

    def _hop_to(self, target_x: float, clip: str, height: float, on_done,
                count: int | None = None, hop_length: float | None = None) -> None:
        distance = target_x - self._x
        if count is None:
            count = max(1, round(abs(distance) / (hop_length or self.HOP_LENGTH)))
        self._hop_queue = deque(self._x + distance * (i + 1) / count for i in range(count))
        self._hop_clip, self._hop_height, self._hop_done = clip, height, on_done
        self._start_next_hop()

    def _start_next_hop(self) -> None:
        if not self._hop_queue:
            self._hop = None
            done, self._hop_done = self._hop_done, None
            if done:
                done()
            return
        x1 = self._hop_queue.popleft()
        duration = self.library.get(self._hop_clip).duration or 0.6
        if self._hop_clip == HAPPY:
            duration = 0.55
        self._hop = {"x0": self._x, "x1": x1, "t0": self.t, "dur": duration}
        if abs(x1 - self._x) > 1:
            self._direction = 1 if x1 > self._x else -1
        self._play(self._hop_clip, restart=self._hop_clip in (ENTER, LEAVE))

    def _cancel_hops(self) -> None:
        self._hop, self._hop_done = None, None
        self._hop_queue.clear()
        self._y_off = self._squash = 0.0

    def _update_hop(self) -> None:
        hop = self._hop
        p = (self.t - hop["t0"]) / hop["dur"]
        if p >= 1.0:
            self._x, self._y_off, self._squash = hop["x1"], 0.0, 0.0
            self._start_next_hop()
            return
        # 0-12 %: crouch on the ground, 12-88 %: in the air, 88-100 %: landing
        air = min(1.0, max(0.0, (p - 0.12) / 0.76))
        eased = air * air * (3 - 2 * air)
        self._x = hop["x0"] + (hop["x1"] - hop["x0"]) * eased
        self._y_off = -self._hop_height * math.sin(math.pi * air)
        if p < 0.12:
            self._squash = 0.11 * math.sin(math.pi * p / 0.12)
        elif p > 0.88:
            self._squash = 0.11 * math.sin(math.pi * (p - 0.88) / 0.12)
        else:
            self._squash = -0.06 * math.sin(math.pi * air)       # stretch

    def _tick(self) -> None:
        self.t = self._now()
        dt = min(0.1, self.t - self._last_t)
        self._last_t = self.t
        self.player.update(dt)

        if self._hop is not None:
            self._update_hop()
        if self.state is State.REMIND and self.t - self._state_t > self.REMIND_WAVE_SECONDS:
            self._set_state(State.IDLE)
        self._hovered = self._cursor_over_me()
        if self._reminder_active and self.t >= self._display_deadline:
            if (self._hovered or self._dragging) and self.t < self._hard_deadline:
                self._display_deadline = self.t + 3        # wait while you aim for a button
            else:
                self._on_display_timeout()
        self._maybe_wander()

        if not self._dragging and self.isVisible():
            pos = (round(self._x), round(self._y))
            if pos != self.pos().toTuple():
                self.move(*pos)

        # 60 fps while hopping or crossfading, 30 fps for gentle idle motion.
        fast = self._hop is not None or self._fade_from is not None or self._dragging
        interval = 16 if fast else 33
        if self._tick_timer.interval() != interval:
            self._tick_timer.setInterval(interval)
        # Repaint only the sprite area; the bubble repaints itself on change.
        self.update(self._sprite_area)

    # ============================================================== painting
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        sx = 1.0 + self._squash * 0.8
        sy = 1.0 - self._squash
        if self._hop is None and self.state in (State.IDLE, State.REMIND):
            breathe = math.sin(2 * math.pi * self.t / 2.6)
            sy *= 1.0 + 0.012 * breathe
            sx *= 1.0 - 0.006 * breathe

        p.translate(self.width() / 2, self.height() - self.BOTTOM_PAD + self._y_off)
        p.scale(sx, sy)

        fade = 1.0
        if self._fade_from is not None:
            fade = (self.t - self._fade_t0) / self.FADE_SECONDS
            if fade >= 1.0:
                self._fade_from, fade = None, 1.0
            else:
                p.setOpacity(1.0 - fade)
                self._draw_sprite(p, self._fade_from)
        p.setOpacity(fade)
        self._draw_sprite(p, self.player.frame)
        p.end()

    def _draw_sprite(self, p: QPainter, pixmap: QPixmap) -> None:
        if self._should_mirror():
            key = pixmap.cacheKey()
            if key not in self._mirror_cache:
                self._mirror_cache[key] = pixmap.transformed(QTransform().scale(-1, 1))
            pixmap = self._mirror_cache[key]
        p.drawPixmap(QPointF(-pixmap.width() / 2, -pixmap.height()), pixmap)

    def _should_mirror(self) -> bool:
        facing = self.library.facing
        if facing == "right":
            return self._direction < 0
        if facing == "left":
            return self._direction > 0
        return False

    # =============================================================== layout
    def _set_library(self, library: AnimationLibrary) -> None:
        self.library = library
        self.player = AnimationPlayer(library)
        self._mirror_cache.clear()
        self._fade_from = None
        self.sprite_w, self.sprite_h = library.frame_size
        width = max(SpeechBubble.WIDTH + 16, self.sprite_w + 40)
        height = self.BUBBLE_AREA + self.sprite_h + self.BOTTOM_PAD
        self.setFixedSize(width, height)
        self._layout_bubble()

    def _layout_bubble(self) -> None:
        x = (self.width() - self.bubble.width()) // 2
        head_top = self.height() - self.BOTTOM_PAD - self.sprite_h
        y = max(0, head_top + 18 - self.bubble.height())   # tail just touches her head
        self.bubble.move(x, y)
        self.bubble.tail_x = self.width() / 2 - x
        self._update_mask()

    def _update_mask(self) -> None:
        """Only the character and the bubble receive the mouse; everything
        else in this window's rectangle is click-through (X11 shape mask)."""
        pad = 14
        sprite = QRect(
            round(self.width() / 2 - self.sprite_w / 2) - pad,
            self.height() - self.BOTTOM_PAD - self.sprite_h - self.HEADROOM,
            self.sprite_w + 2 * pad,
            self.sprite_h + self.HEADROOM + self.BOTTOM_PAD,
        )
        self._sprite_area = sprite
        region = QRegion(sprite)
        if self.bubble.isVisible():
            region = region.united(QRegion(self.bubble.geometry()))
        self.setMask(region)

    def _screen_geometry(self) -> QRect:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    # ================================================================ input
    def _cursor_over_me(self) -> bool:
        # Polled from the real cursor position: enter/leave events can be
        # missed when the window moves under a stationary pointer.
        local = self.mapFromGlobal(QCursor.pos())
        return self.isVisible() and self.mask().contains(local)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event) -> None:
        if self._press_pos is None:
            return
        pos = event.globalPosition().toPoint()
        if not self._dragging:
            if (pos - self._press_pos).manhattanLength() < 5:
                return
            if self.state in (State.ENTER, State.LEAVE, State.HIDDEN):
                return            # no grabbing her mid-entrance/exit
            if self.state is State.WALK:
                self._cancel_hops()
                self._set_state(State.IDLE)
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        top_left = pos - self._drag_offset
        self._x, self._y = float(top_left.x()), float(top_left.y())
        self.move(top_left)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._dragging:
            self._dragging = False
            self.unsetCursor()
            self._schedule_wander()
        elif self._press_pos is not None:
            self._pat()
        self._press_pos = None

    def _show_menu(self, pos) -> None:
        menu = QMenu(self)
        if self._reminder_active:
            menu.addAction("Okay, let's go!", self._on_ok)
            menu.addAction(f"Remind me in {self.settings.snooze_minutes} min", self._on_snooze)
            menu.addSeparator()
        menu.addAction("Bye for now", self.leave_now)
        menu.addAction("Settings…", self.settings_requested.emit)
        menu.addSeparator()
        menu.addAction("Quit", self.quit_requested.emit)
        menu.exec(pos)

    # ============================================================== helpers
    def _now(self) -> float:
        return self._clock.elapsed() / 1000.0

    def _later(self, seconds: float, fn) -> None:
        """Run `fn` after a delay unless the visit has ended in the meantime."""
        visit = self._visit
        QTimer.singleShot(round(seconds * 1000), lambda: fn() if visit == self._visit else None)

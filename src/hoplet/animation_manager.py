"""Loads character animations from disk and plays them back.

Animations are described by <character folder>/animations.json. Each entry is
either a folder of individual frames or a single sprite sheet:

    "idle": {"frames": "idle/*.png", "fps": 8, "loop": true}
    "walk": {"sheet": "walk.png", "frame_width": 256, "frame_height": 320,
             "count": 8, "fps": 12}

All frames are scaled so they are `display_height` pixels tall (times the
user's size setting). An animation that is missing falls back to "idle", so
you can add new art one animation at a time.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap

log = logging.getLogger(__name__)

# Animation names the character logic uses. More can be added freely.
IDLE, ENTER, WALK, REMIND, HAPPY, LEAVE = "idle", "enter", "walk", "remind", "happy", "leave"
REQUIRED = (IDLE, ENTER, WALK, REMIND, HAPPY, LEAVE)


@dataclass
class AnimationClip:
    name: str
    frames: list[QPixmap]
    fps: float = 8.0
    loop: bool = True

    @property
    def duration(self) -> float:
        return len(self.frames) / self.fps if self.fps > 0 else 0.0


class AnimationLibrary:
    """All clips for one character, already scaled to display size."""

    def __init__(self, directory: Path, scale: float = 1.0):
        self.directory = directory
        self.clips: dict[str, AnimationClip] = {}
        self.facing = "front"   # "front", "left" or "right" — used for mirroring
        self._load(scale)

    # ---------------------------------------------------------------- public
    def get(self, name: str) -> AnimationClip:
        return self.clips.get(name) or self.clips[IDLE]

    @property
    def frame_size(self) -> tuple[int, int]:
        """Largest frame size across all clips (so nothing gets cropped)."""
        w = max(f.width() for c in self.clips.values() for f in c.frames)
        h = max(f.height() for c in self.clips.values() for f in c.frames)
        return w, h

    # --------------------------------------------------------------- loading
    def _load(self, scale: float) -> None:
        manifest_path = self.directory / "animations.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("No usable %s (%s)", manifest_path, exc)
            manifest = {}

        self.facing = manifest.get("facing", "front")
        target_h = max(16, round(float(manifest.get("display_height", 210)) * scale))

        for name, spec in manifest.get("animations", {}).items():
            try:
                frames = self._load_frames(spec)
            except Exception as exc:  # bad asset must never crash the companion
                log.warning("Animation %r failed to load: %s", name, exc)
                continue
            if not frames:
                log.warning("Animation %r has no frames; it will fall back to idle", name)
                continue
            frames = [self._scale(f, target_h) for f in frames]
            self.clips[name] = AnimationClip(
                name, frames, float(spec.get("fps", 8)), bool(spec.get("loop", True)))

        if IDLE not in self.clips:
            log.error("No idle animation found in %s", self.directory)
            self.clips[IDLE] = AnimationClip(IDLE, [_emergency_frame(target_h)], 1.0)

        missing = [n for n in REQUIRED if n not in self.clips]
        if missing:
            log.info("Using idle for missing animations: %s", ", ".join(missing))

    def _load_frames(self, spec: dict) -> list[QPixmap]:
        if "frames" in spec:
            pattern = spec["frames"]
            paths = sorted(self.directory.glob(pattern)) if isinstance(pattern, str) \
                else [self.directory / p for p in pattern]
            frames = [QPixmap(str(p)) for p in paths]
            return [f for f in frames if not f.isNull()]

        if "sheet" in spec:
            sheet = QPixmap(str(self.directory / spec["sheet"]))
            if sheet.isNull():
                raise FileNotFoundError(spec["sheet"])
            fw, fh = int(spec["frame_width"]), int(spec["frame_height"])
            cols = int(spec.get("columns", max(1, sheet.width() // fw)))
            rows = max(1, sheet.height() // fh)
            count = int(spec.get("count", cols * rows))
            return [sheet.copy((i % cols) * fw, (i // cols) * fh, fw, fh) for i in range(count)]

        raise ValueError("animation needs either 'frames' or 'sheet'")

    @staticmethod
    def _scale(pixmap: QPixmap, height: int) -> QPixmap:
        if pixmap.height() == height:
            return pixmap
        return pixmap.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)


class AnimationPlayer:
    """Tracks the current clip and frame. Advance it with `update(dt)`."""

    def __init__(self, library: AnimationLibrary):
        self.library = library
        self.clip = library.get(IDLE)
        self.time = 0.0
        self.finished = False

    @property
    def name(self) -> str:
        return self.clip.name

    def play(self, name: str, restart: bool = False) -> bool:
        """Switch clip. Returns True if the clip actually changed."""
        clip = self.library.get(name)
        if clip is self.clip and not restart:
            return False
        changed = clip is not self.clip
        self.clip, self.time, self.finished = clip, 0.0, False
        return changed

    def update(self, dt: float) -> None:
        self.time += dt
        if not self.clip.loop and self.time >= self.clip.duration:
            self.time, self.finished = self.clip.duration, True

    @property
    def frame(self) -> QPixmap:
        frames = self.clip.frames
        index = int(self.time * self.clip.fps)
        index = index % len(frames) if self.clip.loop else min(index, len(frames) - 1)
        return frames[index]


def _emergency_frame(height: int) -> QPixmap:
    """A pink blob, used only if every asset is missing."""
    pix = QPixmap(round(height * 0.8), height)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#FF9EBB"))
    p.setPen(QColor("#E0708F"))
    p.drawEllipse(QRectF(4, height * 0.25, pix.width() - 8, height * 0.73))
    p.end()
    return pix

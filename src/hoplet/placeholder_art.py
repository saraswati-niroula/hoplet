"""Procedurally drawn placeholder characters (a chibi girl and boy).

`generate(out_dir, gender, theme)` writes a complete character folder —
animations.json + PNG frames + icon.png — in exactly the format custom art
uses, so the rest of the app can't tell the difference.
"""
from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QRadialGradient

from .themes import Theme

VERSION = 2          # bump when the drawing changes, so cached frames are redrawn
GENDERS = {"girl": "Girl", "boy": "Boy"}

W, H = 240, 300      # canvas size of every frame
CX = W / 2

SKIN = QColor("#FFE7D6")
SKIN_LINE = QColor("#E9B29B")
HAIR = QColor("#7B4A3A")
HAIR_HI = QColor(255, 220, 200, 90)
HAIR_LINE = QColor("#55302A")
EYE = QColor("#3E2A50")
IRIS = QColor("#8A68C9")
BLUSH = QColor(255, 125, 155, 100)
MOUTH = QColor("#C4485F")
TONGUE = QColor("#FF9AA8")
WHITE = QColor("#FFFFFF")
NO_PEN = QPen(Qt.PenStyle.NoPen)
NO_BRUSH = QBrush(Qt.BrushStyle.NoBrush)


@dataclass
class Pose:
    body_dy: float = 0.0     # whole upper body offset (px, + = down)
    arm_l: float = 16.0      # degrees from hanging straight down, outward +
    arm_r: float = 16.0
    leg_l: float = 0.0       # foot lift in px
    leg_r: float = 0.0
    eyes: str = "open"       # open | half | closed | happy
    mouth: str = "smile"     # smile | open | o | grin
    hair: float = 0.0        # hair sway in degrees
    sparkle: float = -1.0    # 0..1 phase, -1 = no sparkles
    look: float = 0.0        # pupil highlight shift


class Look:
    """Gender + theme colors for one character."""

    def __init__(self, gender: str, theme: Theme):
        self.gender = gender if gender in GENDERS else "girl"
        self.outfit = theme.c("main")
        self.outfit_line = theme.c("deep")
        self.outfit_light = theme.c("light")
        self.accent = theme.c("accent")
        self.shorts = QColor(theme.mix("deep", "#5A4A6A", 0.35))
        self.shoe = theme.c("deep").darker(135)


# ----------------------------------------------------------------- drawing
def pen(color: QColor, width: float) -> QPen:
    p = QPen(color, width)
    p.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return p


def ellipse(p: QPainter, cx, cy, w, h, fill, line=None, lw=2.5):
    p.setBrush(fill)
    p.setPen(pen(line, lw) if line is not None else NO_PEN)
    p.drawEllipse(QRectF(cx - w / 2, cy - h / 2, w, h))


def draw_arm(p: QPainter, look: Look, side: int, angle: float, dy: float):
    sx, sy = CX + side * 25, 184 + dy
    a = math.radians(angle)
    ex, ey = sx + side * math.sin(a) * 40, sy + math.cos(a) * 40
    p.setBrush(NO_BRUSH)
    p.setPen(pen(SKIN_LINE, 14))
    p.drawLine(QPointF(sx, sy), QPointF(ex, ey))
    p.setPen(pen(SKIN, 9.5))
    p.drawLine(QPointF(sx, sy), QPointF(ex, ey))
    ellipse(p, ex, ey, 14, 14, SKIN, SKIN_LINE, 2.2)
    if look.gender == "girl":
        ellipse(p, sx, sy - 1, 24, 22, look.outfit, look.outfit_line, 2.5)      # puffy sleeve
    else:
        ellipse(p, sx, sy, 22, 20, look.outfit, look.outfit_line, 2.5)          # t-shirt sleeve


def draw_eye(p: QPainter, look: Look, x: float, y: float, kind: str, shift: float):
    if kind in ("open", "half"):
        p.save()
        if kind == "half":
            p.setClipRect(QRectF(x - 20, y - 2, 40, 30))
        ellipse(p, x, y, 25, 31, EYE)
        grad = QRadialGradient(QPointF(x, y + 8), 12)
        grad.setColorAt(0, IRIS.lighter(130))
        grad.setColorAt(1, QColor(IRIS.red(), IRIS.green(), IRIS.blue(), 0))
        ellipse(p, x, y + 6, 20, 18, QBrush(grad))
        ellipse(p, x - 4 + shift, y - 7, 10, 11, WHITE)
        ellipse(p, x + 5 + shift, y + 7, 5, 5, QColor(255, 255, 255, 220))
        p.restore()
        p.setBrush(NO_BRUSH)
        p.setPen(pen(EYE, 3.5))
        if kind == "half":
            p.drawLine(QPointF(x - 13, y - 2), QPointF(x + 13, y - 2))
        else:
            p.drawArc(QRectF(x - 14, y - 17, 28, 26), 25 * 16, 130 * 16)
            if look.gender == "girl":            # tiny lash flick at the outer corner
                side = 1 if x > CX else -1
                p.drawLine(QPointF(x + side * 12, y - 9), QPointF(x + side * 17, y - 13))
    elif kind == "closed":
        p.setBrush(NO_BRUSH)
        p.setPen(pen(EYE, 3.5))
        p.drawArc(QRectF(x - 12, y - 8, 24, 16), 200 * 16, 140 * 16)
    elif kind == "happy":
        p.setBrush(NO_BRUSH)
        p.setPen(pen(EYE, 4))
        p.drawArc(QRectF(x - 12, y - 4, 24, 20), 25 * 16, 130 * 16)


def draw_mouth(p: QPainter, kind: str, dy: float):
    x, y = CX, 158 + dy
    if kind == "smile":
        p.setBrush(NO_BRUSH)
        p.setPen(pen(MOUTH, 2.6))
        p.drawArc(QRectF(x - 7, y - 6, 14, 10), 200 * 16, 140 * 16)
    elif kind == "open":
        ellipse(p, x, y, 13, 10, MOUTH)
        ellipse(p, x, y + 2.5, 8, 4, TONGUE)
    elif kind == "o":
        ellipse(p, x, y, 8, 9, MOUTH)
    elif kind == "grin":
        path = QPainterPath(QPointF(x - 10, y - 4))
        path.quadTo(QPointF(x, y + 14), QPointF(x + 10, y - 4))
        path.closeSubpath()
        p.setPen(NO_PEN)
        p.setBrush(MOUTH)
        p.drawPath(path)
        ellipse(p, x, y + 3, 9, 5, TONGUE)


def star(p: QPainter, x: float, y: float, r: float, color: QColor):
    if r <= 0.5:
        return
    path = QPainterPath(QPointF(x, y - r))
    for px, py in ((x + r, y), (x, y + r), (x - r, y), (x, y - r)):
        path.quadTo(QPointF(x, y), QPointF(px, py))
    p.setPen(NO_PEN)
    p.setBrush(color)
    p.drawPath(path)


def draw_bow(p: QPainter, color: QColor, x: float, y: float):
    for side in (-1, 1):
        path = QPainterPath(QPointF(x, y))
        path.quadTo(QPointF(x + side * 10, y - 18), QPointF(x + side * 20, y - 8))
        path.quadTo(QPointF(x + side * 22, y + 4), QPointF(x + side * 18, y + 10))
        path.quadTo(QPointF(x + side * 8, y + 8), QPointF(x, y))
        p.setPen(pen(color.darker(125), 2))
        p.setBrush(color)
        p.drawPath(path)
    ellipse(p, x, y, 9, 9, color.lighter(110), color.darker(125), 2)


def draw_bangs(p: QPainter, points, dy: float):
    bangs = QPainterPath(QPointF(CX - 72, 132 + dy))
    bangs.cubicTo(QPointF(CX - 82, 2 + dy), QPointF(CX + 82, 2 + dy), QPointF(CX + 72, 132 + dy))
    cur = (CX + 72, 132)
    for x, y in points:
        ctrl = QPointF((cur[0] + x) / 2 + (4 if y < cur[1] else -4), max(y, cur[1]) - 2 + dy)
        bangs.quadTo(ctrl, QPointF(x, y + dy))
        cur = (x, y)
    p.setPen(pen(HAIR_LINE, 2.5))
    p.setBrush(HAIR)
    p.drawPath(bangs)
    p.setBrush(NO_BRUSH)
    p.setPen(pen(HAIR_HI, 6))                       # shiny "angel ring"
    p.drawArc(QRectF(CX - 50, 38 + dy, 100, 48), 35 * 16, 110 * 16)


def draw_girl_body(p: QPainter, look: Look, dy: float):
    top, hem = 172 + dy, 254 + dy * 0.5
    path = QPainterPath(QPointF(CX - 22, top))
    path.lineTo(CX + 22, top)
    path.quadTo(QPointF(CX + 34, hem - 40), QPointF(CX + 52, hem))
    path.quadTo(QPointF(CX, hem + 10), QPointF(CX - 52, hem))
    path.quadTo(QPointF(CX - 34, hem - 40), QPointF(CX - 22, top))
    p.setPen(pen(look.outfit_line, 2.5))
    p.setBrush(look.outfit)
    p.drawPath(path)
    frill = QPainterPath(QPointF(CX - 47, hem - 6))
    frill.quadTo(QPointF(CX, hem + 3), QPointF(CX + 47, hem - 6))
    p.setPen(pen(look.outfit_light, 4))
    p.setBrush(NO_BRUSH)
    p.drawPath(frill)
    for side in (-1, 1):
        ellipse(p, CX + side * 9, top + 5, 18, 11, WHITE, look.outfit_line, 2)
    draw_bow(p, look.accent, CX, top + 14)


def draw_boy_body(p: QPainter, look: Look, dy: float):
    top = 172 + dy
    waist = 230 + dy * 0.6
    # shorts
    for side in (-1, 1):
        leg = QPainterPath(QPointF(CX, waist - 4))
        leg.lineTo(CX + side * 33, waist - 4)
        leg.lineTo(CX + side * 35, waist + 22)
        leg.quadTo(QPointF(CX + side * 18, waist + 26), QPointF(CX + side * 3, waist + 22))
        leg.closeSubpath()
        p.setPen(pen(look.shorts.darker(125), 2.5))
        p.setBrush(look.shorts)
        p.drawPath(leg)
    # t-shirt
    shirt = QPainterPath(QPointF(CX - 22, top))
    shirt.lineTo(CX + 22, top)
    shirt.quadTo(QPointF(CX + 36, top + 24), QPointF(CX + 36, waist + 2))
    shirt.quadTo(QPointF(CX, waist + 8), QPointF(CX - 36, waist + 2))
    shirt.quadTo(QPointF(CX - 36, top + 24), QPointF(CX - 22, top))
    p.setPen(pen(look.outfit_line, 2.5))
    p.setBrush(look.outfit)
    p.drawPath(shirt)
    # hem band + round collar
    p.setPen(pen(look.outfit_light, 4))
    band = QPainterPath(QPointF(CX - 32, waist - 3))
    band.quadTo(QPointF(CX, waist + 3), QPointF(CX + 32, waist - 3))
    p.setBrush(NO_BRUSH)
    p.drawPath(band)
    p.setPen(pen(look.outfit_line, 2.2))
    p.setBrush(look.outfit_light)
    p.drawChord(QRectF(CX - 13, top - 8, 26, 18), 180 * 16, 180 * 16)
    star(p, CX + 12, top + 30, 8, look.accent)       # little star on the chest


def draw_character(p: QPainter, pose: Pose, look: Look):
    dy = pose.body_dy
    boy = look.gender == "boy"
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # --- hair behind the head
    if not boy:
        for side in (-1, 1):                          # twin tails
            p.save()
            p.translate(CX + side * 64, 92 + dy)
            p.rotate(side * (-6 + pose.hair * side))
            ellipse(p, side * 12, 56, 40, 100, HAIR, HAIR_LINE, 2.5)
            p.restore()
        ellipse(p, CX, 112 + dy, 158, 148, HAIR, HAIR_LINE, 2.5)
    else:
        ellipse(p, CX, 108 + dy, 154, 132, HAIR, HAIR_LINE, 2.5)

    # --- legs and shoes
    leg_top = (250 if boy else 240) + dy * 0.4
    for side, lift in ((-1, pose.leg_l), (1, pose.leg_r)):
        x = CX + side * 15
        p.setPen(pen(SKIN_LINE, 15))
        p.drawLine(QPointF(x, leg_top), QPointF(x, 278 - lift))
        p.setPen(pen(SKIN, 10.5))
        p.drawLine(QPointF(x, leg_top), QPointF(x, 278 - lift))
        ellipse(p, x + side * 3, 284 - lift, 30, 16, look.shoe, look.shoe.darker(130), 2.2)

    arms = ((-1, pose.arm_l), (1, pose.arm_r))
    (draw_boy_body if boy else draw_girl_body)(p, look, dy)
    for side, angle in arms:                          # hanging arms in front of the body
        if angle <= 95:
            draw_arm(p, look, side, angle, dy)

    # --- head
    ellipse(p, CX, 120 + dy, 138, 120, SKIN, SKIN_LINE, 2.5)
    if not boy:
        for side in (-1, 1):                          # hair ties
            ellipse(p, CX + side * 64, 96 + dy, 16, 16, look.accent, look.accent.darker(125), 2)

    if boy:
        # cowlick (drawn first so the bangs cover its root)
        tuft = QPainterPath(QPointF(CX - 4, 40 + dy))
        tuft.cubicTo(QPointF(CX - 10, 10 + dy), QPointF(CX + 18 + pose.hair, 6 + dy),
                     QPointF(CX + 16 + pose.hair, 22 + dy))
        tuft.cubicTo(QPointF(CX + 8, 16 + dy), QPointF(CX + 4, 26 + dy), QPointF(CX + 6, 40 + dy))
        p.setPen(pen(HAIR_LINE, 2.5))
        p.setBrush(HAIR)
        p.drawPath(tuft)
        points = [(CX + 58, 92), (CX + 44, 112), (CX + 30, 86), (CX + 14, 110), (CX, 84),
                  (CX - 16, 110), (CX - 30, 86), (CX - 44, 112), (CX - 58, 92), (CX - 72, 132)]
    else:
        points = [(CX + 54, 86), (CX + 38, 108), (CX + 20, 82), (CX + 4, 106),
                  (CX - 14, 82), (CX - 32, 108), (CX - 50, 86), (CX - 72, 132)]
    draw_bangs(p, points, dy)

    # --- face
    for side in (-1, 1):
        draw_eye(p, look, CX + side * 29, 133 + dy, pose.eyes, pose.look)
        ellipse(p, CX + side * 47, 154 + dy, 22, 11, BLUSH)
    draw_mouth(p, pose.mouth, dy)
    if not boy:
        draw_bow(p, look.accent, CX + 50, 56 + dy)

    for side, angle in arms:                          # raised arms in front of the head
        if angle > 95:
            draw_arm(p, look, side, angle, dy)

    if pose.sparkle >= 0:
        spots = [(CX - 92, 70, 0.0), (CX + 94, 96, 0.33), (CX - 84, 180, 0.66), (CX + 88, 200, 0.15)]
        for x, y, off in spots:
            r = 11 * math.sin(math.pi * ((pose.sparkle + off) % 1.0))
            star(p, x, y + dy, r, QColor("#FFD45C") if off < 0.5 else look.accent)


# --------------------------------------------------------------- animations
def wave(i: int, n: int, cycles: float = 1.0) -> float:
    return math.sin(2 * math.pi * cycles * i / n)


def idle_frames() -> list[Pose]:
    n = 12
    eyes = {9: "half", 10: "closed", 11: "half"}
    return [Pose(hair=3 * wave(i, n), arm_l=16 + wave(i, n), arm_r=16 + wave(i, n),
                 eyes=eyes.get(i, "open"), look=1.5 * wave(i, n)) for i in range(n)]


def walk_frames() -> list[Pose]:
    n = 8
    out = []
    for i in range(n):
        s = wave(i, n)
        out.append(Pose(leg_l=max(0.0, 9 * s), leg_r=max(0.0, -9 * s),
                        arm_l=18 + 16 * s, arm_r=18 - 16 * s,
                        body_dy=-2.5 * abs(s), hair=5 * s))
    return out


def hop_frames(mouth: str) -> list[Pose]:
    # Matches the hop arc in character.py: crouch -> takeoff -> air -> land
    return [
        Pose(body_dy=6, arm_l=32, arm_r=32, eyes="happy" if mouth == "open" else "open"),
        Pose(body_dy=-1, arm_l=60, arm_r=60, leg_l=4, leg_r=4, hair=-6, mouth=mouth),
        Pose(body_dy=-3, arm_l=115, arm_r=115, leg_l=9, leg_r=9, hair=-8, mouth=mouth),
        Pose(body_dy=-3, arm_l=120, arm_r=120, leg_l=10, leg_r=10, hair=-2, mouth=mouth),
        Pose(body_dy=-1, arm_l=70, arm_r=70, leg_l=5, leg_r=5, hair=7, mouth=mouth),
        Pose(body_dy=5, arm_l=36, arm_r=36, hair=5),
    ]


def remind_frames() -> list[Pose]:
    n = 12
    return [Pose(arm_r=148 + 18 * wave(i, n, 2), arm_l=16,
                 mouth="open" if i < 8 and (i // 2) % 2 == 0 else "smile",
                 hair=2 * wave(i, n), eyes="half" if i == 11 else "open") for i in range(n)]


def happy_frames() -> list[Pose]:
    n = 8
    return [Pose(arm_l=150 + 10 * wave(i, n), arm_r=150 - 10 * wave(i, n),
                 eyes="happy", mouth="grin", sparkle=i / n, hair=4 * wave(i, n),
                 body_dy=-3 * abs(wave(i, n))) for i in range(n)]


ANIMATIONS = {   # name: (frame factory, fps)
    "idle": (idle_frames, 8),
    "enter": (lambda: hop_frames("open"), 10),
    "walk": (walk_frames, 12),
    "remind": (remind_frames, 8),
    "happy": (happy_frames, 10),
    "leave": (lambda: hop_frames("smile"), 10),
}


# ------------------------------------------------------------------ output
def render(pose: Pose, look: Look) -> QImage:
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    draw_character(p, pose, look)
    p.end()
    return img


def render_icon(look: Look, size: int) -> QImage:
    face = render(Pose(eyes="happy", mouth="grin"), look).copy(22, 18, 196, 196)
    return face.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)


def generate(out_dir: Path, gender: str, theme: Theme) -> Path:
    """Write a full character folder. Written to a temp dir first and renamed,
    so a half-finished set is never picked up."""
    look = Look(gender, theme)
    tmp = out_dir.with_name(out_dir.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    manifest = {"display_height": 210, "facing": "front", "animations": {}}
    for name, (factory, fps) in ANIMATIONS.items():
        (tmp / name).mkdir()
        for i, pose in enumerate(factory()):
            render(pose, look).save(str(tmp / name / f"frame_{i:02d}.png"))
        manifest["animations"][name] = {"frames": f"{name}/*.png", "fps": fps, "loop": True}
    (tmp / "animations.json").write_text(json.dumps(manifest, indent=2))
    render_icon(look, 64).save(str(tmp / "icon.png"))
    shutil.rmtree(out_dir, ignore_errors=True)
    tmp.rename(out_dir)
    return out_dir

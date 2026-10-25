"""Programmatically drawn icons approximating the original UI.

Every icon is rendered with QPainter at runtime, so nothing copyrighted is
bundled. Circle colors follow docs/reference/style-guide.md.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from tiptoi_linux.ui import theme

# A glyph painter draws the white symbol into a square of `size` units, with the
# circle already filled; coordinates are 0..size.
Glyph = Callable[[QPainter, float], None]

_SUPERSAMPLE = 4


def _antialias(p: QPainter) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)


def _white(p: QPainter, width: float = 0.0) -> None:
    pen = QPen(QColor(theme.BG_WHITE))
    pen.setWidthF(width if width else p.pen().widthF() or 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(QBrush(QColor(theme.BG_WHITE)))


def _glyph_download(p: QPainter, s: float) -> None:
    _white(p)
    cx = s / 2
    p.drawLine(QPointF(cx, s * 0.24), QPointF(cx, s * 0.58))
    path = QPainterPath()
    path.moveTo(cx - s * 0.16, s * 0.46)
    path.lineTo(cx, s * 0.64)
    path.lineTo(cx + s * 0.16, s * 0.46)
    p.setBrush(Qt.BrushStyle.NoBrush)
    _white(p, s * 0.09)
    p.drawPath(path)
    p.setBrush(QBrush(QColor(theme.BG_WHITE)))
    p.drawRoundedRect(QRectF(s * 0.26, s * 0.70, s * 0.48, s * 0.09), s * 0.045, s * 0.045)


def _glyph_book(p: QPainter, s: float) -> None:
    _white(p, s * 0.07)
    p.setBrush(Qt.BrushStyle.NoBrush)
    left = QPainterPath()
    left.moveTo(s * 0.5, s * 0.32)
    left.cubicTo(s * 0.38, s * 0.24, s * 0.26, s * 0.26, s * 0.2, s * 0.29)
    left.lineTo(s * 0.2, s * 0.7)
    left.cubicTo(s * 0.28, s * 0.67, s * 0.4, s * 0.68, s * 0.5, s * 0.75)
    p.drawPath(left)
    right = QPainterPath()
    right.moveTo(s * 0.5, s * 0.32)
    right.cubicTo(s * 0.62, s * 0.24, s * 0.74, s * 0.26, s * 0.8, s * 0.29)
    right.lineTo(s * 0.8, s * 0.7)
    right.cubicTo(s * 0.72, s * 0.67, s * 0.6, s * 0.68, s * 0.5, s * 0.75)
    p.drawPath(right)


def _glyph_music(p: QPainter, s: float) -> None:
    _white(p, s * 0.07)
    p.setBrush(QBrush(QColor(theme.BG_WHITE)))
    p.drawEllipse(QRectF(s * 0.30, s * 0.58, s * 0.18, s * 0.14))
    p.drawEllipse(QRectF(s * 0.56, s * 0.52, s * 0.18, s * 0.14))
    p.drawLine(QPointF(s * 0.47, s * 0.65), QPointF(s * 0.47, s * 0.28))
    p.drawLine(QPointF(s * 0.73, s * 0.59), QPointF(s * 0.73, s * 0.22))
    p.drawLine(QPointF(s * 0.47, s * 0.28), QPointF(s * 0.73, s * 0.22))


def gear_glyph(hole_color: str) -> Glyph:
    """Gear whose center hole is punched in the circle's own color."""

    def draw(p: QPainter, s: float) -> None:
        from math import cos, pi, sin

        cx, cy = s / 2, s / 2
        _white(p)
        p.setBrush(QBrush(QColor(theme.BG_WHITE)))
        path = QPainterPath()
        teeth = 8
        r_out, r_in = s * 0.32, s * 0.24
        for i in range(teeth * 2):
            r = r_out if i % 2 == 0 else r_in
            a = pi * i / teeth
            x, y = cx + r * cos(a), cy + r * sin(a)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        p.drawPath(path)
        p.setBrush(QColor(hole_color))
        p.drawEllipse(QPointF(cx, cy), s * 0.10, s * 0.10)

    return draw


def _glyph_question(p: QPainter, s: float) -> None:
    font = QFont(p.font())
    font.setPixelSize(int(s * 0.58))
    font.setBold(True)
    p.setFont(font)
    _white(p)
    p.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, "?")


def _glyph_pen(p: QPainter, s: float) -> None:
    _white(p, s * 0.06)
    p.setBrush(Qt.BrushStyle.NoBrush)
    body = QPainterPath()
    body.moveTo(s * 0.38, s * 0.22)
    body.lineTo(s * 0.62, s * 0.22)
    body.lineTo(s * 0.58, s * 0.62)
    body.lineTo(s * 0.5, s * 0.78)
    body.lineTo(s * 0.42, s * 0.62)
    body.closeSubpath()
    p.drawPath(body)


def _glyph_search(p: QPainter, s: float) -> None:
    _white(p, s * 0.08)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(s * 0.26, s * 0.22, s * 0.34, s * 0.34))
    p.drawLine(QPointF(s * 0.58, s * 0.54), QPointF(s * 0.74, s * 0.70))


def circle_icon(color: str, glyph: Glyph, px: int = 64) -> QIcon:
    """A filled colored circle with a white glyph, drawn at high resolution."""
    size = px * _SUPERSAMPLE
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    _antialias(painter)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(color)))
    margin = size * 0.04
    painter.drawEllipse(QRectF(margin, margin, size - 2 * margin, size - 2 * margin))
    glyph(painter, size)
    painter.end()
    return QIcon(pixmap)


# The five nav entries and their circle colors, mirroring the original order.
# WHY lazy: QPixmap/QIcon must not be constructed before a QGuiApplication exists,
# so icons are built on first use, never at module import time.
_NAV_SPECS = {
    "download": (theme.BRAND_ORANGE, _glyph_download),
    "catalog": (theme.ICON_GREEN, _glyph_book),
    "audiobooks": (theme.ICON_PINK, _glyph_music),
    "pen": (theme.ICON_ORANGE, gear_glyph(theme.ICON_ORANGE)),
    "help": (theme.ICON_BLUE, _glyph_question),
}

_ICON_CACHE: dict[str, QIcon] = {}


def nav_icon(key: str) -> QIcon:
    icon = _ICON_CACHE.get(key)
    if icon is None:
        color, glyph = _NAV_SPECS[key]
        icon = circle_icon(color, glyph)
        _ICON_CACHE[key] = icon
    return icon


def search_icon() -> QIcon:
    key = "__search__"
    if key not in _ICON_CACHE:
        _ICON_CACHE[key] = circle_icon(theme.BRAND_ORANGE, _glyph_search)
    return _ICON_CACHE[key]


def pen_device_icon() -> QIcon:
    key = "__pen_device__"
    if key not in _ICON_CACHE:
        _ICON_CACHE[key] = circle_icon(theme.ICON_BLUE, _glyph_pen)
    return _ICON_CACHE[key]


def app_icon() -> QIcon:
    """The application's own icon (packaging/tiptoi.svg rendered to PNG)."""
    key = "__app__"
    if key not in _ICON_CACHE:
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent / "resources" / "tiptoi.png"
        icon = QIcon(str(path))
        _ICON_CACHE[key] = icon if not icon.isNull() else pen_device_icon()
    return _ICON_CACHE[key]

"""
CodeMate — Animated Circular Gauge Widget
Smooth arc gauge using QPainter + QPropertyAnimation.
"""

from __future__ import annotations
import math
from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient
from PySide6.QtWidgets import QWidget
from ui.theme import COLORS, FONTS


class GaugeWidget(QWidget):
    """Animated circular gauge showing a 0–100% value."""

    def __init__(self, label: str = "", color: str = COLORS["accent_cyan"],
                 size: int = 140, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0
        self._display_value = 0.0
        self.setFixedSize(size, size)
        self._anim = QPropertyAnimation(self, b"displayValue")
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ── Animated property ────────────────────────────────────
    def _get_display_value(self):
        return self._display_value

    def _set_display_value(self, v):
        self._display_value = v
        self.update()

    displayValue = Property(float, _get_display_value, _set_display_value)

    def setValue(self, value: float):
        self._value = max(0.0, min(100.0, value))
        self._anim.stop()
        self._anim.setStartValue(self._display_value)
        self._anim.setEndValue(self._value)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 12
        track_width = 8
        arc_width = 8

        # Track (background arc)
        track_color = QColor(COLORS["gauge_track"])
        pen = QPen(track_color, track_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        rect = self._arc_rect(cx, cy, radius)
        painter.drawArc(rect, 225 * 16, -270 * 16)

        # Value arc with gradient
        if self._display_value > 0:
            grad = QConicalGradient(cx, cy, 225)
            c1 = QColor(self._color)
            c2 = QColor(self._color)
            c2.setAlpha(120)
            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            pen = QPen(grad, arc_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            span = -int(270 * (self._display_value / 100.0)) * 16
            painter.drawArc(rect, 225 * 16, span)

        # Center text — value
        painter.setPen(QColor(COLORS["text_primary"]))
        font = QFont(FONTS["family"], 18, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, -8, 0, 0), Qt.AlignmentFlag.AlignCenter,
                         f"{self._display_value:.0f}%")

        # Label below
        painter.setPen(QColor(COLORS["text_secondary"]))
        font = QFont(FONTS["family"], 9)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, 24, 0, 0), Qt.AlignmentFlag.AlignCenter,
                         self._label)
        painter.end()

    def _arc_rect(self, cx, cy, r):
        from PySide6.QtCore import QRectF
        return QRectF(cx - r, cy - r, r * 2, r * 2)

"""
CodeMate — Floating Action Bubble
Frameless, always-on-top circle that appears when code is copied.
"""

from __future__ import annotations
import math
import logging
from PySide6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                             QPoint, Signal, Property, QRect, QRectF)
from PySide6.QtGui import (QPainter, QColor, QRadialGradient, QConicalGradient,
                            QCursor, QFont, QPen)
from PySide6.QtWidgets import QWidget, QApplication
from ui.theme import COLORS
from config import UI_CONFIG

log = logging.getLogger(__name__)


class FloatingBubble(QWidget):
    """
    A glowing circle that pops up near the cursor when code is copied.
    Click to trigger inference. Auto-hides after timeout.
    """
    clicked = Signal()   # emitted when user clicks the bubble

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_size = UI_CONFIG["bubble_size"]
        self._margin = 20  # space for the outer spinner ring
        full = self._base_size + self._margin * 2
        self.setFixedSize(full, full)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # State
        self._pulse = 0.0
        self._is_loading = False
        self._spin_angle = 0

        # NO QGraphicsDropShadowEffect — we hand-paint the glow
        # to avoid UpdateLayeredWindowIndirect dirty region mismatches.

        # Pulse animation
        self._pulse_anim = QPropertyAnimation(self, b"pulse")
        self._pulse_anim.setDuration(1200)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)

        # Auto-hide timer
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

        # Spinner timer (fast for smooth animation)
        self._spin_timer = QTimer(self)
        self._spin_timer.timeout.connect(self._update_spin)

    # ── Pulse property ───────────────────────────────────────
    def _get_pulse(self):
        return self._pulse

    def _set_pulse(self, v):
        self._pulse = v
        self.update()

    pulse = Property(float, _get_pulse, _set_pulse)

    # ── Public API ───────────────────────────────────────────
    def show_at_cursor(self):
        """Show the bubble near the current cursor position."""
        pos = QCursor.pos()
        screen = QApplication.screenAt(pos)
        if screen:
            geo = screen.availableGeometry()
            x = min(pos.x() + 20, geo.right() - self.width())
            y = min(pos.y() - self.height() - 10, geo.bottom() - self.height())
            y = max(y, geo.top())
        else:
            x, y = pos.x() + 20, pos.y() - self.height() - 10
        # Offset by margin so the visible circle is at the intended position
        self.move(x - self._margin, y - self._margin)
        self._is_loading = False
        self._spin_timer.stop()
        self.show()
        self._pulse_anim.start()
        self._hide_timer.start(UI_CONFIG["bubble_timeout_ms"])

    def set_loading(self, loading: bool):
        """Switch to loading spinner state."""
        self._is_loading = loading
        if loading:
            self._pulse_anim.stop()
            self._spin_angle = 0
            self._spin_timer.start(16)  # ~60 FPS for smooth spin
            self._hide_timer.stop()
        else:
            self._spin_timer.stop()
            self._fade_out()

    # ── Drawing ──────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        m = self._margin
        s = self._base_size
        cx, cy = m + s / 2, m + s / 2
        r = s / 2 - 4  # bubble radius

        # ── LOADING STATE — outer spinner ring ───────────────
        if self._is_loading:
            orbit_r = r + 12  # ring radius (outside the bubble)
            ring_w = 4.0      # ring stroke width

            # 1) Dim track ring (full circle, low opacity)
            track = QColor(COLORS["accent_cyan"])
            track.setAlpha(35)
            painter.setPen(QPen(track, ring_w))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(
                cx - orbit_r, cy - orbit_r, orbit_r * 2, orbit_r * 2
            ))

            # 2) Bright sweeping arc — 120° long, rotating
            arc_color = QColor(COLORS["accent_cyan"])
            painter.setPen(QPen(arc_color, ring_w, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            arc_rect = QRectF(
                cx - orbit_r, cy - orbit_r, orbit_r * 2, orbit_r * 2
            )
            start_16 = int(self._spin_angle * 16)
            painter.drawArc(arc_rect, start_16, 120 * 16)

            # 3) Glowing head dot at the leading edge
            head_rad = math.radians(self._spin_angle + 120)
            hx = cx + orbit_r * math.cos(head_rad)
            hy = cy - orbit_r * math.sin(head_rad)

            # Glow behind dot
            glow = QRadialGradient(hx, hy, 8)
            gc = QColor(COLORS["accent_cyan"])
            gc.setAlpha(120)
            glow.setColorAt(0, gc)
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(QRectF(hx - 8, hy - 8, 16, 16))

            # Solid head dot
            painter.setBrush(QColor(COLORS["accent_cyan"]))
            painter.drawEllipse(QRectF(hx - 3, hy - 3, 6, 6))

            # 4) Fading tail dots
            for i in range(1, 6):
                tail_angle = self._spin_angle - i * 12
                tr = math.radians(tail_angle)
                tx = cx + orbit_r * math.cos(tr)
                ty = cy - orbit_r * math.sin(tr)
                alpha = max(15, 180 - i * 35)
                dot_sz = max(1.0, 3.0 - i * 0.4)
                tc = QColor(COLORS["accent_cyan"])
                tc.setAlpha(alpha)
                painter.setBrush(tc)
                painter.drawEllipse(QRectF(
                    tx - dot_sz, ty - dot_sz, dot_sz * 2, dot_sz * 2
                ))

        # ── IDLE STATE — pulsing glow ────────────────────────
        else:
            glow_alpha = int(50 + 40 * self._pulse)
            glow_r = r + 6 + 4 * self._pulse
            grad = QRadialGradient(cx, cy, glow_r)
            c = QColor(COLORS["bubble_bg"])
            c.setAlpha(glow_alpha)
            grad.setColorAt(0.5, c)
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(
                cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2
            ))

        # ── MAIN CIRCLE (always drawn) ───────────────────────
        grad2 = QRadialGradient(cx, cy - r * 0.3, r * 1.5)
        grad2.setColorAt(0, QColor(COLORS["bubble_bg"]).lighter(130))
        grad2.setColorAt(1, QColor(COLORS["bubble_bg"]))
        painter.setBrush(grad2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # ── CENTER TEXT ──────────────────────────────────────
        painter.setPen(QColor("#FFFFFF"))
        if self._is_loading:
            font = QFont("Consolas", 16, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - r, cy - r, r * 2, r * 2),
                Qt.AlignmentFlag.AlignCenter, "…")
        else:
            font = QFont("Consolas", 14, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - r, cy - r, r * 2, r * 2),
                Qt.AlignmentFlag.AlignCenter, "</>")

        painter.end()

    def mousePressEvent(self, event):
        # Only respond to clicks inside the visible circle
        m = self._margin
        s = self._base_size
        cx, cy = m + s / 2, m + s / 2
        dx = event.position().x() - cx
        dy = event.position().y() - cy
        if dx * dx + dy * dy > (s / 2) ** 2:
            event.ignore()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._hide_timer.stop()
            self.clicked.emit()
            event.accept()

    def _fade_out(self):
        self._pulse_anim.stop()
        self.hide()

    def _update_spin(self):
        self._spin_angle = (self._spin_angle + 6) % 360
        self.update()

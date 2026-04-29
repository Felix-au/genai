"""
CodeMate — Floating Action Bubble
Frameless, always-on-top circle that appears when code is copied.
"""

from __future__ import annotations
import logging
from PySide6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                             QPoint, Signal, Property, QRect)
from PySide6.QtGui import (QPainter, QColor, QRadialGradient, QCursor,
                            QFont, QPen)
from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect, QApplication
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
        self._margin = 30  # extra space for glow/shadow
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

        # Glow shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(COLORS["bubble_bg"]).lighter(150))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

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

        # Spinner timer
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
            self._spin_timer.start(30)
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
        r = s / 2 - 4

        # Outer glow pulse
        glow_alpha = int(40 + 30 * self._pulse)
        glow_r = r + 4 + 3 * self._pulse
        grad = QRadialGradient(cx, cy, glow_r)
        c = QColor(COLORS["bubble_bg"])
        c.setAlpha(glow_alpha)
        grad.setColorAt(0.5, c)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - glow_r), int(cy - glow_r),
                            int(glow_r * 2), int(glow_r * 2))

        # Main circle
        grad2 = QRadialGradient(cx, cy - r * 0.3, r * 1.5)
        grad2.setColorAt(0, QColor(COLORS["bubble_bg"]).lighter(130))
        grad2.setColorAt(1, QColor(COLORS["bubble_bg"]))
        painter.setBrush(grad2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        if self._is_loading:
            # Spinner arc
            pen = QPen(QColor("#FFFFFF"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            from PySide6.QtCore import QRectF
            arc_rect = QRectF(cx - r * 0.45, cy - r * 0.45, r * 0.9, r * 0.9)
            painter.drawArc(arc_rect, int(self._spin_angle * 16), 90 * 16)
        else:
            # Code icon "< >"
            painter.setPen(QColor("#FFFFFF"))
            font = QFont("Consolas", 14, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                int(cx - r), int(cy - r), int(r * 2), int(r * 2),
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
        self._spin_angle = (self._spin_angle + 8) % 360
        self.update()

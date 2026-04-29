"""
CodeMate — Glassmorphism Stat Card Widget
"""

from __future__ import annotations
from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from ui.theme import COLORS, FONTS, DIMS


class StatCard(QWidget):
    """A glassmorphism-styled info card with icon, label, and animated value."""

    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setMinimumWidth(180)
        self.setStyleSheet(f"""
            StatCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(26, 31, 46, 200), stop:1 rgba(20, 24, 32, 220));
                border: 1px solid {COLORS['border']};
                border-radius: {DIMS['radius_lg']};
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Icon + Label row
        header = QLabel(f"{icon_text}  {label}")
        header.setStyleSheet(f"""
            font-size: {FONTS['size_sm']};
            color: {COLORS['text_secondary']};
            font-weight: {FONTS['weight_medium']};
            background: transparent;
        """)
        layout.addWidget(header)

        # Value
        self._value_label = QLabel("—")
        self._value_label.setStyleSheet(f"""
            font-size: {FONTS['size_lg']};
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['text_primary']};
            background: transparent;
        """)
        layout.addWidget(self._value_label)

        # Sub-info
        self._sub_label = QLabel("")
        self._sub_label.setStyleSheet(f"""
            font-size: {FONTS['size_xs']};
            color: {COLORS['text_muted']};
            background: transparent;
        """)
        layout.addWidget(self._sub_label)

    def set_value(self, value: str, sub: str = ""):
        self._value_label.setText(value)
        if sub:
            self._sub_label.setText(sub)

    def paintEvent(self, event):
        """Draw subtle glassmorphism background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor(26, 31, 46, 200))
        grad.setColorAt(1, QColor(20, 24, 32, 220))
        painter.setBrush(grad)
        painter.setPen(QColor(COLORS["border"]))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)
        painter.end()
        super().paintEvent(event)

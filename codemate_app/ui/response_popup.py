"""
CodeMate — Response Popup
Frameless popup that displays inference results with syntax highlighting.
"""

from __future__ import annotations
import logging
from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QCursor, QFont, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit, QApplication,
                                QGraphicsDropShadowEffect, QGraphicsOpacityEffect)
from ui.theme import COLORS, FONTS, DIMS

log = logging.getLogger(__name__)


class ResponsePopup(QWidget):
    """Frameless popup that shows the model's response."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(480, 300)
        self.setMaximumSize(700, 550)
        self._drag_pos = None

        # Container
        self._container = QWidget(self)
        self._container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border_accent']};
                border-radius: {DIMS['radius_xl']};
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 212, 255, 60))
        shadow.setOffset(0, 8)
        self._container.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("⚡ CodeMate Response")
        title.setStyleSheet(f"""
            font-size: {FONTS['size_lg']};
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['accent_cyan']};
            background: transparent;
        """)
        header.addWidget(title)
        header.addStretch()

        copy_btn = QPushButton("📋 Copy")
        copy_btn.setObjectName("primary")
        copy_btn.setFixedHeight(32)
        copy_btn.clicked.connect(self._copy_response)
        header.addWidget(copy_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                font-size: 14px;
                color: {COLORS['text_secondary']};
            }}
            QPushButton:hover {{
                background: {COLORS['accent_red']};
                color: white;
            }}
        """)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)

        layout.addLayout(header)

        # Response text area
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: {DIMS['radius_md']};
                padding: 12px;
                font-family: {FONTS['mono']};
                font-size: {FONTS['size_sm']};
                color: {COLORS['text_primary']};
            }}
        """)
        layout.addWidget(self._text_edit)

    def show_response(self, text: str):
        self._text_edit.setPlainText(text)
        # Position near cursor
        pos = QCursor.pos()
        screen = QApplication.screenAt(pos)
        if screen:
            geo = screen.availableGeometry()
            x = min(pos.x() + 30, geo.right() - self.width() - 20)
            y = min(pos.y() - 50, geo.bottom() - self.height() - 20)
            x = max(x, geo.left() + 20)
            y = max(y, geo.top() + 20)
        else:
            x, y = pos.x() + 30, pos.y() - 50
        self.move(x, y)
        self.show()
        self.raise_()

    def _copy_response(self):
        text = self._text_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    # ── Drag support ─────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

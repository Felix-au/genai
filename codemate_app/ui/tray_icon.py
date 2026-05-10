"""
CodeMate — System Tray Icon
"""

from __future__ import annotations
import logging
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QRadialGradient, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from config import BASE_DIR

log = logging.getLogger(__name__)


def _create_default_icon() -> QIcon:
    """Load the CodeMate logo, or fall back to a cyan circle."""
    logo_path = BASE_DIR / "assets" / "CodeMate-logo.png"
    if logo_path.exists():
        return QIcon(str(logo_path))
    # Fallback: programmatic cyan/purple circle
    size = 64
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QRadialGradient(size / 2, size / 2, size / 2)
    grad.setColorAt(0.0, QColor("#00D4FF"))
    grad.setColorAt(1.0, QColor("#A855F7"))
    p.setBrush(grad)
    p.setPen(QColor(0, 0, 0, 0))
    p.drawEllipse(4, 4, size - 8, size - 8)
    p.end()
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    """System tray icon with context menu."""

    show_dashboard_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        icon = _create_default_icon()
        self.setIcon(icon)
        self.setToolTip("CodeMate: Your Coding Companion")

        # Context menu
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #141820;
                border: 1px solid #2A3040;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                color: #E8ECF4;
            }
            QMenu::item:selected {
                background-color: #222840;
            }
        """)

        show_action = QAction("📊 Open Dashboard", self)
        show_action.triggered.connect(self.show_dashboard_requested.emit)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("❌ Quit CodeMate", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_dashboard_requested.emit()

"""
CodeMate — Main Dashboard Window
GPU stats, system info, activity log, and settings.
"""

from __future__ import annotations
import logging
from datetime import datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QCheckBox, QScrollArea, QFrame, QGraphicsDropShadowEffect,
    QPushButton,
)
from ui.theme import COLORS, FONTS, DIMS, card_style
from ui.widgets.gauge_widget import GaugeWidget
from ui.widgets.stat_card import StatCard
from core.system_monitor import SystemStats
from config import UI_CONFIG

log = logging.getLogger(__name__)


class DashboardWindow(QMainWindow):
    """Main dashboard with GPU stats, system info, and settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CodeMate — AI Code Assistant")
        self.setMinimumSize(UI_CONFIG["dashboard_width"], UI_CONFIG["dashboard_height"])
        self._activity_items: list[str] = []

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(20)

        # ── Header ───────────────────────────────────────────
        header = self._build_header()
        main_layout.addLayout(header)

        # ── Content area ─────────────────────────────────────
        content = QHBoxLayout()
        content.setSpacing(20)

        # Left: Gauges + Stats
        left_panel = QVBoxLayout()
        left_panel.setSpacing(16)

        gauges_layout = QHBoxLayout()
        gauges_layout.setSpacing(16)
        self._gpu_gauge = GaugeWidget("GPU", COLORS["accent_cyan"], 140)
        self._mem_gauge = GaugeWidget("VRAM", COLORS["accent_purple"], 140)
        self._cpu_gauge = GaugeWidget("CPU", COLORS["accent_green"], 140)
        self._ram_gauge = GaugeWidget("RAM", COLORS["accent_orange"], 140)
        for g in [self._gpu_gauge, self._mem_gauge, self._cpu_gauge, self._ram_gauge]:
            gauges_layout.addWidget(g, alignment=Qt.AlignmentFlag.AlignCenter)
        left_panel.addLayout(gauges_layout)

        # Stat cards
        cards_layout = QGridLayout()
        cards_layout.setSpacing(12)
        self._card_gpu = StatCard("🖥️", "GPU")
        self._card_driver = StatCard("📦", "Driver")
        self._card_vram = StatCard("💾", "VRAM")
        self._card_model = StatCard("🤖", "Model Status")
        self._card_backend = StatCard("⚡", "Compute")
        self._card_temp = StatCard("🌡️", "GPU Temp")
        cards_layout.addWidget(self._card_gpu, 0, 0)
        cards_layout.addWidget(self._card_driver, 0, 1)
        cards_layout.addWidget(self._card_vram, 0, 2)
        cards_layout.addWidget(self._card_model, 1, 0)
        cards_layout.addWidget(self._card_backend, 1, 1)
        cards_layout.addWidget(self._card_temp, 1, 2)
        left_panel.addLayout(cards_layout)

        content.addLayout(left_panel, stretch=3)

        # Right: Activity log + Settings
        right_panel = QVBoxLayout()
        right_panel.setSpacing(16)

        # Activity log
        log_label = QLabel("📋 Recent Activity")
        log_label.setStyleSheet(f"""
            font-size: {FONTS['size_md']};
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['text_secondary']};
        """)
        right_panel.addWidget(log_label)

        self._activity_scroll = QScrollArea()
        self._activity_scroll.setWidgetResizable(True)
        self._activity_scroll.setFixedWidth(260)
        self._activity_scroll.setStyleSheet(f"""
            QScrollArea {{ background: {COLORS['bg_card']}; border-radius: {DIMS['radius_lg']}; border: 1px solid {COLORS['border']}; }}
        """)
        self._activity_container = QWidget()
        self._activity_layout = QVBoxLayout(self._activity_container)
        self._activity_layout.setContentsMargins(12, 12, 12, 12)
        self._activity_layout.setSpacing(8)
        self._activity_layout.addStretch()
        self._activity_scroll.setWidget(self._activity_container)
        right_panel.addWidget(self._activity_scroll)

        # Settings
        settings_frame = QFrame()
        settings_frame.setStyleSheet(card_style())
        settings_frame.setFixedWidth(260)
        s_layout = QVBoxLayout(settings_frame)
        s_layout.setContentsMargins(16, 12, 16, 12)
        s_layout.setSpacing(10)
        s_label = QLabel("⚙️ Settings")
        s_label.setStyleSheet(f"font-weight: {FONTS['weight_bold']}; color: {COLORS['text_secondary']};")
        s_layout.addWidget(s_label)

        self.chk_startup = QCheckBox("Start at system startup")
        self.chk_minimize = QCheckBox("Minimize to tray on close")
        self.chk_minimize.setChecked(True)
        self.chk_force_cpu = QCheckBox("Force CPU only (requires restart)")
        for chk in [self.chk_startup, self.chk_minimize, self.chk_force_cpu]:
            s_layout.addWidget(chk)

        # Gear button for advanced settings
        self.btn_advanced = QPushButton("⚙️  Advanced Settings")
        self.btn_advanced.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_advanced.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: {DIMS['radius_sm']};
                padding: 8px 12px;
                color: {COLORS['text_secondary']};
                font-size: {FONTS['size_xs']};
                text-align: left;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_card']};
                border-color: {COLORS['accent_cyan']};
                color: {COLORS['text_primary']};
            }}
        """)
        s_layout.addWidget(self.btn_advanced)
        right_panel.addWidget(settings_frame)

        content.addLayout(right_panel, stretch=1)
        main_layout.addLayout(content)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        title = QLabel("CodeMate")
        title.setObjectName("title")
        header.addWidget(title)

        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 18px;")
        header.addWidget(self._status_dot)

        self._status_label = QLabel("Initializing…")
        self._status_label.setObjectName("subtitle")
        header.addWidget(self._status_label)
        header.addStretch()

        ver = QLabel("v1.0.0")
        ver.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: {FONTS['size_xs']};")
        header.addWidget(ver)
        return header

    # ── Public update methods ────────────────────────────────
    def update_stats(self, stats: SystemStats):
        self._gpu_gauge.setValue(stats.gpu_util_percent)
        self._mem_gauge.setValue(stats.gpu_mem_percent)
        self._cpu_gauge.setValue(stats.cpu_percent)
        self._ram_gauge.setValue(stats.ram_percent)

        self._card_gpu.set_value(stats.gpu_name if stats.gpu_name != "N/A" else "No GPU")
        self._card_driver.set_value(stats.gpu_driver)
        self._card_vram.set_value(
            f"{stats.gpu_mem_used_mb} / {stats.gpu_mem_total_mb} MB"
            if stats.gpu_mem_total_mb else "N/A"
        )
        self._card_temp.set_value(
            f"{stats.gpu_temp_c:.0f}°C" if stats.gpu_temp_c else "N/A"
        )

    def set_model_status(self, status: str, color: str = COLORS["text_secondary"]):
        self._status_label.setText(status)
        self._card_model.set_value(status.split("|")[0].strip())

    def set_status_color(self, color: str):
        self._status_dot.setStyleSheet(f"color: {color}; font-size: 18px;")

    def set_backend_info(self, backend: str):
        self._card_backend.set_value(backend.upper())

    def add_activity(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = QLabel(f"[{timestamp}] {message}")
        entry.setWordWrap(True)
        entry.setStyleSheet(f"""
            font-size: {FONTS['size_xs']};
            color: {COLORS['text_secondary']};
            background: {COLORS['bg_secondary']};
            border-radius: {DIMS['radius_sm']};
            padding: 6px 8px;
        """)
        # Insert before the stretch
        count = self._activity_layout.count()
        self._activity_layout.insertWidget(count - 1, entry)
        self._activity_items.append(message)
        # Keep max 50 entries
        if len(self._activity_items) > 50:
            item = self._activity_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
            self._activity_items.pop(0)

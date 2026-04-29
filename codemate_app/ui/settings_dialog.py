"""
CodeMate — Advanced Settings Dialog
API mode toggle and key input — hidden from normal view.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QLineEdit, QPushButton, QFrame,
)
from ui.theme import COLORS, FONTS, DIMS


class SettingsDialog(QDialog):
    """Modal dialog for advanced settings (API mode)."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Settings")
        self.setFixedSize(400, 260)
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {DIMS['radius_lg']};
            }}
        """)

        self._settings = dict(settings)  # working copy
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Header ───────────────────────────────────────────
        title = QLabel("⚙️ Advanced Settings")
        title.setStyleSheet(f"""
            font-size: {FONTS['size_lg']};
            font-weight: {FONTS['weight_bold']};
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(title)

        # ── Separator ────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {COLORS['border']};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # ── API Mode toggle ──────────────────────────────────
        self.chk_api_mode = QCheckBox("API Mode")
        self.chk_api_mode.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                font-size: {FONTS['size_sm']};
            }}
        """)
        self.chk_api_mode.setChecked(self._settings.get("api_mode", False))
        self.chk_api_mode.toggled.connect(self._on_api_mode_toggled)
        layout.addWidget(self.chk_api_mode)

        # ── API Key input ────────────────────────────────────
        self._key_label = QLabel("API Key")
        self._key_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_xs']};
        """)
        layout.addWidget(self._key_label)

        self.txt_api_key = QLineEdit()
        self.txt_api_key.setPlaceholderText("Enter your API key…")
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setText(self._settings.get("api_key", ""))
        self.txt_api_key.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: {DIMS['radius_sm']};
                padding: 8px 12px;
                color: {COLORS['text_primary']};
                font-size: {FONTS['size_sm']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent_cyan']};
            }}
        """)
        layout.addWidget(self.txt_api_key)

        # ── Show/hide key field based on current state ───────
        self._update_key_visibility(self.chk_api_mode.isChecked())

        # ── Buttons ──────────────────────────────────────────
        layout.addStretch()
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: {DIMS['radius_sm']};
                padding: 8px 20px;
                color: {COLORS['text_secondary']};
                font-size: {FONTS['size_sm']};
            }}
            QPushButton:hover {{ background: {COLORS['bg_secondary']}; }}
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save")
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_cyan']};
                border: none;
                border-radius: {DIMS['radius_sm']};
                padding: 8px 20px;
                color: {COLORS['bg_primary']};
                font-weight: {FONTS['weight_bold']};
                font-size: {FONTS['size_sm']};
            }}
            QPushButton:hover {{ background: {COLORS['accent_purple']}; color: white; }}
        """)
        btn_save.clicked.connect(self._on_save)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _on_api_mode_toggled(self, checked: bool):
        self._update_key_visibility(checked)

    def _update_key_visibility(self, visible: bool):
        self._key_label.setVisible(visible)
        self.txt_api_key.setVisible(visible)

    def _on_save(self):
        self._settings["api_mode"] = self.chk_api_mode.isChecked()
        self._settings["api_key"] = self.txt_api_key.text().strip()
        self.accept()

    def get_settings(self) -> dict:
        """Return the updated settings after dialog is accepted."""
        return self._settings

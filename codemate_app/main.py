"""
╔══════════════════════════════════════════════════════════════╗
║              CodeMate — Application Entry Point              ║
╚══════════════════════════════════════════════════════════════╝
Wires all core services and UI together. Single-instance.
"""

from __future__ import annotations

import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Ensure the app directory is on the Python path
app_dir = str(Path(__file__).resolve().parent)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from PySide6.QtCore import Qt, QTimer, QProcess, QThread, Signal
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QCloseEvent

from config import (
    UI_CONFIG, DEFAULT_SETTINGS, SETTINGS_FILE, CONTEXT_CONFIG
)
from core.model_engine import ModelEngine
from core.clipboard_monitor import ClipboardMonitor
from core.context_enricher import enrich_context
from core.system_monitor import SystemMonitor
from core import startup_manager
from ui.theme import get_global_stylesheet, COLORS
from ui.dashboard import DashboardWindow
from ui.floating_bubble import FloatingBubble
from ui.response_popup import ResponsePopup
from ui.tray_icon import TrayIcon
from ui.settings_dialog import SettingsDialog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("CodeMate")

# ── Pipeline log file ────────────────────────────────────────
LOG_FILE = Path(app_dir) / "log.txt"


def _write_pipeline_log(
    input_code: str,
    batches: list,
    queries: list,
    context: str,
    final_prompt: str,
    response: str,
):
    """Append a full pipeline entry to log.txt at the app root."""
    sep = "=" * 72
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "",
        sep,
        f"  CODEMATE PIPELINE LOG — {timestamp}",
        sep,
        "",
        "── INPUT RECEIVED ──────────────────────────────────────",
        input_code,
        "",
        "── WEB CRAWLER — KEYWORD BATCHES ───────────────────────",
    ]
    if batches:
        for i, b in enumerate(batches, 1):
            lines.append(f"  Batch {i}: {b}")
    else:
        lines.append("  (no batches extracted)")

    lines.append("")
    lines.append("── WEB CRAWLER — QUERIES & RESPONSES ──────────────────")
    if queries:
        for q in queries:
            lines.append(f"  [{q['source']}] Query: \"{q['query']}\"")
            lines.append(f"           Result: {q['result']}")
            lines.append("")
    else:
        lines.append("  (no queries executed)")

    lines.append("── ASSEMBLED CONTEXT ───────────────────────────────────")
    lines.append(context if context else "(empty — no context)")

    lines.append("")
    lines.append("── FINAL PROMPT ────────────────────────────────────────")
    lines.append(final_prompt)

    lines.append("")
    lines.append("── INFERENCE RESPONSE ──────────────────────────────────")
    lines.append(response)

    lines.append("")
    lines.append(sep)
    lines.append("")

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
        log.info(f"Pipeline log written to {LOG_FILE}")
    except Exception as e:
        log.error(f"Failed to write pipeline log: {e}")


class _ContextThread(QThread):
    """Runs context enrichment in a background thread so the UI stays responsive."""
    finished_signal = Signal(dict)

    def __init__(self, code: str):
        super().__init__()
        self._code = code

    def run(self):
        context_data = {"batches": [], "queries": [], "context": ""}
        try:
            context_data = enrich_context(self._code)
        except Exception as e:
            log.warning(f"Context enrichment failed: {e}")
        self.finished_signal.emit(context_data)


class CodeMateApp:
    """Main application controller — orchestrates all components."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(UI_CONFIG["app_name"])
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setStyleSheet(get_global_stylesheet())

        self.settings = self._load_settings()
        self._pending_code: str = ""
        self._last_context_data: dict = {}   # structured context for logging
        self._last_input_code: str = ""       # raw code input for logging

        # ── Core services ────────────────────────────────────
        self.engine = ModelEngine()
        self.clipboard = ClipboardMonitor()
        self.sys_monitor = SystemMonitor(
            interval_ms=UI_CONFIG["stats_refresh_ms"]
        )

        # ── UI components ────────────────────────────────────
        self.dashboard = DashboardWindow()
        self.bubble = FloatingBubble()
        self.response_popup = ResponsePopup()
        self.tray = TrayIcon()

        # ── Wire signals ─────────────────────────────────────
        self._connect_signals()

        self.dashboard.chk_startup.setChecked(
            self.settings.get("start_at_startup", False)
        )
        self.dashboard.chk_minimize.setChecked(
            self.settings.get("minimize_to_tray", True)
        )
        self.dashboard.chk_force_cpu.blockSignals(True)
        self.dashboard.chk_force_cpu.setChecked(
            self.settings.get("force_cpu", False)
        )
        self.dashboard.chk_force_cpu.blockSignals(False)

        # Override close event on dashboard
        self.dashboard.closeEvent = self._on_dashboard_close

    def run(self) -> int:
        """Start all services and enter event loop."""
        log.info("Starting CodeMate …")

        # Start background services
        self.sys_monitor.start()
        self.clipboard.start()

        # Start model loading (async)
        # force_cpu overrides api_mode — local CPU inference takes priority
        force_cpu = self.settings.get("force_cpu", False)
        api_mode = self.settings.get("api_mode", False) and not force_cpu
        self.engine.load_async(
            force_cpu=force_cpu,
            api_mode=api_mode,
            api_key=self.settings.get("api_key", ""),
        )

        # Show dashboard and tray
        self.dashboard.show()
        self.tray.show()

        self.dashboard.add_activity("CodeMate started")
        self.dashboard.set_status_color(COLORS["accent_orange"])
        self.dashboard.set_model_status("Loading model…")

        return self.app.exec()

    # ── Signal wiring ────────────────────────────────────────
    def _connect_signals(self):
        # Model engine
        self.engine.signals.model_loaded.connect(self._on_model_loaded)
        self.engine.signals.model_error.connect(self._on_model_error)
        self.engine.signals.inference_started.connect(self._on_inference_start)
        self.engine.signals.inference_finished.connect(self._on_inference_done)
        self.engine.signals.inference_error.connect(self._on_inference_error)

        # Clipboard
        self.clipboard.code_copied.connect(self._on_code_copied)
        self.clipboard.status_changed.connect(
            lambda s: self.dashboard.add_activity(s)
        )

        # System monitor
        self.sys_monitor.stats_updated.connect(self.dashboard.update_stats)

        # Bubble
        self.bubble.clicked.connect(self._on_bubble_clicked)

        # Tray
        self.tray.show_dashboard_requested.connect(self._show_dashboard)
        self.tray.quit_requested.connect(self._quit)

        # Settings checkboxes
        self.dashboard.chk_startup.toggled.connect(self._on_startup_toggled)
        self.dashboard.chk_minimize.toggled.connect(
            lambda v: self._update_setting("minimize_to_tray", v)
        )
        self.dashboard.chk_force_cpu.toggled.connect(
            self._on_force_cpu_toggled
        )

        # Settings header opens advanced settings dialog
        self.dashboard.btn_settings_header.clicked.connect(
            self._on_advanced_settings
        )

    # ── Event handlers ───────────────────────────────────────
    def _on_force_cpu_toggled(self, enabled: bool):
        """Prompt user for restart when toggling CPU-only mode."""
        mode = "CPU-only" if enabled else "GPU-accelerated"
        reply = QMessageBox.question(
            self.dashboard,
            "Restart Required",
            f"Switching to {mode} mode requires a restart.\n\n"
            f"Restart CodeMate now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._update_setting("force_cpu", enabled)
            self._restart()
        else:
            # Revert checkbox without re-triggering the signal
            self.dashboard.chk_force_cpu.blockSignals(True)
            self.dashboard.chk_force_cpu.setChecked(not enabled)
            self.dashboard.chk_force_cpu.blockSignals(False)

    def _on_advanced_settings(self):
        """Open the advanced settings dialog (API mode)."""
        old_api_mode = self.settings.get("api_mode", False)
        dlg = SettingsDialog(self.settings, parent=self.dashboard)
        if dlg.exec():
            new_settings = dlg.get_settings()
            # Persist all changes
            for k, v in new_settings.items():
                self.settings[k] = v
            self._save_settings()

            # If api_mode changed, prompt restart
            new_api_mode = self.settings.get("api_mode", False)
            if new_api_mode != old_api_mode:
                mode = "API" if new_api_mode else "local model"
                reply = QMessageBox.question(
                    self.dashboard,
                    "Restart Required",
                    f"Switching to {mode} mode requires a restart.\n\n"
                    f"Restart CodeMate now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._restart()

    def _on_model_loaded(self, status: str):
        log.info(f"Model loaded: {status}")
        self.dashboard.set_model_status(status)
        self.dashboard.set_status_color(COLORS["accent_green"])
        self.dashboard.add_activity(f"Model ready: {status}")
        # Set mode label
        if self.engine.api_mode:
            self.dashboard.set_backend_info("API")
        elif self.engine.force_cpu:
            self.dashboard.set_backend_info("CPU")
        else:
            self.dashboard.set_backend_info("GPU")

    def _on_model_error(self, err: str):
        log.error(f"Model error: {err}")
        self.dashboard.set_model_status(f"Error: {err[:60]}")
        self.dashboard.set_status_color(COLORS["accent_red"])
        self.dashboard.add_activity(f"⚠ Model error: {err[:80]}")

    def _on_code_copied(self, code: str):
        """Code detected in clipboard — show the bubble."""
        if not self.engine.is_loaded:
            return
        self._pending_code = code
        self.bubble.show_at_cursor()
        snippet = code[:50].replace("\n", " ")
        self.dashboard.add_activity(f"Code detected: {snippet}…")

    def _on_bubble_clicked(self):
        """User clicked the bubble — start inference pipeline."""
        if not self._pending_code:
            return
        code = self._pending_code
        self._pending_code = ""
        self._last_input_code = code
        self.bubble.set_loading(True)

        # Run context enrichment in a background thread so the
        # bubble spinner animation keeps running during web requests.
        self._context_thread = _ContextThread(code)
        self._context_thread.finished_signal.connect(self._on_context_ready)
        self._context_thread.start()

    def _on_context_ready(self, context_data: dict):
        """Context enrichment done — fire inference."""
        if context_data.get("context"):
            self.dashboard.add_activity(
                f"Context enriched: {len(context_data['context'])} chars"
            )
        self._last_context_data = context_data
        self.engine.generate_async(
            self._last_input_code, context_data.get("context", "")
        )

    def _on_inference_start(self):
        self.dashboard.add_activity("⏳ Inference running…")

    def _on_inference_done(self, result: str):

        self.bubble.set_loading(False)
        self.response_popup.show_response(result)
        self.dashboard.add_activity(
            f"✅ Response: {result[:60].replace(chr(10), ' ')}…"
        )

        # ── Write full pipeline to log.txt ────────────────────
        _write_pipeline_log(
            input_code=self._last_input_code,
            batches=self._last_context_data.get("batches", []),
            queries=self._last_context_data.get("queries", []),
            context=self._last_context_data.get("context", ""),
            final_prompt=getattr(self.engine, "last_prompt", "(unavailable)"),
            response=result,
        )

    def _on_inference_error(self, err: str):

        self.bubble.set_loading(False)
        self.dashboard.add_activity(f"❌ Inference error: {err[:80]}")

    def _on_startup_toggled(self, enabled: bool):
        if enabled:
            startup_manager.enable_startup()
        else:
            startup_manager.disable_startup()
        self._update_setting("start_at_startup", enabled)

    # ── Dashboard close behavior ─────────────────────────────
    def _on_dashboard_close(self, event: QCloseEvent):
        if self.settings.get("minimize_to_tray", True):
            event.ignore()
            self.dashboard.hide()
            self.tray.showMessage(
                "CodeMate",
                "Still running in the background. Double-click to reopen.",
                TrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            self._quit()

    def _show_dashboard(self):
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()

    def _quit(self):
        log.info("Shutting down …")
        self.clipboard.stop()
        self.sys_monitor.stop()
        self._save_settings()
        self.tray.hide()
        self.app.quit()

    def _restart(self):
        """Save settings, shut down services, and relaunch the app."""
        log.info("Restarting CodeMate …")
        self.clipboard.stop()
        self.sys_monitor.stop()
        self._save_settings()
        self.tray.hide()
        QProcess.startDetached(sys.executable, sys.argv)
        self.app.quit()

    # ── Settings persistence ─────────────────────────────────
    def _load_settings(self) -> dict:
        if SETTINGS_FILE.exists():
            try:
                return json.loads(SETTINGS_FILE.read_text())
            except Exception:
                pass
        return dict(DEFAULT_SETTINGS)

    def _save_settings(self):
        try:
            SETTINGS_FILE.write_text(json.dumps(self.settings, indent=2))
        except Exception as e:
            log.error(f"Failed to save settings: {e}")

    def _update_setting(self, key: str, value):
        self.settings[key] = value
        self._save_settings()


# ── Entry point ──────────────────────────────────────────────
def main():
    app = CodeMateApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()

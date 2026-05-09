"""
╔══════════════════════════════════════════════════════════════╗
║           CodeMate — System & GPU Monitor                    ║
╚══════════════════════════════════════════════════════════════╝
Periodic system stats collection for the dashboard.
"""

from __future__ import annotations
import logging, time
from dataclasses import dataclass
from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)

@dataclass
class SystemStats:
    cpu_percent: float = 0.0
    ram_used_mb: int = 0
    ram_total_mb: int = 0
    ram_percent: float = 0.0
    gpu_util_percent: float = 0.0
    gpu_mem_used_mb: int = 0
    gpu_mem_total_mb: int = 0
    gpu_mem_percent: float = 0.0
    gpu_temp_c: float = 0.0
    gpu_name: str = "N/A"
    gpu_driver: str = "N/A"


class SystemMonitor(QThread):
    stats_updated = Signal(object)  # emits SystemStats

    def __init__(self, interval_ms: int = 1000):
        super().__init__()
        self._running = True
        self._interval = interval_ms / 1000.0
        self._has_nvidia = False
        self._nvml_handle = None

    def stop(self):
        self._running = False

    def run(self):
        import psutil
        # Try NVIDIA init
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self._has_nvidia = True
        except Exception:
            self._has_nvidia = False

        while self._running:
            try:
                stats = self._collect(psutil)
                self.stats_updated.emit(stats)
            except Exception as e:
                log.debug(f"Stats collection error: {e}")
            time.sleep(self._interval)

        if self._has_nvidia:
            try:
                import pynvml
                pynvml.nvmlShutdown()
            except Exception:
                pass

    def _collect(self, psutil) -> SystemStats:
        mem = psutil.virtual_memory()
        stats = SystemStats(
            cpu_percent=psutil.cpu_percent(interval=None),
            ram_used_mb=int(mem.used / (1024 * 1024)),
            ram_total_mb=int(mem.total / (1024 * 1024)),
            ram_percent=mem.percent,
        )

        if self._has_nvidia and self._nvml_handle:
            try:
                import pynvml
                util = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                name = pynvml.nvmlDeviceGetName(self._nvml_handle)
                if isinstance(name, bytes):
                    name = name.decode()
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(self._nvml_handle, 0)
                except Exception:
                    temp = 0

                stats.gpu_util_percent = float(util.gpu)
                stats.gpu_mem_used_mb = int(mem_info.used / (1024 * 1024))
                stats.gpu_mem_total_mb = int(mem_info.total / (1024 * 1024))
                stats.gpu_mem_percent = (mem_info.used / mem_info.total * 100) if mem_info.total else 0
                stats.gpu_temp_c = float(temp)
                stats.gpu_name = name
            except Exception as e:
                log.debug(f"NVIDIA stats error: {e}")
        else:
            # ── No GPU detected — show honest values ──
            stats.gpu_name = "No GPU"
            stats.gpu_driver = "N/A"
            stats.gpu_mem_total_mb = 0
            stats.gpu_mem_used_mb = 0
            stats.gpu_mem_percent = 0.0
            stats.gpu_util_percent = 0.0
            stats.gpu_temp_c = 0.0

        return stats

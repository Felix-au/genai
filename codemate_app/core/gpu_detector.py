"""
╔══════════════════════════════════════════════════════════════╗
║              CodeMate — GPU Detection & Selection            ║
╚══════════════════════════════════════════════════════════════╝
Detects NVIDIA / AMD / CPU and returns optimal backend info.
"""

from __future__ import annotations

import logging
import subprocess
import re
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """Describes the detected GPU and chosen compute backend."""
    vendor: str = "none"                # "nvidia", "amd", "none"
    name: str = "CPU (no GPU)"
    vram_total_mb: int = 0
    driver_version: str = "N/A"
    compute_backend: str = "cpu"        # "cuda", "rocm", "cpu"
    device_string: str = "cpu"          # torch device string
    supports_4bit: bool = False         # bitsandbytes NF4 support


def _detect_nvidia() -> Optional[GPUInfo]:
    """Try to detect an NVIDIA GPU via pynvml."""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8")
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        driver = pynvml.nvmlSystemGetDriverVersion()
        if isinstance(driver, bytes):
            driver = driver.decode("utf-8")
        pynvml.nvmlShutdown()

        return GPUInfo(
            vendor="nvidia",
            name=name,
            vram_total_mb=int(mem_info.total / (1024 * 1024)),
            driver_version=driver,
            compute_backend="cuda",
            device_string="cuda:0",
            supports_4bit=True,
        )
    except Exception as e:
        log.debug(f"NVIDIA detection failed: {e}")
        return None


def _detect_amd() -> Optional[GPUInfo]:
    """Try to detect an AMD GPU via rocm-smi or WMI fallback."""
    # Attempt 1: rocm-smi
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname", "--showmeminfo", "vram"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            output = result.stdout
            name_match = re.search(r"Card Series:\s*(.+)", output)
            mem_match = re.search(r"Total Memory \(B\):\s*(\d+)", output)
            name = name_match.group(1).strip() if name_match else "AMD GPU"
            vram = int(int(mem_match.group(1)) / (1024 * 1024)) if mem_match else 0

            return GPUInfo(
                vendor="amd",
                name=name,
                vram_total_mb=vram,
                driver_version="ROCm",
                compute_backend="rocm",
                device_string="cuda:0",   # PyTorch ROCm uses cuda device string
                supports_4bit=False,       # bitsandbytes ROCm support is limited
            )
    except Exception as e:
        log.debug(f"rocm-smi detection failed: {e}")

    # Attempt 2: WMI (Windows only) — detects AMD GPU even without ROCm
    try:
        result = subprocess.run(
            ["wmic", "path", "win32_videocontroller", "get",
             "Name,AdapterRAM,DriverVersion", "/format:csv"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if "AMD" in line.upper() or "RADEON" in line.upper():
                    parts = [p.strip() for p in line.split(",")]
                    # CSV format: Node, AdapterRAM, DriverVersion, Name
                    if len(parts) >= 4:
                        adapter_ram = int(parts[1]) if parts[1].isdigit() else 0
                        driver = parts[2]
                        name = parts[3]

                        # Check if PyTorch ROCm is actually available
                        import torch
                        has_rocm = torch.cuda.is_available()  # ROCm maps to CUDA API

                        return GPUInfo(
                            vendor="amd",
                            name=name,
                            vram_total_mb=adapter_ram // (1024 * 1024),
                            driver_version=driver,
                            compute_backend="rocm" if has_rocm else "cpu",
                            device_string="cuda:0" if has_rocm else "cpu",
                            supports_4bit=False,
                        )
    except Exception as e:
        log.debug(f"WMI AMD detection failed: {e}")

    return None


def detect_gpu() -> GPUInfo:
    """
    Detect the best available GPU and return its info.
    Priority: NVIDIA CUDA  →  AMD ROCm  →  CPU fallback.
    """
    # Try NVIDIA first (most common for ML)
    info = _detect_nvidia()
    if info:
        # Verify PyTorch CUDA is actually usable
        try:
            import torch
            if torch.cuda.is_available():
                log.info(f"✅ NVIDIA GPU detected: {info.name} ({info.vram_total_mb}MB VRAM)")
                return info
        except ImportError:
            pass
        log.warning("NVIDIA GPU found but PyTorch CUDA unavailable — falling back")

    # Try AMD
    info = _detect_amd()
    if info and info.compute_backend == "rocm":
        log.info(f"✅ AMD GPU detected (ROCm): {info.name} ({info.vram_total_mb}MB VRAM)")
        return info
    elif info:
        log.info(f"⚠ AMD GPU detected but ROCm unavailable: {info.name} — using CPU")
        return info

    # CPU fallback
    log.info("ℹ No GPU detected — using CPU")
    try:
        import psutil
        ram = psutil.virtual_memory().total // (1024 * 1024)
    except Exception:
        ram = 0

    return GPUInfo(
        vendor="none",
        name="CPU (no GPU detected)",
        vram_total_mb=0,
        driver_version="N/A",
        compute_backend="cpu",
        device_string="cpu",
        supports_4bit=False,
    )


# ── Quick self-test ──────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    gpu = detect_gpu()
    print(f"\n{'='*50}")
    print(f"  Vendor:    {gpu.vendor}")
    print(f"  GPU:       {gpu.name}")
    print(f"  VRAM:      {gpu.vram_total_mb} MB")
    print(f"  Driver:    {gpu.driver_version}")
    print(f"  Backend:   {gpu.compute_backend}")
    print(f"  Device:    {gpu.device_string}")
    print(f"  4-bit:     {gpu.supports_4bit}")
    print(f"{'='*50}")

"""
╔══════════════════════════════════════════════════════════════╗
║                  CodeMate — Configuration                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
from pathlib import Path
from platformdirs import user_data_dir

# ── Portable path resolution ────────────────────────────────
def get_base_path() -> Path:
    """Return the base directory — works both in dev and PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR = get_base_path()
DATA_DIR = Path(user_data_dir("CodeMate", "CodeMate"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"

# ── Model ────────────────────────────────────────────────────
MODEL_CONFIG = {
    "base_model_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    "adapter_path": str(BASE_DIR.parent / "codemate" / "final_adapter"),
    "local_model_cache": str(DATA_DIR / "model_cache"),
    "max_new_tokens": 512,
    "temperature": 0.3,
    "top_p": 0.9,
    "repetition_penalty": 1.1,
    "max_seq_length": 2048,
}

# ── System Prompt ────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are CodeMate, an AI code assistant. Analyze the following code. "
    "If there are errors or tracebacks, identify the bug and suggest a "
    "corrected version. If the code is functional, explain its behavior "
    "step-by-step."
)

# ── Context Enrichment ───────────────────────────────────────
CONTEXT_CONFIG = {
    "enabled": True,
    "max_context_tokens": 300,          # keep context concise
    "wikipedia_sentences": 2,           # sentences per wiki hit
    "howdoi_max_results": 1,
    "query_timeout_seconds": 5,
    "batch_config": {                   # word-batch extraction
        "small_threshold": 50,          # tokens
        "medium_threshold": 200,
        "small_batches": 1,
        "medium_batches": 3,
        "large_batches": 5,
        "words_per_batch": 4,
    },
}

# ── UI ───────────────────────────────────────────────────────
UI_CONFIG = {
    "app_name": "CodeMate",
    "bubble_timeout_ms": 6000,          # auto-hide after 6s
    "bubble_size": 56,
    "stats_refresh_ms": 1000,           # 1s dashboard refresh
    "animation_duration_ms": 600,
    "dashboard_width": 900,
    "dashboard_height": 620,
}

# ── Defaults ─────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "start_at_startup": False,
    "minimize_to_tray": True,
    "context_enrichment": True,
}

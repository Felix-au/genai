"""
╔══════════════════════════════════════════════════════════════╗
║            CodeMate — Local Model Inference Engine            ║
╚══════════════════════════════════════════════════════════════╝
Loads Qwen2.5-Coder-1.5B-Instruct + LoRA adapter with optimal
GPU backend selection.  Runs inference in a QThread.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal, QObject

from config import MODEL_CONFIG, SYSTEM_PROMPT
from core.gpu_detector import GPUInfo, detect_gpu

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Signals relay (so we can emit from the worker thread)
# ─────────────────────────────────────────────────────────────
class EngineSignals(QObject):
    model_loading = Signal()                # emitted when loading starts
    model_loaded = Signal(str)              # emitted with status message
    model_error = Signal(str)               # emitted on load/inference error
    inference_started = Signal()
    inference_finished = Signal(str)        # emitted with generated text
    inference_error = Signal(str)


# ─────────────────────────────────────────────────────────────
# Loader thread — loads model off the main thread
# ─────────────────────────────────────────────────────────────
class ModelLoaderThread(QThread):
    """Loads the model + adapter in a background thread."""

    def __init__(self, engine: "ModelEngine"):
        super().__init__()
        self.engine = engine

    def run(self):
        try:
            self.engine._do_load()
        except Exception as e:
            log.exception("Model loading failed")
            self.engine.signals.model_error.emit(str(e))


# ─────────────────────────────────────────────────────────────
# Inference thread
# ─────────────────────────────────────────────────────────────
class InferenceThread(QThread):
    """Runs a single inference call off the main thread."""

    def __init__(self, engine: "ModelEngine", prompt: str):
        super().__init__()
        self.engine = engine
        self.prompt = prompt

    def run(self):
        try:
            self.engine.signals.inference_started.emit()
            result = self.engine._do_generate(self.prompt)
            self.engine.signals.inference_finished.emit(result)
        except Exception as e:
            log.exception("Inference failed")
            self.engine.signals.inference_error.emit(str(e))


# ─────────────────────────────────────────────────────────────
# Main engine class
# ─────────────────────────────────────────────────────────────
class ModelEngine:
    """
    Manages model lifecycle: load → generate → unload.
    All heavy work runs in QThreads; results delivered via signals.
    """

    def __init__(self):
        self.signals = EngineSignals()
        self.gpu_info: Optional[GPUInfo] = None
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self._loader_thread: Optional[ModelLoaderThread] = None
        self._inference_thread: Optional[InferenceThread] = None

    # ── Public API ───────────────────────────────────────────

    def load_async(self):
        """Start loading model in background thread."""
        if self.is_loaded:
            self.signals.model_loaded.emit("Model already loaded")
            return
        self.signals.model_loading.emit()
        self._loader_thread = ModelLoaderThread(self)
        self._loader_thread.start()

    def generate_async(self, code: str, context: str = ""):
        """Build prompt and start inference in background thread."""
        if not self.is_loaded:
            self.signals.inference_error.emit("Model not loaded yet")
            return
        prompt = self._build_prompt(code, context)
        self.last_prompt = prompt
        self._inference_thread = InferenceThread(self, prompt)
        self._inference_thread.start()

    def is_busy(self) -> bool:
        """Return True if currently running inference."""
        return (
            self._inference_thread is not None
            and self._inference_thread.isRunning()
        )

    # ── Internal ─────────────────────────────────────────────

    def _do_load(self):
        """Heavy model loading — runs in ModelLoaderThread."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        log.info("Detecting GPU …")
        self.gpu_info = detect_gpu()

        base_model_id = MODEL_CONFIG["base_model_id"]
        adapter_path = MODEL_CONFIG["adapter_path"]
        cache_dir = MODEL_CONFIG["local_model_cache"]

        log.info(f"Loading tokenizer from {base_model_id} …")
        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model_id,
            trust_remote_code=True,
            cache_dir=cache_dir,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # ── Decide dtype & quantization based on GPU ─────────
        load_kwargs: dict = {
            "trust_remote_code": True,
            "cache_dir": cache_dir,
        }

        if self.gpu_info.compute_backend == "cuda" and self.gpu_info.supports_4bit:
            # NVIDIA — use 4-bit quantization for memory efficiency
            log.info("Using NVIDIA CUDA with 4-bit NF4 quantization")
            from transformers import BitsAndBytesConfig
            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            load_kwargs["device_map"] = "auto"
            load_kwargs["torch_dtype"] = torch.float16
        elif self.gpu_info.compute_backend == "rocm":
            # AMD ROCm — float16 (bitsandbytes support is limited on ROCm)
            log.info("Using AMD ROCm with float16")
            load_kwargs["device_map"] = "auto"
            load_kwargs["torch_dtype"] = torch.float16
        else:
            # CPU fallback — float32 for stability
            log.info("Using CPU with float32")
            load_kwargs["device_map"] = "cpu"
            load_kwargs["torch_dtype"] = torch.float32

        log.info(f"Loading base model {base_model_id} …")
        t0 = time.time()
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model_id, **load_kwargs
        )

        # ── Apply LoRA adapter ───────────────────────────────
        if Path(adapter_path).exists():
            log.info(f"Applying LoRA adapter from {adapter_path} …")
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(
                self.model, adapter_path
            )
            self.model = self.model.merge_and_unload()
            log.info("LoRA adapter merged successfully")
        else:
            log.warning(f"Adapter path not found: {adapter_path} — using base model only")

        self.model.eval()
        elapsed = time.time() - t0
        self.is_loaded = True

        status = (
            f"Model loaded in {elapsed:.1f}s | "
            f"{self.gpu_info.name} | "
            f"{self.gpu_info.compute_backend.upper()}"
        )
        log.info(f"✅ {status}")
        self.signals.model_loaded.emit(status)

    def _build_prompt(self, code: str, context: str = "") -> str:
        """Format prompt using Qwen2.5 chat template."""
        user_content = f"<CODE>\n{code}\n</CODE>"
        if context.strip():
            user_content += f"\n\nCONTEXT: {context}"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        return prompt

    def _do_generate(self, prompt: str) -> str:
        """Heavy inference — runs in InferenceThread."""
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.model.device)
        attention_mask = inputs["attention_mask"].to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=MODEL_CONFIG["max_new_tokens"],
                temperature=MODEL_CONFIG["temperature"],
                top_p=MODEL_CONFIG["top_p"],
                do_sample=True,
                repetition_penalty=MODEL_CONFIG["repetition_penalty"],
                pad_token_id=self.tokenizer.pad_token_id,
            )

        # Decode only the generated tokens (skip the prompt)
        new_tokens = outputs[0][input_ids.shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return response.strip()


# ── Quick self-test ──────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)

    engine = ModelEngine()

    def on_loaded(msg):
        print(f"\n✅ {msg}")
        print("Running test inference …")
        engine.generate_async("def add(a, b):\n    return a - b")

    def on_result(text):
        print(f"\n📋 Response:\n{text}")
        app.quit()

    def on_error(err):
        print(f"\n❌ Error: {err}")
        app.quit()

    engine.signals.model_loaded.connect(on_loaded)
    engine.signals.inference_finished.connect(on_result)
    engine.signals.inference_error.connect(on_error)
    engine.signals.model_error.connect(on_error)

    engine.load_async()
    sys.exit(app.exec())

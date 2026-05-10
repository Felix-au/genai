# CodeMate — Project Summary

## What It Is
CodeMate is an AI-powered desktop application that monitors the system clipboard for code snippets and provides instant debugging or explanation using a fine-tuned large language model. It runs as a background service on Windows with a floating UI that appears on-demand.

## How It Works

### Pipeline (per request)
1. **Clipboard Detection** — A Win32 native listener (`WM_CLIPBOARDUPDATE`) fires when text is copied. A 14-pattern regex engine determines if the text is code (supports Python, JavaScript, C++, Java, tracebacks).
2. **Floating Bubble** — A translucent, animated circular button appears near the cursor. Auto-hides after 6 seconds if not clicked.
3. **Context Enrichment** — Keywords are extracted from the code (filtering language stop-words), grouped into batches, and queried against Wikipedia and StackOverflow in parallel threads. Results are capped at 300 tokens.
4. **Inference** — The code + enriched context are fed to the model with a system prompt. The model either identifies bugs and suggests fixes, or explains the code step-by-step.
5. **Response Popup** — A dark-themed popup displays the result with a one-click copy button.
6. **Pipeline Logging** — The entire pipeline (input → keyword batches → web queries → assembled context → final prompt → model response) is appended to `log.txt` for auditing.

### Inference Backends
- **Local (default)**: Qwen2.5-Coder-1.5B-Instruct with custom QLoRA adapter. Supports NVIDIA CUDA (4-bit NF4 quantization), AMD ROCm (float16), or CPU (float32). Model auto-downloaded from HuggingFace on first launch.
- **API (opt-in)**: Gemini 2.5 Flash via Google GenAI SDK. Configured through the settings dialog. API errors are masked to prevent backend leakage.

## Key Components

| Component | File | Role |
|---|---|---|
| **App Controller** | `main.py` | Entry point. Wires all services, manages settings persistence, handles signal routing between core and UI. |
| **Model Engine** | `core/model_engine.py` | Dual-backend inference engine. Loads model in a QThread, runs inference in a QThread, emits Qt signals for results. |
| **Clipboard Monitor** | `core/clipboard_monitor.py` | Win32 native clipboard listener with polling fallback. Emits `code_copied` signal when code is detected. |
| **Context Enricher** | `core/context_enricher.py` | Extracts identifiers, queries Wikipedia + StackOverflow in parallel, assembles context string. |
| **GPU Detector** | `core/gpu_detector.py` | Auto-detects NVIDIA (pynvml), AMD (rocm-smi + WMI), or CPU. Returns optimal compute backend. |
| **System Monitor** | `core/system_monitor.py` | Periodic CPU/RAM/GPU/VRAM/temp readings via psutil + pynvml. Feeds dashboard gauges. |
| **Dashboard** | `ui/dashboard.py` | Main window with circular gauge widgets, activity log, settings checkboxes, and status indicators. |
| **Floating Bubble** | `ui/floating_bubble.py` | Always-on-top animated QWidget with radial gradient, positioned at cursor on clipboard events. |
| **Response Popup** | `ui/response_popup.py` | Frameless popup displaying AI response with copy-to-clipboard button. |
| **Settings Dialog** | `ui/settings_dialog.py` | Modal dialog for API mode toggle and API key entry. |
| **Tray Icon** | `ui/tray_icon.py` | System tray icon with show/quit context menu. |

## Model Training Pipeline
The project includes a complete ML training pipeline (in `Model Training CODE/`):
- **Data preparation**: Download from HuggingFace, synthetic bug injection (8 bug types), Gemini-generated explanations
- **Training**: QLoRA fine-tuning on Google Colab T4 (~2 hours, ~13K examples)
- **Evaluation**: CodeBLEU, BLEU, ROUGE-L, Pass@1 metrics with baseline comparison against Gemini Flash zero/few-shot

## Technology Stack
- **Language**: Python 3.10+
- **UI Framework**: PySide6 (Qt6)
- **ML Stack**: PyTorch, HuggingFace Transformers, PEFT (QLoRA), BitsAndBytes (4-bit)
- **GPU Support**: NVIDIA CUDA, AMD ROCm, CPU fallback
- **Web Context**: Wikipedia API, howdoi (StackOverflow)
- **Packaging**: PyInstaller (standalone .exe)
- **Platform**: Windows 10/11 (Win32 clipboard API)

<p align="center">
  <img src="codemate_app/assets/CodeMate-logo.png" width="150" alt="CodeMate Logo"/>
</p>
<h1 align="center">CodeMate: Your Coding Companion</h1>
<p align="center">
  <strong>AI-powered code debugger &amp; explainer that lives in your clipboard</strong><br/>
  <em>Copy code anywhere → floating bubble appears → one click → instant AI analysis</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/model-Qwen2.5--Coder--1.5B-FF6F00?style=flat-square&logo=huggingface&logoColor=white" alt="Model" />
  <img src="https://img.shields.io/badge/fine--tuning-QLoRA-blueviolet?style=flat-square" alt="QLoRA" />
  <img src="https://img.shields.io/badge/ui-PySide6-41CD52?style=flat-square&logo=qt&logoColor=white" alt="PySide6" />
  <img src="https://img.shields.io/badge/api_fallback-Gemini_Flash-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License" />
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Why CodeMate?](#-why-codemate)
- [Screenshots](#-screenshots)
- [Features](#-features)
- [Architecture](#-architecture)
- [Model Pipeline](#-model-pipeline)
- [Quick Start](#-quick-start)
- [Build Standalone EXE](#-build-standalone-exe)
- [Project Structure](#-project-structure)
- [Dependencies](#-dependencies)
- [Configuration](#-configuration)
- [Improvement Ideas](#-improvement-ideas)
- [Author](#-author)

---

## 🔍 Overview

**CodeMate** is a desktop AI assistant that monitors your clipboard for code snippets. The moment you copy code — from VS Code, a browser, a terminal, or anywhere — a floating bubble appears near your cursor. Click it, and CodeMate analyzes the code using a fine-tuned **Qwen2.5-Coder-1.5B-Instruct** model (with custom QLoRA adapters) to:

- **🐛 Debug** — detect errors, tracebacks, and logical bugs, then suggest corrected code
- **📖 Explain** — generate step-by-step walkthroughs of clean, functional code

Before inference, CodeMate automatically enriches the prompt with **web-sourced context** — querying Wikipedia and StackOverflow for relevant information about the libraries and functions in your code.

> All processing runs **locally on your machine** (GPU or CPU). An optional API backend (Gemini Flash) is available for machines without GPU resources.

---

## 🎯 Why CodeMate?

> **Every AI code tool requires you to go to *it* — open a browser, paste code, wait. CodeMate comes to *you*.**

| | Traditional AI Code Tools | CodeMate |
|---|---|---|
| **Workflow** | Open ChatGPT/Copilot Chat → paste code → wait → copy result back | Copy code anywhere → bubble appears → click → response popup with copy button |
| **Context** | You provide context manually | **Auto-enriched** — CodeMate crawls Wikipedia + StackOverflow for relevant context before inference |
| **Model** | Cloud-only (GPT-4, Claude) | **Local-first** — fine-tuned Qwen2.5-Coder-1.5B runs on your GPU/CPU. No internet needed for inference |
| **Integration** | Browser tab or IDE extension | **System-wide** — works with any app that puts text on the clipboard |
| **Privacy** | Code sent to cloud APIs | Code stays on your machine (API mode is opt-in) |
| **Latency** | Network round-trip | Direct GPU inference — sub-second on modern hardware |
| **Fine-tuning** | Generic model | Custom QLoRA adapters trained on 13K+ debug/explain examples |

---

## 📸 Screenshots

<p align="center">
  <img src="Application Screenshots/application_dashboard.PNG" width="700" alt="CodeMate Dashboard"/>
  <br/><em>Dashboard — system metrics, model status, activity log, and settings</em>
</p>

<p align="center">
  <img src="Application Screenshots/CodeMate Popup.PNG" width="500" alt="CodeMate Floating Bubble"/>
  <br/><em>Floating bubble — appears at your cursor when code is detected in the clipboard</em>
</p>

<p align="center">
  <img src="Application Screenshots/CodeMate in Action.PNG" width="600" alt="CodeMate Response Popup"/>
  <br/><em>Response popup — AI analysis with one-click copy to clipboard</em>
</p>

---

## ✨ Features

### 🔍 Intelligent Clipboard Monitoring
| Feature | Description |
|---|---|
| **Win32 Native Listener** | Uses `WM_CLIPBOARDUPDATE` for zero-latency clipboard detection — no polling overhead |
| **Code Detection** | 14-pattern regex engine identifies code vs. plain text (supports Python, JS, C++, Java, tracebacks) |
| **Polling Fallback** | Gracefully falls back to `pyperclip`-based polling if Win32 hooks fail |

### 🧠 Dual Inference Backend
| Feature | Description |
|---|---|
| **Local Model** | Qwen2.5-Coder-1.5B-Instruct + custom QLoRA adapter (rank=16, α=32) |
| **GPU Auto-Detection** | Detects NVIDIA (CUDA + 4-bit NF4 quantization), AMD (ROCm float16), or CPU fallback |
| **API Fallback** | Optional Gemini Flash backend for machines without GPU — transparent to the user |
| **Force CPU Mode** | One-click toggle to force CPU inference (useful for debugging or when GPU is busy) |

### 🌐 Web Context Enrichment
| Feature | Description |
|---|---|
| **Keyword Extraction** | Extracts meaningful identifiers from code, filtering language keywords |
| **Batch Querying** | Groups keywords into batches, queries Wikipedia and StackOverflow in parallel |
| **Token Budget** | Caps context at 300 tokens to keep prompts focused |
| **Pipeline Logging** | Full pipeline (input → keywords → queries → context → prompt → response) logged to `log.txt` |

### 🖥️ Desktop UI
| Feature | Description |
|---|---|
| **Floating Bubble** | Animated, always-on-top circle with radial gradient — appears at cursor position, auto-hides after 6s |
| **Response Popup** | Dark-themed popup with formatted AI response + one-click copy button |
| **Dashboard** | Full-featured control panel: system metrics gauges (CPU/VRAM/GPU/RAM), model status, activity log, settings |
| **System Tray** | Minimize to tray on close, double-click to restore, right-click menu for quit |
| **Auto-Start** | Optional Windows registry startup entry |

### 🔧 System Monitoring
| Feature | Description |
|---|---|
| **CPU / RAM** | Real-time usage via `psutil` |
| **GPU / VRAM** | NVIDIA via `pynvml`, AMD via `rocm-smi` / WMI fallback |
| **GPU Temperature** | Live temperature reading displayed on dashboard |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CodeMate Desktop App                         │
│                                                                 │
│  ┌───────────────┐    ┌──────────────────────────────────────┐  │
│  │  Clipboard    │    │          UI Layer (PySide6)          │  │
│  │  Monitor      │    │                                      │  │
│  │               │    │  ┌────────────┐  ┌────────────────┐  │  │
│  │ Win32 native  ├───►│  │  Floating  │  │   Dashboard    │  │  │
│  │ WM_CLIPBOARD  │    │  │  Bubble    │  │   (gauges,     │  │  │
│  │ UPDATE hook   │    │  └─────┬──────┘  │    activity,   │  │  │
│  └───────────────┘    │        │click     │    settings)  │  │  │
│                       │  ┌─────▼──────┐  └────────────────┘  │  │
│                       │  │  Response   │  ┌───────────────┐  │  │
│                       │  │  Popup      │  │  System Tray  │  │  │
│                       │  └────────────┘  └────────────────┘  │  │
│                       └──────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Core Engine                           │   │
│  │                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐   │   │
│  │  │ Context      │  │ Model Engine │  │ GPU Detector  │   │   │
│  │  │ Enricher     │  │              │  │               │   │   │
│  │  │              │  │ Local:       │  │ NVIDIA→CUDA   │   │   │
│  │  │ Wikipedia    │  │  Qwen2.5     │  │ AMD→ROCm      │   │   │
│  │  │ StackOverflow│  │  + QLoRA     │  │ CPU fallback  │   │   │
│  │  │ (parallel)   │  │              │  └───────────────┘   │   │
│  │  └──────┬───────┘  │ API:         │                      │   │
│  │         │          │  Gemini Flash │                     │   │
│  │         │context   │              │                      │   │
│  │         └─────────►│  QThread      │                     │   │
│  │                    │  inference    │                     │   │
│  │                    └──────────────┘                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  System Monitor (psutil + pynvml) → Dashboard gauges     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline Flow

```
Copy code → Clipboard Monitor detects code (14 regex patterns)
     │
     ▼
Floating Bubble appears at cursor → User clicks
     │
     ▼
Context Enricher (background QThread):
  1. Extract identifiers, filter stop-words
  2. Group into keyword batches
  3. Query Wikipedia + StackOverflow in parallel
  4. Assemble context string (capped at 300 tokens)
     │
     ▼
Model Engine (background QThread):
  → Local: Qwen2.5-Coder-1.5B + QLoRA adapter → torch inference
  → API:   Gemini Flash (if configured)
     │
     ▼
Response Popup → User copies result
     │
     ▼
Full pipeline logged to log.txt
```

---

## 🧪 Model Pipeline

The project includes a complete ML training pipeline alongside the desktop app:

### Training Data
| Source | Type | Count |
|---|---|---|
| HuggingFace code datasets | Clean code | ~6K examples |
| Synthetic bug injection | 8 bug types (off-by-one, wrong operator, missing return, etc.) | ~4K examples |
| Gemini Flash batch generation | Step-by-step explanations | ~3K examples |
| **Total** | | **~13K examples** |

### Training Configuration
| Parameter | Value |
|---|---|
| Base Model | Qwen2.5-Coder-1.5B-Instruct |
| Method | QLoRA (4-bit NF4 quantization) |
| LoRA Rank / Alpha | 16 / 32 |
| Trainable Parameters | ~20–50M |
| Training Hardware | Google Colab T4 GPU |
| Training Time | ~2 hours |
| VRAM Usage | ~12.5 / 15 GB |

### Evaluation Metrics
| Metric | What It Measures |
|---|---|
| CodeBLEU | Structural code similarity (debug fixes) |
| BLEU | Text similarity (explanations) |
| ROUGE-L | Recall of key phrases |
| Pass@1 | Do suggested fixes actually run? |

---

## 🚀 Quick Start

### Option A — Standalone EXE (No Python Required)

Download `CodeMate.exe` from [Releases](https://github.com/Felix-au/CodeMate-Your-Coding-Companion/releases) and run it. All dependencies are bundled inside the EXE. The AI model (~3GB) downloads automatically on first launch.

### Option B — From Source

#### 1. Install Dependencies

```bash
cd codemate_app
pip install -r requirements.txt
```

### 2. Run the App

```bash
python main.py
```

On first launch:
- The base model (Qwen2.5-Coder-1.5B-Instruct) is auto-downloaded from HuggingFace (~3GB)
- GPU is auto-detected (NVIDIA CUDA / AMD ROCm / CPU fallback)
- The dashboard opens and shows model loading progress

### 3. Use It

1. Copy any code snippet to your clipboard (from any application)
2. A glowing blue floating bubble appears near your cursor
3. Click the bubble
4. Wait for context enrichment + inference (~2–10 seconds depending on hardware)
5. A response popup appears with the analysis — click **Copy** to grab it

### API Mode (Optional)

If you don't have a GPU or want faster responses:

1. Click the ⚙ Settings gear on the dashboard
2. Enable **API Mode**
3. Enter your Gemini API key
4. Restart when prompted

---

## 📦 Build Standalone EXE

```bash
cd codemate_app
pip install -r requirements.txt    # ensure all deps are installed
python build.py                    # runs PyInstaller single-file build
```

Output:

```
dist/
└── CodeMate.exe      # Single-file executable (~200–400MB)
                      # All Python deps + libs bundled inside
```

### What's Bundled Inside the EXE
- Python runtime + all dependencies (torch, transformers, PySide6, peft, etc.)
- App assets (icon)
- All core engine and UI modules

### What Downloads on First Run
- **Base model**: Qwen2.5-Coder-1.5B-Instruct (~3GB) from HuggingFace
  - Cached at `%LOCALAPPDATA%/CodeMate/CodeMate/model_cache/`
  - Subsequent launches load from cache (no internet needed)
- **LoRA adapter** (optional): Place in an `adapter/` folder next to `CodeMate.exe` if available

> **Why not bundle the model?** The base model is ~3GB — bundling it would create an impractically large executable. Instead, it downloads once on first launch and is cached permanently.

---

## 📁 Project Structure

```
genai/
├── codemate_app/                    # Desktop application
│   ├── main.py                      # App entry point — wires all services (442 lines)
│   ├── config.py                    # All configuration: model, UI, API, context (88 lines)
│   ├── requirements.txt             # Python dependencies
│   ├── build.py                     # PyInstaller build script
│   ├── build.spec                   # PyInstaller spec file
│   │
│   ├── core/                        # Backend engine
│   │   ├── model_engine.py          # Dual-backend inference: local Qwen + API Gemini (358 lines)
│   │   ├── clipboard_monitor.py     # Win32 native + polling fallback clipboard detection (107 lines)
│   │   ├── context_enricher.py      # Wikipedia + StackOverflow keyword-batch crawler (166 lines)
│   │   ├── gpu_detector.py          # NVIDIA/AMD/CPU auto-detection (182 lines)
│   │   ├── system_monitor.py        # CPU/RAM/GPU/VRAM/temp monitoring via psutil + pynvml
│   │   └── startup_manager.py       # Windows registry auto-start management
│   │
│   ├── ui/                          # PySide6 GUI
│   │   ├── dashboard.py             # Main window: gauges, activity log, settings
│   │   ├── floating_bubble.py       # Animated always-on-top circular button
│   │   ├── response_popup.py        # Dark-themed AI response display
│   │   ├── settings_dialog.py       # Advanced settings (API mode, key entry)
│   │   ├── tray_icon.py             # System tray icon with context menu
│   │   ├── theme.py                 # Global stylesheet + color constants
│   │   └── widgets/                 # Custom gauge widgets
│   │
│   └── assets/
│       ├── CodeMate-logo.png        # App logo (high-res)
│       ├── CodeMate-logo.ico        # App icon (Windows .ico)
│       └── icon.png                 # Legacy icon
│
├── Application Screenshots/         # UI screenshots
│   ├── application_dashboard.PNG    # Dashboard view
│   ├── CodeMate in Action.PNG       # Response popup in action
│   └── CodeMate Popup.PNG           # Floating bubble
│
├── Model Training CODE/             # ML pipeline
│   ├── data/                        # Dataset preparation scripts
│   ├── training/                    # QLoRA training scripts (Colab-ready)
│   └── evaluation/                  # CodeBLEU, BLEU, ROUGE-L, Pass@1 eval
│
├── model_results-adpater-data/      # Training artifacts
│   ├── checkpoints/                 # Training checkpoints
│   ├── final_adapter/               # Merged QLoRA adapter weights
│   ├── data/                        # Processed training data
│   └── results/                     # Evaluation results
│
├── codemate_model_pipeline.ipynb    # End-to-end training notebook
├── codemate_Model_pipeline.pdf      # Pipeline documentation
├── GENAIENDSEM.report.pdf           # Academic project report
├── README.md                        # This file
├── guide.md                         # Quick-start guide
└── LICENSE                          # MIT License
```

---

## 📚 Dependencies

### Application
| Package | Purpose |
|---|---|
| `torch` ≥ 2.2 | PyTorch runtime for local model inference |
| `transformers` ≥ 4.40 | HuggingFace model loading + tokenization |
| `peft` ≥ 0.10 | QLoRA adapter loading and merging |
| `bitsandbytes` ≥ 0.43 | 4-bit NF4 quantization (NVIDIA only) |
| `accelerate` ≥ 0.30 | Device mapping + mixed precision |
| `PySide6` ≥ 6.7 | Qt6 desktop UI framework |
| `psutil` ≥ 5.9 | CPU and RAM monitoring |
| `pynvml` ≥ 11.5 | NVIDIA GPU metrics (VRAM, temp) |
| `wikipedia` ≥ 1.4 | Wikipedia API for context enrichment |
| `howdoi` ≥ 2.0 | StackOverflow scraping for code context |
| `pyperclip` ≥ 1.8 | Cross-platform clipboard fallback |
| `platformdirs` ≥ 4.0 | OS-appropriate data directory paths |
| `google-genai` ≥ 1.0 | Gemini API client (optional API backend) |
| `pyinstaller` ≥ 6.0 | Standalone EXE packaging |

---

## ⚙️ Configuration

All configuration is centralized in `config.py`:

| Section | Key Settings |
|---|---|
| **Model** | Base model ID, adapter path, max tokens (512), temperature (0.3), top_p (0.9) |
| **Context** | Max context tokens (300), Wikipedia sentences (2), query timeout (5s), batch sizes |
| **API** | Gemini model (`gemini-2.5-flash`), max tokens (8192) |
| **UI** | Bubble timeout (6s), bubble size (56px), dashboard dimensions (900×620), stats refresh (1s) |
| **Defaults** | Start at startup (off), minimize to tray (on), force CPU (off), API mode (off) |

---

## 💡 Improvement Ideas

> Suggestions for future enhancements — no code changes required.

### High Impact
- **Multi-Language Support** — Currently code detection regex favors Python/JS. Add patterns for Rust, Go, Kotlin, Swift.
- **Conversation History** — Let users scroll through past clipboard analyses in the dashboard, not just the activity log.
- **Image-to-Code** — Accept screenshots of code (OCR via Tesseract or Gemini Vision) alongside clipboard text.
- **Custom Model Training** — Let users fine-tune the adapter on their own codebase for project-specific analysis.

### Medium Impact
- **Hotkey Trigger** — Add a global hotkey (e.g., `Ctrl+Shift+C`) as an alternative to the bubble click.
- **Streaming Response** — Stream tokens to the response popup as they're generated for perceived speed.
- **Multiple Model Support** — Let users switch between different fine-tuned adapters (Python-focused, JS-focused, etc.).
- **Cross-Platform** — Port clipboard monitoring to macOS (NSPasteboard) and Linux (xclip).

### Polish
- **Response Formatting** — Syntax-highlight code blocks in the response popup using QSyntaxHighlighter.
- **Bubble Customization** — Let users choose bubble color, size, and auto-hide timeout.
- **Dark/Light Theme** — Currently dark-only. Add a light theme option.
- **Telemetry Dashboard** — Show inference latency, context enrichment time, and token counts per request.
- **Auto-Update** — Check GitHub releases for new versions on startup.

---

## 👤 Author

**Felix-au** (Harshit Soni)

- 🔗 GitHub: [github.com/Felix-au](https://github.com/Felix-au)
- 📧 Email: [harshit.soni.23cse@bmu.edu.in](mailto:harshit.soni.23cse@bmu.edu.in)

---

<p align="center">
  <sub>Built for developers who want AI help without leaving their flow.</sub>
</p>

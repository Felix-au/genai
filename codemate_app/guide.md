# CodeMate — Quick Guide

An AI-powered desktop code debugger & explainer that lives in your clipboard. Copy code from anywhere — a floating bubble appears — click it for instant AI analysis.

> [!IMPORTANT]
> **Unlike browser-based AI tools** (ChatGPT, Copilot Chat) that require you to context-switch, paste code, and wait, CodeMate **comes to you** — it monitors your clipboard system-wide, appears as a floating bubble, and delivers analysis in a popup. Your code never leaves your machine (local model by default).

## 🚀 How to Run

### Prerequisites
- Python 3.10+
- Windows 10/11
- (Optional) NVIDIA or AMD GPU for faster inference

### Installation

```bash
cd codemate_app
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

On first launch, the base model (~3GB) is auto-downloaded from HuggingFace. Subsequent launches load from cache.

## 🎯 How to Use

1. **Launch CodeMate** — the dashboard opens showing model loading progress.
2. **Wait for "Model ready"** — the status indicator turns green.
3. **Copy any code** — from VS Code, a browser, a terminal, Stack Overflow — anywhere.
4. **Click the floating bubble** — it appears near your cursor within milliseconds.
5. **Read the response** — a popup shows the AI's analysis (bug fix or explanation).
6. **Click Copy** — grab the result and paste it wherever you need it.

> [!NOTE]
> CodeMate auto-detects whether your code has a bug or is clean. Buggy code gets a fix suggestion; clean code gets a step-by-step explanation.

## ⚙ Settings

Access via the ⚙ gear icon on the dashboard:

| Setting | Description |
|---|---|
| **Start at system startup** | Auto-launch CodeMate when Windows boots |
| **Minimize to tray on close** | Close button hides to system tray instead of quitting |
| **Force CPU only** | Bypass GPU detection and run inference on CPU (requires restart) |
| **API Mode** | Switch to Gemini Flash API backend instead of local model (requires API key + restart) |

## 📦 Building an EXE

```bash
cd codemate_app
python build.py
```

Output in `dist/CodeMate/CodeMate.exe` — the LoRA adapter is copied alongside automatically.

## ⚠️ Important Notes

- **Windows-only** — clipboard monitoring uses native Win32 `WM_CLIPBOARDUPDATE` hooks.
- **First launch is slow** — the base model (~3GB) must download from HuggingFace. Subsequent launches load from local cache.
- **GPU auto-detected** — NVIDIA (CUDA + 4-bit quantization), AMD (ROCm + float16), or CPU fallback.
- **Context enrichment** — CodeMate queries Wikipedia and StackOverflow for context before inference. This requires internet but is not mandatory.
- **Pipeline logging** — every request is logged to `log.txt` with full input → context → prompt → response trace.

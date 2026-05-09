# CodeMate — AI Code Debugger & Explainer

A fine-tuned LLM that accepts code (text or image) and automatically:
- **🐛 Debugs** — detects errors/tracebacks and suggests fixes
- **📖 Explains** — generates step-by-step explanations for clean code

## Architecture

```
Input (Text / Image)
    │
    ├─── [Image] → Gemini Flash API → extracted code text
    │
    ▼
CodeGemma-7B-it (4-bit quantized)
    │
    ├── QLoRA adapters (rank=16, α=32)
    │   ~20-50M trainable parameters
    │
    ▼
Output: Bug fix + explanation  OR  Code walkthrough
```

## Project Structure

```
codemate/
├── data/
│   ├── prepare_data.py          # Download & format HuggingFace datasets
│   ├── synthetic_errors.py      # Programmatic bug injection (8 bug types)
│   └── generate_explanations.py # Gemini Flash batch explanation generator
├── training/
│   ├── codemate_train.py        # Full QLoRA training (Colab-ready)
│   └── requirements.txt         # pip dependencies
├── evaluation/
│   ├── eval_metrics.py          # CodeBLEU, BLEU, ROUGE-L, Pass@1
│   └── baseline_comparison.py   # vs Gemini Flash zero/few-shot
├── demo/
│   └── app.py                   # Gradio web UI
└── README.md
```

## Quick Start

### 1. Prepare Data (local)
```bash
cd data
pip install datasets tqdm
python prepare_data.py --output_dir ./processed
python synthetic_errors.py --output ./processed/synthetic_debug.jsonl
# Optional: generate Gemini explanations (needs API key)
export GOOGLE_API_KEY="your-key"
python generate_explanations.py --output ./processed/gemini_explanations.jsonl
```

### 2. Train on Colab
1. Upload `processed/` folder to Google Drive at `MyDrive/codemate/data/`
2. Open `training/codemate_train.py` in Colab (or copy cells)
3. Set runtime to T4 GPU
4. Run all cells (~2 hours)

### 3. Evaluate
```bash
python evaluation/eval_metrics.py \
    --model_dir /content/drive/MyDrive/codemate/final_adapter \
    --test_file /content/drive/MyDrive/codemate/data/test.jsonl
```

### 4. Demo
```bash
python demo/app.py --model_dir /content/drive/MyDrive/codemate/final_adapter
```

## Training Details

| Parameter | Value |
|-----------|-------|
| Base Model | CodeGemma-7B-it |
| Method | QLoRA (4-bit NF4) |
| LoRA Rank | 16 |
| Training Data | ~13K examples |
| Epochs | 3 |
| VRAM Usage | ~12.5 / 15 GB |
| Training Time | ~2 hours on T4 |

## Metrics

| Metric | What it measures |
|--------|-----------------|
| CodeBLEU | Structural code similarity (debug fixes) |
| BLEU | Text similarity (explanations) |
| ROUGE-L | Recall of key phrases |
| Pass@1 | Do suggested fixes actually run? |

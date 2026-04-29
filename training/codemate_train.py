"""
╔══════════════════════════════════════════════════════════════════╗
║              CodeMate — QLoRA Fine-Tuning Script                ║
║          For Google Colab T4 (15GB VRAM, free tier)             ║
╚══════════════════════════════════════════════════════════════════╝

Copy-paste each section into a Colab cell, or upload this file and
run cells with `# %%` markers in VS Code interactive mode.

Base model: google/codegemma-7b-it (swap to 2b-it if OOM)
Method: QLoRA (4-bit NF4 + LoRA rank 16)
Training: ~2 hours on T4 for 13K samples × 3 epochs
"""

# %% ============================================================
# CELL 1: Install Dependencies
# ============================================================

# !pip install -q \
#     torch \
#     transformers>=4.40.0 \
#     peft>=0.10.0 \
#     bitsandbytes>=0.43.0 \
#     trl>=0.8.0 \
#     datasets \
#     accelerate>=0.30.0 \
#     sentencepiece \
#     protobuf \
#     scipy

# %% ============================================================
# CELL 2: Mount Google Drive & Load Data
# ============================================================

import json
import os
import torch
from pathlib import Path
from datasets import Dataset

# --- Mount Google Drive ---
# Uncomment when running in Colab:
# from google.colab import drive
# drive.mount('/content/drive')

# --- Configuration ---
# Change these paths for your setup
CONFIG = {
    # Model
    "base_model": "google/codegemma-7b-it",   # Switch to "google/codegemma-2b-it" if OOM
    "max_seq_length": 1024,                     # Reduce to 512 if tight on VRAM

    # LoRA
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,

    # Training
    "num_epochs": 3,
    "per_device_batch_size": 4,
    "gradient_accumulation_steps": 4,           # effective batch = 16
    "learning_rate": 2e-4,
    "warmup_ratio": 0.03,
    "weight_decay": 0.01,

    # Paths (adjust for your Google Drive layout)
    "data_dir": "/content/drive/MyDrive/codemate/data",
    "output_dir": "/content/drive/MyDrive/codemate/checkpoints",
    "final_model_dir": "/content/drive/MyDrive/codemate/final_adapter",

    # Checkpointing
    "save_steps": 200,
    "save_total_limit": 3,
    "resume_from_checkpoint": True,             # Auto-resume if session died
}

print(f"🔧 Config loaded")
print(f"   Model: {CONFIG['base_model']}")
print(f"   Max seq length: {CONFIG['max_seq_length']}")
print(f"   Effective batch size: {CONFIG['per_device_batch_size'] * CONFIG['gradient_accumulation_steps']}")


# --- Load data ---
def load_jsonl(filepath):
    """Load a JSONL file into a list of dicts."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def load_all_data(data_dir):
    """Load and merge all JSONL files in the data directory."""
    all_data = []
    data_path = Path(data_dir)

    # Load split files
    for filename in ["train.jsonl", "synthetic_debug.jsonl", "gemini_explanations.jsonl"]:
        filepath = data_path / filename
        if filepath.exists():
            records = load_jsonl(str(filepath))
            all_data.extend(records)
            print(f"   Loaded {len(records):,} from {filename}")

    return all_data


print(f"\n📂 Loading data from {CONFIG['data_dir']} ...")
# If data dir doesn't exist, create sample data for testing
if not os.path.exists(CONFIG["data_dir"]):
    print("   ⚠ Data directory not found. Creating sample data for testing...")
    os.makedirs(CONFIG["data_dir"], exist_ok=True)
    sample = [
        {
            "system": "You are CodeMate, an AI code assistant.",
            "instruction": "<CODE>\ndef add(a, b):\n    return a - b\n</CODE>\n<ERROR>\nTest failed: add(2,3) returned -1, expected 5\n</ERROR>",
            "response": "**Mode: DEBUG**\n\nThe function uses `-` instead of `+`.\n\n**Fixed Code:**\n```python\ndef add(a, b):\n    return a + b\n```",
            "task_type": "debug",
        }
    ] * 100  # Repeat for minimum viable training
    with open(os.path.join(CONFIG["data_dir"], "train.jsonl"), 'w') as f:
        for s in sample:
            f.write(json.dumps(s) + '\n')
    print("   → Created 100 sample records for testing")

raw_data = load_all_data(CONFIG["data_dir"])
print(f"\n   Total records: {len(raw_data):,}")

# Task distribution
task_dist = {}
for r in raw_data:
    t = r.get("task_type", "unknown")
    task_dist[t] = task_dist.get(t, 0) + 1
print(f"   Distribution: {task_dist}")

# %% ============================================================
# CELL 3: Format Data for SFT
# ============================================================

def format_for_chat(example):
    """
    Format a data record into the chat template expected by CodeGemma-it.
    Returns the formatted text string.
    """
    system = example.get("system", "You are CodeMate, an AI code assistant.")
    instruction = example.get("instruction", "")
    response = example.get("response", "")

    # CodeGemma instruction-tuned format
    text = (
        f"<start_of_turn>user\n"
        f"{system}\n\n"
        f"{instruction}<end_of_turn>\n"
        f"<start_of_turn>model\n"
        f"{response}<end_of_turn>"
    )
    return {"text": text}


# Convert to HF Dataset
formatted = [format_for_chat(r) for r in raw_data]
dataset = Dataset.from_list(formatted)

# Train/Val split (90/10 of whatever we have)
split = dataset.train_test_split(test_size=0.1, seed=42)
train_dataset = split["train"]
val_dataset = split["test"]

print(f"✅ Dataset ready: {len(train_dataset):,} train / {len(val_dataset):,} val")
print(f"\n📝 Sample formatted text (first 500 chars):")
print(train_dataset[0]["text"][:500])

# %% ============================================================
# CELL 4: Load Model + QLoRA Setup
# ============================================================

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

print("🔄 Loading tokenizer ...")
tokenizer = AutoTokenizer.from_pretrained(
    CONFIG["base_model"],
    trust_remote_code=True,
)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print("🔄 Loading model with 4-bit quantization ...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    CONFIG["base_model"],
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    torch_dtype=torch.float16,
)

# Prepare for k-bit training
model = prepare_model_for_kbit_training(model)

# LoRA config
lora_config = LoraConfig(
    r=CONFIG["lora_r"],
    lora_alpha=CONFIG["lora_alpha"],
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=CONFIG["lora_dropout"],
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)

# Print trainable params
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
total_params = sum(p.numel() for p in model.parameters())
print(f"\n✅ Model loaded")
print(f"   Total params:     {total_params:,}")
print(f"   Trainable params: {trainable_params:,} ({100 * trainable_params / total_params:.2f}%)")

# VRAM check
if torch.cuda.is_available():
    allocated = torch.cuda.memory_allocated() / 1e9
    reserved = torch.cuda.memory_reserved() / 1e9
    total_gpu = torch.cuda.get_device_properties(0).total_mem / 1e9
    print(f"\n   GPU Memory: {allocated:.1f}GB allocated / {total_gpu:.1f}GB total")
    print(f"   Headroom:   {total_gpu - allocated:.1f}GB")

# %% ============================================================
# CELL 5: Train!
# ============================================================

print("🚀 Starting training ...")
print(f"   Epochs: {CONFIG['num_epochs']}")
print(f"   Steps/epoch: ~{len(train_dataset) // (CONFIG['per_device_batch_size'] * CONFIG['gradient_accumulation_steps'])}")
print(f"   Checkpoints saved to: {CONFIG['output_dir']}")

training_args = TrainingArguments(
    output_dir=CONFIG["output_dir"],
    num_train_epochs=CONFIG["num_epochs"],
    per_device_train_batch_size=CONFIG["per_device_batch_size"],
    gradient_accumulation_steps=CONFIG["gradient_accumulation_steps"],
    learning_rate=CONFIG["learning_rate"],
    weight_decay=CONFIG["weight_decay"],
    warmup_ratio=CONFIG["warmup_ratio"],
    lr_scheduler_type="cosine",
    fp16=True,
    logging_steps=25,
    save_steps=CONFIG["save_steps"],
    save_total_limit=CONFIG["save_total_limit"],
    eval_strategy="steps",
    eval_steps=CONFIG["save_steps"],
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    report_to="none",                  # No wandb on free Colab
    optim="paged_adamw_8bit",          # Memory-efficient optimizer
    gradient_checkpointing=True,       # Trade compute for memory
    gradient_checkpointing_kwargs={"use_reentrant": False},
    dataloader_pin_memory=False,
    max_grad_norm=0.3,
    group_by_length=True,              # Batch similar lengths together
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    tokenizer=tokenizer,
    max_seq_length=CONFIG["max_seq_length"],
    dataset_text_field="text",
    packing=True,                      # Pack short examples together
)

# Auto-resume from checkpoint if available
checkpoint = None
if CONFIG["resume_from_checkpoint"]:
    checkpoints = list(Path(CONFIG["output_dir"]).glob("checkpoint-*"))
    if checkpoints:
        checkpoint = str(max(checkpoints, key=os.path.getmtime))
        print(f"   📌 Resuming from: {checkpoint}")

# TRAIN
train_result = trainer.train(resume_from_checkpoint=checkpoint)

print(f"\n✅ Training complete!")
print(f"   Train loss: {train_result.training_loss:.4f}")
print(f"   Train time: {train_result.metrics.get('train_runtime', 0) / 60:.1f} minutes")

# %% ============================================================
# CELL 6: Save Final Adapter
# ============================================================

print(f"💾 Saving final adapter to {CONFIG['final_model_dir']} ...")
model.save_pretrained(CONFIG["final_model_dir"])
tokenizer.save_pretrained(CONFIG["final_model_dir"])
print("✅ Adapter saved!")

# Also save training config for reproducibility
config_path = os.path.join(CONFIG["final_model_dir"], "training_config.json")
with open(config_path, 'w') as f:
    json.dump(CONFIG, f, indent=2)
print(f"   Config saved to {config_path}")

# %% ============================================================
# CELL 7: Quick Test (Inference)
# ============================================================

print("\n🧪 Running inference test ...")

# Test debug prompt
test_debug = """<start_of_turn>user
You are CodeMate, an AI code assistant. Analyze the following code. If there are errors or tracebacks, identify the bug and suggest a corrected version with an explanation. If the code is functional, explain its behavior step-by-step.

<CODE>
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n)
</CODE>
<ERROR>
RecursionError: maximum recursion depth exceeded
</ERROR><end_of_turn>
<start_of_turn>model
"""

# Test explain prompt
test_explain = """<start_of_turn>user
You are CodeMate, an AI code assistant. Analyze the following code. If there are errors or tracebacks, identify the bug and suggest a corrected version with an explanation. If the code is functional, explain its behavior step-by-step.

<CODE>
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
</CODE><end_of_turn>
<start_of_turn>model
"""

for name, prompt in [("DEBUG", test_debug), ("EXPLAIN", test_explain)]:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.1,
        )
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"\n{'='*60}")
    print(f"📋 Test: {name}")
    print(f"{'='*60}")
    print(response[:800])

print("\n🎉 All done! Your CodeMate adapter is saved and ready.")
print(f"   Adapter path: {CONFIG['final_model_dir']}")
print(f"\nNext steps:")
print(f"   1. Run evaluation/eval_metrics.py on the test set")
print(f"   2. Run demo/app.py to launch the Gradio UI")

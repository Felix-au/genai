"""
CodeMate — Data Preparation Pipeline
=====================================
Downloads public HuggingFace datasets, formats them into the unified
CodeMate prompt template, and creates train/val/test JSONL splits.

Run locally or on Colab:
    pip install datasets tqdm
    python prepare_data.py --output_dir ./processed
"""

import json
import random
import argparse
from pathlib import Path
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are CodeMate, an AI code assistant. "
    "Analyze the following code. If there are errors or tracebacks, "
    "identify the bug and suggest a corrected version with an explanation. "
    "If the code is functional, explain its behavior step-by-step."
)

SEED = 42
TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_debug_example(buggy_code: str, error_msg: str, fixed_code: str, explanation: str) -> dict:
    """Format a debug pair into the unified prompt template."""
    user_input = f"<CODE>\n{buggy_code.strip()}\n</CODE>"
    if error_msg:
        user_input += f"\n<ERROR>\n{error_msg.strip()}\n</ERROR>"

    assistant_output = f"**Mode: DEBUG**\n\n{explanation.strip()}\n\n**Fixed Code:**\n```\n{fixed_code.strip()}\n```"

    return {
        "system": SYSTEM_PROMPT,
        "instruction": user_input,
        "response": assistant_output,
        "task_type": "debug",
    }


def format_explain_example(code: str, explanation: str) -> dict:
    """Format an explanation pair into the unified prompt template."""
    user_input = f"<CODE>\n{code.strip()}\n</CODE>"
    assistant_output = f"**Mode: EXPLAIN**\n\n{explanation.strip()}"

    return {
        "system": SYSTEM_PROMPT,
        "instruction": user_input,
        "response": assistant_output,
        "task_type": "explain",
    }


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

def load_code_alpaca(max_samples: int = 3000) -> list[dict]:
    """
    Load CodeAlpaca-20k from HuggingFace.
    Filter for explanation-style instructions.
    """
    from datasets import load_dataset

    print("[*] Loading CodeAlpaca-20k ...")
    ds = load_dataset("sahil2801/CodeAlpaca-20k", split="train")

    explain_keywords = ["explain", "describe", "what does", "how does", "walk through",
                        "step by step", "purpose", "meaning", "logic"]
    debug_keywords = ["fix", "bug", "error", "wrong", "incorrect", "debug", "issue",
                      "problem", "fail", "crash"]

    explain_examples = []
    debug_examples = []

    for row in tqdm(ds, desc="Filtering CodeAlpaca"):
        instruction_lower = row["instruction"].lower()
        code = row.get("input", "") or ""
        output = row.get("output", "") or ""

        if not output or len(output) < 30:
            continue

        # Classify as explain or debug based on instruction keywords
        is_explain = any(kw in instruction_lower for kw in explain_keywords)
        is_debug = any(kw in instruction_lower for kw in debug_keywords)

        if is_explain and code:
            explain_examples.append(format_explain_example(
                code=code if code else row["instruction"],
                explanation=output,
            ))
        elif is_debug:
            # For debug, treat instruction+input as the buggy scenario
            buggy_input = f"{row['instruction']}\n{code}" if code else row["instruction"]
            debug_examples.append(format_debug_example(
                buggy_code=buggy_input,
                error_msg="",
                fixed_code=output,  # The answer is the fix
                explanation=row["instruction"],
            ))
        elif code and len(code) > 50:
            # Generic code instruction → treat as explanation
            explain_examples.append(format_explain_example(
                code=code,
                explanation=output,
            ))

    explain_examples = explain_examples[:max_samples]
    debug_examples = debug_examples[:max_samples // 2]

    print(f"    → {len(explain_examples)} explain + {len(debug_examples)} debug from CodeAlpaca")
    return explain_examples + debug_examples


def load_code_contests(max_samples: int = 2000) -> list[dict]:
    """
    Load code_contests from DeepMind.
    Extract wrong submissions vs correct solutions as debug pairs.
    """
    from datasets import load_dataset

    print("[*] Loading code_contests (this may take a while) ...")
    try:
        ds = load_dataset("deepmind/code_contests", split="train", trust_remote_code=True)
    except Exception as e:
        print(f"    ⚠ Could not load code_contests: {e}")
        print("    → Skipping this source. Use synthetic errors instead.")
        return []

    debug_examples = []

    for row in tqdm(ds, desc="Processing code_contests"):
        if len(debug_examples) >= max_samples:
            break

        # Get wrong and correct solutions
        incorrect = row.get("incorrect_solutions", {})
        correct = row.get("solutions", {})

        if not incorrect or not correct:
            continue

        # Get Python solutions if available
        incorrect_py = []
        correct_py = []

        if isinstance(incorrect, dict):
            langs = incorrect.get("language", [])
            solns = incorrect.get("solution", [])
            for lang, sol in zip(langs, solns):
                if lang in (3, 4) and sol and len(sol) < 2000:  # Python
                    incorrect_py.append(sol)
        
        if isinstance(correct, dict):
            langs = correct.get("language", [])
            solns = correct.get("solution", [])
            for lang, sol in zip(langs, solns):
                if lang in (3, 4) and sol and len(sol) < 2000:
                    correct_py.append(sol)

        if incorrect_py and correct_py:
            debug_examples.append(format_debug_example(
                buggy_code=incorrect_py[0],
                error_msg=f"Problem: {row.get('description', 'N/A')[:300]}",
                fixed_code=correct_py[0],
                explanation="The original solution has a logical error. Here is the corrected version.",
            ))

    print(f"    → {len(debug_examples)} debug pairs from code_contests")
    return debug_examples


def load_python_code_instructions(max_samples: int = 2000) -> list[dict]:
    """
    Load iamtarun/python_code_instructions_18k_alpaca.
    Good source for Python-specific code explanations.
    """
    from datasets import load_dataset

    print("[*] Loading python_code_instructions ...")
    try:
        ds = load_dataset("iamtarun/python_code_instructions_18k_alpaca", split="train")
    except Exception as e:
        print(f"    ⚠ Could not load: {e}")
        return []

    examples = []
    for row in tqdm(ds, desc="Processing python_code_instructions"):
        if len(examples) >= max_samples:
            break
        
        output = row.get("output", "")
        prompt = row.get("prompt", "")
        
        if not output or len(output) < 50:
            continue

        examples.append(format_explain_example(
            code=output,
            explanation=f"This code implements: {prompt}",
        ))

    print(f"    → {len(examples)} explain pairs from python_code_instructions")
    return examples


# ---------------------------------------------------------------------------
# Split & save
# ---------------------------------------------------------------------------

def split_and_save(examples: list[dict], output_dir: Path):
    """Shuffle and split into train/val/test JSONL files."""
    random.seed(SEED)
    random.shuffle(examples)

    n = len(examples)
    train_end = int(n * TRAIN_RATIO)
    val_end = train_end + int(n * VAL_RATIO)

    splits = {
        "train": examples[:train_end],
        "val": examples[train_end:val_end],
        "test": examples[val_end:],
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    for split_name, split_data in splits.items():
        path = output_dir / f"{split_name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for ex in split_data:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
        print(f"[✓] {split_name}: {len(split_data)} examples → {path}")

    # Summary
    task_counts = {}
    for ex in examples:
        t = ex.get("task_type", "unknown")
        task_counts[t] = task_counts.get(t, 0) + 1

    print(f"\n{'='*50}")
    print(f"Total examples: {n}")
    print(f"Task distribution: {task_counts}")
    print(f"Split sizes: train={len(splits['train'])}, val={len(splits['val'])}, test={len(splits['test'])}")
    print(f"{'='*50}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="CodeMate data preparation")
    parser.add_argument("--output_dir", type=str, default="./processed",
                        help="Directory to save JSONL splits")
    parser.add_argument("--skip_contests", action="store_true",
                        help="Skip code_contests (large download)")
    args = parser.parse_args()

    all_examples = []

    # Source 1: CodeAlpaca (fast, reliable)
    all_examples.extend(load_code_alpaca(max_samples=3000))

    # Source 2: Code Contests (may be slow to download)
    if not args.skip_contests:
        all_examples.extend(load_code_contests(max_samples=2000))

    # Source 3: Python code instructions
    all_examples.extend(load_python_code_instructions(max_samples=2000))

    if len(all_examples) < 1000:
        print("\n⚠ WARNING: Very few examples collected. Consider:")
        print("   1. Running synthetic_errors.py to generate more debug pairs")
        print("   2. Running generate_explanations.py for more explain pairs")
        print("   3. Checking your internet connection for dataset downloads")

    # Split and save
    split_and_save(all_examples, Path(args.output_dir))

    print("\n🎯 Next steps:")
    print("   1. Run synthetic_errors.py to add more debug pairs")
    print("   2. Run generate_explanations.py to add Gemini-generated explanations")
    print("   3. Upload processed/ folder to Google Drive")
    print("   4. Run training notebook on Colab")


if __name__ == "__main__":
    main()

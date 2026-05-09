"""
CodeMate — Baseline Comparison
================================
Compare fine-tuned CodeMate vs Gemini Flash (zero-shot & few-shot)
on the same test set. Proves fine-tuning adds value.

Run:
    export GOOGLE_API_KEY="your-key"
    python baseline_comparison.py --test_file test.jsonl --codemate_results eval_results.json
"""

import json
import os
import time
import argparse
from tqdm import tqdm


SYSTEM_PROMPT = (
    "You are CodeMate, an AI code assistant. "
    "Analyze the following code. If there are errors or tracebacks, "
    "identify the bug and suggest a corrected version with an explanation. "
    "If the code is functional, explain its behavior step-by-step."
)

FEW_SHOT_EXAMPLES = [
    {
        "input": "<CODE>\ndef greet(name):\n    print('Hello ' + nam)\n</CODE>\n<ERROR>\nNameError: name 'nam' is not defined\n</ERROR>",
        "output": "**Mode: DEBUG**\n\nTypo: `nam` should be `name`.\n\n**Fixed Code:**\n```python\ndef greet(name):\n    print('Hello ' + name)\n```",
    },
    {
        "input": "<CODE>\ndef square(x):\n    return x ** 2\n</CODE>",
        "output": "**Mode: EXPLAIN**\n\nThis function takes a number `x` and returns its square using the `**` exponentiation operator.",
    },
    {
        "input": "<CODE>\nfor i in range(10)\n    print(i)\n</CODE>\n<ERROR>\nSyntaxError: expected ':'\n</ERROR>",
        "output": "**Mode: DEBUG**\n\nMissing colon after `range(10)`.\n\n**Fixed Code:**\n```python\nfor i in range(10):\n    print(i)\n```",
    },
]


def setup_gemini():
    """Initialize Gemini Flash."""
    import google.generativeai as genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Set GOOGLE_API_KEY. Get free key: https://aistudio.google.com/apikey")
        exit(1)

    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def gemini_zero_shot(model, instruction: str) -> str:
    """Zero-shot: just system prompt + input."""
    prompt = f"{SYSTEM_PROMPT}\n\n{instruction}"
    try:
        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 512, "temperature": 0.1},
        )
        return response.text
    except Exception as e:
        return f"ERROR: {e}"


def gemini_few_shot(model, instruction: str) -> str:
    """Few-shot: system prompt + 3 examples + input."""
    examples_text = ""
    for ex in FEW_SHOT_EXAMPLES:
        examples_text += f"\n---\nInput:\n{ex['input']}\nOutput:\n{ex['output']}\n"

    prompt = f"{SYSTEM_PROMPT}\n\nHere are some examples:{examples_text}\n---\nNow analyze this:\n{instruction}"
    try:
        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 512, "temperature": 0.1},
        )
        return response.text
    except Exception as e:
        return f"ERROR: {e}"


def compute_bleu(preds, refs):
    """Quick BLEU computation."""
    try:
        import sacrebleu
        return sacrebleu.corpus_bleu(preds, [refs]).score / 100.0
    except ImportError:
        return 0.0


def compute_rouge(preds, refs):
    """Quick ROUGE-L computation."""
    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        scores = [scorer.score(r, p)['rougeL'].fmeasure for p, r in zip(preds, refs)]
        return sum(scores) / len(scores) if scores else 0.0
    except ImportError:
        return 0.0


def main():
    parser = argparse.ArgumentParser(description="Baseline comparison")
    parser.add_argument("--test_file", type=str, required=True)
    parser.add_argument("--codemate_results", type=str, default=None,
                        help="Path to CodeMate eval_results.json (optional)")
    parser.add_argument("--max_samples", type=int, default=100)
    parser.add_argument("--output", type=str, default="baseline_comparison.json")
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    # Load test data
    test_data = []
    with open(args.test_file, 'r', encoding='utf-8') as f:
        for line in f:
            test_data.append(json.loads(line))
    test_data = test_data[:args.max_samples]
    print(f"[*] Comparing on {len(test_data)} samples")

    # Setup Gemini
    gemini = setup_gemini()

    # Generate predictions
    zero_preds, few_preds, references = [], [], []

    for sample in tqdm(test_data, desc="Generating baselines"):
        instruction = sample["instruction"]
        ref = sample["response"]
        references.append(ref)

        # Zero-shot
        zero_preds.append(gemini_zero_shot(gemini, instruction))
        time.sleep(args.delay)

        # Few-shot
        few_preds.append(gemini_few_shot(gemini, instruction))
        time.sleep(args.delay)

    # Compute metrics
    results = {
        "zero_shot": {
            "bleu": compute_bleu(zero_preds, references),
            "rouge_l": compute_rouge(zero_preds, references),
        },
        "few_shot": {
            "bleu": compute_bleu(few_preds, references),
            "rouge_l": compute_rouge(few_preds, references),
        },
    }

    # Load CodeMate results if available
    if args.codemate_results and os.path.exists(args.codemate_results):
        with open(args.codemate_results) as f:
            cm = json.load(f)
        results["codemate"] = {
            "bleu": cm.get("bleu", 0),
            "rouge_l": cm.get("rouge_l", 0),
            "codebleu": cm.get("codebleu", 0),
            "pass_at_1": cm.get("pass_at_1", 0),
        }

    # Display comparison table
    print(f"\n{'='*60}")
    print("📊 BASELINE COMPARISON")
    print(f"{'='*60}")
    print(f"{'Model':<25} {'BLEU':>8} {'ROUGE-L':>8}")
    print(f"{'-'*45}")
    print(f"{'Gemini Flash (0-shot)':<25} {results['zero_shot']['bleu']:>8.4f} {results['zero_shot']['rouge_l']:>8.4f}")
    print(f"{'Gemini Flash (3-shot)':<25} {results['few_shot']['bleu']:>8.4f} {results['few_shot']['rouge_l']:>8.4f}")
    if "codemate" in results:
        print(f"{'CodeMate (fine-tuned)':<25} {results['codemate']['bleu']:>8.4f} {results['codemate']['rouge_l']:>8.4f}")
    print(f"{'='*60}")

    # Save
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Results saved to {args.output}")


if __name__ == "__main__":
    main()

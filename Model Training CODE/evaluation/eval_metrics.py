"""
CodeMate — Evaluation Metrics
==============================
Evaluates the fine-tuned CodeMate model on the test set using:
- BLEU (text similarity for explanations)
- ROUGE-L (recall of key phrases)
- CodeBLEU (structural code similarity for debug fixes)
- Pass@1 (does the fix actually run?)

Run on Colab after training:
    python eval_metrics.py --model_dir /content/drive/MyDrive/codemate/final_adapter \
                           --test_file /content/drive/MyDrive/codemate/data/test.jsonl
"""

import json
import argparse
import subprocess
import tempfile
import os
from pathlib import Path

import torch
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(model_dir: str, base_model: str = "google/codegemma-7b-it"):
    """Load the fine-tuned model with QLoRA adapter."""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    print(f"[*] Loading base model: {base_model}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
    )

    print(f"[*] Loading adapter from: {model_dir}")
    model = PeftModel.from_pretrained(base, model_dir)
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer


def generate_response(model, tokenizer, instruction: str, system: str = "") -> str:
    """Generate a response from the model."""
    prompt = (
        f"<start_of_turn>user\n"
        f"{system}\n\n{instruction}<end_of_turn>\n"
        f"<start_of_turn>model\n"
    )

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.1,
        )

    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )
    return response.strip()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_bleu(predictions: list[str], references: list[str]) -> float:
    """Compute corpus BLEU score."""
    try:
        import sacrebleu
        bleu = sacrebleu.corpus_bleu(predictions, [references])
        return bleu.score / 100.0  # Normalize to 0-1
    except ImportError:
        print("⚠ sacrebleu not installed. pip install sacrebleu")
        return 0.0


def compute_rouge(predictions: list[str], references: list[str]) -> dict:
    """Compute ROUGE-L score."""
    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        scores = []
        for pred, ref in zip(predictions, references):
            score = scorer.score(ref, pred)
            scores.append(score['rougeL'].fmeasure)
        return {"rouge_l": sum(scores) / len(scores) if scores else 0.0}
    except ImportError:
        print("⚠ rouge-score not installed. pip install rouge-score")
        return {"rouge_l": 0.0}


def compute_codebleu(predictions: list[str], references: list[str]) -> float:
    """Compute CodeBLEU score for code similarity."""
    try:
        from codebleu import calc_codebleu
        result = calc_codebleu(
            references=references,
            predictions=predictions,
            lang="python",
            weights=(0.25, 0.25, 0.25, 0.25),
        )
        return result["codebleu"]
    except ImportError:
        print("⚠ codebleu not installed. pip install codebleu")
        return 0.0
    except Exception as e:
        print(f"⚠ CodeBLEU error: {e}")
        return 0.0


def compute_pass_at_1(code_predictions: list[str]) -> float:
    """
    Check if predicted code fixes actually run without errors.
    Returns the fraction that execute successfully.
    """
    passes = 0
    total = 0

    for code in code_predictions:
        # Extract code from the response (between ``` markers)
        import re
        code_blocks = re.findall(r'```(?:python)?\n(.*?)```', code, re.DOTALL)
        if not code_blocks:
            continue

        total += 1
        test_code = code_blocks[0]

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_code)
                f.flush()
                result = subprocess.run(
                    ['python', f.name],
                    capture_output=True,
                    timeout=5,
                    text=True,
                )
                if result.returncode == 0:
                    passes += 1
        except (subprocess.TimeoutExpired, Exception):
            pass
        finally:
            try:
                os.unlink(f.name)
            except Exception:
                pass

    return passes / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def extract_code_from_response(response: str) -> str:
    """Extract code blocks from a model response."""
    import re
    blocks = re.findall(r'```(?:python)?\n(.*?)```', response, re.DOTALL)
    return blocks[0].strip() if blocks else response


def main():
    parser = argparse.ArgumentParser(description="Evaluate CodeMate")
    parser.add_argument("--model_dir", type=str, required=True,
                        help="Path to fine-tuned adapter")
    parser.add_argument("--base_model", type=str, default="google/codegemma-7b-it")
    parser.add_argument("--test_file", type=str, required=True,
                        help="Test JSONL file")
    parser.add_argument("--max_samples", type=int, default=200,
                        help="Max test samples (inference is slow)")
    parser.add_argument("--output", type=str, default="eval_results.json",
                        help="Output results file")
    args = parser.parse_args()

    # Load model
    model, tokenizer = load_model(args.model_dir, args.base_model)

    # Load test data
    test_data = []
    with open(args.test_file, 'r', encoding='utf-8') as f:
        for line in f:
            test_data.append(json.loads(line))
    test_data = test_data[:args.max_samples]
    print(f"\n[*] Evaluating on {len(test_data)} test samples")

    # Separate by task type
    debug_data = [d for d in test_data if d.get("task_type") == "debug"]
    explain_data = [d for d in test_data if d.get("task_type") == "explain"]

    print(f"    Debug samples: {len(debug_data)}")
    print(f"    Explain samples: {len(explain_data)}")

    # Generate predictions
    print("\n[*] Generating predictions ...")
    all_predictions = []
    all_references = []

    debug_pred_codes = []
    debug_ref_codes = []
    explain_preds = []
    explain_refs = []

    for sample in tqdm(test_data, desc="Inference"):
        pred = generate_response(
            model, tokenizer,
            instruction=sample["instruction"],
            system=sample.get("system", ""),
        )
        ref = sample["response"]
        all_predictions.append(pred)
        all_references.append(ref)

        if sample.get("task_type") == "debug":
            debug_pred_codes.append(pred)
            debug_ref_codes.append(ref)
        else:
            explain_preds.append(pred)
            explain_refs.append(ref)

    # Compute metrics
    print("\n[*] Computing metrics ...")
    results = {}

    # Overall BLEU
    results["bleu"] = compute_bleu(all_predictions, all_references)
    print(f"   BLEU (overall):    {results['bleu']:.4f}")

    # ROUGE-L
    rouge = compute_rouge(all_predictions, all_references)
    results["rouge_l"] = rouge["rouge_l"]
    print(f"   ROUGE-L (overall): {results['rouge_l']:.4f}")

    # CodeBLEU on debug fixes
    if debug_pred_codes:
        pred_codes = [extract_code_from_response(p) for p in debug_pred_codes]
        ref_codes = [extract_code_from_response(r) for r in debug_ref_codes]
        results["codebleu"] = compute_codebleu(pred_codes, ref_codes)
        print(f"   CodeBLEU (debug):  {results['codebleu']:.4f}")

    # BLEU on explanations only
    if explain_preds:
        results["explain_bleu"] = compute_bleu(explain_preds, explain_refs)
        print(f"   BLEU (explain):    {results['explain_bleu']:.4f}")

    # Pass@1 on debug fixes
    if debug_pred_codes:
        results["pass_at_1"] = compute_pass_at_1(debug_pred_codes)
        print(f"   Pass@1 (debug):    {results['pass_at_1']:.4f}")

    # Save results
    results["num_samples"] = len(test_data)
    results["num_debug"] = len(debug_data)
    results["num_explain"] = len(explain_data)

    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to {args.output}")
    print(f"\n{'='*50}")
    print("📊 SUMMARY")
    print(f"{'='*50}")
    for k, v in results.items():
        if isinstance(v, float):
            print(f"   {k:20s}: {v:.4f}")
        else:
            print(f"   {k:20s}: {v}")


if __name__ == "__main__":
    main()

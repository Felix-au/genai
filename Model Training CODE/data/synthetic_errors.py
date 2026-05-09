"""
CodeMate — Synthetic Error Injection
=====================================
Takes clean Python code and programmatically injects common bugs to create
debug training pairs. Each pair: (buggy_code + error) → (fixed_code + explanation).

Run:
    python synthetic_errors.py --input clean_code.jsonl --output synthetic_debug.jsonl --count 2000
"""

import json
import random
import re
import argparse
from pathlib import Path
from tqdm import tqdm

SEED = 42
random.seed(SEED)

# ---------------------------------------------------------------------------
# Bug injection strategies
# ---------------------------------------------------------------------------

class BugInjector:
    """Collection of programmatic bug injection strategies for Python code."""

    @staticmethod
    def wrong_comparison_operator(code: str) -> tuple[str, str, str] | None:
        """Replace == with = in conditions."""
        pattern = r'(if|elif|while)\s+.*?=='
        match = re.search(pattern, code)
        if match:
            buggy = code.replace('==', '=', 1)
            return (
                buggy,
                "SyntaxError: invalid syntax (assignment in condition)",
                "Used `=` (assignment) instead of `==` (comparison) in a conditional statement."
            )
        return None

    @staticmethod
    def off_by_one_range(code: str) -> tuple[str, str, str] | None:
        """Change range(n) to range(n-1) or range(n+1)."""
        match = re.search(r'range\((\w+)\)', code)
        if match:
            var = match.group(1)
            if var.isdigit():
                new_val = str(int(var) - 1)
                buggy = code.replace(f'range({var})', f'range({new_val})', 1)
                return (
                    buggy,
                    f"Logic error: loop iterates {new_val} times instead of {var}",
                    f"Off-by-one error: `range({new_val})` should be `range({var})` to cover all elements."
                )
        return None

    @staticmethod
    def missing_return(code: str) -> tuple[str, str, str] | None:
        """Remove a return statement."""
        lines = code.split('\n')
        return_indices = [i for i, line in enumerate(lines) if line.strip().startswith('return ')]
        if return_indices:
            idx = return_indices[-1]  # Remove last return
            removed_line = lines[idx]
            buggy_lines = lines[:idx] + lines[idx+1:]
            buggy = '\n'.join(buggy_lines)
            return (
                buggy,
                "Function returns None unexpectedly",
                f"Missing return statement. The line `{removed_line.strip()}` was removed."
            )
        return None

    @staticmethod
    def wrong_variable_name(code: str) -> tuple[str, str, str] | None:
        """Swap a variable name to create a NameError."""
        # Find variable assignments
        assignments = re.findall(r'^(\s*)(\w+)\s*=', code, re.MULTILINE)
        if len(assignments) >= 2:
            var1 = assignments[0][1]
            var2 = assignments[1][1]
            # Replace later usage of var2 with a typo
            typo = var2 + '_typo'
            # Only replace in usage, not in assignment
            lines = code.split('\n')
            replaced = False
            buggy_lines = []
            for line in lines:
                if not replaced and var2 in line and '=' not in line.split(var2)[0][-2:]:
                    buggy_lines.append(line.replace(var2, typo, 1))
                    replaced = True
                else:
                    buggy_lines.append(line)
            if replaced:
                buggy = '\n'.join(buggy_lines)
                return (
                    buggy,
                    f"NameError: name '{typo}' is not defined",
                    f"Typo in variable name: `{typo}` should be `{var2}`."
                )
        return None

    @staticmethod
    def wrong_indentation(code: str) -> tuple[str, str, str] | None:
        """Break indentation of a random indented line."""
        lines = code.split('\n')
        indented = [(i, line) for i, line in enumerate(lines)
                    if line.startswith('    ') and line.strip()]
        if indented:
            idx, line = random.choice(indented)
            buggy_lines = lines.copy()
            buggy_lines[idx] = line.lstrip()  # Remove all indentation
            buggy = '\n'.join(buggy_lines)
            return (
                buggy,
                f"IndentationError: unexpected indent (line {idx + 1})",
                f"Incorrect indentation at line {idx + 1}. The line should be indented inside its block."
            )
        return None

    @staticmethod
    def missing_colon(code: str) -> tuple[str, str, str] | None:
        """Remove colon from def/if/for/while/class statement."""
        pattern = r'^(\s*(?:def|if|elif|else|for|while|class|try|except|finally|with)\b.+):(\s*)$'
        match = re.search(pattern, code, re.MULTILINE)
        if match:
            original = match.group(0)
            buggy_line = original.rstrip().rstrip(':')
            buggy = code.replace(original, buggy_line + match.group(2), 1)
            return (
                buggy,
                "SyntaxError: expected ':'",
                f"Missing colon at the end of the statement: `{buggy_line.strip()}`."
            )
        return None

    @staticmethod
    def wrong_string_quotes(code: str) -> tuple[str, str, str] | None:
        """Introduce mismatched quotes."""
        match = re.search(r'"([^"]*)"', code)
        if match:
            original = match.group(0)
            buggy_str = "'" + match.group(1) + '"'
            buggy = code.replace(original, buggy_str, 1)
            return (
                buggy,
                "SyntaxError: EOL while scanning string literal",
                f"Mismatched quotes: string starts with `'` but ends with `\"`."
            )
        return None

    @staticmethod
    def missing_import(code: str) -> tuple[str, str, str] | None:
        """Remove an import statement."""
        lines = code.split('\n')
        import_lines = [(i, line) for i, line in enumerate(lines)
                        if line.strip().startswith(('import ', 'from '))]
        if import_lines:
            idx, import_line = import_lines[0]
            buggy_lines = [l for i, l in enumerate(lines) if i != idx]
            buggy = '\n'.join(buggy_lines)
            # Extract module name
            module = import_line.strip().split()[-1] if 'import' in import_line else 'module'
            return (
                buggy,
                f"ModuleNotFoundError: No module named '{module}' / NameError: name '{module}' is not defined",
                f"Missing import: `{import_line.strip()}` is needed but was not included."
            )
        return None


# All strategies
ALL_STRATEGIES = [
    BugInjector.wrong_comparison_operator,
    BugInjector.off_by_one_range,
    BugInjector.missing_return,
    BugInjector.wrong_variable_name,
    BugInjector.wrong_indentation,
    BugInjector.missing_colon,
    BugInjector.wrong_string_quotes,
    BugInjector.missing_import,
]


# ---------------------------------------------------------------------------
# Built-in clean code samples (no external dependency needed)
# ---------------------------------------------------------------------------

BUILTIN_CLEAN_CODE = [
    '''def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)''',

    '''def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1''',

    '''def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result''',

    '''import math

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True''',

    '''def flatten(nested_list):
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result''',

    '''class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        if self.is_empty():
            raise IndexError("Pop from empty stack")
        return self.items.pop()

    def peek(self):
        if self.is_empty():
            raise IndexError("Peek at empty stack")
        return self.items[-1]

    def is_empty(self):
        return len(self.items) == 0

    def size(self):
        return len(self.items)''',

    '''def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []''',

    '''def reverse_linked_list(head):
    prev = None
    current = head
    while current:
        next_node = current.next
        current.next = prev
        prev = current
        current = next_node
    return prev''',

    '''def count_words(text):
    words = text.lower().split()
    word_count = {}
    for word in words:
        word = word.strip(".,!?;:")
        if word:
            word_count[word] = word_count.get(word, 0) + 1
    return word_count''',

    '''def matrix_multiply(A, B):
    rows_A = len(A)
    cols_A = len(A[0])
    cols_B = len(B[0])
    result = [[0] * cols_B for _ in range(rows_A)]
    for i in range(rows_A):
        for j in range(cols_B):
            for k in range(cols_A):
                result[i][j] += A[i][k] * B[k][j]
    return result''',

    '''def longest_common_subsequence(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]''',

    '''from collections import deque

def bfs(graph, start):
    visited = set()
    queue = deque([start])
    visited.add(start)
    result = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return result''',
]


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are CodeMate, an AI code assistant. "
    "Analyze the following code. If there are errors or tracebacks, "
    "identify the bug and suggest a corrected version with an explanation. "
    "If the code is functional, explain its behavior step-by-step."
)


def generate_synthetic_debug_pairs(
    clean_codes: list[str],
    target_count: int = 2000,
) -> list[dict]:
    """
    Generate synthetic debug pairs by injecting bugs into clean code.
    Each clean code snippet gets multiple bug variants.
    """
    pairs = []
    attempts = 0
    max_attempts = target_count * 5

    while len(pairs) < target_count and attempts < max_attempts:
        code = random.choice(clean_codes)
        strategy = random.choice(ALL_STRATEGIES)
        attempts += 1

        result = strategy(code)
        if result is None:
            continue

        buggy_code, error_msg, explanation = result

        # Skip if buggy == original (strategy didn't apply)
        if buggy_code.strip() == code.strip():
            continue

        pairs.append({
            "system": SYSTEM_PROMPT,
            "instruction": f"<CODE>\n{buggy_code}\n</CODE>\n<ERROR>\n{error_msg}\n</ERROR>",
            "response": f"**Mode: DEBUG**\n\n{explanation}\n\n**Fixed Code:**\n```python\n{code}\n```",
            "task_type": "debug",
        })

    return pairs


def load_external_code(input_path: str) -> list[str]:
    """Load clean code from a JSONL file (one code snippet per line)."""
    codes = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            code = data.get("code", data.get("output", data.get("content", "")))
            if code and len(code) > 50 and len(code) < 3000:
                codes.append(code)
    return codes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic debug pairs")
    parser.add_argument("--input", type=str, default=None,
                        help="Optional JSONL file with clean code snippets")
    parser.add_argument("--output", type=str, default="./processed/synthetic_debug.jsonl",
                        help="Output JSONL file")
    parser.add_argument("--count", type=int, default=2000,
                        help="Target number of synthetic pairs")
    args = parser.parse_args()

    # Load code: external file or built-in samples
    if args.input and Path(args.input).exists():
        print(f"[*] Loading clean code from {args.input} ...")
        clean_codes = load_external_code(args.input)
        print(f"    → Loaded {len(clean_codes)} code snippets")
    else:
        print("[*] Using built-in clean code samples (12 algorithms)")
        clean_codes = BUILTIN_CLEAN_CODE

    # Generate pairs
    print(f"[*] Generating {args.count} synthetic debug pairs ...")
    pairs = generate_synthetic_debug_pairs(clean_codes, target_count=args.count)
    print(f"    → Generated {len(pairs)} pairs")

    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    print(f"[✓] Saved to {output_path}")

    # Show distribution of bug types
    print("\n📊 Bug type distribution:")
    for strategy in ALL_STRATEGIES:
        name = strategy.__name__
        count = sum(1 for p in pairs if name.replace('_', ' ') in p['response'].lower()
                    or True)  # simplified
        print(f"    {name}")


if __name__ == "__main__":
    main()

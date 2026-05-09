"""
CodeMate — Gemini Flash Explanation Generator
==============================================
Uses Gemini Flash API (free tier) to generate step-by-step code explanations
for clean code snippets. Outputs JSONL for merging into training data.

Setup:
    pip install google-generativeai
    export GOOGLE_API_KEY="your-key-here"

Run:
    python generate_explanations.py --input clean_code.jsonl --output explanations.jsonl --count 1000
"""

import json
import time
import argparse
import os
from pathlib import Path
from tqdm import tqdm

SYSTEM_PROMPT = (
    "You are CodeMate, an AI code assistant. "
    "Analyze the following code. If there are errors or tracebacks, "
    "identify the bug and suggest a corrected version with an explanation. "
    "If the code is functional, explain its behavior step-by-step."
)

EXPLANATION_PROMPT = """Explain the following Python code step-by-step. Be clear and concise.
Cover:
1. What the function/code does (purpose)
2. How it works (algorithm/logic)
3. Key data structures used
4. Time/space complexity if relevant

Code:
```python
{code}
```

Provide a clear, educational explanation suitable for a CS student."""


def setup_gemini():
    """Initialize the Gemini Flash model."""
    try:
        import google.generativeai as genai
    except ImportError:
        print("❌ Install google-generativeai: pip install google-generativeai")
        exit(1)

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Set GOOGLE_API_KEY environment variable")
        print("   Get a free key at: https://aistudio.google.com/apikey")
        exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    return model


def generate_explanation(model, code: str) -> str | None:
    """Generate a code explanation using Gemini Flash."""
    try:
        response = model.generate_content(
            EXPLANATION_PROMPT.format(code=code),
            generation_config={
                "max_output_tokens": 1024,
                "temperature": 0.3,
            }
        )
        return response.text
    except Exception as e:
        print(f"    ⚠ API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Built-in code samples (for standalone usage without external file)
# ---------------------------------------------------------------------------

BUILTIN_SAMPLES = [
    '''def kadane(arr):
    max_sum = current = arr[0]
    for num in arr[1:]:
        current = max(num, current + num)
        max_sum = max(max_sum, current)
    return max_sum''',

    '''def dijkstra(graph, start):
    import heapq
    dist = {node: float('inf') for node in graph}
    dist[start] = 0
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in graph[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                heapq.heappush(pq, (dist[v], v))
    return dist''',

    '''class LRUCache:
    def __init__(self, capacity):
        from collections import OrderedDict
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)''',

    '''def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            if weights[i-1] <= w:
                dp[i][w] = max(dp[i-1][w], dp[i-1][w-weights[i-1]] + values[i-1])
            else:
                dp[i][w] = dp[i-1][w]
    return dp[n][capacity]''',

    '''def topological_sort(graph):
    from collections import deque
    in_degree = {u: 0 for u in graph}
    for u in graph:
        for v in graph[u]:
            in_degree[v] = in_degree.get(v, 0) + 1
    queue = deque([u for u in in_degree if in_degree[u] == 0])
    result = []
    while queue:
        u = queue.popleft()
        result.append(u)
        for v in graph[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
    return result if len(result) == len(graph) else []''',
]


def load_code_from_file(filepath: str) -> list[str]:
    """Load code snippets from JSONL."""
    codes = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            code = data.get("code", data.get("output", data.get("instruction", "")))
            if code and 50 < len(code) < 3000:
                codes.append(code)
    return codes


def main():
    parser = argparse.ArgumentParser(description="Generate code explanations via Gemini Flash")
    parser.add_argument("--input", type=str, default=None,
                        help="JSONL file with code snippets (optional)")
    parser.add_argument("--output", type=str, default="./processed/gemini_explanations.jsonl")
    parser.add_argument("--count", type=int, default=500,
                        help="Max explanations to generate")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds between API calls (rate limiting)")
    args = parser.parse_args()

    # Load code
    if args.input and Path(args.input).exists():
        print(f"[*] Loading code from {args.input} ...")
        codes = load_code_from_file(args.input)
    else:
        print("[*] Using built-in code samples")
        codes = BUILTIN_SAMPLES

    codes = codes[:args.count]
    print(f"    → {len(codes)} code snippets to explain")

    # Setup Gemini
    model = setup_gemini()
    print("[*] Gemini Flash initialized")

    # Generate explanations
    results = []
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Stream results to file (resume-safe)
    existing = set()
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                existing.add(json.loads(line).get("instruction", ""))
        print(f"    → Resuming: {len(existing)} already done")

    with open(output_path, 'a', encoding='utf-8') as f:
        for code in tqdm(codes, desc="Generating explanations"):
            instruction = f"<CODE>\n{code}\n</CODE>"
            if instruction in existing:
                continue

            explanation = generate_explanation(model, code)
            if explanation:
                record = {
                    "system": SYSTEM_PROMPT,
                    "instruction": instruction,
                    "response": f"**Mode: EXPLAIN**\n\n{explanation}",
                    "task_type": "explain",
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                f.flush()
                results.append(record)

            time.sleep(args.delay)  # Rate limiting

    print(f"\n[✓] Generated {len(results)} new explanations → {output_path}")
    print(f"    Total in file: {len(existing) + len(results)}")


if __name__ == "__main__":
    main()

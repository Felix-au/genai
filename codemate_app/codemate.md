# CodeMate — User Guide

> **CodeMate** is an AI-powered desktop assistant that lives in your system tray and watches your clipboard. The moment you copy a piece of code, a small glowing bubble appears on screen. Click it, and CodeMate analyzes your code — finding bugs, explaining logic, and suggesting fixes — all powered by a fine-tuned language model running **entirely on your device**. No cloud. No API keys. No data leaves your machine.

---

## Table of Contents

1. [How It Works — The Big Picture](#how-it-works--the-big-picture)
2. [Application Walkthrough](#application-walkthrough)
3. [Full Pathway #1 — Bug Detection](#full-pathway-1--bug-detection-copy--bubble--context--prompt--response)
4. [Full Pathway #2 — Code Explanation](#full-pathway-2--code-explanation-copy--bubble--context--prompt--response)
5. [Example 1 — Off-by-One Recursion Bug](#example-1--off-by-one-recursion-bug)
6. [Example 2 — Dictionary KeyError](#example-2--dictionary-keyerror)
7. [Example 3 — List Index Out of Range](#example-3--list-index-out-of-range)
8. [Example 4 — Explaining a Working Algorithm](#example-4--explaining-a-working-binary-search)
9. [Example 5 — JavaScript Async/Await Bug](#example-5--javascript-asyncawait-bug)
11. [Dashboard & Settings](#dashboard--settings)
12. [GPU Detection & Performance](#gpu-detection--performance)
13. [Building as Standalone EXE](#building-as-standalone-exe)
14. [Project Summary](#project-summary)

---

## How It Works — The Big Picture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌────────────────┐
│  You copy    │────▶│  Bubble      │───▶│  Context         │───▶│  AI Model    │────▶│  Response      │
│  some code   │     │  appears     │     │  Enrichment      │     │  (on-device) │     │  Popup         │
│  (Ctrl+C)    │     │  (click it!) │     │  (Wikipedia/SO)  │     │  generates   │     │  with fix /    │
│              │     │              │     │                  │     │  answer      │     │  explanation   │
└──────────────┘     └──────────────┘     └──────────────────┘     └──────────────┘     └────────────────┘
```

**In plain English:**

1. **You copy code** — from any editor, terminal, browser, anywhere. CodeMate is always listening in the background.
2. **A glowing cyan bubble appears** — near your cursor. This is CodeMate saying *"I see code — want me to analyze it?"*
3. **You click the bubble** — CodeMate kicks into action.
4. **Context enrichment fires** — behind the scenes, CodeMate extracts key identifiers from your code and searches Wikipedia and StackOverflow for relevant background context. This gives the AI model extra knowledge to work with.
5. **The AI model runs locally** — your code + context are assembled into a prompt and fed to the fine-tuned Qwen2.5-Coder model running on your GPU (or CPU). Nothing leaves your machine.
6. **A response popup appears** — showing the bug analysis, fix, or step-by-step explanation. You can copy the response to your clipboard.

If you don't click the bubble within 6 seconds, it fades away — no interruption.

---

## Application Walkthrough

### Starting CodeMate

When you launch `main.py` (or `CodeMate.exe`), the following happens:

1. The **Dashboard** window opens — showing live GPU stats, system info, and an activity log.
2. A **system tray icon** (cyan/purple circle) appears in your taskbar.
3. The AI model begins **loading in the background** (status bar shows "Loading model…").
4. The **clipboard monitor** starts — listening for code via Windows native events.

Once the model finishes loading, the status dot turns **green** and you're ready to go.

### Closing / Minimizing

- If **"Minimize to tray on close"** is enabled (default), closing the dashboard window just **hides it to the tray**. CodeMate continues running in the background.
- To fully quit, **right-click the tray icon → Quit CodeMate**.
- To reopen the dashboard, **double-click the tray icon** or right-click → Open Dashboard.

### Settings

| Setting | What It Does |
|---|---|
| **Start at system startup** | Adds CodeMate to Windows startup so it launches automatically when you log in. |
| **Minimize to tray on close** | Closing the dashboard hides it instead of quitting. The app stays active in the background. |

> **Note:** Web context enrichment (Wikipedia + StackOverflow lookups) is **always enabled** — every inference automatically searches for relevant context to help the model produce better results.

---

## Full Pathway #1 — Bug Detection (Copy → Bubble → Context → Prompt → Response)

### Step 1: User Copies Buggy Code

You're debugging a Python script. You select this code in VS Code and press **Ctrl+C**:

```python
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n)
```

Your terminal shows:
```
RecursionError: maximum recursion depth exceeded
```

So you also copy the traceback along with the code.

### Step 2: CodeMate Detects Code

CodeMate's clipboard monitor receives the `WM_CLIPBOARDUPDATE` event from Windows. It reads the clipboard text and runs it through the **code detection heuristic**:

- ✅ Contains `def` keyword (+1)
- ✅ Contains `return` keyword (+1)
- ✅ Contains indentation (+1)
- ✅ Contains `RecursionError` traceback (+1)
- **Score: 4 ≥ 2** → This is code!

**The glowing cyan bubble appears near your cursor.**

### Step 3: User Clicks the Bubble

You click the bubble. CodeMate now does two things simultaneously:
- The bubble switches to a **spinning loader** animation.
- The **context enrichment engine** fires up.

### Step 4: Context Enrichment

The enricher extracts identifiers from your code, skipping language keywords like `def`, `return`, `if`:

**Extracted identifiers:** `factorial`, `RecursionError`, `maximum`, `recursion`, `depth`, `exceeded`

Since the code has fewer than 50 meaningful tokens → **1 keyword batch** is created:

| Batch | Query Words |
|---|---|
| Batch 1 | `"factorial RecursionError maximum recursion"` |

**Web queries fire in parallel:**

| Source | Query | Result |
|---|---|---|
| Wikipedia | `"factorial RecursionError maximum recursion"` | `[Wiki:Recursion] Recursion occurs when the definition of a concept or process depends on a simpler or previous version of itself. It is used throughout mathematics and computer science.` |
| StackOverflow (howdoi) | `"factorial RecursionError maximum recursion"` | `[SO] The recursive call should decrement n. Use factorial(n-1) instead of factorial(n).` |

**Assembled context (capped at ~300 tokens):**
```
[Wiki:Recursion] Recursion occurs when the definition of a concept or process depends on a simpler or previous version of itself. It is used throughout mathematics and computer science. | [SO] The recursive call should decrement n. Use factorial(n-1) instead of factorial(n).
```

### Step 5: Prompt Assembly

CodeMate builds the final prompt using the **Qwen2.5 chat template**:

```
<|im_start|>system
You are CodeMate, an AI code assistant. Analyze the following code. If there are errors or tracebacks, identify the bug and suggest a corrected version. If the code is functional, explain its behavior step-by-step.<|im_end|>
<|im_start|>user
<CODE>
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n)

RecursionError: maximum recursion depth exceeded
</CODE>

CONTEXT: [Wiki:Recursion] Recursion occurs when the definition of a concept or process depends on a simpler or previous version of itself. It is used throughout mathematics and computer science. | [SO] The recursive call should decrement n. Use factorial(n-1) instead of factorial(n).<|im_end|>
<|im_start|>assistant
```

### Step 6: Model Inference

The prompt is tokenized and fed to the **Qwen2.5-Coder-1.5B-Instruct + LoRA adapter** running on your GPU. Generation parameters:

| Parameter | Value |
|---|---|
| max_new_tokens | 512 |
| temperature | 0.3 |
| top_p | 0.9 |
| repetition_penalty | 1.1 |

### Step 7: Response Displayed

The model generates a response. The bubble stops spinning and a **response popup** appears:

> **Bug Found: Infinite Recursion**
>
> The recursive call `factorial(n)` never decrements `n`, causing infinite recursion. The function calls itself with the same argument forever until Python's recursion limit is hit.
>
> **Fixed Code:**
> ```python
> def factorial(n):
>     if n == 0:
>         return 1
>     return n * factorial(n - 1)  # n-1, not n
> ```
>
> The fix changes `factorial(n)` to `factorial(n - 1)` so that each recursive call moves closer to the base case `n == 0`.

You can click **📋 Copy** to copy this response, or drag the popup to move it, or click **✕** to dismiss.

---

## Full Pathway #2 — Code Explanation (Copy → Bubble → Context → Prompt → Response)

### Step 1: User Copies Working Code

You're reviewing a colleague's pull request and want to understand what a function does. You copy it:

```python
def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]
```

### Step 2: CodeMate Detects Code

Heuristic check:
- ✅ `def` keyword
- ✅ `return` keyword
- ✅ `for` loop with `:`
- ✅ Indentation
- ✅ Method calls (`.append(`, `.enumerate(`)
- **Score: 5 ≥ 2** → Code detected!

**Bubble appears.**

### Step 3: Click → Context Enrichment

Extracted identifiers: `levenshtein`, `prev_row`, `curr_row`, `insertions`, `deletions`, `substitutions`, `enumerate`, `append`

Code has ~80 tokens → **3 keyword batches**:

| Batch | Query Words |
|---|---|
| Batch 1 (start) | `"levenshtein prev_row curr_row insertions"` |
| Batch 2 (middle) | `"deletions substitutions enumerate"` |
| Batch 3 (end) | `"curr_row append prev_row"` |

**Web results:**

| Source | Query | Result |
|---|---|---|
| Wikipedia | Batch 1 | `[Wiki:Levenshtein distance] The Levenshtein distance is a string metric for measuring the difference between two sequences. It is the minimum number of single-character edits (insertions, deletions, substitutions) required to change one word into the other.` |
| Wikipedia | Batch 2 | *(no relevant result)* |
| Wikipedia | Batch 3 | *(no relevant result)* |
| StackOverflow | Batch 1 | `[SO] Levenshtein uses dynamic programming with two rows to compute edit distance in O(mn) time.` |

**Assembled context:**
```
[Wiki:Levenshtein distance] The Levenshtein distance is a string metric for measuring the difference between two sequences. It is the minimum number of single-character edits required to change one word into the other. | [SO] Levenshtein uses dynamic programming with two rows to compute edit distance in O(mn) time.
```

### Step 4: Final Prompt

```
<|im_start|>system
You are CodeMate, an AI code assistant. Analyze the following code. If there are errors or tracebacks, identify the bug and suggest a corrected version. If the code is functional, explain its behavior step-by-step.<|im_end|>
<|im_start|>user
<CODE>
def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]
</CODE>

CONTEXT: [Wiki:Levenshtein distance] The Levenshtein distance is a string metric for measuring the difference between two sequences. It is the minimum number of single-character edits required to change one word into the other. | [SO] Levenshtein uses dynamic programming with two rows to compute edit distance in O(mn) time.<|im_end|>
<|im_start|>assistant
```

### Step 5: Model Response

> **Code Explanation — Levenshtein Distance**
>
> This function computes the **Levenshtein (edit) distance** between two strings using an optimized dynamic programming approach with only two rows of memory.
>
> **Step-by-step:**
>
> 1. **Line 2-3**: If `s1` is shorter than `s2`, swap them so `s1` is always the longer string. This ensures the algorithm iterates over the longer string in the outer loop.
>
> 2. **Line 4-5**: Base case — if `s2` is empty, the distance is simply the length of `s1` (all insertions).
>
> 3. **Line 6**: Initialize `prev_row` as `[0, 1, 2, ..., len(s2)]`. This represents the edit distances when `s1` is empty.
>
> 4. **Lines 7-13**: For each character `c1` in `s1`:
>    - Start a new row with `i + 1` (cost of deleting all chars so far).
>    - For each character `c2` in `s2`, compute the minimum of:
>      - **Insertion**: `prev_row[j+1] + 1`
>      - **Deletion**: `curr_row[j] + 1`
>      - **Substitution**: `prev_row[j] + (0 if chars match, 1 if not)`
>    - Append the minimum to `curr_row`.
>
> 5. **Line 14**: Promote `curr_row` to become the next `prev_row`.
>
> 6. **Line 15**: Return the last element of the final row — this is the edit distance.
>
> **Complexity:** O(m × n) time, O(n) space.

---

## Example 1 — Off-by-One Recursion Bug

### Copied Code
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n) + fibonacci(n - 1)
```

### Context Enrichment

| Batch | Words | Source | Result |
|---|---|---|---|
| 1 | `"fibonacci"` | Wikipedia | `[Wiki:Fibonacci sequence] Each number is the sum of the two preceding ones: 0, 1, 1, 2, 3, 5, 8, 13…` |

### Final Prompt
```
<|im_start|>system
You are CodeMate, an AI code assistant. Analyze the following code. If there are errors or tracebacks, identify the bug and suggest a corrected version. If the code is functional, explain its behavior step-by-step.<|im_end|>
<|im_start|>user
<CODE>
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n) + fibonacci(n - 1)
</CODE>

CONTEXT: [Wiki:Fibonacci sequence] Each number is the sum of the two preceding ones: 0, 1, 1, 2, 3, 5, 8, 13…<|im_end|>
<|im_start|>assistant
```

### Model Response
> **Bug Found:** The first recursive call should be `fibonacci(n - 1)`, and the second should be `fibonacci(n - 2)`. Currently `fibonacci(n)` calls itself with the same argument, causing infinite recursion.
>
> **Fixed:**
> ```python
> def fibonacci(n):
>     if n <= 1:
>         return n
>     return fibonacci(n - 1) + fibonacci(n - 2)
> ```

---

## Example 2 — Dictionary KeyError

### Copied Code
```python
user_data = {"name": "Alice", "age": 30}
email = user_data["email"]
print(f"Contact: {email}")
```
```
KeyError: 'email'
```

### Context Enrichment

| Batch | Words | Source | Result |
|---|---|---|---|
| 1 | `"user_data email Contact KeyError"` | StackOverflow | `[SO] Use dict.get(key, default) to avoid KeyError when a key might not exist.` |

### Final Prompt
```
<|im_start|>system
You are CodeMate, an AI code assistant. Analyze the following code. If there are errors or tracebacks, identify the bug and suggest a corrected version. If the code is functional, explain its behavior step-by-step.<|im_end|>
<|im_start|>user
<CODE>
user_data = {"name": "Alice", "age": 30}
email = user_data["email"]
print(f"Contact: {email}")

KeyError: 'email'
</CODE>

CONTEXT: [SO] Use dict.get(key, default) to avoid KeyError when a key might not exist.<|im_end|>
<|im_start|>assistant
```

### Model Response
> **Bug Found:** The dictionary `user_data` does not contain the key `"email"`. Accessing it with `[]` raises a `KeyError`.
>
> **Fix — Option A (safe access with default):**
> ```python
> email = user_data.get("email", "N/A")
> ```
>
> **Fix — Option B (check first):**
> ```python
> if "email" in user_data:
>     email = user_data["email"]
> else:
>     email = "not provided"
> ```

---

## Example 3 — List Index Out of Range

### Copied Code
```python
scores = [85, 92, 78, 95, 88]
for i in range(len(scores) + 1):
    print(f"Student {i+1}: {scores[i]}")
```
```
IndexError: list index out of range
```

### Context Enrichment

| Batch | Words | Source | Result |
|---|---|---|---|
| 1 | `"scores Student IndexError range"` | StackOverflow | `[SO] range(len(list)) iterates valid indices. Adding +1 causes an off-by-one error.` |

### Final Prompt
```
<|im_start|>system
You are CodeMate, an AI code assistant. Analyze the following code. If there are errors or tracebacks, identify the bug and suggest a corrected version. If the code is functional, explain its behavior step-by-step.<|im_end|>
<|im_start|>user
<CODE>
scores = [85, 92, 78, 95, 88]
for i in range(len(scores) + 1):
    print(f"Student {i+1}: {scores[i]}")

IndexError: list index out of range
</CODE>

CONTEXT: [SO] range(len(list)) iterates valid indices. Adding +1 causes an off-by-one error.<|im_end|>
<|im_start|>assistant
```

### Model Response
> **Bug Found:** `range(len(scores) + 1)` generates indices `0, 1, 2, 3, 4, 5`. Index `5` is out of bounds for a list with 5 elements (valid indices: 0–4).
>
> **Fixed:**
> ```python
> scores = [85, 92, 78, 95, 88]
> for i in range(len(scores)):    # remove the + 1
>     print(f"Student {i+1}: {scores[i]}")
> ```
>
> Or more Pythonically:
> ```python
> for i, score in enumerate(scores, start=1):
>     print(f"Student {i}: {score}")
> ```

---

## Example 4 — Explaining a Working Binary Search

### Copied Code
```python
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
```

### Context Enrichment

| Batch | Words | Source | Result |
|---|---|---|---|
| 1 | `"binary_search arr target left"` | Wikipedia | `[Wiki:Binary search] Binary search compares the target value to the middle element of the array. If unequal, the half that cannot contain the target is eliminated.` |
| 2 | `"right mid"` | *(no result)* | |

### Final Prompt
```
<|im_start|>system
You are CodeMate, an AI code assistant. Analyze the following code. If there are errors or tracebacks, identify the bug and suggest a corrected version. If the code is functional, explain its behavior step-by-step.<|im_end|>
<|im_start|>user
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
</CODE>

CONTEXT: [Wiki:Binary search] Binary search compares the target value to the middle element of the array. If unequal, the half that cannot contain the target is eliminated.<|im_end|>
<|im_start|>assistant
```

### Model Response
> **Code is functional. Step-by-step explanation:**
>
> 1. **Initialize pointers**: `left = 0`, `right = len(arr) - 1` — the entire array is the search space.
> 2. **Loop** while `left <= right` (search space is non-empty):
>    - Compute `mid = (left + right) // 2` — the middle index.
>    - **If `arr[mid] == target`**: Found it! Return `mid`.
>    - **If `arr[mid] < target`**: Target is in the right half → move `left = mid + 1`.
>    - **Else**: Target is in the left half → move `right = mid - 1`.
> 3. **If loop ends**: Target not found → return `-1`.
>
> **Complexity:** O(log n) time, O(1) space.
>
> **Requires:** The input array `arr` must be **sorted** in ascending order.

---

## Example 5 — JavaScript Async/Await Bug

### Copied Code
```javascript
async function fetchUser(id) {
    const response = fetch(`/api/users/${id}`);
    const data = response.json();
    return data;
}

fetchUser(42).then(user => console.log(user.name));
```
```
TypeError: response.json is not a function
```

### Context Enrichment

| Batch | Words | Source | Result |
|---|---|---|---|
| 1 | `"fetchUser async fetch api"` | Wikipedia | `[Wiki:Ajax (programming)] Asynchronous JavaScript allows web pages to fetch data from a server without reloading.` |
| 2 | `"TypeError response json"` | StackOverflow | `[SO] You must await the fetch() call before calling .json() — fetch returns a Promise, not a Response.` |

### Final Prompt
```
<|im_start|>system
You are CodeMate, an AI code assistant. Analyze the following code. If there are errors or tracebacks, identify the bug and suggest a corrected version. If the code is functional, explain its behavior step-by-step.<|im_end|>
<|im_start|>user
<CODE>
async function fetchUser(id) {
    const response = fetch(`/api/users/${id}`);
    const data = response.json();
    return data;
}

fetchUser(42).then(user => console.log(user.name));

TypeError: response.json is not a function
</CODE>

CONTEXT: [Wiki:Ajax (programming)] Asynchronous JavaScript allows web pages to fetch data from a server without reloading. | [SO] You must await the fetch() call before calling .json() — fetch returns a Promise, not a Response.<|im_end|>
<|im_start|>assistant
```

### Model Response
> **Bug Found:** Missing `await` keywords. `fetch()` returns a **Promise**, not a Response object directly. Without `await`, `response` is a Promise, and `Promise.json` doesn't exist.
>
> **Fixed:**
> ```javascript
> async function fetchUser(id) {
>     const response = await fetch(`/api/users/${id}`);  // await!
>     const data = await response.json();                // await!
>     return data;
> }
> ```
>
> Both `fetch()` and `.json()` are asynchronous and must be awaited.

---

## Dashboard & Settings

The Dashboard is the main window that appears when you launch CodeMate. It shows:

| Section | What You See |
|---|---|
| **Header** | App name, status dot (🟢 green = ready, 🟡 orange = loading, 🔴 red = error), model status text |
| **Gauge Row** | Four animated circular gauges — GPU utilization %, VRAM usage %, CPU %, RAM % |
| **Stat Cards** | GPU name, driver version, VRAM total, model status, compute backend (CUDA/ROCm/CPU), GPU temperature |
| **Activity Log** | Scrollable timeline of everything CodeMate does — clipboard detections, context lookups, inference runs, results |
| **Settings** | Two toggle checkboxes — Startup, Minimize-to-tray |

All gauges animate smoothly — values glide to their new position rather than jumping.

---

## GPU Detection & Performance

CodeMate automatically detects your GPU and picks the best backend:

| GPU Type | Backend Used | Quantization | Expected Speed |
|---|---|---|---|
| **NVIDIA** (any CUDA GPU) | CUDA | 4-bit NF4 (bitsandbytes) | Fast (~2-5s per response) |
| **AMD** (RX 7000/9000 with ROCm) | ROCm | float16 | Medium (~5-10s per response) |
| **No GPU / Unsupported** | CPU | float32 | Slow (~15-30s per response) |

The detection priority is: **NVIDIA → AMD → CPU fallback**. You'll see which backend was selected in the Dashboard's "Compute" stat card.

---

## Building as Standalone EXE

To package CodeMate as a distributable single-file `.exe`:

```bash
cd codemate_app
pip install -r requirements.txt    # ensure all deps are installed
python build.py                    # runs PyInstaller single-file build
```

This produces:
```
dist/
└── CodeMate.exe      # Single-file executable (~200–400MB)
                      # All Python deps + libs bundled inside
```

### What's Bundled Inside the EXE
- Python runtime + all dependencies (torch, transformers, PySide6, peft, bitsandbytes, etc.)
- Application assets (icon)
- All core engine and UI modules

### What Downloads on First Run
- **Base model**: Qwen2.5-Coder-1.5B-Instruct (~3GB) from HuggingFace
  - Cached at `%LOCALAPPDATA%/CodeMate/CodeMate/model_cache/`
  - Subsequent launches load from cache (no internet needed)
- **LoRA adapter** (optional): Place in an `adapter/` folder next to `CodeMate.exe` if available

> **Why not bundle the model?** The base model is ~3GB — bundling it would create an impractically large executable. Instead, it downloads once on first launch and is cached permanently.

---

## How the Context Enrichment Works (Technical Detail)

### Keyword Extraction

CodeMate strips common language keywords (`def`, `return`, `for`, `import`, etc.) and extracts **meaningful identifiers** — the variable names, function names, and error messages that carry semantic meaning.

### Batch Sizing

| Code Length (tokens) | Number of Batches | Words per Batch |
|---|---|---|
| < 50 | 1 | 4 |
| 50 – 200 | 3 (start, middle, end) | 4 |
| > 200 | 5 (evenly distributed) | 4 |

### Query Strategy

Each batch is searched in **parallel** using a thread pool:
- **Wikipedia** — queries up to 3 batches for encyclopedia context (2-sentence summaries)
- **StackOverflow** (via `howdoi`) — queries the first batch for code-specific answers

All queries have a **5-second timeout**. If they fail or return nothing, the model still works — it just won't have the extra context.

### Context Capping

The assembled context is capped at **~300 tokens** (~1,200 characters). This keeps the context concise and avoids overwhelming the actual code in the prompt. The model's attention should be on *your code*, not a wall of Wikipedia text.

---

## Pipeline Logging (`log.txt`)

Every time CodeMate processes a snippet, a detailed log entry is appended to **`log.txt`** in the application root directory (`codemate_app/log.txt`). This file is a permanent record of every pipeline run.

Each entry contains:

```
========================================================================
  CODEMATE PIPELINE LOG — 2026-04-30 03:45:12
========================================================================

── INPUT RECEIVED ──────────────────────────────────────
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n)

RecursionError: maximum recursion depth exceeded

── WEB CRAWLER — KEYWORD BATCHES ───────────────────────
  Batch 1: factorial RecursionError maximum recursion

── WEB CRAWLER — QUERIES & RESPONSES ──────────────────
  [Wikipedia] Query: "factorial RecursionError maximum recursion"
           Result: [Wiki:Recursion] Recursion occurs when the definition of...

  [StackOverflow] Query: "factorial RecursionError maximum recursion"
           Result: [SO] The recursive call should decrement n...

── ASSEMBLED CONTEXT ───────────────────────────────────
[Wiki:Recursion] Recursion occurs when... | [SO] The recursive call...

── FINAL PROMPT ────────────────────────────────────────
<|im_start|>system
You are CodeMate, an AI code assistant...<|im_end|>
<|im_start|>user
<CODE>
def factorial(n):
    ...
</CODE>

CONTEXT: [Wiki:Recursion] ...<|im_end|>
<|im_start|>assistant

── INFERENCE RESPONSE ──────────────────────────────────
**Bug Found: Infinite Recursion**
The recursive call factorial(n) never decrements n...

========================================================================
```

This log is useful for:
- **Debugging** — see exactly what the model received and produced
- **Auditing** — verify context enrichment is finding relevant information
- **Training data** — collect real-world input/output pairs for future fine-tuning

The file grows over time. Delete or archive it whenever you like.

---

## Project Summary

CodeMate is an AI-powered desktop application that monitors the system clipboard for code snippets and provides instant debugging or explanation using a fine-tuned large language model. It runs as a background service on Windows with a floating UI that appears on-demand.

### Inference Backends
- **Local (default)**: Qwen2.5-Coder-1.5B-Instruct with custom QLoRA adapter. Supports NVIDIA CUDA (4-bit NF4 quantization), AMD ROCm (float16), or CPU (float32). Model auto-downloaded from HuggingFace on first launch.
- **API (opt-in)**: Gemini 2.5 Flash via Google GenAI SDK. Configured through the settings dialog. API errors are masked to prevent backend leakage.

### Key Components

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
| **Build Script** | `build.py` | PyInstaller build automation — single-file EXE output. |
| **Build Spec** | `build.spec` | PyInstaller spec file — collects all hidden imports, data files, and bundles into single EXE. |
| **Config** | `config.py` | Centralized configuration — model params, UI settings, API config. Resolves paths for both dev and frozen modes. |

### Model Training Pipeline
The project includes a complete ML training pipeline (in `Model Training CODE/`):
- **Data preparation**: Download from HuggingFace, synthetic bug injection (8 bug types), Gemini-generated explanations
- **Training**: QLoRA fine-tuning on Google Colab T4 (~2 hours, ~13K examples)
- **Evaluation**: CodeBLEU, BLEU, ROUGE-L, Pass@1 metrics with baseline comparison against Gemini Flash zero/few-shot

### Technology Stack
- **Language**: Python 3.10+
- **UI Framework**: PySide6 (Qt6)
- **ML Stack**: PyTorch, HuggingFace Transformers, PEFT (QLoRA), BitsAndBytes (4-bit)
- **GPU Support**: NVIDIA CUDA, AMD ROCm, CPU fallback
- **Web Context**: Wikipedia API, howdoi (StackOverflow)
- **Packaging**: PyInstaller (single-file .exe, all deps bundled)
- **Platform**: Windows 10/11 (Win32 clipboard API)

---

*CodeMate v1.0 — Built with Qwen2.5-Coder-1.5B-Instruct + LoRA fine-tuning*

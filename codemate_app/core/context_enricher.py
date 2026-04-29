"""
╔══════════════════════════════════════════════════════════════╗
║          CodeMate — Web Context Enrichment Engine             ║
╚══════════════════════════════════════════════════════════════╝
Extracts keyword batches from code, queries Wikipedia & howdoi
for concise context to augment the model prompt.
"""

from __future__ import annotations
import logging, re, concurrent.futures
from typing import List
from config import CONTEXT_CONFIG

log = logging.getLogger(__name__)

# Common language keywords to skip during keyword extraction
STOP_WORDS = {
    "def", "class", "import", "from", "return", "if", "elif", "else",
    "for", "while", "try", "except", "finally", "with", "as", "in",
    "not", "and", "or", "is", "none", "true", "false", "self", "cls",
    "print", "len", "range", "int", "str", "float", "list", "dict",
    "set", "tuple", "bool", "type", "pass", "break", "continue",
    "lambda", "yield", "async", "await", "raise", "assert", "del",
    "global", "nonlocal", "const", "let", "var", "function", "new",
    "this", "null", "undefined", "void", "public", "private",
    "static", "final", "abstract", "interface", "extends", "implements",
    "include", "using", "namespace", "std", "cout", "cin", "endl",
}

def _extract_identifiers(code: str) -> List[str]:
    """Extract meaningful identifiers from code, skipping language keywords."""
    tokens = re.findall(r'[a-zA-Z_]\w{2,}', code)
    seen = set()
    result = []
    for t in tokens:
        low = t.lower()
        if low not in STOP_WORDS and low not in seen and not low.startswith("__"):
            seen.add(low)
            result.append(t)
    return result

def extract_keyword_batches(code: str) -> List[str]:
    """Extract keyword batches from code based on length."""
    cfg = CONTEXT_CONFIG["batch_config"]
    identifiers = _extract_identifiers(code)
    if not identifiers:
        return []

    n = len(identifiers)
    wpb = cfg["words_per_batch"]

    if n < cfg["small_threshold"]:
        num_batches = cfg["small_batches"]
    elif n < cfg["medium_threshold"]:
        num_batches = cfg["medium_batches"]
    else:
        num_batches = cfg["large_batches"]

    num_batches = min(num_batches, max(1, n // wpb))
    batches = []
    if num_batches == 1:
        batches.append(" ".join(identifiers[:wpb]))
    else:
        step = max(1, (n - wpb) // (num_batches - 1))
        for i in range(num_batches):
            start = min(i * step, n - wpb)
            batch = identifiers[start:start + wpb]
            if batch:
                batches.append(" ".join(batch))
    return batches


def _query_wikipedia(query: str) -> str:
    """Query Wikipedia for a short summary."""
    try:
        import wikipedia
        wikipedia.set_lang("en")
        results = wikipedia.search(query, results=1)
        if not results:
            return ""
        page = wikipedia.page(results[0], auto_suggest=False)
        sentences = CONTEXT_CONFIG["wikipedia_sentences"]
        summary = ". ".join(page.summary.split(". ")[:sentences])
        return f"[Wiki:{results[0]}] {summary}."
    except Exception as e:
        log.debug(f"Wikipedia query failed for '{query}': {e}")
        return ""

def _query_howdoi(query: str) -> str:
    """Query StackOverflow via howdoi for code context."""
    try:
        from howdoi import howdoi as hdi
        args = {"query": [query], "num_answers": 1, "all": False,
                "pos": 1, "color": False, "explain": False, "json_output": False}
        parser = hdi.get_parser()
        parsed = parser.parse_args(query.split())
        result = hdi.howdoi(parsed)
        if result and len(result.strip()) > 10:
            # Truncate to keep context concise
            lines = result.strip().split("\n")[:5]
            return f"[SO] {chr(10).join(lines)}"
    except Exception as e:
        log.debug(f"howdoi query failed for '{query}': {e}")
    return ""


def enrich_context(code: str) -> dict:
    """
    Main entry: extract keywords from code, query web sources,
    return a dict with structured results for logging.

    Returns:
        {
            "batches": ["word1 word2 ...", ...],
            "queries": [{"source": "Wikipedia"|"StackOverflow", "query": "...", "result": "..."|""}, ...],
            "context": "assembled context string"
        }
    """
    empty = {"batches": [], "queries": [], "context": ""}

    batches = extract_keyword_batches(code)
    if not batches:
        return empty

    log.debug(f"Context enrichment: {len(batches)} keyword batches")
    query_log = []     # structured log of every query
    results = []
    timeout = CONTEXT_CONFIG["query_timeout_seconds"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        # Submit Wikipedia queries
        wiki_futures = {}
        for b in batches[:3]:
            fut = pool.submit(_query_wikipedia, b)
            wiki_futures[fut] = ("Wikipedia", b)

        # Submit StackOverflow query
        so_futures = {}
        if batches:
            fut = pool.submit(_query_howdoi, batches[0])
            so_futures[fut] = ("StackOverflow", batches[0])

        all_futures = {**wiki_futures, **so_futures}
        for future in concurrent.futures.as_completed(all_futures, timeout=timeout + 2):
            source, query = all_futures[future]
            try:
                r = future.result(timeout=timeout)
                query_log.append({"source": source, "query": query, "result": r or "(no result)"})
                if r:
                    results.append(r)
            except Exception:
                query_log.append({"source": source, "query": query, "result": "(timeout/error)"})

    if not results:
        return {"batches": batches, "queries": query_log, "context": ""}

    context = " | ".join(results)
    # Cap at max_context_tokens (rough: 1 token ≈ 4 chars)
    max_chars = CONTEXT_CONFIG["max_context_tokens"] * 4
    if len(context) > max_chars:
        context = context[:max_chars].rsplit(" ", 1)[0] + "…"

    log.debug(f"Context enrichment result: {len(context)} chars")
    return {"batches": batches, "queries": query_log, "context": context}


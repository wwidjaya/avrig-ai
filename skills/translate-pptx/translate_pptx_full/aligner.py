"""aligner.py — Style-follows-word alignment for paragraph translation.

After translation, a separate LLM call maps each translated word back to the
source word index it came from (a simple index-mapping task — far more
reliable than asking the model to maintain inline tags during translation).
The program validates the mapping (coverage + index range, punctuation-
normalized) and applies styles from the aligned source runs.

No string-similarity/cognate heuristics: their confidence scores are not a
valid signal for non-cognate language pairs (Studi~Study score ~0.05), so we
either trust the validated LLM mapping or fall back to positional splitting.
"""

import json
import re
from dataclasses import dataclass


@dataclass
class AlignResult:
    run_indices: list      # per target word: source run_idx
    confidence: float
    method: str            # "llm"


def _source_tokens(runs):
    """Split each run into words tagged with its run index.
    Whitespace-only runs produce no tokens."""
    tokens = []  # list of (word, run_idx)
    for r in runs:
        for w in r.text.split():
            tokens.append((w, r.run_idx))
    return tokens


def _norm(word: str) -> str:
    """Punctuation-normalized form for coverage matching."""
    return re.sub(r"[^\w]", "", word).lower()


ALIGN_MIN_COVERAGE = 0.85   # tolerate omitted function words (the, a, of...)


def align_segment(seg, translated_text, config=None, logger=None, threshold: float = 0.5):
    """Style-follows-word alignment via validated LLM word mapping.
    Returns AlignResult or None (caller falls back to positional splitting)."""
    tokens = _source_tokens(seg.runs)
    words = translated_text.split()
    if not tokens or not words:
        return None
    if config is None:
        return None

    result = _align_llm(seg, tokens, words, config, logger)
    return result


# ── LLM word→index alignment with validation ─────────────────────────────

ALIGN_SYSTEM_PROMPT = (
    "You are a word alignment assistant.\n"
    "Source words are listed with indices. The Translation was produced from "
    "these words. For EACH word in the Translation, find the source word it "
    "was translated from and return its index.\n"
    "Rules:\n"
    "- One source word may map to MULTIPLE translated words.\n"
    "- One translated phrase may combine several source words; assign the "
    "index of the FIRST source word in that phrase.\n"
    "- Output ONLY a JSON array: [{\"translated\": \"word\", \"index\": 3}, ...]\n"
    "- No other text."
)


def _align_llm(seg, tokens, words, config, logger=None):
    from .translator.client import OllamaClient

    client = OllamaClient(
        url=config.ollama_url,
        model=config.model,
        temperature=0.0,
        timeout=config.timeout,
        max_retries=config.max_retries,
    )
    lines = "\n".join(f"  {i}: {w}" for i, (w, _r) in enumerate(tokens))
    user = (
        f"Source words:\n{lines}\n\n"
        f"Translation: {' '.join(words)}\n\n"
        "Return ONLY the JSON array mapping each translated word to its source index."
    )

    try:
        reply = client.translate_batch([
            {"role": "system", "content": ALIGN_SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ])
    except RuntimeError as e:
        if logger:
            logger.debug(f"  LLM alignment request failed: {e}")
        return None

    mapping = _parse_alignment(reply)
    if mapping is None:
        if logger:
            logger.debug("  LLM alignment: could not parse response")
        return None

    expanded = _expand_mapping(mapping)
    if not _validate_mapping(expanded, words, tokens):
        if logger:
            logger.debug("  LLM alignment: mapping failed validation")
        return None

    run_indices = _resolve_indices(expanded, words, tokens)
    if logger:
        logger.debug(f"  LLM alignment accepted ({len(words)} words, {len(run_indices)} indices)")
    return AlignResult(run_indices=run_indices, confidence=0.95, method="llm")


def _resolve_indices(expanded: dict, words: list, tokens: list) -> list:
    """Per-word source run index; unmapped (omitted) function words inherit
    the style of the nearest mapped word."""
    run_indices = []
    for j, w in enumerate(words):
        key = _find_key(expanded, w)
        if key in expanded and 0 <= expanded[key] < len(tokens):
            run_indices.append(tokens[expanded[key]][1])
        else:
            # inherit nearest mapped word (prefer previous, else next)
            inherited = None
            for k in range(j - 1, -1, -1):
                if run_indices[k] is not None:
                    inherited = run_indices[k]
                    break
            if inherited is None:
                for k in range(j + 1, len(words)):
                    kk = _find_key(expanded, words[k])
                    if kk in expanded and 0 <= expanded[kk] < len(tokens):
                        inherited = tokens[expanded[kk]][1]
                        break
            run_indices.append(inherited if inherited is not None else 0)
    return run_indices


def _find_key(expanded: dict, word: str) -> str:
    """Find the mapping key for a target word, tolerating punctuation
    differences on both sides (e.g. '27032,' vs '27032')."""
    if word in expanded:
        return word
    nw = _norm(word)
    for k in expanded:
        if _norm(k) == nw:
            return k
    # allow one-sided punctuation-only difference
    stripped = word.strip(".,;:!?()[]{}\"'")
    if stripped and stripped != word:
        if stripped in expanded:
            return stripped
        ns = _norm(stripped)
        for k in expanded:
            if _norm(k) == ns:
                return k
    return word  # will fail the in-range check in validation


def _parse_alignment(text: str):
    """Parse '[{"translated": "x", "index": 3}, ...]' into
    {translated: source_index} or None."""
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        return None
    try:
        raw = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, list):
        return None
    mapping = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        t = item.get("translated")
        i = item.get("index")
        if isinstance(t, str) and isinstance(i, int):
            mapping[t] = i
    return mapping if mapping else None


def _expand_mapping(mapping: dict) -> dict:
    """Expand merged entries ('cloud services' -> 'cloud' + 'services')."""
    expanded = {}
    for k, i in mapping.items():
        for piece in k.split():
            expanded[piece] = i
    return expanded


def _validate_mapping(expanded: dict, words: list, tokens: list) -> bool:
    """Coverage: most target words map to an in-range source index.
    Tolerates omitted function words (the/a/of...) up to ALIGN_MIN_COVERAGE.
    Punctuation-normalized comparison on both sides."""
    if not words:
        return False
    mapped = 0
    for w in words:
        key = _find_key(expanded, w)
        if key in expanded and 0 <= expanded[key] < len(tokens):
            mapped += 1
    return mapped / len(words) >= ALIGN_MIN_COVERAGE

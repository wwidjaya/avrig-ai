"""Word-aware proportional run splitting.

Translates at paragraph level (grammar coherence), then distributes the
translated words across the original runs proportionally to each run's
original word count, preserving per-run leading/trailing whitespace.
Formatting is never touched — only run text is reassigned.
"""


def split_translation_by_runs(runs, translated_text: str) -> list[str]:
    """
    Distribute `translated_text` across the original runs.

    Args:
        runs: ordered list of RunInfo (or objects with .word_count,
              .leading_ws, .trailing_ws, .text).
        translated_text: the full translated paragraph text.

    Returns:
        list[str]: one text per run (in order), including restored
        leading/trailing whitespace, ready for run.text assignment.
    """
    words = translated_text.split()
    total_words = len(words)

    orig_counts = [r.word_count for r in runs]
    total_orig = sum(orig_counts)

    # Nothing translatable in the original — keep runs untouched.
    if total_orig == 0:
        return [r.text for r in runs]

    result: list[str] = []
    consumed = 0

    for i, r in enumerate(runs):
        if orig_counts[i] == 0:
            # Whitespace-only / empty run: keep original spacing verbatim.
            result.append(r.text)
            continue

        if consumed >= total_words:
            # No more translated words — emit bare whitespace.
            result.append(r.leading_ws + r.trailing_ws)
            continue

        nonempty_after = sum(1 for c in orig_counts[i + 1:] if c > 0)

        if nonempty_after == 0:
            n = total_words - consumed
        else:
            # Reserve one word for each remaining non-empty run.
            proportion = orig_counts[i] / total_orig
            target = round(proportion * total_words)
            n = max(1, min(target, total_words - consumed - nonempty_after))

        run_words = words[consumed:consumed + n]
        consumed += n
        result.append(r.leading_ws + " ".join(run_words) + r.trailing_ws)

    # Safety net: never drop translated words.
    if consumed < total_words:
        extra = " ".join(words[consumed:])
        for j in range(len(result) - 1, -1, -1):
            if orig_counts[j] > 0:
                result[j] = result[j].rstrip() + " " + extra
                break

    return result

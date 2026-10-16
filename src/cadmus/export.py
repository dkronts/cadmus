"""Data factory: aligned (broken -> correct) pairs for fine-tuning and reward models.

Every injected error is a labelled training signal. The clean sentence is the
target, the corrupted sentence is the model input, and the localized span tells
a downstream model exactly where the damage is. This module is model-free: it
only needs the corruption functions, so it runs in CI without stanza.
"""

import random

from .eval.corruptions import corrupt


def diff_span(clean, broken):
    """Contiguous region where clean and broken differ (single-edit corruptions)."""
    i = 0
    while i < len(clean) and i < len(broken) and clean[i] == broken[i]:
        i += 1
    j = 0
    while (j < len(clean) - i and j < len(broken) - i
           and clean[len(clean) - 1 - j] == broken[len(broken) - 1 - j]):
        j += 1
    return {
        "start": i,
        "clean": clean[i:len(clean) - j] if j else clean[i:],
        "broken": broken[i:len(broken) - j] if j else broken[i:],
    }


def generate_pairs(sentences, rng):
    """Turn clean sentences into labelled (broken -> correct) pairs."""
    pairs = []
    for s in sentences:
        result = corrupt(s, rng)
        if not result:
            continue
        broken, rule = result
        if broken == s:
            continue
        span = diff_span(s, broken)
        pairs.append({
            "rule": rule,
            "broken": broken,
            "correct": s,
            "span_start": span["start"],
            "broken_fragment": span["broken"],
            "correct_fragment": span["clean"],
        })
    return pairs


def corpus_pairs(n=200, seed=42):
    """Pairs drawn from the held-out UD-GDT test sentences (downloads the corpus)."""
    from .eval.harness import load_clean_sentences

    rng = random.Random(seed)
    return generate_pairs(load_clean_sentences(n), rng)


def annotate_with_check(pairs, check):
    """Attach cadmus's own verdict to each pair (does the checker catch it?).

    `check` is any callable text -> iterable of violations (injected so this
    module stays stanza-free). A pair counts as caught when a violation's span
    overlaps the corrupted region; the suggestion is the first overlapping
    violation that carries one.
    """
    for p in pairs:
        start = p["span_start"]
        end = start + len(p["broken_fragment"])
        hits = [v for v in check(p["broken"]) if v.start_char < end and v.end_char > start]
        p["detected"] = bool(hits)
        p["detected_rules"] = sorted({v.rule for v in hits})
        p["suggestion"] = next((v.suggestion for v in hits if v.suggestion), None)
    return pairs

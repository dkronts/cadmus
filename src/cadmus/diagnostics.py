"""Diagnostics: how much morphology the analyzer actually exposes.

Rules can only fire on features the tagger emits. This reports, per UPOS, how
often each expected feature is present — low coverage explains silent rules
(e.g. the Greek tagger repairing case to nominative, or omitting Tense).
Pure over word objects, so it is model-free and CI-testable.
"""

from collections import Counter

from .data import feats

EXPECTED_FEATS = {
    "NOUN": ("Gender", "Case", "Number"),
    "PROPN": ("Gender", "Case", "Number"),
    "ADJ": ("Gender", "Case", "Number"),
    "DET": ("Gender", "Case", "Number"),
    "VERB": ("Number", "Person", "Tense"),
}


def coverage(words):
    """Return (present, total) Counters keyed by (UPOS, feature)."""
    present, total = Counter(), Counter()
    for w in words:
        expected = EXPECTED_FEATS.get(w.upos)
        if not expected:
            continue
        f = feats(w)
        for feat in expected:
            total[(w.upos, feat)] += 1
            if feat in f:
                present[(w.upos, feat)] += 1
    return present, total


def coverage_report(sentences):
    present, total = Counter(), Counter()
    for sent in sentences:
        p, t = coverage(sent.words)
        present.update(p)
        total.update(t)
    lines = []
    for key in sorted(total):
        upos, feat = key
        tot, pres = total[key], present[key]
        pct = 100.0 * pres / tot if tot else 100.0
        note = "  <-- low: rules on this feature will under-fire" if pct < 80 else ""
        lines.append(f"{upos:5} {feat:6} {pct:5.1f}% present ({pres}/{tot}){note}")
    return "\n".join(lines) if lines else "no morphologically-typed tokens found"

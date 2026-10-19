"""Evaluation harness: false-positive scan on clean text, recall on injected errors."""

import random
import re
from collections import defaultdict

from ..checker import CadmusChecker
from ..lexicon import ensure_asset
from .corruptions import corrupt

GREEK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")

TARGET_RULES = {
    "det_noun": {"det_noun"},
    "nonword": {"spelling"},
    "accent": {"spelling"},
    "script_mix": {"spelling"},
    "negation": {"negation"},
    "typography": {"typography"},
    "rel_agreement": {"rel_agreement"},
    "num_noun": {"num_noun"},
    # a de-accented proper noun is caught by propn_accent (if stanza keeps it
    # PROPN) or by spelling (if the unaccented form looks like a common word)
    "propn_accent": {"propn_accent", "spelling"},
}


def load_clean_sentences(limit):
    path = ensure_asset("el_gdt-ud-test.conllu")
    out = []
    block = []
    text = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("# text = "):
                text = line[len("# text = "):]
            elif not line and block:
                if text:
                    out.append(text)
                block, text = [], None
                if len(out) >= limit * 3:
                    break
            elif line and not line.startswith("#"):
                block.append(line)
    filtered = []
    for t in out:
        toks = t.split()
        if not (4 <= len(toks) <= 15):
            continue
        greek = [w for w in toks if GREEK_RE.search(w)]
        if len(greek) / len(toks) < 0.9:
            continue
        if any(ch in t for ch in "@/#"):
            continue
        filtered.append(t)
        if len(filtered) >= limit:
            break
    return filtered


def load_sweep_sentences(path=None):
    """Every ``# text = `` line of the conllu file, in file order.

    No length/Greek-ratio/@/# filtering and no limit: this is the full
    456-sentence clean-sweep population behind the RECON numbers."""
    path = path or ensure_asset("el_gdt-ud-test.conllu")
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("# text = "):
                out.append(line[len("# text = "):])
    return out


def run_sweep(checker=None, verbose=False):
    """Full clean sweep: all ``# text =`` sentences through check_batch."""
    checker = checker or CadmusChecker()
    sentences = load_sweep_sentences()

    counts = defaultdict(int)
    samples = defaultdict(list)
    for s, violations in zip(sentences, checker.check_batch(sentences)):
        for v in violations:
            counts[v.rule] += 1
            if len(samples[v.rule]) < 3:
                samples[v.rule].append((s[:60], v.message[:80]))
            if verbose:
                print(f"  [{v.rule}] {s[:70]} -> {v.message[:80]}")

    lines = []
    lines.append(f"sweep: {len(sentences)} sentences, full clean sweep (all # text lines)")
    lines.append("")
    lines.append("violations on clean text:")
    if not counts:
        lines.append("  none")
    for rule in sorted(counts):
        lines.append(f"  {rule:12} {counts[rule]:3}  e.g. {samples[rule][0][1]}")
    damp = checker._damp_stats
    lines.append("")
    lines.append(f"dampener: {damp['suppressed']} flags suppressed by lexicon, {damp['fired']} fired")
    return "\n".join(lines)


def run_eval(n=100, seed=42, verbose=False):
    checker = CadmusChecker()
    sentences = load_clean_sentences(n)
    rng = random.Random(seed)

    fp_counts = defaultdict(int)
    fp_samples = defaultdict(list)
    for s in sentences:
        for v in checker.check(s):
            fp_counts[v.rule] += 1
            if len(fp_samples[v.rule]) < 3:
                fp_samples[v.rule].append((s[:60], v.message[:80]))

    rec_counts = defaultdict(lambda: [0, 0])
    for s in sentences:
        result = corrupt(s, rng)
        if not result:
            continue
        corrupted, target = result
        rec_counts[target][1] += 1
        fired = {v.rule for v in checker.check(corrupted)}
        if fired & TARGET_RULES.get(target, {target}):
            rec_counts[target][0] += 1
        elif verbose:
            print(f"  MISS [{target}]: {corrupted[:70]} -> {sorted(fired)}")

    lines = []
    lines.append(f"eval: {len(sentences)} clean sentences (UD-GDT test), seed={seed}")
    lines.append("")
    lines.append("false positives on clean text:")
    if not fp_counts:
        lines.append("  none")
    for rule in sorted(fp_counts):
        lines.append(f"  {rule:12} {fp_counts[rule]:3}  e.g. {fp_samples[rule][0][1]}")
    lines.append("")
    lines.append("recall on injected errors:")
    for target in sorted(rec_counts):
        hit, tot = rec_counts[target]
        pct = 100.0 * hit / tot if tot else 0.0
        lines.append(f"  {target:12} {hit}/{tot}  ({pct:.0f}%)")
    damp = checker._damp_stats
    lines.append("")
    lines.append(f"dampener: {damp['suppressed']} flags suppressed by lexicon, {damp['fired']} fired")
    return "\n".join(lines)

"""Evaluation harness: false-positive scan on clean text, recall on injected errors."""

import os
import random
import re
from collections import defaultdict

from ..checker import CadmusChecker
from ..lexicon import ensure_asset
from .corruptions import REL_FLIP, NUM_FLIP, corrupt, corrupt_num_noun, corrupt_rel_agreement

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


def _strict_results(texts, results):
    """Pair inputs with checker results, failing loudly if the checker dropped any."""
    texts = list(texts)
    results = list(results)
    if len(results) != len(texts):
        raise ValueError(f"checker returned {len(results)} results for {len(texts)} inputs")
    return zip(texts, results)


def load_clean_sentences(limit, path=None):
    path = path or ensure_asset("el_gdt-ud-test.conllu")
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


def load_targeted_sentences(path=None, forms=None):
    """Sentences bearing at least one target construction, at any length.

    Same ``# text = `` scan as load_sweep_sentences, and the same
    Greek-ratio and ``@/#`` hygiene filters as load_clean_sentences, but the
    4-15 token length filter is skipped: relative clauses and gendered
    numerals live mostly in the long tail. ``forms`` defaults to the
    construction keys of the rel_agreement/num_noun corruptions. No limit.

    The pool intentionally overlaps the length-filtered clean pool used by
    the FP scan and the random recall pass: a 4-15 token sentence bearing a
    REL_FLIP/NUM_FLIP form is returned by both loaders and is touched by both
    the random corrupt() recall pass and the targeted corruptors in a single
    run_eval. This is by design, not double-counting — the targeted pass is a
    construction lens over the same corpus, not a disjoint partition, and
    each pass measures a different question (false positives on clean text,
    random-corruption recall, construction-targeted recall)."""
    path = path or ensure_asset("el_gdt-ud-test.conllu")
    if forms is None:
        forms = set(REL_FLIP) | set(NUM_FLIP)
    patterns = [re.compile(rf"\b{re.escape(f)}\b", re.IGNORECASE) for f in forms]
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.startswith("# text = "):
                continue
            t = line[len("# text = "):]
            toks = t.split()
            if not toks:
                continue
            greek = [w for w in toks if GREEK_RE.search(w)]
            if len(greek) / len(toks) < 0.9:
                continue
            if any(ch in t for ch in "@/#"):
                continue
            if not any(p.search(t) for p in patterns):
                continue
            out.append(t)
    return out


def sweep_tally(pairs, verbose=False):
    """Per-violation tally over (sentence, violations) pairs: (counts, samples) per rule."""
    counts = defaultdict(int)
    samples = defaultdict(list)
    for s, violations in pairs:
        for v in violations:
            counts[v.rule] += 1
            if len(samples[v.rule]) < 3:
                samples[v.rule].append((s[:60], v.message[:80]))
            if verbose:
                print(f"  [{v.rule}] {s[:70]} -> {v.message[:80]}")
    return counts, samples


def run_sweep(checker=None, verbose=False, path=None):
    """Full clean sweep: all ``# text =`` sentences through check_batch."""
    checker = checker or CadmusChecker()
    sentences = load_sweep_sentences(path=path)

    counts, samples = sweep_tally(
        _strict_results(sentences, checker.check_batch(sentences)), verbose=verbose
    )

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


def run_eval(n=100, seed=42, verbose=False, checker=None, targeted=True, targeted_path=None, path=None):
    """False-positive scan on clean text plus recall on injected errors.

    When verbose, printed output is ordered: false-positive violation lines
    first, then recall MISS lines, then targeted recall MISS lines, each group
    under its own section header mirroring the report headings. Empty verbose
    sections print a '  none' marker mirroring the report.

    targeted=False skips the construction-pool recall pass entirely and omits
    its report section; targeted_path overrides the conllu asset it loads.
    path overrides the conllu asset loaded for the FP scan and random recall
    pass.
    """
    checker = checker or CadmusChecker()
    sentences = load_clean_sentences(n, path=path)
    rng = random.Random(seed)

    if verbose:
        print("false positives on clean text:")
    fp_counts, fp_samples = sweep_tally(
        _strict_results(sentences, checker.check_batch(sentences)), verbose=verbose
    )
    if verbose and not fp_counts:
        print("  none")

    rec_counts = defaultdict(lambda: [0, 0])
    pairs = []
    for s in sentences:
        result = corrupt(s, rng)
        if not result:
            continue
        corrupted, target = result
        rec_counts[target][1] += 1
        pairs.append((corrupted, target))

    corrupted_texts = [c for c, _ in pairs]
    results = checker.check_batch(corrupted_texts) if pairs else []
    if verbose:
        print("recall on injected errors:")
    if verbose and not pairs:
        print("  none")
    for i, (corrupted, violations) in enumerate(_strict_results(corrupted_texts, results)):
        target = pairs[i][1]
        fired = {v.rule for v in violations}
        if fired & TARGET_RULES.get(target, {target}):
            rec_counts[target][0] += 1
        elif verbose:
            print(f"  MISS [{target}]: {corrupted[:70]} -> {sorted(fired)}")

    if targeted:
        tgt_counts = defaultdict(lambda: [0, 0])
        tgt_pairs = []
        for s in load_targeted_sentences(path=targeted_path):
            for corrupt_fn in (corrupt_rel_agreement, corrupt_num_noun):
                result = corrupt_fn(s, rng)
                if not result:
                    continue
                corrupted, target = result
                tgt_counts[target][1] += 1
                tgt_pairs.append((corrupted, target))

        tgt_label = os.path.basename(targeted_path) if targeted_path else "construction pool"
        tgt_texts = [c for c, _ in tgt_pairs]
        tgt_results = checker.check_batch(tgt_texts) if tgt_pairs else []
        if verbose:
            print(f"targeted recall ({tgt_label}):")
        if verbose and not tgt_pairs:
            print("  none")
        for i, (corrupted, violations) in enumerate(_strict_results(tgt_texts, tgt_results)):
            target = tgt_pairs[i][1]
            fired = {v.rule for v in violations}
            if fired & TARGET_RULES.get(target, {target}):
                tgt_counts[target][0] += 1
            elif verbose:
                print(f"  MISS [{target}]: {corrupted[:70]} -> {sorted(fired)}")

    label = os.path.basename(path) if path else "UD-GDT test"
    lines = []
    lines.append(f"eval: {len(sentences)} clean sentences ({label}), seed={seed}")
    lines.append("")
    lines.append("false positives on clean text:")
    if not fp_counts:
        lines.append("  none")
    for rule in sorted(fp_counts):
        lines.append(f"  {rule:12} {fp_counts[rule]:3}  e.g. {fp_samples[rule][0][1]}")
    lines.append("")
    lines.append("recall on injected errors:")
    if not rec_counts:
        lines.append("  none")
    for target in sorted(rec_counts):
        hit, tot = rec_counts[target]
        pct = 100.0 * hit / tot if tot else 0.0
        lines.append(f"  {target:12} {hit}/{tot}  ({pct:.0f}%)")
    if targeted:
        lines.append("")
        lines.append(f"targeted recall ({tgt_label}):")
        if not tgt_counts:
            lines.append("  none")
        for target in sorted(tgt_counts):
            hit, tot = tgt_counts[target]
            pct = 100.0 * hit / tot if tot else 0.0
            lines.append(f"  {target:12} {hit}/{tot}  ({pct:.0f}%)")
    damp = checker._damp_stats
    lines.append("")
    lines.append(f"dampener: {damp['suppressed']} flags suppressed by lexicon, {damp['fired']} fired")
    return "\n".join(lines)

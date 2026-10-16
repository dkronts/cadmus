"""Streaming check helper for live-gating (watch mode).

One text per line (e.g. a JSONL log or `tail -f` of an LLM server). The check
callable is injected so this module stays stanza-free and CI-testable.
"""

from .data import filter_violations


def iter_checked(lines, check, min_severity=None, rules=None):
    """Yield (text, violations) for each non-blank line, filtered.

    `check` is any callable text -> iterable of violations. Blank lines are
    skipped so a stream of records with separators does not emit noise.
    """
    for line in lines:
        text = line.rstrip("\n")
        if not text.strip():
            continue
        violations = filter_violations(check(text), min_severity=min_severity, rules=rules)
        yield text, violations

"""Analysis-shadow normalization: typography fixes applied to a copy fed to
the parser, with an offset mapper back to the original text.

Detection stays on the original text (nothing is ever rewritten for the
user); the shadow only gives the analyzer well-formed punctuation and
spacing, so tokenization and sentence segmentation do not degrade on messy
machine output (LLM/STT text with `?`, missing spaces, double spaces)."""

import re

QUESTION_MARK = re.compile(r"\?")
SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?»])")
DOUBLE_SPACE = re.compile(r"  +")
NO_SPACE_AFTER = re.compile(r"[,;:!?](?=[\w«])", re.UNICODE)
ELLIPSIS = re.compile(r"\.\.\.")


def _no_space_after_guards(text, pos):
    ch = text[pos]
    if ch == "." and any(s <= pos < e for s, e in ELLIPSIS.finditer(text)):
        return False
    nxt = text[pos + 1] if pos + 1 < len(text) else ""
    if ch in ",.:" and nxt.isdigit():
        return False
    if ch in ".:" and pos >= 1 and text[pos - 1].isdigit():
        return False
    return True


def normalization_edits(text):
    """Non-overlapping sorted (start, end, replacement) edits for the shadow."""
    raw = []
    for m in QUESTION_MARK.finditer(text):
        if m.start() >= 1 and text[m.start() - 1].isdigit():
            continue
        raw.append((m.start(), m.end(), ";"))
    for m in SPACE_BEFORE_PUNCT.finditer(text):
        raw.append((m.start(), m.end(), m.group(1)))
    for m in DOUBLE_SPACE.finditer(text):
        raw.append((m.start(), m.start() + 1, ""))
    for m in NO_SPACE_AFTER.finditer(text):
        if _no_space_after_guards(text, m.start()):
            raw.append((m.end(), m.end(), " "))
    edits = []
    last_end = -1
    for start, end, repl in sorted(raw):
        if start < last_end:
            continue
        edits.append((start, end, repl))
        last_end = end
    return edits


class OffsetMapper:
    """Maps character offsets in the analysis shadow back to the original."""

    def __init__(self, orig_len, shadow_len, edits):
        self._map = [0] * (shadow_len + 1)
        orig_pos = shadow_pos = 0
        for start, end, repl in edits:
            for i in range(start - orig_pos):
                self._map[shadow_pos + i] = orig_pos + i
            shadow_pos += start - orig_pos
            orig_pos = end
            for i in range(len(repl)):
                self._map[shadow_pos + i] = start
            shadow_pos += len(repl)
        for i in range(orig_len - orig_pos + 1):
            self._map[shadow_pos + i] = orig_pos + i

    def to_orig(self, pos):
        return self._map[pos]

    def span_to_orig(self, start, end):
        return self._map[start], self._map[end]


def normalize_for_analysis(text):
    """Return (shadow_text, mapper). mapper is None when text is clean."""
    edits = normalization_edits(text)
    if not edits:
        return text, None
    parts = []
    pos = 0
    for start, end, repl in edits:
        parts.append(text[pos:start])
        parts.append(repl)
        pos = end
    parts.append(text[pos:])
    shadow = "".join(parts)
    return shadow, OffsetMapper(len(text), len(shadow), edits)

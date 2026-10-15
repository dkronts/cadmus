"""Typography checks: Greek punctuation conventions and spacing (text-level)."""

import re

GREEK_LOWER = re.compile(r"[α-ωάέήίόύώϊϋΐΰ]")
SPACE_BEFORE_PUNCT = re.compile(r"\s+[,.;:!?»]")
NO_SPACE_AFTER = re.compile(r"[,;:!?](?=[\w«])", re.UNICODE)
DOUBLE_SPACE = re.compile(r"  +")
QUESTION_MARK = re.compile(r"\?")
ELLIPSIS = re.compile(r"\.\.\.")


def typography(text, base=0):
    """Returns list of (start, end, message, suggestion) with absolute offsets."""
    out = []
    ellipsis = {m.span() for m in ELLIPSIS.finditer(text)}
    for m in QUESTION_MARK.finditer(text):
        if m.start() >= 1 and text[m.start() - 1].isdigit():
            continue
        out.append((m.start(), m.end(),
                    "TYPOGRAPHY: '?' used as question mark — Greek uses ';'", ";"))
    for m in SPACE_BEFORE_PUNCT.finditer(text):
        out.append((m.start(), m.end(),
                    f"TYPOGRAPHY: space before '{text[m.end() - 1]}'", ""))
    for m in DOUBLE_SPACE.finditer(text):
        out.append((m.start(), m.start() + 1, "TYPOGRAPHY: double space", ""))
    for m in NO_SPACE_AFTER.finditer(text):
        if m.group(0)[0] == "." and any(s <= m.start() < e for s, e in ellipsis):
            continue
        ch = m.group(0)[0]
        nxt = text[m.end()] if m.end() < len(text) else ""
        if ch in ",.:" and nxt.isdigit():
            continue
        if ch in ".:" and m.start() >= 1 and text[m.start() - 1].isdigit():
            continue
        out.append((m.start(), m.end(), f"TYPOGRAPHY: missing space after '{ch}'", ""))
    for m in re.finditer(r"(?<=[.!?])\s+(\S)", text):
        ch = m.group(1)
        if GREEK_LOWER.match(ch):
            pos = m.start(1)
            out.append((pos, pos + 1,
                        "TYPOGRAPHY: sentence starts with a lowercase letter", ""))
    return [(s + base, e + base, msg, sug) for s, e, msg, sug in out]

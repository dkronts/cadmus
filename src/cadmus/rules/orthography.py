"""Orthography rules: non-words, accent errors, script mixing."""

import re

from .. import orthography

_ABBREV_RE = re.compile(r"[.,'’]|\s")


def _abbrev_or_elided(text):
    return bool(_ABBREV_RE.search(text))


_ACCENTED = "άέήίόύώΐΰ"


def _coverage_known(text, env):
    """Surface-form membership in the per-sentence env lexicons (UD-train
    forms + Wikipedia/UD PROPN surfaces) — coverage hunspell lacks.

    PROPN coverage is consulted only for accented tokens: the title dump
    holds unaccented variants (`απο`, `βορεια`) that are homographic with
    de-accented common words, so an unaccented match is ambiguous and stays
    flagged (same precision-first rule as `PropnLexicon.accent_suggestion`)."""
    f = text.lower()
    lex = env.get("lexicon")
    if lex is not None and f in lex.entries:
        return True
    propn = env.get("propn")
    if (propn is not None and any(c in _ACCENTED for c in f)
            and f in propn.forms):
        return True
    return False


def spelling(sent, by_id, env):
    out = []
    for w in sent.words:
        if w.upos in ("PUNCT", "SYM", "NUM"):
            continue
        if w.text.isupper() and len(w.text) >= 2:
            continue
        if not orthography.is_checkable(w.text):
            continue
        if orthography.is_script_mixed(w.text):
            out.append((w, w, f"SCRIPT-MIX: '{w.text}' mixes Greek and Latin characters"))
            continue
        if _abbrev_or_elided(w.text):
            continue
        if w.upos in ("X", "PROPN"):
            continue
        if orthography.is_known(w.text):
            continue
        if _coverage_known(w.text, env):
            continue
        kind, suggestions = orthography.classify_unknown(w.text)
        if kind == "accent":
            out.append((w, w, f"ACCENT: '{w.text}' → '{suggestions[0]}' (accent/diacritic error)",
                        suggestions[0]))
        elif suggestions:
            out.append((w, w,
                        f"NONWORD: '{w.text}' (unknown word; suggestions: {', '.join(suggestions)})",
                        suggestions[0]))
        else:
            out.append((w, w, f"NONWORD: '{w.text}' (unknown word)"))
    return out

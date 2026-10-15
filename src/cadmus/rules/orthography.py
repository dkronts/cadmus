"""Orthography rules: non-words, accent errors, script mixing."""

from .. import orthography


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
        if w.upos in ("X", "PROPN"):
            continue
        if orthography.is_known(w.text):
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

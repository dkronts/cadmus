"""Proper-noun accent rule: mis-accented place/person names via a title lexicon."""

from .. import orthography


def propn_accent(sent, by_id, env):
    lex = env.get("propn")
    if lex is None:
        return []
    out = []
    for w in sent.words:
        if w.upos != "PROPN":
            continue
        if not orthography.is_checkable(w.text) or orthography.is_script_mixed(w.text):
            continue
        sug = lex.accent_suggestion(w.text)
        if sug:
            out.append((w, w,
                        f"ACCENT-PROPN: '{w.text}' → '{sug}' (proper-noun accent)", sug))
    return out

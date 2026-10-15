"""Government rules: prepositional case government."""

from ..data import AMBIGUOUS_PREPS, GEN_PREPS, feats

FIXED_GEN_EXCEPTIONS = {"κοινού"}


def prep_case(sent, by_id, env):
    out = []
    for w in sent.words:
        if w.deprel != "case" or w.upos != "ADP":
            continue
        h = by_id.get(w.head)
        if not h or h.upos not in ("NOUN", "PROPN", "PRON"):
            continue
        low = w.text.lower()
        if low in AMBIGUOUS_PREPS:
            continue
        want = "Gen" if low in GEN_PREPS else "Acc"
        got = feats(h).get("Case")
        if got and got != want and h.text.lower() not in FIXED_GEN_EXCEPTIONS:
            out.append((w, h, f"PREP-CASE: '{w.text}' wants {want}, '{h.text}' is {got}"))
    return out

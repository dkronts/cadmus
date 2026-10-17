"""Government rules: prepositional case government."""

from ..data import AMBIGUOUS_PREPS, GEN_PREPS, feats

FIXED_GEN_EXCEPTIONS = {"κοινού"}


def prep_case(sent, by_id, env):
    out = []
    lex = env.get("lexicon")
    nominal_cases = getattr(lex, "nominal_cases", None)
    for w in sent.words:
        if w.deprel != "case" or w.upos != "ADP":
            continue
        h = by_id.get(w.head)
        if not h or h.upos not in ("NOUN", "PROPN", "PRON"):
            continue
        low = w.text.lower()
        if low in AMBIGUOUS_PREPS:
            continue
        got = feats(h).get("Case")
        if got == "Dat":
            # fossilized dative survives only in fixed expressions (εν τάξει)
            continue
        if h.upos == "PRON":
            # weak/relative pronoun Case from the tagger is noise-prone
            continue
        if nominal_cases is not None and not nominal_cases(h.text):
            # head form attested nowhere: its Case rests on no evidence
            continue
        want = "Gen" if low in GEN_PREPS else "Acc"
        if got and got != want and h.text.lower() not in FIXED_GEN_EXCEPTIONS:
            out.append((w, h, f"PREP-CASE: '{w.text}' wants {want}, '{h.text}' is {got}"))
    return out

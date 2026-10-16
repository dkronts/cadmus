"""Morphology rules that must bypass the tagger's case/tense repair.

The Greek tagger silently *repairs* errors: it re-tags an accusative copula
predicate ("Είναι γιατρό") as nominative, and assigns Tense inconsistently after
να. So these rules decide from the *surface form* (and reliable Gender/Number),
never from the tagger's Case/Tense.
"""

import unicodedata

from ..data import feats

COP_LEMMAS = {"είμαι", "γίνομαι", "είσμαι"}


def _deaccent(s):
    d = unicodedata.normalize("NFD", s)
    return unicodedata.normalize("NFC", "".join(c for c in d if not unicodedata.combining(c)))


def _masc_oblique(form, f):
    """True if a masculine NOUN surface form can only be an oblique (acc) case.

    A masculine nominative singular ends in -ς and a plural in -οι/-εις/-ες, so a
    masc form ending in -ο (sg) / -ους (pl) is never a nominative predicate."""
    if f.get("Gender") != "Masc":
        return False
    g = _deaccent(form.lower())
    if f.get("Number") == "Sing":
        return g.endswith("ο")
    if f.get("Number") == "Plur":
        return g.endswith("ους")
    return False


def copula_pred(sent, by_id, env):
    """Copula predicate must be nominative; flag masculine nouns in accusative."""
    out = []
    for w in sent.words:
        if w.upos not in ("VERB", "AUX") or (w.lemma or "").lower() not in COP_LEMMAS:
            continue
        pred = None
        if w.deprel == "cop":
            h = by_id.get(w.head)
            if h and h.upos == "NOUN":
                pred = h
        else:
            for c in sent.words:
                if c.head == w.id and c.deprel == "nsubj" and c.upos == "NOUN":
                    pred = c
                    break
        if pred is not None and _masc_oblique(pred.text, feats(pred)):
            pf = feats(pred)
            subj = next((c for c in sent.words
                         if c.head == pred.id and c.deprel == "nsubj"
                         and c.upos in ("NOUN", "PROPN")), None)
            if subj is not None:
                sg = feats(subj).get("Gender")
                if sg and pf.get("Gender") and sg != pf["Gender"]:
                    continue  # predicate gender contradicts its subject -> tagger mis-tagged, skip
            out.append((pred, w,
                        f"COPULA-PRED: '{pred.text}' is accusative, but a copula "
                        f"predicate must be nominative"))
    return out


def na_form(sent, by_id, env):
    """να must be followed by a dependent (non-past) verb form, not a past indicative."""
    vf = env.get("verbforms")
    if vf is None:
        return []
    out = []
    for w in sent.words:
        if w.upos not in ("VERB", "AUX"):
            continue
        has_na = any(c.deprel == "aux" and (c.lemma or "").lower() == "να" and c.head == w.id
                     for c in sent.words)
        if has_na and vf.illegal_after_na(w.text):
            out.append((w, w,
                        f"NA-FORM: '{w.text}' is a past indicative, but να requires "
                        f"a dependent (non-past) verb form"))
    return out

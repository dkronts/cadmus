"""Negation selection: δε(ν) with indicative, μη(ν) with subjunctive/imperative.

Greek subjunctive is analytic (να/ας/μήπως + dependent form) and stanza does
not mark Mood=Sub, so context is detected positionally: a marker immediately
before the negator. Imperatives are recognized by the absence of both Tense
and Mood.
"""

from ..data import feats


def _subjunctive_context(words, i):
    window = words[max(0, i - 2):i]
    return any(x.text.lower() in ("να", "ας", "μήπως") for x in window)


def _verb_after(words, i):
    for x in words[i + 1:]:
        if x.upos == "PUNCT":
            return None
        if x.upos in ("VERB", "AUX"):
            f = feats(x)
            if "Mood" in f or "Tense" in f or f.get("VerbForm") == "Fin":
                return x
    return None


def negation(sent, by_id, env):
    out = []
    words = sent.words
    for i, w in enumerate(words):
        low = w.text.lower()
        if low not in ("δεν", "μην"):
            continue
        verb = _verb_after(words, i)
        if verb is None:
            continue
        f = feats(verb)
        sub = _subjunctive_context(words, i)
        imperative = "Mood" not in f and "Tense" not in f
        if low == "δεν" and (sub or imperative):
            out.append((w, verb, f"NEGATION: 'δεν' with non-indicative '{verb.text}' — expected 'μην'"))
        elif low == "μην" and not sub and not imperative and "Tense" in f:
            out.append((w, verb, f"NEGATION: 'μην' with indicative '{verb.text}' — expected 'δεν'"))
    return out

"""Agreement rules: determiner-noun, adjective-noun, subject-verb, copula predicate."""

from ..data import (
    DEFINITE_ARTICLES, HETEREOCLITE_PLURALS, conj_closure, feats,
    has_own_determiner,
)
from ..orthography import strip_accents

AGREEMENT_FEATURES = ("Gender", "Case", "Number")

# Gendered, agreeing numeral forms (nom/acc of 3 and 4), keyed by de-accented
# lowercase form. The tagger *repairs* a numeral's Gender to match its noun, so
# the numeral's true gender comes from its surface form, not its feats.
NUM_GENDER = {
    "τρεις": {"Masc", "Fem"},
    "τεσσερις": {"Masc", "Fem"},
    "τρια": {"Neut"},
    "τεσσερα": {"Neut"},
}
NUM_CORRECT = {
    "τρεις": {"Neut": "τρία"},
    "τεσσερις": {"Neut": "τέσσερα"},
    "τρια": {"Masc": "τρεις", "Fem": "τρεις"},
    "τεσσερα": {"Masc": "τέσσερις", "Fem": "τέσσερις"},
}


def _effective_gender(word, feats, env):
    lex = env.get("lexicon")
    if lex is not None and word.upos == "NOUN":
        return lex.resolve_gender(word)
    return feats.get("Gender")


def _det_gender(w, f, env):
    lex = env.get("lexicon")
    if lex is not None:
        paradigm = lex.resolve_det_gender(w)
        if paradigm is not None:
            return paradigm
    return f.get("Gender")


def _form_feats_gate(lex, h, k, det_val):
    """True when the noun's surface form supports the article's reading.

    Form-level attestation from the treebank, applied to Case/Number only:
    if the form is attested (as NOUN/PROPN) with the article's value, the
    mismatch is analyzer noise on a case/number-syncretic form, not an error
    (Gender is exempt: the corruption target swaps article gender, and
    dual-gender-attested forms would lose real detections)."""
    if k not in ("Case", "Number"):
        return False
    ff = getattr(lex, "form_feats", None)
    if ff is None:
        return False
    attested = ff(h.text).get(k)
    if not attested:
        return False
    return det_val in attested


def det_noun(sent, by_id, env):
    out = []
    lex = env.get("lexicon")
    for w in sent.words:
        if w.deprel != "det":
            continue
        h = by_id.get(w.head)
        if not h or h.upos not in ("NOUN", "PROPN"):
            continue
        f, hf = feats(w), feats(h)
        if _heteroclite_escape(w, h, f, hf):
            continue
        noun_gender = _effective_gender(h, hf, env)
        det_gender = _det_gender(w, f, env)
        target = DEFINITE_ARTICLES.get(
            (noun_gender or hf.get("Gender"), hf.get("Number"), hf.get("Case"))
        )
        for k in AGREEMENT_FEATURES:
            noun_val = noun_gender if k == "Gender" else hf.get(k)
            det_val = det_gender if k == "Gender" else f.get(k)
            if det_val is not None and noun_val is not None and det_val != noun_val:
                if lex is not None and _form_feats_gate(lex, h, k, det_val):
                    continue
                msg = f"DET-NOUN {k}: '{w.text}'[{det_val}] vs '{h.text}'[{noun_val}]"
                out.append((w, h, msg, f"«{target}»") if target else (w, h, msg))
    return out


def _heteroclite_escape(det, noun, det_f, noun_f):
    if det_f.get("Number") != "Plur" or "Gender" not in det_f:
        return False
    article_gender = HETEREOCLITE_PLURALS.get(noun.lemma or "")
    return (
        bool(article_gender)
        and det_f["Gender"] == article_gender
        and noun_f.get("Number") == "Plur"
    )


def adj_noun(sent, by_id, env):
    out = []
    for w in sent.words:
        if w.deprel != "amod":
            continue
        h = by_id.get(w.head)
        if not h or h.upos not in ("NOUN", "PROPN"):
            continue
        f, hf = feats(w), feats(h)
        if f.get("Case") and hf.get("Case") and f["Case"] != hf["Case"]:
            continue
        noun_gender = _effective_gender(h, hf, env)
        for k in AGREEMENT_FEATURES:
            noun_val = noun_gender if k == "Gender" else hf.get(k)
            if k in f and noun_val is not None and f[k] != noun_val:
                out.append((w, h, f"ADJ-NOUN {k}: '{w.text}'[{f[k]}] vs '{h.text}'[{noun_val}]"))
    return out


def num_noun(sent, by_id, env):
    """A gendered numeral (τρεις/τρία, τέσσερις/τέσσερα) must match its noun's gender.

    The tagger repairs the numeral's Gender to agree, so the numeral's true
    gender is read from its surface form; only the noun's gender is trusted.
    """
    out = []
    for w in sent.words:
        if w.upos != "NUM" or w.deprel != "nummod":
            continue
        key = strip_accents(w.text.lower())
        allowed = NUM_GENDER.get(key)
        if not allowed:
            continue
        h = by_id.get(w.head)
        if not h or h.upos not in ("NOUN", "PROPN"):
            continue
        noun_gender = _effective_gender(h, feats(h), env)
        if noun_gender and noun_gender not in allowed:
            sug = NUM_CORRECT.get(key, {}).get(noun_gender)
            msg = (f"NUM-NOUN Gender: '{w.text}' (only {'/'.join(sorted(allowed))}) "
                   f"vs noun '{h.text}'[{noun_gender}]")
            out.append((w, h, msg, sug) if sug else (w, h, msg))
    return out


def subj_verb(sent, by_id, env):
    out = []
    for w in sent.words:
        if w.deprel != "nsubj":
            continue
        h = by_id.get(w.head)
        if not h or h.deprel != "root" or h.upos not in ("VERB", "AUX", "ADJ"):
            continue
        f, hf = feats(w), feats(h)
        members = conj_closure(w, by_id)
        coordinated = len(members) > 1 and all(has_own_determiner(m, by_id) for m in members)
        if "Number" in f and "Number" in hf and f["Number"] != hf["Number"]:
            plural_licensed = hf["Number"] == "Plur" and coordinated
            if not plural_licensed:
                out.append((w, h, f"SUBJ-VERB Number: '{w.text}'[{f['Number']}] vs '{h.text}'[{hf['Number']}]"))
        if hf.get("Person") in ("1", "2") and w.upos != "PRON":
            out.append((w, h, f"SUBJ-VERB Person: verb '{h.text}' is {hf['Person']}p but subject '{w.text}' is not a pronoun"))
    return out


def _relcl_ancestor(w, by_id):
    """Nearest ancestor (or self) heading an acl:relcl clause, else None."""
    seen = set()
    cur = w
    while cur is not None and cur.id not in seen:
        seen.add(cur.id)
        if cur.deprel == "acl:relcl":
            return cur
        if cur.head == 0:
            return None
        cur = by_id.get(cur.head)
    return None


def rel_agreement(sent, by_id, env):
    """'ο οποίος' must agree with its antecedent in Gender+Number (Case is free)."""
    out = []
    for w in sent.words:
        f = feats(w)
        if f.get("PronType") != "Rel" or (w.lemma or "").lower() != "οποίος":
            continue
        relcl = _relcl_ancestor(w, by_id)
        if not relcl:
            continue
        ant = by_id.get(relcl.head)
        if not ant or ant.upos not in ("NOUN", "PROPN"):
            continue
        af = feats(ant)
        ant_gender = _effective_gender(ant, af, env)
        for k in ("Gender", "Number"):
            wv = f.get(k)
            av = ant_gender if k == "Gender" else af.get(k)
            if wv and av and wv != av:
                out.append((w, ant,
                            f"REL-ANT {k}: relative pronoun '{w.text}'[{wv}] vs antecedent '{ant.text}'[{av}]"))
    return out

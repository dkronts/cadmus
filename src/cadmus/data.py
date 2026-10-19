"""Morphological feature utilities and static linguistic data for Modern Greek."""

GEN_PREPS = {
    "λόγω", "εκτός", "έναντι", "ένεκα", "αντί", "διά", "προ",
    "εκ", "εξ", "μεταξύ",
    # measured (v0.0.18, 456-sentence clean sweep): these also govern Gen in
    # edited Greek and were the dominant prep_case FP source when classed Acc
    "εξαιτίας", "μέσω", "εναντίον", "περί", "υπέρ", "ενώπιον",
    "απόρροια",
}

# dual-government prepositions (Gen or Acc, both standard) — never flagged
AMBIGUOUS_PREPS = {"παρά", "κατά", "υπό", "μέχρι"}

# Standard Greek words measured as hunspell el_GR gaps (judged false
# positives from round-trip LLM pilots, 2026-10; pilots since retired).
# Exact measured forms only: each new entry must come with its own
# measured FP evidence. Transliterations of foreign terms (Ατγουντ,
# ταμαζίχτ...) stay unlisted by design — documented residue.
EXTRA_KNOWN_WORDS = frozenset({
    "αγκάθιο", "απάτριδες", "δυστοπικό", "ιστότοπο", "μαλαισιανό",
    "τουρκμενικού", "συλλογικοτήτων", "σαουδάραβες", "σαουδικά",
    "φετβά", "ουκρανού",
})

HETEREOCLITE_PLURALS = {
    "πλευρά": "Neut",
}

DEFINITE_ARTICLES = {
    ("Fem", "Sing", "Nom"): "η", ("Fem", "Sing", "Gen"): "της", ("Fem", "Sing", "Acc"): "την",
    ("Fem", "Plur", "Nom"): "οι", ("Fem", "Plur", "Gen"): "των", ("Fem", "Plur", "Acc"): "τις",
    ("Masc", "Sing", "Nom"): "ο", ("Masc", "Sing", "Gen"): "του", ("Masc", "Sing", "Acc"): "τον",
    ("Masc", "Plur", "Nom"): "οι", ("Masc", "Plur", "Gen"): "των", ("Masc", "Plur", "Acc"): "τους",
    ("Neut", "Sing", "Nom"): "το", ("Neut", "Sing", "Gen"): "του", ("Neut", "Sing", "Acc"): "το",
    ("Neut", "Plur", "Nom"): "τα", ("Neut", "Plur", "Gen"): "των", ("Neut", "Plur", "Acc"): "τα",
}

# 'ο οποίος' paradigm: (Gender, Number, Case) -> full pronoun form. Case is
# free (it belongs to the relative clause); Gender+Number must match the
# antecedent — used to emit the corrected relative pronoun as a suggestion.
REL_PRONOUNS = {
    ("Masc", "Sing", "Nom"): "ο οποίος", ("Masc", "Sing", "Gen"): "του οποίου",
    ("Masc", "Sing", "Acc"): "τον οποίο",
    ("Fem", "Sing", "Nom"): "η οποία", ("Fem", "Sing", "Gen"): "της οποίας",
    ("Fem", "Sing", "Acc"): "την οποία",
    ("Neut", "Sing", "Nom"): "το οποίο", ("Neut", "Sing", "Gen"): "του οποίου",
    ("Neut", "Sing", "Acc"): "το οποίο",
    ("Masc", "Plur", "Nom"): "οι οποίοι", ("Masc", "Plur", "Gen"): "των οποίων",
    ("Masc", "Plur", "Acc"): "τους οποίους",
    ("Fem", "Plur", "Nom"): "οι οποίες", ("Fem", "Plur", "Gen"): "των οποίων",
    ("Fem", "Plur", "Acc"): "τις οποίες",
    ("Neut", "Plur", "Nom"): "τα οποία", ("Neut", "Plur", "Gen"): "των οποίων",
    ("Neut", "Plur", "Acc"): "τα οποία",
}

RULE_SEVERITY = {
    "spelling": "medium",
    "typography": "low",
    "det_noun": "medium",
    "adj_noun": "medium",
    "num_noun": "medium",
    "subj_verb": "high",
    "prep_case": "high",
    "verb_valence": "medium",
    "negation": "high",
    "propn_accent": "low",
    "copula_pred": "medium",
    "rel_agreement": "medium",
    "na_form": "medium",
}

SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


def filter_violations(violations, min_severity=None, rules=None):
    """Pure filter over objects exposing .rule and .severity (model-free)."""
    out = list(violations)
    if rules:
        wanted = set(rules)
        out = [v for v in out if v.rule in wanted]
    if min_severity is not None:
        rank = SEVERITY_RANK[min_severity]
        out = [v for v in out if SEVERITY_RANK.get(v.severity, 0) >= rank]
    return out


def feats(word):
    f = word.feats or ""
    return dict(kv.split("=") for kv in f.split("|") if "=" in kv)


def conj_closure(word, by_id):
    seen = {word.id}
    frontier = [word]
    while frontier:
        w = frontier.pop()
        for x in by_id.values():
            if x.head == w.id and x.deprel == "conj" and x.id not in seen:
                seen.add(x.id)
                frontier.append(x)
    return [by_id[i] for i in sorted(seen)]


def has_own_determiner(word, by_id):
    return any(x.head == word.id and x.deprel == "det" for x in by_id.values())

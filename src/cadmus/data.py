"""Morphological feature utilities and static linguistic data for Modern Greek."""

GEN_PREPS = {
    "λόγω", "εκτός", "έναντι", "ένεκα", "αντί", "διά", "υπό", "προ",
    "εκ", "εξ", "μεταξύ",
}

AMBIGUOUS_PREPS = {"παρά", "κατά"}

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

RULE_SEVERITY = {
    "spelling": "medium",
    "typography": "low",
    "det_noun": "medium",
    "adj_noun": "medium",
    "subj_verb": "high",
    "prep_case": "high",
    "verb_valence": "medium",
    "negation": "high",
    "copula_pred": "medium",
    "rel_agreement": "medium",
    "na_form": "medium",
}


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

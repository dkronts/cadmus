"""Morphological feature utilities and static linguistic data for Modern Greek."""

GEN_PREPS = {
    "λόγω", "εκτός", "έναντι", "ένεκα", "αντί", "διά", "υπό", "προ",
    "εκ", "εξ", "μεταξύ",
}

AMBIGUOUS_PREPS = {"παρά", "κατά"}

HETEREOCLITE_PLURALS = {
    "πλευρά": "Neut",
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

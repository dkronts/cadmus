"""Stanza-protocol fakes for model-free rule unit tests."""


class FW:
    def __init__(self, id=1, text="", upos="", feats=None, lemma=None,
                 head=0, deprel="", start_char=None, end_char=None):
        self.id = id
        self.text = text
        self.upos = upos
        self.feats = feats
        self.lemma = lemma if lemma is not None else text
        self.head = head
        self.deprel = deprel
        self.start_char = start_char
        self.end_char = end_char


class FS:
    def __init__(self, words, text=None):
        self.words = words
        self.text = text or " ".join(w.text for w in words)


class FakeLexicon:
    def __init__(self, det_genders=None, noun_genders=None, suspect_ids=()):
        self.det_genders = det_genders or {}
        self.noun_genders = noun_genders or {}
        self.suspect_ids = set(suspect_ids)

    def resolve_det_gender(self, word):
        return self.det_genders.get(word.text.lower())

    def resolve_gender(self, word):
        return self.noun_genders.get(word.lemma) or (word.feats or "").split("Gender=")[-1].split("|")[0] if "Gender=" in (word.feats or "") else None

    def is_suspect(self, word):
        return word.id in self.suspect_ids


def sent(words):
    by_id = {w.id: w for w in words}
    return FS(words), by_id

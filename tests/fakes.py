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
    def __init__(self, det_genders=None, noun_genders=None, suspect_ids=(),
                 form_feats=None):
        self.det_genders = det_genders or {}
        self.noun_genders = noun_genders or {}
        self.suspect_ids = set(suspect_ids)
        if form_feats is not None:
            # capability flag: the rule detects form_feats by getattr, so the
            # method exists only when the test configures attestation data
            self.form_feats = lambda text: form_feats.get(text.lower(), {})

    def resolve_det_gender(self, word):
        return self.det_genders.get(word.text.lower())

    def resolve_gender(self, word):
        return self.noun_genders.get(word.lemma) or (word.feats or "").split("Gender=")[-1].split("|")[0] if "Gender=" in (word.feats or "") else None

    def is_suspect(self, word):
        return word.id in self.suspect_ids


def sent(words):
    by_id = {w.id: w for w in words}
    return FS(words), by_id


class FakeDoc:
    def __init__(self, text):
        self.text = text
        self.sentences = []
        self.tokens = []


class FakeNLP:
    """Minimal stanza-pipeline stand-in: callable and supports ``pipe``."""

    def __init__(self):
        self.call_count = 0
        self.pipe_calls = 0

    def __call__(self, text):
        self.call_count += 1
        return FakeDoc(text)

    def pipe(self, texts):
        self.pipe_calls += 1
        return [FakeDoc(t) for t in texts]


class FakeNLPProcessMany(FakeNLP):
    """stanza <=1.15: has ``process_many`` but no ``pipe``."""

    def __init__(self):
        super().__init__()
        self.process_many_calls = 0

    def process_many(self, texts):
        self.process_many_calls += 1
        return [FakeDoc(t) for t in texts]

    pipe = None  # emulate the missing attribute

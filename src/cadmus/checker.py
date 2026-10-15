"""Core checker: text in, violations out."""

from dataclasses import dataclass

from .lexicon import FormLexicon
from .pipeline import load_pipeline
from .rules import DAMPENABLE, RULES


@dataclass
class Violation:
    sentence: str
    rule: str
    message: str
    start_char: int
    end_char: int

    def as_dict(self):
        return {
            "sentence": self.sentence,
            "rule": self.rule,
            "message": self.message,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }


class CadmusChecker:
    def __init__(self, nlp=None, use_lexicon=True):
        self.nlp = nlp or load_pipeline()
        self.use_lexicon = use_lexicon
        self._lexicon = None
        self._damp_stats = {"suppressed": 0, "fired": 0}

    def lexicon(self):
        if self._lexicon is None and self.use_lexicon:
            try:
                self._lexicon = FormLexicon.load()
            except Exception:
                self.use_lexicon = False
        return self._lexicon

    def check(self, text):
        doc = self.nlp(text)
        violations = []
        for sent in doc.sentences:
            by_id = {w.id: w for w in sent.words}
            env = {}
            if self.use_lexicon:
                env["lexicon"] = self.lexicon()
            for name, fn in RULES.items():
                for w, h, msg in fn(sent, by_id, env):
                    if name in DAMPENABLE and self._dampened(w, h, rule=name):
                        self._damp_stats["suppressed"] += 1
                        continue
                    self._damp_stats["fired"] += 1
                    violations.append(
                        Violation(sent.text, name, msg, *self._offsets(sent, w))
                    )
        return violations

    def _dampened(self, w, h, rule=None):
        lex = self.lexicon()
        if lex is None:
            return False
        if rule == "det_noun" and w.upos == "DET" and lex.resolve_det_gender(w) is not None:
            if h is None or not lex.is_suspect(h):
                return False
            return not lex.noun_genders.get(h.lemma or "")
        if lex.is_suspect(w):
            return True
        return h is not None and h.id != w.id and lex.is_suspect(h)

    @staticmethod
    def _offsets(sent, w):
        start = getattr(w, "start_char", None)
        end = getattr(w, "end_char", None)
        if start is not None and end is not None:
            return start, end
        for t in sent.tokens:
            if t.words and t.words[0].id == w.id:
                return t.start_char, t.end_char
        return -1, -1

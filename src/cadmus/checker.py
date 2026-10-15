"""Core checker: text in, violations out."""

from dataclasses import dataclass, field

from .data import RULE_SEVERITY
from .lexicon import FormLexicon
from .pipeline import load_pipeline
from .rules import DAMPENABLE, RULES
from .rules.typography import typography


@dataclass
class Violation:
    sentence: str
    rule: str
    message: str
    start_char: int
    end_char: int
    suggestion: str = ""
    severity: str = field(default="medium", init=False)

    def __post_init__(self):
        self.severity = RULE_SEVERITY.get(self.rule, "medium")

    def as_dict(self):
        return {
            "sentence": self.sentence,
            "rule": self.rule,
            "message": self.message,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "suggestion": self.suggestion,
            "severity": self.severity,
        }


class CadmusChecker:
    def __init__(self, nlp=None, use_lexicon=True):
        self.nlp = nlp or load_pipeline()
        self.use_lexicon = use_lexicon
        self._lexicon = None
        self._propn = None
        self._damp_stats = {"suppressed": 0, "fired": 0}

    def lexicon(self):
        if self._lexicon is None and self.use_lexicon:
            try:
                self._lexicon = FormLexicon.load()
            except Exception:
                self.use_lexicon = False
        return self._lexicon

    def propn(self):
        if self._propn is None:
            try:
                from .lexicon import PropnLexicon

                self._propn = PropnLexicon.load()
            except Exception:
                self._propn = False
        return self._propn or None

    def check(self, text):
        doc = self.nlp(text)
        violations = []
        for s, e, msg, sug in typography(text):
            containing = next(
                (sent for sent in doc.sentences
                 if sent.tokens and sent.tokens[0].start_char <= s < sent.tokens[-1].end_char + 1),
                None,
            )
            sent_text = containing.text if containing else text[:80]
            violations.append(Violation(sent_text, "typography", msg, s, e, suggestion=sug))
        for sent in doc.sentences:
            by_id = {w.id: w for w in sent.words}
            env = {}
            if self.use_lexicon:
                env["lexicon"] = self.lexicon()
            env["propn"] = self.propn()
            for name, fn in RULES.items():
                for flag in fn(sent, by_id, env):
                    w, h, msg = flag[0], flag[1], flag[2]
                    suggestion = flag[3] if len(flag) > 3 else ""
                    if name in DAMPENABLE and self._dampened(w, h, rule=name):
                        self._damp_stats["suppressed"] += 1
                        continue
                    self._damp_stats["fired"] += 1
                    violations.append(
                        Violation(sent.text, name, msg, *self._offsets(sent, w),
                                  suggestion=suggestion)
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

"""Core checker: text in, violations out."""

from dataclasses import dataclass, field

from .data import RULE_SEVERITY
from .lexicon import FormLexicon
from .normalize import normalize_for_analysis
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
    confirmed: bool = None
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
            "confirmed": self.confirmed,
            "severity": self.severity,
        }


class CadmusChecker:
    def __init__(self, nlp=None, use_lexicon=True):
        self.nlp = nlp or load_pipeline()
        self.use_lexicon = use_lexicon
        self._lexicon = None
        self._propn = None
        self._verbforms = None
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

    def verbforms(self):
        if self._verbforms is None:
            try:
                from .lexicon import VerbForms

                self._verbforms = VerbForms.load()
            except Exception:
                self._verbforms = False
        return self._verbforms or None

    def check(self, text, deep=False):
        """Analyze `text` through a typography-normalized shadow copy.

        The parser sees punctuation/spacing fixes (better tokenization on
        messy machine output); all reported offsets/sentences refer to the
        original text via an offset mapper.

        With ``deep=True``, every violation carrying a suggestion is
        *confirmed* by a second analysis pass: the suggestion is applied to
        a copy and the same rule must no longer fire at that span. Costs one
        extra analysis per suggestion-bearing violation."""
        shadow, mapper = normalize_for_analysis(text)
        violations = self._analyze(text, self.nlp(shadow), mapper)
        if deep:
            self._confirm_suggestions(text, violations)
        return violations

    def _confirm_suggestions(self, text, violations):
        for v in violations:
            v.confirmed = False
            sug = v.suggestion.strip().strip("«»")
            if not sug or v.start_char < 0 or v.end_char <= v.start_char:
                continue
            corrected = text[:v.start_char] + sug + text[v.end_char:]
            try:
                recheck = self._analyze(corrected, self.nlp(corrected))
            except Exception:
                continue
            region = (v.start_char, v.start_char + len(sug))
            still_flagged = any(
                r.rule == v.rule
                and not (r.end_char <= region[0] or r.start_char >= region[1])
                for r in recheck
            )
            v.confirmed = not still_flagged

    def check_batch(self, texts, batch_size=32):
        """Check many texts efficiently via the pipeline's batched processor.

        Returns a list of violation-lists, one per input text, in order.
        Supports both the ``pipe`` (newer stanza) and ``process_many``
        (stanza <=1.15) batch APIs, falling back to per-text calls.
        """
        texts = list(texts)
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        results = []
        for chunk_idx, i in enumerate(range(0, len(texts), batch_size)):
            chunk = texts[i:i + batch_size]
            normalized = [normalize_for_analysis(t) for t in chunk]
            docs = self._iter_docs([shadow for shadow, _ in normalized])
            consumed = 0
            for orig, (_, mapper), doc in zip(chunk, normalized, docs):
                results.append(self._analyze(orig, doc, mapper))
                consumed += 1
            if consumed < len(chunk):
                raise ValueError(
                    f"pipeline returned {consumed} results for chunk {chunk_idx} "
                    f"(texts {i}..{i + len(chunk) - 1}) of {len(texts)} texts"
                )
        if len(results) != len(texts):
            raise ValueError(
                f"pipeline returned {len(results)} results for {len(texts)} texts "
                f"(chunk {len(results) // batch_size})"
            )
        return results

    def _iter_docs(self, texts):
        if callable(getattr(self.nlp, "pipe", None)):
            return self.nlp.pipe(texts)
        if callable(getattr(self.nlp, "process_many", None)):
            return self.nlp.process_many(texts)
        return [self.nlp(t) for t in texts]

    def _analyze(self, text, doc, mapper=None):
        violations = []
        for s, e, msg, sug in typography(text):
            containing = next(
                (sent for sent in doc.sentences
                 if sent.tokens and sent.tokens[0].start_char <= s < sent.tokens[-1].end_char + 1),
                None,
            )
            if containing is not None:
                sent_text = self._orig_sentence_text(text, containing, mapper)
            else:
                sent_text = text[:80]
            violations.append(Violation(sent_text, "typography", msg, s, e, suggestion=sug))
        for sent in doc.sentences:
            by_id = {w.id: w for w in sent.words}
            env = {}
            if self.use_lexicon:
                env["lexicon"] = self.lexicon()
            env["propn"] = self.propn()
            env["verbforms"] = self.verbforms()
            sent_text = self._orig_sentence_text(text, sent, mapper)
            for name, fn in RULES.items():
                for flag in fn(sent, by_id, env):
                    w, h, msg = flag[0], flag[1], flag[2]
                    suggestion = flag[3] if len(flag) > 3 else ""
                    if name in DAMPENABLE and self._dampened(w, h, rule=name):
                        self._damp_stats["suppressed"] += 1
                        continue
                    self._damp_stats["fired"] += 1
                    start, end = self._offsets(sent, w)
                    if mapper is not None:
                        start, end = mapper.span_to_orig(start, end)
                    violations.append(
                        Violation(sent_text, name, msg, start, end,
                                  suggestion=suggestion)
                    )
        return violations

    @staticmethod
    def _orig_sentence_text(text, sent, mapper):
        if mapper is None:
            return sent.text
        tokens = getattr(sent, "tokens", None)
        if not tokens:
            return sent.text
        start = mapper.to_orig(tokens[0].start_char)
        end = mapper.to_orig(tokens[-1].end_char)
        return text[start:end]

    def diagnose(self, text):
        """Report analyzer feature coverage over `text` (why rules may stay silent)."""
        from .diagnostics import coverage_report

        return coverage_report(self.nlp(text).sentences)

    def _dampened(self, w, h, rule=None):
        lex = self.lexicon()
        if lex is None:
            return False
        if rule == "det_noun" and w.upos == "DET" and lex.resolve_det_gender(w) is not None:
            if h is None or not lex.is_suspect(h):
                return False
            return not lex.noun_gender(h.lemma)
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

"""Local data assets: downloads, caching, UD-derived lexicon and verb frames."""

import gzip
import json
import os
import re
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "cadmus"

ASSETS = {
    "el_GR.aff": "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/el_GR/el_GR.aff",
    "el_GR.dic": "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/el_GR/el_GR.dic",
    "el_gdt-ud-train.conllu": "https://raw.githubusercontent.com/UniversalDependencies/UD_Greek-GDT/master/el_gdt-ud-train.conllu",
    "el_gdt-ud-test.conllu": "https://raw.githubusercontent.com/UniversalDependencies/UD_Greek-GDT/master/el_gdt-ud-test.conllu",
}

WIKI_TITLES_URL = "https://dumps.wikimedia.org/elwiki/latest/elwiki-latest-all-titles-in-ns0.gz"
WIKI_TITLES_FILE = "elwiki-titles.gz"

AGREEMENT_KEYS = ("Case", "Gender", "Number", "Person")
CORE_DEPRELS = {"obj", "iobj", "ccomp", "xcomp", "expl"}
_GREEK_TITLE = re.compile(r"^[Α-Ωα-ωάέήίόύώϊϋΐΰ]+(ς)?$")


def _deaccent(s):
    d = unicodedata.normalize("NFD", s)
    return unicodedata.normalize("NFC", "".join(c for c in d if not unicodedata.combining(c)))


def ensure_asset(name):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        url = ASSETS[name]
        tmp = path.with_suffix(path.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)
        os.replace(tmp, path)
    return path


def iter_conllu_sentences(path):
    block = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                if block:
                    yield block
                    block = []
            else:
                block.append(line)
    if block:
        yield block


def _parse_feats(raw):
    if not raw or raw == "_":
        return {}
    return dict(kv.split("=", 1) for kv in raw.split("|") if "=" in kv)


class FormLexicon:
    """form -> set of (UPOS, agreement feats); noun lemma -> attested genders."""

    def __init__(self, entries, noun_genders=None, det_genders=None):
        self.entries = entries
        self.noun_genders = noun_genders or {}
        self.det_genders = det_genders or {}

    @classmethod
    def build(cls, conllu_path):
        entries = {}
        noun_genders = {}
        det_genders = {}
        for block in iter_conllu_sentences(conllu_path):
            for line in block:
                if line.startswith("#") or "\t" not in line:
                    continue
                cols = line.split("\t")
                form, lemma, upos, feats = cols[1], cols[2], cols[3], _parse_feats(cols[5])
                if "-" in cols[0] or "." in cols[0]:
                    continue
                key = {k: feats[k] for k in AGREEMENT_KEYS if k in feats}
                if upos not in ("NOUN", "PROPN", "ADJ", "DET", "VERB", "AUX", "PRON"):
                    continue
                if upos == "NOUN" and "Gender" in feats and lemma not in ("_", ""):
                    noun_genders.setdefault(lemma, Counter())[feats["Gender"]] += 1
                if upos == "DET" and feats.get("PronType") == "Art" and "Gender" in feats:
                    det_genders.setdefault(form.lower(), Counter())[feats["Gender"]] += 1
                if not key:
                    continue
                analyses = entries.setdefault(form.lower(), set())
                analyses.add((upos, tuple(sorted(key.items()))))
        serialized = {k: [[u, [list(p) for p in pairs]] for u, pairs in sorted(v)]
                      for k, v in entries.items()}
        genders = {lemma: dict(c) for lemma, c in noun_genders.items()
                   if len(c) == 1 and sum(c.values()) >= 2}
        dets = {form: dict(c) for form, c in det_genders.items()
                if len(c) == 1 and sum(c.values()) >= 2}
        return cls(serialized,
                   {lemma: next(iter(c)) for lemma, c in genders.items()},
                   {form: next(iter(c)) for form, c in dets.items()})

    @classmethod
    def load(cls):
        lex_path = CACHE_DIR / "lexicon.v2.json"
        if not lex_path.exists():
            ensure_asset("el_gdt-ud-train.conllu")
            lex = cls.build(ensure_asset("el_gdt-ud-train.conllu"))
            lex_path.write_text(
                json.dumps({"entries": lex.entries, "noun_genders": lex.noun_genders,
                            "det_genders": lex.det_genders},
                           ensure_ascii=False),
                encoding="utf-8",
            )
            return lex
        data = json.loads(lex_path.read_text(encoding="utf-8"))
        return cls(data["entries"], data["noun_genders"], data.get("det_genders"))

    def resolve_gender(self, word):
        attested = self.noun_genders.get(word.lemma or "")
        feats = _word_feats(word)
        if not attested:
            return feats.get("Gender")
        if feats.get("Gender") == attested:
            return attested
        return attested

    def resolve_det_gender(self, word):
        return self.det_genders.get(word.text.lower())

    def is_suspect(self, word):
        analyses = self.entries.get(word.text.lower())
        if not analyses:
            return False
        feats = _word_feats(word)
        if not any(k in feats for k in AGREEMENT_KEYS):
            return False
        for upos, pairs in analyses:
            if upos == word.upos and all(feats.get(k) == v for k, v in pairs):
                return False
        return True

    def nominal_cases(self, form):
        """Set of Case values a surface form is attested with as NOUN/ADJ/PROPN.

        Surface-form based, so it is immune to the tagger *repairing* a wrong
        case to nominative. Empty when the form is unseen (precision-first)."""
        cases = set()
        for upos, pairs in self.entries.get(form.lower(), ()):
            if upos in ("NOUN", "ADJ", "PROPN"):
                case = dict(pairs).get("Case")
                if case:
                    cases.add(case)
        return cases


class VerbForms:
    """Surface-form verb classes from UD-GDT, used to detect a past indicative
    wrongly used after να.

    The tagger assigns Tense inconsistently at inference, so we classify by the
    *surface form* instead: a form is illegal after να only if it is attested
    exclusively as a finite past indicative and never as a να-governed verb."""

    ASSET = "verbforms.v1.json"

    def __init__(self, past_indicative, legal_after_na):
        self.past_indicative = set(past_indicative)
        self.legal_after_na = set(legal_after_na)

    @classmethod
    def build(cls, conllu_path):
        past, legal = set(), set()
        for block in iter_conllu_sentences(conllu_path):
            rows = []
            for line in block:
                if line.startswith("#") or "\t" not in line:
                    continue
                c = line.split("\t")
                if "-" in c[0] or "." in c[0]:
                    continue
                rows.append(c)
            for c in rows:
                if c[3] not in ("VERB", "AUX"):
                    continue
                form = c[1].lower()
                f = _parse_feats(c[5])
                if f.get("VerbForm") == "Fin" and f.get("Tense") == "Past":
                    past.add(form)
                if any(r[6] == c[0] and r[1] == "να" and r[7] == "aux" for r in rows):
                    legal.add(form)
        return cls(past, legal)

    @classmethod
    def load(cls):
        path = CACHE_DIR / cls.ASSET
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(data["past_indicative"], data["legal_after_na"])
        ensure_asset("el_gdt-ud-train.conllu")
        lex = cls.build(ensure_asset("el_gdt-ud-train.conllu"))
        path.write_text(
            json.dumps({"past_indicative": sorted(lex.past_indicative),
                        "legal_after_na": sorted(lex.legal_after_na)},
                       ensure_ascii=False),
            encoding="utf-8",
        )
        return lex

    def illegal_after_na(self, form):
        f = form.lower()
        return f in self.past_indicative and f not in self.legal_after_na


def _word_feats(word):
    f = word.feats or ""
    return dict(kv.split("=", 1) for kv in f.split("|") if "=" in kv)


class VerbFrames:
    """verb lemma -> Counter of core-dependency frames from the treebank."""

    MIN_TOTAL = 4

    def __init__(self, counters):
        self.counters = counters

    @classmethod
    def build(cls, conllu_path):
        counters = {}
        for block in iter_conllu_sentences(conllu_path):
            rows = []
            for line in block:
                if line.startswith("#") or "\t" not in line:
                    continue
                cols = line.split("\t")
                if "-" in cols[0] or "." in cols[0]:
                    continue
                rows.append(cols)
            for cols in rows:
                if cols[3] != "VERB" or cols[2] in ("_", ""):
                    continue
                head = cols[6]
                core = tuple(sorted({
                    c[7].split(":")[0]
                    for c in rows
                    if c[6] == cols[0] and c[7].split(":")[0] in CORE_DEPRELS
                }))
                counters.setdefault(cols[2].lower(), Counter())[core] += 1
        return cls(counters)

    @classmethod
    def load(cls):
        path = CACHE_DIR / "frames.v1.json"
        if not path.exists():
            ensure_asset("el_gdt-ud-train.conllu")
            raw = cls.build(ensure_asset("el_gdt-ud-train.conllu"))
            data = {lemma: {",".join(k): v for k, v in c.items()} for lemma, c in raw.counters.items()}
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls({lemma: Counter({tuple(k.split(",")) if k else (): v
                                    for k, v in c.items()})
                    for lemma, c in data.items()})

    def unexpected(self, verb_word, children):
        counter = self.counters.get((verb_word.lemma or "").lower())
        if not counter:
            return None
        if sum(counter.values()) < self.MIN_TOTAL:
            return None
        core = tuple(sorted({c.deprel.split(":")[0] for c in children
                             if c.deprel.split(":")[0] in CORE_DEPRELS}))
        if not core or core in counter:
            return None
        if not ({"obj", "iobj"} & set(core)):
            return None
        known = counter.most_common(3)
        pretty = " | ".join(f"«{' + '.join(k) if any(k) else 'no core object'}» ({v})" for k, v in known)
        return f"VERB-VALENCE: '{verb_word.text}' ({verb_word.lemma}) usually takes {pretty}, here: {' + '.join(core)}"


class PropnLexicon:
    """Proper-noun surface forms (Wikipedia titles + UD-train PROPNs).

    Used only to detect proper-noun ACCENT errors: a token whose de-accented
    form maps to exactly one attested form that differs from it only by accents
    is treated as a mis-accented proper noun. Ambiguous or unknown forms are
    never flagged (precision-first)."""

    ASSET = "propn.v1.json"

    def __init__(self, forms):
        self.forms = {f.lower() for f in forms}
        self.accent_index = {}
        for f in self.forms:
            self.accent_index.setdefault(_deaccent(f), set()).add(f)

    @classmethod
    def _ensure_wiki(cls):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / WIKI_TITLES_FILE
        if not path.exists() or path.stat().st_size == 0:
            tmp = path.with_suffix(".part")
            urllib.request.urlretrieve(WIKI_TITLES_URL, tmp)
            os.replace(tmp, path)
        return path

    @classmethod
    def build(cls):
        forms = set()
        train = ensure_asset("el_gdt-ud-train.conllu")
        for block in iter_conllu_sentences(train):
            for line in block:
                if line.startswith("#") or "\t" not in line:
                    continue
                cols = line.split("\t")
                if cols[3] == "PROPN" and "-" not in cols[0] and "." not in cols[0]:
                    forms.add(cols[1].lower())
        with gzip.open(cls._ensure_wiki(), "rt", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i == 0:
                    continue
                title = re.sub(r"\(.*?\)", " ", line.strip().replace("_", " "))
                for tok in title.split():
                    if len(tok) >= 3 and _GREEK_TITLE.match(tok):
                        forms.add(tok.lower())
        return cls(forms)

    @classmethod
    def load(cls):
        path = CACHE_DIR / cls.ASSET
        if path.exists():
            return cls(json.loads(path.read_text(encoding="utf-8")))
        lex = cls.build()
        path.write_text(json.dumps(sorted(lex.forms), ensure_ascii=False), encoding="utf-8")
        return lex

    def accent_suggestion(self, form):
        f = form.lower()
        if f in self.forms:
            return None
        cands = self.accent_index.get(_deaccent(f))
        if not cands or len(cands) != 1:
            return None
        cand = next(iter(cands))
        if cand == f:
            return None
        return cand[0].upper() + cand[1:] if form[:1].isupper() else cand

"""Local data assets: downloads, caching, UD-derived lexicon and verb frames."""

import json
import os
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

AGREEMENT_KEYS = ("Case", "Gender", "Number", "Person")
CORE_DEPRELS = {"obj", "iobj", "ccomp", "xcomp", "expl"}


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

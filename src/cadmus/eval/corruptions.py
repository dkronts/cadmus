"""Deterministic corruption functions simulating LLM-style Greek errors."""

import random
import re
import unicodedata

from ..data import DEFINITE_ARTICLES

ARTICLES = DEFINITE_ARTICLES
FORM_TO_KEY = {v: k for k, v in ARTICLES.items()}

GREEK_WORD = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]+")
HOMOGLYPHS = str.maketrans({"ο": "o", "ε": "e", "α": "a", "ι": "i", "Ο": "O", "Ε": "E", "Α": "A", "Ι": "I"})


def _words(text):
    return [(m.start(), m.group()) for m in re.finditer(r"\S+", text)]


def _strip_accents(s):
    decomposed = unicodedata.normalize("NFD", s)
    return unicodedata.normalize("NFC", "".join(c for c in decomposed if not unicodedata.combining(c)))


def corrupt_det(text, rng):
    candidates = [m for m in _words(text) if m[1] in FORM_TO_KEY]
    if not candidates:
        return None
    start, form = rng.choice(candidates)
    g, n, c = FORM_TO_KEY[form]
    same_case_wrong = [f for k, f in ARTICLES.items() if k[2] == c and (k[0], k[1]) != (g, n)]
    if not same_case_wrong:
        return None
    return text[:start] + rng.choice(same_case_wrong) + text[start + len(form):], "det_noun"


def corrupt_typo(text, rng):
    candidates = [m for m in _words(text)
                  if GREEK_WORD.fullmatch(m[1]) and len(m[1]) >= 5]
    if not candidates:
        return None
    start, w = rng.choice(candidates)
    i = rng.randrange(1, len(w) - 2)
    mangled = w[:i] + w[i + 1] + w[i] + w[i + 2:]
    return text[:start] + mangled + text[start + len(w):], "nonword"


def corrupt_accent(text, rng):
    candidates = [m for m in _words(text)
                  if GREEK_WORD.fullmatch(m[1]) and _strip_accents(m[1]) != m[1]]
    if not candidates:
        return None
    start, w = rng.choice(candidates)
    return text[:start] + _strip_accents(w) + text[start + len(w):], "accent"


def corrupt_homoglyph(text, rng):
    candidates = [m for m in _words(text)
                  if GREEK_WORD.fullmatch(m[1]) and any(ord(ch) in HOMOGLYPHS for ch in m[1])]
    if not candidates:
        return None
    start, w = rng.choice(candidates)
    return text[:start] + w.translate(HOMOGLYPHS) + text[start + len(w):], "script_mix"


def corrupt_negation(text, rng):
    candidates = [m for m in _words(text) if m[1].lower() in ("δεν", "μην")]
    if not candidates:
        return None
    start, w = rng.choice(candidates)
    swap = {"δεν": "μην", "μην": "δεν"}[w.lower()]
    if w[0].isupper():
        swap = swap.capitalize()
    return text[:start] + swap + text[start + len(w):], "negation"


def corrupt_question_mark(text, rng):
    positions = [i for i, ch in enumerate(text) if ch == ";"]
    if not positions:
        return None
    i = rng.choice(positions)
    return text[:i] + "?" + text[i + 1:], "typography"


def corrupt_spacing(text, rng):
    positions = [i for i, ch in enumerate(text) if ch == "," and i + 1 < len(text) and text[i + 1] == " "]
    if not positions:
        return None
    i = rng.choice(positions)
    return text[:i] + " ," + text[i + 1:], "typography"


ALL = [corrupt_det, corrupt_typo, corrupt_accent, corrupt_homoglyph,
       corrupt_negation, corrupt_question_mark, corrupt_spacing]


def corrupt(text, rng):
    order = list(ALL)
    rng.shuffle(order)
    for fn in order:
        result = fn(text, rng)
        if result:
            return result
    return None

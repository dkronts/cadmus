"""Orthography layer: hunspell el_GR via spylls, script-mix and accent helpers."""

import re
import unicodedata

from .lexicon import ensure_asset

GREEK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
LATIN_RE = re.compile(r"[A-Za-z]")
SKIP_RE = re.compile(r"[\d@#/\\]|https?://|\.(com|gr|org|net)$", re.IGNORECASE)

_SPELL = None
_LOOKUP_CACHE = {}
_DEACCENT = str.maketrans("άέήίόύώΆΈΉΊΌΎΏ", "αεηιουωΑΕΗΙΟΥΩ")


def _enclitic_variant(token):
    accented = [i for i, c in enumerate(token) if c in "άέήίόύώ"]
    if len(accented) < 2:
        return None
    last = accented[-1]
    return token[:last] + token[last].translate(_DEACCENT) + token[last + 1:]


def strip_accents(s):
    decomposed = unicodedata.normalize("NFD", s)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", stripped)


def _dictionary():
    global _SPELL
    if _SPELL is None:
        from spylls.hunspell import Dictionary

        from .lexicon import CACHE_DIR

        ensure_asset("el_GR.aff")
        ensure_asset("el_GR.dic")
        _SPELL = Dictionary.from_files(str(CACHE_DIR / "el_GR"))
    return _SPELL


def is_checkable(token):
    if SKIP_RE.search(token):
        return False
    if not any(c.isalpha() for c in token):
        return False
    return True


def is_known(token):
    if not is_checkable(token):
        return True
    if not GREEK_RE.search(token):
        return True
    d = _dictionary()
    key = token
    if key in _LOOKUP_CACHE:
        return _LOOKUP_CACHE[key]
    variants = {token, token.lower(), token.lower().capitalize(), token.upper()}
    result = any(d.lookup(v) for v in variants)
    if not result:
        variant = _enclitic_variant(token)
        if variant is not None:
            result = d.lookup(variant) or d.lookup(variant.lower())
    _LOOKUP_CACHE[key] = result
    return result


def classify_unknown(token):
    """Returns (kind, suggestions) with kind in {'accent','nonword'}."""
    d = _dictionary()
    raw = list(d.suggest(token))
    suggestions = [s for s in raw if s != token][:3]
    base = strip_accents(token).lower()
    for s in raw:
        if strip_accents(s).lower() == base:
            return "accent", [s]
    return "nonword", suggestions


def is_script_mixed(token):
    if not is_checkable(token):
        return False
    if token.isupper() and len(token) >= 2:
        return False
    alpha = [c for c in token if c.isalpha()]
    if len(alpha) < 2:
        return False
    return bool(GREEK_RE.search(token) and LATIN_RE.search(token))

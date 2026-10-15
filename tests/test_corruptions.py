import random

from cadmus.eval.corruptions import (
    corrupt_accent, corrupt_det, corrupt_homoglyph, corrupt_typo,
)


def test_corrupt_det():
    result = corrupt_det("Είδα την ταινία χθες το βράδυ.", random.Random(1))
    assert result is not None
    text, rule = result
    assert rule == "det_noun"
    assert "την" not in text
    assert "ταινία" in text


def test_corrupt_typo():
    original = "Η οικονομική κατάσταση βελτιώθηκε."
    result = corrupt_typo(original, random.Random(3))
    assert result is not None
    text, rule = result
    assert rule == "nonword"
    assert text != original


def test_corrupt_accent():
    original = "Η οικονομική κατάσταση βελτιώθηκε."
    result = corrupt_accent(original, random.Random(5))
    assert result is not None
    text, rule = result
    assert rule == "accent"
    assert text != original
    assert "οικονομικ" in text or "καταστασ" in text or "βελτιωθ" in text


def test_corrupt_homoglyph():
    result = corrupt_homoglyph("Το κορίτσι έφυγε.", random.Random(7))
    assert result is not None
    text, rule = result
    assert rule == "script_mix"
    assert any(c.isascii() and c.isalpha() for c in text)

import random
from types import SimpleNamespace

from cadmus.export import annotate_with_check, diff_span, generate_pairs

SENTENCES = [
    "Ο πρόεδρος υπέγραψε τη συμφωνία χθες το βράδυ.",
    "Η κυβέρνηση δεν θα πάρει αυτή την απόφαση.",
    "Οι πολίτες διαμαρτυρήθηκαν για τους φόρους στην πλατεία.",
    "Αγόρασα ένα καινούριο αυτοκίνητο από το αντιπροσωπείο.",
]


def test_diff_span_single_edit_reconstructs():
    clean = "Η κυβέρνηση δεν θα πάρει την απόφαση."
    broken = "Η κυβέρνηση μην θα πάρει την απόφαση."
    d = diff_span(clean, broken)
    assert clean[:d["start"]] + d["clean"] + clean[d["start"] + len(d["clean"]):] == clean
    assert broken[:d["start"]] + d["broken"] + broken[d["start"] + len(d["broken"]):] == broken
    assert d["clean"] != d["broken"] and d["clean"] and d["broken"]


def test_generate_pairs_are_aligned_and_labelled():
    rng = random.Random(0)
    pairs = generate_pairs(SENTENCES, rng)
    assert pairs, "expected at least one corrupted pair"
    for p in pairs:
        assert p["broken"] != p["correct"]
        assert p["rule"]
        s = p["span_start"]
        cf, bf = p["correct_fragment"], p["broken_fragment"]
        assert p["correct"][:s] + cf + p["correct"][s + len(cf):] == p["correct"]
        assert p["broken"][:s] + bf + p["broken"][s + len(bf):] == p["broken"]


def _pair():
    broken = "Η κυβέρνηση μην θα πάρει την απόφαση."
    start = broken.index("μην")
    return {"rule": "negation", "broken": broken, "correct": broken.replace("μην", "δεν"),
            "span_start": start, "broken_fragment": "μην", "correct_fragment": "δεν"}


def _v(rule, start, end, suggestion=None):
    return SimpleNamespace(rule=rule, start_char=start, end_char=end, suggestion=suggestion)


def test_annotate_with_check_overlap_catches():
    end = _pair()["span_start"] + 3
    pairs = annotate_with_check([_pair()], lambda t: [_v("negation", end - 1, end, "δεν")])
    assert pairs[0]["detected"] is True
    assert pairs[0]["detected_rules"] == ["negation"]
    assert pairs[0]["suggestion"] == "δεν"


def test_annotate_with_check_no_overlap_is_miss():
    pairs = annotate_with_check([_pair()], lambda t: [_v("spelling", 0, 1)])
    assert pairs[0]["detected"] is False
    assert pairs[0]["detected_rules"] == []
    assert pairs[0]["suggestion"] is None

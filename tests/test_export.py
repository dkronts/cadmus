import random

from cadmus.export import diff_span, generate_pairs

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

import pytest

from cadmus import CadmusChecker
from cadmus.corpora import BROKEN_SENTENCES, DEMO_SENTENCES


@pytest.fixture(scope="session")
def checker():
    return CadmusChecker()


@pytest.mark.parametrize("sentence", BROKEN_SENTENCES)
def test_broken_sentences_flagged(checker, sentence):
    violations = checker.check(sentence)
    assert violations, f"expected a violation for: {sentence}"


def test_demo_corpus_clean(checker):
    flagged = [(s, checker.check(s)) for s in DEMO_SENTENCES]
    failures = [(s, [str(v.message) for v in vs]) for s, vs in flagged if vs]
    assert not failures, f"false positives: {failures}"


def test_offsets_are_sane(checker):
    for s in BROKEN_SENTENCES:
        for v in checker.check(s):
            assert 0 <= v.start_char < v.end_char <= len(s)


def test_negation_clean(checker):
    assert checker.check("Δεν θέλω να μην έρθεις.") == []
    assert checker.check("Μην ξεχάσεις να έρθεις.") == []


def test_negation_flagged(checker):
    assert any(v.rule == "negation" for v in checker.check("Θέλω να δεν έρχεσαι."))
    assert any(v.rule == "negation" for v in checker.check("Μην πήγαμε χθες."))


def test_accent_carries_suggestion(checker):
    vs = [v for v in checker.check("Αύριο διαβασω το μάθημα.") if v.rule == "spelling"]
    assert vs and vs[0].suggestion == "διαβάσω"


def test_propn_accent_end_to_end(checker):
    vs = [v for v in checker.check("Ταξίδεψα στη Ρωσια.") if v.suggestion == "Ρωσία"]
    assert vs, "expected a proper-noun accent correction for 'Ρωσια'"


def test_rel_agreement_clean(checker):
    assert [v for v in checker.check("Ο γιατρός ο οποίος πραγματοποίησε την έκτρωση φεύγει.")
            if v.rule == "rel_agreement"] == []
    assert [v for v in checker.check("Η ομάδα η οποία θεωρεί τις εγγυήσεις σημαντικές κέρδισε.")
            if v.rule == "rel_agreement"] == []


def test_rel_agreement_flagged(checker):
    assert any(v.rule == "rel_agreement"
               for v in checker.check("Ο γιατρός η οποία πραγματοποίησε την έκτρωση φεύγει."))
    assert any(v.rule == "rel_agreement"
               for v in checker.check("Οι γιατροί τα οποία πραγματοποίησαν την έκτρωση φεύγουν."))


def test_copula_pred_flagged(checker):
    assert any(v.rule == "copula_pred" for v in checker.check("Είναι γιατρό."))
    assert any(v.rule == "copula_pred" for v in checker.check("Θα γίνεις πρόεδρο."))


def test_copula_pred_clean(checker):
    assert [v for v in checker.check("Είναι γιατρός.") if v.rule == "copula_pred"] == []


def test_copula_pred_subject_guard(checker):
    # neuter predicate mis-tagged masculine; subject is neuter -> suppressed
    assert [v for v in checker.check("Υπαίτιο για αυτό είναι το Κοινοβούλιο.")
            if v.rule == "copula_pred"] == []


def test_na_form_flagged(checker):
    assert any(v.rule == "na_form" for v in checker.check("Νομίζω ότι να έκανε λάθος."))


def test_na_form_clean(checker):
    assert [v for v in checker.check("Θέλω να έρθεις αύριο.") if v.rule == "na_form"] == []


def test_num_noun_flagged(checker):
    assert any(v.rule == "num_noun" for v in checker.check("Τρεις παιδιά φύγαν."))
    assert any(v.rule == "num_noun" for v in checker.check("Τρία άνδρες φύγαν."))


def test_num_noun_clean(checker):
    assert [v for v in checker.check("Τρεις άνδρες φύγαν.") if v.rule == "num_noun"] == []
    assert [v for v in checker.check("Τρία παιδιά φύγαν.") if v.rule == "num_noun"] == []

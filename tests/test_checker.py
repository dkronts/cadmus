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


def test_spelling_coverage_suppression(checker):
    cases = {
        "Χρυσοπηγής": ("Μια από τις πιο όμορφες εικόνες της Σίφνου είναι το εκκλησάκι "
                       "της Παναγίας της Χρυσοπηγής που βρίσκεται χτισμένο σε ένα πελώριο βράχο."),
        "ευρωζώνη": ("Η Δανία, η Σουηδία και η Μεγάλη Βρετανία καλούνται να προσχωρήσουν "
                     "στην ευρωζώνη πριν από τη διεύρυνση προς Ανατολάς."),
        "ερυθηματώδης": ("Ο διαβήτης τύπου Β και ο ερυθηματώδης λύκος απασχολούν την έρευνα."),
    }
    for token, sentence in cases.items():
        vs = [v for v in checker.check(sentence)
              if v.rule == "spelling" and f"'{token}'" in v.message]
        assert not vs, f"expected no spelling flag for lexicon-covered '{token}': {vs}"


def test_spelling_abbreviations_and_elisions_clean(checker):
    assert [v for v in checker.check("Το νησί απέχει 12 χλμ. από την πρωτεύουσα.")
            if v.rule == "spelling"] == []
    assert [v for v in checker.check("Το έμαθε απ' τους ίδιους τους γείτονες χθες.")
            if v.rule == "spelling"] == []


def test_spelling_unknown_word_still_flagged(checker):
    vs = [v for v in checker.check("Ο σκανταλοτρυγόνος τραγουδά δυνατά.")
          if v.rule == "spelling"]
    assert vs and "σκανταλοτρυγόνος" in vs[0].message


def test_messy_text_offsets_map_to_original(checker):
    """The parser sees the normalized shadow; reported offsets stay original."""
    s = "Η πράσινο δέντρο , είναι μεγάλο?"
    vs = checker.check(s)
    assert any(v.rule == "det_noun" for v in vs), f"expected det_noun through the shadow: {vs}"
    for v in vs:
        assert 0 <= v.start_char < v.end_char <= len(s)
    q = [v for v in vs if v.rule == "typography" and "'?'" in v.message]
    assert q and s[q[0].start_char] == "?"


def test_messy_text_sentence_shows_original(checker):
    s = "Το παιδί  παίζει,καλά."
    for v in checker.check(s):
        assert v.sentence == s or v.sentence in s


def test_prep_case_new_gen_preps_flagged(checker):
    assert any(v.rule == "prep_case"
               for v in checker.check("Εξαιτίας το πρόβλημα, αναβλήθηκε η συνεδρίαση."))
    assert any(v.rule == "prep_case"
               for v in checker.check("Μέσω την τηλεόραση μεταδόθηκε η είδηση."))


def test_prep_case_new_gen_preps_clean(checker):
    for s in ("Εξαιτίας του προβλήματος, αναβλήθηκε η συνεδρίαση.",
              "Μέσω της τηλεόρασης μεταδόθηκε η είδηση.",
              "Το σχέδιο είναι υπό έλεγχο.",
              "Εν συντομία, όλα κρίθηκαν έγκαιρα."):
        assert [v for v in checker.check(s) if v.rule == "prep_case"] == [], s


def test_deep_confirmation_confirms_good_suggestion(checker):
    vs = [v for v in checker.check("Βλέπω τους καρέκλες.", deep=True)
          if v.rule == "det_noun"]
    assert vs, "expected a det_noun flag"
    assert vs[0].suggestion.strip("«»") == "τις"
    assert vs[0].confirmed is True
    # without deep, confirmation is not attempted
    plain = [v for v in checker.check("Βλέπω τους καρέκλες.") if v.rule == "det_noun"]
    assert plain[0].confirmed is None


def test_deep_confirmation_confirms_spelling_suggestion(checker):
    vs = [v for v in checker.check("Αύριο διαβασω το μάθημα.", deep=True)
          if v.rule == "spelling"]
    assert vs and vs[0].confirmed is True

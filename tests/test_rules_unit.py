from fakes import FW, FakeLexicon, sent

from cadmus.rules.agreement import adj_noun, det_noun, subj_verb
from cadmus.rules.government import prep_case
from cadmus.rules.negation import negation
from cadmus.rules.typography import typography


def test_det_noun_gender_mismatch_with_paradigm_override():
    words = [
        FW(1, "τους", "DET", "Case=Acc|Gender=Neut|Number=Plur", head=2, deprel="det"),
        FW(2, "Κοινοβούλιο", "NOUN", "Case=Acc|Gender=Neut|Number=Sing"),
    ]
    s, by_id = sent(words)
    lex = FakeLexicon(det_genders={"τους": "Masc"})
    flags = det_noun(s, by_id, {"lexicon": lex})
    assert any("Masc" in f[2] for f in flags)
    assert all(f[3] == "«το»" for f in flags)


def test_det_noun_heteroclite_escape():
    words = [
        FW(1, "τα", "DET", "Case=Acc|Gender=Neut|Number=Plur"),
        FW(2, "πλευρά", "NOUN", "Case=Acc|Gender=Fem|Number=Plur", lemma="πλευρά", head=1, deprel="det"),
    ]
    s, by_id = sent(words)
    assert det_noun(s, by_id, {}) == []


def test_adj_noun_case_mismatch_skipped():
    words = [
        FW(1, "πολύχρωμων", "ADJ", "Case=Gen|Gender=Fem|Number=Plur", head=2, deprel="amod"),
        FW(2, "φωτογραφίες", "NOUN", "Case=Acc|Gender=Fem|Number=Plur"),
    ]
    s, by_id = sent(words)
    assert adj_noun(s, by_id, {}) == []


def test_adj_noun_number_mismatch_flagged():
    words = [
        FW(1, "πεινασμένη", "ADJ", "Case=Nom|Gender=Fem|Number=Sing", head=2, deprel="amod"),
        FW(2, "γάτες", "NOUN", "Case=Nom|Gender=Fem|Number=Plur"),
    ]
    s, by_id = sent(words)
    assert any("Number" in f[2] for f in adj_noun(s, by_id, {}))


def _coordination_sentence(plural_verb):
    return [
        FW(1, "Ο", "DET", "Case=Nom|Gender=Masc|Number=Sing", head=2, deprel="det"),
        FW(2, "άντρας", "NOUN", "Case=Nom|Gender=Masc|Number=Sing", head=5, deprel="nsubj"),
        FW(3, "η", "DET", "Case=Nom|Gender=Fem|Number=Sing", head=4, deprel="det"),
        FW(4, "γυναίκα", "NOUN", "Case=Nom|Gender=Fem|Number=Sing", head=2, deprel="conj"),
        FW(5, "συζητούν" if plural_verb else "συζητά", "VERB",
           "Mood=Ind|Number=Plur|Person=3" if plural_verb else "Mood=Ind|Number=Sing|Person=3",
           head=0, deprel="root"),
    ]


def test_subj_verb_plural_licensed_by_coordination():
    s, by_id = sent(_coordination_sentence(plural_verb=True))
    assert subj_verb(s, by_id, {}) == []


def test_subj_verb_plural_with_single_subject_flagged():
    words = [
        FW(1, "Η", "DET", "Case=Nom|Gender=Fem|Number=Sing", head=2, deprel="det"),
        FW(2, "γάτα", "NOUN", "Case=Nom|Gender=Fem|Number=Sing", head=3, deprel="nsubj"),
        FW(3, " είναι", "AUX", "Number=Plur|Person=3", head=0, deprel="root"),
    ]
    s, by_id = sent(words)
    assert any("Number" in f[2] for f in subj_verb(s, by_id, {}))


def test_prep_case_gen_governing():
    words = [
        FW(1, "Λόγω", "ADP", head=2, deprel="case"),
        FW(2, "καθυστέρηση", "NOUN", "Case=Acc|Gender=Fem|Number=Sing"),
    ]
    s, by_id = sent(words)
    assert any("Gen" in f[2] for f in prep_case(s, by_id, {}))


def test_negation_delta_with_subjunctive():
    words = [
        FW(1, "να", "AUX"),
        FW(2, "δεν", "PART"),
        FW(3, "έρθεις", "VERB", "Aspect=Perf|Number=Sing|Person=2|VerbForm=Fin", head=0, deprel="root"),
    ]
    s, by_id = sent(words)
    assert any("μην" in f[2] for f in negation(s, by_id, {}))


def test_negation_mhn_with_indicative():
    words = [
        FW(1, "Μην", "PART"),
        FW(2, "πήγαμε", "VERB", "Mood=Ind|Tense=Past|Number=Plur|Person=1", head=0, deprel="root"),
    ]
    s, by_id = sent(words)
    assert any("δεν" in f[2] for f in negation(s, by_id, {}))


def test_negation_clean_pairs():
    clean = [
        [FW(1, "Δεν", "PART"),
         FW(2, "θέλω", "VERB", "Mood=Ind|Tense=Pres|Number=Sing|Person=1", head=0, deprel="root")],
        [FW(1, "να", "AUX"),
         FW(2, "μην", "PART"),
         FW(3, "έρθεις", "VERB", "Aspect=Perf|Number=Sing|Person=2|VerbForm=Fin", head=0, deprel="root")],
        [FW(1, "Μην", "PART"),
         FW(2, "ξεχάσεις", "VERB", "Aspect=Perf|Number=Sing|Person=2|VerbForm=Fin", head=0, deprel="root")],
    ]
    for words in clean:
        s, by_id = sent(words)
        assert negation(s, by_id, {}) == []


def test_typography_checks():
    flags = typography("Πώς είσαι ? Δεν , ήρθα.  καλό")
    msgs = [m for _, _, m, _ in flags]
    assert any("?" in m for m in msgs)
    assert any("space before" in m for m in msgs)
    assert any("double space" in m for m in msgs)


def test_typography_lowercase_start():
    flags = typography("Ήρθαμε χθες. ήμασταν λιγοι.")
    assert any("lowercase" in m for _, _, m, _ in flags)
    assert typography("ήρθαμε χθες.") == []

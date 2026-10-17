from fakes import FW, FakeLexicon, sent

from cadmus import orthography as orth_layer
from cadmus.data import filter_violations
from cadmus.lexicon import FormLexicon, PropnLexicon
from cadmus.rules.agreement import adj_noun, det_noun, num_noun, rel_agreement, subj_verb
from cadmus.rules.government import prep_case
from cadmus.rules.negation import negation
from cadmus.rules.orthography import spelling
from cadmus.rules.propn import propn_accent
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


def test_det_noun_form_attested_with_article_suppressed():
    # the noun's surface form is attested with the article's CASE: syncretic noise
    words = [
        FW(1, "το", "DET", "Case=Acc|Gender=Neut|Number=Sing", head=2, deprel="det"),
        FW(2, "ένταλμα", "NOUN", "Case=Nom|Gender=Neut|Number=Sing", lemma="ένταλμα"),
    ]
    s, by_id = sent(words)
    lex = FakeLexicon(det_genders={"το": "Neut"},
                      form_feats={"ένταλμα": {"Case": {"Nom", "Acc"}}})
    assert det_noun(s, by_id, {"lexicon": lex}) == []


def test_det_noun_form_case_disjoint_fires():
    words = [
        FW(1, "το", "DET", "Case=Acc|Gender=Neut|Number=Sing", head=2, deprel="det"),
        FW(2, "βιβλίο", "NOUN", "Case=Nom|Gender=Neut|Number=Sing", lemma="βιβλίο"),
    ]
    s, by_id = sent(words)
    lex = FakeLexicon(det_genders={"το": "Neut"},
                      form_feats={"βιβλίο": {"Case": {"Nom"}}})
    assert any("Case" in f[2] for f in det_noun(s, by_id, {"lexicon": lex}))


def test_det_noun_gender_not_gated_even_when_attested():
    # Gender mismatches always fire (the corruption target swaps article gender)
    words = [
        FW(1, "Η", "DET", "Case=Nom|Gender=Fem|Number=Sing", head=2, deprel="det"),
        FW(2, "υπουργός", "NOUN", "Case=Nom|Gender=Masc|Number=Sing", lemma="υπουργός"),
    ]
    s, by_id = sent(words)
    lex = FakeLexicon(det_genders={"η": "Fem"},
                      form_feats={"υπουργός": {"Gender": {"Masc", "Fem"}}})
    assert any("Gender" in f[2] for f in det_noun(s, by_id, {"lexicon": lex}))


def test_det_noun_unseen_form_still_fires():
    # unseen forms keep the tagger-based behavior (recall protection)
    words = [
        FW(1, "τους", "DET", "Case=Acc|Gender=Masc|Number=Plur", head=2, deprel="det"),
        FW(2, "πρόποδες", "NOUN", "Case=Acc|Gender=Fem|Number=Plur", lemma="πρόποδη"),
    ]
    s, by_id = sent(words)
    lex = FakeLexicon(det_genders={"τους": "Masc"}, form_feats={})
    assert det_noun(s, by_id, {"lexicon": lex})


def test_det_noun_without_form_feats_resource_keeps_old_behavior():
    words = [
        FW(1, "τους", "DET", "Case=Acc|Gender=Masc|Number=Plur", head=2, deprel="det"),
        FW(2, "πρόποδες", "NOUN", "Case=Acc|Gender=Fem|Number=Plur", lemma="πρόποδη"),
    ]
    s, by_id = sent(words)
    lex = FakeLexicon(det_genders={"τους": "Masc"})
    assert det_noun(s, by_id, {"lexicon": lex})


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


def _relcl(ant_feats, rel_feats, rel_lemma="οποίος"):
    # antecedent (root) <- acl:relcl verb <- relative pronoun (nsubj)
    return [
        FW(1, "γιατρός", "NOUN", ant_feats, head=0, deprel="root"),
        FW(2, "παρακολουθεί", "VERB", "Number=Sing", head=1, deprel="acl:relcl"),
        FW(3, rel_lemma, "PRON", rel_feats, head=2, deprel="nsubj"),
    ]


def test_rel_agreement_clean():
    words = _relcl("Case=Nom|Gender=Masc|Number=Sing",
                   "Case=Nom|Gender=Masc|Number=Sing|PronType=Rel")
    assert rel_agreement(*sent(words), {}) == []


def test_rel_agreement_gender_mismatch():
    words = _relcl("Case=Nom|Gender=Masc|Number=Sing",
                   "Case=Nom|Gender=Fem|Number=Sing|PronType=Rel")
    assert any("Gender" in f[2] for f in rel_agreement(*sent(words), {}))


def test_rel_agreement_number_mismatch():
    words = _relcl("Case=Nom|Gender=Masc|Number=Sing",
                   "Case=Nom|Gender=Masc|Number=Plur|PronType=Rel")
    assert any("Number" in f[2] for f in rel_agreement(*sent(words), {}))


def test_rel_agreement_case_is_free():
    # relative pronoun takes its case from the clause; only Gender/Number checked
    words = _relcl("Case=Nom|Gender=Fem|Number=Plur",
                   "Case=Gen|Gender=Fem|Number=Plur|PronType=Rel")
    assert rel_agreement(*sent(words), {}) == []


def test_rel_agreement_resolves_through_pp():
    # pronoun governed by an adverb inside the clause; antecedent is the relcl head
    words = [
        FW(1, "πρόταση", "NOUN", "Case=Nom|Gender=Fem|Number=Sing", head=4, deprel="nsubj"),
        FW(2, "σύμφωνα", "ADV", head=4, deprel="advmod"),
        FW(3, "οποία", "PRON", "Case=Acc|Gender=Masc|Number=Sing|PronType=Rel", head=2, deprel="obl", lemma="οποίος"),
        FW(4, "έγινε", "VERB", "Number=Sing", head=0, deprel="root"),
        FW(5, "δεχτεί", "VERB", head=1, deprel="acl:relcl"),
    ]
    # pronoun (3) -> adverb (2) -> relcl verb (5) -> antecedent (1); walk-up finds it
    words[2].head = 5
    words[1].head = 5
    s, by_id = sent(words)
    assert any("Gender" in f[2] for f in rel_agreement(s, by_id, {}))


def test_rel_agreement_ignores_non_relative():
    words = _relcl("Case=Nom|Gender=Masc|Number=Sing",
                   "Case=Nom|Gender=Fem|Number=Sing", rel_lemma="αυτός")
    assert rel_agreement(*sent(words), {}) == []


def test_prep_case_gen_governing():
    words = [
        FW(1, "Λόγω", "ADP", head=2, deprel="case"),
        FW(2, "καθυστέρηση", "NOUN", "Case=Acc|Gender=Fem|Number=Sing"),
    ]
    s, by_id = sent(words)
    assert any("Gen" in f[2] for f in prep_case(s, by_id, {}))


def test_prep_case_measured_gen_preps_govern_gen():
    for adp in ("Εξαιτίας", "Μέσω", "Εναντίον", "Περί", "Υπέρ", "Ενώπιον"):
        words = [
            FW(1, adp, "ADP", head=2, deprel="case"),
            FW(2, "προβλήματος", "NOUN", "Case=Gen|Gender=Neut|Number=Sing"),
        ]
        s, by_id = sent(words)
        assert prep_case(s, by_id, {}) == [], adp


def test_prep_case_mechri_dual_case_skipped():
    for case in ("Acc", "Gen"):
        words = [
            FW(1, "μέχρι", "ADP", head=2, deprel="case"),
            FW(2, "βράδυ" if case == "Acc" else "βραδίου",
               "NOUN", f"Case={case}|Gender=Neut|Number=Sing"),
        ]
        s, by_id = sent(words)
        assert prep_case(s, by_id, {}) == [], case


def test_prep_case_new_gen_prep_flags_acc():
    words = [
        FW(1, "Εξαιτίας", "ADP", head=2, deprel="case"),
        FW(2, "πρόβλημα", "NOUN", "Case=Acc|Gender=Neut|Number=Sing"),
    ]
    s, by_id = sent(words)
    assert any("Gen" in f[2] for f in prep_case(s, by_id, {}))


def test_prep_case_fossilized_dative_skipped():
    words = [
        FW(1, "εν", "ADP", head=2, deprel="case"),
        FW(2, "συντομία", "NOUN", "Case=Dat|Gender=Fem|Number=Sing"),
    ]
    s, by_id = sent(words)
    assert prep_case(s, by_id, {}) == []


def test_prep_case_ypo_dual_case_skipped():
    words = [
        FW(1, "υπό", "ADP", head=2, deprel="case"),
        FW(2, "έλεγχο", "NOUN", "Case=Acc|Gender=Masc|Number=Sing"),
    ]
    s, by_id = sent(words)
    assert prep_case(s, by_id, {}) == []


def test_prep_case_pron_head_skipped():
    words = [
        FW(1, "σε", "ADP", head=2, deprel="case"),
        FW(2, "μας", "PRON", "Case=Gen|Number=Plur|Person=1"),
    ]
    s, by_id = sent(words)
    assert prep_case(s, by_id, {}) == []


def test_prep_case_unseen_head_form_skipped():
    words = [
        FW(1, "για", "ADP", head=2, deprel="case"),
        FW(2, "Ανατολάς", "PROPN", "Case=Gen|Number=Plur"),
    ]
    s, by_id = sent(words)
    lex = FakeLexicon(nominal_cases={})
    assert prep_case(s, by_id, {"lexicon": lex}) == []


def test_prep_case_seen_head_wrong_case_fires():
    words = [
        FW(1, "Λόγω", "ADP", head=2, deprel="case"),
        FW(2, "καθυστέρηση", "NOUN", "Case=Acc|Gender=Fem|Number=Sing"),
    ]
    s, by_id = sent(words)
    lex = FakeLexicon(nominal_cases={"καθυστέρηση": ["Gen", "Acc"]})
    assert any("Gen" in f[2] for f in prep_case(s, by_id, {"lexicon": lex}))


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


def test_propn_accent_flagged():
    lex = PropnLexicon(["Ρωσία"])
    words = [FW(1, "Ρωσια", "PROPN", head=0, deprel="root")]
    s, by_id = sent(words)
    flags = propn_accent(s, by_id, {"propn": lex})
    assert flags and flags[0][3] == "Ρωσία"


def test_propn_accent_clean_and_ambiguous():
    assert propn_accent(*sent([FW(1, "Ρωσία", "PROPN", head=0, deprel="root")]),
                        {"propn": PropnLexicon(["Ρωσία"])}) == []
    # ambiguous (both accented and unaccented attested) -> never flag
    amb = PropnLexicon(["Αθηνα", "Αθήνα"])
    assert propn_accent(*sent([FW(1, "Αθηνα", "PROPN", head=0, deprel="root")]),
                        {"propn": amb}) == []


def _v(rule, severity):
    from types import SimpleNamespace
    return SimpleNamespace(rule=rule, severity=severity)


def test_filter_by_rules():
    vs = [_v("det_noun", "medium"), _v("typography", "low")]
    assert [v.rule for v in filter_violations(vs, rules=["typography"])] == ["typography"]


def test_filter_by_min_severity():
    vs = [_v("typography", "low"), _v("det_noun", "medium"), _v("negation", "high")]
    assert [v.rule for v in filter_violations(vs, min_severity="medium")] == ["det_noun", "negation"]
    assert [v.rule for v in filter_violations(vs, min_severity="high")] == ["negation"]
    assert len(filter_violations(vs, min_severity="low")) == 3


def test_filter_combined():
    vs = [_v("typography", "low"), _v("det_noun", "medium")]
    assert filter_violations(vs, min_severity="medium", rules=["typography"]) == []


def test_num_noun_gender_mismatch_flagged():
    words = [
        FW(1, "τρεις", "NUM", "Case=Acc|Gender=Neut|Number=Plur", head=2, deprel="nummod"),
        FW(2, "παιδιά", "NOUN", "Case=Acc|Gender=Neut|Number=Plur"),
    ]
    s, by_id = sent(words)
    flags = num_noun(s, by_id, {})
    assert any("Gender" in f[2] for f in flags)
    assert flags[0][3] == "τρία"


def test_num_noun_uses_surface_form_not_tagger_feats():
    # tagger repaired the numeral's Gender to Neut; the form 'τρεις' is M/F,
    # so against a neuter noun it must still flag.
    words = [
        FW(1, "τρεις", "NUM", "Gender=Neut|Number=Plur", head=2, deprel="nummod"),
        FW(2, "παιδιά", "NOUN", "Gender=Neut|Number=Plur"),
    ]
    s, by_id = sent(words)
    assert any("Gender" in f[2] for f in num_noun(s, by_id, {}))


def test_num_noun_clean_pairs():
    for num, noun, g in [("τρεις", "άνδρες", "Masc"), ("τρία", "παιδιά", "Neut"),
                         ("τέσσερις", "γυναίκες", "Fem"), ("τέσσερα", "παιδιά", "Neut")]:
        words = [
            FW(1, num, "NUM", f"Gender={g}|Number=Plur", head=2, deprel="nummod"),
            FW(2, noun, "NOUN", f"Gender={g}|Number=Plur"),
        ]
        s, by_id = sent(words)
        assert num_noun(s, by_id, {}) == [], f"{num} {noun} should be clean"


def test_num_noun_ignores_invariable_numerals():
    words = [
        FW(1, "δύο", "NUM", "Gender=Neut|Number=Plur", head=2, deprel="nummod"),
        FW(2, "γυναίκες", "NOUN", "Gender=Fem|Number=Plur"),
    ]
    s, by_id = sent(words)
    assert num_noun(s, by_id, {}) == []


def test_num_noun_uses_lexicon_noun_gender():
    # feats say Neut but the lexicon attests the lemma as Masc -> clean
    words = [
        FW(1, "τρεις", "NUM", "Gender=Neut|Number=Plur", head=2, deprel="nummod", lemma="τρεις"),
        FW(2, "άνδρες", "NOUN", "Gender=Neut|Number=Plur", lemma="άνδρας"),
    ]
    s, by_id = sent(words)
    lex = FakeLexicon(noun_genders={"άνδρας": "Masc"})
    assert num_noun(s, by_id, {"lexicon": lex}) == []


def _unknown_dict(monkeypatch, kind="nonword", suggestions=()):
    monkeypatch.setattr(orth_layer, "is_known", lambda t: False)
    monkeypatch.setattr(orth_layer, "classify_unknown", lambda t: (kind, list(suggestions)))


def test_spelling_flags_unknown_word(monkeypatch):
    _unknown_dict(monkeypatch, suggestions=["σωστή λήψη"])
    words = [FW(1, "τρισκαίδεκαφωτιά", "NOUN", "Case=Nom|Number=Sing")]
    s, by_id = sent(words)
    flags = spelling(s, by_id, {})
    assert flags and "NONWORD" in flags[0][2]


def test_spelling_formlexicon_coverage_suppresses(monkeypatch):
    _unknown_dict(monkeypatch)
    words = [FW(1, "βοειδών", "NOUN", "Case=Gen|Number=Plur")]
    s, by_id = sent(words)
    assert spelling(s, by_id, {}) != []
    env = {"lexicon": FormLexicon({"βοειδών": {("NOUN", (("Case", "Gen"),))}})}
    assert spelling(s, by_id, env) == []


def test_spelling_propn_coverage_suppresses(monkeypatch):
    _unknown_dict(monkeypatch)
    words = [FW(1, "Χρυσοπηγής", "NOUN", "Case=Gen|Number=Sing")]
    s, by_id = sent(words)
    assert spelling(s, by_id, {}) != []
    env = {"propn": PropnLexicon(["Χρυσοπηγής"])}
    assert spelling(s, by_id, env) == []


def test_spelling_coverage_is_case_insensitive(monkeypatch):
    _unknown_dict(monkeypatch)
    words = [FW(1, "Ευρωζώνη", "NOUN", "Case=Nom|Number=Sing")]
    s, by_id = sent(words)
    env = {"propn": PropnLexicon(["ευρωζώνη"])}
    assert spelling(s, by_id, env) == []


def test_spelling_abbreviations_and_elisions_skipped(monkeypatch):
    _unknown_dict(monkeypatch)
    for text in ("χλμ.", "απ'", "ό,τι", "μ.Χ.", "καθ'"):
        words = [FW(1, text, "NOUN", "Case=Nom|Number=Sing")]
        s, by_id = sent(words)
        assert spelling(s, by_id, {}) == [], text


def test_spelling_script_mix_not_suppressed_by_guards(monkeypatch):
    _unknown_dict(monkeypatch)
    words = [FW(1, "Kαζάρμα", "NOUN", "Case=Nom|Number=Sing")]
    s, by_id = sent(words)
    flags = spelling(s, by_id, {"propn": PropnLexicon(["καζάρμα"])})
    assert flags and "SCRIPT-MIX" in flags[0][2]


def test_spelling_accent_flag_carries_suggestion(monkeypatch):
    _unknown_dict(monkeypatch, kind="accent", suggestions=["διαβάσω"])
    words = [FW(1, "διαβασω", "VERB", "Mood=Sub|Number=Sing")]
    s, by_id = sent(words)
    flags = spelling(s, by_id, {})
    assert flags and "ACCENT" in flags[0][2] and flags[0][3] == "διαβάσω"


def test_spelling_unaccented_propn_match_still_flagged(monkeypatch):
    # 'απο' is an unaccented Wikipedia title variant, homographic with the
    # de-accented form of 'από' — an accent error there must stay flagged.
    _unknown_dict(monkeypatch)
    words = [FW(1, "απο", "ADP", "")]
    s, by_id = sent(words)
    env = {"propn": PropnLexicon(["απο"])}
    assert spelling(s, by_id, env) != []

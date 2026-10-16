from fakes import FW, sent

from cadmus.rules.morphology import copula_pred, na_form


class FakeVerbForms:
    def __init__(self, illegal):
        self.illegal = set(illegal)

    def illegal_after_na(self, form):
        return form.lower() in self.illegal


# --- copula_pred ---

def test_copula_clean_nominative_not_flagged():
    # Είναι γιατρός  (γιατρός = masc nom sg)
    words = [FW(1, "Είναι", "AUX", "Mood=Ind|Number=Sing", "είμαι", head=2, deprel="cop"),
             FW(2, "γιατρός", "NOUN", "Case=Nom|Gender=Masc|Number=Sing", "γιατρός")]
    s, by_id = sent(words)
    assert copula_pred(s, by_id, {}) == []


def test_copula_accusative_predicate_flagged():
    # Είναι γιατρό  (tagger repairs Case to Nom; surface -ό is accusative)
    words = [FW(1, "Είναι", "AUX", "Mood=Ind|Number=Sing", "είμαι", head=2, deprel="cop"),
             FW(2, "γιατρό", "NOUN", "Case=Nom|Gender=Masc|Number=Sing", "γιατρός")]
    s, by_id = sent(words)
    out = copula_pred(s, by_id, {})
    assert len(out) == 1 and out[0][0].text == "γιατρό"


def test_copula_root_copula_nsubj_flagged():
    # Θα γίνεις πρόεδρο  (γίνεις root, πρόεδρο nsubj masc acc)
    words = [FW(1, "Θα", "AUX", None, "θα", head=2, deprel="aux"),
             FW(2, "γίνεις", "VERB", "Mood=Ind|Number=Sing", "γίνομαι", head=0, deprel="root"),
             FW(3, "πρόεδρο", "NOUN", "Case=Nom|Gender=Masc|Number=Sing", "πρόεδρος", head=2, deprel="nsubj")]
    s, by_id = sent(words)
    out = copula_pred(s, by_id, {})
    assert len(out) == 1 and out[0][0].text == "πρόεδρο"


def test_copula_feminine_not_flagged():
    # Είναι δασκάλα  (feminine nom=acc syncretism -> never flagged)
    words = [FW(1, "Είναι", "AUX", "Mood=Ind|Number=Sing", "είμαι", head=2, deprel="cop"),
             FW(2, "δασκάλα", "NOUN", "Case=Nom|Gender=Fem|Number=Sing", "δασκάλα")]
    s, by_id = sent(words)
    assert copula_pred(s, by_id, {}) == []


def test_copula_plural_accusative_flagged_nominative_not():
    acc = [FW(1, "Είναι", "AUX", "Mood=Ind", "είμαι", head=2, deprel="cop"),
           FW(2, "γιατρούς", "NOUN", "Case=Nom|Gender=Masc|Number=Plur", "γιατρός")]
    nom = [FW(1, "Είναι", "AUX", "Mood=Ind", "είμαι", head=2, deprel="cop"),
           FW(2, "γιατροί", "NOUN", "Case=Nom|Gender=Masc|Number=Plur", "γιατρός")]
    s, by_id = sent(acc)
    assert len(copula_pred(s, by_id, {})) == 1
    s, by_id = sent(nom)
    assert copula_pred(s, by_id, {}) == []


# --- na_form ---

def test_na_form_past_indicative_flagged():
    # να πήγες  (πήγες = aorist indicative, illegal after να)
    words = [FW(1, "να", "AUX", None, "να", head=2, deprel="aux"),
             FW(2, "πήγες", "VERB", "Aspect=Perf|Number=Sing|Person=2", "πηγαίνω", head=0, deprel="root")]
    s, by_id = sent(words)
    env = {"verbforms": FakeVerbForms({"πήγες"})}
    out = na_form(s, by_id, env)
    assert len(out) == 1 and out[0][0].text == "πήγες"


def test_na_form_dependent_not_flagged():
    # να έρθεις  (dependent form, legal)
    words = [FW(1, "να", "AUX", None, "να", head=2, deprel="aux"),
             FW(2, "έρθεις", "VERB", "Aspect=Perf|Number=Sing|Person=2", "έρχομαι", head=0, deprel="root")]
    s, by_id = sent(words)
    env = {"verbforms": FakeVerbForms({"πήγες"})}
    assert na_form(s, by_id, env) == []


def test_na_form_without_na_not_flagged():
    words = [FW(1, "Έκανε", "VERB", "Aspect=Perf|Tense=Past", "κάνω", head=0, deprel="root")]
    s, by_id = sent(words)
    env = {"verbforms": FakeVerbForms({"έκανε"})}
    assert na_form(s, by_id, env) == []


def test_na_form_without_lexicon_is_noop():
    words = [FW(1, "να", "AUX", None, "να", head=2, deprel="aux"),
             FW(2, "πήγες", "VERB", None, "πηγαίνω", head=0, deprel="root")]
    s, by_id = sent(words)
    assert na_form(s, by_id, {}) == []

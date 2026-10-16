from .agreement import adj_noun, det_noun, rel_agreement, subj_verb
from .government import prep_case
from .negation import negation
from .orthography import spelling
from .propn import propn_accent
from .valence import verb_valence

RULES = {
    "det_noun": det_noun,
    "adj_noun": adj_noun,
    "subj_verb": subj_verb,
    "rel_agreement": rel_agreement,
    "prep_case": prep_case,
    "spelling": spelling,
    "verb_valence": verb_valence,
    "negation": negation,
    "propn_accent": propn_accent,
}

DAMPENABLE = {"det_noun", "adj_noun", "subj_verb", "rel_agreement", "prep_case", "verb_valence", "negation"}

__all__ = ["RULES", "DAMPENABLE"]

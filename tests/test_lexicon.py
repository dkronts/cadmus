import io

from cadmus.lexicon import FormLexicon, VerbFrames

MINI = """# sent_id = mini-1
# text = Ο σκύλος τρώει το φαγητό
1\tΟ\tο\tDET\tDET\tCase=Nom|Definite=Def|Gender=Masc|Number=Sing|PronType=Art\t2\tdet\t_\t_
2\tσκύλος\tσκύλος\tNOUN\tNOUN\tCase=Nom|Gender=Masc|Number=Sing\t3\tnsubj\t_\t_
3\tτρώει\tτρώω\tVERB\tVERB\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t_\t_
4\tτο\tο\tDET\tDET\tCase=Acc|Definite=Def|Gender=Neut|Number=Sing|PronType=Art\t5\tdet\t_\t_
5\tφαγητό\tφαγητό\tNOUN\tNOUN\tCase=Acc|Gender=Neut|Number=Sing\t3\tobj\t_\t_

# sent_id = mini-2
# text = Ο σκύλος τρώει
1\tΟ\tο\tDET\tDET\tCase=Nom|Definite=Def|Gender=Masc|Number=Sing|PronType=Art\t2\tdet\t_\t_
2\tσκύλος\tσκύλος\tNOUN\tNOUN\tCase=Nom|Gender=Masc|Number=Sing\t3\tnsubj\t_\t_
3\tτρώει\tτρώω\tVERB\tVERB\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t_\t_
"""


class _Word:
    def __init__(self, text, upos, feats):
        self.text = text
        self.upos = upos
        self.feats = feats


def _write(tmp_path):
    p = tmp_path / "mini.conllu"
    p.write_text(MINI, encoding="utf-8")
    return p


def test_form_lexicon_build(tmp_path):
    lex = FormLexicon.build(_write(tmp_path))
    analyses = lex.entries["σκύλος"]
    assert ["NOUN", [["Case", "Nom"], ["Gender", "Masc"], ["Number", "Sing"]]] in analyses
    assert not lex.is_suspect(_Word("σκύλος", "NOUN", "Case=Nom|Gender=Masc|Number=Sing"))
    assert lex.is_suspect(_Word("σκύλος", "NOUN", "Case=Acc|Gender=Masc|Number=Sing"))
    assert not lex.is_suspect(_Word("φοο", "NOUN", "Case=Acc"))


def test_form_gender_reads_noun_propn_entries(tmp_path):
    lex = FormLexicon.build(_write(tmp_path))
    assert lex.form_gender("σκύλος") == {"Masc"}
    assert lex.form_gender("Σκύλος") == {"Masc"}
    assert lex.form_gender("φαγητό") == {"Neut"}
    assert lex.form_gender("αόρατο") == set()
    assert lex.form_gender("το") == set()  # DET attestation carries no noun gender
    dual = FormLexicon({"ξ": {("NOUN", (("Case", "Nom"), ("Gender", "Masc"))),
                              ("PROPN", (("Gender", "Fem"),)),
                              ("ADJ", (("Gender", "Neut"),)),
                              ("NOUN", (("Case", "Gen"), ("Number", "Sing")))}})
    assert dual.form_gender("ξ") == {"Masc", "Fem"}


def test_verb_frames_build(tmp_path):
    frames = VerbFrames.build(_write(tmp_path))
    counter = frames.counters["τρώω"]
    assert counter[("obj",)] == 1
    assert counter[()] == 1


def test_verb_frames_unexpected(tmp_path):
    frames = VerbFrames.build(_write(tmp_path))
    frames.MIN_TOTAL = 2

    class _C:
        def __init__(self, deprel):
            self.deprel = deprel

    class _V:
        text, lemma = "τρώει", "τρώω"

    # v0.0.21 skeleton relaxation: obj+iobj is clitic-tagging noise against
    # an attested obj frame, not a valence surprise
    assert frames.unexpected(_V(), [_C("obj"), _C("iobj")]) is None
    assert frames.unexpected(_V(), [_C("obj")]) is None

    from collections import Counter

    intrans = VerbFrames({"τρώω": Counter({(): 9})})
    intrans.MIN_TOTAL = 2
    msg = intrans.unexpected(_V(), [_C("obj")])
    assert msg is not None and "VERB-VALENCE" in msg

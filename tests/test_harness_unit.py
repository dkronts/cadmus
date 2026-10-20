"""Model-free, asset-free tests for the 456-sweep loader and report."""

import importlib.util
import random
from pathlib import Path

import pytest

from cadmus.checker import Violation
from cadmus.eval import harness
from cadmus.eval.harness import load_sweep_sentences, load_targeted_sentences, run_eval, run_sweep

TEXTS = [
    "Τρεις λέξεις εδώ",
    "Απάντησε στο mail@example.com άμεσα παρακαλώ",
    "Μια πολύ μεγάλη πρόταση που έχει πολλές λέξεις και ξεπερνά καθαρά τα δεκαπέντε tokens",
    "Σύντομη πρόταση.",
]


def _fixture(tmp_path):
    lines = []
    for i, text in enumerate(TEXTS, start=1):
        lines.append(f"# sent_id = {i}")
        lines.append(f"# text = {text}")
        lines.append("1\tλέξη\tλέξη\t_\t_\t_\t0\troot\t_\t_")
        lines.append("")
    path = tmp_path / "fixture.conllu"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_load_sweep_sentences_returns_every_text_in_order(tmp_path):
    path = _fixture(tmp_path)
    assert load_sweep_sentences(path=path) == TEXTS


def test_load_sweep_sentences_keeps_short_and_at_sign_sentences(tmp_path):
    path = _fixture(tmp_path)
    texts = load_sweep_sentences(path=path)
    assert len(texts) == 4
    assert len(texts[0].split()) == 3
    assert any("@" in t for t in texts)


class StubChecker:
    def __init__(self):
        self._damp_stats = {"suppressed": 2, "fired": 5}
        self.batches = []

    def check_batch(self, texts, batch_size=32):
        texts = list(texts)
        self.batches.append(texts)
        out = [[] for _ in texts]
        out[0].append(Violation(texts[0], "spelling", "unknown form 'λεξη'", 0, 4))
        out[1].append(Violation(texts[1], "typography", "space before punct", 0, 1))
        out[2].append(Violation(texts[2], "spelling", "unknown form 'tokens'", 0, 6))
        return out


class ManySpellingChecker:
    def __init__(self):
        self._damp_stats = {"suppressed": 0, "fired": 0}

    def check_batch(self, texts, batch_size=32):
        out = [[] for _ in texts]
        for i, msg in [(0, "m0"), (0, "m1"), (1, "m2"), (1, "m3"), (2, "m4")]:
            out[i].append(Violation(texts[i], "spelling", msg, 0, 4))
        return out


class EmptyChecker:
    def __init__(self):
        self._damp_stats = {"suppressed": 0, "fired": 0}

    def check_batch(self, texts, batch_size=32):
        return [[] for _ in texts]


class ShortResultsChecker:
    """check_batch returns one fewer result than inputs, from short_from_call on."""

    def __init__(self, short_from_call=0):
        self._damp_stats = {"suppressed": 0, "fired": 0}
        self.calls = 0
        self.short_from_call = short_from_call

    def check_batch(self, texts, batch_size=32):
        results = [[] for _ in texts]
        if self.calls >= self.short_from_call:
            results = results[:-1]
        self.calls += 1
        return results


def test_run_sweep_report_counts_and_dampener(monkeypatch):
    monkeypatch.setattr(harness, "load_sweep_sentences", lambda path=None: list(TEXTS))
    stub = StubChecker()
    report = run_sweep(checker=stub)

    assert stub.batches == [TEXTS]
    assert "4 sentences" in report
    assert "full clean sweep (all # text lines)" in report
    spelling = [ln for ln in report.splitlines() if "spelling" in ln]
    typography = [ln for ln in report.splitlines() if "typography" in ln]
    assert len(spelling) == 1 and " 2 " in spelling[0]
    assert len(typography) == 1 and " 1 " in typography[0]
    assert "dampener: 2 flags suppressed by lexicon, 5 fired" in report


def test_run_sweep_forwards_path_to_load_sweep_sentences(monkeypatch):
    recorded = []

    def recorder(path=None):
        recorded.append(path)
        return list(TEXTS)

    monkeypatch.setattr(harness, "load_sweep_sentences", recorder)

    some_path = "other/ud-file.conllu"
    run_sweep(checker=StubChecker(), path=some_path)
    assert recorded == [some_path]

    run_sweep(checker=StubChecker())
    assert recorded == [some_path, None]


def test_run_sweep_caps_samples_at_three():
    checker = ManySpellingChecker()
    counts, samples = harness.sweep_tally(zip(TEXTS, checker.check_batch(TEXTS)))
    assert counts["spelling"] == 5
    assert [msg for _, msg in samples["spelling"]] == ["m0", "m1", "m2"]


def test_run_sweep_verbose_prints_each_violation(monkeypatch, capsys):
    monkeypatch.setattr(harness, "load_sweep_sentences", lambda path=None: list(TEXTS))
    run_sweep(checker=StubChecker(), verbose=True)
    out = capsys.readouterr().out
    assert "[spelling] Τρεις λέξεις εδώ -> unknown form 'λεξη'" in out
    assert (
        "[typography] Απάντησε στο mail@example.com άμεσα παρακαλώ "
        "-> space before punct" in out
    )
    assert out.count("[spelling]") == 2


def test_run_sweep_empty_counts_prints_none(monkeypatch):
    monkeypatch.setattr(harness, "load_sweep_sentences", lambda path=None: list(TEXTS))
    report = run_sweep(checker=EmptyChecker())
    assert "violations on clean text:\n  none" in report


def test_run_sweep_raises_when_checker_returns_short_results(monkeypatch):
    monkeypatch.setattr(harness, "load_sweep_sentences", lambda path=None: list(TEXTS))
    with pytest.raises(ValueError, match="checker returned 3 results for 4 inputs"):
        run_sweep(checker=ShortResultsChecker())


def test_run_eval_fp_tally_uses_check_batch(monkeypatch):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    monkeypatch.setattr(harness, "load_targeted_sentences", lambda path=None, forms=None: [])
    stub = StubChecker()
    report = run_eval(checker=stub)

    assert stub.batches == [TEXTS]
    assert "4 clean sentences" in report
    spelling = [ln for ln in report.splitlines() if "spelling" in ln]
    typography = [ln for ln in report.splitlines() if "typography" in ln]
    assert len(spelling) == 1 and " 2 " in spelling[0]
    assert len(typography) == 1 and " 1 " in typography[0]
    assert "dampener: 2 flags suppressed by lexicon, 5 fired" in report


class RecallStubChecker:
    def __init__(self, fire_for=()):
        self._damp_stats = {"suppressed": 0, "fired": 0}
        self.batches = []
        self.fire_for = set(fire_for)

    def check_batch(self, texts, batch_size=32):
        texts = list(texts)
        self.batches.append(texts)
        return [
            [Violation(t, "spelling", "unknown form", 0, 4)] if t in self.fire_for else []
            for t in texts
        ]


def _recall_report(monkeypatch, checker, corrupt_map, verbose=False):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: corrupt_map.get(s))
    monkeypatch.setattr(harness, "load_targeted_sentences", lambda path=None, forms=None: [])
    return run_eval(checker=checker, verbose=verbose)


def test_run_eval_recall_batches_corrupted_and_tallies_hit_and_miss(monkeypatch):
    hit = TEXTS[0] + " ληθ"
    miss = TEXTS[1] + " ληθ"
    checker = RecallStubChecker(fire_for={hit})
    report = _recall_report(
        monkeypatch,
        checker,
        {TEXTS[0]: (hit, "nonword"), TEXTS[1]: (miss, "nonword")},
    )
    assert checker.batches == [TEXTS, [hit, miss]]
    recall_lines = [ln for ln in report.splitlines() if "nonword" in ln]
    assert recall_lines == ["  nonword      1/2  (50%)"]


def test_run_eval_verbose_prints_miss_line(monkeypatch, capsys):
    corrupted = TEXTS[0] + " αβγ"
    checker = RecallStubChecker()
    report = _recall_report(
        monkeypatch, checker, {TEXTS[0]: (corrupted, "nonword")}, verbose=True
    )
    out = capsys.readouterr().out
    assert f"  MISS [nonword]: {corrupted[:70]} -> []" in out
    assert "  nonword      0/1  (0%)" in report


def test_run_eval_verbose_groups_fp_and_recall_sections(monkeypatch, capsys):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    corrupt_map = {s: (s + " αβγ", "negation") for s in TEXTS}
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: corrupt_map.get(s))
    monkeypatch.setattr(harness, "load_targeted_sentences", lambda path=None, forms=None: [])
    run_eval(checker=StubChecker(), verbose=True)
    out = capsys.readouterr().out

    assert "[spelling] Τρεις λέξεις εδώ -> unknown form 'λεξη'" in out
    fp_header = out.index("false positives on clean text:")
    first_spelling = out.index("[spelling]")
    recall_header = out.index("recall on injected errors:")
    first_miss = out.index("MISS [negation]")
    assert fp_header < first_spelling < recall_header < first_miss


def test_run_eval_empty_fp_prints_none(monkeypatch):
    report = _recall_report(monkeypatch, EmptyChecker(), {})
    assert "false positives on clean text:\n  none" in report


def test_run_eval_empty_recall_prints_none(monkeypatch):
    report = _recall_report(monkeypatch, EmptyChecker(), {})
    assert "recall on injected errors:\n  none" in report


def test_run_eval_verbose_empty_fp_prints_none(monkeypatch, capsys):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    monkeypatch.setattr(harness, "load_targeted_sentences", lambda path=None, forms=None: [])
    run_eval(checker=EmptyChecker(), verbose=True)
    out = capsys.readouterr().out
    assert "false positives on clean text:\n  none" in out


def test_run_eval_verbose_empty_recall_prints_none(monkeypatch, capsys):
    _recall_report(monkeypatch, EmptyChecker(), {}, verbose=True)
    out = capsys.readouterr().out
    assert "recall on injected errors:\n  none" in out


def test_run_eval_recall_raises_when_checker_returns_short_results(monkeypatch):
    corrupted = TEXTS[0] + " ληθ"
    with pytest.raises(ValueError, match="checker returned 0 results for 1 inputs"):
        _recall_report(
            monkeypatch,
            ShortResultsChecker(short_from_call=1),
            {TEXTS[0]: (corrupted, "nonword")},
        )


TARGETED_TEXTS = [
    "Ο καθηγητής που μίλησε χθες στην εκδήλωση ο οποίος παρουσίασε τα νέα ευρήματα "
    "της έρευνας που διεξήχθη το περασμένο εξάμηνο στο εργαστήριο",
    "τρεις φίλοι ήρθαν",
    "Σύντομη πρόταση.",
    "Ο οποίος παρουσίασε τα νέα ευρήματα της έρευνας που διεξήχθη χθες #2 στο εργαστήριο",
    "Ο οποίος ψήφισε το draft στο meeting δεν ήρθε καθόλου",
]


def _targeted_fixture(tmp_path):
    lines = []
    for i, text in enumerate(TARGETED_TEXTS, start=1):
        lines.append(f"# sent_id = {i}")
        lines.append(f"# text = {text}")
        lines.append("1\tλέξη\tλέξη\t_\t_\t_\t0\troot\t_\t_")
        lines.append("")
    path = tmp_path / "targeted.conllu"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_load_targeted_sentences_keeps_construction_bearing_any_length(tmp_path):
    path = _targeted_fixture(tmp_path)
    texts = load_targeted_sentences(path=path)
    assert texts == [TARGETED_TEXTS[0], TARGETED_TEXTS[1]]
    assert len(texts[0].split()) >= 20
    assert len(texts[1].split()) == 3


def test_load_targeted_sentences_honours_explicit_forms(tmp_path):
    path = _targeted_fixture(tmp_path)
    assert load_targeted_sentences(path=path, forms={"ήρθαν"}) == [TARGETED_TEXTS[1]]


class TargetedStubChecker:
    def __init__(self, rules_by_text):
        self._damp_stats = {"suppressed": 0, "fired": 0}
        self.batches = []
        self.rules_by_text = rules_by_text

    def check_batch(self, texts, batch_size=32):
        texts = list(texts)
        self.batches.append(texts)
        return [
            [Violation(t, r, "targeted", 0, 4) for r in self.rules_by_text.get(t, [])]
            for t in texts
        ]


def test_run_eval_targeted_section_reports_per_rule_recall(monkeypatch):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    rel_sentence = "Ο άντρας ο οποίος μίλησε χθες ήταν ήρεμος"
    num_sentence = "τρεις κορίτσια τραγούδησαν χθες"
    monkeypatch.setattr(
        harness,
        "load_targeted_sentences",
        lambda path=None, forms=None: [rel_sentence, num_sentence],
    )
    rel_corrupted, rel_target = harness.corrupt_rel_agreement(rel_sentence, random.Random(0))
    num_corrupted, num_target = harness.corrupt_num_noun(num_sentence, random.Random(0))
    assert {rel_target, num_target} <= set(harness.TARGET_RULES)

    checker = TargetedStubChecker({rel_corrupted: ["rel_agreement"]})
    report = run_eval(checker=checker)

    assert checker.batches == [TEXTS, [rel_corrupted, num_corrupted]]
    section = report.split("targeted recall (construction pool):\n")[1]
    lines = []
    for ln in section.splitlines():
        if not ln.strip():
            break
        lines.append(ln)
    assert lines == ["  num_noun     0/1  (0%)", "  rel_agreement 1/1  (100%)"]


def test_run_eval_empty_targeted_pool_prints_none(monkeypatch):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    monkeypatch.setattr(harness, "load_targeted_sentences", lambda path=None, forms=None: [])
    report = run_eval(checker=EmptyChecker())
    assert "targeted recall (construction pool):\n  none" in report


def test_run_eval_verbose_prints_targeted_miss_line(monkeypatch, capsys):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: [])
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    rel_sentence = "Ο άντρας ο οποίος μίλησε χθες ήταν ήρεμος"
    monkeypatch.setattr(
        harness, "load_targeted_sentences", lambda path=None, forms=None: [rel_sentence]
    )
    run_eval(checker=EmptyChecker(), verbose=True)
    out = capsys.readouterr().out

    recall_header = out.index("recall on injected errors:")
    targeted_header = out.index("targeted recall (construction pool):")
    first_miss = out.index("  MISS [rel_agreement]")
    assert recall_header < targeted_header < first_miss


def test_run_eval_verbose_empty_targeted_prints_none(monkeypatch, capsys):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    monkeypatch.setattr(harness, "load_targeted_sentences", lambda path=None, forms=None: [])
    run_eval(checker=EmptyChecker(), verbose=True)
    out = capsys.readouterr().out

    assert "targeted recall (construction pool):\n  none" in out
    fp_header = out.index("false positives on clean text:")
    recall_header = out.index("recall on injected errors:")
    targeted_header = out.index("targeted recall (construction pool):")
    assert fp_header < recall_header < targeted_header


def test_run_eval_verbose_targeted_header_names_targeted_path(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    monkeypatch.setattr(harness, "load_targeted_sentences", lambda path=None, forms=None: [])
    tgt = str(tmp_path / "alt_pool.conllu")
    run_eval(checker=EmptyChecker(), verbose=True, targeted_path=tgt)
    out = capsys.readouterr().out

    assert "targeted recall (alt_pool.conllu):" in out
    assert "targeted recall (construction pool):" not in out


def test_run_eval_verbose_targeted_false_omits_header(monkeypatch, capsys):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    monkeypatch.setattr(harness, "load_targeted_sentences", lambda path=None, forms=None: [])
    run_eval(checker=EmptyChecker(), verbose=True, targeted=False)
    out = capsys.readouterr().out

    assert "targeted recall (construction pool):" not in out
    assert "false positives on clean text:" in out
    assert "recall on injected errors:" in out


def test_run_eval_targeted_false_skips_load_and_section(monkeypatch):
    recorded = []

    def recorder(path=None, forms=None):
        recorded.append(path)
        return []

    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    monkeypatch.setattr(harness, "load_targeted_sentences", recorder)
    report = run_eval(checker=EmptyChecker(), targeted=False)

    assert recorded == []
    assert "targeted recall" not in report


def test_run_eval_forwards_targeted_path(monkeypatch):
    recorded = []

    def recorder(path=None, forms=None):
        recorded.append(path)
        return []

    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    monkeypatch.setattr(harness, "load_targeted_sentences", recorder)
    run_eval(checker=EmptyChecker(), targeted_path="other/file.conllu")

    assert recorded == ["other/file.conllu"]


CLEAN_TEXTS = [
    "Τρεις λέξεις εδώ τρέχουν",
    "Η γάτα κάθεται πάνω στον καναπέ",
    "Οι φίλοι μου παίζουν ποδόσφαιρο κάθε απόγευμα",
]


def _clean_fixture(tmp_path):
    lines = []
    for i, text in enumerate(CLEAN_TEXTS, start=1):
        lines.append(f"# sent_id = {i}")
        lines.append(f"# text = {text}")
        lines.append("1\tλέξη\tλέξη\t_\t_\t_\t0\troot\t_\t_")
        lines.append("")
    path = tmp_path / "clean.conllu"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_run_eval_forwards_path_to_load_clean_sentences(tmp_path, monkeypatch):
    path = _clean_fixture(tmp_path)
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    stub = StubChecker()
    report = run_eval(n=3, checker=stub, path=path, targeted=False)

    assert stub.batches == [CLEAN_TEXTS]
    assert "3 clean sentences" in report


def _header_report(monkeypatch, **kwargs):
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n, path=None: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
    monkeypatch.setattr(harness, "load_targeted_sentences", lambda path=None, forms=None: [])
    return run_eval(checker=EmptyChecker(), **kwargs)


def test_run_eval_report_header_names_path_corpus(tmp_path, monkeypatch):
    report = _header_report(monkeypatch, path=str(tmp_path / "custom_corpus.conllu"))
    first = report.splitlines()[0]
    assert "custom_corpus.conllu" in first
    assert "UD-GDT" not in first


def test_run_eval_report_header_defaults_to_ud_gdt(monkeypatch):
    report = _header_report(monkeypatch)
    assert "UD-GDT test" in report.splitlines()[0]


def _targeted_header(report):
    return [ln for ln in report.splitlines() if ln.startswith("targeted recall")][0]


def test_run_eval_targeted_section_names_targeted_path(tmp_path, monkeypatch):
    report = _header_report(monkeypatch, targeted_path=str(tmp_path / "alt_pool.conllu"))
    header = _targeted_header(report)
    assert "alt_pool.conllu" in header
    assert "construction pool" not in header


def test_run_eval_targeted_section_defaults_to_construction_pool(monkeypatch):
    report = _header_report(monkeypatch)
    assert "construction pool" in _targeted_header(report)


def _load_sweep456():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "sweep456.py"
    spec = importlib.util.spec_from_file_location("sweep456", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sweep456_main_forwards_args(monkeypatch):
    sweep456 = _load_sweep456()
    recorded = {}

    def recorder(verbose=False, path=None):
        recorded["verbose"] = verbose
        recorded["path"] = path
        return "report"

    monkeypatch.setattr(harness, "run_sweep", recorder)
    result = sweep456.main(["--verbose", "--path", "/tmp/x.conllu"])
    assert result == "report"
    assert recorded == {"verbose": True, "path": "/tmp/x.conllu"}


def test_sweep456_main_defaults(monkeypatch):
    sweep456 = _load_sweep456()
    recorded = {}

    def recorder(verbose=False, path=None):
        recorded["verbose"] = verbose
        recorded["path"] = path
        return "report"

    monkeypatch.setattr(harness, "run_sweep", recorder)
    sweep456.main([])
    assert recorded == {"verbose": False, "path": None}

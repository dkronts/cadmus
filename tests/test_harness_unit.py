"""Model-free, asset-free tests for the 456-sweep loader and report."""

import importlib.util
from pathlib import Path

import pytest

from cadmus.checker import Violation
from cadmus.eval import harness
from cadmus.eval.harness import load_sweep_sentences, run_eval, run_sweep

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
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: None)
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
    monkeypatch.setattr(harness, "load_clean_sentences", lambda n: list(TEXTS))
    monkeypatch.setattr(harness, "corrupt", lambda s, rng: corrupt_map.get(s))
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


def test_run_eval_empty_fp_prints_none(monkeypatch):
    report = _recall_report(monkeypatch, EmptyChecker(), {})
    assert "false positives on clean text:\n  none" in report


def test_run_eval_recall_raises_when_checker_returns_short_results(monkeypatch):
    corrupted = TEXTS[0] + " ληθ"
    with pytest.raises(ValueError, match="checker returned 0 results for 1 inputs"):
        _recall_report(
            monkeypatch,
            ShortResultsChecker(short_from_call=1),
            {TEXTS[0]: (corrupted, "nonword")},
        )


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

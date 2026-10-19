"""Model-free, asset-free tests for the 456-sweep loader and report."""

from cadmus.checker import Violation
from cadmus.eval import harness
from cadmus.eval.harness import load_sweep_sentences, run_sweep

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

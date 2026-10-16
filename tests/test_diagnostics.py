from fakes import FW, FS

from cadmus.diagnostics import coverage, coverage_report


def test_coverage_counts_present_and_missing():
    words = [
        FW(1, "άντρας", "NOUN", "Case=Nom|Gender=Masc|Number=Sing"),
        FW(2, "τρέχει", "VERB", "Number=Sing|Person=3"),  # no Tense
    ]
    present, total = coverage(words)
    assert total[("NOUN", "Gender")] == 1 and present[("NOUN", "Gender")] == 1
    assert total[("VERB", "Tense")] == 1 and present[("VERB", "Tense")] == 0


def test_coverage_report_flags_low_coverage():
    rep = coverage_report([FS([FW(1, "τρέχει", "VERB", "Number=Sing|Person=3")])])
    assert "Tense" in rep and "0.0%" in rep and "low" in rep


def test_coverage_report_empty():
    assert coverage_report([FS([FW(1, "τρέχει", "PUNCT", None)])]) == \
        "no morphologically-typed tokens found"

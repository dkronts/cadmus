from types import SimpleNamespace

from cadmus.stream import iter_checked


def _v(rule, severity):
    return SimpleNamespace(rule=rule, severity=severity)


def _check(text):
    if "bad" in text:
        return [_v("det_noun", "medium"), _v("typography", "low")]
    return []


def test_iter_checked_skips_blank_lines():
    out = list(iter_checked(["ok", "", "   ", "a bad line\n"], _check))
    assert [t for t, _ in out] == ["ok", "a bad line"]


def test_iter_checked_passes_violations_through():
    out = list(iter_checked(["a bad line"], _check))
    assert [v.rule for v in out[0][1]] == ["det_noun", "typography"]


def test_iter_checked_applies_severity_and_rules():
    sev = list(iter_checked(["a bad line"], _check, min_severity="medium"))
    assert [v.rule for v in sev[0][1]] == ["det_noun"]
    rules = list(iter_checked(["a bad line"], _check, rules=["typography"]))
    assert [v.rule for v in rules[0][1]] == ["typography"]

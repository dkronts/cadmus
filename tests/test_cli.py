import errno
import functools
import io
import json

import pytest

import cadmus.cli as cli
from cadmus.checker import Violation


class StubChecker:
    def __init__(self, *args, **kwargs):
        self._damp_stats = {"suppressed": 0, "fired": 0}

    def check(self, text, deep=False):
        return []

    def check_batch(self, texts, batch_size=32):
        self.recorded_batch_size = batch_size
        return [[] for _ in texts]

    def diagnose(self, text):
        return "diagnose report"


@pytest.fixture(autouse=True)
def _stub_checker(monkeypatch):
    monkeypatch.setattr(cli, "CadmusChecker", StubChecker)


def test_batch_rejects_zero_batch_size(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["batch", "--batch-size", "0"])
    assert excinfo.value.code == 2
    assert "must be >= 1" in capsys.readouterr().err


def test_batch_rejects_negative_batch_size(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["batch", "--batch-size", "-1"])
    assert excinfo.value.code == 2
    assert "must be >= 1" in capsys.readouterr().err


def _batch_recorder(monkeypatch, tmp_path):
    recorded = {}

    class RecorderChecker(StubChecker):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            recorded["checker"] = self

    monkeypatch.setattr(cli, "CadmusChecker", RecorderChecker)
    path = tmp_path / "texts.txt"
    path.write_text("first line\nsecond line\n", encoding="utf-8")
    return recorded, str(path)


def test_batch_forwards_valid_batch_size(monkeypatch, tmp_path):
    recorded, path = _batch_recorder(monkeypatch, tmp_path)
    rc = cli.main(["batch", "--batch-size", "8", path])
    assert rc == 0
    assert recorded["checker"].recorded_batch_size == 8


def test_batch_default_batch_size_is_32(monkeypatch, tmp_path):
    recorded, path = _batch_recorder(monkeypatch, tmp_path)
    rc = cli.main(["batch", path])
    assert rc == 0
    assert recorded["checker"].recorded_batch_size == 32


def _violations(text):
    return [
        Violation(sentence=text, rule="det_noun",
                  message="article-noun disagreement", start_char=0, end_char=3),
        Violation(sentence=text, rule="subj_verb",
                  message="subject-verb disagreement", start_char=4, end_char=9,
                  suggestion="use a plural verb"),
    ]


def _violation_batch_recorder(monkeypatch, tmp_path):
    recorded = {}

    class ViolationChecker(StubChecker):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            recorded["checker"] = self

        def check_batch(self, texts, batch_size=32):
            self.recorded_batch_size = batch_size
            self.recorded_texts = list(texts)
            return [_violations(t) if "bad" in t else [] for t in texts]

    monkeypatch.setattr(cli, "CadmusChecker", ViolationChecker)
    path = tmp_path / "texts.txt"
    path.write_text("clean line\nbad line\n", encoding="utf-8")
    return recorded, str(path)


def test_batch_renders_violations(monkeypatch, tmp_path, capsys):
    recorded, path = _violation_batch_recorder(monkeypatch, tmp_path)
    rc = cli.main(["batch", path])
    out = capsys.readouterr().out
    assert rc == 0
    assert recorded["checker"].recorded_texts == ["clean line", "bad line"]
    assert "[det_noun/medium] article-noun disagreement  :: bad line" in out
    assert ("[subj_verb/high] subject-verb disagreement  → use a plural verb"
            "  :: bad line") in out
    assert "clean line" not in out


def test_batch_as_json_emits_violations(monkeypatch, tmp_path, capsys):
    _, path = _violation_batch_recorder(monkeypatch, tmp_path)
    rc = cli.main(["batch", "--json", path])
    assert rc == 0
    objects = [json.loads(ln) for ln in capsys.readouterr().out.splitlines()]
    assert [obj["text"] for obj in objects] == ["clean line", "bad line"]
    assert objects[0]["violations"] == []
    assert {"text", "violations"} <= set(objects[1])
    violation = objects[1]["violations"][0]
    assert {"rule", "severity", "message", "suggestion",
            "start_char", "end_char"} <= set(violation)
    assert violation["rule"] == "det_noun"
    assert violation["severity"] == "medium"
    assert violation["message"] == "article-noun disagreement"
    assert violation["suggestion"] == ""
    assert violation["start_char"] == 0
    assert violation["end_char"] == 3


def test_batch_severity_filter(monkeypatch, tmp_path, capsys):
    _, path = _violation_batch_recorder(monkeypatch, tmp_path)
    rc = cli.main(["batch", "--severity", "high", path])
    out = capsys.readouterr().out
    assert rc == 0
    assert "det_noun" not in out
    assert "[subj_verb/high] subject-verb disagreement" in out


def test_batch_rules_filter(monkeypatch, tmp_path, capsys):
    _, path = _violation_batch_recorder(monkeypatch, tmp_path)
    rc = cli.main(["batch", "--rules", "det_noun", path])
    out = capsys.readouterr().out
    assert rc == 0
    assert "[det_noun/medium] article-noun disagreement" in out
    assert "subj_verb" not in out


def test_eval_forwards_flags(monkeypatch, tmp_path, capsys):
    recorded = {}

    def recorder(**kwargs):
        recorded.update(kwargs)
        return "report"

    monkeypatch.setattr("cadmus.eval.harness.run_eval", recorder)
    path = str(tmp_path / "t.conllu")
    rc = cli.main(["eval", "--n", "5", "--seed", "7", "-v", "--no-targeted",
                   "--targeted-path", path])
    assert rc == 0
    assert recorded["n"] == 5
    assert recorded["seed"] == 7
    assert recorded["verbose"] is True
    assert recorded["targeted"] is False
    assert recorded["targeted_path"] == path
    assert "report" in capsys.readouterr().out


def test_eval_forwards_path(monkeypatch, tmp_path, capsys):
    recorded = {}

    def recorder(**kwargs):
        recorded.update(kwargs)
        return "report"

    monkeypatch.setattr("cadmus.eval.harness.run_eval", recorder)
    path = str(tmp_path / "t.conllu")
    rc = cli.main(["eval", "--path", path])
    assert rc == 0
    assert recorded["path"] == path
    assert "report" in capsys.readouterr().out


def test_eval_missing_path_reports_clean_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("cadmus.eval.harness.CadmusChecker", StubChecker)
    rc = cli.main(["eval", "--path", str(tmp_path / "nope.conllu")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "cadmus: error:" in captured.err
    assert "Traceback" not in captured.err


def test_eval_missing_targeted_path_reports_clean_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("cadmus.eval.harness.CadmusChecker", StubChecker)
    monkeypatch.setattr(
        "cadmus.eval.harness.load_clean_sentences",
        lambda limit, path=None: ["Ο σκύλος τρέχει γρήγορα στο πάρκο"],
    )
    rc = cli.main(["eval", "--targeted-path", str(tmp_path / "nope.conllu")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "cadmus: error:" in captured.err
    assert "Traceback" not in captured.err


def test_eval_no_targeted_ignores_missing_targeted_path(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("cadmus.eval.harness.CadmusChecker", StubChecker)
    monkeypatch.setattr(
        "cadmus.eval.harness.load_clean_sentences",
        lambda limit, path=None: ["Ο σκύλος τρέχει γρήγορα στο πάρκο"],
    )
    rc = cli.main(["eval", "--no-targeted",
                   "--targeted-path", str(tmp_path / "nope.conllu")])
    captured = capsys.readouterr()
    assert rc == 0
    assert "cadmus: error:" not in captured.err
    assert "Traceback" not in captured.err


def _open_recorder(monkeypatch):
    opened = []
    real_open = open

    @functools.wraps(open)
    def recording_open(*args, **kwargs):
        handle = real_open(*args, **kwargs)
        opened.append(handle)
        return handle

    monkeypatch.setattr("builtins.open", recording_open)
    return opened


@pytest.mark.parametrize("cmd", ["batch", "watch", "diagnose", "check"])
def test_path_file_handles_are_closed(monkeypatch, tmp_path, cmd):
    opened = _open_recorder(monkeypatch)
    path = tmp_path / "texts.txt"
    path.write_text("clean line\n", encoding="utf-8")
    rc = cli.main([cmd, str(path)])
    assert rc == 0
    assert opened
    assert all(handle.closed for handle in opened)


@pytest.mark.parametrize("cmd", ["batch", "watch", "diagnose", "check"])
def test_stdin_is_not_closed(monkeypatch, capsys, cmd):
    stdin = io.StringIO("clean line\n")
    monkeypatch.setattr(cli.sys, "stdin", stdin)
    rc = cli.main([cmd])
    assert rc == 0
    assert not stdin.closed


@pytest.mark.parametrize("cmd", ["batch", "watch", "diagnose", "check"])
def test_missing_input_file_reports_clean_error(tmp_path, capsys, cmd):
    missing = str(tmp_path / "nope.txt")
    rc = cli.main([cmd, missing])
    captured = capsys.readouterr()
    assert rc == 2
    assert "cadmus: error:" in captured.err
    assert "no such file:" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("cmd", ["batch", "watch", "diagnose", "check"])
def test_directory_input_reports_clean_error(tmp_path, capsys, cmd):
    directory = tmp_path / "adir"
    directory.mkdir()
    rc = cli.main([cmd, str(directory)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "cadmus: error:" in captured.err
    assert "is a directory:" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("cmd", ["batch", "watch", "diagnose", "check"])
def test_non_utf8_input_reports_clean_error(tmp_path, capsys, cmd):
    path = tmp_path / "bad.txt"
    path.write_bytes(b"clean\n\xff\xfe\x00garbage\n")
    rc = cli.main([cmd, str(path)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "cadmus: error:" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("cmd", ["batch", "watch", "diagnose", "check"])
def test_read_error_reports_clean_error(monkeypatch, tmp_path, capsys, cmd):
    path = tmp_path / "texts.txt"
    path.write_text("clean line\n", encoding="utf-8")
    real_open = open

    def failing_open(*args, **kwargs):
        handle = real_open(*args, **kwargs)

        def fail_read(*a, **k):
            raise OSError(errno.EIO, "Input/output error")

        monkeypatch.setattr(handle, "read", fail_read)
        return handle

    monkeypatch.setattr("builtins.open", failing_open)
    rc = cli.main([cmd, str(path)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "cadmus: error:" in captured.err
    assert str(path) in captured.err
    assert "Traceback" not in captured.err

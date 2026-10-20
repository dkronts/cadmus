import pytest

import cadmus.cli as cli


class StubChecker:
    def __init__(self, *args, **kwargs):
        pass

    def check_batch(self, texts, batch_size=32):
        self.recorded_batch_size = batch_size
        return [[] for _ in texts]


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

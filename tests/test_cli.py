import pytest

import cadmus.cli as cli


class StubChecker:
    def __init__(self, *args, **kwargs):
        pass


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

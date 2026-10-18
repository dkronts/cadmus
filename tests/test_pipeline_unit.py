"""Model-free tests for the pipeline loader's lemma-workaround retry."""

import sys
import types

from cadmus import pipeline


class _FakeStanza:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def Pipeline(self, *a, **kw):
        self.calls += 1
        if self.calls <= self.failures:
            raise FileNotFoundError(
                "Pretrained file /nlp/scr/horatio/stanza_resources/el/"
                "pretrain/conll17.pt does not exist")
        return "pipeline-ok"


def test_first_build_failure_retries_after_download(monkeypatch):
    fake = _FakeStanza(failures=1)
    monkeypatch.setitem(sys.modules, "stanza", types.SimpleNamespace(Pipeline=fake.Pipeline))
    workaround_calls = []
    monkeypatch.setattr(pipeline, "_try_apply_lemma_workaround",
                        lambda: workaround_calls.append(1))
    assert pipeline.load_pipeline() == "pipeline-ok"
    assert fake.calls == 2
    assert len(workaround_calls) == 2  # retried after the download


def test_persistent_failure_raises_friendly_error(monkeypatch):
    fake = _FakeStanza(failures=99)
    monkeypatch.setitem(sys.modules, "stanza", types.SimpleNamespace(Pipeline=fake.Pipeline))
    monkeypatch.setattr(pipeline, "_try_apply_lemma_workaround", lambda: None)
    try:
        pipeline.load_pipeline()
    except RuntimeError as e:
        assert "fix_stanza_lemma" in str(e)
    else:
        raise AssertionError("expected RuntimeError")


def test_unrelated_failure_propagates(monkeypatch):
    def _boom(*a, **kw):
        raise FileNotFoundError("some other missing file")

    monkeypatch.setitem(sys.modules, "stanza", types.SimpleNamespace(Pipeline=_boom))
    monkeypatch.setattr(pipeline, "_try_apply_lemma_workaround", lambda: None)
    try:
        pipeline.load_pipeline()
    except FileNotFoundError as e:
        assert "some other" in str(e)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_sudo_fallback_creates_parent_dirs(monkeypatch, tmp_path):
    cache = tmp_path / ".cache" / "stanza" / "resources" / "el" / "pretrain"
    cache.mkdir(parents=True)
    (cache / "conll17.pt").write_bytes(b"x")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(pipeline.os, "symlink",
                        lambda *a, **kw: (_ for _ in ()).throw(PermissionError("denied")))
    monkeypatch.setattr(pipeline.os.path, "exists", lambda p: False)
    import types as _t
    monkeypatch.setitem(sys.modules, "stanza", _t.SimpleNamespace())
    calls = []
    monkeypatch.setattr(pipeline.subprocess, "run",
                        lambda cmd, check: calls.append(cmd))
    pipeline._try_apply_lemma_workaround()
    assert calls and calls[0][0:2] == ["sudo", "-n"]
    joined = " ".join(calls[0])
    assert "mkdir -p" in joined and "ln -sf" in joined

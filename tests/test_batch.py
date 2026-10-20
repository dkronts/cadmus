import pytest

from cadmus.checker import CadmusChecker
from fakes import FakeDoc, FakeNLP, FakeNLPProcessMany


class ShortPipeNLP(FakeNLP):
    """pipe() yields one fewer doc than the input, as a truncating pipeline would."""

    def pipe(self, texts):
        self.pipe_calls += 1
        return [FakeDoc(t) for t in texts][:-1]


class ShortLastChunkNLP(FakeNLP):
    """pipe() drops the last doc only for single-text chunks (the final chunk)."""

    def pipe(self, texts):
        self.pipe_calls += 1
        docs = [FakeDoc(t) for t in texts]
        return docs[:-1] if len(texts) == 1 else docs


class LongPipeNLP(FakeNLP):
    """pipe() yields one extra doc (a duplicate of the last), as an over-producing pipeline would."""

    def pipe(self, texts):
        self.pipe_calls += 1
        docs = [FakeDoc(t) for t in texts]
        return docs + docs[-1:]


class LongSecondChunkNLP(FakeNLP):
    """pipe() duplicates the last doc only on the second pipe() call."""

    def pipe(self, texts):
        self.pipe_calls += 1
        docs = [FakeDoc(t) for t in texts]
        return docs + docs[-1:] if self.pipe_calls == 2 else docs


def _checker():
    nlp = FakeNLP()
    return CadmusChecker(nlp=nlp, use_lexicon=False), nlp


def test_check_batch_returns_one_list_per_text_in_order():
    checker, _ = _checker()
    texts = ["Αυτό είναι σωστό.", "Δεν πειράζει.", "Τρίτη μέρα."]
    out = checker.check_batch(texts)
    assert isinstance(out, list) and len(out) == len(texts)
    assert all(isinstance(v, list) for v in out)


def test_check_batch_uses_pipe_not_per_text_call():
    checker, nlp = _checker()
    checker.check_batch(["Ένα.", "Δύο.", "Τρία."])
    assert nlp.pipe_calls == 1
    assert nlp.call_count == 0


def test_check_batch_chunks_by_batch_size():
    checker, nlp = _checker()
    checker.check_batch(["α.", "β.", "γ.", "δ.", "ε."], batch_size=2)
    assert nlp.pipe_calls == 3  # ceil(5 / 2)


def test_check_batch_surfaces_typography_without_a_model():
    checker, _ = _checker()
    out = checker.check_batch(["Αυτό είναι σωστό ?", "Καθαρή πρόταση."])
    assert any(v.rule == "typography" for v in out[0])
    assert out[1] == []


def test_check_batch_falls_back_to_process_many():
    nlp = FakeNLPProcessMany()
    checker = CadmusChecker(nlp=nlp, use_lexicon=False)
    out = checker.check_batch(["Ένα.", "Δύο.", "Τρία.", "Τέσσερα."], batch_size=3)
    assert len(out) == 4
    assert nlp.process_many_calls == 2  # ceil(4 / 3)
    assert nlp.call_count == 0


def test_check_batch_raises_when_pipeline_returns_too_few_docs():
    checker = CadmusChecker(nlp=ShortPipeNLP(), use_lexicon=False)
    with pytest.raises(ValueError, match="chunk 0"):
        checker.check_batch(["Ένα.", "Δύο.", "Τρία."])


def test_check_batch_error_names_the_truncating_chunk():
    checker = CadmusChecker(nlp=ShortPipeNLP(), use_lexicon=False)
    with pytest.raises(ValueError, match="chunk 0"):
        checker.check_batch(["α.", "β.", "γ.", "δ.", "ε."], batch_size=2)


def test_check_batch_error_names_a_later_truncating_chunk():
    checker = CadmusChecker(nlp=ShortLastChunkNLP(), use_lexicon=False)
    with pytest.raises(ValueError, match=r"chunk 2 \(texts 4\.\.4\) of 5 texts"):
        checker.check_batch(["α.", "β.", "γ.", "δ.", "ε."], batch_size=2)


def test_check_batch_raises_when_pipeline_returns_too_many_docs():
    checker = CadmusChecker(nlp=LongPipeNLP(), use_lexicon=False)
    with pytest.raises(ValueError, match="more than 3 results for chunk 0"):
        checker.check_batch(["Ένα.", "Δύο.", "Τρία."])


def test_check_batch_error_names_the_over_producing_chunk():
    checker = CadmusChecker(nlp=LongSecondChunkNLP(), use_lexicon=False)
    with pytest.raises(ValueError, match=r"chunk 1 \(texts 2\.\.3\) of 4 texts"):
        checker.check_batch(["α.", "β.", "γ.", "δ."], batch_size=2)


def test_check_batch_rejects_zero_batch_size():
    checker, _ = _checker()
    with pytest.raises(ValueError, match="batch_size must be >= 1") as excinfo:
        checker.check_batch(["Ένα.", "Δύο."], batch_size=0)
    assert "must not be zero" not in str(excinfo.value)


def test_check_batch_rejects_negative_batch_size():
    checker, _ = _checker()
    with pytest.raises(ValueError, match="batch_size must be >= 1") as excinfo:
        checker.check_batch(["Ένα.", "Δύο."], batch_size=-3)
    assert "must not be zero" not in str(excinfo.value)


def test_check_batch_rejects_float_batch_size():
    checker, _ = _checker()
    with pytest.raises(TypeError, match="cannot be interpreted"):
        checker.check_batch(["Ένα.", "Δύο."], batch_size=2.5)


def test_check_batch_rejects_string_batch_size():
    checker, _ = _checker()
    with pytest.raises(TypeError, match="cannot be interpreted"):
        checker.check_batch(["Ένα.", "Δύο."], batch_size="4")


def test_check_batch_accepts_bool_true_as_one():
    checker, nlp = _checker()
    out = checker.check_batch(["Ένα.", "Δύο.", "Τρία."], batch_size=True)
    assert len(out) == 3
    assert nlp.pipe_calls == 3
    assert nlp.call_count == 0

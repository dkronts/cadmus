"""Regression ratchet over the round-trip LLM-Greek pilot corpora.

tests/data/llm_greek_pilot.v1.jsonl    — 100 pairs, Qwen3-8B q4 (llama.cpp)
tests/data/llm_greek_pilot35b.v1.jsonl — 200 pairs, Qwen3 MoE 35B q5 (Ollama,
                                          same seed, so the first 100 EN
                                          sources are identical to v1)

EN sides come from the OPUS GlobalVoices bitext and were machine-translated
to Greek by the local model; flags were hand-judged true/false against the
human reference. This test keeps improvements from regressing:

- recall ratchet: every flag judged TRUE must still fire
- precision ratchet: no flag may appear that is not in the judged-false or
  known-reference lists (new FPs fail loudly; when a rule improves, shrink
  the lists in the fixture deliberately)

Needs stanza (full suite only, not the model-free CI subset).
"""

import json
from pathlib import Path

import pytest

from cadmus import CadmusChecker

DATA = Path(__file__).parent / "data"
FIXTURES = [
    (DATA / "llm_greek_pilot.v1.jsonl", 9, 32),
    (DATA / "llm_greek_pilot35b.v1.jsonl", 33, 80),
]


def _rows(fixture):
    with open(fixture, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh]


@pytest.mark.parametrize("fixture,n_true,n_false", FIXTURES)
def test_true_flags_still_fire(fixture, n_true, n_false):
    checker = CadmusChecker()
    for row in _rows(fixture):
        fired = {(v.rule, v.message) for v in checker.check(row["llm_el"])}
        for verdict in row["llm_verdicts"]:
            if verdict["verdict"] != "true" or verdict.get("waived"):
                continue
            assert (verdict["rule"], verdict["message"]) in fired, (
                f"#{row['id']} lost a true detection: {verdict['rule']}: "
                f"{verdict['message']} in: {row['llm_el'][:80]}")


@pytest.mark.parametrize("fixture,n_true,n_false", FIXTURES)
def test_no_new_flags_beyond_judged_lists(fixture, n_true, n_false):
    checker = CadmusChecker()
    for row in _rows(fixture):
        allowed = {(v["rule"], v["message"]) for v in row["llm_verdicts"]}
        for v in checker.check(row["llm_el"]):
            assert (v.rule, v.message) in allowed, (
                f"#{row['id']} new flag on LLM Greek: {v.rule}: {v.message} "
                f"in: {row['llm_el'][:80]}")


@pytest.mark.parametrize("fixture,n_true,n_false", FIXTURES)
def test_no_new_flags_on_human_reference(fixture, n_true, n_false):
    checker = CadmusChecker()
    for row in _rows(fixture):
        known = {(v["rule"], v["message"]) for v in row["ref_known"]}
        for v in checker.check(row["ref_el"]):
            assert (v.rule, v.message) in known, (
                f"#{row['id']} new flag on human Greek: {v.rule}: {v.message} "
                f"in: {row['ref_el'][:80]}")


@pytest.mark.parametrize("fixture,n_true,n_false", FIXTURES)
def test_fixture_counts(fixture, n_true, n_false):
    rows = _rows(fixture)
    verdicts = [v for r in rows for v in r["llm_verdicts"]]
    assert len(rows) in (100, 200)
    assert sum(1 for v in verdicts if v["verdict"] == "true") == n_true
    assert sum(1 for v in verdicts if v["verdict"] == "false") == n_false
    assert all(v["verdict"] in ("true", "false") for v in verdicts)

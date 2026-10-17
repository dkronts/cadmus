"""Regression ratchet over the round-trip LLM-Greek pilot corpus.

tests/data/llm_greek_pilot.v1.jsonl holds 100 GlobalVoices EN-EL pairs whose
EN side was machine-translated to Greek by a local Qwen3-8B (q4) and whose
flags were hand-judged true/false against the human reference. This test
keeps improvements from regressing:

- recall ratchet: every flag judged TRUE must still fire
- precision ratchet: no flag may appear that is not in the judged-false or
  known-reference lists (new FPs fail loudly; when a rule improves, shrink
  the lists in the fixture deliberately)

Needs stanza (full suite only, not the model-free CI subset).
"""

import json
from pathlib import Path

from cadmus import CadmusChecker

FIXTURE = Path(__file__).parent / "data" / "llm_greek_pilot.v1.jsonl"


def _rows():
    with open(FIXTURE, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh]


def test_true_flags_still_fire():
    checker = CadmusChecker()
    for row in _rows():
        fired = {(v.rule, v.message) for v in checker.check(row["llm_el"])}
        for verdict in row["llm_verdicts"]:
            if verdict["verdict"] != "true":
                continue
            assert (verdict["rule"], verdict["message"]) in fired, (
                f"#{row['id']} lost a true detection: {verdict['rule']}: "
                f"{verdict['message']} in: {row['llm_el'][:80]}")


def test_no_new_flags_beyond_judged_lists():
    checker = CadmusChecker()
    for row in _rows():
        allowed = {(v["rule"], v["message"]) for v in row["llm_verdicts"]}
        for v in checker.check(row["llm_el"]):
            assert (v.rule, v.message) in allowed, (
                f"#{row['id']} new flag on LLM Greek: {v.rule}: {v.message} "
                f"in: {v.llm_el if hasattr(v, 'llm_el') else row['llm_el'][:80]}")


def test_no_new_flags_on_human_reference():
    checker = CadmusChecker()
    for row in _rows():
        known = {(v["rule"], v["message"]) for v in row["ref_known"]}
        for v in checker.check(row["ref_el"]):
            assert (v.rule, v.message) in known, (
                f"#{row['id']} new flag on human Greek: {v.rule}: {v.message} "
                f"in: {row['ref_el'][:80]}")


def test_fixture_counts():
    rows = _rows()
    verdicts = [v for r in rows for v in r["llm_verdicts"]]
    assert len(rows) == 100
    assert sum(1 for v in verdicts if v["verdict"] == "true") == 9
    assert sum(1 for v in verdicts if v["verdict"] == "false") == 32
    assert all(v["verdict"] in ("true", "false") for v in verdicts)

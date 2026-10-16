# Cadmus — agent working agreement

Greek grammar/syntax **detection** layer. Detection-first, precision-first.
The state of the world lives in `TODOs.md` (roadmap + evidence log) and
`README.md` (public claims). Every claim in the README must be backed by a
measurement in the repo.

## Hard invariants (never violate)

1. **0-FP correctness tier.** A rule ships only with **zero false positives on
   clean text, measured end-to-end through the analyzer** (stanza), not against
   gold trees.
2. **Measure before build.** A documented rejection with data is a first-class
   outcome (see the `REJECTED` entries in `TODOs.md`).
3. **`main` stays green.** Model-free CI subset + full local suite + `cadmus
   eval` must pass before every push.
4. **Detection only.** Never auto-rewrite user text; suggestions are advisory
   strings.
5. **Attribution.** Commit only as `dkronts
   <211030943+dkronts@users.noreply.github.com>`. Never mention the
   maintainer's personal identity, real name, or academic history in any repo
   artifact, commit message, doc, or issue.
6. **Refinement bound.** At most **2** guard/refinement attempts on a failing
   rule, then reject it with the measured evidence.

## Environment facts (verified 2026-10)

- stanza 1.15.0, CPU torch. `Pipeline` has `process_many`, **not** `pipe`.
- Data assets auto-build under `~/.cache/cadmus` from public UD-GDT + Greek
  Wikipedia title dumps (train/test conllu, `verbforms.v1.json`,
  `frames.v1.json`, `propn.v1.json`).
- **Analyzer repairs**: copula-predicate `Case`; `Tense` after `να` is
  unreliable; numeral `Gender` is repaired to match its noun. For these, decide
  from **surface forms** (pattern: `copula_pred`, `na_form`, `num_noun` in
  `src/cadmus/rules/`).
- Eval pool: 148 clean eval sentences (4–15 tokens); full clean test set = 456
  (`grep -c '# text =' ~/.cache/cadmus/el_gdt-ud-test.conllu`).
- Python env: use an interpreter with cadmus installed (`python -c "import
  stanza, spylls"`); a prepared venv may exist under `/tmp/opencode` (`ls -d
  /tmp/opencode/*/venv`). Otherwise `python -m venv .venv &&
  .venv/bin/pip install -e ".[dev]"`.
- Perf baselines (**re-measure, don't trust**): model load ~5 s; single
  ~35 ms/sentence; batch ~19 sentences/s.

## The loop — one shippable increment per run

```
RECON → SELECT → GATE → IMPLEMENT → VERIFY → SHIP → RECORD → (next | stop)
```

1. **RECON**: read `TODOs.md` + recent `git log`; run `cadmus eval --verbose`
   (MISS lines + FP samples); run `cadmus diagnose`; diff README claims vs
   tests.
2. **SELECT**: highest value-per-effort item from the backlog below; skip
   blocked items.
3. **GATE** (rules only): prototype over the 456-sentence clean sweep through
   the analyzer + targeted error probes. `0 FP` + recall > 0 → implement.
   FP → ≤2 guards → else reject. No signal → reject.
4. **IMPLEMENT**: rule + model-free unit tests (`tests/fakes.py`) + integration
   tests (`tests/test_checker.py`) + README + `TODOs.md` entry + version bump
   (`pyproject.toml` + `src/cadmus/__init__.py`).
5. **VERIFY**: full `pytest` locally; model-free CI subset; eval shows no new
   FP; if a hot path changed, re-run the perf benchmark and keep batch ≥ 17
   sentences/s.
6. **SHIP**: commit as dkronts, push, confirm the CI job is green.
7. **RECORD**: `TODOs.md` Done/REJECTED entry with the numbers; README measured
   table only if eval numbers changed.

## Backlog priority (current order — keep synced with `TODOs.md`)

1. Push-gate the integration suite in CI (cache stanza model + pip deps) and
   add coverage reporting (no hard threshold yet).
2. Correction suggestions for high-recall rules (extend beyond `det_noun` /
   `num_noun` / `copula_pred`: `propn_accent`, `rel_agreement`, spelling
   suggestion ranking).
3. Server/API layer for warm-model reuse — **ASK USER** for scope first.
4. Style tier (quote style, final -ν, adjective position, proper-noun casing as
   advisory, off by default) — **ASK USER** first (product decision).
5. Blocked on external resources: LLM judge (model download), error corpus
   (annotation), LanguageTool baseline (JRE + download). **Never download
   these autonomously.**

## Decision matrix

**Autonomous — just do it**: backlog ordering; measurement verdicts (the 0-FP
gate is objective); guard refinements (≤2); tests/docs/version chores; push to
`main` after green CI.

**ASK USER (interrupt)**: new heavy dependencies or any multi-GB / JRE
download; publishing to PyPI, tags, releases, or any publicity; breaking
public API changes; style-tier scope; anything spending money.

**STOP and report**: roadmap exhausted (all items shipped/rejected/blocked);
CI red twice on the same change; environment broken (no stanza, no assets, no
network to GitHub); any invariant conflict.

**Definition of done for a run**: either a green-pushed increment, or a
documented rejection in `TODOs.md`, or a stop-report. Never leave `main` red
or claims unmeasured.

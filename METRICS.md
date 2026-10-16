# Cadmus — metrics log

Progress + error-distribution ledger for the loop (see `AGENTS.md`).
Append one run-log entry per shipped increment; keep the distributions
current so SELECT stays data-driven. Numbers are measurements, not claims —
re-measure, don't trust.

## Current baseline (v0.0.14, 2026-10-16)

- Rules: 12 shipped — `det_noun`, `adj_noun`, `subj_verb`, `rel_agreement`,
  `copula_pred`, `na_form`, `num_noun`, `prep_case`, `spelling`,
  `verb_valence`, `negation`, `propn_accent` — plus text-level `typography`.
- Tests: 78 collected (59 model-free in the CI subset), all green.
- Eval (UD-GDT clean test, fixed seed): recall — accents 95%, script-mix 96%,
  non-words 88%, proper-noun accent 62%, wrong article 68%, δεν/μην 100%,
  typography 100%. `rel_agreement`, `copula_pred`, `na_form`, `num_noun` have
  no corruption-pool samples — validated by targeted probes only.
- Precision: ~7 FP / 100 clean sentences. 0-FP rules: `typography`,
  `propn_accent`, `rel_agreement`, `copula_pred`, `na_form`, `num_noun`.
- Perf (CPU): model load ~5.4 s; single ~35 ms/sentence; batch ~19.4 sent/s.

## Error distribution (FP by rule, latest ~100-clean sweep — approximate)

| Rule | FP / 100 clean | Dominant cause |
|---|---|---|
| spelling | ~5 | rare words / PROPNs outside the dictionaries |
| det_noun | ~4 | stanza re-parse on corrupted input; rare-noun gender |
| adj_noun | ~1 | genitive modifier misattachment |
| subj_verb | ~1 | coordination parse artifacts |

## Recall by injected error type (latest sweep)

| Error type | Recall | Notes |
|---|---|---|
| negation (δεν/μην) | 100% | |
| typography | 100% | text-level |
| script_mix | 96% | |
| accent | 95% | |
| nonword | 88% | PROPN misses dominate |
| propn_accent | 62% | inflected/foreign names silent by design |
| det_noun (article swap) | 68% | stanza "repairs" the corrupted article |
| rel_agreement / copula_pred / na_form / num_noun | n/a | no pool samples; targeted probes |

## Surfaced gaps (open — mirrored in TODOs.md)

- rare nouns absent from UD train still FP-prone via the tagger
- det corruption misses when stanza re-parses structure (attach changes)
- no `Mood=Sub` in Greek stanza — mood rules need positional context
- `na_form` / `verb_valence` recall bounded by treebank coverage
- relcl rules have no corruption-pool samples (need a longer-sentence pool)

## Run log

One row per increment: version, date, what shipped, tests, recall/FP delta,
perf if re-measured.

| Version | Date | Increment | Tests | Recall Δ | FP Δ | Perf |
|---|---|---|---|---|---|---|
| v0.0.14 | 2026-10 | `num_noun` (surface-form numeral gender) | 78 | targeted probes only | 0 | — |

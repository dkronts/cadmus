# Cadmus — metrics log

Progress + error-distribution ledger for the loop (see `AGENTS.md`).
Append one run-log entry per shipped increment; keep the distributions
current so SELECT stays data-driven. Numbers are measurements, not claims —
re-measure, don't trust.

## Current baseline (v0.0.15, 2026-10-16)

- Rules: 12 shipped — `det_noun`, `adj_noun`, `subj_verb`, `rel_agreement`,
  `copula_pred`, `na_form`, `num_noun`, `prep_case`, `spelling`,
  `verb_valence`, `negation`, `propn_accent` — plus text-level `typography`.
- Tests: 89 collected (67 model-free in the CI subset), all green.
- Eval (UD-GDT clean test, fixed seed): recall — accents 95%, script-mix 96%,
  non-words 88%, proper-noun accent 62%, wrong article 68%, δεν/μην 100%,
  typography 100%. `rel_agreement`, `copula_pred`, `na_form`, `num_noun` have
  no corruption-pool samples — validated by targeted probes only.
- Precision: ~7 FP / 100 clean sentences (eval pool). Full 456-sentence clean
  sweep: `spelling` 22 FP (was 77 pre-v0.0.15); other rules unchanged
  (`prep_case` 26, `det_noun` 23, `verb_valence` 11, `adj_noun` 9,
  `rel_agreement` 9, `typography` 5, `subj_verb` 5, `propn_accent` 1).
  0-FP rules on the pool: `typography`, `propn_accent`, `rel_agreement`,
  `copula_pred`, `na_form`, `num_noun`.
- Perf (CPU): model load ~5.4 s; single ~35 ms/sentence; batch ~19.4 sent/s.

## Error distribution (FP by rule, latest ~100-clean sweep — approximate)

| Rule | FP / 100 clean | Dominant cause |
|---|---|---|
| spelling | ~5 pool / 22 per 456 full (was 77) | residue: source typos + script-mix homoglyphs + words in no repo resource (see v0.0.15 REJECTED) |
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

- rare nouns absent from UD train still FP-prone via the tagger (det_noun
  residue 19/456: unseen-form Gender noise + dual-usage nouns like
  «Υπουργός» — form-level Gender gating measured and REJECTED: pool recall
  58→38%; a tagger-quality ceiling)
- prep_case residue is 1/456 (από + παραλίες tagged Nom); the dormant
  `nominal_cases` resource is now active as the unseen-head guard
- gender-coverage extensions must derive from the persisted `entries` at
  resolve time (`nominal_cases`/`form_feats` precedents shipped);
  `build()`-filter changes are inert against the cached `lexicon.v2.json`
  because `load()` short-circuits to it
- `PropnLexicon.forms` holds ~5.5k unaccented title variants (`απο`, `βορεια`)
  — unsafe as a known-word set for unaccented tokens (accent recall 87→60%
  when trusted; v0.0.15 restricts PROPN coverage to accented tokens)
- spelling residue on the full clean set (22 FP) is correct detection of
  imperfect source text — the 0-FP gate is unreachable without gutting the rule
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
| v0.0.15 | 2026-10 | spelling: env-lexicon coverage suppression (accented-only PROPN) + abbreviation/elision guards | 89 | unchanged (accent 87%, nonword 96%, script-mix 95%, propn_accent 78%) | spelling 77→22 per 456 clean; other rules unchanged | — |
| v0.0.16 | 2026-10 | typography-first normalization: analysis shadow + offset mapper | 101 | identical (accent 87%, nonword 96%, script-mix 95%, propn_accent 78%, det 58%, negation/typography 100%) | identical per-rule FP on 456 clean | 34 sent/s batch |
| v0.0.17 | 2026-10 | det_noun: form_feats Case/Number attestation gate | 106 | identical (det 58%) | det_noun 23→19 per 456 clean (Gender-gating rejected: 58→38 recall) | — |
| v0.0.18 | 2026-10 | prep_case: measured GEN_PREPS extension + Dat/PRON/unseen-head guards, nominal_cases activated | 116 | identical; new Acc-detection for the added Gen-preps (probes) | prep_case 26→1 per 456 clean | — |
| v0.0.19 | 2026-10 | selective two-pass suggestion confirmation (`--deep`, `Violation.confirmed`) | 118 | identical (deep is opt-in; default path unchanged) | identical | default path 34 sent/s batch (v0.0.16) |

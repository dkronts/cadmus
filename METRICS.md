# Cadmus — metrics log

Progress + error-distribution ledger for the development loop.
Append one run-log entry per shipped increment; keep the distributions
current so SELECT stays data-driven. Numbers are measurements, not claims —
re-measure, don't trust.

## Current baseline (v0.0.15, 2026-10-16)

- Rules: 12 shipped — `det_noun`, `adj_noun`, `subj_verb`, `rel_agreement`,
  `copula_pred`, `na_form`, `num_noun`, `prep_case`, `spelling`,
  `verb_valence`, `negation`, `propn_accent` — plus text-level `typography`.
- Tests: 177 collected (120 model-free in the CI subset), all green.
- Eval (UD-GDT clean test, fixed seed): recall — accents 95%, script-mix 96%,
  non-words 88%, proper-noun accent 62%, wrong article 68%, δεν/μην 100%,
  typography 100%. `copula_pred`, `na_form` have no corruption-pool samples —
  validated by targeted probes only. `rel_agreement`/`num_noun` are now
  measurable via the construction-targeted recall pool (v0.0.25: 23 UD-GDT
  sentences → 17 rel + 6 num corruptions); recall numbers pending a model run.
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
| rel_agreement / num_noun | pending | construction-targeted pool (17/6 corruptions); awaiting model run |
| copula_pred / na_form | n/a | no pool samples; targeted probes |

Note on the targeted-recall pool (intended overlap, not double-counting):
`load_targeted_sentences` skips only the 4-15 token length filter, so the
targeted pool is a superset lens over the same corpus — a short (4-15 token)
target-bearing sentence legitimately appears in both the random recall pool
and the targeted pool, and is touched by both corruptors in one `run_eval`.
Each pass answers a different question (FP on clean text, random-corruption
recall, construction-targeted recall); do not treat the overlap as a bug.

## Surfaced gaps (open — mirrored in TODOs.md)

- det_noun residue 13/456 (was 19) after the v0.0.26 dual-gender article
  Gender gate; the rest is a measured tagger-quality ceiling (unconditional
  Gender gating costs pool recall 58→38%, suspect-gated disjoint-evidence
  is inert 19→19)
- spelling residue 22/456 is correct detection of imperfect source text
  (documented REJECTED v0.0.15)
- prep_case/verb_valence/rel_agreement residues (1/1/2) documented as
  attachment/sparsity ceilings
- verb-prep government, determiner omission, stutter detection: REJECTED
  after pilot RECON (zero true signal — see TODOs 2026-10-18); stutter and
  article omission become candidates again only with an STT corpus

- rare nouns absent from UD train still FP-prone via the tagger (det_noun
  residue 13/456 after the v0.0.26 dual-gender article gate: unseen-form
  Gender noise + dual-usage nouns like
  «Υπουργός» — form-level Gender gating measured and REJECTED twice:
  unconditional gate costs pool recall 58→38% (v0.0.17); suspect-head
  disjoint-evidence gate measured inert (19→19 FP, recall 58% held — all
  18 clean-sweep Gender mismatches have non-suspect heads); a
  tagger-quality ceiling. `FormLexicon.form_gender` kept dormant+tested
  (nominal_cases precedent) for any future consumer)
- prep_case residue is 1/456 (από + παραλίες tagged Nom); the dormant
  `nominal_cases` resource is now active as the unseen-head guard
- gender-coverage extensions must derive from the persisted `entries` at
  resolve time (`nominal_cases`/`form_feats` precedents shipped);
  `build()`-filter changes are inert against a stale cache because `load()`
  short-circuits to it — v0.0.26 shipped the filename-bump path
  (`lexicon.v3.json` + `det_gender_sets`)
- `PropnLexicon.forms` holds ~5.5k unaccented title variants (`απο`, `βορεια`)
  — unsafe as a known-word set for unaccented tokens (accent recall 87→60%
  when trusted; v0.0.15 restricts PROPN coverage to accented tokens)
- spelling residue on the full clean set (22 FP) is correct detection of
  imperfect source text — the 0-FP gate is unreachable without gutting the rule
- det corruption misses when stanza re-parses structure (attach changes)
- no `Mood=Sub` in Greek stanza — mood rules need positional context
- `na_form` / `verb_valence` recall bounded by treebank coverage
- relcl corruption-pool samples: construction-targeted pool shipped (v0.0.25,
  23 sentences → 17 rel + 6 num corruptions); recall numbers pending a model run

## det_noun dual-gender article Gender gate RECON — SHIPPED (2026-10-20)

`FormLexicon.build()` kept only unambiguous article forms in `det_genders`
(`len(c)==1`), so syncretic articles («του» = Gen Masc+Neut) resolved via the
tagger's feats guess and produced Gender FPs against heads whose gender is one
of the article's *other* attested readings. Shipped: `build()` now also
serializes `det_gender_sets` (form -> genders, forms with >=2 genders and
total count >=2 — 6 forms in UD-train: ένα, ενός, οι, το, του, των) into a
bumped `lexicon.v3.json` (the documented stale-cache inertness constraint
made the filename bump mandatory), `FormLexicon.det_gender_set(word)` exposes
it, and `det_noun` suppresses a Gender mismatch when the article form's
attested set contains the head's resolved gender. Case/Number stay on
`_form_feats_gate`, untouched.

Measured (this machine, CPU pipeline, same session before/after):
- 456-sentence clean sweep: det_noun FP **19 → 13** (−6, all Gender; the 2
  Case + 1 Number residues unchanged; every other rule's count identical).
  Suppressed flags: «του»[Neut] vs υπολογιστή[Masc], «του»[Masc] vs
  Aθανασίου[Neut], «του»[Masc] vs Μαλάουι[Neut], «ενός»[Neut] vs φρουρού[Masc],
  «των»[Fem] vs γαλλικών[Masc], «Οι»[Fem] vs αντιπροσώποι[Masc]. Zero new
  flags.
- eval (n=100, seed 42): det recall **58% → 58%** (14/24), pool FP identical
  (det_noun 3, spelling 1), all other recalls identical (accent 87%, nonword
  96%, script-mix 95%, propn_accent 78%, negation/typography 100%), targeted
  pool identical (rel 3/17, num 3/6).
- Ship criteria met (FP drop, no recall regression) — gate kept. 4 new
  model-free unit tests + FakeLexicon `det_gender_sets` option.

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
| v0.0.20 | 2026-10 | adj_noun: form-attestation guards (adj_analyses, noun_gen_attested, form_feats) | 126 | identical (no pool target; 2 pilot trues waived with docs) | adj_noun 9→0 per 456 clean — joins the 0-FP tier | — |
| v0.0.21 | 2026-10 | verb_valence: argument-skeleton relaxation (ccomp/xcomp→clause, obj/iobj→objlike, expl dropped) | 128 | identical | verb_valence 11→1 per 456 clean (residue: sparse-treebank οφείλω+obj) | — |
| v0.0.22 | 2026-10 | rel_agreement: antecedent-ambiguity guard (agr_attested, NP ancestors, genitive possessors, foreign names) | 131 | identical (no pool target; probes fire) | rel_agreement 9→2 per 456 clean (νόσος = likely true source error kept) | — |
| v0.0.23 | 2026-10 | spelling: EXTRA_KNOWN_WORDS hunspell-gap whitelist (11 measured words) | 124 | identical | treebank 22 unchanged; pilot LLM-Greek NONWORD FPs −11 (ratchet green) | — |
| v0.0.24 | 2026-10 | suggestions: rel_agreement «ο οποίος», copula_pred «γιατρός», ranked spelling primaries | 136 | identical | identical (messages unchanged; only suggestion fields gained) | — |
| — (rejected) | 2026-10 | det_noun: suspect-head disjoint-evidence Gender gate (`form_gender`) — **REJECTED**, gate reverted, resource kept | 139 | identical (det 58%, 14/24) | det_noun 19→19 per 456 clean (gate inert: 0 suppressions; all 18 Gender mismatches non-suspect) | — |
| v0.0.25 (unreleased) | 2026-10 | eval: construction-targeted recall pool (`load_targeted_sentences` + targeted pass in `run_eval`) | 177 | pending model run (pool: rel 17, num 6 corruptions) | unchanged (FP scan + random recall pool identical) | — |
| v0.0.26 (unreleased) | 2026-10 | det_noun: dual-gender article Gender gate (`det_gender_sets` in `lexicon.v3.json`) | 186 | identical (det 58%, 14/24) | det_noun 19→13 per 456 clean (6 Gender FPs on «του/ενός/των/Οι»; pool FP identical) | — |

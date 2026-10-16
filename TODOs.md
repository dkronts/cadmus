# Cadmus — Roadmap & TODOs

Tracking file for everything we know we want. Checkbox = done. Items are
roughly ordered by value-per-effort within each phase.

## v0.0.2 — Dictionaries + Measurement (next)

- [x] **Hunspell `el_GR` integration** (`spylls`, pure Python)
      - non-word detection (typos, hallucinated words)
      - accent errors (`διαβασω` → `διαβάζω`)
      - Greek/Latin character mixup (ο vs o, ε vs e) — normalization check
      - candidate suggestions for flagged tokens
- [x] **Evaluation harness**
      - clean corpus: UD Greek-GDT held-out sentences (+ Wikipedia el)
      - corruption functions sampled from an LLM-error taxonomy:
        case swap, agreement break, prep-government violation, accent drop,
        char mixup, word order shuffle...
      - report precision/recall per rule; fail CI on precision regression
- [x] **Lexicon mined from UD-GDT** (form → {lemma, UPOS, feats})
      - tagger-conflict dampener: if stanza's analysis is not in the
        lexicon's analysis set, downgrade rule confidence instead of firing
- [x] **Verb-frame dictionary mined from UD-GDT** (verb lemma → dependency
      patterns + counts) — foundation for subcategorization rules

Measured at v0.0.3 (100 UD-GDT test sentences): recall — non-words 96%,
script-mix 97%, accents 89%, wrong article 62%, δεν/μην swap 100%; ~5 FPs/100
clean. Fixed gaps:
- [x] enclitic double accents (το κτίριό μου) no longer flagged as unknown
- [x] article paradigm table from the treebank: det gender resolved from form
      (counters the tagger "repairing" corrupted articles; recall 62→81% on
      the same pool, then pool shifted when negation corruption joined)
- [x] noun-gender overrides from lemma attestations (missing-feats nouns covered)

Newly surfaced gaps:
- [x] PROPN coverage: place-name/person accent errors (Ρωσια, Τύορκους) —
      added a proper-noun accent rule backed by a Wikipedia+UD title lexicon
      (see v0.0.5). Inflected/foreign forms stay silent by design (ambiguous)
- [ ] rare nouns absent from UD train (πρόποδες) still FP-prone via tagger
- [ ] det corruption misses when stanza re-parses structure (attach changes)
- [ ] stanza emits no Mood=Sub for Greek: any future mood-dependent rule must
      use positional context (see rules/negation.py)

## v0.0.3 — Rules backlog

- [ ] Verb subcategorization (deeper valence coverage):
      intransitive with object ("τρέχει κάτι"), ditransitive missing
      indirect object, wrong-case object (genitive objects)
- [x] δε(ν)/μη(ν) selection (indicative vs subjunctive/imperative, from
      Mood/VerbForm features + positional να-context)
- [ ] Copula predicate case (nominative predicate: "είμαι ράφτης";
      accusative object predicate: "τον έκαναν πρόεδρο")
      **BLOCKED**: the Greek POS model *repairs* case — "Είναι γιατρό" is
      re-tagged `Case=Nom`, so the accusative error is invisible to any
      feats-based rule. Needs a surface-form case check (declension table),
      not tagger feats.
- [ ] Relative pronoun agreement (ο οποίος ↔ antecedent, via `acl:relcl`) —
      shipped in v0.0.8
- [ ] Clitic rules: clitic doubling, clitic case with ditransitives,
      clitic position
- [ ] να + dependent verb form checks
      **BLOCKED**: stanza emits no `Mood=Sub` and assigns `Tense` inconsistently
      (the wrong "να πήγες" sometimes loses `Tense=Past`), so a feats rule misses
      the error. 0 FP but unreliable recall — needs a verb-form surface lexicon
      (which inflections are legal after να) rather than tagger feats.
- [ ] Numeral/noun agreement quirks (δύο + plural verb etc.)
- [ ] Adjective position classes (attributive vs predicative)

## v0.0.4 — Orthography & typography layer (no ML needed)

- [x] Greek question mark `;` vs `?`
- [x] Spacing rules: space before punctuation, missing space after, double
      spaces (decimals `3,14` / times `10:30` exempted)
- [x] Capitalization after a sentence terminator (`. ! ?`) — text-level, only
      fires mid-text so bare lowercase sentence starts are not penalized
- [ ] Quote style `«»` — deferred to an optional **style tier** (straight
      quotes are common and not an error; flagging them cost precision)
- [ ] Proper-noun casing
- [ ] Final -ν correctness (τον/το, στην/στη) where lexicon supports it

## v0.0.5 — Proper-noun lexicon + accent fixes

- [x] `PropnLexicon`: proper-noun surface forms mined from the Greek Wikipedia
      title dump (`elwiki-latest-all-titles-in-ns0`) + every `PROPN` form in
      UD-GDT (~169k forms), cached as `~/.cache/cadmus/propn.v1.json`
- [x] `propn_accent` rule: flags a capitalized token whose de-accented form maps
      to a **unique** attested form differing only by accents; ambiguous or
      unknown forms stay silent (precision-first, 0 FP on clean text)
- [x] Fixed a dead-code bug in `classify_unknown`: `spylls.suggest()` returns a
      generator that was consumed before the accent branch ran, so accent errors
      were always reported as NONWORD. Now `διαβασω → ACCENT → διαβάσω`, and
      spelling violations carry a structured `suggestion`
- [x] Eval target `propn_accent` counts detection by `propn_accent` **or**
      `spelling` (a de-accented name the tagger re-labels as a common word is
      caught by the spelling layer); recall 62%, 0 FP

## v0.0.6 — Usability & integration

- [~] Suggestion generation (not just flags): `det_noun` now emits the
      corrected article from the paradigm table; broader per-rule suggestions
      (suffix/declension tables) still pending
- [x] `--rules` filter, `--severity`, `--quiet` CLI options (pure
      `data.filter_violations`; `--quiet` = no output, exit code drives gating)
- [x] Rule severity + category taxonomy in JSON output (`Violation.severity`,
      `RULE_SEVERITY`; surfaced in CLI and `--json`)
- [x] GitHub Actions CI: model-free rule unit tests (fake stanza objects),
      integration job gated behind `workflow_dispatch`

## v0.0.7 — Data factory export

- [x] `cadmus export`: aligned (broken -> correct) pairs from the held-out
      UD-GDT test sentences, labelled by error type with a localized diff span
      (`--format jsonl|json`); model-free (no stanza), CI-tested
- [x] `--with-check` to attach the checker's own detection + suggestion per pair
      (shipped in v0.0.9)
- [ ] richer targets: multi-error sentences, sentence-pair (context) examples

## v0.0.8 — Relative-pronoun agreement

- [x] `rel_agreement` rule: `ο οποίος` (and its inflected forms) must agree with
      its antecedent in **Gender + Number**; Case is free (it comes from the
      relative clause). The antecedent is found by walking the head chain up to
      the nearest `acl:relcl` verb and taking that verb's head — this also
      resolves pronouns buried in a prepositional phrase (`σύμφωνα με την οποία`)
- [x] Antecedent restricted to `NOUN`/`PROPN`; the rule is dampenable, so
      tagger-suspect tokens are suppressed. **0 FP** on clean UD-GDT text
- [x] Model-free unit tests (fake trees, incl. the PP walk-up path) + stanza
      integration tests (correct vs. wrong-gender relative clauses)
- [ ] Eval recall not yet measured: the corruption pool is filtered to 4–15
      tokens, which excludes almost every relative clause, so `corrupt_rel_agreement`
      has no samples. Needs a longer-sentence pool or a dedicated relcl sub-corpus

## v0.0.9 — Export self-check

- [x] `export --with-check`: runs the checker on each broken sentence and attaches
      `detected` (a violation overlapping the corrupted span), `detected_rules`,
      and the checker's `suggestion` — turning the export into a per-pair QA report
      on what cadmus actually catches
- [x] Dependency-injected `annotate_with_check(pairs, check)` keeps `export.py`
      stanza-free (model-free CI test with a fake checker)

## v0.0.10 — Streaming & batch

- [ ] Batch mode (stanza batch processing) for whole documents
- [x] `watch` mode: check a stream of texts (one per line) as they arrive —
      silent on clean lines, prints violations per record, `--json`/`--severity`/
      `--rules` supported. Reads stdin or a file; for a growing file pipe it
      (`tail -f server.log | cadmus watch`). Pure `stream.iter_checked` helper
      (injected checker) keeps it model-free and CI-tested

## Later / research

- [ ] Confidence gating + escalation to a local Greek-tuned LLM judge
      (Krikri-8B / Meltemi-7B) for low-confidence spans
- [ ] Error corpus from real quantized-MoE outputs (collect + annotate;
      calibrate the corruption taxonomy against it)
- [ ] LanguageTool Greek baseline comparison on the same eval set
- [x] Diagnostics mode: `cadmus diagnose` reports, per UPOS, how often each
      expected feature (Gender/Case/Number/Tense/Person) is present, flagging
      low-coverage features where rules will under-fire (shipped in v0.0.11)
- [ ] WordNet/selectional preferences (only if semantics rules ever
      become tractable)

## Done

- [x] v0.0.1 — det-noun / adj-noun / subj-verb (coordination-aware) /
      prep-case rules; demo corpus as regression set; CLI
- [x] v0.0.4 — typography rule (`?`→`;`, spacing, capitalization), severity
      taxonomy on every violation, `det_noun` article suggestions, model-free
      rule unit tests + GitHub Actions CI. Measured (150 UD-GDT test sentences):
      recall — non-words 92%, script-mix 95%, accents 95%, wrong article 62%,
      δεν/μην 100%, typography 100%; ~7 FPs/100 clean (typography 0 FP).
- [x] v0.0.5 — proper-noun accent lexicon (Wikipedia titles + UD-GDT PROPNs,
      ~169k forms) and `propn_accent` rule; fixed the `classify_unknown`
      generator bug so accent errors report as ACCENT with suggestions.
      Measured (200 UD-GDT test sentences): recall — accents 95%, script-mix 96%,
      non-words 88%, proper-noun accent 62%, wrong article 68%, δεν/μην 100%,
      typography 100%; ~7 FPs/100 clean (typography and propn_accent 0 FP).
- [x] v0.0.6 — CLI gating for middleware use: `--severity` (min level),
      `--rules` (id allow-list), `--quiet` (silent, exit code 1 if any filtered
      violation remains); pure `filter_violations` helper with model-free tests.
- [x] v0.0.7 — data-factory export: `cadmus export` emits aligned
      (broken → correct) pairs from UD-GDT, labelled by error type with a
      localized diff span (`jsonl`/`json`); model-free and CI-tested.
- [x] v0.0.8 — `rel_agreement`: `ο οποίος` ↔ antecedent Gender+Number agreement
      via the `acl:relcl` head chain (resolves PP-nested pronouns too);
      dampenable, 0 FP on clean text, model-free + integration tests.
- [x] v0.0.9 — `export --with-check`: per-pair `detected`/`detected_rules`/
      `suggestion` from the checker (span-overlap), via a dependency-injected
      `annotate_with_check` that keeps the export module stanza-free.
- [x] v0.0.10 — `watch` mode: live-gate a stream of texts (one per line) from
      stdin or a file; silent on clean lines, `--json`/`--severity`/`--rules`.
      Pure `stream.iter_checked` helper (injected checker), model-free CI test.
- [x] v0.0.11 — `diagnose` mode: per-UPOS feature-coverage report (where the
      tagger omits Gender/Case/Tense), via a model-free `diagnostics` module.
      Documented two analyzer-imposed blockers: copula-predicate case and
      να-verb-form rules can't use tagger feats (the model repairs case and
      assigns Tense inconsistently) — they need surface-form morphology.

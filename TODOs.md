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
- [x] Copula predicate case (nominative predicate: "είμαι ράφτης") — shipped
      in v0.0.12 as `copula_pred`. The tagger *repairs* case ("Είναι γιατρό" →
      `Case=Nom`), so the rule ignores tagger Case and instead flags a masculine
      NOUN predicate whose surface form ends in -ο/-ους (a masculine nominative
      always ends in -ς). Suppressed when the predicate's gender contradicts its
      overt subject (guards mis-tagged predicate adjectives). 0 FP on clean text;
      recall limited to masculine nouns (fem/neuter nom=acc syncretism is unsafe).
- [ ] Relative pronoun agreement (ο οποίος ↔ antecedent, via `acl:relcl`) —
      shipped in v0.0.8
- [ ] Clitic rules: clitic doubling, clitic case with ditransitives,
       clitic position — **REJECTED (analyzer + precision)**. Three sub-ideas
       measured and dropped: (1) the tagger tags indirect-object clitics as
       `obj`, not `iobj` (`Του μίλησα` → `obj`/`Gen`), so the deprel signal the
       rule needs isn't emitted; (2) a valence-free `iobj`+Acc invariant is 0 FP
       on clean test but 3 FP on train gold and never fires on analyzer output;
       (3) a per-verb clitic-case lexicon is coverage-limited (2 FP on clean test
       from unseen verbs) and Greek verbs legitimately license several clitic
       cases, so the closed-set invariant doesn't hold. No safe offline rule.
- [x] να + dependent verb form checks — shipped in v0.0.12 as `na_form`. The
      tagger assigns `Tense` inconsistently, so the rule classifies by *surface
      form* against a UD-GDT verb-form lexicon: flags a `να`-governed verb only
      when its form is attested exclusively as a finite past indicative and never
      after `να`. 0 FP on clean text; recall bounded by treebank coverage.
- [x] Numeral/noun gender agreement — shipped in v0.0.14 as `num_noun`. The
       tagger *repairs* a numeral's `Gender` to match its noun (`τρεις παιδιά` →
       `Gender=Neut`), so the rule reads the numeral's gender from its **surface
       form** (`τρεις`/`τέσσερις` → M/F, `τρία`/`τέσσερα` → N) and only trusts the
       noun's gender (via the same lemma-attestation resolver as `adj_noun`).
       0 FP on clean text (148 eval + 456 full test, via the analyzer). Recall
       not in the corruption pool (no gendered numeral in the 4–15-token pool),
       so it is validated by targeted integration tests, like `rel_agreement`.
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
- [ ] Proper-noun casing — **REJECTED (precision)**. A strict policy (sentence-
      internal, fully-lowercase, in `PropnLexicon`, not a dictionary word, not a
      treebank common word) still yields ~5 FP / 456 clean sentences (1.1%), all
      systematic: Greek *lowercases* demonyms and adjectives (`ολλανδός`,
      `τούρκος`, `ευρωπαίοι`, `ευρωζώνη`, `ερυθηματώδης`) that nonetheless carry
      Wikipedia titles, so the title dump conflates always-capitalized proper
      nouns with correctly-lowercase ones. No cheap offline filter separates them;
      a safe rule needs a curated always-capitalized (person/place-only) list we
      don't have. Shipping it would break the 0-FP invariant every other rule holds.
- [ ] Final -ν correctness (τον/το, στην/στη) — **REJECTED (prescriptive)**.
      The ν-variant is free variation (τον/το, στην/στη both standard); there is no
      grammatical error to flag, only house style, and any rule would fire on
      correct text. Belongs in a style tier, not the correctness layer.

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

- [x] Batch mode: `CadmusChecker.check_batch(texts)` runs the pipeline's batched
      processor (`pipe` on newer stanza, `process_many` on <=1.15, per-text
      fallback) and `cadmus batch` checks a file/stdin of one-text-per-line in
      chunks (`--batch-size`); model-free tests cover both APIs + chunking
- [x] `watch` mode: check a stream of texts (one per line) as they arrive —
      silent on clean lines, prints violations per record, `--json`/`--severity`/
      `--rules` supported. Reads stdin or a file; for a growing file pipe it
      (`tail -f server.log | cadmus watch`). Pure `stream.iter_checked` helper
      (injected checker) keeps it model-free and CI-tested

## v0.0.15 — Spelling precision (lexicon coverage + abbreviation guards)

- [x] `spelling` now consults the per-sentence env lexicons the checker already
      builds: a token unknown to hunspell is treated as known when its surface
      form is attested in `FormLexicon.entries` (UD-GDT train) or in
      `PropnLexicon.forms` (Wikipedia titles + UD PROPNs). PROPN coverage
      counts **only for accented tokens**: the title dump holds ~5.5k unaccented
      variants (`απο`, `βορεια`) homographic with de-accented common words, and
      trusting them cost accent recall (87→60% on the eval pool); restricted,
      recall is back to baseline and the suppression stays (`Χρυσοπηγής`,
      `ευρωζώνη`, `ερυθηματώδης` no longer flagged)
- [x] `spelling` skips abbreviations/elisions/multiword tokens (containing
      `.`, `,`, `'`/`’` or whitespace): `χλμ.`, `κ.`, `αριθ.`, `απ'`, `ό,τι`
      were ~50 of the 77 full-test clean-text FPs; corruptions never produce
      such tokens (typo/accent/homoglyph require a pure-Greek word), so recall
      is untouched
- [x] Measured (456-sentence full clean test, end-to-end through the analyzer):
      spelling FPs **77 → 22 (−71%)**; every other rule's FP count unchanged;
      injected-error recall unchanged (accent 87%, nonword 96%, script-mix 95%,
      propn_accent 78%, eval pool seed 42). Model-free unit tests (8) +
      integration probes (3) added
- [ ] 0-FP gate on the full 456-sentence clean set — **REJECTED (coverage)**.
      After the two shipped guards the residue is 22 flags, every one a correct
      detection of imperfect source text or an uncovered rare word: 7 are
      genuine typos in the UD-GDT source (`αποτέλεσματα`, `πρέσβειας`,
      `αντιπροσώποι`, `Βορεία`, `ηλίκια`, `μεσαιωνκής`, `καφκικές`), 7 are
      archaic/rare forms attested in none of the repo's resources
      (`συνεκλήθη`, `διαβουλεύθηκε`, `αθετούντο`, `παρέμβω`, `επανεδραιώσει`,
      `βοειδών`, `κκ`), 4 are compounds (`τουρκοκουρδικό`, `Βορειοκορεάτες`,
      `κρεατάλευρα`×2), 4 are real Greek/Latin script mixing (`Kαζάρμα`,
      `Bενετοκρατίας`, `Aθανασίου`, `Dybkjζr`). No surface signal separates
      these populations from real errors, so suppressing them means deleting
      ACCENT/NONWORD detection (a recall regression). 0 FP is unreachable for
      the spelling rule without gutting it; the eval-pool spelling FP count
      (5/148) lies entirely inside this residue.

## Later / research

- [ ] Confidence gating + escalation to a local Greek-tuned LLM judge
      (Krikri-8B / Meltemi-7B) for low-confidence spans — **needs external
      resource**: no local Greek-tuned model is installed; requires a multi-GB
      model download + GPU. Deferred until such a model is provisioned.
- [ ] Error corpus from real quantized-MoE outputs (collect + annotate;
      calibrate the corruption taxonomy against it) — **needs external
      resource**: requires collecting/annotating real outputs (human labeling);
      not derivable offline.
- [ ] LanguageTool Greek baseline comparison on the same eval set — **needs
      external resource**: neither the `languagetool` CLI nor
      `language_tool_python` is installed (and the CLI needs a JRE + a large
      download). Deferred until the tool is provisioned.
- [x] Diagnostics mode: `cadmus diagnose` reports, per UPOS, how often each
      expected feature (Gender/Case/Number/Tense/Person) is present, flagging
      low-coverage features where rules will under-fire (shipped in v0.0.11)
- [ ] WordNet/selectional preferences (only if semantics rules ever
      become tractable)

## Brainstorm — next steps

Fill this section only when "Newly surfaced gaps" and the backlog are both
exhausted (loop step 8 in `AGENTS.md`): propose concrete candidates with
value / effort / risk / how to measure, then work the autonomous ones and
ASK USER for any that hit the decision matrix.

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
- [x] v0.0.12 — `copula_pred` + `na_form`, the two rules that bypass the tagger's
       case/tense repair by deciding from surface forms: `copula_pred` flags a
       masculine NOUN copula predicate ending in -ο/-ους (never nominative),
       suppressed on subject-gender conflict; `na_form` flags a `να`-governed
       verb whose surface form is attested only as a past indicative (new
       `VerbForms` UD-GDT lexicon). Both 0 FP on clean text; model-free unit
       tests + integration tests.
- [x] v0.0.13 — batch mode: `check_batch` (batched pipeline via `pipe`/
        `process_many`/fallback) + `cadmus batch` CLI for one-text-per-line input;
        model-free tests for both batch APIs and chunking. Documented two rejected
        rules (proper-noun casing, final -ν) with the precision evidence, and the
        external-resource blockers on the remaining research items.
- [x] v0.0.15 — spelling precision: unknown tokens attested in the env's
        `FormLexicon`/`PropnLexicon` (accented tokens for PROPN coverage) are
        treated as known, and abbreviation/elision tokens (`χλμ.`, `απ'`, `ό,τι`)
        are skipped; 456-sentence clean sweep spelling FPs 77 → 22 with recall
        unchanged; the 0-FP gate on the full clean set documented REJECTED
        (residue = source typos + script mixing + words in no repo resource).
        89 tests (67 model-free).
- [x] v0.0.14 — `num_noun`: gendered numerals (`τρεις`/`τρία`, `τέσσερις`/`τέσσερα`)
        must match their noun's gender; decides the numeral's gender from its
        surface form (the tagger repairs `Gender` to agree) and trusts only the
        noun's gender via the `adj_noun` lemma-attestation resolver. Dampenable,
        0 FP on clean text (148 eval + 456 full test), model-free unit tests +
        integration tests. Documented the clitic-rule rejection (analyzer tags
        indirect clitics as `obj`; per-verb case lexicon is coverage-limited).

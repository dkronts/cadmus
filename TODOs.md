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
- [ ] PROPN coverage: place-name/person accent errors (Ρωσια, Τύορκους) are
      skipped by design — needs a proper-noun lexicon (Wikipedia titles?)
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
- [ ] Relative pronoun agreement (ο οποίος ↔ antecedent, via `acl`)
- [ ] Clitic rules: clitic doubling, clitic case with ditransitives,
      clitic position
- [ ] να + dependent verb form checks
- [ ] Numeral/noun agreement quirks (δύο + plural verb etc.)
- [ ] Adjective position classes (attributive vs predicative)

## v0.0.4 — Orthography & typography layer (no ML needed)

- [ ] Greek question mark `;` vs `?`
- [ ] Quote style `«»`, spacing rules, space before/after punctuation
- [ ] Capitalization after sentence end; proper-noun casing
- [ ] Final -ν correctness (τον/το, στην/στη) where lexicon supports it

## v0.0.5 — Usability & integration

- [ ] Suggestion generation (not just flags): paradigm tables per
      declension classes (suffix tables)
- [ ] `--rules` filter, `--severity`, `--quiet` CLI options
- [ ] Rule severity + category taxonomy in JSON output
- [ ] Batch mode (stanza batch processing) for whole documents
- [ ] `watch` mode: read a growing file / named pipe — for live-gating
      local LLM output (ollama / llama.cpp server logs)
- [ ] GitHub Actions CI: model-free rule unit tests (fake stanza objects),
      integration job optional/nightly

## Later / research

- [ ] Confidence gating + escalation to a local Greek-tuned LLM judge
      (Krikri-8B / Meltemi-7B) for low-confidence spans
- [ ] Error corpus from real quantized-MoE outputs (collect + annotate;
      calibrate the corruption taxonomy against it)
- [ ] LanguageTool Greek baseline comparison on the same eval set
- [ ] Diagnostics mode: report tagger feats coverage gaps (missing
      Gender/Case on tokens) per document
- [ ] WordNet/selectional preferences (only if semantics rules ever
      become tractable)

## Done

- [x] v0.0.1 — det-noun / adj-noun / subj-verb (coordination-aware) /
      prep-case rules; demo corpus as regression set; CLI

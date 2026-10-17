# Cadmus

Greek **grammar and syntax intelligence layer** — a modular guardian for
machine-generated Greek.

![ci](https://github.com/dkronts/cadmus/actions/workflows/ci.yml/badge.svg)

Neural models are now the most prolific producers of Greek text: local LLMs
(especially quantized MoE variants), speech-to-text engines, translation and
summarization pipelines. Their output degrades in characteristic ways — broken
agreement, wrong case government, valence anomalies, orthographic damage.
Cadmus detects those failures deterministically and locally, with no API calls
and no cloud.

## Where this is going

Cadmus is built as infrastructure, not a point tool:

- **Correction layer** over poor LLM output — flag now, rewrite later
- **STT post-processor** — speech-to-text Greek needs it even more than LLM Greek
- **Middleware** — a gate sitting between a model and the user, fast enough to
  keep up with streaming generation
- **Data factory** — every detected error is a training signal: aligned
  (broken → correct) pairs for fine-tuning and RLHF-style reward models

(Cadmus: the one who brought letters to Greece. Now he proofreads them.)

## How it works

```
text → typography-normalized shadow (analysis only; offsets mapped back)
     → stanza (Greek: tokenize, POS, morph features, lemmas, dependencies)
     → rule engine (checks over the morphosyntactic analysis)
     → violations: rule id, severity, message, character offsets, suggestions
```

Precision-first: rules interrogate a disambiguated analysis and flag
contradictions; they never require a full parse to succeed.

### Rules

| Rule | Catches |
|---|---|
| `det_noun` | article–noun agreement; article gender taken from a treebank paradigm table (resists the tagger "repairing" corrupted input), noun gender from lemma attestations; heteroclite-plural exceptions (τα πλευρά); emits the corrected article as a suggestion |
| `adj_noun` | adjective–noun agreement (only when cases match — case mismatches indicate parse artifacts) |
| `num_noun` | gendered numeral–noun agreement (`τρεις παιδιά` → `τρία παιδιά`). The tagger *repairs* the numeral's gender to match the noun, so the numeral's gender is read from its surface form (`τρεις`/`τέσσερις` → M/F, `τρία`/`τέσσερα` → N) and only the noun's gender is trusted (lemma attestations, as in `adj_noun`) |
| `subj_verb` | subject–verb number and person, with coordination-aware number licensing |
| `rel_agreement` | `ο οποίος` ↔ antecedent Gender+Number agreement (Case is free — it comes from the relative clause); the antecedent is located by walking the head chain to the nearest `acl:relcl` verb, so pronouns inside a prepositional phrase (`σύμφωνα με την οποία`) resolve too |
| `copula_pred` | accusative copula predicate (`Είναι γιατρό` → `γιατρός`). The tagger *repairs* the case to nominative, so the rule decides from the surface form: a masculine NOUN predicate ending in `-ο`/`-ους` can never be nominative (a masculine nominative ends in `-ς`). Suppressed when the predicate's gender contradicts its overt subject |
| `na_form` | a past indicative wrongly used after `να` (`να έκανε` → `να κάνει`). Tagger `Tense` is unreliable, so a UD-GDT verb-form lexicon flags a `να`-governed verb only when its surface form is attested **exclusively** as a past indicative and never after `να` |
| `prep_case` | prepositional case government (λόγω/εκτός/εξαιτίας/μέσω/… + Gen; others + Acc), dual-government prepositions (παρά, κατά, υπό, μέχρι) never flagged, fossilized datives (εν τάξει) and pronoun/unattested heads skipped |
| `spelling` | non-words, accent/diacritic errors (incl. enclitic double accents), Greek/Latin script mixing — via hunspell `el_GR` (spylls); skips proper-noun spelling, acronyms, abbreviations/elisions (`χλμ.`, `απ'`), and unknown tokens whose surface form is attested in the UD-train form lexicon or (accented tokens only) the PROPN title lexicon |
| `verb_valence` | unexpected object patterns per verb, from subcategorization frames mined out of UD-GDT; nominative "objects" (postverbal subjects) are exempt |
| `negation` | δεν/μην selection — subjunctive context detected positionally (να/ας/μήπως), imperative by missing Tense+Mood |
| `propn_accent` | mis-accented proper nouns (`Ρωσια` → `Ρωσία`, `Παπαδοπουλος` → `Παπαδόπουλος`) against a 169k-form title lexicon mined from Wikipedia + UD-GDT; flags only when the de-accented form maps to a **unique** attested form (ambiguous → silent) |
| `typography` | Greek punctuation conventions: `?` → `;`, stray space before punctuation, missing space after, double spaces, lowercase after a sentence terminator (text-level, no parser needed) |

A treebank-derived **form lexicon** acts as a dampener: when the analyzer's
reading of a word is impossible per the treebank, flags involving it are
suppressed (tagger-error tolerance).

### Measured (v0.0.5, `cadmus eval`, 200 UD-GDT test sentences)

| Error type (injected) | Recall |
|---|---|
| accent errors | 95% |
| Greek/Latin homoglyph mixing | 96% |
| typos / non-words | 88% |
| proper-noun accent | 62% |
| wrong article form | 68% |
| δεν/μην swap | 100% |
| typography | 100% |

False positives on clean text: ~7 per 100 sentences (mostly rare-word spelling
and a handful of tagger artifacts); on the full 456-sentence clean test set the
`spelling` rule's FPs dropped 77 → 22 at v0.0.15 (env-lexicon coverage
suppression + abbreviation/elision guards, recall unchanged — the 22-flag
residue is correct detection of imperfect source text and script mixing).
`typography`, `propn_accent`,
`rel_agreement`, `copula_pred`, `na_form` and `num_noun` fire **zero** false
positives. Every
violation carries a `severity` (`low`/`medium`/`high`) so callers can filter style
nits from hard errors.

`rel_agreement` and `num_noun` are validated by targeted tests rather than the
corruption table above: the eval pool is filtered to short (4–15 token)
sentences, which excludes nearly every relative clause and gendered numeral, so
the injected-error harness has no samples to score yet.

The proper-noun lexicon is mined from the Greek Wikipedia title dump plus every
`PROPN` surface form in UD-GDT (~169k forms, cached under `~/.cache/cadmus`).
Recall is capped by design: inflected or foreign names whose de-accented form is
ambiguous are left alone rather than guessed.

## Install

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .            # pulls stanza (and torch)
cadmus demo                  # first run downloads the Greek models (~1 GB)
```

### Known stanza bug (Greek lemma model)

Stanza 1.15's Greek lemma classifier hardcodes a path from its training
machine. If pipeline loading fails with `conll17.pt does not exist`:

```bash
sh scripts/fix_stanza_lemma.sh
```

(Or create a sudoless symlink manually; `cadmus.pipeline` also attempts an
automatic fix where permissions allow.)

## Usage

```bash
echo "Λόγω την καθυστέρηση, αργήσαμε." | cadmus check
cadmus check output.txt
cadmus check output.txt --json
cadmus demo
cadmus eval --n 100
```

As a gate in front of a model, filter to what matters and let the exit code
drive the pipeline (0 = clean, 1 = violations remain):

```bash
cadmus check draft.txt --severity medium   # ignore low-severity style nits
cadmus check draft.txt --rules negation,prep_case   # only these checks
cadmus check draft.txt --deep              # confirm each suggestion by re-analysis
cadmus check draft.txt --quiet || echo "needs review"
```

`--deep` runs a second analysis pass per suggestion: the fix is applied to a
copy and the same rule must no longer fire there (`✓confirmed` in output,
`confirmed` in JSON) — analyzer-verified suggestions, not just pattern
matches. Slower (one extra analysis per suggestion); the default path is
unchanged.

### Live-gating a model

`watch` checks a stream of texts (one per line) as they arrive — silent on clean
lines, one line per violation otherwise. Pipe a server log or a JSONL stream:

```bash
tail -f ollama.log | cadmus watch                 # flag as they stream by
cadmus watch responses.jsonl --json               # one JSON verdict per record
cadmus watch responses.jsonl --severity medium    # ignore style nits
```

### Batch

`watch` parses each line as it arrives (lowest latency). When you already have a
whole file of texts and want throughput, `batch` runs the analyzer's batched
processor instead of one call per line:

```bash
cadmus batch responses.txt                  # one text per line, batched
cadmus batch responses.txt --batch-size 64  # larger pipeline batches
cadmus batch responses.txt --json           # one JSON verdict per record
```

### Diagnostics

Rules can only fire on features the tagger emits. `cadmus diagnose` reports how
much morphology the analyzer actually exposes, flagging low-coverage features
(where a rule will silently under-fire):

```bash
cadmus diagnose corpus.txt
# VERB  Tense   50.0% present (1/2)  <-- low: rules on this feature will under-fire
```

### Data factory

Every injected error is a labelled training pair. `cadmus export` mines the
held-out UD-GDT test sentences and emits aligned `(broken → correct)` records
with the error type and a localized diff span — ready for fine-tuning or a
reward model:

```bash
cadmus export --n 5000 --format jsonl > pairs.jsonl
# {"rule":"accent","broken":"...αξιοποιησουμε...","correct":"...αξιοποιήσουμε...",
#  "span_start":20,"broken_fragment":"η","correct_fragment":"ή"}
```

`--with-check` runs the checker on each broken sentence and attaches its own
verdict, so the export doubles as a QA report on what cadmus actually catches:

```bash
cadmus export --n 500 --with-check
# {...,"detected":true,"detected_rules":["det_noun"],"suggestion":"«της»"}
```

Library:

```python
from cadmus import CadmusChecker
c = CadmusChecker()
for v in c.check("Η πράσινο δέντρο είναι μεγάλο."):
    print(v.severity, v.rule, v.message, v.suggestion)
# medium det_noun DET-NOUN Gender: 'Η'[Fem] vs 'δέντρο'[Neut] «το»
```

## Roadmap

See [TODOs.md](TODOs.md). Highlights: verb subcategorization depth, clitics,
broader suggestion generation (rewriting, not just flagging), and batch
processing. Typography + severity taxonomy landed in v0.0.4, the proper-noun
accent lexicon in v0.0.5, CLI gating in v0.0.6, the data-factory export in
v0.0.7, relative-pronoun agreement in v0.0.8, `export --with-check` in v0.0.9,
and streaming `watch` mode for live-gating in v0.0.10.

## License

MIT — Cadmus contributors

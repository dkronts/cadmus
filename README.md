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
text → stanza (Greek: tokenize, POS, morph features, lemmas, dependencies)
     → rule engine (checks over the morphosyntactic analysis)
     → violations: rule id, severity, message, character offsets, suggestions
```

Precision-first: rules interrogate a disambiguated analysis and flag
contradictions; they never require a full parse to succeed.

### Rules in v0.0.4

| Rule | Catches |
|---|---|
| `det_noun` | article–noun agreement; article gender taken from a treebank paradigm table (resists the tagger "repairing" corrupted input), noun gender from lemma attestations; heteroclite-plural exceptions (τα πλευρά); emits the corrected article as a suggestion |
| `adj_noun` | adjective–noun agreement (only when cases match — case mismatches indicate parse artifacts) |
| `subj_verb` | subject–verb number and person, with coordination-aware number licensing |
| `prep_case` | prepositional case government (λόγω/εκτός/… + Gen; others + Acc), with fixed-expression exceptions (από κοινού) |
| `spelling` | non-words, accent/diacritic errors (incl. enclitic double accents), Greek/Latin script mixing — via hunspell `el_GR` (spylls); skips proper-noun spelling and acronyms |
| `verb_valence` | unexpected object patterns per verb, from subcategorization frames mined out of UD-GDT; nominative "objects" (postverbal subjects) are exempt |
| `negation` | δεν/μην selection — subjunctive context detected positionally (να/ας/μήπως), imperative by missing Tense+Mood |
| `typography` | Greek punctuation conventions: `?` → `;`, stray space before punctuation, missing space after, double spaces, lowercase after a sentence terminator (text-level, no parser needed) |

A treebank-derived **form lexicon** acts as a dampener: when the analyzer's
reading of a word is impossible per the treebank, flags involving it are
suppressed (tagger-error tolerance).

### Measured (v0.0.4, `cadmus eval`, 150 UD-GDT test sentences)

| Error type (injected) | Recall |
|---|---|
| typos / non-words | 92% |
| Greek/Latin homoglyph mixing | 95% |
| accent errors | 95% |
| wrong article form | 62% |
| δεν/μην swap | 100% |
| typography | 100% |

False positives on clean text: ~7 per 100 sentences (mostly rare-word spelling
and a handful of tagger artifacts). Every violation carries a `severity`
(`low`/`medium`/`high`) so callers can filter style nits from hard errors.

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

Library:

```python
from cadmus import CadmusChecker
c = CadmusChecker()
for v in c.check("Η πράσινο δέντρο είναι μεγάλο."):
    print(v.severity, v.rule, v.message, v.suggestion)
# medium det_noun DET-NOUN Gender: 'Η'[Fem] vs 'δέντρο'[Neut] «το»
```

## Roadmap

See [TODOs.md](TODOs.md). Highlights: proper-noun lexicon, verb
subcategorization depth, clitics, broader suggestion generation (rewriting, not
just flagging), and the correction/fine-tuning data factory. Typography and a
severity taxonomy landed in v0.0.4.

## License

MIT — Cadmus contributors

# Cadmus

Greek **grammar and syntax intelligence layer** — a modular guardian for
machine-generated Greek.

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
     → violations: rule id, message, character offsets, suggestions
```

Precision-first: rules interrogate a disambiguated analysis and flag
contradictions; they never require a full parse to succeed.

### Rules in v0.0.3

| Rule | Catches |
|---|---|
| `det_noun` | article–noun agreement; article gender taken from a treebank paradigm table (resists the tagger "repairing" corrupted input), noun gender from lemma attestations; heteroclite-plural exceptions (τα πλευρά) |
| `adj_noun` | adjective–noun agreement (only when cases match — case mismatches indicate parse artifacts) |
| `subj_verb` | subject–verb number and person, with coordination-aware number licensing |
| `prep_case` | prepositional case government (λόγω/εκτός/… + Gen; others + Acc), with fixed-expression exceptions (από κοινού) |
| `spelling` | non-words, accent/diacritic errors (incl. enclitic double accents), Greek/Latin script mixing — via hunspell `el_GR` (spylls); skips proper-noun spelling and acronyms |
| `verb_valence` | unexpected object patterns per verb, from subcategorization frames mined out of UD-GDT; nominative "objects" (postverbal subjects) are exempt |
| `negation` | δεν/μην selection — subjunctive context detected positionally (να/ας/μήπως), imperative by missing Tense+Mood |

A treebank-derived **form lexicon** acts as a dampener: when the analyzer's
reading of a word is impossible per the treebank, flags involving it are
suppressed (tagger-error tolerance).

### Measured (v0.0.3, `cadmus eval`, 100 UD-GDT test sentences)

| Error type (injected) | Recall |
|---|---|
| typos / non-words | 96% |
| Greek/Latin homoglyph mixing | 97% |
| accent errors | 89% |
| wrong article form | 62% |
| δεν/μην swap | 100% |

False positives on clean text: ~5 per 100 sentences.

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
for v in c.check("Οι γάτες είναι πεινασμένη."):
    print(v.rule, v.message)
```

## Roadmap

See [TODOs.md](TODOs.md). Highlights: proper-noun lexicon, verb
subcategorization depth, clitics, punctuation layer, suggestion generation
(rewriting, not just flagging), and the correction/fine-tuning data factory.

## License

MIT — Cadmus contributors

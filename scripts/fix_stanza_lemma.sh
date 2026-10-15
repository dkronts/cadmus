#!/bin/sh
# Workaround for stanza 1.15 Greek packaging bug:
# the el lemma-classifier checkpoint hardcodes /nlp/scr/horatio/... as its
# pretrain path. This links the cached conll17.pt there.
set -e
REAL=$(find "$HOME/.cache/stanza" -path '*el/pretrain/conll17.pt' | head -1)
if [ -z "$REAL" ]; then
  echo "conll17.pt not found in stanza cache; run once so models download first." >&2
  exit 1
fi
sudo mkdir -p /nlp/scr/horatio/stanza_resources/el/pretrain
sudo ln -sf "$REAL" /nlp/scr/horatio/stanza_resources/el/pretrain/conll17.pt
echo "linked $REAL -> /nlp/scr/horatio/stanza_resources/el/pretrain/conll17.pt"

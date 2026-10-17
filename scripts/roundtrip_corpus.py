#!/usr/bin/env python3
"""Build a round-trip LLM-Greek error corpus from an OPUS parallel corpus.

Methodology (pilot: 100 GlobalVoices pairs, 2026-10-17):
  1. Download an OPUS EN-EL moses bitext (GlobalVoices v2018q4).
  2. Filter to clean, deduplicated, sentence-aligned pairs (10-32 EN tokens).
  3. Machine-translate the EN side with a local OpenAI-compatible server
     (default: llama.cpp at 127.0.0.1:8000, Qwen3-8B q4, temperature 0.3).
  4. Emit JSONL rows {id, en, ref_el, llm_el} ready for judging.

Flags on the outputs are then judged by a human against ref_el and recorded
in tests/data/llm_greek_pilot.v1.jsonl (see tests/test_llm_pilot.py for the
regression ratchet). Judging stays manual by design: round-trip output also
contains legitimate paraphrases, so diffs are not error lists.

Usage:
  python scripts/roundtrip_corpus.py --n 100 --out /tmp/pilot.jsonl
  python scripts/roundtrip_corpus.py --n 100 --out /tmp/pilot.jsonl \
      --url http://127.0.0.1:8001/v1 --model weaker-model-id
"""

import argparse
import json
import random
import re
import urllib.request
import zipfile
from io import BytesIO

OPUS_URL = ("https://object.pouta.csc.fi/OPUS-GlobalVoices/v2018q4/"
            "moses/el-en.txt.zip")
GREEK = re.compile(r"[Α-Ωα-ωάέήίόύώϊϋΐΰ]")
ASCII_WORD = re.compile(r"[A-Za-z]")

PROMPT = "Translate to Greek. Output ONLY the translation, nothing else.\n\n"


def fetch_pairs(limit_pool=20000):
    with urllib.request.urlopen(OPUS_URL, timeout=300) as r:
        data = r.read()
    zf = zipfile.ZipFile(BytesIO(data))
    en = zf.read("GlobalVoices.el-en.en").decode("utf-8").splitlines()
    el = zf.read("GlobalVoices.el-en.el").decode("utf-8").splitlines()
    seen, pairs = set(), []
    for e, g in zip(en, el):
        e, g = e.strip(), g.strip()
        et, gt = e.split(), g.split()
        if not (10 <= len(et) <= 32 and 8 <= len(gt) <= 36):
            continue
        if not e.endswith(".") or not g.endswith("."):
            continue
        if not GREEK.search(g) or GREEK.search(e) or not ASCII_WORD.search(e):
            continue
        if any(ch in e + g for ch in "@#|<>") or "http" in e.lower():
            continue
        if e[:60] in seen or g[:60] in seen:
            continue
        seen.add(e[:60])
        pairs.append((e, g))
        if len(pairs) >= limit_pool:
            break
    return pairs


def _clean(text):
    """Strip <think> scaffolding and take the first paragraph."""
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    text = text.strip().strip('"').strip()
    return text.split("\n\n")[0].strip()


def translate(url, model, text, api="chat"):
    """One EN->EL call. api='chat' uses /v1/chat/completions (llama.cpp);
    api='completions' uses /v1/completions for servers whose chat template
    only emits reasoning (e.g. MTP variants served via Ollama)."""
    if api == "completions":
        prompt = ("Translate the following English sentence to Greek. "
                  "Output ONLY the Greek translation.\n\n"
                  f"English: {text}\nGreek: <think>\n\n</think>\n\n")
        body = json.dumps({
            "model": model, "prompt": prompt,
            "temperature": 0.3, "max_tokens": 600,
        }).encode()
        path, extract = "/completions", lambda ch: ch.get("text")
    else:
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": PROMPT + text}],
            "temperature": 0.3,
            "max_tokens": 600,
            "chat_template_kwargs": {"enable_thinking": False},
        }).encode()
        path, extract = "/chat/completions", lambda ch: ch["message"].get("content")
    req = urllib.request.Request(
        url.rstrip("/") + path, data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = extract(json.load(r)["choices"][0])
    return _clean(raw or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model", default="qwen3.8-flash-next-unsloth-ud-q4_k_xl")
    ap.add_argument("--api", choices=["chat", "completions"], default="chat")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    pairs = fetch_pairs()
    rng = random.Random(args.seed)
    rng.shuffle(pairs)
    with open(args.out, "w", encoding="utf-8") as fh:
        for i, (e, g) in enumerate(pairs[:args.n]):
            try:
                llm = translate(args.url, args.model, e, api=args.api)
            except Exception as exc:
                llm = ""
                print(f"[{i}] error: {exc}")
            fh.write(json.dumps({"id": i, "en": e, "ref_el": g,
                                 "llm_el": llm}, ensure_ascii=False) + "\n")
            if (i + 1) % 10 == 0:
                print(f"{i + 1}/{args.n}", flush=True)
    print("wrote", args.out)


if __name__ == "__main__":
    main()

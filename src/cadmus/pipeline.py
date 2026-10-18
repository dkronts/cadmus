"""Stanza pipeline loading with the Greek lemma-model workaround."""

import os
import shlex
import subprocess

HORATIO_PATH = "/nlp/scr/horatio/stanza_resources/el/pretrain/conll17.pt"


def _try_apply_lemma_workaround():
    if os.path.exists(HORATIO_PATH):
        return
    import stanza

    home = os.path.expanduser("~/.cache/stanza")
    for root, _dirs, files in os.walk(home):
        if "conll17.pt" in files and root.endswith("el/pretrain"):
            real = os.path.join(root, "conll17.pt")
            try:
                os.makedirs(os.path.dirname(HORATIO_PATH), exist_ok=True)
                os.symlink(real, HORATIO_PATH)
                return
            except PermissionError:
                # sudo ln alone does not create parent directories
                target_dir = shlex.quote(os.path.dirname(HORATIO_PATH))
                subprocess.run(
                    ["sudo", "-n", "sh", "-c",
                     f"mkdir -p {target_dir} && "
                     f"ln -sf {shlex.quote(real)} {shlex.quote(HORATIO_PATH)}"],
                    check=False,
                )
                return


def load_pipeline(devices="cpu"):
    import stanza

    def _build():
        return stanza.Pipeline(
            "el",
            processors="tokenize,mwt,pos,lemma,depparse",
            verbose=False,
            devices=devices,
        )

    _try_apply_lemma_workaround()
    try:
        return _build()
    except FileNotFoundError as exc:
        if "conll17" not in str(exc):
            raise
        # first build on a fresh machine: stanza has now downloaded the el
        # resources, so the workaround can find conll17.pt — retry once
        _try_apply_lemma_workaround()
        try:
            return _build()
        except FileNotFoundError as exc2:
            if "conll17" in str(exc2):
                raise RuntimeError(
                    "Stanza Greek lemma model bug: checkpoint references "
                    f"{HORATIO_PATH}. Run scripts/fix_stanza_lemma.sh or see README."
                ) from exc2
            raise

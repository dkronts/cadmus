"""Valence rule: verb subcategorization frames mined from the treebank."""

from ..data import feats
from ..lexicon import CORE_DEPRELS, VerbFrames


def _is_obj_like(child):
    if child.deprel.split(":")[0] not in ("obj", "iobj"):
        return True
    return feats(child).get("Case", "Acc") != "Nom"


def verb_valence(sent, by_id, env):
    frames = env.get("frames")
    if frames is None:
        frames = env["frames"] = VerbFrames.load()
    out = []
    for w in sent.words:
        if w.upos != "VERB":
            continue
        children = [x for x in sent.words if x.head == w.id and _is_obj_like(x)]
        msg = frames.unexpected(w, children)
        if msg:
            out.append((w, w, msg))
    return out

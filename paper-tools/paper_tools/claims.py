"""Extract every cited sentence of a manuscript as a claim to audit (input for the claim-ref-audit skill)."""
from __future__ import annotations

import csv
import re

from . import text as T

# Cue words (English + Indonesian) for the claim type. The type only guides the reviewer; a person decides.
GAP = re.compile(r"\b(no (?:prior|previous|existing)|not yet|none of|first (?:to|time)|novel|for the first time|"
                 r"has not been|have not been|lack of|belum (?:ada|pernah)|pertama kali|satu-satunya|tidak ada)\b", re.I)
PRIOR = re.compile(r"\b(has been|have been|was|were|reported|showed|demonstrated|proposed|developed|found|"
                   r"telah|sudah|dilaporkan|menunjukkan|mengusulkan|menemukan)\b", re.I)
METHOD = re.compile(r"\b(following|according to|using the|we use[ds]?|method|procedure|protocol|scale|instrument|"
                    r"model of|mengikuti|menurut|menggunakan|metode|prosedur|instrumen|skala)\b", re.I)
NUMBER = re.compile(r"(?<![\w.])[-−]?\d+(?:[.,]\d+)?\s*(?:%|percent|persen|dB|Hz|kHz|MHz|GHz|ms|s\b|K\b|°C)?")
RECENT = re.compile(r"\b(recent(?:ly)?|state[- ]of[- ]the[- ]art|current|terkini|terbaru|baru-baru ini)\b", re.I)


def claim_type(sentence: str) -> str:
    stripped = T.strip_citations(sentence)
    if GAP.search(stripped):
        return "gap"
    if re.search(r"\d", stripped) and NUMBER.search(stripped):
        return "number"
    if METHOD.search(stripped):
        return "method"
    if PRIOR.search(stripped):
        return "prior-work"
    return "background"


def extract(manuscript_text: str):
    rows = []
    for s in T.sentences(manuscript_text):
        keys, style = T.citations(s.text)
        if not keys:
            continue
        rows.append({
            "id": "C%03d" % (len(rows) + 1),
            "section": s.section,
            "line": s.line,
            "type": claim_type(s.text),
            "recent_cue": bool(RECENT.search(s.text)),
            "keys": ";".join(keys),
            "n_keys": len(keys),
            "style": style,
            "sentence": s.text,
        })
    return rows


def write_csv(rows, path):
    fields = ["id", "section", "line", "type", "recent_cue", "keys", "n_keys", "style", "sentence",
              "verdict", "evidence", "fix"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "verdict": "", "evidence": "", "fix": ""})


def summary(rows) -> dict:
    by_type = {}
    for r in rows:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    return {
        "claims": len(rows),
        "by_type": by_type,
        "citation_dumps": [r["id"] for r in rows if r["n_keys"] >= 4],
        "recent_cues": [r["id"] for r in rows if r["recent_cue"]],
    }

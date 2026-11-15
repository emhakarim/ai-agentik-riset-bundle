"""Reading ledger: which cited works the authors actually read, and how deeply.

reads.csv columns: key, status, date, note
  status: full      the full text was read
          abstract  only the abstract / summary was read
          none      not read yet (cited from another paper, a search result, a suggestion)

The ledger is filled by people (or by the AI only for what it actually opened in this session, marked as such in
the note). It never changes a citation; it makes visible which claims rest on works nobody has read.
"""
from __future__ import annotations

import csv
import datetime as _dt
from pathlib import Path

from . import claims as C

STATUSES = ("full", "abstract", "none")
# Claim types where reading only the abstract is not enough to rely on the citation.
NEEDS_FULL = {"number", "method", "gap"}


def load(path) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return {r["key"]: r for r in csv.DictReader(fh) if r.get("key")}


def save(ledger: dict, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["key", "status", "date", "note"], lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        for k in sorted(ledger):
            w.writerow(ledger[k])


def mark(path, keys, status, note="", date=None):
    if status not in STATUSES:
        raise ValueError("status must be one of %s" % ", ".join(STATUSES))
    led = load(path)
    for k in keys:
        led[k] = {"key": k, "status": status, "date": date or _dt.date.today().isoformat(), "note": note}
    save(led, path)
    return led


def check(manuscript: str, ledger: dict):
    """Per cited key: its status; and the claims that need a full reading but rest on keys not read in full."""
    rows = C.extract(manuscript)
    keys = []
    for r in rows:
        for k in r["keys"].split(";"):
            if k and k not in keys:
                keys.append(k)
    status = {k: (ledger.get(k, {}).get("status") or "unknown") for k in keys}
    weak = []
    for r in rows:
        if r["type"] not in NEEDS_FULL:
            continue
        bad = [k for k in r["keys"].split(";") if status.get(k) != "full"]
        if bad:
            weak.append({"id": r["id"], "line": r["line"], "type": r["type"], "keys": bad,
                         "status": [status[k] for k in bad], "sentence": r["sentence"][:120]})
    counts = {s: sum(1 for v in status.values() if v == s) for s in STATUSES + ("unknown",)}
    return {"cited": len(keys), "counts": counts, "claims_needing_full_text": weak}

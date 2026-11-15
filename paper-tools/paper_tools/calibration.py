"""Calibrate a (simulated) review panel with planted flaws.

`seed` makes a copy of a manuscript with known flaws planted in it and writes an answer key (JSON). Run the review
on the seeded copy without showing the key, then `score` the review report against the key: which planted flaws were
found (recall), and how many findings the report made in total. Repeat on several manuscripts to see what kinds of
problems the panel misses.

Planted flaw types (each is a small, realistic change):
  number      a number in the results is changed (e.g. 0.45 -> 0.54)            -> must be caught as a wrong number
  overclaim   a hedge becomes a strong claim ("suggests" -> "proves")             -> overclaim
  citation    two citation keys are swapped between sentences                    -> citation does not support claim
  statement   a required statement section is removed (data availability ...)    -> missing statement
  causal      a correlational verb becomes causal ("is associated with" -> "causes")
"""
from __future__ import annotations

import json
import random
import re

from . import text as T

OVERCLAIM = [(r"\bsuggests?\b", "proves"), (r"\bmay\b", "will"), (r"\bindicates?\b", "demonstrates conclusively"),
             (r"\bmenunjukkan\b", "membuktikan"), (r"\bdapat\b", "pasti")]
CAUSAL = [(r"\bis associated with\b", "causes"), (r"\bwas associated with\b", "caused"),
          (r"\bare associated with\b", "cause"), (r"\bwere associated with\b", "caused"),
          (r"\bcorrelated with\b", "caused"), (r"\bberhubungan dengan\b", "menyebabkan"),
          (r"\bberkorelasi dengan\b", "menyebabkan")]
STATEMENT_HEAD = re.compile(r"^#{1,6}\s*(data availability|ketersediaan data|conflicts? of interest|"
                            r"konflik kepentingan|funding|pendanaan)\b.*$", re.I | re.M)
NUM = re.compile(r"(?<![\w.,])(\d+[.,]\d+)(?![\w])")

KEYWORDS = {
    "number": r"number|value|differ|inconsisten|mismatch|wrong|incorrect|angka|nilai|berbeda|tidak sesuai|salah",
    "overclaim": r"overclaim|overstat|too strong|prove|conclusive|klaim berlebih|terlalu kuat|membuktikan",
    "citation": r"citation|reference|cite|support|rujukan|sitasi|mendukung",
    "statement": r"statement|data availability|conflict|funding|pernyataan|ketersediaan data|konflik|pendanaan",
    "causal": r"causal|causation|correlation|cause|kausal|sebab|korelasi",
}


def _swap_digits(s: str, rng) -> str:
    digits = [i for i, c in enumerate(s) if c.isdigit()]
    if len(digits) >= 2:
        i, j = digits[-2], digits[-1]
        if s[i] != s[j]:
            lst = list(s)
            lst[i], lst[j] = lst[j], lst[i]
            return "".join(lst)
    i = digits[-1]
    return s[:i] + str((int(s[i]) + 3) % 10) + s[i + 1:]


def seed(text: str, kinds=("number", "overclaim", "citation", "statement", "causal"), seed_value: int = 1):
    """Return (seeded_text, key). key: list of {id, kind, line, before, after}."""
    rng = random.Random(seed_value)
    lines = text.splitlines()
    key = []

    def plant(kind, line_no, before, after):
        key.append({"id": "F%d" % (len(key) + 1), "kind": kind, "line": line_no + 1, "before": before,
                    "after": after})

    refs_head = re.compile(r"^#{1,6}\s*(references|bibliography|daftar pustaka|pustaka|referensi)\b", re.I)
    in_refs, body = False, []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("#"):
            in_refs = bool(refs_head.match(ln.strip()))
            continue
        # flaws go into the running text only: not into the reference list, tables, images or code
        if not in_refs and ln.strip() and not ln.lstrip().startswith(("|", "!", "```", "<!--")):
            body.append(i)
    if "number" in kinds:
        cands = [i for i in body if NUM.search(lines[i])]
        if cands:
            i = rng.choice(cands)
            m = rng.choice(list(NUM.finditer(lines[i])))
            new = _swap_digits(m.group(1), rng)
            lines[i] = lines[i][:m.start(1)] + new + lines[i][m.end(1):]
            plant("number", i, m.group(1), new)
    for kind, table in (("overclaim", OVERCLAIM), ("causal", CAUSAL)):
        if kind not in kinds:
            continue
        neg = re.compile(r"\b(not|no|never|cannot|tidak|belum|bukan|tak)\s+$", re.I)
        # skip negated hedges ("tidak dapat", "may not"): changing them does not make an overclaim
        cands = [(i, pat, rep, m) for i in body for pat, rep in table for m in re.finditer(pat, lines[i], re.I)
                 if not neg.search(lines[i][:m.start()]) and not re.match(r"\s+not\b", lines[i][m.end():], re.I)]
        if cands:
            i, pat, rep, m = rng.choice(cands)
            lines[i] = lines[i][:m.start()] + rep + lines[i][m.end():]
            plant(kind, i, m.group(0), rep)
    if "citation" in kinds:
        # only keys written literally in the line can be swapped (APA keys like Duflo_2001 are derived, not written)
        cited = [(i, [k for k in T.citations(lines[i])[0] if k in lines[i]]) for i in body]
        cited = [(i, k) for i, k in cited if k]
        if len(cited) >= 2:
            (i, ki), (j, kj) = rng.sample(cited, 2)
            a, b = ki[0], kj[0]
            if a != b:
                lines[i] = lines[i].replace(a, b, 1)
                lines[j] = lines[j].replace(b, a, 1)
                plant("citation", i, a, b)
                plant("citation", j, b, a)
    joined = "\n".join(lines)
    if "statement" in kinds:
        m = STATEMENT_HEAD.search(joined)
        if m:
            start = m.start()
            nxt = re.compile(r"^#{1,6}\s", re.M).search(joined, m.end())
            end = nxt.start() if nxt else len(joined)
            line_no = joined.count("\n", 0, start)
            plant("statement", line_no, m.group(0).strip(), "(removed)")
            joined = joined[:start] + joined[end:]
    return joined + ("\n" if text.endswith("\n") else ""), key


def score(report: str, key, window: int = 3):
    """A planted flaw counts as found when a report line names its line number (+-window) or quotes its changed
    text, and also uses words for that kind of problem."""
    from . import lint as L

    rlines = report.splitlines()
    found = []
    for k in key:
        hit = False
        if k["kind"] == "statement":
            # a removed statement is found when the report says it is missing, in any language
            heading = k["before"].lstrip("# ")
            pats = [p for p in L.STATEMENTS.values() if re.search(p, heading, re.I)]
            if any(re.search(p, ln, re.I) and re.search(r"missing|absent|no .{0,40}statement|tidak ada|belum ada|"
                                                         r"hilang|kurang", ln, re.I)
                   for p in pats for ln in rlines):
                found.append({**k, "found": True})
                continue
        for ln in rlines:
            near = any(abs(int(n) - k["line"]) <= window
                       for n in re.findall(r"(?:line|baris|l\.)\s*(\d+)", ln, re.I))
            quoted = (k["after"] != "(removed)" and k["after"].lower() in ln.lower()) or \
                     (k["kind"] == "statement" and re.search(re.escape(k["before"].lstrip("# ").split()[0]), ln, re.I))
            if (near or quoted) and re.search(KEYWORDS[k["kind"]], ln, re.I):
                hit = True
                break
        found.append({**k, "found": hit})
    by_kind = {}
    for f in found:
        d = by_kind.setdefault(f["kind"], [0, 0])
        d[0] += f["found"]
        d[1] += 1
    return {"planted": len(key), "found": sum(f["found"] for f in found),
            "recall": (sum(f["found"] for f in found) / len(key)) if key else None,
            "by_kind": {k: "%d/%d" % tuple(v) for k, v in by_kind.items()},
            "missed": [f for f in found if not f["found"]]}


def save_key(key, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(key, fh, ensure_ascii=False, indent=1)


def load_key(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

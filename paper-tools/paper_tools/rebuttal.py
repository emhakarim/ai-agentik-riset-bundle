"""Check a response-to-reviewers letter against the reviews and the revised manuscript.

- every reviewer point (ids such as R1.1, R2.3, E.1) has an answer in the letter;
- every place the letter points to (Section 3.2, Table 2, Figure 4 / Bagian, Tabel, Gambar) exists in the draft;
- every number with decimals quoted in the letter also appears in the draft.
"""
from __future__ import annotations

import re

from . import lint as L
from . import numbers as N

POINT_ID = re.compile(r"\b((?:R\d+|E|AE|EIC)\.\d+[a-z]?)\b")
ANSWER = re.compile(r"\b(response|reply|answer|tanggapan|jawaban|respons)\b", re.I)
SECTION_REF = re.compile(r"\b(?:Section|Sect\.|Bagian|Subbab|Bab)\s+(\d+(?:\.\d+)*)", re.I)
FLOAT_REF = re.compile(r"\b(Table|Tabel|Figure|Fig\.|Gambar)\s+(\d+)\b", re.I)
NUMBERED_HEADING = re.compile(r"^(?:#{1,6}\s*|\\(?:sub)*section\*?\{)\s*(\d+(?:\.\d+)*)\.?\s")


def point_ids(text: str):
    seen, out = set(), []
    for m in POINT_ID.finditer(text):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


def _blocks(letter: str):
    """Split the letter into {point_id: text until the next point id}."""
    marks = [(m.start(), m.group(1)) for m in POINT_ID.finditer(letter)]
    blocks = {}
    for i, (pos, pid) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(letter)
        blocks[pid] = blocks.get(pid, "") + letter[pos:end]
    return blocks


def check(reviews: str, letter: str, draft: str):
    ids = point_ids(reviews)
    blocks = _blocks(letter)
    unanswered = []
    for pid in ids:
        b = blocks.get(pid)
        if not b:
            unanswered.append({"id": pid, "why": "not in letter"})
            continue
        m = ANSWER.search(b)
        body = b[m.end():] if m else ""
        if not m or len(re.findall(r"\w+", body)) < 5:
            unanswered.append({"id": pid, "why": "no answer text"})
    extra = [p for p in blocks if p not in ids] if ids else []

    sections = set()
    for line in draft.splitlines():
        m = NUMBERED_HEADING.match(line.strip())
        if m:
            sections.add(m.group(1))
    defined = set()
    for line in draft.splitlines():
        m = L.FLOAT_DEF.match(line)
        if m:
            defined.add(L.float_key(m))
    bad_places = []
    for m in SECTION_REF.finditer(letter):
        if sections and m.group(1) not in sections:
            bad_places.append(m.group(0))
    for m in FLOAT_REF.finditer(letter):
        if (L.KIND[m.group(1).lower()], int(m.group(2))) not in defined:
            bad_places.append(m.group(0))

    draft_vals = []
    for n in N.manuscript_numbers(draft, ignore_small=-1):
        draft_vals += [v for v, _ in n["readings"]]
    missing_numbers = []
    for n in N.manuscript_numbers(letter, ignore_small=10 ** 9):
        if n["decimals"] == 0:
            continue
        if not any(N._matches(val, dec, False, v) for val, dec in n["readings"] for v in draft_vals):
            missing_numbers.append(n["raw"])
    return {"points": len(ids), "unanswered": unanswered, "ids_not_in_reviews": extra,
            "places_not_found": sorted(set(bad_places)), "numbers_not_in_draft": sorted(set(missing_numbers)),
            "numbered_sections_found": len(sections)}

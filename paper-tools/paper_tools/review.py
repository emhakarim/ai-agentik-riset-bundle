"""Validate a simulated-review report (from the journal-review-sim skill).

Rules checked:
- a combined decision is stated;
- sections A (fix now), B (author decisions) and C (new work) exist;
- every finding bullet carries a check mark: [checked ...] / [dicek ...] or [wrong] / [salah] (or [unchecked] /
  [belum dicek], which is reported);
- every C item says what is requested and from whom (request / permintaan / minta / ask).
"""
from __future__ import annotations

import re

DECISION = re.compile(r"(combined decision|editor'?s? decision|keputusan gabungan|keputusan editor)", re.I)
SECTION = re.compile(r"^#{1,6}\s*([ABC])[\.\s:)\-]", re.M)
FINDINGS_HEAD = re.compile(r"^#{1,6}\s*(findings|checked findings|temuan)", re.I)
MARK = re.compile(r"\[(checked|dicek|wrong|salah|unchecked|to check|belum dicek|perlu dicek)\b[^\]]*\]", re.I)
UNCHECKED = re.compile(r"\[(unchecked|to check|belum dicek|perlu dicek)", re.I)
REQUEST = re.compile(r"\b(request|requested|permintaan|minta|diminta|ask(?:ed)?)\b", re.I)


def _section_bullets(text: str, head_re):
    """Bullets under a matching heading, including its sub-headings (e.g. one ### per reviewer)."""
    out, inside, level = [], False, 0
    for line in text.splitlines():
        h = re.match(r"^(#{1,6})\s", line)
        if h:
            depth = len(h.group(1))
            if head_re.match(line):
                inside, level = True, depth
            elif not inside or depth <= level:
                inside = False
            continue
        if inside and re.match(r"^\s*[-*]\s+\S", line) and not line.startswith("  "):
            out.append(line.strip())
    return out


def check(report: str):
    sections = set(SECTION.findall(report))
    findings = _section_bullets(report, FINDINGS_HEAD)
    no_mark = [f[:100] for f in findings if not MARK.search(f)]
    unchecked = [f[:100] for f in findings if UNCHECKED.search(f)]
    c_items = _section_bullets(report, re.compile(r"^#{1,6}\s*C[\.\s:)\-]"))
    c_no_request = [c[:100] for c in c_items if not REQUEST.search(c)]
    return {
        "has_decision": bool(DECISION.search(report)),
        "sections_missing": [s for s in "ABC" if s not in sections],
        "findings": len(findings),
        "findings_without_mark": no_mark,
        "findings_unchecked": unchecked,
        "c_items": len(c_items),
        "c_items_without_request": c_no_request,
    }

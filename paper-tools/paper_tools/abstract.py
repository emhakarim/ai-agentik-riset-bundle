"""Abstract checks: word limits, required parts, and the same numbers in both language versions and in the body.

A bilingual abstract (e.g. Indonesian + English for SINTA journals) must carry the same numbers; an abstract must not
contain a number that the body does not.
"""
from __future__ import annotations

import re

from . import numbers as N

HEAD = re.compile(r"^\s*(?:#{1,6}\s*|\\section\*?\{|\*\*)?\s*(abstract|abstrak|summary|ringkasan)\b", re.I)
NEXT_HEAD = re.compile(r"^\s*(?:#{1,6}\s+\S|\\section)")
KEYWORDS = re.compile(r"^\s*(?:\*\*|_)?\s*(keywords|kata kunci|key words)\b", re.I)
PARTS = {  # structured-abstract parts; English + Indonesian names
    "background": r"background|introduction|latar belakang|pendahuluan|purpose|objective|aims?|tujuan",
    "methods": r"methods?|design|metode|desain",
    "results": r"results?|findings|hasil|temuan",
    "conclusion": r"conclusions?|implications?|simpulan|kesimpulan|implikasi",
}


def find_abstracts(text: str):
    """Return [(heading, body)] for each abstract-like section (stops at the next heading or the keywords line)."""
    out, cur, head = [], None, None
    for line in text.splitlines():
        m = HEAD.match(line)
        if m:
            if cur is not None:
                out.append((head, "\n".join(cur).strip()))
            head, cur = m.group(1), []
            rest = line[m.end():].strip(" *:}.")
            if rest:
                cur.append(rest)
            continue
        if cur is not None and (NEXT_HEAD.match(line) or KEYWORDS.match(line)):
            out.append((head, "\n".join(cur).strip()))
            cur = None
            continue
        if cur is not None:
            cur.append(line)
    if cur is not None:
        out.append((head, "\n".join(cur).strip()))
    return out


def words(text: str) -> int:
    return len(re.findall(r"\w+(?:[-'’]\w+)*", re.sub(r"\$[^$]*\$", " M ", text)))


def _values(text: str):
    rows = N.manuscript_numbers("# A\n\n" + text, ignore_small=-1)
    return [r for r in rows if not (r["decimals"] == 0 and not r["percent"] and 1900 <= r["value"] <= 2100)]


def _found(row, values) -> bool:
    return any(N._matches(val, dec, row["percent"], v) or N._matches(v, dec, False, val)
               for val, dec in row["readings"] for v in values)


def numbers_missing(src: str, dst: str):
    """Numbers written in `src` that do not appear (at the written precision) in `dst`."""
    dst_vals = []
    for r in _values(dst):
        dst_vals += [v for v, _ in r["readings"]]
        if r["percent"]:
            dst_vals += [v / 100 for v, _ in r["readings"]]
    return [r["raw"] for r in _values(src) if not _found(r, dst_vals)]


def parts_present(text: str):
    # a part label is a word followed by a colon ("Methods:", "**Hasil:**"), at the start or after a sentence
    return {k: bool(re.search(r"(?:^|[\s*.;])(?:%s)\s*\**\s*:" % pat, text, re.I)) for k, pat in PARTS.items()}


def check(manuscript: str, max_words=None, other_language: str = None, structured=False):
    abstracts = find_abstracts(manuscript)
    body = manuscript
    for _, a in abstracts:
        body = body.replace(a, " ")
    report = {"abstracts": []}
    for head, a in abstracts:
        item = {"heading": head, "words": words(a), "over_limit": bool(max_words and words(a) > max_words),
                "numbers_not_in_body": numbers_missing(a, body)}
        if structured:
            item["parts_missing"] = [k for k, ok in parts_present(a).items() if not ok]
        report["abstracts"].append(item)
    texts = [a for _, a in abstracts]
    if other_language is not None:
        texts.append(other_language)
    if len(texts) >= 2:
        first, second = texts[0], texts[1]
        report["language_versions"] = {
            "only_in_first": numbers_missing(first, second),
            "only_in_second": numbers_missing(second, first),
        }
    return report

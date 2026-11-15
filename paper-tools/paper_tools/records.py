"""Read bibliographic database exports into screening records (id, title, abstract, doi, year, authors, journal,
source): RIS (Scopus, Zotero, EndNote, Mendeley), PubMed MEDLINE/.nbib, Web of Science plain text, and CSV.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

RIS_TAG = re.compile(r"^([A-Z][A-Z0-9])  - ?(.*)$")
NBIB_TAG = re.compile(r"^([A-Z]{2,4})\s*- (.*)$")
WOS_TAG = re.compile(r"^([A-Z][A-Z0-9]) (.*)$")


def _year(s):
    m = re.search(r"(1[89]|20)\d{2}", s or "")
    return m.group(0) if m else ""


def _finish(rec, source, n):
    rec.setdefault("id", "%s-%d" % (source, n))
    for k in ("title", "abstract", "doi", "year", "authors", "journal"):
        rec.setdefault(k, "")
    rec["source"] = source
    rec["doi"] = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", rec["doi"].strip(), flags=re.I)
    return rec


def read_ris(text, source="ris"):
    out, rec, last = [], {}, None
    authors = []
    for line in text.splitlines():
        m = RIS_TAG.match(line)
        if not m:
            if last and line.strip() and rec.get(last) is not None:
                rec[last] += " " + line.strip()
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "TY":
            rec, authors, last = {}, [], None
        elif tag == "ER":
            rec["authors"] = "; ".join(authors)
            out.append(_finish(rec, source, len(out) + 1))
            rec, authors, last = {}, [], None
            continue
        elif tag in ("TI", "T1") and not rec.get("title"):
            rec["title"], last = val, "title"
        elif tag in ("AB", "N2") and not rec.get("abstract"):
            rec["abstract"], last = val, "abstract"
        elif tag == "DO":
            rec["doi"] = val
        elif tag in ("PY", "Y1", "DA") and not rec.get("year"):
            rec["year"] = _year(val)
        elif tag in ("AU", "A1"):
            authors.append(val)
        elif tag in ("T2", "JO", "JF") and not rec.get("journal"):
            rec["journal"] = val
        elif tag == "ID" and val:
            rec["id"] = val
        else:
            last = None
    return out


def read_nbib(text, source="pubmed"):
    out = []
    for block in re.split(r"\n\s*\n(?=PMID-)", text.strip()):
        rec, last, authors = {}, None, []
        for line in block.splitlines():
            m = NBIB_TAG.match(line)
            if m:
                tag, val = m.group(1), m.group(2).strip()
                last = None
                if tag == "PMID":
                    rec["id"] = "PMID" + val
                elif tag == "TI":
                    rec["title"], last = val, "title"
                elif tag == "AB":
                    rec["abstract"], last = val, "abstract"
                elif tag == "DP":
                    rec["year"] = _year(val)
                elif tag == "AU":
                    authors.append(val)
                elif tag == "JT":
                    rec["journal"] = val
                elif tag in ("LID", "AID") and "[doi]" in val:
                    rec["doi"] = val.replace("[doi]", "").strip()
            elif last and line.startswith("      "):
                rec[last] += " " + line.strip()
        if rec:
            rec["authors"] = "; ".join(authors)
            out.append(_finish(rec, source, len(out) + 1))
    return out


def read_wos(text, source="wos"):
    out, rec, last, authors = [], None, None, []
    for line in text.splitlines():
        if line.startswith("PT ") and rec is None:
            rec, authors, last = {}, [], None
            continue
        if rec is None:
            continue
        if line.startswith("ER"):
            rec["authors"] = "; ".join(authors)
            out.append(_finish(rec, source, len(out) + 1))
            rec, last = None, None
            continue
        if line.startswith("   ") and last:
            if last == "authors":
                authors.append(line.strip())
            else:
                rec[last] += " " + line.strip()
            continue
        m = WOS_TAG.match(line)
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        last = {"TI": "title", "AB": "abstract", "AU": "authors"}.get(tag)
        if tag == "TI":
            rec["title"] = val
        elif tag == "AB":
            rec["abstract"] = val
        elif tag == "AU":
            authors.append(val)
        elif tag == "DI":
            rec["doi"] = val
        elif tag == "PY":
            rec["year"] = _year(val)
        elif tag == "SO":
            rec["journal"] = val
        elif tag == "UT":
            rec["id"] = val
    return out


def read_csv_records(path, source="csv"):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for i, r in enumerate(rows, 1):
        low = {k.strip().lower(): (v or "") for k, v in r.items() if k}
        rec = {"id": low.get("id") or low.get("eid") or low.get("pmid") or "",
               "title": low.get("title", ""), "abstract": low.get("abstract", ""),
               "doi": low.get("doi", ""), "year": _year(low.get("year", "")),
               "authors": low.get("authors", "") or low.get("author", ""),
               "journal": low.get("source title", "") or low.get("journal", "")}
        if not rec["id"]:
            del rec["id"]
        out.append(_finish(rec, source, i))
    return out


def read_any(path, source=None):
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    suf = p.suffix.lower()
    name = source or p.stem
    if suf == ".csv":
        return read_csv_records(p, name)
    if suf in (".ris",) or re.search(r"^TY  - ", text, re.M):
        return read_ris(text, name)
    if suf in (".nbib", ".medline") or re.search(r"^PMID- ", text, re.M):
        return read_nbib(text, name)
    if re.search(r"^PT [A-Z]", text, re.M) and re.search(r"^ER\s*$", text, re.M):
        return read_wos(text, name)
    raise ValueError("unknown export format: %s (use RIS, PubMed .nbib, WoS plain text or CSV)" % path)


def merge(paths):
    """Read several exports; prefix ids with the source when they would collide."""
    all_recs, seen = [], set()
    for p in paths:
        for r in read_any(p):
            rid = r["id"]
            if rid in seen:
                r["id"] = "%s:%s" % (r["source"], rid)
            seen.add(r["id"])
            all_recs.append(r)
    return all_recs

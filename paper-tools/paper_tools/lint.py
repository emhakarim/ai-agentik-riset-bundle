"""Manuscript checks that need no network: placeholders, citations vs bibliography, tables/figures, required
statements, reference recency and long sentences."""
from __future__ import annotations

import datetime as _dt
import re
import unicodedata

from . import bib as B
from . import text as T

PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME|XXX+|Lorem ipsum)\b|\?\?\?+|\[(citation needed|cite|ref|refs|CITE|REF|"
                         r"rujukan|sitasi|kutipan)\]|\{\{[^}]*\}\}|\bX\.XX\b|\bxx(?:\.x+)?\s*%", re.I)
# A caption: "**Table 1.**", "*Figure 2*", "![Figure 3: ...]", or a line starting "Table 1." / "Table 1:" / "Table 1 |".
FLOAT_DEF = re.compile(r"^\s*(?:(?:\*\*|\*|!\[)\s*(Table|Tabel|Figure|Fig\.|Gambar)\s+(\d+)\b"
                       r"|(Table|Tabel|Figure|Fig\.|Gambar)\s+(\d+)\s*[.:|–—-])", re.I)
FLOAT_REF = re.compile(r"\b(Table|Tabel|Figure|Fig\.|Gambar)\s+(\d+)\b", re.I)
REF_SECTIONS = re.compile(r"^(references|bibliography|daftar pustaka|pustaka|referensi)", re.I)
KIND = {"table": "table", "tabel": "table", "figure": "figure", "fig.": "figure", "gambar": "figure"}

# Statements many journals require; each is a set of heading / lead-in alternatives (English + Indonesian).
STATEMENTS = {
    "conflict_of_interest": r"conflicts? of interest|competing interests?|declaration of interest|konflik kepentingan",
    "funding": r"funding|financial support|acknowledg|pendanaan|ucapan terima kasih",
    "data_availability": r"data(\s*(and|or|/|&)\s*code)?\s+availability|availability of (data|code)|"
                         r"ketersediaan data",
    "ai_use": r"(use of )?(generative )?ai\b|artificial intelligence|ai[- ]assisted|penggunaan ai|kecerdasan buatan",
    "author_contributions": r"author contributions?|credit authorship|kontribusi penulis",
    "ethics": r"ethic|informed consent|etika|persetujuan",
}
PROFILES = {
    "general": ["conflict_of_interest", "funding", "data_availability", "ai_use"],
    "health": ["conflict_of_interest", "funding", "data_availability", "ai_use", "ethics", "author_contributions"],
    "education": ["conflict_of_interest", "funding", "data_availability", "ai_use", "ethics"],
    "none": [],
}


def placeholders(text: str):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in PLACEHOLDER.finditer(line):
            out.append({"line": n, "match": m.group(0), "context": line.strip()[:160]})
    return out


def cited_keys(text: str):
    keys, styles = [], set()
    for s in T.sentences(text):
        k, style = T.citations(s.text)
        keys += k
        if style:
            styles.add(style)
    seen, ordered = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered, styles


def _norm_name(s: str) -> str:
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", s).lower())


def _first_surname(entry: dict) -> str:
    first = re.split(r"\s+and\s+", entry.get("author", "") or "")[0].strip(" {}")
    if not first:
        return ""
    return first.split(",")[0] if "," in first else first.split()[-1]


def resolve(keys, entries: dict):
    """Map APA-style keys (Surname_Year, from 'Duflo (2001)') to the bibliography's own keys by first author and
    year; keys already in the bibliography, numbers and unmatched keys are returned unchanged."""
    if not entries:
        return list(keys)
    index = {}
    for k, e in entries.items():
        y, sn = B.year(e), _norm_name(_first_surname(e))
        if y and sn:
            index.setdefault((sn, str(y)), []).append(k)
    for cands in index.values():  # APA letters a, b, c follow the reference list order: by title
        cands.sort(key=lambda k: (_norm_name(entries[k].get("title", "")), k))
    out = []
    for k in keys:
        m = re.match(r"^(.+)_(\d{4})([a-z]?)$", k)
        if k in entries or not m:
            out.append(k)
            continue
        cands = index.get((_norm_name(m.group(1)), m.group(2)), [])
        i = ord(m.group(3)) - ord("a") if m.group(3) else 0
        out.append(cands[i] if i < len(cands) else k)
    return out


def citations_vs_bib(text: str, entries: dict):
    keys, styles = cited_keys(text)
    keys = resolve(keys, entries)
    named = [k for k in keys if not k.isdigit()]
    return {
        "styles": sorted(styles),
        "cited": len(keys),
        "missing_in_bib": [k for k in named if k not in entries] if entries else [],
        "uncited_in_bib": [k for k in entries if k not in set(keys)] if entries and named else [],
    }


def float_key(m):
    """(kind, number) from a FLOAT_DEF match (either alternative)."""
    word, num = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    return KIND[word.lower()], int(num)


def floats(text: str):
    defined, referenced = {}, {}
    for n, line in enumerate(text.splitlines(), 1):
        m = FLOAT_DEF.match(line)
        if m:
            defined.setdefault(float_key(m), n)
            rest = line[m.end():]
        else:
            rest = line
        for r in FLOAT_REF.finditer(rest):
            referenced.setdefault((KIND[r.group(1).lower()], int(r.group(2))), n)
    # LaTeX: \label{tab:x} / \ref{tab:x}
    labels = set(re.findall(r"\\label\{([^}]+)\}", text))
    refs = set(re.findall(r"\\(?:auto|c|C|eq)?ref\{([^}]+)\}", text))
    return {
        "undefined": [{"kind": k, "number": i, "line": ln} for (k, i), ln in sorted(referenced.items())
                      if (k, i) not in defined],
        "unreferenced": [{"kind": k, "number": i, "line": ln} for (k, i), ln in sorted(defined.items())
                         if (k, i) not in referenced],
        "latex_missing_labels": sorted(refs - labels),
    }


def statements(text: str, profile="general"):
    wanted = list(profile) if isinstance(profile, (list, tuple)) else PROFILES.get(profile, [])
    heads = []
    for line in text.splitlines():
        st = line.strip()
        m = T.HEADING_MD.match(st) or T.HEADING_TEX.match(st)
        if m:
            heads.append(m.group(m.lastindex))
            continue
        b = re.match(r"^\*\*([^*]{3,80})\*\*|^\\(?:paragraph|textbf)\{([^}]{3,80})\}", st)
        if b:
            heads.append(b.group(1) or b.group(2))
    missing = [w for w in wanted if not any(re.search(STATEMENTS[w], h, re.I) for h in heads)]
    return {"profile": profile, "required": wanted, "missing": missing}


def recency(text: str, entries: dict, years: int = 5, minimum: float = 0.0, as_of=None):
    """Share of cited references published from (as_of - years) to as_of, both included.

    This is how journals usually phrase "the last 5 years" when the submission year is current: for a 2026
    submission and years=5 the window is 2021-2026. Use years=4 for a strict five-calendar-year window (2022-2026).
    """
    as_of = as_of or _dt.date.today().year
    keys, _ = cited_keys(text)
    named = list(dict.fromkeys(k for k in resolve(keys, entries) if k in entries))
    ys = [B.year(entries[k]) for k in named]
    known = [y for y in ys if y]
    recent = [y for y in known if y >= as_of - years]
    share = (len(recent) / len(known)) if known else None
    return {"as_of": as_of, "window_years": years, "references": len(named), "with_year": len(known),
            "recent": len(recent), "share": share, "minimum": minimum,
            "ok": (share is None or share >= minimum)}


def long_sentences(text: str, limit: int = 40):
    out = []
    for s in T.sentences(text):
        if FLOAT_DEF.match(s.text) or REF_SECTIONS.match(s.section or ""):  # captions and references may be long
            continue
        plain = re.sub(r"\[[^\]]*\]|\$[^$]*\$|\\\(.*?\\\)", " M ", s.text)  # citations out, inline math = 1 word
        words = len(re.findall(r"\w+", plain))
        if words > limit:
            out.append({"line": s.line, "words": words, "start": s.text[:90]})
    return out

"""A small, tolerant BibTeX reader (no dependencies). Good enough for checks; not a full BibTeX implementation."""
from __future__ import annotations

import re
from pathlib import Path

ENTRY = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.S)


def _value(s: str, i: int):
    """Read one field value starting at s[i] ({...}, "..." or bare word); return (value, next_index)."""
    while i < len(s) and s[i] in " \t\r\n":
        i += 1
    if i >= len(s):
        return "", i
    if s[i] == "{":
        depth, j = 0, i
        while j < len(s):
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
                if depth == 0:
                    return s[i + 1:j], j + 1
            j += 1
        return s[i + 1:], len(s)
    if s[i] == '"':
        j = i + 1
        while j < len(s) and not (s[j] == '"' and s[j - 1] != "\\"):
            j += 1
        return s[i + 1:j], j + 1
    m = re.match(r"[^,}\s]+", s[i:])
    return (m.group(0), i + len(m.group(0))) if m else ("", i)


def parse(text: str) -> dict:
    """Return {key: {"type": ..., field: value}} with lower-case field names; later duplicates win."""
    return _scan(text)[0]


def issues(text: str) -> list:
    """Problems that make entries silently disappear or lose fields: duplicate keys, unreadable entries."""
    return _scan(text)[1]


def load_issues(*paths) -> list:
    out = []
    for p in paths:
        for it in issues(Path(p).read_text(encoding="utf-8", errors="replace")):
            out.append({**it, "file": str(p)})
    return out


def _scan(text: str):
    out, problems, seen = {}, [], {}
    for m in ENTRY.finditer(text):
        etype, key = m.group(1).lower(), m.group(2)
        if etype in ("comment", "preamble", "string"):
            continue
        i, fields = m.end(), {"type": etype}
        while i < len(text):
            fm = re.compile(r"\s*([A-Za-z][\w\-]*)\s*=\s*").match(text, i)
            if not fm:
                break
            val, i = _value(text, fm.end())
            fields[fm.group(1).lower()] = " ".join(val.split())
            sep = re.compile(r"\s*,?\s*").match(text, i)
            i = sep.end()
            if i < len(text) and text[i] == "}":
                break
        line = text.count("\n", 0, m.start()) + 1
        if i < len(text) and text[i] != "}":
            problems.append({"key": key, "line": line,
                             "problem": "unreadable text in entry; fields after it are lost: %r" % text[i:i + 40]})
        elif len(fields) == 1:
            problems.append({"key": key, "line": line, "problem": "no fields read"})
        if key in seen:
            problems.append({"key": key, "line": line,
                             "problem": "duplicate key (also on line %d); the later entry replaces the earlier one"
                                        % seen[key]})
        seen.setdefault(key, line)
        out[key] = fields
    return out, problems


def load(*paths) -> dict:
    """Merge several .bib files; later files override earlier ones (like an overrides file)."""
    merged = {}
    for p in paths:
        merged.update(parse(Path(p).read_text(encoding="utf-8", errors="replace")))
    return merged


def year(entry: dict):
    m = re.search(r"\d{4}", entry.get("year", "") or entry.get("date", ""))
    return int(m.group(0)) if m else None


def doi(entry: dict):
    d = entry.get("doi", "").strip()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", d, flags=re.I)
    return d or None

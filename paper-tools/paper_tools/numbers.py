"""Trace every number in a manuscript to the analysis outputs it should come from.

A number in the text is "traced" when some source file (CSV, TSV, JSON, Markdown, TXT, LaTeX table) contains a value
that rounds to it at the precision written in the text (also as a percentage of a fraction). Untraced numbers are not
necessarily wrong, but each one needs a reason: a constant, a design choice, a value from the literature, ...
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import text as T

REF_SECTIONS = re.compile(r"^(references|bibliography|daftar pustaka|pustaka|referensi|acknowledg|ucapan terima)",
                          re.I)
# Numbers that are labels, not results: "Table 3", "Section 2.1", "Fig. 4", "Eq. (5)", "H1", "Q2", "n = ..." stays.
LABEL = re.compile(r"(?:Table|Tabel|Figure|Fig\.|Gambar|Section|Bagian|Subbab|Bab|Chapter|Eq\.|Equation|Persamaan|"
                   r"Appendix|Lampiran|Step|Langkah|Stage|Tahap|Phase|Fase|Item|Butir|Hypothesis|Hipotesis|Model|"
                   r"Paper|Study|Studi|Version|Versi|v)\s*\(?[A-Z]?\d+(?:\.\d+)*\)?", re.I)
NUM = re.compile(r"(?<![\w.,])([-−+]?\d{1,3}(?:[.,  ]\d{3})+(?:[.,]\d+)?|[-−+]?\d+(?:[.,]\d+)?"
                 r"|(?<=[\s=<>(\[])[-−+]?\.\d+)"  # APA style without a leading zero: p = .003
                 r"(?![\w])(\s*%)?")
SOURCE_SUFFIX = {".csv", ".tsv", ".json", ".md", ".txt", ".tex", ".dat"}


def _as(s: str, decimal: str):
    thousands = "." if decimal == "," else ","
    t = s.replace(thousands, "")
    if decimal == ",":
        t = t.replace(",", ".")
    try:
        return float(t), (len(t.split(".")[1]) if "." in t else 0)
    except ValueError:
        return None


def parse_number(raw: str, decimal: str = "auto"):
    """Return the possible readings [(value, decimals), ...] of a number as written.

    Handles 1,234.5 / 1.234,5 / 0,085 / 12 345. With decimal="auto" an ambiguous number such as 1,234 or 1.234
    (one separator followed by exactly three digits) gives both readings; any reading may match a source value.
    """
    s = raw.replace("−", "-").replace(" ", "").replace(" ", "").lstrip("+")
    if decimal in (".", ","):
        r = _as(s, decimal)
        return [r] if r else []
    has_c, has_d = "," in s, "." in s
    if has_c and has_d:
        r = _as(s, "," if s.rfind(",") > s.rfind(".") else ".")
        return [r] if r else []
    sep = "," if has_c else ("." if has_d else None)
    if sep is None:
        r = _as(s, ".")
        return [r] if r else []
    if s.count(sep) > 1:  # 1.234.567 or 1,234,567: the separator groups thousands
        r = _as(s, "," if sep == "." else ".")
        return [r] if r else []
    head, tail = s.lstrip("-").split(sep)
    readings = [_as(s, sep)]
    if len(tail) == 3 and head not in ("", "0"):
        readings.append(_as(s, "," if sep == "." else "."))
    return [r for r in readings if r]


def manuscript_numbers(text: str, ignore_small: int = 12, decimal: str = "auto"):
    rows = []
    in_refs = False
    for s in T.sentences(text):
        in_refs = bool(REF_SECTIONS.match(s.section or "")) if s.section else in_refs
        if in_refs:
            continue
        clean = s.text.replace("{,}", ",").replace("{.}", ".")  # LaTeX decimal comma: 1{,}44
        clean = re.sub(r"\\times\s*10\^\{?[-\u2212]?\d+\}?|10\^\{?[-\u2212]?\d+\}?|\^\{?\d+\}?|_\{?\d+\}?", " ", clean)
        clean = LABEL.sub(" ", clean)
        clean = re.sub(r"\[[^\]]*\]|\\\w*cite\w*\{[^}]*\}|\(([A-Z][^()]*?,\s*)?(19|20)\d{2}[a-z]?\)", " ", clean)
        clean = re.sub(r"https?://\S+|doi:\S+|10\.\d{4,}/\S+", " ", clean)
        for m in NUM.finditer(clean):
            readings = parse_number(m.group(1), decimal)
            if not readings:
                continue
            value, decimals = readings[0]
            is_pct = bool(m.group(2))
            if len(readings) == 1 and decimals == 0 and not is_pct and (
                    abs(value) <= ignore_small or 1900 <= value <= 2100):
                continue
            rows.append({"section": s.section, "line": s.line, "raw": m.group(0).strip(), "value": value,
                         "decimals": decimals, "readings": readings, "percent": is_pct, "sentence": s.text})
    return rows


def _walk_json(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            _walk_json(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_json(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append(float(obj))
    elif isinstance(obj, str):
        out.extend(_numbers_in_text(obj))


def _numbers_in_text(s: str):
    vals = []
    for m in re.finditer(r"[-−]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s):
        try:
            vals.append(float(m.group(0).replace("−", "-")))
        except ValueError:
            pass
    return vals


def source_values(paths):
    """Collect every numeric value from the given files / folders (recursive), with the file each came from."""
    values = []
    files = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*")) if f.is_file() and f.suffix.lower() in SOURCE_SUFFIX]
        elif p.is_file():
            files.append(p)
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="replace")
        found = []
        if f.suffix.lower() == ".json":
            try:
                _walk_json(json.loads(txt), found)
            except json.JSONDecodeError:
                found = _numbers_in_text(txt)
        else:
            found = _numbers_in_text(txt)
        values += [(v, str(f)) for v in found]
    return values


def _matches(target: float, decimals: int, percent: bool, v: float, signed: bool = True) -> bool:
    """A source value rounds to the manuscript number. signed=False ignores the sign, used only to flag a sign
    flip (source r = -0.45, manuscript r = 0.45): such a number is reported, never counted as traced."""
    tol = 0.5 * 10 ** -decimals + 1e-12
    f = (lambda x: x) if signed else abs
    if abs(f(v) - f(target)) <= tol:
        return True
    if percent and abs(f(v * 100) - f(target)) <= tol:
        return True
    return False


def trace(manuscript_text: str, sources, ignore_small: int = 12, decimal: str = "auto"):
    nums = manuscript_numbers(manuscript_text, ignore_small, decimal)
    vals = source_values(sources)
    for n in nums:
        hit = next((f for v, f in vals for val, dec in n["readings"] if _matches(val, dec, n["percent"], v)), None)
        flip = None
        if hit is None:  # same size, opposite sign: a reversed effect direction must never pass as traced
            flip = next((f for v, f in vals for val, dec in n["readings"]
                         if val != 0 and _matches(val, dec, n["percent"], v, signed=False)), None)
        n["traced"] = hit is not None
        n["sign_flipped"] = flip is not None
        n["source"] = hit or flip or ""
    return nums

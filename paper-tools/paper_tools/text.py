"""Read a manuscript (Markdown or LaTeX) and split it into sections and sentences.

Everything here is local and deterministic: no network, no model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Citation syntaxes we recognise:
#   pandoc   [@key], [@key1; @key2, p. 4], @key
#   LaTeX    \cite{a,b}, \citep{a}, \citet[p.~3]{a}, \parencite{a}, \textcite{a}, \autocite{a}
#   bracket  [key] or [key1, key2] where key looks like author2020word
#   numeric  [1], [2, 3], [4-6]
#   APA      (Duflo, 2001), (Card & Krueger, 1996), (Glewwe dkk., 2011; Duflo, 2001, p. 5), Duflo (2001),
#            Sumida dan Kawata (2021), Glewwe et al. (2011). Keys become Surname_Year (e.g. Espinosa_Andrade_2024),
#            the form Crossref uses for BibTeX keys; lint.resolve() also matches them by first author and year.
CITE_PANDOC = re.compile(r"\[(?P<body>[^\[\]]*@[^\[\]]+)\]")
_UP = "A-ZÀ-Þ"
_NAME = r"[%s][\wÀ-ɏ'’\-]+" % _UP
CITE_APA_PAREN = re.compile(r"\(([^()]*?\b(?:\d{4}[a-z]?|n\.d\.)[^()]*)\)")
APA_PART = re.compile(r"^\s*(?:(?:e\.g\.|mis\.|misalnya|lihat|see|cf\.|bdk\.)\s*,?\s+)?"
                      r"(?P<auth>[%s][^;()\d=]*?)\s*,\s*(?P<year>\d{4}[a-z]?|n\.d\.)"
                      r"(?:\s*,\s*(?:p|pp|hlm|h|para)\.?\s*[\d–\-]+)?\s*$" % _UP)
CITE_APA_NARR = re.compile(r"(?<![\w(])(?P<auth>%s(?:\s+%s)?(?:\s+(?:&|dan|and)\s+%s|\s+(?:dkk\.|et al\.))?)"
                           r"\s+\((?P<year>\d{4}[a-z]?)\)" % (_NAME, _NAME, _NAME))
_FIRST_AUTHOR_SPLIT = re.compile(r"\s+(?:&|dan|and)\s+|\s+(?:dkk|et al)\.?|,")
# sentence words that can stand before a narrative citation and are not part of the author name
_LEAD_WORDS = {"menurut", "penelitian", "studi", "kajian", "hasil", "temuan", "dalam", "pada", "oleh", "laporan",
               "according", "in", "the", "as", "see", "lihat", "seperti", "sebagaimana", "following", "mengikuti"}
CITE_PANDOC_KEY = re.compile(r"@([A-Za-z0-9_:\-.]+[A-Za-z0-9_])")
CITE_LATEX = re.compile(r"\\(?:[a-zA-Z]*cite[a-zA-Z]*)\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}")
CITE_BRACKET = re.compile(r"\[((?:[A-Za-z][A-Za-z\-]*\d{4}[A-Za-z0-9]*)(?:\s*[,;]\s*[A-Za-z][A-Za-z\-]*\d{4}[A-Za-z0-9]*)*)\]")
CITE_NUMERIC = re.compile(r"\[(\d+(?:\s*[-\u2013,]\s*\d+)*)\]")

HEADING_MD = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
HEADING_TEX = re.compile(r"^\\(?:sub)*section\*?\{(.*)\}")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\u00C0-\u024F\[\(\"'0-9])")
ABBREV = ("e.g.", "i.e.", "et al.", "Fig.", "Eq.", "Ref.", "vs.", "cf.", "No.", "dkk.", "mis.", "yaitu.", "Tab.", "pp.",
          "p.", "Vol.", "approx.", "resp.")


@dataclass
class Sentence:
    section: str
    line: int
    text: str


def read(path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _strip_blocks(text: str) -> str:
    """Blank out code blocks, display math, HTML comments and LaTeX comments, keeping line numbers."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"```.*?```", blank, text, flags=re.S)
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    text = re.sub(r"\$\$.*?\$\$", blank, text, flags=re.S)
    text = re.sub(r"\\begin\{(equation|align|eqnarray|verbatim|lstlisting)\*?\}.*?\\end\{\1\*?\}", blank, text,
                  flags=re.S)
    text = re.sub(r"(?m)(?<!\\)%.*$", lambda m: " " * len(m.group(0)), text) if "\\begin{document}" in text else text
    return text


def sentences(text: str):
    """Yield Sentence objects with the current section heading and the line where the sentence starts."""
    text = _strip_blocks(text)
    section = ""
    para, start = [], 0
    out = []

    def flush():
        if not para:
            return
        block = " ".join(s.strip() for s in para)
        protected = block
        for i, ab in enumerate(ABBREV):
            protected = protected.replace(ab, ab.replace(".", "\u2024"))
        for s in SENT_SPLIT.split(protected):
            s = s.replace("\u2024", ".").strip()
            if s:
                out.append(Sentence(section, start, s))

    for n, line in enumerate(text.splitlines(), 1):
        m = HEADING_MD.match(line) or HEADING_TEX.match(line.strip())
        if m:
            flush()
            para = []
            section = (m.group(2) if m.re is HEADING_MD else m.group(1)).strip()
            continue
        if not line.strip() or line.lstrip().startswith("|"):
            flush()
            para = []
            continue
        if not para:
            start = n
        para.append(line)
    flush()
    return out


def apa_key(authors: str, year: str) -> str:
    """'Card & Krueger', '1996' -> 'Card_1996'; 'Espinosa Andrade dkk.', '2024' -> 'Espinosa_Andrade_2024'."""
    first = _FIRST_AUTHOR_SPLIT.split(authors.strip())[0].strip()
    return re.sub(r"\s+", "_", first) + "_" + year


def strip_citations(sentence: str) -> str:
    """The sentence without its citations, so years and reference numbers are not read as the sentence's numbers."""
    s = re.sub(r"\[[^\]]*\]|\\\w*cite\w*\{[^}]*\}", " ", sentence)

    def paren(m):
        return " " if any(APA_PART.match(p) for p in m.group(1).split(";")) else m.group(0)
    s = CITE_APA_PAREN.sub(paren, s)
    return re.sub(r"(?<=[\w.])\s+\(\d{4}[a-z]?\)", " ", s)


def citations(sentence: str):
    """Return (keys, style) for one sentence; keys keep the order they appear in."""
    keys = []
    style = None
    for m in CITE_PANDOC.finditer(sentence):
        keys += CITE_PANDOC_KEY.findall(m.group("body"))
        style = "pandoc"
    for m in CITE_LATEX.finditer(sentence):
        keys += [k.strip() for k in m.group(1).split(",") if k.strip()]
        style = "latex"
    for m in CITE_BRACKET.finditer(sentence):
        keys += [k.strip() for k in re.split(r"[,;]", m.group(1)) if k.strip()]
        style = style or "bracket"
    for m in CITE_NUMERIC.finditer(sentence):
        for part in re.split(r"\s*,\s*", m.group(1)):
            if re.search(r"[-\u2013]", part):
                a, b = re.split(r"\s*[-\u2013]\s*", part)
                keys += [str(i) for i in range(int(a), int(b) + 1)]
            else:
                keys.append(part.strip())
        style = style or "numeric"
    apa = []
    for m in CITE_APA_PAREN.finditer(sentence):
        for part in m.group(1).split(";"):
            pm = APA_PART.match(part)
            if pm:
                apa.append((m.start() + 1, apa_key(pm.group("auth"), pm.group("year"))))
    for m in CITE_APA_NARR.finditer(sentence):
        auth = m.group("auth").split()
        while len(auth) > 1 and auth[0].lower() in _LEAD_WORDS:
            auth = auth[1:]
        if auth[0].lower() in _LEAD_WORDS or (auth[0].isupper() and len(auth[0]) > 1):
            continue  # "Menurut (2001)", or an acronym such as "PISA (2022)": not an author-year citation
        apa.append((m.start(), apa_key(" ".join(auth), m.group("year"))))
    if apa:
        keys += [k for _, k in sorted(apa)]
        style = style or "apa"
    seen, ordered = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered, style

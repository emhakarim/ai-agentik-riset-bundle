"""Compare bibliography entries with Crossref metadata (needs network; sends only DOIs, never manuscript text)."""
from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from . import bib as B

API = "https://api.crossref.org/works/"
USER_AGENT = "paper-tools/0.1 (reference metadata check)"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"<[^>]+>|[{}\\]", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def fetch(doi: str, opener=None, retries: int = 2):
    """Return Crossref's `message` for a DOI, or None if not found. `opener` lets tests inject a fake."""
    url = API + urllib.parse.quote(doi, safe="")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    open_ = opener or (lambda r: urllib.request.urlopen(r, timeout=20))
    for attempt in range(retries + 1):
        try:
            with open_(req) as resp:
                return json.loads(resp.read().decode("utf-8"))["message"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries:
                raise
        except urllib.error.URLError:
            if attempt == retries:
                raise
        time.sleep(1.5 * (attempt + 1))
    return None


def _surnames(entry_authors: str):
    out = []
    for a in re.split(r"\s+and\s+", entry_authors or ""):
        a = a.strip()
        if not a or a.lower() == "others":
            continue
        out.append(_norm(a.split(",")[0] if "," in a else a.split()[-1]))
    return out


def _squash(s: str) -> str:
    """Title/venue key: HTML tags removed without leaving gaps (high-<i>T</i><sub>c</sub> == high-Tc), then only
    letters and digits."""
    s = re.sub(r"<[^>]+>", "", s or "")
    return _norm(s).replace(" ", "")


def _similar(a: str, b: str, ratio: float = 0.9) -> bool:
    import difflib
    a, b = _squash(a), _squash(b)
    return a == b or a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= ratio


def _pages_match(ours: str, theirs: str) -> bool:
    o = _norm(ours.replace("--", "-")).split()
    t = _norm(theirs).split()
    if o == t:
        return True
    # Crossref often stores only the first page (or the article number); accept when the first pages agree
    return bool(o and t and len(t) == 1 and o[0] == t[0])


def compare(entry: dict, msg: dict) -> list:
    """Return a list of differences between a bib entry and Crossref's record (empty list = match)."""
    diffs = []
    cr_title_raw = (msg.get("title") or [""])[0]
    if entry.get("title") and cr_title_raw:
        if not _similar(entry["title"], cr_title_raw, 0.95):
            diffs.append(("title", entry.get("title"), " ".join(cr_title_raw.split())))
    cr_auth = [_norm(x.get("family", x.get("name", ""))) for x in msg.get("author", [])]
    ours = _surnames(entry.get("author", ""))

    def same(o, c):  # Crossref sometimes stores the full name as the family name ("Kane Yee")
        return o == c or (c.split() and c.split()[-1] == o) or (o.split() and o.split()[-1] == c)

    if ours and cr_auth:
        if not same(ours[0], cr_auth[0]):
            diffs.append(("first_author", ours[0], cr_auth[0]))
        missing = [s for s in ours if not any(same(s, c) for c in cr_auth)]
        if missing:
            diffs.append(("authors_not_in_crossref", ", ".join(missing), ", ".join(cr_auth[:8])))
    years = set()
    for k in ("published-print", "published-online", "issued", "published"):
        parts = (msg.get(k) or {}).get("date-parts") or [[None]]
        if parts[0] and parts[0][0]:
            years.add(parts[0][0])
    y = B.year(entry)
    if y and years and y not in years:
        diffs.append(("year", y, "/".join(str(v) for v in sorted(years))))
    for f, cf in (("volume", "volume"), ("number", "issue"), ("pages", "page")):
        ov, cv = (entry.get(f) or "").strip(), str(msg.get(cf) or "").strip()
        if f == "pages" and not cv:
            cv = str(msg.get("article-number") or "")
        if f == "pages":
            # an article number in the bib entry is fine when Crossref holds it (or only a page count) separately
            same = _pages_match(ov, cv) or _norm(ov) == _norm(str(msg.get("article-number") or "")) or (
                ov.isdigit() and len(ov) >= 5 and re.fullmatch(r"1-\d+", cv) is not None)
        else:
            same = _norm(ov) == _norm(cv)
        if ov and cv and not same:
            diffs.append((f, ov, cv))
    venue = (entry.get("journal") or entry.get("booktitle") or "")
    cr_venue = (msg.get("container-title") or [""])[0]
    if venue and cr_venue and not _similar(venue, cr_venue, 0.9):  # tolerates typos in Crossref's own record
        diffs.append(("venue", venue, cr_venue))
    return diffs


def check(entries: dict, keys=None, opener=None, pause: float = 0.2):
    """Check the given keys (default: all). Each row: key, doi, status (ok / differs / no_doi / not_found / error)."""
    rows = []
    for key in (keys or list(entries)):
        e = entries.get(key)
        if e is None:
            rows.append({"key": key, "doi": "", "status": "missing_in_bib", "diffs": []})
            continue
        d = B.doi(e)
        if not d:
            rows.append({"key": key, "doi": "", "status": "no_doi", "diffs": []})
            continue
        try:
            msg = fetch(d, opener)
        except Exception as ex:  # network trouble is reported, not hidden
            rows.append({"key": key, "doi": d, "status": "error", "diffs": [("error", str(ex), "")]})
            continue
        if msg is None:
            rows.append({"key": key, "doi": d, "status": "not_found", "diffs": []})
            continue
        diffs = compare(e, msg)
        rows.append({"key": key, "doi": d, "status": "differs" if diffs else "ok", "diffs": diffs})
        time.sleep(pause)
    return rows

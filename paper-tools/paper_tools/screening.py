"""Systematic-review screening support: de-duplicate records, compare two independent screeners, list conflicts
for the adjudicator, apply adjudication, and count the PRISMA 2020 flow.

CSV formats (UTF-8, header row):
  records:   id, title, doi, year, source  (other columns are kept)
  screener:  id, decision (include / exclude / maybe), reason (an exclusion code such as E1, E2 ...)
  adjudication: id, decision, reason
"""
from __future__ import annotations

import csv
import re
import unicodedata

INCLUDE = {"include", "in", "yes", "y", "1", "masuk", "ya"}
EXCLUDE = {"exclude", "out", "no", "n", "0", "keluar", "tidak"}
MAYBE = {"maybe", "unsure", "?", "ragu"}


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(rows, path, fields=None):
    fields = fields or (list(rows[0].keys()) if rows else ["id"])
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def _norm_doi(d: str) -> str:
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", (d or "").strip(), flags=re.I).lower()


def dedupe(records):
    """Keep the first record per DOI, then per normalised title (+ year when both have one)."""
    kept, dupes, by_doi, by_title = [], [], {}, {}
    for r in records:
        d, t = _norm_doi(r.get("doi", "")), _norm_title(r.get("title", ""))
        y = str(r.get("year", "")).strip()
        hit = by_doi.get(d) if d else None
        if hit is None and t:
            # same title: a duplicate unless both records give a year and the years differ (e.g. a new edition)
            hit = next((rid for yy, rid in by_title.get(t, []) if not y or not yy or yy == y), None)
        if hit is not None:
            dupes.append({**r, "duplicate_of": hit})
            continue
        kept.append(r)
        if d:
            by_doi[d] = r["id"]
        if t:
            by_title.setdefault(t, []).append((y, r["id"]))
    return kept, dupes


def decision(value: str) -> str:
    v = (value or "").strip().lower()
    if v in INCLUDE:
        return "include"
    if v in EXCLUDE:
        return "exclude"
    if v in MAYBE:
        return "maybe"
    raise ValueError("unknown decision %r" % value)


def cohen_kappa(a, b):
    """Cohen's kappa for two raters over the same items (lists of labels)."""
    if len(a) != len(b) or not a:
        raise ValueError("need two equal, non-empty lists")
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(lab) / n) * (b.count(lab) / n) for lab in labels)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def pabak(a, b, k: int = 2):
    """Prevalence-adjusted bias-adjusted kappa: (k*po - 1)/(k - 1). Unlike Cohen's kappa it does not collapse when
    almost every record is excluded (the usual case in screening).

    k is the number of categories in the coding scheme, fixed in advance. It is not counted from the sample: one
    'maybe' would otherwise change k from 2 to 3 and raise PABAK for the same agreement. compare() reports PABAK
    on the screening decision itself, advance (include or maybe) vs exclude, so k = 2."""
    if len(a) != len(b) or not a:
        raise ValueError("need two equal, non-empty lists")
    if k < 2:
        raise ValueError("k must be at least 2")
    po = sum(x == y for x, y in zip(a, b)) / len(a)
    return (k * po - 1) / (k - 1)


def _advance(d: str) -> str:
    return "exclude" if d == "exclude" else "advance"


def seed_check(final: dict, seeds):
    """Seed studies are records known to be eligible; every one must end as include. Returns the missed ids."""
    return [s for s in seeds if final.get(s, {}).get("decision") != "include"]


def write_xlsx(sheets: dict, path):
    """Write {sheet_name: [rows as dicts]} to a minimal .xlsx with the standard library only (inline strings)."""
    import zipfile
    from xml.sax.saxutils import escape

    def col(n):
        s = ""
        while n:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    names = list(sheets)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/'
                   '2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
                   'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/'
                   'xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.'
                   'main+xml"/>' + "".join(
                       '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-'
                       'officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1) for i in range(len(names))) + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/'
                   'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
                   'relationships"><sheets>' + "".join(
                       '<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(n[:31]), i + 1, i + 1)
                       for i, n in enumerate(names)) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/relationships">' + "".join(
                       '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                       'relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1)
                       for i in range(len(names))) + "</Relationships>")
        for i, n in enumerate(names):
            rows = sheets[n]
            header = list(rows[0].keys()) if rows else ["(empty)"]
            xml_rows = []
            for r_i, values in enumerate([header] + [[r.get(h, "") for h in header] for r in rows], 1):
                cells = "".join('<c r="%s%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                                % (col(c_i), r_i, escape(str(v if v is not None else "")))
                                for c_i, v in enumerate(values, 1))
                xml_rows.append('<row r="%d">%s</row>' % (r_i, cells))
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1),
                       '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/'
                       'spreadsheetml/2006/main"><sheetData>' + "".join(xml_rows) + "</sheetData></worksheet>")


def compare(screener_a, screener_b):
    """Align two screeners by id. Conflicts: different decisions, or any 'maybe' (goes to the adjudicator)."""
    a = {r["id"]: r for r in screener_a}
    b = {r["id"]: r for r in screener_b}
    missing = sorted(set(a) ^ set(b))
    ids = [i for i in a if i in b]
    da = [decision(a[i]["decision"]) for i in ids]
    db = [decision(b[i]["decision"]) for i in ids]
    conflicts, agreed = [], {}
    for i, x, y in zip(ids, da, db):
        if x != y or x == "maybe":
            conflicts.append({"id": i, "a": x, "a_reason": a[i].get("reason", ""), "b": y,
                              "b_reason": b[i].get("reason", "")})
        else:
            reason = a[i].get("reason", "") if x == "exclude" else ""
            agreed[i] = {"id": i, "decision": x, "reason": reason, "by": "agreement"}
    pab = pabak([_advance(x) for x in da], [_advance(y) for y in db], k=2) if ids else None
    return {"n": len(ids), "kappa": cohen_kappa(da, db) if ids else None, "pabak": pab,
            "pabak_basis": "advance (include/maybe) vs exclude, k = 2",
            "agreement": (sum(x == y for x, y in zip(da, db)) / len(ids)) if ids else None,
            "conflicts": conflicts, "agreed": agreed, "missing_in_one": missing}


def apply_adjudication(agreed: dict, adjudication):
    final = dict(agreed)
    for r in adjudication:
        d = decision(r["decision"])
        if d == "maybe":
            raise ValueError("adjudicator must decide include/exclude for %s" % r["id"])
        final[r["id"]] = {"id": r["id"], "decision": d, "reason": r.get("reason", ""), "by": "adjudicator"}
    return final


def prisma_counts(identified_by_source: dict, duplicates: int, title_abstract: dict, full_text: dict = None,
                  not_retrieved: int = 0):
    """PRISMA 2020 numbers for the flow diagram.

    identified_by_source: {"Scopus": 120, "ERIC": 80, ...}
    title_abstract:       final decisions at title/abstract stage ({id: {"decision": ...}})
    full_text:            final decisions at full-text stage, with exclusion reasons
    """
    identified = sum(identified_by_source.values())
    screened = identified - duplicates
    ta_excl = sum(1 for v in title_abstract.values() if v["decision"] == "exclude")
    sought = screened - ta_excl
    out = {"identified": identified, "by_source": identified_by_source, "duplicates_removed": duplicates,
           "records_screened": screened, "records_excluded": ta_excl, "reports_sought": sought,
           "reports_not_retrieved": not_retrieved, "reports_assessed": sought - not_retrieved}
    if full_text is not None:
        reasons = {}
        for v in full_text.values():
            if v["decision"] == "exclude":
                reasons[v.get("reason") or "unspecified"] = reasons.get(v.get("reason") or "unspecified", 0) + 1
        out["reports_excluded_by_reason"] = reasons
        out["studies_included"] = sum(1 for v in full_text.values() if v["decision"] == "include")
    return out

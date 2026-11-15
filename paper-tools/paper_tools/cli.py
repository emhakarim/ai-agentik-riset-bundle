"""paper-check: local checks for a research manuscript before submission.

    paper-check gate      DRAFT --bib refs.bib [--sources results/ ...] [--profile general] [--recent-years 5
                          --recent-min 0.8] [--crossref] [--lang id|en] [--json out.json]
    paper-check claims    DRAFT --out claims.csv
    paper-check numbers   DRAFT --sources results/ [--decimal auto|.|,]
    paper-check lint      DRAFT [--bib refs.bib] [--profile general]
    paper-check refs      --bib refs.bib [--draft DRAFT]          (Crossref; sends DOIs only)
    paper-check rebuttal  --reviews reviews.md --letter letter.md --draft DRAFT
    paper-check review    REPORT

Exit code: 0 = pass, 1 = at least one blocking problem, 2 = usage error.
Nothing is sent over the network except DOIs, and only with `refs` or `gate --crossref`.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from . import abstract as AB
from . import bib as B
from . import calibration as CAL
from . import fmt as F
from . import reads as RD
from . import records as RECS
from . import screening as SC
from . import claims as C
from . import lint as L
from . import numbers as N
from . import rebuttal as RB
from . import refs as R
from . import review as RV
from . import text as T

MSG = {
    "id": {
        "pass": "LULUS", "fail": "GAGAL", "warn": "PERHATIAN",
        "placeholders": "placeholder di naskah", "missing_bib": "sitasi tanpa entri di bibliografi",
        "uncited": "entri bibliografi yang tidak disitasi", "undefined_float": "tabel/gambar dirujuk tapi tidak ada",
        "unref_float": "tabel/gambar tidak pernah dirujuk", "statements": "pernyataan wajib belum ada",
        "recency": "porsi rujukan terbaru", "long": "kalimat lebih dari 40 kata",
        "untraced": "angka yang tidak ditemukan di file sumber", "claims": "kalimat bersitasi untuk diaudit",
        "dumps": "kalimat dengan 4+ sitasi", "crossref_bad": "rujukan yang metadatanya berbeda / tidak ditemukan",
        "summary": "Ringkasan", "skipped": "dilewati (tidak ada masukan)",
        "unread": "klaim angka/metode/celah bersandar pada rujukan yang belum dibaca penuh",
    },
    "en": {
        "pass": "PASS", "fail": "FAIL", "warn": "WARN",
        "placeholders": "placeholders in the manuscript", "missing_bib": "citations missing from the bibliography",
        "uncited": "bibliography entries never cited", "undefined_float": "tables/figures referenced but not defined",
        "unref_float": "tables/figures never referenced", "statements": "required statements missing",
        "recency": "share of recent references", "long": "sentences over 40 words",
        "untraced": "numbers not found in the source files", "claims": "cited sentences to audit",
        "dumps": "sentences with 4+ citations", "crossref_bad": "references that differ from / are missing in Crossref",
        "summary": "Summary", "skipped": "skipped (no input)",
        "unread": "number/method/gap claims resting on works not read in full",
    },
}


def _entries(paths):
    return B.load(*paths) if paths else {}


def gate(a):
    m = MSG[a.lang]
    text = T.read(a.draft)
    entries = _entries(a.bib)
    result = {"draft": a.draft, "checks": []}

    def add(name, status, count, detail):
        result["checks"].append({"check": name, "status": status, "count": count, "detail": detail})

    ph = L.placeholders(text)
    if a.template:  # {{NAME}} markers are filled by a build step, they are not unfinished text
        ph = [p for p in ph if not p["match"].startswith("{{")]
    add("placeholders", "fail" if ph else "pass", len(ph), ph[:20])
    cv = L.citations_vs_bib(text, entries)
    numeric_only = cv["styles"] == ["numeric"]
    if entries and numeric_only:
        add("missing_bib", "skipped", 0, ["numeric citations [1]: run the gate on the source with citation keys"])
    elif entries:
        add("missing_bib", "fail" if cv["missing_in_bib"] else "pass", len(cv["missing_in_bib"]), cv["missing_in_bib"])
        add("uncited", "warn" if cv["uncited_in_bib"] else "pass", len(cv["uncited_in_bib"]), cv["uncited_in_bib"])
    else:
        add("missing_bib", "skipped", 0, [])
    if a.bib:
        bi = B.load_issues(*a.bib)
        add("bib_issues", "fail" if bi else "pass", len(bi), bi)
    fl = L.floats(text)
    bad_floats = fl["undefined"] + fl["latex_missing_labels"]
    # in a template, tables may be inserted by the build step, so a missing caption is only a warning
    add("undefined_float", ("warn" if a.template else "fail") if bad_floats else "pass", len(bad_floats), bad_floats)
    add("unref_float", "warn" if fl["unreferenced"] else "pass", len(fl["unreferenced"]), fl["unreferenced"])
    st = L.statements(text, a.profile)
    add("statements", "fail" if st["missing"] else "pass", len(st["missing"]), st["missing"])
    if entries and a.recent_min > 0 and numeric_only:
        add("recency", "skipped", 0, [])
    elif entries and a.recent_min > 0:
        rc = L.recency(text, entries, a.recent_years, a.recent_min, a.as_of)
        add("recency", "pass" if rc["ok"] else "fail",
            None if rc["share"] is None else round(100 * rc["share"], 1), rc)
    ls = L.long_sentences(text)
    add("long", "warn" if ls else "pass", len(ls), ls[:20])
    if a.sources:
        tr = N.trace(text, a.sources, decimal=a.decimal)
        bad = [{"line": n["line"], "number": n["raw"]} for n in tr if not n["traced"] and not n.get("sign_flipped")]
        add("untraced", "warn" if bad else "pass", len(bad), bad[:50])
        flips = [{"line": n["line"], "number": n["raw"], "source": n["source"]} for n in tr if n.get("sign_flipped")]
        add("sign_flipped", "fail" if flips else "pass", len(flips), flips[:50])
    else:
        add("untraced", "skipped", 0, [])
    if a.reads:
        rc = RD.check(text, RD.load(a.reads))
        weak = rc["claims_needing_full_text"]
        add("unread", "warn" if weak else "pass", len(weak),
            [{"id": w["id"], "line": w["line"], "type": w["type"], "keys": w["keys"], "status": w["status"]}
             for w in weak])
    rows = C.extract(text)
    s = C.summary(rows)
    add("claims", "info", s["claims"], s["by_type"])
    add("dumps", "warn" if s["citation_dumps"] else "pass", len(s["citation_dumps"]), s["citation_dumps"])
    if a.crossref and entries:
        keys = [k for k in L.cited_keys(text)[0] if k in entries] or list(entries)
        cr = R.check(entries, keys)
        bad = [r for r in cr if r["status"] in ("differs", "not_found", "error")]
        add("crossref_bad", "fail" if bad else "pass", len(bad),
            [{"key": r["key"], "status": r["status"], "diffs": r["diffs"]} for r in bad])

    failed = any(c["status"] == "fail" for c in result["checks"])
    result["verdict"] = "fail" if failed else "pass"
    for c in result["checks"]:
        label = m.get(c["check"], c["check"])
        status = {"pass": m["pass"], "fail": m["fail"], "warn": m["warn"], "info": "INFO",
                  "skipped": m["skipped"]}[c["status"]]
        count = "" if c["count"] is None else ("%s%%" % c["count"] if c["check"] == "recency" else c["count"])
        print("%-10s %-55s %s" % (status, label, count))
        if c["status"] in ("fail", "warn") and c["detail"]:
            for d in (c["detail"] if isinstance(c["detail"], list) else [c["detail"]])[:8]:
                print("           - %s" % (d,))
    print("\n%s: %s" % (m["summary"], m["fail"] if failed else m["pass"]))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1, default=str)
    return 1 if failed else 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="paper-check", description=__doc__.split("\n")[0])
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gate", help="run every local check and give PASS / FAIL")
    g.add_argument("draft")
    g.add_argument("--bib", nargs="*", default=[], help="one or more .bib files; later files override earlier ones")
    g.add_argument("--sources", nargs="*", default=[], help="result files or folders that numbers must come from")
    g.add_argument("--profile", default="general", choices=sorted(L.PROFILES))
    g.add_argument("--recent-years", type=int, default=5)
    g.add_argument("--recent-min", type=float, default=0.0, help="e.g. 0.8 for 80 %% of references in the window")
    g.add_argument("--as-of", type=int, default=None, help="year the recency window ends (default: this year)")
    g.add_argument("--decimal", default="auto", choices=["auto", ".", ","])
    g.add_argument("--crossref", action="store_true", help="also check cited references at Crossref (sends DOIs)")
    g.add_argument("--lang", default="id", choices=["id", "en"])
    g.add_argument("--reads", help="reading ledger CSV (paper-check reads): warn on number/method/gap claims that "
                                   "rest on works not read in full")
    g.add_argument("--template", action="store_true",
                   help="the draft is a template: {{NAME}} markers and tables are filled by a build step")
    g.add_argument("--json")

    c = sub.add_parser("claims", help="list cited sentences (CSV) for the claim-to-reference audit")
    c.add_argument("draft")
    c.add_argument("--out", required=True)

    n = sub.add_parser("numbers", help="trace numbers in the text to source files")
    n.add_argument("draft")
    n.add_argument("--sources", nargs="+", required=True)
    n.add_argument("--decimal", default="auto", choices=["auto", ".", ","])
    n.add_argument("--all", action="store_true", help="also list the traced numbers")

    li = sub.add_parser("lint", help="placeholders, citations vs bibliography, tables/figures, statements")
    li.add_argument("draft")
    li.add_argument("--bib", nargs="*", default=[])
    li.add_argument("--profile", default="general", choices=sorted(L.PROFILES))

    r = sub.add_parser("refs", help="compare bibliography entries with Crossref metadata (sends DOIs only)")
    r.add_argument("--bib", nargs="+", required=True)
    r.add_argument("--draft", help="only the references cited in this draft")

    rb = sub.add_parser("rebuttal", help="check a response letter against the reviews and the revised draft")
    rb.add_argument("--reviews", required=True)
    rb.add_argument("--letter", required=True)
    rb.add_argument("--draft", required=True)

    rv = sub.add_parser("review", help="validate a simulated-review report")
    rv.add_argument("report")

    ab = sub.add_parser("abstract", help="abstract word limit, structured parts, same numbers in both languages "
                                         "and in the body")
    ab.add_argument("draft")
    ab.add_argument("--max-words", type=int)
    ab.add_argument("--structured", action="store_true", help="require background / methods / results / conclusion")
    ab.add_argument("--other", help="a file with the abstract in the other language (if not in the draft)")

    sc = sub.add_parser("screen", help="systematic-review screening: dedupe, compare two screeners, adjudicate, "
                                       "PRISMA counts")
    sc_sub = sc.add_subparsers(dest="step", required=True)
    s0 = sc_sub.add_parser("import", help="read RIS / PubMed .nbib / WoS / CSV exports into one records CSV")
    s0.add_argument("exports", nargs="+")
    s0.add_argument("--out", required=True)
    s5 = sc_sub.add_parser("log", help="write the screening CSV files into one Excel workbook (one sheet each)")
    s5.add_argument("csvs", nargs="+")
    s5.add_argument("--out", required=True)
    s1 = sc_sub.add_parser("dedupe")
    s1.add_argument("records")
    s1.add_argument("--out", required=True)
    s1.add_argument("--dupes")
    s2 = sc_sub.add_parser("compare")
    s2.add_argument("screener_a")
    s2.add_argument("screener_b")
    s2.add_argument("--conflicts", required=True, help="CSV for the adjudicator")
    s2.add_argument("--agreed", required=True, help="CSV of the decisions both screeners agree on")
    s3 = sc_sub.add_parser("final")
    s3.add_argument("agreed")
    s3.add_argument("adjudication")
    s3.add_argument("--out", required=True)
    s3.add_argument("--seeds", nargs="*", default=[], help="ids of known eligible studies; each must be included")
    s4 = sc_sub.add_parser("prisma")
    s4.add_argument("--sources", nargs="+", required=True, help="name=count, e.g. Scopus=120 ERIC=80")
    s4.add_argument("--duplicates", type=int, required=True)
    s4.add_argument("--title-abstract", required=True, help="final CSV of the title/abstract stage")
    s4.add_argument("--full-text", help="final CSV of the full-text stage")
    s4.add_argument("--not-retrieved", type=int, default=0)

    se = sub.add_parser("seed", help="plant known flaws in a copy of a manuscript (panel calibration)")
    se.add_argument("draft")
    se.add_argument("--out", required=True)
    se.add_argument("--key", required=True)
    se.add_argument("--seed", type=int, default=1)
    se.add_argument("--kinds", nargs="*", default=["number", "overclaim", "citation", "statement", "causal"])
    so = sub.add_parser("score", help="score a review report against the planted-flaw key")
    so.add_argument("report")
    so.add_argument("--key", required=True)

    rd = sub.add_parser("reads", help="reading ledger: mark which cited works were read (full / abstract / none)")
    rd_sub = rd.add_subparsers(dest="step", required=True)
    r1 = rd_sub.add_parser("mark")
    r1.add_argument("keys", nargs="+")
    r1.add_argument("--status", required=True, choices=RD.STATUSES)
    r1.add_argument("--file", default="reads.csv")
    r1.add_argument("--note", default="")
    r2 = rd_sub.add_parser("check")
    r2.add_argument("draft")
    r2.add_argument("--file", default="reads.csv")

    fo = sub.add_parser("format", help="convert Markdown to DOCX / LaTeX / PDF with pandoc (template + CSL style)")
    fo.add_argument("draft")
    fo.add_argument("--out", required=True)
    fo.add_argument("--bib", nargs="*", default=[])
    fo.add_argument("--csl")
    fo.add_argument("--reference-doc")
    fo.add_argument("--template")
    fo.add_argument("--lang")
    fo.add_argument("--number-sections", action="store_true")
    fo.add_argument("--dry-run", action="store_true", help="only print the pandoc command")

    a = p.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252; manuscripts are not ASCII
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if a.cmd == "gate":
        return gate(a)
    if a.cmd == "claims":
        rows = C.extract(T.read(a.draft))
        C.write_csv(rows, a.out)
        print(json.dumps(C.summary(rows), ensure_ascii=False))
        return 0
    if a.cmd == "numbers":
        tr = N.trace(T.read(a.draft), a.sources, decimal=a.decimal)
        bad = 0
        for t in tr:
            if not t["traced"] or a.all:
                mark = "ok " if t["traced"] else ("+/-" if t.get("sign_flipped") else "?? ")
                print("%s line %-5d %-14s %s" % (mark, t["line"], t["raw"],
                                                t["source"] or t["sentence"][:80]))
            bad += not t["traced"]
        print("numbers: %d, untraced: %d" % (len(tr), bad))
        return 0
    if a.cmd == "lint":
        text, entries = T.read(a.draft), _entries(a.bib)
        out = {"placeholders": L.placeholders(text), "citations": L.citations_vs_bib(text, entries),
               "floats": L.floats(text), "statements": L.statements(text, a.profile),
               "bib_issues": B.load_issues(*a.bib) if a.bib else []}
        print(json.dumps(out, ensure_ascii=False, indent=1))
        bad = (out["placeholders"] or out["citations"]["missing_in_bib"] or out["floats"]["undefined"]
               or out["statements"]["missing"] or out["bib_issues"])
        return 1 if bad else 0
    if a.cmd == "refs":
        entries = _entries(a.bib)
        problems = B.load_issues(*(a.bib if isinstance(a.bib, list) else [a.bib]))
        for it in problems:  # an entry that cannot be read must never vanish silently
            print("%-10s %-30s line %d: %s" % ("bib_issue", it["key"], it["line"], it["problem"]))
        keys = None
        if a.draft:
            cited = [k for k in L.resolve(L.cited_keys(T.read(a.draft))[0], entries) if not k.isdigit()]
            keys = list(dict.fromkeys(cited))
        rows = R.check(entries, keys)
        for row in rows:
            print("%-10s %-30s %s" % (row["status"], row["key"], row["doi"]))
            for d in row["diffs"]:
                print("           %s: ours=%r crossref=%r" % d)
        bad = ("differs", "not_found", "error", "missing_in_bib")
        return 1 if problems or any(r["status"] in bad for r in rows) else 0
    if a.cmd == "rebuttal":
        out = RB.check(T.read(a.reviews), T.read(a.letter), T.read(a.draft))
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 1 if (out["unanswered"] or out["places_not_found"]) else 0
    if a.cmd == "review":
        out = RV.check(T.read(a.report))
        print(json.dumps(out, ensure_ascii=False, indent=1))
        bad = (not out["has_decision"] or out["sections_missing"] or out["findings_without_mark"]
               or out["c_items_without_request"])
        return 1 if bad else 0
    if a.cmd == "abstract":
        out = AB.check(T.read(a.draft), a.max_words, T.read(a.other) if a.other else None, a.structured)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        bad = any(x["over_limit"] or x["numbers_not_in_body"] or x.get("parts_missing") for x in out["abstracts"])
        lv = out.get("language_versions", {})
        bad = bad or bool(lv.get("only_in_first") or lv.get("only_in_second")) or not out["abstracts"]
        return 1 if bad else 0
    if a.cmd == "screen":
        return _screen(a)
    if a.cmd == "reads":
        if a.step == "mark":
            led = RD.mark(a.file, a.keys, a.status, a.note)
            print("%s: %d key(s) marked %s; ledger now has %d entries" % (a.file, len(a.keys), a.status, len(led)))
            return 0
        out = RD.check(T.read(a.draft), RD.load(a.file))
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "seed":
        seeded, key = CAL.seed(T.read(a.draft), tuple(a.kinds), a.seed)
        with open(a.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(seeded)
        CAL.save_key(key, a.key)
        print("planted %d flaw(s): %s" % (len(key), ", ".join(k["kind"] for k in key)))
        print("give the reviewers %s only; keep %s hidden until scoring" % (a.out, a.key))
        return 0
    if a.cmd == "score":
        out = CAL.score(T.read(a.report), CAL.load_key(a.key))
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "format":
        cmd = F.build_command(a.draft, a.out, a.bib, a.csl, a.reference_doc, a.template, a.lang, a.number_sections)
        print(" ".join('"%s"' % c if " " in c else c for c in cmd))
        if a.dry_run:
            return 0
        code, so, se = F.run(cmd)
        sys.stdout.write(so)
        sys.stderr.write(se)
        return code
    return 2


def _screen(a):
    if a.step == "import":
        recs = RECS.merge(a.exports)
        fields = ["id", "title", "abstract", "doi", "year", "authors", "journal", "source"]
        SC.write_csv(recs, a.out, fields)
        by = {}
        for r in recs:
            by[r["source"]] = by.get(r["source"], 0) + 1
        print("records: %d %s -> %s" % (len(recs), json.dumps(by, ensure_ascii=False), a.out))
        return 0
    if a.step == "log":
        from pathlib import Path
        SC.write_xlsx({Path(c).stem: SC.read_csv(c) for c in a.csvs}, a.out)
        print("workbook: %s (%d sheet(s))" % (a.out, len(a.csvs)))
        return 0
    if a.step == "dedupe":
        kept, dupes = SC.dedupe(SC.read_csv(a.records))
        SC.write_csv(kept, a.out)
        if a.dupes:
            SC.write_csv(dupes, a.dupes)
        print("records: %d, kept: %d, duplicates: %d" % (len(kept) + len(dupes), len(kept), len(dupes)))
        return 0
    if a.step == "compare":
        res = SC.compare(SC.read_csv(a.screener_a), SC.read_csv(a.screener_b))
        SC.write_csv(res["conflicts"], a.conflicts, ["id", "a", "a_reason", "b", "b_reason", "decision", "reason"])
        SC.write_csv(list(res["agreed"].values()), a.agreed, ["id", "decision", "reason", "by"])
        print(json.dumps({k: res[k] for k in ("n", "kappa", "pabak", "agreement", "missing_in_one")},
                         ensure_ascii=False))
        print("conflicts for the adjudicator: %d -> %s" % (len(res["conflicts"]), a.conflicts))
        return 1 if res["missing_in_one"] else 0
    if a.step == "final":
        agreed = {r["id"]: r for r in SC.read_csv(a.agreed)}
        final = SC.apply_adjudication(agreed, SC.read_csv(a.adjudication))
        SC.write_csv(list(final.values()), a.out, ["id", "decision", "reason", "by"])
        inc = sum(1 for v in final.values() if v["decision"] == "include")
        print("final decisions: %d (include %d, exclude %d)" % (len(final), inc, len(final) - inc))
        missed = SC.seed_check(final, a.seeds)
        if a.seeds:
            print("seed studies: %d, missed: %s" % (len(a.seeds), ", ".join(missed) or "none"))
        return 1 if missed else 0
    if a.step == "prisma":
        sources = {}
        for s in a.sources:
            name, _, n = s.rpartition("=")
            sources[name] = int(n)
        ta = {r["id"]: r for r in SC.read_csv(a.title_abstract)}
        ft = {r["id"]: r for r in SC.read_csv(a.full_text)} if a.full_text else None
        print(json.dumps(SC.prisma_counts(sources, a.duplicates, ta, ft, a.not_retrieved), ensure_ascii=False,
                         indent=1))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())

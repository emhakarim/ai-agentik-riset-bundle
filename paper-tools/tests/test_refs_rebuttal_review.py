import io
import json

from paper_tools import bib as B
from paper_tools import rebuttal as RB
from paper_tools import refs as R
from paper_tools import review as RV

CROSSREF = {
    "title": ["GPU Solvers"],
    "author": [{"family": "Smith"}, {"family": "Doe"}],
    "container-title": ["J. Comp."],
    "issued": {"date-parts": [[2020, 5]]},
    "volume": "12", "issue": "3", "page": "1-10",
}


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_opener(record):
    def opener(req):
        return _Resp(json.dumps({"message": record}).encode("utf-8"))
    return opener


def test_crossref_match_and_differences():
    e = B.parse("@article{k, author={Smith, J. and Doe, J.}, title={{GPU} solvers}, journal={J. Comp.}, "
                "year={2020}, volume={12}, number={3}, pages={1--10}, doi={10.1/x}}")
    rows = R.check(e, opener=fake_opener(CROSSREF), pause=0)
    assert rows[0]["status"] == "ok", rows[0]["diffs"]
    bad = B.parse("@article{k, author={Brown, A.}, title={GPU solvers}, journal={J. Comp.}, year={2019}, "
                  "volume={13}, doi={10.1/x}}")
    rows = R.check(bad, opener=fake_opener(CROSSREF), pause=0)
    fields = {d[0] for d in rows[0]["diffs"]}
    assert rows[0]["status"] == "differs" and {"first_author", "year", "volume"} <= fields
    # real cases seen on a live check: HTML in Crossref titles, first-page-only records, a typo in Crossref's venue
    rec = dict(CROSSREF, title=["Microwave impedance of high-<i>T</i>\n <i>c</i> films"], page="1053",
               **{"container-title": ["IEEE Transactions on Appiled Superconductivity"]})
    e2 = B.parse("@article{k, author={Smith, J.}, title={Microwave impedance of high-Tc films}, journal={IEEE "
                 "Transactions on Applied Superconductivity}, year={2020}, volume={12}, number={3}, "
                 "pages={1053--1061}, doi={10.1/x}}")
    assert R.check(e2, opener=fake_opener(rec), pause=0)[0]["status"] == "ok"
    e3 = B.parse("@article{k, author={Smith, J.}, title={GPU solvers}, journal={J. Comp.}, year={2020}, "
                 "pages={1--8}, doi={10.1/x}}")
    assert R.check(e3, opener=fake_opener(dict(CROSSREF, page="1-4")), pause=0)[0]["diffs"] == [("pages", "1--8", "1-4")]
    # live Paper 1 cases: full name stored as family ("Kane Yee"); article number vs a 1-N page count
    yee = dict(CROSSREF, author=[{"family": "Kane Yee"}])
    e4 = B.parse("@article{k, author={Yee, K.}, title={GPU solvers}, journal={J. Comp.}, year={2020}, doi={10.1/x}}")
    assert R.check(e4, opener=fake_opener(yee), pause=0)[0]["status"] == "ok"
    e5 = B.parse("@article{k, author={Smith, J.}, title={GPU solvers}, journal={J. Comp.}, year={2020}, "
                 "pages={6817674}, doi={10.1/x}}")
    assert R.check(e5, opener=fake_opener(dict(CROSSREF, page="1-11")), pause=0)[0]["status"] == "ok"
    nodoi = B.parse("@book{b, title={X}, year={2001}}")
    assert R.check(nodoi, opener=fake_opener(CROSSREF), pause=0)[0]["status"] == "no_doi"


REVIEWS = """Reviewer 1
R1.1 The sample size is small.
R1.2 Define the effect size.
Editor
E.1 Add a data availability statement.
"""
LETTER = """R1.1 The sample size is small.
Response: We agree and added a power analysis in Section 3.2, see Table 2 (power = 0.82).
R1.2 Define the effect size.
Response: Done.
"""
DRAFT = """# 1 Introduction

x

## 3.2 Power

The power was 0.82 for d = 0.5.

**Table 2.** Power.
"""


def test_rebuttal_checks():
    out = RB.check(REVIEWS, LETTER, DRAFT)
    assert out["points"] == 3
    assert {u["id"]: u["why"] for u in out["unanswered"]} == {"R1.2": "no answer text", "E.1": "not in letter"}
    assert out["places_not_found"] == [] and out["numbers_not_in_draft"] == []
    out2 = RB.check(REVIEWS, LETTER.replace("Section 3.2", "Section 4.1").replace("0.82", "0.91"), DRAFT)
    assert out2["places_not_found"] == ["Section 4.1"] and out2["numbers_not_in_draft"] == ["0.91"]


REPORT = """# Simulated review

## Combined decision

Major revision.

## Findings

- **[checked, code]** The margin definition was wrong.
- **[wrong]** Reviewer claim about Pennycook.
- A finding without any mark.

## A. Fix now

- fix x

## B. Owner decisions

- title

## C. New runs

- Request to the lab: rerun with finer mesh.
- Rerun something.
"""


def test_review_findings_under_reviewer_subheadings():
    rep = REPORT.replace("## Findings\n", "## Findings\n\n### Editor\n").replace(
        "- A finding without any mark.", "### Methodology\n\n- A finding without any mark.")
    out = RV.check(rep)
    assert out["findings"] == 3 and len(out["findings_without_mark"]) == 1


def test_review_report_validation():
    out = RV.check(REPORT)
    assert out["has_decision"] and out["sections_missing"] == []
    assert out["findings"] == 3 and len(out["findings_without_mark"]) == 1
    assert out["c_items"] == 2 and out["c_items_without_request"] == ["- Rerun something."]

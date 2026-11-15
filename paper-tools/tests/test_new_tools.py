import json

import pytest

from paper_tools import abstract as AB
from paper_tools import calibration as CAL
from paper_tools import cli
from paper_tools import fmt as F
from paper_tools import screening as SC

MS = """# Judul

**Abstrak.** Penelitian ini melibatkan 64 siswa. Model PBL meningkatkan hasil belajar (d = 0,45; p = 0,003) dengan
N-Gain 0,52.

**Kata kunci:** PBL

**Abstract.** This study involved 64 students. PBL improved learning outcomes (d = 0.45; p = .003) with an N-Gain
of 0.62.

**Keywords:** PBL

## Hasil

Sebanyak 64 siswa ikut. Effect size d = 0,45, p = 0,003, N-Gain 0,52.
"""


def test_abstract_language_versions_and_body():
    out = AB.check(MS, max_words=30)
    heads = [x["heading"].lower() for x in out["abstracts"]]
    assert heads == ["abstrak", "abstract"]
    assert out["abstracts"][0]["over_limit"] is False
    assert out["abstracts"][1]["numbers_not_in_body"] == ["0.62"]
    assert out["language_versions"]["only_in_first"] == ["0,52"]
    assert out["language_versions"]["only_in_second"] == ["0.62"]
    assert AB.check(MS, max_words=10)["abstracts"][0]["over_limit"] is True


def test_structured_abstract_parts():
    txt = "## Abstract\n\nBackground: x. Methods: y. Results: z.\n\n## Intro\n\nbody\n"
    out = AB.check(txt, structured=True)
    assert out["abstracts"][0]["parts_missing"] == ["conclusion"]


RECORDS = [
    {"id": "1", "title": "Problem-Based Learning in Physics", "doi": "10.1/ABC", "year": "2021"},
    {"id": "2", "title": "problem based learning in physics!", "doi": "", "year": "2021"},
    {"id": "3", "title": "Another study", "doi": "https://doi.org/10.1/abc", "year": "2022"},
    {"id": "4", "title": "A Handbook", "doi": "", "year": "2010"},
    {"id": "5", "title": "A handbook", "doi": "", "year": "2018"},
]


def test_dedupe():
    kept, dupes = SC.dedupe(RECORDS)
    assert [r["id"] for r in kept] == ["1", "4", "5"]  # different years: a new edition, kept
    assert {d["id"]: d["duplicate_of"] for d in dupes} == {"2": "1", "3": "1"}


def test_kappa_compare_adjudicate_prisma():
    assert SC.cohen_kappa(list("aabb"), list("aabb")) == 1.0
    assert abs(SC.cohen_kappa(["y", "y", "n", "n", "y", "n"], ["y", "n", "n", "n", "y", "y"]) - 1 / 3) < 1e-9
    a = [{"id": "1", "decision": "include"}, {"id": "2", "decision": "exclude", "reason": "E2"},
         {"id": "3", "decision": "maybe"}, {"id": "4", "decision": "exclude", "reason": "E1"}]
    b = [{"id": "1", "decision": "include"}, {"id": "2", "decision": "exclude", "reason": "E2"},
         {"id": "3", "decision": "include"}, {"id": "4", "decision": "include"}]
    res = SC.compare(a, b)
    assert [c["id"] for c in res["conflicts"]] == ["3", "4"]
    assert set(res["agreed"]) == {"1", "2"}
    final = SC.apply_adjudication(res["agreed"], [{"id": "3", "decision": "include"},
                                                  {"id": "4", "decision": "exclude", "reason": "E1"}])
    assert sum(v["decision"] == "include" for v in final.values()) == 2
    with pytest.raises(ValueError):
        SC.apply_adjudication({}, [{"id": "9", "decision": "maybe"}])
    pr = SC.prisma_counts({"Scopus": 4, "ERIC": 2}, 2, final,
                          {"1": {"decision": "include"}, "3": {"decision": "exclude", "reason": "E3"}})
    assert pr["identified"] == 6 and pr["records_screened"] == 4 and pr["records_excluded"] == 2
    assert pr["reports_sought"] == 2 and pr["studies_included"] == 1 and pr["reports_excluded_by_reason"] == {"E3": 1}


DRAFT = """# Results

The intervention suggests a gain of 0.45 points [smith2020a]. Scores were associated with attendance [lee2019b].
Motivation may rise with feedback [kim2021c].

## Data Availability

Data on request.

## Funding

None.
"""


def test_seed_and_score():
    seeded, key = CAL.seed(DRAFT, seed_value=3)
    kinds = sorted(k["kind"] for k in key)
    assert kinds == ["causal", "citation", "citation", "number", "overclaim", "statement"]
    causal = next(k for k in key if k["kind"] == "causal")
    assert "Data Availability" not in seeded and causal["after"] in seeded and causal["before"] not in seeded
    num = next(k for k in key if k["kind"] == "number")
    assert num["after"] in seeded and num["before"] != num["after"]
    report = "\n".join([
        "- [checked] line %d: the value %s differs from the results table" % (num["line"], num["after"]),
        "- [checked] '%s' is a causal claim from correlational data" % causal["after"],
        "- [checked] the data availability statement is missing",
    ])
    sc = CAL.score(report, key)
    assert sc["planted"] == 6 and sc["found"] == 3
    # a removed statement counts as found when a finding says it is missing, in other words or another language
    assert CAL.score("- line 40: no data and code availability statement, missing", key)["by_kind"]["statement"] == "1/1"
    assert sc["by_kind"]["number"] == "1/1" and sc["by_kind"]["citation"] == "0/2"


def test_seed_never_touches_the_reference_list():
    text = DRAFT + "\n## References\n\n[1] A. Author, 2020, 12(3), 45.6.\n[2] B. Author, 2021.\n"
    for s in range(1, 30):
        seeded, key = CAL.seed(text, seed_value=s)
        assert seeded.split("## References")[1] == text.split("## References")[1]


def test_format_command():
    cmd = F.build_command("d.md", "out.docx", bib=["r.bib"], csl="apa.csl", reference_doc="tpl.docx", lang="id-ID")
    assert cmd[:4] == ["pandoc", "d.md", "-o", "out.docx"]
    assert "--citeproc" in cmd and "--bibliography=r.bib" in cmd and "--csl=apa.csl" in cmd
    assert "--reference-doc=tpl.docx" in cmd and "lang=id-ID" in cmd
    with pytest.raises(ValueError):
        F.build_command("d.md", "out.tex", reference_doc="tpl.docx")
    with pytest.raises(ValueError):
        F.build_command("d.md", "out.xyz")


def test_cli_screen_and_seed(tmp_path, capsys):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text("id,decision,reason\n1,include,\n2,exclude,E1\n", encoding="utf-8")
    b.write_text("id,decision,reason\n1,exclude,E2\n2,exclude,E1\n", encoding="utf-8")
    code = cli.main(["screen", "compare", str(a), str(b), "--conflicts", str(tmp_path / "c.csv"),
                     "--agreed", str(tmp_path / "g.csv")])
    assert code == 0 and "conflicts for the adjudicator: 1" in capsys.readouterr().out
    d = tmp_path / "d.md"
    d.write_text(DRAFT, encoding="utf-8")
    assert cli.main(["seed", str(d), "--out", str(tmp_path / "s.md"), "--key", str(tmp_path / "k.json")]) == 0
    assert len(json.loads((tmp_path / "k.json").read_text(encoding="utf-8"))) == 6
    assert cli.main(["format", str(d), "--out", str(tmp_path / "o.docx"), "--dry-run"]) == 0

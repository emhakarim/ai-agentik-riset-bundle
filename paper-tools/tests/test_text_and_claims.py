from paper_tools import claims as C
from paper_tools import text as T

DRAFT = """# Introduction

GPU solvers have been reported to run faster [smith2020gpu]. No prior study has measured this on mobile GPUs
[lee2021mobile, kim2022edge]. We use the scale of Likert [likert1932].

## Methods

The effect size was d = 0.45 [@cohen1988; @lakens2013, p. 4]. Following \\citet[p.~3]{field2018}, outliers were
removed. Numbered style works too [3, 5-7]. Many works exist [a2020x, b2021y, c2022z, d2023w].

```
code [notacite2020x] is ignored
```

Plain sentence without citation. e.g. this one, et al. 2020 should not split.
"""


def test_citation_styles():
    assert T.citations("x [@cohen1988; @lakens2013, p. 4].") == (["cohen1988", "lakens2013"], "pandoc")
    assert T.citations(r"x \citet[p.~3]{field2018,b2019}.")[0] == ["field2018", "b2019"]
    assert T.citations("x [3, 5-7].") == (["3", "5", "6", "7"], "numeric")
    assert T.citations("x [smith2020gpu].") == (["smith2020gpu"], "bracket")
    assert T.citations("x [see below].") == ([], None)


def test_sentences_keep_sections_and_skip_code():
    ss = T.sentences(DRAFT)
    assert ss[0].section == "Introduction"
    assert any(s.section == "Methods" for s in ss)
    assert not any("notacite" in s.text for s in ss)
    assert any(s.text.startswith("Plain sentence") for s in ss)
    assert any("et al. 2020 should not split" in s.text for s in ss)


def test_claims_extract_and_types():
    rows = C.extract(DRAFT)
    by_first_key = {r["keys"].split(";")[0]: r for r in rows}
    assert by_first_key["smith2020gpu"]["type"] == "prior-work"
    assert C.claim_type("It was reported to run 10x faster [a2020b].") == "number"
    assert by_first_key["lee2021mobile"]["type"] == "gap"
    assert by_first_key["likert1932"]["type"] == "method"
    assert by_first_key["cohen1988"]["type"] == "number"
    s = C.summary(rows)
    # [3, 5-7] expands to four references, so it is a dump just like the four named keys
    assert s["citation_dumps"] == [by_first_key["3"]["id"], by_first_key["a2020x"]["id"]]


def test_indonesian_gap_cue():
    rows = C.extract("# Pendahuluan\n\nBelum ada penelitian yang mengukur hal ini [ali2024ukur].\n")
    assert rows[0]["type"] == "gap"


def test_write_csv(tmp_path):
    out = tmp_path / "c.csv"
    C.write_csv(C.extract(DRAFT), out)
    head = out.read_text(encoding="utf-8").splitlines()[0]
    assert head.startswith("id,section,line,type") and head.endswith("verdict,evidence,fix")


def test_apa_citations():
    assert T.citations("Basis buktinya lemah (Cuesta dkk., 2016).") == (["Cuesta_2016"], "apa")
    assert T.citations("Sumber daya (Card & Krueger, 1996; Duflo, 2001, p. 5).") == (["Card_1996", "Duflo_2001"], "apa")
    assert T.citations("Menurut Duflo (2001), sekolah baru menambah lama sekolah.") == (["Duflo_2001"], "apa")
    assert T.citations("Sumida dan Kawata (2021) dan Glewwe et al. (2011).")[0] == ["Sumida_2021", "Glewwe_2011"]
    assert T.citations("Fasilitas dasar (Espinosa Andrade dkk., 2024).")[0] == ["Espinosa_Andrade_2024"]
    assert T.citations("Laporan (OECD, 2019).")[0] == ["OECD_2019"]
    # not citations: statistics, ranges, acronyms followed by a year
    assert T.citations("Data (N = 300, 2019), rentang (2019-2026), PISA (2022).") == ([], None)


def test_apa_years_are_not_claim_numbers():
    rows = C.extract("# Intro\n\nBasis buktinya lemah (Cuesta dkk., 2016).\n\nRerata naik 5 poin (Duflo, 2001).\n")
    assert [r["type"] for r in rows] == ["background", "number"]

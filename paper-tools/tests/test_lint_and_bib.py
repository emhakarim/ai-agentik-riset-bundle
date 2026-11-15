from paper_tools import bib as B
from paper_tools import lint as L

BIB = """
@article{smith2020gpu,
  author = {Smith, John and Doe, Jane},
  title = {{GPU} solvers},
  journal = "J. Comp.",
  year = 2020, volume = {12}, number = {3}, pages = {1--10},
  doi = {https://doi.org/10.1000/xyz},
}
@book{likert1932, author={Likert, R.}, title={A technique}, year={1932}}
@misc{unused2025, title={Never cited}, year={2025},}
"""

DRAFT = """# Introduction

GPU solvers are fast [smith2020gpu]. A scale was used [likert1932]. Missing one [ghost2023x]. TODO add more.

**Table 1.** Results.

Table 1 and Table 2 show it. Figure 3 is cited.

**Figure 4.** Never referenced.

## Conflict of Interest

None.

## Funding

None.
"""


def test_bib_parse():
    e = B.parse(BIB)
    assert set(e) == {"smith2020gpu", "likert1932", "unused2025"}
    assert e["smith2020gpu"]["title"] == "{GPU} solvers"
    assert e["smith2020gpu"]["journal"] == "J. Comp."
    assert B.year(e["smith2020gpu"]) == 2020
    assert B.doi(e["smith2020gpu"]) == "10.1000/xyz"
    assert e["unused2025"]["title"] == "Never cited"


def test_lint_checks():
    entries = B.parse(BIB)
    assert [p["match"] for p in L.placeholders(DRAFT)] == ["TODO"]
    cv = L.citations_vs_bib(DRAFT, entries)
    assert cv["missing_in_bib"] == ["ghost2023x"] and cv["uncited_in_bib"] == ["unused2025"]
    fl = L.floats(DRAFT)
    assert {(u["kind"], u["number"]) for u in fl["undefined"]} == {("table", 2), ("figure", 3)}
    assert [(u["kind"], u["number"]) for u in fl["unreferenced"]] == [("figure", 4)]
    st = L.statements(DRAFT, "general")
    assert st["missing"] == ["data_availability", "ai_use"]


def test_indonesian_statements():
    st = L.statements("## Ketersediaan Data\n\nx\n\n**Penggunaan AI**\n\ny\n", ["data_availability", "ai_use"])
    assert st["missing"] == []


def test_recency_and_long_sentences():
    entries = B.parse(BIB)
    rc = L.recency(DRAFT, entries, years=5, minimum=0.8, as_of=2024)
    assert rc["with_year"] == 2 and rc["recent"] == 1 and rc["share"] == 0.5 and rc["ok"] is False
    long = "# A\n\n" + " ".join(["word"] * 45) + ".\n"
    assert L.long_sentences(long)[0]["words"] == 45


def test_bib_issues_duplicate_and_unreadable():
    bad = """@book{2019, talis and the literature_2019, ISSN={1993-9019}, year={2019} }
@book{2019, url={x}, year={2019}}
@article{ok2020, author={A, B}, year={2020}}
"""
    probs = B.issues(bad)
    kinds = sorted(p["problem"].split(";")[0].split(" (")[0] for p in probs)
    assert kinds == ["duplicate key", "unreadable text in entry"]
    assert all(p["key"] == "2019" for p in probs)
    assert B.issues(BIB) == []


def test_apa_keys_resolve_to_bib_keys():
    entries = B.parse("@article{smith2020gpu, author={Smith, John and Doe, Jane}, year={2020}}\n"
                      "@article{Espinosa_Andrade_2024, author={Espinosa Andrade, Ana}, year={2024}}")
    assert L.resolve(["Smith_2020", "Espinosa_Andrade_2024", "Ghost_2021", "3"], entries) == \
        ["smith2020gpu", "Espinosa_Andrade_2024", "Ghost_2021", "3"]
    cv = L.citations_vs_bib("# A\n\nFast (Smith & Doe, 2020). Missing (Ghost, 2021).\n", entries)
    assert cv["missing_in_bib"] == ["Ghost_2021"] and cv["styles"] == ["apa"]


def test_apa_year_suffixes_map_to_distinct_entries():
    # Zetta finding C: (Retnawati, 2016a; Retnawati, 2016b) must resolve to two different entries
    entries = B.parse("@book{r1, author={Retnawati, Heri}, title={Validitas reliabilitas}, year={2016}}\n"
                      "@book{r2, author={Retnawati, Heri}, title={Analisis kuantitatif instrumen}, year={2016}}")
    assert L.resolve(["Retnawati_2016a", "Retnawati_2016b"], entries) == ["r2", "r1"]  # a/b by title order
    cv = L.citations_vs_bib("# A\n\nSatu (Retnawati, 2016a; Retnawati, 2016b).\n", entries)
    assert cv["missing_in_bib"] == [] and cv["uncited_in_bib"] == []

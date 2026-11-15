import zipfile

from paper_tools import cli
from paper_tools import reads as RD
from paper_tools import records as RECS
from paper_tools import screening as SC

RIS = """TY  - JOUR
AU  - Smith, John
AU  - Doe, Jane
TI  - Problem-based learning in physics
T2  - Journal of Physics Education
PY  - 2021
AB  - We studied PBL
  in two schools.
DO  - https://doi.org/10.1/ABC
ER  -

TY  - JOUR
TI  - Second record
PY  - 2019///
ER  -
"""

NBIB = """PMID- 12345
TI  - Flipped classroom and nursing students: a
      randomized trial.
AB  - Background text.
AU  - Lee K
DP  - 2022 Mar
JT  - Nurse Education Today
LID - 10.1016/j.nedt.2022.1 [doi]

PMID- 67890
TI  - Another trial.
DP  - 2020
"""

WOS = """FN Clarivate Analytics Web of Science
VR 1.0
PT J
AU Kim, A
   Park, B
TI Gamification in mathematics
   classrooms
SO COMPUTERS & EDUCATION
PY 2023
DI 10.1016/j.compedu.2023.9
UT WOS:000111
ER

EF
"""


def test_readers(tmp_path):
    ris = RECS.read_ris(RIS, "scopus")
    assert [r["title"] for r in ris] == ["Problem-based learning in physics", "Second record"]
    assert ris[0]["abstract"] == "We studied PBL in two schools." and ris[0]["doi"] == "10.1/ABC"
    assert ris[0]["authors"] == "Smith, John; Doe, Jane" and ris[1]["year"] == "2019"
    nb = RECS.read_nbib(NBIB)
    assert nb[0]["id"] == "PMID12345" and nb[0]["title"] == "Flipped classroom and nursing students: a randomized trial."
    assert nb[0]["doi"] == "10.1016/j.nedt.2022.1" and nb[0]["year"] == "2022" and len(nb) == 2
    wos = RECS.read_wos(WOS)
    assert wos[0]["title"] == "Gamification in mathematics classrooms" and wos[0]["authors"] == "Kim, A; Park, B"
    assert wos[0]["id"] == "WOS:000111" and wos[0]["doi"] == "10.1016/j.compedu.2023.9"
    (tmp_path / "a.ris").write_text(RIS, encoding="utf-8")
    (tmp_path / "b.nbib").write_text(NBIB, encoding="utf-8")
    (tmp_path / "c.txt").write_text(WOS, encoding="utf-8")
    allr = RECS.merge([tmp_path / "a.ris", tmp_path / "b.nbib", tmp_path / "c.txt"])
    assert len(allr) == 5 and len({r["id"] for r in allr}) == 5


def test_pabak_seed_xlsx(tmp_path):
    a = ["exclude"] * 18 + ["include", "exclude"]
    b = ["exclude"] * 18 + ["exclude", "include"]
    assert SC.cohen_kappa(a, b) < 0  # kappa collapses at low prevalence
    assert abs(SC.pabak(a, b) - 0.8) < 1e-9  # PABAK: 2*0.9 - 1
    final = {"1": {"decision": "include"}, "2": {"decision": "exclude"}}
    assert SC.seed_check(final, ["1", "2", "3"]) == ["2", "3"]
    out = tmp_path / "log.xlsx"
    SC.write_xlsx({"agreed": [{"id": "1", "decision": "include"}], "empty": []}, out)
    with zipfile.ZipFile(out) as z:
        assert "xl/worksheets/sheet2.xml" in z.namelist()
        assert "include" in z.read("xl/worksheets/sheet1.xml").decode("utf-8")


DRAFT = """# Results

The effect was d = 0.45 [smith2020a]. Prior studies reported PBL in schools [lee2019b].
No prior study has measured this in Indonesia [kim2021c].
"""


def test_reads_ledger_and_gate(tmp_path, capsys):
    led = tmp_path / "reads.csv"
    RD.mark(led, ["smith2020a"], "abstract")
    RD.mark(led, ["kim2021c"], "full", note="pdf from author")
    out = RD.check(DRAFT, RD.load(led))
    assert out["counts"]["full"] == 1 and out["counts"]["abstract"] == 1 and out["counts"]["unknown"] == 1
    weak = out["claims_needing_full_text"]
    assert [w["keys"] for w in weak] == [["smith2020a"]]  # number claim on an abstract-only read
    d = tmp_path / "d.md"
    d.write_text(DRAFT, encoding="utf-8")
    cli.main(["gate", str(d), "--profile", "none", "--reads", str(led), "--lang", "en"])
    assert "not read in full" in capsys.readouterr().out
    assert cli.main(["reads", "mark", "lee2019b", "--status", "none", "--file", str(led)]) == 0


def test_pabak_k_is_fixed_not_counted_from_sample():
    # Zetta finding B: one 'maybe' must not raise PABAK for the same agreement
    a = ["exclude"] * 8 + ["include", "maybe"]
    b = ["exclude"] * 8 + ["exclude", "include"]
    assert abs(SC.pabak(a, b) - SC.pabak(a, b, k=2)) < 1e-12
    out = SC.compare([{"id": str(i), "decision": d} for i, d in enumerate(a)],
                     [{"id": str(i), "decision": d} for i, d in enumerate(b)])
    # advance-vs-exclude: records 8 (include vs exclude) disagree, record 9 (maybe vs include) agree -> po = 0.9
    assert abs(out["pabak"] - 0.8) < 1e-9 and "k = 2" in out["pabak_basis"]

from paper_tools import cli

DRAFT = """# Introduction

Prior work reported 12.5 ms [smith2020gpu].

## Data Availability

Data on request.

## Conflict of Interest

None.

## Funding

None.

## Use of AI

AI tools were used for language editing; the authors checked all output.
"""
BIB = "@article{smith2020gpu, author={Smith, J.}, title={T}, year={2023}}\n"


def test_gate_pass_and_fail(tmp_path, capsys):
    d, b, src = tmp_path / "d.md", tmp_path / "r.bib", tmp_path / "res"
    src.mkdir()
    (src / "t.csv").write_text("x\n12.48\n", encoding="utf-8")
    d.write_text(DRAFT, encoding="utf-8")
    b.write_text(BIB, encoding="utf-8")
    code = cli.main(["gate", str(d), "--bib", str(b), "--sources", str(src), "--recent-min", "0.8",
                     "--as-of", "2026", "--lang", "en", "--json", str(tmp_path / "o.json")])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "Summary: PASS" in out

    d.write_text(DRAFT.replace("## Use of AI", "## Notes") + "\nTODO\n", encoding="utf-8")
    code = cli.main(["gate", str(d), "--bib", str(b), "--lang", "id"])
    out = capsys.readouterr().out
    assert code == 1 and "Ringkasan: GAGAL" in out and "placeholder" in out


def test_claims_command(tmp_path, capsys):
    d = tmp_path / "d.md"
    d.write_text(DRAFT, encoding="utf-8")
    assert cli.main(["claims", str(d), "--out", str(tmp_path / "c.csv")]) == 0
    assert '"claims": 1' in capsys.readouterr().out

"""CLI: parameter daftar tanpa JSON, --params, help alat, dan hasil yang sama dengan bentuk JSON."""
import json

import pytest

from edu_stats import cli


@pytest.fixture()
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("EDU_STATS_AUDIT_DIR", str(tmp_path / "audit"))
    f = tmp_path / "d.csv"
    rows = ["kelompok,skor,B1,B2,B3"]
    vals = [("A", 70, 3, 4, 3), ("A", 74, 4, 4, 4), ("A", 69, 2, 3, 3), ("A", 72, 4, 5, 4), ("A", 75, 5, 4, 5),
            ("B", 80, 4, 5, 5), ("B", 83, 5, 5, 4), ("B", 79, 3, 4, 4), ("B", 85, 5, 5, 5), ("B", 81, 4, 4, 5)]
    rows += [",".join(map(str, v)) for v in vals]
    f.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return f


def _run(capsys, *args):
    code = cli.main(list(args))
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_parse_list_forms():
    assert cli._parse_value("B1,B2,B3", as_list=True) == ["B1", "B2", "B3"]
    assert cli._parse_value('["B1","B2"]', as_list=True) == ["B1", "B2"]
    assert cli._parse_value("[B1, B2]", as_list=True) == ["B1", "B2"]   # PowerShell membuang tanda kutip
    assert cli._parse_value("1,2,3", as_list=True) == [1, 2, 3]
    assert cli._parse_value("B1", as_list=True) == ["B1"]


def test_parse_scalar_unchanged():
    assert cli._parse_value("0.05") == 0.05
    assert cli._parse_value("true") is True
    assert cli._parse_value("nilai") == "nilai"
    assert cli._parse_value("a,b") == "a,b"   # bukan parameter daftar: tetap teks


def test_comma_list_equals_json_form(data, capsys):
    c1, j1 = _run(capsys, "run", "reliability", f"file={data}", "items=B1,B2,B3")
    c2, j2 = _run(capsys, "run", "reliability", f"file={data}", 'items=["B1","B2","B3"]')
    assert c1 == 0 and c2 == 0
    assert j1["result"] == j2["result"]


def test_powershell_stripped_quotes(data, capsys):
    code, out = _run(capsys, "run", "descriptives", f"file={data}", "columns=[skor,B1]")
    assert code == 0, out
    assert "error" not in out


def test_groups_order_comma(data, capsys):
    code, out = _run(capsys, "run", "ttest_independent", f"file={data}", "dv=skor", "group=kelompok", "groups=B,A")
    assert code == 0, out
    assert out["apa"][0].index("B (") < out["apa"][0].index("A (")


def test_params_file_and_override(data, tmp_path, capsys):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"file": str(data), "dv": "skor", "group": "kelompok", "groups": ["A", "B"]}), encoding="utf-8")
    code, out = _run(capsys, "run", "ttest_independent", "--params", str(p), "groups=B,A")
    assert code == 0, out
    assert out["apa"][0].index("B (") < out["apa"][0].index("A (")


def test_params_file_missing(capsys, tmp_path):
    assert cli.main(["run", "descriptives", "--params", str(tmp_path / "tidak-ada.json")]) == 2


def test_help_tool_lists_parameters(capsys):
    assert cli.main(["help", "reliability"]) == 0
    out = capsys.readouterr().out
    assert "items" in out and "daftar" in out and "Contoh: edu-stats run reliability" in out


def test_help_unknown_tool(capsys):
    assert cli.main(["help", "tidak_ada"]) == 2

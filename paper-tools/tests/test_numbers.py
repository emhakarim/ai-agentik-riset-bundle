import json

from paper_tools import numbers as N


def test_parse_number_formats():
    assert N.parse_number("0,085") == [(0.085, 3)]
    assert N.parse_number("2.37491") == [(2.37491, 5)]
    assert N.parse_number("1.234.567") == [(1234567.0, 0)]
    assert N.parse_number("1,234.5") == [(1234.5, 1)]
    assert N.parse_number("1.234,5") == [(1234.5, 1)]
    assert sorted(N.parse_number("1,234")) == [(1.234, 3), (1234.0, 0)]  # ambiguous: both readings
    assert N.parse_number("−0,011") == [(-0.011, 3)]
    assert N.parse_number("1,234", decimal=",") == [(1.234, 3)]


def test_trace_matches_rounding_percent_and_comma(tmp_path):
    (tmp_path / "res.csv").write_text("metric,value\nd,0.4512\nshare,0.873\nn,128\n", encoding="utf-8")
    (tmp_path / "res.json").write_text(json.dumps({"f": 2.374912, "nested": [{"p": 0.0012}]}), encoding="utf-8")
    draft = ("# Results\n\nThe effect was d = 0,45 with n = 128 and 87.3% agreed. The peak is 2.3749 GHz, "
             "p = .0012. The other value 3.14 is not from the data. In 2024 we used 7 classes.\n\n"
             "# References\n\nSmith 2020, 45(3), 123-130.\n")
    rows = N.trace(draft, [tmp_path])
    got = {r["raw"]: r["traced"] for r in rows}
    assert got["0,45"] and got["128"] and got["87.3%"] and got["2.3749"]
    assert got["3.14"] is False
    assert "2024" not in got and "7" not in got  # years and small integers are ignored
    assert not any(r["section"] == "References" for r in rows)


def test_labels_are_not_numbers():
    rows = N.manuscript_numbers("# R\n\nTable 3 and Section 2.1 and Figure 12 show 45.6 units.\n")
    assert [r["raw"] for r in rows] == ["45.6"]


def test_sign_flip_is_flagged_not_traced(tmp_path):
    # Zetta finding A: r = -0.45 in the output, +0.45 in the manuscript must not pass as traced
    (tmp_path / "res.csv").write_text("metric,value\nr,-0.4512\nbeta,0.3210\n", encoding="utf-8")
    draft = "# Results\n\nThe correlation was r = 0.45 and beta = 0.32, while r = −0.45 is correct.\n"
    rows = {(r["raw"], r["line"]): r for r in N.trace(draft, [tmp_path])}
    flipped = [r for r in rows.values() if r["raw"] == "0.45"][0]
    assert not flipped["traced"] and flipped["sign_flipped"]
    assert [r for r in rows.values() if r["raw"] == "0.32"][0]["traced"]
    correct = [r for r in rows.values() if r["raw"] in ("−0.45", "-0.45")][0]
    assert correct["traced"] and not correct["sign_flipped"]

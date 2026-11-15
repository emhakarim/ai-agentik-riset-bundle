"""Validasi aiken_v, cvr_lawshe, item_analysis_cognitive terhadap tabel terbitan dan perhitungan independen."""
import itertools

import numpy as np
import pandas as pd
import pingouin as pg
import pytest

from edu_stats import instrument, tools
from edu_stats.data import load


def _csv(tmp_path, name, df):
    p = tmp_path / name
    df.to_csv(p, index=False)
    return load(str(p))


# ------------------------------------------------ Aiken's V
def test_aiken_table_value(tmp_path):
    # Aiken (1985), Tabel 1: 5 penilai, 5 kategori -> V = .80, p = .040
    df = pd.DataFrame({"butir": ["B1", "B2"], "A1": [5, 3], "A2": [5, 4], "A3": [4, 3], "A4": [5, 2], "A5": [5, 3]})
    out = instrument.aiken_v(_csv(tmp_path, "a.csv", df), ["A1", "A2", "A3", "A4", "A5"], 1, 5, item_col="butir")
    b1, b2 = out["result"]["items"]
    assert b1["V"] == pytest.approx((4 + 4 + 3 + 4 + 4) / 20)
    assert b1["V_critical"] == pytest.approx(0.80)
    assert instrument._aiken_pvalue(16, 5, 5) == pytest.approx(126 / 3125)  # = .0403
    assert b1["valid"] and not b2["valid"]
    assert out["result"]["items_valid"] == ["B1"]


def test_aiken_pvalue_bruteforce():
    # bandingkan dengan enumerasi lengkap semua kombinasi skor
    for n, c in [(3, 4), (4, 4), (6, 3)]:
        sums = [sum(t) for t in itertools.product(range(c), repeat=n)]
        for s in range(n * (c - 1) + 1):
            expect = sum(x >= s for x in sums) / len(sums)
            assert instrument._aiken_pvalue(s, n, c) == pytest.approx(expect, abs=1e-12)


def test_aiken_rejects_out_of_range(tmp_path):
    df = pd.DataFrame({"A1": [5, 6], "A2": [4, 4]})
    with pytest.raises(Exception, match="di luar"):
        instrument.aiken_v(_csv(tmp_path, "x.csv", df), ["A1", "A2"], 1, 5)


# ------------------------------------------------ CVR Lawshe
@pytest.mark.parametrize("n,ne_crit,cvr_crit", [
    # Ayre & Scally (2014), Tabel 2 (α = .05, satu sisi)
    (5, 5, 1.00), (6, 6, 1.00), (7, 7, 1.00), (8, 7, 0.75), (9, 8, 0.778), (10, 9, 0.80), (11, 9, 0.636),
    (12, 10, 0.667), (13, 10, 0.538), (14, 11, 0.571), (15, 12, 0.60), (20, 15, 0.50), (40, 26, 0.30)])
def test_cvr_critical_ayre_scally(n, ne_crit, cvr_crit):
    k, c = instrument._cvr_crit(n, 0.05)
    assert k == ne_crit
    assert c == pytest.approx(cvr_crit, abs=1e-3)


def test_cvr_items_and_cvi(tmp_path):
    # 10 ahli; E = esensial. Butir 1: 10 E, butir 2: 9 E, butir 3: 6 E
    rows = [["E"] * 10, ["E"] * 9 + ["U"], ["E"] * 6 + ["U", "U", "T", "T"]]
    df = pd.DataFrame(rows, columns=[f"ahli{i}" for i in range(1, 11)])
    df.insert(0, "butir", ["K1", "K2", "K3"])
    out = instrument.cvr_lawshe(_csv(tmp_path, "c.csv", df), [f"ahli{i}" for i in range(1, 11)], ["e"], item_col="butir")
    cvr = [r["CVR"] for r in out["result"]["items"]]
    assert cvr == pytest.approx([1.0, 0.8, 0.2])
    assert out["result"]["items_retained"] == ["K1", "K2"]
    assert out["result"]["CVI"] == pytest.approx(0.9)
    # kode numerik: 3 = esensial (skala 1–3)
    num = pd.DataFrame({f"a{i}": [3, 3 if i < 9 else 2] for i in range(10)})
    out2 = instrument.cvr_lawshe(_csv(tmp_path, "n.csv", num), list(num.columns), [3])
    assert [r["n_essential"] for r in out2["result"]["items"]] == [10, 9]
    with pytest.raises(Exception, match="Tidak ada satu pun"):
        instrument.cvr_lawshe(_csv(tmp_path, "n2.csv", num), list(num.columns), ["E"])


# ------------------------------------------------ analisis butir kognitif
@pytest.fixture
def mc_test(tmp_path):
    rng = np.random.default_rng(12)
    n, k = 60, 8
    theta = rng.normal(size=n)
    b = np.linspace(-1.5, 1.5, k)
    key = {f"S{j + 1}": "ABCD"[j % 4] for j in range(k)}
    resp = {}
    for j in range(k):
        correct = rng.random(n) < 1 / (1 + np.exp(-(1.7 * (theta - b[j]))))
        wrong = rng.choice([o for o in "ABCD" if o != key[f"S{j + 1}"]], n)
        resp[f"S{j + 1}"] = np.where(correct, key[f"S{j + 1}"], wrong)
    resp["S8"] = rng.choice(list("ABCD"), n)  # butir acak -> D rendah
    df = pd.DataFrame(resp)
    df.loc[0, "S1"] = None  # jawaban kosong
    return _csv(tmp_path, "mc.csv", df), df, key


def test_item_analysis_with_key(mc_test):
    ds, df, key = mc_test
    out = instrument.item_analysis_cognitive(ds, list(key), key=key)
    scored = pd.DataFrame({i: (df[i] == key[i]).astype(float) for i in key})
    total = scored.sum(axis=1)
    r = out["result"]
    assert r["n_group"] == round(0.27 * 60) == 16
    assert r["kr20"] == pytest.approx(pg.cronbach_alpha(scored)[0])
    order = np.argsort(-total.to_numpy(), kind="mergesort")
    up, lo = order[:16], order[-16:]
    for row in r["items"]:
        x = scored[row["item"]].to_numpy()
        assert row["P"] == pytest.approx(x.mean())
        assert row["D"] == pytest.approx(x[up].mean() - x[lo].mean())
        assert row["r_pbi_corrected"] == pytest.approx(np.corrcoef(x, total - x)[0, 1])
        props = sum(d["prop_all"] for d in row["distractors"]) + row["prop_blank"]
        assert props == pytest.approx(1.0)
    s1 = next(x for x in r["items"] if x["item"] == "S1")
    assert s1["prop_blank"] == pytest.approx(1 / 60)
    assert any("kosong" in n for n in out["notes"])


def test_item_analysis_binary_and_guards(tmp_path):
    df = pd.DataFrame({"a": [1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0], "b": [1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0],
                       "c": [0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0]})
    out = instrument.item_analysis_cognitive(_csv(tmp_path, "b.csv", df), ["a", "b", "c"])
    assert out["result"]["items"][0]["P"] == pytest.approx(8 / 12)
    assert "distractors" not in out["result"]["items"][0]
    bad = pd.DataFrame({"a": [1, 2] * 6, "b": [0, 1] * 6})
    with pytest.raises(Exception, match="0/1"):
        instrument.item_analysis_cognitive(_csv(tmp_path, "x.csv", bad), ["a", "b"])
    with pytest.raises(Exception, match="Kunci"):
        instrument.item_analysis_cognitive(_csv(tmp_path, "y.csv", df), ["a", "b"], key={"a": "A"})


def test_registered_in_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("EDU_STATS_AUDIT_DIR", str(tmp_path / "audit"))
    for t in ("aiken_v", "cvr_lawshe", "item_analysis_cognitive"):
        assert t in tools.list_tools()

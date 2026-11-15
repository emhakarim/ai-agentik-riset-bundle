"""Validasi κ, ICC, mediasi, moderasi terhadap contoh terbitan, statsmodels, pingouin, dan perhitungan independen."""
import json

import numpy as np
import pandas as pd
import pingouin as pg
import pytest
import statsmodels.api as sm

from edu_stats import instrument, relate, tools
from edu_stats.data import load


def _csv(tmp_path, name, df):
    p = tmp_path / name
    df.to_csv(p, index=False)
    return load(str(p))


# ------------------------------------------------ kappa
def test_cohen_kappa_hand_computed(tmp_path):
    # tabel 2×2: [[20, 5], [10, 15]] -> po = .70, pe = (25·30 + 25·20)/50² = .50, κ = .40
    r1 = ["Y"] * 25 + ["N"] * 25
    r2 = ["Y"] * 20 + ["N"] * 5 + ["Y"] * 10 + ["N"] * 15
    out = instrument.inter_rater_kappa(_csv(tmp_path, "k.csv", pd.DataFrame({"g1": r1, "g2": r2})), ["g1", "g2"])
    r = out["result"]
    assert r["kappa"] == pytest.approx(0.40)
    assert r["percent_agreement"] == pytest.approx(70.0)
    assert r["label"].startswith("lemah")


def test_weighted_kappa_hand_computed(tmp_path):
    rng = np.random.default_rng(2)
    a = rng.integers(1, 5, 80)
    b = np.clip(a + rng.integers(-1, 2, 80), 1, 4)
    out = instrument.inter_rater_kappa(_csv(tmp_path, "w.csv", pd.DataFrame({"a": a, "b": b})), ["a", "b"], weights="quadratic")
    cats = [1, 2, 3, 4]
    O = pd.crosstab(a, b).reindex(index=cats, columns=cats, fill_value=0).to_numpy() / 80
    E = np.outer(O.sum(1), O.sum(0))
    W = np.array([[(i - j) ** 2 for j in range(4)] for i in range(4)]) / 9
    expect = 1 - (W * O).sum() / (W * E).sum()
    assert out["result"]["kappa"] == pytest.approx(expect)


def test_fleiss_kappa_published_example(tmp_path):
    # contoh Fleiss' kappa yang lazim dipakai (10 subjek, 14 penilai, 5 kategori): κ = 0.210
    counts = [[0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0], [2, 2, 8, 1, 1],
              [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2], [6, 5, 2, 1, 0], [0, 2, 2, 3, 7]]
    rows = [sum(([c + 1] * k for c, k in enumerate(row)), []) for row in counts]
    df = pd.DataFrame(rows, columns=[f"r{i}" for i in range(14)])
    out = instrument.inter_rater_kappa(_csv(tmp_path, "f.csv", df), list(df.columns))
    assert out["result"]["method"] == "Fleiss' κ"
    assert out["result"]["kappa"] == pytest.approx(0.210, abs=5e-4)


# ------------------------------------------------ ICC
def test_icc_vs_pingouin(tmp_path):
    rng = np.random.default_rng(6)
    true = rng.normal(70, 10, 30)
    df = pd.DataFrame({f"guru{j}": true + rng.normal(j * 1.5, 4, 30) for j in range(4)}).round(1)
    out = instrument.icc(_csv(tmp_path, "i.csv", df), list(df.columns))["result"]["icc"]
    long = df.reset_index().melt(id_vars="index", var_name="rater", value_name="score")
    ref = pg.intraclass_corr(long, targets="index", raters="rater", ratings="score").set_index("Type")
    # pingouin 0.7 memakai notasi McGraw & Wong: A = absolute agreement (ICC2), C = consistency (ICC3)
    for mine, theirs in [("ICC1", "ICC(1,1)"), ("ICC2", "ICC(A,1)"), ("ICC3", "ICC(C,1)"),
                         ("ICC1k", "ICC(1,k)"), ("ICC2k", "ICC(A,k)"), ("ICC3k", "ICC(C,k)")]:
        assert out[mine]["value"] == pytest.approx(ref.loc[theirs, "ICC"]), mine
        assert out[mine]["F"] == pytest.approx(ref.loc[theirs, "F"]), mine
        lo, hi = ref.loc[theirs, "CI95"]
        assert out[mine]["ci"][0] == pytest.approx(lo, abs=0.006), mine
        assert out[mine]["ci"][1] == pytest.approx(hi, abs=0.006), mine


# ------------------------------------------------ mediasi
@pytest.fixture
def medmod(tmp_path):
    rng = np.random.default_rng(31)
    n = 200
    X = rng.normal(0, 1, n)
    M = 0.5 * X + rng.normal(0, 1, n)
    W = rng.normal(0, 1, n)
    Y = 0.3 * X + 0.4 * M + 0.2 * W + 0.25 * X * W + rng.normal(0, 1, n)
    df = pd.DataFrame({"dukungan": X, "efikasi": M, "motivasi": W, "hasil": Y, "kelas_e": (W > 0).astype(int)}).round(4)
    return _csv(tmp_path, "mm.csv", df), df


def test_mediation_paths_and_bootstrap(medmod, tmp_path, monkeypatch):
    ds, df = medmod
    out = relate.mediation(ds, "dukungan", "efikasi", "hasil", n_boot=2000)
    r = out["result"]
    ols = lambda y, xs: sm.OLS(df[y], sm.add_constant(df[xs])).fit().params  # noqa: E731
    a = ols("efikasi", ["dukungan"])["dukungan"]
    pb = ols("hasil", ["dukungan", "efikasi"])
    c = ols("hasil", ["dukungan"])["dukungan"]
    paths = {p["path"]: p["B"] for p in r["paths"]}
    assert paths["a"] == pytest.approx(a) and paths["b"] == pytest.approx(pb["efikasi"])
    assert paths["c"] == pytest.approx(c) and paths["c'"] == pytest.approx(pb["dukungan"])
    assert r["indirect_effect"] == pytest.approx(a * pb["efikasi"])
    assert r["indirect_effect"] == pytest.approx(paths["c"] - paths["c'"])  # identitas OLS: c = c' + ab
    ref = pg.mediation_analysis(data=df, x="dukungan", m="efikasi", y="hasil", n_boot=2000, seed=1)
    ref_ci = ref[ref.path == "Indirect"][["CI2.5", "CI97.5"]].to_numpy()[0]
    assert r["indirect_ci_boot"][0] == pytest.approx(ref_ci[0], abs=0.03)
    assert r["indirect_ci_boot"][1] == pytest.approx(ref_ci[1], abs=0.03)
    assert r["indirect_significant"]
    # seed tetap -> replay identik
    monkeypatch.setenv("EDU_STATS_AUDIT_DIR", str(tmp_path / "audit"))
    run = tools.run_tool("mediation", {"file": ds.path, "x": "dukungan", "m": "efikasi", "y": "hasil", "n_boot": 1000})
    rep = tools.replay(run["audit"]["audit_id"])
    assert rep["identical"]
    json.dumps(run, allow_nan=False)


# ------------------------------------------------ moderasi
def test_moderation_interaction_and_simple_slopes(medmod):
    ds, df = medmod
    out = relate.moderation(ds, "hasil", "dukungan", "motivasi")
    r = out["result"]
    xc, wc = df.dukungan - df.dukungan.mean(), df.motivasi - df.motivasi.mean()
    full = sm.OLS(df.hasil, sm.add_constant(pd.DataFrame({"x": xc, "w": wc, "xw": xc * wc}))).fit()
    assert r["coefficients"][3]["B"] == pytest.approx(full.params["xw"])
    assert r["coefficients"][3]["p"] == pytest.approx(full.pvalues["xw"])
    # simple slope pada W = M + 1SD = koefisien X bila W di-center ulang di titik itu
    for s in r["simple_slopes"]:
        w2 = df.motivasi - s["w_value"]
        refit = sm.OLS(df.hasil, sm.add_constant(pd.DataFrame({"x": xc, "w": w2, "xw": xc * w2}))).fit()
        assert s["slope"] == pytest.approx(refit.params["x"])
        assert s["se"] == pytest.approx(refit.bse["x"])
    assert r["p_change"] == pytest.approx(r["coefficients"][3]["p"])  # uji ΔR² setara uji t interaksi
    out_b = relate.moderation(ds, "hasil", "dukungan", "kelas_e")
    assert out_b["result"]["w_binary"] and [s["at"] for s in out_b["result"]["simple_slopes"]] == ["W = 0", "W = 1"]

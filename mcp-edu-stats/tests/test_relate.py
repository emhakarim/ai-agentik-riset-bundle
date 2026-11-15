"""Validasi relate.py terhadap scipy, pingouin, dan statsmodels."""
import numpy as np
import pandas as pd
import pingouin as pg
import pytest
from scipy import stats

from edu_stats import relate
from edu_stats.data import load


@pytest.fixture
def survey(tmp_path):
    rng = np.random.default_rng(5)
    n = 120
    motivasi = rng.normal(3.5, 0.6, n)
    efikasi = 0.5 * motivasi + rng.normal(0, 0.5, n)
    jam = rng.poisson(6, n).astype(float)
    hasil = 40 + 6 * motivasi + 4 * efikasi + 0.8 * jam + rng.normal(0, 6, n)
    df = pd.DataFrame({"motivasi": motivasi, "efikasi diri": efikasi, "jam_belajar": jam, "hasil": hasil}).round(3)
    df.loc[3, "jam_belajar"] = np.nan  # satu nilai kosong untuk menguji pairwise vs listwise
    p = tmp_path / "survey.csv"
    df.to_csv(p, index=False)
    return load(str(p)), df


@pytest.mark.parametrize("method", ["pearson", "spearman", "kendall"])
def test_correlation_vs_pingouin(survey, method):
    ds, df = survey
    out = relate.correlation(ds, ["motivasi", "efikasi diri", "jam_belajar"], method=method)
    for row in out["result"]["pairs"]:
        sub = df[[row["var1"], row["var2"]]].dropna()
        ref = pg.corr(sub[row["var1"]], sub[row["var2"]], method=method)
        assert row["n"] == ref["n"].iloc[0]
        assert row["coefficient"] == pytest.approx(ref["r"].iloc[0])
        assert row["p"] == pytest.approx(ref["p_val"].iloc[0] if "p_val" in ref else ref["p-val"].iloc[0])
    n_pairs = [r["n"] for r in out["result"]["pairs"]]
    assert n_pairs == [120, 119, 119]  # pairwise deletion


def test_pearson_ci_fisher(survey):
    ds, df = survey
    row = relate.correlation(ds, ["motivasi", "hasil"])["result"]["pairs"][0]
    ref = stats.pearsonr(df.motivasi, df.hasil).confidence_interval(0.95)
    assert row["ci"][0] == pytest.approx(ref.low, abs=1e-10)
    assert row["ci"][1] == pytest.approx(ref.high, abs=1e-10)


def test_regression_vs_pingouin(survey):
    ds, df = survey
    preds = ["motivasi", "efikasi diri", "jam_belajar"]
    out = relate.regression(ds, "hasil", preds)
    d = df[["hasil", *preds]].dropna()
    ref = pg.linear_regression(d[preds], d["hasil"])
    coefs = out["result"]["coefficients"]
    for mine, (_, r) in zip(coefs, ref.iterrows()):
        assert mine["B"] == pytest.approx(r["coef"])
        assert mine["se"] == pytest.approx(r["se"])
        assert mine["p"] == pytest.approx(r["pval"])
    m = out["result"]["model"]
    assert m["R2"] == pytest.approx(ref["r2"].iloc[0])
    assert m["adj_R2"] == pytest.approx(ref["adj_r2"].iloc[0])
    assert m["n"] == 119 and out["input"]["n_dropped"] == 1
    # beta = B pada data terstandar
    z = (d - d.mean()) / d.std(ddof=1)
    zref = pg.linear_regression(z[preds], z["hasil"])
    for mine, b in zip(coefs[1:], zref["coef"].iloc[1:]):
        assert mine["beta"] == pytest.approx(b)
    # VIF prediktor 1 = 1/(1 − R² dari regresi motivasi atas prediktor lain)
    r2_aux = pg.linear_regression(d[["efikasi diri", "jam_belajar"]], d["motivasi"])["r2"].iloc[0]
    assert coefs[1]["vif"] == pytest.approx(1 / (1 - r2_aux))
    # sr² = R² penuh − R² tanpa prediktor itu
    r2_wo = pg.linear_regression(d[["efikasi diri", "jam_belajar"]], d["hasil"])["r2"].iloc[0]
    assert coefs[1]["sr2"] == pytest.approx(m["R2"] - r2_wo)


def _write(tmp_path, name, df):
    p = tmp_path / name
    df.to_csv(p, index=False)
    return load(str(p))


def test_chi_square_rxc_vs_pingouin(tmp_path):
    rng = np.random.default_rng(9)
    df = pd.DataFrame({"zona": rng.choice(["Urban", "Rural", "3T"], 200, p=[.5, .3, .2]),
                       "minat": rng.choice(["Rendah", "Sedang", "Tinggi"], 200)})
    out = relate.chi_square(_write(tmp_path, "c.csv", df), "zona", "minat")
    _, _, st = pg.chi2_independence(df, x="zona", y="minat", correction=False)
    pear = st[st.test == "pearson"].iloc[0]
    ll = st[st.test == "log-likelihood"].iloc[0]
    assert out["result"]["pearson"]["chi2"] == pytest.approx(pear["chi2"])
    assert out["result"]["pearson"]["p"] == pytest.approx(pear["pval"])
    assert out["result"]["likelihood_ratio"]["G2"] == pytest.approx(ll["chi2"])
    assert out["effect_size"]["cramers_v"] == pytest.approx(pear["cramer"])


def test_chi_square_2x2_small(tmp_path):
    # tabel [[8, 2], [1, 5]] -> frekuensi harapan kecil, harus merekomendasikan Fisher
    df = pd.DataFrame({"kelompok": ["E"] * 10 + ["K"] * 6,
                       "lulus": ["Ya"] * 8 + ["Tidak"] * 2 + ["Ya"] * 1 + ["Tidak"] * 5})
    out = relate.chi_square(_write(tmp_path, "s.csv", df), "kelompok", "lulus")
    obs = np.array([[2, 8], [5, 1]])  # kolom diurutkan abjad: Tidak, Ya
    assert out["result"]["recommended"] == "fisher_exact"
    assert out["result"]["fisher_exact"]["p"] == pytest.approx(stats.fisher_exact(obs).pvalue)
    assert out["result"]["yates"]["chi2"] == pytest.approx(stats.chi2_contingency(obs, correction=True)[0])
    assert out["effect_size"]["odds_ratio"]["OR"] == pytest.approx(2 * 1 / (8 * 5))
    assert abs(out["effect_size"]["phi"]) == pytest.approx(out["effect_size"]["cramers_v"])

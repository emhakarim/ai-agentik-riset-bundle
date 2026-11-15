"""Validasi compare.py terhadap nilai acuan R (dataset `sleep`) dan pustaka independen (scipy, pingouin)."""
import numpy as np
import pandas as pd
import pingouin as pg
import pytest
from scipy import stats

from edu_stats import compare
from edu_stats.data import load

SLEEP_1 = [0.7, -1.6, -0.2, -1.2, -0.1, 3.4, 3.7, 0.8, 0.0, 2.0]
SLEEP_2 = [1.9, 0.8, 1.1, 0.1, -0.1, 4.4, 5.5, 1.6, 4.6, 3.4]


@pytest.fixture
def sleep_long(tmp_path):
    df = pd.DataFrame({"extra": SLEEP_1 + SLEEP_2, "group": [1] * 10 + [2] * 10})
    p = tmp_path / "sleep_long.csv"
    df.to_csv(p, index=False)
    return load(str(p))


@pytest.fixture
def sleep_wide(tmp_path):
    p = tmp_path / "sleep_wide.csv"
    pd.DataFrame({"obat1": SLEEP_1, "obat2": SLEEP_2}).to_csv(p, index=False)
    return load(str(p))


@pytest.fixture
def three_groups(tmp_path):
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "skor": np.concatenate([rng.normal(70, 8, 25), rng.normal(75, 12, 30), rng.normal(80, 5, 20)]).round(1),
        "kelas": ["A"] * 25 + ["B"] * 30 + ["C"] * 20,
    })
    p = tmp_path / "three.csv"
    df.to_csv(p, index=False)
    return load(str(p)), df


# ------------------------------------------------ nilai acuan R: t.test(extra ~ group, data = sleep)
def test_ttest_independent_matches_R(sleep_long):
    r = compare.ttest_independent(sleep_long, "extra", "group")["result"]
    assert r["welch"]["t"] == pytest.approx(-1.860813, abs=1e-5)
    assert r["welch"]["df"] == pytest.approx(17.77647, abs=1e-4)
    assert r["welch"]["p"] == pytest.approx(0.07939414, abs=1e-6)
    assert r["student"]["df"] == 18
    assert r["student"]["p"] == pytest.approx(0.07918671, abs=1e-6)
    assert r["welch"]["ci_diff"][0] == pytest.approx(-3.3654832, abs=1e-5)
    assert r["welch"]["ci_diff"][1] == pytest.approx(0.2054832, abs=1e-5)


def test_ttest_paired_matches_R(sleep_wide):
    out = compare.ttest_paired(sleep_wide, "obat1", "obat2")
    r = out["result"]
    assert r["t"] == pytest.approx(-4.062128, abs=1e-5)
    assert r["df"] == 9
    assert r["p"] == pytest.approx(0.002832890, abs=1e-7)
    assert r["ci_difference"][0] == pytest.approx(-2.4598858, abs=1e-5)
    assert r["ci_difference"][1] == pytest.approx(-0.7001142, abs=1e-5)
    assert out["effect_size"]["d_z"] == pytest.approx(-1.284558, abs=1e-5)


def test_cohens_d_and_ci(sleep_long):
    es = compare.ttest_independent(sleep_long, "extra", "group")["effect_size"]
    assert es["cohens_d"] == pytest.approx(pg.compute_effsize(SLEEP_1, SLEEP_2, eftype="cohen"), abs=1e-9)
    assert es["hedges_g"] == pytest.approx(pg.compute_effsize(SLEEP_1, SLEEP_2, eftype="hedges"), abs=2e-3)
    # CI noncentral t: batas harus memenuhi definisi inversinya
    t_obs = es["cohens_d"] * np.sqrt(100 / 20)
    lo, hi = (c * np.sqrt(100 / 20) for c in es["cohens_d_ci"])
    assert stats.nct.cdf(t_obs, 18, lo) == pytest.approx(0.975, abs=1e-8)
    assert stats.nct.cdf(t_obs, 18, hi) == pytest.approx(0.025, abs=1e-8)


def test_cohens_d_ci_negative_t_mirrors_positive(tmp_path):
    # Regresi: dengan t negatif besar, nct.cdf(x < 0, df, ncp besar) di scipy bisa NaN dan solver gagal.
    # Data yang sama dengan urutan kelompok dibalik harus memberi CI cerminan.
    prog = [78, 85, 72, 90, 81, 76, 88, 69, 84, 79]
    kont = [71, 65, 80, 62, 74, 70, 68, 77, 60, 73]
    p = tmp_path / "res.csv"
    pd.DataFrame({"skor": prog + kont, "kel": ["Program"] * 10 + ["Kontrol"] * 10}).to_csv(p, index=False)
    data = load(str(p))
    pos = compare.ttest_independent(data, "skor", "kel", groups=["Program", "Kontrol"])["effect_size"]
    neg = compare.ttest_independent(data, "skor", "kel", groups=["Kontrol", "Program"])["effect_size"]
    assert neg["cohens_d"] == pytest.approx(-pos["cohens_d"], abs=1e-12)
    assert neg["cohens_d_ci"][0] == pytest.approx(-pos["cohens_d_ci"][1], abs=1e-9)
    assert neg["cohens_d_ci"][1] == pytest.approx(-pos["cohens_d_ci"][0], abs=1e-9)
    k = np.sqrt(100 / 20)
    lo, hi = (c * k for c in neg["cohens_d_ci"])
    assert stats.nct.cdf(-neg["cohens_d"] * k, 18, -hi) == pytest.approx(0.975, abs=1e-8)
    assert stats.nct.cdf(-neg["cohens_d"] * k, 18, -lo) == pytest.approx(0.025, abs=1e-8)


def test_one_sided_and_one_sample(sleep_wide):
    r = compare.ttest_one_sample(sleep_wide, "obat1", 0, alternative="greater")["result"]
    ref = stats.ttest_1samp(SLEEP_1, 0, alternative="greater")
    assert r["t"] == pytest.approx(ref.statistic)
    assert r["p"] == pytest.approx(ref.pvalue)
    assert r["ci_difference"][1] == float("inf")


# ------------------------------------------------ ANOVA vs pingouin
def test_anova_oneway(three_groups):
    ds, df = three_groups
    out = compare.anova_oneway(ds, "skor", "kelas")
    r = out["result"]
    a = pg.anova(df, dv="skor", between="kelas", detailed=True)
    assert r["anova"]["F"] == pytest.approx(a["F"][0])
    assert r["anova"]["p"] == pytest.approx(a["p_unc"][0])
    assert out["effect_size"]["eta_squared"] == pytest.approx(a["np2"][0])
    w = pg.welch_anova(df, dv="skor", between="kelas")
    assert r["welch"]["F"] == pytest.approx(w["F"][0])
    assert r["welch"]["df2"] == pytest.approx(w["ddof2"][0])
    assert r["welch"]["p"] == pytest.approx(w["p_unc"][0])

    tk = pg.pairwise_tukey(df, dv="skor", between="kelas")
    for mine, ref in zip(r["posthoc"]["tukey"], tk.itertuples()):
        assert mine["mean_difference"] == pytest.approx(ref.diff)
        assert mine["p"] == pytest.approx(ref.p_tukey, abs=1e-6)
    sc = stats.tukey_hsd(*[df.skor[df.kelas == k].to_numpy() for k in "ABC"])
    ci = sc.confidence_interval()
    assert r["posthoc"]["tukey"][0]["ci"][0] == pytest.approx(ci.low[0, 1], abs=1e-6)

    gh = pg.pairwise_gameshowell(df, dv="skor", between="kelas")
    for mine, ref in zip(r["posthoc"]["games_howell"], gh.itertuples()):
        assert mine["mean_difference"] == pytest.approx(ref.diff)
        assert mine["df"] == pytest.approx(ref.df)
        assert mine["p"] == pytest.approx(ref.pval, abs=1e-6)


# ------------------------------------------------ nonparametrik vs scipy / pingouin
def test_mann_whitney(three_groups):
    ds, df = three_groups
    r = compare.mann_whitney(ds, "skor", "kelas", groups=["A", "B"])["result"]
    a, b = df.skor[df.kelas == "A"], df.skor[df.kelas == "B"]
    ref = stats.mannwhitneyu(a, b, method="asymptotic", use_continuity=False)
    assert r["U1"] == pytest.approx(ref.statistic)
    assert r["p"] == pytest.approx(ref.pvalue)


def test_wilcoxon(sleep_wide):
    r = compare.wilcoxon(sleep_wide, "obat1", "obat2")["result"]
    ref = stats.wilcoxon(SLEEP_1, SLEEP_2, zero_method="wilcox", correction=False, method="approx")
    assert r["n_zero"] == 1
    assert r["T"] == pytest.approx(ref.statistic)
    assert r["p"] == pytest.approx(ref.pvalue)


def test_kruskal_and_dunn(three_groups):
    ds, df = three_groups
    out = compare.kruskal_wallis(ds, "skor", "kelas")
    ref = stats.kruskal(*[df.skor[df.kelas == k] for k in "ABC"])
    assert out["result"]["H"] == pytest.approx(ref.statistic)
    assert out["result"]["p"] == pytest.approx(ref.pvalue)
    for row in out["result"]["posthoc_dunn"]:
        assert row["p_bonferroni"] >= row["p_holm"] - 1e-12 >= row["p_unadjusted"] - 1e-12


def test_friedman(tmp_path):
    rng = np.random.default_rng(7)
    base = rng.normal(60, 10, 15)
    df = pd.DataFrame({"pre": base, "mid": base + rng.normal(3, 4, 15), "post": base + rng.normal(6, 4, 15)}).round(1)
    p = tmp_path / "rm.csv"
    df.to_csv(p, index=False)
    out = compare.friedman(load(str(p)), ["pre", "mid", "post"])
    ref = pg.friedman(df.melt(ignore_index=False).reset_index(), dv="value", within="variable", subject="index")
    assert out["result"]["chi2"] == pytest.approx(ref["Q"].iloc[0])
    assert out["effect_size"]["kendalls_w"] == pytest.approx(ref["W"].iloc[0])


def test_indonesian_csv_and_errors(tmp_path):
    p = tmp_path / "id.csv"
    p.write_text("nilai;kelas\n70,5;A\n80,25;A\n65;B\n90,75;B\n;B\n", encoding="utf-8")
    out = compare.ttest_independent(load(str(p)), "nilai", "kelas")
    assert out["input"]["n_used"] == 4 and out["input"]["n_dropped"] == 1
    assert out["result"]["groups"][0]["mean"] == pytest.approx(75.375)
    with pytest.raises(Exception, match="tepat 2 grup"):
        q = tmp_path / "x.csv"
        q.write_text("y,g\n1,a\n2,a\n3,b\n4,b\n5,c\n6,c\n")
        compare.ttest_independent(load(str(q)), "y", "g")


# ------------------------------------------------ ANCOVA, faktorial, RM-ANOVA vs pingouin
@pytest.fixture
def prepost(tmp_path):
    rng = np.random.default_rng(11)
    n = 60
    kelas = np.repeat(["Kontrol", "PBL", "Flipped"], [22, 20, 18])
    pre = rng.normal(60, 10, n)
    boost = np.select([kelas == "PBL", kelas == "Flipped"], [6, 9], 0)
    post = 10 + 0.8 * pre + boost + rng.normal(0, 5, n)
    df = pd.DataFrame({"pre test": pre.round(1), "post": post.round(1), "kelas": kelas,
                       "gender": rng.choice(["L", "P"], n)})
    p = tmp_path / "prepost.csv"
    df.to_csv(p, index=False)
    return load(str(p)), df


def test_ancova_vs_pingouin(prepost):
    import statsmodels.formula.api as smf

    ds, df = prepost
    out = compare.ancova(ds, "post", "kelas", ["pre test"])
    ref = pg.ancova(df, dv="post", between="kelas", covar="pre test")
    tab = {r["effect"]: r for r in out["result"]["anova_table"]}
    for src in ("kelas", "pre test"):
        row = ref[ref.Source == src].iloc[0]
        assert tab[src]["F"] == pytest.approx(row["F"])
        assert tab[src]["p"] == pytest.approx(row["p_unc"])
    # rerata terkoreksi = M_j − b·(M_cov_j − M_cov)
    b = smf.ols("post ~ C(kelas) + Q('pre test')", data=df).fit().params["Q('pre test')"]
    for a in out["result"]["adjusted_means"]:
        sub = df[df.kelas == a["group"]]
        assert a["mean_adjusted"] == pytest.approx(sub.post.mean() - b * (sub["pre test"].mean() - df["pre test"].mean()))
    pair = out["result"]["pairwise_bonferroni"][0]
    adj = {a["group"]: a["mean_adjusted"] for a in out["result"]["adjusted_means"]}
    assert pair["mean_difference"] == pytest.approx(adj[pair["group1"]] - adj[pair["group2"]])


def test_factorial_vs_pingouin(prepost):
    ds, df = prepost
    out = compare.anova_factorial(ds, "post", ["kelas", "gender"])
    ref = pg.anova(df, dv="post", between=["kelas", "gender"], ss_type=3)
    tab = {r["effect"]: r for r in out["result"]["anova_table"]}
    for src, mine in (("kelas", "kelas"), ("gender", "gender"), ("kelas * gender", "kelas × gender")):
        row = ref[ref.Source == src].iloc[0]
        assert tab[mine]["F"] == pytest.approx(row["F"])
        assert tab[mine]["p"] == pytest.approx(row["p_unc"])
        assert tab[mine]["partial_eta_squared"] == pytest.approx(row["np2"])


def test_rm_anova_vs_pingouin(tmp_path):
    rng = np.random.default_rng(3)
    base = rng.normal(50, 10, 20)
    df = pd.DataFrame({"t1": base, "t2": base + rng.normal(2, 3, 20), "t3": base + rng.normal(5, 8, 20),
                       "t4": base + rng.normal(6, 2, 20)}).round(2)
    p = tmp_path / "rm4.csv"
    df.to_csv(p, index=False)
    out = compare.anova_rm(load(str(p)), ["t1", "t2", "t3", "t4"])
    r = out["result"]
    long = df.reset_index().melt(id_vars="index")
    ref = pg.rm_anova(long, dv="value", within="variable", subject="index", correction=True, detailed=True, effsize="np2")
    assert r["F"] == pytest.approx(ref["F"].iloc[0])
    assert r["p_sphericity_assumed"] == pytest.approx(ref["p_unc"].iloc[0])
    assert r["corrections"]["greenhouse_geisser"]["epsilon"] == pytest.approx(ref["eps"].iloc[0])
    assert out["effect_size"]["partial_eta_squared"] == pytest.approx(ref["np2"].iloc[0])
    sph = pg.sphericity(long, dv="value", within="variable", subject="index")
    assert out["assumptions"]["mauchly"]["W"] == pytest.approx(sph.W)
    assert out["assumptions"]["mauchly"]["p_refined"] == pytest.approx(sph.pval)
    assert out["assumptions"]["mauchly"]["chi2"] == pytest.approx(sph.chi2)

"""Validasi power.py terhadap G*Power 3.1, tabel Cohen (1988), dan tabel Krejcie & Morgan (1970)."""
import pytest

from edu_stats import power, tools


@pytest.fixture(autouse=True)
def audit_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("EDU_STATS_AUDIT_DIR", str(tmp_path / "audit"))


def test_ttest_independent_gpower():
    # G*Power: d = 0.5, α = .05 dua sisi, power .80 -> 64 per grup (actual power .8015)
    r = power.power_ttest(0.5, power=0.80)["result"]
    assert (r["n_group1"], r["n_group2"], r["n_total"]) == (64, 64, 128)
    assert r["achieved_power"] == pytest.approx(0.8015, abs=5e-4)
    # d = 0.8 -> 26 per grup; d = 0.2 -> 394 per grup
    assert power.power_ttest(0.8, power=0.80)["result"]["n_group1"] == 26
    assert power.power_ttest(0.2, power=0.80)["result"]["n_group1"] == 394
    # satu sisi d = 0.5 -> 51 per grup
    assert power.power_ttest(0.5, power=0.80, alternative="greater")["result"]["n_group1"] == 51


def test_ttest_paired_and_power_from_n():
    # G*Power matched pairs: d_z = 0.5, power .80 -> 34 pasangan
    assert power.power_ttest(0.5, design="paired", power=0.80)["result"]["n"] == 34
    assert power.power_ttest(0.5, design="one_sample", power=0.95)["result"]["n"] == 54
    pw = power.power_ttest(0.5, n=64)["result"]["power"]
    assert pw == pytest.approx(0.8015, abs=5e-4)


def test_anova_gpower():
    # G*Power: f = 0.25, k = 3, power .80 -> N = 159 (53 per grup)
    r = power.power_anova(3, f=0.25, power=0.80)["result"]
    assert (r["n_per_group"], r["n_total"]) == (53, 159)
    # k = 4, f = 0.25 -> 45 per grup (N = 180)
    assert power.power_anova(4, f=0.25, power=0.80)["result"]["n_total"] == 180
    via_eta = power.power_anova(3, eta_squared=0.25 ** 2 / (1 + 0.25 ** 2), power=0.80)["result"]
    assert via_eta["n_total"] == 159


def test_correlation_cohen_table():
    # Cohen (1988): r = .30, α2 = .05, power .80 -> n = 85; r = .10 -> 783
    assert power.power_correlation(0.30, power=0.80)["result"]["n"] == 85
    assert power.power_correlation(0.10, power=0.80)["result"]["n"] == 783
    pw = power.power_correlation(0.30, n=85)["result"]["power"]
    assert 0.80 <= pw < 0.81


def test_survey_krejcie_morgan_and_slovin():
    # Tabel Krejcie & Morgan (1970): N = 1000 -> 278; N = 100 -> 80; N = 10000 -> 370
    for N, n in [(1000, 278), (100, 80), (10000, 370)]:
        assert power.sample_size_survey(N)["result"]["n"] == n
    assert power.sample_size_survey()["result"]["n"] == 385
    s = power.sample_size_survey(1000, method="slovin")
    assert s["result"]["n"] == 286 and any("Slovin" in x for x in s["notes"])


def test_guards_and_tool_registry():
    with pytest.raises(Exception, match="tepat salah satu"):
        power.power_ttest(0.5)
    with pytest.raises(Exception, match="tepat salah satu"):
        power.power_ttest(0.5, power=0.8, n=20)
    out = tools.run_tool("power_ttest", {"d": 0.5, "power": 0.8})
    assert out["result"]["n_total"] == 128 and out["audit"]["data_sha256"] is None
    assert "tidak dikenal" in tools.run_tool("power_anova", {"k": 3, "x": 1})["error"]
    assert "error" in tools.run_tool("power_correlation", {"r": 0.3})
    assert set(tools.public_functions()) == set(tools.list_tools())

"""Validasi instrument.py terhadap pingouin, bentuk tertutup, dan nilai tabel."""
from pathlib import Path

import numpy as np
import pandas as pd
import pingouin as pg
import pytest

from edu_stats import instrument
from edu_stats.data import load

ZETTA_CSV = Path(__file__).resolve().parents[3] / "Zetta Skill MCP" / "datasets" / "data_survei_resiliensi_300.csv"


@pytest.fixture
def likert(tmp_path):
    rng = np.random.default_rng(21)
    n = 150
    trait = rng.normal(0, 1, n)
    lam = [0.8, 0.7, 0.6, 0.75, 0.5, 0.65]
    cols = {f"B{i + 1}": np.clip(np.round(3 + l * trait + rng.normal(0, 0.7, n)), 1, 5) for i, l in enumerate(lam)}
    df = pd.DataFrame(cols)
    df["B6"] = 6 - df["B6"]  # butir negatif
    p = tmp_path / "likert.csv"
    df.to_csv(p, index=False)
    return load(str(p)), df


def test_r_table_values():
    # nilai tabel r Product Moment klasik (dua sisi, α = .05)
    assert instrument.r_table(30) == pytest.approx(0.361, abs=5e-4)
    assert instrument.r_table(100) == pytest.approx(0.197, abs=5e-4)
    assert instrument.r_table(30, alpha=0.01) == pytest.approx(0.463, abs=5e-4)


def test_reverse_detected_then_fixed(likert, tmp_path):
    ds, df = likert
    items = [f"B{i}" for i in range(1, 7)]
    before = instrument.reliability(ds, items)
    assert "B6" in before["result"]["items_below_criteria"]
    assert any("negatif" in n for n in before["notes"])

    prep = instrument.prepare_scale(ds, items, "skor", reverse=["B6"], scale_min=1, scale_max=5)
    out_path = Path(prep["result"]["output_path"])
    assert out_path.name == "likert_skor.csv" and out_path.exists()
    assert pd.read_csv(tmp_path / "likert.csv").equals(df)  # file asli tidak berubah
    new = pd.read_csv(out_path)
    assert (new["B6_R"] == 6 - df["B6"]).all()
    assert new["skor"].iloc[0] == pytest.approx(np.mean([*df.iloc[0, :5], 6 - df["B6"].iloc[0]]))

    fixed = [*items[:5], "B6_R"]
    after = instrument.reliability(load(str(out_path)), fixed)
    ref = pg.cronbach_alpha(new[fixed])
    assert after["result"]["cronbach_alpha"] == pytest.approx(ref[0])
    assert after["result"]["alpha_ci"][0] == pytest.approx(ref[1][0], abs=1e-3)
    assert after["result"]["alpha_ci"][1] == pytest.approx(ref[1][1], abs=1e-3)
    for row in after["result"]["items"]:
        rest = [c for c in fixed if c != row["item"]]
        assert row["alpha_if_deleted"] == pytest.approx(pg.cronbach_alpha(new[rest])[0])
        assert row["r_item_total_corrected"] == pytest.approx(np.corrcoef(new[row["item"]], new[rest].sum(axis=1))[0, 1])


def test_prepare_scale_guards(likert):
    ds, _ = likert
    with pytest.raises(Exception, match="scale_min"):
        instrument.prepare_scale(ds, ["B1", "B6"], "s", reverse=["B6"])
    with pytest.raises(Exception, match="ditimpa"):
        instrument.prepare_scale(ds, ["B1", "B2"], "s", output_path=ds.path)


def test_omega_closed_form_three_items(tmp_path):
    # Model satu faktor dengan 3 butir just-identified: λ1² = s12·s13/s23 (dst.)
    rng = np.random.default_rng(4)
    f = rng.normal(size=400)
    X = np.column_stack([2 * f + rng.normal(0, 1, 400), 1.5 * f + rng.normal(0, 1.2, 400), f + rng.normal(0, 0.8, 400)])
    S = np.cov(X, rowvar=False)
    l1 = np.sqrt(S[0, 1] * S[0, 2] / S[1, 2])
    l2 = np.sqrt(S[0, 1] * S[1, 2] / S[0, 2])
    l3 = np.sqrt(S[0, 2] * S[1, 2] / S[0, 1])
    lam = np.array([l1, l2, l3])
    psi = np.diag(S) - lam ** 2
    expected = lam.sum() ** 2 / (lam.sum() ** 2 + psi.sum())
    p = tmp_path / "o.csv"
    pd.DataFrame(X, columns=["a", "b", "c"]).to_csv(p, index=False)
    om = instrument.reliability(load(str(p)), ["a", "b", "c"])["result"]["omega"]
    assert om["converged"]
    assert om["omega_total"] == pytest.approx(expected, abs=1e-5)


@pytest.mark.skipif(not ZETTA_CSV.exists(), reason="dataset Zetta tidak tersedia")
def test_zetta_dataset_alpha():
    # acuan bersama dengan Zetta (lihat KOLABORASI.md): α RES (RES4, RES7 dibalik) = .896
    ds = load(str(ZETTA_CSV))
    items = [f"RES{i}" for i in range(1, 9)]
    df = ds.df[items].copy()
    df[["RES4", "RES7"]] = 6 - df[["RES4", "RES7"]]
    expected = pg.cronbach_alpha(df)[0]
    assert round(expected, 3) == 0.896
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        prep = instrument.prepare_scale(ds, items, "RES_skor", reverse=["RES4", "RES7"], scale_min=1, scale_max=5,
                                        output_path=os.path.join(d, "res.csv"))
        fixed = [c if c not in ("RES4", "RES7") else f"{c}_R" for c in items]
        a = instrument.reliability(load(prep["result"]["output_path"]), fixed)["result"]["cronbach_alpha"]
    assert a == pytest.approx(expected)


def test_n_gain(tmp_path):
    df = pd.DataFrame({"pre": [40, 50, 60, 100, 30, 20], "post": [70, 90, 60, 100, 79, 30],
                       "kelas": ["E", "E", "E", "E", "K", "K"]})
    p = tmp_path / "g.csv"
    df.to_csv(p, index=False)
    out = instrument.n_gain(load(str(p)), "pre", "post", 100, group="kelas")
    e, k = out["result"]["groups"]["E"], out["result"]["groups"]["K"]
    ge = [(70 - 40) / 60, (90 - 50) / 50, 0.0]  # siswa pre = 100 dikeluarkan
    assert e["n_excluded_pre_max"] == 1
    assert e["mean_individual_gain"] == pytest.approx(np.mean(ge))
    assert e["category_counts"] == {"tinggi": 1, "sedang": 1, "rendah": 1}
    assert k["mean_individual_gain"] == pytest.approx(np.mean([49 / 70, 10 / 80]))
    assert k["class_average_gain"] == pytest.approx((54.5 - 25) / (100 - 25))
    assert instrument._eff_cat(55.5) == "kurang efektif" and instrument._eff_cat(75) == "cukup efektif"
    with pytest.raises(Exception, match="melebihi"):
        instrument.n_gain(load(str(p)), "pre", "post", 90)

"""Inspeksi data, statistik deskriptif, uji normalitas, uji homogenitas."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

from . import fmt
from .data import Dataset, DataError, check_columns, group_series, numeric_frame, select_groups, to_numeric


def inspect_data(ds: Dataset) -> dict:
    cols = []
    for c in ds.df.columns:
        s = ds.df[c]
        info = {"column": c, "dtype": str(s.dtype), "n_valid": int(s.notna().sum()), "n_missing": int(s.isna().sum()),
                "n_unique": int(s.nunique(dropna=True)),
                "examples": [fmt.clean(v) for v in s.dropna().unique()[:5].tolist()]}
        try:
            x = to_numeric(s, c).dropna()
            info["numeric"] = True
            if len(x):
                info.update(min=float(x.min()), max=float(x.max()))
        except DataError:
            info["numeric"] = False
        if c in ds.value_labels:
            info["value_labels"] = ds.value_labels[c]
        cols.append(info)
    return {"result": {"n_rows": len(ds.df), "n_columns": ds.df.shape[1], "columns": cols}}


def _desc(x: np.ndarray, conf: float = 0.95) -> dict:
    n = len(x)
    out = {"n": n}
    if n == 0:
        return out
    m = float(np.mean(x))
    sd = float(np.std(x, ddof=1)) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    tcrit = stats.t.ppf(0.5 + conf / 2, n - 1) if n > 1 else float("nan")
    out.update(mean=m, sd=sd, se=se, ci_low=m - tcrit * se, ci_high=m + tcrit * se, median=float(np.median(x)),
               min=float(np.min(x)), max=float(np.max(x)), range=float(np.ptp(x)),
               q1=float(np.percentile(x, 25)), q3=float(np.percentile(x, 75)), variance=sd ** 2)
    if n >= 3 and sd > 0:
        sk = float(stats.skew(x, bias=False))
        se_sk = math.sqrt(6 * n * (n - 1) / ((n - 2) * (n + 1) * (n + 3)))
        out.update(skewness=sk, se_skewness=se_sk, z_skewness=sk / se_sk)
    if n >= 4 and sd > 0:
        ku = float(stats.kurtosis(x, bias=False))
        se_sk = math.sqrt(6 * n * (n - 1) / ((n - 2) * (n + 1) * (n + 3)))
        se_ku = 2 * se_sk * math.sqrt((n * n - 1) / ((n - 3) * (n + 5)))
        out.update(kurtosis=ku, se_kurtosis=se_ku, z_kurtosis=ku / se_ku)
    return out


def descriptives(ds: Dataset, columns: list[str], group: str | None = None, conf_level: float = 0.95) -> dict:
    notes: list = []
    rows = []
    if group:
        g = group_series(ds, group)
        for c in columns:
            check_columns(ds, [c])
            x = to_numeric(ds.df[c], c, notes)
            for lev in select_groups(g, None):
                v = x[(g == lev) & x.notna()].to_numpy()
                rows.append({"variable": c, "group": lev, **_desc(v, conf_level)})
    else:
        for c in columns:
            check_columns(ds, [c])
            x = to_numeric(ds.df[c], c, notes)
            d = _desc(x.dropna().to_numpy(), conf_level)
            d["n_missing"] = int(x.isna().sum())
            rows.append({"variable": c, **d})
    apa = []
    for r in rows:
        if r.get("n", 0) > 1:
            lab = r["variable"] + (f" ({r['group']})" if "group" in r else "")
            apa.append(f"{lab}: M = {fmt.num(r['mean'])}, SD = {fmt.num(r['sd'])}, n = {r['n']}")
    notes.append("SD memakai n−1. Skewness/kurtosis memakai rumus terkoreksi (sama seperti SPSS); "
                 "|z| > 1.96 menandakan penyimpangan dari normal pada α = .05.")
    return {"result": {"descriptives": rows}, "apa": apa, "notes": notes}


def _normality_one(x: np.ndarray, alpha: float) -> dict:
    from statsmodels.stats.diagnostic import lilliefors

    n = len(x)
    out = {"n": n}
    if n < 3:
        out["error"] = "n < 3, uji normalitas tidak bisa dihitung"
        return out
    if np.ptp(x) == 0:
        out["error"] = "Semua nilai sama, uji normalitas tidak bisa dihitung"
        return out
    w, pw = stats.shapiro(x)
    out["shapiro_wilk"] = {"W": float(w), "p": float(pw)}
    if n >= 5:
        ks, pk = lilliefors(x, dist="norm", pvalmethod="table")
        out["kolmogorov_smirnov_lilliefors"] = {"D": float(ks), "p": float(pk),
                                                 "catatan": "p dari tabel Lilliefors; SPSS menampilkan .200 sebagai batas bawah"}
    d = _desc(x)
    out["z_skewness"] = d.get("z_skewness")
    out["z_kurtosis"] = d.get("z_kurtosis")
    normal = bool(pw > alpha)
    out["normal"] = normal
    out["keputusan"] = (f"Data berdistribusi normal (Shapiro-Wilk {fmt.p(pw)} > {alpha})" if normal
                        else f"Data tidak berdistribusi normal (Shapiro-Wilk {fmt.p(pw)} ≤ {alpha})")
    out["apa"] = f"W({n}) = {fmt.num(w, 3)}, {fmt.p(pw)}"
    return out


def normality(ds: Dataset, columns: list[str], group: str | None = None, alpha: float = 0.05) -> dict:
    notes: list = []
    rows = []
    g = group_series(ds, group) if group else None
    for c in columns:
        check_columns(ds, [c])
        x = to_numeric(ds.df[c], c, notes)
        if g is None:
            rows.append({"variable": c, **_normality_one(x.dropna().to_numpy(), alpha)})
        else:
            for lev in select_groups(g, None):
                rows.append({"variable": c, "group": lev, **_normality_one(x[(g == lev) & x.notna()].to_numpy(), alpha)})
    notes.append("Keputusan utama memakai Shapiro-Wilk (dianjurkan untuk n < 2000). Untuk n besar (> 300), "
                 "uji formal sangat sensitif; pertimbangkan juga skewness/kurtosis dan Q-Q plot.")
    return {"result": {"normality": rows}, "apa": [f"{r['variable']}{' (' + r['group'] + ')' if 'group' in r else ''}: {r['apa']}" for r in rows if "apa" in r], "notes": notes}


def _levene(samples, alpha):
    f_mean, p_mean = stats.levene(*samples, center="mean")
    f_med, p_med = stats.levene(*samples, center="median")
    k = len(samples)
    n = sum(len(s) for s in samples)
    homog = bool(p_mean > alpha)
    return {"levene_mean": {"F": float(f_mean), "df1": k - 1, "df2": n - k, "p": float(p_mean)},
            "brown_forsythe_median": {"F": float(f_med), "df1": k - 1, "df2": n - k, "p": float(p_med)},
            "homogeneous": homog,
            "keputusan": (f"Varians homogen (Levene {fmt.p(p_mean)} > {alpha})" if homog
                          else f"Varians tidak homogen (Levene {fmt.p(p_mean)} ≤ {alpha})"),
            "apa": f"F({k - 1}, {n - k}) = {fmt.num(f_mean)}, {fmt.p(p_mean)}"}


def homogeneity(ds: Dataset, dv: str, group: str, groups: list[str] | None = None, alpha: float = 0.05) -> dict:
    notes: list = []
    x = to_numeric(ds.df[dv], dv, notes) if dv in ds.df else check_columns(ds, [dv])
    g = group_series(ds, group)
    levs = select_groups(g, groups)
    samples = [x[(g == lev) & x.notna()].to_numpy() for lev in levs]
    res = _levene(samples, alpha)
    res["groups"] = {lev: len(s) for lev, s in zip(levs, samples)}
    notes.append("Levene 'based on mean' sama dengan baris pertama tabel SPSS; Brown-Forsythe (median) lebih tahan outlier.")
    return {"result": res, "apa": [f"Levene: {res['apa']}"], "notes": notes}

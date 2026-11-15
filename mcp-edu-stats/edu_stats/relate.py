"""Uji hubungan: korelasi (Pearson/Spearman/Kendall), regresi linear berganda, chi-square.

Konvensi keluaran sama dengan compare.py: `result`, `apa`, `effect_size`, `assumptions`, `notes`, `input`.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
from scipy import stats

from . import fmt
from .compare import _check_alt, _input
from .data import Dataset, DataError, check_columns, group_series, numeric_frame, to_numeric
from .describe import _normality_one

_METHODS = ("pearson", "spearman", "kendall")
_SYMBOL = {"pearson": "r", "spearman": "rₛ", "kendall": "τ_b"}


# ---------------------------------------------------------------- korelasi
def _corr_ci(r: float, n: int, method: str, conf: float) -> tuple[float, float]:
    """CI via transformasi Fisher z. SE Spearman & Kendall mengikuti Bonett & Wright (2000)."""
    if n <= 4 or abs(r) >= 1:
        return (float("nan"), float("nan"))
    if method == "pearson":
        se = 1 / math.sqrt(n - 3)
    elif method == "spearman":
        se = math.sqrt((1 + r ** 2 / 2) / (n - 3))
    else:
        se = math.sqrt(0.437 / (n - 4))
    z = math.atanh(r)
    q = stats.norm.ppf(0.5 + conf / 2)
    return math.tanh(z - q * se), math.tanh(z + q * se)


def _corr_pair(x: np.ndarray, y: np.ndarray, method: str, alternative: str):
    if method == "pearson":
        res = stats.pearsonr(x, y, alternative=alternative)
    elif method == "spearman":
        res = stats.spearmanr(x, y, alternative=alternative)
    else:
        res = stats.kendalltau(x, y, alternative=alternative, variant="b")
    return float(res.statistic), float(res.pvalue)


def correlation(ds: Dataset, columns: list[str], method: str = "pearson", alpha: float = 0.05,
                alternative: str = "two-sided", conf_level: float = 0.95, listwise: bool = False) -> dict:
    """Matriks korelasi berpasangan. Default: pairwise deletion (seperti SPSS); `listwise=True` untuk listwise."""
    _check_alt(alternative)
    if method not in _METHODS:
        raise DataError(f"method harus salah satu dari {_METHODS}, bukan {method!r}")
    if len(columns) < 2:
        raise DataError("Korelasi butuh minimal 2 kolom.")
    notes: list = []
    check_columns(ds, columns)
    data = pd.DataFrame({c: to_numeric(ds.df[c], c, notes) for c in columns})
    n_dropped = 0
    if listwise:
        n0 = len(data)
        data = data.dropna()
        n_dropped = n0 - len(data)
        notes.append(f"Penghapusan listwise: {n_dropped} baris dibuang.")
    else:
        notes.append("Penghapusan pairwise: tiap pasangan memakai semua baris yang lengkap untuk kedua kolom itu (n bisa berbeda).")
    pairs, apa = [], []
    sym = _SYMBOL[method]
    for a, b in itertools.combinations(columns, 2):
        sub = data[[a, b]].dropna()
        n = len(sub)
        if n < 3:
            pairs.append({"var1": a, "var2": b, "n": n, "error": "n < 3, korelasi tidak bisa dihitung"})
            continue
        x, y = sub[a].to_numpy(), sub[b].to_numpy()
        if np.ptp(x) == 0 or np.ptp(y) == 0:
            pairs.append({"var1": a, "var2": b, "n": n, "error": "Salah satu kolom konstan, korelasi tidak terdefinisi"})
            continue
        r, p = _corr_pair(x, y, method, alternative)
        lo, hi = _corr_ci(r, n, method, conf_level)
        row = {"var1": a, "var2": b, "n": n, "coefficient": r, "p": p, "ci": [lo, hi], "df": n - 2,
               "r_squared": r ** 2 if method == "pearson" else None, "label": fmt.label_r(r), **fmt.sig(p, alpha)}
        pairs.append(row)
        apa.append(f"{a} – {b}: {sym}({n - 2}) = {fmt.nolead(r)}, {fmt.p(p)}, "
                   f"{int(conf_level * 100)}% CI {fmt.ci(lo, hi, lead=False)}")
    mat = {c: {d: (1.0 if c == d else None) for d in columns} for c in columns}
    for r in pairs:
        if "coefficient" in r:
            mat[r["var1"]][r["var2"]] = mat[r["var2"]][r["var1"]] = r["coefficient"]
    assumptions = {}
    if method == "pearson":
        assumptions["normality"] = {c: {k: v for k, v in _normality_one(data[c].dropna().to_numpy(), alpha).items()
                                        if k in ("n", "shapiro_wilk", "normal", "keputusan", "error")} for c in columns}
        assumptions["catatan"] = ("Pearson mengasumsikan hubungan linear dan tanpa outlier ekstrem; periksa scatterplot. "
                                  "Bila data ordinal/tidak normal, pakai Spearman atau Kendall.")
    if alternative != "two-sided":
        notes.append("Uji satu sisi; CI tetap dilaporkan dua sisi.")
    notes.append("Label kekuatan mengikuti Cohen (1988): .10 kecil, .30 sedang, .50 besar.")
    n_used = len(data.dropna()) if listwise else int(data.notna().all(axis=1).sum())
    return {
        "result": {"method": method, "pairs": pairs, "matrix": mat, "alternative": alternative},
        "effect_size": {"catatan": "Koefisien korelasi itu sendiri adalah ukuran efek; lihat 'label' per pasangan."},
        "assumptions": assumptions,
        "apa": apa,
        "notes": notes,
        "input": _input(ds, n_used, n_dropped, {"columns": columns, "listwise": listwise}),
    }


# ---------------------------------------------------------------- regresi linear
def regression(ds: Dataset, dv: str, predictors: list[str], alpha: float = 0.05, conf_level: float = 0.95) -> dict:
    """Regresi linear berganda OLS (metode Enter), lengkap dengan diagnostik asumsi klasik."""
    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    from statsmodels.stats.stattools import durbin_watson

    if not predictors:
        raise DataError("Regresi butuh minimal satu prediktor.")
    if dv in predictors:
        raise DataError("Variabel terikat tidak boleh sekaligus menjadi prediktor.")
    notes: list = []
    df_, n0, n_dropped = numeric_frame(ds, [dv, *predictors], notes)
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang (listwise) karena ada nilai kosong.")
    n, k = len(df_), len(predictors)
    if n <= k + 1:
        raise DataError(f"Data lengkap ({n}) terlalu sedikit untuk {k} prediktor.")
    for c in predictors:
        if df_[c].nunique() < 2:
            raise DataError(f"Prediktor '{c}' konstan; keluarkan dari model.")
    y = df_[dv].to_numpy()
    X = sm.add_constant(df_[predictors].to_numpy(), has_constant="add")
    res = sm.OLS(y, X).fit()
    if np.linalg.matrix_rank(X) < X.shape[1]:
        raise DataError("Ada prediktor yang merupakan kombinasi linear prediktor lain (multikolinearitas sempurna).")

    ci = res.conf_int(alpha=1 - conf_level)
    sd_y = y.std(ddof=1)
    r2, df_res = float(res.rsquared), float(res.df_resid)
    coefs = [{"term": "(Constant)", "B": float(res.params[0]), "se": float(res.bse[0]), "t": float(res.tvalues[0]),
              "p": float(res.pvalues[0]), "ci": [float(ci[0, 0]), float(ci[0, 1])]}]
    for i, c in enumerate(predictors, start=1):
        vif = float(variance_inflation_factor(X, i)) if k > 1 else 1.0
        t = float(res.tvalues[i])
        sr2 = t ** 2 * (1 - r2) / df_res
        coefs.append({"term": c, "B": float(res.params[i]), "se": float(res.bse[i]), "t": t, "p": float(res.pvalues[i]),
                      "ci": [float(ci[i, 0]), float(ci[i, 1])], "beta": float(res.params[i] * df_[c].std(ddof=1) / sd_y),
                      "sr2": sr2, "vif": vif, "tolerance": 1 / vif, **fmt.sig(float(res.pvalues[i]), alpha)})

    resid = np.asarray(res.resid)
    dw = float(durbin_watson(resid))
    bp_lm, bp_p, bp_f, bp_fp = het_breuschpagan(resid, X)
    infl = res.get_influence()
    std_resid = infl.resid_studentized_internal
    cooks = infl.cooks_distance[0]
    f2 = r2 / (1 - r2) if r2 < 1 else float("inf")
    max_vif = max((c["vif"] for c in coefs[1:]), default=1.0)

    model = {"R": math.sqrt(r2), "R2": r2, "adj_R2": float(res.rsquared_adj), "F": float(res.fvalue),
             "df1": int(res.df_model), "df2": int(df_res), "p": float(res.f_pvalue),
             "se_estimate": math.sqrt(res.mse_resid), "n": n}
    apa = [f"Model: R² = {fmt.nolead(r2)}, adj. R² = {fmt.nolead(model['adj_R2'])}, "
           f"F({model['df1']}, {model['df2']}) = {fmt.num(model['F'])}, {fmt.p(model['p'])}, f² = {fmt.num(f2)}"]
    for c in coefs[1:]:
        apa.append(f"{c['term']}: B = {fmt.num(c['B'])}, SE = {fmt.num(c['se'])}, β = {fmt.num(c['beta'])}, "
                   f"t({model['df2']}) = {fmt.num(c['t'])}, {fmt.p(c['p'])}, "
                   f"{int(conf_level * 100)}% CI {fmt.ci(*c['ci'])}")
    notes.append("β = koefisien terstandar (sama dengan 'Standardized Coefficients Beta' SPSS). "
                 "sr² = kontribusi unik prediktor terhadap R² (korelasi semi-parsial kuadrat).")
    notes.append("Breusch-Pagan versi studentized (Koenker), sama dengan default lmtest::bptest di R.")
    if n < 50 + 8 * k:
        notes.append(f"n = {n} di bawah aturan praktis Green (1991) n ≥ 50 + 8k = {50 + 8 * k} untuk menguji model.")
    return {
        "result": {"model": model, "coefficients": coefs, **fmt.sig(model["p"], alpha)},
        "effect_size": {"R2": r2, "f2": f2, "label": fmt.label_f2(f2)},
        "assumptions": {
            "normality_of_residuals": {k_: v for k_, v in _normality_one(resid, alpha).items()
                                       if k_ in ("n", "shapiro_wilk", "normal", "keputusan", "error")},
            "multicollinearity": {"max_vif": max_vif, "ok": max_vif < 10,
                                  "keputusan": ("Tidak ada multikolinearitas serius (VIF < 10)" if max_vif < 10
                                                else "Multikolinearitas serius (VIF ≥ 10)"),
                                  "catatan": "Sebagian penulis memakai batas lebih ketat VIF < 5."},
            "homoscedasticity_breusch_pagan": {"LM": float(bp_lm), "df": k, "p": float(bp_p),
                                               "homoscedastic": bool(bp_p > alpha),
                                               "keputusan": (f"Homoskedastis ({fmt.p(bp_p)} > {alpha})" if bp_p > alpha
                                                             else f"Heteroskedastis ({fmt.p(bp_p)} ≤ {alpha}); pertimbangkan SE robust (HC3)")},
            "independence_durbin_watson": {"DW": dw, "ok": 1.5 <= dw <= 2.5,
                                           "keputusan": ("Tidak ada autokorelasi berarti (1.5 ≤ DW ≤ 2.5)" if 1.5 <= dw <= 2.5
                                                         else "Indikasi autokorelasi residu (DW di luar 1.5–2.5)")},
            "outliers": {"n_std_resid_gt3": int(np.sum(np.abs(std_resid) > 3)),
                         "n_cooks_gt_4_over_n": int(np.sum(cooks > 4 / n)), "max_cooks_d": float(cooks.max()),
                         "catatan": "Cook's D > 4/n menandai kasus berpengaruh untuk diperiksa, bukan untuk otomatis dibuang."},
        },
        "apa": apa,
        "notes": notes,
        "input": _input(ds, n, n_dropped, {"dv": dv, "predictors": predictors}),
    }


# ---------------------------------------------------------------- chi-square
def chi_square(ds: Dataset, row: str, col: str, alpha: float = 0.05) -> dict:
    """Uji independensi chi-square untuk tabel kontingensi dua variabel kategorik."""
    notes: list = []
    check_columns(ds, [row, col])
    r_s, c_s = group_series(ds, row), group_series(ds, col)
    ok = r_s.notna() & c_s.notna()
    n_dropped = int((~ok).sum())
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang karena kategori kosong.")
    tab = pd.crosstab(r_s[ok], c_s[ok])
    if tab.shape[0] < 2 or tab.shape[1] < 2:
        raise DataError(f"Tabel kontingensi minimal 2×2; ditemukan {tab.shape[0]}×{tab.shape[1]}.")
    obs = tab.to_numpy()
    N = int(obs.sum())
    chi2, p, dfv, expected = stats.chi2_contingency(obs, correction=False)
    g, p_g, _, _ = stats.chi2_contingency(obs, correction=False, lambda_="log-likelihood")
    kmin = min(obs.shape) - 1
    V = math.sqrt(chi2 / (N * kmin))
    pct_lt5 = float(np.mean(expected < 5) * 100)
    out = {"pearson": {"chi2": float(chi2), "df": int(dfv), "p": float(p)},
           "likelihood_ratio": {"G2": float(g), "df": int(dfv), "p": float(p_g)}}
    es = {"cramers_v": V, "label": fmt.label_cramer_v(V, kmin)}
    is2x2 = obs.shape == (2, 2)
    if is2x2:
        cy, py, _, _ = stats.chi2_contingency(obs, correction=True)
        out["yates"] = {"chi2": float(cy), "df": 1, "p": float(py)}
        fe = stats.fisher_exact(obs)
        out["fisher_exact"] = {"p": float(fe.pvalue)}
        a, b, c, d = obs.ravel()
        es["phi"] = float((a * d - b * c) / math.sqrt((a + b) * (c + d) * (a + c) * (b + d)))
        if min(a, b, c, d) > 0:
            orr = a * d / (b * c)
            se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
            q = stats.norm.ppf(0.975)
            es["odds_ratio"] = {"OR": orr, "ci95": [math.exp(math.log(orr) - q * se), math.exp(math.log(orr) + q * se)]}
        else:
            notes.append("Ada sel bernilai 0; odds ratio tidak dihitung.")
    assumption_ok = pct_lt5 <= 20 and expected.min() >= 1
    if assumption_ok:
        use, p_use = "pearson", float(p)
    else:
        use, p_use = ("fisher_exact", out["fisher_exact"]["p"]) if is2x2 else ("pearson", float(p))
    apa = [f"χ²({int(dfv)}, N = {N}) = {fmt.num(chi2)}, {fmt.p(p)}, Cramér's V = {fmt.nolead(V)}"]
    if use == "fisher_exact":
        apa.append(f"Fisher's exact test: {fmt.p(p_use)}")
    if not assumption_ok:
        notes.append(f"PERINGATAN: {fmt.num(pct_lt5, 1)}% sel memiliki frekuensi harapan < 5 (batas 20%) atau ada yang < 1. "
                     + ("Pakai Fisher's exact test." if is2x2 else "Gabungkan kategori yang berdekatan atau pakai uji eksak."))
    notes.append("Cramér's V dilabel menurut Cohen (1988) dengan menyesuaikan df* = min(baris, kolom) − 1.")
    return {
        "result": {"observed": {str(k): {str(c): int(v) for c, v in r.items()} for k, r in tab.to_dict("index").items()},
                   "expected": {str(rk): {str(ck): float(expected[i, j]) for j, ck in enumerate(tab.columns)}
                                for i, rk in enumerate(tab.index)},
                   **out, "recommended": use, "p": p_use, **fmt.sig(p_use, alpha)},
        "effect_size": es,
        "assumptions": {"expected_counts": {"pct_cells_expected_lt5": pct_lt5, "min_expected": float(expected.min()),
                                            "ok": assumption_ok}},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, N, n_dropped, {"row": row, "col": col}),
    }


# ---------------------------------------------------------------- mediasi & moderasi
def _ols(y: np.ndarray, X: np.ndarray):
    import statsmodels.api as sm

    return sm.OLS(y, sm.add_constant(X, has_constant="add")).fit()


def mediation(ds: Dataset, x: str, m: str, y: str, covariates: list[str] | None = None, n_boot: int = 5000,
              seed: int = 12345, conf_level: float = 0.95) -> dict:
    """Mediasi sederhana X → M → Y (model 4 Hayes): jalur a, b, c, c', efek tak langsung a·b dengan CI bootstrap
    persentil (seed tetap → hasil bisa di-replay) dan uji Sobel."""
    covariates = list(covariates or [])
    if len({x, m, y, *covariates}) != 3 + len(covariates):
        raise DataError("x, m, y, dan kovariat harus kolom yang berbeda.")
    if not 1000 <= n_boot <= 50000:
        raise DataError("n_boot harus 1000–50000 (lazim 5000).")
    notes: list = []
    df_, n0, n_dropped = numeric_frame(ds, [x, m, y, *covariates], notes)
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang (listwise) karena ada nilai kosong.")
    n = len(df_)
    if n < 10 + len(covariates):
        raise DataError(f"Data lengkap ({n}) terlalu sedikit untuk mediasi.")
    X_, M_, Y_ = df_[x].to_numpy(), df_[m].to_numpy(), df_[y].to_numpy()
    C = df_[covariates].to_numpy() if covariates else np.empty((n, 0))

    ra = _ols(M_, np.column_stack([X_, C]))
    rb = _ols(Y_, np.column_stack([X_, M_, C]))
    rc = _ols(Y_, np.column_stack([X_, C]))
    a, sa = float(ra.params[1]), float(ra.bse[1])
    cp, b, sb = float(rb.params[1]), float(rb.params[2]), float(rb.bse[2])
    c = float(rc.params[1])
    ab = a * b

    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    D = np.column_stack([X_, M_, Y_, C])
    for i in range(n_boot):
        s = D[rng.integers(0, n, n)]
        Xa = np.column_stack([np.ones(n), s[:, 0], s[:, 3:]])
        Xb = np.column_stack([np.ones(n), s[:, 0], s[:, 1], s[:, 3:]])
        a_i = np.linalg.lstsq(Xa, s[:, 1], rcond=None)[0][1]
        b_i = np.linalg.lstsq(Xb, s[:, 2], rcond=None)[0][2]
        boots[i] = a_i * b_i
    lo, hi = np.percentile(boots, [100 * (1 - conf_level) / 2, 100 * (1 + conf_level) / 2])
    boot_sig = bool(lo > 0 or hi < 0)
    se_sobel = math.sqrt(b ** 2 * sa ** 2 + a ** 2 * sb ** 2)
    z = ab / se_sobel
    p_sobel = float(2 * stats.norm.sf(abs(z)))
    ab_std = ab * X_.std(ddof=1) / Y_.std(ddof=1)

    def path(name, r, i, desc):
        ci = r.conf_int(alpha=1 - conf_level)[i]
        return {"path": name, "keterangan": desc, "B": float(r.params[i]), "se": float(r.bse[i]), "t": float(r.tvalues[i]),
                "p": float(r.pvalues[i]), "ci": [float(ci[0]), float(ci[1])]}

    paths = [path("a", ra, 1, f"{x} → {m}"), path("b", rb, 2, f"{m} → {y} (mengontrol {x})"),
             path("c", rc, 1, f"{x} → {y} (efek total)"), path("c'", rb, 1, f"{x} → {y} (efek langsung)")]
    kind = ("tidak ada efek tak langsung" if not boot_sig else
            "mediasi penuh (efek langsung tidak signifikan)" if paths[3]["p"] >= 0.05 else
            "mediasi parsial (efek langsung tetap signifikan)")
    notes.append(f"Keputusan efek tak langsung memakai CI bootstrap persentil ({n_boot} sampel ulang, seed = {seed}); "
                 "signifikan bila CI tidak memuat 0 (Hayes, 2018). Uji Sobel disertakan sebagai pembanding tetapi "
                 "kurang dianjurkan karena mengasumsikan a·b berdistribusi normal.")
    notes.append("Istilah 'mediasi penuh/parsial' banyak dikritik (Hayes, 2018); laporkan besaran a·b dan c' apa adanya. "
                 "Mediasi dengan data potong-lintang tidak membuktikan hubungan kausal.")
    apa = [f"Efek tak langsung {x} → {m} → {y}: a·b = {fmt.num(ab, 3)}, {int(conf_level * 100)}% CI bootstrap "
           f"{fmt.ci(lo, hi, 3)} ({'signifikan' if boot_sig else 'tidak signifikan'}); a = {fmt.num(a, 3)}, "
           f"b = {fmt.num(b, 3)}, c = {fmt.num(c, 3)}, c' = {fmt.num(cp, 3)}, {fmt.p(paths[3]['p'])} untuk c'."]
    return {
        "result": {"paths": paths, "indirect_effect": ab, "indirect_ci_boot": [float(lo), float(hi)],
                   "indirect_significant": boot_sig, "sobel": {"z": z, "se": se_sobel, "p": p_sobel},
                   "kesimpulan": kind, "n_boot": n_boot, "seed": seed, "n": n},
        "effect_size": {"indirect_standardized": ab_std,
                        "proportion_mediated": ab / c if abs(c) > 1e-12 else None,
                        "catatan": "Proporsi termediasi tidak stabil bila c kecil; jangan ditafsirkan bila c ≈ 0."},
        "assumptions": {"normality_of_residuals_y_model": {k_: v for k_, v in _normality_one(np.asarray(rb.resid), 0.05).items()
                                                            if k_ in ("n", "shapiro_wilk", "normal", "keputusan")}},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, n, n_dropped, {"x": x, "m": m, "y": y, "covariates": covariates}),
    }


def moderation(ds: Dataset, y: str, x: str, w: str, covariates: list[str] | None = None, center: bool = True,
               conf_level: float = 0.95) -> dict:
    """Moderasi (model 1 Hayes): Y = b0 + b1·X + b2·W + b3·X·W (+ kovariat). Simple slopes X pada W = M − 1SD, M, M + 1SD
    (atau pada tiap nilai W bila W biner 0/1)."""
    import statsmodels.api as sm

    covariates = list(covariates or [])
    notes: list = []
    df_, n0, n_dropped = numeric_frame(ds, [y, x, w, *covariates], notes)
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang (listwise) karena ada nilai kosong.")
    n = len(df_)
    if n < 10 + len(covariates):
        raise DataError(f"Data lengkap ({n}) terlalu sedikit untuk moderasi.")
    Xv, Wv, Yv = df_[x].to_numpy(), df_[w].to_numpy(), df_[y].to_numpy()
    binary_w = set(np.unique(Wv)) <= {0.0, 1.0}
    mx = Xv.mean() if center else 0.0
    mw = Wv.mean() if (center and not binary_w) else 0.0
    xc, wc = Xv - mx, Wv - mw
    C = df_[covariates].to_numpy() if covariates else np.empty((n, 0))
    D = sm.add_constant(np.column_stack([xc, wc, xc * wc, C]), has_constant="add")
    res = sm.OLS(Yv, D).fit()
    res0 = sm.OLS(Yv, sm.add_constant(np.column_stack([xc, wc, C]), has_constant="add")).fit()
    names = ["(Constant)", x, w, f"{x} × {w}", *covariates]
    ci = res.conf_int(alpha=1 - conf_level)
    coefs = [{"term": nm, "B": float(res.params[i]), "se": float(res.bse[i]), "t": float(res.tvalues[i]),
              "p": float(res.pvalues[i]), "ci": [float(ci[i, 0]), float(ci[i, 1])]} for i, nm in enumerate(names)]
    dr2 = float(res.rsquared - res0.rsquared)
    f_ch = dr2 / ((1 - res.rsquared) / res.df_resid)
    p_ch = float(stats.f.sf(f_ch, 1, res.df_resid))

    cov = res.cov_params()
    if binary_w:
        points = [("W = 0", 0.0), ("W = 1", 1.0)]
    else:
        sd = Wv.std(ddof=1)
        points = [("M − 1SD", Wv.mean() - sd), ("M", Wv.mean()), ("M + 1SD", Wv.mean() + sd)]
    tcrit = stats.t.ppf(0.5 + conf_level / 2, res.df_resid)
    slopes = []
    for lab, wv in points:
        wcv = wv - mw
        est = res.params[1] + res.params[3] * wcv
        se = math.sqrt(cov[1, 1] + wcv ** 2 * cov[3, 3] + 2 * wcv * cov[1, 3])
        t = est / se
        slopes.append({"at": lab, "w_value": float(wv), "slope": float(est), "se": se, "t": float(t),
                       "p": float(2 * stats.t.sf(abs(t), res.df_resid)), "ci": [est - tcrit * se, est + tcrit * se]})
    inter = coefs[3]
    apa = [f"Interaksi {x} × {w}: B = {fmt.num(inter['B'], 3)}, t({int(res.df_resid)}) = {fmt.num(inter['t'])}, "
           f"{fmt.p(inter['p'])}, ΔR² = {fmt.nolead(dr2, 3)}"]
    for s in slopes:
        apa.append(f"Simple slope {x} pada {w} {s['at']} ({fmt.num(s['w_value'])}): B = {fmt.num(s['slope'], 3)}, "
                   f"{fmt.p(s['p'])}, {int(conf_level * 100)}% CI {fmt.ci(*s['ci'], d=3)}")
    if center:
        notes.append("X" + (" dan W" if not binary_w else "") + " di-center pada reratanya; B untuk X dan W adalah efek "
                     "bersyarat pada rerata variabel lainnya. B interaksi tidak berubah oleh centering.")
    notes.append("Moderasi ditentukan oleh signifikansi B interaksi (setara uji ΔR²). Simple slopes hanya ditafsirkan "
                 "bila interaksi bermakna. Johnson-Neyman belum tersedia.")
    return {
        "result": {"coefficients": coefs, "R2": float(res.rsquared), "delta_R2_interaction": dr2,
                   "F_change": f_ch, "p_change": p_ch, "simple_slopes": slopes, "w_binary": binary_w,
                   "centered": center, "n": n, **fmt.sig(inter["p"], 0.05)},
        "effect_size": {"delta_R2": dr2, "f2_interaction": dr2 / (1 - res.rsquared), "label": fmt.label_f2(dr2 / (1 - res.rsquared))},
        "assumptions": {"normality_of_residuals": {k_: v for k_, v in _normality_one(np.asarray(res.resid), 0.05).items()
                                                   if k_ in ("n", "shapiro_wilk", "normal", "keputusan")}},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, n, n_dropped, {"y": y, "x": x, "w": w, "covariates": covariates}),
    }

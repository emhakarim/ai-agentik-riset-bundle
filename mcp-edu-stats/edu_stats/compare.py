"""Uji perbandingan: uji-t, ANOVA satu arah (+ post hoc), dan uji nonparametrik.

Konvensi:
- Setiap fungsi menerima `Dataset` dan mengembalikan dict berisi `result`, `apa`,
  `assumptions`, `effect_size`, `notes`, `input`. Audit ditambahkan oleh server/CLI.
- Selisih dihitung grup/kolom PERTAMA dikurangi KEDUA (sama seperti SPSS).
- `alternative`: "two-sided" (default), "greater" (pertama > kedua), "less".
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
from scipy import optimize, stats

from . import fmt
from .data import Dataset, DataError, check_columns, group_series, numeric_frame, select_groups, to_numeric
from .describe import _desc, _levene, _normality_one

_ALTS = ("two-sided", "greater", "less")


# ---------------------------------------------------------------- utilitas
def _check_alt(alternative: str) -> str:
    if alternative not in _ALTS:
        raise DataError(f"alternative harus salah satu dari {_ALTS}, bukan {alternative!r}")
    return alternative


def _input(ds: Dataset, n_used: int, n_dropped: int, extra: dict | None = None) -> dict:
    out = {"file": ds.path, "sha256": ds.sha256, "n_used": int(n_used), "n_dropped": int(n_dropped)}
    if extra:
        out.update(extra)
    return out


def _p_from_t(t: float, df: float, alternative: str) -> float:
    if alternative == "two-sided":
        return float(2 * stats.t.sf(abs(t), df))
    if alternative == "greater":
        return float(stats.t.sf(t, df))
    return float(stats.t.cdf(t, df))


def _p_from_z(z: float, alternative: str) -> float:
    if alternative == "two-sided":
        return float(2 * stats.norm.sf(abs(z)))
    if alternative == "greater":
        return float(stats.norm.sf(z))
    return float(stats.norm.cdf(z))


def _t_ci(est: float, se: float, df: float, conf: float, alternative: str) -> tuple[float, float]:
    """CI selisih rerata, konsisten dengan arah uji (satu sisi -> batas tak hingga)."""
    if alternative == "two-sided":
        q = stats.t.ppf(0.5 + conf / 2, df)
        return est - q * se, est + q * se
    q = stats.t.ppf(conf, df)
    if alternative == "greater":
        return est - q * se, math.inf
    return -math.inf, est + q * se


def _ncp_ci(t_obs: float, df: float, conf: float) -> tuple[float, float]:
    """CI parameter noncentrality t (metode inversi, Steiger & Fouladi 1997)."""
    if t_obs < 0:
        # Simetri: T ~ nct(df, ncp) <=> -T ~ nct(df, -ncp). scipy dapat mengembalikan NaN untuk
        # nct.cdf(x < 0, df, ncp besar), sehingga t negatif dihitung lewat |t| lalu dicerminkan.
        lo, hi = _ncp_ci(-t_obs, df, conf)
        return -hi, -lo
    a = (1 - conf) / 2

    def solve(target):
        f = lambda ncp: stats.nct.cdf(t_obs, df, ncp) - target  # noqa: E731
        lo, hi = t_obs - 10, t_obs + 10
        while f(lo) < 0:
            lo -= 10
        while f(hi) > 0:
            hi += 10
        return optimize.brentq(f, lo, hi, xtol=1e-10)

    return solve(1 - a), solve(a)


def _hedges_j(df: float) -> float:
    return math.exp(math.lgamma(df / 2) - math.log(math.sqrt(df / 2)) - math.lgamma((df - 1) / 2))


def _group_samples(ds: Dataset, dv: str, group: str, groups: list[str] | None, need: int | None, notes: list):
    check_columns(ds, [dv, group])
    x = to_numeric(ds.df[dv], dv, notes)
    g = group_series(ds, group)
    levs = select_groups(g, groups, need)
    in_sel = g.isin(levs)
    n_dropped = int((in_sel & x.isna()).sum())
    n_other = int((~in_sel).sum())
    if n_other:
        notes.append(f"{n_other} baris di luar grup terpilih {levs} (atau grup kosong) tidak dianalisis.")
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang karena nilai '{dv}' kosong.")
    samples = [x[(g == lev) & x.notna()].to_numpy(dtype=float) for lev in levs]
    for lev, s in zip(levs, samples):
        if len(s) < 2:
            raise DataError(f"Grup '{lev}' hanya punya {len(s)} data valid; butuh minimal 2.")
    return levs, samples, n_dropped


def _group_desc(levs, samples) -> list[dict]:
    rows = []
    for lev, s in zip(levs, samples):
        d = _desc(s)
        rows.append({"group": lev, "n": d["n"], "mean": d["mean"], "sd": d["sd"], "se": d["se"],
                     "median": d["median"], "min": d["min"], "max": d["max"]})
    return rows


def _normality_block(levs, samples, alpha) -> dict:
    out = {}
    for lev, s in zip(levs, samples):
        r = _normality_one(s, alpha)
        out[str(lev)] = {k: r.get(k) for k in ("n", "shapiro_wilk", "normal", "keputusan", "error")}
    return out


def _alt_note(alternative: str, a: str, b: str) -> str:
    if alternative == "two-sided":
        return "Uji dua sisi."
    sign = ">" if alternative == "greater" else "<"
    return f"Uji satu sisi: H1 {a} {sign} {b}. CI dilaporkan satu sisi."


# ---------------------------------------------------------------- uji-t
def ttest_independent(ds: Dataset, dv: str, group: str, groups: list[str] | None = None,
                      alpha: float = 0.05, alternative: str = "two-sided", conf_level: float = 0.95) -> dict:
    _check_alt(alternative)
    notes: list = []
    levs, (x1, x2), n_dropped = _group_samples(ds, dv, group, groups, 2, notes)
    n1, n2 = len(x1), len(x2)
    m1, m2 = x1.mean(), x2.mean()
    v1, v2 = x1.var(ddof=1), x2.var(ddof=1)
    diff = m1 - m2

    # Student (varians diasumsikan sama)
    df_s = n1 + n2 - 2
    sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / df_s)
    se_s = sp * math.sqrt(1 / n1 + 1 / n2)
    t_s = diff / se_s
    p_s = _p_from_t(t_s, df_s, alternative)
    ci_s = _t_ci(diff, se_s, df_s, conf_level, alternative)

    # Welch
    se_w = math.sqrt(v1 / n1 + v2 / n2)
    df_w = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    t_w = diff / se_w
    p_w = _p_from_t(t_w, df_w, alternative)
    ci_w = _t_ci(diff, se_w, df_w, conf_level, alternative)

    lev = _levene([x1, x2], alpha)
    use_welch = not lev["homogeneous"]
    chosen = "welch" if use_welch else "student"
    t, dfv, pv = (t_w, df_w, p_w) if use_welch else (t_s, df_s, p_s)

    # Effect size: Cohen's d (SD gabungan), Hedges' g, CI via noncentral t
    d = diff / sp
    j = _hedges_j(df_s)
    g = d * j
    k = math.sqrt(n1 * n2 / (n1 + n2))
    lo, hi = _ncp_ci(d * k, df_s, conf_level)
    d_ci = (lo / k, hi / k)

    a, b = str(levs[0]), str(levs[1])
    test_name = "Welch's t-test" if use_welch else "Student's t-test"
    apa = (f"{test_name}: {a} (M = {fmt.num(m1)}, SD = {fmt.num(math.sqrt(v1))}) vs {b} "
           f"(M = {fmt.num(m2)}, SD = {fmt.num(math.sqrt(v2))}), t({fmt.df_str(dfv)}) = {fmt.num(t)}, {fmt.p(pv)}, "
           f"d = {fmt.num(d)}, {int(conf_level * 100)}% CI {fmt.ci(*d_ci)}")
    notes.append(_alt_note(alternative, a, b))
    notes.append("Pemilihan Student/Welch berdasarkan Levene (mean). Banyak ahli menganjurkan Welch "
                 "sebagai default karena tetap valid saat varians sama; keduanya dilaporkan.")
    notes.append("Cohen's d memakai SD gabungan (pooled); CI d dihitung dengan distribusi t noncentral.")
    return {
        "result": {
            "groups": _group_desc(levs, [x1, x2]),
            "mean_difference": diff,
            "student": {"t": t_s, "df": df_s, "p": p_s, "se_diff": se_s, "ci_diff": list(ci_s)},
            "welch": {"t": t_w, "df": df_w, "p": p_w, "se_diff": se_w, "ci_diff": list(ci_w)},
            "recommended": chosen,
            "alternative": alternative,
            **fmt.sig(pv, alpha),
        },
        "effect_size": {"cohens_d": d, "cohens_d_ci": list(d_ci), "hedges_g": g, "label": fmt.label_d(d),
                        "conf_level": conf_level},
        "assumptions": {"normality": _normality_block(levs, [x1, x2], alpha), "homogeneity": lev},
        "apa": [apa],
        "notes": notes,
        "input": _input(ds, n1 + n2, n_dropped, {"dv": dv, "group": group, "groups": levs}),
    }


def ttest_paired(ds: Dataset, var1: str, var2: str, alpha: float = 0.05, alternative: str = "two-sided",
                 conf_level: float = 0.95) -> dict:
    _check_alt(alternative)
    notes: list = []
    df_, n0, n_dropped = numeric_frame(ds, [var1, var2], notes)
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang (listwise) karena salah satu nilai kosong.")
    n = len(df_)
    if n < 2:
        raise DataError(f"Hanya {n} pasangan lengkap; butuh minimal 2.")
    x1, x2 = df_[var1].to_numpy(), df_[var2].to_numpy()
    dif = x1 - x2
    md, sd_d = dif.mean(), dif.std(ddof=1)
    if sd_d == 0:
        raise DataError("Semua selisih pasangan sama persis; uji-t berpasangan tidak bisa dihitung.")
    se = sd_d / math.sqrt(n)
    dfv = n - 1
    t = md / se
    pv = _p_from_t(t, dfv, alternative)
    ci = _t_ci(md, se, dfv, conf_level, alternative)
    r12 = float(np.corrcoef(x1, x2)[0, 1])

    dz = md / sd_d
    lo, hi = _ncp_ci(t, dfv, conf_level)
    dz_ci = (lo / math.sqrt(n), hi / math.sqrt(n))
    d_av = md / ((x1.std(ddof=1) + x2.std(ddof=1)) / 2)

    apa = (f"Paired t-test: {var1} (M = {fmt.num(x1.mean())}, SD = {fmt.num(x1.std(ddof=1))}) vs {var2} "
           f"(M = {fmt.num(x2.mean())}, SD = {fmt.num(x2.std(ddof=1))}), t({dfv}) = {fmt.num(t)}, {fmt.p(pv)}, "
           f"d_z = {fmt.num(dz)}, {int(conf_level * 100)}% CI {fmt.ci(*dz_ci)}")
    notes.append(_alt_note(alternative, var1, var2))
    notes.append("Selisih = kolom pertama − kolom kedua. d_z = rerata selisih / SD selisih; "
                 "d_av = rerata selisih / rata-rata kedua SD (lebih sebanding dengan d independen).")
    return {
        "result": {
            "variables": [{"variable": v, **{k: _desc(a)[k] for k in ("n", "mean", "sd", "se")}}
                          for v, a in ((var1, x1), (var2, x2))],
            "mean_difference": md, "sd_difference": sd_d, "se_difference": se, "ci_difference": list(ci),
            "t": t, "df": dfv, "p": pv, "correlation": r12, "alternative": alternative,
            **fmt.sig(pv, alpha),
        },
        "effect_size": {"d_z": dz, "d_z_ci": list(dz_ci), "d_av": d_av, "label": fmt.label_d(dz),
                        "conf_level": conf_level},
        "assumptions": {"normality_of_differences": {k: v for k, v in _normality_one(dif, alpha).items()
                                                      if k in ("n", "shapiro_wilk", "normal", "keputusan", "error")}},
        "apa": [apa],
        "notes": notes,
        "input": _input(ds, n, n_dropped, {"var1": var1, "var2": var2}),
    }


def ttest_one_sample(ds: Dataset, column: str, mu: float, alpha: float = 0.05, alternative: str = "two-sided",
                     conf_level: float = 0.95) -> dict:
    _check_alt(alternative)
    notes: list = []
    check_columns(ds, [column])
    s = to_numeric(ds.df[column], column, notes)
    n_dropped = int(s.isna().sum())
    x = s.dropna().to_numpy()
    n = len(x)
    if n < 2:
        raise DataError(f"Hanya {n} data valid; butuh minimal 2.")
    m, sd = x.mean(), x.std(ddof=1)
    if sd == 0:
        raise DataError("Semua nilai sama; uji-t satu sampel tidak bisa dihitung.")
    se = sd / math.sqrt(n)
    dfv = n - 1
    t = (m - mu) / se
    pv = _p_from_t(t, dfv, alternative)
    ci = _t_ci(m - mu, se, dfv, conf_level, alternative)
    d = (m - mu) / sd
    lo, hi = _ncp_ci(t, dfv, conf_level)
    d_ci = (lo / math.sqrt(n), hi / math.sqrt(n))
    apa = (f"One-sample t-test: {column} (M = {fmt.num(m)}, SD = {fmt.num(sd)}) vs μ0 = {fmt.num(mu)}, "
           f"t({dfv}) = {fmt.num(t)}, {fmt.p(pv)}, d = {fmt.num(d)}, {int(conf_level * 100)}% CI {fmt.ci(*d_ci)}")
    notes.append(_alt_note(alternative, column, f"μ0 = {mu}"))
    if n_dropped:
        notes.append(f"{n_dropped} nilai kosong dibuang.")
    return {
        "result": {"n": n, "mean": m, "sd": sd, "se": se, "mu": mu, "mean_difference": m - mu,
                   "ci_difference": list(ci), "t": t, "df": dfv, "p": pv, "alternative": alternative,
                   **fmt.sig(pv, alpha)},
        "effect_size": {"cohens_d": d, "cohens_d_ci": list(d_ci), "label": fmt.label_d(d), "conf_level": conf_level},
        "assumptions": {"normality": {k: v for k, v in _normality_one(x, alpha).items()
                                      if k in ("n", "shapiro_wilk", "normal", "keputusan", "error")}},
        "apa": [apa],
        "notes": notes,
        "input": _input(ds, n, n_dropped, {"column": column}),
    }


# ---------------------------------------------------------------- ANOVA satu arah
def _tukey(levs, samples, msw, dfw, conf):
    k = len(samples)
    qcrit = stats.studentized_range.ppf(conf, k, dfw)
    rows = []
    for (i, a), (j, b) in itertools.combinations(enumerate(levs), 2):
        xi, xj = samples[i], samples[j]
        diff = xi.mean() - xj.mean()
        se = math.sqrt(msw / 2 * (1 / len(xi) + 1 / len(xj)))
        q = abs(diff) / se
        rows.append({"group1": a, "group2": b, "mean_difference": diff, "se": se * math.sqrt(2),
                     "q": q, "p": float(stats.studentized_range.sf(q, k, dfw)),
                     "ci": [diff - qcrit * se, diff + qcrit * se]})
    return rows


def _games_howell(levs, samples, conf):
    k = len(samples)
    rows = []
    for (i, a), (j, b) in itertools.combinations(enumerate(levs), 2):
        xi, xj = samples[i], samples[j]
        ni, nj = len(xi), len(xj)
        vi, vj = xi.var(ddof=1) / ni, xj.var(ddof=1) / nj
        diff = xi.mean() - xj.mean()
        se = math.sqrt(vi + vj)
        dfv = (vi + vj) ** 2 / (vi ** 2 / (ni - 1) + vj ** 2 / (nj - 1))
        q = abs(diff) / se * math.sqrt(2)
        qcrit = stats.studentized_range.ppf(conf, k, dfv)
        half = qcrit * se / math.sqrt(2)
        rows.append({"group1": a, "group2": b, "mean_difference": diff, "se": se, "df": dfv, "q": q,
                     "p": float(stats.studentized_range.sf(q, k, dfv)), "ci": [diff - half, diff + half]})
    return rows


def anova_oneway(ds: Dataset, dv: str, group: str, groups: list[str] | None = None, alpha: float = 0.05,
                 conf_level: float = 0.95) -> dict:
    notes: list = []
    levs, samples, n_dropped = _group_samples(ds, dv, group, groups, None, notes)
    k = len(samples)
    if k < 3:
        notes.append("Hanya 2 grup: ANOVA setara dengan uji-t Student (F = t²).")
    ns = np.array([len(s) for s in samples], dtype=float)
    means = np.array([s.mean() for s in samples])
    vars_ = np.array([s.var(ddof=1) for s in samples])
    allx = np.concatenate(samples)
    N = len(allx)
    gm = allx.mean()
    ssb = float(np.sum(ns * (means - gm) ** 2))
    ssw = float(np.sum((ns - 1) * vars_))
    sst = ssb + ssw
    dfb, dfw = k - 1, N - k
    msb, msw = ssb / dfb, ssw / dfw
    F = msb / msw
    pF = float(stats.f.sf(F, dfb, dfw))

    # Welch ANOVA
    w = ns / vars_
    sw = w.sum()
    mw = float(np.sum(w * means) / sw)
    A = float(np.sum(w * (means - mw) ** 2) / (k - 1))
    tmp = float(np.sum((1 - w / sw) ** 2 / (ns - 1)))
    B = 1 + 2 * (k - 2) / (k ** 2 - 1) * tmp
    F_w = A / B
    df2_w = (k ** 2 - 1) / (3 * tmp)
    p_w = float(stats.f.sf(F_w, k - 1, df2_w))

    eta2 = ssb / sst
    omega2 = (ssb - dfb * msw) / (sst + msw)

    lev = _levene(samples, alpha)
    homog = lev["homogeneous"]
    tukey = _tukey(levs, samples, msw, dfw, conf_level)
    gh = _games_howell(levs, samples, conf_level)
    rec_test = "classic" if homog else "welch"
    rec_post = "tukey" if homog else "games_howell"
    Fx, d2x, px = (F, dfw, pF) if homog else (F_w, df2_w, p_w)
    label = "F" if homog else "Welch's F"
    apa = [f"One-way ANOVA ({label}): F({dfb}, {fmt.df_str(d2x)}) = {fmt.num(Fx)}, {fmt.p(px)}, "
           f"η² = {fmt.nolead(eta2)}, ω² = {fmt.nolead(omega2)}"]
    for r in (tukey if homog else gh):
        apa.append(f"{'Tukey' if homog else 'Games-Howell'} {r['group1']} − {r['group2']}: "
                   f"Δ = {fmt.num(r['mean_difference'])}, {int(conf_level * 100)}% CI {fmt.ci(*r['ci'])}, {fmt.p(r['p'])}")
    notes.append("Pemilihan ANOVA klasik/Welch dan post hoc Tukey/Games-Howell berdasarkan Levene (mean).")
    notes.append("η² cenderung bias ke atas pada sampel kecil; ω² lebih konservatif.")
    return {
        "result": {
            "groups": _group_desc(levs, samples),
            "anova": {"ss_between": ssb, "ss_within": ssw, "ss_total": sst, "df_between": dfb, "df_within": dfw,
                      "ms_between": msb, "ms_within": msw, "F": F, "p": pF},
            "welch": {"F": F_w, "df1": k - 1, "df2": df2_w, "p": p_w},
            "recommended_test": rec_test,
            "posthoc": {"tukey": tukey, "games_howell": gh, "recommended": rec_post},
            **fmt.sig(px, alpha),
        },
        "effect_size": {"eta_squared": eta2, "omega_squared": omega2, "label": fmt.label_eta2(eta2)},
        "assumptions": {"normality": _normality_block(levs, samples, alpha), "homogeneity": lev},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, N, n_dropped, {"dv": dv, "group": group, "groups": levs}),
    }


# ---------------------------------------------------------------- nonparametrik
def _tie_sum(x: np.ndarray) -> float:
    _, c = np.unique(x, return_counts=True)
    return float(np.sum(c ** 3 - c))


def mann_whitney(ds: Dataset, dv: str, group: str, groups: list[str] | None = None, alpha: float = 0.05,
                 alternative: str = "two-sided") -> dict:
    _check_alt(alternative)
    notes: list = []
    levs, (x1, x2), n_dropped = _group_samples(ds, dv, group, groups, 2, notes)
    n1, n2 = len(x1), len(x2)
    N = n1 + n2
    allx = np.concatenate([x1, x2])
    rk = stats.rankdata(allx)
    R1, R2 = rk[:n1].sum(), rk[n1:].sum()
    U1 = R1 - n1 * (n1 + 1) / 2
    U2 = n1 * n2 - U1
    mu = n1 * n2 / 2
    sigma = math.sqrt(n1 * n2 / 12 * ((N + 1) - _tie_sum(allx) / (N * (N - 1))))
    z = (U1 - mu) / sigma
    p_asym = _p_from_z(z, alternative)
    has_ties = _tie_sum(allx) > 0
    p_exact = None
    if not has_ties and N <= 50:
        p_exact = float(stats.mannwhitneyu(x1, x2, alternative=alternative, method="exact").pvalue)
    r = abs(z) / math.sqrt(N)
    rrb = 2 * U1 / (n1 * n2) - 1
    a, b = str(levs[0]), str(levs[1])
    apa = (f"Mann-Whitney U: {a} (Mdn = {fmt.num(np.median(x1))}) vs {b} (Mdn = {fmt.num(np.median(x2))}), "
           f"U = {fmt.num(min(U1, U2), 1)}, z = {fmt.num(z)}, {fmt.p(p_asym)}, r = {fmt.nolead(r)}")
    notes.append(_alt_note(alternative, a, b))
    notes.append("z tanpa koreksi kontinuitas, dengan koreksi ties (sama seperti SPSS 'Asymp. Sig.'). "
                 "p eksak dihitung bila n ≤ 50 dan tidak ada ties.")
    notes.append("r = |z|/√N; rank-biserial = 2U₁/(n₁n₂) − 1 (positif: grup pertama cenderung lebih tinggi).")
    return {
        "result": {"groups": [{"group": lv, "n": len(s), "median": float(np.median(s)), "mean_rank": float(R / len(s)),
                               "sum_ranks": float(R)} for lv, s, R in ((a, x1, R1), (b, x2, R2))],
                   "U": float(min(U1, U2)), "U1": float(U1), "U2": float(U2), "z": z, "p": p_asym,
                   "p_exact": p_exact, "alternative": alternative, **fmt.sig(p_asym, alpha)},
        "effect_size": {"r": r, "rank_biserial": rrb, "label": fmt.label_r(r)},
        "assumptions": {"catatan": "Tidak mengasumsikan normalitas. Membandingkan median hanya bila bentuk distribusi kedua grup serupa."},
        "apa": [apa],
        "notes": notes,
        "input": _input(ds, N, n_dropped, {"dv": dv, "group": group, "groups": levs}),
    }


def wilcoxon(ds: Dataset, var1: str, var2: str, alpha: float = 0.05, alternative: str = "two-sided") -> dict:
    _check_alt(alternative)
    notes: list = []
    df_, n0, n_dropped = numeric_frame(ds, [var1, var2], notes)
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang (listwise) karena salah satu nilai kosong.")
    x1, x2 = df_[var1].to_numpy(), df_[var2].to_numpy()
    dif = x1 - x2
    n_zero = int(np.sum(dif == 0))
    d = dif[dif != 0]
    n = len(d)
    if n < 1:
        raise DataError("Semua selisih nol; uji Wilcoxon tidak bisa dihitung.")
    rk = stats.rankdata(np.abs(d))
    Wp, Wm = float(rk[d > 0].sum()), float(rk[d < 0].sum())
    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24 - _tie_sum(np.abs(d)) / 48)
    z = (Wp - mu) / sigma
    pv = _p_from_z(z, alternative)
    r = abs(z) / math.sqrt(n)
    rrb = (Wp - Wm) / (Wp + Wm)
    apa = (f"Wilcoxon signed-rank: {var1} (Mdn = {fmt.num(np.median(x1))}) vs {var2} (Mdn = {fmt.num(np.median(x2))}), "
           f"T = {fmt.num(min(Wp, Wm), 1)}, z = {fmt.num(z)}, {fmt.p(pv)}, r = {fmt.nolead(r)}")
    notes.append(_alt_note(alternative, var1, var2))
    notes.append(f"Selisih = {var1} − {var2}. {n_zero} pasangan dengan selisih nol dibuang (metode Wilcoxon, sama seperti SPSS).")
    notes.append("z memakai koreksi ties tanpa koreksi kontinuitas. r = |z|/√n (n = pasangan tak-nol); "
                 "sebagian buku memakai √(2n) — sebutkan rumus yang dipakai di laporan.")
    return {
        "result": {"n_pairs": len(dif), "n_nonzero": n, "n_zero": n_zero,
                   "n_positive": int(np.sum(d > 0)), "n_negative": int(np.sum(d < 0)),
                   "sum_ranks_positive": Wp, "sum_ranks_negative": Wm, "T": min(Wp, Wm), "z": z, "p": pv,
                   "medians": {var1: float(np.median(x1)), var2: float(np.median(x2))},
                   "alternative": alternative, **fmt.sig(pv, alpha)},
        "effect_size": {"r": r, "rank_biserial": rrb, "label": fmt.label_r(r)},
        "assumptions": {"catatan": "Mengasumsikan distribusi selisih kurang lebih simetris."},
        "apa": [apa],
        "notes": notes,
        "input": _input(ds, len(dif), n_dropped, {"var1": var1, "var2": var2}),
    }


def _adjust(ps: list[float], method: str) -> list[float]:
    m = len(ps)
    if method == "bonferroni":
        return [min(1.0, p * m) for p in ps]
    order = np.argsort(ps)  # Holm
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        adj[i] = run
    return adj.tolist()


def kruskal_wallis(ds: Dataset, dv: str, group: str, groups: list[str] | None = None, alpha: float = 0.05) -> dict:
    notes: list = []
    levs, samples, n_dropped = _group_samples(ds, dv, group, groups, None, notes)
    k = len(samples)
    allx = np.concatenate(samples)
    N = len(allx)
    H, pv = stats.kruskal(*samples)
    H, pv = float(H), float(pv)
    rk = stats.rankdata(allx)
    idx = np.cumsum([0] + [len(s) for s in samples])
    mean_ranks = [float(rk[idx[i]:idx[i + 1]].mean()) for i in range(k)]
    eps2 = H / (N - 1)
    eta2h = (H - k + 1) / (N - k)

    s2 = N * (N + 1) / 12 - _tie_sum(allx) / (12 * (N - 1))
    pairs = []
    for (i, a), (j, b) in itertools.combinations(enumerate(levs), 2):
        ni, nj = len(samples[i]), len(samples[j])
        zz = (mean_ranks[i] - mean_ranks[j]) / math.sqrt(s2 * (1 / ni + 1 / nj))
        pairs.append({"group1": a, "group2": b, "mean_rank_difference": mean_ranks[i] - mean_ranks[j], "z": zz,
                      "p_unadjusted": float(2 * stats.norm.sf(abs(zz)))})
    raw = [r["p_unadjusted"] for r in pairs]
    for r, pb, ph in zip(pairs, _adjust(raw, "bonferroni"), _adjust(raw, "holm")):
        r["p_bonferroni"], r["p_holm"] = pb, ph

    apa = [f"Kruskal-Wallis: H({k - 1}) = {fmt.num(H)}, {fmt.p(pv)}, ε² = {fmt.nolead(eps2)}"]
    if pv < alpha:
        for r in pairs:
            apa.append(f"Dunn {r['group1']} − {r['group2']}: z = {fmt.num(r['z'])}, p (Holm) {fmt.p(r['p_holm'])[2:]}")
    notes.append("H dengan koreksi ties. ε² = H/(N−1) (Tomczak & Tomczak, 2014). Post hoc Dunn memakai varians terkoreksi ties.")
    return {
        "result": {"groups": [{"group": lv, "n": len(s), "median": float(np.median(s)), "mean_rank": mr}
                              for lv, s, mr in zip(levs, samples, mean_ranks)],
                   "H": H, "df": k - 1, "p": pv, "posthoc_dunn": pairs, **fmt.sig(pv, alpha)},
        "effect_size": {"epsilon_squared": eps2, "eta_squared_H": eta2h, "label": fmt.label_eta2(eps2)},
        "assumptions": {"catatan": "Tidak mengasumsikan normalitas; observasi antar grup independen."},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, N, n_dropped, {"dv": dv, "group": group, "groups": levs}),
    }


def friedman(ds: Dataset, columns: list[str], alpha: float = 0.05) -> dict:
    notes: list = []
    if len(columns) < 3:
        raise DataError("Friedman butuh minimal 3 kolom (kondisi/pengukuran berulang). Untuk 2 kolom pakai Wilcoxon.")
    df_, n0, n_dropped = numeric_frame(ds, columns, notes)
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang (listwise) karena ada nilai kosong.")
    n, k = df_.shape
    if n < 2:
        raise DataError(f"Hanya {n} subjek lengkap; butuh minimal 2.")
    chi2, pv = stats.friedmanchisquare(*[df_[c].to_numpy() for c in columns])
    chi2, pv = float(chi2), float(pv)
    ranks = df_.rank(axis=1)
    W = chi2 / (n * (k - 1))
    apa = [f"Friedman: χ²({k - 1}, N = {n}) = {fmt.num(chi2)}, {fmt.p(pv)}, Kendall's W = {fmt.nolead(W)}"]
    notes.append("χ² dengan koreksi ties. Kendall's W = χ²/(n(k−1)). Untuk post hoc gunakan Wilcoxon berpasangan + koreksi Holm.")
    return {
        "result": {"conditions": [{"variable": c, "median": float(df_[c].median()), "mean_rank": float(ranks[c].mean())}
                                  for c in columns],
                   "chi2": chi2, "df": k - 1, "n": n, "p": pv, **fmt.sig(pv, alpha)},
        "effect_size": {"kendalls_w": W, "label": fmt.label_kendall_w(W)},
        "assumptions": {"catatan": "Data berpasangan/berulang pada subjek yang sama; tidak mengasumsikan normalitas."},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, n, n_dropped, {"columns": columns}),
    }


# ---------------------------------------------------------------- model linear: ANCOVA & ANOVA faktorial
def _safe_frame(ds: Dataset, dv: str, factors: list[str], covariates: list[str], notes: list):
    """Data bersih dengan nama kolom aman (y, f0.., c0..) agar formula tidak rusak oleh spasi/simbol."""
    check_columns(ds, [dv, *factors, *covariates])
    d = pd.DataFrame({"y": to_numeric(ds.df[dv], dv, notes)})
    for i, f in enumerate(factors):
        d[f"f{i}"] = group_series(ds, f)
    for i, c in enumerate(covariates):
        d[f"c{i}"] = to_numeric(ds.df[c], c, notes)
    n0 = len(d)
    d = d.dropna()
    n_dropped = n0 - len(d)
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang (listwise) karena ada nilai kosong.")
    for i, f in enumerate(factors):
        d[f"f{i}"] = d[f"f{i}"].astype(str)
        if d[f"f{i}"].nunique() < 2:
            raise DataError(f"Faktor '{f}' hanya punya 1 level setelah data kosong dibuang.")
    return d, n_dropped


def _anova_table(res, names: dict, ss_resid: float) -> list[dict]:
    from statsmodels.stats.anova import anova_lm

    tab = anova_lm(res, typ=3)
    rows = []
    for term, r in tab.iterrows():
        if term == "Intercept":
            continue
        label = "Residual" if term == "Residual" else names.get(term, term)
        row = {"effect": label, "ss": float(r["sum_sq"]), "df": float(r["df"]), "ms": float(r["sum_sq"] / r["df"])}
        if term != "Residual":
            row.update(F=float(r["F"]), p=float(r["PR(>F)"]),
                       partial_eta_squared=float(r["sum_sq"] / (r["sum_sq"] + ss_resid)))
            row["label"] = fmt.label_eta2(row["partial_eta_squared"])
        rows.append(row)
    return rows


def _term_names(factors, covariates) -> dict:
    """Peta nama term statsmodels -> nama kolom asli."""
    base = {f"C(f{i}, Sum)": f for i, f in enumerate(factors)}
    base.update({f"c{i}": c for i, c in enumerate(covariates)})
    out = dict(base)
    keys = list(base)
    for r in range(2, len(keys) + 1):
        for combo in itertools.combinations(keys, r):
            out[":".join(combo)] = " × ".join(base[k] for k in combo)
    return out


def _sort_levels(values) -> list:
    vals = list(values)
    try:
        return sorted(vals, key=float)
    except ValueError:
        return sorted(vals)


def _resid_normality(resid, alpha):
    return {k: v for k, v in _normality_one(np.asarray(resid), alpha).items()
            if k in ("n", "shapiro_wilk", "normal", "keputusan", "error")}


def ancova(ds: Dataset, dv: str, group: str, covariates: list[str], alpha: float = 0.05,
           conf_level: float = 0.95) -> dict:
    """ANCOVA satu faktor (SS tipe III) + uji homogenitas kemiringan regresi + rerata terkoreksi."""
    import statsmodels.formula.api as smf
    from patsy import build_design_matrices

    if not covariates:
        raise DataError("ANCOVA butuh minimal satu kovariat (mis. skor pretest).")
    notes: list = []
    d, n_dropped = _safe_frame(ds, dv, [group], covariates, notes)
    cov_terms = " + ".join(f"c{i}" for i in range(len(covariates)))
    res = smf.ols(f"y ~ C(f0, Sum) + {cov_terms}", data=d).fit()
    names = _term_names([group], covariates)
    table = _anova_table(res, names, float(res.ssr))

    # Homogenitas kemiringan regresi: interaksi grup × kovariat harus tidak signifikan
    inter = " + ".join(f"C(f0, Sum):c{i}" for i in range(len(covariates)))
    res_i = smf.ols(f"y ~ C(f0, Sum) + {cov_terms} + {inter}", data=d).fit()
    slopes = [r for r in _anova_table(res_i, names, float(res_i.ssr)) if "×" in r["effect"]]
    slopes_ok = all(r["p"] > alpha for r in slopes)

    # Rerata terkoreksi pada rerata kovariat + perbandingan berpasangan (Bonferroni)
    levs = _sort_levels(d["f0"].unique())
    newd = pd.DataFrame({"f0": levs, **{f"c{i}": d[f"c{i}"].mean() for i in range(len(covariates))}})
    X = np.asarray(build_design_matrices([res.model.data.design_info], newd)[0])
    pred = res.get_prediction(newd).summary_frame(alpha=1 - conf_level)
    adj = [{"group": lv, "n": int((d["f0"] == lv).sum()), "mean_observed": float(d.y[d.f0 == lv].mean()),
            "mean_adjusted": float(pred["mean"].iloc[i]), "se": float(pred["mean_se"].iloc[i]),
            "ci": [float(pred["mean_ci_lower"].iloc[i]), float(pred["mean_ci_upper"].iloc[i])]}
           for i, lv in enumerate(levs)]
    m = len(levs) * (len(levs) - 1) // 2
    q = stats.t.ppf(1 - (1 - conf_level) / (2 * m), res.df_resid)
    pairs = []
    for i, j in itertools.combinations(range(len(levs)), 2):
        tt = res.t_test(X[i] - X[j])
        diff, se, p = float(np.squeeze(tt.effect)), float(np.squeeze(tt.sd)), float(np.squeeze(tt.pvalue))
        pairs.append({"group1": levs[i], "group2": levs[j], "mean_difference": diff, "se": se,
                      "t": diff / se, "p_unadjusted": p, "p_bonferroni": min(1.0, p * m),
                      "ci_bonferroni": [diff - q * se, diff + q * se]})

    g = next(r for r in table if r["effect"] == group)
    resid = next(r for r in table if r["effect"] == "Residual")
    apa = [f"ANCOVA: {group} F({fmt.df_str(g['df'])}, {fmt.df_str(resid['df'])}) = {fmt.num(g['F'])}, {fmt.p(g['p'])}, "
           f"ηp² = {fmt.nolead(g['partial_eta_squared'])} (kovariat: {', '.join(covariates)})"]
    for a in adj:
        apa.append(f"{a['group']}: M terkoreksi = {fmt.num(a['mean_adjusted'])}, SE = {fmt.num(a['se'])}")
    if not slopes_ok:
        notes.append("PERINGATAN: kemiringan regresi tidak homogen (interaksi grup × kovariat signifikan). "
                     "Asumsi ANCOVA dilanggar; pertimbangkan model moderasi / Johnson-Neyman.")
    notes.append("SS tipe III dengan kode efek (Sum), sama seperti default SPSS. Rerata terkoreksi dihitung pada rerata kovariat.")
    resid_v = np.asarray(res.resid)
    lev_res = _levene([resid_v[(d["f0"] == lv).to_numpy()] for lv in levs], alpha)
    return {
        "result": {"anova_table": table, "adjusted_means": adj, "pairwise_bonferroni": pairs,
                   "r_squared": float(res.rsquared), "adj_r_squared": float(res.rsquared_adj), **fmt.sig(g["p"], alpha)},
        "effect_size": {"partial_eta_squared": g["partial_eta_squared"], "label": g["label"]},
        "assumptions": {
            "homogeneity_of_regression_slopes": {"tests": slopes, "homogeneous": slopes_ok,
                                                 "keputusan": "Kemiringan homogen" if slopes_ok else "Kemiringan TIDAK homogen"},
            "homogeneity_of_variance_residuals": lev_res,
            "normality_of_residuals": _resid_normality(resid_v, alpha),
        },
        "apa": apa,
        "notes": notes,
        "input": _input(ds, len(d), n_dropped, {"dv": dv, "group": group, "covariates": covariates}),
    }


def anova_factorial(ds: Dataset, dv: str, factors: list[str], alpha: float = 0.05) -> dict:
    """ANOVA faktorial antar-subjek (2+ faktor, semua interaksi), SS tipe III."""
    import statsmodels.formula.api as smf

    if len(factors) < 2:
        raise DataError("ANOVA faktorial butuh minimal 2 faktor. Untuk 1 faktor pakai anova_oneway.")
    notes: list = []
    d, n_dropped = _safe_frame(ds, dv, factors, [], notes)
    fcols = [f"f{i}" for i in range(len(factors))]
    cells = d.groupby(fcols)["y"]
    if (cells.size() < 2).any():
        raise DataError("Ada sel (kombinasi level) dengan < 2 data; ANOVA faktorial tidak bisa dihitung andal.")
    res = smf.ols("y ~ " + " * ".join(f"C({c}, Sum)" for c in fcols), data=d).fit()
    table = _anova_table(res, _term_names(factors, []), float(res.ssr))
    resid = next(r for r in table if r["effect"] == "Residual")
    apa = [f"{r['effect']}: F({fmt.df_str(r['df'])}, {fmt.df_str(resid['df'])}) = {fmt.num(r['F'])}, {fmt.p(r['p'])}, "
           f"ηp² = {fmt.nolead(r['partial_eta_squared'])}" for r in table if r["effect"] != "Residual"]
    desc = [{**{factors[i]: key[i] for i in range(len(factors))}, "n": int(len(v)), "mean": float(v.mean()),
             "sd": float(v.std(ddof=1))} for key, v in cells]
    notes.append("SS tipe III dengan kode efek (Sum), sama seperti default SPSS. Bila interaksi signifikan, "
                 "tafsirkan efek utama dengan hati-hati dan lanjutkan dengan analisis simple effects.")
    return {
        "result": {"anova_table": table, "cell_descriptives": desc, "r_squared": float(res.rsquared)},
        "effect_size": {r["effect"]: {"partial_eta_squared": r["partial_eta_squared"], "label": r["label"]}
                        for r in table if r["effect"] != "Residual"},
        "assumptions": {"homogeneity": _levene([v.to_numpy() for _, v in cells], alpha),
                        "normality_of_residuals": _resid_normality(res.resid, alpha)},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, len(d), n_dropped, {"dv": dv, "factors": factors}),
    }


# ---------------------------------------------------------------- ANOVA pengukuran berulang
def anova_rm(ds: Dataset, columns: list[str], alpha: float = 0.05) -> dict:
    """RM-ANOVA satu faktor within (format lebar: satu kolom per pengukuran).

    Uji Mauchly + koreksi Greenhouse-Geisser / Huynh-Feldt; post hoc t berpasangan Bonferroni."""
    if len(columns) < 2:
        raise DataError("RM-ANOVA butuh minimal 2 kolom pengukuran.")
    notes: list = []
    df_, n0, n_dropped = numeric_frame(ds, columns, notes)
    if n_dropped:
        notes.append(f"{n_dropped} subjek dibuang (listwise) karena ada nilai kosong.")
    Y = df_.to_numpy()
    n, k = Y.shape
    if n < k:
        raise DataError(f"Jumlah subjek lengkap ({n}) harus ≥ jumlah pengukuran ({k}).")
    gm = Y.mean()
    ss_cond = n * float(np.sum((Y.mean(axis=0) - gm) ** 2))
    ss_subj = k * float(np.sum((Y.mean(axis=1) - gm) ** 2))
    ss_err = float(np.sum((Y - gm) ** 2)) - ss_cond - ss_subj
    df1, df2 = k - 1, (k - 1) * (n - 1)
    F = (ss_cond / df1) / (ss_err / df2)
    p = float(stats.f.sf(F, df1, df2))
    peta2 = ss_cond / (ss_cond + ss_err)
    geta2 = ss_cond / (ss_cond + ss_subj + ss_err)

    # Sferisitas: kontras ortonormal (Helmert)
    pdim = k - 1
    C = np.zeros((k, pdim))
    for j in range(pdim):
        C[: j + 1, j] = 1
        C[j + 1, j] = -(j + 1)
        C[:, j] /= np.linalg.norm(C[:, j])
    S = np.atleast_2d(np.cov(Y @ C, rowvar=False, ddof=1))
    eps_gg = float(np.trace(S) ** 2 / (pdim * np.trace(S @ S)))
    eps_hf = min(1.0, (n * pdim * eps_gg - 2) / (pdim * (n - 1 - pdim * eps_gg)))
    if k > 2:
        W = float(np.linalg.det(S) / (np.trace(S) / pdim) ** pdim)
        f = 1 - (2 * pdim ** 2 + pdim + 2) / (6 * pdim * (n - 1))
        chi2 = -(n - 1) * f * math.log(W)
        dfm = pdim * (pdim + 1) / 2 - 1
        pm = float(stats.chi2.sf(chi2, dfm))
        # p dengan suku orde kedua (Anderson; sama seperti R mauchly.test & pingouin)
        w2 = ((pdim + 2) * (pdim - 1) * (pdim - 2) * (2 * pdim ** 3 + 6 * pdim ** 2 + 3 * k + 2)
              / (288 * ((n - 1) * pdim * f) ** 2))
        p1, p2 = stats.chi2.sf(chi2, dfm), stats.chi2.sf(chi2, dfm + 4)
        mauchly = {"W": W, "chi2": chi2, "df": dfm, "p": pm, "p_refined": float(p1 + w2 * (p2 - p1)),
                   "sphericity": pm > alpha,
                   "catatan": "p = aproksimasi χ² (seperti SPSS); p_refined = dengan koreksi orde kedua (seperti R)."}
    else:
        mauchly = {"catatan": "Dengan 2 pengukuran sferisitas selalu terpenuhi."}
        pm = 1.0
    corr = {name: {"epsilon": e, "df1": df1 * e, "df2": df2 * e, "p": float(stats.f.sf(F, df1 * e, df2 * e))}
            for name, e in (("greenhouse_geisser", eps_gg), ("huynh_feldt", eps_hf))}
    if pm > alpha:
        use, d1, d2, pu = "sphericity_assumed", df1, df2, p
    else:
        use = "huynh_feldt" if eps_gg > 0.75 else "greenhouse_geisser"
        d1, d2, pu = corr[use]["df1"], corr[use]["df2"], corr[use]["p"]

    m = k * (k - 1) // 2
    pairs = []
    for i, j in itertools.combinations(range(k), 2):
        dif = Y[:, i] - Y[:, j]
        t = dif.mean() / (dif.std(ddof=1) / math.sqrt(n))
        pv = float(2 * stats.t.sf(abs(t), n - 1))
        pairs.append({"var1": columns[i], "var2": columns[j], "mean_difference": float(dif.mean()), "t": float(t),
                      "df": n - 1, "p_unadjusted": pv, "p_bonferroni": min(1.0, pv * m)})
    apa = [f"RM-ANOVA ({use.replace('_', '-')}): F({fmt.df_str(d1)}, {fmt.df_str(d2)}) = {fmt.num(F)}, {fmt.p(pu)}, "
           f"ηp² = {fmt.nolead(peta2)}"]
    if k > 2:
        apa.append(f"Mauchly: W = {fmt.nolead(mauchly['W'], 3)}, χ²({fmt.df_str(mauchly['df'])}) = {fmt.num(mauchly['chi2'])}, "
                   f"{fmt.p(pm)}; ε GG = {fmt.nolead(eps_gg, 3)}")
    notes.append("Bila Mauchly signifikan: ε GG > .75 → Huynh-Feldt, selain itu Greenhouse-Geisser (Girden, 1992).")
    notes.append("ε Huynh-Feldt memakai rumus asli (seperti SPSS), dibatasi maksimal 1.")
    return {
        "result": {"conditions": [{"variable": c, "mean": float(df_[c].mean()), "sd": float(df_[c].std(ddof=1))} for c in columns],
                   "ss_conditions": ss_cond, "ss_subjects": ss_subj, "ss_error": ss_err, "df1": df1, "df2": df2,
                   "F": F, "p_sphericity_assumed": p, "corrections": corr, "recommended": use,
                   "p": pu, "posthoc_bonferroni": pairs, **fmt.sig(pu, alpha)},
        "effect_size": {"partial_eta_squared": peta2, "generalized_eta_squared": geta2, "label": fmt.label_eta2(peta2)},
        "assumptions": {"mauchly": mauchly},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, n, n_dropped, {"columns": columns}),
    }

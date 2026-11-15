"""Instrumen: penyiapan skor skala, reliabilitas (α, ω), validitas butir (r hitung vs r tabel), N-Gain.

Konvensi keluaran sama dengan compare.py. `prepare_scale` adalah satu-satunya fungsi yang menulis file,
dan tidak pernah menimpa file data asli.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats

from . import fmt
from .compare import _input
from .data import Dataset, DataError, check_columns, group_series, numeric_frame, to_numeric, _sha256


# ---------------------------------------------------------------- penyiapan skala
def prepare_scale(ds: Dataset, items: list[str], name: str, reverse: list[str] | None = None,
                  scale_min: float | None = None, scale_max: float | None = None, method: str = "mean",
                  output_path: str | None = None) -> dict:
    """Balik butir negatif, hitung skor total/rerata, dan tulis ke FILE BARU (.csv).

    Skor kosong bila ada butir yang kosong pada baris itu (tidak diisi diam-diam)."""
    reverse = list(reverse or [])
    if method not in ("mean", "sum"):
        raise DataError("method harus 'mean' atau 'sum'.")
    check_columns(ds, items)
    unknown = [r for r in reverse if r not in items]
    if unknown:
        raise DataError(f"Butir terbalik {unknown} tidak ada di daftar items.")
    if reverse and (scale_min is None or scale_max is None):
        raise DataError("Untuk membalik butir, isi scale_min dan scale_max (mis. 1 dan 5 untuk Likert 1–5). "
                        "Rentang tidak ditebak dari data karena bisa salah bila tidak ada responden yang memilih ujung skala.")
    if name in ds.df.columns:
        raise DataError(f"Kolom '{name}' sudah ada; pilih nama skor lain.")
    notes: list = []
    out = ds.df.copy()
    X = pd.DataFrame({c: to_numeric(ds.df[c], c, notes) for c in items})
    if reverse:
        bad = [(c, v) for c in reverse for v in X[c].dropna().unique() if v < scale_min or v > scale_max]
        if bad:
            raise DataError(f"Nilai di luar rentang {scale_min}–{scale_max}: {bad[:5]}")
        for c in reverse:
            X[c] = scale_min + scale_max - X[c]
            out[f"{c}_R"] = X[c]
        notes.append(f"Butir dibalik dengan rumus ({scale_min} + {scale_max}) − x; kolom baru berakhiran _R, kolom asli tetap.")
    n_incomplete = int(X.isna().any(axis=1).sum())
    score = X.mean(axis=1, skipna=False) if method == "mean" else X.sum(axis=1, min_count=len(items))
    score[X.isna().any(axis=1)] = np.nan
    out[name] = score
    if n_incomplete:
        notes.append(f"{n_incomplete} baris punya butir kosong; skor '{name}' dibiarkan kosong pada baris itu.")

    src = Path(ds.path)
    dest = Path(output_path).expanduser() if output_path else src.with_name(f"{src.stem}_skor.csv")
    dest = dest.resolve()
    if dest == src:
        raise DataError("output_path tidak boleh sama dengan file data asli; file asli tidak boleh ditimpa.")
    if dest.suffix.lower() != ".csv":
        raise DataError("output_path harus berakhiran .csv.")
    out.to_csv(dest, index=False, encoding="utf-8")
    notes.append(f"File baru ditulis: {dest}. File asli tidak diubah. Analisis selanjutnya pakai file baru ini.")
    s = score.dropna()
    return {
        "result": {"output_path": str(dest), "output_sha256": _sha256(dest), "score_column": name, "method": method,
                   "items": items, "reversed": reverse, "n_scored": int(len(s)),
                   "score_summary": {"mean": float(s.mean()) if len(s) else None, "sd": float(s.std(ddof=1)) if len(s) > 1 else None,
                                     "min": float(s.min()) if len(s) else None, "max": float(s.max()) if len(s) else None}},
        "apa": [],
        "notes": notes,
        "input": _input(ds, len(s), n_incomplete, {"items": items}),
    }


# ---------------------------------------------------------------- reliabilitas
def _alpha(X: np.ndarray) -> float:
    k = X.shape[1]
    item_var = X.var(axis=0, ddof=1).sum()
    total_var = X.sum(axis=1).var(ddof=1)
    return float(k / (k - 1) * (1 - item_var / total_var))


def _omega_ml(X: np.ndarray) -> dict:
    """Omega total dari model satu faktor ML (skor jumlah tak berbobot), Σ = λλᵀ + Ψ."""
    S = np.cov(X, rowvar=False, ddof=1)
    p = S.shape[0]
    sd = np.sqrt(np.diag(S))
    R = S / np.outer(sd, sd)
    logdet_R = np.linalg.slogdet(R)[1]

    def f_ml(theta):
        lam, psi = theta[:p], theta[p:]
        Sig = np.outer(lam, lam) + np.diag(psi)
        sign, logdet = np.linalg.slogdet(Sig)
        if sign <= 0:
            return 1e10
        return logdet + np.trace(R @ np.linalg.inv(Sig)) - logdet_R - p

    # nilai awal: loading dari komponen utama pertama
    w, v = np.linalg.eigh(R)
    lam0 = np.abs(v[:, -1]) * math.sqrt(w[-1])
    lam0 = np.clip(lam0, 0.1, 0.95)
    x0 = np.concatenate([lam0, 1 - lam0 ** 2])
    bounds = [(-1.5, 1.5)] * p + [(1e-4, 1.5)] * p
    res = optimize.minimize(f_ml, x0, method="L-BFGS-B", bounds=bounds, options={"maxiter": 5000, "ftol": 1e-14, "gtol": 1e-10})
    lam_std, psi_std = res.x[:p], res.x[p:]
    if lam_std.sum() < 0:
        lam_std = -lam_std
    lam_raw, psi_raw = lam_std * sd, psi_std * sd ** 2
    num = lam_raw.sum() ** 2
    omega = float(num / (num + psi_raw.sum()))
    heywood = bool(np.any(psi_std <= 2e-4))
    return {"omega_total": omega, "loadings_std": lam_std.tolist(), "converged": bool(res.success), "heywood_case": heywood}


def _feldt_ci(a: float, n: int, k: int, conf: float) -> tuple[float, float]:
    df1, df2 = n - 1, (n - 1) * (k - 1)
    lo = 1 - (1 - a) * stats.f.ppf(0.5 + conf / 2, df1, df2)
    hi = 1 - (1 - a) * stats.f.ppf(0.5 - conf / 2, df1, df2)
    return float(lo), float(hi)


def r_table(n: int, alpha: float = 0.05) -> float:
    """r kritis (tabel r Product Moment) dua sisi untuk df = n − 2."""
    dfv = n - 2
    t = stats.t.ppf(1 - alpha / 2, dfv)
    return float(t / math.sqrt(t ** 2 + dfv))


def reliability(ds: Dataset, items: list[str], conf_level: float = 0.95, alpha_level: float = 0.05,
                min_item_total: float = 0.30) -> dict:
    """Cronbach's α (+ CI Feldt), α terstandar, ω total, dan statistik butir (validitas butir)."""
    if len(items) < 2:
        raise DataError("Reliabilitas butuh minimal 2 butir.")
    notes: list = []
    df_, n0, n_dropped = numeric_frame(ds, items, notes)
    if n_dropped:
        notes.append(f"{n_dropped} responden dibuang (listwise) karena ada butir kosong.")
    n, k = df_.shape
    if n < 3:
        raise DataError(f"Hanya {n} responden lengkap; butuh minimal 3.")
    const = [c for c in items if df_[c].nunique() < 2]
    if const:
        raise DataError(f"Butir {const} konstan (semua jawaban sama); keluarkan dulu dari analisis.")
    X = df_.to_numpy(dtype=float)
    a = _alpha(X)
    ci = _feldt_ci(a, n, k, conf_level)
    Rm = np.corrcoef(X, rowvar=False)
    rbar = float((Rm.sum() - k) / (k * (k - 1)))
    a_std = k * rbar / (1 + (k - 1) * rbar)
    omega = _omega_ml(X) if k >= 3 else {"omega_total": None, "catatan": "ω butuh minimal 3 butir."}

    total = X.sum(axis=1)
    rcrit = r_table(n, alpha_level)
    rows = []
    for j, c in enumerate(items):
        x = X[:, j]
        rest = total - x
        r_c = float(np.corrcoef(x, rest)[0, 1])
        r_u = float(np.corrcoef(x, total)[0, 1])
        a_del = _alpha(np.delete(X, j, axis=1)) if k > 2 else None
        rows.append({"item": c, "mean": float(x.mean()), "sd": float(x.std(ddof=1)),
                     "r_item_total_corrected": r_c, "r_item_total": r_u, "alpha_if_deleted": a_del,
                     "valid_r_table": bool(r_c >= rcrit), "valid_min_r": bool(r_c >= min_item_total),
                     "alpha_naik_bila_dibuang": bool(a_del is not None and a_del > a)})
    weak = [r["item"] for r in rows if not r["valid_r_table"] or not r["valid_min_r"]]
    neg = [r["item"] for r in rows if r["r_item_total_corrected"] < 0]
    if neg:
        notes.append(f"PERINGATAN: butir {neg} berkorelasi negatif dengan total — kemungkinan butir terbalik yang belum "
                     "dibalik. Jalankan prepare_scale dengan parameter reverse.")
    if weak:
        notes.append(f"Butir di bawah kriteria (r tabel = {fmt.nolead(rcrit, 3)} atau r ≥ {min_item_total}): {weak}. "
                     "Pertimbangkan revisi/buang satu per satu lalu hitung ulang.")
    else:
        notes.append("Semua butir memenuhi kedua kriteria validitas butir.")
    notes.append("r item-total terkoreksi = korelasi butir dengan total butir lain (Corrected Item-Total Correlation SPSS). "
                 "r tabel dua sisi untuk df = n − 2.")
    notes.append("ω total dari model satu faktor ML (McDonald, 1999). Bila skala multidimensi, α dan ω satu faktor kurang tepat.")
    if isinstance(omega, dict) and omega.get("heywood_case"):
        notes.append("PERINGATAN: kasus Heywood (uniqueness ≈ 0) pada model faktor; nilai ω perlu ditafsirkan hati-hati.")
    om = omega.get("omega_total") if isinstance(omega, dict) else None
    apa = [f"Cronbach's α = {fmt.nolead(a)}, {int(conf_level * 100)}% CI {fmt.ci(*ci, lead=False)} "
           f"({k} butir, n = {n}; {fmt.label_alpha(a)})"]
    if om is not None:
        apa.append(f"McDonald's ω = {fmt.nolead(om)}")
    rc = [r["r_item_total_corrected"] for r in rows]
    apa.append(f"r item-total terkoreksi berkisar {fmt.nolead(min(rc))}–{fmt.nolead(max(rc))}; "
               f"{len(items) - len(weak)} dari {k} butir memenuhi kriteria.")
    return {
        "result": {"n": n, "k": k, "cronbach_alpha": a, "alpha_ci": list(ci), "standardized_alpha": a_std,
                   "mean_inter_item_r": rbar, "omega": omega, "r_table": rcrit, "items": rows,
                   "items_below_criteria": weak, "label": fmt.label_alpha(a)},
        "effect_size": {},
        "assumptions": {"catatan": "α mengasumsikan unidimensi dan tau-equivalence; ω hanya mengasumsikan unidimensi."},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, n, n_dropped, {"items": items}),
    }


# ---------------------------------------------------------------- N-Gain
def _gain_cat(g: float) -> str:
    if g >= 0.7:
        return "tinggi"
    if g >= 0.3:
        return "sedang"
    return "rendah"


def _eff_cat(pct: float) -> str:
    if pct < 40:
        return "tidak efektif"
    if pct < 56:
        return "kurang efektif"
    if pct <= 75:
        return "cukup efektif"
    return "efektif"


def _ngain_block(pre: np.ndarray, post: np.ndarray, max_score: float) -> dict:
    ok = pre < max_score
    g = (post[ok] - pre[ok]) / (max_score - pre[ok])
    class_g = (post.mean() - pre.mean()) / (max_score - pre.mean())
    mean_g = float(g.mean()) if len(g) else float("nan")
    cats = pd.Series([_gain_cat(x) for x in g]).value_counts().reindex(["tinggi", "sedang", "rendah"], fill_value=0)
    return {"n": int(len(pre)), "n_excluded_pre_max": int((~ok).sum()), "mean_pre": float(pre.mean()),
            "mean_post": float(post.mean()), "mean_individual_gain": mean_g,
            "sd_individual_gain": float(g.std(ddof=1)) if len(g) > 1 else None,
            "class_average_gain": float(class_g), "category": _gain_cat(mean_g),
            "effectiveness_pct": mean_g * 100, "effectiveness": _eff_cat(mean_g * 100),
            "category_counts": {k: int(v) for k, v in cats.items()},
            "n_negative_gain": int(np.sum(g < 0))}


def n_gain(ds: Dataset, pre: str, post: str, max_score: float, group: str | None = None) -> dict:
    """N-Gain ternormalisasi Hake: g = (post − pre) / (skor maks − pre)."""
    notes: list = []
    cols = [pre, post]
    df_, n0, n_dropped = numeric_frame(ds, cols, notes)
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang karena pretest/posttest kosong.")
    if (df_.to_numpy() > max_score).any():
        raise DataError(f"Ada skor melebihi max_score = {max_score}; periksa data atau max_score.")
    blocks = {}
    if group:
        g = group_series(ds, group).loc[df_.index]
        for lev in sorted(g.dropna().unique(), key=str):
            m = (g == lev).to_numpy()
            blocks[str(lev)] = _ngain_block(df_[pre].to_numpy()[m], df_[post].to_numpy()[m], max_score)
    else:
        blocks["semua"] = _ngain_block(df_[pre].to_numpy(), df_[post].to_numpy(), max_score)
    apa = [f"{k}: rerata N-Gain = {fmt.num(b['mean_individual_gain'])} ({b['category']}), "
           f"N-Gain % = {fmt.num(b['effectiveness_pct'], 1)}% ({b['effectiveness']}), n = {b['n']}" for k, b in blocks.items()]
    excl = sum(b["n_excluded_pre_max"] for b in blocks.values())
    if excl:
        notes.append(f"{excl} siswa dengan pretest = skor maksimum dikeluarkan (N-Gain tidak terdefinisi).")
    notes.append("Kategori Hake (1999): g ≥ .70 tinggi, .30 ≤ g < .70 sedang, g < .30 rendah. "
                 "Tafsiran efektivitas (%): < 40 tidak efektif, 40–55 kurang efektif, 56–75 cukup efektif, > 75 efektif.")
    notes.append("mean_individual_gain = rerata g per siswa; class_average_gain = <g> Hake dari rerata kelas. Sebutkan yang dipakai.")
    if group:
        notes.append("N-Gain bersifat deskriptif. Untuk menguji beda N-Gain antar kelompok, simpan g per siswa lalu "
                     "pakai uji-t independen / Mann-Whitney.")
    return {
        "result": {"max_score": max_score, "groups": blocks},
        "effect_size": {},
        "assumptions": {},
        "apa": apa,
        "notes": notes,
        "input": _input(ds, len(df_), n_dropped, {"pre": pre, "post": post, "group": group}),
    }


# ---------------------------------------------------------------- validitas isi (penilaian ahli)
def _rating_frame(ds: Dataset, raters: list[str], item_col: str | None):
    check_columns(ds, raters + ([item_col] if item_col else []))
    if len(raters) < 2:
        raise DataError("Butuh minimal 2 kolom penilai (ahli).")
    labels = (ds.df[item_col].astype(str).tolist() if item_col
              else [f"butir {i + 1}" for i in range(len(ds.df))])
    return labels


def _aiken_pvalue(s_obs: int, n: int, c: int) -> float:
    """P(S ≥ s_obs) di bawah H0: tiap penilai memilih kategori secara seragam (Aiken, 1985)."""
    pmf = np.array([1.0])
    one = np.full(c, 1.0 / c)
    for _ in range(n):
        pmf = np.convolve(pmf, one)
    return float(pmf[s_obs:].sum())


def _aiken_vcrit(n: int, c: int, alpha: float) -> float | None:
    for s in range(n * (c - 1) + 1):
        if _aiken_pvalue(s, n, c) <= alpha:
            return s / (n * (c - 1))
    return None


def aiken_v(ds: Dataset, raters: list[str], scale_min: float, scale_max: float, item_col: str | None = None,
            alpha: float = 0.05) -> dict:
    """Aiken's V per butir. Format data: satu baris per butir, satu kolom per ahli (skor lo..hi)."""
    notes: list = []
    labels = _rating_frame(ds, raters, item_col)
    c = int(round(scale_max - scale_min)) + 1
    if c < 2 or scale_max - scale_min != c - 1:
        raise DataError("scale_min dan scale_max harus bilangan bulat dengan scale_max > scale_min (mis. 1 dan 5).")
    R = pd.DataFrame({r: to_numeric(ds.df[r], r, notes) for r in raters})
    bad = R[(R < scale_min) | (R > scale_max) | ((R - scale_min) % 1 != 0)].stack()
    if len(bad):
        raise DataError(f"Ada skor di luar {scale_min}–{scale_max} atau bukan bilangan bulat: {bad.unique()[:5].tolist()}")
    rows = []
    for lab, (_, r) in zip(labels, R.iterrows()):
        x = r.dropna().to_numpy()
        n = len(x)
        if n < 2:
            rows.append({"item": lab, "n_raters": n, "error": "kurang dari 2 penilai"})
            continue
        s = int(round(np.sum(x - scale_min)))
        v = s / (n * (c - 1))
        p = _aiken_pvalue(s, n, c)
        vcrit = _aiken_vcrit(n, c, alpha)
        rows.append({"item": lab, "n_raters": n, "sum_s": s, "V": v, "p": p, "V_critical": vcrit,
                     "valid": bool(p <= alpha),
                     "kategori": "tinggi" if v > 0.8 else ("sedang" if v >= 0.4 else "rendah")})
    n_missing = int(R.isna().sum().sum())
    if n_missing:
        notes.append(f"{n_missing} sel penilaian kosong; V tiap butir dihitung dari penilai yang mengisi.")
    vs = [r["V"] for r in rows if "V" in r]
    valid = [r["item"] for r in rows if r.get("valid")]
    notes.append("V = Σ(r − lo) / [n(c − 1)]. p eksak = peluang ekor kanan bila tiap ahli menilai acak seragam "
                 "(dasar tabel Aiken, 1985); butir valid bila p ≤ α (setara V ≥ V_critical).")
    notes.append("Kategori deskriptif yang lazim di Indonesia (Retnawati, 2016): V ≤ .4 rendah, .4 < V ≤ .8 sedang, "
                 "V > .8 tinggi — sebutkan kriteria mana yang dipakai.")
    apa = [f"Aiken's V berkisar {fmt.nolead(min(vs))}–{fmt.nolead(max(vs))} (rerata {fmt.nolead(float(np.mean(vs)))}; "
           f"{len(raters)} ahli, skala {int(scale_min)}–{int(scale_max)}); {len(valid)} dari {len(rows)} butir "
           f"signifikan pada α = {alpha} (V kritis = {fmt.nolead(_aiken_vcrit(len(raters), c, alpha), 3)})."] if vs else []
    return {"result": {"c_categories": c, "n_raters": len(raters), "items": rows, "mean_V": float(np.mean(vs)) if vs else None,
                       "items_valid": valid, "items_not_valid": [r["item"] for r in rows if "V" in r and not r["valid"]]},
            "effect_size": {}, "assumptions": {}, "apa": apa, "notes": notes,
            "input": _input(ds, len(rows), 0, {"raters": raters})}


def _cvr_crit(n: int, alpha: float) -> tuple[int, float]:
    for k in range(n + 1):
        if stats.binom.sf(k - 1, n, 0.5) <= alpha:
            return k, (k - n / 2) / (n / 2)
    return n, 1.0


def cvr_lawshe(ds: Dataset, raters: list[str], essential: list, item_col: str | None = None,
               alpha: float = 0.05) -> dict:
    """CVR Lawshe per butir + CVI. `essential` = nilai yang berarti 'esensial' (mis. [3] atau ["E"])."""
    labels = _rating_frame(ds, raters, item_col)
    if not essential:
        raise DataError("Isi 'essential' dengan nilai jawaban yang berarti esensial, mis. [3] atau [\"E\"].")
    ess = {str(e).strip().lower() for e in essential}
    for e in list(ess):
        try:
            ess.add(fmt.num(float(e), 0))  # '3' dan '3.0' dianggap sama
        except ValueError:
            pass
    rows = []
    for lab, (_, r) in zip(labels, ds.df[raters].iterrows()):
        vals = [v for v in r.tolist() if not (isinstance(v, float) and math.isnan(v)) and str(v).strip() != ""]
        n = len(vals)
        if n < 2:
            rows.append({"item": lab, "n_raters": n, "error": "kurang dari 2 penilai"})
            continue
        norm = []
        for v in vals:
            s = str(v).strip().lower()
            try:
                s = fmt.num(float(s), 0)
            except ValueError:
                pass
            norm.append(s)
        ne = sum(s in ess for s in norm)
        cvr = (ne - n / 2) / (n / 2)
        k, crit = _cvr_crit(n, alpha)
        rows.append({"item": lab, "n_raters": n, "n_essential": ne, "CVR": cvr, "CVR_critical": crit,
                     "n_essential_critical": k, "retained": bool(ne >= k)})
    kept = [r for r in rows if r.get("retained")]
    cvi = float(np.mean([r["CVR"] for r in kept])) if kept else None
    if not any(r.get("n_essential") for r in rows):
        raise DataError(f"Tidak ada satu pun penilaian yang cocok dengan essential = {essential}. Periksa kodenya.")
    notes = ["CVR = (n_e − N/2)/(N/2) (Lawshe, 1975). Batas kritis dari uji binomial eksak satu sisi "
             f"(Ayre & Scally, 2014), α = {alpha}. CVI = rerata CVR butir yang dipertahankan."]
    if len({r['n_raters'] for r in rows if 'n_raters' in r}) > 1:
        notes.append("Jumlah penilai berbeda antarbutir (ada sel kosong); batas kritis dihitung per butir.")
    apa = [f"{len(kept)} dari {len(rows)} butir memenuhi CVR kritis ({fmt.nolead(_cvr_crit(len(raters), alpha)[1])} untuk "
           f"{len(raters)} ahli); CVI = {fmt.nolead(cvi) if cvi is not None else 'n/a'}."]
    return {"result": {"n_raters": len(raters), "items": rows, "CVI": cvi,
                       "items_retained": [r["item"] for r in kept],
                       "items_dropped": [r["item"] for r in rows if "CVR" in r and not r["retained"]]},
            "effect_size": {}, "assumptions": {}, "apa": apa, "notes": notes,
            "input": _input(ds, len(rows), 0, {"raters": raters, "essential": essential})}


# ---------------------------------------------------------------- analisis butir tes kognitif
def _p_cat(p: float) -> str:
    return "sukar" if p < 0.30 else ("sedang" if p <= 0.70 else "mudah")


def _d_cat(d: float) -> str:
    if d < 0:
        return "negatif (buang)"
    if d >= 0.40:
        return "sangat baik"
    if d >= 0.30:
        return "baik"
    if d >= 0.20:
        return "cukup (perlu perbaikan)"
    return "jelek (buang/revisi total)"


def _decision(d: float) -> str:
    return "diterima" if d >= 0.30 else ("revisi" if d >= 0.20 else "dibuang")


def item_analysis_cognitive(ds: Dataset, items: list[str], key: dict | None = None, group_fraction: float = 0.27,
                            alpha_level: float = 0.05) -> dict:
    """Analisis butir tes pilihan ganda / benar-salah: kesukaran (P), daya beda (D atas–bawah), r point-biserial,
    KR-20, dan analisis pengecoh bila `key` (kunci jawaban, {butir: opsi benar}) diberikan.
    Tanpa `key`, data harus sudah berskor 0/1. Jawaban kosong dihitung salah."""
    check_columns(ds, items)
    if len(items) < 2:
        raise DataError("Butuh minimal 2 butir.")
    if not 0.1 <= group_fraction <= 0.5:
        raise DataError("group_fraction harus di antara 0.10 dan 0.50 (lazim 0.27).")
    notes: list = []
    raw = ds.df[items]
    if key:
        missing_key = [i for i in items if i not in key]
        if missing_key:
            raise DataError(f"Kunci jawaban belum ada untuk butir {missing_key}.")
        norm = raw.apply(lambda s: s.map(lambda v: None if pd.isna(v) or str(v).strip() == "" else str(v).strip().upper()))
        X = pd.DataFrame({i: (norm[i] == str(key[i]).strip().upper()).astype(float) for i in items})
    else:
        X = pd.DataFrame({i: to_numeric(raw[i], i, notes) for i in items})
        vals = set(np.unique(X.stack().dropna()))
        if not vals <= {0.0, 1.0}:
            raise DataError(f"Tanpa kunci jawaban, data harus 0/1; ditemukan nilai {sorted(vals)[:6]}. "
                            "Untuk butir uraian/politomus pakai reliability.")
        norm = None
    n_blank = int(raw.isna().sum().sum())
    if n_blank:
        notes.append(f"{n_blank} jawaban kosong dihitung salah (0).")
    X = X.fillna(0.0)
    n, k = X.shape
    if n < 10:
        raise DataError(f"Hanya {n} peserta; analisis butir butuh minimal 10 (idealnya ≥ 30).")
    total = X.sum(axis=1)
    order = np.argsort(-total.to_numpy(), kind="mergesort")
    ng = max(1, int(round(group_fraction * n)))
    up_idx, lo_idx = order[:ng], order[-ng:]
    cut_hi, cut_lo = total.iloc[up_idx].min(), total.iloc[lo_idx].max()
    ties = int(((total == cut_hi).sum() > (total.iloc[up_idx] == cut_hi).sum())
               + ((total == cut_lo).sum() > (total.iloc[lo_idx] == cut_lo).sum()))
    if ties:
        notes.append("Ada skor total yang sama tepat di batas kelompok atas/bawah; peserta dipilih menurut urutan data "
                     "(deterministik). Hasil D bisa sedikit berubah bila urutan baris berubah.")
    rcrit = r_table(n, alpha_level)
    rows = []
    for i in items:
        x = X[i].to_numpy()
        p = float(x.mean())
        pu, pl = float(x[up_idx].mean()), float(x[lo_idx].mean())
        d = pu - pl
        rest = total.to_numpy() - x
        r_pbi = float(np.corrcoef(x, rest)[0, 1]) if 0 < p < 1 and np.ptp(rest) > 0 else None
        row = {"item": i, "P": p, "kesukaran": _p_cat(p), "P_upper": pu, "P_lower": pl, "D": d, "daya_beda": _d_cat(d),
               "r_pbi_corrected": r_pbi, "valid_r_table": bool(r_pbi is not None and r_pbi >= rcrit),
               "keputusan": _decision(d)}
        if norm is not None:
            col = norm[i]
            opts = sorted(set(col.dropna()) | {str(key[i]).strip().upper()})
            dist = []
            for o in opts:
                ch = (col == o).to_numpy()
                prop, cu, cl = float(ch.mean()), float(ch[up_idx].mean()), float(ch[lo_idx].mean())
                is_key = o == str(key[i]).strip().upper()
                entry = {"option": o, "is_key": is_key, "prop_all": prop, "prop_upper": cu, "prop_lower": cl}
                if not is_key:
                    entry["berfungsi"] = bool(prop >= 0.05 and cl > cu)
                    entry["catatan"] = ("berfungsi" if entry["berfungsi"] else
                                        "dipilih < 5% peserta" if prop < 0.05 else "lebih banyak dipilih kelompok atas")
                dist.append(entry)
            prop_blank = float(col.isna().mean())
            row["distractors"] = dist
            row["prop_blank"] = prop_blank
        rows.append(row)
    p_arr = X.mean(axis=0).to_numpy()
    var_t = float(total.var(ddof=0))
    kr20 = float(k / (k - 1) * (1 - np.sum(p_arr * (1 - p_arr)) / var_t)) if var_t > 0 else None
    cnt = pd.Series([r["keputusan"] for r in rows]).value_counts().reindex(["diterima", "revisi", "dibuang"], fill_value=0)
    notes.append(f"Kelompok atas/bawah = {int(group_fraction * 100)}% ({ng} peserta). Kategori P (Arikunto): < .30 sukar, "
                 ".30–.70 sedang, > .70 mudah. Kategori D (Ebel & Frisbie, 1991): ≥ .40 sangat baik, .30–.39 baik, "
                 ".20–.29 cukup, < .20 jelek. Keputusan butir mengikuti D; pertimbangkan juga P dan isi butir.")
    if key:
        notes.append("Pengecoh berfungsi bila dipilih ≥ 5% peserta dan lebih banyak dipilih kelompok bawah daripada atas.")
    notes.append("KR-20 setara Cronbach's α untuk butir 0/1. r point-biserial terkoreksi = korelasi butir dengan skor butir lain.")
    apa = [f"KR-20 = {fmt.nolead(kr20) if kr20 is not None else 'n/a'} ({k} butir, n = {n}; {fmt.label_alpha(kr20)}). "
           f"Butir diterima: {cnt['diterima']}, revisi: {cnt['revisi']}, dibuang: {cnt['dibuang']}."]
    return {"result": {"n": n, "k": k, "n_group": ng, "kr20": kr20, "mean_total": float(total.mean()),
                       "sd_total": float(total.std(ddof=1)), "r_table": rcrit, "items": rows,
                       "summary": {k_: int(v) for k_, v in cnt.items()}},
            "effect_size": {}, "assumptions": {}, "apa": apa, "notes": notes,
            "input": _input(ds, n, 0, {"items": items, "key_given": bool(key)})}


# ---------------------------------------------------------------- kesepakatan antar-penilai
def _kappa_label(k: float) -> str:
    """Landis & Koch (1977)."""
    if k is None or (isinstance(k, float) and math.isnan(k)):
        return "n/a"
    if k < 0:
        return "buruk (poor)"
    for c, lab in [(0.20, "sangat lemah (slight)"), (0.40, "lemah (fair)"), (0.60, "sedang (moderate)"),
                   (0.80, "kuat (substantial)")]:
        if k <= c:
            return lab
    return "hampir sempurna (almost perfect)"


def _icc_label(v: float) -> str:
    """Koo & Li (2016)."""
    if v < 0.5:
        return "buruk (poor)"
    if v < 0.75:
        return "sedang (moderate)"
    if v < 0.9:
        return "baik (good)"
    return "sangat baik (excellent)"


def _as_labels(s: pd.Series) -> pd.Series:
    def norm(v):
        if pd.isna(v) or str(v).strip() == "":
            return None
        try:
            return fmt.num(float(v), 6).rstrip("0").rstrip(".")
        except ValueError:
            return str(v).strip()
    return s.map(norm)


def inter_rater_kappa(ds: Dataset, raters: list[str], weights: str | None = None, conf_level: float = 0.95) -> dict:
    """Kesepakatan kategorik: Cohen's κ (2 penilai; `weights` None/'linear'/'quadratic' untuk data ordinal) atau
    Fleiss' κ (≥ 3 penilai). Format: satu baris per subjek/butir, satu kolom per penilai."""
    from statsmodels.stats.inter_rater import cohens_kappa, fleiss_kappa

    check_columns(ds, raters)
    if len(raters) < 2:
        raise DataError("Butuh minimal 2 kolom penilai.")
    if weights not in (None, "linear", "quadratic"):
        raise DataError("weights harus None, 'linear', atau 'quadratic'.")
    notes: list = []
    L = pd.DataFrame({r: _as_labels(ds.df[r]) for r in raters})
    n0 = len(L)
    L = L.dropna()
    n_dropped = n0 - len(L)
    if n_dropped:
        notes.append(f"{n_dropped} baris dibuang karena ada penilaian kosong.")
    n = len(L)
    if n < 2:
        raise DataError("Kurang dari 2 subjek dengan penilaian lengkap.")
    cats = sorted(set(L.to_numpy().ravel()), key=lambda v: (float(v) if v.replace(".", "", 1).lstrip("-").isdigit() else math.inf, v))
    q = stats.norm.ppf(0.5 + conf_level / 2)
    if len(raters) == 2:
        tab = pd.crosstab(L[raters[0]], L[raters[1]]).reindex(index=cats, columns=cats, fill_value=0)
        wt = {None: None, "linear": "linear", "quadratic": "quadratic"}[weights]
        if weights and not all(c.replace(".", "", 1).lstrip("-").isdigit() for c in cats):
            raise DataError("Kappa berbobot butuh kategori ordinal berupa angka.")
        res = cohens_kappa(tab.to_numpy(), wt=wt) if wt else cohens_kappa(tab.to_numpy())
        k = float(res.kappa)
        se, se0 = float(res.std_kappa), float(res.std_kappa0)
        z = k / se0 if se0 > 0 else float("nan")
        p = float(2 * stats.norm.sf(abs(z)))
        po = float(np.trace(tab.to_numpy()) / n)
        name = "Cohen's κ" + (f" berbobot {weights}" if weights else "")
        result = {"method": name, "kappa": k, "se": se, "ci": [k - q * se, k + q * se], "z": z, "p": p,
                  "percent_agreement": po * 100, "categories": cats,
                  "confusion_table": {str(r): {str(c): int(v) for c, v in row.items()} for r, row in tab.iterrows()}}
        notes.append("SE dan CI asimtotik (Fleiss, Cohen & Everitt, 1969); uji z memakai SE di bawah H0 (κ = 0).")
    else:
        if weights:
            raise DataError("Kappa berbobot hanya untuk 2 penilai. Untuk ≥ 3 penilai ordinal/interval pakai icc.")
        counts = np.array([[int((row == c).sum()) for c in cats] for _, row in L.iterrows()])
        m = len(raters)
        k = float(fleiss_kappa(counts, method="fleiss"))
        pj = counts.sum(axis=0) / (n * m)
        s = float(np.sum(pj * (1 - pj)))
        se0 = math.sqrt(2) / (s * math.sqrt(n * m * (m - 1))) * math.sqrt(max(s ** 2 - np.sum(pj * (1 - pj) * (1 - 2 * pj)), 0))
        z = k / se0 if se0 > 0 else float("nan")
        p = float(2 * stats.norm.sf(abs(z)))
        po = float(np.mean((np.sum(counts * (counts - 1), axis=1)) / (m * (m - 1))))
        name = "Fleiss' κ"
        result = {"method": name, "kappa": k, "se0": se0, "z": z, "p": p, "percent_agreement": po * 100,
                  "categories": cats, "category_proportions": dict(zip(cats, pj.tolist()))}
        notes.append("Fleiss' κ (1971); SE di bawah H0 (Fleiss, Nee & Landis, 1979). CI tidak dihitung.")
    notes.append("Label Landis & Koch (1977): ≤ .20 sangat lemah, .21–.40 lemah, .41–.60 sedang, .61–.80 kuat, > .80 hampir sempurna.")
    label = _kappa_label(k)
    ci_txt = f", {int(conf_level * 100)}% CI {fmt.ci(*result['ci'], lead=False)}" if "ci" in result else ""
    apa = [f"{name} = {fmt.nolead(k)}{ci_txt}, z = {fmt.num(z)}, {fmt.p(p)} ({label}; "
           f"kesepakatan {fmt.num(result['percent_agreement'], 1)}%, {len(raters)} penilai, n = {n})"]
    return {"result": {**result, "n": n, "n_raters": len(raters), "label": label, **fmt.sig(p, 0.05)},
            "effect_size": {}, "assumptions": {}, "apa": apa, "notes": notes,
            "input": _input(ds, n, n_dropped, {"raters": raters, "weights": weights})}


def icc(ds: Dataset, raters: list[str], conf_level: float = 0.95) -> dict:
    """Intraclass correlation (Shrout & Fleiss, 1979; McGraw & Wong, 1996) — enam bentuk, dengan F dan CI.
    Format: satu baris per subjek, satu kolom per penilai (skor interval/rasio atau ordinal banyak kategori)."""
    notes: list = []
    df_, n0, n_dropped = numeric_frame(ds, raters, notes)
    if n_dropped:
        notes.append(f"{n_dropped} subjek dibuang (listwise) karena ada penilaian kosong.")
    Y = df_.to_numpy(dtype=float)
    n, k = Y.shape
    if k < 2 or n < 3:
        raise DataError("ICC butuh minimal 2 penilai dan 3 subjek lengkap.")
    gm = Y.mean()
    ssr = k * float(np.sum((Y.mean(axis=1) - gm) ** 2))
    ssc = n * float(np.sum((Y.mean(axis=0) - gm) ** 2))
    sst = float(np.sum((Y - gm) ** 2))
    sse = sst - ssr - ssc
    ssw = sst - ssr
    df1, dfc, dfe, dfw = n - 1, k - 1, (n - 1) * (k - 1), n * (k - 1)
    msr, msc, mse, msw = ssr / df1, ssc / dfc, sse / dfe, ssw / dfw
    a = 1 - conf_level
    fq = lambda d1, d2: stats.f.ppf(1 - a / 2, d1, d2)  # noqa: E731

    out = {}
    # ICC1: satu arah acak
    f1 = msr / msw
    v1 = (msr - msw) / (msr + (k - 1) * msw)
    fl, fu = f1 / fq(df1, dfw), f1 * fq(dfw, df1)
    out["ICC1"] = {"value": v1, "ci": [(fl - 1) / (fl + k - 1), (fu - 1) / (fu + k - 1)], "F": f1, "df1": df1, "df2": dfw}
    out["ICC1k"] = {"value": (msr - msw) / msr, "ci": [1 - 1 / fl, 1 - 1 / fu], "F": f1, "df1": df1, "df2": dfw}
    # ICC3: dua arah campuran, konsistensi
    f3 = msr / mse
    v3 = (msr - mse) / (msr + (k - 1) * mse)
    fl3, fu3 = f3 / fq(df1, dfe), f3 * fq(dfe, df1)
    out["ICC3"] = {"value": v3, "ci": [(fl3 - 1) / (fl3 + k - 1), (fu3 - 1) / (fu3 + k - 1)], "F": f3, "df1": df1, "df2": dfe}
    out["ICC3k"] = {"value": (msr - mse) / msr, "ci": [1 - 1 / fl3, 1 - 1 / fu3], "F": f3, "df1": df1, "df2": dfe}
    # ICC2: dua arah acak, kesepakatan absolut (CI Satterthwaite)
    v2 = (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
    fj = msc / mse
    vn = (k - 1) * (n - 1) * (k * v2 * fj + n * (1 + (k - 1) * v2) - k * v2) ** 2
    vd = (n - 1) * k ** 2 * v2 ** 2 * fj ** 2 + (n * (1 + (k - 1) * v2) - k * v2) ** 2
    v = vn / vd
    fl2, fu2 = stats.f.ppf(1 - a / 2, n - 1, v), stats.f.ppf(1 - a / 2, v, n - 1)
    lo2 = n * (msr - fl2 * mse) / (fl2 * (k * msc + (k * n - k - n) * mse) + n * msr)
    hi2 = n * (fu2 * msr - mse) / (k * msc + (k * n - k - n) * mse + n * fu2 * msr)
    out["ICC2"] = {"value": v2, "ci": [lo2, hi2], "F": f3, "df1": df1, "df2": dfe}
    out["ICC2k"] = {"value": (msr - mse) / (msr + (msc - mse) / n),
                    "ci": [lo2 * k / (1 + lo2 * (k - 1)), hi2 * k / (1 + hi2 * (k - 1))], "F": f3, "df1": df1, "df2": dfe}
    desc = {"ICC1": "satu arah acak, penilai tunggal", "ICC1k": "satu arah acak, rerata k penilai",
            "ICC2": "dua arah acak, kesepakatan absolut, penilai tunggal",
            "ICC2k": "dua arah acak, kesepakatan absolut, rerata k penilai",
            "ICC3": "dua arah campuran, konsistensi, penilai tunggal",
            "ICC3k": "dua arah campuran, konsistensi, rerata k penilai"}
    for key, d in out.items():
        d["p"] = float(stats.f.sf(d["F"], d["df1"], d["df2"]))
        d["model"] = desc[key]
        d["label"] = _icc_label(d["value"])
    notes.append("Pilih bentuk ICC sebelum melihat hasil (Koo & Li, 2016): penilai dianggap sampel dari populasi penilai "
                 "→ ICC2; hanya penilai ini yang relevan → ICC3; skor akhir = rerata penilai → bentuk 'k'. "
                 "Kesepakatan absolut (ICC2) lebih ketat daripada konsistensi (ICC3).")
    notes.append("Label Koo & Li (2016): < .50 buruk, .50–.75 sedang, .75–.90 baik, > .90 sangat baik — tafsirkan "
                 "berdasarkan CI, bukan hanya nilai titik.")
    r2 = out["ICC2"]
    apa = [f"ICC(2,1) = {fmt.nolead(r2['value'])}, {int(conf_level * 100)}% CI {fmt.ci(*r2['ci'], lead=False)}, "
           f"F({df1}, {dfe}) = {fmt.num(r2['F'])}, {fmt.p(r2['p'])} ({k} penilai, n = {n}; {r2['label']}). "
           "Sebutkan bentuk ICC yang dipakai sesuai desain."]
    return {"result": {"n": n, "k": k, "icc": out,
                       "anova": {"ms_rows": msr, "ms_cols": msc, "ms_error": mse, "ms_within": msw}},
            "effect_size": {}, "assumptions": {}, "apa": apa, "notes": notes,
            "input": _input(ds, n, n_dropped, {"raters": raters})}

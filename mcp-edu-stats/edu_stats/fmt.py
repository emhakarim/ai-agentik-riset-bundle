"""Format angka gaya APA 7 dan label interpretasi baku (deterministik)."""
from __future__ import annotations

import math

import numpy as np


def clean(obj):
    """Ubah tipe numpy/pandas ke tipe JSON biasa; NaN -> None."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    return obj


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def num(x, d: int = 2) -> str:
    if not _ok(x):
        return "n/a"
    s = f"{x:.{d}f}"
    return "0." + "0" * d if s in ("-0." + "0" * d,) else s


def nolead(x, d: int = 2) -> str:
    """Untuk statistik yang tidak bisa > 1 (r, p, alpha, eta²): tanpa nol di depan."""
    s = num(x, d)
    return s.replace("0.", ".", 1) if s.startswith(("0.", "-0.")) else s


def p(pv) -> str:
    if not _ok(pv):
        return "p = n/a"
    if pv < 0.001:
        return "p < .001"
    if pv > 0.999:
        return "p > .999"
    return "p = " + nolead(pv, 3)


def ci(lo, hi, d: int = 2, lead: bool = True) -> str:
    f = num if lead else nolead
    return f"[{f(lo, d)}, {f(hi, d)}]"


def df_str(dfv) -> str:
    if not _ok(dfv):
        return "n/a"
    return str(int(round(dfv))) if abs(dfv - round(dfv)) < 1e-9 else num(dfv, 2)


def sig(pv, alpha: float) -> dict:
    s = bool(_ok(pv) and pv < alpha)
    return {
        "significant": s,
        "keputusan": (f"Signifikan pada α = {alpha} (H0 ditolak)" if s else f"Tidak signifikan pada α = {alpha} (H0 tidak ditolak)"),
    }


def _band(v, cuts, labels):
    if not _ok(v):
        return "n/a"
    a = abs(v)
    for c, lab in zip(cuts, labels):
        if a < c:
            return lab
    return labels[-1]


# Cohen (1988)
def label_d(d):
    return _band(d, [0.2, 0.5, 0.8], ["sangat kecil (negligible)", "kecil (small)", "sedang (medium)", "besar (large)"])


def label_r(r):
    return _band(r, [0.1, 0.3, 0.5], ["sangat kecil (negligible)", "kecil (small)", "sedang (medium)", "besar (large)"])


def label_eta2(e):
    return _band(e, [0.01, 0.06, 0.14], ["sangat kecil (negligible)", "kecil (small)", "sedang (medium)", "besar (large)"])


def label_f2(f2):
    return _band(f2, [0.02, 0.15, 0.35], ["sangat kecil (negligible)", "kecil (small)", "sedang (medium)", "besar (large)"])


def label_cramer_v(v, dfmin: int):
    s = math.sqrt(max(dfmin, 1))
    return _band(v, [0.1 / s, 0.3 / s, 0.5 / s], ["sangat kecil (negligible)", "kecil (small)", "sedang (medium)", "besar (large)"])


def label_kendall_w(w):
    return _band(w, [0.1, 0.3, 0.5], ["sangat lemah", "lemah", "sedang", "kuat"])


# George & Mallery (2003)
def label_alpha(a):
    if not _ok(a):
        return "n/a"
    for c, lab in [(0.9, "sangat baik (excellent)"), (0.8, "baik (good)"), (0.7, "dapat diterima (acceptable)"),
                   (0.6, "diragukan (questionable)"), (0.5, "buruk (poor)")]:
        if a >= c:
            return lab
    return "tidak dapat diterima (unacceptable)"


EFFECT_SIZE_SOURCES = {
    "d / g / r / eta2 / f2": "Cohen, J. (1988). Statistical power analysis for the behavioral sciences (2nd ed.).",
    "alpha": "George, D., & Mallery, P. (2003). SPSS for Windows step by step (4th ed.).",
    "n_gain": "Hake, R. R. (1998/1999). Interactive-engagement vs traditional methods; Analyzing change/gain scores.",
}

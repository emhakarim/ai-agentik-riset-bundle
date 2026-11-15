"""Analisis power dan ukuran sampel (a priori & post hoc) + ukuran sampel survei.

Isi `power` untuk mencari n (a priori), atau isi `n` untuk mencari power (sensitivitas/post hoc).
Hasil uji-t dan ANOVA memakai distribusi noncentral (sama seperti G*Power).
"""
from __future__ import annotations

import math

from scipy import optimize, stats

from . import fmt
from .data import DataError

_ALT = {"two-sided": "two-sided", "greater": "larger", "less": "smaller"}


def _one_of(power, n, n_name="n"):
    if (power is None) == (n is None):
        raise DataError(f"Isi tepat salah satu: 'power' (untuk mencari {n_name}) atau '{n_name}' (untuk mencari power).")
    if power is not None and not 0 < power < 1:
        raise DataError("power harus di antara 0 dan 1 (mis. 0.80).")


def _check_alpha(alpha):
    if not 0 < alpha < 0.5:
        raise DataError("alpha harus di antara 0 dan 0.5 (mis. 0.05).")


def power_ttest(d: float, design: str = "independent", alpha: float = 0.05, power: float | None = None,
                n: int | None = None, ratio: float = 1.0, alternative: str = "two-sided") -> dict:
    """design: 'independent' (n = per grup pertama, grup kedua = n·ratio), 'paired', atau 'one_sample' (n = jumlah subjek/pasangan)."""
    from statsmodels.stats.power import TTestIndPower, TTestPower

    _one_of(power, n)
    _check_alpha(alpha)
    if alternative not in _ALT:
        raise DataError(f"alternative harus salah satu dari {list(_ALT)}")
    if d == 0:
        raise DataError("Ukuran efek d tidak boleh 0.")
    if design not in ("independent", "paired", "one_sample"):
        raise DataError("design harus 'independent', 'paired', atau 'one_sample'.")
    alt = _ALT[alternative]
    eff = abs(d) if alternative == "two-sided" else d
    notes = []
    if design == "independent":
        an = TTestIndPower()
        if power is not None:
            n1 = an.solve_power(effect_size=eff, alpha=alpha, power=power, ratio=ratio, alternative=alt)
            n1c = math.ceil(n1 - 1e-9)
            n2c = math.ceil(n1c * ratio - 1e-9)
            achieved = an.power(eff, n1c, alpha, ratio=n2c / n1c, alternative=alt)
            res = {"n_group1": n1c, "n_group2": n2c, "n_total": n1c + n2c, "n_exact": n1, "achieved_power": achieved}
            apa = (f"Untuk mendeteksi d = {fmt.num(d)} dengan power {fmt.nolead(power)} dan α = {alpha} ({alternative}), "
                   f"dibutuhkan n = {n1c} + {n2c} = {n1c + n2c} (uji-t independen; power tercapai {fmt.nolead(achieved, 3)}).")
        else:
            pw = an.power(eff, n, alpha, ratio=ratio, alternative=alt)
            res = {"n_group1": n, "n_group2": math.ceil(n * ratio), "power": pw}
            apa = f"Dengan n = {n} per grup, d = {fmt.num(d)}, α = {alpha}: power = {fmt.nolead(pw, 3)}."
    else:
        an = TTestPower()
        if power is not None:
            nn = an.solve_power(effect_size=eff, alpha=alpha, power=power, alternative=alt)
            nc = math.ceil(nn - 1e-9)
            achieved = an.power(eff, nc, alpha, alternative=alt)
            res = {"n": nc, "n_exact": nn, "achieved_power": achieved}
            unit = "pasangan" if design == "paired" else "subjek"
            apa = (f"Untuk mendeteksi d{'_z' if design == 'paired' else ''} = {fmt.num(d)} dengan power {fmt.nolead(power)} "
                   f"dan α = {alpha} ({alternative}), dibutuhkan {nc} {unit} (power tercapai {fmt.nolead(achieved, 3)}).")
        else:
            pw = an.power(eff, n, alpha, alternative=alt)
            res = {"n": n, "power": pw}
            apa = f"Dengan n = {n}, d = {fmt.num(d)}, α = {alpha}: power = {fmt.nolead(pw, 3)}."
        if design == "paired":
            notes.append("Untuk desain berpasangan, d yang dipakai adalah d_z (rerata selisih / SD selisih), "
                         "bukan d antar-grup. d_z = d / √(2(1 − r)) bila korelasi pre-post r diketahui.")
    notes.append("Patokan Cohen (1988): d = 0.2 kecil, 0.5 sedang, 0.8 besar. Sebaiknya d diambil dari penelitian "
                 "sejenis atau meta-analisis, bukan sekadar patokan.")
    if n is not None:
        notes.append("Power post hoc dengan memakai d dari data sendiri (observed power) tidak informatif; "
                     "pakai untuk analisis sensitivitas dengan d yang ditetapkan sebelumnya.")
    return {"result": {"design": design, "d": d, "alpha": alpha, "alternative": alternative, **res},
            "apa": [apa], "notes": notes}


def power_anova(k: int, f: float | None = None, eta_squared: float | None = None, alpha: float = 0.05,
                power: float | None = None, n_total: int | None = None) -> dict:
    """ANOVA satu arah antar-subjek dengan k grup sama besar. Ukuran efek: Cohen's f atau η²."""
    from statsmodels.stats.power import FTestAnovaPower

    _one_of(power, n_total, "n_total")
    _check_alpha(alpha)
    if k < 2:
        raise DataError("k (jumlah grup) minimal 2.")
    if (f is None) == (eta_squared is None):
        raise DataError("Isi tepat salah satu: f (Cohen) atau eta_squared.")
    if eta_squared is not None:
        if not 0 < eta_squared < 1:
            raise DataError("eta_squared harus di antara 0 dan 1.")
        f = math.sqrt(eta_squared / (1 - eta_squared))
    an = FTestAnovaPower()
    if power is not None:
        nt = an.solve_power(effect_size=f, alpha=alpha, power=power, k_groups=k)
        per = math.ceil(nt / k - 1e-9)
        achieved = an.power(f, per * k, alpha, k_groups=k)
        res = {"n_per_group": per, "n_total": per * k, "n_total_exact": nt, "achieved_power": achieved}
        apa = (f"Untuk mendeteksi f = {fmt.num(f)} pada {k} grup dengan power {fmt.nolead(power)} dan α = {alpha}, "
               f"dibutuhkan {per} per grup (N = {per * k}; power tercapai {fmt.nolead(achieved, 3)}).")
    else:
        pw = an.power(f, n_total, alpha, k_groups=k)
        res = {"n_total": n_total, "power": pw}
        apa = f"Dengan N = {n_total} pada {k} grup, f = {fmt.num(f)}, α = {alpha}: power = {fmt.nolead(pw, 3)}."
    return {"result": {"k": k, "f": f, "alpha": alpha, **res}, "apa": [apa],
            "notes": ["Patokan Cohen (1988): f = 0.10 kecil, 0.25 sedang, 0.40 besar. f = √(η² / (1 − η²))."]}


def _corr_power(r: float, n: int, alpha: float, alternative: str) -> float:
    z = math.atanh(abs(r)) * math.sqrt(n - 3)
    if alternative == "two-sided":
        c = stats.norm.ppf(1 - alpha / 2)
        return float(stats.norm.sf(c - z) + stats.norm.cdf(-c - z))
    c = stats.norm.ppf(1 - alpha)
    return float(stats.norm.sf(c - z))


def power_correlation(r: float, alpha: float = 0.05, power: float | None = None, n: int | None = None,
                      alternative: str = "two-sided") -> dict:
    """Uji korelasi Pearson H0: ρ = 0, aproksimasi Fisher z (sama dengan tabel Cohen, 1988)."""
    _one_of(power, n)
    _check_alpha(alpha)
    if not 0 < abs(r) < 1:
        raise DataError("r harus di antara −1 dan 1, bukan 0.")
    if alternative not in _ALT:
        raise DataError(f"alternative harus salah satu dari {list(_ALT)}")
    if power is not None:
        nn = optimize.brentq(lambda x: _corr_power(r, x, alpha, alternative) - power, 4, 1e7)
        nc = math.ceil(nn - 1e-9)
        res = {"n": nc, "n_exact": nn, "achieved_power": _corr_power(r, nc, alpha, alternative)}
        apa = (f"Untuk mendeteksi r = {fmt.nolead(r)} dengan power {fmt.nolead(power)} dan α = {alpha} ({alternative}), "
               f"dibutuhkan n = {nc}.")
    else:
        if n < 5:
            raise DataError("n minimal 5.")
        pw = _corr_power(r, n, alpha, alternative)
        res = {"n": n, "power": pw}
        apa = f"Dengan n = {n}, r = {fmt.nolead(r)}, α = {alpha}: power = {fmt.nolead(pw, 3)}."
    return {"result": {"r": r, "alpha": alpha, "alternative": alternative, **res}, "apa": [apa],
            "notes": ["Aproksimasi Fisher z; G*Power (metode eksak) bisa memberi n lebih kecil 1–2.",
                      "Patokan Cohen (1988): r = .10 kecil, .30 sedang, .50 besar."]}


def sample_size_survey(population: int | None = None, margin: float = 0.05, conf_level: float = 0.95,
                       proportion: float = 0.5, method: str = "cochran") -> dict:
    """Ukuran sampel survei untuk menaksir proporsi. method: 'cochran' (+ koreksi populasi terhingga) atau 'slovin'."""
    if not 0 < margin < 0.5:
        raise DataError("margin (batas galat) harus di antara 0 dan 0.5, mis. 0.05 untuk ±5%.")
    if population is not None and population < 1:
        raise DataError("population harus bilangan positif.")
    notes = []
    if method == "cochran":
        z = stats.norm.ppf(0.5 + conf_level / 2)
        n0 = z ** 2 * proportion * (1 - proportion) / margin ** 2
        n_exact = n0 / (1 + (n0 - 1) / population) if population else n0
        nc = math.ceil(n_exact - 1e-9)
        apa = (f"Dengan rumus Cochran (tingkat kepercayaan {int(conf_level * 100)}%, margin ±{fmt.num(margin * 100, 1)}%, "
               f"p = {proportion}{', N = ' + str(population) if population else ''}), dibutuhkan n = {nc} responden.")
        notes.append("Dengan p = .5 dan koreksi populasi terhingga, hasil sama dengan tabel Krejcie & Morgan (1970).")
        res = {"n": nc, "n_exact": n_exact, "n0_infinite": n0}
    elif method == "slovin":
        if not population:
            raise DataError("Rumus Slovin membutuhkan population (N).")
        n_exact = population / (1 + population * margin ** 2)
        nc = math.ceil(n_exact - 1e-9)
        apa = f"Dengan rumus Slovin (N = {population}, e = {margin}), dibutuhkan n = {nc} responden."
        notes.append("PERINGATAN: rumus Slovin tidak memuat tingkat kepercayaan maupun variabilitas populasi dan "
                     "banyak dikritik dalam literatur metodologi. Bila memungkinkan, pakai Cochran atau analisis power.")
        res = {"n": nc, "n_exact": n_exact}
    else:
        raise DataError("method harus 'cochran' atau 'slovin'.")
    notes.append("Ukuran sampel survei menjamin ketepatan taksiran proporsi, bukan power uji hipotesis. "
                 "Tambahkan cadangan untuk responden yang tidak mengembalikan angket.")
    return {"result": {"method": method, "population": population, "margin": margin, "conf_level": conf_level,
                       "proportion": proportion, **res}, "apa": [apa], "notes": notes}

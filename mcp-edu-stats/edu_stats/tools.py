"""Registri alat edu-stats: satu pintu untuk server MCP dan CLI.

Setiap pemanggilan: baca data -> hitung -> bersihkan ke JSON -> catat audit -> lampirkan `audit`.
Kesalahan data dikembalikan sebagai {"error": ...} (bukan exception) agar AI bisa membacanya.
"""
from __future__ import annotations

import functools
import inspect
from pathlib import Path

from . import audit, compare, describe, fmt, instrument, power, relate
from .data import DataError, load

# alat tanpa file data (perencanaan sampel)
_PLAIN_TOOLS = {
    "power_ttest": power.power_ttest,
    "power_anova": power.power_anova,
    "power_correlation": power.power_correlation,
    "sample_size_survey": power.sample_size_survey,
}

# alat yang menerima Dataset sebagai argumen pertama (diganti parameter `file` + `sheet`)
_DATA_TOOLS = {
    "inspect_data": describe.inspect_data,
    "descriptives": describe.descriptives,
    "normality": describe.normality,
    "homogeneity": describe.homogeneity,
    "ttest_independent": compare.ttest_independent,
    "ttest_paired": compare.ttest_paired,
    "ttest_one_sample": compare.ttest_one_sample,
    "anova_oneway": compare.anova_oneway,
    "anova_factorial": compare.anova_factorial,
    "anova_rm": compare.anova_rm,
    "ancova": compare.ancova,
    "mann_whitney": compare.mann_whitney,
    "wilcoxon": compare.wilcoxon,
    "kruskal_wallis": compare.kruskal_wallis,
    "friedman": compare.friedman,
    "correlation": relate.correlation,
    "regression": relate.regression,
    "chi_square": relate.chi_square,
    "prepare_scale": instrument.prepare_scale,
    "reliability": instrument.reliability,
    "n_gain": instrument.n_gain,
    "aiken_v": instrument.aiken_v,
    "cvr_lawshe": instrument.cvr_lawshe,
    "item_analysis_cognitive": instrument.item_analysis_cognitive,
    "inter_rater_kappa": instrument.inter_rater_kappa,
    "icc": instrument.icc,
    "mediation": relate.mediation,
    "moderation": relate.moderation,
}

_DESC = {
    "inspect_data": "Lihat struktur file data: kolom, tipe, jumlah kosong, contoh nilai, value label SPSS. Jalankan PERTAMA.",
    "descriptives": "Statistik deskriptif (n, M, SD, SE, CI, median, skewness/kurtosis + z), opsional per grup.",
    "normality": "Uji normalitas Shapiro-Wilk + Kolmogorov-Smirnov (Lilliefors), opsional per grup.",
    "homogeneity": "Uji homogenitas varians Levene (mean) + Brown-Forsythe (median).",
    "ttest_independent": "Uji-t dua sampel independen (Student & Welch, rekomendasi via Levene), Cohen's d + CI, Hedges' g.",
    "ttest_paired": "Uji-t berpasangan (mis. pretest vs posttest kelompok yang sama), d_z + CI.",
    "ttest_one_sample": "Uji-t satu sampel terhadap nilai acuan mu (mis. KKM).",
    "anova_oneway": "ANOVA satu arah (+ Welch), η², ω², post hoc Tukey / Games-Howell.",
    "anova_factorial": "ANOVA faktorial antar-subjek (2+ faktor, SS tipe III), partial η².",
    "anova_rm": "ANOVA pengukuran berulang (format lebar: satu kolom per waktu), Mauchly, koreksi GG/HF.",
    "ancova": "ANCOVA (mis. posttest dengan kovariat pretest): SS tipe III, homogenitas kemiringan, rerata terkoreksi.",
    "mann_whitney": "Uji Mann-Whitney U (alternatif nonparametrik uji-t independen), r efek.",
    "wilcoxon": "Uji Wilcoxon signed-rank (alternatif nonparametrik uji-t berpasangan), r efek.",
    "kruskal_wallis": "Uji Kruskal-Wallis (alternatif nonparametrik ANOVA satu arah) + post hoc Dunn.",
    "friedman": "Uji Friedman (alternatif nonparametrik RM-ANOVA), Kendall's W.",
    "correlation": "Korelasi Pearson / Spearman / Kendall berpasangan + CI.",
    "regression": "Regresi linear berganda + uji asumsi klasik (normalitas, VIF, Breusch-Pagan, Durbin-Watson, outlier).",
    "chi_square": "Uji chi-square independensi (+ Fisher untuk 2×2), Cramér's V, odds ratio.",
    "prepare_scale": "Balik butir negatif dan hitung skor skala; menulis FILE BARU, file asli tidak diubah.",
    "reliability": "Reliabilitas (Cronbach's α + CI, ω McDonald) dan validitas butir (r item-total vs r tabel, α if deleted).",
    "n_gain": "N-Gain ternormalisasi Hake + kategori dan tafsiran efektivitas, opsional per kelompok.",
    "aiken_v": "Validitas isi Aiken's V per butir dari skor penilaian ahli (baris = butir, kolom = ahli), p eksak & V kritis.",
    "cvr_lawshe": "Content Validity Ratio Lawshe per butir + CVI, batas kritis binomial eksak (Ayre & Scally, 2014).",
    "item_analysis_cognitive": "Analisis butir tes pilihan ganda/benar-salah: tingkat kesukaran, daya beda 27%, r point-biserial, KR-20, analisis pengecoh.",
    "inter_rater_kappa": "Kesepakatan antar-penilai kategorik: Cohen's κ (2 penilai, opsional berbobot) atau Fleiss' κ (≥ 3 penilai).",
    "icc": "Intraclass correlation (6 bentuk Shrout-Fleiss/McGraw-Wong) + F + CI untuk kesepakatan/reliabilitas penilai skor kontinu.",
    "mediation": "Mediasi sederhana X → M → Y: jalur a, b, c, c', efek tak langsung + CI bootstrap (seed tetap) dan uji Sobel.",
    "moderation": "Moderasi X × W terhadap Y: B interaksi, ΔR², simple slopes pada W = M ± 1SD (atau 0/1).",
    "r_table": "Nilai r tabel Product Moment (r kritis dua sisi) untuk n dan α tertentu.",
    "power_ttest": "Ukuran sampel / power uji-t (independen, berpasangan, satu sampel) dari Cohen's d. Isi power ATAU n.",
    "power_anova": "Ukuran sampel / power ANOVA satu arah dari Cohen's f atau η². Isi power ATAU n_total.",
    "power_correlation": "Ukuran sampel / power uji korelasi Pearson dari r. Isi power ATAU n.",
    "sample_size_survey": "Ukuran sampel survei dari ukuran populasi (Cochran / Krejcie-Morgan, atau Slovin).",
    "audit_log": "Tampilkan catatan audit pemanggilan alat terakhir.",
    "replay": "Jalankan ulang analisis dari audit_id dan buktikan hasilnya identik (serta data tidak berubah).",
}


def _error(msg: str, tool: str) -> dict:
    return {"error": msg, "tool": tool}


def run_tool(name: str, params: dict, record: bool = True) -> dict:
    """Jalankan alat berdasarkan nama dengan parameter dict. Selalu mengembalikan dict JSON-aman."""
    params = dict(params or {})
    try:
        if name == "r_table":
            n = int(params["n"])
            a = float(params.get("alpha", 0.05))
            out = {"result": {"n": n, "df": n - 2, "alpha": a, "r_table": instrument.r_table(n, a)},
                   "notes": ["r kritis dua sisi; butir valid bila r hitung ≥ r tabel."]}
            data_sha = None
        elif name in _PLAIN_TOOLS:
            sig = inspect.signature(_PLAIN_TOOLS[name])
            unknown = [k for k in params if k not in sig.parameters]
            if unknown:
                return _error(f"Parameter tidak dikenal: {unknown}. Parameter yang tersedia: {list(sig.parameters)}", name)
            out = _PLAIN_TOOLS[name](**params)
            data_sha = None
        elif name in _DATA_TOOLS:
            if "file" not in params:
                return _error("Parameter 'file' (path file data) wajib diisi.", name)
            file, sheet = params.pop("file"), params.pop("sheet", None)
            ds = load(file, sheet)
            sig = inspect.signature(_DATA_TOOLS[name])
            unknown = [k for k in params if k not in sig.parameters]
            if unknown:
                allowed = [p for p in sig.parameters if p != "ds"]
                return _error(f"Parameter tidak dikenal: {unknown}. Parameter yang tersedia: ['file', 'sheet', *{allowed}]", name)
            out = _DATA_TOOLS[name](ds, **params)
            params = {"file": str(Path(file).expanduser().resolve()), "sheet": sheet, **params}
            data_sha = ds.sha256
        else:
            return _error(f"Alat '{name}' tidak dikenal. Alat tersedia: {list_tools()}", name)
    except (DataError, KeyError, TypeError, ValueError) as e:
        msg = str(e)
        if isinstance(e, KeyError):
            msg = f"Parameter wajib tidak ada: {msg}"
        elif isinstance(e, TypeError) and "required positional argument" in msg:
            msg = f"Parameter wajib belum diisi: {msg.split(':', 1)[-1].strip()}"
        return _error(msg, name)
    out = fmt.clean(out)
    if record:
        entry = audit.record(name, params, data_sha, out)
        out["audit"] = {k: entry[k] for k in ("audit_id", "timestamp", "result_digest", "data_sha256")}
        if "warning" in entry:
            out["audit"]["warning"] = entry["warning"]
    return out


def replay(audit_id: str) -> dict:
    """Ulangi analisis dari log audit dan bandingkan digest hasil serta hash data."""
    entry = audit.find(audit_id)
    if entry is None:
        return _error(f"audit_id '{audit_id}' tidak ditemukan di {audit.audit_dir()}", "replay")
    params = dict(entry["params"])
    out = run_tool(entry["tool"], params, record=False)
    if "error" in out:
        return {"replayed": False, "audit_id": audit_id, "tool": entry["tool"], "error": out["error"]}
    now_digest = audit.digest(out)
    now_sha = None
    if params.get("file"):
        from .data import _sha256
        now_sha = _sha256(Path(params["file"]))
    data_same = entry.get("data_sha256") == now_sha
    same = now_digest == entry["result_digest"]
    if same:
        verdict = "Hasil identik dengan catatan audit."
    elif not data_same:
        verdict = "Hasil BERBEDA karena file data sudah berubah sejak analisis asli."
    else:
        verdict = "Hasil BERBEDA walau data sama — periksa perbedaan versi library di bawah."
    return {"replayed": True, "audit_id": audit_id, "tool": entry["tool"], "identical": same,
            "data_unchanged": data_same, "original_digest": entry["result_digest"], "replay_digest": now_digest,
            "versions_original": entry.get("versions"), "versions_now": audit.versions(), "keputusan": verdict}


def audit_log(last_n: int = 20) -> dict:
    return {"entries": audit.read_log(last_n), "path": str(audit.audit_dir() / "audit.jsonl")}


def list_tools() -> list[str]:
    return [*_DATA_TOOLS, *_PLAIN_TOOLS, "r_table", "audit_log", "replay"]


def describe_tool(name: str) -> str:
    return _DESC.get(name, "")


def _public_wrapper(name: str):
    """Fungsi dengan tanda tangan publik (ds -> file, sheet) untuk didaftarkan ke MCP."""
    fn = _DATA_TOOLS[name]
    sig = inspect.signature(fn)
    params = [inspect.Parameter("file", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation="str")]
    params += [p for p in list(sig.parameters.values())[1:]]
    params.append(inspect.Parameter("sheet", inspect.Parameter.KEYWORD_ONLY, default=None, annotation="str | int | None"))
    params = sorted(params, key=lambda p: (p.kind, p.default is not inspect.Parameter.empty))

    @functools.wraps(fn)
    def wrapper(**kwargs):
        return run_tool(name, kwargs)

    wrapper.__signature__ = inspect.Signature(params, return_annotation="dict")
    wrapper.__annotations__ = {p.name: p.annotation for p in params} | {"return": "dict"}
    wrapper.__name__ = name
    wrapper.__doc__ = f"{_DESC[name]}\n\n{inspect.getdoc(fn) or ''}".strip()
    return wrapper


def _plain_wrapper(name: str, fn):
    @functools.wraps(fn)
    def wrapper(**kwargs):
        return run_tool(name, kwargs)

    wrapper.__signature__ = inspect.signature(fn)
    wrapper.__name__ = name
    wrapper.__doc__ = f"{_DESC[name]}\n\n{inspect.getdoc(fn) or ''}".strip()
    return wrapper


def public_functions() -> dict:
    """{nama: fungsi} siap didaftarkan sebagai alat MCP."""
    out = {n: _public_wrapper(n) for n in _DATA_TOOLS}
    for n, fn in _PLAIN_TOOLS.items():
        out[n] = _plain_wrapper(n, fn)

    def r_table(n: int, alpha: float = 0.05) -> dict:
        return run_tool("r_table", {"n": n, "alpha": alpha})

    def audit_log_tool(last_n: int = 20) -> dict:
        return audit_log(last_n)

    def replay_tool(audit_id: str) -> dict:
        return replay(audit_id)

    r_table.__doc__ = _DESC["r_table"]
    audit_log_tool.__doc__ = _DESC["audit_log"]
    replay_tool.__doc__ = _DESC["replay"]
    out.update({"r_table": r_table, "audit_log": audit_log_tool, "replay": replay_tool})
    return out

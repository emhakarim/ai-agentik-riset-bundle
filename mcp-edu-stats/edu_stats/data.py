"""Pemuatan data, pembersihan tipe, dan pemilihan kolom.

Semua analisis memakai modul ini supaya cara membaca file (CSV Indonesia
dengan ';' dan koma desimal, Excel, SPSS .sav, Stata .dta) selalu konsisten.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


class DataError(ValueError):
    """Kesalahan data yang pesannya aman ditampilkan ke pengguna."""


@dataclass
class Dataset:
    df: pd.DataFrame
    path: str
    sha256: str
    value_labels: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


_CACHE: dict = {}
_DEC_COMMA = re.compile(r"^\s*-?\d+(\.\d{3})*,\d+\s*$")


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text_head(p: Path) -> tuple[str, str]:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(p, encoding=enc) as f:
                return f.read(20000), enc
        except UnicodeDecodeError:
            continue
    raise DataError(f"Tidak bisa membaca encoding file {p.name}")


def _read_csv(p: Path, notes: list) -> pd.DataFrame:
    head, enc = _read_text_head(p)
    first = head.splitlines()[0] if head else ""
    counts = {";": first.count(";"), "\t": first.count("\t"), ",": first.count(",")}
    sep = max(counts, key=counts.get)
    if counts[sep] == 0:
        sep = ","
    # File CSV dari Excel berbahasa Indonesia memakai ';' dan koma desimal.
    decimal = "," if sep == ";" else "."
    df = pd.read_csv(p, sep=sep, decimal=decimal, encoding=enc)
    notes.append(f"CSV dibaca dengan pemisah {sep!r}, desimal {decimal!r}, encoding {enc}.")
    return df


def load(path: str, sheet: str | int | None = None) -> Dataset:
    p = Path(path).expanduser()
    if not p.exists():
        raise DataError(f"File tidak ditemukan: {p}")
    p = p.resolve()
    key = (str(p), p.stat().st_mtime_ns, sheet)
    if key in _CACHE:
        return _CACHE[key]
    ext = p.suffix.lower()
    notes: list = []
    labels: dict = {}
    if ext in (".csv", ".txt", ".tsv"):
        df = _read_csv(p, notes)
    elif ext in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(p, sheet_name=sheet if sheet is not None else 0)
    elif ext in (".sav", ".zsav"):
        import pyreadstat

        df, meta = pyreadstat.read_sav(str(p))
        labels = {k: {str(_fmt_code(a)): b for a, b in v.items()} for k, v in meta.variable_value_labels.items()}
    elif ext == ".dta":
        import pyreadstat

        df, meta = pyreadstat.read_dta(str(p))
        labels = {k: {str(_fmt_code(a)): b for a, b in v.items()} for k, v in meta.variable_value_labels.items()}
    else:
        raise DataError(f"Format {ext} belum didukung. Pakai .csv, .xlsx, .sav, atau .dta.")
    df.columns = [str(c).strip() for c in df.columns]
    if df.columns.duplicated().any():
        dup = df.columns[df.columns.duplicated()].tolist()
        raise DataError(f"Nama kolom ganda: {dup}. Ubah nama kolom agar unik.")
    ds = Dataset(df=df, path=str(p), sha256=_sha256(p), value_labels=labels, notes=notes)
    _CACHE.clear()  # simpan hanya file terakhir agar memori tetap kecil
    _CACHE[key] = ds
    return ds


def _fmt_code(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def check_columns(ds: Dataset, cols: list[str]) -> None:
    missing = [c for c in cols if c not in ds.df.columns]
    if missing:
        raise DataError(
            f"Kolom tidak ada: {missing}. Kolom yang tersedia: {list(ds.df.columns)}"
        )


def to_numeric(s: pd.Series, name: str, notes: list | None = None) -> pd.Series:
    """Ubah kolom ke angka. Gagal keras bila ada teks yang bukan angka."""
    if pd.api.types.is_bool_dtype(s):
        return s.astype(float)
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    raw = s.astype("string").str.strip()
    raw = raw.mask(raw == "", pd.NA)
    fixed = raw.where(~raw.fillna("").str.match(_DEC_COMMA), raw.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    out = pd.to_numeric(fixed, errors="coerce")
    bad = raw.notna() & out.isna()
    if bad.any():
        examples = raw[bad].unique()[:5].tolist()
        raise DataError(
            f"Kolom '{name}' berisi nilai bukan angka, misalnya {examples}. "
            "Perbaiki data atau kodekan dulu ke angka."
        )
    if notes is not None and (fixed != raw).fillna(False).any():
        notes.append(f"Kolom '{name}': koma desimal diubah menjadi titik.")
    return out.astype(float)


def numeric_frame(ds: Dataset, cols: list[str], notes: list) -> tuple[pd.DataFrame, int, int]:
    """Kolom numerik dengan penghapusan listwise. Mengembalikan (df, n_awal, n_dibuang)."""
    check_columns(ds, cols)
    df = pd.DataFrame({c: to_numeric(ds.df[c], c, notes) for c in cols})
    n0 = len(df)
    df = df.dropna()
    return df, n0, n0 - len(df)


def group_series(ds: Dataset, col: str) -> pd.Series:
    """Kolom grup sebagai label teks (memakai value label SPSS bila ada)."""
    check_columns(ds, [col])
    s = ds.df[col]
    labels = ds.value_labels.get(col, {})

    def lab(v):
        if pd.isna(v):
            return np.nan
        code = _fmt_code(v)
        return labels.get(code, code)

    return s.map(lab).astype(object)


def select_groups(g: pd.Series, groups: list[str] | None, need: int | None = None) -> list[str]:
    present = [x for x in pd.unique(g.dropna())]
    if groups:
        groups = [str(x) for x in groups]
        unknown = [x for x in groups if x not in present]
        if unknown:
            raise DataError(f"Grup {unknown} tidak ditemukan. Grup yang ada: {present}")
        chosen = groups
    else:
        try:
            chosen = sorted(present, key=lambda x: float(x))
        except ValueError:
            chosen = sorted(present)
    if need is not None and len(chosen) != need:
        raise DataError(
            f"Analisis ini butuh tepat {need} grup, ditemukan {len(chosen)}: {chosen}. "
            "Pilih grup dengan parameter 'groups'."
        )
    if len(chosen) < 2:
        raise DataError(f"Butuh minimal 2 grup, ditemukan: {chosen}")
    return chosen

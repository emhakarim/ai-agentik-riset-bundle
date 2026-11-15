"""Jejak audit: setiap analisis dicatat (alat, parameter, hash data, versi library)
sehingga bisa diputar ulang dan dibuktikan hasilnya sama."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import platform
import uuid
from pathlib import Path


def audit_dir() -> Path:
    d = Path(os.environ.get("EDU_STATS_AUDIT_DIR", Path.home() / ".edu-stats" / "audit"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def versions() -> dict:
    import numpy, pandas, scipy, statsmodels

    from . import __version__

    v = {"edu_stats": __version__, "python": platform.python_version(), "numpy": numpy.__version__,
         "pandas": pandas.__version__, "scipy": scipy.__version__, "statsmodels": statsmodels.__version__}
    try:
        import pingouin

        v["pingouin"] = pingouin.__version__
    except Exception:  # pragma: no cover
        pass
    return v


def digest(result: dict) -> str:
    body = {k: v for k, v in result.items() if k not in ("audit", "notes")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]


def record(tool: str, params: dict, data_sha: str | None, result: dict) -> dict:
    entry = {
        "audit_id": uuid.uuid4().hex[:12],
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        "tool": tool,
        "params": params,
        "data_sha256": data_sha,
        "result_digest": digest(result),
        "versions": versions(),
    }
    try:
        with open(audit_dir() / "audit.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError as e:  # audit gagal tidak boleh menggagalkan analisis
        entry["warning"] = f"Audit log tidak tertulis: {e}"
    return entry


def read_log(last_n: int = 20) -> list[dict]:
    f = audit_dir() / "audit.jsonl"
    if not f.exists():
        return []
    lines = f.read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in lines[-last_n:]]


def find(audit_id: str) -> dict | None:
    f = audit_dir() / "audit.jsonl"
    if not f.exists():
        return None
    for line in f.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("audit_id") == audit_id:
            return e
    return None

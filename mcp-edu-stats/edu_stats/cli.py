"""CLI edu-stats: jalankan alat statistik dari terminal, dan buktikan ulang hasil.

Contoh:
    edu-stats list
    edu-stats help ttest_independent
    edu-stats run ttest_independent file=data.csv dv=nilai group=kelas groups=Program,Kontrol
    edu-stats run reliability file=angket.csv items=B1,B2,B3
    edu-stats run ancova --params analisis.json
    edu-stats replay 3f2a9c1b7d0e
    edu-stats log 10

(Tanpa perintah `edu-stats` di PATH: `python -m edu_stats.cli ...` dengan Python virtualenv edu-stats.)

Aturan nilai parameter:
- Parameter berupa daftar (columns, items, raters, groups, covariates, predictors, factors, reverse, essential)
  boleh ditulis dipisah koma tanpa tanda kutip: items=B1,B2,B3. Bentuk JSON items='["B1","B2"]' tetap diterima,
  begitu juga [B1,B2] (bentuk yang tersisa bila shell membuang tanda kutip).
- Nilai lain dibaca sebagai JSON bila bisa (angka, true/false, objek), selain itu sebagai teks.
- --params berkas.json membaca parameter dari berkas JSON; key=value di baris perintah menimpanya.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

from . import tools


def _signature(name: str) -> inspect.Signature | None:
    fn = tools.public_functions().get(name)
    return inspect.signature(fn) if fn else None


def _is_list_param(sig: inspect.Signature | None, key: str) -> bool:
    if sig is None or key not in sig.parameters:
        return False
    ann = str(sig.parameters[key].annotation).lower()
    return "list" in ann and "dict" not in ann


def _scalar(v: str):
    try:
        return json.loads(v)
    except json.JSONDecodeError:
        return v


def _parse_value(v: str, as_list: bool = False):
    if as_list:
        s = v.strip()
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        parts = [p.strip().strip("\"'") for p in s.split(",")]
        return [_scalar(p) if p.replace(".", "", 1).lstrip("-").isdigit() else p for p in parts if p != ""]
    return _scalar(v)


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _help_tool(name: str) -> int:
    sig = _signature(name)
    if sig is None:
        print(f"Alat '{name}' tidak dikenal. Lihat: edu-stats list", file=sys.stderr)
        return 2
    print(f"{name}: {tools.describe_tool(name)}\n")
    print("Parameter:")
    example = []
    for p in sig.parameters.values():
        ann = p.annotation if p.annotation is not inspect.Parameter.empty else ""
        req = p.default is inspect.Parameter.empty
        default = "" if req else f" (bawaan: {p.default!r})"
        kind = "daftar, pisahkan dengan koma" if _is_list_param(sig, p.name) else str(ann)
        print(f"  {p.name:16s} {'WAJIB  ' if req else 'opsional'} {kind}{default}")
        if req:
            example.append(f"{p.name}={'A,B' if _is_list_param(sig, p.name) else '...'}")
    print(f"\nContoh: edu-stats run {name} " + " ".join(example))
    return 0


def _run(rest: list[str]) -> int:
    if not rest:
        print("Pakai: run <alat> key=value ... [--params berkas.json]", file=sys.stderr)
        return 2
    name, args = rest[0], rest[1:]
    sig = _signature(name)
    params: dict = {}
    if "--params" in args:
        i = args.index("--params")
        if i + 1 >= len(args):
            print("--params butuh path berkas JSON", file=sys.stderr)
            return 2
        path = Path(args[i + 1]).expanduser()
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Tidak bisa membaca --params {path}: {e}", file=sys.stderr)
            return 2
        if not isinstance(loaded, dict):
            print("--params harus berisi objek JSON {\"nama\": nilai}", file=sys.stderr)
            return 2
        params.update(loaded)
        args = args[:i] + args[i + 2:]
    for kv in args:
        if "=" not in kv:
            print(f"Argumen '{kv}' harus berbentuk key=value", file=sys.stderr)
            return 2
        k, v = kv.split("=", 1)
        params[k] = _parse_value(v, _is_list_param(sig, k))
    out = tools.run_tool(name, params)
    _print(out)
    return 1 if "error" in out else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):  # pragma: no cover
        pass
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "help":
        if not rest:
            print(__doc__)
            return 0
        return _help_tool(rest[0])
    if cmd == "list":
        for n in tools.list_tools():
            print(f"{n:20s} {tools.describe_tool(n)}")
        return 0
    if cmd == "run":
        return _run(rest)
    if cmd == "replay":
        if len(rest) != 1:
            print("Pakai: replay <audit_id>", file=sys.stderr)
            return 2
        out = tools.replay(rest[0])
        _print(out)
        return 0 if out.get("identical") else 1
    if cmd == "log":
        _print(tools.audit_log(int(rest[0]) if rest else 20))
        return 0
    print(f"Perintah '{cmd}' tidak dikenal. Pakai: list | help <alat> | run | replay | log", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

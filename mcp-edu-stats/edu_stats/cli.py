"""CLI edu-stats — cadangan bila MCP tidak tersedia, dan untuk membuktikan ulang hasil.

Contoh:
    python -m edu_stats.cli list
    python -m edu_stats.cli run ttest_independent file=data.csv dv=nilai group=kelas
    python -m edu_stats.cli run reliability file=angket.csv items='["B1","B2","B3"]'
    python -m edu_stats.cli replay 3f2a9c1b7d0e
    python -m edu_stats.cli log 10

Nilai parameter dibaca sebagai JSON bila bisa (angka, list, true/false), selain itu sebagai teks.
"""
from __future__ import annotations

import json
import sys

from . import tools


def _parse_value(v: str):
    try:
        return json.loads(v)
    except json.JSONDecodeError:
        return v


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):  # pragma: no cover
        pass
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "list":
        for n in tools.list_tools():
            print(f"{n:20s} {tools.describe_tool(n)}")
        return 0
    if cmd == "run":
        if not rest:
            print("Pakai: run <alat> key=value ...", file=sys.stderr)
            return 2
        name, params = rest[0], {}
        for kv in rest[1:]:
            if "=" not in kv:
                print(f"Argumen '{kv}' harus berbentuk key=value", file=sys.stderr)
                return 2
            k, v = kv.split("=", 1)
            params[k] = _parse_value(v)
        out = tools.run_tool(name, params)
        _print(out)
        return 1 if "error" in out else 0
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
    print(f"Perintah '{cmd}' tidak dikenal. Pakai: list | run | replay | log", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

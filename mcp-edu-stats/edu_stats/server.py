"""Server MCP edu-stats (transport stdio).

Jalankan:  python -m edu_stats.server
Claude Code:  claude mcp add edu-stats -- <path-python> -m edu_stats.server

Semua logika ada di `tools.py`; file ini hanya mendaftarkan alat. Mendukung dua nama kelas di SDK `mcp`:
`mcp.server.fastmcp.FastMCP` (seri 1.x) dan `mcp.server.mcpserver.MCPServer` (nama baru, bila ada).
STATUS: diuji 2026-11-14 dengan mcp 2.3.0 (`MCPServer`): semua alat terdaftar, skema masukan benar, dan
pemanggilan lewat klien stdio berhasil (tests/test_tools.py::test_mcp_server_registers_all_tools).
"""
from __future__ import annotations

from . import tools

INSTRUCTIONS = (
    "edu-stats: alat statistik deterministik untuk riset pendidikan. Semua angka yang Anda laporkan WAJIB "
    "berasal dari keluaran alat ini; jangan menghitung sendiri. Mulai dengan inspect_data. Kutip kalimat dari "
    "field 'apa' apa adanya, sebutkan asumsi yang dilanggar dari 'assumptions' dan 'notes', dan sertakan "
    "audit_id agar hasil bisa dibuktikan ulang dengan alat replay."
)


def _server_class():
    try:
        from mcp.server.fastmcp import FastMCP

        return FastMCP
    except ImportError:
        pass
    try:
        from mcp.server.mcpserver import MCPServer

        return MCPServer
    except ImportError as e:
        raise SystemExit(
            "Paket 'mcp' belum terpasang. Pasang dengan:  python -m pip install \"edu-stats[server]\"  "
            "atau pakai CLI cadangan:  python -m edu_stats.cli"
        ) from e


def build_server():
    cls = _server_class()
    try:
        server = cls("edu-stats", instructions=INSTRUCTIONS)
    except TypeError:
        server = cls("edu-stats")
    for name, fn in tools.public_functions().items():
        server.add_tool(fn, name=name, description=fn.__doc__)
    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()

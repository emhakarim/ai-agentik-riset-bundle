# educational-resilience-mcp (alat Zetta)

Server MCP kedua dari repo MCP-dan-Skill-AI-Kependidikan, dibuat oleh tim Zetta. Lisensi MIT (lihat `LICENSE` di akar
bundle). Pendamping skill `skills/educational-resilience-analyst/`.

| Alat | Fungsi | Ke internet? |
|---|---|---|
| `run_psychometrics` | Cronbach's α dan statistik butir | Tidak |
| `run_ancova_experiment` | ANCOVA eksperimen pre/post | Tidak |
| `screen_careless_responders` | Deteksi responden tidak serius (straight-lining) | Tidak |
| `run_meta_analysis` | Meta-analisis sederhana | Tidak |
| `manage_slr_review` | Alur kajian pustaka/SLR: impor, dedup, penyaringan | Tidak |
| `generate_prisma_svg` | Diagram alir PRISMA 2020 (SVG), bisa dari JSON `paper-check screen prisma` | Tidak |
| `export_apa7_table` | Tabel APA 7 | Tidak |
| `verify_crossref_doi` | Cek DOI dan metadata ke Crossref | Hanya DOI |
| `search_openalex_works` | Pencarian karya di OpenAlex | Hanya kata kunci |
| `search_eric_works` | Pencarian karya di ERIC | Hanya kata kunci |

## Memasang

Server ini hanya butuh Python 3.10+ dan paket `mcp`. Cara termudah: pakai virtualenv edu-stats yang sudah Anda buat
(sudah berisi `mcp`, dan bila `edu_stats` terpasang, sebagian uji memakai mesin statistik edu-stats).

Claude Code (ganti `<...>` dengan path di komputer Anda):

```
claude mcp add educational-resilience -- <path>/mcp-edu-stats/.venv/Scripts/python.exe <path>/zetta-mcp/server.py
```

Di macOS/Linux, `python` venv ada di `.venv/bin/python`. Untuk Antigravity atau Codex, daftarkan perintah yang sama
sebagai server MCP stdio di berkas konfigurasi masing-masing.

Tanpa venv edu-stats: `python -m venv .venv`, aktifkan, `pip install -r requirements.txt`, lalu daftarkan
`<venv python> server.py`.

## Catatan

- Data diolah di komputer Anda. Alat pencarian hanya mengirim kata kunci; `verify_crossref_doi` hanya mengirim DOI.
- `educational_ai_research_handbook.md` adalah panduan pendamping dari tim Zetta.

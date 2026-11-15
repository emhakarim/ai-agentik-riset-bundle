# Bundle peserta: AI Agentik untuk Riset

Workshop Pelatihan Optimasi Penggunaan AI · PUI Resiliensi Pendidikan, UNY · 15 November 2026 (daring)

Semua isi bundle berlisensi **MIT** (lihat `LICENSE` dan `academic-humanizer/LICENSE`). Data di folder `data/`
dan `latihan/` **sepenuhnya sintetis**, bukan data orang sungguhan.

## Isi

| Folder | Isi |
|---|---|
| `skills/` | 15 skill: 11 skill penulisan paper (berbahasa Inggris, semua bidang), 3 skill pendidikan berbahasa Indonesia (analisis-kuantitatif, pelaporan-hasil, pengembangan-instrumen), dan `educational-resilience-analyst` dari tim Zetta |
| `mcp-edu-stats/` | MCP statistik pendidikan `edu-stats` dengan CLI cadangan dan audit log |
| `zetta-mcp/` | MCP kedua dari tim Zetta (`educational-resilience-mcp`): psikometri, ANCOVA, responden tidak serius, meta-analisis, SLR/PRISMA, tabel APA 7, verifikasi DOI, pencarian OpenAlex & ERIC. Lihat `zetta-mcp/README.md` |
| `paper-tools/` | Perintah `paper-check`: angka, rujukan (Crossref, hanya DOI), klaim, abstrak, PRISMA, surat tanggapan |
| `academic-humanizer/` | Skill penyuntingan bahasa akademik dari pihak ketiga (AIScientists-Dev, MIT), dengan `LICENSE` dan `SOURCE.md` aslinya |
| `data/` | `data_survei_resiliensi_300.csv` (survei sintetis, N = 300) dan `kualitatif/` (12 transkrip sintetis, codebook, pengodean dua koder, satu transkrip untuk latihan anonimisasi) |
| `latihan/` | Bahan latihan workshop: data demo kecil, draf kajian pustaka berisi kesalahan sisipan, dan `refs.bib` |

## Memasang

Ikuti `panduan-instalasi.md`. Ringkasnya:

- **Skill:** salin folder di `skills/` ke `~/.claude/skills/` (Claude Code) atau `<proyek>/.agents/skills/` (Antigravity).
- **edu-stats:** dari folder `mcp-edu-stats`, buat virtualenv lalu `pip install -e ".[dev,server]"`. Daftarkan ke agen
  sebagai server MCP stdio: `<python venv> -m edu_stats.server`. Cadangan tanpa MCP: `python -m edu_stats.cli list`.
- **paper-check:** dari folder `paper-tools`, `pip install -e .`, lalu `paper-check --help`.
- **MCP Zetta (opsional):** daftarkan `<python venv edu-stats> zetta-mcp/server.py` sebagai server MCP stdio; rincian di `zetta-mcp/README.md`.

## academic-research-skills (Imbad0202): pasang sendiri dari sumber resminya

Tidak ikut di bundle karena lisensinya **CC BY-NC 4.0** (non-komersial). Cocok dipakai berdampingan dengan skill di
bundle ini, dipilih per tahap. Cara pasang menurut repo resminya (https://github.com/Imbad0202/academic-research-skills):

- **Claude Code:** jalankan di dalam Claude Code
  ```
  /plugin marketplace add Imbad0202/academic-research-skills
  /plugin install academic-research-skills
  ```
- **claude.ai / Claude Desktop (paket berbayar):** Customize › Plugins › Add › Add marketplace › Add from a repository,
  masukkan repo di atas, lalu pasang `academic-research-skills`.
- **Codex CLI:** pakai repo saudaranya, `Imbad0202/academic-research-skills-codex`.
- Cara lain (skill proyek, skill global, salin repo): lihat `docs/SETUP.md` di repo tersebut.

Sebelum memakai:
1. **Hanya untuk keperluan non-komersial** (riset dan penulisan akademik), dengan atribusi: "Based on Academic
   Research Skills by Cheng-I Wu".
2. **Baca `docs/DATA_FLOWS.md`** di repo itu. Ada fitur opsional yang mengirim data keluar komputer: pemanggilan
   model lain (`ARS_CROSS_MODEL`), pengambilan sumber untuk audit klaim (`ARS_CLAIM_AUDIT`), resolver bibliografi, dan
   cek pembaruan. Untuk naskah yang belum terbit atau data responden, **biarkan `ARS_CROSS_MODEL` kosong** dan jangan
   menyetujui pengiriman naskah ke layanan atau model lain.
3. Gunakan versi tertentu dan audit ulang sebelum memperbarui; skill pihak ketiga dapat berubah tanpa pemberitahuan.
4. Skill ARS dan skill di bundle ini terpisah: jangan menyalin isi ARS ke skill lain.

## Etika

Jangan memasukkan data responden asli atau draf yang belum terbit ke layanan AI berbasis web. Olah data di komputer
sendiri, ambil angka dari keluaran alat, cek setiap rujukan, dan nyatakan penggunaan AI di naskah.

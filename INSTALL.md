# INSTALL.md: petunjuk pemasangan untuk agen AI

Berkas ini ditulis untuk dibaca **agen AI** (Claude Code, Antigravity, Codex) yang diminta pengguna memasang toolkit
ini. Pengguna cukup menempelkan prompt seperti:

> Pasang toolkit workshop dari https://github.com/emhakarim/ai-agentik-riset-bundle. Baca dan ikuti INSTALL.md di
> repo itu langkah demi langkah. Jelaskan setiap perintah sebelum dijalankan dan minta izin saya.

## Aturan untuk agen

1. Jelaskan apa yang akan dilakukan dan **minta izin** sebelum menjalankan perintah, mengunduh, atau mengubah berkas
   konfigurasi. Tampilkan perintahnya apa adanya.
2. Hanya ubah lokasi yang disebut di berkas ini: folder repo, virtualenv di dalamnya, folder skill agen, dan berkas
   konfigurasi MCP agen. Sebelum mengubah berkas konfigurasi yang sudah ada, buat salinan cadangannya.
3. Jangan menimpa skill atau server MCP yang sudah ada dengan nama yang sama tanpa bertanya.
4. Python, Git, dan Pandoc boleh dipasang **hanya setelah pengguna menyetujui secara eksplisit**, dan hanya dari sumber
   resmi (winget, Homebrew, apt, atau python.org). Jangan mengetikkan kata sandi administrator; bila perintah meminta
   `sudo` atau persetujuan admin, minta pengguna yang menjalankannya.
5. Jangan mengirim data pengguna ke mana pun. Pemasangan hanya mengunduh dari GitHub dan PyPI.
6. Jangan memasang academic-research-skills kecuali pengguna memintanya (lihat langkah 8), dan jangan pernah mengisi
   `ARS_CROSS_MODEL`.
7. Bila sebuah langkah gagal, berhenti, tampilkan pesan galatnya, dan tawarkan jalan keluar di bawah. Jangan menebak.

## Langkah 0 · Cek lingkungan

- Sistem operasi (Windows, macOS, Linux) dan agen yang sedang dipakai.
- Python 3.10 atau lebih baru: `python --version` (Windows; bila tidak ada, coba `py -3 --version`) atau
  `python3 --version` (macOS/Linux).
- Git: `git --version` (opsional; tanpa Git, pakai ZIP di langkah 1).
- Pandoc: `pandoc --version` (opsional; hanya untuk skill manuscript-format, konversi ke Word/PDF).

Di bawah, `PY` berarti `python` atau `py -3` (Windows) atau `python3` (macOS/Linux), dan `VENVPY` berarti
`mcp-edu-stats\.venv\Scripts\python.exe` (Windows) atau `mcp-edu-stats/.venv/bin/python` (macOS/Linux), keduanya
relatif ke folder repo. Saat mendaftarkan MCP, selalu pakai **path absolut**.

## Langkah 0b · Pasang yang belum ada (dengan izin pengguna)

Tawarkan dulu, jelaskan apa yang akan dipasang, lalu tunggu persetujuan. Lewati yang sudah ada.

| | Windows (winget) | macOS | Linux (Debian/Ubuntu) |
|---|---|---|---|
| Python 3.12 | `winget install -e --id Python.Python.3.12` | `brew install python@3.12`, atau penginstal dari python.org | `sudo apt install python3 python3-venv python3-pip` (dijalankan pengguna) |
| Git (opsional) | `winget install -e --id Git.Git` | `xcode-select --install` atau `brew install git` | `sudo apt install git` |
| Pandoc (opsional) | `winget install -e --id JohnMacFarlane.Pandoc` | `brew install pandoc` | `sudo apt install pandoc` |

- Bila winget atau Homebrew tidak tersedia, arahkan pengguna ke python.org/downloads (Windows: centang **"Add
  python.exe to PATH"** saat memasang).
- Setelah memasang, terminal lama belum mengenal perintah baru. Buka terminal baru, atau di Windows pakai `py -3.12`.
- Cek lagi `PY --version` sebelum lanjut.

### Pustaka Python yang akan terpasang

Tidak perlu dipasang satu per satu: `pip install` di langkah 2 mengunduh semuanya dari PyPI ke dalam virtualenv.
Total unduhan sekitar 90 MB (42 paket; terbesar scipy 37 MB, numpy 13 MB, pandas 11 MB, statsmodels 10 MB) dan
sekitar 390 MB ruang disk setelah terpasang. Sampaikan ini ke pengguna sebelum langkah 2 dan pastikan ada ruang
kosong minimal 1 GB; bila koneksi pengguna terbatas, sarankan jaringan yang stabil.

| Untuk | Pustaka |
|---|---|
| edu-stats | numpy, pandas, scipy, statsmodels, openpyxl (baca Excel), pyreadstat (baca SPSS .sav/Stata) |
| server MCP (edu-stats dan Zetta) | mcp |
| paper-check | tidak ada (hanya pustaka bawaan Python) |
| opsional, untuk menjalankan tes | pytest, pingouin (`pip install -e "./mcp-edu-stats[dev]"`) |

## Langkah 1 · Ambil berkas

Tanyakan lokasi yang diinginkan pengguna; bawaan: folder home pengguna.

```
git clone https://github.com/emhakarim/ai-agentik-riset-bundle.git
```

Tanpa Git: unduh
`https://github.com/emhakarim/ai-agentik-riset-bundle/releases/download/v2026.11.15/bundle-peserta-ai-agentik-2026-11-15.zip`
lalu ekstrak (isinya berada di folder `bundle-peserta-ai-agentik/`).

## Langkah 2 · Pasang edu-stats dan paper-check (satu virtualenv)

Dari folder repo:

```
PY -m venv mcp-edu-stats/.venv
VENVPY -m pip install --upgrade pip
VENVPY -m pip install -e "./mcp-edu-stats[server]"
VENVPY -m pip install -e ./paper-tools
```

- **Galat SSL/sertifikat** (umum di jaringan kampus/kantor): set `PIP_USE_FEATURE=truststore` lalu ulangi
  (PowerShell: `$env:PIP_USE_FEATURE="truststore"`; cmd: `set PIP_USE_FEATURE=truststore`; macOS/Linux:
  `export PIP_USE_FEATURE=truststore`).
- **Paket `mcp` tetap gagal terunduh:** pasang tanpa server, `VENVPY -m pip install -e ./mcp-edu-stats`, lalu beri
  tahu pengguna bahwa edu-stats tetap bisa dipakai lewat CLI (`VENVPY -m edu_stats.cli ...`) dengan hasil yang sama,
  tetapi belum sebagai server MCP.

Uji:

```
VENVPY -m edu_stats.cli list
VENVPY -m paper_tools.cli --help
```

Cek pustaka yang terpasang: `VENVPY -m pip list`. Perintah uji pertama menampilkan daftar alat statistik; perintah kedua menampilkan subperintah `paper-check` (gate,
claims, numbers, refs, …). Perintah `paper-check` juga tersedia di folder `Scripts` (Windows) atau `bin` venv.

## Langkah 3 · Daftarkan server MCP

Ada dua server, keduanya stdio dan memakai `VENVPY` (path absolut):

| Nama | Perintah |
|---|---|
| `edu-stats` | `VENVPY -m edu_stats.server` |
| `educational-resilience` (alat Zetta, opsional) | `VENVPY <repo>/zetta-mcp/server.py` |

**Claude Code** (bila perintah `claude` ada di PATH):

```
claude mcp add --scope user edu-stats -- "<VENVPY absolut>" -m edu_stats.server
claude mcp add --scope user educational-resilience -- "<VENVPY absolut>" "<repo absolut>/zetta-mcp/server.py"
```

Bila `claude` tidak ada di PATH (mis. hanya aplikasi desktop): cadangkan `~/.claude.json`, lalu tambahkan di dalam
objek `mcpServers` (buat bila belum ada):

```json
"edu-stats": { "type": "stdio", "command": "<VENVPY absolut>", "args": ["-m", "edu_stats.server"] },
"educational-resilience": { "type": "stdio", "command": "<VENVPY absolut>", "args": ["<repo absolut>/zetta-mcp/server.py"] }
```

Di Windows, tulis backslash dalam JSON sebagai `\\`.

**Antigravity:** buka panel agen › menu MCP › *Manage MCP Servers* › *View raw config* (`mcp_config.json`), lalu
tambahkan entri yang sama di dalam `mcpServers` (kunci `command` dan `args`). Bila menu atau lokasinya berbeda di
versi pengguna, tanyakan pengguna atau rujuk dokumentasi Antigravity; jangan menebak lokasi berkas.

**Codex:** cadangkan lalu tambahkan ke `~/.codex/config.toml`:

```toml
[mcp_servers.edu-stats]
command = "<VENVPY absolut>"
args = ["-m", "edu_stats.server"]

[mcp_servers.educational-resilience]
command = "<VENVPY absolut>"
args = ["<repo absolut>/zetta-mcp/server.py"]
```

## Langkah 4 · Pasang skill

Skill adalah folder berisi `SKILL.md`. Salin **setiap folder** di `skills/` (15 skill) dan folder
`academic-humanizer/`:

- **Claude Code:** ke `~/.claude/skills/` (Windows: `C:\Users\<nama>\.claude\skills\`).
- **Antigravity:** ke `<folder kerja/proyek>/.agents/skills/`. Tanyakan folder kerja yang dipakai pengguna.
- **Codex:** bila versi pengguna mendukung skill, ikuti dokumentasi Codex untuk lokasinya; bila tidak, cukup MCP
  (langkah 3).

Jangan menimpa folder skill yang sudah ada tanpa bertanya.

## Langkah 5 · Muat ulang dan uji

1. Minta pengguna memulai ulang sesi agen (server MCP dan skill dimuat saat sesi dibuka).
2. Di sesi baru, uji dengan data contoh repo:
   - "Jalankan descriptives pada `data/data_survei_resiliensi_300.csv` untuk kolom Pre_Test dan Post_Test lewat
     edu-stats." Agen harus memanggil alat MCP `edu-stats`, bukan menghitung sendiri.
   - Bila alat MCP belum muncul, gunakan CLI: `VENVPY -m edu_stats.cli run descriptives
     file=data/data_survei_resiliensi_300.csv columns='["Pre_Test","Post_Test"]'`.

## Langkah 6 · Laporkan ke pengguna

Ringkas: lokasi repo, versi Python, apa yang terpasang, server MCP yang terdaftar (dan di berkas mana), skill yang
disalin (dan ke mana), hasil uji, serta langkah yang gagal atau dilewati.

## Langkah 7 · Bila ada masalah

| Gejala | Coba |
|---|---|
| `python` tidak dikenal | Pakai `python3` atau `py -3`; bila tidak ada, minta pengguna memasang Python 3.10+ dari python.org |
| Galat SSL saat pip | `PIP_USE_FEATURE=truststore` (langkah 2) |
| `Connection broken: InvalidChunkLength` atau unduhan terputus saat pip | Jaringan/proxy memutus unduhan besar (numpy, scipy, pandas). Ulangi dengan `--retries 10 --timeout 60`; bila tetap gagal, minta pengguna pindah jaringan (mis. hotspot ponsel) lalu ulangi. Jangan mencoba melewati proxy atau mematikan verifikasi sertifikat |
| Alat MCP tidak muncul | Periksa path absolut `VENVPY`, lalu mulai ulang sesi agen; sementara pakai CLI |
| Skill tidak terpanggil | Pastikan tiap skill berada di foldernya sendiri dengan `SKILL.md`, lalu mulai ulang sesi |

## Langkah 8 · academic-research-skills (hanya bila pengguna meminta)

Skill pihak ketiga oleh Cheng-I Wu (Imbad0202), lisensi CC BY-NC 4.0 (non-komersial). Pasang dari sumber resminya,
bukan dari repo ini. Claude Code:

```
/plugin marketplace add Imbad0202/academic-research-skills
/plugin install academic-research-skills
```

Sebelumnya minta pengguna membaca `docs/DATA_FLOWS.md` di repo tersebut. Biarkan `ARS_CROSS_MODEL` kosong untuk naskah
yang belum terbit atau data responden.

# Panduan instalasi peserta (kirim H-3)

Workshop AI Agentik untuk Riset. Siapkan laptop (Windows/macOS) dengan langkah di bawah. Butuh ±30 menit dan
koneksi internet. Bila ada kendala, bawa laptop 15 menit sebelum sesi.

**Kuota dan ruang disk:** unduhan sekitar 100–120 MB (pustaka Python sekitar 90 MB, terbesar scipy 37 MB;
ditambah penginstal Python sekitar 25 MB bila belum ada) dan ruang kosong minimal 1 GB (virtualenv sekitar 390 MB).
Pakai jaringan yang stabil; unduhan besar paling sering terputus di jaringan kampus/kantor.

## Cara tercepat

Setelah Python (langkah 1) dan satu agen (langkah 2) terpasang, buka agen lalu tempel prompt ini:

> Pasang toolkit dari https://github.com/emhakarim/ai-agentik-riset-bundle sesuai INSTALL.md, langkah demi langkah.
> Pasang secara GLOBAL untuk semua proyek: skill ke folder skill global agen ini dan perintah edu-stats yang bisa
> dipanggil dari folder mana pun, bukan di folder proyek yang sedang dibuka. Jelaskan tiap perintah dan minta izin saya.

Agen akan mengerjakan langkah 3 dan 4 di bawah untuk Anda, dengan meminta izin di setiap langkah. Langkah
manual di bawah tetap berlaku bila Anda ingin memasang sendiri.

## 1. Python 3.10 atau lebih baru

- Unduh dari python.org. Saat memasang di Windows, **centang “Add python.exe to PATH”**.
- Atau lewat terminal: Windows `winget install -e --id Python.Python.3.12`; macOS `brew install python@3.12`.
- Cek di terminal (buka terminal baru setelah memasang): `python --version` atau `py -3 --version`.
- Pustaka pendukung (numpy, pandas, scipy, statsmodels, openpyxl, pyreadstat, mcp) tidak perlu dipasang manual:
  semuanya ikut terpasang saat toolkit dipasang di langkah 3, baik oleh agen maupun manual.
- Agen juga bisa memasangkan Python untuk Anda bila Anda mengizinkannya (lihat INSTALL.md langkah 0b).

## 2. Satu agen AI (pilih minimal satu)

Perintah dan lokasi berkas bisa berubah antarversi; ikuti dokumentasi resmi bila berbeda.

- **Claude Code** (Anthropic; perlu akun Claude berbayar atau API): pasang aplikasi desktop Claude dan buka tab Code,
  atau pasang versi terminal sesuai petunjuk di dokumentasi resmi Claude Code.
- **Antigravity** (Google): unduh dari situs resmi Antigravity, masuk dengan akun Google.
- **Codex** (OpenAI; perlu akun ChatGPT berbayar atau API): pasang Codex CLI atau ekstensi IDE sesuai dokumentasi resmi.

## 3. Toolkit

- Unduh bundle dari https://github.com/emhakarim/ai-agentik-riset-bundle/releases (berkas ZIP), lalu ekstrak.
- Pasang edu-stats (dari folder `mcp-edu-stats` di bundle):

```
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev,server]"      (Windows)
.venv/bin/python -m pip install -e ".[dev,server]"          (macOS)
```

- Uji: `.venv\Scripts\python -m edu_stats.cli list` harus menampilkan daftar alat.
- Daftarkan ke Claude Code: `claude mcp add edu-stats -- <path>\mcp-edu-stats\.venv\Scripts\python.exe -m edu_stats.server`.
  Bila paket `mcp` gagal terpasang, CLI di atas tetap bisa dipakai dengan hasil yang sama.
- Opsional, MCP Zetta: `claude mcp add educational-resilience -- <path>\mcp-edu-stats\.venv\Scripts\python.exe <path>\zetta-mcp\server.py`.
- paper-check: dari folder `paper-tools`, `pip install -e .`, lalu `paper-check --help`.
- **Galat SSL saat pip** (sering di jaringan kampus/kantor): jalankan dulu
  `$env:PIP_USE_FEATURE="truststore"` (PowerShell) atau `set PIP_USE_FEATURE=truststore` (cmd), lalu ulangi.

## 4. Skill

Salin tiap folder skill dari `skills/` (dan `academic-humanizer/`) di bundle ke folder skill **global** agen Anda,
supaya berlaku di semua proyek:

- Claude Code: `~/.claude/skills/` (Windows: `C:\Users\<nama>\.claude\skills\`)
- Antigravity: `~/.gemini/config/skills/` (Windows: `C:\Users\<nama>\.gemini\config\skills\`)
- Codex: `~/.agents/skills/` (Windows: `C:\Users\<nama>\.agents\skills\`)
- claude.ai / Claude Desktop: unggah ZIP per skill di Customize › Skills; ZIP-nya ada di halaman rilis GitHub
  (`skill-zip-untuk-claude-ai.zip`).

Untuk satu proyek saja: `<folder proyek>/.claude/skills/` (Claude Code) atau `<folder proyek>/.agents/skills/`
(Antigravity, Codex).

Skill pihak ketiga **academic-research-skills** (Imbad0202, CC BY-NC 4.0) tidak ada di bundle; cara pasang resminya ada
di `README.md` bagian academic-research-skills.

## 5. Etika selama workshop

Gunakan **data contoh** yang disediakan. Jangan membawa data responden asli atau draf naskah yang belum terbit untuk
latihan.

# Panduan instalasi peserta (kirim H-3)

Workshop AI Agentik untuk Riset. Siapkan laptop (Windows/macOS) dengan langkah di bawah. Butuh ±30 menit dan
koneksi internet. Bila ada kendala, bawa laptop 15 menit sebelum sesi.

## Cara tercepat

Setelah Python (langkah 1) dan satu agen (langkah 2) terpasang, buka agen lalu tempel prompt ini:

> Pasang toolkit workshop dari https://github.com/emhakarim/ai-agentik-riset-bundle. Baca dan ikuti INSTALL.md di
> repo itu langkah demi langkah. Jelaskan setiap perintah sebelum dijalankan dan minta izin saya.

Agen akan mengerjakan langkah 3 dan 4 di bawah untuk Anda, dengan meminta izin di setiap langkah. Langkah
manual di bawah tetap berlaku bila Anda ingin memasang sendiri.

## 1. Python 3.10 atau lebih baru

- Unduh dari python.org. Saat memasang di Windows, **centang “Add python.exe to PATH”**.
- Cek di terminal: `python --version`

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

Salin folder skill dari `skills/` di bundle ke:

- Claude Code: `~/.claude/skills/` (Windows: `C:\Users\<nama>\.claude\skills\`)
- Antigravity: `<folder proyek>/.agents/skills/`

Skill pihak ketiga **academic-research-skills** (Imbad0202, CC BY-NC 4.0) tidak ada di bundle; cara pasang resminya ada
di `README.md` bagian academic-research-skills.

## 5. Etika selama workshop

Gunakan **data contoh** yang disediakan. Jangan membawa data responden asli atau draf naskah yang belum terbit untuk
latihan.

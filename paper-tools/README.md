# paper-tools (`paper-check`)

Deterministic, local checks for a research manuscript before submission, in any discipline. It is the code behind the
eleven paper skills in `../skills/`: the skills describe the procedure, and `paper-check` enforces the parts a script can
check.

Python ≥ 3.10, no dependencies (pytest only for the tests). Licence: MIT (see `../LICENSE`).

## Install

```bash
cd paper-tools
python -m pip install -e .
```

On a laptop where pip fails on SSL verification, add `--use-feature=truststore` to the install command.

## Commands

| Command | What it checks | Network |
|---|---|---|
| `paper-check gate DRAFT --bib refs.bib --sources results/` | everything below that runs offline, with a PASS / FAIL verdict (exit code 0 / 1) | no (yes with `--crossref`) |
| `paper-check claims DRAFT --out claims.csv` | every cited sentence, with its keys and a claim type (number, method, prior-work, gap, background), for the claim-to-reference audit. Citation styles: pandoc `[@key]`, LaTeX `\cite{}`, `[key2020x]`, numeric `[3]`, APA author-year `(Duflo, 2001)` / `Duflo (2001)` | no |
| `paper-check numbers DRAFT --sources results/` | every number in the text traced to the output files (CSV, JSON, MD, TXT, TeX) | no |
| `paper-check lint DRAFT --bib refs.bib` | placeholders, citations missing from the bibliography, uncited entries, tables and figures referenced but not defined, required statements | no |
| `paper-check refs --bib refs.bib [--draft DRAFT]` | each reference against Crossref: title, authors, year, venue, volume, issue, pages. Duplicate keys and unreadable entries are reported as `bib_issue` (also in `lint` and `gate`), never skipped silently | **DOIs only** |
| `paper-check rebuttal --reviews r.md --letter l.md --draft d.md` | every reviewer point (R1.1, E.1, …) answered; every "Section / Table / Figure" the letter names exists; letter numbers present in the draft | no |
| `paper-check review REPORT` | a simulated-review report has a decision, sections A/B/C, a check mark on every finding, and a request on every C item | no |
| `paper-check abstract DRAFT [--max-words N] [--structured] [--other en.md]` | abstract word limit; structured parts; numbers that are not in the body; numbers that differ between the language versions | no |
| `paper-check screen import / dedupe / compare / final / log / prisma` | systematic-review screening: reading RIS, PubMed .nbib, WoS and CSV exports; de-duplication (DOI, then title + year); two screeners compared (Cohen's kappa, PABAK, conflicts and "maybe" to the adjudicator); final decisions with a seed-study check; Excel log; PRISMA 2020 counts | no |
| `paper-check reads mark KEY… --status full/abstract/none` / `reads check DRAFT` | reading ledger: which cited works were read; flags number, method and gap claims resting on works not read in full (also `gate --reads`) | no |
| `paper-check seed DRAFT --out s.md --key k.json` / `paper-check score REPORT --key k.json` | review-panel calibration: plant known flaws (number, overclaim, swapped citations, missing statement, causal verb), then score which ones a review found | no |
| `paper-check format DRAFT --out x.docx --bib … --csl … --reference-doc template.docx` | conversion with pandoc (must be installed separately) using the journal template and a CSL citation style; `--dry-run` only prints the command | no |

`gate` options:
- `--profile general|education|health|none`: which statements are required (conflict of interest, funding, data
  availability, AI use; plus ethics and author contributions for health/education).
- `--recent-min 0.8 --recent-years 5 --as-of 2026`: journal recency quota. The window is as_of − years … as_of, both
  included; for a 2026 submission that is 2021–2026.
- `--template`: the draft is a template whose `{{NAME}}` markers and tables are filled by a build step.
- `--lang id|en`: output language. `--json out.json`: machine-readable result.

Input formats: Markdown (pandoc `[@key]`, `[key2020x]`, numeric `[1]`) and LaTeX (`\cite{}`, `\citep{}`, …).
Indonesian and English cue words and statement headings are recognised. Decimal commas (`0,085`, `1{,}44`) and
thousands separators are handled; an ambiguous `1,234` is tried both ways.

## Examples

```bash
paper-check gate naskah.md --bib pustaka.bib --sources output/tabel --profile education --recent-min 0.8 --as-of 2026
paper-check claims naskah.md --out klaim.csv
paper-check numbers naskah.md --sources output/tabel
paper-check refs --bib pustaka.bib --draft naskah.md
paper-check rebuttal --reviews review.md --letter tanggapan.md --draft naskah-revisi.md
```

## What it does not do

- It does not judge whether a reference *supports* a sentence. It lists the sentences, and a person or the
  `claim-ref-audit` skill judges them.
- "Traced" means that a source file contains a value that rounds to the number in the text. Point `--sources` at the
  generated tables and outputs only. A large raw-data folder contains so many numbers that coincidental matches become
  likely. An untraced number is not necessarily wrong, but it needs a reason (a design input, a constant, a cited
  value, a formula).
- Sentence splitting and claim types are heuristics. Read the CSV; don't trust the type blindly.

## Privacy

Nothing leaves the computer except DOIs sent to `api.crossref.org`, and only with `refs` or `gate --crossref`. The
User-Agent is generic (`paper-tools/0.1`). Manuscript text, reviews and data are never sent.

## Tests

```bash
python -m pytest -q
```

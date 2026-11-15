---
name: sr-screening
description: |
  Screen studies for a systematic, scoping or rapid review: turn the protocol (PICO/PICOS/SPIDER/PCC, PROSPERO) into
  written eligibility rules with ordered exclusion codes, de-duplicate records, have two independent blinded screeners
  (two separate sub-agents, or a person and a sub-agent) decide at title/abstract and full-text stages, measure
  agreement (Cohen's kappa), send conflicts to an adjudicator, and produce the PRISMA 2020 flow counts (paper-check
  screen). Use for systematic review screening, "penyaringan artikel", PRISMA flow, or inclusion/exclusion decisions.
---

# Screening for a systematic review

Screening decides which studies a review rests on. It must be reproducible: written rules, two independent
decisions, a record of every exclusion reason, and counts for the PRISMA 2020 flow diagram. Talk to the user in their
language, Indonesian by default.

## Hard rules

1. **The rules come before the screening.** Write the eligibility criteria and the exclusion codes in advance, from the
   protocol, and get the author's agreement. Changes made during screening are recorded as protocol amendments, with
   the reason.
2. **Two independent screeners, blinded to each other.** Use two separate sub-agents with no shared context, or a
   person and a sub-agent. Neither sees the other's decisions until both are done. A third party (the adjudicator,
   ideally a person) decides every conflict.
3. **AI screening is assistance, not authority.**
   - Report in the methods how AI screeners were used.
   - Have a person check a sample of the AI's exclusions; at least the full-text exclusions must be checked by a
     person.
   - When unsure, the screener answers **maybe**, which goes to the adjudicator. It never guesses.
4. **Judge only what is there.** Screeners decide from the title and abstract (stage 1) or the full text (stage 2),
   never from assumptions about the study. Do not bypass paywalls; record "not retrieved" instead.
5. **The data stay local.** Records and full texts are not uploaded anywhere new.

## Steps

1. **Protocol to rules.** From the question framework (PICO/PICOS for interventions, PCC for scoping, SPIDER for
   qualitative), write:
   - the inclusion criteria, each testable from a title or abstract where possible;
   - the **ordered exclusion codes**, for example:
     - E1 wrong population;
     - E2 wrong intervention or exposure;
     - E3 wrong comparator;
     - E4 wrong outcome;
     - E5 wrong study design;
     - E6 wrong publication type (editorial, protocol, conference abstract);
     - E7 language or date outside the limits;
     - E8 duplicate report.

     The first code that applies is the one recorded.
   - Ten or more worked examples of include and exclude for calibration.
2. **Search and records.** Export the records from each database (Scopus, WoS, ERIC, PubMed, Garuda, …) and record
   each search string and its date.
   - Read the exports directly into one file:
     `paper-check screen import scopus.ris pubmed.nbib wos.txt garuda.csv --out records.csv`
     The formats it reads are RIS (Scopus, Zotero, EndNote, Mendeley), PubMed MEDLINE `.nbib`, Web of Science plain
     text, and CSV. The file name becomes the source name, and the counts per source feed the PRISMA "identified" box.
   - Remove duplicates: `paper-check screen dedupe records.csv --out unique.csv --dupes duplicates.csv`
   - **Seed studies:** before screening, list three to ten studies that the protocol must include (known key
     papers). They are the check that the rules and the screeners do not lose eligible work.
3. **Pilot.** Both screeners screen the same 30 to 50 records. Compare them with `paper-check screen compare`, which
   reports Cohen's kappa, **PABAK** and raw agreement.
   - Kappa collapses when almost every record is excluded, which is the usual case. Read PABAK alongside it.
   - If kappa and PABAK are below about 0.6, clarify the rules and the examples, then pilot again.
4. **Title/abstract stage.** Each screener writes `id, decision, reason` (include / exclude / maybe, with an E-code
   when excluding).
   - `paper-check screen compare a.csv b.csv --conflicts conflicts.csv --agreed agreed.csv` reports kappa and the
     raw agreement, and lists the conflicts and every "maybe".
   - The adjudicator fills `decision` and `reason` in the conflicts file.
   - `paper-check screen final agreed.csv adjudicated.csv --out ta_final.csv --seeds <seed ids>` writes the final
     decisions and fails if any seed study was excluded. If one was, find out why: a rule, a screener error, or the
     record itself. Fix the cause before going on.
   - `paper-check screen log records.csv agreed.csv conflicts.csv ta_final.csv --out screening_log.xlsx` writes one
     Excel workbook with a sheet per step, for the audit trail and the supplement.
5. **Full-text stage.** Retrieve the full texts of the included records and record those not retrieved. Repeat step 4
   with full-text decisions; the exclusion reasons are mandatory here.
6. **PRISMA counts:**
   `paper-check screen prisma --sources Scopus=412 ERIC=230 --duplicates 120 --title-abstract ta_final.csv
   --full-text ft_final.csv --not-retrieved 3`
   This gives the numbers for each box of the PRISMA 2020 flow diagram, including the full-text exclusions per
   reason.
7. **Report in the methods:**
   - the databases and dates;
   - the full search strings (in a supplement);
   - the de-duplication method;
   - the number of screeners and their independence;
   - how AI was used;
   - kappa and PABAK at each stage;
   - the seed-study check;
   - how conflicts were resolved;
   - the flow diagram.

The next steps of a systematic review (data extraction, risk of bias, synthesis, GRADE) need their own protocol.
`results-to-paper` and `method-crosscheck` apply to the synthesis numbers.

## With the MCP-dan-Skill-AI-Kependidikan tools (optional)

If the edu-stats and Zetta MCP servers from this toolkit are connected, use them for these steps:

- Searches: Zetta's `search_openalex_works` and `search_eric_works` (education), with keywords only.
- Flow diagram: pass the JSON written by `paper-check screen prisma` to Zetta's `generate_prisma_svg` through its
  `prisma_json` parameter. It draws the PRISMA 2020 diagram and checks that the counts add up; the counts
  themselves still come from `paper-check screen`.
- Agreement beyond kappa and PABAK (weighted or more than two screeners): edu-stats `inter_rater_kappa`.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.

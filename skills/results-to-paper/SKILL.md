---
name: results-to-paper
description: |
  Turn analysis or simulation results into paper tables, figures and claims without a hand-typed number, in any
  discipline: numbers only from tool outputs (edu-stats, R/Python/SPSS output, simulation runs, coding software
  exports) with their provenance, reporting per the right standard (APA 7, CONSORT, STROBE, COREQ/SRQR, convergence and
  uncertainty for simulations), every claim in its narrowest true form, and a trace check (paper-check numbers). Use
  when writing or updating the results/methods sections, tables, figures, the abstract, or checking a number in a draft.
---

# From results to the paper

Every number in a manuscript must come from an output that someone else can reproduce: an `edu-stats` call in its
audit log, a script with its input file and hash, a simulation run with its version stamp, or a qualitative coding
export. A number typed by hand can drift from the data without anyone noticing. A script that reads the output
cannot.

Talk to the user in their language, Indonesian by default.

## Hard rules

1. **The AI never computes statistics by itself.**
   - Numbers come from a tool:
     - `edu-stats` (MCP), whose calls are logged in `~/.edu-stats/audit/audit.jsonl` and can be replayed;
     - R or Python scripts;
     - SPSS, JASP, jamovi or NVivo exports;
     - the simulation software.
   - Mental arithmetic, "about", and values remembered from earlier in the chat are not sources.
2. **Each table and figure is produced from its source files.** Prefer a script that writes both the table and a note
   listing every source file with its hash (sha256) and the tool version. If the table must be filled by hand, keep a
   side file mapping each cell to its source.
3. **Use one data version.** Tables built from an older dataset, model or software version must not be mixed with
   newer ones. Record the version in the note.
4. **Raw data and drafts stay where the author keeps them.** Do not upload participant data. Respect consent, ethics
   approval and anonymisation: no names, IDs or quotes that identify a person.
5. **The author approves claim changes.**

## Report the right things for the design

| Design | Report at least | Standard |
|---|---|---|
| Group comparison, experiment, quasi-experiment | n per group, M and SD, the test with its statistic, df and exact p (APA style: *p* = .032, *p* < .001), effect size with 95 % CI, assumption checks and what was done when they failed | APA 7 (JARS-Quant); CONSORT for randomised trials |
| Correlation, regression | r or B, SE, β, CI, R², the model's assumptions (linearity, normality of residuals, homoscedasticity, VIF) | APA 7 |
| Survey, observational, cohort | sampling, response rate, missing data handling, confounders | STROBE (observational health) |
| Instrument development | validity evidence (expert: Aiken's V, CVR; construct: EFA/CFA fit), reliability (α or ω with CI), item analysis | APA 7 / COSMIN (health) |
| Classroom action research, R&D (ADDIE, 4D) | cycle or phase results, criteria for success set in advance, N-Gain with its category | the journal's own guide |
| Qualitative | sampling and saturation, the analysis method (e.g. thematic analysis, Braun & Clarke), the coding process, trustworthiness, reflexivity, quotes with pseudonyms | COREQ (interviews/focus groups), SRQR |
| Simulation, numerical | software and version, mesh/grid or time-step convergence (e.g. Richardson extrapolation with the observed order), stop criterion, uncertainty, comparison with a reference | the field's verification and validation practice |
| Systematic review | flow of records, risk of bias, synthesis method | PRISMA 2020 |

## Writing the claim

- State the **narrowest version the data support**, with its uncertainty, in the abstract as well (reviewers read
  the abstract first). For example, write "d = 0.45, 95 % CI [0.12, 0.78]", not "a large effect"; and "+0.21 % from the
  reference after extrapolation", not "agrees with the reference".
- Name the condition and the comparison: which group, which instrument, which mesh level or which model.
- Significance is not importance: report the effect size and its practical meaning. Report non-significant results
  too.
- If a result depends on the model or method, say so and show both (see `method-crosscheck`).
- Correlation is not causation, and a quasi-experiment without a control group is not proof of an effect. Use the
  verbs the design allows.

## Steps

1. List the sources: the output files, the `edu-stats` audit ids, the scripts and the run folders, each with its
   version.
2. Generate or update the tables and figures from those sources, and write the source note.
3. Compare them with the draft. List every number that changes and why.
4. Update the text, with the author's agreement for claim changes.
5. Run `paper-check numbers DRAFT --sources <the generated tables and outputs>`.
   - Point `--sources` at the generated tables and outputs only. A whole raw-data folder contains so many numbers
     that coincidental matches become likely.
   - Every untraced number needs a reason: a design input, a constant, a value from the literature (cite it), or a
     derived value (give the formula). Otherwise fix it.
6. Run `paper-check gate` before the paper moves on (see `paper-pipeline`).

## With the MCP-dan-Skill-AI-Kependidikan tools (optional)

If the edu-stats and Zetta MCP servers from this toolkit are connected, use them for these steps:

- Statistics: the edu-stats tools (for example `ttest_independent`, `ancova`, `regression`, `reliability`). Each
  result carries an `apa` sentence and an `audit_id`; `replay` proves a number later.
- APA 7 tables: Zetta's `export_apa7_table` accepts edu-stats JSON output.
- Online survey data: screen careless responders with Zetta's `screen_careless_responders` before the analysis,
  and report how many records were removed and why.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.
- If the edu-stats MCP server is not connected, use its command line, which gives the same results and writes
  the same audit log: `python -m edu_stats.cli run <tool> key=value`. If neither works, do not compute the number
  yourself: say which number is missing.

---
name: journal-review-sim
description: |
  Simulate a journal peer review of a draft paper before submission, in any discipline: five independent read-only
  reviewers (editor of the target journal, methodology, field expert, devil's advocate, reader from a neighbouring
  field), every finding checked against the data, outputs, code or official sources, the result sorted into A (fix
  now), B (author decision) and C (needs new data or analysis), an editor's decision letter, and a re-review mode after
  revision. Use for "review my paper", "simulasi review", pre-submission check or readiness for a journal.
---

# Simulated journal review

The aim is to hear the reviewers' objections before the journal does, and to answer each with evidence. A simulated
reviewer can be wrong just like a real one, so **no finding is acted on until it has been checked**. Write the report
and talk to the user in their language, Indonesian by default.

## Hard rules

1. **No manuscript text leaves the machine.** Reviewers read the local file. Web checks use only names, titles or
   DOIs.
2. **Reviewers only read.** They do not edit the draft or any data.
3. **Every finding is checked** before it is accepted. Mark it **[checked: data / output / code / Crossref / official
   source]**. If the reviewer is wrong, mark it **[wrong]** and give the reason; recompute from unrounded values before
   agreeing or disagreeing. Use [dicek ...] / [salah] when the report is in Indonesian.
4. **The report and the draft stay local**, for example `review/review-YYYY-MM-DD.md`.
5. **Author decisions are asked, not assumed.** This covers the title, authorship, funding and conflict-of-interest
   statements, ethics, scope and length.
6. All five reviewers are one model family. Agreement between them is weaker evidence than agreement between
   independent human reviewers. Say so in the report.

## Steps

1. **Target journal.** Read the journal's official author guidelines and scope page. Note:
   - the word limit and structure (e.g. IMRaD);
   - the reference style and any recency rule;
   - whether review is blind;
   - the required statements (conflict of interest, funding, data availability, ethics, AI use);
   - the reporting standard (APA 7, CONSORT, STROBE, PRISMA, COREQ/SRQR);
   - for Indonesian journals: the SINTA level, the template, and whether a bilingual abstract is required.
   These become the editor's checklist.
2. **Five reviewers as separate sub-agents.** Run them in parallel. Each gets the draft path, the journal checklist
   and these hard rules. Tell each that the others exist but not what they found.
   - **Editor of the target journal**: scope fit, format, and reasons for desk rejection (placeholders, missing
     statements, anonymisation, claims in the abstract that the body does not support, wrong reporting standard).
   - **Methodology**: design and sampling, validity and reliability of instruments, assumptions of the tests, effect
     sizes and CIs, missing data, multiple comparisons, convergence and uncertainty for simulations, trustworthiness
     for qualitative work, reproducibility (data and code availability).
   - **Field expert**: correctness within the discipline, missing or outdated literature, whether the novelty is real
     (check current sources), fairness to prior work.
   - **Devil's advocate**: the strongest case for rejection, such as overclaims, cherry-picked results, a simpler
     explanation or confounders.
   - **Reader from a neighbouring field**: can the paper be followed without insider knowledge, are terms defined,
     can a practitioner use the result, can each figure be read on its own?

   Each reviewer returns:
   - a recommendation (accept / minor / major / reject / return before review);
   - strengths;
   - weaknesses;
   - numbered findings, each with its exact location in the draft.
3. **Check every finding** against the data and outputs (`edu-stats` audit log, scripts, run files), Crossref
   (`paper-check refs`) and official pages. Run `paper-check gate` for the mechanical problems.
4. **Sort the accepted findings:**
   - **A, fix in the draft now** (no new data): wrong numbers or definitions, overclaims, missing CIs or effect
     sizes, outdated facts, reference errors, missing statements;
   - **B, author decision**: title, framing, authors and affiliations, length, supplementary material, statements;
   - **C, new data or analysis**: write each as a request, saying what to run or collect, from whom, and which claim
     it settles.
5. **Editor's decision letter.** Write the decision, two or three sentences on why, and the required changes,
   numbered and grouped by reviewer. Base it on checked findings only. It goes at the top of the report and is the
   input for `paper-rebuttal`.
6. **Apply A** only after the author agrees. Back up the draft first, then list each change.
7. **Validate the report** with `paper-check review REPORT`. It checks that the decision and the A/B/C sections are
   present, that every finding is marked, and that every C item is a request.

## Report layout

- Header: the draft reviewed (path and date), the journal, the five reviewers, the rules followed.
- **Combined decision**: a table of reviewer vs recommendation, the strengths all reviewers named, and the main
  weakness they agreed on.
- **Findings**: each with its [checked ...] or [wrong] mark and the evidence.
- **A**, **B** and **C** sections.
- Notes.

## Calibration mode (how good is the panel?)

A simulated panel is only useful if it catches real problems. Measure that with planted flaws:

1. **Plant flaws in a copy** of a finished or published paper:
   `paper-check seed paper.md --out seeded.md --key key.json`
   This plants:
   - a changed number;
   - an overclaim ("suggests" becomes "proves");
   - two swapped citations;
   - a removed required statement;
   - a correlational verb turned causal.
   Keep `key.json` out of the reviewers' reach.
2. Run the normal five-reviewer review on `seeded.md`. The reviewers are not told that flaws were planted.
3. **Score it:** `paper-check score report.md --key key.json`. It counts a flaw as found when a finding names its line
   (±3) or quotes the changed text and uses words for that kind of problem. It gives the recall per flaw type and
   lists the misses.
4. Repeat with three to five papers and different `--seed` values. Note which flaw types the panel misses, then
   strengthen those reviewer briefs (for example, tell the methodology reviewer to recompute every reported
   statistic from the tables).
5. Report the calibration result (recall per flaw type, number of papers) next to any claim about the panel. This
   measures recall on planted flaws only. It says nothing about false alarms or about subtle real-world problems.

**Calibration so far** (one paper: a 609-line Indonesian simulation paper, seed 7, 5 planted flaws, 2026-11-14):
- **The panel together found 5/5.**
- Per reviewer: editor 5/5, methodology 5/5, devil's advocate 5/5, neighbouring-field reader 5/5, field expert 4/5.
  The field expert missed the removed data-availability statement. Statements are therefore the editor's job, and
  the panel needs every seat.
- Lesson for the briefs: telling each reviewer to **recompute stated percentages and ratios from the tables**, and to
  **compare each [n] with entry n of the reference list**, is what made the planted number and the swapped
  citations visible. Keep those two instructions in every brief.
- The same run also found about 15 real, unplanted problems in that draft, all confirmed in the original. Examples:
  an abstract claim the body did not support, a "three decades" range that was 2.4, a value that differed between
  the text and a figure caption, and an unsupported "known to be mesh-sensitive".

## Re-review mode (after a revision)

1. Give each reviewer the earlier report (or the real reviews), the response letter and the revised draft.
2. Each reviewer checks every earlier point and marks it:
   - **resolved**;
   - **partly resolved**: say what is still missing;
   - **not resolved**;
   - **disputed with reason**: is the argument convincing?
3. Each reviewer also looks for **new problems the revision introduced**: numbers changed in one place but not in
   another, unverified new references, new claims.
4. Report as a table (point | status | evidence) followed by a new combined decision.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.
- If the edu-stats MCP server is not connected, use its command line, which gives the same results and writes
  the same audit log: `python -m edu_stats.cli run <tool> key=value`. If neither works, do not compute the number
  yourself: say which number is missing.

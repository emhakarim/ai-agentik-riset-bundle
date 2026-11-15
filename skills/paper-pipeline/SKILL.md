---
name: paper-pipeline
description: |
  Run a research paper (any discipline) from scope to submission and revision as one tracked pipeline: scope and
  journal (deep-research) -> literature (sota-review, sr-screening) -> results (results-to-paper, method-crosscheck,
  edu-stats) -> draft (paper-drafting) -> integrity (paper-check gate, refs, claim-ref-audit) -> clarity -> simulated
  review (journal-review-sim) -> revision -> re-review -> journal package (manuscript-format, statements, AI-use
  disclosure) -> real review (paper-rebuttal). Keeps a local
  state file per paper. Use when starting a paper, asking "what's next", or preparing a submission.
---

# Paper pipeline

This skill puts the other skills in order and keeps track of where each paper stands. The rules of each stage live
in that stage's skill. Talk to the user in their language, Indonesian by default.

## State file

Keep one local state file per paper, for example `review/state-<paper>.md`. It holds:
- the target journal and its rules, with the date they were read;
- the draft path and its backups;
- the stage table: status (todo / doing / done / blocked), date, output file, and what the stage is waiting for;
- the open author decisions;
- the open requests for new data or analyses.

Read the state file first whenever the user asks about the paper, and update it after every stage.

## Stages

| # | Stage | Skill / tool | Done when |
|---|---|---|---|
| 0 | Scope | the author + this skill (`deep-research` for an unfamiliar topic) | journal chosen; guidelines read; the claim stated in two sentences; design and reporting standard named |
| 1 | Literature | `sota-review` (`sr-screening` for a systematic review) | review report; concept matrix; claims checked; references verified; PRISMA counts for a systematic review |
| 2 | Results | `results-to-paper`, `method-crosscheck`, `edu-stats` | every number from a tool output with provenance; differences explained; claims in their narrowest true form |
| 3 | Draft | `paper-drafting` | outline with evidence approved; all sections written; abstract checked (`paper-check abstract`); no gap markers left |
| 4 | Integrity | `paper-check gate DRAFT --bib … --sources … --profile … --reads reads.csv`, `paper-check refs`, `claim-ref-audit` | gate PASS; references match Crossref; no "does not support" left; untraced numbers explained; key claims rest on works read in full |
| 5 | Clarity | language editing (e.g. `academic-humanizer`, optional) | clearer text; numbers, citations and symbols unchanged (diff checked) |
| 6 | Simulated review | `journal-review-sim` | five reviewers; findings checked; A/B/C lists; editor's letter; `paper-check review` passes |
| 7 | Revision | `paper-rebuttal`, steps 2 to 6, applied to the simulated review | A done, B decided, C done or moved to limitations |
| 8 | Re-review | `journal-review-sim`, re-review mode | no essential point left open; stage 4 repeated on the changed text |
| 9 | Journal package | `manuscript-format` (pandoc + journal template + CSL), document skills (docx, pdf) | the checklist below is complete |
| 10 | Real review | `paper-rebuttal`, then stages 4, 8 and 9 | response letter; revised paper; resubmission |

Go back to an earlier stage whenever needed. New data goes to stage 2; a new important paper in the field goes to
stage 1.

### Stage 9 checklist

- The final language is set. After a translation, run stage 5 again.
- The template is applied.
- The statements are written:
  - conflict of interest;
  - funding;
  - data availability;
  - ethics approval and consent;
  - author contributions;
  - AI-use disclosure.
- The paper is anonymised if review is blind.
- The cover letter is written.
- The graphical abstract or highlights are done, if the journal requires them.

## AI-use disclosure (stage 9)

Most journals now require a statement on AI use. Write it from facts, not from a template:

1. Read the journal's current AI policy on its official page and note the date. Also check the publisher's policy
   (COPE, Elsevier, Springer Nature and Taylor & Francis each have one).
2. List what AI tools actually did on this paper, for example:
   - literature search and reference checks;
   - scripts that generate tables from the analysis outputs;
   - language editing;
   - the simulated review.
   State what they did **not** do: generate data, compute statistics outside the validated tools, or write results
   that were not checked.
3. State that the authors checked all output and take full responsibility. An AI is never listed as an author.
4. Use the journal's wording and its required place for the statement (methods, acknowledgements or a separate
   section). The author approves the final text.

## Rules for every stage

- Drafts, reviews, reports and the state file stay local unless the author decides otherwise.
- No manuscript text goes to web services; only DOIs, titles and keywords are sent.
- Numbers come only from tools (`edu-stats`, scripts, the simulator), never from the AI's own arithmetic.
- Heavy jobs run one at a time, with a time estimate given first.
- Authorship, funding, ethics, the title and conflicts of interest are the author's decisions.

## Reporting to the user

When asked "where is the paper?", answer from the state file:
- the current stage;
- what was done since the last report;
- what is blocked, and on whom;
- the next step;
- the open decisions.

Then offer to continue with the next stage.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.
- If the edu-stats MCP server is not connected, use its command line, which gives the same results and writes
  the same audit log: `python -m edu_stats.cli run <tool> key=value`. If neither works, do not compute the number
  yourself: say which number is missing.

---
name: paper-rebuttal
description: |
  Answer journal reviewers: split the reviews into numbered points, classify each (text fix, analysis, new data,
  disagree with evidence, out of scope), plan the revision with the author, track every change in the manuscript, and
  write a point-by-point response letter that quotes each point and says what was done and where - then check with
  paper-check rebuttal that every point is answered and every "changed in Section X" really is there. Use when reviews
  arrive (real or from journal-review-sim) or for a response letter / surat tanggapan reviewer / revision plan.
---

# Response to reviewers

A good response letter makes the editor's job easy. Every point appears in it, every answer says exactly what changed
and where, and any disagreement rests on evidence rather than tone. Talk to the user in their language (Indonesian by
default). Write the letter in the journal's language.

## Hard rules

1. **Reviews are confidential.** Keep the reviews, the letter and the drafts local. Do not paste them into web tools.
2. **Every number in an answer comes from the outputs** (see `results-to-paper`). New analyses are run by the
   author's tools (`edu-stats`, scripts, the simulator), not computed by the AI.
3. **Make no promises the revision does not keep.** If the letter says "added in Section 3.2", the draft must contain
   it. `paper-check rebuttal` checks this.
4. **The author decides** what to accept, what to dispute, and anything about authorship, funding, ethics or scope.

## Steps

1. **Split the reviews into points.** Give each an id: R1.1, R1.2, … for reviewers and E.1, … for the editor. Quote
   each one exactly in the working file. Keep the ids in the reviews file too, because `paper-check rebuttal` reads
   them there.
2. **Classify each point:**
   - **T, text**: clarify, define, add a limitation or a reference, fix a number;
   - **A, analysis**: a new analysis of data already collected (assumption checks, effect sizes, a sensitivity
     analysis, another model);
   - **N, new data**: more participants, another experiment or simulation, a second coder; give the cost and time;
   - **D, disagree**: the reviewer is mistaken, or the request would make the paper wrong; gather the evidence;
   - **S, out of scope**: fair but beyond this paper; answer it with a limitation or future-work sentence.
   When several reviewers ask for the same thing, link the points and answer once with a cross-reference.
3. **Revision plan** for the author: a table of id | class | proposed action | location | effort. Mark the points the
   editor called essential. Wait for the author's agreement, especially on every D and S.
4. **Revise.** Back up the draft first. Keep a change log of id → location, old wording, new wording. Produce a
   version with the changes highlighted if the journal asks for one.
5. **Write the letter.**
   - Open with thanks to the editor and the reviewers, and summarise the main changes in three to five bullets.
   - For each point, give:
     - **the comment**, quoted with its id;
     - **the response**: agree or not, and why;
     - **the change**: what changed and where (section, table, figure, page or line), with the new text if it is
       short.
   - For a disagreement: thank the reviewer, give the evidence (data, a reference, a derivation), and say what was
     still improved, for example a clearer sentence.
   - Keep it plain and short. For language polishing, use an editor such as `academic-humanizer` (MIT, optional),
     never to change the content.
6. **Check before sending:**
   - `paper-check rebuttal --reviews reviews.md --letter letter.md --draft revised.md` lists:
     - points without an answer;
     - sections, tables and figures that the letter names but the draft does not have;
     - numbers in the letter that are not in the draft.
   - Then run `paper-check gate revised.md ...` again.
   - Run `claim-ref-audit` on the changed sentences.
7. **Optional:** run `journal-review-sim` in re-review mode on the revised draft and the letter.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.
- If the edu-stats MCP server is not connected, use its command line, which gives the same results and writes
  the same audit log: `python -m edu_stats.cli run <tool> key=value`. If neither works, do not compute the number
  yourself: say which number is missing.

---
name: claim-ref-audit
description: |
  Check that every cited sentence in a manuscript is actually supported by the work it cites, not only that the
  reference exists: list cited sentences locally (paper-check claims), read each cited work by DOI, judge support
  (supports / partly / does not support / cannot check), propose a fix for each weak citation, and trace the paper's
  own numbers to its outputs. Use before submission, after a literature update, or when asked whether the references
  really back the claims.
---

# Claim-to-reference audit

`paper-check refs` confirms that each reference is real and that its metadata is right. That does not tell you
whether the reference says what the sentence claims. Reviewers often find exactly this kind of problem:
- a real paper cited for something it does not show;
- a review article cited for a specific number;
- an old paper cited for "recent studies".

Write the report and talk to the user in their language, Indonesian by default.

## Hard rules

1. **No manuscript text leaves the machine.** Fetch the *reference* by DOI, title or arXiv/PubMed id (Crossref,
   OpenAlex, Semantic Scholar, PubMed, arXiv, the publisher's abstract page). Compare it with the sentence
   **locally**. Never put a draft sentence into a query.
2. **Judge only on what was read.** If only the abstract was read, say so. A detail the abstract does not cover is
   **cannot check**, not **supports**. Ask the user for full texts they have access to.
3. **Do not bypass paywalls, CAPTCHAs or bot protection.** List the references that could not be read.
4. **The report stays local**, because it quotes the draft. Edits need the author's agreement.

## Steps

1. **List the claims.** Run `paper-check claims DRAFT --out claims.csv`. For each sentence with a citation, the CSV
   holds:
   - the section and line;
   - the citation keys (pandoc `[@key]`, LaTeX `\cite{}`, `[key2020x]`, numeric `[3]`, or APA author-year such as
     "(Duflo, 2001)" and "Duflo (2001)", read as `Duflo_2001` and matched to the bibliography by first author and
     year);
   - a suggested claim type: `number`, `method`, `prior-work`, `gap` or `background`;
   - flags for citation dumps (4 or more references on one sentence) and for "recent" cues.

   The type is only a hint; correct it where it is wrong.
2. **Read each cited work once, and record how far you read it.** Take the DOI from the bibliography. Keep the
   title, the abstract, and the full text when available, and cache them locally.
   - Record what was actually read in the **reading ledger**:
     `paper-check reads mark KEY ... --status full|abstract|none --file reads.csv [--note "..."]`
   - The authors mark what they themselves read. The AI marks only what it opened in this session, with a note
     saying so.
   - `paper-check reads check DRAFT --file reads.csv` (or `gate --reads reads.csv`) lists the number, method and gap
     claims that rest on works not read in full. Those claims need the full text before submission.
3. **Judge each claim against its references:**
   - **supports**: the work states or clearly shows the claim;
   - **partly**: it supports a weaker or narrower version; write that version;
   - **does not support**: it is about something else or says the opposite;
   - **cannot check**: not readable, or the detail is not in what was read.

   Extra checks by claim type:
   - *number*: the same number, unit, population and condition appear in the work;
   - *prior-work*: the work really did X, rather than only proposing or simulating it;
   - *method*: the cited source is the original method or the validation of the instrument, not a paper that used it;
   - *gap*: citations cannot prove that nothing exists; check gaps with the claim check in `sota-review`;
   - *"recent"*: the work is recent for the field.
4. **Trace the paper's own numbers.** Run `paper-check numbers DRAFT --sources <outputs>` (see `results-to-paper`).
   Every untraced number needs a reason.
5. **Propose a fix for each problem:**
   - narrow the sentence;
   - move the citation to the sentence it does support;
   - replace it with a better reference, taken from Crossref, never typed by hand;
   - or remove the citation.
   Thin out citation dumps.
6. **Report:**
   - a table: id | section | claim (shortened) | key | type | verdict | evidence (a short quote from the source,
     under 15 words, or a page number) | fix;
   - counts per verdict;
   - the references that could not be read.

For a long manuscript, split the claims across sub-agents by section, with these rules in each brief. Then check
every "does not support" and "partly" verdict yourself before reporting it.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.

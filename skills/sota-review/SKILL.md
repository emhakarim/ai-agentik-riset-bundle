---
name: sota-review
description: |
  Build or update the state of the art / literature review for a paper, thesis or proposal in any discipline: a
  six-stage review (question and field, timeframe, final question, reported database + snowballing search,
  concept-matrix analysis, reflexivity), a check of every "first / no prior / belum ada" claim, verified reference
  metadata (Crossref), the journal's recency quota, and edits proposed for the author's approval. Use for "SoTA",
  "kajian pustaka", "tinjauan pustaka", literature review, related work, novelty or research gap.
---

# State-of-the-art review

A state-of-the-art section is an argument, not a list of summaries. It answers three questions: **where the field is
now, how it got there, and what remains open**. It also places this paper within that story (Barry, Merkebu & Varpio
2022). The review must be *checkable*: every novelty claim survives a fresh search, and every reference is real and
correctly cited.

Write the report and talk to the user in the user's language. Use Indonesian unless the user writes in another
language.

## Hard rules

1. **No manuscript text leaves the machine.** Search with your own keywords, titles, author names or DOIs. Never paste
   a sentence of an unpublished draft into a web search or an external tool.
2. **Check every reference's metadata, not only its DOI.** The authors, title, venue, year, volume, issue and pages
   must match Crossref (`paper-check refs`). A real DOI attached to invented authors or volumes is a common AI error.
   Never type metadata from memory. If a reference cannot be verified, label it "unverified" and keep it out of the
   draft.
3. **Facts about tools, products, datasets, policies or guidelines come from official sources** (documentation,
   release notes, the publisher's or agency's own page), each with its URL and the date seen. A blog post is a lead,
   not a source.
4. **Do not bypass CAPTCHAs, paywalls or bot protection.** If a source is blocked, say so and ask the user for the
   file.
5. **The author approves every text edit.** Show a change list or a diff first.
6. **Reports stay local** (for example `review/sota-YYYY-MM-DD.md`). Do not upload or commit unpublished drafts
   unless the author asks.

## Choose the review type first

Say which type the review is (Grant & Booth 2009), because each type promises something different:

- **State-of-the-art review**: covers current work, does not promise completeness, and does not formally grade study
  quality. This is the usual type for the introduction of an empirical paper.
- **Systematic review**: follows a protocol and screens every hit against criteria. Report it with **PRISMA 2020**
  (Page et al. 2021), register it if the field expects it (for example PROSPERO in health), and use two screeners.
- **Scoping, integrative or narrative review**: state the type and its limits.

Whatever the type, run Grant & Booth's SALSA check (Search, AppraisaL, Synthesis, Analysis) to make sure none of the
four steps was skipped.

## The six stages (Barry et al. 2022)

1. **Question and field.** State the paper's novelty claim in one or two sentences. Name the fields it sits in and
   the search streams. Name the **concepts** that will become the columns of the concept matrix: methods,
   populations, settings, outcomes, theories, tools.
2. **Timeframe.** Decide what "now" means and justify it, for example by the journal's recency rule, a turning point
   (a new policy, curriculum, technology or guideline), or the last major review. Keep the seminal older works that
   explain how the field got here. A review with only recent papers, or only old ones, is a known weakness
   (Cakravastia).
3. **Final question.** After the broad overview, rewrite the novelty claim. It often narrows. Record the change and
   the reason.
4. **Reported search.** Run it in two passes and record both, so anyone can repeat them.
   - **Database pass.** Per stream, record:
     - the databases (Crossref, OpenAlex, Semantic Scholar, Scopus/WoS if available, ERIC for education,
       PubMed for health, IEEE Xplore / arXiv for engineering, Garuda / SINTA for Indonesian journals,
       Google Scholar);
     - the query strings;
     - the date of the search;
     - the number of hits screened and read.
   - **Snowballing pass** (Wohlin 2014).
     - Start from a few clearly relevant papers from different groups and years.
     - In each iteration, go **backward** through each paper's references and **forward** through the papers that
       cite it ("cited by" in OpenAlex, Semantic Scholar or Scholar).
     - Screen each candidate on title, then abstract, then full text, against inclusion criteria written down
       beforehand.
     - Record per iteration: the candidates, the papers included, and the reason for each exclusion.
     - Stop when an iteration adds no new included paper.
5. **Analysis: critical, not summary.** Organise by **concept, not by author** (Webster & Watson 2002).
   - Build a **concept matrix**: works as rows (this paper last), concepts as columns, and in each cell what the work
     does on that concept, with the citation.
   - A column that only this paper fills is a *candidate* gap. It must pass the claim check below before it becomes a
     gap in the paper.
   - For each work, appraise: is the method appropriate, are the conclusions justified by the data, is conflicting
     evidence ignored, are the comparisons comparable (Finn 2005, via Cakravastia)? Use the appraisal tool that fits
     the design: CASP or JBI checklists for health and social research, risk of bias for trials, and reliability or
     validity evidence for instruments.
   - **Verify your interpretation**: search on purpose for work that would contradict the novelty claim.
6. **Reflexivity.** State the authors' own position: developers of the tool being compared, insiders in the setting
   studied, funders' interests, the theory preferred. Write competitor and prior-work descriptions fairly, and make
   claims the narrowest true version.

## Checks to run every time

- **Claim check.** Search the draft for "first", "novel", "no prior", "has not been", "only", "unique", "pertama",
  "belum ada", "belum pernah", "satu-satunya" and "tidak ada". Also check every row of any positioning table. For each
  claim, decide whether it is still true, partly true (narrow it) or false (remove it), and give the source.
  `paper-check claims` lists these sentences with type `gap`.
- **Recency quota.** If the journal has a rule (for example ≥ 80 % of references from the last 5 years), measure it
  with `paper-check gate DRAFT --bib refs.bib --recent-min 0.8 --as-of YEAR`. When a needed classic is added, balance
  it with recent work. Prefer replacing weak, off-topic references over padding the list.
- **Relevance.** Every citation must support the sentence it sits in (see `claim-ref-audit`). Avoid citation dumps
  (`paper-check` flags 4 or more citations on one sentence): cite the one or two works that matter, and say why.
- **Seminal and recent.** Check that the field's key older works and the latest one or two years are both
  represented.

## Output

1. **SoTA report** (local file) containing:
   - the review type and the decisions from stages 1 to 3;
   - the search record: queries, plus every snowballing iteration;
   - the concept matrix;
   - the analysis per concept;
   - the claim-check table;
   - the reflexivity note;
   - the proposed reference additions and removals, with the quota count.
2. **Reference changes**: new entries taken from Crossref (never typed by hand), then `paper-check refs` run again.
3. **Proposed text edits** to the introduction, the positioning table and the limitations, applied only after the
   author agrees.

## With the MCP-dan-Skill-AI-Kependidikan tools (optional)

If the edu-stats and Zetta MCP servers from this toolkit are connected, use them for these steps:

- Searches: Zetta's `search_openalex_works` and `search_eric_works` (education), with keywords only.
- Single DOIs: Zetta's `verify_crossref_doi`; the whole bibliography: `paper-check refs`.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.

## Sources

- Barry, E. S., Merkebu, J., & Varpio, L. (2022). State-of-the-art literature review methodology: A six-step approach
  for knowledge synthesis. *Perspectives on Medical Education*, 11(5), 1-8. doi:10.1007/s40037-022-00725-9
- Grant, M. J., & Booth, A. (2009). A typology of reviews. *Health Information & Libraries Journal*, 26(2), 91-108.
  doi:10.1111/j.1471-1842.2009.00848.x
- Webster, J., & Watson, R. T. (2002). Analyzing the past to prepare for the future: Writing a literature review.
  *MIS Quarterly*, 26(2), xiii-xxiii. doi:10.2307/4132319; update: Watson & Webster (2020), *Journal of Decision
  Systems*, 29(3), 129-147, doi:10.1080/12460125.2020.1798591
- Wohlin, C. (2014). Guidelines for snowballing in systematic literature studies. *Proc. EASE 2014*, 1-10.
  doi:10.1145/2601248.2601268
- Page, M. J., et al. (2021). The PRISMA 2020 statement. *BMJ*, 372, n71. doi:10.1136/bmj.n71
- Cakravastia, A. *Literature Review and State of the Art in Research* (lecture slides, FTI ITB), after Hart, Ridley,
  Finn, and Boote & Beile.

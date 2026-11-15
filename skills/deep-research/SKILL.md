---
name: deep-research
description: |
  Research a question in depth with a small team of sub-agents and a checked evidence base: plan sub-questions,
  search several source types in parallel, verify every source (exists, says what is claimed, is current), grade the
  evidence, synthesise with disagreements kept visible, and fact-check the final text claim by claim. Modes: quick
  brief, full report, fact-check of a text, literature scan, Socratic guided dialogue. Use for "riset mendalam", deep
  research, background research for a proposal, fact-checking a claim, or exploring a new topic before a review.
---

# Deep research

The goal is an answer you can defend: every claim tied to a source that was actually read, the strength of the
evidence stated, and disagreement in the literature shown rather than smoothed over. Talk to the user in their
language, Indonesian by default.

## Hard rules

1. **Every claim in the output has a source that was read in this session**: a URL or DOI, plus what it says. If a
   source could not be read, the claim is marked unverified or dropped.
2. **Check scholarly references at Crossref** (`paper-check refs`). Never write a citation from memory.
3. **Prefer primary and official sources.** Use peer-reviewed papers, official statistics (BPS, OECD, UNESCO, WHO),
   laws and regulations, standards, and the documentation of tools. News, blogs and AI summaries are leads, not
   evidence.
4. **No unpublished manuscript text goes into searches**, only the user's own keywords.
5. **Do not bypass paywalls or CAPTCHAs.** Say what could not be accessed.
6. **Quotes stay short** (under 15 words, with attribution). Summaries must not reproduce a source.

## Team (sub-agents, each with these rules in its brief)

- **Planner** (you): split the question into three to seven sub-questions, choose the source types for each, and set
  the stopping rule (enough when new sources stop changing the answer).
- **Searchers**, one per sub-question or source type, run in parallel. They return candidate sources with the URL or
  DOI, the date, the type, and the passage that is relevant.
- **Verifier**: opens each source and confirms that it exists, that it says what the searcher reported, and that it is
  current. It also notes conflicts of interest or retractions (the Crossref and Retraction Watch status).
- **Synthesiser**: builds the answer per sub-question and states where sources agree and where they disagree, and
  why (different populations, methods or years).
- **Fact-checker**: reads the final text sentence by sentence and checks each claim against the evidence table. Any
  sentence without support is removed or marked.

## Evidence table (the core output)

| # | Claim | Source (DOI/URL, date read) | Source type | Evidence strength | Agrees / disagrees with | Note |
|---|---|---|---|---|---|---|

Rate evidence strength by design, for example from strongest to weakest:
1. systematic reviews and meta-analyses;
2. randomised trials;
3. quasi-experimental or cohort studies;
4. cross-sectional studies or surveys;
5. qualitative studies (strong for meaning, not for frequency);
6. expert opinion and grey literature.

Health research can use GRADE. In education, consider the effect sizes and the setting (country, level, subject).

## Modes

- **Quick brief**: one page, three to five key points, each with one or two sources and its evidence strength,
  plus what is not known.
- **Full report**: the question and sub-questions; the method (sources, search strings, dates); the findings per
  sub-question; the disagreements; the gaps; the evidence table; the references.
- **Fact-check of a text**: split the user's text into claims (`paper-check claims` for cited text, or by
  sentence). For each claim, give a verdict (supported / partly / not supported / no evidence found) with its source.
  Only the claims are searched, never the whole text.
- **Literature scan**: map who is publishing on the topic, which venues, which methods and which open questions, as
  input for `sota-review`.
- **Socratic dialogue**: guide the user with questions to sharpen the research question before searching. Ask one
  question at a time and summarise the decisions.

## Hand-over

- For a paper, pass the verified references and the concept list to `sota-review`, and the open questions to the
  author.
- Save the report locally (e.g. `research/<topic>-YYYY-MM-DD.md`) with the evidence table and the search record.

## With the MCP-dan-Skill-AI-Kependidikan tools (optional)

If the edu-stats and Zetta MCP servers from this toolkit are connected, use them for these steps:

- Literature: Zetta's `search_openalex_works`, `search_eric_works` and `verify_crossref_doi`.
- Pooling effect sizes across studies: Zetta's `run_meta_analysis`, reporting only the numbers it returns.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.

---
name: paper-drafting
description: |
  Draft a research paper (any discipline) from verified inputs only: pick the structure for the design and journal,
  build an outline with the evidence for each paragraph, draft section by section in the author's voice, write the
  abstract (structured or not, bilingual ID/EN when required) with identical numbers in both languages and the body
  (paper-check abstract), title, keywords, highlights and cover letter. Use for "tulis draf", outline, abstract,
  "abstrak dua bahasa", introduction/discussion writing, or turning notes and results into a manuscript.
---

# Drafting a paper

A draft is assembled from parts that have already been checked:
- the literature review (`sota-review`);
- the results with their provenance (`results-to-paper`);
- the design and methods the author actually used.

Drafting adds structure and prose. It never adds facts. Talk to the user in their language, Indonesian by default,
and write the draft in the language the journal requires.

## Hard rules

1. **No new facts in the draft.**
   - Every number comes from the result outputs.
   - Every citation comes from the verified bibliography.
   - Every methods detail comes from the author: their protocol, instrument, ethics approval and data.
   - If something is missing, write a visible gap marker such as `[TODO: sample size per class]`. Never write a
     plausible guess. `paper-check gate` fails until every marker is resolved, so nothing is submitted with a gap.
2. **The author's voice and decisions come first.** Ask for the main claim, the intended reader and the target
   journal before drafting. Show the outline before writing prose.
3. **The manuscript stays local.** No draft text goes to web services.
4. **The AI's role is recorded** for the AI-use disclosure (see `paper-pipeline`).

## Steps

1. **Structure.** Choose it from the journal's guidelines and the design:
   - IMRaD for empirical studies;
   - an extended structure for a systematic review (PRISMA 2020 sections);
   - a qualitative structure with reflexivity and context;
   - R&D or classroom action research (ADDIE/4D phases, PTK cycles), as Indonesian journals expect;
   - a short communication;
   - a thesis chapter.
   Note the word limits per section and for the abstract.
2. **Outline with evidence.** For every paragraph, write a one-line point plus its evidence: a result id, a table or
   figure, the citation keys, or the author's note. A paragraph with no evidence is either reasoning (mark it as such)
   or should go.
   - **Introduction**: context, then what is known (from the concept matrix), then the gap (checked), then the aim
     and research questions or hypotheses.
   - **Methods**: design, participants or sample, instruments (with validity and reliability evidence), procedure,
     analysis (the tool and version, e.g. edu-stats or R, and the tests chosen), ethics.
   - **Results**: in the order of the research questions; statistics in APA style; tables and figures referenced
     in the text. No interpretation yet.
   - **Discussion**: the main finding in one sentence, then a comparison with prior work (agreeing and
     disagreeing), the explanation, the implications (practical and theoretical), the limitations, and future work.
   - **Conclusion**: answers to the research questions, with no new results.
3. **Draft section by section.** Write the methods and results first, then the discussion, then the introduction,
   and the abstract last. Keep each claim in its narrowest true form, as in `results-to-paper`.
4. **Abstract.**
   - Follow the journal's form: structured (Background/Aims, Methods, Results, Conclusion) or a single paragraph,
     within the word limit.
   - It must contain only numbers that also appear in the body.
   - For bilingual abstracts (common in SINTA journals), translate meaning, not word by word, and keep every number
     identical. Mind decimal commas in Indonesian (0,45) and points in English (0.45).
   - Check with `paper-check abstract DRAFT --max-words N [--structured] [--other abstract-en.md]`. It reports:
     - an abstract over the limit;
     - missing parts;
     - numbers that are not in the body;
     - numbers that differ between the two language versions.
5. **Title, keywords, highlights.** The title should be specific and contain no claim the results do not support.
   Choose keywords from the field's thesaurus where one exists (ERIC descriptors, MeSH) and avoid repeating title
   words. Write three to five highlights if the journal asks for them.
6. **Cover letter.** Include:
   - the aim and main finding in two sentences;
   - why the paper fits this journal;
   - a statement that it is not under consideration elsewhere;
   - the required declarations;
   - suggested or excluded reviewers if the author wants them.
   No claims beyond the paper.
7. **Hand over** to `paper-pipeline` stage 4: run `paper-check gate`, then `claim-ref-audit`.

## Style

- Use one term per concept throughout, and define abbreviations at first use.
- Prefer short sentences: `paper-check gate` flags sentences over 40 words.
- Use the active voice where the journal allows it, and past tense for what was done and found.
- Avoid hype words: "novel", "groundbreaking", "pertama kali", "sangat signifikan" (significance is not a size).
- Optional language polishing: `academic-humanizer` (MIT, AIScientists-Dev). It must not change any number,
  citation or symbol, so check the diff.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.
- If the edu-stats MCP server is not connected, use its command line, which gives the same results and writes
  the same audit log: `python -m edu_stats.cli run <tool> key=value`. If neither works, do not compute the number
  yourself: say which number is missing.

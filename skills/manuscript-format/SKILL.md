---
name: manuscript-format
description: |
  Put a finished manuscript into the journal's format: Markdown to DOCX (journal Word template), LaTeX or PDF with
  pandoc, the right citation style from a CSL file (APA 7, IEEE, Vancouver, Harvard, Chicago, or the journal's own),
  the journal's section order and statements, figures and tables as the journal wants them, and a final check. Use for
  "format ke template jurnal", convert to Word/LaTeX/PDF, change citation style, or prepare the submission files.
---

# Formatting for the journal

Formatting changes how the paper looks, never what it says. Talk to the user in their language, Indonesian by
default.

## Hard rules

1. **Content is frozen before formatting.** Run `paper-check gate` on the final Markdown first. After conversion,
   check that nothing was lost (step 5).
2. **Use the journal's own files.** Download the template (.docx or .tex) and the citation style from the journal's
   official author page, or take the style from the Zotero Style Repository. Record where each came from. Do not
   invent a template.
3. **Install nothing without asking.** pandoc and a LaTeX engine are separate programs; ask the user before
   installing them (Windows: `winget install JohnMacFarlane.Pandoc`; for PDF also MiKTeX or TeX Live).
4. Files stay local.

## Steps

1. **Read the guidelines** and note:
   - the file type (DOCX, LaTeX, PDF);
   - the template;
   - the reference style;
   - the section order and the required statements;
   - figure formats and resolution (often ≥ 300 dpi, TIFF/EPS/PNG);
   - whether tables must be editable;
   - line numbering, anonymisation, and whether files are separate (title page, main text, figures).
2. **Prepare the inputs:**
   - the manuscript in Markdown with pandoc citations `[@key]`;
   - `refs.bib`, already checked with `paper-check refs`;
   - the CSL file;
   - the journal's Word template saved as a reference document (`--reference-doc`), or its LaTeX template.
3. **Convert:**
   - `paper-check format naskah.md --out naskah.docx --bib refs.bib --csl apa.csl --reference-doc template.docx
     --lang id-ID`
   - Use `--dry-run` to see the pandoc command without running it.
   - For LaTeX, use `--out naskah.tex --template journal.tex`; for PDF, `--out naskah.pdf` (needs xelatex).
   - Built-in styles are not needed. The CSL decides the citation and reference format: APA 7 (author-year),
     IEEE (numeric), Vancouver (health), and so on.
4. **Journal-specific touches** that pandoc does not do:
   - apply the template's styles to the title, authors and affiliations;
   - move figures to the end or to separate files if required;
   - add line numbers;
   - remove author names for blind review, including from the document properties;
   - check that the bilingual abstracts and the keywords are in the right places.
   The `docx` skill can edit a DOCX directly.
5. **Check after conversion:**
   - Every in-text citation resolved: no `???` or `[@key]` left.
   - The reference list complete and in the right style.
   - Table and figure numbers and cross-references correct.
   - Numbers unchanged: run `paper-check numbers` on the Markdown, then spot-check the DOCX or PDF.
   - Word count within the limit.
   - The statements present.
   - The file opens in Word or LibreOffice.
6. **Submission package:**
   - the main file;
   - the title page, if separate;
   - the figures and supplementary files;
   - the cover letter;
   - the declarations, each with its file name as the journal's form asks.
   Add it to the `paper-pipeline` state file.

## When a tool is not available

- If `paper-check` is not installed (for example on claude.ai, or on a computer without the toolkit), say so
  plainly, do by hand the part of the check that can be done by hand, and mark that check "not run with
  paper-check". Never report a tool result that was not run.

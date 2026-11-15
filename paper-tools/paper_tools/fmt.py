"""Convert a Markdown manuscript to DOCX / LaTeX / PDF with pandoc, using a journal template and a citation style.

pandoc is an external program (https://pandoc.org; on Windows `winget install JohnMacFarlane.Pandoc`). This module only
builds and runs the command; it never downloads anything. Citation styles are CSL files (Zotero style repository or
the journal's own); a Word template is a reference .docx (the journal's template saved as a document).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

FORMATS = {".docx": "docx", ".tex": "latex", ".pdf": "pdf", ".odt": "odt", ".html": "html"}


def pandoc_path():
    return shutil.which("pandoc")


def build_command(draft, out, bib=(), csl=None, reference_doc=None, template=None, lang=None, number_sections=False,
                  resource_path=None, extra=()):
    out = Path(out)
    fmt = FORMATS.get(out.suffix.lower())
    if not fmt:
        raise ValueError("unsupported output %s (use %s)" % (out.suffix, ", ".join(FORMATS)))
    cmd = ["pandoc", str(draft), "-o", str(out), "--standalone"]
    if fmt == "pdf":
        cmd += ["--pdf-engine=xelatex"]
    if bib:
        cmd += ["--citeproc"] + ["--bibliography=%s" % b for b in bib]
    if csl:
        cmd += ["--csl=%s" % csl]
    if reference_doc:
        if fmt not in ("docx", "odt"):
            raise ValueError("--reference-doc only applies to .docx / .odt")
        cmd += ["--reference-doc=%s" % reference_doc]
    if template:
        cmd += ["--template=%s" % template]
    if lang:
        cmd += ["-M", "lang=%s" % lang]
    if number_sections:
        cmd += ["--number-sections"]
    if resource_path:
        cmd += ["--resource-path=%s" % resource_path]
    cmd += list(extra)
    return cmd


def run(cmd):
    exe = pandoc_path()
    if not exe:
        raise FileNotFoundError("pandoc is not installed (Windows: winget install JohnMacFarlane.Pandoc)")
    res = subprocess.run([exe] + cmd[1:], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.returncode, res.stdout, res.stderr

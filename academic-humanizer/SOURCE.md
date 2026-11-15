# Source of this skill

- Upstream: https://github.com/AIScientists-Dev/academic-humanizer
- Commit: 94b88b2 (copied 2026-11-12, SKILL.md version 0.3.3), unchanged.
- Licence: MIT (see LICENSE in this folder). It builds on blader/humanizer (MIT).
- Copied files: SKILL.md, LICENSE, examples/before-after.md. Not copied: README images.

Audit before adoption (Aksara, 2026-11-12, board 6ty): prompt-only skill, no scripts, hooks, MCP servers or network
access; `allowed-tools` is Read / Write / Edit / Grep / Glob / AskUserQuestion; no hidden characters or injected
instructions. It keeps every number, result and citation, and is not for evading AI-use disclosure (both papers
carry an AI-use statement).

Project rules on top of the skill:
- Numbers in the drafts come from stamped data through the generator scripts; the skill edits prose only, in the
  `.src.md` sources, never in the generated `docs/draft-*.md`.
- Audit first and show the change log; the owner approves before a rewrite is kept.
- Before updating to a newer upstream version, read the new SKILL.md again (prompt-injection check).

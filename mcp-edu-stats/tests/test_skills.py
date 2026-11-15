"""Skill (SKILL.md) hanya boleh menyebut alat & parameter yang benar-benar ada di edu-stats."""
import inspect
import re
from pathlib import Path

import pytest

from edu_stats import tools

SKILLS = Path(__file__).resolve().parents[2] / "skills"
FILES = sorted(SKILLS.glob("*/SKILL.md"))
CALL = re.compile(r"`([a-z_][a-z0-9_]*)\(([^`]*)\)`")
# alat milik Zetta yang boleh disebut di skill Aksara
ZETTA_TOOLS = {"verify_crossref_doi", "search_openalex_works", "export_apa7_table",
               "run_ancova_experiment", "run_psychometrics"}


def _param_names(args: str) -> list[str]:
    s = re.sub(r'"[^"]*"|\'[^\']*\'|\[[^\]]*\]', "", args)
    names = []
    for part in s.split(","):
        m = re.match(r"\s*([A-Za-z_]\w*)", part)
        if m:
            names.append(m.group(1))
    return names


def _allowed(name: str) -> set[str]:
    fn = tools.public_functions()[name]
    return set(inspect.signature(fn).parameters)


def test_skills_exist():
    names = {p.parent.name for p in FILES}
    assert {"analisis-kuantitatif", "pelaporan-hasil"} <= names


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.parent.name)
def test_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n", text, re.S)
    assert m, "frontmatter harus berisi name dan description"
    assert m.group(1) == path.parent.name
    assert 50 < len(m.group(2)) < 1024


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.parent.name)
def test_tool_calls_match_code(path):
    known = set(tools.list_tools())
    problems = []
    for name, args in CALL.findall(path.read_text(encoding="utf-8")):
        if name in ZETTA_TOOLS:
            continue
        if name not in known:
            problems.append(f"alat tidak dikenal: {name}({args})")
            continue
        bad = [p for p in _param_names(args) if p not in _allowed(name)]
        if bad:
            problems.append(f"{name}: parameter tidak ada {bad}")
    assert not problems, "\n".join(problems)


def test_every_data_tool_is_mentioned():
    text = "\n".join(p.read_text(encoding="utf-8") for p in FILES)
    missing = [t for t in tools.list_tools() if f"`{t}" not in text and t not in ("audit_log",)]
    assert not missing, f"alat belum disebut di skill mana pun: {missing}"

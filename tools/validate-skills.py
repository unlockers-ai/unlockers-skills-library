#!/usr/bin/env python3
"""Check every skill against the Agent Skills format that Claude Code, OpenCode and Copilot load.

A skill that fails here is silently skipped by at least one client, so CI runs it:

    python3 tools/validate-skills.py

- frontmatter is valid YAML (a bare `(default: main)` in a description is not)
- `name` matches the directory and ^[a-z0-9]+(-[a-z0-9]+)*$, at most 64 characters
- `description` is present, at most 1024 characters
- every relative link stays inside the skill or points at a sibling skill, because the
  rest of this repo is not installed with it — link `references/<doc>.md` instead
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)\s]*)?\)")


def frontmatter(text):
    if not text.startswith("---\n"):
        raise ValueError("no YAML frontmatter")
    return yaml.safe_load(text.split("\n---", 1)[0][4:]) or {}


def problems(skill_md):
    skill_dir = skill_md.parent
    text = skill_md.read_text()
    try:
        meta = frontmatter(text)
    except (ValueError, yaml.YAMLError) as error:
        return [f"frontmatter: {error}".splitlines()[0]]

    found = []
    name = meta.get("name", "")
    if name != skill_dir.name:
        found.append(f"name {name!r} does not match directory {skill_dir.name!r}")
    if not NAME.match(name) or len(name) > 64:
        found.append(f"name {name!r} is not lowercase-hyphenated, at most 64 characters")
    if not 1 <= len(meta.get("description") or "") <= 1024:
        found.append("description missing or longer than 1024 characters")

    for path in [skill_md, *skill_dir.glob("references/*.md")]:
        for target in LINK.findall(path.read_text()):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                found.append(f"{path.relative_to(ROOT)}: broken link {target}")
            elif not resolved.is_relative_to(SKILLS):
                found.append(f"{path.relative_to(ROOT)}: {target} is outside skills/ "
                             "and will not be installed")
    return found


def main():
    failed = False
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        for problem in problems(skill_md):
            print(f"{skill_md.parent.name}: {problem}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

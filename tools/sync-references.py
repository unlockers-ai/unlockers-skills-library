#!/usr/bin/env python3
"""Copy the docs each skill links to into that skill's references/ directory.

docs/ is the single source of truth: a rule two skills share is written once. But a skill
is installed on its own (npx skills, a Claude Code plugin, a copy into ~/.claude/skills),
and ../../docs/ is not there when it arrives. So a skill links `references/<doc>.md`, and
this script fills references/ with the docs it links to, plus every doc those link to,
rewriting the links so they resolve from the new location.

    python3 tools/sync-references.py          # rewrite skills/*/references/
    python3 tools/sync-references.py --check  # exit 1 if anything is out of date (CI)

Never edit a file under references/ by hand — edit docs/ and run this.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SKILLS = ROOT / "skills"
REPO_URL = "https://github.com/unlockers-ai/unlockers-skills-library/blob/main"

LINK = re.compile(r"\]\(([^)\s#]+)(#[^)\s]*)?\)")
REFERENCE_LINK = re.compile(r"\]\(references/([a-z0-9-]+\.md)")
DOC_TO_DOC_LINK = re.compile(r"\]\(([a-z0-9-]+\.md)")


def linked_docs(text, pattern):
    return {name for name in pattern.findall(text) if (DOCS / name).is_file()}


def closure(names):
    """Every doc reachable from `names` through doc-to-doc links."""
    seen, todo = set(), list(names)
    while todo:
        name = todo.pop()
        if name not in seen:
            seen.add(name)
            todo.extend(linked_docs((DOCS / name).read_text(), DOC_TO_DOC_LINK) - seen)
    return seen


def relocate(doc_text):
    """Rewrite a doc's links so they resolve from skills/<skill>/references/."""
    def fix(match):
        target, anchor = match.group(1), match.group(2) or ""
        if target.startswith(("http://", "https://", "mailto:")) or "/" not in target:
            return match.group(0)  # external, or a sibling doc that is copied too
        if target.startswith("../skills/"):
            return f"](../../{target[len('../skills/'):]}{anchor})"
        # Anything else (agents/, diagrams/) is not installed with a skill: link the repo.
        resolved = (DOCS / target).resolve().relative_to(ROOT)
        return f"]({REPO_URL}/{resolved.as_posix()}{anchor})"

    return LINK.sub(fix, doc_text)


def expected_files():
    files = {}
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        skill_dir = skill_md.parent
        for name in sorted(closure(linked_docs(skill_md.read_text(), REFERENCE_LINK))):
            header = (f"<!-- Generated from docs/{name} by tools/sync-references.py. "
                      "Edit the source, not this copy. -->\n\n")
            files[skill_dir / "references" / name] = header + relocate((DOCS / name).read_text())
    return files


def main():
    check = "--check" in sys.argv[1:]
    expected = expected_files()
    present = set(SKILLS.glob("*/references/*.md"))
    stale = sorted(present - set(expected))
    changed = sorted(p for p, text in expected.items()
                     if not p.is_file() or p.read_text() != text)

    if check:
        for path in changed + stale:
            print(f"out of date: {path.relative_to(ROOT)}")
        if changed or stale:
            print("Run: python3 tools/sync-references.py")
            return 1
        return 0

    for path in changed:
        path.parent.mkdir(exist_ok=True)
        path.write_text(expected[path])
        print(f"wrote   {path.relative_to(ROOT)}")
    for path in stale:
        path.unlink()
        print(f"removed {path.relative_to(ROOT)}")
        if not any(path.parent.iterdir()):
            path.parent.rmdir()
    return 0


if __name__ == "__main__":
    sys.exit(main())

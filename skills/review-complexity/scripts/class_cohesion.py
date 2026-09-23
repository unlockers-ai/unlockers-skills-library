#!/usr/bin/env python3
"""The method × attribute usage matrix behind `docs/accidental-complexity-guide.md` §10 (God Objects).

For one class it builds `U[m][a] = 1 when method m reads or writes self.a directly`,
where `A` is what `__init__` assigns on `self` and `M` is every other method
(`async def` included — the `cohesion` PyPI package silently skips those), and prints
the readings that say whether the class is one class or several.

How to read the numbers:

* **TCC** — the share of method pairs touching at least one attribute in common.
  Below about 0.3 the class is several classes wearing one name.
* **Sole-touched attributes** — an attribute used by exactly one method is that
  method's dependency, not the class's; it leaves with the method.
* **Empty rows** — a method touching no attribute at all is pure dispatch, or a free
  function that happens to live here.
* **Components** — the connected components of the "shares an attribute" graph. What
  stays connected once the plumbing is set aside is a candidate class, and the
  attributes of that component are its constructor.

The trap, and why `--plumbing` exists: one attribute that everybody touches — a clock,
a store, the single repository — glues every method into one component and hides all
the structure. Connected components alone therefore say nothing until the plumbing is
named and excluded; TCC, which counts pairs rather than reachability, does not have
that blind spot, which is why it is read first.

Usage:
    python3 skills/review-complexity/scripts/class_cohesion.py FILE [CLASS] [--plumbing a,b,c] [--json]

With CLASS omitted every class in the file with at least two methods is analysed.
"""

from __future__ import annotations

import argparse
import ast
import itertools
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class MethodRow:
    """One row of the matrix: a method and the attributes it touches directly."""

    name: str
    touched: frozenset[str]


@dataclass(frozen=True)
class Readings:
    """Everything the matrix has to say, in one comparable object."""

    class_name: str
    attributes: tuple[str, ...]
    methods: tuple[str, ...]
    pairs: int
    sharing_pairs: int
    disjoint_pairs: int
    tcc: float
    sole_touched: tuple[tuple[str, str], ...]
    empty_rows: tuple[str, ...]
    components: tuple[tuple[str, ...], ...]
    components_without_plumbing: tuple[tuple[str, ...], ...]
    touch_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class UsageMatrix:
    """The method × attribute matrix of a single class."""

    class_name: str
    attributes: tuple[str, ...]
    rows: tuple[MethodRow, ...]

    @staticmethod
    def of(class_def: ast.ClassDef) -> UsageMatrix:
        functions = [n for n in class_def.body if isinstance(n, FunctionNode)]
        inits = [f for f in functions if f.name == "__init__"]
        attributes = tuple(_assigned_on_self(inits[0])) if inits else ()
        rows = tuple(
            MethodRow(f.name, frozenset(_self_attributes(f)) & frozenset(attributes))
            for f in functions
            if f.name != "__init__"
        )
        return UsageMatrix(class_def.name, attributes, rows)

    @property
    def methods(self) -> tuple[str, ...]:
        return tuple(row.name for row in self.rows)

    def tcc(self) -> float:
        pairs = list(itertools.combinations(self.rows, 2))
        if not pairs:
            return 0.0
        return sum(1 for a, b in pairs if a.touched & b.touched) / len(pairs)

    def sole_touched(self) -> tuple[tuple[str, str], ...]:
        touchers = {a: [r.name for r in self.rows if a in r.touched] for a in self.attributes}
        return tuple((a, names[0]) for a, names in touchers.items() if len(names) == 1)

    def empty_rows(self) -> tuple[str, ...]:
        return tuple(row.name for row in self.rows if not row.touched)

    def touch_counts(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            (a, sum(1 for r in self.rows if a in r.touched)) for a in self.attributes
        )

    def components(self, excluding: frozenset[str] = frozenset()) -> tuple[tuple[str, ...], ...]:
        """Connected components of the "shares an attribute" graph, plumbing set aside."""
        seeds = [MethodRow(r.name, r.touched - excluding) for r in self.rows]
        found: list[tuple[str, ...]] = []
        while seeds:
            group = [seeds.pop(0)]
            joined = True
            while joined:
                joined = False
                for row in list(seeds):
                    if any(row.touched & member.touched for member in group):
                        group.append(row)
                        seeds.remove(row)
                        joined = True
            found.append(tuple(sorted(r.name for r in group)))
        return tuple(found)

    def readings(self, plumbing: frozenset[str]) -> Readings:
        pairs = list(itertools.combinations(self.rows, 2))
        sharing = sum(1 for a, b in pairs if a.touched & b.touched)
        return Readings(
            class_name=self.class_name,
            attributes=self.attributes,
            methods=self.methods,
            pairs=len(pairs),
            sharing_pairs=sharing,
            disjoint_pairs=len(pairs) - sharing,
            tcc=round(self.tcc(), 2),
            sole_touched=self.sole_touched(),
            empty_rows=self.empty_rows(),
            components=self.components(),
            components_without_plumbing=self.components(excluding=plumbing),
            touch_counts=self.touch_counts(),
        )

    def grid(self) -> str:
        width = max((len(name) for name in self.methods), default=0)
        header = " " * width + "  " + "".join(f"{i + 1:<3}" for i in range(len(self.attributes)))
        body = [
            f"{row.name:<{width}}  "
            + "".join(f"{'●' if a in row.touched else '·':<3}" for a in self.attributes)
            for row in self.rows
        ]
        legend = [f"    {i + 1:>2}  {a}" for i, a in enumerate(self.attributes)]
        return "\n".join([header, *body, "", *legend])


def _assign_targets(node: ast.AST) -> list[ast.expr]:
    if isinstance(node, ast.AnnAssign):
        targets: list[ast.expr] = [node.target]
    elif isinstance(node, ast.Assign):
        targets = list(node.targets)
    else:
        return []
    return [e for t in targets for e in (t.elts if isinstance(t, ast.Tuple) else [t])]


def _is_self_attribute(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def _assigned_on_self(function: FunctionNode) -> list[str]:
    names: list[str] = []
    for node in ast.walk(function):
        for target in _assign_targets(node):
            if _is_self_attribute(target) and target.attr not in names:  # type: ignore[attr-defined]
                names.append(target.attr)  # type: ignore[attr-defined]
    return names


def _self_attributes(function: FunctionNode) -> set[str]:
    return {n.attr for n in ast.walk(function) if _is_self_attribute(n)}  # type: ignore[attr-defined]


def matrices_in(source: str, class_name: str | None) -> list[UsageMatrix]:
    """Every class asked for: the named one, or all those with at least two methods."""
    classes = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ClassDef)]
    if class_name:
        return [UsageMatrix.of(c) for c in classes if c.name == class_name]
    return [m for m in (UsageMatrix.of(c) for c in classes) if len(m.methods) >= 2]


def _block(title: str, items: list[str]) -> list[str]:
    return [title, *(f"    {i}" for i in items or ["(none)"])]


def report(matrix: UsageMatrix, readings: Readings, plumbing: frozenset[str]) -> str:
    members = len(readings.attributes) + len(readings.methods)
    lines = [
        f"{readings.class_name}: |A|={len(readings.attributes)} attributes  "
        f"|M|={len(readings.methods)} methods  members={members}",
        "",
        matrix.grid(),
        "",
        f"TCC = {readings.tcc:.2f}  ({readings.sharing_pairs} of {readings.pairs} method pairs "
        f"share an attribute, {readings.disjoint_pairs} share none)",
        *_block(
            "sole-touched attributes (a dependency of one method, not of the class):",
            [f"{a} → {m}" for a, m in readings.sole_touched],
        ),
        *_block("empty rows (dispatch, or a free function):", list(readings.empty_rows)),
        *_block(
            f"attribute-only components: {len(readings.components)}",
            [", ".join(c) for c in readings.components],
        ),
    ]
    if plumbing:
        lines += _block(
            f"components without plumbing {sorted(plumbing)}: "
            f"{len(readings.components_without_plumbing)}",
            [", ".join(c) for c in readings.components_without_plumbing],
        )
    lines += _block(
        "per-attribute touch count:", [f"{a}: {n}" for a, n in readings.touch_counts]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="method × attribute cohesion matrix")
    parser.add_argument("file")
    parser.add_argument("klass", nargs="?", metavar="CLASS")
    parser.add_argument("--plumbing", default="", help="comma-separated attributes to set aside")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    plumbing = frozenset(p.strip() for p in args.plumbing.split(",") if p.strip())
    matrices = matrices_in(Path(args.file).read_text(encoding="utf-8"), args.klass)
    if not matrices:
        sys.exit(f"class_cohesion: nothing to analyse in {args.file}")
    readings = [m.readings(plumbing) for m in matrices]
    if args.json:
        print(json.dumps([asdict(r) for r in readings], indent=2, ensure_ascii=False))
        return
    print("\n\n".join(report(m, r, plumbing) for m, r in zip(matrices, readings)))


if __name__ == "__main__":
    main()

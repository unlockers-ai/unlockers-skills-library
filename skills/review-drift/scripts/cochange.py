#!/usr/bin/env python3
"""Files that change together — the Tornhill co-change signal, from git alone.

CodeScene computes temporal coupling too, where you have it; without it, a
dozen lines of git log give the same answer. Prints the top pairs as
`count  file_a  file_b` (and JSON with --json) so the drift reviewer can use
them as sibling hints: two files that always move together without importing
each other are joined by something implicit — usually a string key.

Run from inside the repository. Paths default to the whole tree.

Usage:  cochange.py [--since "90 days ago"] [--top 20] [--min 3] [--json] [PATH ...]
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
from collections import Counter


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="90 days ago")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--min", type=int, default=3, help="minimum co-changes to report")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("paths", nargs="*", default=["."])
    args = ap.parse_args()

    root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, check=True).stdout.strip()
    log = subprocess.run(
        ["git", "log", f"--since={args.since}", "--no-merges", "--name-only",
         "--pretty=format:--%H", "--", *args.paths],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout
    pairs: Counter[tuple[str, str]] = Counter()
    commits = 0
    for block in log.split("--")[1:]:
        files = sorted({f for f in block.splitlines()[1:] if f.strip()})
        if 1 < len(files) <= 30:  # a 30-file commit is a rename, not a coupling
            commits += 1
            pairs.update(itertools.combinations(files, 2))

    rows = [(n, a, b) for (a, b), n in pairs.most_common() if n >= args.min][: args.top]
    if args.json:
        print(json.dumps({"since": args.since, "commits": commits,
                          "pairs": [{"count": n, "a": a, "b": b} for n, a, b in rows]}))
        return
    print(f"# co-change since {args.since!r}: {commits} commits, pairs with >= {args.min}")
    for n, a, b in rows:
        print(f"{n:3d}  {a}  {b}")


if __name__ == "__main__":
    main()

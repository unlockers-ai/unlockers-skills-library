#!/usr/bin/env python3
"""Publish a drift review: findings → GitHub issues, digest → a tracking issue,
the reviewed commit → a `drift/<date>` tag, the full report → a secret gist.

The reviewer (LLM) writes two files and stops; this script — deterministic,
no model — does every GitHub write, so what gets filed is inspectable before
it happens (`--dry-run`) and the reviewer never holds `gh`.

Input: a findings JSON next to the report, written by the review-drift skill:

    {"window": {"base": "<sha>", "end": "<sha>", "ref": "origin/main"},
     "models": ["opus", "fable"],
     "findings": [
       {"title": "...", "blast_radius": "local|module|codebase|doc",
        "confidence": "high|medium|low", "sensitive": true|false,
        "already_issue": 35 | null, "models": ["opus"],
        "body": "<markdown: evidence, siblings, radius, proposal, risk, confidence>"}],
     "not_findings": 14,
     "rule_discovered": "<one sentence>" | null}

Usage:
    drift_publish.py --findings F.json --report R.md [--repo owner/name]
                     [--date YYYY-MM-DD] [--duration "22 min"]
                     [--tracking-issue N] [--label drift] [--dry-run]

--repo defaults to the current checkout's GitHub repo. Without
--tracking-issue the digest is printed, not posted — open one issue titled
"Drift review log" and pass its number to keep a history.

Requires gh (logged in) and git; the tag is pushed to origin. On another
host, replace this script: the findings JSON is the contract.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path



def sh(*args: str, dry: bool = False, capture: bool = True) -> str:
    if dry:
        print("  $", " ".join(a if " " not in a else repr(a[:60] + ("…" if len(a) > 60 else "")) for a in args))
        return ""
    return subprocess.run(args, check=True, capture_output=capture, text=True).stdout.strip()


def issue_body(f: dict, date: str, report_url: str) -> str:
    who = ", ".join(f.get("models", [])) or "the drift review"
    head = (
        f"Found by the design-drift review of {date} ({who}); "
        f"blast radius **{f['blast_radius']}**, confidence **{f['confidence']}**"
        + (", security- or user-facing" if f.get("sensitive") else "")
        + f". Full report: {report_url}\n\n"
    )
    return head + f["body"].strip() + "\n"


def comment_body(f: dict, date: str, report_url: str) -> str:
    who = ", ".join(f.get("models", [])) or "the drift review"
    return (
        f"The drift review of {date} ({who}) re-found this and adds:\n\n"
        + f["body"].strip()
        + f"\n\nFull report: {report_url}\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--duration", default="")
    ap.add_argument("--repo", default="")
    ap.add_argument("--tracking-issue", type=int, default=None)
    ap.add_argument("--label", default="drift")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dry = a.dry_run
    repo = a.repo or sh("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")

    data = json.loads(a.findings.read_text())
    findings = data["findings"]
    window = data["window"]
    models = ", ".join(data.get("models", []))

    # 1. the full report, off the repo, linkable
    if dry:
        report_url = "<gist url>"
        print("gist:", a.report)
    else:
        report_url = sh("gh", "gist", "create", "--desc", f"Drift review {a.date} ({models}) — {repo}",
                        "--filename", f"drift-{a.date}.md", str(a.report))

    # 2. findings → new issues or comments on the issue that already covers them
    sh("gh", "-R", repo, "label", "create", a.label, "--force",
       "--description", "Found by the design-drift review", dry=dry)
    created, commented = [], []
    for f in findings:
        n = f.get("already_issue")
        if n:
            print(f"comment on #{n}: {f['title']}")
            sh("gh", "-R", repo, "issue", "comment", str(n), "--body", comment_body(f, a.date, report_url), dry=dry)
            commented.append((n, f))
        else:
            print(f"new issue: {f['title']}")
            url = sh("gh", "-R", repo, "issue", "create", "--label", a.label, "--title", f["title"],
                     "--body", issue_body(f, a.date, report_url), dry=dry)
            created.append((url.rsplit("/", 1)[-1] if url else "?", f))

    # 3. the reviewed commit gets a tag: the next run's base
    tag = f"drift/{a.date}"
    sh("git", "tag", "-f", tag, window["end"], dry=dry)
    sh("git", "push", "-q", "-f", "origin", tag, dry=dry)

    # 4. the digest, one comment on the tracking issue
    def row(num: object, f: dict) -> str:
        flag = " ⚠" if f.get("sensitive") else ""
        return f"- #{num} **{f['title']}** — {f['blast_radius']}, {f['confidence']}{flag}"

    digest = "\n".join([
        f"## {a.date} — `{window['base'][:7]}..{window['end'][:7]}` ({window.get('ref', 'origin/main')}), {models}",
        "",
        f"**{len(created)} new issue(s), {len(commented)} already filed and commented, "
        f"{data.get('not_findings', '?')} seeds ruled out.**"
        + (f" {a.duration}." if a.duration else ""),
        "",
        *(row(n, f) for n, f in created),
        *(f"- #{n} (already) — added: {f['title']}" for n, f in commented),
        "",
        *( [f"**Rule the codebase is discovering:** {data['rule_discovered']}", ""] if data.get("rule_discovered") else []),
        f"Full report: {report_url} · reviewed commit tagged `{tag}`",
    ])
    print("\n" + digest + "\n")
    if a.tracking_issue:
        sh("gh", "-R", repo, "issue", "comment", str(a.tracking_issue), "--body", digest, dry=dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())

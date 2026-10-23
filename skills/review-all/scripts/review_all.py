#!/usr/bin/env python3
"""The deterministic halves of the `review-all` skill: `collect` decides which
lenses delivered, `publish` posts the result to the pull request. The
orchestrator (LLM) launches the lenses and writes the prose summary; this
script — no model — does the checking and every GitHub write, so both are
testable and the same on every run. Same split as `review-drift`'s `drift_publish.py`.

A lens has delivered when its report under `reviews/` exists, its header pins
the compare SHA, and it closes with `X Critical, Y Major, Z Minor`; anything
else is *not reviewed*, never "0 findings" — except that a report pinned to one
of the `--previous` commits is *carried* when it has no Critical or Major
(the summary names those commits as `**Previous:**`). `collect` prints one
table row per lens for the summary. `publish` takes the compare SHA from the summary's own
header, re-reads the five reports against it, and posts: the summary as one PR
comment (one per reviewed SHA, updated in place on a re-run) and a commit
status `review/<lens>` on the full head SHA per lens — `success` when it ran and found
no Critical, `failure` on a Critical, `error` when not reviewed. The statuses
are a record, not a gate, unless the repo makes them required checks. It refuses
when the PR head is no longer the reviewed commit: a status on an old SHA is
invisible, and a comment about it reviews code that is not there any more.

Usage:
    review_all.py collect --compare <sha> [--previous <sha>]... [--dir reviews]
    review_all.py publish --pr N [--repo owner/name] [--dir reviews]

`publish` requires gh (logged in); --repo defaults to the current checkout's
GitHub repo. On another host, replace `GhCli`: the `GitHub` protocol is the
contract, and `github_contract.py` the tests a replacement must pass.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import ClassVar, Protocol

REPORTS = {  # lens → report file; the protocol table minus review-pr and review-impact (tests hold them equal)
    "complexity": "complexity-review-issues.md",
    "testing": "testing-review-issues.md",
    "architecture": "architecture-review-issues.md",
    "security": "security-review-issues.md",
    "slop": "slop-review-issues.md",
}
SUMMARY_FILE = "review-summary.md"
SUMMARY_LINE = re.compile(r"(\d+) Critical, (\d+) Major, (\d+) Minor")
COMPARE_LINE = re.compile(r"\*\*Compare:\*\*\s*([0-9a-f]{7,40})")
PREVIOUS_LINE = re.compile(r"\*\*Previous:\*\*\s*([0-9a-f]{7,40}(?:,\s*[0-9a-f]{7,40})*)")
DESCRIPTION_LIMIT = 140  # GitHub truncates a status description past this


class StaleReview(Exception):
    """The PR head moved since the review; publishing it would mislead."""


class SummaryDisagrees(Exception):
    """The pasted table in the summary is not what the reports say."""


@dataclass(frozen=True)
class CommitStatus:
    context: str
    state: str  # success | failure | error
    description: str


@dataclass(frozen=True)
class Comment:
    id: int
    body: str


@dataclass(frozen=True)
class Reviewed:
    lens: str
    critical: int
    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.critical} Critical, {self.major} Major, {self.minor} Minor"

    def table_row(self) -> str:
        return self._row(REPORTS[self.lens])

    def _row(self, report: str) -> str:
        return f"| {self.lens} | {self.critical} | {self.major} | {self.minor} | {report} |"

    def status(self) -> CommitStatus:
        return CommitStatus(f"review/{self.lens}", "failure" if self.critical else "success", str(self))


@dataclass(frozen=True)
class Carried:
    """A clean lens not resumed in a verification round: its report from an earlier one."""

    reviewed: Reviewed
    from_sha: Sha

    def _note(self) -> str:
        return f"(carried from {self.from_sha.short()})"

    def table_row(self) -> str:
        return self.reviewed._row(f"{REPORTS[self.reviewed.lens]} {self._note()}")

    def status(self) -> CommitStatus:
        status = self.reviewed.status()
        return replace(status, description=f"{status.description} {self._note()}")


@dataclass(frozen=True)
class NotReviewed:
    lens: str
    reason: str

    def table_row(self) -> str:
        return f"| {self.lens} | not reviewed — {self.reason} | | | {REPORTS[self.lens]} |"

    def status(self) -> CommitStatus:
        return CommitStatus(f"review/{self.lens}", "error", f"not reviewed — {self.reason}"[:DESCRIPTION_LIMIT])


LensOutcome = Reviewed | Carried | NotReviewed


@dataclass(frozen=True)
class Sha:
    """A commit SHA, full or abbreviated. Git's own floor for an abbreviation is
    7 hex characters; anything shorter names no commit, not even itself."""

    value: str
    _MIN_ABBREV: ClassVar[int] = 7

    def same_commit(self, other: Sha) -> bool:
        if min(len(self.value), len(other.value)) < self._MIN_ABBREV:
            return False
        return self.value.startswith(other.value) or other.value.startswith(self.value)

    def short(self) -> str:
        return self.value[:10]

    def __str__(self) -> str:
        return self.value


def pinned_sha(report: str) -> Sha | None:
    found = COMPARE_LINE.search(report)
    return Sha(found.group(1)) if found else None


def earlier_shas(summary: str) -> tuple[Sha, ...]:
    """The earlier rounds' compare SHAs a verification summary names; none on a first review."""
    found = PREVIOUS_LINE.search(summary)
    return tuple(Sha(sha.strip()) for sha in found.group(1).split(",")) if found else ()


def delivery(lens: str, report: str | None, compare: Sha, earlier: tuple[Sha, ...] = ()) -> LensOutcome:
    """The delivery check: a report counts only if it is about this commit — or,
    in a verification round, if it is a clean one about an earlier round's."""
    if report is None:
        return NotReviewed(lens, "no report")
    pinned = pinned_sha(report)
    if pinned is None:
        return NotReviewed(lens, "report pins no commit")
    found = SUMMARY_LINE.findall(report)
    if not found:
        return NotReviewed(lens, "no 'X Critical, Y Major, Z Minor' line")
    reviewed = Reviewed(lens, *map(int, found[-1]))
    if compare.same_commit(pinned):
        return reviewed
    if not any(sha.same_commit(pinned) for sha in earlier):
        return NotReviewed(lens, f"report pins {pinned.short()}, not this one")
    if reviewed.critical or reviewed.major:
        return NotReviewed(lens, f"report pins {pinned.short()}: a lens with an open Critical or Major verifies the new commit")
    return Carried(reviewed, pinned)


def collect(reviews: Path, compare: Sha, earlier: tuple[Sha, ...] = ()) -> list[LensOutcome]:
    reports = {lens: reviews / name for lens, name in REPORTS.items()}
    return [delivery(lens, path.read_text() if path.exists() else None, compare, earlier)
            for lens, path in reports.items()]


def marker(sha: Sha) -> str:
    return f"<!-- review-all {sha} -->"


def comment_body(sha: Sha, summary_markdown: str) -> str:
    return f"{marker(sha)}\n{summary_markdown.strip()}\n"


class GitHub(Protocol):
    def pr_head(self, pr: int) -> str: ...
    def comments(self, pr: int) -> list[Comment]: ...
    def create_comment(self, pr: int, body: str) -> str: ...
    def update_comment(self, comment_id: int, body: str) -> str: ...
    def set_status(self, sha: str, status: CommitStatus, target_url: str) -> None: ...


def publish(gh: GitHub, pr: int, summary_markdown: str,
            outcomes_for: Callable[[Sha, tuple[Sha, ...]], list[LensOutcome]]) -> str:
    """Decide, then apply. Returns the comment URL every status points at."""
    compare = pinned_sha(summary_markdown)
    if compare is None:
        raise StaleReview("the summary pins no commit — its header must carry **Compare:** <sha>")
    head = Sha(gh.pr_head(pr))
    if not head.same_commit(compare):
        raise StaleReview(f"PR #{pr} head is {head.short()}, the review is of {compare.short()} — the PR head moved: see review-all, publish step")
    outcomes = outcomes_for(head, earlier_shas(summary_markdown))  # the full SHA from here on: statuses and the marker name the commit exactly
    missing = [o.table_row() for o in outcomes if o.table_row() not in summary_markdown]
    if missing:
        raise SummaryDisagrees("the summary's table is not what the reports say — collect again and paste:\n" + "\n".join(missing))
    body = comment_body(head, summary_markdown)
    statuses = [o.status() for o in outcomes]
    existing = next((c.id for c in gh.comments(pr) if c.body.startswith(marker(head))), None)

    url = gh.update_comment(existing, body) if existing is not None else gh.create_comment(pr, body)
    for status in statuses:
        gh.set_status(head.value, status, url)
    return url


def comments_from_pages(slurped: str) -> list[Comment]:
    """`gh api --paginate --slurp` returns one array per page, 30 comments each."""
    return [Comment(c["id"], c["body"]) for page in json.loads(slurped) for c in page]


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def current_repo() -> str:
    return _gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()


class GhCli:
    def __init__(self, repo: str, run: Callable[..., str] = _gh) -> None:
        self._repo = repo
        self._run = run

    def pr_head(self, pr: int) -> str:
        return self._run("-R", self._repo, "pr", "view", str(pr), "--json", "headRefOid", "-q", ".headRefOid").strip()

    def comments(self, pr: int) -> list[Comment]:
        return comments_from_pages(self._run("api", "--paginate", "--slurp", f"repos/{self._repo}/issues/{pr}/comments"))

    def create_comment(self, pr: int, body: str) -> str:
        return json.loads(self._run("api", "-X", "POST", f"repos/{self._repo}/issues/{pr}/comments", "-f", f"body={body}"))["html_url"]

    def update_comment(self, comment_id: int, body: str) -> str:
        return json.loads(self._run("api", "-X", "PATCH", f"repos/{self._repo}/issues/comments/{comment_id}", "-f", f"body={body}"))["html_url"]

    def set_status(self, sha: str, status: CommitStatus, target_url: str) -> None:
        self._run(
            "api", "-X", "POST", f"repos/{self._repo}/statuses/{sha}",
            "-f", f"state={status.state}", "-f", f"context={status.context}",
            "-f", f"description={status.description}", "-f", f"target_url={target_url}",
        )


def main(argv: list[str] | None = None, github: GitHub | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect", help="print one row per lens: delivered with its counts, or not reviewed")
    c.add_argument("--compare", required=True)
    c.add_argument("--previous", action="append", default=[],
                   help="a verification round: an earlier round's compare SHA, once per earlier round")
    c.add_argument("--dir", type=Path, default=Path("reviews"))
    q = sub.add_parser("publish", help="post the summary comment and one status per lens to the PR")
    q.add_argument("--pr", type=int, required=True)
    q.add_argument("--repo", default="", help="owner/name (default: the current checkout's GitHub repo)")
    q.add_argument("--dir", type=Path, default=Path("reviews"))
    a = p.parse_args(argv)

    if a.command == "collect":
        earlier = tuple(map(Sha, a.previous))
        if earlier:
            print(f"**Previous:** {', '.join(a.previous)}\n")  # the summary's header line, pasted with the table
        print("\n".join(o.table_row() for o in collect(a.dir, Sha(a.compare), earlier)))
        return
    url = publish(github or GhCli(a.repo or current_repo()), a.pr, (a.dir / SUMMARY_FILE).read_text(), lambda sha, earlier: collect(a.dir, sha, earlier))
    print(f"published to PR #{a.pr}: {url}")


if __name__ == "__main__":
    main()

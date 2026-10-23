"""
Tests for review_all.py — the deterministic halves of the `review-all`
skill: which lenses delivered (a report counts only if it pins this commit and
closes with a summary line), and the publish step: one status per lens on the
reviewed SHA, one comment per SHA.
"""

import json
import re
from pathlib import Path

import pytest

import review_all
from github_contract import SHA as CONTRACT_SHA
from github_contract import GitHubContract

PROTOCOL = Path(__file__).resolve().parents[3] / "docs" / "review-protocol.md"

Carried = review_all.Carried
Comment = review_all.Comment
CommitStatus = review_all.CommitStatus
GhCli = review_all.GhCli
NotReviewed = review_all.NotReviewed
Reviewed = review_all.Reviewed
Sha = review_all.Sha
SHA = "66f73df5703891dea7995a6df4ce08283a801975"
OLD_SHA = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"  # the round before (r2)
R1_SHA = "9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"  # the first round
EARLIER = (Sha(OLD_SHA), Sha(R1_SHA))
CLEAN = "0 Critical, 0 Major, 0 Minor"


class FakeGitHub:
    def __init__(self, head: str, comments: list[Comment] = ()) -> None:
        self.head = head
        self._comments = list(comments)
        self.statuses: list[tuple[str, CommitStatus, str]] = []

    def pr_head(self, pr: int) -> str:
        return self.head

    def comments(self, pr: int) -> list[Comment]:
        return list(self._comments)

    def create_comment(self, pr: int, body: str) -> str:
        self._comments.append(Comment(len(self._comments) + 1, body))
        return f"https://github.com/c/{len(self._comments)}"

    def update_comment(self, comment_id: int, body: str) -> str:
        self._comments = [Comment(c.id, body) if c.id == comment_id else c for c in self._comments]
        return f"https://github.com/c/{comment_id}"

    def set_status(self, sha: str, status: CommitStatus, target_url: str) -> None:
        self.statuses.append((sha, status, target_url))


def _report(compare: str = SHA, summary: str = "0 Critical, 1 Major, 2 Minor", header: bool = True) -> str:
    head = f"**Compare:** {compare} (x)  ·  **Base:** 0 (main)\n" if header else ""
    return f"# Testing Review\n\n{head}\n## Summary\n{summary}\n"


CLEAN_SECURITY = Reviewed("security", 0, 0, 0)


def _summary(compare: str = SHA, outcomes=(CLEAN_SECURITY,)) -> str:
    rows = "\n".join(o.table_row() for o in outcomes)
    return f"# Review summary\n\n**Compare:** {compare} (x)\n\n{rows}"


def _publish(gh: FakeGitHub, summary: str | None = None, outcomes=(CLEAN_SECURITY,)) -> str:
    summary = _summary(outcomes=outcomes) if summary is None else summary
    return review_all.publish(gh, 152, summary, lambda sha, earlier: list(outcomes))


# --- delivery ---------------------------------------------------------------

@pytest.mark.parametrize(
    "report,expected",
    [
        (_report(), Reviewed("testing", 0, 1, 2)),
        (_report(compare=SHA[:7]), Reviewed("testing", 0, 1, 2)),
        (_report(compare=SHA[:7], summary="1 Critical, 0 Major, 0 Minor"), Reviewed("testing", 1, 0, 0)),
        (_report(summary="9 Critical, 9 Major, 9 Minor\n\n0 Critical, 0 Major, 1 Minor"), Reviewed("testing", 0, 0, 1)),
        (None, NotReviewed("testing", "no report")),
        (_report(header=False), NotReviewed("testing", "report pins no commit")),
        (_report(compare=OLD_SHA), NotReviewed("testing", "report pins 1a2b3c4d5e, not this one")),
        (_report(summary="2 violations found"), NotReviewed("testing", "no 'X Critical, Y Major, Z Minor' line")),
    ],
)
def test_given_a_report_when_checked_for_delivery_then_only_one_pinned_to_this_commit_with_a_last_summary_line_counts(report, expected):
    assert review_all.delivery("testing", report, Sha(SHA)) == expected


@pytest.mark.parametrize(
    "report,expected",
    [
        (_report(compare=OLD_SHA, summary="0 Critical, 0 Major, 1 Minor"),
         Carried(Reviewed("testing", 0, 0, 1), Sha(OLD_SHA))),
        (_report(compare=R1_SHA, summary=CLEAN), Carried(Reviewed("testing", 0, 0, 0), Sha(R1_SHA))),
        (_report(compare=OLD_SHA, summary="0 Critical, 1 Major, 0 Minor"),
         NotReviewed("testing", "report pins 1a2b3c4d5e: a lens with an open Critical or Major verifies the new commit")),
        (_report(compare=OLD_SHA, summary="1 Critical, 0 Major, 0 Minor"),
         NotReviewed("testing", "report pins 1a2b3c4d5e: a lens with an open Critical or Major verifies the new commit")),
        (_report(), Reviewed("testing", 0, 1, 2)),
    ],
)
def test_given_a_verification_round_when_checked_then_only_a_clean_report_on_an_earlier_round_is_carried(report, expected):
    """Only the lenses that had something to say are resumed to verify; a clean
    one keeps its report from whichever round it was last clean in."""
    assert review_all.delivery("testing", report, Sha(SHA), EARLIER) == expected


def test_given_an_abbreviated_compare_sha_when_checked_against_a_full_one_then_it_is_the_same_commit():
    assert review_all.delivery("testing", _report(compare=SHA), Sha(SHA[:10])) == Reviewed("testing", 0, 1, 2)


@pytest.mark.parametrize("compare", ["", "6", SHA[:6]])
def test_given_a_compare_shorter_than_gits_floor_when_checked_then_no_report_counts(compare):
    assert review_all.delivery("testing", _report(compare=SHA), Sha(compare)) == NotReviewed("testing", f"report pins {SHA[:10]}, not this one")


def test_given_a_reviews_dir_when_collected_then_every_lens_is_accounted_for_delivered_or_not(tmp_path):
    (tmp_path / "security-review-issues.md").write_text(_report(summary="0 Critical, 0 Major, 0 Minor"))

    assert review_all.collect(tmp_path, Sha(SHA)) == [
        NotReviewed("complexity", "no report"), NotReviewed("testing", "no report"),
        NotReviewed("architecture", "no report"), Reviewed("security", 0, 0, 0),
        NotReviewed("slop", "no report")]


@pytest.mark.parametrize(
    "outcome,row",
    [
        (Reviewed("testing", 0, 1, 2), "| testing | 0 | 1 | 2 | testing-review-issues.md |"),
        (NotReviewed("slop", "no report"), "| slop | not reviewed — no report | | | slop-review-issues.md |"),
        (Carried(Reviewed("security", 0, 0, 0), Sha(OLD_SHA)),
         "| security | 0 | 0 | 0 | security-review-issues.md (carried from 1a2b3c4d5e) |"),
    ],
)
def test_given_an_outcome_when_rendered_as_a_table_row_then_counts_are_in_critical_major_minor_order(outcome, row):
    assert outcome.table_row() == row


def test_given_the_protocol_report_shape_when_parsed_then_the_header_and_summary_line_are_what_the_script_reads():
    protocol = PROTOCOL.read_text()
    example = protocol.replace("<sha>", SHA).replace("X Critical, Y Major, Z Minor", "1 Critical, 2 Major, 3 Minor")

    assert review_all.delivery("testing", example, Sha(SHA)) == Reviewed("testing", 1, 2, 3)


def test_given_the_protocol_table_when_compared_to_the_script_then_the_lens_registry_is_the_same():
    protocol = PROTOCOL.read_text()
    rows = re.findall(r"\| \[`review-(\w+)`\].*?`reviews/([\w-]+\.md)`", protocol)

    assert {lens: report for lens, report in rows if lens not in ("pr", "impact")} == review_all.REPORTS


# --- statuses ---------------------------------------------------------------

@pytest.mark.parametrize(
    "outcome,expected",
    [
        (Reviewed("security", 0, 0, 0), CommitStatus("review/security", "success", "0 Critical, 0 Major, 0 Minor")),
        (Reviewed("testing", 0, 1, 2), CommitStatus("review/testing", "success", "0 Critical, 1 Major, 2 Minor")),
        (Reviewed("slop", 1, 0, 0), CommitStatus("review/slop", "failure", "1 Critical, 0 Major, 0 Minor")),
        (NotReviewed("impact", "subagent errored"), CommitStatus("review/impact", "error", "not reviewed — subagent errored")),
        (Carried(Reviewed("security", 0, 0, 0), Sha(OLD_SHA)),
         CommitStatus("review/security", "success", "0 Critical, 0 Major, 0 Minor (carried from 1a2b3c4d5e)")),
    ],
)
def test_given_a_lens_outcome_when_turned_into_a_status_then_only_a_critical_or_a_missing_report_is_red(outcome, expected):
    assert outcome.status() == expected


# --- publish ----------------------------------------------------------------

def test_given_a_fresh_sha_when_published_then_one_comment_and_one_status_per_lens_point_at_it():
    gh = FakeGitHub(head=SHA)
    outcomes = [Reviewed("security", 0, 0, 0), NotReviewed("slop", "no report")]

    url = _publish(gh, outcomes=outcomes)

    assert gh.comments(152) == [Comment(1, f"<!-- review-all {SHA} -->\n{_summary(outcomes=outcomes)}\n")]
    assert gh.statuses == [(SHA, o.status(), url) for o in outcomes]


def test_given_a_comment_for_this_sha_already_when_published_again_then_it_is_updated_not_duplicated():
    gh = FakeGitHub(head=SHA, comments=[Comment(7, f"<!-- review-all {SHA} -->\nold")])

    _publish(gh)

    assert gh.comments(152) == [Comment(7, f"<!-- review-all {SHA} -->\n{_summary()}\n")]


def test_given_a_comment_for_an_older_sha_when_published_then_a_new_comment_is_added():
    old = Comment(7, f"<!-- review-all {OLD_SHA} -->\nold")
    gh = FakeGitHub(head=SHA, comments=[old])

    _publish(gh)

    assert gh.comments(152) == [old, Comment(2, f"<!-- review-all {SHA} -->\n{_summary()}\n")]


def test_given_the_pr_head_moved_since_the_review_when_published_then_nothing_is_written():
    gh = FakeGitHub(head=OLD_SHA)

    with pytest.raises(review_all.StaleReview, match="the PR head moved"):
        _publish(gh)

    assert (gh.comments(152), gh.statuses) == ([], [])


def test_given_a_summary_pinning_an_abbreviated_sha_when_published_then_statuses_and_marker_carry_the_full_head():
    gh = FakeGitHub(head=SHA)

    url = _publish(gh, summary=_summary(compare=SHA[:12]))

    assert gh.statuses == [(SHA, CLEAN_SECURITY.status(), url)]
    assert gh.comments(152)[0].body.startswith(f"<!-- review-all {SHA} -->\n")


def test_given_a_summary_table_that_disagrees_with_the_reports_when_published_then_nothing_is_written():
    gh = FakeGitHub(head=SHA)

    with pytest.raises(review_all.SummaryDisagrees, match=r"\| slop \| 1 \| 0 \| 0 \|"):
        _publish(gh, summary=_summary(outcomes=[CLEAN_SECURITY]), outcomes=[CLEAN_SECURITY, Reviewed("slop", 1, 0, 0)])

    assert (gh.comments(152), gh.statuses) == ([], [])


def test_given_a_summary_that_pins_no_commit_when_published_then_nothing_is_written():
    gh = FakeGitHub(head=SHA)

    with pytest.raises(review_all.StaleReview, match="pins no commit"):
        _publish(gh, summary="# Review summary\n\n| … |")

    assert (gh.comments(152), gh.statuses) == ([], [])


def test_given_reports_on_disk_when_published_then_the_statuses_come_from_the_reports_at_the_summarys_sha(tmp_path):
    (tmp_path / "slop-review-issues.md").write_text(_report(summary="1 Critical, 0 Major, 0 Minor"))
    gh = FakeGitHub(head=SHA)

    summary = _summary(outcomes=review_all.collect(tmp_path, Sha(SHA)))

    url = review_all.publish(gh, 152, summary, lambda sha, earlier: review_all.collect(tmp_path, sha, earlier))

    missing = [(SHA, CommitStatus(f"review/{lens}", "error", "not reviewed — no report"), url)
               for lens in ("complexity", "testing", "architecture", "security")]
    assert gh.statuses == [*missing, (SHA, CommitStatus("review/slop", "failure", "1 Critical, 0 Major, 0 Minor"), url)]


def _verification_summary(reviews: Path) -> str:
    """What the orchestrator pastes in a verification round: collect's whole output under the header."""
    rows = review_all.collect(reviews, Sha(SHA), EARLIER)
    return _summary(outcomes=rows).replace("(x)\n", f"(x)\n**Previous:** {OLD_SHA}, {R1_SHA}\n")


def test_given_a_verification_summary_naming_the_earlier_rounds_when_published_then_clean_lenses_are_carried(tmp_path):
    (tmp_path / "security-review-issues.md").write_text(_report(compare=OLD_SHA, summary=CLEAN))
    (tmp_path / "slop-review-issues.md").write_text(_report(summary="0 Critical, 0 Major, 1 Minor"))
    gh = FakeGitHub(head=SHA)

    url = review_all.publish(gh, 152, _verification_summary(tmp_path),
                             lambda sha, earlier: review_all.collect(tmp_path, sha, earlier))

    missing = [(SHA, CommitStatus(f"review/{lens}", "error", "not reviewed — no report"), url)
               for lens in ("complexity", "testing", "architecture")]
    assert gh.statuses == [
        *missing, (SHA, CommitStatus("review/security", "success", f"{CLEAN} (carried from 1a2b3c4d5e)"), url),
        (SHA, CommitStatus("review/slop", "success", "0 Critical, 0 Major, 1 Minor"), url)]


def test_given_collect_args_with_earlier_rounds_when_main_runs_then_it_prints_their_header_line_and_carries_clean_lenses(
        tmp_path, capsys):
    (tmp_path / "security-review-issues.md").write_text(_report(compare=R1_SHA, summary=CLEAN))

    review_all.main(["collect", "--compare", SHA, "--previous", OLD_SHA, "--previous", R1_SHA, "--dir", str(tmp_path)])

    out = capsys.readouterr().out.splitlines()
    assert (out[:2], out[5]) == ([f"**Previous:** {OLD_SHA}, {R1_SHA}", ""],
                                 "| security | 0 | 0 | 0 | security-review-issues.md (carried from 9f8e7d6c5b) |")


def test_given_two_pages_of_comments_when_parsed_then_all_are_returned_in_order():
    pages = '[{"id": 1, "body": "a"}, {"id": 2, "body": "b"}][{"id": 3, "body": "c"}]'.replace("][", "],[")

    assert review_all.comments_from_pages(f"[{pages}]") == [Comment(1, "a"), Comment(2, "b"), Comment(3, "c")]


# --- Sha ----------------------------------------------------------------

@pytest.mark.parametrize(
    "a,b",
    [
        (SHA, SHA),
        (SHA, SHA[:10]),
        (SHA[:7], SHA),
    ],
)
def test_given_full_or_abbreviated_forms_of_one_sha_when_compared_then_they_are_the_same_commit(a, b):
    assert Sha(a).same_commit(Sha(b))


@pytest.mark.parametrize("a,b", [(SHA, OLD_SHA), (SHA, SHA[:6]), ("", SHA)])
def test_given_a_different_commit_or_too_short_an_abbreviation_when_compared_then_they_are_not_the_same_commit(a, b):
    assert not Sha(a).same_commit(Sha(b))


def test_given_a_sha_when_rendered_short_then_it_is_the_first_ten_characters():
    assert Sha(SHA).short() == SHA[:10]


# --- main ---------------------------------------------------------------

def test_given_collect_args_when_main_runs_then_it_prints_the_table_rows(tmp_path, capsys):
    (tmp_path / "slop-review-issues.md").write_text(_report(summary="1 Critical, 0 Major, 0 Minor"))

    review_all.main(["collect", "--compare", SHA, "--dir", str(tmp_path)])

    assert "| slop | 1 | 0 | 0 | slop-review-issues.md |" in capsys.readouterr().out


def test_given_publish_args_when_main_runs_then_it_publishes_through_the_injected_github(tmp_path, capsys):
    (tmp_path / "security-review-issues.md").write_text(_report(summary="0 Critical, 0 Major, 0 Minor"))
    summary = _summary(outcomes=review_all.collect(tmp_path, Sha(SHA)))
    (tmp_path / review_all.SUMMARY_FILE).write_text(summary)
    gh = FakeGitHub(head=SHA)

    review_all.main(["publish", "--pr", "152", "--dir", str(tmp_path)], github=gh)

    assert gh.comments(152) == [Comment(1, f"<!-- review-all {SHA} -->\n{summary}\n")]
    assert "published to PR #152" in capsys.readouterr().out


def test_given_publish_args_in_a_verification_round_when_main_runs_then_a_report_from_the_first_round_is_carried(
        tmp_path):
    (tmp_path / "security-review-issues.md").write_text(_report(compare=R1_SHA, summary=CLEAN))
    (tmp_path / review_all.SUMMARY_FILE).write_text(_verification_summary(tmp_path))
    gh = FakeGitHub(head=SHA)

    review_all.main(["publish", "--pr", "152", "--dir", str(tmp_path)], github=gh)

    carried = CommitStatus("review/security", "success", f"{CLEAN} (carried from 9f8e7d6c5b)")
    assert carried in [status for _, status, _ in gh.statuses]


# --- GitHub contract ------------------------------------------------------

class FakeGhProcess:
    """Stands in for the `gh` binary: parses the same argv `GhCli` builds and
    answers the shapes `gh pr view`/`gh api` return, so `GhCli` runs exactly as
    it does against the real CLI — only the process underneath it is faked."""

    _PAGE_SIZE = 30

    def __init__(self, head: str) -> None:
        self.head = head
        self._comments: dict[int, str] = {}
        self._next_id = 1
        self.statuses: list[tuple[str, dict[str, str]]] = []

    def __call__(self, *args: str) -> str:
        if args[0] == "-R":
            return f"{self.head}\n"
        fields = {args[i + 1].split("=", 1)[0]: args[i + 1].split("=", 1)[1]
                  for i, a in enumerate(args) if a == "-f"}
        if args[1] == "--paginate":
            ids = sorted(self._comments)
            pages = [ids[i:i + self._PAGE_SIZE] for i in range(0, len(ids), self._PAGE_SIZE)] or [[]]
            return json.dumps([[{"id": i, "body": self._comments[i]} for i in page] for page in pages])
        path = args[3]
        if path.endswith("/comments") and "POST" in args:
            comment_id = self._next_id
            self._next_id += 1
            self._comments[comment_id] = fields["body"]
            return json.dumps({"id": comment_id, "html_url": f"https://github.com/c/{comment_id}"})
        if "/comments/" in path:
            comment_id = int(path.rsplit("/", 1)[-1])
            self._comments[comment_id] = fields["body"]
            return json.dumps({"id": comment_id, "html_url": f"https://github.com/c/{comment_id}"})
        sha = path.rsplit("/", 1)[-1]
        self.statuses.append((sha, fields))
        return json.dumps({"state": fields["state"]})


class TestFakeGitHubContract(GitHubContract):
    def create_github(self):
        return FakeGitHub(head=CONTRACT_SHA)

    def recorded_statuses(self, gh):
        return [(sha, status) for sha, status, _url in gh.statuses]


class TestGhCliContract(GitHubContract):
    def create_github(self):
        self._process = FakeGhProcess(head=CONTRACT_SHA)
        return GhCli("owner/name", run=self._process)

    def recorded_statuses(self, gh):
        return [(sha, CommitStatus(fields["context"], fields["state"], fields["description"]))
                for sha, fields in self._process.statuses]

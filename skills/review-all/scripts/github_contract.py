"""Contract for the `GitHub` port in `review_all.py`: whatever
posts a comment must have it show up in the list, updating an existing
comment must replace its body in place rather than add a new one, listing
must survive GitHub's own page size, and a status must be recorded against
the sha it was set on.
"""

from abc import ABC, abstractmethod

from review_all import CommitStatus, GitHub

PR = 152
SHA = "66f73df5703891dea7995a6df4ce08283a801975"


class GitHubContract(ABC):

    @abstractmethod
    def create_github(self) -> GitHub:
        """A GitHub whose PR #152 is on SHA and carries no comments yet."""
        ...

    @abstractmethod
    def recorded_statuses(self, gh: GitHub) -> list[tuple[str, CommitStatus]]:
        """Every (sha, status) passed to set_status so far, in order."""
        ...

    def test_given_a_pr_when_asked_for_its_head_then_the_commit_it_is_on_is_returned(self):
        gh = self.create_github()

        assert gh.pr_head(PR) == SHA

    def test_given_no_comments_when_one_is_created_then_it_is_the_only_one_listed(self):
        gh = self.create_github()

        url = gh.create_comment(PR, "hello")

        assert [c.body for c in gh.comments(PR)] == ["hello"]
        assert url

    def test_given_an_existing_comment_when_updated_then_its_body_changes_in_place(self):
        gh = self.create_github()
        gh.create_comment(PR, "old")
        comment_id = gh.comments(PR)[0].id

        gh.update_comment(comment_id, "new")

        assert [(c.id, c.body) for c in gh.comments(PR)] == [(comment_id, "new")]

    def test_given_more_comments_than_one_page_when_listed_then_all_of_them_come_back(self):
        gh = self.create_github()
        for i in range(35):
            gh.create_comment(PR, f"comment {i}")

        assert len(gh.comments(PR)) == 35

    def test_given_a_status_when_set_then_it_is_recorded_against_the_sha(self):
        gh = self.create_github()
        status = CommitStatus("review/testing", "success", "0 Critical, 0 Major, 0 Minor")

        gh.set_status(SHA, status, "https://example/c/1")

        assert self.recorded_statuses(gh) == [(SHA, status)]

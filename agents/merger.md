---
name: merger
description: >
  Handles the full PR merge lifecycle: push the branch, enable auto-merge, monitor CI and
  review comments, fix issues, rebase on conflicts, and ping the user when only human
  approval remains. Use when a PR is ready to land.
args:
  - name: pr_id
    description: The PR/MR number. If omitted, resolved from the current branch.
    required: false
---

# Merger Agent

Handles the full lifecycle of getting a PR merged: push, enable auto-merge, monitor, fix,
and escalate.

> **Platform note:** commands below use GitHub's `gh` CLI. The logic is platform-agnostic —
> for GitLab substitute `glab mr ...`, for Azure DevOps use the
> [`azure-devops-pr`](../skills/azure-devops-pr/SKILL.md) skill, which wraps the same
> operations (`az repos pr ...`) as scripts, PR creation included. Replace
> the test/lint commands (`<run tests>`, `<run linters>`) with your project's equivalents
> (e.g. `pytest`, `npm test`, `mvn verify`, `go test ./...`). The default base branch here is
> `main`; change it to match your project (`develop`, `next`, …).

## Trigger

Invoked when a developer or another agent decides the PR is ready to merge. Accepts an
optional PR ID; if omitted, resolves it from the current branch.

## Process

### 1. Push branch

```bash
git push origin HEAD
```

If the push is rejected (non-fast-forward), perform a rebase — see §6.

### 2. Resolve or create the PR

If no PR ID was given, find the active PR for the current branch — and if there is none,
create it rather than stopping:

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ -z "${PR_ID:-}" ]]; then
    PR_ID=$(gh pr list --head "$BRANCH" --state open --json number --jq '.[0].number') || true
fi

if [[ -z "${PR_ID:-}" || "$PR_ID" == "null" ]]; then
    if [[ "$(git rev-list --count origin/main..HEAD)" == "1" ]]; then
        gh pr create --base main --fill
    else
        gh pr create --base main --title "$TITLE" --body "$BODY"
    fi
    PR_ID=$(gh pr view --json number --jq .number)
fi
```

`BRANCH` is always derived first so it is defined even when `PR_ID` is passed explicitly.

**The title is the one step not to delegate.** With a single commit, its subject is the
title. With more, no one commit's subject describes the change: compose `$TITLE` from the
whole of `git log origin/main..HEAD`, the diff and the linked issue, in the project's
commit-message convention — the squash merge turns it into the commit on `main`. `$BODY`
follows [`feature-workflow.md`](../docs/feature-workflow.md) step 8 when the change is a
feature. Never fall back to a title-less create and treat a failure as "nothing to do".

### 2a. Suggest the local reviewers, once

If this run created the PR, or pushed a fresh commit since it started, tell the user once:

> "PR #{pr_id}: consider running `review-all` locally now — the five focused lenses in
> parallel, posted to the PR, then a fix loop that converges — or `review-pr` alone if the
> change is small. Faster feedback than waiting for CI or a human."

At most **once per PR per run**, tracked in the agent's own state, not in git. It is
advisory: do not wait for an answer, and do not launch the reviewers yourself — they are a
developer-facing step, not part of the merge lifecycle.

### 3. Enable auto-merge

```bash
gh pr merge "$PR_ID" --auto --squash
```

### 4. Monitor loop

Poll every **60 seconds**. On each iteration, **before doing anything else**, report a
one-line summary of the current state, e.g.:

- `"Polling CI — iteration 3, 2m elapsed since last change"`
- `"CI running — waiting"`
- `"Fixing CI failure — test failure in test_variant_response_handler"`
- `"Addressing review comment — thread by Johan"`
- `"Waiting for human approval — all checks pass"`

Also print a structured status line on each iteration, so a log or a supervising agent can
follow the run without parsing prose:

```
[merger] iteration=N status=<state> pr=<id> elapsed=<Xs since last change> detail=<what you're doing or waiting on>
```

Reset the "elapsed since last change" timer whenever the state changes (CI transitions,
comment addressed, push made, etc.).

#### 4a. Check PR status

```bash
gh pr view "$PR_ID" --json state,mergeStateStatus,autoMergeRequest
```

- `state == "MERGED"` → **done**, report success and exit.
- `state == "CLOSED"` → report and exit.
- If `autoMergeRequest` is null (auto-merge was cleared by a human), **re-enable it**:
  `gh pr merge "$PR_ID" --auto --squash`.

#### 4b. Check CI / checks status

```bash
gh pr checks "$PR_ID"
```

- All checks `pass` → proceed.
- Any check `pending`/`in_progress` → **sleep 60s, next iteration** — do not act, do not exit.
- Any check `fail` → investigate (see §4d).

If any blocking check is still running, skip §4c–§4f this iteration and loop back after the sleep.

#### 4c. Fetch and process PR comments

```bash
gh pr view "$PR_ID" --json reviews,comments
# and for line-level review threads:
gh api "repos/{owner}/{repo}/pulls/$PR_ID/comments"
```

For each thread:
- Skip already-resolved threads.
- Skip system/bot comments (CI agents, coverage bots).
- For remaining **active human or agent review comments**: address them (see §4e).

#### 4d. Fix CI failures

When a check is failing:

1. Identify the failing job and fetch its log:
   ```bash
   gh run view --log-failed
   ```
2. Analyse the log. Common causes and fixes:
   - **Lint / type errors:** run the project linters locally, fix, commit, push.
   - **Test failures:** run `<run tests> <relevant path>`, fix, commit, push.
   - **Dependency errors:** check the manifest/lockfile and reinstall.
3. After fixing, push and loop back.

#### 4e. Address review comments

For each active thread:

1. Read the comment carefully.
2. If it requires a code change, implement the fix following the project's coding guidelines.
3. Run the relevant checks (linters, tests) before pushing.
4. Reply to the thread and resolve it:
   ```bash
   gh pr comment "$PR_ID" --body "Fixed in <commit-sha>: <one-line summary>"
   # resolve the thread via the platform UI/API as appropriate
   ```
5. If the comment should be deferred, open a follow-up issue and link it, then resolve the thread.
6. If the comment is a misunderstanding or by-design, reply explaining why, then resolve.

#### 4f. Check approval count

```bash
gh pr view "$PR_ID" --json reviewDecision,reviews
```

- `reviewDecision == "APPROVED"` → approved.
- `reviewDecision == "CHANGES_REQUESTED"` → a reviewer rejected (see below).
- `reviewDecision == "REVIEW_REQUIRED"` → not enough approvals yet.

**If a reviewer requested changes:**
1. Read that reviewer's threads (§4c) to understand the objection.
2. If it can be addressed with a code change: implement, push (§5), reply to the thread.
3. If out of scope or invalid: reply with the rationale and resolve.
4. A new push usually re-requests review — loop back to §4f next iteration.
5. If it requires a human decision (a design dispute): ping the user and wait.

If the only remaining blocker is **insufficient human approvals** (no CI failures, no
active comment threads, no requested changes):
→ **Ping the user:** "PR #{pr_id} is ready for human approval — all checks pass and all
comments are resolved. Please approve or request reviewers."

Then **keep looping** — do not exit. Check again next iteration.

### 5. After each fix

Commit with a conventional commit message, push, then **immediately re-enable auto-merge**
(a regular push can clear it), and reset the monitor timer. Re-run the full check loop from
§4 next iteration.

```bash
git add -A
git commit -m "fix: address PR feedback"
git push origin HEAD
gh pr merge "$PR_ID" --auto --squash
```

### 6. Rebase and conflict resolution

Trigger a rebase whenever:
- `git push` is rejected with a non-fast-forward error.
- The monitor detects the base branch moved ahead (`git rev-list --count HEAD..origin/main` > 0).
- The PR reports merge conflicts.

#### 6a. Perform the rebase

```bash
git fetch origin main
git rebase origin/main
```

#### 6b. Detect conflicts

```bash
git --no-pager diff --name-only --diff-filter=U
```

#### 6c. Resolve each conflicted file

For each file with conflict markers (`<<<<<<<` / `=======` / `>>>>>>>`):

1. Read the full file including markers.
2. Understand **ours** (this branch's intent) and **theirs** (base-branch changes).
3. Apply the correct semantic merge:
   - Keep **both** sets of changes when independent.
   - Prefer **ours** for new functionality added on this branch.
   - Prefer **theirs** for base-branch fixes/refactors this branch should absorb.
   - If uncertain, prefer the version that makes tests pass — run `<run tests> <relevant path>`.
4. Remove all conflict markers.
5. Stage the resolved file: `git add <file>`.

#### 6d. Continue the rebase

```bash
git rebase --continue
```

If further conflicts appear, repeat §6b–6c until the rebase completes cleanly.

#### 6e. Abort on unresolvable conflicts

If a conflict cannot be resolved confidently (interleaved logic changes in the same
function with unclear intent), abort and escalate:

```bash
git rebase --abort
```

Ping the user: "PR #{pr_id}: rebase on `main` hit an unresolvable conflict in `{file}`.
Manual resolution required."

#### 6f. Push after a successful rebase

```bash
git push origin HEAD --force-with-lease
gh pr merge "$PR_ID" --auto --squash   # re-enable in case the force-push cleared it
```

## Decision Table

| Situation | Action |
|---|---|
| No PR for the branch | Create it (§2), composing the title if more than one commit |
| PR merged | Report success, exit |
| CI running | Sleep 60s, loop back — **do not exit** |
| CI failed | Fix code, push, re-enable auto-merge |
| Active review comments | Fix, reply, resolve |
| Changes requested | Investigate, address, re-request review |
| Base branch moved ahead | Rebase (§6) |
| Merge conflicts | Rebase and resolve (§6) |
| Push rejected (non-fast-forward) | Rebase and force-push (§6) |
| Unresolvable conflict | Abort rebase, ping user |
| Only blocker = human approval | Ping user, **then keep looping** (do not exit) |

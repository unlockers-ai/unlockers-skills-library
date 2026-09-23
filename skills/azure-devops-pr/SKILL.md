---
name: azure-devops-pr
description: >
  USE THIS SKILL for any Azure DevOps pull-request interaction: create a PR; fetch, read, address, or
  reply to PR review comments and threads; resolve a thread; turn review feedback into a
  tracked follow-up work item; or set auto-complete on a PR. Triggers on "fetch pr
  comments", "address pr comments", "reply to review comments", "address review feedback",
  "follow up on that comment", "set auto-complete", "enable auto-complete", "create a PR",
  "open a pull request".
  Azure DevOps only — see the platform note for GitHub and GitLab.
args:
  - name: pr_id
    description: The PR number. If omitted, resolved from the active PR for the current branch.
    required: false
---

# Azure DevOps Pull Requests

Everything this library does against a PR *host* — as opposed to against the code — lives
here: creating the PR, review threads, replies, follow-up work items, and auto-complete.

> **Platform:** Azure DevOps, via the `az` CLI. The workflows generalise but the commands do
> not: GitHub has no thread-status model and no work-item hierarchy, so `follow-up-thread`
> maps to creating a linked issue and resolving the review comment, and `auto-complete-pr`
> maps to `gh pr merge --auto --squash`. Ask an agent to port the scripts — the shapes are
> close and the mapping is mechanical.

## Setup

The scripts read three environment variables. Set them once per repo (direnv, your shell
profile, or a wrapper):

```bash
export AZDO_ORG=your-org             # https://dev.azure.com/<AZDO_ORG>
export AZDO_PROJECT="Your Project"   # spaces are fine
export AZDO_REPO=your-repo
# optional: work-item type created by follow-up-thread (default: Task)
export AZDO_FOLLOWUP_WORK_ITEM_TYPE=Task
```

Requires `az` installed and authenticated (`az login`, plus the `azure-devops` extension)
with access to the project. Every script takes an optional PR id and falls back to the
active PR for the current branch.

## Operations

### Create the PR

```bash
scripts/create-pr.sh [--title "..."] [--description "..."] [--target-branch main] [--work-items "8198 8201"]
```

Push the branch first. Squash merge is set at creation. A work item is linked from a
trailing `-<id>` or `/<id>` in the branch name when none is passed; if there is none, the PR
is created unlinked.

**Compose the title yourself unless the branch is one commit ahead.** The script uses a
single commit's subject, and refuses otherwise — no one commit's subject describes a
multi-commit change. Read `git log origin/<target>..HEAD`, the diff and the linked work
item (`az boards work-item show --id <id>`), then write one title in the project's
commit-message convention: it becomes the squash commit through `auto-complete-pr.sh`.

**Offer, don't impose, a diagram.** For a change whose shape is easier seen than read — a
new control flow, a new interaction between services — offer to sketch a small Mermaid
diagram for the description. Azure DevOps PR descriptions do not render Mermaid, so render
it to PNG (`mmdc`) and attach it rather than pasting the source.

### Read the review threads

```bash
scripts/fetch-pr-comments.sh [pr-id]
```

Returns every thread as JSON. Then:

1. **Filter out the noise.** Drop `commentType == "system"` and bot threads (build status,
   static analysis) unless asked for them. What remains is human review.
2. **Present each thread** with its **thread id** (needed for every reply), author, file
   and line, status, and the comment text.
3. **Group by file** rather than listing chronologically — that is the order the work gets
   done in.

### Reply to a thread, and optionally resolve it

```bash
scripts/reply-to-thread.sh <pr-id> <thread-id> "<reply text>" [status]
```

Status is one of `active`, `fixed`, `wontFix`, `closed`, `byDesign`, `pending`. Omit it to
reply without changing status.

**Only mark a thread `fixed` once the fix is actually committed.** Resolving a thread on the
strength of an intention is how review feedback gets lost.

### Turn feedback into a tracked follow-up

```bash
scripts/follow-up-thread.sh <pr-id> <thread-id> "<title>" "<description>" "<reply>"
```

For valid feedback that should not be done in this PR. Creates a work item as a child of the
PR's linked story, replies with a cross-reference, and resolves the thread. Requires the PR
to have at least one linked work item — the parent is taken from it.

Before running it, prepare the three strings properly:

- **title** — imperative and specific. "Extract the retry policy into a port", not "review comment".
- **description** — enough for someone with no memory of this PR to pick it up: what the
  reviewer observed, which files, and why it was deferred.
- **reply** — acknowledge the point and give the deferral rationale. "Agreed, but it touches
  the scheduler contract and wants its own PR" is a reason; "follow-up created" is not.

This is not a way to close threads you disagree with. If the feedback is wrong, reply and
argue it. If it is right and small, just fix it.

### Set auto-complete

```bash
scripts/auto-complete-pr.sh [pr-id]
```

Squash merge, with the PR title and description as the commit message — so a
conventional-commit PR title produces a conventional-commit merge. Fix the PR title before
running this, not after.

For the full merge lifecycle — push, enable auto-complete, watch CI, fix, escalate — use the
[`merger`](../../agents/merger.md) agent, which drives this skill.

## Notes

- `pullRequestThreadComments` posts a **reply inside** a thread; `az devops invoke` with no
  resource sub-path creates a **new top-level thread** instead. The scripts use the REST
  endpoint directly to avoid the ambiguity.
- Pass JSON bodies via `--body` or a temp file. Heredocs get intercepted by some terminal
  wrappers and fail silently.
- Thread status `2` in the raw REST API is `fixed`.

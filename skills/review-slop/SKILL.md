---
name: review-slop
description: Detect slop in a branch or PR — correct work that should not be in the diff. Verbose comments and docs, duplication across sibling files, ceremony without a threat model, scaffolding shipped as product, checks that must be remembered, and verification sitting in the wrong layer. Use when reviewing a change heavy in docs, config, CI or deploy plumbing, or when asked "what can we cut", "is this too verbose", "review for slop".
args:
  - name: compare_ref
    description: "Branch to review, OR a PR/MR number (default: current branch). When a number is given, the source/target branches are resolved from the git platform."
    required: false
  - name: base_ref
    description: "Base branch to compare against (default: main)"
    required: false
  - name: report_path
    description: "Path the report must be written to, when a caller pins it (default: reviews/slop-review-issues.md)"
    required: false
---

# Slop Review Skill

The lens no other reviewer here applies: code and prose that are **correct** and still
should not be in the diff.

## Reference

[`references/slop-review-guide.md`](references/slop-review-guide.md) — the seven patterns with the
quotes they came from, how to confirm each, and the counter-pressure test. **Read it first,
including the counter-pressure section**; a reviewer that skips it deletes the checks that
catch silent failure.

**Protocol:** [`references/review-protocol.md`](references/review-protocol.md) — arguments, ref resolution, exhaustiveness, severity levels, report shape. Read it first.
Its § 4 *Be exhaustive* is mandatory; the lens steps it refers to are steps 3–4 (*Apply the slop lens*, *Apply the counter-pressure*) below.

[`references/accidental-complexity-guide.md`](references/accidental-complexity-guide.md) is a
different axis (smells inside domain code). Where a finding is really about a missing value
object or a defensive null check, it belongs to `review-complexity`, not here.

## Process

1. **Resolve refs and gather the diff** — per [`review-protocol.md`](references/review-protocol.md).
   Read the commit messages too: a war story already in one does not also belong in a
   comment.

2. **Look outside the diff before judging it.** This lens depends on protocol § 4 more
   than the others do: three of the seven patterns — duplication across siblings,
   verification in the wrong layer, more than one source of truth — name a change
   *outside* the diff, so a diff-only pass finds none of them. Read the whole of every new
   file, and find the siblings that have no hunk at all.

3. **Apply the slop lens**, per pattern:

   - **Prose that isn't ours** — for each comment block and doc paragraph: is it in the
     tool's own documentation, in the line below it, or in the commit message? Judge by
     *category remaining*, never by lines removed.
   - **Checks that can't fire, or must be remembered** — for each assertion, name the
     runtime state that trips it. For each check, name what invokes it; if the answer is
     "a human who remembers", say so.
   - **Verification in the wrong layer** — for anything CI does in shell, ask whether the
     Makefile, a check script or the deploy tool already does it, and whether a laptop can
     run it.
   - **More than one source of truth** — for each new secret or pipeline variable, what
     does it authorise, and is the value already committed? For each fact added to the
     agent entry file (`CLAUDE.md`, `AGENTS.md`), is it also in `docs/`?
   - **Duplication across siblings** — for each new file, find the file it was copied
     from and diff them. For each repeated block or name-set, grep it and count the files.
     Then enumerate the rest of that family: a block duplicated into four of five siblings
     is the same finding as one omitted from the fifth.
   - **Scaffolding kept as product** — for each new script or module, who runs it after
     this branch lands?
   - **Over-claiming** — for each confident claim in prose or in a commit message, run it
     if it can be run, and quote the result.

4. **Apply the counter-pressure before writing any finding that removes a check.** State
   what still catches the failure. If nothing does, it is not a finding.

5. **Confirm § 4 of the protocol is satisfied**, then **generate report** → `reviews/slop-review-issues.md`

## Severity Model

| Severity | Indicators |
|----------|------------|
| Critical | A second source of truth for a value that must not drift; a check that gives false assurance (opt-in, or structurally dead); a claim asserted as fact that is inference |
| Major | Verification in a layer only CI can run; scaffolding shipped as product; a block, file or name-set duplicated across siblings |
| Minor | Comments and docs restating public documentation, the code, or the commit message |

## Exclusions

- Smells inside domain code — those are `review-complexity`.
- Style and formatting — owned by the linters.
- "This is verbose" with no named cost. Every finding names what the next maintainer pays.
- Whether content belongs in this repo at all. A runbook for a system the repo does not
  build may well be in the wrong place, but that is an ownership call for the people who
  own the work, not a defect a diff reviewer should rule on.

## Output Format

Per [`review-protocol.md`](references/review-protocol.md) § 6, with two additions — every
finding names the cost of keeping it, and every finding that removes a check names what
still catches the failure:

```markdown
### 1. Title
**Location:** path/to/file:123
**Pattern:** one of the seven
**Issue:** what is there that should not be
**Cost of keeping it:** what the next maintainer pays — drift, false assurance, a second
path to maintain. Not "it is verbose".
**Still caught by:** (checks only) what fails if this goes. "Nothing" means keep it.
**Suggestion:** the specific deletion or move
**Reference:** a file in this repo that already does it right, if there is one
```

The summary paragraph says what the change carries that it does not need, and what that
costs.

## When to run it

On a diff heavy in docs, config, CI or deploy plumbing — where the other lenses have little
to say. On a code-only change it usually reports nothing, which is a correct result, not a
reason to invent findings.

## Example Usage

```
review-slop                # Current branch vs main
review-slop feat/foo       # Specific branch
review-slop feat/foo dev   # Different base
review-slop 30             # PR/MR by number
```

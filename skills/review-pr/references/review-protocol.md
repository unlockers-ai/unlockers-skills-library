<!-- Generated from docs/review-protocol.md by tools/sync-references.py. Edit the source, not this copy. -->

# Review Protocol

Every `review-*` skill in this library shares one invocation contract, one severity
vocabulary, and one report shape. Each skill documents only its own **lens** — what it
looks for — and points here for the rest.

## Arguments

| Argument | Meaning |
|----------|---------|
| `compare_ref` | Branch to review, **or** a PR/MR number. Default: current branch. |
| `base_ref` | Branch to compare against. Default: `main`. |
| `report_path` | Where the report must be written, when a caller — a CI job, an orchestrating agent — pins it. Default: see § 6. |

## 1. Resolve refs

If `compare_ref` is a number, it is a PR/MR ID — resolve its source and target branches
from the hosting platform:

```bash
# GitHub
gh pr view <ID> --json headRefName,baseRefName

# GitLab
glab mr view <ID>

# Azure DevOps  (strip the refs/heads/ prefix from both)
az repos pr show --id <ID> --query "{source: sourceRefName, target: targetRefName}" -o json
```

Then `git fetch origin <source>`. Otherwise use `compare_ref` (or the current branch) and
`base_ref` (or `main`) as given.

## 2. Gather the diff

```bash
git log --oneline {base}..{compare}      # what the author was doing
git diff {base}...{compare} --stat       # shape and size
git diff {base}...{compare} --name-only  # files to classify
git diff {base}...{compare}              # the review surface
```

Use three dots. `{base}...{compare}` diffs against the merge base, so unrelated commits
that landed on `base` since the branch started do not appear as changes.

`--stat` is file-level, so it cannot show a long function added whole inside a short diff.
List the longest function added or changed in the diff, by line count — `review-complexity`
checks it against [`code-design-rules.md`](code-design-rules.md) rule 4.

## 3. Read enough surrounding code

A diff alone cannot tell you whether a change fits. Before judging any file, read one or
two sibling modules in the same directory and the package's entry point. Reviews that skip
this produce findings that are locally reasonable and wrong in context.

## 4. Be exhaustive

Both halves below are mandatory. Measured on a fixed ground truth, a reviewer without them
found 2 of 20 known issues across 5 runs; with them, 7 of 12 across 3 runs. The failure
mode is not ignorance — it is satisficing. Left to its own judgement the model reports the
first plausible finding and stops, so issues surface only on the run *after* the previous
ones were fixed.

Each skill names its **lens steps** — the steps of its process that enumerate what to look
for. Those are what "every item" below refers to.

**Enumerate; do not satisfice.**

- There is no cap on findings. One issue is not "done". The review is done when every
  item of the skill's lens steps has been evaluated against **every** changed hunk and the
  outcome of each evaluation is known.
- Do not stop at the first or most interesting finding, and never write "and similar
  issues elsewhere" — list every occurrence with its own location.
- Before writing the report, restate the changed files and confirm each was opened. A
  file you did not read cannot be reported as clean.
- Never claim something was "applied consistently across all N" unless you have opened
  all N and can name them. Unverified consistency claims are the largest single source of
  missed findings: verify, or say nothing.

**Read whole files — and the files missing from the diff.**

- The diff is the entry point, not the evidence. For each changed file, read the **full
  file**, not just the hunk. § 3 is the floor, not the ceiling.
- When a change touches one member of a family of siblings — skills, adapters, docs,
  config entries, test modules — search out the whole family and check every member,
  **including members with no hunk in the diff**. An omitted sibling emits no diff line
  and is invisible to a diff-only review, yet is one of the most common real defects.
- Same for callers: search the repo for every modified public symbol and check each call
  site, not only those the diff happened to touch.
- Use whatever search your toolset makes best — a code-intelligence or symbol index where
  you have one, otherwise glob/grep. Completeness of the enumeration is what counts, not
  which tool produced it.

Exhaustive is not the same as finding something. Once every lens item has been evaluated
and none survives confirmation, the empty report is the right one.

## 5. Severity

The same three levels everywhere. Each skill's own table says what fills them.

| Severity | Meaning |
|----------|---------|
| **Critical** | Broken, exploitable, or violates an explicit project rule. Blocks merge. |
| **Major** | Real cost that will be paid later. Fix before merge, or file a follow-up. |
| **Minor** | Worth fixing, blocks nothing. |

## 6. Report

Each skill writes a Markdown file under `reviews/` (`reviews/code-review-issues.md`,
`reviews/security-review-issues.md`, …) — create the directory if it does not exist — or to
`report_path` when one is given. The review is complete only when that file exists:
printing the report in chat, or saving it anywhere else, does not count. A caller that
collects reports from a fixed location has nothing to collect otherwise.

**Keep `reviews/` out of git.** A report is about one commit and is wrong about the branch
the moment it moves; a committed one is read as current documentation of the subsystem and
nothing updates it. Untracked, it still works with no PR open, on any host, before a push.

**Pin the commit, and anchor every finding.** The report opens with the SHAs it analysed,
and every finding carries `path:line` valid at the compare SHA:

```markdown
# <Lens> Review: <compare ref>

**Compare:** <sha> (<ref>)  ·  **Base:** <sha> (<ref>)  ·  **Merge base:** <sha>
```

That keeps the report a superset of a PR review rather than an alternative to one: posting
the findings as line comments is a second step someone can take later, from the report, and
it needs the SHA and the line to do it. Writing straight to a PR instead would tie the
output to a PR that has to exist already.

Every finding carries:

```markdown
### 1. Title
**Location:** path/to/file:123
**Issue:** what is wrong — one or two sentences
**Why it matters:** the concrete consequence, not a restatement of the rule
**Suggestion:** a specific edit, not "consider refactoring"
**Reference:** an existing file in the repo that already does it right, if there is one
```

A finding that names something *outside* the diff has no line to anchor to — cite the file
it is about and say so.

Close with a summary line: `X Critical, Y Major, Z Minor` and a one-paragraph verdict.

## Rules that apply to every reviewer

- **Report findings, do not fix them.** These skills are read-only. Fixing is a separate,
  explicitly-requested step.
- **Confirm before reporting.** A search hit is a candidate. Read the code around it and
  discard the ones that do not survive.
- **No finding without a consequence.** If you cannot state what breaks or what it costs,
  it is not a finding.
- **Cite a reference where one exists.** "Do it like `path/to/other.py:45`" is worth more
  than a paragraph of principle.
- **Say when the answer is nothing.** An empty report is a valid, useful outcome.
- **Reach for a tool before a script.** Linters and analysers (`ruff`, `pylint`, `radon`,
  `lizard`, `jscpd`, `vulture`, CodeScene, or your language's equivalents) have rules more
  precise than an AST walker written mid-review — a private attribute is still an
  attribute; `async def` is still a method. The map from smell to tool and rule code is in
  [`accidental-complexity-guide.md` § Tools That Measure These](accidental-complexity-guide.md#tools-that-measure-these).
  Tool numbers inform a finding and its trade-off; they never decide it, and a finding
  quotes which tool and threshold it leaned on. Hand-roll only what no tool measures.

## The reviewers

| Skill | Lens | Report |
|-------|------|--------|
| [`review-pr`](../../review-pr/SKILL.md) | Catch-all: bugs, design, security, coverage in one pass | `reviews/code-review-issues.md` |
| [`review-complexity`](../../review-complexity/SKILL.md) | Accidental complexity | `reviews/complexity-review-issues.md` |
| [`review-testing`](../../review-testing/SKILL.md) | Test quality and coverage | `reviews/testing-review-issues.md` |
| [`review-architecture`](../../review-architecture/SKILL.md) | Boundaries, seams, dependency direction | `reviews/architecture-review-issues.md` |
| [`review-security`](../../review-security/SKILL.md) | Secrets, injection, authz, crypto, deps | `reviews/security-review-issues.md` |
| [`review-impact`](../../review-impact/SKILL.md) | Blast radius; which suites must pass | `reviews/impact-analysis.md` |
| [`review-slop`](../../review-slop/SKILL.md) | Correct work that shouldn't be in the diff: verbosity, duplication, ceremony, misplaced checks | `reviews/slop-review-issues.md` |

**Which to run:** `review-pr` alone for a small change. For anything substantial, the
focused passes find more than the catch-all does — they are cheap to run in parallel.
`review-impact` is the one to run *before* pushing rather than after. `review-slop` earns
its place on a diff heavy in docs, config, CI or deploy plumbing, where the other lenses
have little to say.

What no reviewer here can see is a consequence outside the diff that nobody touched —
[`review-drift`](../../review-drift/SKILL.md) runs after merges for that, and does not
use this protocol.

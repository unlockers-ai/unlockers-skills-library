---
name: review-testing
description: Review PR/MR changes for test quality and coverage against project testing standards. Use when reviewing a branch or pull request for whether its tests are well-written and cover the new code.
args:
  - name: compare_ref
    description: "Branch to review, OR a PR/MR number (default: current branch). When a number is given, the source/target branches are resolved from the git platform."
    required: false
  - name: base_ref
    description: "Base branch to compare against (default: main)"
    required: false
  - name: report_path
    description: "Path the report must be written to, when a caller pins it (default: reviews/testing-review-issues.md)"
    required: false
---

# Testing Review Skill

Reviews PR changes to ensure tests meet project standards. Focus: does this PR maintain or
improve our testing quality?

**Rules:** [`references/testing-rules.md`](references/testing-rules.md) —
**Reviewer tips:** [`references/testing-review-guide.md`](references/testing-review-guide.md)

**Protocol:** [`references/review-protocol.md`](references/review-protocol.md) — arguments, ref resolution, exhaustiveness, severity levels, report shape. Read it first.
Its § 4 *Be exhaustive* is mandatory; the lens steps it refers to are steps 3–5 (*Review test files*, *Review coverage*, *Check bug-fix discipline*) below.

## Process

1. **Resolve refs and gather the diff** — per [`review-protocol.md`](references/review-protocol.md).

2. **Split the diff** into (a) new/modified test files, (b) new/modified production code.

3. **Review test files** — check each against the criteria in the guide:
   - No mocks — No fixed sleeps — Naming convention — Parametrize/table-drive appropriately
   - Assert whole objects — No trivial tests — Short with clear intent.

4. **Review coverage** — for each production file:
   - Identify public functions/methods/classes added or modified.
   - Check whether corresponding test coverage exists.
   - Flag untested code paths.

5. **Check bug-fix discipline**
   - If the PR is a bug fix, verify a failing test was added (fails without the fix, passes
     with it).

6. **Confirm § 4 of the protocol is satisfied**, then **generate report** → `reviews/testing-review-issues.md`

## Output Format

```markdown
# Testing Review: {branch-name}

**Compare:** {sha} ({ref})  ·  **Base:** {sha} ({ref})  ·  **Merge base:** {sha}

## Critical
### {N}. {title}
**Location:** {test_file}:{line}
**Issue:** …

## Major
### {N}. {title}
…

### Missing coverage

| Production File | Untested Code |
|-----------------|---------------|
| path/to/file    | `function_name()`, `ClassName.method()` |

## Minor
…

## Positive Observations
- {What was done well}

## Summary
{X} Critical, {Y} Major, {Z} Minor — overall assessment
```

Severity, per the protocol: **Critical** — a test that cannot fail, reaches the network,
or asserts nothing about the change; **Major** — a rule of
[`testing-rules.md`](references/testing-rules.md) broken, or a changed code path with no
test when that path carries a business rule, a security guard or error handling that
keeps or loses user data; **Minor** — naming, size or structure, and any other untested
branch or surviving mutation. Without this bar the testing lens found new Majors on every
one of nine rounds of one PR: there is always one more thing that could be pinned.

## Example Usage

```
review-testing              # Current branch vs main
review-testing feat/foo     # Specific branch
review-testing feat/foo dev # Different base
review-testing 3574         # PR/MR by number
```

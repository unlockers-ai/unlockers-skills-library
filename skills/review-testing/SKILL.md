---
name: review-testing
description: Review PR/MR changes for test quality and coverage against project testing standards. Use when reviewing a branch or pull request for whether its tests are well-written and cover the new code.
args:
  - name: compare_ref
    description: "Branch to review, OR a PR/MR number (default: current branch). When a number is given, the source/target branches are resolved from the git platform."
    required: false
  - name: base_ref
    description: Base branch to compare against (default: main)
    required: false
  - name: report_path
    description: "Path the report must be written to, when a caller pins it (default: reviews/testing-review-issues.md)"
    required: false
---

# Testing Review Skill

Reviews PR changes to ensure tests meet project standards. Focus: does this PR maintain or
improve our testing quality?

**Rules:** [`docs/testing-rules.md`](../../docs/testing-rules.md) —
**Reviewer tips:** [`docs/testing-review-guide.md`](../../docs/testing-review-guide.md)

**Protocol:** [`docs/review-protocol.md`](../../docs/review-protocol.md) — arguments, ref resolution, exhaustiveness, severity levels, report shape. Read it first.
Its § 4 *Be exhaustive* is mandatory; the lens steps it refers to are steps 3–5 (*Review test files*, *Review coverage*, *Check bug-fix discipline*) below.

## Process

1. **Resolve refs and gather the diff** — per [`review-protocol.md`](../../docs/review-protocol.md).

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

## Violations

### {test_file}
- **Line {N}**: {violation description}

## Missing Coverage

| Production File | Untested Code |
|-----------------|---------------|
| path/to/file    | `function_name()`, `ClassName.method()` |

## Positive Observations
- {What was done well}

## Summary
- {X} violations found
- {Y} untested code paths
- Overall assessment
```

## Example Usage

```
review-testing              # Current branch vs main
review-testing feat/foo     # Specific branch
review-testing feat/foo dev # Different base
review-testing 3574         # PR/MR by number
```

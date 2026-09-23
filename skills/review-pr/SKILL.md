---
name: review-pr
description: Perform a comprehensive code review of branch or pull-request changes — bugs, design, security, test coverage. Use when you want a broad review rather than the focused testing/complexity passes.
args:
  - name: compare_ref
    description: "Branch to review, OR a PR/MR number (default: current branch). When a number is given, the source/target branches are resolved from the git platform."
    required: false
  - name: base_ref
    description: Base branch to compare against (default: main)
    required: false
  - name: report_path
    description: "Path the report must be written to, when a caller pins it (default: reviews/code-review-issues.md)"
    required: false
---

# Code Review Skill

Performs a comprehensive AI-powered code review of changes between refs. For deeper focused
passes, also run [`review-complexity`](../review-complexity/SKILL.md) and
[`review-testing`](../review-testing/SKILL.md).

**Protocol:** [`docs/review-protocol.md`](../../docs/review-protocol.md) — arguments, ref resolution, exhaustiveness, severity levels, report shape. Read it first.
Its § 4 *Be exhaustive* is mandatory; the lens steps it refers to are step 2 (*Analyze changes*) below.

**Standards to review against**, so a finding cites a rule rather than a preference:
[`code-design-rules.md`](../../docs/code-design-rules.md) (types and exceptions),
[`hexagonal-architecture-rules.md`](../../docs/hexagonal-architecture-rules.md) (where code
goes — only where the codebase is actually hexagonal), [`testing-rules.md`](../../docs/testing-rules.md)
(what a test must look like), and the project's conventions doc for what it has already
decided on purpose.

## Process

1. **Resolve refs and gather the diff** — per [`review-protocol.md`](../../docs/review-protocol.md).

2. **Analyze changes**
   - Review all modified files for bugs, design issues, and quality problems.
   - Evaluate test coverage, identify security concerns, assess architectural decisions.

3. **Categorize issues by severity** (Critical / Major / Minor — see criteria below).

4. **Confirm § 4 of the protocol is satisfied**, then **generate report** → `reviews/code-review-issues.md` with file locations, line numbers, clear
   problem descriptions, concrete fixes, and summary statistics.

## Review Criteria

### Critical Issues
- Logic errors and incorrect implementations
- Security vulnerabilities
- Breaking changes
- Missing error handling for critical paths
- Race conditions or concurrency bugs
- Resource leaks

### Major Issues
- Architecture violations (layering, dependency direction)
- Tight coupling between modules
- Missing abstractions
- Incomplete implementations
- Significant performance concerns
- Poor error-handling patterns

### Minor Issues
- Code duplication
- Dead code
- Inconsistent naming or patterns
- Test quality (missing tests, weak assertions)
- Missing documentation for complex logic
- Minor performance optimizations

## Exclusions

- Style/formatting (assumed handled by linters)
- Personal preferences without technical merit
- Issues already flagged by automated tools

## Output Format

```markdown
# Code Review Issues: branch-name

## Critical Issues
### 1. Title
**Location:** path/to/file:123
**Issue:** Clear description
**Fix:** Concrete suggestion

## Major Issues
...

## Minor Issues
...

## Summary
- X Critical, Y Major, Z Minor issues
- Overall assessment and recommendations
```

## Example Usage

```
review-pr              # Current branch vs main
review-pr feat/foo     # Specific branch
review-pr feat/foo dev # Different base
review-pr 3574         # PR/MR by number
```

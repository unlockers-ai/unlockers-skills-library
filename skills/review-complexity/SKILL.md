---
name: review-complexity
description: Detect accidental complexity in code changes — unnecessary code that doesn't serve the domain problem. Use when reviewing a branch or pull request for over-engineering, defensive null checks, redundant exception handling, and similar smells.
args:
  - name: compare_ref
    description: "Branch to review, OR a PR/MR number (default: current branch). When a number is given, the source/target branches are resolved from the git platform."
    required: false
  - name: base_ref
    description: Base branch to compare against (default: main)
    required: false
  - name: report_path
    description: "Path the report must be written to, when a caller pins it (default: reviews/complexity-review-issues.md)"
    required: false
---

# Accidental Complexity Review Skill

Specialized code review focused on **accidental complexity** — unnecessary code that
doesn't serve the domain problem.

## Reference

See [`docs/accidental-complexity-guide.md`](../../docs/accidental-complexity-guide.md) for
the full smell catalogue with examples, detection heuristics, and the linter rules that
measure each smell, and [`docs/code-design-rules.md`](../../docs/code-design-rules.md) for
the shape a suggestion should point at — a missing value object or a missing
behaviour-bearing type is behind more of these smells than any other single cause.

**Protocol:** [`docs/review-protocol.md`](../../docs/review-protocol.md) — arguments, ref resolution, exhaustiveness, severity levels, report shape. Read it first.
Its § 4 *Be exhaustive* is mandatory; the lens steps it refers to are steps 2–3 (*Apply the complexity lens*, *Challenge each finding*) below.

## Process

1. **Resolve refs and gather the diff** — per [`review-protocol.md`](../../docs/review-protocol.md).

2. **Apply the complexity lens** — for each changed file, hunt for:

   **Critical** (design holes):
   - Null/None checks inside domain logic
   - Emptiness guards on collections before an operation that should already be a safe
     no-op on empty — no reliable search exists for these, so reason about every
     conditional whose subject is a collection (see the guide, 1.4)
   - Optional arguments that are never actually null
   - Defensive programming hiding broken contracts

   **Major** (structural complexity):
   - Multi-layer exception handling (adapter + service + caller all catching)
   - Boolean flag parameters that split behaviour
   - Always-null optional arguments
   - Emptiness guards around already-safe collection operations
   - Middle-man classes that just delegate
   - God objects / classes doing too much — linters and CodeScene for the screen, then the
     method × attribute matrix (guide §10) for what is inside;
     [`scripts/class_cohesion.py`](scripts/class_cohesion.py) computes it for Python
   - Long functions — the longest function the protocol's § 2 listed, against
     [`code-design-rules.md`](../../docs/code-design-rules.md) rule 4

   **Minor** (code smells):
   - Long parameter lists (>4 params)
   - Speculative generality (YAGNI violations)
   - Unnecessary class/state (could be a function)
   - Primitive obsession / data clumps
   - Nested conditionals (arrow anti-pattern)

3. **Challenge each finding:**
   - Can this be removed entirely?
   - Can complexity be pushed elsewhere (up the stack, into an adapter)?
   - Is there a simpler design that eliminates the need?

4. **Confirm § 4 of the protocol is satisfied**, then **generate report** → `reviews/complexity-review-issues.md`

## Severity Model

| Severity | Indicators |
|----------|------------|
| Critical | Null checks in domain logic, emptiness guards before operations already safe on empty, optional params never used as null, exception handling masking design flaws |
| Major | Multi-layer try/catch, boolean flags splitting behaviour, unnecessary delegation, feature envy |
| Minor | Long param lists, speculative generality, unnecessary state, primitive obsession |

## Output Format

```markdown
# Accidental Complexity Review: {branch-name}

## Critical Issues
### 1. Title
**Location:** path/to/file:123
**Smell:** name of the pattern
**Why it matters:** brief explanation of the hidden cost
**Suggestion:** concrete refactor to eliminate the complexity

## Major Issues
...

## Minor Issues
...

## Summary
- X Critical, Y Major, Z Minor issues
- Overall complexity health assessment
```

## Example Usage

```
review-complexity              # Current branch vs main
review-complexity feat/foo     # Specific branch
review-complexity feat/foo dev # Different base
review-complexity 3574         # PR/MR by number
```

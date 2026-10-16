---
name: bugszero-root-cause
description: Fix a bug by removing the design weakness that allowed it, not just the failing behaviour. Use when a bug is the second of its kind, when the obvious fix is another defensive check, or whenever a fix should prevent the whole family.
argument-hint: [bug-description]
---

# BugsZero Root-Cause Fix

Treats a bug as evidence of a design weakness. The fix is not complete when the symptom
stops; it is complete when the same *family* of defect has become hard to write.

**Method:** [`references/bugszero-root-cause.md`](references/bugszero-root-cause.md) — read it
first, including the bug-pattern catalogue it links to.

## Relationship to the ordinary bug workflow

[`bugfix-workflow.md`](references/bugfix-workflow.md) is the default: reproduce with a
failing test, fix, confirm. This skill is what you run when that is not enough — when the
bug is the second of its kind, when the natural fix is another guard clause, or when the
reproduction was hard to write because the code offers nowhere to stand. It replaces the
"fix" step with a structural change; the test-first discipline still applies.

## Input

- The failing behaviour: `{bug-description}`. If omitted, infer it from the current task or
  the failing test.
- The affected code path and a known reproduction.

## Process

1. **Characterize the failure.** Reproduce it. State actual versus expected. Then widen:
   what is the *family* of inputs or states that could fail the same way? Fixing one member
   of a family is the thing this skill exists to prevent.

2. **Find the enabling weakness.** Not "what line is wrong" but "what design choice made
   this easy to write and hard to notice?" Match it to a known pattern where you can —
   hidden testable code, index arithmetic, unconstrained construction, temporal coupling,
   primitive obsession, a null used as a flag, validation that happens too late.

3. **Design the prevention constraint.** Prefer constraints that make the mistake
   unwriteable — types, constructor invariants, a boundary that no longer admits the bad
   state, an ordering the API enforces — over checks that catch it at runtime. A new
   defensive `if` is usually a sign that step 2 has not finished.

4. **Refactor structurally.** The smallest coherent change that removes the cause. If it is
   large, say so and agree the scope before starting rather than half-applying it.

5. **Prove the new invariant.** A test for the original bug, and a test that asserts the
   constraint itself — the one that would fail if someone removed the guarantee later.

## Gates before completion

- The reported bug is fixed.
- The design weakness has been changed, not bypassed.
- Reintroducing the same family of defect is now materially harder.
- Tests assert the new invariant, not just the old symptom.

## Output

- The failure characterization: reproduction, expected versus actual, and the family.
- The bug pattern identified, and how it allowed this bug.
- The prevention constraint, and the structural change made.
- The tests added, and which invariant each one pins.

If the structural fix is too large for the current change, say so explicitly: apply the
narrow fix, name the weakness in the PR description, and file the follow-up. An unstated
compromise is how the family survives.

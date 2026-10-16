---
name: scope-challenge
description: Capture a feature request as a very short PRD, then challenge it for the smallest valuable scope before implementing. Use on every functional or feature request — "add X", "we need Y", "build Z" — not only when the user asks to simplify, cut scope, or reduce the MVP.
---

# Scope Challenge

A small codebase is always easier to change than a large one. Every functional request is
therefore challenged on its simplicity **before** implementation, not after.

This runs at the front of [`docs/feature-workflow.md`](../../docs/feature-workflow.md): it
questions *what* is being built, then hands the agreed scope to the workflow, whose step 2
slices *how* it gets delivered. Challenge the scope first — slicing a request that should
have been half its size just produces more slices.

## Steps

1. **Capture a very short PRD** as an artefact of the session: the need, in a handful of
   lines, in domain terms. No implementation detail. If it does not fit on a screen, it is
   describing a solution rather than a need.

2. **Look for a higher-value subset**, along one or more of these axes:

   - **Shrink the problem.** Is a subset of the functional cases enough for the next step?
   - **Shrink the population.** Is a subset of the users enough — one team, one tenant, one
     region — with the rest following once it has proved out?
   - **Hand the edge case back to a human.** Can a rare case be left to fail explicitly,
     with a clear exception, instead of building the logic that handles it? An edge case
     that occurs twice a year rarely repays the branch that handles it, and the branch is
     never exercised.

3. **Offer the user several scope reductions**, each with its trade-off, and let them
   choose. Do not pick for them, and do not proceed to implementation on your own reading —
   the point of the exercise is the decision, not the recommendation.

4. **Update the PRD to the agreed scope.** It stays very short.

## When to Stop

Say so when the request is already minimal. A request that cannot usefully be cut is the
normal case for a bug fix, a one-rule change, or a slice the user has already narrowed —
report that in a line and move on. Manufacturing three options for a two-hour change wastes
more than it saves.

## Why

- It makes the next step to implement unambiguous, which is most of what a small scope buys.
- The short, current PRD makes any gap between the need and the implementation visible —
  which is what a later [`review-complexity`](../review-complexity/SKILL.md) pass needs in
  order to call code accidental rather than merely unfamiliar.

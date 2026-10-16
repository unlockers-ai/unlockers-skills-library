---
name: legacy-3p
description: Change legacy code in three ordered phases — Protect with characterization tests, Prepare by refactoring for the change, Produce the feature with TDD. Use when adding a feature to untested or badly-structured code, or when the honest answer to "can I test this?" is no.
argument-hint: [change-description]
---

# Legacy 3P — Protect, Prepare, Produce

A sequencing strategy for changing legacy code. The order is the whole method: safety
first, then design, then the feature. Skipping ahead is how legacy code stays legacy.

**Method:** [`references/3p-protect-prepare-produce.md`](references/3p-protect-prepare-produce.md) — read it first.

## When this applies

Use it when [`feature-workflow.md`](references/feature-workflow.md) cannot start — the code
has no tests, or has tests that would not catch a regression, or is shaped so the feature
has nowhere to go. If the area is already well covered and well factored, use the ordinary
workflow; 3P is for the case where writing the first test is itself the hard part.

## The three phases

**1. Protect** — build a safety net over everything the change might affect.

Quick-and-dirty is correct here: characterization tests, approval tests, snapshot tests, at
whatever level they can be written cheaply. Coverage of the change surface is the only goal.
Readability, speed, elegance and long-term maintainability are explicitly *not* goals in
this phase, and reviewing these tests against the usual standard is a category error —
they are scaffolding and most will be deleted in Prepare.

The exit condition is a feeling worth taking seriously: you can refactor aggressively
without fear.

**2. Prepare** — refactor until the feature becomes easy to add.

Behaviour does not change here. Remove the structural obstacles, separate business rules
from framework and infrastructure, make dependencies explicit, create the seams. As real
seams appear, replace the coarse Protect tests with focused ones and delete what is no
longer earning its place.

Exit condition: adding the feature with ordinary TDD now feels like the code was built that
way from the start.

**3. Produce** — write the feature, test-first, on the prepared design.

Keep only the high-level tests that cover wiring and critical end-to-end paths.

## Process

1. **Scope the change surface.** Which code paths and side effects could this touch? That
   set, not the whole file, is what Protect must cover.
2. **Protect.** Write the characterization tests. Run them against unmodified code and
   confirm they pass — a characterization test that fails on day one is describing
   something other than current behaviour.
3. **Verify the net.** Deliberately break something small and confirm a test catches it. An
   unverified safety net is a belief, not a net.
4. **Prepare.** Refactor in small steps, running the net after each. Behaviour must not
   change; if a Protect test fails, the refactor was wrong, not the test.
5. **Produce.** TDD the feature.
6. **Report which phase you are in.** The phases have different standards, and a reviewer
   who thinks they are looking at Produce tests when they are looking at Protect tests will
   give the wrong feedback.

## Why the order pays

The developer making the change gets the benefit of the testing and refactoring investment
immediately, in this change, rather than banking it for a successor who may never arrive.
That is what makes the investment defensible under delivery pressure — and it is the
argument to make when someone proposes going straight to Produce.

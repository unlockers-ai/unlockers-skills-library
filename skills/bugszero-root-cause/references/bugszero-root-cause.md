<!-- Generated from docs/bugszero-root-cause.md by tools/sync-references.py. Edit the source, not this copy. -->

# BugsZero Root-Cause Bug Fixing (Arlo Belshee + Johan Martinsson)

BugsZero treats bugs as largely preventable outcomes of design and workflow choices.
The objective is not only to fix the observed failure, but to remove the conditions that made that failure likely.

## Core idea
- Patch-level fixes are incomplete when the same defect family can easily reappear.
- Root-cause fixing means changing structure so a class of mistakes becomes hard or impossible.
- Most recurring bug sources can be recognized as design anti-patterns and addressed with prevention patterns.

## Root-cause bug-fix loop
1. **Characterize the failure**
   - Capture observed behavior and triggering scenario.
   - Define the broader defect family, not just the single input that failed.
2. **Find the enabling weakness**
   - Identify what design choice made this bug easy to introduce.
   - Map it to a known bug pattern if possible.
3. **Design a prevention constraint**
   - Prefer constraints in types, constructors, boundaries, and sequencing over late defensive checks.
4. **Refactor structurally**
   - Apply the smallest structural change that blocks recurrence of the defect family.
5. **Prove the new invariant**
   - Add focused tests around the new invariant and boundaries.

## Frequent bug patterns and prevention moves
- **Hidden testable code** → extract pure function from orchestration and test it thoroughly.
- **Use of indices** → prefer higher-order operations/for-each, or encapsulate index + collection logic.
- **Non-constrained construction** → require mandatory constructor args, validate in constructor, use factory/builder/type-safe params.
- **Primitive obsession / exposed internals / temporal coupling / null flag / late validation** → encode domain constraints explicitly and reduce accidental complexity.

## Done criteria for a “BugsZero-quality” fix
- The bug is fixed in behavior.
- The design weakness that enabled the bug has been addressed.
- It is materially harder to reintroduce the same defect family.
- Tests assert the new safety boundary/invariant.

## References
- Arlo Belshee #Bug Zero session: https://agile-israel-2017.events.co.il/presentations/4713-bug-zero
- BugsZero Kata repo: https://github.com/martinsson/BugsZero-Kata
- Kata instructions: https://github.com/martinsson/BugsZero-Kata/blob/master/instructions-intermediate.md
- Bug patterns list: https://github.com/martinsson/BugsZero-Kata/blob/master/bug-patterns.md
- Hidden testable code: https://martinsson-johan.blogspot.com/2018/04/bug-pattern-hidden-testable-code.html
- Use of indices: https://martinsson-johan.blogspot.com/2018/05/bug-generator-use-of-indices.html
- Non-constrained construction: https://martinsson-johan.blogspot.com/2018/05/bug-generator-non-constrained.html
- Design away bugs / poka-yoke framing: https://martinsson-johan.blogspot.com/2016/06/its-not-configuration-issue-its-design.html

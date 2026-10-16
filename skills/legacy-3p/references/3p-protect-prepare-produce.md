<!-- Generated from docs/3p-protect-prepare-produce.md by tools/sync-references.py. Edit the source, not this copy. -->

# 3P Protect-Prepare-Produce (Johan Martinsson) — Methodology Notes

3P is a legacy-code change strategy that maximizes short-term ROI by sequencing work as **Protect → Prepare → Produce**.
Instead of postponing tests/refactoring, it front-loads safety and design work so feature delivery is faster and safer.

## Protect (goal: fearless refactoring safety net)
- Scope: all code paths and side effects in the area that will be changed.
- Requirement: complete coverage of the change surface; if behavior can change, it must be asserted.
- Intention: developer should be able to refactor aggressively without worrying about introducing bugs.
- Preferred style: quick-and-dirty characterization tests, approval tests, or snapshot tests at a high level.
- Ordinary long-term test quality rules are secondary here (maintainability, elegance, readability, speed, portability).
- What matters most now: behavioral coverage and regression detection for upcoming refactoring.

## Prepare (goal: make feature addition easy and traditionally testable)
- Refactor deeply to remove structural obstacles to the new feature.
- Isolate business rules from framework/infrastructure concerns and make dependencies explicit.
- Create seams and testable design so core behavior can be verified with focused unit/integration tests.
- Replace or pull down fragile high-level protection tests where appropriate.
- Exit criterion: adding the feature with incremental TDD feels straightforward, as if this code had been built with TDD from the start.

## Produce (goal: implement new behavior cleanly)
- Implement the feature with TDD on the prepared design.
- Keep only the high-level tests needed for wiring and critical end-to-end behavior.
- Deliver with lower risk, faster feedback, and less long-term design debt.

## Core rationale
- The same developer gets the benefit of testing/refactoring investment immediately.
- Time between investment and payoff is minimized, improving decision quality and motivation.
- Quick-and-dirty tests are tactical and temporary: Protect optimizes safety, Prepare restores long-term test quality.

## References
- Method overview: https://martinsson-johan.blogspot.com/2022/11/breaking-out-of-legacy-with-3p.html
- Quick and dirty tests context: https://martinsson-johan.blogspot.com/2023/04/quick-and-dirty-tests-ftw.html
- SpeakerDeck (TechExcellence): https://speakerdeck.com/martinsson/getting-out-of-legacy-with-3p-protect-prepare-produce-techexcellence-meetup
- SpeakerDeck (BreizCamp): https://speakerdeck.com/martinsson/3p-protect-prepare-produce-to-get-out-of-legacy-breizcamp
- Talk video: https://www.youtube.com/watch?v=E2d2BYxOiME
- Related kata (reference only): https://github.com/martinsson/Refactoring-Kata-Lift-Pass-Pricing

---
name: write-tests
description: Write or improve tests that read like specifications — fakes over mocks, whole-object assertions, clear business intent, short bodies. Use whenever adding or revising automated tests.
---

# Write Tests

Apply the project's testing standards when creating or revising tests, in any language or
test framework.

**Full rules:** [`references/testing-rules.md`](references/testing-rules.md)

## The Short Version

1. **Fakes, not mocks.** Hand-write simulators for the ports/boundaries; use real
   collaborators everywhere else. Tests assert *what the system does*, not *how it calls things*.
2. **One thing per test.** Name it `given_<context>_when_<action>_then_<result>`.
3. **Assert the whole object** (`assert obj == Expected(...)`), copying generated fields
   (IDs, timestamps) from the actual object.
4. **Keep bodies short** — ≤ 10 statements / ≤ 15 lines. Push detail into helpers; keep the
   data that matters visible in the test.
5. **Parametrize / table-drive** repeated logic instead of copy-pasting test bodies.
6. **No fixed sleeps.** Yield, or wait on a predicate / completion signal.
7. **Run through the project's test runner**, never an ad-hoc entry point.

## For Bug Fixes

Follow [`references/bugfix-workflow.md`](references/bugfix-workflow.md) — write a failing test
that reproduces the *observable consequence* first, confirm it fails, then fix.

## For New Features

Follow [`references/feature-workflow.md`](references/feature-workflow.md) — agree the business
rules and the test list with the user before writing code.

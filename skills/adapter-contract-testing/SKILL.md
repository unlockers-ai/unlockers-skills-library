---
name: adapter-contract-testing
description: Write or review contract tests that hold a fake and its real adapter to the same specification. Use when introducing a port, adding a fake/simulator, or when tests pass against a fake but the real integration breaks.
---

# Adapter Contract Testing

Runs one shared test suite against both the real adapter and its simulator, so the fake
cannot drift away from what it stands in for.

**Method:** [`references/adapter-contract-testing.md`](references/adapter-contract-testing.md) — read it first.

## When this applies

The `no-mocks` rule in [`testing-rules.md`](references/testing-rules.md) buys fast, readable
tests by testing against fakes. It also creates one risk: a fake that has quietly stopped
behaving like the thing it replaces. Contract testing is what makes that trade safe. Reach
for it whenever a port gets a second implementation.

## Process

1. **Identify the port** — the interface, and its real and simulated implementations. If
   there is no interface, that is the first finding: there is nothing to hold both sides to.
2. **Write the contract** as an abstract test class with one abstract factory method
   (`create_<port>`). Every test in it must be true of *any* correct implementation.
3. **Subclass exactly twice** — real and simulator. No third subclass.
4. **Move behaviour into the contract.** Any test currently written against only one
   implementation that should hold for both belongs in the contract, not where it is.
5. **Run both** in CI, and check they both actually run — a contract with a silently
   skipped subclass is worse than no contract, because it reads as coverage.

## What to flag when reviewing

- `skip` inside a contract subclass. The simulator should be pre-seeded to satisfy the
  contract instead; a skip is the fake declaring which part of the specification it ignores.
- Tests asserting shared behaviour that live outside the contract — they only constrain one
  implementation.
- Simulator-only assertions living inside the contract — they will fail the real adapter
  for the wrong reason.
- More than two subclasses; a factory method that takes configuration and lets the two
  sides be set up differently.
- A port whose fake has no contract at all, when the real adapter talks to something the
  test suite never exercises.

## Done criteria

- The contract captures the shared behaviour the pipeline actually depends on.
- Real and simulator subclasses pass the same tests, with no skips.
- Simulator-specific tests sit outside the contract.

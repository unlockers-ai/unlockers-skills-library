<!-- Generated from docs/testing-rules.md by tools/sync-references.py. Edit the source, not this copy. -->

# Testing Rules

Rules for writing tests that read like specifications and stay cheap to maintain.
Examples are Python; the rules are not — see the note on language in the README.

**For bug fixes, see [`bugfix-workflow.md`](bugfix-workflow.md) — always write a failing test before fixing.**

## 0. Key Principles

- **Prefer fakes/simulators over mocking frameworks.** Avoid `unittest.mock` and its
  equivalents where a hand-written fake would do. See §1.
- Test one thing per test function.
- Use a naming pattern that states intent: `given_<context>_when_<action>_then_<result>`.
- **Assert the whole object when possible** (`assert obj == ExpectedObj(...)`), not a
  scatter of individual attributes. For generated fields (IDs, timestamps), copy them
  from the actual object: `assert obj == Expected(id=obj.id, ...)`.
- Place tests in the conventional location for your stack and mirror the production
  structure.
- Drive tests through the project's test runner, never an ad-hoc `main`/script entry point.
- Don't add redundant prose to assertions. Just write `assert x == 5`.
- Don't write trivial tests that only exercise the language or a library.
- Never assert a bare `false`. Raise/throw an explicit failure with a message instead.

## 1. No Mocks — Use Simulators Instead

- Avoid mocking frameworks. Use **simulators (fakes)** that behave like the real thing.
- Only the **ports** (boundaries) of a hexagonal / ports-and-adapters architecture
  should have simulators.
- Unit tests test the **whole stack down to the simulator**.
- Use the **real collaborator** when it is not a port (internal domain objects and services).

Example:
- ✅ Create `FakeBasePriceRepository` implementing the `BasePriceRepository` interface.
- ✅ Create `FakeHolidayRepository` implementing the `HolidayRepository` interface.
- ❌ Don't patch or `Mock()` a port.
- ✅ Use real domain objects and services in tests (they are not ports).

**Why:** mocks couple tests to *how* code calls collaborators; fakes let you assert
*what* the system actually does. Tests survive refactors.

**The risk this creates** is a fake that has drifted from the adapter it stands in for.
That is what contract tests are for — see [`adapter-contract-testing.md`](adapter-contract-testing.md).
A new port gets a contract, not just a fake.

**How far they reach:** business tests cover the *entire* inner hexagon — use case and
domain — with the ports faked at the boundary, including cases where one use case
orchestrates several services. Given no business logic in the controller and none in the
repository, that makes them the complete record of the business rules; a rule they cannot
reach is a rule sitting in the wrong layer. See
[`hexagonal-architecture-rules.md`](hexagonal-architecture-rules.md).

## 2. Keep Tests Short with Clear Business Intent

- Tests have **hard limits**: **≤ 10 statements** and **≤ 15 lines** in the test body.
  Exceeding either is a signal to refactor — extract a helper, add default arguments to
  an existing helper, or call helpers positionally instead of with keyword arguments.
- Express **clear business intent** in test names and structure.
- Hide implementation details in **helper methods**.
- Keep the **relevant data inside the test** (don't bury the data that matters in helpers).
- Test methods should read like specifications.

Example:
```python
def test_given_adult_when_calculating_price_then_pays_full_price() -> None:
    # Arrange — relevant data visible
    configure_base_price_to(35)
    age = 30

    # Act
    result = calculator.calculate_price(age, regular_day)

    # Assert
    assert result.price == 35
```

## 3. Use Parametrized / Data-Driven Tests to Avoid Duplication

Use your framework's table-driven mechanism when several cases share logic but differ in
data: `@pytest.mark.parametrize`, JUnit `@ParameterizedTest`, Jest `it.each`, Go
table-driven subtests, etc. Don't copy-paste a test body with small edits.

Example:
```python
@pytest.mark.parametrize(
    "age,date,expected_price",
    [
        (30, date(2024, 1, 15), 35),
        (65, date(2024, 1, 15), 27),
        (5, date(2024, 1, 15), 0),
    ],
)
def test_given_different_ages_when_calculating_price_then_returns_expected_price(
    age: int, date: date, expected_price: int
) -> None:
    result = calculator.calculate_price(age, date)
    assert result.price == expected_price
```

## 4. Never Use Fixed-Time Sleeps

Fixed sleeps make tests brittle and slow. Try, in order:
1. Yield control (`sleep(0)` / `await asyncio.sleep(0)` / equivalent) to let the work run.
2. Use a **wait-for-predicate** helper that returns as soon as the condition holds.
3. Expose a test-only hook (an awaitable, a callback, a completion signal) to await on.
4. Ask the user what to do about it.
5. Leave a `FIXME` documenting the gap.

## 5. Running Tests — Timeouts and Hang Detection

**Why this matters:** A hanging test is almost always an environment/infrastructure
issue, not a code issue. Waiting on it produces nothing and wastes unbounded time.
Detecting and stopping a hang immediately is critical.

**Set explicit performance budgets** appropriate to your project, for example:
- A single application's full suite completes in **< 1 minute**.
- The full monorepo suite completes in **< 3 minutes**.
- Any individual test completes in **< 10 seconds** (enforce a per-test timeout in config).

If a run exceeds its budget, something is hung — not slow.

**Default: just run the tests.** Use a sensible initial wait — a couple of seconds for a
single file, ~60s for one application, ~180s for a full monorepo.

**If the run exceeds the expected wait, treat it as hung. Stop it immediately.** Do not
keep waiting.

1. **Run an infra health check first** (a fast script that pings the services the tests
   depend on). If a service is down, fix it and re-run. Don't bisect until infra is healthy.
2. **If infra is healthy, bisect by subdirectory.** Each sub-run is bounded by the
   per-test timeout, so a small wait is enough. Sum the durations of the passing parts to
   estimate the healthy run time, then use that as the wait for the next full run.

**Never** wait longer than the expected run time hoping output appears. A run that
produces no output within its budget is hung, not thinking.

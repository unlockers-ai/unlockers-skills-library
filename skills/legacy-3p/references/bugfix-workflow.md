<!-- Generated from docs/bugfix-workflow.md by tools/sync-references.py. Edit the source, not this copy. -->

# Bug Fix Workflow (Test-First)

When fixing a bug — whether discovered during code review, reported by a user, or found
during development — **always** follow this workflow. It is language- and framework-agnostic.

## Steps

1. **Audit existing test coverage for the affected code.**
   - Before writing anything, look at what tests already exist around the buggy code path.
     A bug that surfaced this easily usually means coverage is thin or asserts the wrong thing.
   - If coverage is absent or shallow, plan additional tests beyond the single bug-repro
     test — enough to give the next maintainer a real safety net, not just the one missing case.
   - If you spot existing tests that look ineffective, not business-facing, or unlikely to
     prove correctness (they only check that a mock was called, they pin implementation
     details rather than behaviour, they could never have failed for this bug), **raise an
     issue**: file a follow-up work item or add a `FIXME(<context>):` and flag it in the PR
     description rather than silently leaving them as-is.

2. **Write one or more failing tests that reproduce the bug.**
   - The tests must fail *before* the fix and pass *after*.
   - Tests should demonstrate the *observable consequence* of the bug, not just the
     immediate symptom — think about what goes wrong on the *next* cycle or interaction.
   - Prefer behaviour-level / business-facing assertions over mock-call assertions where
     the layer allows it.

3. **Run the tests and confirm they fail.**
   - If they pass, the tests don't actually catch the bug — rethink what you're asserting.
   - The failure message should make the defect obvious.

4. **Apply the fix.**
   - Stay focused on the bug at hand. If, while fixing, you see **symptomatic causes**
     (related design smells, missing guards elsewhere, sibling code with the same latent
     issue) that are too big to address now:
     - Either add a `FIXME(<context>):` comment in the relevant location and flag it
       explicitly in the PR description, **or** open a follow-up work item and link it.
     - Do not silently expand the scope of the bug fix.

5. **Run the tests and confirm they pass.**

6. **Run the full test suite** to check for regressions.

7. **Summarise in the PR.**
   - Call out: the test(s) added, any coverage gaps found, any FIXMEs left behind, and any
     follow-up issues filed.

## Common Mistake: Testing the Symptom Instead of the Consequence

A state-corruption bug often doesn't manifest immediately — it shows up on the *next*
operation. For example:

- **Wrong:** Assert that a guarded action wasn't called (the guard works, but state is
  silently corrupted).
- **Right:** Assert that a *subsequent* action — which would only happen if the state was
  corrupted — is also not called.

Always ask: "If the state is wrong but the action was blocked, what happens *next*?"

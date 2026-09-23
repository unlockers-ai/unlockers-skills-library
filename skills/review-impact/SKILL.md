---
name: review-impact
description: Analyse the blast radius of branch or pull-request changes across a multi-package repo — who breaks if this is wrong, and which test suites must pass. Use before pushing a change to shared code.
args:
  - name: compare_ref
    description: "Branch to review, OR a PR/MR number (default: current branch). When a number is given, the source/target branches are resolved from the git platform."
    required: false
  - name: base_ref
    description: Base branch to compare against (default: main)
    required: false
  - name: report_path
    description: "Path the report must be written to, when a caller pins it (default: reviews/impact-analysis.md)"
    required: false
---

# Impact Analysis Skill

Maps the **blast radius** of a change across packages. Two questions: who breaks if this is
wrong, and which suites must pass before pushing?

Unlike the other reviewers, this one is most useful **before** you push, not after. It
answers "what did I just put at risk", and its output is a list of commands to run.

**Protocol:** [`docs/review-protocol.md`](../../docs/review-protocol.md) — arguments, ref resolution, exhaustiveness, severity levels, report shape. Read it first.
Its § 4 *Be exhaustive* is mandatory; the lens steps it refers to are steps 2–7 — every changed path bucketed, every modified symbol traced below.

> **Adapt to your repo.** This skill assumes a multi-package repo — shared packages that
> several deployables depend on. Substitute your own layout for `<shared>/` and `<app>/`,
> and your own commands for `<run tests for X>`, `<run type checker>`, `<run linters>`.
> In a single-package repo, steps 4–5 collapse to "grep the whole tree" and the skill is
> still worth running.

## Process

1. **Resolve refs and gather the diff** — per [`review-protocol.md`](../../docs/review-protocol.md).

2. **Bucket every changed path**: shared package, deployable, scripts, root config,
   docs/specs, infrastructure. The interesting ones are shared packages — a change confined
   to a single deployable has a blast radius of one.

3. **Extract the modified public surface.** For each non-test change in a shared package,
   list what was added, changed or removed: top-level functions, classes, public methods,
   module constants, settings/config fields, serialized schemas.

   For each, classify the change as **signature** or **behavioural** — a changed return
   type, a new error path, a different side effect, a changed default. This is the single
   most important distinction in the report: signature breaks are caught by the compiler
   or type checker, behavioural breaks are caught in production.

4. **Trace callers.** For each symbol above, search the whole repo:

   ```bash
   grep -rn '\b<symbol>\b' --include='<source-glob>' .
   ```

   Group hits by package and by kind — same-package, sibling-shared-package,
   deployable-runtime, deployable-test. Track re-exports separately: a symbol re-exported
   from a package entry point has a wider surface than its definition suggests.

5. **Trace dependency changes.** For each modified manifest, list added, removed and
   bumped dependencies, then find which deployables depend on that package.

6. **Trace the cross-cutting cases.** These are the ones that bite, because the compiler
   sees nothing:
   - **Config/settings classes** — renaming or removing a field is an environment-contract
     change. List every consumer, and remember the deployment configs outside this repo.
   - **New test infrastructure** (shared fixtures, conftest, test base classes) — often
     needs a full type-check rather than an incremental one.
   - **Message/queue contracts and event schemas** — list every producer and consumer.
     A rolling deploy means old and new run simultaneously; ask whether the change is
     compatible in both directions.
   - **Database models and migrations** — list every service reading or writing the same
     table or collection.

7. **Recommend verification.** Concrete, copy-pasteable commands, one per impacted package.
   The point of the report is this list.

8. **Confirm § 4 of the protocol is satisfied**, then **generate report** → `reviews/impact-analysis.md`

## Severity Model

| Severity | Indicators |
|----------|------------|
| Critical | Behavioural change to a symbol with at least one runtime caller outside its package; config field renamed or removed; message/schema contract change |
| Major | Signature change with multiple callers; dependency bump affecting two or more deployables; re-exported symbol modified |
| Minor | Purely additive surface; change confined to one package; test-only callers |

## Output Format

```markdown
# Impact Analysis: {branch}

## Change Summary
- Shared packages touched: …
- Deployables touched: …
- Public symbols modified: N (M behavioural, K signature-only)

## Blast Radius

### <shared>/pkg — `Foo.do_thing()` (behavioural)
**Callers (5):**
- <app-a>/…/bar.py:42 (runtime)
- <app-b>/…/baz.py:13 (runtime)
- <shared>/other/qux.py:88 (sibling)

**Risk:** Critical — the error path changed and the runtime callers don't handle the new exception.
**Required:** `<run tests for app-a>`, `<run tests for app-b>`, `<run tests for shared/other>`

## Cross-Cutting Concerns
- `Settings.broker_url` renamed → environment contract change; update deployment configs
- New shared fixture → run the full type check, not the incremental one

## Recommended Verification
```bash
<run tests for app-a> <run tests for app-b>
<run type checker>
<run linters>
```

## Summary
- Critical: 1 | Major: 2 | Minor: 0
- Push-blocking: yes/no
```

## Example Usage

```
review-impact              # Current branch vs main
review-impact feat/foo     # Specific branch
review-impact feat/foo dev # Different base
review-impact 3574         # PR/MR by number
```

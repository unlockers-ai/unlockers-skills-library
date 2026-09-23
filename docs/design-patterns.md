# Design Patterns

> Examples are in Python, but the pattern is language-agnostic — it applies to any code
> that mixes I/O with decision logic.

## Gather at the Boundary, Reason with Pure Functions

When a function needs to make decisions based on data fetched from an external source
(DB, repository, HTTP), centralise all I/O at the **top** of the function, then delegate
the reasoning to **pure** helpers.

### Rule

- I/O calls belong at the **top** of the function — one clear place to see what data is loaded.
- Decision logic belongs in **pure functions** that receive already-fetched data as plain
  collections.
- Never scatter I/O across helper functions that are called from within the decision logic.

### Before

```python
async def _find_active_session(repo, ws_id, tracked, status):
    sessions = await repo.get_many(Query(workstation_id=ws_id, status=status))
    return next((s for s in sessions if tracked_name(s) == tracked), None)

async def _resolve_routing(repo, ws_id, tracked, policy):
    # I/O buried in helper — called twice for ONGOING: once here, once below
    if ongoing := await _find_active_session(repo, ws_id, tracked, ONGOING):
        return ReturnExistingSession(ongoing)

    if paused := await _find_active_session(repo, ws_id, tracked, PAUSED):
        return ResumeExistingSession(paused)

    # Third repo call — same query as the first one
    blocking = await repo.get_many(Query(workstation_id=ws_id, status=ONGOING))
    ...
```

### After

```python
def _find_by_tracked_object(sessions, tracked):
    return next((s for s in sessions if tracked_name(s) == tracked), None)

async def _resolve_routing(repo, ws_id, tracked, policy):
    # All I/O at the top — two queries, each executed exactly once
    ongoing = await repo.get_many(Query(workstation_id=ws_id, status=ONGOING))
    paused  = await repo.get_many(Query(workstation_id=ws_id, status=PAUSED))

    # Pure reasoning on already-fetched data
    if ongoing_same := _find_by_tracked_object(ongoing, tracked):
        return ReturnExistingSession(ongoing_same)

    if paused_same := _find_by_tracked_object(paused, tracked):
        return ResumeExistingSession(paused_same)

    if not ongoing:
        return CreateNewSession(ONGOING)

    blocking = ongoing[0]
    ...
```

### Why It Matters

- **No hidden I/O:** reading the function top-to-bottom reveals every external call upfront.
- **No duplicate queries:** the `ONGOING` list is fetched once and reused for both the
  identity check and the blocking check.
- **Testable helpers:** `_find_by_tracked_object` is a pure function — trivially testable
  in isolation without any async or repository setup.
- **Easier to optimise:** if the two queries should become one (a combined or batch
  fetch), the change is local to the I/O section.

### When to Apply

Any time a function calls an impure helper (async, side-effecting, I/O) more than once for
the same underlying data, or when a helper hides an I/O call that only exists to support a
decision made at the call site.

In a use case, this is not an optional pattern but the mechanics of a rule:
[`hexagonal-architecture-rules.md`](hexagonal-architecture-rules.md) rule 2 says when to
split deciding from applying, and lists the signals that say it is time.

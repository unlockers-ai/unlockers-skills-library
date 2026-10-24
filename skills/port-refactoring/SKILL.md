---
name: port-refactoring
description: "Design the ideal port for an adapter to an external service (typically wrapping a generated API client) by perfecting its interface through the simplifications it allows in every caller, then plan the safe path there. Use when refactoring an adapter or data-access class toward a hexagonal port, when generated vendor types leak into domain code, or when asked what an adapter's interface should be."
---

# Port Refactoring

Finds the interface an adapter's callers need, in pseudo-code, before any real refactoring.

**Method:** [`references/port-refactoring-method.md`](references/port-refactoring-method.md) — read
it first, whole. Its examples come from four adapters to one healthcare vendor; the rules are not
vendor-specific.

## Process

1. **Inventory** per the method's step 1, including the callers a class-name search misses and the
   live-caller check. If no method has a live caller, stop: report the deletion proposal.
2. **Write the interface and rewrite every caller** against it, in pseudo-code, outside the
   codebase (a proof-of-concept branch or a scratch file). Behaviour unchanged unless listed.
3. **Loop** on the central step until its stop criterion holds: a full sweep finds nothing, and
   every remaining signal is listed with its reason.
4. **Run the signals table and the three tests**, then self-review against the interface review
   grid. Any finding restarts step 3.
5. **Report**: target interface, callers after, simplifications ranked (deleted vs moved code),
   defects found (check the method's defect families), `TODO`s, and the Phase 2 path.

Phase 2 (the real refactoring) starts only after a human has reviewed the interface.

## Done criteria

- Every live caller rewritten; leak counters at zero in callers, or each remainder listed with
  its reason.
- Every signal and test answered present/absent with evidence.
- Behaviour changes and `TODO`s listed separately from the target.

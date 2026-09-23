# Code Design Rules

What good looks like *inside* a type or a function. For where code goes — controllers, use
cases, ports — see [`hexagonal-architecture-rules.md`](hexagonal-architecture-rules.md).

[`accidental-complexity-guide.md`](accidental-complexity-guide.md) catalogues the smells and
how to detect them. This page states the target shape and the order to reach for it in.
Examples are Python; the rules are not.

**Rules 1 and 2 come first.** Before any architectural move, look at whether the primitives
have types and whether the data clumps have behaviour. They are cheap, they are local, and
they are where most of the leverage is. They also test well — no hidden state, no side
effects, so the tests are plain function calls with plain assertions.

## 1. Wrap Primitives in Types That Carry Their Rules

A domain concept represented as `str`, `int` or `float` has nowhere to put its rules, so the
rules end up scattered across every caller — and the type system stops helping.

```python
@dataclass(frozen=True)
class Millimetres:
    value: int

@dataclass(frozen=True)
class Chf:
    centimes: int

    def __post_init__(self) -> None:
        if self.centimes < 0:
            raise ValueError("Chf cannot be negative")
```

`Millimetres(30) + Chf(500)` no longer compiles or runs — the mistake is caught by the
type, not by a reviewer. And the negativity rule lives in one place instead of at every
site that constructs an amount.

**Consequence of skipping it:** validation gets duplicated at call sites, drifts between
them, and the case someone forgot surfaces as an exception thrown deep in the domain (see
rule 3).

**Detection:** the guide's [§5 Primitive Obsession](accidental-complexity-guide.md).

**Capability values are the sharpest case of this.** A value that grants access — a push
endpoint, a share link's slug, a door code, a reset token — is logged and errored-on by
*name*, never by value. The type that holds it owns the naming (a `name` property that
returns something like `"push subscription for device 3"`); where no such type exists, log
a short fingerprint instead, never a prefix of the value itself. Logs leave the box — to a
log aggregator, a support ticket, a screenshot — so this is a repo-wide rule, not a
per-module judgment call.

## 2. Attach Behaviour to Data Clumps, as Immutable Objects

When the same group of values travels together — `street, city, postal_code`;
`amount, currency`; `start, end` — it is an object that has not been written yet. Until it
is, the logic that belongs to it lives in whichever service happened to need it first, and
the next service that needs it writes its own copy.

Give the clump a type and move the logic onto it. Make it **immutable**: any mutation is a
named method on the object, with the narrowest visibility that works.

```python
@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def overlaps(self, other: "DateRange") -> bool: ...
    def extended_to(self, new_end: date) -> "DateRange": ...   # returns a new range
```

Types from rules 1 and 2 belong in their own file. Left inside the service that first
needed them, they couple every later user of the type to that service.

**Consequence of skipping it:** the service classes grow, and the same rule gets
reimplemented slightly differently in each of them.

**Detection:** the guide's [§6 Data Clumps](accidental-complexity-guide.md) and
[§18 Anemic Domain Model](accidental-complexity-guide.md).

**Scope:** this is about domain data — a clump with rules or logic that would otherwise be
reimplemented per caller. A private view-assembly helper's parameter list (a page builder's
`(outcome, why)`, a `_result_page(...)` with ten keyword arguments) is exempt: it is display
data for one template, at the controller's edge
([`hexagonal-architecture-rules.md`](hexagonal-architecture-rules.md) rule 1), not a domain
concept. Grouping it into a type is a normal refactor to consider, not a consequence of this
rule.

## 3. Let Exceptions Propagate

**The default is the simplest possible handling:** don't catch. Let the exception travel to
the top of the application, where one generic handler turns it into an error response.

Any other strategy — catching mid-flight, wrapping, replacing exceptions with an explicit
result type — has to be justified case by case, on that case's merits. It is a reasonable
choice sometimes; it is never the starting point.

Nested exception handling inside one class, or the same failure handled at several levels
of the application, is a design error rather than a robustness measure. Each catch is a
place a future reader must decide whether the failure was really handled.

**Where the catch is a symptom:** an exception thrown deep in the domain because an illegal
value got that far usually means the value should have been rejected at construction. Fix
it with rule 1, not with a `try`.

**Detection and the boundary cases where catching *is* right:** the guide's
[§2 Exception Handling Complexity](accidental-complexity-guide.md) — adapters translating
library errors, framework-level handlers, resource cleanup.

## 4. Keep Functions Short

Past about 30 lines, a function is usually doing more than one job. There's no single fix
— but the one worth naming, because it isn't obvious, is separating **deciding** from
**applying** (see [`hexagonal-architecture-rules.md`](hexagonal-architecture-rules.md) §2):
it's what most often cuts complexity out of a use case or a service.

**Consequence of skipping it:** the whole function can only be tested through its side
effects, so covering every branch means faking every one of them too.

**Detection:** the guide's [§19 Long Functions](accidental-complexity-guide.md).

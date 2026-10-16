<!-- Generated from docs/hexagonal-architecture-rules.md by tools/sync-references.py. Edit the source, not this copy. -->

# Hexagonal Architecture Rules

Where code goes, once it is well-shaped. For the shape itself — value objects, immutability,
exceptions — see [`code-design-rules.md`](code-design-rules.md), and start there: rules 1
and 2 of that page are worth more than anything here, and cost less.

These rules assume controllers/routers at the edge, use cases just behind them orchestrating
calls to ports, and a domain that knows about neither. Examples are Python; the rules are not.

## 1. Keep the Controller Minimal

A controller may call a repository directly for a genuinely simple operation. Past about
four lines, extract a use case.

The use case is the testable encapsulation layer between the router and the ports. Its
surface should let functional tests run without touching IO — no HTTP client, no framework
test harness, no database.

**Consequence of skipping it:** the only way to test that logic is through the transport,
which makes the tests slow, indirect, and coupled to the framework — so they get written
thinly, or not at all.

## 2. Separate Deciding from Applying

As soon as a use case grows, split it into two phases:

- **Decide** — gather everything needed up front, then produce a decision. Pure: no writes,
  no side effects.
- **Apply** — execute the decision: writes, mutations, notifications.

[`design-patterns.md`](design-patterns.md) has the mechanics — gather all I/O at the top of
the function, hand plain data to pure helpers, and never hide a read inside a decision
helper.

The split propagates: if a service the use case calls mixes reads and writes itself, it
needs the same treatment, or the use case's "pure" decision phase isn't pure.

**Signals that it is time:**

- **Several functional cases.** From three, a decision table earns its place.
- **More than one `catch`.** Scattered exception handling means the failure decisions are
  spread out too; centralise them at the top (see
  [`code-design-rules.md`](code-design-rules.md) rule 3).
- **More than one read-port call, or more than one write-port call.** One read plus one
  write is a normal use case. Two reads means the second may depend on the first, which is
  where duplicate queries and hidden ordering live.

**Consequence of skipping it:** every functional case has to be tested through the writes,
so the test count multiplies with the number of side effects instead of the number of rules.

## 3. Make Multiple Side Effects Transactional — or Decide Not To

As soon as an operation produces more than one side effect, ask what happens when the second
one fails after the first has succeeded. If the resulting state is inconsistent, either:

- make the set transactional with the tooling available (a database transaction is the usual
  answer), or
- address the inconsistency explicitly another way — compensation, idempotent retry,
  reconciliation.

Ignoring it is allowed. It has to be an **intentional decision**, recorded where the next
reader will find it — not an omission.

**Consequence of skipping it:** the inconsistency is discovered in production, by someone
who has no way to tell whether it was considered.

## 4. Business Tests Cover the Whole Inner Hexagon

Business tests run against the use case and the domain together, with the ports faked at the
boundary — see [`testing-rules.md`](testing-rules.md) §1.

Because rules 1–3 leave no business logic in the controller and none in the repository,
these tests capture *all* the business rules, including the cases where a use case
orchestrates several services. That is the payoff for the other three rules, and the check
on them: business logic that these tests cannot reach is business logic in the wrong place.

## 5. An Adapter's Inbound Shape Comes From a Schema, Not From `.get()`

Where the provider publishes an OpenAPI/JSON-Schema document, generate or write the
types from it and validate the response against them. Reach for a hand-rolled
`b.get("field")` only when there is no schema to have.

Reading a payload field by field is reading the fields *you expected*. A key that does not
exist is indistinguishable from one that is empty, so a typo, a rename or a field that was
never there at all arrives as a default and the adapter reports success. Where the provider
publishes no schema, write the model yourself from real responses and validate against it
anyway — the point is that an unknown field fails at the boundary.

**What it cost, once:** a bookings adapter read `b.get("status")` for seven weeks. The
provider has no `status` field, so every booking came back `""` — and an empty status was
read as *confirmed* downstream. A schema would have rejected the attribute at the point of
writing it. Instead one config flag stood between an unconfirmed enquiry and a guest being
granted early access.

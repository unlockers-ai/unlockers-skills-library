<!-- Generated from docs/port-refactoring-method.md by tools/sync-references.py. Edit the source, not this copy. -->

# Port Refactoring Method

How to take an adapter to an external service (usually wrapping a generated API client) and find
the port it should be: the interface its callers need, not the one the vendor ships. Distilled
from refactoring a mail adapter by hand, then replayed by agents on three more adapters to the
same vendor (a patient-identity service, a reference-codes service, a health directory); the
examples come from those runs.

Two phases, with a review between them:

1. **Design the target interface**, perfecting it through the simplifications it allows in its
   callers, in pseudo-code, until it allows no more.
2. **Interface review**: a reviewer judges the target before anyone invests in the path to it.
3. **Get there safely**: the target becomes the goal, reached in small tested steps.

## Phase 1: design the target interface

### 1. Inventory

For each public method of the adapter: its callers, what they do in the port's place
(validation, parsing, re-association, `catch`, parameters carried through layers), generated
types leaking out, traps.

**Live callers.** For each caller, what triggers it, checked: a route (its path searched in the
front end, outside the generated client), a scheduled command, a worker. Only live production
callers shape the port; a test or a vendor probe is not a use. A method with no live caller: propose
deleting it, or a `TODO` naming the caller to come. If no method has one, the deliverable is the
deletion proposal, not a port designed for hypothetical callers.

**Source of truth.** Search for the business concept, not only the adapter. If the same data
already has another source in the application, choosing the source comes before shaping the port
(reference codes: the front end read the same tables from the local database, and the adapter's
route was no longer called).

Searching for the class name misses callers. Also include:

- code that catches what the adapter lets through: every `catch` and `instanceof` on the
  generated client's exception (queue worker, shared error classifier). Once that exception stops
  leaving the adapter, the port's exception must get the same reaction there (retryable or not),
  unless that reaction is itself a defect, to be listed. A classifier that walks the exception
  chain keeps the old classification if the client exception is chained;
- readers of the adapter's output when a route returns it as is or it is stored: front-end
  components and the API schema included (directory: 8 front-end files read the raw vendor
  response);
- existing fakes and mocks, each response with the HTTP status the real service would return:
  what they had to reproduce is the list of the port's leaks;
- drift in the generated client: hand-written overrides (an accessor looks missing without them);
  hand edits inside generated files, lost at the next regeneration (`git log -p` on every model
  used); operations removed from the spec whose generated files linger.

Measure before, production and tests separately. The target is zero in callers; the adapter and
its mapper keep their imports. Count: imports of generated models, constructions of generated
models, `catch` of the client exception, accessors and setters called on generated objects (no
name pattern catches them all), and vendor field names repeated in your own DTOs, API schemas and
front-end types — the leak the other counters miss.

If one method weighs much more than the others, in the adapter or in its caller (mail: sending,
12 parameters; identity: the search procedure in the domain service), study it alone first.

### 2. Write the interface and rewrite every caller against it

Pseudo-code on purpose: the point is to judge a shape, not to run a program. Behaviour unchanged by
default; a business decision met on the way becomes a `TODO`, a deliberate change is listed
separately. When the honest interface cannot express the current behaviour, it is usually a bug:
fixing it is the change to list (identity: a technical failure returned in an HTTP 200 read as
"identifier inactive" does not fit an `isActive()`).

### 3. Perfect it through the simplifications — the central step

After every change to the interface, sweep **all** its callers, not only the one just rewritten
(missed twice on the mail adapter). Look for what the caller still does in the port's place:

- generated models or accessors, `catch` of the generated client;
- revalidation, reparsing, re-association (mail: new message ids matched back by position);
- parameters carried through several layers (the identity traits went down 4 levels);
- logic duplicated between callers;
- dead code the new interface makes visible.

Each finding is a question to the interface: *what should it return or accept so the caller no
longer has to do this?* (`move()` returns "old id ⇒ new id".) The answer changes the interface and
starts another sweep.

Three cases where placement is not obvious:

- **A procedure of calls to get one answer** (retry with one more criterion, fallback): the port
  guarantees the answer, and the adapter does what its vendor does not. When nobody knows what the
  vendor does, the procedure stays with the caller and the question goes into a `TODO`.
- **What must be recorded even on failure.** The trace of the exchange with the vendor stays in
  the adapter: a simulator has no exchange to trace. A business record (a history row) belongs to
  the caller: the port's exception carries what it needs to write it, or, when one port call makes
  several exchanges, the caller passes a journal to the port.
- **Reading a vendor format already stored**: a static mapper function, not a port method.

**Stop criterion:** a full sweep of every caller finds nothing, and every signal below still
present is kept on purpose, listed out of scope with its reason and the test it partly fails
(identity: the front end reads the stored vendor JSON, so a simulator must forge that format).
Defects in callers unrelated to the port are listed, not fixed. In the summary, tell deleted code
from code merely moved; in pseudo-code only the leak counters can be measured exactly after.

With a single caller, one sweep is often enough: the effort goes to the signals and the tests.

### Signals that the interface can go further

In the interface itself (Ousterhout's red flags, applied to a port):

| Signal | For a port |
|---|---|
| Pass-through method | it repeats a remote call with renamed parameters: the port abstracts nothing |
| Information leakage | one piece of vendor knowledge lives in two places |
| Temporal decomposition | the caller chains two methods in a fixed order for one intention (mail: send, then file the copy in Sent) |
| Overexposure | the common case must supply the rare case's options |
| Hard to name | one sentence without vendor vocabulary cannot describe the method; a name says where the data is (`…Remote`) instead of the intention |
| Repetition in the adapter | the same pattern in several methods (mail: the trace `try/catch` copied 5 times) |
| Header interface | each caller uses a disjoint subset. A subset that never calls the vendor (permission check, database read) leaves the port and stays in the current class; the port is the new class. Vendor subsets: one role interface per observed use |

Three tests:

1. **The second adapter.** Write the simulator in your head, starting from the existing fakes, or
   as a few lines of contract if there are none. If it must reproduce a vendor quirk (ids matched
   by position, a failure status inside a 200), the quirk belongs to the adapter. A fake that takes
   a path the real service never takes hides bugs (identity: a KO answered in a 200 hid the
   verification bug).
2. **The contract without the vendor.** Every postcondition can be stated without a word of the
   vendor or the protocol.
3. **One exception, one reaction.** Each port exception calls for a distinct reaction from the
   caller (a global error listener counts as one); otherwise merge them. An error the caller could
   do nothing about disappears: deleting a message already gone succeeds (*define errors out of
   existence*). A vendor error of unknown meaning stays an exception, with the question to the
   vendor as a `TODO`, never an empty result.

## Interface review

On the proof-of-concept PR. Judge the shape of the objects, the names, how methods are cut, and the
split between port, adapter and mapper. Feedback restarts step 3. The grid that came out of the
mail adapter's review:

- an object that exists is valid (built once, then accessors);
- no associative arrays in the port's API, an object with accessors instead; a list of value
  objects is fine;
- the port owns its value objects; another domain's API DTO is converted at the HTTP edge, never
  used as a port type;
- a boolean that selects a behaviour becomes two methods, and what really differs is passed as
  data (16 trace methods became 2); a boolean that states a domain fact (request a read receipt)
  stays data;
- pure data transformation goes into static functions, one per case, testable without mocks;
- what depends on the environment is decided at injection, not by an `if`;
- generated models never leave the adapter; errors are translated in one place;
- conforming to the vendor's model is an explicit choice, method by method (mail: vendor JSON
  stored as is).

The proof of concept's summary fixes the target: a table method by method (input, output,
errors), before/after measurements, behaviour changes, `TODO`s.

## Phase 2: get there safely

The proof-of-concept code is only an illustration; the path starts again from the current code.

1. **Safety net first**: coverage and mutation testing of the existing tests on what the
   refactoring touches, gaps filled.
2. **A simulator and a shared contract test** with the real adapter — see
   [`adapter-contract-testing.md`](adapter-contract-testing.md). Simulate the port, never the
   generated client. A simulator that needs test-only methods signals a leaking port.
3. **Small steps, each compiled and tested**, in the proof of concept's order; each leaves the code
   mergeable.
4. Clean-ups found on the way (dead code) merge separately; the target's documentation stays on the
   proof-of-concept branch.
5. Business `TODO`s are decided before the step that touches them.

## Defects the method surfaces

Shaping the interface finds real defects without looking for them: six on the mail adapter, and
several on each of the three adapters tried next. Families to look for first, most frequent
first:

- a failure status inside a 200 response, never read (all four adapters); identity: a
  verification failing for technical reasons downgraded the patient's identity and wiped it;
- an error swallowed into an empty result, or an unknown code read as "not found";
- a hand fix inside the generated client, lost at regeneration;
- a fake that takes a path the real service never takes;
- the vendor's HTTP code or message relayed as ours (directory: a 401 from the proxy logged the
  user out);
- every error retried, deterministic ones included;
- position-based association, an input mutated by the port.

## Sources

Cockburn, *Hexagonal Architecture*; Fowler, *Role Interface* and *Flag Argument*; Freeman and
Pryce, *Growing Object-Oriented Software, Guided by Tests* ("don't mock what you don't own");
Ousterhout, *A Philosophy of Software Design* (red flags, *define errors out of existence*);
Evans, *Domain-Driven Design* (anti-corruption layer, conformist); King, *Parse, don't validate*.

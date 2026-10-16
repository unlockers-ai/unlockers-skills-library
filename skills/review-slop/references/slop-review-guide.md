<!-- Generated from docs/slop-review-guide.md by tools/sync-references.py. Edit the source, not this copy. -->

# Slop Review Guide

The lens behind [`review-slop`](../../review-slop/SKILL.md): work that is *correct*
and still shouldn't be in the diff. Volume, duplication, ceremony, and checks that sit in
the wrong place.

This is a different axis from
[`accidental-complexity-guide.md`](accidental-complexity-guide.md), which catalogues smells
*inside* domain code — null guards, exception layering, primitive obsession. Nothing here
is about a language. It is about comments, docs, config, CI, and where a check lives.

**Provenance, so you can weigh it:** the patterns were extracted from the review rounds of
one docs-and-deploy-heavy branch — a log shipper — which went **+1614 → +545 → +451** lines
across three rounds while *gaining* working behaviour. The quotes are the reviewer's own
words. One branch is thin evidence: treat the patterns as strong and the severity
weightings as provisional, and add to this page as other branches confirm or contradict it.

## The patterns

### 1. Prose that isn't ours

Comments and docs that restate public documentation, restate the code beneath them, or
narrate how the code came to exist.

> *"documents things any modern model already knows or is a copy of public doc"*
> *"largely a repetition and knowable from reading the config files"*
> *"line 53-60 seem superfluous now"* — a war story already in the commit message

**Confirm:** could a competent reader get this from the tool's own docs, from the line
below, or from `git log`? Then it is not ours to carry. Where the project forbids comments
that are not hacks or workarounds, a comment that survives must earn it.

**Keep** what is *specific to us*: a constraint the code cannot express, a value that was
chosen for a reason, a trap that has actually bitten. Those belong next to the code.

**Watch for the half-cut.** A logging doc went 253 → 83 lines and still drew *"useless
crap"* three times; the second pass took it to 43. A percentage is not evidence. Ask
whether a whole **category** is still present — categories go to zero, not down.

### 2. Checks that can't fire, or that must be remembered

> *"it asserts things that will never happen"* — 12 deploy tasks → 5
> *"why not use ansible templating that will provide both the check and the assurance that
> it is always checked on deploy?"*

Two distinct findings share this shape:

- **The condition is structurally impossible.** Prefer failure that falls out of the
  structure — a template that cannot render, a missing file the tool already errors on, a
  schema model that refuses to validate — over an assertion restating it.
- **The check is opt-in.** A correct check you have to *remember* is not a check. Move it
  somewhere it cannot be skipped: a deploy step, a pre-commit hook, a pipeline stage, a
  test fixture.

### 3. Verification in the wrong layer

> *"the checks in the workflow are better done in the makefile or in a script called from it"*

Logic in a CI workflow that a laptop cannot run gives you two paths that agree only while
someone maintains both. Push it down into the shared tool — the Makefile, a check script,
the deploy tool.

The trap is fixing this **one layer at a time**: that branch moved a check from CI shell to
the Makefile, and needed a second round to move it into the deploy playbook. The question
is not "where is a better place for this" but **"what already runs every time, and can
this live inside it?"**

### 4. More than one source of truth

> *"only the tokens need to be secrets"* — 5 CI secrets, 2 actually secret; the other
> three were already committed, so the design contradicted itself

Ceremony without a threat model is the common case: something treated as secret that
authorises nothing and is already in the repo. Ask what an attacker gains, and check
whether the value is committed somewhere already.

Same shape in prose: the agent entry file (`CLAUDE.md`, `AGENTS.md`) holds what bites plus
a pointer; detail lives in `docs/`. A fact in both places will drift.

### 5. Duplication across siblings, inherited by copying one

> *"this must be the same for every ansible action in the ci, no?"*

22 lines of SSH setup, byte-identical in three workflows. The third was written by copying
the second, which is exactly what made it read as consistency.

The repeated element is not always a whole file. It can be a block inside two otherwise
different files, or a set of names — six skill names, five report filenames — typed out
fresh in each place that needs them. Same cost: a change has to be made N times by hand,
and the Nth is the one that gets missed. Count the copies; that number is the finding.

A pre-existing duplicate that this diff *extends* still counts. If the change had to touch
fourteen files to add one sentence, the diff is itself the evidence of the cost.

**Confirm:** diff the new file against the one it was copied from; for a repeated block or
name-set, grep the repeated text and count the files. Then **generalise** — the reviewer
above found the SSH block from a *single* file, by asking what else must need the same
thing. A reviewer that only reads the diff finds none of these.

### 6. Scaffolding kept as product

> *"scripts/loki_check.py was only useful while building, right? not anymore"*

539 lines — module, CLI, 16 tests — to run one query and check the result wasn't empty.
Replaced by one committed alert rule that does it continuously.

**Confirm:** was this written to answer a question during development? Is anything but a
human going to run it again? Having tests is what makes scaffolding feel load-bearing;
they are part of the thing to delete, not a reason to keep it.

### 7. Over-claiming inference as fact

> *"this is in switzerland normally"*

Documentation asserted a storage region inferred from a token field that is a routing
code. Different axis from volume, same reflex: output outrunning evidence.

**Confirm:** run the claim. A stated count, a "verified against the full repo", an "N/N
tests green" is checkable — check it, and quote what you got. Also check claims against
the diff itself: a commit message that narrates behaviour no hunk implements is the same
defect, and the cheapest to confirm. Where the claim cannot be run, say what is known and
what was guessed.

## The counter-pressure — read before cutting anything

A reviewer built only from the list above will delete the things that catch silent
failure. The same branch produced all of these, none flagged by the reviewer, all real:

- **The first deploy shipped nothing** — playbook green, readiness probe 200, every batch
  rejected by the far end.
- **An alert rule existed in an error state.** "Created successfully" wasn't working.
- **A credential comparison passed spuriously** (the two sides hashed
  differently-normalised input), and a feature was then built on the false conclusion —
  and kept, after the diagnosis was disproved, by rewriting its comment.
- **A monitoring default would have cried wolf**, expecting a container that logs nothing.
- **A flat metric counter** nearly reported as healthy, because there were no errors.
- **The default notification policy routed to a receiver named `empty`** — the alert would
  have fired into the void.

So the test is not "is this check ceremony":

> Keep a check when the failure is **silent**, can **actually occur at runtime**, and
> **nothing downstream reveals it**. Cut it when the condition is structurally impossible,
> would fail loudly anyway, or something downstream already catches it.

Cutting is not free either. Every finding names what the next maintainer pays for keeping
the thing — and a finding that proposes removing a check names what still catches the
failure. Severity is defined once, in the [`review-slop`](../../review-slop/SKILL.md)
skill.

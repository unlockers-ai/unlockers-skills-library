---
name: review-architecture
description: Review branch or pull-request changes for architectural fit — layering, ports and adapters, dependency direction, package boundaries. Use when a change adds a collaborator, crosses a package boundary, or introduces a new seam.
args:
  - name: compare_ref
    description: "Branch to review, OR a PR/MR number (default: current branch). When a number is given, the source/target branches are resolved from the git platform."
    required: false
  - name: base_ref
    description: Base branch to compare against (default: main)
    required: false
  - name: report_path
    description: "Path the report must be written to, when a caller pins it (default: reviews/architecture-review-issues.md)"
    required: false
---

# Architecture Review Skill

Reviews changes for **architectural fit**: are boundaries respected, are the seams in the
right place, and can this be extended without infrastructure leaking into the domain?

**Protocol:** [`docs/review-protocol.md`](../../docs/review-protocol.md) — arguments, ref resolution, exhaustiveness, severity levels, report shape. Read it first.
Its § 4 *Be exhaustive* is mandatory; the lens steps it refers to are steps 3–5 (*Map the dependency direction*, *Apply the architecture lens*, *Check the seams*) below.

**Also read:** the project's conventions doc (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`
— whichever exists) and [`docs/design-patterns.md`](../../docs/design-patterns.md). If the
project keeps ADRs or design specs, check whether an active one constrains the touched area.

## Process

1. **Resolve refs and gather the diff** — per [`review-protocol.md`](../../docs/review-protocol.md).

2. **Learn the existing architecture before judging it.** For each touched package, read
   its README, its entry point, and one or two existing modules. Determine what style the
   codebase is actually in — hexagonal, layered, event-driven, transaction-script — and
   review against *that*, not against a preferred style. A change that is idiomatic for a
   layered codebase is not a finding because you would have written it hexagonally.

3. **Map the dependency direction.** For each new import crossing a package or layer
   boundary, note which way it points. Most architectural findings are an arrow pointing
   the wrong way.

4. **Apply the architecture lens**

   **Critical** (boundary violations):
   - One deployable importing another deployable's internals
   - Shared library importing from an application
   - Domain layer importing an adapter or infrastructure module — the inverted dependency
   - A new SDK / HTTP / DB / broker call placed directly in domain or service code
     instead of behind a port
   - A concrete adapter constructed inside domain code instead of injected
   - Direct clock, filesystem, randomness or environment access where a port already exists
   - Bypassing an established abstraction with a raw client
   - State written to a module global or singleton instead of an explicit owner

   **Major** (design cost, paid later):
   - New external collaborator with no port — no seam means untestable
   - Optional constructor dependency added "to simplify tests" (use a Fake instead)
   - New shared mutable state across components
   - One bounded context reaching into another's models or storage
   - A "manager"/"service" class accumulating unrelated responsibilities
   - Behaviour that obviously belongs on an entity pushed into a service (anaemic model)
   - Config object threaded through many layers instead of injecting the resolved value
   - New public API duplicating an abstraction that already exists nearby

   **Minor** (alignment):
   - Module in the wrong folder for what it actually is (adapter living under services)
   - Public symbol not exported where its peers are
   - Naming that fights the established vocabulary
   - Test reaching across the boundary it is meant to respect

5. **Check the seams.** Every new external collaborator — HTTP, DB, queue, filesystem,
   clock, randomness, subprocess — should enter through a port with at least one Fake or
   Null implementation. Constructors should require all collaborators in production.

6. **Confirm § 4 of the protocol is satisfied**, then **generate report** → `reviews/architecture-review-issues.md`

## Severity Model

| Severity | Indicators |
|----------|------------|
| Critical | Hard boundary violation; direct infrastructure call in domain; abstraction bypassed |
| Major | Missing seam or port; optional collaborator; god class; cross-context leakage; config tunnelling |
| Minor | Misplaced module; naming drift; missing export |

## Output Format

Per [`review-protocol.md`](../../docs/review-protocol.md), with two extra fields on each finding:

```markdown
**Principle violated:** e.g. dependency inversion / package boundary / seam-at-boundary
**Suggestion:** the concrete refactor — introduce port `X`, move the call into adapter `Y`
```

If the project has ADRs or active design specs, close with an **Alignment** section stating
whether the change satisfies them. Drift from a merged, authoritative spec is Critical;
drift from a draft is Major.

## Example Usage

```
review-architecture              # Current branch vs main
review-architecture feat/foo     # Specific branch
review-architecture feat/foo dev # Different base
review-architecture 3574         # PR/MR by number
```

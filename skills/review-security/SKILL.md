---
name: review-security
description: Review branch or pull-request changes for application-level security issues — secrets, injection, path traversal, broken authz, weak crypto, vulnerable dependencies. Use before merging changes that touch an external boundary.
args:
  - name: compare_ref
    description: "Branch to review, OR a PR/MR number (default: current branch). When a number is given, the source/target branches are resolved from the git platform."
    required: false
  - name: base_ref
    description: Base branch to compare against (default: main)
    required: false
  - name: report_path
    description: "Path the report must be written to, when a caller pins it (default: reviews/security-review-issues.md)"
    required: false
---

# Security Review Skill

Reviews changes for **application-level security**: what an attacker could do with this
diff. Examples below are Python; the vectors are not.

**Scope:** application code. Infrastructure and network hardening are out of scope unless
the diff touches deployment configuration.

**Protocol:** [`docs/review-protocol.md`](../../docs/review-protocol.md) — arguments, ref resolution, exhaustiveness, severity levels, report shape. Read it first.
Its § 4 *Be exhaustive* is mandatory; the lens steps it refers to are steps 2–4 (*Find the trust boundaries*, *Apply the security lens*, *Check dependencies*) below.

## Process

1. **Resolve refs and gather the diff** — per [`review-protocol.md`](../../docs/review-protocol.md).

2. **Find the trust boundaries this diff touches.** Security findings cluster at
   boundaries, so classify the changes first: HTTP routes, message/queue handlers,
   settings and environment, subprocess and shell, filesystem paths, deserialization,
   token and auth handling, cryptography, logging, dependency manifests. A diff touching
   none of these is usually a short review — say so rather than manufacturing findings.

3. **Apply the security lens**

   **Critical** (exploitable as-is — blocks merge):
   - Secret, credential or API key committed in source, config or a test fixture
   - Shell execution with `shell=True` (or equivalent) on attacker-influenced input
   - `pickle.loads`, unsafe YAML loading, `eval`, `exec` on untrusted data
   - Query built by string concatenation or interpolation with user input
   - Path joined from user input without containment — `..` traversal, especially before
     a read or write
   - New endpoint or message handler with no authn/authz check where its peers have one
   - Token validation disabled, signature unverified, `alg=none` accepted
   - TLS verification disabled
   - Hard-coded key, reused IV, MD5/SHA1 used for security, or a non-cryptographic RNG
     used for tokens, passwords or IDs
   - Secret, token or full PII payload written to logs
   - CORS opened to `*`, or an open redirect introduced

   **Major** (likely exploitable — fix before merge):
   - No validation at a trust boundary (request body, message payload, uploaded file)
   - Error responses leaking stack traces, internal paths or database errors
   - Authentication present but authorization missing — any authenticated user can act on
     another's resources. Check object-level access, not just route-level.
   - No rate limiting or replay protection on a new public or auth-sensitive endpoint
   - Dependency added with known CVEs, or unmaintained, or pinned to a range that resolves
     to a vulnerable release
   - Settings field holding a secret without a secret-wrapper type
   - File written non-atomically to a path other processes read
   - Long-lived task holding secrets in memory with no rotation hook

   **Minor** (defence in depth):
   - User identifiers logged without a consistent redaction policy
   - HTTP client with no explicit timeout
   - Permissive file modes on write
   - Security headers missing where peer responses set them
   - Test fixtures using realistic-looking secrets that could be mistaken for real ones

4. **Check dependencies.** For each modified manifest, list what was added or bumped, and
   flag anything known-vulnerable, abandoned, or pulled from an unexpected index. Suggest
   running the ecosystem's audit tool (`pip-audit`, `npm audit`, `cargo audit`, …).

5. **Confirm § 4 of the protocol is satisfied**, then **generate report** → `reviews/security-review-issues.md`

## Severity Model

| Severity | Indicators |
|----------|------------|
| Critical | Exploitable as-is: secret leak, code execution, injection, broken auth, broken crypto |
| Major | Exploitable under realistic conditions: weak validation, missing authz, vulnerable dependency |
| Minor | Hygiene gap with no immediate exploit path |

## Output Format

Per [`review-protocol.md`](../../docs/review-protocol.md), with one extra field that is
required on every finding:

```markdown
**Vector:** how it is reached — e.g. injection / path traversal / broken authz / secret in source
**Why it matters:** the attacker scenario in one concrete sentence
```

"Why it matters" must name what an attacker gains. If you cannot write that sentence, the
finding is speculative — leave it out.

Close with a **Dependency Notes** section and the standard summary.

## Exclusions

- Style and lint issues — handled elsewhere.
- Performance concerns with no denial-of-service angle.
- Threat-model questions about infrastructure this diff does not change.

## Example Usage

```
review-security              # Current branch vs main
review-security feat/foo     # Specific branch
review-security feat/foo dev # Different base
review-security 3574         # PR/MR by number
```

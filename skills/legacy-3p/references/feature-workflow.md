<!-- Generated from docs/feature-workflow.md by tools/sync-references.py. Edit the source, not this copy. -->

# Feature Workflow (Spec-First, Test-First)

For bugs, see [`bugfix-workflow.md`](bugfix-workflow.md). For features, always:

1. **Business need in the work item.** Stated as *As a `<role>` / I want `<capability>` /
   so that `<outcome>`*. Restate it verbatim in the PR description. If missing, fix the
   work item or ask the user before proceeding.
2. **Challenge the scope before slicing it.** Capture the need as a very short PRD, then
   offer the user reductions — fewer functional cases, fewer users, an edge case left to
   fail explicitly. Cutting the request comes before splitting it; slicing a request that
   should have been half its size just produces more slices.
3. **Propose vertical slices by default.** Split the agreed scope into the smallest
   end-to-end slices that each deliver observable value, and let the user pick the first.
   Implement one slice at a time, repeating steps 4–9 per slice. Skip slicing only if the story is
   genuinely trivial (single rule, single layer, a couple of hours).
4. **Agree business rules and the test list with the user first.** List the rules in
   domain terms, then for each rule list the tests (`given_..._when_..._then_...`, one line
   each, no code). Cover nominal, boundary, and negative cases. Get user agreement before
   writing anything.
5. **Write the agreed tests and confirm they fail** for the right reason. Follow
   [`testing-rules.md`](testing-rules.md).
6. **Implement** to make them pass, following
   [`code-design-rules.md`](code-design-rules.md) and
   [`hexagonal-architecture-rules.md`](hexagonal-architecture-rules.md). Out-of-scope work
   becomes a `FIXME` or a follow-up work item — never silent expansion. If a missing rule
   surfaces, go back to step 4.
7. **Run the full test suite** as your post-change verification.
8. **PR description must contain:** business need (verbatim), business rules, summary,
   changes, tests added / FIXMEs / coverage gaps, open questions, related work items.
9. **Run the review skills** (`review-pr`, `review-complexity`, `review-testing`, and
   `review-security` if the change touches a trust boundary) and fix what they surface, then hand off to the `merger` agent.

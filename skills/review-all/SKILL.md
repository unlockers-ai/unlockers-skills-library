---
name: review-all
description: "Run the five verdict lenses (complexity, testing, architecture, security, slop) on a branch or PR at once — one subagent per lens, in parallel, on one pinned commit — write a single summary of what they found, and post it to the PR as one comment plus one commit status per lens; then, if findings are to be fixed, run the fix loop: the same reviewers approve the plan and verify the fix, sharing one history of every round, with no second full review. Use before merging a PR, when asked to \"review everything\", \"run all the reviewers\", \"full review\", or whenever a change is substantial enough that one lens is not enough."
args:
  - name: compare_ref
    description: "Branch to review, OR a PR/MR number (default: current branch). When a number is given, the source/target branches are resolved from the git platform."
    required: false
  - name: base_ref
    description: "Base branch to compare against (default: main)"
    required: false
---

# Review All

The orchestrator. It reviews nothing itself: it pins the commit, launches one subagent
per lens, has [`scripts/review_all.py`](scripts/review_all.py) check what they delivered,
writes `reviews/review-summary.md`, and publishes. Read
[`docs/review-protocol.md`](../../docs/review-protocol.md) § 1, § 5, § 6 and § 7; the
rest is for the subagents.

## Lenses

Five of the protocol's "The reviewers" table: `review-complexity`, `review-testing`,
`review-architecture`, `review-security`, `review-slop` — the lenses whose findings are
verdicts on the change. Two are left out on purpose:

- `review-pr`, the catch-all: watched over several PRs, everything it found one of the
  others had also found. If it ever finds something the five missed, put it back.
- `review-impact`: it reports blast radius, which every modification has by definition,
  so as a review it raises an issue for exactly the thing we set out to do. It stays a
  skill to run by hand *before pushing*, where "which suites must pass" is the question.

## Process

1. **Pin the commit, on disk too.** Resolve the refs once, per protocol § 1, and record
   the three SHAs (compare, base, merge base). Then materialise the compare commit in a
   scratch directory outside the checkout:

   ```bash
   git worktree add --detach "$SCRATCH/review-<compare sha>" <compare sha>
   ```

   The subagents get the SHAs and that path, never branch names or this checkout: the
   lenses run linters, analysers and tests against files on disk, so a review from a
   checkout on `main` would measure `main` under the PR's SHA, and five subagents checking
   out the same tree would clobber each other and any other session sharing it.

2. **Clear the previous run.** Delete the five report files under `reviews/` in this
   checkout (the paths in the protocol's table) and `reviews/review-summary.md`. A stale
   report from an earlier commit must not be mistaken for this run's; step 4 would catch
   it, but only by its SHA. On a PR's first review, also delete `reviews/rounds/`,
   `reviews/fix-plan.md` and `reviews/decisions.md`: they belong to the previous PR.

3. **Launch five subagents in one message**, so they run in parallel, on the strongest
   model available (a review is a hard task; never inherit a cheaper session model). Each
   prompt says:
   - read the lens's `SKILL.md` and follow it in full, including everything it links —
     protocol § 4 (exhaustiveness) is mandatory;
   - review compare `<sha>` against base `<sha>` (merge base `<sha>`), naming the
     branches only as context; run every tool and every read in the worktree at
     `<path>`; do not fetch, checkout or change any working tree;
   - `report_path`: the lens's path under `reviews/` **in this checkout**, the report
     opening with the protocol's `**Compare:** … **Base:** … **Merge base:** …` line;
   - report findings, fix nothing, and reply with the report's closing summary line
     only (`X Critical, Y Major, Z Minor`);
   - it will be resumed later to review the fix plan and verify the fix (protocol § 7).

   **Keep the five agent IDs.** The fix loop resumes these same reviewers (in Claude Code,
   `SendMessage` to the ID); a fresh reviewer knows nothing of what was decided and
   reopens it.

4. **Check delivery.**

   ```bash
   python3 scripts/review_all.py collect --compare <sha>
   ```

   A lens has delivered when its report exists, pins this compare SHA and closes with a
   summary line; the script prints one table row per lens. A row that says *not
   reviewed* is **red**: re-run that one lens once, collect again; if it is still red, it
   stays in the summary as not reviewed — never as "0 findings" — and the run is
   incomplete.

5. **Write `reviews/review-summary.md`.** Paste the table from step 4, then read each
   report's Critical and Major headings — not the whole file; the reports stay the
   record. In a verification round, list only *open* and new findings:

   ```markdown
   # Review summary: <compare ref>

   **Compare:** <sha> (<ref>)  ·  **Base:** <sha> (<ref>)  ·  **Merge base:** <sha>

   | Lens | Critical | Major | Minor | Report |
   |------|----------|-------|-------|--------|
   <the rows the script printed>

   ## Critical
   - **<lens>** — <finding title> — `path:line`

   ## Major
   - …

   **Verdict:** <one paragraph: mergeable as is / after the Majors / blocked, and by what.>
   ```

6. **Publish**, when the review is of a PR (a number was given, or `gh pr view` on the
   branch finds one):

   ```bash
   python3 scripts/review_all.py publish --pr <N>
   ```

   That takes the compare SHA from the summary's header, re-checks the five reports
   against it, refuses if the table you pasted disagrees with them, and posts the summary
   as one PR comment (one per reviewed SHA, updated in place on a re-run) plus a commit
   status `review/<lens>` on that SHA per lens: green when it ran, red on a Critical,
   error when not reviewed. The statuses are the record of what was reviewed, not a gate,
   unless the repo makes them required checks. It refuses if the PR head has moved since
   step 1: verify the new head as in fix loop step 5, never with a second full run.

   The script speaks GitHub. On GitLab or Azure DevOps, post the summary as one MR/PR
   comment by hand (`glab mr note`, or `azure-devops-pr`) and skip the statuses — or
   replace `GhCli`: the `GitHub` protocol in the script is the contract, and
   `scripts/github_contract.py` the tests a replacement must pass. With no PR, the summary
   in `reviews/` is the result; publishing can follow once one exists.

7. **Clean up.** `git worktree remove` the scratch tree. With no Critical and no Major,
   stop here. Otherwise, when whoever called wants the findings fixed, run the fix loop
   below; this skill still fixes nothing itself.

## The fix loop

A full review runs **once** per PR. After it, the same reviewers approve the plan before
any code changes, then check the result. No reviewer gets a second exhaustive pass —
protocol § 7 says why, and what a resumed reviewer may answer.

The reviewers converge because they share one context that grows by a round at a time:
the archived reports of every lens and `reviews/decisions.md`. Every reviewer reads the
whole of it; one that sees only its own report re-raises what another lens settled.

**Archive every round.** Once its summary is written, copy the five reports,
`review-summary.md` and, from the second round on, `fix-plan.md` into
`reviews/rounds/r<n>/` (`r1` is the first review). The next round rewrites the reports in
place; the archive is the history.

1. **Write the fix plan** to `reviews/fix-plan.md`: one line per Critical and Major,
   by lens and number, and for each: *fix* (the specific change), *won't fix* (why), or
   *defer* (to an issue, named). Minors: say which are fixed; the rest are deferred as
   a group.

2. **Plan review.** Resume, in one message, every reviewer that reported a Critical or
   Major. Each gets the **whole** plan, not only its own lines, so a conflict between
   lenses (one asks to remove a check that another asks to test) comes up before any code
   is written. If an objection holds, change the plan and send only the changed lines
   back to whoever objected. If two lenses still disagree after that, the user decides;
   don't pick one yourself.

3. **Record the decisions** in `reviews/decisions.md`: your conclusion on every
   Critical and Major of the round, one line each, with the round, the lens and number,
   the decision (*fix: <the agreed change>*, *won't fix*, *deferred → #n*, or how a
   conflict between lenses was settled) and the reason. A *fix* line records the
   approach, not that it worked: verification judges that, and you append
   *verified r<n>* once it does. Append each round; never rewrite earlier lines.

   ```markdown
   - r1 · testing #2 · fix: assert the whole Booking, not its id · a partial assert let the date bug through
   - r1 · slop #1 vs security #3 · keep the check, move it into the deploy step · settled by the user
   - r1 · complexity #4 · deferred → #212 · touches three slices, out of this PR
   ```

4. **Implement with a fresh fixer**: a new subagent each round, not a resumed one,
   working in its own worktree on the PR branch (never this checkout). Its prompt
   carries the agreed plan and `reviews/decisions.md`, not the reports. It commits,
   runs `<run tests>` and the project's other gates, and pushes. A resumed fixer
   accumulates every round's context and ends up costing more than all the reviews.

5. **Verify.** Pin the new head, add its worktree (Process step 1), and resume, in one
   message, only the reviewers that reported a Critical or Major, with the new compare
   SHA, the previous one, and the worktree path. Each rewrites its report for the new
   SHA, following protocol § 7. A clean lens is not resumed: its report, pinned to the
   last round it was reviewed in, is carried; one with an open Critical or Major is
   *not reviewed*. Then `collect --compare <new> --previous <r_n-1> --previous <r_n-2> …`,
   passing every earlier round's compare SHA; it prints the `**Previous:**` header line
   above the table: paste both into the summary, never type them. Then publish,
   `git worktree remove`, as in Process steps 4–7, and let step 6 below decide what
   comes next.

6. **Stop** when no lens reports an open Critical or Major. At most **one** further
   plan → fix → verify loop is allowed. What is still open after it goes to the user
   with the reports, not into a third loop. New findings outside the change are filed
   as a follow-up issue and never start a loop.

**When a reviewer can't be resumed** (the session ended, or its ID is lost), start a
fresh one on the same lens and have it follow protocol § 7 as though it had been
resumed — the archive and `decisions.md` are what make that possible.

**Cost:** resuming after the prompt cache has expired rewrites the reviewer's cache,
roughly its 60–100k context. That is still an order of magnitude cheaper than a fresh
exhaustive review of the lens.

## Example usage

```
review-all              # current branch vs main
review-all 141          # PR/MR by number
review-all feat/foo dev # branch against another base
```

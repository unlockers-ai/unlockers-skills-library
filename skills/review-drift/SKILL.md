---
name: review-drift
description: Design-drift review — given what recently landed on main, what does the REST of the codebase now owe us? Finds new duplication, a good local idea that should spread, a rule stated but unapplied, a third workaround for one root cause, and proposes fixes with a blast radius. Runs after merges (nightly, from the bundled runner) or by hand on a window. Report, never fix. Use when asked "what did the last merges imply", "design drift", "what should spread", "review beyond the diff".
args:
  - name: base
    description: "Start of the window: a commit/ref on main. Default: the newest `drift/*` tag (the last reviewed commit), else origin/main~5 (about five merges)."
    required: false
  - name: report
    description: "Report path (git-ignored or outside the repo). Default: .design/drift-<today>.md"
    required: false
---

# Design-Drift Review

Not a diff review. A diff reviewer answers "is this change good?"; this one answers:

> **Given what changed recently, what does the rest of the codebase now owe us?**

Recent changes are *evidence*. Each either (a) introduced something the codebase already
had, (b) worked around something for the second or third time, (c) introduced a good idea
locally that the rest should adopt, (d) wrote down a rule the rest does not yet follow, or
(e) made an already-bad place worse. Find those consequences *outside the diff*; propose
fixes with an honest blast radius.

The `review-*` skills cannot do this by construction: they are bounded by a diff, and every
finding here lives in a file the diff did not touch. [`review-protocol.md`](references/review-protocol.md)
§ 4 asks a diff reviewer to check the siblings of what changed; this skill makes that the
whole job, over the codebase, unbounded in time.

## 0. Preconditions

1. **Candidate seeds.** Run [`scripts/design-candidates.sh`](scripts/design-candidates.sh)
   from the repo root (the nightly runner does it for you). It writes to `.design/` —
   clone pairs (`jscpd`, and `pylint` for Python), complexity and argument-count hits
   (`ruff` for Python), files that change together (`cochange.json`), and `tools.txt`,
   which says which of those tools were missing. These are **candidate seeds and candidate
   siblings**, tagged by source — not findings. A missing tool is not a failure; it goes
   into the report's "what you did not check".
2. **CodeScene, optional — but never silently.** If the CodeScene MCP server is available
   (`ToolSearch` query
   `select:mcp__codescene__analyze_change_set,mcp__codescene__code_health_review,mcp__codescene__code_health_score`),
   call `analyze_change_set(base_ref=<base>, git_repository_path=<this checkout>)` and keep
   the result for step 4. If the tools are there and the call **errors**, the review fails:
   say so at the top and stop — a configured tool that broke must not produce a report that
   looks like one run with it. If CodeScene is simply not set up, carry on, and say so in
   the header.
3. **Don't re-derive what is already known.** Read the previous report's not-findings
   ledger when the runner names one, and the open issues (`gh issue list --limit 100
   --state open`; `glab issue list`, or `az boards query` on other hosts). A seed ruled out
   with a stated reason is not re-investigated unless this window touched that reason; a
   finding that is already an issue is reported as "already #N" with only what you add.
4. **Read the rules** the project has written down: its conventions doc (`CLAUDE.md`,
   `AGENTS.md`), and whichever of these it has adopted —
   [`code-design-rules.md`](references/code-design-rules.md),
   [`hexagonal-architecture-rules.md`](references/hexagonal-architecture-rules.md),
   [`design-patterns.md`](references/design-patterns.md),
   [`accidental-complexity-guide.md`](references/accidental-complexity-guide.md),
   [`testing-rules.md`](references/testing-rules.md). They define "good" and "cruft"
   *here*; do not import your own taste where they speak. Note which of them the window
   **edited** — a newly written rule is a seed.

## 1. The window

Establish it from merges, never from dates: `git log --merges --first-parent --oneline
<base>..origin/main`. `--since` matches commit timestamps, which after rebases and
cherry-picks do not track when work landed. In a history with no merge commits
(squash-only), use the first-parent commits instead. State the exact range and file count
at the top of the report.

Reading order — this matters more than anything else in the method:

1. `git log --format='%n===== %h %s%n%b' --stat <base>..origin/main` — **commit messages
   first.** Where they state their reasons, those reasons are the seeds.
2. `git show` of each merge.
3. The full diff **only** for files a seed points at.

## 2. Seeds — the claims the diff makes

The best seed is a *justification*: a sentence in a commit message or a doc that names its
own rule ("one list, not a habit"; "only the tokens are secrets"; "a capability is named,
never quoted"). Quote it. Then walk the mechanical list, one grep per seed — expect a third
to die on the first grep:

- a new type / value object / wrapper; a new helper;
- a new *pattern* (validating, logging-and-continuing, reading config, resolving a name);
- a **workaround** — "because X does Y, we Z";
- a **rule newly applied** in one place;
- a **rule newly stated** in the docs or the conventions file — the doc is in the diff, the
  code it describes is not: the rule is the seed, every unfixed place a sibling;
- a **fix** of a bug class in one place; a **deletion**;
- a commit whose **own diff contradicts the rule it states** — stronger than a gap; name it;
- a `.design/` candidate whose *reason* you can name.

When a seed names a **join or a setting, read the config file** — the seed list is
code-shaped, and a missing line of YAML is as real a sibling as a missing function call.

## 3. Siblings — the whole codebase, unbounded in time

Only the seed is windowed. Grep *outside the touched files*:

- new type → where is the same primitive still naked?
- new helper → where is the same logic still inlined?
- new pattern → where does the old one survive? are there now two ways?
- workaround → is this the 2nd/3rd for one root cause? then the root cause is the finding
- rule stated/applied → where else does it visibly apply, unapplied?
- fix → does the bug class sit in a sibling adapter/route/script?
- deletion → is the same dead weight elsewhere?
- **trace one real input through every join the seed touched.** A miss the tests
  canonicalise away is found by execution, not by grep.

`cochange.json` lists files that move together without necessarily importing each other —
they are joined by something implicit, usually a string key, and are siblings grep will
not find by name.

Cite line numbers from `grep -n` on HEAD, never from diff hunks. A seed with no siblings
goes to the ledger with the search you ran. A diff fact whose *consequence* lives outside
the diff (a feature gated on an event that never fires) is a finding about the consequence.

## 4. Worsened places

For each file the window touched that got worse, or was already a hotspot, say what the
change tells you the file *wants to become* — one of: a list, a type, a value object for
the clump, a port, a split.

- **With CodeScene:** `analyze_change_set` (step 0) names what degraded, with thresholds;
  `code_health_review` on a file gives smells with line ranges.
- **Without it:** the `.design/` complexity hits plus churn —
  `git log --since="6 months ago" --format= --name-only | sort | uniq -c | sort -rn | head`
  — give the hotspots; the [tools table](references/accidental-complexity-guide.md#tools-that-measure-these)
  says which rule measures which smell.

Either way, remember a health score cannot see a semantic default that lies: a green
adapter says nothing about its inbound contract.

## 5. The rule the codebase is discovering

When two or three seeds are local instances of one general rule, state it in a sentence and
say whether it belongs in `docs/` or the conventions file. A doc line is a valid, cheap
finding.

## Report — two files

Write the markdown to the `report` path, and **beside it the same name with `.md`
replaced by `.findings.json`** (`drift-2026-09-23.md` → `drift-2026-09-23.findings.json`,
never `drift-2026-09-23.md.findings.json`) — the machine-readable half that
[`scripts/drift_publish.py`](scripts/drift_publish.py) turns into issues, comments and a
digest. Its shape (the script's docstring is the authority):

```json
{"window": {"base": "<sha>", "end": "<sha>", "ref": "origin/main"},
 "models": ["opus"],
 "findings": [{"title": "…", "blast_radius": "local|module|codebase|doc",
               "confidence": "high|medium|low", "sensitive": false,
               "already_issue": null, "models": ["opus"],
               "body": "<the finding's full markdown: evidence, siblings, radius, proposal, risk, confidence>"}],
 "not_findings": 14, "rule_discovered": "<one sentence>" }
```

`already_issue` is the open issue number when one covers the finding — then `body` holds
only what you add. `sensitive` flags a security- or user-facing consequence.

The markdown, in this order:

1. **Header**: `window: <base>..<end>`, files, tools available (CodeScene yes/no, and
   `tools.txt`), **what you did not check**, the window you rejected and why.
2. **Findings, ranked by leverage** — the fix that removes the most future workarounds
   first; a long sibling list is scope, not importance. Each:
   - **Title** — the design consequence, not the symptom
   - **Evidence** — commit + file:line + the quoted claim
   - **Siblings** — every location, file:line; this list *is* the blast radius and later
     *is* the fix's checklist
   - **Blast radius** — `local` / `module` / `codebase` / `doc`; flag security- or
     user-facing consequences even when the radius is small
   - **Proposal** — ordered steps; for `codebase`, the order (driven by what reads each
     sibling) and an explicit **stop-point**
   - **Risk & effort** — small/medium/large; the test that proves it, written first
   - **Confidence** — high/medium/low and *why you might be wrong*
   - **Already #N** when an open issue covers it — then only what you add
3. **Not-findings ledger** — a table `seed | search | verdict`. Rows a next run would
   plausibly re-derive; a seed nobody would think of twice needs no row.
4. **The rule(s) the codebase is discovering.**
5. **Only the tools saw this** — what CodeScene or the `.design/` candidates surfaced that
   grep and git did not. If nothing, say so: it is how the tools earn their place.

An empty findings list is a valid outcome for a quiet window. Say which seeds you walked.

## Rules of engagement

- **Outside the diff, always.** A finding wholly inside the touched files is a diff-review
  finding; leave it out unless it anchors siblings elsewhere.
- **Concrete or nothing.** Every claim has a file:line. No "consider looking at".
- **Deliberate exceptions exist — look before generalising**: a comment, a test name, a
  conventions-file paragraph, a commit message that says "considered and not taken".
- **Report, do not fix.** Someone else decides whether to spend the radius. Findings become
  issues when the owner says so.
- **Write the report files and stop.** No `git add`, no commit, no push, no PR, no issue —
  the runner, or the person who invoked you, publishes. A reviewer that pushes on its own
  is a reviewer nobody reads first.
- **Say what you did not check**, at the top.

## Running it

**By hand**, on the last few merges:

```bash
skills/review-drift/scripts/design-candidates.sh
claude -p "/review-drift report=.design/drift-report.md"
python3 skills/review-drift/scripts/drift_publish.py \
    --findings .design/drift-report.findings.json --report .design/drift-report.md --dry-run
```

Add `.design/` to the project's `.gitignore`. Reports are about one window and go stale as
soon as main moves, like the review reports in [`review-protocol.md`](references/review-protocol.md) § 6.

**Nightly**, [`scripts/review-drift-nightly.sh`](scripts/review-drift-nightly.sh) does the
whole loop: skip if no merge landed since the newest `drift/*` tag, review in a throwaway
worktree on one or more models, merge their reports, then publish — findings become issues
(or comments on the issue that already covers them), a digest goes to a tracking issue, and
the reviewed commit is tagged `drift/<date>` as the next run's base. Schedule it with cron,
launchd or a CI schedule; its header lists the knobs. Publishing is GitHub (`gh`); on
another host, replace `drift_publish.py` — the findings JSON is the contract.

Running two models and merging finds more than either alone: they seed differently. The
cost is two reviews; start with one.

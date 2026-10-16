# Unlockers Skills Library

A reusable library of **agent definitions**, **skills**, and the **documentation** they
reference — for code review, testing discipline, refactoring, and getting PRs merged.

**Examples are Python. The rules are not.** Nothing here is tied to Python except the code
in the examples, and translating an example is something an agent does well on request —
so the examples stay short and concrete rather than being written five times. Git-platform
commands default to GitHub's `gh` CLI, with GitLab (`glab`) and Azure DevOps (`az`) noted
where they differ; the one skill that cannot be generalised says so in its name.

[`AGENTS.md`](AGENTS.md) is the map — read that first if you are an agent working here, or
a human deciding where something new belongs. [`diagrams/`](diagrams/) has the visual
version: the [merger's lifecycle](diagrams/merger-lifecycle.md) and
[how the pieces relate](diagrams/library-map.md).

## Layout

```
agents/      Subagent definitions (autonomous task-performers)
skills/      Skills — task-scoped capabilities (SKILL.md per skill)
docs/        Reference documentation that the skills and agents point to
tools/       Keeps the skills installable: bundles docs into each skill, validates the format
```

### Agents

| Agent | What it does |
|-------|--------------|
| [`merger`](agents/merger.md) | Full PR merge lifecycle: push, enable auto-merge, monitor CI and reviews, fix, rebase on conflicts, escalate to human approval. |
| [`refactor`](agents/refactor.md) | Clean-code refactoring specialist — restructures without changing behaviour. |

### Review skills

All seven share one contract — arguments, ref resolution, exhaustiveness, severity levels,
report shape — documented once in [`docs/review-protocol.md`](docs/review-protocol.md). Each
skill below adds a single lens. They are read-only: they report, they do not fix.

| Skill | Lens | Report |
|-------|------|--------|
| [`review-pr`](skills/review-pr/SKILL.md) | Catch-all: bugs, design, security, coverage in one pass | `reviews/code-review-issues.md` |
| [`review-complexity`](skills/review-complexity/SKILL.md) | Accidental complexity — defensive checks, redundant exception handling, over-engineering | `reviews/complexity-review-issues.md` |
| [`review-testing`](skills/review-testing/SKILL.md) | Test quality and coverage | `reviews/testing-review-issues.md` |
| [`review-architecture`](skills/review-architecture/SKILL.md) | Boundaries, seams, dependency direction | `reviews/architecture-review-issues.md` |
| [`review-security`](skills/review-security/SKILL.md) | Secrets, injection, authz, crypto, dependencies | `reviews/security-review-issues.md` |
| [`review-impact`](skills/review-impact/SKILL.md) | Blast radius; which suites must pass — run this *before* pushing | `reviews/impact-analysis.md` |
| [`review-slop`](skills/review-slop/SKILL.md) | Correct work that shouldn't be in the diff — verbose prose, duplication across siblings, ceremony, checks in the wrong layer | `reviews/slop-review-issues.md` |

`review-pr` alone is enough for a small change. For anything substantial the focused passes
find more than the catch-all does, and they run in parallel. `review-slop` is for diffs heavy
in docs, config, CI or deploy plumbing, where the other lenses have little to say.

### Other skills

| Skill | What it does |
|-------|--------------|
| [`scope-challenge`](skills/scope-challenge/SKILL.md) | Capture a feature request as a very short PRD, then challenge it for the smallest valuable scope before building. |
| [`write-tests`](skills/write-tests/SKILL.md) | Write or improve tests: fakes over mocks, whole-object assertions, short bodies. |
| [`adapter-contract-testing`](skills/adapter-contract-testing/SKILL.md) | Hold a fake and its real adapter to one shared contract, so the fake cannot drift. |
| [`bugszero-root-cause`](skills/bugszero-root-cause/SKILL.md) | Fix a bug by removing the design weakness that allowed it, not just the symptom. |
| [`legacy-3p`](skills/legacy-3p/SKILL.md) | Change legacy code in order: Protect with characterization tests, Prepare by refactoring, Produce with TDD. |
| [`review-drift`](skills/review-drift/SKILL.md) | After merges, what the *rest* of the codebase now owes: duplication, an idea that should spread, a rule stated but unapplied. Nightly runner and GitHub issue publisher included; CodeScene optional. |
| [`quality-gate`](skills/quality-gate/SKILL.md) | Objective thresholds as a backstop for when review nudges don't land. Final CI stage, Claude Code hook, or both. |
| [`azure-devops-pr`](skills/azure-devops-pr/SKILL.md) | **Azure DevOps only.** Create a PR; review threads, replies, follow-up work items, auto-complete. Ships its own scripts. |

### Docs

| Doc | Referenced by |
|-----|----------------|
| [`review-protocol.md`](docs/review-protocol.md) | every `review-*` skill |
| [`testing-rules.md`](docs/testing-rules.md) | `write-tests`, `review-testing` |
| [`testing-review-guide.md`](docs/testing-review-guide.md) | `review-testing` |
| [`adapter-contract-testing.md`](docs/adapter-contract-testing.md) | `adapter-contract-testing` |
| [`accidental-complexity-guide.md`](docs/accidental-complexity-guide.md) | `review-complexity`, `refactor` |
| [`bugfix-workflow.md`](docs/bugfix-workflow.md) | `write-tests`, `bugszero-root-cause`, testing rules |
| [`bugszero-root-cause.md`](docs/bugszero-root-cause.md) | `bugszero-root-cause` |
| [`3p-protect-prepare-produce.md`](docs/3p-protect-prepare-produce.md) | `legacy-3p` |
| [`feature-workflow.md`](docs/feature-workflow.md) | feature development, `scope-challenge` |
| [`code-design-rules.md`](docs/code-design-rules.md) | `review-pr`, `review-complexity`, `refactor`, feature workflow |
| [`hexagonal-architecture-rules.md`](docs/hexagonal-architecture-rules.md) | `review-architecture`, `review-pr`, testing rules, feature workflow |
| [`design-patterns.md`](docs/design-patterns.md) | `refactor`, `review-architecture` |
| [`slop-review-guide.md`](docs/slop-review-guide.md) | `review-slop` |

## Installing

Every skill follows the [Agent Skills](https://agentskills.io) format — a directory with a
`SKILL.md` — so the same files load in Claude Code, OpenCode, GitHub Copilot and the other
clients that read it. Each skill is self-contained: the docs it relies on are bundled in its
`references/` directory, so installing one skill never leaves a dangling link.

**OpenCode, GitHub Copilot, Cursor, Codex and others** — with the
[`skills`](https://github.com/vercel-labs/skills) CLI:

```bash
npx skills add unlockers-ai/unlockers-skills-library             # choose skills and clients interactively
npx skills add unlockers-ai/unlockers-skills-library --skill '*' -a opencode -y
npx skills add unlockers-ai/unlockers-skills-library -g          # for every project (~/.config/opencode/skills, ~/.copilot/skills)
npx skills update                                                # pull the latest version
```

Project installs land in `.agents/skills/`, which OpenCode and Copilot both read; commit them
or the `skills-lock.json` the CLI writes, so the team gets the same versions.

**Claude Code** — as a plugin, which also brings the agents:

```
/plugin marketplace add unlockers-ai/unlockers-skills-library
/plugin install unlockers-skills@unlockers
```

Skills are then named `unlockers-skills:review-pr` and so on. Update with
`/plugin marketplace update unlockers`, or enable auto-update for the marketplace under
**Marketplaces** in `/plugin`. The `npx skills` route above works for Claude Code too, if you
want the skills without the agents.

**By hand** — copy a directory from `skills/` into `.claude/skills/`, `.opencode/skills/`,
`.github/skills/` or `.agents/skills/`. Copy the whole directory: some skills
(`quality-gate`, `azure-devops-pr`, `review-drift`) ship scripts and config next to `SKILL.md`.

**Agents** are not part of the Agent Skills format, so each client has its own place for them.
The files in `agents/` carry frontmatter for both Claude Code and OpenCode:

- Claude Code: the plugin installs them, or copy into `.claude/agents/`.
- OpenCode: copy into `.opencode/agents/` (or `~/.config/opencode/agents/`). The file name is
  the agent name.
- GitHub Copilot: copy into `.github/agents/` and rename to `<name>.agent.md`.

The agents link to `docs/` in this repository, so outside a plugin install they read those
rules from GitHub.

The review skills and the merger agent take an optional PR/MR number or branch and default
to the current branch against `main`.

Skills that reference "the project's conventions doc" mean whatever your repo uses —
`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`.

## Sources

Distilled from real project agent and skill definitions and made project-neutral. The
methodology notes behind `bugszero-root-cause` and the 3P legacy approach are
[Johan Martinsson's](https://martinsson-johan.blogspot.com/); BugsZero is Arlo Belshee's,
via the [BugsZero Kata](https://github.com/martinsson/BugsZero-Kata).

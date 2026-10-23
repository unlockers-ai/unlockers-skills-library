# Working in This Repository

This is a library of agent definitions, skills, and the documentation they reference. It
holds no application code. Everything here is prose that an agent reads and acts on, so the
quality bar is whether an agent given only this file plus one skill would do the right
thing.

Copy this file to `CLAUDE.md` or symlink it if your tooling expects that name.

## The map

Three kinds of file, and the distinction matters when adding one:

| Directory | What lives there | Test for belonging |
|-----------|------------------|--------------------|
| `agents/` | Autonomous task-performers with their own loop and stopping condition | Runs unattended for many steps and decides when it is done |
| `skills/` | Task-scoped capabilities invoked for one job | Has an obvious "I am now doing X" trigger |
| `docs/` | Knowledge that more than one skill needs | Two or more things link to it, or would if it existed |
| `diagrams/` | Visual companions, for humans | It would be weight in a file an agent reads |

Diagrams stay in `diagrams/` and out of the skills and docs: those are read by agents, where
prose is the working format. If a diagram and the prose disagree, the prose is right.

A rule that only one skill uses belongs in that skill. A rule two skills use belongs in
`docs/` — otherwise the copies drift, which is exactly how the review protocol ended up
worded three different ways before it was extracted.

## What is here

**Reviewing.** [`docs/review-protocol.md`](docs/review-protocol.md) is the entry point: it
owns the invocation contract, the exhaustiveness rule, the severity vocabulary, the report
shape, the rules every reviewer obeys, and § 7 for later rounds. The seven `skills/review-*` lens skills each add one lens on top of it. Start
there before reading any individual reviewer. [`skills/review-all`](skills/review-all/SKILL.md) runs five of
them in parallel before merge, then the fix loop: the same reviewers approve the plan and
verify the fix against one shared history, so the rounds converge.

**Testing.** [`docs/testing-rules.md`](docs/testing-rules.md) is the standard;
[`skills/write-tests`](skills/write-tests/SKILL.md) applies it,
[`skills/review-testing`](skills/review-testing/SKILL.md) enforces it with the help of
[`docs/testing-review-guide.md`](docs/testing-review-guide.md), and
[`skills/adapter-contract-testing`](skills/adapter-contract-testing/SKILL.md) covers the
risk the no-mocks rule creates — a fake that has drifted from what it stands in for.

**Deciding what to build.** [`skills/scope-challenge`](skills/scope-challenge/SKILL.md)
runs at the front of feature work: a very short PRD, then reductions offered to the user
before anything is built. It questions *what*; the feature workflow's slicing step then
handles *how*.

**Changing code.** [`docs/bugfix-workflow.md`](docs/bugfix-workflow.md) and
[`docs/feature-workflow.md`](docs/feature-workflow.md) are the defaults, both test-first.
[`skills/bugszero-root-cause`](skills/bugszero-root-cause/SKILL.md) is the escalation when a
bug is the second of its kind. [`agents/refactor`](agents/refactor.md) restructures without
changing behaviour, guided by
[`docs/accidental-complexity-guide.md`](docs/accidental-complexity-guide.md) and
[`docs/design-patterns.md`](docs/design-patterns.md). The target shape both workflows and
the refactor agent aim at is stated in [`docs/code-design-rules.md`](docs/code-design-rules.md)
(inside a type or function) and
[`docs/hexagonal-architecture-rules.md`](docs/hexagonal-architecture-rules.md) (where code
goes). [`skills/port-refactoring`](skills/port-refactoring/SKILL.md) designs the port an adapter
to an external service should become, following
[`docs/port-refactoring-method.md`](docs/port-refactoring-method.md).

**Landing it.** [`agents/merger`](agents/merger.md) owns the merge lifecycle.
[`skills/azure-devops-pr`](skills/azure-devops-pr/SKILL.md) is the Azure DevOps
implementation of the PR-host operations it needs.

**The backstop.** Everything above nudges: reviewers report and hope, agents improve what
they are pointed at. [`skills/quality-gate`](skills/quality-gate/SKILL.md) is what runs when
the nudges do not land — objective thresholds against the codebase as it stands, last in
CI, catching the drift that accumulates when every individual review was right to pass.
It is the only thing here that cannot be reasoned with.

**Beyond the diff.** [`skills/review-drift`](skills/review-drift/SKILL.md) sits between the
two: judgement like a reviewer, but over the whole codebase rather than a diff. After
merges land it asks what the rest of the code now owes — the new type still missing
elsewhere, the third workaround for one root cause, the rule written down and applied once
— and files what it finds as issues. The gate sees that a file got too big; the drift
review sees why, and where else the same thing is happening.

## Conventions for content

- **Examples are Python. The rules are not.** Do not expand an example into five languages —
  it lengthens the page without clarifying the rule, and translation is something an agent
  does well on request. Say "examples are Python" once and move on.
- **State the rule, then the consequence.** A rule an agent cannot see the cost of gets
  dropped the first time it is inconvenient.
- **Show the fix, not the principle.** "Do it like `path/to/file:45`" beats a paragraph.
- **Say when the answer is nothing.** Reviewers especially must be able to return an empty
  report without feeling they have failed.
- **Do not hardcode one project.** Organisation names, branch names, directory layouts and
  toolchain commands are inputs. `main` is the default base branch; `<run tests>` is a
  placeholder. Anything that cannot be generalised goes in the skill's name — see
  `azure-devops-pr`.
- **Platform commands default to GitHub `gh`**, with the GitLab and Azure DevOps equivalents
  noted where they differ.

## Adding a skill

1. Check whether it is a lens on something that exists rather than a new thing. Another
   reviewer is usually a section in an existing one.
2. `skills/<name>/SKILL.md`, with YAML frontmatter: `name`, `description`, and `args` if it
   takes any. The `description` is what gets matched against a user's request — write it to
   be found, listing the phrasings that should trigger it.
3. Put shared knowledge in `docs/` and link to it. Put scripts inside the skill directory,
   not in a repo-level `scripts/` — a skill has to be copyable on its own.
4. Add it to the README tables and to the map above.

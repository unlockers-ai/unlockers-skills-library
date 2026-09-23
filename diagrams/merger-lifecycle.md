# Merger Agent — Lifecycle

What [`agents/merger`](../agents/merger.md) does between "this PR is ready" and "this PR is
merged".

## Setup

Runs once. The interesting parts: a rejected push means the base branch moved, which is a
rebase, which can end in a conflict the agent should not guess at; and a branch with no PR
gets one, with a title written for the whole change rather than copied from the last commit.

```mermaid
flowchart LR
    START([PR is ready]) --> PUSH[Push branch]
    PUSH --> REJ{Rejected?}
    REJ -->|no| ID[Resolve PR id]
    REJ -->|yes| REBASE[Rebase on base]
    REBASE --> CONF{Conflicts?}
    CONF -->|none| PUSH
    CONF -->|textual| FIX[Resolve, re-run tests]
    FIX --> PUSH
    CONF -->|semantic| HUMAN([Ask the user])
    ID --> HAS{PR exists?}
    HAS -->|no| CREATE[Create PR<br/>compose title if &gt;1 commit]
    CREATE --> SUGG[Suggest local reviewers, once]
    SUGG --> AUTO
    HAS -->|yes| AUTO[Enable auto-merge, squash]
    AUTO --> LOOP([Enter monitor loop])

    classDef fix fill:#fff4e6,stroke:#d9822b
    classDef halt fill:#fdecea,stroke:#c62828
    class REBASE,FIX fix
    class HUMAN halt
```

## The monitor loop

Every 60 seconds, until the PR merges or closes. Each iteration reports one line of state
first, so a watching human can see what it thinks is happening.

Read it top to bottom: each gate must be clear before the next one is even looked at. A
failing check means review comments are not read this iteration — there is no point
addressing feedback on code that is about to change.

**Every fix returns to the top.** A push can clear auto-merge and invalidates checks that
had already passed, so nothing continues forward after a change; it re-enters at `Poll`.

```mermaid
flowchart TB
    POLL[Poll PR] --> STATE{PR state?}
    STATE -->|merged| DONE([Merged — report and exit])
    STATE -->|closed| SHUT([Closed by a human — exit])
    STATE -->|open| ARM{Auto-merge<br/>still set?}

    ARM -->|cleared| REARM[Re-enable it]
    ARM -->|set| CI
    REARM --> CI{CI checks?}

    CI -->|running| SLEEP[Sleep 60s]
    CI -->|failing| LOG[Read failed job log] --> FIXCI[Fix lint / tests / deps]
    CI -->|all pass| TH{Open review<br/>threads?}

    TH -->|yes| TRIAGE{Triage each}
    TH -->|none| APPR{Review decision?}

    TRIAGE -->|needs a change| FIXPR[Implement fix, run checks]
    TRIAGE -->|valid, out of scope| DEFER[Open follow-up, link it]
    TRIAGE -->|by design / misread| WHY[Reply with rationale]

    APPR -->|changes requested| TRIAGE
    APPR -->|approved| SLEEP
    APPR -->|not enough approvals| PING[Ping the user once,<br/>then keep looping]

    DEFER --> CLOSE[Reply and resolve thread]
    WHY --> CLOSE
    FIXCI --> PUSH[Commit, push,<br/>re-enable auto-merge]
    FIXPR --> PUSH

    PUSH --> POLL
    CLOSE --> POLL
    SLEEP --> POLL
    PING --> SLEEP

    classDef fix fill:#fff4e6,stroke:#d9822b
    classDef exit fill:#e8f5e9,stroke:#2e7d32
    classDef halt fill:#fdecea,stroke:#c62828
    class FIXCI,FIXPR,PUSH,REARM fix
    class DONE,SHUT exit
    class PING halt
```

## What it never does

- **Merge by hand.** It sets auto-merge and makes the conditions true; the platform merges.
- **Exit while CI is running.** A pending check means sleep and re-poll, not "probably fine".
- **Approve the PR.** Missing human approval is the one blocker it cannot clear — so it
  pings *once* and keeps looping rather than exiting, and the PR lands the moment someone
  approves.
- **Silently resolve a thread it disagreed with.** By-design gets a written rationale;
  out-of-scope gets a rationale *and* a tracked follow-up.
- **Force-push past a conflict it did not understand.** Textual conflicts it resolves;
  semantic ones it escalates.

# Library Map

How the pieces relate. Prose version in [`AGENTS.md`](../AGENTS.md); this is the shape.

## Where each thing acts

Everything in the library sits somewhere on the path from *deciding to change code* to
*that change being live* — and the further right it sits, the less it argues.

```mermaid
flowchart TB
    subgraph W [" Deciding what to write "]
        direction LR
        BF[bugfix-workflow]
        FF[feature-workflow]
        BZ[bugszero-root-cause]
        L3P[legacy-3p]
        BF -.->|second bug<br/>of its kind| BZ
        FF -.->|can't start:<br/>no tests, no seams| L3P
    end

    subgraph T [" Writing it "]
        direction LR
        WT[write-tests]
        ACT[adapter-contract-testing]
        RF[refactor]
        WT -.->|fakes need<br/>holding to a contract| ACT
    end

    subgraph R [" Reviewing it — nudges "]
        direction LR
        RPR[review-pr]
        RC[review-complexity]
        RT[review-testing]
        RA[review-architecture]
        RS[review-security]
        RI[review-impact]
        RSL[review-slop]
        RPR ~~~ RC ~~~ RT ~~~ RSL
        RA ~~~ RS ~~~ RI
    end

    subgraph M [" Landing it "]
        direction LR
        MG[merger]
        ADO[azure-devops-pr]
        MG -->|Azure DevOps| ADO
    end

    QG[quality-gate<br/><i>backstop</i>]

    W --> T --> R --> M --> QG

    classDef backstop fill:#fdecea,stroke:#c62828,stroke-width:2px
    class QG backstop
```

`review-impact` is the exception to the left-to-right reading: run it **before** pushing,
not during review. It answers "what did I just put at risk", and its output is a list of
test suites to run.

## Nudges and the backstop

The reviewers report and hope. That works most of the time, and the failures are silent —
which is the whole reason the last box exists.

```mermaid
flowchart TD
    DIFF[A diff] --> REV[Reviewers<br/>judgment, on the diff]
    REV --> FIND{Findings}
    FIND -->|acted on| GOOD([Fixed])
    FIND -->|"deferred, disputed,<br/>or 'fine in this case'"| DRIFT[Accumulates]
    DRIFT --> DIFF

    DRIFT ==>|"every review was right,<br/>the file is now 400 lines"| QG[quality-gate<br/>thresholds, on the codebase]
    QG --> BLOCK([Build fails])

    classDef backstop fill:#fdecea,stroke:#c62828,stroke-width:2px
    class QG,BLOCK backstop
```

The loop on the left is the normal case and it is not a failure — most "fine in this case"
judgements really are fine. But nothing in that loop can see the fourteenth reasonable
increment, because each review only ever sees one. The gate reads the file rather than the
diff, so it sees the total; that is the only thing it is better at, and it is enough.

A gate that fires is therefore evidence about the loop as much as about the file. If the
same file trips it every release, the reviewers have been raising it and nobody has been
acting.

## The docs behind the skills

Knowledge lives in `docs/` when more than one thing needs it. Extraction is what stops the
copies drifting — the review protocol was worded three different ways before it was pulled
out.

```mermaid
flowchart LR
    RP[review-protocol.md] --> ALLREV[all seven review-* skills]
    TR[testing-rules.md] --> WT[write-tests]
    TR --> RT[review-testing]
    TRG[testing-review-guide.md] --> RT
    ACTD[adapter-contract-testing.md] --> ACT[adapter-contract-testing]
    ACG[accidental-complexity-guide.md] --> RC[review-complexity]
    ACG --> RF[refactor]
    DP[design-patterns.md] --> RF
    DP --> RA[review-architecture]
    SRG[slop-review-guide.md] --> RSL[review-slop]
    CDR[code-design-rules.md] --> RC
    CDR --> RF
    HAR[hexagonal-architecture-rules.md] --> RA
    HAR --> TR
    BFD[bugfix-workflow.md] --> WT
    BFD --> BZS[bugszero-root-cause]
    BZD[bugszero-root-cause.md] --> BZS
    P3[3p-protect-prepare-produce.md] --> L3[legacy-3p]
    FW[feature-workflow.md] --> L3
```

One consequence worth stating: **`legacy-3p`'s Protect tests deliberately violate
`testing-rules.md`.** They are quick-and-dirty scaffolding, most of them deleted in Prepare.
Reviewing them against the testing rules is a category error, so `review-testing` needs to
be told which phase it is looking at.

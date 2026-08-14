# Strategy Lab Model C — current Stage-60 runtime contract

Status: **CURRENT THROUGH v0.4.1_12; v0.4.1_13 FINALIZATION PLANNED**

This file answers: **How does the current Model-C Stage-60 runtime execute candidates, and what
production boundary must `_13` preserve/change?**

Read after:

- `docs/PROJECT_STATE.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Historical `_23` design details and old acceptance boundaries are preserved in patch/evidence history;
this file describes the current contract.

## Current status

Model C is the selected production direction and the normal first Stage-60 runtime.

Actual source through `_12` still contains the transitional automatic chain:

`Model C -> Model B -> Model A cold`.

That chain is **current implementation, not the approved long-term architecture**. Automatic B/A
production fallback is transition debt scheduled for removal by `_13`. B/A code may remain as
benchmark/reference/test tooling.

## Search-semantic boundary

Model C accelerates execution only. It must not redefine:

- adaptive graph reachability or planner decisions;
- immutable CandidateSpec identity;
- ResourceInventory semantics;
- candidate ordering/ranking/result ownership;
- pinned endpoint epoch;
- downstream Stage 70/80/85/result behavior;
- cancellation and Stage-90 semantic restoration.

One admitted logical frontier batch contains at most three candidates.

## Dispatcher identity

One physical warm `dvtws2` worker serves one compatible physical Model-C segment.

Each candidate/endpoint probe has a controlled TCP client source port. Identity is preserved twice:

1. IPFW rule matches exact source port + pinned destination IPv4 + TCP/443 and routes to the Model-C
   divert endpoint;
2. Model-C Lua condition selects only the candidate whose allowed client source-port set matches the
   flow.

Outgoing packets use TCP source port; reverse-direction packets use TCP destination port so the same
client identity is retained. Invalid/missing selector metadata fails closed; it is not success or
fall-through to another candidate.

## Candidate rendering / resources

Model C does not create new candidate identities.

For each candidate it preserves exact ordered Lua actions and candidate-defined filters/ranges.
Candidate BLOB declarations are resolved from the immutable job ResourceInventory and unioned only
when semantically compatible for that physical segment.

Unsupported/conflicting/incompatible declarations are infrastructure errors. They must never be
silently approximated into another strategy.

Accepted measurement results remain:

- Lua initialization: no production reduction justified;
- current-width BLOB preload/common set: no material startup/RSS penalty;
- production discovery: bounded GET-4K retained.

## Source-port leasing

Production source-port ownership uses `preferred-free-else-alternate` leasing.

The lease must:

- avoid collision with the normal Zapret2 service/runtime;
- preserve exact candidate attribution;
- clean all temporary rules/ports on success, failure and cancellation;
- fail closed when a safe lease cannot be established.

## Logical batches and physical segments (`_11`)

The planner-selected logical batch is preserved as the observation/result boundary.

Model C may partition that logical batch into contiguous profile-compatible physical segments when
candidate profile dimensions require it. Segments execute sequentially under the same logical batch.
This does not rewrite planner decisions, candidate order or logical evidence identity.

A logical batch can therefore contain more than one physical worker lifecycle.

## Readiness (`_12`)

Each physical Model-C segment becomes ready only after the same qualifying predicates are observed:

- expected process identity exists;
- required socket is ready;
- startup log is clean;
- two consecutive snapshots satisfy all predicates.

Polling interval is 25 ms with a 4 s bound. A bad snapshot resets the consecutive-success count.
This replaced the prior one-second sleep behavior without weakening readiness proof.

Latest owner-live lifecycle replay showed 5/5 Model-C-only completion, no fallback,
cleanup/restoration PASS, with physical-segment startup median 82.5 ms.

Evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

## Failure / cleanup boundary through `_12`

A Model-C infrastructure failure is not a candidate network FAIL.

Through `_12`, current source cleans Model C and then can replay through Model B, whose own cold Model
A fallback remains available. That behavior is a legacy transition safety net only.

Cleanup/restoration requirements remain independent of fallback policy:

- temporary Model-C process/socket/rules are removed before returning from its execution boundary;
- cancellation/exit traps remain bounded;
- Stage 90 owns semantic restoration of the original Zapret2 service/configuration state.

## `_13` production finalization

`v0.4.1_13` changes only the production runtime fallback boundary:

- Model C becomes the only normal Stage-60 runtime;
- the same logical work is not silently replayed through Model B/cold Model A;
- Model-C infrastructure errors remain explicit and bounded;
- production plumbing that exists solely for B/A fallback is removed;
- B/A implementation may remain outside normal production execution for reference/test purposes.

`_13` must **not** change planner/search semantics, source-port attribution, `_11` segmentation,
`_12` readiness, adaptive-budget ownership, GET-4K discovery, cleanup or Stage-90 restoration.

Do not first optimize timeout admission for the legacy `C -> B` transition. If a later Model-C-only
containment defect is observed, handle it as a separate evidence-based task.

## `_13` acceptance

Automated:

- production Stage 60 reaches Model C only;
- injected Model-C infrastructure failure produces explicit bounded failure with no B/A replay;
- cleanup succeeds on success/failure/cancel;
- leasing and attribution remain exact;
- logical-batch/segment evidence remains intact;
- full Strategy Lab corrective matrix and FreeBSD-15 package qualification PASS.

Owner-live:

- one selected normal Model-C-only run;
- correct result handling;
- semantic restoration PASS;
- no temporary IPFW/process/socket residue.

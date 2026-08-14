# Strategy Lab Model C — current Stage-60 runtime contract

Status: **CURRENT THROUGH v0.4.1_13 · MODEL-C-ONLY PRODUCTION**

This file answers: **How does the current Model-C Stage-60 production runtime execute candidates, and what failure boundary is authoritative?**

Read after:

- `docs/PROJECT_STATE.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Historical `_23` design details and old acceptance boundaries are preserved in patch/evidence history; this file describes the current contract.

## Current status

Model C is the selected and only normal production Stage-60 runtime.

`v0.4.1_13` removes the transitional automatic production chain:

`Model C -> Model B -> Model A cold`.

Normal production now executes Model C only. A Model-C infrastructure/selector/rendering/readiness/attribution/cleanup failure is an explicit bounded structural Stage-60 error; the same logical work is not silently replayed through Model B or cold Model A.

Model B and Model A remain reachable only through explicit reference/benchmark/test overrides. Legacy compatibility code inside their reference modules may retain B->A fallback semantics for those explicit runs; it is outside the normal production path.

## Production owner boundary (`_13`)

The packaged `stage60-parallel` compatibility command routes through `strategy_lab_py/stage60_model_c_production.py`.

That owner:

- reuses the proven Model-C `_bucket_batch` engine;
- preserves the existing Stage-60 planner as the sole planner/decision owner;
- translates Model-C infrastructure failure into a structural `Stage60ParallelError` class which is deliberately **not** `WarmInfrastructureError`;
- therefore cannot enter the legacy Model-B/cold-Model-A fallback handler;
- records `model_c_only=true`, `cold_fallback_available=false`, and an explicit infrastructure error in persisted Stage-60 evidence when such a result file exists;
- always restores temporary monkey-patched compatibility state and performs bounded cleanup.

Explicit `STRATEGY_LAB_STAGE60_MODEL=model-b|parallel|cold` remains reference/test tooling only.

## Search-semantic boundary

Model C accelerates execution only. It does not redefine:

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

1. IPFW rule matches exact source port + pinned destination IPv4 + TCP/443 and routes to the Model-C divert endpoint;
2. Model-C Lua condition selects only the candidate whose allowed client source-port set matches the flow.

Outgoing packets use TCP source port; reverse-direction packets use TCP destination port so the same client identity is retained. Invalid/missing selector metadata fails closed; it is not success or fall-through to another candidate.

## Candidate rendering / resources

Model C does not create new candidate identities.

For each candidate it preserves exact ordered Lua actions and candidate-defined filters/ranges. Candidate BLOB declarations are resolved from the immutable job ResourceInventory and unioned only when semantically compatible for that physical segment.

Unsupported/conflicting/incompatible declarations are infrastructure errors. They are never silently approximated into another strategy or replayed through another production model.

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

Model C may partition that logical batch into contiguous profile-compatible physical segments when candidate profile dimensions require it. Segments execute sequentially under the same logical batch. This does not rewrite planner decisions, candidate order or logical evidence identity.

A logical batch can therefore contain more than one physical worker lifecycle.

## Readiness (`_12`)

Each physical Model-C segment becomes ready only after the same qualifying predicates are observed:

- expected process identity exists;
- required socket is ready;
- startup log is clean;
- two consecutive snapshots satisfy all predicates.

Polling interval is 25 ms with a 4 s bound. A bad snapshot resets the consecutive-success count. This replaced the prior one-second sleep behavior without weakening readiness proof.

Latest owner-live lifecycle replay before `_13` showed 5/5 Model-C-only completion, no fallback, cleanup/restoration PASS, with physical-segment startup median 82.5 ms.

Evidence: `docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

## Failure / cleanup boundary (`_13`)

A Model-C infrastructure failure is not a candidate network FAIL.

Normal production behavior is now:

1. fail Model C explicitly;
2. clean temporary Model-C process/socket/rules within bounded cleanup;
3. propagate structural Stage-60 failure;
4. never replay the affected logical work through Model B or Model A;
5. leave Stage 90 as owner of semantic restoration of the original Zapret2 service/configuration state.

Cancellation remains cancellation, not infrastructure fallback.

The old Model-C compatibility module and Model-B module remain available to measurements/reference tooling, but their fallback behavior is not reachable from the normal packaged production entry point.

## `_13` acceptance

Automated:

- production Stage 60 routes through the Model-C-only owner;
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

Do not reopen A/B/C selection after `_13`. Any later timeout, containment or Model-C defect requires its own concrete evidence and task boundary.

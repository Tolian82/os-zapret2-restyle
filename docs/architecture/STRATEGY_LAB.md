# Strategy Lab architecture

Status: **CURRENT**

This document is the active base product/lifecycle/stage contract for asynchronous
Strategy Lab. Historical implementation sequences and superseded experiment plans live
in decisions, patches, devlogs and verification records and do not override this file,
`docs/PROJECT_STATE.md`, `docs/START_HERE.md`, or newer owner canon.

Read with:

- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — current Stage-50/60 search semantics;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md` — finite parent budgets;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md` — selected Stage-60 runtime;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — live verification coverage.

## Objective

Provide an asynchronous Strategy Lab that:

- tests a domain/IP target without interference from the saved normal Zapret2 runtime;
- reports online progress by numbered stages;
- searches native Zapret2 candidates adaptively;
- preserves deterministic candidate/resource/endpoint identity;
- distinguishes infrastructure failure from candidate network failure;
- confirms stability before recommendation;
- supports controlled cancellation with partial results;
- always cleans temporary state;
- restores the exact initial Zapret2 service state;
- supports Russian/English GUI presentation;
- remains bounded by finite operation/stage/job budgets.

## Non-goals

Strategy Lab does not:

- use classic zapret/nfqws1 strategy syntax as a search source;
- run multiple permanent dvtws2 instances;
- automatically replace/merge the user's saved Traffic Strategy;
- infer arbitrary unrelated service endpoints;
- turn a global success percentage into a PASS when a required endpoint fails;
- treat A/B/C as still-competing production runtime choices;
- treat historical experiment sequencing as current work merely because it remains in
  historical records.

## High-level flow

```text
Diagnostics GUI
  -> start asynchronous job / return job_id
  -> acquire shared lifecycle boundary
  -> snapshot exact initial Zapret2 state
  -> stop normal runtime when required
  -> capability + clean-baseline checks
  -> Stage-50 evidence
  -> Stage-60 adaptive native search using selected Model C runtime
  -> stability / extended checks / shortlist
  -> cleanup temporary processes/rules/runtime
  -> exact restoration
  -> publish complete or partial result
```

## Job model

Only one Strategy Lab job may be active. A second start reports busy and does not alter
the active job.

The job survives page refresh/close. Reopening Diagnostics discovers the active job and
resumes read-only polling.

Job state describes work but never replaces the shared lifecycle lock.

## Lifecycle ownership

Before baseline/candidate testing Strategy Lab must:

1. enter the same exclusive lifecycle boundary used by normal Zapret2 mutations;
2. classify initial state exactly as RUNNING or STOPPED;
3. reject incomplete/unknown state before temporary runtime mutation;
4. record the process/supervisor/firewall/runtime evidence required for restoration;
5. stop the normal service through its approved lifecycle path when initially RUNNING;
6. verify the normal runtime is absent before isolated testing.

Every exit path performs cleanup and restoration, including normal completion, no
candidate, timeout, cancellation, candidate start/probe failure and internal error.

Final-state contract:

- initial RUNNING -> fully RUNNING;
- initial STOPPED -> fully STOPPED;
- temporary dvtws2/rules/sockets/runtime state absent;
- restoration failure -> explicit restore failure, never normal success.

Stage 90 cleanup/restoration is not user-cancelable.

## Cancel contract

Cancel is a controlled request, not an abrupt abandonment:

1. persist cancel request;
2. stop current bounded probe/runtime activity;
3. remove temporary candidate state;
4. preserve already completed results;
5. mark unexecuted work skipped due to cancellation;
6. run mandatory Stage 90 restoration;
7. publish partial result.

## Numbered stages

### 00 — Target initialization

Validate/normalize target, establish required endpoint/protocol contract and create job
state.

### 10 — Lifecycle snapshot

Acquire lifecycle ownership, classify initial state and persist restoration evidence.

### 20 — Stop normal Zapret2

Stop the initially running normal service and verify normal process/rule absence. Leave
an initially stopped service stopped.

### 30 — Network capability precheck

Record required IPv4/IPv6/capability evidence. The fixed IPv4 UDP/443 QUIC check remains
a capability/precheck, not an adaptive QUIC strategy-search branch.

### 40 — Clean baseline

Resolve/pin required target identity and test the target without Zapret2. If the target
already satisfies the direct-access contract, return `TARGET_ACCESSIBLE` rather than
searching for an unnecessary bypass.

### 50 — Low-cost TLS 1.3 reconnaissance

Run low-cost native candidates and record evidence. Stage-50 family results influence
priority only and never become a hard Stage-60 family allowlist.

### 60 — Adaptive native-Zapret2 search

Explore the bounded native graph according to current evidence, compatibility, cost and
remaining budget. Candidate identity/resources/ranges/actions are immutable. Normal
planner logical width is at most three.

**Model C is the selected normal production runtime for Stage 60.** Packaged source
through `v0.4.1_12` still contains legacy automatic B/A fallback, but that is transition
debt scheduled for removal in `v0.4.1_13`; it is not an unresolved model-selection
question.

### 70 — Stability confirmation

Run fresh sequential checks for the best candidates and apply the current stability
contract with fail-fast rejection when success becomes impossible.

### 80 — Extended protocol testing

Execute applicable supported extended branches such as TLS 1.2, plain HTTP and explicitly
configured request-response UDP. QUIC adaptive candidate search is not part of the
current target.

### 85 — Shortlist

Rank truthful stable results and normally publish up to three candidates when available.
A smaller truthful result is valid. Never write the recommendation into saved settings
automatically.

### 90 — Cleanup and exact restoration

Remove temporary processes/rules/runtime and restore exact initial normal Zapret2 state.

### 99 — Final report

Build complete/partial result only from recorded evidence and report restoration outcome
explicitly.

## Status semantics

User-visible stage states:

- `PASS` — valid stage result obtained;
- `FAIL` — tested network condition/candidate failed;
- `TIMEOUT` — stage exhausted its finite budget;
- `SKIPPED` — not applicable or canceled before execution;
- `ERROR` — internal/infrastructure failure prevented a valid result.

A negative network result is `FAIL`, not `ERROR`. Model-C infrastructure/readiness/
attribution/rendering failure is not silently classified as candidate network FAIL.

## Candidate / resource / endpoint identity

Each candidate is one immutable `CandidateSpec` sufficient to reproduce its tested
strategy. One job-scoped `ResourceInventory` snapshots available Lua/BLOB/inline/built-in
resources. Installed resources are availability, not permission to generate unrelated
Cartesian combinations.

For one search epoch, endpoint identity is pinned and original hostname/SNI semantics are
preserved. A deliberate re-resolution creates a new explicit epoch instead of silently
changing comparison targets.

## Probe / validation contract

Web probes are bounded and explicit about IP family, TLS version where relevant,
redirect/retry/fresh-connection behavior, deadlines and response-size limit.

Current mass discovery uses bounded GET-4K because measured HEAD/GET-1 alternatives did
not justify a production change. Stability/result stages remain separate evidence levels.

## Model C runtime contract

Model C executes planner-selected logical work while preserving search semantics.

Current accepted properties:

- exact source-port-qualified candidate attribution through IPFW + Lua selector;
- pinned endpoints sequential inside one candidate;
- logical batch width at most three;
- `preferred-free-else-alternate` source-port leasing;
- profile-compatible physical segmentation without changing logical batch identity;
- readiness requires expected process identity, socket readiness, clean startup log and
  two consecutive qualifying snapshots;
- 25 ms readiness polling, bounded by 4 s;
- cleanup on success/failure/cancel;
- Stage-90 semantic restoration remains mandatory.

The A/B/C selection experiment is closed. Model A/B may remain for reference/testing;
they are not competing normal production choices.

## Timeout / budget contract

Containment invariant:

`bounded child operation <= candidate/stage parent <= finite job parent`.

Current parent-budget policy is `eligible-work-v1`. Admission is based on remaining
absolute budget. Cleanup/restoration is not made unbounded to gain more search time.

A historical containment question affected the transitional `C -> B` replay path. Do
not optimize that legacy fallback instead of completing Model-C-only production. A later
Model-C-only timeout audit is a separate evidence-based task if selected.

## DNS fact boundary

Historical local/container DNS slowness/failures are closed because the owner fixed DNS.
Treat DNS as working now. Reopen DNS diagnosis only on fresh direct reproducible evidence;
do not revive the old diagnosis because an old log/doc/test mentions it.

## Circular validation

Circular validation is a separate bounded lifecycle transaction for an already selected
profile/result. It shares the lifecycle lock with automated Strategy Lab and therefore
cannot run concurrently with a Strategy Lab job. Saved configuration remains immutable;
cleanup and exact service-state restoration are mandatory.

## Current handoff

Current packaged source is `v0.4.1_12`.

The exact next packaged source change is `v0.4.1_13`: remove automatic Model-B/cold-
Model-A production replay so Model C becomes the only normal production Stage-60 runtime,
while preserving search semantics, budgets, leasing/attribution, segmentation, readiness,
cleanup and restoration.

See `docs/START_HERE.md` for exact work surfaces and acceptance.

# Strategy Lab adaptive workload budget architecture

Status: **CURRENT**

This file answers: **How are finite parent budgets derived without changing search/runtime semantics?**

Read with:

- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`.

Current implementation origin: `docs/patches/v0.4.0_26.md`.

## Ownership boundary

Budget policy owns only finite parent time envelopes and admission against remaining absolute time.
It does **not** choose candidates, reorder the adaptive graph, select Model A/B/C, alter source-port
ownership, reinterpret PASS/FAIL, rank results or change restoration semantics.

Therefore runtime selection may change independently (for example `_13` retiring B/A production
fallback) without changing this budget policy, provided all child work remains contained by the same
absolute stage/job parents.

Invariant:

`bounded child operation <= stage parent <= finite job parent`.

An adaptive extension is never permission for an unbounded child and never restarts the job clock.

## When the plan becomes authoritative

Initial configured budgets exist from job start because early stages already require finite parents.

The workload-derived plan becomes authoritative only after Stage 30 PASS, when Strategy Lab has:

- validated endpoint count;
- measured IPv4/IPv6/QUIC capability state;
- validated Standard/Extended mode;
- validated Generic UDP request state.

All resulting deadlines remain anchored to the original job `started_epoch`.

## Input matrix

Canonical workload dimensions:

`endpoint count × IPv4/IPv6 capability × TLS/QUIC eligibility × Generic UDP eligibility × mode`.

Current semantics:

- IPv4 must be available for the search plan to proceed;
- native Stage-60 search epoch remains IPv4;
- IPv6 adds only currently implemented eligible baseline work;
- QUIC/Generic UDP additions apply only when their existing Extended branches are actually eligible;
- unavailable/skipped work adds no budget.

## Base floors

Environment-configured minimums remain:

- `STRATEGY_LAB_STANDARD_BUDGET`, default `150 s`;
- `STRATEGY_LAB_EXTENDED_BUDGET`, default `120 s`;
- `STRATEGY_LAB_STAGE80_TIMEOUT`, default `120 s`.

The proven reference two-endpoint topology keeps the existing Extended total floor of `270 s` when no
optional additions are eligible. The policy does not reduce a known-safe configured floor merely
because one observed run was faster.

## `eligible-work-v1` additions

Current bounded weights:

- endpoint count above two: `+30 s` per extra endpoint to Standard;
- extra endpoints in Extended mode: another `+15 s` per extra endpoint to Extended/Stage 80;
- IPv6 available: `+5 s` per endpoint to Standard;
- Extended QUIC available: `+20 s`;
- Extended Generic UDP configured: `+15 s`.

Calculation is additive/monotonic and starts from cached original configured bases so recalculation
cannot compound additions.

## Deadlines

Let `t0` be original job start time.

After adaptation:

- `standard_deadline = t0 + effective_standard`;
- Standard `overall_deadline = standard_deadline`;
- Extended `overall_deadline = t0 + effective_standard + effective_extended`;
- Stage-80 deadline remains the minimum of its finite local parent and the overall deadline.

Children remain subject to their own bounded operation/candidate admission below these parents.

## Evidence

Successful adaptation persists `adaptive-budget.json` with:

- policy/schema;
- exact workload matrix;
- weights/additions;
- configured bases;
- effective Standard/Extended/search/Stage-80 seconds.

`status.json` exposes public effective budget/deadline fields and timing telemetry records the same
adaptation event.

## Fail-closed rules

Planning fails closed when required Stage-30 state is malformed, no endpoint exists or IPv4 is not
actually available. It does not infer capability from old jobs, DNS names, historical telemetry or
expectation.

Optional unavailable work contributes zero seconds.

## Relationship to Model-C-only `_13`

Through `_12`, current Stage 60 may execute Model C and then legacy B/A fallback. `_13` removes the
automatic production B/A replay.

This budget document does **not** require the old `C -> B -> A` order and must not be used as a reason
to preserve it. Its requirement is only that whichever runtime the current production architecture
selects remains bounded by child/stage/job containment and remaining-budget admission.

Do not enlarge parent budgets merely to keep a legacy fallback alive. If Model-C-only operation later
exposes a concrete containment defect, investigate it as its own evidence-based timeout task.

## Verification

Source contract: `scripts/test-strategy-lab-adaptive-budget.sh`.

The accepted `_26` owner-live gate established `eligible-work-v1` operation, workload/effective-budget
evidence, no unexpected timeout/fallback and clean semantic restoration for its tested topology.
Future runtime changes preserve this policy unless a dedicated budget patch explicitly changes it.

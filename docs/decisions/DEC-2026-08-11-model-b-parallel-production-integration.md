# DEC-2026-08-11 — Select controlled-parallel Model B for staged Strategy Lab integration

Status: **Accepted for staged integration; not yet production-default**
Date: 2026-08-11

## Context

Strategy Lab production Stage 60 still uses Model A: one cold candidate runtime/process per candidate, fully torn down before the next candidate.

The measurement series established:

- Model A cold reference on `_11`;
- three-worker Model B coexistence owner-live ACCEPT and reproducibility on `_16`/`_17`;
- complete sequential warm exhaustive no-candidate replay ACCEPT 5/5 on `_19`;
- controlled parallel candidate probing with unique source-port-qualified IPFW attribution implemented in `_20`;
- failed-probe attribution corrected in `_21` without changing scheduling or parallel width;
- `_21` owner-live controlled-parallel replay ACCEPT 5/5 on the complete 16-candidate/two-endpoint `telegram.org` no-candidate corpus.

The `_21` five-run mean parallel exhaustive search wall is `33025.6 ms` versus `89012 ms` retained cold Stage-60 candidate runtime, a mean measured same-corpus reduction of about `62.90%`. Compared directly with the accepted `_19` sequential warm mean `74808.2 ms`, controlled parallelism reduces the same warm exhaustive search wall by about `55.85%`.

The owner appliance has two logical CPUs. Five full three-worker batches still achieved observed overlap width 3 with only about 0.23% run-to-run coefficient of variation. CPU count is therefore retained as telemetry, not used to gate architecture or silently change semantics.

## Decision

Select **Model B controlled-parallel, width 3** as the next Strategy Lab production-shaped Stage-60 integration candidate.

This decision does **not** set `production_approved=true` and does **not** change the current default production engine. Model A remains the default until the integrated path passes the gates below.

Width 3 is selected because it is the maximum coexistence/parallel width with repeated owner-live evidence. Do not scale width automatically from `hw.ncpu`; future width changes require separate evidence.

## Required integration semantics

The staged integrated engine must preserve the current adaptive planner's deterministic candidate order while allowing one batch of at most three candidate tasks to execute concurrently.

1. The planner produces the authoritative ordered candidate schedule.
2. One batch contains the next one to three scheduled candidates.
3. Candidate tasks in that batch may execute concurrently.
4. Pinned endpoints inside each candidate remain sequential.
5. Results are committed to Strategy Lab state in original planner order, not thread completion order.
6. Early-stop is evaluated only after committing the completed in-flight batch in planner order. No next batch is launched once the accepted winner threshold has been reached.
7. Testing up to two additional candidates already in the in-flight batch is acceptable; silently reordering candidate priority is not.
8. Every candidate/endpoint probe retains unique source-port-qualified IPFW ownership and endpoint pinning.
9. A PASS requires the strict connected-socket endpoint/local-port evidence already defined by `_21`; failed probes retain exact command binding plus exact IPFW counter attribution.
10. All worker/rule/runtime cleanup remains mandatory before Stage 60 can finalize or hand off.

## Staged rollout

### Integration patch

Add a production-shaped alternate Stage-60 engine behind an explicit internal selection such as `STRATEGY_LAB_STAGE60_ENGINE=model_b_parallel` while the default remains Model A.

The alternate engine must use normal Strategy Lab job state, deadlines, cancellation, persistence, Stage-70 handoff, Stage-90 restoration and terminal finalization. It must not call the standalone benchmark harness as a subprocess or create a second independent orchestration model.

### Required owner-live gates before default switch

At minimum:

- Standard no-winner `telegram.org`: complete graph exhaustion or truthful budget containment, result equivalence, no residue, restoration PASS;
- Standard winner `rutracker.org`: deterministic ordered batch commit, correct early-stop threshold, correct Stage-70 shortlist/handoff, restoration PASS;
- cancellation during an active parallel batch: bounded child termination, worker/rule cleanup, truthful cancelled state, restoration PASS;
- one controlled worker/readiness failure: no false PASS, deterministic batch failure/fallback policy, cleanup/restoration PASS;
- timing telemetry: direct integrated Stage-60 and full-job wall time, not projection only.

### Default switch

Only a later, separate patch may make Model B parallel the normal Stage-60 engine. That patch must retain a documented recovery/fallback path to Model A and update the live matrix/architecture authorities.

## Rejected alternatives for this step

- **CPU-derived width**: rejected for now; only width 3 is repeatedly proven.
- **Model C single-process bucket**: not selected because exact dispatcher/flow-chain identity is still unproven and unnecessary to justify the already measured Model B gain.
- **Immediate production-default switch from the benchmark harness**: rejected because winner/early-stop, integrated budgets/cancellation and Stage-70 handoff are not yet owner-live proven.
- **More sequential Model B benchmarking**: not selected; `_19` and `_21` reproducibility already make the next uncertainty an integration uncertainty, not a mechanism-performance uncertainty.

## Evidence

Primary live evidence:

- `docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_20-model-b-parallel-attribution-reject.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`;
- `docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`;
- `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

Until the staged integration gates pass, production Strategy Lab remains Model A.
# DEC-2026-08-11 — Select controlled-parallel Model B for Strategy Lab production integration

Status: **IMPLEMENTED IN `v0.4.0_22`; PRODUCTION-ACTIVE WITH COLD MODEL A FALLBACK; OWNER-LIVE PRODUCTION EVIDENCE RECORDED**

## Context

Strategy Lab originally used cold Model A in production: each candidate owned a fresh
candidate runtime and fresh dvtws2 process and was fully torn down before the next
candidate.

The adaptive-search experiment plan required warm-worker coexistence, exact traffic
attribution, result equivalence, bounded cleanup, complete no-candidate replay and repeated
live evidence before any warm architecture could be selected.

That evidence chain is now complete:

- Model A cold reference accepted on `v0.4.0_11`;
- Model B coexistence accepted on `_16` and repeated 5/5 on `_17`;
- complete sequential exhaustive Model B accepted 5/5 on `_19`;
- controlled three-worker parallel probing introduced experimentally on `_20`;
- `_20` first live run proved actual three-way overlap and performance but exposed a
  failed-probe attribution false reject;
- `_21` corrected only that attribution contract while keeping PASS socket identity strict;
- `_21` then produced an owner-live ACCEPT followed by five unchanged ACCEPT repeats;
- `_22` integrated the selected semantics into the real production Stage 60 and has owner-
  live production evidence for Standard no-candidate, Standard working-candidate and
  fail-closed Extended cold-fallback paths.

The `_21` repeat series used the retained Standard `telegram.org` no-candidate reference
`job.tMYnFA`: 16 Stage-60 candidates, two pinned endpoints and 32 endpoint probes.

Measured repeat-series mean:

- cold Model A Stage-60 candidate runtime: 89012 ms;
- sequential warm Model B `_19` exhaustive mean: 74808.2 ms;
- controlled-parallel Model B `_21` exhaustive mean: 33025.6 ms;
- measured reduction versus cold Model A candidate runtime: about 62.90%;
- measured reduction versus sequential warm Model B: about 55.85%;
- min/max spread across the five `_21` repeats: 184 ms, about 0.56%;
- peak three-worker RSS: about 13 MiB;
- all runs retained deterministic route attribution, result equivalence, bounded
  concurrency, cleanup and semantic restoration.

The owner appliance has two logical CPUs. CPU count is retained only as measurement
metadata. Width is not selected from this appliance topology and the architecture remains
valid on other OPNsense systems.

## Decision

**Controlled-parallel Model B is the production Stage-60 architecture from `v0.4.0_22`.**

The production design preserves these proven boundaries:

1. At most three candidate workers are resident in one batch.
2. Candidate tasks may execute concurrently up to that width.
3. Pinned endpoints inside one candidate remain sequential.
4. Every concurrent candidate/endpoint probe owns a unique controlled TCP source port.
5. Each temporary IPFW route is exact and source-port qualified.
6. A successful probe still requires connected-socket endpoint identity evidence.
7. A failed probe may establish route ownership only through the `_21` proven combination
   of exact executed source-port binding, exact pinned `--resolve` binding, exact matching
   IPFW counter growth and successful route cleanup.
8. No cold no-candidate result may become PASS because of warm/parallel execution.
9. Worker identity/readiness and aggregate RSS remain observable.
10. Batch cleanup is mandatory before the next batch.
11. Final Strategy Lab lifecycle restoration remains semantic and mandatory.
12. Cold Model A remains the correctness/runtime fallback and rollback reference.

## Production implementation

`v0.4.0_22` integrates the selected behavior into the real Stage-60 search owner with normal
job budgets, cancellation, progress/state persistence, deterministic planner/frontier
ordering, budget admission, partial containment and Stage-90 restoration. It does not call
the laboratory exhaustive harness as the production implementation.

The implementation includes automated coverage for:

- complete no-candidate graph exhaustion;
- deterministic winner-band handling with concurrent in-flight candidates;
- Stage-60 deadline/budget admission under batched parallel execution;
- cancellation while a multi-worker batch is active;
- worker readiness/start failure with fail-closed cleanup;
- probe failure/timeout containment while sibling candidate probes remain safe;
- exact per-flow source-port/IPFW attribution;
- no dedicated-rule/listener/runtime residue;
- unchanged Stage 70/80/85 ownership and inputs;
- semantic service/configuration restoration.

Explicit rollback/testing selector:
`STRATEGY_LAB_STAGE60_MODEL=cold`.

## Owner-live production closeout

Canonical record:
`docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

Observed `_22` production paths:

- Standard `telegram.org` `job.KpLHgb`: real production Model B, 16/16
  `graph_exhausted`, zero winners, width-three overlap, no fallback, Stage 60 `34227 ms`,
  terminal `NO_CANDIDATE`, restoration PASS;
- Standard `rutracker.org` `job.GK0X66`: real production Model B, 16/16, two Stage-60
  winners, no fallback, Stage 60 `28151 ms`, downstream Stage 70/85 success, terminal
  `SUCCESS`, restoration PASS;
- Extended `rutracker.org` `job.d5XV82`: first warm batch detected
  `controlled source port is already in use: 42003`; the designed fail-closed Model A
  fallback completed all 16 candidates, Stage 80 and restoration successfully.

The Standard `rutracker.org` 16/16 result is not a recurrence of the historical fixed
Stage-60 parent-timeout defect. That defect was closed by `_7`/`_8`. The `_22` run found two
Stage-60 winners, below the target of three, so graph exhaustion was truthful current
behavior.

The supplied `_22` owner-live set did not reach `early_stop.triggered=true` because no run
reached three Stage-60 winners. This remains a precise coverage note, not a defect claim.
The single observed `42003` source-port collision is likewise not declared fixed; the
fallback/cleanup boundary is verified and the collision should be investigated only if it
recurs or becomes reproducible.

## Rejected alternatives at selection time

- **Keep sequential warm Model B as the production target:** safe and reproducible, but the
  complete exhaustive live series showed only about 15.96% Stage-60 candidate-runtime
  improvement versus cold Model A, substantially below the controlled-parallel result.
- **Scale width directly from CPU count:** rejected. CPU topology is measurement context,
  not a correctness selector; fixed width three remains the evidence-backed boundary.
- **Move directly to Model C / one-process candidate bucket:** rejected. Exact dispatcher
  identity, per-flow state isolation and cleanup have not been proven to the same standard.
- **Run more than three workers concurrently:** not selected. There is no owner-live
  coexistence/attribution evidence beyond width three.

## Evidence

Primary production record:
`docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

Selection evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md`.

Supporting records:

- `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_20-model-b-parallel-attribution-reject.md`;
- `docs/patches/v0.4.0_21.md`;
- `docs/patches/v0.4.0_22.md`;
- PR #175 owner-live evidence comment.

## Next action

Treat width-three controlled-parallel Model B as the active production Stage-60 baseline.
Do not reopen the architecture-selection question from older evidence. If the observed
controlled-source-port collision recurs, collect exact live socket/process/rule evidence and
handle it as a separate corrective scope. Any Model C, endpoint-parallel or width-greater-
than-three work remains a separate evidence-gated experiment.
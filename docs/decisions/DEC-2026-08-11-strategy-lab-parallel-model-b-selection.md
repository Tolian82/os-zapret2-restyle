# DEC-2026-08-11 — Select controlled-parallel Model B for Strategy Lab production integration

Status: **APPROVED FOR IMPLEMENTATION; NOT YET PRODUCTION-ACTIVE**

## Context

Strategy Lab currently uses cold Model A in production: each candidate owns a fresh
candidate runtime and fresh dvtws2 process and is fully torn down before the next
candidate.

The adaptive-search experiment plan required warm-worker coexistence, exact traffic
attribution, result equivalence, bounded cleanup, complete no-candidate replay and repeated
live evidence before any warm architecture could be selected.

That evidence now exists:

- Model A cold reference accepted on `v0.4.0_11`;
- Model B coexistence accepted on `_16` and repeated 5/5 on `_17`;
- complete sequential exhaustive Model B accepted 5/5 on `_19`;
- controlled three-worker parallel probing introduced experimentally on `_20`;
- `_20` first live run proved actual three-way overlap and performance but exposed a
  failed-probe attribution false reject;
- `_21` corrected only that attribution contract while keeping PASS socket identity strict;
- `_21` then produced an owner-live ACCEPT followed by five unchanged ACCEPT repeats.

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
metadata. Width is not selected from this appliance topology and the architecture must
remain valid on other OPNsense systems.

## Decision

**Controlled-parallel Model B is selected as the target architecture for the next
production Strategy Lab integration patch.**

The selected production design must preserve these proven boundaries:

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
12. The existing cold Model A path remains the correctness/fallback reference during the
    production migration and rollback boundary.

## Production transition boundary

This decision **does not set `production_approved=true` on the current experiment harness**
and does not silently switch normal Strategy Lab jobs to Model B.

The next logical patch must integrate the selected behavior into the real Stage-60 search
owner with normal job budgets, cancellation, progress/state persistence, winner early-stop,
partial/budget containment and Stage-90 restoration. It must not merely call the laboratory
exhaustive harness from production.

The integration must include automated coverage for at least:

- complete no-candidate graph exhaustion;
- winner early-stop with concurrent in-flight candidates resolved deterministically;
- Stage-60 deadline/budget admission under batched parallel execution;
- cancellation while a multi-worker batch is active;
- one-worker readiness/start failure with fail-closed cleanup;
- one probe failure/timeout while sibling candidate probes continue safely;
- exact per-flow source-port/IPFW attribution;
- no dedicated-rule/listener/runtime residue;
- unchanged Stage 70/80/85 ownership and inputs;
- semantic service/configuration restoration.

After source/CI/FreeBSD package acceptance, owner-live verification must include both a
no-candidate graph-exhausted path and a winner/early-stop path before the production Model B
migration is declared complete.

## Rejected alternatives at this point

- **Keep sequential warm Model B as the production target:** safe and reproducible, but the
  complete exhaustive live series shows only about 15.96% Stage-60 candidate-runtime
  improvement versus cold Model A, substantially below the controlled-parallel result.
- **Scale width directly from CPU count:** rejected. CPU topology is measurement context,
  not a correctness selector; a fixed proven width of three is the current evidence-backed
  boundary.
- **Move directly to Model C / one-process candidate bucket:** rejected for now. It has not
  yet proven exact dispatcher identity, per-flow state isolation or cleanup, while Model B
  already has a strong live evidence chain.
- **Run more than three workers concurrently:** not selected. There is no owner-live
  coexistence/attribution evidence beyond width three.

## Evidence

Primary acceptance record:
`docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md`.

Supporting records:

- `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_20-model-b-parallel-live-reject.md`;
- `docs/patches/v0.4.0_21.md`.

## Next action

Implement one separate production-integration patch using the proven width-three
controlled-parallel Model B semantics, keeping cold Model A as a fallback/reference until
owner-live production-path verification passes.

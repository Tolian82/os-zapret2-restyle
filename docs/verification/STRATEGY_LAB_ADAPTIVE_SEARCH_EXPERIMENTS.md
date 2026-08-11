# Strategy Lab adaptive-search experiment plan

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How are disputed Strategy Lab search/runtime optimizations measured before they become
production architecture, and which experiment results are now accepted?

Purpose:
Retain the accepted A/B runtime evidence chain and define the boundary for any future
optimization experiment without confusing historical experiment state with current
production state.

Read after:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` and the latest dated Strategy Lab
decision/evidence records.

Raw appliance logs belong under `docs/verification/evidence/`.

==================================================
CURRENT STATUS
==================================================

The Model B architecture-selection experiment is **complete**.

Current production source is `v0.4.0_22` / `PLUGIN_REVISION=22`. Stage 60 normally uses
`B-warm-worker-parallel-batched` with fixed maximum candidate width three. Cold Model A is
retained as the correctness/runtime fallback when warm infrastructure cannot be proven safe.

Owner-live production evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

The current production live set proves:

- Standard `telegram.org` `job.KpLHgb`: complete 16/16 warm graph exhaustion, real width-three
  overlap, no fallback, `NO_CANDIDATE`, clean restoration;
- Standard `rutracker.org` `job.GK0X66`: real warm production Stage 60, two working Stage-60
  candidates, successful downstream stability/finalization and clean restoration;
- Extended `rutracker.org` `job.d5XV82`: one controlled-source-port conflict triggered the
  designed fail-closed cold Model A fallback; the job still completed successfully and
  restored cleanly.

The explicit three-winner `_22` `early_stop.triggered=true` branch was not reached by these
supplied `_22` jobs because the Standard `rutracker.org` run found two Stage-60 winners.
This is a coverage statement, not evidence that the historical Stage-60 timeout defect
returned.

==================================================
ACCEPTED EXPERIMENT CHAIN
==================================================

### Model A — cold reference

`v0.4.0_11`, owner Standard `rutracker.org` job `job.TtZeaH`:

- 25 cold samples;
- complete PASS/FAIL/resource/range coverage;
- total candidate median `1580 ms`;
- readiness median about `1046 ms`;
- probe median `220 ms`;
- RSS median `4332 KiB`, max `4356 KiB`;
- verified restoration;
- `conclusion=reference_collected`.

This remains the correctness/fallback reference.

### Model B — coexistence

`_16` produced the first owner-live coexistence ACCEPT. `_17` repeated the accepted path
5/5. Three warm workers coexisted with unique process/divert identities, numeric aggregate
RSS around 13 MiB, exact route ownership, result equivalence, independent cleanup and
semantic restoration.

### Model B — sequential exhaustive

`v0.4.0_19`, retained Standard no-candidate reference `job.tMYnFA`:

- 16 candidates;
- two pinned endpoints;
- complete replay of the cold Stage-60 corpus;
- five owner-live ACCEPT repeats;
- mean warm exhaustive time `74808.2 ms`;
- mean measured candidate-runtime speedup about `15.96%` versus the retained cold runtime;
- peak aggregate three-worker RSS `12976-12992 KiB`.

This was safe and reproducible but not fast enough to be the final production target.

### Model B — controlled parallel

`_20` introduced candidate-level parallelism up to width three with unique controlled TCP
source ports and exact source-port-qualified IPFW rules while pinned endpoints remained
sequential inside each candidate. Its first live run proved actual overlap/performance but
exposed a failed-probe route-attribution false reject.

`_21` corrected only that failed-probe attribution boundary and then produced six accepted
controlled-parallel runs, including five unchanged repeats:

- repeat mean parallel exhaustive search `33025.6 ms`;
- about `62.90%` measured candidate-runtime reduction versus cold Model A;
- about `55.85%` reduction versus sequential warm Model B;
- five-repeat spread `184 ms` (about 0.56%);
- peak aggregate RSS roughly 13 MiB;
- route attribution, overlap, result equivalence, cleanup and restoration all PASS.

Decision:
`docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md`.

Production integration:
`docs/patches/v0.4.0_22.md`.

==================================================
CURRENT PRODUCTION BOUNDARY
==================================================

The production Stage-60 implementation must preserve the accepted Model B boundaries:

1. maximum candidate width three;
2. candidate tasks may overlap only inside that width;
3. pinned endpoints inside one candidate remain sequential;
4. each concurrent candidate/endpoint probe owns a unique controlled TCP source port;
5. each temporary IPFW rule is exact and source-port qualified;
6. successful probes retain strict connected-socket endpoint identity;
7. failed probes use the accepted `_21` exact command binding + IPFW counter-growth + cleanup
   attribution boundary;
8. planner/frontier ordering remains authoritative and deterministic;
9. batch cleanup is mandatory before the next batch;
10. warm infrastructure failure disables warm execution and falls back to Model A;
11. Stage 70/80/85 ownership and inputs remain unchanged;
12. Stage 90 semantic restoration remains mandatory.

`STRATEGY_LAB_STAGE60_MODEL=cold` remains the explicit rollback/testing selector.

==================================================
HISTORICAL STAGE-60 TIMEOUT NOTE
==================================================

Do not infer the current completion contract from the old `_9` three-winner run.

`v0.4.0_6` exposed the old fixed Stage-60 parent boundary after only part of the graph.
`v0.4.0_7` closed that defect with Standard and Extended 16/16 Stage-60 completion, and
`v0.4.0_8` closed the observed late-stage containment boundary.

A current 16/16 Stage-60 result is therefore normal when the current winner target is not
reached. The `_22` Standard `rutracker.org` run found two winners and truthfully ended with
`graph_exhausted` / `within_normal_band=true`.

==================================================
FUTURE EXPERIMENT RULES
==================================================

No new runtime architecture is selected merely because it appears faster in source tests.
Any future Model C, width greater than three, dispatcher/bucket, endpoint-parallel, or other
runtime optimization must be a separate experiment with:

- fixed current source/reference inputs;
- exact result-equivalence checks;
- traffic attribution;
- bounded concurrency and resource measurement;
- failure/cleanup/restoration controls;
- repeated owner-live evidence before architecture selection;
- a separate production integration patch after selection.

CPU count remains measurement metadata, not a direct width selector.

==================================================
CURRENT WATCH ITEM
==================================================

`job.d5XV82` observed `controlled source port is already in use: 42003`. The production
fail-closed fallback behaved correctly and cleanup/restoration passed. Do not redesign the
source-port plan from one non-reproduced collision. If it recurs, collect active socket,
process, batch/source-port plan and rule evidence first, then decide whether a corrective
experiment/patch is justified.
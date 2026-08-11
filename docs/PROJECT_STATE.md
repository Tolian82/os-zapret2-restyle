# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the fastest authoritative recovery of current version, verified live boundary,
blockers, active architectural direction, and next action.

Read after:
`AGENTS.md` and `docs/INDEX.md`.

Do not store here:
Full chronological history, detailed implementation design, or complete test logs.
Those belong in `docs/devlog/`, `docs/patches/`, and `docs/verification/evidence/`.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current source line: `VERSION=0.4.0`, `PLUGIN_REVISION=22`
Current source candidate: `os-zapret2-restyle-0.4.0_22.pkg`
Latest published testing prerelease: `v0.4.0_22`
Latest owner-tested testing candidate: `v0.4.0_22`
Required package ABI: `FreeBSD:15:amd64`
Current `_22` merge commit: `cfb3c86a2dfafefa0f3fffb002fad9fa4278da71`

Current Strategy Lab production Stage-60 engine:
`B-warm-worker-parallel-batched`, fixed candidate width at most 3, no CPU-count gate.

Cold Model A remains the correctness/runtime fallback when warm infrastructure cannot be
proven safe. Pinned endpoints remain sequential inside one candidate. Candidate-level work
may overlap only inside the accepted width-three boundary.

==================================================
AUTHORITATIVE CURRENT LIVE BOUNDARY
==================================================

Current owner-live evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

The current `_22` owner-live set contains three completed jobs.

### Standard telegram.org — job.KpLHgb

- terminal outcome: `NO_CANDIDATE`;
- Stage 60 execution: `B-warm-worker-parallel-batched`;
- `graph_exhausted`, 16/16 candidates, zero winners;
- warm batches widths `3,3,3,3,3,1`;
- every width-three batch observed overlap 3;
- no warm fallback;
- Stage-60 adapter: `34227 ms`;
- total job through restoration: `89039 ms`;
- Stage 90: PASS;
- post-test dedicated rules `19128-19130`: absent.

This is the accepted current production no-candidate graph-exhaustion path.

### Standard rutracker.org — job.GK0X66

- terminal outcome: `SUCCESS`;
- Stage 60 execution: `B-warm-worker-parallel-batched`;
- 16/16 candidates completed;
- Stage-60 winners: `seqovl-host`, `seqovl-midsld`;
- `winner_count=2`, `within_normal_band=true`, `early_stop.triggered=false`;
- no warm fallback;
- Stage-60 adapter: `28151 ms`;
- total job: `81272 ms`;
- Stage 70: three stable candidates;
- Stage 85: three final candidates;
- Stage 90: PASS.

The 16/16 result is not the historical Stage-60 timeout/partial-completion defect. The
current run found two Stage-60 winners, below the target of three, so truthful graph
exhaustion is expected. Do not diagnose current behavior from the older `_9` run that
happened to obtain three Stage-60 winners and stopped after six candidates.

The explicit `_22` `early_stop.triggered=true` branch is not owner-live observed in this
supplied set because no `_22` run reached three Stage-60 winners. This is a coverage note,
not a current defect.

### Extended rutracker.org — job.d5XV82

- the first warm batch observed `controlled source port is already in use: 42003`;
- fail-closed fallback to `A-cold` activated for the rest of Stage 60;
- all 16 Stage-60 candidates still completed;
- the same two Stage-60 winners were retained;
- Stage-60 adapter: `35166 ms`;
- total job: `100444 ms`;
- Stage 80: PASS;
- Stage 90: PASS;
- post-test dedicated rules: absent.

This proves the production cold fallback/cleanup boundary live. It does not prove that the
one observed source-port collision is fixed. Investigate that condition only if it recurs or
can be reproduced.

==================================================
CURRENT ARCHITECTURE
==================================================

Strategy Lab automated orchestration is Python-owned. Python owns durable state/progress,
stage budgets and cancellation, request/probe execution and parsing, candidate/search
policy, Stage 50/60/70/80/85 behavior, shortlist/result generation and telemetry.

Audited shell adapters retain the narrow FreeBSD/OPNsense mutation boundary for dvtws2,
IPFW, lifecycle, process and filesystem operations.

Stage order remains:
`00 -> 10 -> 20 -> 30 -> 40 -> 50 -> 60 -> 70 -> 80 -> 85 -> 90 -> 99`.

Stage 60 uses the native Zapret2 deterministic search graph and fixed search epoch. Only
currently reachable frontier candidates may enter a parallel batch. Results are committed
in deterministic planner order rather than thread-completion order. Batch cleanup is
mandatory before the next batch.

Successful warm probes require the accepted `_21` connected-socket identity boundary.
Failed/blocked probes may establish ownership only through exact requested source-port
binding, exact pinned `--resolve` binding, exact matching IPFW counter growth and cleanup.

Warm infrastructure/readiness/attribution/cleanup failure disables warm execution for the
rest of Stage 60 and replays affected work through cold Model A subject to the normal budget.
Ordinary network FAIL/timeout evidence is not itself an infrastructure fallback trigger.

Stage 70/80/85 ownership and contracts are unchanged by `_22`. Stage 90 semantic restoration
remains mandatory on every terminal path.

==================================================
ACCEPTED HISTORICAL BASELINES
==================================================

These historical records remain valid comparison boundaries but must not override later
patch/PR/live evidence when diagnosing current behavior.

- `_32` timeout-containment gate: **OWNER-LIVE PASS through `v0.4.0_8`**.
- `_33` adaptive validation gate: **CHANGE-SPECIFIC OWNER-LIVE PASS on `v0.4.0_9`**.
- Model A experiment gate: **REFERENCE COLLECTED on `v0.4.0_11` / `job.TtZeaH`**.
- Model B coexistence: accepted on `_16`, repeated 5/5 on `_17`.
- Model B sequential exhaustive: sequential exhaustive ACCEPT 5/5 on `v0.4.0_19`, with a
  mean measured candidate-runtime speedup of about 15.96% versus the retained cold reference.
- Model B controlled parallel: `_21` produced six accepted controlled-parallel runs including
  five unchanged repeats; repeat mean `33025.6 ms`, about `62.90%` candidate-runtime reduction
  versus cold Model A and about `55.85%` versus sequential warm Model B; peak aggregate RSS
  remained roughly 13 MiB.

Historical Stage-60 note:
`v0.4.0_6` exposed the fixed parent timeout after only part of the graph; `v0.4.0_7` closed
that boundary with 16/16 Standard and Extended expansion runs; `v0.4.0_8` closed the observed
late-stage containment boundary. Therefore a current 16/16 Stage-60 run is not, by itself,
evidence of the old timeout defect.

==================================================
CURRENT WATCH ITEMS
==================================================

1. `job.d5XV82` observed one controlled source-port collision on `42003`. The fail-closed
   fallback worked correctly and cleanup/restoration passed. Do not change source solely from
   one non-reproduced collision; investigate if it recurs.
2. The explicit `_22` three-winner `early_stop.triggered=true` branch is automated-regression
   covered but was not reached by the supplied `_22` owner-live jobs. Do not confuse this
   coverage note with the already-fixed historical Stage-60 partial/timeout defect.
3. Rows in the broader live regression matrix that were not selected for the current change
   remain backlog rather than blanket release blockers.

==================================================
DOCUMENT / EVIDENCE PRECEDENCE FOR CURRENT DIAGNOSIS
==================================================

Before diagnosing a current package from historical evidence:

1. read the current `PROJECT_STATE.md`;
2. read the patch document for the installed/current revision;
3. read the current revision's PR conversation and owner-live comments when available;
4. read the latest dated verification evidence for that revision;
5. use older evidence only as a historical comparison unless a current document explicitly
   retains it as an active contract.

If those sources disagree, later source/patch/PR/live evidence wins for current-state claims;
historical records remain preserved as history and must not be silently rewritten.

==================================================
NEXT ACTION
==================================================

Treat `_22` production Model B as the active Stage-60 implementation and use the recorded
owner-live jobs as the current baseline. No correction is justified by the old six-candidate
`_9` behavior.

If the controlled-source-port collision recurs, collect the exact active socket/process and
Stage-60 batch evidence before deciding on a corrective patch. Otherwise continue the
planned Strategy Lab work from the `_22` production baseline.
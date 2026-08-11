# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.0_22` PRODUCTION STAGE-60 MODEL B OWNER-LIVE PASS FOR STANDARD NO-CANDIDATE AND WORKING-CANDIDATE PATHS; EXTENDED FAIL-CLOSED COLD FALLBACK OBSERVED; BROADER REGRESSION MATRIX REMAINS RISK-SELECTED.**

This matrix is the canonical live-appliance regression inventory for Strategy Lab. Source
tests, GitHub CI, and FreeBSD package builds cannot substitute for owner-live evidence when
a row or change-specific behavior is selected for live verification. Not every pending row
is automatically a release blocker; selection follows
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

Detailed historical logs remain under `docs/verification/evidence/`. Current diagnosis must
start from the current patch, PR/live comments and latest dated evidence before historical
records are used for comparison.

Only FreeBSD 15 amd64 packages are valid.

==================================================
TEST RECORD
==================================================

- Tester: repository owner
- Latest test date/time: `2026-08-11`
- OPNsense version: `26.7.1_1`; kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Required package ABI: `FreeBSD:15:amd64`
- Latest published testing candidate: `os-zapret2-restyle-0.4.0_22.pkg`
- Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_22.pkg`
- Current source candidate: `os-zapret2-restyle-0.4.0_22.pkg`
- Current Stage-60 production engine: `B-warm-worker-parallel-batched`
- Production candidate width: at most `3`, fixed and not CPU-count gated
- Cold Model A: correctness/runtime fallback after warm infrastructure failure
- Latest Standard no-winner job: `job.KpLHgb` (`telegram.org`, 16/16 `graph_exhausted`)
- Latest Standard working-candidate job: `job.GK0X66` (`rutracker.org`)
- Latest Extended working-candidate/fallback job: `job.d5XV82` (`rutracker.org`)
- Historical no-candidate reference `job.tMYnFA` includes `telegram.org` and `web.telegram.org`
- Generic UDP target/port: `PENDING OWNER`

Current accepted owner-live evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

Current production patch contract:
`docs/patches/v0.4.0_22.md`.

Accepted parallel architecture evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_21-model-b-parallel-reproducibility.md`.

==================================================
CURRENT `_22` PRODUCTION LIVE RESULTS
==================================================

### Standard telegram.org — job.KpLHgb

- outcome `NO_CANDIDATE`;
- Stage 60 `B-warm-worker-parallel-batched`;
- 16/16 complete, zero winners, `graph_exhausted`;
- warm batch widths `3,3,3,3,3,1`;
- every width-three batch observed overlap `3`;
- no fallback;
- Stage 60 `34227 ms`;
- total job `89039 ms`;
- Stage 90 PASS and no rules `19128-19130` after the completed test set.

### Standard rutracker.org — job.GK0X66

- outcome `SUCCESS`;
- Stage 60 remained production Model B with no fallback;
- 16/16 complete;
- winners `seqovl-host` and `seqovl-midsld`;
- `winner_count=2`, `within_normal_band=true`, `early_stop.triggered=false`;
- Stage 60 `28151 ms`;
- total job `81272 ms`;
- Stage 70 produced three stable candidates;
- Stage 85 produced three final candidates;
- Stage 90 PASS.

The 16/16 result is current truthful behavior, not the historical fixed-timeout defect.
This `_22` run found two Stage-60 winners, below the target of three, and therefore exhausted
the graph. The older `_9` run happened to obtain three winners and stopped after six
candidates; that historical outcome must not be used as the current completion rule.

### Extended rutracker.org — job.d5XV82

- first warm batch observed `controlled source port is already in use: 42003`;
- fail-closed fallback to `A-cold` activated for the rest of Stage 60;
- all 16 candidates completed with the same two Stage-60 winners;
- Stage 60 `35166 ms`;
- total job `100444 ms`;
- Stage 80 PASS;
- Stage 90 PASS;
- no dedicated Model B rule residue after the completed test set.

The fallback is owner-live verified. The single `42003` collision is an observed condition,
not a proven corrected defect; investigate only if it recurs or can be reproduced.

The explicit `_22` `early_stop.triggered=true` branch was not reached by this supplied set
because no `_22` run reached three Stage-60 winners. This is a coverage statement, not a
regression claim.

==================================================
VERIFIED PROGRESSION — CURRENT INTERPRETATION
==================================================

- `_27` produced the selected v0.4.0 Scenario 1 live PASS.
- Adaptive `_28` focused evidence is retained in
  `docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`.
- `v0.4.0_6` exposed the fixed Stage-60 parent boundary after only part of the graph;
  evidence: `2026-08-09-v0.4.0_6-stage60-timeout.md`.
- `v0.4.0_7` closed that Stage-60 boundary: Standard and Extended both completed 16/16;
  evidence: `2026-08-10-v0.4.0_7-late-stage-pass.md`.
- `v0.4.0_8` closed the observed late-stage containment boundary;
  evidence: `2026-08-10-v0.4.0_8-timeout-containment-pass.md`.
- `_9` remains historical adaptive-validation evidence. Its Standard no-candidate run took
  about 144.125 s. Its three-winner `rutracker.org` run completed in about 71.023 s. These
  timings/results are historical comparisons, not current `_22` completion rules.
- Model A cold reference was collected on `_11` / `job.TtZeaH` with median candidate RSS
  4332 KiB.
- MODEL B `_17` REPEATED OWNER-LIVE COEXISTENCE ACCEPT — EXPERIMENT ONLY: five accepted
  repeats; already-warm dispatch+probe path about 86.5% below the retained Model A median;
  startup-amortized estimate roughly 62.0% lower.
- `_19` sequential exhaustive no-candidate Model B replay accepted 5/5. Warm exhaustive
  mean 74.8082 s versus 89.012 s retained cold candidate runtime, about 15.96% measured
  candidate-runtime speedup.
- `_20` introduced controlled parallel candidate probing and exposed a failed-probe route
  attribution false reject.
- `_21` corrected that attribution contract and produced six accepted controlled-parallel
  runs including five unchanged repeats. Repeat mean was `33025.6 ms`, about `62.90%`
  faster than the cold candidate runtime and about `55.85%` faster than sequential warm
  Model B, with roughly 13 MiB peak aggregate RSS.
- `_22` integrated the accepted width-three Model B semantics into the real Stage 60. The
  owner-live jobs above verify the real production no-candidate path, real warm working-
  candidate path, fail-closed cold fallback, and clean restoration.

==================================================
MODEL A COLD REFERENCE — PASS ON `v0.4.0_11`
==================================================

Accepted evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

The retained reference contains 25 cold samples, PASS/FAIL candidates, repetitions,
`blob-free`/`builtin`/`external` resource classes, range variation, numeric RSS and verified
restoration. Model A remains the correctness/fallback reference; it is no longer the normal
Stage-60 production engine on `_22`.

==================================================
MODEL B `_17` REPEATED OWNER-LIVE COEXISTENCE ACCEPT — EXPERIMENT ONLY
==================================================

Accepted historical evidence:

- `docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`.

This section is retained as the coexistence baseline that preceded exhaustive and parallel
search experiments. It does not override later `_21` or `_22` evidence.

==================================================
MODEL B `_18` / `_19` EXHAUSTIVE NO-CANDIDATE BENCHMARK — OWNER-LIVE ACCEPT
==================================================

Historical reference `job.tMYnFA` supplies 16/16 cold Stage-60 candidates over the pinned
`telegram.org` / `web.telegram.org` endpoint epoch. `_19` replayed the complete corpus five
times using warm workers. Mean measured wall time was 74.8082 s and mean measured
candidate-runtime speedup was about 15.96%.

Evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`.

==================================================
MODEL B `_20` / `_21` CONTROLLED PARALLEL EXPERIMENT — ACCEPTED ARCHITECTURE INPUT
==================================================

`_20` introduced unique controlled TCP source ports, source-port-qualified IPFW rules and
candidate-level concurrency up to width three while endpoints remained sequential inside a
candidate. `_21` corrected failed-probe attribution and then produced reproducible owner-live
ACCEPT evidence. This accepted experiment is the architecture input implemented in `_22`.

Decision:
`docs/decisions/DEC-2026-08-11-strategy-lab-parallel-model-b-selection.md`.

==================================================
PYTHON MIGRATION OWNERSHIP
==================================================

The automated Strategy Lab Python migration is complete. Python owns automated state,
stage orchestration, finite requests/probes, candidate/search policy, Stage 50/60/70/80/85,
final results and telemetry. Audited FreeBSD mutations and private lifecycle state remain
narrow shell boundaries.

Authoritative plan:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

==================================================
SCENARIO MATRIX
==================================================

| # | Scenario | Required expected result | Evidence location | Result |
|---|---|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result truthful; Stage 90 restores RUNNING; no temporary residue | `2026-08-08-v0.3.3_27-scenario-01-pass.md`; current `_22` production evidence also exercises RUNNING restoration | **PASS ON `_27` — v0.4.0 mandatory row** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Final service remains STOPPED; restoration verified | `PENDING OWNER` | **PENDING REGRESSION** |
| 3 | Extended TLS 1.2 and HTTP | Available successes replay-verified; unavailable protocols explicitly skipped | `_22` Extended working path observed, but dedicated formal row remains unselected | **PENDING REGRESSION** |
| 4 | Extended QUIC | Endpoint-bound/replay-verified when available; otherwise explicit skip | `PENDING OWNER` | **PENDING REGRESSION** |
| 5 | Generic UDP port and payload | Accepted only in Extended mode; complete profile and cleanup | `PENDING OWNER` | **PENDING REGRESSION** |
| 6 | Target already accessible | `TARGET_ACCESSIBLE`; search skipped; service state exact | `PENDING OWNER` | **PENDING REGRESSION** |
| 7 | No working candidate | `NO_CANDIDATE`; shortlist empty; restoration verified | `_22` `job.KpLHgb` provides current change-specific no-candidate evidence; dedicated formal row remains unselected | **PENDING REGRESSION** |
| 8 | User cancellation after service stop | Unfinished stages skipped; 90/99 run; original service restored | `PENDING OWNER` | **PENDING REGRESSION** |
| 9 | Hard whole-worker timeout | `TIMEOUT`; results persist; restoration verified | `PENDING OWNER` | **PENDING REGRESSION** |
| 10 | Controlled internal failure | `ERROR`; truthful stage; restoration verified | `PENDING OWNER` | **PENDING REGRESSION** |
| 11 | Circular start/browser validation/stop | Parent files unchanged; private session; clean stop | `PENDING OWNER` | **PENDING REGRESSION** |
| 12 | Circular stale-worker recovery | Owner mismatch handled; cleanup/restoration verified | `PENDING OWNER` | **PENDING REGRESSION** |
| 13 | Settings Apply during automated Strategy Lab | Apply rejected before mutation; config unchanged | `PENDING OWNER` | **PENDING REGRESSION** |
| 14 | Settings Apply during circular or restore_failed | Apply rejected until restoration proven | `PENDING OWNER` | **PENDING REGRESSION** |
| 15 | Diagnostics page reload | Active reload resumes; terminal reload preserves evidence | `PENDING OWNER` | **PENDING REGRESSION** |
| 16 | Russian and English presentation | Deterministic localized presentation | `PENDING OWNER` | **PENDING REGRESSION** |
| 17 | Retention with reduced limits | Protected evidence retained; only excess verified terminal artifacts removed | `PENDING OWNER` | **PENDING REGRESSION** |
| 18 | Reboot after clean terminal completion | No temporary residue returns; normal service/rules valid | `PENDING OWNER` | **PENDING REGRESSION** |

==================================================
CONFIRMED DEFECTS / LIVE RECHECKS
==================================================

- Stage 40 DNS timeout on `_26`: closed by `_27` owner live Scenario 1 PASS.
- Stage 50 aggregate abort on `_25`: closed by `_27`.
- Stage 60 fixed 70-second parent timeout on `v0.4.0_6`: closed by `v0.4.0_7` with 16/16 Standard and Extended runs.
- Late-stage containment after Stage 60: closed for observed normal paths by `v0.4.0_8`.
- Adaptive validation depth/winner path: change-specific live PASS on `_9`; retained as historical evidence.
- Model A measurement: reference collected on `_11`.
- Model B coexistence/readiness/access corrections: accepted through `_16`/`_17`.
- Model B exhaustive multi-endpoint replay: accepted 5/5 on `_19`.
- Model B controlled parallel attribution: `_20` false reject corrected by `_21`; `_21` accepted reproducibly.
- Production Model B Stage 60: `_22` current owner-live evidence records Standard warm no-candidate and working-candidate PASS plus safe Extended cold fallback.
- Controlled source port `42003` collision: observed once in `job.d5XV82`; fallback/cleanup PASS; source collision itself not declared fixed or reproducible.

==================================================
FAILURE HANDLING / RELEASE GATE
==================================================

A mandatory selected live behavior fails if restoration is unverified, saved strategy is
unexpectedly changed, temporary workers/rules remain, lifecycle ownership is violated, or
required evidence is missing. CI alone never turns a live requirement into PASS.

Stable release preparation follows the risk-based selection policy; this matrix is not an
all-or-nothing release checklist. Rows 2-18 remain regression backlog unless explicitly
selected for a release/change. Current `_22` change-specific owner-live evidence is recorded
above and in the dedicated evidence file.
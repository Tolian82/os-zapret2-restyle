# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.0_23` MODEL-C PRODUCTION CANDIDATE PENDING OWNER-LIVE VERIFICATION; `v0.4.0_22` MODEL-B OWNER-LIVE BASELINE REMAINS ACCEPTED; BROADER REGRESSION MATRIX REMAINS RISK-SELECTED.**

This matrix is the canonical live-appliance regression inventory for Strategy Lab. Source
tests, GitHub CI and FreeBSD package builds do not substitute for owner-live evidence when
a behavior is selected for live verification. Not every pending row is automatically a
release blocker; selection follows
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

Detailed historical logs remain under `docs/verification/evidence/`. Current diagnosis must
start from the current patch, PR/live comments and latest dated evidence before historical
records are used for comparison.

Only FreeBSD 15 amd64 packages are valid.

==================================================
TEST RECORD
==================================================

- Tester: repository owner
- Latest completed test date/time: `2026-08-11`
- OPNsense version: `26.7.1_1`; kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Required package ABI: `FreeBSD:15:amd64`
- Latest published testing candidate before `_23` publication: `os-zapret2-restyle-0.4.0_22.pkg`
- Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_22.pkg`
- Current source candidate: `os-zapret2-restyle-0.4.0_23.pkg`
- Current Stage-60 production candidate: `C-warm-bucket-source-port-dispatch`
- Immediate runtime fallback/reference: `B-warm-worker-parallel-batched`
- Final runtime fallback: cold Model A
- Candidate width: at most `3`, fixed and not CPU-count gated
- Pinned endpoints inside one candidate: sequential
- Latest Standard no-winner job: `job.KpLHgb` (`telegram.org`, 16/16 `graph_exhausted`)
- Latest Standard working-candidate job: `job.GK0X66` (`rutracker.org`)
- Latest Extended working-candidate/fallback job: `job.d5XV82` (`rutracker.org`)
- Generic UDP target/port: `PENDING OWNER`

Current `_23` patch/decision:

- `docs/patches/v0.4.0_23.md`;
- `docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`.

Latest accepted owner-live evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

==================================================
CURRENT `_23` CHANGE-SPECIFIC LIVE GATE — PENDING PACKAGE TEST
==================================================

The owner explicitly requested publication before live testing. Therefore `_23` becomes
source/CI/package-qualified first, then these checks are run on the published package.
Until they pass, do not relabel `_22` evidence as `_23` evidence.

Required first live set:

1. **Normal Model-C ownership** — Stage 60 reports
   `C-warm-bucket-source-port-dispatch` with no silent Model-B fallback.
2. **One-worker bucket identity** — at least one multi-candidate batch records
   `physical_worker_count=1`, one bucket PID/divert port, distinct candidate route rules and
   exact per-candidate selector source-port sets.
3. **Standard no-candidate path** — use a blocked target such as the retained
   `telegram.org` comparison and require truthful graph exhaustion/no false PASS.
4. **Standard working-candidate path** — use the retained `rutracker.org` comparison and
   require truthful Stage-60 winners plus unchanged Stage-70/85 handoff.
5. **Attribution** — successful probes keep strict connected-socket endpoint/local-port
   identity; failed probes keep exact command source-port + exact pinned resolve + matching
   IPFW counter growth + cleanup.
6. **Fallback** — if Model C is unavailable, evidence must identify Model B; if Model B is
   also unavailable, the existing cold Model-A fallback remains the final fail-closed path.
7. **Restoration/residue** — Stage 90 verifies original service state and dedicated rules
   `19128-19130` are absent after terminal completion.

Cancellation/failure coverage remains automated and may be selected for an additional live
run if the first appliance evidence exposes a runtime-only ambiguity.

==================================================
ACCEPTED `_22` PRODUCTION MODEL-B LIVE BASELINE
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
- Stage 60 remained Model B with no fallback;
- 16/16 complete;
- winners `seqovl-host` and `seqovl-midsld`;
- `winner_count=2`, `within_normal_band=true`, `early_stop.triggered=false`;
- Stage 60 `28151 ms`;
- total job `81272 ms`;
- Stage 70 produced three stable candidates;
- Stage 85 produced three final candidates;
- Stage 90 PASS.

The 16/16 result is truthful current search behavior, not the historical fixed-timeout
defect. This `_22` run found two Stage-60 winners, below the target of three, and therefore
exhausted the graph. The older `_9` run happened to obtain three winners and stopped after
six candidates; that historical outcome is not a current completion rule.

### Extended rutracker.org — job.d5XV82

- first warm batch observed `controlled source port is already in use: 42003`;
- fail-closed fallback to `A-cold` activated for the rest of Stage 60;
- all 16 candidates completed with the same two Stage-60 winners;
- Stage 60 `35166 ms`;
- total job `100444 ms`;
- Stage 80 PASS;
- Stage 90 PASS;
- no dedicated Model-B rule residue after the completed test set.

The fallback is owner-live verified. The single `42003` collision is an observed condition,
not a proven corrected defect; investigate only if it recurs or can be reproduced.

The explicit `_22` `early_stop.triggered=true` branch was not reached by this supplied set
because no `_22` run reached three Stage-60 winners. This is a coverage statement, not a
regression claim.

==================================================
VERIFIED PROGRESSION — RETAINED HISTORY
==================================================

- `_27` produced the selected v0.4.0 Scenario 1 live PASS.
- Adaptive `_28` focused evidence:
  `docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`.
- `v0.4.0_6` exposed the fixed Stage-60 parent boundary after only part of the graph;
  evidence: `2026-08-09-v0.4.0_6-stage60-timeout.md`.
- `v0.4.0_7` closed that Stage-60 boundary: Standard and Extended both completed 16/16;
  evidence: `2026-08-10-v0.4.0_7-late-stage-pass.md`.
- `v0.4.0_8` closed the observed late-stage containment boundary;
  evidence: `2026-08-10-v0.4.0_8-timeout-containment-pass.md`.
- `_9` is historical adaptive-validation evidence. Standard no-candidate completed in
  about 144.125 s; its three-winner `rutracker.org` run completed in about 71.023 s.
- Model A cold reference was collected on `_11` / `job.TtZeaH` with median candidate RSS
  4332 KiB.
- MODEL B `_17` REPEATED OWNER-LIVE COEXISTENCE ACCEPT — EXPERIMENT ONLY: five accepted
  repeats; already-warm dispatch+probe path about 86.5% below the retained Model A median;
  startup-amortized estimate roughly 62.0% lower.
- `_19` sequential exhaustive no-candidate Model B replay accepted 5/5: mean 74.8082 s
  versus 89.012 s retained cold candidate runtime, about 15.96% measured candidate-runtime
  speedup.
- `_20` introduced controlled parallel candidate probing and exposed a failed-probe route
  attribution false reject.
- `_21` corrected attribution and produced six accepted controlled-parallel runs including
  five unchanged repeats. Repeat mean `33025.6 ms`, about `62.90%` faster than cold candidate
  runtime and about `55.85%` faster than sequential warm Model B, with roughly 13 MiB peak RSS.
- `_22` integrated Model B into real Stage 60 and the owner-live jobs above accepted the
  no-candidate, working-candidate, fallback and restoration boundaries.
- `_23` is the next forward production candidate: one physical Model-C bucket with exact
  source-port Lua dispatch, accepted Model B fallback and cold Model A final fallback.

==================================================
MODEL A COLD REFERENCE — PASS ON `v0.4.0_11`
==================================================

Accepted evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

The retained reference contains 25 cold samples, PASS/FAIL candidates, repetitions,
`blob-free`/`builtin`/`external` resource classes, range variation, numeric RSS and verified
restoration. Model A remains the final correctness/fallback reference.

==================================================
MODEL B `_17` REPEATED OWNER-LIVE COEXISTENCE ACCEPT — EXPERIMENT ONLY
==================================================

Accepted historical evidence:

- `docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`.

This section is retained as the coexistence baseline that preceded exhaustive and parallel
search experiments. It does not override later `_21`, `_22` or `_23` state.

==================================================
MODEL B `_18` / `_19` EXHAUSTIVE NO-CANDIDATE BENCHMARK — OWNER-LIVE ACCEPT
==================================================

Historical `job.tMYnFA` supplies 16/16 cold Stage-60 candidates over the pinned
`telegram.org` / `web.telegram.org` endpoint epoch. `_19` replayed the complete corpus five
times using warm workers. Mean measured wall time was 74.8082 s and mean measured
candidate-runtime speedup was about 15.96%.

Evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_19-model-b-exhaustive-reproducibility.md`.

==================================================
MODEL B `_20` / `_21` CONTROLLED PARALLEL EXPERIMENT — ACCEPTED FALLBACK AUTHORITY
==================================================

`_20` introduced unique controlled TCP source ports, source-port-qualified IPFW rules and
candidate-level concurrency up to width three while endpoints remained sequential inside a
candidate. `_21` corrected failed-probe attribution and produced reproducible owner-live
ACCEPT evidence. `_22` made that architecture production-active; `_23` retains it as the
immediate runtime fallback/reference.

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
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result truthful; Stage 90 restores RUNNING; no temporary residue | `2026-08-08-v0.3.3_27-scenario-01-pass.md`; `_22` also exercises RUNNING restoration | **PASS ON `_27` — v0.4.0 mandatory row** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Final service remains STOPPED; restoration verified | `PENDING OWNER` | **PENDING REGRESSION** |
| 3 | Extended TLS 1.2 and HTTP | Available successes replay-verified; unavailable protocols explicitly skipped | `_22` Extended working path observed; dedicated formal row unselected | **PENDING REGRESSION** |
| 4 | Extended QUIC | Endpoint-bound/replay-verified when available; otherwise explicit skip | `PENDING OWNER` | **PENDING REGRESSION** |
| 5 | Generic UDP port and payload | Accepted only in Extended mode; complete profile and cleanup | `PENDING OWNER` | **PENDING REGRESSION** |
| 6 | Target already accessible | `TARGET_ACCESSIBLE`; search skipped; service state exact | `PENDING OWNER` | **PENDING REGRESSION** |
| 7 | No working candidate | `NO_CANDIDATE`; shortlist empty; restoration verified | `_22` `job.KpLHgb` accepted baseline; `_23` change-specific recheck pending | **PENDING REGRESSION** |
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

- Stage 40 DNS timeout on `_26`: closed by `_27` owner-live Scenario 1 PASS.
- Stage 50 aggregate abort on `_25`: closed by `_27`.
- Stage 60 fixed 70-second parent timeout on `v0.4.0_6`: closed by `v0.4.0_7` with
  16/16 Standard and Extended runs.
- Late-stage containment after Stage 60: closed for observed normal paths by `v0.4.0_8`.
- Adaptive validation depth/winner path: change-specific live PASS on `_9`.
- Model A measurement: reference collected on `_11`.
- Model B coexistence/readiness/access corrections: accepted through `_16`/`_17`.
- Model B exhaustive multi-endpoint replay: accepted 5/5 on `_19`.
- Model B controlled parallel attribution: `_20` false reject corrected by `_21`; `_21`
  accepted reproducibly.
- Production Model B Stage 60: `_22` owner-live evidence accepted Standard warm no-candidate
  and working-candidate paths plus safe Extended cold fallback.
- Controlled source port `42003` collision: observed once in `job.d5XV82`; fallback/cleanup
  PASS; source collision itself not declared fixed or reproducible.
- Model C Stage 60: `_23` source/package candidate; owner-live status remains PENDING until
  the published package is tested.

==================================================
FAILURE HANDLING / RELEASE GATE
==================================================

A selected mandatory live behavior fails if restoration is unverified, saved strategy is
unexpectedly changed, temporary workers/rules remain, lifecycle ownership is violated or
required evidence is missing. CI alone never turns a live requirement into PASS.

Stable release preparation follows the risk-based selection policy; this matrix is not an
all-or-nothing release checklist. Rows 2-18 remain regression backlog unless explicitly
selected for a release/change. `_23` testing-prerelease publication is authorized before
its focused owner-live Model-C gate and does not imply stable-release promotion.

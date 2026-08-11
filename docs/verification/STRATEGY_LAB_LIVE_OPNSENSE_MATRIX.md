# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.0_25` SOURCE-PORT CORRECTIVE PENDING OWNER-LIVE VERIFICATION; `_23` PROVED MODEL C LIVE AND EXPOSED THE SHARED `42004` COLLISION; `_22` REMAINS THE ACCEPTED MODEL-B FALLBACK BASELINE.**

This matrix is the canonical live-appliance regression inventory. Source tests, GitHub CI
and FreeBSD package builds do not substitute for selected owner-live evidence. Detailed
historical logs remain under `docs/verification/evidence/`; current diagnosis starts from
`docs/PROJECT_STATE.md`, the current patch, current PR/live comments and latest dated
evidence before older records are used.

Only FreeBSD 15 amd64 packages are valid.

==================================================
TEST RECORD
==================================================

- Tester: repository owner
- Latest completed test date: `2026-08-11`
- OPNsense: `26.7.1_1`; FreeBSD 15 amd64
- Current source candidate: `os-zapret2-restyle-0.4.0_25.pkg`
- Latest published/owner-tested package before `_25`: `os-zapret2-restyle-0.4.0_23.pkg`
- Preferred Stage-60 model: `C-warm-bucket-source-port-dispatch`
- Immediate fallback/reference: `B-warm-worker-parallel-batched`
- Final fallback: cold Model A
- Candidate width: at most 3, not CPU-count gated
- Pinned endpoints inside one candidate: sequential

Current change authority:

- `docs/patches/v0.4.0_25.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_23-model-c-live-hold.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`.

==================================================
`_23` OWNER-LIVE MODEL-C EVIDENCE
==================================================

### Extended rutracker.org — `job.FaLtIk`

- outcome `SUCCESS`;
- Stage 60 genuinely used `C-warm-bucket-source-port-dispatch`;
- 16/16 candidates completed, `graph_exhausted`;
- winners `seqovl-host` and `seqovl-midsld`;
- multi-candidate batches used `physical_worker_count=1`, exact selector source-port sets
  and dedicated rules `19128-19130`;
- no fallback;
- Stage 70/80/85 succeeded;
- semantic Stage-90 restoration succeeded.

This run proves that the one-worker Model-C dispatcher is viable on the owner appliance.

### Extended telegram.org — `job.G0wC5l`

- IPv4 available; IPv6 unavailable; QUIC/IPv4 closed, so IPv6/QUIC were excluded;
- first warm batch reported:
  `Model C unavailable (controlled source port is already in use: 42004); Model B fallback failed (controlled source port is already in use: 42004)`;
- both warm models inherited the same static concrete source-port plan;
- Stage 60 therefore used `A-cold-fallback`, completed 13 candidates, zero winners;
- `stopped_reason=insufficient_stage_budget`; Stage 60 reported `TIMEOUT`;
- restoration was exact RUNNING -> RUNNING with identical runtime/config/firewall hashes and
  `temporary_runtime_clean=true`.

This is a source-port ownership/fallback amplification defect, not the historical `_7`/`_8`
fixed-parent-timeout defect and not a lifecycle-restoration failure.

==================================================
CURRENT `_25` CHANGE-SPECIFIC LIVE GATE
==================================================

`_25` keeps deterministic `42000+` values as preferred ports but leases exact free concrete
ports per admitted warm batch. Foreign occupied ports are skipped without destructive
action. Model B fallback performs a fresh lease rather than inheriting Model C's failed
concrete port. Exact IPFW/curl/endpoint attribution remains unchanged.

Required first live recheck after publication:

1. Extended `telegram.org` completes through normal Model C unless another genuine
   infrastructure failure occurs.
2. If preferred `42004` (or another preferred port) is occupied, Stage-60 evidence records a
   lease replacement rather than a shared Model-C/Model-B collision.
3. Model-C `selector_ports` use the actual leased ports.
4. Successful probes retain connected endpoint/local-port identity; failed probes retain
   exact command source-port + pinned `--resolve` + exact IPFW counter growth + cleanup.
5. Stage 90 restores the original semantic service state and rules `19128-19130` leave no
   residue.

Timeout values are intentionally unchanged in `_25` so the source-port correction is
measured without hiding accidental cold fallback behind a larger limit.

==================================================
FOLLOW-UP TIMING DESIGN — ADAPTIVE BUDGET
==================================================

After `_25` is measured, Strategy Lab budget must be derived from the actual eligible work
matrix:

`number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode`.

Available/selected IPv6, QUIC and Generic UDP work should automatically add a finite
reasonable budget proportional to the real work. Do not replace this with one guessed
oversized static timeout. Admission, stage/overall deadlines, cancellation and telemetry
remain finite and observable.

==================================================
ACCEPTED `_22` MODEL-B COMPARISON BASELINE
==================================================

### Standard telegram.org — `job.KpLHgb`

- `NO_CANDIDATE`, 16/16, zero winners, `graph_exhausted`;
- Model B widths `3,3,3,3,3,1`, overlap 3 in width-three batches;
- no fallback;
- Stage 60 `34227 ms`; total `89039 ms`; clean restoration.

### Standard rutracker.org — `job.GK0X66`

- `SUCCESS`, 16/16;
- winners `seqovl-host`, `seqovl-midsld`;
- Stage 60 `28151 ms`; total `81272 ms`;
- Stage 70/85 and restoration successful.

### Extended rutracker.org — `job.d5XV82`

- historical `controlled source port is already in use: 42003` activated cold fallback;
- all 16 candidates completed with the same two winners;
- Stage 60 `35166 ms`; total `100444 ms`;
- Stage 80/restoration successful.

The current 16/16 behavior is truthful search behavior. The older `_9` run happened to reach
three winners and stop after six candidates; that is historical evidence, not a current
completion rule.

==================================================
RETAINED PROGRESSION
==================================================

- Adaptive `_28` focused evidence:
  `docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`.
- `v0.4.0_6` exposed the old fixed Stage-60 parent boundary at approximately 70 s.
- `v0.4.0_7` closed it with 16/16 Standard and Extended completion.
- `v0.4.0_8` closed observed late-stage containment.
- `_9` historical adaptive runs were about 144.125 s no-candidate and about 71.023 s for
  its three-winner path.
- Model A reference: `_11` / `job.TtZeaH`.
- Model B coexistence `_17`: about 86.5% lower already-warm dispatch+probe path and roughly 62.0% startup-amortized improvement versus retained cold reference.
- Model B exhaustive `_19`: mean 74.8082 s, about 15.96% improvement versus cold candidate
  runtime.
- `_20` exposed failed-probe attribution false reject; `_21` corrected it and produced
  reproducible controlled-parallel acceptance.
- `_22` integrated Model B into production and owner-live accepted no-candidate,
  working-candidate, fallback and restoration boundaries.
- `_23` integrated Model C; owner-live `job.FaLtIk` proved it works and `job.G0wC5l` exposed
  shared static source-port collision amplification.
- `_25` is the corrective source-port lease candidate; `_24` is intentionally skipped by
  owner instruction.

==================================================
SCENARIO MATRIX
==================================================

| # | Scenario | Required expected result | Evidence location | Result |
|---|---|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result truthful; Stage 90 restores RUNNING; no temporary residue | `2026-08-08-v0.3.3_27-scenario-01-pass.md`; later `_22/_23` also exercise RUNNING restoration | **PASS ON `_27` — v0.4.0 mandatory row** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Final service remains STOPPED; restoration verified | `PENDING OWNER` | **PENDING REGRESSION** |
| 3 | Extended TLS 1.2 and HTTP | Available successes replay-verified; unavailable protocols explicitly skipped | `_23` Extended working path observed; dedicated formal row unselected | **PENDING REGRESSION** |
| 4 | Extended QUIC | Endpoint-bound/replay-verified when available; otherwise explicit skip | `PENDING OWNER` | **PENDING REGRESSION** |
| 5 | Generic UDP port and payload | Accepted only in Extended mode; complete profile and cleanup | `PENDING OWNER` | **PENDING REGRESSION** |
| 6 | Target already accessible | `TARGET_ACCESSIBLE`; search skipped; service state exact | `PENDING OWNER` | **PENDING REGRESSION** |
| 7 | No working candidate | `NO_CANDIDATE`; shortlist empty; restoration verified | `_22` accepted baseline; `_25` change-specific recheck selected | **PENDING REGRESSION** |
| 8 | User cancellation after service stop | Unfinished stages skipped; 90/99 run; original service restored | `PENDING OWNER` | **PENDING REGRESSION** |
| 9 | Hard whole-worker timeout | `TIMEOUT`; results persist; restoration verified | `_23 job.G0wC5l` observed Stage-60 timeout with exact restoration; dedicated formal row unselected | **PENDING REGRESSION** |
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
FAILURE / RELEASE POLICY
==================================================

Selected live behavior fails if restoration is unverified, saved strategy changes
unexpectedly, temporary workers/rules remain, lifecycle ownership is violated, or the
result is falsely classified. Broader pending rows remain risk-selected regression backlog,
not an all-or-nothing release checklist.

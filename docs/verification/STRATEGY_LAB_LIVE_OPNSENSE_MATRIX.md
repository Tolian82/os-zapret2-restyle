# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` MODEL-C-ONLY OWNER-LIVE PASS; INITIAL-ZAPRET2-STOPPED IS THE CURRENT SELECTED REGRESSION ROW.**

This matrix is the canonical live-appliance regression inventory. Source tests, GitHub CI
and FreeBSD package builds do not substitute for selected owner-live evidence. Detailed
historical logs remain under `docs/verification/evidence/`; current diagnosis starts from
`docs/PROJECT_STATE.md`, the current release/patch, current PR/live comments and latest
dated evidence before older records are used.

Only FreeBSD 15 amd64 packages are valid.

==================================================
TEST / RELEASE RECORD
==================================================

- Tester: repository owner
- Latest completed live test date: `2026-08-15`
- OPNsense / package architecture: FreeBSD 15 amd64
- Current published release package: `os-zapret2-restyle-0.4.1_1.pkg`
- Current published release tag: `v0.4.1`
- Latest owner-tested runtime package: `os-zapret2-restyle-0.4.1_13.pkg`
- Current testing tag: `v0.4.1_13`
- `_13` source/testing-tag target: `45ce19f8e4b37df31ea97af8b8d7900a866f81f5`
- `_13` testing-package digest: `sha256:7a2f864aa14ba2170ca378954ab5421092b76aca79b7b1765b976de2f024797b`
- Normal Stage-60 production model: `C-warm-bucket-source-port-dispatch`
- Automatic production Model B/A fallback: disabled from `_13`
- Model B/A: explicit reference/benchmark/test tooling only
- Candidate width: at most 3, not CPU-count gated
- Pinned endpoints inside one candidate: sequential

Current authority:

- `docs/START_HERE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/ROADMAP.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`.

==================================================
`v0.4.1_13` MODEL-C-ONLY OWNER-LIVE GATE — PASS
==================================================

The owner installed `os-zapret2-restyle-0.4.1_13` and supplied retained telemetry for three
normal Standard Strategy Lab jobs.

### telegram.org — `job.6RhNa1`

- outcome `NO_CANDIDATE`;
- direct TLS baseline inaccessible;
- Model C Stage 60 completed `16/16` candidates;
- zero shortlist entries;
- `stopped_reason=graph_exhausted`;
- Stage 60 `37186 ms`;
- persisted `model_c_only=true` and `.fallbacks=[]`;
- Stage-90 semantic restoration verified `RUNNING -> RUNNING`;
- strategy unchanged and temporary runtime clean.

### rutracker.org — `job.PEEjoY`

- outcome `SUCCESS`;
- direct TLS baseline inaccessible;
- Model C Stage 60 completed `16/16` candidates;
- `stopped_reason=graph_exhausted`;
- stable shortlist: `03-seqovl`, `seqovl-host`, `seqovl-midsld`;
- Stage 60 `26191 ms`;
- persisted `model_c_only=true` and `.fallbacks=[]`;
- Stage-90 semantic restoration verified `RUNNING -> RUNNING`;
- strategy unchanged and temporary runtime clean.

### www.youtube.com — `job.7Kz5ro`

- outcome `SUCCESS`;
- direct TLS baseline inaccessible in the measured environment;
- Model C Stage 60 stopped after `7/16` candidates;
- `stopped_reason=enough_candidates`;
- stable shortlist count `3`: `multidisorder-midsld`, `seqovl-midsld`, `golden-owner-multisplit-fake-tls-7`;
- Stage 60 `7173 ms`;
- persisted `model_c_only=true` and `.fallbacks=[]`;
- Stage-90 semantic restoration verified `RUNNING -> RUNNING`;
- strategy unchanged and temporary runtime clean.

These three jobs jointly prove the selected `_13` normal-production paths for exhaustive
no-candidate, exhaustive success, and early success without automatic Model B/A replay.

Durable evidence:
`docs/verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`.

==================================================
RETAINED ACCEPTED RUNTIME BASELINES
==================================================

### `_26` adaptive-budget production-wiring basis — Extended telegram.org `job.xhdgCU`

- Model C `16/16`, zero winners, `graph_exhausted`;
- `.parallel.fallbacks=[]`;
- Stage 60 `34209 ms`;
- Stage 80 PASS with unsupported optional protocols skipped;
- Stage 90 `6924 ms`, PASS;
- total job `114644 ms`;
- post-job normal Zapret2 RUNNING and no `19128-19130` residue.

Durable evidence:
`docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`.

### `_25` source-port corrective — Extended telegram.org `job.5yGde5`

- Model C 16/16, zero winners, `graph_exhausted`;
- `.parallel.fallbacks=[]`;
- Stage 60 `34198 ms`; total `114759 ms`;
- lease policy `preferred-free-else-alternate` / `foreign_port_action=skip-only`;
- fallback obtains a fresh lease rather than inheriting a failed concrete allocation;
- clean Stage-90 restoration and no `19128-19130` residue.

Durable evidence:
`docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`.

### `_23` Model-C working path — Extended rutracker.org `job.FaLtIk`

- outcome `SUCCESS`;
- Model C 16/16, `graph_exhausted`;
- winners `seqovl-host` and `seqovl-midsld`;
- multi-candidate batches used `physical_worker_count=1` with exact source-port selectors;
- no fallback; Stage 70/80/85 and semantic Stage-90 restoration succeeded.

The same `_23` cycle exposed `job.G0wC5l` shared-port collision amplification at `42004`;
that defect is closed by `_25` and is retained as historical evidence rather than current
behavior.

### `_22` accepted Model-B reference

Standard `telegram.org`, `job.KpLHgb`:

- `NO_CANDIDATE`, 16/16, zero winners, `graph_exhausted`;
- widths `3,3,3,3,3,1`, overlap 3 in width-three batches;
- no fallback; Stage 60 `34227 ms`; total `89039 ms`; clean restoration.

Standard `rutracker.org`, `job.GK0X66`:

- `SUCCESS`, 16/16;
- winners `seqovl-host`, `seqovl-midsld`;
- Stage 60 `28151 ms`; total `81272 ms`;
- Stage 70/85 and restoration successful.

==================================================
RETAINED PROGRESSION
==================================================

- `_28` removed the Stage-50 family reachability hard gate.
- `_29` added immutable CandidateSpec/ResourceInventory ownership.
- `_30` added the native Zapret2 DAG/resource/range contract.
- `_31` added adaptive neighbor ordering, fixed endpoint epoch and timing telemetry.
- `_32` closed measured parent-budget/late-stage containment.
- `_33` completed discovery/stability/finalist validation.
- Model A `_11` remains the cold correctness reference.
- Model B `_16`/`_17`/`_19`/`_21` established warm, exhaustive and controlled-parallel
  evidence before production integration on `_22`.
- `_23` integrated Model C and exposed the shared preferred-port defect.
- `_25` corrected source-port leasing and fallback ownership (`_24` intentionally skipped).
- `_26` implemented workload-derived finite parent budgets and passed owner-live
  production-wiring verification.
- `v0.4.1` promoted the accepted testing line through exact release-preparation, semantic tag,
  FreeBSD 15 package/checksum, GitHub Release and Pages/pkg repository publication.
- `_3/_4` closed BLOB startup/RSS/common-set optimization from measured negative evidence.
- `_12` closed the selected warm/readiness repeat verification.
- `_13` made normal Stage 60 Model-C-only and removed automatic Model B/A production replay.
- `_13` owner-live telemetry on 2026-08-15 accepted exhaustive no-winner, exhaustive success,
  and early-success paths with exact RUNNING restoration.

==================================================
SCENARIO MATRIX
==================================================

| # | Scenario | Required expected result | Evidence location | Result |
|---|---|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result truthful; Stage 90 restores RUNNING; no temporary residue | `2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md` | **PASS ON `_13`** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Final service remains STOPPED; restoration verified | `PENDING OWNER` | **CURRENT SELECTED REGRESSION** |
| 3 | Extended TLS 1.2 and HTTP | Available successes replay-verified; unavailable protocols explicitly skipped | `_23` Extended working path observed; dedicated formal row unselected | **PENDING REGRESSION** |
| 4 | Extended QUIC | Endpoint-bound/replay-verified when available; otherwise explicit skip | `_25/_26` exercised explicit skip; available-QUIC row remains unselected | **PENDING REGRESSION** |
| 5 | Generic UDP port and payload | Accepted only in Extended mode; complete profile and cleanup | `PENDING OWNER` | **PENDING REGRESSION** |
| 6 | Target already accessible | `TARGET_ACCESSIBLE`; search skipped; service state exact | `PENDING OWNER` | **PENDING REGRESSION** |
| 7 | No working candidate | `NO_CANDIDATE`; shortlist empty; restoration verified | `_13 job.6RhNa1`; retained `_22/_25/_26` evidence | **PASS ON `_13`** |
| 8 | User cancellation after service stop | Unfinished stages skipped; 90/99 run; original service restored | `PENDING OWNER` | **PENDING REGRESSION** |
| 9 | Hard whole-worker timeout | `TIMEOUT`; results persist; restoration verified | `_23 job.G0wC5l` observed timeout with exact restoration; dedicated formal row unselected | **PENDING REGRESSION** |
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

A selected live path fails if restoration is unverified, saved strategy changes
unexpectedly, temporary workers/rules remain, lifecycle ownership is violated, a result is
falsely classified, or an adaptive plan does not match measured capabilities.

The selected `_13` Model-C-only owner-live gate is complete. Broader pending rows remain
risk-selected regression backlog, not an all-or-nothing release checklist. The current selected
row is initial Zapret2 STOPPED; any source correction is justified only if that live row exposes
a real defect.
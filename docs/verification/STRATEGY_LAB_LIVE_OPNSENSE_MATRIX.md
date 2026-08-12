# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1 / 0.4.1_1` PUBLISHED; `_26` OWNER-LIVE PASS REMAINS THE SELECTED UNCHANGED RUNTIME BASIS; `_22` REMAINS THE ACCEPTED MODEL-B FALLBACK BASELINE.**

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
- Latest completed live test date: `2026-08-12`
- OPNsense: `26.7.1_1`; FreeBSD 15 amd64
- Current published release package: `os-zapret2-restyle-0.4.1_1.pkg`
- Current published release tag: `v0.4.1`
- Latest owner-tested runtime package: `os-zapret2-restyle-0.4.0_26.pkg`
- v0.4.1 release merge: `c53e1c1656517fa764f97a175bb82eea02dbc374`
- v0.4.1 package digest: `sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e`
- `_26` runtime commit: `8ada9cba28916fff506f19b34f5ef3de16e2008e`
- Preferred Stage-60 model: `C-warm-bucket-source-port-dispatch`
- Immediate fallback/reference: `B-warm-worker-parallel-batched`
- Final fallback: cold Model A
- Candidate width: at most 3, not CPU-count gated
- Pinned endpoints inside one candidate: sequential

Current release authority:

- `docs/releases/v0.4.1.md`;
- `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`;
- `docs/PROJECT_STATE.md`;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

Current runtime evidence authority:

- `docs/patches/v0.4.0_26.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-publication.md`;
- `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`;
- `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`;
- `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

The published `0.4.1_1` package has not yet been separately claimed as installed on the
owner appliance. The release-preparation patch changed version/release metadata and
version-aware contracts, not Strategy Lab runtime semantics, so the accepted `_26` appliance
run remains the truthful selected live basis.

==================================================
`v0.4.1` RELEASE-SELECTED LIVE BASIS — PASS ON `_26`
==================================================

### Extended telegram.org — `job.xhdgCU`

Published testing package `os-zapret2-restyle-0.4.0_26` completed the selected production-
wiring gate inherited by v0.4.1.

`adaptive-budget.json` recorded `policy=eligible-work-v1` with the actual work matrix:

- mode Extended;
- endpoint count `2`;
- IPv4 true;
- IPv6 false;
- TLS 1.3 true;
- Extended TCP true;
- QUIC/IPv4 false;
- Generic UDP false.

The independent public state matched the same capabilities: IPv4 available, IPv6
unavailable, QUIC/IPv4 closed, QUIC/IPv6 skipped and UDP request unconfigured.

Because no optional branch was eligible, all additions were zero. Effective budgets were
exactly Standard `150 s`, Extended `120 s`, search/job parent `270 s`, Stage 80 `120 s`.
`status.json` persisted the same `150/120/270/120` values with deadlines anchored to the
original job start. `timing-telemetry.json` recorded `phase=budget_adaptation`, `stage=30`,
`outcome=pass` with the same plan.

Stage 60:

- `execution_model=C-warm-bucket-source-port-dispatch`;
- 16/16 candidates completed;
- zero winners;
- `stopped_reason=graph_exhausted`;
- `.parallel.fallbacks=[]`;
- Stage 60 duration `34209 ms`.

The source-port lease wrapper remained active with
`policy=preferred-free-else-alternate` and `foreign_port_action=skip-only`.

Final result:

- Stage 80 PASS, QUIC/UDP correctly skipped by capability/input;
- Stage 90 `6924 ms`, PASS;
- total job `114644 ms`;
- Stage 99 `NO_CANDIDATE`;
- post-job `configctl zapret status` RUNNING, pid `78016` at observation time;
- post-job rules `19128-19130` absent.

Durable evidence:
`docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`.

==================================================
RETAINED ACCEPTED RUNTIME BASELINES
==================================================

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

### `_22` accepted Model-B fallback/reference

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
- v0.4.1 promoted the accepted testing line through exact release-preparation, semantic tag,
  FreeBSD 15 package/checksum, GitHub Release and Pages/pkg repository publication.

==================================================
SCENARIO MATRIX
==================================================

| # | Scenario | Required expected result | Evidence location | Result |
|---|---|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result truthful; Stage 90 restores RUNNING; no temporary residue | `2026-08-08-v0.3.3_27-scenario-01-pass.md`; later `_22/_23/_25/_26` also exercise RUNNING restoration | **PASS ON `_27` — v0.4.0 historical mandatory row** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Final service remains STOPPED; restoration verified | `PENDING OWNER` | **PENDING REGRESSION** |
| 3 | Extended TLS 1.2 and HTTP | Available successes replay-verified; unavailable protocols explicitly skipped | `_23` Extended working path observed; dedicated formal row unselected | **PENDING REGRESSION** |
| 4 | Extended QUIC | Endpoint-bound/replay-verified when available; otherwise explicit skip | `_25/_26` exercised explicit skip; available-QUIC row remains unselected | **PENDING REGRESSION** |
| 5 | Generic UDP port and payload | Accepted only in Extended mode; complete profile and cleanup | `PENDING OWNER` | **PENDING REGRESSION** |
| 6 | Target already accessible | `TARGET_ACCESSIBLE`; search skipped; service state exact | `PENDING OWNER` | **PENDING REGRESSION** |
| 7 | No working candidate | `NO_CANDIDATE`; shortlist empty; restoration verified | `_22`; `_25 job.5yGde5`; `_26 job.xhdgCU` | **PASS ON `_26` — v0.4.1 selected live basis** |
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

For v0.4.1, publication gates are complete. The unchanged runtime used accepted `_26`
owner-live evidence as its selected live basis. Broader pending rows remain risk-selected
regression backlog, not an all-or-nothing release checklist. Any later runtime-affecting
change must select and execute its own appropriate live gate.

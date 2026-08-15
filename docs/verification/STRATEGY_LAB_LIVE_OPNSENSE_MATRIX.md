# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` MODEL-C-ONLY OWNER-LIVE PASS; INITIAL-ZAPRET2-STOPPED PASS; EXTENDED TLS-1.2 / HTTP / CLOSED-QUIC GATING PASS; CONFIGURED GENERIC UDP IS THE CURRENT SELECTED REGRESSION ROW.**

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
- `docs/verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`;
- `docs/verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md`;
- `docs/verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md`.

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
INITIAL ZAPRET2 STOPPED — PASS ON `_13`
==================================================

### rutracker.org Standard — `job.5b97u9`

The permanent Zapret2 service was initially STOPPED. Strategy Lab started normally and the
GUI reported:

- status `ЗАВЕРШЕНО`;
- outcome `SUCCESS`;
- stable working strategies: `3`.

Immediate post-job observation:

```text
root@OPNsense:~ # configctl zapret status
zapret is not running
root@OPNsense:~ # pgrep -af 'dvtws2|zapret.*supervisor'
```

The process query produced no output. The observed lifecycle path is therefore:

`STOPPED -> Strategy Lab runs -> SUCCESS -> STOPPED`

with no normal `dvtws2` or Zapret2 supervisor left running.

The owner explicitly accepted this result as sufficient for the selected STOPPED regression
and stated that further telemetry, repeat execution or deeper duplicate checking of this same
scenario is unnecessary. Do not fabricate unobserved firewall/socket/hash evidence; the row is
accepted on the observable lifecycle/result evidence above.

Durable evidence:
`docs/verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md`.

==================================================
EXTENDED TLS 1.2 / HTTP / QUIC CAPABILITY GATING — PASS ON `_13`
==================================================

### rutracker.org Extended — `job.TJlWoY`

GUI-level result:

- terminal status `ЗАВЕРШЕНО`;
- terminal outcome `SUCCESS`;
- stable shortlist count `1`;
- Stage 80 `PASS`;
- Stage 80 summary `QUIC=skipped, UDP=skipped`;
- Stage 90 `PASS`, normal Zapret2 service restored and operational.

Persisted TLS-1.2 result:

- `tls12-multisplit`: executed, runtime ready/stable, firewall interception observed, endpoint probe failed by timeout, `all_pass=false`;
- `tls12-fake`: executed, runtime ready/stable, firewall interception observed, endpoint probe failed by connection reset, `all_pass=false`;
- `.extended.protocols.tls12.working=null`.

Persisted HTTP result:

- `http-multisplit`: executed, runtime ready/stable, selected endpoint IP matched the observed remote IP, firewall interception observed, endpoint probe timed out, `all_pass=false`;
- `http-multidisorder`: executed, runtime ready/stable, selected endpoint IP matched the observed remote IP, firewall interception observed, endpoint probe timed out, `all_pass=false`;
- `.extended.protocols.http.working=null`.

These are truthful negative target/environment results, not orchestration failures: the protocol
branches actually ran, their temporary runtimes reached ready/stable state, interception and
endpoint evidence was produced, Stage 80 completed PASS, and Stage 90 restored normally.

QUIC capability gating is also accepted: Stage 30 classified QUIC/IPv4 as closed, and Stage 80
explicitly reported `QUIC=skipped` rather than misclassifying a capability absence as a failed
candidate.

Generic UDP remains open. The same Stage-80 run reported `UDP=skipped` because no request payload
file was supplied; a port value alone does not constitute a configured Generic UDP request.

Durable evidence:
`docs/verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md`.

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
- `_13 job.5b97u9` accepted initial-STOPPED behavior: Strategy Lab completed successfully and
  left the permanent service STOPPED; the owner closed the row without redundant deeper replay.
- `_13 job.TJlWoY` accepted Extended TLS-1.2 and HTTP branch execution with truthful negative
  results plus explicit closed-QUIC capability gating; configured Generic UDP remains pending.

==================================================
SCENARIO MATRIX
==================================================

| # | Scenario | Required expected result | Evidence location | Result |
|---|---|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result truthful; Stage 90 restores RUNNING; no temporary residue | `2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md` | **PASS ON `_13`** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Strategy Lab starts/completes; final permanent service remains STOPPED; no normal dvtws2/supervisor remains | `2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md` | **PASS ON `_13` — OWNER ACCEPTED** |
| 3 | Extended TLS 1.2 and HTTP | Both branches execute truthfully; working result may be positive or null; lifecycle restored | `2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md` | **PASS ON `_13`** |
| 4 | Extended QUIC capability gating | Endpoint-bound/replay-verified when available; otherwise explicit capability skip | `2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md` | **PASS ON `_13` — CLOSED/EXPLICIT SKIP** |
| 5 | Generic UDP port and payload | Accepted only in Extended mode; complete configured request executes; truthful working/not_found result and cleanup | `PENDING OWNER` | **CURRENT SELECTED REGRESSION** |
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

A selected live path normally fails if restoration is unverified, saved strategy changes
unexpectedly, temporary workers/rules remain, lifecycle ownership is violated, a result is
falsely classified, or an adaptive plan does not match measured capabilities.

For scenario 2 specifically, the owner accepted the observable STOPPED lifecycle/result evidence
from `job.5b97u9` as sufficient and explicitly declined additional duplicate telemetry or repeat
checking. That row is PASS and must not be reopened merely because deeper evidence could have been
collected.

For scenario 3, a protocol branch is not required to invent a winner. `job.TJlWoY` is PASS because
TLS 1.2 and HTTP both executed real candidates with ready/stable temporary runtimes and truthful
negative endpoint results, while the overall Extended job and restoration completed normally.

The selected `_13` Model-C-only owner-live gate, initial-STOPPED row, Extended TLS-1.2/HTTP row and
closed-QUIC capability-gating row are complete. Broader pending rows remain risk-selected regression
backlog, not an all-or-nothing release checklist. The current selected row is configured Generic UDP;
any source correction is justified only if that materially different live row exposes a real defect.
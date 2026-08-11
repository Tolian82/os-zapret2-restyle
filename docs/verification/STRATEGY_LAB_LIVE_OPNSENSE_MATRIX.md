# Strategy Lab live OPNsense verification matrix

Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; `_32` TIMEOUT-CONTAINMENT LIVE PASS; `_33` ADAPTIVE-VALIDATION CHANGE-SPECIFIC LIVE PASS; MODEL A COLD REFERENCE COLLECTED ON `_11`; MODEL B `_17` REPEATED COEXISTENCE ACCEPT 5/5 (EXPERIMENT ONLY); `_18` EXHAUSTIVE NO-CANDIDATE BENCHMARK SOURCE CANDIDATE; FULL REGRESSION MATRIX OPEN**

This is the canonical live-appliance regression inventory. Source tests, CI and package
builds do not substitute for an owner-live row when that row is selected as mandatory.
Only FreeBSD 15 amd64 packages are valid.

==================================================
TEST RECORD
==================================================

- Tester: repository owner
- Latest test date/time: `2026-08-11`
- OPNsense: `26.7.1_1`; kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Required package ABI: `FreeBSD:15:amd64`
- Latest published testing candidate: `os-zapret2-restyle-0.4.0_17.pkg`
- Latest owner-installed testing candidate: `os-zapret2-restyle-0.4.0_17.pkg`
- Latest owner-tested Model B candidate: `os-zapret2-restyle-0.4.0_17.pkg` — five repeated coexistence accepts
- Current source candidate: `os-zapret2-restyle-0.4.0_18.pkg`
- Current source purpose: `_18` experiment-only batched exhaustive Model B benchmark for Standard `NO_CANDIDATE / graph_exhausted`
- Current source overlay: exact persisted Stage-60 corpus/order; at most three warm workers per batch; sequential probes; deterministic attribution; cleanup between batches; production Strategy Lab unchanged
- Revision note: `_15` remains intentionally unclaimed; no `_15` package/release or live result is recorded here
- Accepted Model A reference job: `job.TtZeaH` (`rutracker.org`)
- Historical Standard no-winner timing job: `job.tU3wiL` (`telegram.org`)
- Historical Extended no-winner timing job: `job.hsP8Ro` (`telegram.org`)
- Historical Standard winner timing job: `job.UPRDlc` (`rutracker.org`)
- WAN interface: `vtnet1`

Latest Model B reproducibility evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`.

First accepted Model B coexistence evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`.

Accepted Model A reference evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

Current source experiment contract:
`docs/patches/v0.4.0_18.md`.

==================================================
VERIFIED MEASUREMENT BOUNDARY
==================================================

`v0.4.0_9` provides the decisive cold full-search comparison:

- Standard `telegram.org` `job.tU3wiL`: `NO_CANDIDATE`, all 16 Stage-60 candidates checked, `stopped_reason=graph_exhausted`, Stage 60 about `89.247 s`, total through restoration about `144.125 s`;
- Extended `telegram.org` `job.hsP8Ro`: all 16 candidates checked, total about `169.262 s`;
- Standard `rutracker.org` `job.UPRDlc`: three winners found, Stage 60 stopped after six candidates, total about `71.023 s`.

Therefore maximum search time must be measured on a no-candidate graph-exhausted workload,
not on a successful target that triggers adaptive early stop.

Model A `_11` accepted cold distributions include total candidate median `1580 ms`,
readiness median `1046 ms`, probe median `220 ms`, stop+cleanup median `81 ms`, and RSS
median `4332 KiB`.

The first Model B coexistence accept occurred on `_16`. `_17` preserved that ready-pool
path and changed only failed-readiness handling. The owner installed `_17` and repeated the
coexistence experiment five times: 5/5 `accept`, 5/5 restoration verified, pool startup mean
`1163.6 ms`, dispatch-median mean `12.4 ms`, probe-median mean `200.3 ms`, and no dedicated
rules remained after the series.

The already-warm mean `dispatch+probe` path is about `86.5%` below Model A's cold candidate
median. Amortizing one three-worker startup over three probes gives about `600.6 ms` per
candidate, roughly `62.0%` below the cold median. These are mechanism-level estimates, not
full-search speedups.

==================================================
`_18` EXHAUSTIVE MODEL B GATE
==================================================

The benchmark reference must be a fresh completed Standard domain job with:

- `outcome=NO_CANDIDATE`;
- Stage 60 `stopped_reason=graph_exhausted`;
- zero working Stage-60 candidates;
- complete persisted candidate and schedule arrays;
- verified restoration and clean temporary runtime;
- the same current `ResourceInventory`.

The benchmark replays that exact candidate order in batches of at most three warm workers.
Before any probe each batch requires stable readiness, unique PID/divert identity and
numeric RSS. Probes remain sequential with exactly one selected temporary route. Every
candidate must remain non-PASS, interception must be attributable, workers must remain
healthy, and complete batch cleanup must finish before the next batch.

The report measures warm exhaustive search wall time, batch startup/cleanup, dispatch/probe
medians and peak batch RSS. It compares measured warm exhaustive runtime with the sum of
the same cold Stage-60 candidate durations. A full-job value is also projected as
`cold_job_total - cold_stage60_candidate_runtime + warm_exhaustive_search`; that field is
explicitly a projection, not a measured Model B full job.

Model B remains `experiment_only=true`, `parallel_probes=false`, and
`production_approved=false`.

==================================================
SCENARIO MATRIX
==================================================

| # | Scenario | Required expected result | Evidence | Result |
|---|---|---|---|---|
| 1 | Standard blocked domain, initial RUNNING | Truthful terminal result; Stage 90 restores RUNNING; no residue | `_27` owner evidence | **PASS ON `_27` — v0.4.0 mandatory row** |
| 2 | Standard blocked domain, initial STOPPED | Final service STOPPED; restoration verified | PENDING OWNER | **PENDING REGRESSION** |
| 3 | Extended TLS 1.2 and HTTP | Available branches verified; unavailable explicit | PENDING OWNER | **PENDING REGRESSION** |
| 4 | Extended QUIC | Endpoint-bound result or explicit skip | PENDING OWNER | **PENDING REGRESSION** |
| 5 | Generic UDP | Extended-only input/result/cleanup contract | PENDING OWNER | **PENDING REGRESSION** |
| 6 | Target already accessible | `TARGET_ACCESSIBLE`; search skipped | PENDING OWNER | **PENDING REGRESSION** |
| 7 | No working candidate | `NO_CANDIDATE`; empty shortlist; not internal error | `_9` has supporting owner evidence | **PENDING REGRESSION** |
| 8 | User cancellation | Partial result; restoration runs | PENDING OWNER | **PENDING REGRESSION** |
| 9 | Hard worker timeout | `TIMEOUT`; results retained; restoration verified | PENDING OWNER | **PENDING REGRESSION** |
| 10 | Controlled internal failure | `ERROR`; restoration verified | PENDING OWNER | **PENDING REGRESSION** |
| 11 | Circular start/validation/stop | Parent unchanged; private session; clean stop | PENDING OWNER | **PENDING REGRESSION** |
| 12 | Circular stale-worker recovery | Safe cleanup/restoration before retry | PENDING OWNER | **PENDING REGRESSION** |
| 13 | Settings Apply during automated job | Apply rejected; config unchanged | PENDING OWNER | **PENDING REGRESSION** |
| 14 | Settings Apply during circular/restore_failed | Unsafe apply rejected | PENDING OWNER | **PENDING REGRESSION** |
| 15 | Diagnostics reload | Active job resumes; terminal evidence retained | PENDING OWNER | **PENDING REGRESSION** |
| 16 | RU/EN presentation | Deterministic localized presentation | PENDING OWNER | **PENDING REGRESSION** |
| 17 | Retention | Protected evidence retained | PENDING OWNER | **PENDING REGRESSION** |
| 18 | Reboot after clean completion | No temporary runtime/rules return | PENDING OWNER | **PENDING REGRESSION** |

==================================================
RELEASE / NEXT GATE
==================================================

Scenario 1 remains the selected mandatory v0.4.0 row. `_28`, `_32`, and `_33` retain their
focused/change-specific owner-live passes. Rows 2–18 remain regression backlog.

`v0.4.0_17` is the latest published and owner-installed testing candidate and has five
repeated Model B coexistence accepts. `_18` is the current source candidate only for the
exhaustive no-candidate benchmark; ordinary Strategy Lab still uses Model A.

After `_18` qualifies and is published: install it, run a fresh Standard `telegram.org`
job, require truthful `NO_CANDIDATE / graph_exhausted` with complete restoration, then run
`strategy_lab_model_b_exhaustive.sh` against that exact fresh job and preserve the report
plus post-run service/IPFW residue evidence.

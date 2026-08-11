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

Detailed chronological history belongs in `docs/devlog/`, `docs/patches/`, and
`docs/verification/evidence/` rather than this current-state ledger.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current published project release/package: `v0.4.0` / `os-zapret2-restyle-0.4.0_1.pkg`
Latest published testing prerelease: `v0.4.0_17` / `os-zapret2-restyle-0.4.0_17.pkg`
Latest owner-installed testing candidate: `v0.4.0_17` / `os-zapret2-restyle-0.4.0_17.pkg`
Latest owner-tested Model B candidate: `v0.4.0_17` / five repeated coexistence accepts
Current source line: `VERSION=0.4.0`
Current package revision: `PLUGIN_REVISION=18`
Current source candidate: `os-zapret2-restyle-0.4.0_18.pkg`
Current released package: `os-zapret2-restyle-0.4.0_1.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Model B `_17` repeated owner-live coexistence ACCEPT 5/5; `_18` batched exhaustive no-candidate benchmark implemented in source and pending CI/publication**
Current source overlay: **`_18` replays an exact persisted Standard `NO_CANDIDATE / graph_exhausted` Stage-60 corpus in original order using at most three warm Model B workers per batch, sequential probes, deterministic attribution and cleanup between batches; production Strategy Lab remains cold Model A**
Revision note: **`_15` remains intentionally unclaimed by this source line because a stale concurrent `_15` branch exists; no `_15` package/release or live result is recorded here**
v0.4.0 release gate: **COMPLETE — published and installed by the owner**
`_32` timeout-containment gate: **OWNER-LIVE PASS through `v0.4.0_8`**
`_33` adaptive validation gate: **CHANGE-SPECIFIC OWNER-LIVE PASS on `v0.4.0_9`**
Model A experiment gate: **REFERENCE COLLECTED on `v0.4.0_11` / `job.TtZeaH`**
Model B coexistence gate: **first ACCEPT on `_16`; repeated ACCEPT 5/5 on `_17`; EXPERIMENT ONLY; `production_approved=false`**

Current primary Strategy Lab authorities:

- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`;
- `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`;
- `docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

Current live-gate authority:
`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Latest Model B reproducibility evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`.

First accepted Model B coexistence evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_16-model-b-live-accept.md`.

Accepted Model A reference evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

Previous Model B reject evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_13-model-b-worker-access-reject.md`.

Current source experiment contract:
`docs/patches/v0.4.0_18.md`.

Current live-release-gate decision:
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

==================================================
MIGRATION OWNERSHIP
==================================================

The automated Strategy Lab Python migration is complete. Python is authoritative for:

- automated-job state/progress/event persistence;
- stage orchestration, budgets, cancellation and finalization;
- finite request/probe execution and parsing;
- candidate runtime/readiness/interception and Stage-50 screening;
- Stage-60 expansion, Stage-70 stability and Stage-80 extended orchestration;
- final profile construction, replay, shortlist and automated circular eligibility;
- active Diagnostics status/reload presentation state.

The shared lifecycle lock, audited FreeBSD system mutations, and private circular-session
state remain deliberate shell boundaries. Experimental work must not move those boundaries
without a new architectural decision.

==================================================
ADAPTIVE SEARCH IMPLEMENTATION STATE
==================================================

Current progression relevant to the active measurement cycle:

- `_28` / `0.4.0_2` — Stage-50 family acceptance stopped being a Stage-60 hard gate;
- `_29` / `0.4.0_3` — canonical immutable `CandidateSpec` and job-scoped `ResourceInventory`;
- `_30` / `0.4.0_4` — native Zapret2 search DAG and semantic resource branches;
- `_31` / `0.4.0_5` — adaptive ordering, fixed search epoch and durable timing telemetry;
- `_32` / `0.4.0_6`–`0.4.0_8` — telemetry-driven timeout containment, owner-live passed on Standard and Extended no-winner paths;
- `_33` / `0.4.0_9` — bounded discovery, strict fail-fast 3/3 stability and finalist depth validation; winner and no-winner paths passed change-specifically;
- `0.4.0_11` — complete accepted Model A cold reference with numeric candidate RSS;
- `0.4.0_12`–`0.4.0_16` — Model B coexistence harness, preflight/access/process-query corrections and first owner-live `conclusion=accept`;
- `0.4.0_17` — failed-readiness fail-fast correction. The owner installed `_17`; five sequential repeats of the unchanged ready-pool coexistence path all returned `accept` with restoration verified;
- `0.4.0_18` — experiment-only batched exhaustive Model B benchmark for an exact no-candidate `graph_exhausted` Stage-60 corpus. It keeps the proven coexistence width at no more than three warm workers and cleans each batch before starting the next.

Warm runtime selection remains evidence-gated by the A/B/C experiment plan. No Model B/C
worker, dispatcher, warm preload or parallel candidate probing is production-approved.

==================================================
LATEST AUTOMATED SEARCH OWNER RESULTS — `v0.4.0_9`
==================================================

The most useful cold full-search comparison remains the `_9` owner evidence:

- Standard `telegram.org` `job.tU3wiL` — `NO_CANDIDATE`, all 16 Stage-60 graph candidates checked, `stopped_reason=graph_exhausted`, Stage 60 about 89.247 s, total through mandatory restoration about 144.125 s;
- Extended `telegram.org` `job.hsP8Ro` — `NO_CANDIDATE`, all 16 Stage-60 graph candidates checked, total through mandatory restoration about 169.262 s;
- Standard `rutracker.org` `job.UPRDlc` — `SUCCESS`, Stage 60 stopped after six candidates when three working candidates were found, total through mandatory restoration about 71.023 s.

This distinction is now part of the measurement contract: successful targets can stop the
adaptive search early and therefore do not represent worst-case user wait time. Exhaustive
search timing must use a no-candidate graph-exhausted workload.

Exact record:
`docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md`.

==================================================
MODEL A — ACCEPTED COLD REFERENCE
==================================================

Owner Standard `rutracker.org` job `job.TtZeaH` on `v0.4.0_11` produced 25 cold candidate
samples and `conclusion=reference_collected` with every coverage check true.

Measured cold distributions:

- total candidate median 1580 ms, p90 3411 ms, max 3463 ms;
- readiness median 1046 ms, p90 1052 ms, max 1138 ms;
- combined prepare median 140 ms, p90 160 ms, max 165 ms;
- launch median 17 ms, p90 20 ms, max 21 ms;
- probe median 220 ms, p90 2045 ms, max 2055 ms;
- stop + cleanup median 81 ms, p90 102 ms, max 109 ms;
- RSS minimum 4316 KiB, median 4332 KiB, p90 4348 KiB, maximum 4356 KiB.

Exact accepted evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

==================================================
MODEL B — COEXISTENCE AND REPRODUCIBILITY
==================================================

The first owner-live Model B coexistence accept occurred on `_16`. Three warm workers had
unique process/divert identity, aggregate RSS 12964 KiB, pool startup 1162 ms, dispatch
median 12.0 ms and probe median 200.5 ms. Result equivalence, route attribution,
coexistence, independent stop/death and semantic restoration all passed.

`v0.4.0_17` preserved that accepted ready-pool path and corrected only the separate
failed-readiness branch. The owner installed `_17` and executed the coexistence harness five
more times sequentially against `job.TtZeaH`:

- acceptance: 5/5;
- restoration verified: 5/5;
- external harness real time: 14.90–15.03 s, mean about 14.972 s;
- pool startup mean 1163.6 ms;
- dispatch-median mean 12.4 ms;
- probe-median mean 200.3 ms;
- no dedicated rules 19128–19130 remained after the series;
- the normal Zapret2 service was running after the series.

Relative to Model A's 1580 ms cold candidate median, the already-warm mean
`dispatch+probe` value of about 212.7 ms is roughly 86.5% lower. Amortizing one measured
three-worker startup over three probes gives about 600.6 ms/candidate, roughly 62.0% lower.
These are mechanism-level coexistence estimates, not full-search speedups.

Exact repeated evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_17-model-b-reproducibility.md`.

Model B remains `experiment_only=true`, `parallel_probes=false`, and
`production_approved=false`.

==================================================
MODEL B EXHAUSTIVE BENCHMARK — `_18` SOURCE CANDIDATE
==================================================

`v0.4.0_18` adds a dedicated measurement path without changing production search:

`strategy_lab_model_b_exhaustive.sh REFERENCE_JOB OUTPUT`

The reference must be a completed Standard domain job with:

- `outcome=NO_CANDIDATE`;
- Stage 60 `stopped_reason=graph_exhausted`;
- zero working Stage-60 candidates;
- a complete persisted Stage-60 candidate/schedule corpus;
- verified restoration and clean temporary runtime;
- the same current `ResourceInventory`.

The benchmark replays that exact corpus in original order in batches of at most three warm
workers. Every batch requires stable worker readiness, unique PID/divert identity, numeric
RSS, sequential single-rule route attribution, no false PASS, worker health throughout the
batch and complete cleanup before the next batch. A failed readiness or identity gate skips
all downstream probes for that batch and flows to common cleanup/restoration.

The report measures warm exhaustive search wall time, batch startup/cleanup, dispatch,
probe timing and peak batch RSS. It compares measured warm exhaustive runtime with the sum
of the same cold Stage-60 candidate-runner durations. A full-job number is also projected as
`cold_job_total - cold_stage60_candidate_runtime + warm_exhaustive_search`; that projection
is explicitly marked as not a measured Model B full job.

Exact source contract:
`docs/patches/v0.4.0_18.md`.

==================================================
CONFIRMED DEFECT / REGRESSION BACKLOG
==================================================

Closed measurement/corrective boundaries:

1. Stage-50 parent timeout on `0.4.0_5` — closed by `_6` owner evidence.
2. Stage-60 fixed parent timeout — closed by `_7` owner evidence.
3. Stage-70/80/85/90 normal-path containment — closed by `_8` owner evidence.
4. `_33` winner/no-winner adaptive validation — closed change-specifically by `_9`.
5. Model A RSS propagation — closed by `_11`.
6. Model B false clean preflight — closed by `_13`.
7. Model B post-drop hostlist traversal and FreeBSD process-query selection — closed by `_16` owner-live accept.
8. Model B failed-readiness continuation — source-corrected by `_17`; negative path remains focused regression evidence, while `_17` owner installation and 5/5 ready-pool repeats confirm no regression of the accepted path.

Other product/regression observations remain separate backlog unless selected by the
risk-based live gate, including issue #155 presentation/localization, STOPPED restoration,
cancellation/hard-timeout/internal-failure rows, extended TLS/HTTP/QUIC/configured UDP,
circular/settings/retention/reboot coverage and presentation rechecks.

See `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

==================================================
DELIVERY AND LIVE-GATE BOUNDARY
==================================================

The stable `v0.4.0 / 0.4.0_1` release cycle remains complete. `_32` and `_33` retain their
owner-live pass evidence. `v0.4.0_11` remains the accepted Model A cold reference.
`v0.4.0_17` is the latest published and owner-installed testing prerelease; its five
repeated Model B coexistence runs all accept with verified restoration. Current source
candidate `_18` only adds the exhaustive no-candidate benchmark. Model B remains explicitly
non-production and sequential. Revision `_15` remains unclaimed by this source line.

==================================================
NEXT ACTION
==================================================

1. Qualify `os-zapret2-restyle-0.4.0_18.pkg` through canonical CI and FreeBSD 15 package inspection, including the exhaustive benchmark regression and package-content contract.
2. Publish `_18` as the next testing prerelease only after the exact candidate is green and merged.
3. Install `_18` on the owner OPNsense appliance.
4. Run a fresh Standard `telegram.org` Strategy Lab job on `_18` and require a truthful `NO_CANDIDATE`, Stage-60 `graph_exhausted`, full candidate corpus and verified restoration. This fresh cold run is the contemporaneous reference for the benchmark.
5. Run the `_18` exhaustive Model B harness against that fresh job and compare measured warm exhaustive candidate-runtime wall time, RSS and attribution with the exact cold corpus. Treat the full-job speedup field as a projection only.
6. Keep production Strategy Lab on Model A until repeated exhaustive evidence and an explicit architecture decision justify any change.

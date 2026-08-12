# os-zapret2-restyle — Roadmap

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What should be done next?

Purpose:
Record ordered future work and gates without duplicating current-state or implementation history.

Updated when:
Priority, sequencing, or acceptance gates change.

Read after:
`docs/DEVLOG.md`.

Do not store here:
Detailed rationale, current live logs, or completed implementation internals.

==================================================
CURRENT PRIORITY
==================================================

Stable project publication `v0.4.1` / package `os-zapret2-restyle-0.4.1_1.pkg` is complete.
The Strategy Lab Python migration, adaptive-search redesign, Model-A measurement,
controlled-parallel Model B, preferred Model C, source-port lease correction and adaptive
workload budget are all retained as the current accepted architecture.

Current state authority:
`docs/PROJECT_STATE.md`.

Current release evidence:
`docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`.

The next engineering cycle may proceed from `main`. New work must be selected as one
independent logical change with its own risk-based verification rather than reopening the
completed v0.4.1 publication cycle.

==================================================
COMPLETED STRATEGY LAB FOUNDATION
==================================================

- [x] Initial asynchronous Strategy Lab architecture, lifecycle, network precheck,
  candidate runtime, family search, expansion, stability, extended protocols, circular
  validation and GUI.
- [x] Shell-era corrective series and semantic restoration hardening.
- [x] Python 3.13 migration of state, stage ownership, request/probe parsing, candidates,
  Stage 50/60/70/80/85 and final results.
- [x] Live Stage-40 DNS and Stage-90 restoration corrections.
- [x] Risk-based owner-live release-gate policy.

==================================================
COMPLETED ADAPTIVE-SEARCH SERIES
==================================================

Historical engineering labels `_28`-`_33` are completed work-item names and must not be
confused with package revision suffixes.

- [x] `_28` — Stage-50 family acceptance no longer gates Stage-60 reachability.
- [x] `_29` — immutable Python `CandidateSpec` and job-scoped `ResourceInventory`.
- [x] `_30` — deterministic native Zapret2 graph with golden/resource/range coverage.
- [x] `_31` — adaptive neighbor ordering, fixed endpoint epoch and timing telemetry.
- [x] `_32` — measured operation/stage/job deadline containment and late-stage correction.
- [x] `_33` — lightweight discovery, fail-fast 3/3 stability and finalist cold/deep
  validation.

==================================================
COMPLETED RUNTIME MODEL SERIES
==================================================

### Model A — cold correctness/reference

- [x] `v0.4.0_11` / `job.TtZeaH` retained as the cold correctness/performance reference.
- [x] 25 candidate samples retained with timing/RSS/restoration evidence.

### Model B — controlled warm workers

- [x] coexistence accepted on `_16`;
- [x] reproducibility repeated 5/5 on `_17`;
- [x] sequential exhaustive benchmark accepted on `_19`;
- [x] failed-probe attribution corrected and controlled parallel accepted on `_21`;
- [x] width-three Model B integrated into real Stage 60 on `_22`;
- [x] `_22` owner-live no-candidate, working-candidate, fallback and restoration evidence
  recorded.

Model B remains the accepted immediate fallback/reference. Do not repeat the old Model-B
architecture benchmark unless a later change invalidates its assumptions.

### Model C — preferred one-worker bucket

- [x] Model C became the normal Stage-60 owner on `_23`;
- [x] one physical warm bucket services up to three candidate source-port selectors;
- [x] exact candidate Lua/BLOB/range semantics and endpoint/source-port attribution are
  preserved;
- [x] working-candidate and graph-exhausted owner-live behavior were observed;
- [x] `_23` exposed shared preferred-port collision amplification rather than hiding it;
- [x] `_25` corrected ownership with `preferred-free-else-alternate` leasing;
- [x] fallback Model B obtains a fresh independent lease;
- [x] `_25` owner-live proved 16/16 Model-C completion without fallback and with clean
  restoration.

==================================================
COMPLETED ADAPTIVE BUDGET CYCLE — `_26`
==================================================

- [x] derive finite parent budgets only after Stage-30 capability measurement;
- [x] persist `policy=eligible-work-v1`, measured work matrix, explicit additions and
  effective budgets in `adaptive-budget.json`;
- [x] keep deadlines anchored to the original job start epoch;
- [x] preserve the calibrated two-endpoint floor `150/120/270/120` when optional work is
  not eligible;
- [x] add bounded source-tested headroom for extra endpoints, IPv6 baseline work,
  Extended QUIC and configured Generic UDP;
- [x] pass source, corrective-matrix, FreeBSD 15 package and testing-prerelease gates;
- [x] owner-live Extended `telegram.org`, `job.xhdgCU`, proved production wiring, Model-C
  16/16 no-fallback execution, exact measured budget persistence and clean restoration.

==================================================
COMPLETED RELEASE CYCLE — `v0.4.1 / 0.4.1_1`
==================================================

- [x] owner authorization received for v0.4.1 package revision 1;
- [x] set `VERSION=0.4.1`;
- [x] reset `PLUGIN_REVISION=1`;
- [x] synchronize README, changelog, current state, Engineering Memory, release record,
  live-release boundary and version-aware CI contracts;
- [x] complete applicable PR CI and FreeBSD 15 package build;
- [x] squash merge PR #185 with exact subject `v0.4.1_1: Prepare release v0.4.1`;
- [x] verify semantic tag `v0.4.1` at exact merge `c53e1c1656517fa764f97a175bb82eea02dbc374`;
- [x] verify Release trigger run `31596967737` SUCCESS;
- [x] verify full Release workflow run `31596979559` SUCCESS;
- [x] verify package `os-zapret2-restyle-0.4.1_1.pkg`, size `180305` bytes and digest
  `sha256:cb481b37ed5ef6b57360ecbe7f1678b75d2d8e6520beb92e3d624b1bc9eb837e`;
- [x] verify matching `SHA256SUMS`;
- [x] verify GitHub Release ID `369226460` publication;
- [x] verify Pages/pkg repository deployment `5869308071` SUCCESS;
- [x] record durable release-publication evidence and current-state closeout.

The workflow-created GitHub Release is currently marked prerelease by the existing release
workflow. No v0.4.1 publication task remains pending.

==================================================
FOLLOW-UP OPTIMIZATION BACKLOG
==================================================

Independent optimization ideas remain separate work items:

- common Lua preload versus candidate-minimal initialization;
- BLOB loading/startup/RSS tradeoffs;
- lazy bucket creation versus eager bucket creation;
- candidate width greater than three;
- endpoint-level parallelism;
- broader dispatcher/bucket grouping beyond one adaptive frontier batch.

Every item above requires its own evidence and must not silently weaken candidate
attribution, finite deadlines, cleanup or semantic restoration.

QUIC remains capability/precheck scope rather than an adaptive Stage-60 search priority.
IPv6 remains capability-gated and lower priority.

==================================================
BROADER OWNER-ASSISTED REGRESSION BACKLOG
==================================================

The canonical matrix remains `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.
Rows are selected per change/release risk; they are not all unconditional blockers.

Retained backlog includes:

- initial Zapret2 STOPPED;
- Extended TLS 1.2/HTTP and capability-gated QUIC;
- Generic UDP;
- already-accessible target;
- cancellation and controlled internal failure;
- circular start/stop/TTL/stale recovery;
- Settings Apply guards;
- active/terminal Diagnostics reload behavior;
- Russian/English presentation;
- retention and reboot/residue checks.

==================================================
RELEASE BOUNDARY
==================================================

Published semantic tag `v0.4.1` and its release assets are immutable project history. The
current package identity is `os-zapret2-restyle-0.4.1_1.pkg` for `FreeBSD:15:amd64`.

Future stable releases require their own exact VERSION authorization, risk-selected live
basis, revision reset to `1`, release-preparation PR and full Release/Pages/pkg-repository
pipeline.

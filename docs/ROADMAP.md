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

The Strategy Lab Python migration, adaptive-search redesign, Model-A measurement,
controlled-parallel Model B, preferred Model C, source-port lease correction and adaptive
workload budget are complete through the published and owner-tested `v0.4.0_26` runtime.

Current objective:
**complete the owner-authorized full `v0.4.1 / 0.4.1_1` release cycle from that accepted
runtime without changing Strategy Lab behavior in the release-preparation patch.**

Current state authority:
`docs/PROJECT_STATE.md`.

Release authority:

- `docs/releases/v0.4.1.md`;
- `docs/devlog/2026-08-12-release-v0.4.1.md`;
- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

The release cycle is complete only after the release-preparation PR passes, exact squash
merge is verified, immutable semantic tag `v0.4.1` is created at that merge, and the full
Release workflow publishes package `os-zapret2-restyle-0.4.1_1.pkg`, checksum and matching
`FreeBSD:15:amd64` Pages/pkg repository.

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

`v0.4.0_26` is therefore the accepted runtime basis being promoted to v0.4.1.

==================================================
CURRENT RELEASE CYCLE — `v0.4.1 / 0.4.1_1`
==================================================

Release preparation:

- [x] owner authorization received for v0.4.1 package revision 1;
- [x] set `VERSION=0.4.1`;
- [x] reset `PLUGIN_REVISION=1`;
- [x] synchronize README, changelog, current state, Engineering Memory, release record,
  live-release boundary and version-aware CI contracts;
- [ ] pass the complete applicable PR CI and FreeBSD 15 package build;
- [ ] squash merge with exact subject `v0.4.1_1: Prepare release v0.4.1`;
- [ ] verify immutable semantic tag `v0.4.1` at the exact merge commit;
- [ ] verify full Release workflow success;
- [ ] verify package `os-zapret2-restyle-0.4.1_1.pkg` and checksum;
- [ ] verify matching Pages/pkg repository publication;
- [ ] record durable release-publication evidence and current-state closeout.

The release-preparation change itself adds no new runtime behavior, so accepted `_26`
owner-live evidence is the risk-selected live basis. Pending unrelated matrix rows are not
converted to false PASS claims.

==================================================
FOLLOW-UP OPTIMIZATION BACKLOG
==================================================

After v0.4.1 publication, independent optimization ideas remain separate work items:

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

Stable `v0.4.0` remains immutable. The current release-preparation source line is v0.4.1
revision 1. By project protocol the stable Git tag is semantic `v0.4.1`; `_1` belongs to
the package identity `os-zapret2-restyle-0.4.1_1.pkg`.

Future stable releases require their own exact VERSION authorization, risk-selected live
basis, revision reset to `1`, release-preparation PR and full Release/Pages/pkg-repository
pipeline.

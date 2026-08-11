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

Strategy Lab Python migration, adaptive-search `_28`-`_33`, Model A measurement and the
accepted Model B warm/parallel series are complete through the owner-tested production
`v0.4.0_22` baseline.

Current objective:
**owner-live verify the already published `v0.4.0_23`, which moves normal Stage 60 to one
warm Model C bucket with deterministic source-port Lua dispatch while retaining accepted
Model B and cold Model A as fail-closed fallbacks.**

`v0.4.0_23` is published from main commit
`77b1beec471d161fb80584bf884e98970d4c75b3`. Publication evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_23-publication.md`.

Current state authority:
`docs/PROJECT_STATE.md`.

Current patch:
`docs/patches/v0.4.0_23.md`.

Current decision:
`docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md`.

Current Model-C architecture:
`docs/architecture/STRATEGY_LAB_MODEL_C.md`.

Primary adaptive-search architecture:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`.

Runtime/search verification history and methodology:
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

==================================================
COMPLETED STRATEGY LAB FOUNDATION
==================================================

- [x] Initial Strategy Lab architecture, lifecycle, network precheck, candidate runtime,
  family search, expansion, stability, extended protocols, circular validation and GUI.
- [x] Shell-era corrective series and semantic restoration hardening.
- [x] Python 3.13 migration of state, stage ownership, request/probe parsing, candidates,
  Stage 50/60/70/80/85 and final results.
- [x] Live Stage-40 DNS and Stage-90 restoration corrections.
- [x] Risk-based owner-live release-gate policy.

==================================================
COMPLETED ADAPTIVE-SEARCH SERIES
==================================================

The post-migration adaptive-search redesign is complete. Historical cycle names `_28`-`_33`
refer to engineering work items and must not be confused with current package revision
suffixes.

- [x] `_28` — Stage-50 family acceptance no longer gates Stage-60 reachability.
- [x] `_29` — immutable Python `CandidateSpec` and job-scoped `ResourceInventory`.
- [x] `_30` — deterministic native Zapret2 graph with golden/resource/range coverage.
- [x] `_31` — adaptive neighbor ordering, fixed endpoint epoch and timing telemetry.
- [x] `_32` — deadline/budget containment corrected from measured live evidence through
  package revisions `0.4.0_7` / `_8`.
- [x] `_33` — lightweight discovery, fail-fast 3/3 stability and finalist cold/deep
  validation completed through `0.4.0_9` and its owner-live evidence.

The old ROADMAP statement that `_32` was the next source cycle is superseded by the actual
merged implementation/evidence chain and must not be used for current planning.

==================================================
COMPLETED RUNTIME MODEL SERIES
==================================================

### Model A — cold reference

- [x] `v0.4.0_11` / `job.TtZeaH` accepted as the cold correctness/performance reference.
- [x] 25 candidate samples retained with timing/RSS/restoration evidence.

### Model B — multiple warm workers

- [x] coexistence accepted on `_16`;
- [x] reproducibility repeated 5/5 on `_17`;
- [x] sequential exhaustive benchmark accepted 5/5 on `_19`;
- [x] controlled parallel attribution corrected and accepted on `_21`;
- [x] width-three controlled-parallel Model B integrated into real Stage 60 on `_22`;
- [x] `_22` owner-live no-candidate, working-candidate, fallback and restoration paths
  recorded.

Model B remains an accepted fallback/reference after the `_23` Model C switch. Do not
repeat the old Model B architecture benchmark unless a later change invalidates its
assumptions.

==================================================
ACTIVE MODEL C CYCLE — `v0.4.0_23`
==================================================

Owner instruction selected a direct production-candidate switch rather than another
side-by-side experiment harness.

Source/CI/publication tasks:

- [x] make Model C the normal Stage-60 packaged owner;
- [x] render up to three currently-ready `CandidateSpec` chains into one physical warm
  `dvtws2` bucket;
- [x] preserve exact candidate payload/range/Lua/BLOB semantics inside the shared profile;
- [x] use `zapret-auto.lua` `condition` plus packaged client-source-port selector;
- [x] retain three exact source-port-qualified IPFW routes to the one bucket worker;
- [x] retain candidate parallel width <=3 and sequential endpoints inside a candidate;
- [x] fail closed Model C -> accepted Model B -> cold Model A;
- [x] keep Stage-60 budget/cancel/progress/planner semantics and Stage-70/80/85 ownership
  unchanged;
- [x] add focused Model-C regression while retaining Model-B fallback regression;
- [x] pass complete CI and FreeBSD 15 package qualification on the final PR head;
- [x] squash merge PR #177 and publish `v0.4.0_23` as a verified testing prerelease;
- [x] verify tag/release/asset and automatic deletion of `publish/v0.4.0_23`.

Publication identity:

- main/tag target: `77b1beec471d161fb80584bf884e98970d4c75b3`;
- package: `os-zapret2-restyle-0.4.0_23.pkg`;
- size: `177429` bytes;
- digest: `sha256:f735f88e62fc82e5e856123f0d7c3dc26bd550b3ec0d5ab0e72bb2277dabe364`;
- publication workflow run: `31520848437`, success.

Owner-live gate after publication:

- [ ] prove normal Stage 60 actually executes `C-warm-bucket-source-port-dispatch`;
- [ ] observe one physical worker servicing a multi-candidate batch;
- [ ] verify exact selector source-port sets and route attribution;
- [ ] Standard no-candidate / graph-exhaustion path;
- [ ] Standard working-candidate path and unchanged Stage-70/85 handoff;
- [ ] Model-C -> Model-B fallback if naturally or deliberately exercised;
- [ ] cancellation/cleanup/restoration and absence of `19128-19130` residue.

Owner-live PASS promotes `_23` from published production candidate to the current accepted
Model-C appliance baseline. A correctness/attribution/restoration failure returns the
production recommendation to accepted Model B instead of weakening the safety contract.

==================================================
FOLLOW-UP OPTIMIZATION BACKLOG
==================================================

Only after `_23` owner-live correctness is established consider independent optimizations:

- common Lua preload versus candidate-minimal initialization;
- BLOB loading/startup/RSS tradeoffs;
- lazy bucket creation versus eager bucket creation;
- width greater than three;
- endpoint-level parallelism;
- broader dispatcher/bucket grouping beyond the current one adaptive frontier batch.

Every item above is a separate experiment/patch. None is implied by `_23` acceptance.

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

The stable `v0.4.0 / 0.4.0_1` release cycle is complete. Current `_22` and `_23` work is a
forward testing-candidate line and does not rewrite the immutable semantic `v0.4.0` tag.

A later stable release requires its own exact VERSION authorization, release-selected live
gates, revision reset to `1`, release-preparation PR and full Release/Pages/pkg-repository
pipeline. Testing prerelease `v0.4.0_23` publishes only the verified FreeBSD 15 `.pkg` asset.

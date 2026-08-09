# os-zapret2-restyle — Engineering Memory Index

## Required reading order

1. repository-root `AGENTS.md`;
2. `docs/INDEX.md`;
3. `docs/PROJECT_STATE.md`;
4. specialist documents for the requested scope.

A full repository-wide reading is required for a repository-wide audit or genuine
full-context recovery. Small focused work uses the risk-based specialist reading defined
in `AGENTS.md`.

## Current Strategy Lab transition authorities

For current Strategy Lab post-migration/adaptive-search work, read these first:

- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — approved migration map and completed automated Python ownership;
- `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md` — rationale, language responsibility boundary, compatibility invariants, bug-backlog policy, and migration delivery rules;
- `docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md` — active post-migration search-policy decision; supersedes family hard gating, fixed `-d10`, and the planned QUIC strategy-search branch while keeping warm-runtime selection experimental;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — approved native-Zapret2 `CandidateSpec`/`ResourceInventory`, adaptive search graph, resource classes, validation and timeout target architecture;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` — A/B/C cold/warm runtime, dispatcher, preload, discovery-probe and timeout-telemetry verification plan;
- `docs/devlog/2026-08-08-strategy-lab-adaptive-search-design.md` — documentation-only design handoff into the planned `_28`–`_33` implementation series;
- `docs/patches/v0.4.0_2.md` — `_28` source contract: Stage-50 evidence changes Stage-60 priority but never catalog-family reachability;
- `docs/devlog/2026-08-09-v0.4.0_2-stage60-family-reachability.md` — `_28` implementation, regression, publication and owner-tested closeout;
- `docs/patches/v0.4.0_3.md` — `_29` source contract: immutable normalized `CandidateSpec`, job-scoped installed `ResourceInventory`, exact Python rendering and active shell-adapter policy cleanup;
- `docs/devlog/2026-08-09-v0.4.0_3-candidate-spec-resource-inventory.md` — `_29` implementation, resource-dependency review, regression boundary and `_30` handoff;
- `docs/patches/v0.4.0_4.md` — `_30` source contract: native Zapret2 DAG, golden/reference corpus, semantic resource branches and candidate-defined output ranges;
- `docs/devlog/2026-08-09-v0.4.0_4-native-search-graph.md` — `_30` graph implementation, exact-spec handoff, regressions and `_31` handoff;
- `docs/patches/v0.4.0_5.md` — `_31` source contract: live-evidence graph ordering, fixed search-epoch endpoint binding, two-to-three-winner defaults and durable phase timing;
- `docs/devlog/2026-08-09-v0.4.0_5-adaptive-search-planner.md` — `_31` implementation, regressions, unchanged timeout/runtime boundary and `_32` handoff;
- `docs/patches/v0.4.0_6.md` — first `_32` containment slice: Stage-50 enclosing timeout and child-cleanup envelope correction;
- `docs/verification/evidence/2026-08-09-v0.4.0_6-stage60-timeout.md` — owner evidence that `_6` closes Stage 50 and exposes the fixed Stage-60 70-second parent timeout;
- `docs/patches/v0.4.0_7.md` — second `_32` containment slice: Stage-60 candidate admission and use of remaining Standard search budget;
- `docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md` — owner Standard/Extended evidence: Stage 60 PASS 16/16, truthful `NO_CANDIDATE`, restoration PASS and late-stage timing;
- `docs/patches/v0.4.0_8.md` — current final `_32` source slice: Stage-70/80 admission plus explicit Stage-85/restoration parent bounds;
- `docs/devlog/2026-08-10-v0.4.0_8-late-stage-containment.md` — `_8` implementation and `_33` handoff boundary;
- `docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md` — `_28` focused live PASS: `accepted=[]`, all 14 Stage-60 catalog candidates attempted, Stage-90 restoration PASS and no temporary IPFW residue;
- `docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md` — active release-specific live-selection policy; preserves the full regression matrix without making every pending row an unconditional release blocker;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical owner-assisted live regression inventory; v0.4.0-selected Scenario 1 is PASS on `_27`, latest adaptive timeout evidence is `_7`, and `_8` is live-pending;
- `docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md` — v0.4.0-selected `_27` live evidence: Stages 40/50/60/70/90 PASS and truthful `NO_CANDIDATE`;
- `docs/patches/v0.3.3_27.md` — corrective Stage-40 DNS/stage deadline contract;
- `docs/devlog/2026-08-08-v0.3.3_27-stage40-dns-deadline.md` — `_26` Stage-40 diagnosis and `_27` corrective implementation record;
- `docs/verification/evidence/2026-08-08-v0.3.3_25-scenario-01-stage50-candidate-isolation.md` — `_25` live Stage-50 evidence proving a working `seqovl` candidate and aggregate candidate-isolation defect;
- `docs/patches/v0.3.3_26.md` — corrective Stage-50 candidate-local failure isolation contract;
- `docs/devlog/2026-08-08-v0.3.3_26-stage50-candidate-isolation.md` — `_25` diagnosis and `_26` corrective implementation record;
- `docs/patches/v0.3.3_25.md` — Migration Patch 8 GUI/status reconciliation and post-migration live-gate source candidate;
- `docs/devlog/2026-08-08-v0.3.3_25-gui-status-reconciliation.md` — Patch 8 source diagnosis, reconciliation and live-gate handoff;
- `docs/patches/v0.3.3_24.md` — Migration Patch 7 final-result/shortlist ownership and obsolete automated-shell retirement;
- `docs/devlog/2026-08-08-v0.3.3_24-python-final-results.md` — Patch 7 implementation, compatibility repairs, verification and Patch 8 handoff;
- `docs/patches/v0.3.3_23.md` — Migration Patch 6 expansion/stability/extended-orchestration cutover;
- `docs/devlog/2026-08-08-v0.3.3_23-python-search-extended.md` — Patch 6 implementation and Patch 7 handoff;
- `docs/patches/v0.3.3_22.md` — Migration Patch 5 candidate-runtime/family-screening cutover;
- `docs/devlog/2026-08-08-v0.3.3_22-python-candidate-family.md` — Patch 5 implementation and Patch 6 handoff;
- `docs/patches/v0.3.3_21.md` — Migration Patch 4 request/probe execution and parsing cutover;
- `docs/devlog/2026-08-08-v0.3.3_21-python-request-probes.md` — Patch 4 implementation, terminal-race correction and Patch 5 handoff;
- `docs/patches/v0.3.3_20.md` — Migration Patch 3 stage machine/budget/cancellation/finalization cutover;
- `docs/devlog/2026-08-07-v0.3.3_20-python-stage-orchestration.md` — Patch 3 ownership and lifecycle-adapter boundary;
- `docs/patches/v0.3.3_19.md` — Migration Patch 2 state/progress/event persistence cutover;
- `docs/devlog/2026-08-07-v0.3.3_19-python-state-persistence.md` — Patch 2 ownership, atomicity, parity and verification;
- `docs/patches/v0.3.3_18.md` — Migration Patch 1 packaged Python foundation;
- `docs/devlog/2026-08-07-v0.3.3_18-python-foundation.md` — Patch 1 platform evidence and implementation;
- `docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md` — final owner-observed shell-era live boundary before migration;
- `docs/PROJECT_STATE.md` — current candidate identity, confirmed defect backlog, live phase, and next action.

Migration Patches 2–7 make Python authoritative for the complete automated Strategy Lab
job path: state/persistence, stage orchestration/budgets/cancellation/finalization,
finite request/probe execution and parsing, unified candidate runtime/readiness/
interception, Stage-50 family screening, Stage-60 expansion, Stage-70 stability/replay,
Stage-80 extended TLS 1.2/HTTP/QUIC/generic-UDP orchestration, Stage-85 complete profile
construction/exact replay/unified shortlist publication, and automated-job circular
eligibility. Audited FreeBSD mutations remain behind explicit narrow shell adapters and
private circular-session state remains shell-owned by design.

Migration Patch 8 reconciled Diagnostics/API status-read presentation with persisted
Python state and reopened the owner-assisted post-migration live matrix. Corrective `_26`
fixes candidate-local Stage-50 failure isolation and `_27` widens the valid Stage-40 DNS
operation envelope without changing ownership or parser semantics.

The 2026-08-08 adaptive-search decision remains the target architecture. `_28` through
`_31` implement reachability, candidate/resource normalization, the native graph,
adaptive ordering, fixed endpoint identity, winner bounds and timing telemetry. `_32` is
implemented incrementally from owner telemetry: `_6` closes the observed Stage-50 parent
boundary, `_7` closes the observed Stage-60 fixed-parent boundary, and current `_8`
contains Stage 70/80 candidate admission plus Stage 85/restoration parent bounds. `_33`
remains the separate discovery/fail-fast-stability/finalist-deep-validation cycle.
The A/B/C warm-runtime choice remains evidence-gated by the experiment plan.

## Existing Strategy Lab product authorities

These contracts remain authoritative unless the Python migration decision explicitly
changes implementation ownership. Migration and corrective work are not permission to
weaken product behavior.

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md` — third-audit findings SL3-001…SL3-007 and source/CI traceability;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` — approved next search architecture and explicit current-vs-target boundary;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` — required evidence before warm/multi-process search optimizations become production rules;
- `docs/architecture/STRATEGY_LAB.md` — base product/stage/lifecycle contract with the 2026-08-08 search-policy supersession linked explicitly;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md` — state, cancellation, timeout, candidate ownership, restoration recovery, and verification;
- `docs/architecture/STRATEGY_LAB_ACTIVATION.md` — active Diagnostics path;
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md` — complete replay-verified profiles;
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md` — multi-protocol shortlist;
- `docs/architecture/STRATEGY_LAB_UDP_INPUT.md` — validated UDP input;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_ISOLATION.md` — immutable parent and private circular sessions;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_OWNERSHIP.md` — circular locking, ownership, and stale restoration;
- `docs/architecture/STRATEGY_LAB_SETTINGS_GUARD.md` — Settings lifecycle coordination;
- `docs/architecture/STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md` — active-job resume and idle terminal reload contract;
- `docs/architecture/STRATEGY_LAB_STRUCTURED_RESULTS.md` — structured replay evidence and safe profile copy;
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md` — persisted progress and RU/EN presentation contract;
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md` — removed obsolete interfaces and canonical module ownership;
- `docs/architecture/STRATEGY_LAB_RETENTION.md` — bounded cleanup and protected evidence;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_MATRIX.md` — discoverable corrective CI entry point;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md` — earlier hardening finding-to-patch traceability;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md` — shell-era source/CI closure; live matrix remains the product gate;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — canonical live regression inventory with release-specific mandatory-row selection;
- `docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md` — latest owner evidence and timeout-containment `_7` Stage-60 PASS;
- `docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md` — adaptive-search `_28` focused live PASS;
- `docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md` — v0.4.0 release-selected Scenario-1 live-gate PASS;
- `docs/verification/evidence/2026-08-08-v0.3.3_25-scenario-01-stage50-candidate-isolation.md` — prior post-migration Stage-50 evidence;
- `docs/verification/evidence/2026-08-07-v0.3.3_16-scenario-01-stage50-hostlist-access.md` — `_16` post-drop hostlist traversal evidence;
- `docs/verification/evidence/2026-08-07-v0.3.3_15-scenario-01-stage50-freebsd-daemon-supervisor.md` — `_15` resident FreeBSD daemon startup evidence;
- `docs/verification/evidence/2026-08-07-v0.3.3_14-scenario-01-stage50-family-runner-and-ui.md` — `_14` family-runner failure and GUI backlog evidence.

## Engineering process

`docs/WORKING_CONVENTIONS.md`, `docs/DEVELOPMENT_GUIDE.md`, `docs/DECISIONS.md`,
`docs/decisions/`, `docs/DEVLOG.md`, `docs/devlog/`, `docs/ROADMAP.md`,
`docs/REQUIREMENTS.md`, `docs/patches/`, and `docs/releases/`.

Current stable-release preparation records:
`docs/releases/v0.4.0.md` and `docs/devlog/2026-08-09-release-v0.4.0.md`.

A dated file under `docs/decisions/` may be the primary authority for a focused decision.
`docs/DECISIONS.md` remains the consolidated historical ledger; when old consolidated
wording conflicts with a later active dated decision, the later decision controls and
must state its supersession explicitly.

## GitHub delivery authority

1. current owner instruction;
2. repository-root `AGENTS.md`;
3. `docs/GITHUB_PUBLICATION.md`;
4. `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
5. `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
6. `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
7. `docs/GITHUB_WORKFLOW.md`.

Key rules:

- use the connected GitHub plugin first for every repository operation;
- use a narrow fallback only when the plugin is responding and one exact function or permission is confirmed missing;
- if the GitHub plugin is unavailable, stop GitHub work and wait for explicit owner direction;
- inventory workflows, branches, PRs, runs, artifacts, tags, releases, assets, and permissions before mutation;
- ordinary changes use one logical Ready PR and one squash merge;
- candidate publication is not a code PR;
- only one active publication run is allowed per candidate;
- read the exact job log before any response to failure;
- external infrastructure failure causes no source change and allows at most one unchanged rerun after recovery;
- no speculative runner switching, replacement branches, duplicate trackers, or unbounded retries;
- all PR/commit/squash titles use the exact package-candidate prefix;
- `main` and published tags are never force-updated.

Historical atomic/serial/Draft/full-reread wording cannot override the active authority
order above.

Never infer current state only from chat history or historical patch records. Re-read
current `main`, current GitHub objects, and the specialist authority for the operation.
Source/CI completion never substitutes for owner-provided live OPNsense evidence.

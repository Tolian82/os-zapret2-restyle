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

For any new Strategy Lab work after the `v0.3.3_17` live handoff, read these first:

- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — approved migration map, completed automated Python ownership and Patch 8 boundary;
- `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md` — rationale, language responsibility boundary, compatibility invariants, bug-backlog policy, and migration delivery rules;
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
- `docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md` — final owner-observed shell-era live boundary;
- `docs/PROJECT_STATE.md` — current candidate identity, confirmed defect backlog, migration phase, and next action.

Migration Patches 2–7 make Python authoritative for the complete automated Strategy Lab
job path: state/persistence, stage orchestration/budgets/cancellation/finalization,
finite request/probe execution and parsing, unified candidate runtime/readiness/
interception, Stage-50 family screening, Stage-60 expansion, Stage-70 stability/replay,
Stage-80 extended TLS 1.2/HTTP/QUIC/generic-UDP orchestration, Stage-85 complete profile
construction/exact replay/unified shortlist publication, and automated-job circular
eligibility. Audited FreeBSD mutations remain behind explicit narrow shell adapters and
private circular-session state remains shell-owned by design.

The next source task after `_24` qualification is Migration Patch 8: reconcile GUI/status
presentation with persisted Python state and then resume the owner-assisted post-migration
OPNsense live matrix. Do not treat `_24` source qualification as live closure.

## Existing Strategy Lab product authorities

These contracts remain authoritative unless the Python migration decision explicitly
changes implementation ownership. Migration is not permission to weaken product behavior.

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md` — third-audit findings SL3-001…SL3-007 and source/CI traceability;
- `docs/architecture/STRATEGY_LAB.md` — approved product/stage/lifecycle/search contract;
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
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md` — obsolete interfaces and canonical ownership;
- `docs/architecture/STRATEGY_LAB_RETENTION.md` — bounded cleanup and protected evidence;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_MATRIX.md` — discoverable corrective CI entry point;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md` — earlier hardening finding-to-patch traceability;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md` — shell-era source/CI closure; live matrix remains the product gate;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — live gate, paused at failed `_17` Scenario 1 until Python parity source is qualified;
- `docs/verification/evidence/2026-08-07-v0.3.3_16-scenario-01-stage50-hostlist-access.md` — `_16` post-drop hostlist traversal evidence;
- `docs/verification/evidence/2026-08-07-v0.3.3_15-scenario-01-stage50-freebsd-daemon-supervisor.md` — `_15` resident FreeBSD daemon startup evidence;
- `docs/verification/evidence/2026-08-07-v0.3.3_14-scenario-01-stage50-family-runner-and-ui.md` — `_14` family-runner failure and GUI backlog evidence.

## Engineering process

`docs/WORKING_CONVENTIONS.md`, `docs/DEVELOPMENT_GUIDE.md`, `docs/DECISIONS.md`,
`docs/decisions/`, `docs/DEVLOG.md`, `docs/devlog/`, `docs/ROADMAP.md`,
`docs/REQUIREMENTS.md`, `docs/patches/`, and `docs/releases/`.

A dated file under `docs/decisions/` may be the primary authority for a focused decision.

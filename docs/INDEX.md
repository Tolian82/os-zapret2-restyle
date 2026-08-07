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

- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md` — approved incremental migration map from large shell orchestration to Python while preserving PHP/API and lifecycle contracts;
- `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md` — rationale, language responsibility boundary, compatibility invariants, bug-backlog policy, and migration delivery rules;
- `docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md` — final owner-observed shell-era boundary: stage 40 PASS, stage 50 ERROR, stage 90 PASS, immediate GUI error/no-output and active 0% progress;
- `docs/devlog/2026-08-07-strategy-lab-python-migration-handoff.md` — completed handoff and exact next work unit;
- `docs/PROJECT_STATE.md` — current candidate identity, confirmed defect backlog, migration phase, and next action.

The next source task is Migration Patch 1 only: verify the supported OPNsense Python
runtime/dependency model and add the minimal packaged compatibility foundation without
changing Strategy Lab product behavior.

## Existing Strategy Lab product authorities

These contracts remain authoritative unless the Python migration decision explicitly
changes implementation ownership. Migration is not permission to weaken product behavior.

- `docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md` — third-audit findings SL3-001…SL3-007 and source/CI traceability;
- `docs/architecture/STRATEGY_LAB.md` — original approved product/stage/lifecycle/search contract;
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
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — live gate, now paused at failed `_17` Scenario 1 pending Python migration parity;
- `docs/verification/evidence/2026-08-07-v0.3.3_16-scenario-01-stage50-hostlist-access.md` — `_16` post-drop hostlist traversal evidence;
- `docs/verification/evidence/2026-08-07-v0.3.3_15-scenario-01-stage50-freebsd-daemon-supervisor.md` — `_15` resident FreeBSD daemon startup evidence;
- `docs/verification/evidence/2026-08-07-v0.3.3_14-scenario-01-stage50-family-runner-and-ui.md` — `_14` family-runner failure and GUI backlog evidence.

## Engineering process

`docs/WORKING_CONVENTIONS.md`, `docs/DEVELOPMENT_GUIDE.md`, `docs/DECISIONS.md`,
`docs/decisions/`, `docs/DEVLOG.md`, `docs/devlog/`, `docs/ROADMAP.md`,
`docs/REQUIREMENTS.md`, `docs/patches/`, and `docs/releases/`.

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

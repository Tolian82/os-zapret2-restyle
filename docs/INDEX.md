# os-zapret2-restyle — Engineering Memory Index

## Required reading order

1. repository-root `AGENTS.md`;
2. `docs/INDEX.md`;
3. `docs/PROJECT_STATE.md`;
4. specialist documents for the requested scope.

## Product authorities

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md` — state, cancellation, timeout, restoration, and verification;
- `docs/architecture/STRATEGY_LAB_ACTIVATION.md` — active Diagnostics path;
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md` — complete replay-verified profiles;
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md` — multi-protocol shortlist;
- `docs/architecture/STRATEGY_LAB_UDP_INPUT.md` — validated UDP input;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_ISOLATION.md` — immutable parent and private circular sessions;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_OWNERSHIP.md` — circular locking, ownership, and stale restoration;
- `docs/architecture/STRATEGY_LAB_SETTINGS_GUARD.md` — Settings lifecycle coordination;
- `docs/architecture/STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md` — latest-job pointer and reload restoration;
- `docs/architecture/STRATEGY_LAB_STRUCTURED_RESULTS.md` — structured replay evidence and safe complete-profile copy;
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md` — persisted progress and complete RU/EN presentation;
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md` — removed circular aliases and duplicate state hook;
- `docs/architecture/STRATEGY_LAB_RETENTION.md` — bounded cleanup and protected lifecycle evidence;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_MATRIX.md` — one discoverable nonrecursive Strategy Lab CI entry point;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md` — finding-to-patch traceability;
- `docs/PROJECT_STATE.md` — current verified baseline and next action.

## Engineering process

`docs/WORKING_CONVENTIONS.md`, `docs/DEVELOPMENT_GUIDE.md`, `docs/DECISIONS.md`, `docs/decisions/`, `docs/DEVLOG.md`, `docs/devlog/`, `docs/ROADMAP.md`, `docs/REQUIREMENTS.md`, `docs/patches/`, and `docs/releases/`.

## GitHub delivery authority

1. current owner instruction;
2. repository-root `AGENTS.md`;
3. `docs/GITHUB_PUBLICATION.md`;
4. `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
5. `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
6. `docs/GITHUB_WORKFLOW.md`.

Every PR title, PR-branch commit subject, and final squash subject must begin with the exact package-candidate prefix. `main` is never force-updated. Historical atomic/serial wording cannot override current GitHub governance.

Never infer current state only from chat history or historical patch records. Re-read current `main`, current PR state, and applicable active authorities.

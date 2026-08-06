# os-zapret2-restyle — Engineering Memory Index

## Required reading order

1. repository-root `AGENTS.md`;
2. `docs/INDEX.md`;
3. `docs/PROJECT_STATE.md`;
4. specialist documents for the requested scope.

A full repository-wide reading is required for a repository-wide audit or genuine
full-context recovery. Small focused work uses the risk-based specialist reading defined
in `AGENTS.md`.

## Product authorities

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md` — state, cancellation, timeout, restoration, and verification;
- `docs/architecture/STRATEGY_LAB_ACTIVATION.md` — active Diagnostics path;
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md` — complete replay-verified profiles;
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md` — multi-protocol shortlist;
- `docs/architecture/STRATEGY_LAB_UDP_INPUT.md` — validated UDP input;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_ISOLATION.md` — immutable parent and private circular sessions;
- `docs/architecture/STRATEGY_LAB_CIRCULAR_OWNERSHIP.md` — circular locking, ownership, and stale restoration;
- `docs/architecture/STRATEGY_LAB_SETTINGS_GUARD.md` — Settings lifecycle coordination;
- `docs/architecture/STRATEGY_LAB_PERSISTED_RESULT_RELOAD.md` — active-job resume and idle terminal reload;
- `docs/architecture/STRATEGY_LAB_STRUCTURED_RESULTS.md` — structured replay evidence and safe profile copy;
- `docs/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md` — persisted progress and RU/EN presentation;
- `docs/architecture/STRATEGY_LAB_OBSOLETE_SURFACES.md` — removed obsolete interfaces;
- `docs/architecture/STRATEGY_LAB_RETENTION.md` — bounded cleanup and protected evidence;
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_MATRIX.md` — discoverable corrective CI entry point;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md` — finding-to-patch traceability;
- `docs/audit/STRATEGY_LAB_HARDENING_CLOSURE.md` — source/CI closure and release-block status;
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md` — owner-assisted live gate;
- `docs/PROJECT_STATE.md` — current verified baseline and next action.

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

- inventory workflows, branches, PRs, runs, artifacts, tags, releases, assets, and
  permissions before mutation;
- ordinary changes use one logical Ready PR and one squash merge;
- candidate publication is not a code PR;
- only one active publication run is allowed per candidate;
- read the exact job log before any response to failure;
- external infrastructure failure causes no source change and allows at most one
  unchanged rerun after recovery;
- no speculative runner switching, replacement branches, duplicate trackers, or
  unbounded retries;
- all PR/commit/squash titles use the exact package-candidate prefix;
- `main` and published tags are never force-updated.

Historical atomic/serial/Draft/full-reread wording cannot override the active authority
order above.

Never infer current state only from chat history or historical patch records. Re-read
current `main`, current GitHub objects, and the specialist authority for the operation.
Source/CI completion never substitutes for owner-provided live OPNsense evidence.

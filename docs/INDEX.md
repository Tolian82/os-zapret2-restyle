# os-zapret2-restyle — Engineering Memory Index

This file answers: **Where should I look?**

It is navigation only. Permanent principles are canonical in `docs/PROJECT_PRINCIPLES.md`.

## Mandatory startup order

For every new/resumed project context:

1. repository-root `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md` — permanent project principles;
3. `docs/START_HERE.md` — current operational handoff;
4. `docs/PROJECT_STATE.md` — current state;
5. specialist documents named by the current task.

Read every selected required document completely through EOF. Historical documentation is read when
the current task/plan needs it, not automatically on every new chat.

## Core Engineering Memory map

- `docs/PROJECT_PRINCIPLES.md` — Which permanent principles must always be in context?
- `docs/START_HERE.md` — What must the next session know to resume immediately?
- `docs/PROJECT_STATE.md` — Where is the project now?
- `docs/DECISIONS.md` and `docs/decisions/` — Why was something approved/superseded?
- `docs/WORKING_CONVENTIONS.md` — How are settled principles implemented in day-to-day engineering?
- `docs/DEVELOPMENT_GUIDE.md` — How is development performed?
- `docs/ARCHITECTURE.md` and `docs/architecture/` — How is the system built?
- `docs/AUDIT.md` and `docs/audit/` — What has been audited/found and what remains?
- `docs/DEVLOG.md` and `docs/devlog/` — What was done historically?
- `docs/ROADMAP.md` — What should be done next, including long-term/deferred work?
- `docs/REQUIREMENTS.md` — What must the product do?
- `docs/patches/` — Exact patch contracts/history.
- `docs/verification/` and `docs/verification/evidence/` — Test/live evidence.
- `docs/releases/` — Stable release records.

## Current Strategy Lab / Model-C continuation

Read first:

- `docs/START_HERE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/ROADMAP.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`;
- `docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

Current packaged source is `VERSION=0.4.1`, `PLUGIN_REVISION=12`. Current next source patch is
`v0.4.1_13` Model-C-only production finalization. See `START_HERE` for exact source surfaces,
expected result and complete near/long-term plan.

### Retained accepted evidence

Use these when the current task requires historical proof; they are not mandatory startup reading
for every continuation:

- Model-A cold reference:
  `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- Model-B production baseline:
  `docs/patches/v0.4.0_22.md`,
  `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`;
- Model-C switch/source-port acceptance:
  `docs/patches/v0.4.0_23.md`, `docs/patches/v0.4.0_25.md`,
  `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`;
- adaptive budgets:
  `docs/patches/v0.4.0_26.md`,
  `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`;
- stable `v0.4.1` publication:
  `docs/releases/v0.4.1.md`,
  `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`;
- Lua initialization:
  `docs/patches/v0.4.1_2.md`,
  `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`;
- BLOB startup/common set:
  `docs/architecture/STRATEGY_LAB_BLOB_LOADING.md`, `docs/patches/v0.4.1_3.md`,
  `docs/patches/v0.4.1_4.md`,
  `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md`,
  `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md`;
- discovery probe:
  `docs/patches/v0.4.1_5.md`, `docs/patches/v0.4.1_6.md`,
  `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md`;
- lifecycle/readiness series:
  `docs/patches/v0.4.1_7.md` through `docs/patches/v0.4.1_12.md` and current `_12` live evidence.

## GitHub delivery

For any GitHub mutation read completely:

- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`;
- `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md` when package delivery is involved;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md` for evidence/failure handling;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/GITHUB_WORKFLOW.md` as the concise workflow view.

The current 2026-08-14 decision amends older broad pre-mutation inventory wording: inspect the
mandatory core state every time, then expand inventory according to the operation/risk.

## OPNsense command authority

Owner console target is root `csh`. POSIX-only syntax must explicitly enter `sh`/`/bin/sh` and
return with `exit`.

# os-zapret2-restyle — Engineering Memory Index

This file answers: **Where should I look?**

It is navigation only. Permanent principles are canonical in `docs/PROJECT_PRINCIPLES.md`.

## Mandatory startup order

For every new/resumed project context:

1. repository-root `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md`;
3. `docs/START_HERE.md`;
4. `docs/PROJECT_STATE.md`;
5. specialist documents explicitly named by the current task in `START_HERE.md`.

Read selected required documents completely through EOF. Historical material is read when the
current task/plan/evidence needs it, not automatically on every new chat.

## Core map

- `docs/PROJECT_PRINCIPLES.md` — permanent principles that must always be in context;
- `docs/START_HERE.md` — exact current handoff and next task;
- `docs/PROJECT_STATE.md` — current factual project/repository/product state;
- `docs/ROADMAP.md` — ordered near-term, long-term and deferred work;
- `docs/DECISIONS.md`, `docs/decisions/` — why something was approved/superseded;
- `docs/WORKING_CONVENTIONS.md` — how permanent principles are applied day to day;
- `docs/DEVELOPMENT_GUIDE.md` — repeatable development procedure;
- `docs/ARCHITECTURE.md`, `docs/architecture/` — current technical contracts;
- `docs/AUDIT.md`, `docs/audit/` — audit findings/evidence/remediation history;
- `docs/DEVLOG.md`, `docs/devlog/` — chronological implementation history;
- `docs/REQUIREMENTS.md` — product requirements;
- `docs/patches/` — exact patch contracts/history;
- `docs/verification/`, `docs/verification/evidence/` — test/live evidence;
- `docs/releases/` — semantic release records.

## Current Strategy Lab / Model-C continuation

Current packaged source: `VERSION=0.4.1`, `PLUGIN_REVISION=12`.
Current next source patch: `v0.4.1_13` Model-C-only production finalization.

Required current-task specialist reading is defined only by `docs/START_HERE.md`. For `_13` it is:

- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Do not infer extra mandatory reading from the historical lists below.

### Retained evidence navigation

Use only when the current task needs historical proof:

- Model A reference: `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- Model B baseline: `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`;
- Model C source-port acceptance:
  `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`;
- adaptive budgets:
  `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`;
- stable `v0.4.1`: `docs/verification/evidence/2026-08-12-v0.4.1-release-publication.md`;
- Lua: `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`;
- BLOB startup: `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md`;
- BLOB common set: `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md`;
- discovery: `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md`;
- latest readiness/lifecycle:
  `docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

## GitHub delivery reading

For every GitHub mutation, the only always-required delivery procedure after startup is:

- `docs/GITHUB_PUBLICATION.md`.

Read decision files only when the operation needs their rationale/special boundary, for example:

- package delivery: `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`;
- CI/evidence dispute: `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- documentation/preflight authority question:
  `docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`;
- title-policy dispute: `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`.

`docs/GITHUB_WORKFLOW.md` is a concise cheat sheet, not a second mandatory authority.

## OPNsense command authority

Owner console target is root `csh`. POSIX-only syntax must explicitly enter `sh`/`/bin/sh` and
return with `exit`.

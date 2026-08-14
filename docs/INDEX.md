# os-zapret2-restyle — Engineering Memory Index

This file answers: **Where should I look?**

Navigation only. Permanent principles are canonical in `docs/PROJECT_PRINCIPLES.md`.

## Mandatory startup order

1. repository-root `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md`;
3. `docs/START_HERE.md`;
4. `docs/PROJECT_STATE.md`;
5. specialist documents named by the current task in `START_HERE.md`.

`START_HERE.md` carries the mandatory short summary of the most recent completed logical work and
points to detailed patch/devlog/evidence records. Historical material is read when the task needs it,
not automatically on every new chat.

## Core map

- `docs/PROJECT_PRINCIPLES.md` — cumulative permanent canon;
- `docs/START_HERE.md` — exact current handoff and latest completed work;
- `docs/PROJECT_STATE.md` — current factual project/repository/product/environment state;
- `docs/ROADMAP.md` — current ordered near-/long-term/deferred plan;
- `docs/ARCHITECTURE.md` — current top-level technical architecture;
- `docs/architecture/` — current specialist architecture contracts;
- `docs/WORKING_CONVENTIONS.md` — day-to-day application of principles;
- `docs/GITHUB_PUBLICATION.md` — GitHub delivery procedure;
- `docs/DEVELOPMENT_GUIDE.md` — repeatable development procedure;
- `docs/DECISIONS.md`, `docs/decisions/` — decision history/rationale;
- `docs/AUDIT.md`, `docs/audit/` — audit evidence/history;
- `docs/DEVLOG.md`, `docs/devlog/` — implementation/activity chronology;
- `docs/patches/` — logical patch contracts/history;
- `docs/verification/`, `docs/verification/evidence/` — automated/live evidence;
- `docs/releases/` — semantic release records.

## Latest continuity / canon-lock record

Current docs/governance checkpoint:

- `docs/decisions/DEC-2026-08-14-owner-canon-lock-and-repository-hygiene.md`;
- `docs/patches/v0.4.1_12-owner-canon-lock-doc-audit.md`;
- `docs/devlog/2026-08-14-owner-canon-lock-doc-audit.md`.

It strengthens the prior zero-memory decision and establishes:

- one unambiguous owner fact/decision is enough; do not repeatedly reconfirm it;
- DNS is fixed/currently working unless fresh direct evidence shows a new problem;
- Model C is selected; A/B/C production model selection is closed;
- `зафиксируй` means a full review/correction of all conflicting active authority docs;
- stale tests/contracts do not override current canon;
- owner-facing project reports are understandable Russian by default;
- routine temporary branch/repository cleanup is part of normal completion;
- root architecture and base Strategy Lab architecture were corrected after stale `_31` / unselected
  A/B/C wording was found in active files.

Prior continuity decision remains historical foundation:
`docs/decisions/DEC-2026-08-14-owner-canon-and-zero-memory-recovery.md`.

## Current Strategy Lab / Model-C continuation

Current packaged source: `VERSION=0.4.1`, `PLUGIN_REVISION=12`.

**Model C is already selected.** Current `_12` B/A fallback is transition debt only.

Exact next source patch: `v0.4.1_13` — remove automatic B/A production replay and make Model C the
only normal production Stage-60 runtime.

Required current-task specialist reading:

- `docs/architecture/STRATEGY_LAB_MODEL_C.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

Current top-level/base architecture is also synchronized in:

- `docs/ARCHITECTURE.md`;
- `docs/architecture/STRATEGY_LAB.md`.

Do not let historical A/B/C experiment records override these current authorities.

## Retained evidence navigation

Use when historical proof is needed:

- Model A reference: `docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`;
- Model B reference: `docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`;
- Model C source-port acceptance: `docs/verification/evidence/2026-08-12-v0.4.0_25-source-port-live-pass.md`;
- adaptive budgets: `docs/verification/evidence/2026-08-12-v0.4.0_26-adaptive-budget-live-pass.md`;
- Lua: `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`;
- BLOB startup/RSS: `docs/verification/evidence/2026-08-12-v0.4.1_3-blob-startup-rss-live-pass.md`;
- BLOB common set: `docs/verification/evidence/2026-08-12-v0.4.1_4-blob-common-set-live-pass.md`;
- discovery: `docs/verification/evidence/2026-08-13-v0.4.1_6-discovery-corrective-live-pass.md`;
- latest readiness/lifecycle: `docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

These are evidence/history, not competing current production choices.

## GitHub delivery reading

For every GitHub mutation after startup read:

- `docs/GITHUB_PUBLICATION.md`.

Decision references when rationale is needed:

- canon lock / stale docs or tests / Russian status / cleanup:
  `docs/decisions/DEC-2026-08-14-owner-canon-lock-and-repository-hygiene.md`;
- zero-memory recovery foundation:
  `docs/decisions/DEC-2026-08-14-owner-canon-and-zero-memory-recovery.md`;
- operational handoff/preflight:
  `docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`;
- package delivery: `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`;
- CI evidence handling: `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`.

## OPNsense command authority

Owner console target is root `csh`. POSIX-only syntax must explicitly enter `sh`/`/bin/sh` and return
with `exit`.

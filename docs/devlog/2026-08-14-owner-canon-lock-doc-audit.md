# Devlog — 2026-08-14 — Canon lock and active-documentation reconciliation

Scope: docs/governance only. `VERSION=0.4.1`, `PLUGIN_REVISION=12` unchanged.

## Trigger

The owner required stronger persistence of explicit project canon and pointed out two recurring
failure modes:

- previously confirmed facts such as fixed DNS were still being spoken about as if uncertain;
- repeated explicit selection of Model C could still be challenged indirectly by old docs/tests.

The owner also required project status to be written in understandable Russian and routine repository
cleanup to be handled without offloading it back to the owner.

## Preflight

Verified through the connected GitHub plugin:

- `main`: `938d01bca0617d4dad6e4715e637ebd2a3cb11f4`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=12`;
- open PRs: none;
- prior temporary `agent/owner-canon-zero-memory-recovery` branch: absent;
- current publication procedure read before mutation.

A pinned recursive tree was obtained because this task explicitly required broad active-documentation
reconciliation.

## Full active-authority review result

Already-current files correctly locked DNS/Model C:

- `docs/START_HERE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/ROADMAP.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`.

Concrete stale active contradictions were found in:

1. `docs/ARCHITECTURE.md`: still described the `_31` cold-candidate implementation and explicitly
   stated that A/B/C were experimental models with no architecture selection yet;
2. `docs/architecture/STRATEGY_LAB.md`: still described old implementation status and said runtime
   coexistence/simultaneous probes were governed by the A/B/C experiment plan.

These were current architecture documents, not merely historical evidence, so leaving them unchanged
would violate owner canon.

## Corrective

- rewrote current root architecture around the actual Python/Model-C architecture and current accepted
  measurement decisions;
- rewrote the base Strategy Lab architecture into a current-state contract and removed obsolete model
  selection ambiguity;
- strengthened `PROJECT_PRINCIPLES` and `AGENTS` with canon-lock behavior;
- defined `зафиксируй` as a full active-document sweep, not a single-file note;
- established that stale tests/CI contracts must be corrected rather than allowed to dictate obsolete
  architecture;
- made owner-facing project status Russian and outcome-oriented by default;
- made post-task branch/repository hygiene a routine silent obligation;
- synchronized current handoff/state/roadmap and publication procedure;
- added decision and patch records for durable reasoning/history.

## Current locked facts after corrective

- DNS is fixed/currently working; reopen only on fresh direct reproducible evidence;
- Model C is selected for normal production Stage 60; A/B/C selection is closed;
- `_12` still contains B/A fallback only as implementation transition debt;
- `_13` remains the exact next packaged source change to remove that fallback.

## Immediate continuation

After docs-only merge/cleanup, proceed to `v0.4.1_13` unless a newer owner instruction changes the
priority.

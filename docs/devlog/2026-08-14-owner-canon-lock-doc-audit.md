# Devlog — 2026-08-14 — Canon lock and active-documentation reconciliation

Scope: docs/governance only. `VERSION=0.4.1`, `PLUGIN_REVISION=12` unchanged.

## Trigger

The owner required stronger persistence of explicit project canon and pointed out recurring failure
modes:

- previously confirmed facts such as fixed DNS were still being spoken about as if uncertain;
- repeated explicit selection of Model C could still be challenged indirectly by old docs/tests;
- technical GitHub/CI status was being reported in jargon rather than normal Russian;
- routine temporary-branch cleanup was being surfaced as an owner problem instead of being completed.

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

## Full active/current-looking authority review result

Already-current files correctly locked DNS/Model C, including:

- `docs/START_HERE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/ROADMAP.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_MODEL_C.md`.

Concrete stale contradictions/current-looking obsolete authority were found in three places:

1. `docs/ARCHITECTURE.md`: still described the `_31` cold-candidate implementation and explicitly
   stated that A/B/C were experimental models with no architecture selection yet;
2. `docs/architecture/STRATEGY_LAB.md`: still described old implementation status and said runtime
   coexistence/simultaneous probes were governed by the A/B/C experiment plan;
3. `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`: still marked itself current and
   explicitly described Model B as the selected production Stage-60 engine while Model C was future.

The first two were active architecture authorities. The third was a verification/experiment document
whose own `CURRENT` status made its historical Model-B conclusion look active. Leaving any of the
three unchanged would violate owner canon.

## Corrective

- rewrote current root architecture around the actual Python/Model-C architecture and current accepted
  measurement decisions;
- restored/preserved the useful complete Strategy Lab lifecycle/stage/interface/probe/report contracts
  while removing obsolete model-selection ambiguity from the base Strategy Lab architecture;
- converted the old adaptive-search A/B/C experiment plan into an explicit
  **HISTORICAL / COMPLETED** experiment/evidence index; the full pre-archive text remains available at
  the same path in commit `938d01bca0617d4dad6e4715e637ebd2a3cb11f4`;
- strengthened `PROJECT_PRINCIPLES` and `AGENTS` with canon-lock behavior;
- defined `зафиксируй` as a full active-document sweep, not a single-file note;
- established that stale tests/CI contracts must be corrected rather than allowed to dictate obsolete
  architecture;
- made owner-facing project status Russian and outcome-oriented by default;
- made post-task branch/repository hygiene a routine silent obligation;
- preserved the full useful development/publication procedures while adding the new rules;
- synchronized current handoff/state/roadmap/index and decision/patch records.

## Current locked facts after corrective

- DNS is fixed/currently working; reopen only on fresh direct reproducible evidence;
- Model C is selected for normal production Stage 60; A/B/C selection is closed;
- historical Model-B measurements remain evidence/reference, not current production authority;
- `_12` still contains B/A fallback only as implementation transition debt;
- `_13` remains the exact next packaged source change to remove that fallback.

## Immediate continuation

After docs-only merge/cleanup, proceed to `v0.4.1_13` unless a newer owner instruction changes the
priority.

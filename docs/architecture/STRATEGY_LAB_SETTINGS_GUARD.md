# Strategy Lab Settings Apply guard

## Purpose

The Settings page must not persist a new Traffic Strategy, target list, or service
configuration while automated Strategy Lab or circular validation owns Zapret2 lifecycle
state.

## Backend authority

`strategy_lab_guard.sh` is the machine-readable authority. It checks, in order:

1. a nonterminal automated Strategy Lab active job;
2. an active circular session, including `restore_failed`;
3. occupancy of the shared Zapret2 lifecycle lock.

The response identifies `busy`, owner type, owner ID, state, and reason. Missing or invalid
guard output is fail-closed in the Settings API.

## Apply transaction

`SettingsController::applyAction()` checks lifecycle availability before taking the native Config lock and again after releasing that lock, immediately before dispatching the shared Apply. Model/Python validation and candidate rendering happen without a GUI-side persistent save. The original configd/FD9 transaction owns root revalidation, runtime mutation, native Config commit and same-operation rollback.

A busy/unknown guard result leaves persistent configuration unchanged. A race after the advisory checks remains protected by the original shared owner and fail-closed transaction; the GUI does not hold a second Config writer or Config lock across configd dispatch.

## Read endpoint

`SettingsController::lifecycleAction()` exposes the same structured guard result for GUI
status and future proactive button control. It does not mutate lifecycle state.

## Safety properties

- no JavaScript-only enforcement;
- no model mutation before the first guard check;
- no GUI-side save before the original root transaction;
- `restore_failed` circular sessions remain blocking;
- unknown, invalid, or unavailable guard state fails closed;
- normal Settings validation and rollback behavior remains unchanged.

## Verification

The focused test exercises idle, automated owner, circular restoration failure, and raw
lifecycle-lock occupancy, and statically verifies both API guard points and the configd
action.

## Source history

The [full original page](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_SETTINGS_GUARD.md) preserves earlier source versions, investigation notes and acceptance claims at their actual dates. [PROJECT_STATE](../PROJECT_STATE.md) owns current evidence; this page owns its bounded technical contract.

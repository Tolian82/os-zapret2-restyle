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

`SettingsController::applyAction()` checks the guard:

- before acquiring the configuration lock or changing the in-memory model;
- again under the configuration lock after normalization and validation but before save.

A busy result raises a user-visible lifecycle error and leaves persistent configuration
unchanged. The existing reconfigure path remains protected by the shared lifecycle lock;
if ownership begins after the second guard check, reconfigure fails and the existing
rollback restores the previous model and generated configuration.

## Read endpoint

`SettingsController::lifecycleAction()` exposes the same structured guard result for GUI
status and future proactive button control. It does not mutate lifecycle state.

## Safety properties

- no JavaScript-only enforcement;
- no model mutation before the first guard check;
- no save before the second guard check;
- `restore_failed` circular sessions remain blocking;
- unknown, invalid, or unavailable guard state fails closed;
- normal Settings validation and rollback behavior remains unchanged.

## Verification

The focused test exercises idle, automated owner, circular restoration failure, and raw
lifecycle-lock occupancy, and statically verifies both API guard points and the configd
action.

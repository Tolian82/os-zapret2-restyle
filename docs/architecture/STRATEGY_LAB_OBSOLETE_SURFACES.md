# Strategy Lab obsolete-surface removal

Status: **ACTIVE CONTRACT — UPDATED BY THIRD-AUDIT PATCH 4**

This document records implementation surfaces that are no longer allowed to participate in Strategy Lab control flow or state persistence.

## Removed circular aliases

Circular validation state and stop control exist only inside the validated private session:

```text
circular/sessions/<session-id>/state.json
circular/sessions/<session-id>/stop.request
```

The former global `circular/state.json` and `circular/stop` symlinks are not created or read. Active/latest pointer files select a session; they never duplicate session state.

## Explicit worker orchestration only

The supported stage flow is owned by the explicit worker stage machine and worker control modules. Transitional state-level orchestration hooks are forbidden.

Removed surfaces include:

- `strategy_lab_skip_unfinished()` from state/expansion/stability paths;
- `strategy_lab_skip_remaining()` from expansion/stability/extended/QUIC/UDP modules;
- the earlier TLS-only `strategy_lab_shortlist_build()` in `stability.sh`.

Skipping unfinished work remains explicit through `worker_skip_unfinished()` in `worker_stage_machine.sh`, called by cancellation/error/prerequisite/timeout finalization in `worker_control.sh`. Stage 80 branch order is explicit in the stage machine. Unified shortlist construction is owned only by `profile.sh`.

## No load-order behavior selection

A module may not intentionally redefine a function already defined by another module that is sourced into the same main worker process. Source order is not a dispatch mechanism.

The transitional `worker_state_serialization.sh` module was removed after its useful lock/revision persistence behavior was moved into the canonical owners:

- `state.sh` — job-state transformations and candidate/family result state;
- `lifecycle.sh` — lifecycle snapshot/restoration persistence;
- `worker_budget.sh` — budget/deadline persistence;
- `expansion.sh` — parameter-expansion result persistence;
- `stability.sh` — stability and shortlist state persistence;
- `extended.sh` — extended TCP result persistence;
- `quic.sh` — QUIC result persistence;
- `udp.sh` — UDP result persistence;
- `worker_result.sh` — circular eligibility semantics and persistence.

When these modules run inside the main worker, persistence uses `strategy_lab_state_transform()` so the per-job state lock and monotonic revision contract are preserved. Narrow direct atomic fallbacks are retained only where a module is intentionally exercised standalone by focused runner tests that do not load `state.sh`.

Circular eligibility has one canonical definition in `worker_result.sh`. It uses the TLS 1.3 circular subset (`circular_items` / `circular_count`) rather than the general multi-protocol shortlist count. Unified shortlist construction has one canonical definition in `profile.sh`.

## Verification

Two repository contracts enforce this architecture:

- `test-strategy-lab-obsolete-surfaces.sh` rejects removed aliases, hooks, the serialization override module, and duplicate shortlist/circular-eligibility owners;
- `test-strategy-lab-module-namespace.sh` parses the exact modules loaded together by the main worker and fails if the same function name is defined by more than one of them.

The unified-shortlist regression additionally proves that the general Extended shortlist may contain more protocols/items than the TLS 1.3 circular subset without changing circular eligibility.

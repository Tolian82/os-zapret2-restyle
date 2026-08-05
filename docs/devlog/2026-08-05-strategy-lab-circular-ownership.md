# 2026-08-05 — Circular ownership and stale recovery

## Scope

Implement revision 38 and complete the remaining launch-serialization and stale-owner
portion of hardening finding 11.

## Result

Circular launcher operations now use an independent lock. The session owner is identified
by both PID and process-start token. A reused PID cannot be accepted as the original
worker.

A stale nonterminal session is reconciled before another circular start. Recovery uses the
private session runtime and lifecycle snapshot, cleans temporary dvtws2 and IPFW state,
and verifies restoration of the original Zapret2 semantic state. Successful recovery
clears the active pointer; restoration failure remains visible and blocks retry.

## Verification

The mandatory focused test exercises valid ownership, PID-reuse rejection, successful
stale restoration, failed restoration, and active-pointer behavior. Full circular and
end-to-end contracts remain mandatory.

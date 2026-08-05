# 2026-08-05 — Circular session isolation

## Scope

Implement revision 37 of the Strategy Lab hardening plan.

## Result

Circular validation now treats the completed automated job as immutable input. A new
private circular session snapshots the parent status, circular shortlist, and endpoints,
then owns every mutable runtime and lifecycle artifact.

The existing API still starts circular validation with the completed parent job ID. The
backend maps that request to an internal session ID and returns both identities in state.

## Verification contract

The circular focused test checks parent checksums before and after profile construction,
ensures no parent `candidate-runtime` directory appears, verifies lifecycle evidence
survives state transitions, and exercises lifecycle-lock failure against session state.

## Remaining finding 11 work

Revision 38 will add an independent launch lock, owner identity, and stale-session cleanup
with verified restoration before another session may start.

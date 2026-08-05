# 2026-08-05 — Settings lifecycle guard

## Scope

Implement revision 39 and close hardening finding 12.

## Result

Settings Apply now queries one backend lifecycle authority before touching the model and
again immediately before save. Automated Strategy Lab jobs, circular sessions, circular
restoration failure, and any occupied Zapret lifecycle lock block the operation.

The existing reconfigure lock and rollback remain the final race defense if ownership
begins after the second check.

## Verification

The mandatory focused test covers idle, automated, circular, and lifecycle-lock states and
verifies both Settings API guard points plus the configd action.

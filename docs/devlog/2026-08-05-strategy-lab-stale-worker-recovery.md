# 2026-08-05 — Strategy Lab stale-worker reconciliation

Patch candidate: `v0.3.2_29`.

Added launcher-side reconciliation for nonterminal Strategy Lab jobs whose recorded worker is no longer the live worker for that job. Start, status, cancel, and result operations now recover a stale job while holding the launcher lock.

Recovery cleans the reserved candidate runtime and IPFW range, restores the recorded initial Zapret2 service state through the normal lifecycle transaction, writes a terminal `ERROR` or `RESTORE_FAILED` result, and removes stale PID and active-job markers.

Verification is supplied by `scripts/test-strategy-lab-stale-worker-recovery.sh` and is wired into the mandatory domain-diagnostics contract suite. Patch `_30` remains blocked until GitHub validation and the FreeBSD package build for this commit complete successfully.

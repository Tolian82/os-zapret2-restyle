# 2026-08-05 — Strategy Lab hard whole-worker deadline

Patch candidate: `v0.3.2_28`.

Added an independent parent-aware watchdog for the complete Strategy Lab worker. Standard runs are bounded by 150 seconds and extended runs by 270 seconds. Deadline expiry records a cancellation request for an active cancellable child, resolves the persisted current stage, and enters the existing TIMEOUT cleanup and Zapret2 restoration path.

The watchdog is stopped before final restoration and ignores deadline signals after finalization begins, preventing restoration from being interrupted by a late alarm.

Verification is supplied by `scripts/test-strategy-lab-hard-deadline.sh` and is wired into the mandatory domain-diagnostics contract suite. Patch `_29` remains blocked until GitHub validation and the FreeBSD package build for this commit complete successfully.

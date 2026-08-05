# 2026-08-05 — Strategy Lab preflight residue cleanup

Patch candidate: `v0.3.2_27`.

Added a mandatory preflight barrier before Strategy Lab stage execution. The worker now removes any candidate `dvtws2` runtime, reserved divert socket, and IPFW `19100–19131` residue left by an earlier abnormal run before collecting network or accessibility evidence.

The range remains exclusively reserved for Strategy Lab and is cleaned destructively without foreign-rule ownership, snapshot, or restoration logic. A cleanup failure is persisted as a terminal stage-00 error and the active-job marker is cleared.

Verification is provided by `scripts/test-strategy-lab-preflight-cleanup.sh`, which is wired into the mandatory domain-diagnostics contract suite. Patch `_28` remains blocked until GitHub validation and the FreeBSD package build for this commit complete successfully.

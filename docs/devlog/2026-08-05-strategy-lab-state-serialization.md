# 2026-08-05 — Strategy Lab state serialization

Patch candidate: `v0.3.2_30`.

Introduced one per-job transaction boundary for authoritative Strategy Lab state. Every `status.json` mutation now acquires `status.lock`, writes atomically, and increments a monotonic revision. Cancellation, worker stages, lifecycle evidence, protocol results, budgets, shortlist data, and circular eligibility no longer race through independent temporary files.

Terminal `completed` and `error` states are irreversible by later cancellation, stage, or worker updates. The first cancellation timestamp remains stable across repeated requests.

Verification is supplied by `scripts/test-strategy-lab-state-race.sh` and is wired into the mandatory domain-diagnostics contract suite. Patch `_31` remains blocked until GitHub validation and the FreeBSD package build for this commit complete successfully.

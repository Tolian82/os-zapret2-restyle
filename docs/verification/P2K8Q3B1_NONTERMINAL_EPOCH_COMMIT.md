# #1052 P2k8q3b1 — terminal common owner only after native epoch completion

**Candidate:** `v0.6.5_50`, 14 November 2026. Source-level original FD9 safety repair; not an active schema-2 generator, observed native packet, scheduled minute worker or installed owner acceptance.

## Reproducible failure and repair

In `v0.6.5_49` original `shared_apply_execute_service` wrote `committed` before calling `finish-epoch`. If original P2c PID/birth, raw/debug inode, or immutable pretraffic validation refused, Apply returned error 70 but the common journal remained terminal and trusted by a later lifecycle call. A post-Config/IPFW rollback cannot safely be inferred, and first native events must not be erased.

The repair uses **one original shared journal** and one FD9, with no fallback owner:
1. Normal release/Voice/preview continues `config-saved → committed` exactly as before.
2. An actually active schema-2 native release after Config save/readback, IPFW commit, sealed-tree and real engine/supervisor verification enters **nonterminal** `epoch-finalizing`.
3. The existing `finish-epoch` CLI demands original FreeBSD root FD9 and the new exact-operation `attest_epoch_finalizing_generation`. It verifies the **same** original P2c map/argv/seal, live PID/birth, single engine and supervisor, and exact pending journal ID; `EpochReceipts.finish_running` reattests this before/after raw/debug reads. Its cursor remains zero, preserving first events.
4. Only a successful immutable epoch allows `committed`. Failure moves to `requires-review` when the journal permits; a failed journal write leaves the owner nonterminal. Public `attest_running_generation` and the minute/ACK worker still refuse `epoch-finalizing`.

## Evidence boundaries

The updated `scripts/test-shared-apply-execute.sh` uses the genuine shell Apply executor, a stub only for native FD9 completion and fault injection, checking success, refusal and journal-transition errors. `scripts/test-shared-apply-operation.py` verifies real file-backed transitions and blocked next Apply; `scripts/test-auto-detect-owner.py` exercises physically sealed synthetic original P2c process/map fixture and refusal of the nonterminal owner by the ordinary worker. These are **source tests**, not a real installed native active observer or complete historical writer-FD/rollover/worker result. Report exact-head CI and FreeBSD package evidence separately.

**Still closed:** active original generator schema-2, 60-second cron, real original worker/ACK, old writer-FD/previous generation and lossless 512-step/4MiB rollover. The original `authorize` command remains absent deliberately; `commit_authorized=false`. No `_50.pkg` publication or owner appliance change.

[Normative plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k8q3a call path](P2K8Q3A_ORIGINAL_FD9_EPOCH_HANDOFF.md) · [original two-phase epoch](P2K8Q2_TWO_PHASE_PRETRAFFIC_EPOCH.md).

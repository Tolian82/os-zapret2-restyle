# #1052 P2k8k — guarded original-current post-commit ACK (import-only)

**Historical/supersession status (source `v0.6.5_46`):** The standalone single-intent P2k8k post-commit ACK helper and tests were deleted in `_46`, replaced by per-slot `CursorChain.acknowledge()` inside the sole original Config-held v2 chain. Historical `_41` evidence is preserved; it is not an installed worker or an active alternative. The replacement contract is [P2k8p](P2K8P_ORIGINAL_CONFIG_HELD_V2.md).


**Candidate:** `v0.6.5_41`, 14 November 2026. Neither installed native observer, cron, user OPNsense acceptance nor testing package is authorized.

## Concrete end-to-end boundary

A future same original P2a queue owner must first synchronously obtain a real completion from the existing PHP `OPNsense\\Core\\Config::lock()` → P1 → P2k2b native transaction. `acknowledge_current_checkpoint()` accepts that result only while the original queue lock remains held, the original P2c **current live** generation is freshly attested, and protected P2k2a epoch and original rotated pending device/inode/content-hash still match. It reopens the protected immutable destination plan and checkpoint; hashes and end-debug cursor must match original intent, and the **entire checkpoint** must equal the response of the native Config child. A checkpoint with `ack_authorized=false` is a durable write receipt, **not independently sufficient** to ACK.

The existing `DurableInbox.acknowledge()` retains exclusive responsibility for fresh pending-FD read, complete-last-line validation, final inode/mtime recheck, unlink and directory fsync. P2k8k supplies its callbacks only after reattesting the same P2c current owner before/after independent P2b `FDState.DRAINED` probe of the exact prior inode and rereading protected checkpoint bytes. `BUSY` / `UNKNOWN`, stale or corrupt completion, changed original owner, old inode and missing original queue lock keep the source. A later manual GUI deletion after a **completed** destination checkpoint must not be reversed just to ACK.

## Verification and unfinished gates

`scripts/test-auto-detect-post-commit-ack.py` reuses the real P2k2a/P2k2b physical-file fixture to check 11 scenarios: full checkpoint+ACK, missing/corrupt checkpoint, busy/unknown FD, changing P2c owner, false PHP response, replaced pending inode, preserved later manual removal, missing queue lock and disabled public CLI. Only current P2c/FD test observations are injected; synthetic fixtures are **not** a native running producer. A focused fast CI check is added; the same existing native VM evidence is reused for unchanged FD9/engine behavior, not claimed for this new ACK code.

**Not yet connected:** `run_original_pending_cycle()`, `auto_detect_minute.py`, sealed active schema-2 generation, old-generation writer-FD/debug recovery and installed cron. A real caller must hold the original P2a queue across the entire PHP child and this ACK; after crash-before-response the source is retained until the original Config transaction can be replayed safely. No second engine, Config parser/writer, legacy `zapret-hosts-auto.txt` import, Strategy Lab or OPNsense setup change is made.

[Specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [Plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k8j ingress](P2K8J_CONFIGD_MINUTE_INGRESS.md) · [Original Config handoff](P2K8G_NATIVE_CONFIG_FD_HANDOFF.md).

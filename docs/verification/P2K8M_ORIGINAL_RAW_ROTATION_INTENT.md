# #1052 P2k8m — original-current raw rotation to protected debug intent (dormant)

**Candidate:** `v0.6.5_43`, 14 November 2026. This is source-only. No cron, installed worker, schema-2 live observer, product package or physical owner acceptance.

## Precise transaction and refusal

The original `DurableInbox.exclusive()` queue owner holds **one open-file description** across P2a rotation or interrupted hardlink recovery, P2b original-current writer-FD inspection and P2k1/P2k2a raw/debug intent attestation. `stage_original_current_locked()` re-attests the original P2c `GenerationProof` (generation=id, exact inbox/debug paths and trailing native observer), **requires the existing immutable `EpochReceipts._epoch()`** and refuses to invent an epoch from nonempty native debug. The only source it may rotate is that same generation; an earlier or ambiguous `pending` blocks both mutation and new attribution. An existing current pending takes priority over new inbox bytes. A crash after link-before-replace can complete the same P2a rotation, but only for the original generation.

Once the pending inode is fully detached (link count one), the helper demands the original P2b `FDState.DRAINED` and a stable inode/size/mtime/content snapshot, then executes `propose_window()` against the *real* pinned empty-debug epoch and `EpochReceipts.stage()` to create a protected immutable intent. Owner generation and writer-FD are checked again after staging. A busy/unknown FD, partial tail, debug/raw mismatch, changed engine, absent epoch, second pending or second same-epoch intent **never creates a permission to ACK**. Already rotated bytes remain in pending for safe retry; new inbox content is not discarded. The old `zapret-hosts-auto.txt` has no role.

`run_native_stage_original_current_once()` binds fixed original queue and root-private receipt paths, original engine group, real P2c and P2b and FreeBSD root only. It is **not exposed as a CLI or configd/cron action**. The working owner-installed `auto_detect_minute.py` still refuses active observation and remains unscheduled; the original shared engine/FD9/IPFW, Config, Voice/WAN and Strategy Lab are untouched.

## Focused source test

`scripts/test-auto-detect-original-rotation.py` runs a **physical** P2a queue and P2k2a root-private receipt tree with actual hardlinks, replacement, root-mode constraints, native-format debug lines and immutable journal reads. It tests empty raw, committed intent without ACK, BUSY/UNKNOWN retention with retry, link-before-replace recovery, historical-generation denial before rotation, missing trusted epoch, changing owner after rotation, debug mismatch, same-intent replay, second-intent refusal, mismatched writer group, absent original queue flock and disabled public CLI. P2c and P2b current owner/FD are injected in the portable fixture — not claimed as live OPNsense proof. Exact-head fast CI and scoped native packaging remain independent.

## Unfinished authoritative gates

**Key blocker:** original FD9 still does not issue a real sealed active schema-2 generation and initialize a trusted zero-length debug epoch in the correct pretraffic lifecycle. Existing P2k2a receipts support **only one immutable intent with cursor offset zero per generation**, including after downstream ACK, so this module intentionally cannot process the next minute under the same generation. P2k8l already provides dormant current PHP Config commit→P2k8k ACK, but it is not dispatched by this module. Next: native original-FD9 generation/epoch gate, safe old generation process/FD evidence, durable multi-minute cursor succession, then genuinely safe bounded configd worker and cron. No production enablement based solely on these tests.

[Plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k8l](P2K8L_ORIGINAL_QUEUE_CONFIG_ACK.md) · [P2k2a](P2K2A_IMMUTABLE_EPOCH_INTENT.md) · [P2k2b](P2K2B_DESTINATION_CHECKPOINT.md).

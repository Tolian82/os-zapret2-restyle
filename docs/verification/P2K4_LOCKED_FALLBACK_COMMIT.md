# #1052 P2k4 — one locked P1→durable fallback transaction (inactive)

**Source candidate:** `v0.6.5_26`, no published `_26.pkg`; installed stable `0.6.5_1.pkg` unchanged. This is a source-only qualification of the **actual P2k3-to-P2k2b result path**, not production activation.

## Red path / observable behavior

Before this increment, `prepare_verified_batch()` yielded an ephemeral PSL/exclusion-aware decision and `DestinationCommit.commit()` durably wrote arbitrary caller-supplied effects in a **separate later lock window**. Thus a file edit between the two could invalidate exclusions, or a source batch with only excluded/covered domains could not advance its durable debug checkpoint because `commit(effects={})` refused. Crash recovery after a physical insertion could also cause P1 to return no *new* additions even though an old P2k2b plan still had to be finished.

## Implemented boundary

- `backend/auto_detect_destination_commit.py` now exposes `exclusive_targets()`, its existing root-owned, nofollow, nonblocking `flock` guard. Ordinary `commit()` still obtains the same lock and checks that the low-level write is called while it is held. An empty effects map is accepted to durably persist a **zero-write** cursor checkpoint after valid source intent.
- `backend/auto_detect_verified_commit.py` is the only new compose path. Under the existing real P2a queue lock, it acquires `exclusive_targets()` **before** reading any P1 GUI/Config snapshots, checks the supplied complete manual/automatic/global-exclude snapshot's `auto` bytes against the actual protected `auto-domains.txt`, and invokes the authentic P2k3 P2c/P2b/P2k1/P2k2a verifier **inside the same lock**. It compares fresh original P2c proofs and exact source receipt identity, allows only canonical P1 `auto` additions (or no-op exclusions), and calls the real P2k2b durable plan/CAS/checkpoint writer before releasing the lock.
- On replay of a partially applied P2k2b plan, the bridge rejects foreign/auto-owned-removal destinations and permits a previously planned auto addition only if it is still required by P1 **or is already physically present**. This enables crash replay after a file write but before checkpoint, without blind re-addition. If a user removed a line after a checkpoint, subsequent replays return the checkpoint without restoring it.
- `ack_authorized=false` **always**. Pending stays on disk after all file/checkpoint successes; this still **cannot** provide a P2j `committed=True` callback and must not be connected to `DurableInbox.acknowledge()`.
- `snapshot()` is an **explicit injected integration seam**, not a deployed authoritative GUI reader. The actual native GUI/Model must be made to take the same lock on GUI reads/writes and enforce form revisions before native activation; current GUI saves are **not yet coordinated**. Caller-injected snapshots / fake owner and FD are **never authority for a live service**. The CLI entry `run_native_verified_commit_worker()` always refuses.

## Bounded verification

`scripts/test-auto-detect-verified-commit.py` uses the **actual** original P2a, P2k1, P2k2a, P2k3, P1 and P2k2b modules with protected temporary files, injected owner and FD *simulations*, testing: PSL eTLD+1 write and committed cursor without acknowledgment; replay/idempotence; preserving a GUI deletion after completed checkpoint; zero-write checkpoint for global exclusion; interruption after physical write before checkpoint and recovery; GUI lock contention; stale shared file snapshot; unknown native FD; cross-HOSTLIST `!` blocking and disabled public entry. A focused local S0 with explicit fake dependencies passed file-write/replay/deletion; this is not full integrated/native evidence. Run the integration test in the existing fast affected CI after IDNA installation, not a new VM campaign. Native package build is **CI-only**; post-merge results must be recorded separately.

## What remains before any production Auto-detect

Still missing: original FD9 authorized schema-2 observer and startup ownership repair after privilege drop; qualified native process/FD proof and old-generation crash handling; an **authoritative** current Config/HOSTLIST/owned-component snapshot and shared real GUI revisioned save (P3/P4); persistent auto-owned provenance and safe relocation; completion/ack consistency; and short native once-per-minute cron→configd worker. No new live observer, `dvtws.args`, GUI, config.xml writer, IPFW, Voice, WAN, Strategy Lab or final HOSTLIST write on an installed appliance is enabled by this PR. P2 partial; P3–P5 open.

[Approved specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [ordered plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k3](P2K3_VERIFIED_PENDING_POLICY.md) · [P2k2b](P2K2B_DESTINATION_CHECKPOINT.md).

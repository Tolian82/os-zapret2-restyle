# #1052 P2k2b — dormant destination transaction and cursor checkpoint

**Historical/supersession status (source `v0.6.5_46`):** The physical CAS/checkpoint implementation remains in use as a **per-v2-slot** journal. The old single-intent `DestinationCommit.commit()/_source()` and corresponding test/CLI were removed in `_46`; all new callers use the original Config-held v2 path. The replacement contract is [P2k8p](P2K8P_ORIGINAL_CONFIG_HELD_V2.md).


**Candidate:** source `v0.6.5_24`; no published `_24.pkg`. Owner-installed stable `0.6.5_1.pkg` remains unchanged.

## Failure addressed

P2k2a has an immutable pending raw/debug intent but no destination transaction. A crash after writing one of several HOSTLISTs and before committing the debug cursor must not lose a pending event, append it twice or silently overwrite GUI changes.

Import-only `auto_detect_destination_commit.py` adds a durable **prepare → per-target apply → checkpoint** journal under the original root-only P2k2a epoch folder, which `auto_detect_epoch_receipts.py` now recognizes. A caller must hold the real P2a `DurableInbox.exclusive()` lock and must independently establish original owner, sealed generation, old-writer FD drain and a valid P1 routing/ownership decision. The installed service has no such caller: this source primitive cannot enable production collection.

- Immutable `destination/plan.json` is written before changing any target. It pins pending inode/data hash and P2k2a end cursor and stores target pathname, effects and before/after SHA256.
- Each existing target must be owner-controlled, single-link, non-symlink and bounded. A separate root-owned, nofollow, nonblocking GUI-compatible flock guards the transaction; future P3 GUI writes must acquire **the same lock**.
- Each replacement uses same-directory temporary file, inherited owner/mode, fsync, before-hash comparison, atomic replace and directory fsync. On restart a target matching the after-hash is not written again; one matching the before-hash can finish; a third hash indicates a GUI conflict and refuses without discarding pending. This refuses *uncoordinated* edits rather than pretending to merge them.
- Only after every target matches the planned after-hash does immutable `destination/checkpoint.json` record the confirmed end offset/hash. The original `epoch.json` remains immutable with initial offset zero. Checkpoint replay **never rewrites** user deletions made after completion.
- Plain auto-owned additions can be replayed idempotently. Other rows including `!/^ ` are preserved byte-for-byte in normal additive updates. Removal from shared editable `auto` destination is explicitly forbidden until real ownership is modeled. Caller-supplied effects are **not proof** of valid origins/PSL/exclusions and may never come directly from untrusted raw data.
- `ack_authorized=false` is unconditional. Pending is never deleted here. `run_native_destination_writer()` refuses. No FD9, Config, GUI, cron/configd, IPFW, runtime arguments, Voice or Strategy Lab are changed.

## Verification boundary

`scripts/test-auto-detect-destination-commit.py` covers actual P2a/P2k1/P2k2a filesystem integration, multi-target replay, failure after first write, manual deletion after checkpoint, manual edit after plan, queue/GUI locks, stale pending and symlink rejection, and closed native entry. The central fast source CI runs this test. Before PR, Python compilation and two physical-file transaction scenarios with **synthetic epoch/queue stand-ins** passed. Those stand-ins are not a substitute for the integrated test or native FreeBSD FD9/installed evidence; exact PR-head CI outcome must be checked separately. No extra native VM is appropriate for this unwired Python primitive.

## Remaining before any activation

Independent real old-generation **original sealed provenance** and FD-drain proof, P1 routing and durable auto-owned identity (including relocations), shared lock plus stale-GUI-form revision protection, original FD9 post-drop root reownership before IPFW, authorized schema-2, original native observer and once-per-minute cron/configd worker remain open. P2 is partial; P3–P5 are open. A durable file checkpoint is **not an acknowledgment**.

[Owner specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P2 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k2a](P2K2A_IMMUTABLE_EPOCH_INTENT.md).

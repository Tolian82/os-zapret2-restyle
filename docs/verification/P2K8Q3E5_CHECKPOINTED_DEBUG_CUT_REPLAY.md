# #1052 P2k8q3e5 — original already-committed destination after native debug inode replacement

**Source candidate:** `v0.6.5_64` (15 November 2026); no published package or active schema-2/cron.

## User-path failure on pre-fix _63

An actual previous P2k8n native-debug intent is fully prepared for one original raw inode; original PHP Config/P1/P2k8p writes final Auto HOSTLIST with protected GUI lock, fsyncs all physical targets and commits immutable `destination/plan.json` plus `destination/checkpoint.json`. Before the original queue can unlink that raw pending, the independent debug pathname is atomically replaced by a NEW protected inode. A GUI user may then delete the just-added auto-domain. In _63 the next original P2k8o stage/Config replay and ACK **fail** because the old debug filename no longer points to its sealed inode—despite the completed durable checkpoint. Trying to recompute the old event or apply destination effects again could undo the user's deletion.

## One existing durable transaction, not an alternative writer

1. Preserve the original `intent.json` as `evidence=native-debug`; preserve exact original `plan.json` and `checkpoint.json` with SHA-256 binding and destination paths. Do not fabricate a diagnostic cursor offset, rewrite the plan, silently convert to `raw-first`, or create a new recovery receipt.
2. The old completed checkpoint is authoritative ONLY after the original queue lock, FD9/P2c live generation attestation, same pending dev/inode/size/SHA and P2b ALL-PID FDState.DRAINED; the existing `_checkpoint` verifies original plan and checkpoint consistency and exact original destination mapping. Protected new debug pathname still must be an actual bounded regular file; its dev/inode must differ from the sealed old inode. **Tampering/truncating the same original debug inode never counts as a replacement.**
3. In original `CursorChain.prepare`, a durable checkpoint permits returning the **same original open slot** even after debug inode cut, never creating a replacement `intent` or altering saved mode. Without checkpoint, the previous _63 preplan conversion path remains the only permitted optional recovery and refuses a directory with any destination artifact.
4. In original Config-held `commit_with_original_v2_model`, check the validated existing checkpoint **under the same GUI destination lock** before asking the now-unavailable old diagnostic inode to prove the event again. Return the checkpoint read-only: do not re-run P1 effects, re-add a GUI-deleted domain, touch source lists or acquire a second Config writer. Without checkpoint, normal original native-debug prefix and current P1/canonical CAS are still mandatory.
5. In original `CursorChain.commit/acknowledge`, the saved committed checkpoint is checked with exact source/owner and current protected debug identity. Original queue physical ACK may delete the exact drained pending only after independent destination checkpoint authenticity remains sound. A crash after physical unlink but before ACK receipt is already handled by the same original v2 replay: do not insert another domain. Previous original `native-debug` debug cursor is maintained and advances only to the saved, validated prior debug-end byte offset.
6. Remaining **partial-plan-without-checkpoint** case: if one target has been changed but another failed, a later debug cut MUST retain pending and never replay that old plan against a GUI-deleted row automatically; recovery requires the separate P2k8q3e6 eligibility/CAS proof.

## Source regression matrix

- `scripts/test-auto-detect-cursor-chain.py`: checkpoint then physical protected debug inode cut → original raw ACK; fresh original chain replay after user deletes Auto Hostlist row → completed checkpoint read-only and no new recovery record; same-inode debug prefix corruption still refuses; P2b BUSY retains pending.
- `scripts/test-auto-detect-original-v2-config.py`: actual original P2k8o/P2k8p original Config/P1 checkpoint before cut, subsequent GUI deletion, replay and ACK with unchanged final Auto and known HOSTLIST; inject second-target failure to create real partial plan, cut diagnostic inode, delete previous effect in GUI, prove refused retry with retained pending.
- `scripts/test-auto-detect-original-v2-prepare.py`: original P2a pending, original P2k8o stage, original Config-related durable checkpoint, protected debug cut, original staging and same-checkpoint ACK without rewrite or GUI re-add.
- Fast red→green must execute these **same changed original-path tests** against the _63 base and _64 code in qualified CI. Do not equate source/test file presence, S0 synthetic scenario, native pkg build, or previous _61 real-IPFW packet experiment with installed owner acceptance.

## Still OPEN

P2k8q3e6: real partially applied original plan WITHOUT final checkpoint across a debug cut. Subsequent finite 4 MiB raw/debug + 512-slot history, crash/reboot/ENOSPC and all-PID historical writer FD qualification, ACTIVE original FD9 schema-2/cron, and owner-installed live HTTP/IPFW no-pause acceptance. The installed plugin remains stable `0.6.5_1.pkg`; no `_64.pkg` published. No STOP/CONT, daemon restart, IPFW detach, independent worker or second config.xml writer.

[Original pre-destination _63](P2K8Q3E4_PREPLAN_NATIVE_DEBUG_RECOVERY.md) · [Original _62 raw-first](P2K8Q3E3_ORIGINAL_RAW_FIRST_V2_FALLBACK.md) · [Original native _61 running IPFW](P2K8Q3E2_RUNNING_NONBLOCKING_DEBUG_COHORT.md).

# #1052 P2k8q3f2a — first-archive ACK-gated retirement and second original source cut

**Candidate:** `v0.6.5_67`, source only. No testing package publication, original ACTIVE schema-2 authorization or cron. This does NOT claim complete P2k8q3f2 native acceptance.

## User-visible risk and exact source

The original P2a queue and P2k8o high-water debug cut preserve the first native debug inode under `.original-debug-retained` while RUNNING `dvtws2` continues to forward IPFW-diverted traffic. Prior _66 necessarily refused a second cut. Blindly unlinking that archive would risk erasing undelivered raw discoveries, a stale generation or a still-open historical writer's data. P2k8q3f2a changes only the **actual original** `auto_detect_original_v2_prepare.py` under its already-held queue lock and original `CursorChain.tip()`; no new worker, process, signal, parser, Config writer, stop or IPFW action.

## Retirement gate (all checks mandatory)

1. Original P2k8n `tip()` must validate the complete contiguous same-generation chain, immutable original destination plan/checkpoint and ACK. It must have no open intent or slot, at least one acknowledged `raw-first` step, and the exact committed original cursor **device+inode must match the first archived debug inode**. The `raw-first` fallback does not promise debug profile attribution, only original raw discovery truth. Future second-old inode lacks this anchor, so no third unproven archive retirement.
2. The protected old debug file must have exactly one link, original root owner/mode and valid bounded content; the original cursor's SHA-256 prefix must still match, with no embedded NUL/incomplete line. The current active debug must be a different protected inode and have reached the conservative 2 MiB high water below the 4 MiB limit.
3. Original P2a locked `pending` must be empty; current protected native raw `inbox.txt` must be empty with a single link. An incomplete, uncommitted, cut-but-unacknowledged or concurrently observed raw event leaves all original bytes untouched and refuses retirement. Delayed future native raw appends remain processed through the established generation-sticky `raw-first`, not inferred from deleted debug text.
4. Original P2c owner/FD9 must remain identical. The unchanged FreeBSD P2b kernel-wide all-process FD scanner, not just the current `dvtws2` PID, must report `FDState.DRAINED` again **after** archive read and before retirement. `BUSY` or `UNKNOWN` refuses. Archive/current/raw inode+mtime+size/link identities are checked immediately before unlink.
5. Only the proven first archived name is unlinked and the original producer directory fsynced. The same existing P2a helper then creates/fsyncs an empty debug inode, hardlinks the active previous debug under the **same single retained alias**, and atomically replaces the live `debug.log`. No time window lacks the live pathname. Crash after verified old unlink but before the second cut leaves the active inode untouched; a subsequent original call can reconstruct and retry. Any crash before qualified retirement preserves the old archive.

## Regression boundaries

The existing true-original `scripts/test-auto-detect-original-v2-prepare.py` gains four physical source cases: successful first-cut→Config/ACK→second-cut→next raw/ACK; unacknowledged pending/live raw or BUSY FD refusing without loss; corrupted old archived debug refusing; and a deliberately injected post-unlink directory-fsync failure followed by safe retry. Existing first-cut source, native P2i and old-FD tests remain required. The isolated pre-PR Python AST/helper-level exercises validate syntax and basic filesystem guard behavior only; they are **not** a substitute for actual full original test execution or native all-PID evidence.

## Remaining mandatory gate

**P2k8q3f2b:** In the EXISTING disposable OPNsense 26.7 P2i real-IPFW test, prove a second same-generation **original** source cut with real completed original Config/P1 checkpoint/ACK, real FreeBSD all-PID FD DRAINED, actual delivered known HTTP during the retirement/cut and after it, unchanged original native PID/birth and preserved exact native raw events. Then qualify ENOSPC/reboot/historical process race, a true finite raw/debug high-water lifetime, and 512-step original v2 journal retirement before ACTIVE original FD9 schema-2/cron or owner-installed acceptance. The historical _66 one-cut native proof cannot be silently promoted to this later second-cut claim. No `_67.pkg` published or installed, and original stable `0.6.5_1.pkg` is unchanged.

[First original source high-water](P2K8Q3F1_ORIGINAL_ONE_DEBUG_HIGHWATER_CUT.md) · [Current handoff](../START_HERE.md) · [Canonical #1052 contract](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md).

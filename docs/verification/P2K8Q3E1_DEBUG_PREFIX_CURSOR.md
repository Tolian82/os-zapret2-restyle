# #1052 P2k8q3e1 — original debug-positive prefix cursor

**Candidate:** v0.6.5_60, 15 November 2026. This is a source-only change in the original native P2k1 reader and its existing P2a/P2k8o/P2k8n v2 call path. The installed Auto-detect collector and minute cron remain OFF.

## Reproducible pre-fix failure

When original P2a hardlink+replace has detached the first raw inode, real dvtws2 can write a second event to the NEW raw inode while the native debug file is still the SAME inode. Before this patch, `propose_window()` compared *all* debug positives from the current cursor to one pending raw file. Two positives versus one verified raw line raised `raw_and_positive_debug_not_one_to_one`, although the first event had enough evidence to be processed. Blindly advancing to the end would instead consume the next event without its pending raw.

## Correction

The existing original P2k1 reader still validates original process/generation/profile evidence, the secured native debug pathname/inode and SHA prefix, complete bounded raw/debug, host order, native positive grammar and path, then stops after the last positive **actually belonging to the current raw**. It returns an end-offset SHA over only that prefix. The following debug positive is retained for a later v2 cursor, not added to the previous batch. All existing original P2k8n cursor checkpoint/ACK and P2k8o queue ownership code is reused; no parallel coordinator or second durable writer.

## Checks and limitations

- Reader tests: first raw matches a prefix of two debug positives; the second raw consumes the next positive from the returned offset; SHA of the original prefix is exact.
- Refusal tests: missing, misordered, unauthorized-profile, wrong raw path and invalid lines remain rejected. A later forged positive cannot be silently authorized by the preceding raw.
- Original physical path: two separate P2a raw inodes, second native-format debug positive before the first original P2k8o prepare, then independent original P2k8n v2 prepared intent, target commit, physical ACK and cursor advance.
- Fast source verification is the existing CI user-path suite (`scripts/test-auto-detect-debug-window.py`, `scripts/test-auto-detect-original-v2-prepare.py`, `scripts/test-auto-detect-cursor-chain.py`). A local focused pure-Python ordered-prefix harness passed five cases; full exact-source suite and native/installed evidence remain separate.
- No production signal or IPFW action is introduced. Existing _58 SIGSTOP only occurred inside an isolated historical disposable experiment and is NOT acceptable for production.

**Still open:** native _55 measured a positive on raw:new/debug:old followed by actual debug-name replacement. The original v2 cursor is still tied to the old debug inode. This patch does NOT authorize a rollover to the new debug inode, historical writer FD, crash/reboot/ENOSPC, 4 MiB raw/debug and 512-slot rollover or an ACTIVE schema-2 observer. Preserve unacknowledged pending and fail closed until independent debug-cohort continuity is proven without traffic stalls.

[Current plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [Specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [Native _55](P2K8Q3C2_NATIVE_MIDCUT_RAW_DEBUG.md) · [Native _58](P2K8Q3D3_NATIVE_INFLIGHT_DIVERT_STOP.md).

# #1052 P2k8o — forward-only original raw to v2 prepared intent

**Candidate:** `v0.6.5_45`, 14 November 2026. Source-only qualification; not a live FD9 observer, registered configd/cron collector, owner-installed package or product acceptance.

## Replacement and DEV-050 retirement

Under [DEV-050](../PROJECT_PRINCIPLES.md), P2k8o **replaces**, not wraps, the outdated first-minute-only P2k8m original raw→P2k2a v1-intent composer. The project removes `backend/auto_detect_original_rotation.py`, `scripts/test-auto-detect-original-rotation.py` and its fast CI step in the **same change**. No dormant P2k8m CLI, wrapper or v1 fallback remains. Its earlier [historical verification record](P2K8M_ORIGINAL_RAW_ROTATION_INTENT.md) is retained only as history.

New `backend/auto_detect_original_v2_source.py` independently verifies the current authenticated original P2c generation and exact raw/debug paths. Its `detached_original_raw()` checks protected owner/permissions, stable single-link pending device/inode, exact size, nofollow FD, unchanged mtime/link count and complete newline-terminated source before any v2 intent. **No imports from P2k8m**; the new v2 code reuses the already-approved lower-level P2a queue and native P2b FD/P2k1 debug checks rather than duplicating their state ownership.

## One bounded original queue transaction

`backend/auto_detect_original_v2_prepare.py` adds `prepare_original_v2_locked()` which requires the **original** P2a `DurableInbox.exclusive()` held over preflight, optional original hardlink→replace crash recovery and v2 intent. Before changing inbox it demands authentic original P2c current proof, the genuinely existing P2k2a zero-debug epoch and validated P2k8n v2 tip, and rejects more than one pending, old-generation pending, a full chain, or a previously prepared slot with missing/wrong original pending (including crash after unlink before ACK). An exact current pending has priority over later live raw; an interrupted original hardlink is completed only under the same generation. After rotation, reattest the process; `CursorChain.prepare()` then independently demands P2b original pending writer `FDState.DRAINED`, native P2k1 one-to-one debug/raw pair and immutable per-minute v2 prepared intent.

No extra daemon/engine, second Config writer/lock or old `zapret-hosts-auto.txt` reader. The private native helper and `main()` remain unregistered; no destination write or ACK is triggered here. Original source `_44` v2 per-slot checkpoint/ACK still exists for eventual **same original PHP Config lock** integration. The earlier P2k8k/l one-intent PHP Config/ACK path is **transition debt** and must be deleted once the v2 Config-child replacement is implemented, not kept as alternate product logic. V1 on-disk state is **not migrated** on this experimental stand.

## Focused checks and acceptance boundaries

`scripts/test-auto-detect-original-v2-prepare.py` exercises 14 physical cases: empty input, exact first intent, **two** original queue→v2 prepared-intent→physical destination checkpoint→ACK loops, pending before newly added live input, same-inode hardlink recovery, busy and unknown writer FD, old-generation pending preflight, interrupted after unlink before ACK (cannot rotate later data), missing zero-debug epoch, owner changes before/after rotation, legacy-receipt refusal, mandatory lock and disabled CLI. Only P2c engine witness and P2b FD state are injected in portable tests. Existing `test-auto-detect-cursor-chain.py` covers 15 more physical v2 destination/ACK cases.

**Not yet qualified:** original real FD9 active schema-2 generation and pretraffic epoch; the original PHP Config-held P1/durable v2 checkpoint ACK child; old engine process/FD/debug recovery; v2 512-slot / bounded native debug compaction; real native running overlap, configd and 60s cron. Source CI and disposable package build never equal an owner-installed native acceptance. No `_45.pkg` publication.

[Current plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k8n](P2K8N_APPEND_ONLY_CURSOR_CHAIN.md) · [older source historical record](P2K8M_ORIGINAL_RAW_ROTATION_INTENT.md).

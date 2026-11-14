# #1052 P2k8q2 — two-phase original sealed pretraffic/debug epoch (source-only)

**Candidate:** `v0.6.5_48`, 14 November 2026. No active original-FD9 schema-2 map producer, native observer, cron, Config write, published `_48.pkg` or owner-appliance acceptance.

## Failure mode and forward-only resolution

Old `EpochReceipts.begin(proof, cursor)` demanded **empty native debug AFTER a running PID/birth existed**. The real single `dvtws2` can emit valid native debug and raw before PID is authenticated, so a late empty check drops the first event or deadlocks the collector. It is **deleted** per DEV-050, without a dormant compatibility method or old v1 receipt.

The only new root-private v2 epoch contract now has two immutable writes:

1. **Prelaunch, while original FD9 + original P2a queue flock are held:** `EpochReceipts.seal_pretraffic(queue, workspace, candidate_sha256)` requires a **verified original shared bundle seal**, actual native release `dvtws.args` and **ACTIVE** `auto-detect-generation.json`, validated by canonical P2c `_valid_map()` against original PHP candidate SHA and native observer/profile ancestry. It refuses the inert P2h preview, stale/modified argv or guessed candidate. Both native raw and debug are separately `O_NOFOLLOW`-read twice on original file descriptors; bytes must be zero, dev+ino distinct, owner/mode correct, and original P2a pending absent. Immutable `pretraffic.json` stores sealed candidate digest, raw/debug dev+ino, exact profiles, candidate and argv SHA; it is fsynced through the original root-only epoch directory. FreeBSD native invocation verifies the original held FD9 instead of taking another lock.
2. **Postlaunch, after the original credentials/owner checks:** `EpochReceipts.finish_running(proof,queue,attest)` demands the same original P2c generation (live PID/birth/executable, shared operation/argv), current original queue flock and exact original raw/debug dev+ino, then fsyncs `epoch.json` with pretraffic SHA, real process birth and **debug cursor offset zero**. Here raw/debug **MAY already contain first-packet events**; the bytes and inode are retained, never truncated or reinitialized. Concurrent/changed process, replaced inode or conflicting immutable replay fails without ACK.
3. `EpochReceipts._epoch()` and therefore P2k8n `CursorChain.tip/prepare/commit/acknowledge` require **both** matching immutable records. A seed alone is not an owner, target commit or ACK. All original P2k8n/o/p tests now use a real physically sealed shared-work release in a shared test fixture; their P2c process/P2b writer-FD witness remains injected portable input, never claimed as installed native acceptance.

## Evidence / open gate

`scripts/test-auto-detect-pretraffic-epoch.py` has 18 source-level physical tests: first native events between phases retained at offset zero, exact durable replay, nonempty raw/debug and old pending unchanged, fake SHA/forged map/inert preview/modified sealed argv refusal, changed raw/debug inode, competing PID/birth, changed seed/foreign receipt, no original lock or obsolete `begin()`, corrupt seed and an off-target FreeBSD gate refusal. The three existing current v2 test suites (P2k8n/o/p) exercise the replaced actual epoch entry path.

**Still unimplemented in the live original FD9:** create/seal an authorized schema-2 **active** release and trailing observer argv and invoke `seal_pretraffic` before the first packet; then prove genuinely active same-process `finish_running`, historical previous engine/writer-FD provenance and safe bounded 512-step/4MiB rollover. No installed active schema-2 producer exists today: this is an import-only source contract, not a passed real packet test of the new phase protocol. The installed observer `authorize` command remains absent and refuses launch, configd minute unscheduled, 60s cron not present. `commit_authorized=false`.

[Plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2k8q1 native pretraffic check](P2K8Q1_ORIGINAL_FD9_PRETRAFFIC_ZERO.md) · [P2k8n cursor](P2K8N_APPEND_ONLY_CURSOR_CHAIN.md) · [P2k8p original Config v2](P2K8P_ORIGINAL_CONFIG_HELD_V2.md).

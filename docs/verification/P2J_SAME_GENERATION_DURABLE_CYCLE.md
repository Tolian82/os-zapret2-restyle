# #1052 P2j — same-generation pending cycle, **dormant**

**Historical/supersession status (source `v0.6.5_46`):** The earlier callback-injected P2j `auto_detect_cycle.py` alternate coordinator and standalone tests were deleted in `_46` per DEV-050. The sole forward-only original v2 queue→Config→P1→ACK composer replaces it; this document remains historical evidence. The replacement contract is [P2k8p](P2K8P_ORIGINAL_CONFIG_HELD_V2.md).


**Source candidate:** `v0.6.5_21`. P2j is an integration precursor, **NOT** a running or installed minute worker. The original P2i pinned OPNsense/FreeBSD proof is [#43429359714](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43429359714); it established real P2h preview first-match/raw+debug and the upstream pre-drop chown, **not** durable destination writes or installed FD9 startup.

## Observable failure and red → green

After `os.link(inbox, pending/<id>.txt)` but before `os.replace()`, an interrupted run leaves pending and live inbox at the **same inode**. A naive `pending-first` coordinator waits for a drain that can never occur. More dangerously, after a new FD9 Apply starts another `dvtws2`, an untagged pending segment cannot safely be attributed to the new process's profile/source just because its current engine exists. A current PID, path, or native profile number alone is insufficient.

The existing P2a queue had no `rotate(generation=...)` API: attempting an actual same-generation cycle against that source raises `TypeError` before processing (**local pre-fix RED, six scenarios**). New scoped tests exercise the **actual `DurableInbox`** via the internal P2j coordinator and require strictly authenticated generation-tied pending filenames, unchanged inode in link-before-replace recovery and fail-closed retention for unknown generation, BUSY/UNKNOWN FD, unconfirmed debug, incomplete final line or failed commit. The patched portable queue/bridge passed **11 scoped local scenarios** using an S0 mirror of the existing queue plus the new bridge. The exact repository-source GitHub CI result is a **separate gate**; do not confuse portable injected owner/FD results with real FreeBSD/PID/FD acceptance.

## Implemented transition contract

`backend/auto_detect_queue.py` keeps every previous P2a caller working: `rotate()` without a generation still has its original behavior. An optional strictly validated 32-lowercase-hex `generation` creates `pending/<generation>-<random128bit>.txt`. A link-before-replace recovery from a different generation refuses replacement, rather than turning a stale inode into a new owned event.

`backend/auto_detect_cycle.py` exports only an internal `_cycle_once` and an explicitly **refusing** `run_native_cycle()`. With injected test adapters, it uses the existing `DurableInbox.exclusive()/segments()/rotate()/acknowledge()` directly, plus the real types `GenerationProof` and `FDState`:

1. Require callable owner attester, FD probe, debug correlation and durable sink **before** lock/rotation; absent adapters reject.
2. Reattest the original owner generation and exact `inbox/debug` paths inside the queue lock. Every pending filename must carry that exact original generation; an old/untagged segment is **preserved and blocks** processing, not attributed to the new process.
3. If existing pending still aliases live inbox (interrupted hardlink before replace), complete that **same-generation** rotation first; otherwise replay existing pending before admitting another new rotation.
4. For each saved segment, the caller's FD inspector must return **exactly `FDState.DRAINED`** on its exact dev/inode and owner; BUSY/UNKNOWN cannot acknowledge.
5. The caller's debug correlator must return literal `True`; then a future P3 sink must return literal `True` only after durable idempotent commit. Reattest owner immediately before and after these steps. Any uncertainty retains pending. The underlying queue remains responsible for old FD identity, file size, final-newline and fsync/unlink safety.

**Critical limitations:** The injected debug/commit adapters in the portable tests are simulations. There is **no implemented trustworthy live debug cursor** (profile number, raw inode/offset, pre-append debug, generation), no real P3 idempotent/atomic destination sink, and no native configd/cron callsite. The currently deployed P2h has **no authorized schema2**; the upstream startup chown ordering fix from P2i remains a proof in a disposable guest and **is not wired into FD9**. Therefore `run_native_cycle()` always refuses, no native raw gathering/auto-owned list/cron is activated, and a different-generation pending segment is deliberately never deleted just to clear a backlog. Older-generation recovery with its own persisted sealed debug/source evidence must be designed before production activation; a current generation cannot prove historic origin.

## Verification choice and next gate

Run new scoped portable tests first: `python3 scripts/test-auto-detect-queue.py` plus `python3 scripts/test-auto-detect-cycle.py`; both execute from central changed-path fast CI. The existing P2e/P2g/P2i one disposable FreeBSD workflow is justified by changed `auto_detect_queue.py` semantics; do not add a VM or re-run historical P0. Exact HEAD CI and selected native status must be linked only after execution. No user appliance, production data, Config writer, actual IPFW, Strategy Lab, Voice/WAN or installer is modified.

**P2k next action:** prove generation-specific debug/raw offset persistence and an idempotent durable sink (especially old-generation pending after restart), and integrate fail-closed post-drop reownership with the original FD9 startup *before* IPFW and the activation of any real native observer. P2/P3–P5 remain OPEN.

[Approved specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P2 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) · [P2a queue](P2_AUTO_DETECT_QUEUE.md) · [P2b FD](P2B_AUTO_DETECT_FREEBSD_FD.md) · [P2c owner](P2C_AUTO_DETECT_OWNER_GENERATION.md) · [P2i native](P2I_NATIVE_ORIGINAL_PREVIEW_LOOPBACK.md).

# #1052 P2a — durable pending queue primitive (nonactivating)

**Scope:** v0.6.5_10 source only. This is one P2 engineering checkpoint, **not a completed worker**, per the [approved P0–P5 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) and [normative specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md).

## Observable user-path boundary

The old `inbox.txt` inode remains saved at `pending/<unique>.txt` after `os.link` + `os.replace`, so an existing native append FD may still write to it, and future opens write to the new inode. Crash after link and before replace is recoverable by detecting the pending inode equal to live inbox, finishing rotation, then deferring consumption. A second worker cannot rotate under the same lock. A rejected or incomplete segment remains pending rather than being truncated or deleted.

**Implemented:** `backend/auto_detect_queue.py` exports `DurableInbox.exclusive()`, `segments()`, `rotate()`, `acknowledge(..., drained, committed)`. The worker lock uses nonblocking flock and covers all critical operations. Pre-existing secure root, pending and inbox must be root owned, with private directories; device/inode, regular-file type, hard-link count, symlink and owner checks fail closed. Fsync covers prepared new file, pending directory after hard link, live directory after replace and pending directory after acknowledgement. Max 512 segments and 4 MiB per segment; incomplete final line/overflow/unknown file denies acknowledgement. No age cleanup, `truncate` or `copytruncate`.

**Proof callback contract:** `drained(path, dev, inode)` must prove native verified dvtws2 owner has no old writer FD; `committed(data)` must durably persist every valid result and ownership relocation before returning true. This source-only primitive deliberately supplies neither callback; its CLI refuses standalone execution. Never insert permissive dummy callbacks in production. The true worker must retain input on any unknown FD/process/debug/map state. Replay is at least once, with idempotent durable ownership processing.

## Executed exact-source S0

```sh
python3 scripts/test-auto-detect-queue.py
python3 -m py_compile src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_queue.py scripts/test-auto-detect-queue.py
```

**Results:** 9 of 9 portable tests PASS and py_compile PASS on Linux. Cases include open writer through replace, link-before-replace crash, new inbox separation, failed FD/commit proof, lock contention, partial last line, malicious pending/symlink, oversized pending, and retried failed commit. These are portable filesystem tests, **not native FreeBSD/OPNsense or live dvtws2 evidence**. No engine, WAN, FD9, Config, IPFW, Voice, Strategy Lab, GUI, cron or owner OPNsense was operated.

## Subsequent dormant P2j composition

The later [P2j generation-bound cycle](P2J_SAME_GENERATION_DURABLE_CYCLE.md) extends `DurableInbox.rotate()` with an **optional** validated 32-hex common-generation tag in `pending/<generation>-<random>.txt` while retaining this original P2a API behavior when the tag is omitted. The internal coordinator refuses old or untagged generations, completes link-before-replace recovery for the *same* generation and only delegates acknowledgment to the original P2a implementation after explicit FD/debug/commit tests. This does **not** supply the missing genuine debug cursor, idempotent permanent sink, authorized owner map or installed worker.

## Remaining mandatory P2 gate

1. Qualify FreeBSD `fstat -n -p` (dev/inode/write mode) against actual verified shared dvtws2 process with held FD, process exit/reuse, unavailable inspector and reboot. Native proof is not an inferred Linux result.
2. Persist production source→native generation and confirmed raw/debug correlation, excluding IPSET-only/mixed, Voice and STUN, and refusing mismatched generations.
3. Apply all known/ambiguous destinations and auto-owned relocations with a durable journal across crashes and simultaneous GUI edits, using P1 policy; never write Config. Deleting a pending segment requires the complete durable commit.
4. Only then wire the OPNsense 60-second cron→configd short worker, and complete crash/race native acceptance. P3 owns the final explicit-only auto HOSTLIST and migration separately.

No testing package was requested or published. The installed stable 0.6.5_1 is unchanged and Issue #1052 remains open.

# #1052 P2b — FreeBSD saved-inode FD inspection (read-only; no worker activation)

**Scope:** v0.6.5_11, continuing the [P2a durable queue](P2_AUTO_DETECT_QUEUE.md) under the [approved P0–P5 plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). This is an implementation/proof checkpoint, **not completion of P2** or authorization to acknowledge a raw segment.

## User-relevant invariant and actual code

If the existing `dvtws2` append FD still refers to an old inode protected by `pending`, the periodic collector must retain that segment. The same holds when FreeBSD inspection fails or process ownership is uncertain. A verified no-open-FD result can become one **necessary**, but not sufficient, prerequisite for eventual acknowledgement; successful durable hostlist/ownership commit and raw/debug generation correlation remain separate.

`src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_fd.py` is **detached read-only**. Its `probe_pending_fd(segment, device_id, inode, owner=OwnerToken(...))` demands a caller-provided exact PID, process birth stamp and absolute executable identity. It rejects non-FreeBSD, non-root, symlinks, wrong inode/owner/mode/link count, failed commands, modified pending, mismatched PID/birth/binary, incomplete or unverifiable `fstat` output. `fstat -n -v -p PID PATH` filters by the **actual pending directory entry** and reports target device/inode and FD access mode; the parser refuses mismatched or malformed records. A matching FD (even read-only) returns `BUSY`, a trustworthy header-only observation under stable owner returns `DRAINED`, all unknowns return `UNKNOWN`. It does not read Config or user domain values, mutate a list, kill/restart an engine, or touch IPFW.

**Critical owner boundary:** a PID file or freshly observed `ps` record alone is **not** an authenticated original shared-service generation. The authentic `OwnerToken` must be provisioned by the later persisted generation/owner binder; this module does not create such a token. In P2b `auto_detect_queue.acknowledge()` has **no production caller** and the new inspector cannot delete a pending segment. Do not treat a passing `fstat` check as exactly-once or completed domain processing.

### FreeBSD 15 wire-format correction discovered by the first native gate

The initial scoped native runner failed **at the held-writer assertion**, rather than being declared PASS. Review of the [exact FreeBSD stable/15 fstat.c](https://github.com/freebsd/freebsd-src/blob/stable/15/usr.bin/fstat/fstat.c) revealed the cause: the numeric `DEV` column is printed using `%#5jx` as a **single hexadecimal filesystem ID**, not a major/minor pair. Its filename filter compares the same `st_dev` + `st_ino` values. The targeted correction compares that hex `DEV` directly to `st_dev`, and the fixture reproduces the true on-wire format. The superseded failed run remains failed; actual native proof requires a new exact-head green run.

## Verification selected before PR

S0 exact staged source: `python3 -m py_compile` plus `python3 scripts/test-auto-detect-fd.py --self-test`, **9 portable cases PASS**: valid closed evidence, held writer and reader, foreign inode/device, changed birth/executable, damaged/missing/truncated output, error/stderr, off-target refusal, symlink/replaced inode. The new native script has a fail-closed non-OPNsense guard.

S2 scoped [native OPNsense 26.7 workflow](../../.github/workflows/p2-native-fstat.yml): a **single disposable guest** opens a real writer FD in an isolated Python child and demonstrates `BUSY` while held, `DRAINED` after closure with the same live PID, `UNKNOWN` on incorrect birth and after process exit. That tests the real FreeBSD **kernel fstat wire format and file-open lifecycle**, not native `dvtws2` owner authorization, traffic capture, generation binding or production watcher. A green workflow and separately qualified native package are required before calling the respective proof PASS. Its exact-head run/result will be reported in #1052; no other historical VM matrix is justified. Do not confuse package built in CI with a published/installed test package.

## Remaining P2 work

1. Bind the real shared service's **authenticated** active `dvtws2` PID/birth/executable and same-generation final argv, observer profile, raw/debug files and exact source HOSTLIST map. Reject stopped/foreign/reused PID, stale generations, Voice/STUN/mixed-IPSET and corrupted/synthetic records.
2. Use the guarded FD probe under the worker lock, without turning uncertain information into `drained=True`. Cover engine-owned old FD and concurrent append/rotation on real FreeBSD, not just a surrogate.
3. Durably commit all destination/auto-owned routing and relocation with crash journal, native hot reload and user editing conflict protection before pending unlink (at least once + idempotent).
4. Register the approved native 60-second OPNsense cron → configd Python worker only after the above gates; preserve original FD9, single Config writer, Voice and Lab.

**Evidence levels:** source implementation and 9 local portable tests; native workflow result pending execution at authoring, genuine common owner and owner-appliance acceptance **NOT VERIFIED**. Stable v0.6.5_1 package unchanged.

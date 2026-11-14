# #1052 P2k8q3b2b — original P2b historical writer-FD inspection

**Source candidate:** `v0.6.5_52`, 14 November 2026. **Original path:** `backend/auto_detect_original_lock_handoff.py` → `CursorChain.acknowledge()` → **existing** `auto_detect_fd.py::probe_pending_fd()`. No second owner, writer, scanner daemon, queue, lock, Config parser or ACK algorithm.

## Reproducible unsafe condition on pre-fix source

A previous `dvtws2`/child PID may retain the same open native raw inode after the original queue's hardlink + replace. The original `probe_pending_fd()` checked exactly one PID with `/usr/bin/fstat -n -v -p <current engine> <pending>`. A current process with no matching FD produced `FDState.DRAINED`, even if an old **different PID** still held the inode and could append after the original physical ACK. P2c attesting the new engine's birth does not exclude this historical writer.

## Single-source correction

The same root-only, original-P2c-bound P2b inspector now executes **`/usr/bin/fstat -n -v -m <pending>` without `-p`**. It limits stdout to 128 KiB/4096 rows, checks native header, integer PID and FD, hexadecimal FreeBSD device, exact original inode and R/W access for **every process**, and treats all other open FDs as BUSY. An mmap/special/unparseable row, partial output, kernel warning, foreign inode or changed owner/file yields UNKNOWN, never DRAINED. The caller holds one read-only `O_NOFOLLOW` FD to pin the original inode; **only** the precise `os.getpid()` + this FD number with `r` mode is ignored so the inspector does not always block itself. Original process birth/exe and original physical dev/inode/nlink/size/mtime checks run before and after the native scan; the existing Config-held v2 ACK pathway still must reattest immediately before physical unlink. Unknown and BUSY are never ACK permits.

All-process `fstat` is a **bounded snapshot**, not an atomic writer-freeze guarantee. In particular, an external process opening the inode after inspection or a race not caught by current protected-file mode/queue lock is not proven safe by this change. No previous-generation sealed debug/raw receipts or automatic historical pending replay are added. The original running process, packet profile ancestry and native generation must still be independently qualified before enabling the actual observer.

## Tests and claim limits

- **Portable exact source** `scripts/test-auto-detect-fd.py --self-test`: old PID writer and unrelated reader refuse even if current P2c engine has no FD; only inspector's exact read-only FD may be ignored; malformed/special/mismatched rows, wrong PID birth, group ownership, symlink, race, warning and off-FreeBSD refuse.
- **Disposable OPNsense/FreeBSD** existing P2b `--native` test: real process A holds native raw FD (BUSY), closes while remaining alive (DRAINED), then **distinct prior-process B** opens the same inode while A remains the qualified current owner (BUSY), closes (DRAINED); wrong birth/reaped current PID remain UNKNOWN. Existing `.github/workflows/p2-native-fstat.yml` triggers this exact HEAD test. Another P2e/P2g/P2i VM may run if its production importer is affected; its PASS is not a substitute for the P2b native writer witness.

No observer `authorize`, native auto generation, minute scheduling or actual owner appliance install is performed. Source code and disposable process evidence are not user-live validation. Stable owner-installed `0.6.5_1.pkg` unchanged; no `_52.pkg` publication. All 4 MiB raw/debug and 512 cursor-slot **lossless rollover**, previous-generation signed/sealed provenance, early-packet/rollback/reboot and full ACK safety remain open.

[Original P2b](P2B_AUTO_DETECT_FREEBSD_FD.md) · [P2c owner](P2C_AUTO_DETECT_OWNER_GENERATION.md) · [Original Config-held v2](P2K8P_ORIGINAL_CONFIG_HELD_V2.md) · [Normative plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md).

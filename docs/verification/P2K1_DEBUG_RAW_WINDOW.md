# #1052 P2k1 — generation-bound native debug/raw window **proposal, not acknowledgment**

**Source increment:** `v0.6.5_22`. This is a **bounded, read-only, import-only correlator** between original P2c `GenerationProof`, the actual native debug file and already saved raw segment *bytes*. No installed engine, cron/configd worker, FD9 writer, owned HOSTLIST, purge or production socket is changed. P2 remains OPEN.

## User-visible failure before this boundary

A discovered domain in a native debug line must **not** automatically become a HOSTLIST entry. The pinned upstream Zapret2 v1.0.7 [`nfq2/desync.c` auto-add path](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L473-L487) writes `HOSTLIST_DEBUGLOG_APPEND(... "adding to ...")` **before** `HostlistPoolAddStr` and `append_to_list_file`. If the append fails, debug can contain a plausible positive while `inbox.txt` never received the hostname. Likewise, there are `fail counter`, `incoming RST`, `NOT adding` and other diagnostic lines that must not count as positive raw events. Previous P2i synthetic raw/debug equality and P2j's callable `correlate` slot are not a root-owned durable checkpoint or authenticated engine-to-inode transaction.

Before P2k1, no native raw/debug reader with explicit byte-offset, same-generation and inode-prefix checks existed (`src/.../auto_detect_debug_window.py` absent). The smallest failing path was: **a debug positive without a completed raw line** / **new generation with prior debug data** must not allow the P2j commit/ack path. Portable tests cover both refusals on real local files; earlier source P2j cannot supply these checks.

## Implemented inert reader

`backend/auto_detect_debug_window.py` has:

- `empty_epoch(proof)` — accepts only a **zero-length, separately provided exact** P2c-generation debug path on an attested root-owned regular inode; returns an in-memory `Cursor(generation, device, inode, offset=0, sha256(empty))`. It **rejects nonempty historical debug** rather than assuming old data belongs to the new process.
- `propose_window(proof, cursor, raw)` — requires original 32-hex operation/generation identity and trailing observer profile; reads the complete debug inode through `O_NOFOLLOW` with exact owner, links, parent and opt-in root:nobody `0710/0660` modes. Rechecks dev/inode/size/mtime before/after a bounded read; rejects truncated, replaced, rewritten or incomplete debug data by the cursor's prefix digest and exact byte offset. Upper limits are 4 MiB full debug, 256 KiB unread debug window, 4 MiB raw and 4096 raw rows.
- For **only** pinned v1.0.7 positive `host : profile N (...) : client ... : proto ... : adding to <exact-native-inbox>` lines, validates explicit observer number, native raw path and strict ASCII hostname (never infer unknown/Voice/IPSET/other profile). Other debug diagnostics cannot count as successful appends. It requires the **entire ordered list** of positive log candidates to equal the actual complete newline-terminated raw rows; missing, additional, reordered or wrong-profile positives refuse. Returns immutable `Window(candidates, proposed_cursor)` including native profile number, **byte offset** and proposed digest, but **does not persist or advance any cursor**.
- Public `run_native_debug_collector()` unconditionally refuses. There is **no** registered worker or `True` callback for P2j `acknowledge`. No raw/debug contents are uploaded; tests use synthetic non-user domains.

## Why this is deliberately NOT a complete P2k / no deletion authorization

1. The native debug and raw file writes are **not atomic with each other**: equality of two read-only snapshots is necessary supporting evidence, never independently proves the actual `dvtws2` completed a particular append. Their original generation, open writer FDs, old saved inbox inode and true startup ownership **must be independently attested** under the original FD9. Untrusted `nobody` can write both raw/debug, so a forged matching pair cannot authorize permanent target mutation.
2. A `Cursor` supplied by a caller is not a **root-persisted epoch receipt**, and `proposed_cursor` is not durable. Crash/reboot and old-generation pending **cannot be acknowledged** until the original sealed source map and per-generation cursor+debug segments are recovered safely. There is no active rotation of debug under P2k1.
3. The P3 normalized/auto-owned HOSTLIST destination must be an atomic, idempotent, Config-independent durable commit with GUI conflict protection. No such commit adapter is supplied or called here. P2j continues to refuse native activation; this module's `Window` is not the literal `True` required by P2j, by design.
4. The observer has only known **TCP/HTTP** native matching qualification from P2i; the parser also recognizes upstream `tls`/`quic` syntax **without** claiming actual accepted traffic for those protocols.

## Verification scope

S0: `python3 -m py_compile` plus `python3 scripts/test-auto-detect-debug-window.py`, actual-file 13-case portable suite covering complete positive, counter/reset/NOT adding exclusion, debug-before-raw failure, missing/extra/order failures, wrong native profile/path, incomplete final lines, switched generation or inode, tampered cursor prefix, symlink/wrong mode/hardlink, pre-existing debug history and disabled public entry. One group-permission case is conditionally skipped only when runner has GID 0. `scripts/test-auto-detect-cycle.py` continues unchanged.

S1 exact-head central CI runs the new 13-case test inside its **existing fast user-path gate**. No additional isolated VM is justified just for an import-only parser; reuse P2i's already qualified real native log format and actual FreeBSD observation as prior evidence, **not** as a fresh P2k native result. The actual CI HEAD/result must be reported separately.

**Next P2k2:** durable original-FD9-owned generation/debug epoch receipt and cursor persistence (including old-generation pending recovery, prefix/hash/inode proof and one checkpoint transaction with destination commit), then implement the P3 atomic auto-owned destination writer and force original FD9 `nobody` startup `chown` reownership before IPFW/recording. Only after real FD9, native FD drain, debug binding, destination fsync and crash/reboot tests can the one-minute configd/cron consumer and authorized schema2 be activated.

[Approved specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) · [P2j dormant same-generation cycle](P2J_SAME_GENERATION_DURABLE_CYCLE.md) · [P2i native evidence](P2I_NATIVE_ORIGINAL_PREVIEW_LOOPBACK.md) · [P2c owner](P2C_AUTO_DETECT_OWNER_GENERATION.md).

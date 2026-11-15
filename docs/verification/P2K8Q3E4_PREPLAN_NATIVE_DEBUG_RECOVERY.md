# #1052 P2k8q3e4 — original prepared native-debug pre-destination recovery

**Candidate:** source `v0.6.5_63`, 15 November 2026. This is a **source-only dormant original Config/FD9 chain**; no active schema-2 observer, cron, external worker, engine signal or published .pkg.

## Pre-fix actual user boundary

The previous _62 source allowed authoritative UNKNOWN raw-first only when a **new intent** was prepared after the diagnostic debug inode changed. An already prepared native-debug `intent.json` stayed permanently tied to the old debug inode; the legitimate original pending raw/FD9/P2b proof remained but a fresh protected debug inode caused `CursorChain.prepare()` replay to refuse, even with no destination plan. The _61 real OPNsense native test established that such independent raw/debug cuts can occur while diverted HTTP continues normally. The new regression drives the old **P2a→P2k8o→P2k8n→original Config/P1→ACK** path end to end; with old _62 source the new required completed scenario would fail.

## Durable one-slot recovery contract

1. The original P2a queue's **held single lock** and original shared P2c/FD9 owner qualify exactly one detached same-generation pending raw file, unchanged raw device/inode/size/SHA and FreeBSD P2b **all-PID FDState.DRAINED**. No new writer/lock/service.
2. The original immutable `intent.json` was already prepared as `evidence=native-debug` with valid original debug prefix. Only if its required old debug inode is now different from a separately root-protected and bounded current debug file, and there is **no destination directory at all**, may an explicit recovery occur. Same-inode content corruption, missing/unsafe debug, wrong generation/owner, BUSY/UNKNOWN FD, malformed/incomplete raw and any destination artifacts fail closed.
3. The same original protected v2 slot gains exactly one `recovery.json`, created using existing `_write_once` (new file, fsync, link-once and directory fsync). It seals the **SHA-256 of the unchanged original intent bytes**, generation, pending and pending SHA, original previous ACK, and the replacement debug dev/inode/size/SHA. The original intent **is never edited**. A crash after the durable receipt but before Config commit is safe to replay.
4. Each `CursorChain.tip()` checks the unchanged original intent against its previously ACKed predecessor FIRST, then verifies the immutable recovery receipt and derives an **effective `evidence=raw-first`** view with debug end equal to the already acknowledged start. No fake new debug cursor. This view, and only this view, is passed to original PHP Config/P1/PSL/manual-exclusion policy and the **existing** durable destination plan/checkpoint/ACK. After physical ACK, the generation remains sticky raw-first, including when historical debug names are restored.
5. A corrupt/replaced/malformed recovery record, mismatched SHA, new debug reusing original device/inode, already started destination, changed Config/P1 target or process/FD/ref cannot authorize commit/ACK. A post-checkpoint diagnostic cut remains blocked by this source-only increment; its rescue needs a distinct evidence-based P2k8q3e5 contract. No unbounded retries or implicit age deletion.

## Focused source regressions and evidence classification

- `scripts/test-auto-detect-cursor-chain.py`: true P2a pending, initial native-debug intent, protected atomic debug inode cut, original immutable intent + durable recovery, crash-like reconstruction of a fresh chain object, repeated original Config checkpoint and original physical ACK, next sticky raw-first event; corrupt forged receipt, busy raw, false owner, already existing empty/committed destination directories refuse without deleting pending.
- `scripts/test-auto-detect-original-v2-prepare.py`: same **original P2k8o** held-queue prepare replay after debug swap, then original v2 completion.
- `scripts/test-auto-detect-original-v2-config.py`: real original Config-held source policy route, P1 and final Auto HOSTLIST, no known YouTube/User guesses, new manual/global exclusion after original native event but **before** commit, idempotent replay.
- A local POSIX isolated scope check verifies hardlink+atomic debug cut with old inode preserved, exact SHA anchor of original intent and unchanged committed cursor; it **does not** prove exact modified repository test suite, FreeBSD all-PID FD behavior, or installed appliance.
- Exact-head CI/package-build/native installed claims must be made only from actual completed workflow logs. A native package build is not publication or owner acceptance.

## Still blocked

This recovery is limited to an original `native-debug` intent **without any started destination**. After any plan or checkpoint, pending remains retained and the original mode cannot be rewritten; this is P2k8q3e5. Finite debug/raw 4 MiB and 512 original cursor slots, all-process historical ownership across reboot/ENOSPC, the real original FD9 enabled schema-2 release, cron and owner-installed continuous-IPFW acceptance remain OPEN. Periodic STOP/CONT, engine restart, disable IPFW, independent daemon/queue or second Config writer are forbidden.

[Original _62 raw-first mode](P2K8Q3E3_ORIGINAL_RAW_FIRST_V2_FALLBACK.md) · [Real _61 running IPFW](P2K8Q3E2_RUNNING_NONBLOCKING_DEBUG_COHORT.md) · [Source plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md).

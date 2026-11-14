# #1052 P2k8q3d1 — original P2k8o native debug pre-cut

Source candidate v0.6.5_56, 15 November 2026. Source-only bounded backpressure, NOT native feature activation or a continuous lossless rollover.

## Failure before this change

Original v2 P2k8o rotated current raw into pending BEFORE original P2k8n CursorChain.prepare invoked P2k1 propose_window. An already-invalid debug file could make the downstream stage refuse after the raw inode had been detached. The original raw was intact but stranded pending instead of remaining live; this violates the intended fail-closed source handoff.

## Selected single-owner repair

The SAME P2k8o helper, under ONE original P2a queue flock and P2c owner proof, uses the EXISTING P2k1 _read_exact protected native debug reader before either a fresh raw rotation or same-generation crash-link completion. It verifies exact P2k8n ACK cursor dev/inode, SHA-256 committed prefix and cursor bound, protected stable <=4 MiB debug snapshot, <=256 KiB unread tail, complete newline and no NUL. Known-bad input refuses BEFORE a raw cut; no alternate writer, debug parser, queue, configd, cron or collector was added. A fully detached current pending follows unchanged original P2b and v2 retry.

## Real-file tests

Five cases added to scripts/test-auto-detect-original-v2-prepare.py against original P2a/v2/immutable original epoch: (1) unread >256 KiB, (2) debug >4 MiB, (3) replaced debug inode with same contents, (4) prior ACK debug prefix altered before second batch, (5) partial native line. Each requires unchanged original live raw inode, no new pending and no irreversible intent; exact restoration allows original same-generation retry. Portable P2c owner and P2b FD are injected, NOT physical owner-installed witnesses. The helper logic was also exercised locally against a separate five-case real-file harness, but exact source integration needs CI qualification.

## Unresolved safety gate

This is a finite pre-cut snapshot, NOT an atomic native producer barrier. The real _55 OPNsense native witness still proves an HTTP event between independently replaced raw and debug pathnames reaches raw:current/debug:previous. Prove a genuine original FD9/P2c no-writer epoch, or certified durable cross-inode provenance, before any production debug rotation. Historical FD closure, 4 MiB raw/debug and 512-slot v2 rollover, disk full, crash/reboot, ACTIVE schema-2, cron and physical ACK remain UNQUALIFIED. commit_authorized=false. No _56.pkg published; stable owner-installed _1 unchanged.

[Original preparer](../../src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_original_v2_prepare.py) · [Native midcut](P2K8Q3C2_NATIVE_MIDCUT_RAW_DEBUG.md) · [Plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md).

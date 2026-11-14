# #1052 P2k8q3d3 — original IPFW packet in flight during native STOP

Candidate v0.6.5_58, 15 November 2026. The SAME existing original P2e/P2g/P2i disposable OPNsense 26.7 native VM, original FD9/one PID, P2a queue, P0 scoped IPFW and pinned upstream dvtws2. No new worker, independent queue, production signal, package release or activation.

## Concrete missing evidence after _57

The _55 FreeBSD native interstitial real event proved live independent raw/debug swaps split one positive across two generations (`raw:current,debug:previous`). _57 proved the SAME original PID can be kernel-STOPPED before both swaps and resumed afterward with an event correctly in both new inodes. But the _57 STOP interval had **no diverted traffic at all**. That proof cannot establish packet availability during STOP. This increment measures the missing live IPFW case rather than declaring quiescence safe for the installed router.

## Original guest executable test

1. Run the unchanged existing original P2i `--native` negative control, retaining the real midcut split and first-match; release its PID, scoped divert rules and producer root.
2. Run original `--native-quiesced` sequentially in the SAME guest and pinned release. Require one original dvtws2 PID/birth and dropped nobody UID; demonstrate native known-host first-match and first unknown native raw/debug evidence. Confirm original FreeBSD `ps stat=T` after sending SIGSTOP only to that disposable PID.
3. Read the real original P0 outbound loopback scoped IPFW `-a list` rule packet count. Launch ONE known-HOSTLIST HTTP exchange concurrently through the existing P0 native exchange. Require (a) its thread started, (b) the original scoped rule packet count **increased** before SIGCONT, and (c) the same HTTP exchange is still INCOMPLETE while dvtws2 remains FreeBSD STOPPED. Print `REAL_NATIVE_STOPPED_DIVERT=ipfw_packet_counted_request_stalled` only when all three are proven.
4. Only while the same PID remains STOPPED run the ONE original P2a queue physical raw rotate and the existing guest-only debug rename/recreate with fsync. Require exact original pending raw and old debug unchanged, fresh raw/debug paths empty and same original native process still kernel STOPPED after both changes.
5. SIGCONT and prove same PID/birth no longer STOPPED; require the **same outstanding known-HOSTLIST exchange** delivered exactly to the original P0 synthetic server. It must not create a native auto positive or new raw. Print `REAL_NATIVE_STOPPED_DIVERT_RECOVERY=known_first_match_delivered_after_sigcont` only after exact delivery.
6. Finally send a distinct native unknown HTTP/RST after resume, requiring one positive in each current new raw/debug inode, old ones retained without duplicate, true original P0 first-match, genuine P2b all-process old-inode FD snapshot, and full cleanup. On ANY test error during STOP, SIGCONT occurs before bounded synthetic-thread join, engine termination, scoped IPFW removal and original FD9 unlock. New no-leak failure code explicitly blocks successful test cleanup.

The exact-head workflow already runs both original `--native` and `--native-quiesced` sequentially in the SAME guest; only existing P2i test code and canonical documentation/revision changed. No additional VM, workflow, signal caller or fallback queue.

## Evidence boundary

The packet-count + incomplete-request measurement proves a real diverted packet **stalls while original dvtws2 is STOPPED in this guest experiment**. Eventual delivery after SIGCONT, if observed, does not prove bounded latency or no loss across all production TCP/UDP/IPFW flows. It is a strong reason not to enable a production SIGSTOP rotation without traffic-availability and crash/reboot/ENOSPC proofs. A single all-PID old-raw FD snapshot remains non-authorizing. Historical sealed previous-generation provenance, continuous lossless 4 MiB raw/debug and 512-step original v2 cursor rollover, genuine owner ACK and ACTIVE schema-2/cron remain OPEN. `commit_authorized=false`; no `_58.pkg` published; stable owner-installed `_1.pkg` unchanged.

[P2i native test](../../scripts/test-p2i-original-preview-native.py) · [Previous native STOP-only](P2K8Q3D2_NATIVE_STOPPED_CUT_WITNESS.md) · [Plan](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md).

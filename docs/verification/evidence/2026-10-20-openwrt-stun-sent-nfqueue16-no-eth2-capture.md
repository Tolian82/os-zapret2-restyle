# 20 October 2026 — Valid headless STUN send on OpenWrt; queue delta +16, no match to narrow eth2 capture

**Status:** user ran the corrected Python3 headless STUN test on vOpenWrt, 20 Oct 2026. **The sender succeeded locally, but on-wire location/packet contents and youtubeUnblock fake emission remain unverified.** This does not establish a failed server, a broken STUN filter or six fake UDP packets.

## Exact owner observations

```text
=== UDP SENDER PREFLIGHT ===
SENDER=python3
=== BEFORE ===
NFQUEUE_BEFORE=7752
=== START CAPTURE ===
=== SEND EXACTLY ONE STUN REQUEST ===
STUN_BYTES_SENT=20
SEND_EXIT=0
=== AFTER ===
NFQUEUE_AFTER=7768
NFQUEUE_DELTA=16
=== WAN PACKETS ===
(empty)
=== PAYLOAD DISTRIBUTION ===
(empty)
=== CAPTURE STATUS ===
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on eth2, link-type EN10MB (Ethernet), snapshot length 96 bytes
0 packets captured
0 packets received by filter
0 packets dropped by kernel
```

The sent 20-byte packet was a correct RFC5389 Binding Request with header bytes `000100002112a442` and 12-byte transaction ID. The sender's `socket.sendto` returning 20 establishes delivery to the local kernel, **not** that the packet traversed `eth2` or reached the public STUN server. Capture BPF was `udp and src host 192.168.80.236 and dst port 19302` **only on `eth2`**; packets using another interface, IP source, or translated/detoured path would be invisible. This is an overly strong assumption about egress, **not a tcpdump syntax failure**.

`inet fw4 youtubeUnblock` queue 537 UDP counter increased by 16 across the run, but it is **global across active traffic** and measures queue rule matches, not packets conclusively classified as STUN or emitted six 64-byte fake payloads. The delta cannot be attributed to this single STUN probe without a packet trace and/or isolated classifier evidence.

**Next one bounded measurement** on OpenWrt, no settings changes: DNS-resolve target with installed `python3`, record `ip -4 route get TARGET`; start `tcpdump -i any -nn -tt -q -l 'udp and port 19302'` (prove capture is listening before send), issue precisely one valid 20-byte Python socket UDP request to the **same pinned resolved IPv4**, print `getsockname()` source and `STUN_BYTES_SENT`, stop capture after seconds and report observed UDP lengths plus before/after queue counters. `-i any` is Linux's interface-wide capture; it may report multiple interface representations of the same datagram, so observed counts must be deduplicated by interface, tuple and timing if necessary. If no matching packets appear, debug routing/nft interception before attributing failure to the public server or desync. This is still a headless **synthetic** probe, not a Telegram SOCKS5 real-call acceptance.

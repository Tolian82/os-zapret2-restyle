# 2026-10-20 — First OpenWrt headless STUN attempt never sent a packet (BusyBox nc CLI mismatch)

**Owner-live observation; no valid STUN network test occurred.** Test intent was one RFC5389 20-byte STUN Binding Request to `stun.l.google.com:19302` from OpenWrt 25.12.5, routed by `eth2` source `192.168.80.236`. The actual `nc` is BusyBox 1.37.0 with help `Usage: nc [IPADDR PORT]`; `nc -u -w 2` options are unsupported.

```text
=== ROUTE AND BASELINE ===
default via 192.168.80.1 dev eth2 src 192.168.80.236 metric 1
default via 192.168.2.140 dev eth1 src 192.168.2.236 metric 3
meta l4proto udp ct original packets < 9 counter packets 3786 bytes 393502 queue flags bypass to 537
=== SEND ONE STUN BINDING REQUEST ===
NC_EXIT=1
BusyBox v1.37.0 ... Usage: nc [IPADDR PORT]
=== YOUTUBEUNBLOCK AFTER ===
meta l4proto udp ct original packets < 9 counter packets 3786 bytes 393502 queue flags bypass to 537
=== WAN UDP PACKETS ===
(empty)
=== CAPTURE DIAGNOSTICS ===
0 packets captured
0 packets received by filter
0 packets dropped by kernel
```

**Interpretation:** invalid BusyBox invocation stopped local data generation. No evidence for or against working STUN match, upstream response, UDP spoofing or six 64-byte fakes. No OpenWrt packet-forwarding setting should be changed on this basis. Counter did not change and the bounded capture showed no matching WAN packet.

**One corrected action:** detect installed `python3` (UDP socket/sendto) or `socat` (`UDP4`) and use exactly one 20-byte RFC5389 Binding Request with correct `00 01 00 00 21 12 a4 42` header, transaction ID 12 bytes; capture only WAN `src 192.168.80.236` and `udp dst port 19302`, compare counters before and after. Refuse to run if there is no supported UDP sender. Does not test real Telegram client's SOCKS5 `:1070`, nor the pinned non-STUN Reflector Hello.

Package version remains v0.5.5_7; documentation-only issue, no change to appliance plugin or runtime.

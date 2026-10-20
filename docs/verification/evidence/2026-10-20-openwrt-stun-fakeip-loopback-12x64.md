# 20 October 2026 — First captured OpenWrt synthetic STUN: FakeIP loopback, 12 × 64 and 1 × 20

**Evidence level: owner-live OpenWrt 25.12.5 shell, one resolved-domain STUN send and `tcpdump -i any` metadata. No PCAP payload or WAN egress evidence.** The result is an important local fake emission observation, not Telegram call bypass acceptance.

## Exact run

```text
=== RESOLVE STUN SERVER ===
STUN_SERVER=198.18.0.10
=== ROUTE ===
198.18.0.10 via 192.168.80.1 dev eth2 src 192.168.80.236
=== BEFORE ===
NFQUEUE_BEFORE=8614
=== SEND STUN ===
LOCAL_SOCKET=192.168.80.236:39459
STUN_BYTES_SENT=20
SEND_EXIT=0
=== AFTER ===
NFQUEUE_AFTER=8624
NFQUEUE_DELTA=10
=== CAPTURED UDP ===
1792499615.374943 lo In IP 192.168.80.236.39459 > 198.18.0.10.19302: UDP, length 64
[10 additional UDP 64 and one UDP 20, captured in ~39 microseconds]
1792499615.374978 lo In IP 192.168.80.236.39459 > 198.18.0.10.19302: UDP, length 20
1792499615.374980 lo In IP 192.168.80.236.39459 > 198.18.0.10.19302: UDP, length 64
1792499615.374982 lo In IP 192.168.80.236.39459 > 198.18.0.10.19302: UDP, length 64
=== PAYLOAD SIZES ===
PAYLOAD=20 PACKETS=1
PAYLOAD=64 PACKETS=12
=== TCPDUMP STATUS ===
listening on any, link-type LINUX_SLL2
13 packets captured
26 packets received by filter
0 packets dropped by kernel
```

**Critical source-qualified interpretation:** `198.18.0.10` belongs to **Podkop's configured FakeIP block `198.18.0.0/15`** (upstream `itdoginfo/podkop/podkop/files/usr/lib/constants.sh`, `SB_FAKEIP_INET4_RANGE`). It is **not** the public IPv4 of `stun.l.google.com`. The `ip route get` result is a main route lookup, not evidence the subsequent actual netfilter-marked packet egressed `eth2`. All 13 recorded datagrams are marked `lo In`, so there is **no confirmed external UDP** to Google's STUN responder and no STUN answer.

Captured on `lo` are **12 UDP payloads length 64** accompanying **one 20-byte request**, consistent with a UDP fake mechanism but **not enough to attribute the exact number and source to youtubeUnblock's configured 6×64** or assert two triggers/sections. NFQUEUE global UDP rule count `8614→8624` is +10, not the number of 64-byte packets, and is not safely correlated one-to-one with either application payload or fakes. `tcpdump` received-by-filter count 26 vs captured 13 cannot be blindly interpreted as 13 duplicate packets.

## One next controlled step

**Bypass FakeIP only for this test's target resolution, without modifying any DNS, proxy or firewall setting.** Fetch `stun.l.google.com` publicly resolvable A record via remote DNS-over-HTTPS `https://dns.google/resolve?name=stun.l.google.com&type=A` **through the existing local GOST `socks5h://127.0.0.1:1088`** (preflight curl support/connectivity and validate JSON A as globally routable IPv4). Use this **numeric real IP** for one RFC5389 20-byte STUN send. Before sending, print `ip route get REAL_IP`; during send, `tcpdump -i any -nn 'udp and port 19302'`, report interface/direction, UDP sizes and NFT queue counters before/after. If DoH or GOST unavailable, stop without packet emission or config modification and report the failure. Avoid assuming specific IP or claiming Google receipt unless a response is independently captured.

This new IP-only experiment will not be a test of **actual Telegram client's SOCKS5** `192.168.1.236:1070` voice transport, nor of the pinned 40-byte **non-STUN Telegram reflector**. Preserve separate current tgcalls media-positive `.1.140` and negative `.1.2/.1.236` evidence. No need for a human test participant now; no package version changes.

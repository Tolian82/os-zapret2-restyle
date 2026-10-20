# 2026-10-20 — OpenWrt STUN public IPv4 resolved through pfSense DNS, no DNS or proxy changes

**Owner-live evidence; only DNS resolution completed. The subsequent numeric-IP STUN request has not yet been observed or accepted.**

## Owner's DNS and HTTPS outputs

On **OpenWrt**:
```text
drill stun.l.google.com A @127.0.0.1
stun.l.google.com. 60 IN A 198.18.0.10
SERVER: 127.0.0.1

drill stun.l.google.com A @192.168.1.140
stun.l.google.com. 1392 IN A 74.125.250.129
SERVER: 192.168.1.140
```

`198.18.0.10` is within Podkop/sing-box FakeIP reserved `198.18.0.0/15`. The answer from pfSense `192.168.1.140` is a **globally routable IPv4, `74.125.250.129`** at the time observed. This isolates FakeIP **for the synthetic probe's destination** without switching Podkop off, changing the router's resolver, or touching the proxy. It does not imply the real Telegram client is unaffected by FakeIP or that that IP remains a live STUN responder indefinitely.

Both attempts to obtain Google DNS-over-HTTPS A records via different installed proxy paths failed:
- OpenWrt `socks5h://127.0.0.1:1088`: `curl: (35) ssl_handshake returned: (-0x7200) SSL - An invalid SSL record was received`.
- OPNsense Squid `http://192.168.1.2:3128`: `curl: (35) TLS connect error: error:0A00010B:SSL routines::wrong version number`; OpenWrt repeated the Squid route and saw the `-0x7200` handshake error.

These TLS-layer errors concern the **particular `dns.google` HTTPS path**; no evidence implicates UDP processing, STUN, Podkop service health or youtubeUnblock. Stop further DoH/proxy experimentation because DNS resolution for this specific test is already solved by pfSense DNS.

## One next accepted scope

From OpenWrt `root@vOpenWrt` send **exactly one 20-byte RFC5389 STUN Binding Request using Python3 directly to numeric `74.125.250.129:19302`**. Before send, show `ip -4 route get 74.125.250.129`; start `tcpdump -i any -nn -tt -q -l 'udp and host 74.125.250.129 and port 19302'`, snapshot youtubeUnblock UDP queue537 nft counter before/after, print socket source, count packet payload lengths **separately per interface and direction**. An optional UDP receive with 2s timeout is allowed to report response. No other DNS lookups, no human Telegram call, no router config, firewall, NAT, sing-box or service changes. Distinguish all-capture `lo In` from real `eth2 Out` and account for possible duplicates; do not equate queue-counter increments directly to emitted 64-byte fake packets.

Existing `tgcalls_cli` non-STUN Reflector control remains separate and must not be re-executed without one-factor rationale. No package/version changes.

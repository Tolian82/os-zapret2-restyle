# 20 October 2026 — OpenWrt STUN egress observed: six UDP64 before original UDP20 on eth2

**Owner-live controlled proof, 20.10.2026.** Scope: one direct **20-byte STUN Binding Request** emitted by Python3 on OpenWrt VM (not Telegram, not SOCKS5 GOST), explicitly targeting numerical public IPv4 `74.125.250.129:19302`. Passive `tcpdump -i any` filtered on host and UDP port. No configuration changes, no packet body retained; no replies were observed/received over the 2-second socket receive window.

## Exact owner output

```text
=== PUBLIC STUN TARGET ===
TARGET=74.125.250.129:19302
74.125.250.129 via 192.168.80.1 dev eth2 src 192.168.80.236
NFQUEUE_BEFORE=10386
=== SEND ONE STUN REQUEST ===
LOCAL_SOCKET=('192.168.80.236', 48758)
STUN_BYTES_SENT=20
RESPONSE=TIMEOUT
SEND_EXIT=0
=== NFQUEUE ===
BEFORE=10386
AFTER=10394
DELTA=8
=== CAPTURED UDP ===
1792504514.113260 eth2  Out IP 192.168.80.236.48758 > 74.125.250.129.19302: UDP, length 64
1792504514.113268 eth2  Out IP 192.168.80.236.48758 > 74.125.250.129.19302: UDP, length 64
1792504514.113274 eth2  Out IP 192.168.80.236.48758 > 74.125.250.129.19302: UDP, length 64
1792504514.113275 eth2  Out IP 192.168.80.236.48758 > 74.125.250.129.19302: UDP, length 64
1792504514.113277 eth2  Out IP 192.168.80.236.48758 > 74.125.250.129.19302: UDP, length 64
1792504514.113279 eth2  Out IP 192.168.80.236.48758 > 74.125.250.129.19302: UDP, length 64
1792504514.113280 eth2  Out IP 192.168.80.236.48758 > 74.125.250.129.19302: UDP, length 20
=== PACKETS BY INTERFACE AND SIZE ===
eth2 length=20 count=1
eth2 length=64 count=6
=== CAPTURE STATUS ===
7 packets captured
7 packets received by filter
0 packets dropped by kernel
```

## Interpretation and boundaries

- **Egress wire-format proof: PASS.** The packet sequence in the capture is **six 64-byte UDP payloads followed by the single 20-byte original**. All captured on the **physical OpenWrt WAN interface `eth2 Out`**, source `192.168.80.236:48758`, destination `74.125.250.129:19302`; no observed `lo In` FakeIP path for this test. The number/size/order coincide exactly with the user's youtubeUnblock Telegram UDP fake configuration `udp-fake-seq-len=6`, `udp-fake-len=64`, `udp-stun-filter=on`, `udp-mode=fake`. Combined with registered queue 537 and upstream youtubeUnblock STUN classifier/fake emitter, this is **strong practical confirmation of the installed output behavior**. Because packet bodies and process attribution were not inspected, do not pretend there is cryptographic proof of packet generator identity.
- **Queue counter:** 10386→10394, delta **+8** (global rule counter, may contain traffic beyond the single probe; cannot map 8 directly to seven observed packets or six fakes). No negative assertion about unrelated traffic.
- **No response:** Python received **`RESPONSE=TIMEOUT` after two seconds**. This is not evidence of Google STUN server receipt, end-to-end reachability, or DPI bypass. An outbound interface capture itself cannot prove packets passed the external router `192.168.80.1` or reached a remote host.
- **FakeIP issue isolated for this test:** Public IP `74.125.250.129` was obtained via `drill @192.168.1.140`; prior `drill @127.0.0.1` returned Podkop FakeIP `198.18.0.10` and loopback `12×64+1×20`. Neither changing DNS nor disabling Podkop was necessary.
- **Protocol separation:** This synthetic STUN20 does **not** validate actual Windows/Android Telegram voice calls using `GOST SOCKS5 :1070`. Pinned `tgcalls_cli` uses **40-byte non-STUN Reflector Hello**, so its existing media-success via pfSense and failure via OPNsense cannot be attributed to this STUN profile, and blindly copying `6×64` into native non-STUN Strategy #4 is unwarranted.
- **No more equivalent OpenWrt STUN TX testing is needed.** STUN fake/wire-output property has been confirmed. The remaining priority is the separate non-STUN native OPNsense media blocker.

## Next one-factor OPNsense experiment (not yet executed)

As already specified in the [reference architecture](../../architecture/TELEGRAM_OPENWRT_PROXY_UDP_REFERENCE.md), isolate the effect of the **ordinary non-STUN Telegram Strategy #4** by a single controlled pinned `tgcalls_cli` run via OPNsense `.1.2` with **only Strategy #4's fake disabled** temporarily in GUI, native Voice STUN #1 untouched, routes/NAT/PF/firewall/proxies unchanged; verify current effective runtime and WAN capture before interpreting output; restore Strategy #4 via GUI. On OPNsense captured WAN, original 40B Hello should remain, 16B fake packets should be absent if effect isolation succeeded. Requires safe owner-coordinated protocol, no handwaving rollback or silent changes. This would isolate injected non-STUN fakes but a negative call still does not localize where blocking occurs. No need for a real Telegram interlocutor.

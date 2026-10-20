# 2026-10-20 — GOST SOCKS5 UDP accepted, STUN WAN fake 6×64; direct tgcalls repeats fail

**Scope:** owner-live OpenWrt GOST UCI and init-script inspection, SOCKS5 UDP ASSOCIATE control, one UDP/STUN20 sent through GOST SOCKS5 and captured on OpenWrt physical egress, on-device OPNsense Squid ACL inventory, one additional pinned direct-UDP `tgcalls_cli` through each OPNsense and OpenWrt gateway, and TNAS `/32` route restoration. All observations are scoped to the installed systems on 20 October 2026; not a production Telegram-audio test. Credentials from source UCI have been intentionally omitted.

## Important topology and isolation

- TNAS `192.168.1.100` Docker `tgvoice-lab`, network mode `host`, binary `/results/tgcalls_cli` SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`, fixed reflector `91.108.13.10:596`, two Caller/Callee instances and 15-second duration. **This binary's known reflector mode sends native direct non-STUN UDP; it is not a Telegram SOCKS5 or HTTP-CONNECT client.** No proof has been shown that changing GOST UDP, Podkop UDP-over-TCP, or Squid SSLPorts alters its route/transport.
- pfSense `192.168.1.140` previous same binary/reflector direct-UDP 15-second test resulted in both Established, `Call established=yes` at 1.561s, BWE nonzero, exit0 and route restoration. This proves a viable direct UDP route at that test time, **not** that Squid forwarded the lab UDP through the remote HTTP parent. There is no simultaneous pfSense LAN/WAN capture yet.
- OPNsense `192.168.1.2` intended Telegram selected TCP/TLS path via remote parent is separate from native Zapret2 UDP through WAN `vtnet1`; OpenWrt `192.168.1.236` intended real Telegram client uses an **explicit SOCKS5** application proxy `:1070`. Lab direct-route changes do not exercise that proxy.

## GOST `universal_lan` — exact protocol distinction

The operator's `/etc/config/gost` contains three independently enabled instances; the only modified section was `universal_lan`:
```text
config gost 'universal_lan'
    option enable '1'
    option listen '0.0.0.0:1070?udp=true'
    option mode 'auto'
    option log_level 'error'
```
The `main` instance uses local SOCKS5 `127.0.0.1:1088?dns=0` with remote HTTP parent `185.203.117.88:33128?keepalive=true`; another authenticated SOCKS listener exists at `:1050`. **No credential values or source credential-bearing upstream URL are recorded.**

Owner-supplied `/etc/init.d/gost` uses `config_get listen/mode/upstream` and starts `-L ${mode}://${listen}`, with `-F ${upstream}` only where upstream exists; thus for `universal_lan` the effective argument is intended as `-L auto://0.0.0.0:1070?udp=true` and **no parent `-F` is assigned to that section**. The actual live GOST PID arguments were not captured, but a successful SOCKS5 UDP ASSOCIATE on the same port proves effective UDP support.

Prior to enabling UDP (no `udp` key), the owner received:
```text
SOCKS_GREETING=0500
UDP_ASSOCIATE_REPLY=05020001
UDP_RELAY=0.0.0.0:0
UDP_ASSOCIATE_STATUS=2
UDP_ASSOCIATE=REJECTED
```
After setting `?udp=true` and applying the GOST configuration, with `mode=auto` preserved:
```text
SOCKS_GREETING=0500
UDP_ASSOCIATE_REPLY=05000001
UDP_RELAY=192.168.1.236:36797
UDP_ASSOCIATE_STATUS=0
UDP_ASSOCIATE=ACCEPTED
```
The returned UDP relay port is **per-association ephemeral**. This proves GOST SOCKS5 negotiation works, **not** that the actual Telegram client uses UDP ASSOCIATE for media.

## One headless UDP/STUN20 through SOCKS5 GOST

A Python SOCKS5 client on OpenWrt opened a *new* TCP UDP ASSOCIATE to `192.168.1.236:1070`, kept the TCP control association open, and sent **one SOCKS5-encapsulated 20-byte STUN Binding Request** in a 30-byte SOCKS UDP request to numeric public `74.125.250.129:19302`. A simultaneous bounded `tcpdump -i any` on OpenWrt captured the following `eth2 Out` IP/UDP payload sizes:
```text
SOCKS_GREETING=0500
UDP_ASSOCIATE=ACCEPTED
UDP_RELAY=192.168.1.236:52131
SOCKS_UDP_BYTES_SENT=30
ORIGINAL_STUN_BYTES=20
SOCKS_UDP_RESPONSE=TIMEOUT
ETH2_OUT_TOTAL=7
ETH2_OUT_UDP64=6
ETH2_OUT_STUN20=1
0 packets dropped by kernel
TEST_RC=0
```
All seven egress packets used source `192.168.80.236:56664`, destination `74.125.250.129:19302`. The original STUN20 follows the six fake-shaped UDP64 frames. This **directly confirms packet egress through the GOST SOCKS5 association and configured youtubeUnblock-like 6×64 packet transformation on OpenWrt egress**; it does **not** prove that the server received/replied, end-to-end audio works, the Telegram client uses this transport, or the internal precise NFQUEUE path for every datagram. In particular, **`SOCKS_UDP_RESPONSE=TIMEOUT`**, so no STUN_RX.

Earlier separate OpenWrt-origin (not SOCKS) direct STUN20 `eth2 Out` observation was also 6×UDP64 + 1×UDP20, so the new proof is specifically **application-layer SOCKS UDP source**, not merely a repeat of the same origin.

## OPNsense Squid 6.14: active generated ACL inventory, not media

Owner supplied a read-only filter of `/usr/local/etc/squid/squid.conf`:
```text
Squid Cache: Version 6.14
63:acl SSL_ports port 443
64:acl SSL_ports port 563
65:acl SSL_ports port 80
66:acl SSL_ports port 1194
67:acl SSL_ports port 1195
68:acl SSL_ports port 3500
69:acl SSL_ports port 5222
70:acl SSL_ports port 8886
71:acl SSL_ports port 9411
80:acl Safe_ports port 1025-65535
85:acl Safe_ports port 563
115:http_access deny !Safe_ports
118:http_access deny CONNECT !SSL_ports
146:http_access deny all
```
`pgrep -fl squid` showed a running Squid parent, worker processes and `security_file_certgen` helpers. The initial assistant AWK listing script failed with syntax errors, so it **did not inspect `cache_peer`, `cache_peer_access`, `never_direct`, persistent-connection directives, or a live CONNECT destination**; the later grep only establishes the listed ACLs. **563 is currently in both ACLs, not proven used by any Telegram tunnel.** Configuration-only hypotheses about `client_persistent_connections`, `server_persistent_connections`, `no-delay`, `no-query`, `proxy-only`, `connection-auth=off` or extra SSL ports are untested and not causal findings. Some Safe_ports allow 563 implicitly through 1025–65535 as well. An HTTP CONNECT ACL **cannot by itself tunnel arbitrary direct UDP/596**.

## Two more pinned 15-second direct UDP reflector calls

**OPNsense route (no route mutation):**
```text
TNAS_ROUTE=91.108.13.10 from 192.168.1.100 via 192.168.1.2 dev ovs_eth1
Caller state: Reconnecting
Callee state: Reconnecting
Call established: no
BWE non-zero: no
TGCALLS_EXIT=1
```
No simultaneous packet capture accompanied this *new* rerun. The previous OPNsense captures already demonstrated the exact fake-ON and fake-OFF outgoing original/fake mix, with no WAN incoming UDP.

**Direct route through OpenWrt .1.236 (not SOCKS):** one guarded TNAS test began from
`91.108.13.10 via 192.168.1.2 dev ovs_eth1 proto dhcp src 192.168.1.100 metric 1024`;
verified `.1.236` on-link; replaced **only** `91.108.13.10/32` by `via 192.168.1.236 dev ovs_eth1 proto static src 192.168.1.100 metric 1024`, checked `OPENWRT_ROUTE=PASS`, ran same pinned binary:
```text
Duration: 15s
Caller state: Reconnecting
Callee state: Reconnecting
Call established: no
BWE non-zero: no
TGCALLS_EXIT=1
=== RESTORE ORIGINAL ROUTE ===
RESTORE=PASS
FINAL_EXIT=1
REMOTE_SSH_EXIT=1
```
**RESTORE PASS** is distinct from failed call exit1. This test has **no OpenWrt capture**, so it does not verify forwarding/NAT or youtubeUnblock participation in the direct non-STUN Hello. Crucially, toggling GOST `udp=true` cannot be credited or blamed for this result: there is no SOCKS5 use in `tgcalls_cli`. The owner also tried setting **Podkop “UDP through TCP”** and saw **the same failed call**; whether the switch remains enabled was not recorded, and the direct generator did not show an association with Podkop. Do **not** record this as a demonstrated failure of Podkop encapsulation or infer a persistent intended toggle value.

## Next single diagnostic: simultaneous pfSense forwarding wire proof

Before any changes, **read-only identify** pfSense `192.168.1.140` physical LAN/WAN interfaces, source-route to `91.108.13.10` and remote HTTP parent, and actual NAT egress ownership. Then choose a **single 15-second same-pinned-binary direct UDP run** through pfSense `192.168.1.140` while capturing at both pfSense LAN/WAN; compare:

1. `192.168.1.100 -> 91.108.13.10:596` on LAN; WAN destination and actual UDP source after NAT; both outbound original40 and return direction;
2. Any pfSense-initiated TCP to parent `185.203.117.88:33128` **during the same window**; do not assume overlap means it transported the UDP;
3. Actual `91.108.13.10:596` packets with PF state/NAT source if available. If the WAN destination is still Telegram and replies arrive, that would show **direct UDP forwarding** despite selected HTTPS being sent to the parent. If no UDP leaves and another documented tunnel path exists, investigate *that* explicitly rather than assuming Squid translates UDP into HTTP.

A source-filtered `tcpdump` of only laboratory endpoint traffic and parent connection metadata is the proposed test. Do not capture unrelated user payloads, copy proxy credentials or include raw external client IDs in public docs. Ensure the temporary TNAS `/32` route restores to `.1.2` under verified trap; no pfSense/OpenWrt/OPNsense firewall, NAT, proxy, IPFW, Podkop, youtubeUnblock or default-route mutations permitted. **Do not conflate pfSense positive direct-UDP `MEDIA_PASS` with a real Telegram-over-SOCKS5 CALL_PASS.**

**Docs only: `VERSION` and `PLUGIN_REVISION` remain unchanged at `v0.5.5_7`.**

# 20 October 2026 — native Telegram reflector TTL7 vs original Strategy #4: owner-live A/B

**Scope and proof level:** owner-supplied OPNsense root console and bounded WAN packet capture on installed `os-zapret2-restyle-0.5.5_7`, target `91.108.13.10:596`, same external WAN `vtnet1` and Docker `tgcalls_cli` 13.0.0. **No Telegram reflector RX, call or media success.** Both runs used ordinary `UDP 596–599`, `payload=unknown` Strategy #4 (not native Voice STUN #1); two 16-byte zero fakes + 40-byte original per Hello.

| Invariant / result | TTL7 experiment (recorded earlier) | Original/no-TTL control (fresh 11:43 appliance time) |
|---|---|---|
| GUI/effective action | `fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2:ip_ttl=7` | `fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2` |
| Active runtime preflight | TTL7 present in `runtime-v2/traffic.conf` | `grep -Fxq` returned `ORIGINAL_STRATEGY=PASS` |
| Fake WAN UDP | 120 packets, 16-byte payload, **TTL=7** | 120 packets, 16-byte payload, **TTL=63** |
| Original WAN UDP | 60 packets, 40-byte payload, TTL=63 | 60 packets, 40-byte payload, TTL=63 |
| WAN ordering in sample | fake → fake → original | fake → fake → original |
| Sample checksum | `[udp sum ok]` | `[udp sum ok]` |
| UDP inbound from `91.108.13.10:596` | 0 | **0** |
| IPFW rule 19000 | `60 4080` | `60 4080` |
| Caller/Callee | Reconnecting / Reconnecting | Reconnecting / Reconnecting |
| `Call established`, `BWE non-zero` | no / no | **no / no** |
| `TGCALLS_EXIT` | 1 | **1** |
| Overall Zapret status | running | running |

The owner ran a second TTL7 check after configuring HTTP proxy support; it again produced **120 fake TTL7 + 60 original TTL63, UDP RX 0, call=no** (owner live ~08:54). This is repeat evidence of the wire change and unchanged negative outcome, **not** proof the proxy controls UDP.

The **fresh no-TTL control** uses OPNsense `vtnet1` capture at ~11:43:56 local appliance time and PCAP `/tmp/tgvoice-no-ttl.56Oz9o/wan.pcap`, retained **only on the owner's OPNsense**. One bounded 15s `/results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15` run used TNAS `192.168.1.100`, with route guard `via 192.168.1.2 dev ovs_eth1`. The caller and callee both remained Reconnecting. `SSH_EXIT=0` means the shell completed; `TGCALLS_EXIT=1` is the CLI failure. The capture for this run filtered UDP only, so **no statement about ICMP** can be deduced.

## Fresh HTTP proxy and endpoint-list observations (independent from UDP)

- Owner fetched `https://core.telegram.org/getReflectorList` through the verified sing-box `socks5h://127.0.0.1:1080` and also via pfSense: HTTP 200; **616 records**, including **all four `91.108.13.10:596–599`**. Thus this test IP:port **is in the official list** at the observation time. Membership is not a UDP reply/liveness proof.
- The prior lab TCP policy `sing-box :1080 → Squid :3130 → parent 185.203.117.88:33128` yielded HTTP 200 and Squid `FIRSTUP_PARENT`. On OPNsense, **ordinary explicit Squid listener** `http://192.168.1.2:3128` (not intercept-only `127.0.0.1:3128`) gave `curl` HTTP200 and FreeBSD `fetch` EXIT0 for reflector list, with parent shown in access.log.
- Configd proxy support created `/usr/local/opnsense/service/conf/configd.conf.d/proxy.conf` using `http://192.168.1.2:3128`. After `service configd restart`, `configctl configd environment` reported HTTP_PROXY, HTTPS_PROXY, http_proxy, https_proxy and NO_PROXY/no_proxy variables; `configctl proxy status`, sing-box and zapret remained running. This **does not** automatically proxy interactive shell or all router daemons; no corresponding pkg/console permanent setting is proven.
- None of those TCP/HTTPS observations test or redirect the reflector CLI's direct **UDP** media; they do not attribute the UDP failure to proxy services.

## Decision and next research gate

**Completed control:** changing *only fake TTL* between 7 and default TTL63 is observable and repeatable on WAN; **neither** produced a UDP reply or media. No sweep of more TTLs, no blind repeats of A2/A3a, and no claim about DPI position or Telegram relay validity.

**One bounded next objective:** qualify **actual UDP reflector responsiveness** on a genuinely independent viable outbound path for the *same pinned protocol/endpoint* (or identify a source-validated control with a known working responder and accepted reply). Existing pfSense **HTTPS** list success does not prove that pfSense UDP works, and the old `192.168.1.140` path must not be reused as an assumed working route. Only after such an independent control should a new candidate trial be designed; do not change native STUN profile #1, OPNsense default gateway, IPFW, proxy or routes in advance. Document the particular comparator and observe a correlated reply/READY, not just WAN egress.

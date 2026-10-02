# 2026-10-02 — seven failed real calls through OPNsense; owner-reported calls connect via alternate Windows gateway

**Status:** OWNER-LIVE ROUTING A/B OBSERVATION · SEVEN FAILED OPNsense-GATEWAY CALLS · EXACT LAN/WAN PCAP CORRELATION · **NO CURRENT UDP MEDIA PASS**
**Related earlier first call:** [October 2 first real P2P-disabled audible call and original UDP-only capture](2026-10-02-real-telegram-windows-android-p2p-disabled-call.md).
**Operational policy / packet path:** [Telegram traffic policy](../../architecture/TELEGRAM_TRAFFIC_POLICY.md), [GUI/helper/PF/NAT audit](../../architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md).
**Original material:** owner-supplied plaintext transcript of Windows `Find-NetRoute`/`route print -4`, plus **14 raw PCAPs** (`tgvoice-real-call2` through `call8`, LAN and WAN). The source PCAPs contain real network metadata and potentially call-related payloads and **are deliberately not committed to this public repository**. SHA-256 values identify the owner's private originals.

## Owner-observed A/B result, with precisely limited attribution

The owner ran numerous real Telegram call attempts; **all seven captured attempts (call2–call8) were unsuccessful at establishing the voice call** while the Windows machine used `192.168.1.107` on `Ethernet 6`, with **`192.168.1.2` as its only IPv4 default gateway**. The Telegram application itself connected but voice calls did **not** establish. The owner had removed the Telegram proxy for the controlled baseline before the series, but subsequent individual Telegram proxy-setting changes were **not supplied as independent per-call notes**; see observed TCP paths below. No successful audio claim is made for calls 2–8.

The owner then restored the previous dual-interface configuration. Their second `Find-NetRoute` snapshot selected Windows `192.168.3.81` on `Ethernet 7`, IPv4 default `192.168.3.140` (metric 15), **in preference to** the still-present `192.168.1.2` default (metric 281) on `192.168.1.107`. The owner reports that **real voice calls then started connecting**. This is a **positive owner-observed alternate-route control**, but no PCAP or process-level media attribution from a *successful* `192.168.3.140` call was supplied in the present upload. In particular, it is **not yet proof that UDP rather than TCP was the successful media transport** and **not yet proof which specific provider/path dropped replies**. The default-gateway change is verified by Windows route snapshots. The selected application proxy setting *at the moment of the subsequent successful calls* is not separately captured, so do not claim an otherwise perfectly controlled single-variable A/B test.

**Newer observation supersedes neither the earlier first call nor the approved fixed-reflector acceptance gates.** In the initial [call1 evidence](2026-10-02-real-telegram-windows-android-p2p-disabled-call.md), sound was good while the Windows default route selected the other gateway, but 99 *specific* Telegram UDP packets were demonstrably sent to OPNsense's Ethernet MAC and traversed its WAN. Both can be simultaneously true; the route of other/unobserved media was unknown. Call2–8 now provide the deliberate `192.168.1.2`-gateway failure series. The independently qualified current TNAS `tgcalls_cli` fixed-reflector `MEDIA_PASS` through OPNsense remains open.

## Windows route evidence supplied by owner

| Configuration | Source / selected interface | Selected default route | Owner outcome |
|---|---|---|---|
| **A — only OPNsense gateway for IPv4** | `192.168.1.107`, interface index 30, `Ethernet 6`, manual address | `0.0.0.0/0 via 192.168.1.2`; `Find-NetRoute` for `91.108.9.88` and `91.108.9.100` both resolved to it; active `route print -4` had no other IPv4 default | Telegram connected; captured voice calls 2–8 failed to establish |
| **B — restored other preferred gateway** | `192.168.3.81`, interface index 24, `Ethernet 7`, DHCP address | `0.0.0.0/0 via 192.168.3.140` metric 15; `192.168.1.2` default remains at metric 281 | Owner reports voice calls resumed establishing; **no matching successful-call capture** |

The earlier command `Get-NetRoute -AddressFamily IPv6 -DestinationPrefix ::/0` returned no default IPv6 route during controlled Windows setup. Secondary link-local/on-link networks appeared in the IPv4 route list but did not supply another IPv4 default while A was active. **Do not remove permanent Windows routes or modify the default gateway merely because the owner supplied this A/B evidence.** Nothing on any live device was changed by the documentation work.

## Per-capture packet analysis

All seven LAN captures use the controlled Windows client's OPNsense-facing NIC; all seven WAN captures are from the same OPNsense WAN, filtering for TCP/UDP (excluding DNS/53); snaplen 160 means some large TCP payloads may be truncated, but all relevant 28- and 40-byte UDP originals and 16-byte fakes were fully present. Across *each* pair:

- Every Telegram UDP original observed on LAN also appeared with **matching full UDP payload bytes** on WAN after source NAT. All the LAN Telegram UDP frames targeted **the same OPNsense LAN destination MAC**. This shows correct Windows → OPNsense L2 forwarding for those packets, and packets exiting OPNsense WAN; it does **not** prove upstream server receipt.
- Reflector-control packets are 40-byte non-STUN Hello-like datagrams sent repeatedly to varying `91.108.9.*:596–599` endpoints. No current STUN-only profile changes their payload in these captures.
- When 28-byte STUN probes were present to another `91.108.9.*:1400` endpoint, WAN contained exactly **two additional 16-byte all-zero payload packets per STUN probe**, consistent with the previously observed `stun-zero-fake-repeats-2` active helper. This is packet generation, **not verified network effectiveness**.
- **No inbound UDP from the observed Telegram endpoint range** was captured on WAN or forwarded back to this Windows client on LAN in any of the seven call windows. Captures do include occasional unrelated incoming WAN UDP/NTP, showing they did not capture *outbound-only* traffic by definition. The `tcp or udp` BPF filter would not match non-initial IP fragments lacking a UDP header; no claim is made about all IP protocols or unobserved paths.

| Attempt | LAN capture UTC interval | Reflector Hello (40 B) | STUN (28 B) | Extra WAN zero16 fakes | Inbound observed Telegram UDP | Telegram target(s) |
|---|---|---:|---:|---:|---:|---|
| 2 | 12:11:18–12:11:59 | 41 | 7 | 14 | **0** | `91.108.9.25:598`, `91.108.9.114:1400` |
| 3 | 12:14:19–12:15:35 | 41 | 7 | 14 | **0** | `91.108.9.88:597`, `91.108.9.22:1400` |
| 4 | 12:16:13–12:16:53 | 50 | 8 | 16 | **0** | `91.108.9.57:599`, `91.108.9.73:1400` |
| 5 | 12:17:37–12:18:21 | 41 | 7 | 14 | **0** | `91.108.9.8:598`, `91.108.9.117:1400` |
| 6 | 12:18:52–12:19:29 | 41 | 0 | 0 | **0** | `91.108.9.9:596` |
| 7 | 12:20:14–12:22:11 | 90 | 9 | 18 | **0** | `91.108.9.83:598`, `91.108.9.99:1400` |
| 8 | 12:22:27–12:23:02 | 41 | 7 | 14 | **0** | `91.108.9.103:597`, `91.108.9.101:1400` |
| **Total** | — | **345** | **45** | **90** | **0** | varying endpoints |

There were **390 original Telegram UDP datagrams** corresponding byte-for-byte between LAN and WAN; the additional **90** zero16 WAN payloads total **480 outgoing Telegram-destination UDP datagrams**. The original IPv4 lengths sum to **25,980 bytes** (`345 × (20+8+40) + 45 × (20+8+28)`) in this PCAP-level accounting; this is a derived figure, **not a claimed contemporaneous IPFW-counter delta** (no full per-call before/after IPFW snapshot was included). A tempting but invalid conclusion would be that exactly 390 packets must appear in any later live IPFW counter regardless of previous traffic or different rule state.

**Call 6 is a useful naturally occurring control:** the capture contained 41 non-STUN originals but **no** STUN probes and thus **no** observed STUN fake packets, yet this call also failed by the owner's report. Hence one cannot attribute all failures *solely* to the currently generated STUN fakes.

## Captured WAN checksum qualification — all 480 packets valid

After preparing the complete 14-PCAP comparison, the owner-provided raw Ethernet/IPv4 frames were additionally checked at **both checksum levels**, not merely matched by payload. For every original LAN Telegram UDP datagram (28- or 40-byte payload), each corresponding NATed WAN UDP datagram, and each additional 16-byte zero-payload WAN fake, the complete UDP datagram was present within snaplen 160. A fresh checksum was computed over the actual captured IPv4 pseudoheader (including the **post-NAT source**), UDP header and payload, using IPv4 one's-complement arithmetic. The IPv4 header checksum was independently validated on the captured WAN datagram.

| Call | Original WAN Telegram UDP | Extra zero16 WAN fakes | Valid WAN IPv4 header checksum | Valid WAN UDP checksum |
|---|---:|---:|---:|---:|
| 2 | 48 | 14 | **62 / 62** | **62 / 62** |
| 3 | 48 | 14 | **62 / 62** | **62 / 62** |
| 4 | 58 | 16 | **74 / 74** | **74 / 74** |
| 5 | 48 | 14 | **62 / 62** | **62 / 62** |
| 6 | 41 | 0 | **41 / 41** | **41 / 41** |
| 7 | 99 | 18 | **117 / 117** | **117 / 117** |
| 8 | 48 | 14 | **62 / 62** | **62 / 62** |
| **Total** | **390** | **90** | **480 / 480** | **480 / 480** |

All **390 original LAN UDP** datagrams also had valid recorded UDP checksums. The packet evidence therefore does **not** show the local UDP-checksum corruption that had complicated September's experimental post-NAT **fragmentation**. These present real-call datagrams were unfragmented; **do not extrapolate this validation to earlier fragmentation experiments, all possible offload/wire behaviors, or remote server receipt**. Valid captured outbound checksums plus zero captured inbound Telegram UDP do not uniquely identify ISP filtering, Telegram server refusal or another route/transport selection mechanism. They *do* remove any observed invalid WAN checksum as an explanation for these particular packets.

## Simultaneously observed TCP paths: do not assume each was Telegram media

LAN and WAN TCP were captured concurrently this time. WAN traffic to and from the configured external Squid parent `185.203.117.88:33128` was active during each observed UDP-attempt window, including inbound TCP payload. It is a useful sign that OPNsense's **general TCP parent path was not completely silent** while voice setup failed, but the WAN capture includes other LAN and router traffic. **Without application/process-to-flow evidence or Squid access logs, this is not proof any particular TCP byte was Telegram signaling or audio.**

| Attempt(s) | Distinguishing *concurrent LAN TCP* pattern | Bound of inference |
|---|---|---|
| 2–4 | bidirectional TCP with `149.154.167.51:80` (and `91.105.192.100:80`) | Addresses/ports match Telegram-like direct traffic; possible local transparent Squid handling. Proxy-selection mechanism was not logged per call. |
| 5 | high-volume bidirectional TCP on `192.168.1.2:3128` | Consistent with the configured Squid explicit HTTP proxy being active; do not assign process identity from PCAP alone. |
| 6–8 | bidirectional TCP on `192.168.1.2:1080` | Consistent with sing-box SOCKS5 being used; cannot prove SOCKS UDP ASSOCIATE from TCP traffic. |
| 2–8 WAN | simultaneous bidirectional TCP `192.168.80.251 ↔ 185.203.117.88:33128` | Indicates active parent-proxy sessions but not per-call proof of media, completeness or an exact 1:1 mapping to LAN flows. |

Across all these different observed TCP patterns, **the same UDP failure signature persists**: originals leave OPNsense, optional zero16 STUN fakes leave, **no Telegram UDP replies on the captured WAN** and the owner reports no established voice call. This is why repeatedly reconfiguring an already-present TCP parent or DNS setup **without evidence** is not justified by these PCAPs.

The observations do **not** distinguish:
- Upstream provider filtering, destination-side rejection/selection, NAT/hook/checksum behavior, an invalid experimental STUN fake, or Telegram selecting a different path; a separate **captured** working control is required before assigning root cause.
- Whether changing the Windows default gateway alone explains recovery: the exact Telegram in-app proxy state of the positive owner control was not independently recorded.
- Whether any successful real call uses **UDP media** rather than TCP fallback; the first good-audio capture had no Telegram UDP reply.

## Exact private raw-capture identity

**Store these originals off-repository.** File names include a download suffix `(2)`; SHA-256 is computed from each *uploaded byte-for-byte PCAP*. Capture packet counts below reflect parsed Ethernet/IPv4 frames and can differ from tcpdump's total where a file also contains non-IPv4 frames.

| Attempt | LAN PCAP (bytes / SHA-256) | WAN PCAP (bytes / SHA-256) |
|---|---|---|
| 2 | 238245 · `96eb481c658856af90c4e083fdaa0f212930392e1547d1d74b702606a63abca3` | 281102 · `2566e9b3d18b6b587aa59e31b79db656b2a56439c561d15b2d113f5c2946b390` |
| 3 | 254056 · `25881a945c2338d8188789727cc04a115e053802a988533b9ae124a201c111fd` | 304983 · `2d186ce00e8d73b3854ddcde8bebec5c9fff37980a0cc51c42109c962236fc3f` |
| 4 | 136065 · `a3a2f74573ccef8b457aa82546869067bbb789ff3aea80840ce7ea9ce8ff4b52` | 139368 · `49f58a3d1d7bca66c6f1b1901d8fedd372f8f964ffa4d8b2278406ecc392ae7c` |
| 5 | 308180 · `7b1c8a7e60f484d847d5ab644d08ea83693ffc30e8bcfe18c80a8cd1487dd608` | 415552 · `04b2206fe6b4b12bcd319fceb6a5b62fb11305fa00761f7c20089ca13276e97c` |
| 6 | 91675 · `cb585958d453168bc01e4cb7d047d5034a2f8f7295effd02729348b76e03bc68` | 72627 · `4acf2d807d2f3c9a6a58fa55bc64b2e40df111e025d8eb13b944bfd918f29c6c` |
| 7 | 250166 · `ec1efa5b6767025d75fb956f88a1408f311602dc590ec7530915338caf6f8c01` | 182539 · `69d7891cc77ba560cce705964b94d40f58f1918b9f4d861e31c1aa94de824023` |
| 8 | 75713 · `68f66fc167706e71261be6d762e63a76bf31fc5cfdd4c84ffda305ff973ee605` | 73985 · `d22a887f8d89f1cda7f8ae0d9ae95c6171d97d586f4e16b650637a72c4d773e8` |

## Next bounded investigation — owner-live control before a new strategy sweep

**First capture one *successful* real Windows/Android call through the restored `192.168.3.140` preferred gateway, P2P settings and Telegram in-app proxy mode explicitly recorded.** Keep other selected conditions as close as feasible to an unsuccessful `192.168.1.2` call. Prefer a short Windows-side capture limited to the Telegram process's destinations and both UDP/TCP (or a capture on the actual `192.168.3.140` path), plus one bounded OPNsense check for cross-path attribution. Record establishment and whether audio is demonstrably bidirectional. Then determine whether a successful control has any Telegram UDP responses and which IP/port, or whether it uses TCP fallback.

Only after a matched **working** control can we isolate what `192.168.1.2` loses (transport, NAT checksum/order, traffic selection, or upstream response). Do not change PFIL hook order, broad IPFW diversion, working Squid parent settings, existing sing-box or install one-shot Voice autostart solely because UDP replies are absent. The latter remains an independent **not-yet-implemented** lab reboot task; TNAS routes and container stay manual-only per owner decision.

Current stage gates remain **OPEN** for repeatable current-oracle `MEDIA_PASS` and a real-call **UDP** `CALL_PASS`. Owner-reported successful alternative-gateway connection is preserved as evidence without prematurely claiming either gate.

# 2026-10-20 — Owner-reported working pfSense / OpenWrt / Podkop / youtubeUnblock topology and next test

**Scope:** New owner-supplied architecture description + GUI screenshots, compared with upstream `Waujito/youtubeUnblock` README. These are not direct packet-capture proof that youtubeUnblock processed the pinned reflector Hello. **OpenWrt .236 control not run yet.**

## Owner topology

- TNAS host `192.168.1.100` contains an **OpenWrt VM** at `192.168.1.236` (not a Docker container). TNAS interface `ovs_eth1=192.168.1.100/24` shares IPv4 LAN, so `.236` is a *candidate direct on-link next-hop*; its forwarding/NAT/routes/firewall are not yet verified.
- pfSense `192.168.1.140` has Squid and routes Telegram-targeted traffic to the OpenWrt VM according to owner description, but exact TCP vs UDP policy-routing / NAT rules have **not** yet been supplied. HTTP Squid alone does not forward arbitrary UDP.
- OpenWrt Podkop handles Telegram TCP/TLS via the same external Squid parent `185.203.117.88:33128` (owner report); youtubeUnblock handles selected UDP. The correct original user objective is to get **local native Zapret2** UDP via OPNsense same-ISP WAN working, not to permanently move voice service to .236.
- Additional former proposed gateway `192.168.4.1`: OPNsense `route -n get` shows via `192.168.1.140`; strict SSH to root@.4.1 fails **before authentication** because no known ED25519 host key (SSH exit255). Do not disable strict host checking by default or claim the host is inaccessible. This gateway is not qualified as independent until source/connection is known.

## Owner screenshots of OpenWrt youtubeUnblock Telegram section

| UI setting | Captured selection |
|---|---|
| QUIC drop | unchecked |
| UDP mode | `fake` |
| UDP faking strategy | `none` |
| UDP fake seq len | `6` |
| UDP fake len | `64` |
| UDP dport filter | empty |
| UDP stun filter | checked |
| UDP QUIC filter | `disabled` |
| SNI domains | many Telegram-related domains including `t.me`, `telegram.org`, `telegram.com`, etc.; screenshots partial and do not establish exact installed complete list |

Upstream source [README](https://github.com/Waujito/youtubeUnblock/blob/main/README.md) documents matching `--udp-mode=fake`, `--udp-fake-seq-len=6`, `--udp-fake-len=64`, `--udp-stun-filter`, and `--udp-faking-strategy=none`; [author issue #265](https://github.com/Waujito/youtubeUnblock/issues/265) discusses Telegram *STUN* calls. Do not equate this to the current ordinary Zapret2 profile `unknown + fake-zero16:repeats=2`. Especially the pinned current `tgcalls_cli` fixed reflector sends **40-byte non-STUN Hello**, without SNI. A STUN-only selector is not proof that youtubeUnblock acts on these Hello packets. Independent routing, firewall, NAT or other traffic matches may account for the positive .140 control.

## Existing successful and failed controls

- Same pinned current engine-13 `tgcalls_cli`, `91.108.13.10:596`: `192.168.1.140` path => both Established, call=yes, BWE nonzero, CLI0 and source-route restore PASS.
- TNAS -> OPNsense `192.168.1.2`: native Voice/ordinary strategy unknown fakes (2 × 16), outgoing originals (60 × 40), WAN incoming UDP 0, call=no. The A/B varies *both* network path and presence/type of fake and cannot yet distinguish DPI/NAT versus fake-induced failure.
- Planned one guarded same-binary/same-endpoint control with direct `91.108.13.10/32 via 192.168.1.236 dev ovs_eth1` on TNAS. Preflight must establish .236 direct on-link and `proto dhcp via 192.168.1.2` original; restore **exact** original route even if Docker call fails. If no call, cannot assert youtubeUnblock failure without OpenWrt forwarding/NAT/queue counters/PCAP. If yes, call/media pass on .236; does **not**, by itself, attribute success to youtubeUnblock.
- **Next architecture question:** How exactly does pfSense send **Telegram UDP (not TCP Squid)** to OpenWrt .236? A readable GUI policy route/NAT/firewall rule or `pfctl` snapshot can distinguish gateway route from TCP CONNECT proxy.

No changes to plugin source, OPNsense runtime/Voice/IPFW/PF/proxy, TNAS default route or installed OpenWrt config are authorized by this note.

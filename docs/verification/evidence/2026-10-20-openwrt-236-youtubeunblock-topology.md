# 2026-10-20 — Owner-reported working pfSense / OpenWrt / Podkop / youtubeUnblock topology and next test

**Scope:** New owner-supplied topology + direct gateway trials, compared with upstream documentation. **Owner has since corrected the earlier pfSense/OpenWrt routing interpretation.** The .236 direct reflector control was performed and failed; see correction below. This does not show youtubeUnblock processed the pinned non-STUN Hello.

## Owner topology

- TNAS host `192.168.1.100` contains an **OpenWrt VM** at `192.168.1.236` (not a Docker container). TNAS interface `ovs_eth1=192.168.1.100/24` shares IPv4 LAN, so `.236` is a *candidate direct on-link next-hop*; its forwarding/NAT/routes/firewall are not yet verified.
- **Superseded earlier hypothesis:** pfSense `192.168.1.140` has Squid with a Telegram TLS hostname ACL selecting external HTTP parent, **not proven to forward UDP to OpenWrt**. The owner gave an explicit correction after the initial report; see below.
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
- **Completed:** direct `91.108.13.10/32 via 192.168.1.236 dev ovs_eth1` was tested. `GATEWAY_ONLINK=PASS`, `OPENWRT_ROUTE=PASS`, 15s pinned current client returned `Call established=no`, `TGCALLS_EXIT=1`, `RESTORE=PASS`. This is not proof that actual Telegram SOCKS proxy mode fails.
- **Next architecture question:** What pfSense routing/NAT path carries **direct reflector UDP**, independently of its Squid HTTP/TLS ACL? Read-only firewall/NAT evidence would distinguish direct gateway UDP from SOCKS/proxy traffic.

No changes to plugin source, OPNsense runtime/Voice/IPFW/PF/proxy, TNAS default route or installed OpenWrt config are authorized by this note.

## OWNER correction and direct OpenWrt control — 2026-10-20 (supersedes earlier topology interpretation)

**New control: FAIL via .1.236.** TNAS pinned `tgcalls_cli` 13.0.0, same binary SHA checked and `91.108.13.10:596`, route switched temporarily to `via 192.168.1.236 dev ovs_eth1` after direct on-link guard, 15s runtime; Caller/Callee Reconnecting, `Call established: no`, `BWE non-zero: no`, `TGCALLS_EXIT=1`, `RESTORE=PASS`, `FINAL_EXIT=0`. There was no packet capture on OpenWrt; this does not establish that .236 forwards/NATs this arbitrary client-origin UDP, or that youtubeUnblock saw the packet.

**Owner corrected an important earlier misstatement:** pfSense `192.168.1.140` Squid uses **TLS hostname ACL** `ssl::server_name "/opt/allow-domains/Services/telegram.lst"`, `cache_peer_access voiceproxy allow telegram_sites`, `never_direct allow telegram_sites`, `ssl_bump splice telegram_sites`, and `cache_peer bgvps.duckdns.org parent 33128 0 ... name=voiceproxy` (same remote proxy `185.203.117.88:33128`). This establishes a configured **TCP/TLS Squid parent selection**, **not** generic Telegram UDP forwarding by Squid into OpenWrt. The former claim that pfSense routes all Telegram UDP to OpenWrt **is withdrawn** unless a specific pfSense firewall/policy-routing observation shows it.

The owner's **real Telegram client** is explicitly configured with SOCKS5 `192.168.1.236:1070` (OpenWrt GOST); this is a crucial difference from the **direct-UDP**, no-SOCKS `tgcalls_cli --mode reflector` harness. The latter does **not** exercise the GOST SOCKS listener and therefore cannot serve as a test of Telegram-with-proxy `1070`.

Owner-supplied OpenWrt `/etc/config/gost`:
- `main`: enabled SOCKS5, local `127.0.0.1:1088?dns=0`, upstream `http://185.203.117.88:33128?keepalive=true`. Chained proxy path intended for selected TCP/TLS traffic.
- `universal_lan`: enabled GOST `mode=auto` on `0.0.0.0:1070`, used explicitly by real Telegram. No explicit upstream is declared in this section; how its outbound packets interact with router policy requires observation.
- `socks_wan`: enabled SOCKS5 on all interfaces at `:1050` with authentication (credentials **not recorded**).
- Podkop MAIN: `Proxy` / URL `socks5://127.0.0.1:1088`, Telegram selected community list, **UDP through TCP unchecked**. Upstream Podkop documentation says this flag must be enabled to encapsulate UDP in a TCP connection; do not claim generic Telegram UDP uses the HTTP parent merely because selected TCP/TLS uses this chain.
- youtubeUnblock GUI Telegram UDP selector as captured previously (STUN, fake 6×64, strategy none). Those selections do not prove its classification/processing of the pinned **40-byte non-STUN** Hello.

### Causal interpretation and next candidate

| Test path | Same pinned client, reflector | Owner result | What it proves |
|---|---|---|---|
| TNAS `/32 via 192.168.1.140` | direct UDP, **no SOCKS client** | `Established`, BWE nonzero, CLI exit 0 | The pinned endpoint and binary are working over this gateway at the observed time. |
| TNAS `/32 via 192.168.1.236` | direct UDP, **no SOCKS client** | Reconnecting, no call, CLI exit 1, restore PASS | This VM was **not a successful arbitrary UDP gateway in this experiment**; not proof about real Telegram's SOCKS path. |
| TNAS `/32 via 192.168.1.2` | direct UDP; ordinary Zapret2 Strategy #4 added 2×16 zero fake to originals | Reconnecting, 0 WAN RX in supplied captures, no call | The negative is confounded by **both different gateway/ISP/NAT and injected fakes**. |

**Next one-factor control to design:** route pinned `tgcalls_cli` through existing OPNsense `.1.2` while temporarily making the *non-STUN ordinary Strategy #4* inactive, with native Voice STUN #1 unchanged. Preflight saved+effective profile, intercept/routing and revert the original profile; confirm on WAN **only original UDP 40-byte Hellos, no fake 16-byte packets** before interpreting caller/callee outcome. This distinguishes effects of fake-injection from effects of the OPNsense path, unlike reusing youtubeUnblock STUN values against a non-STUN harness. Do not disable the entire Zapret2 service, rewrite NAT/IPFW or assume that a no-fake negative locates the DPI drop.

**Open question after this:** On pfSense, which exact UDP route/NAT/egress handles direct traffic from `192.168.1.100` to `91.108.13.10:596`? The supplied Squid ACL does not answer that.

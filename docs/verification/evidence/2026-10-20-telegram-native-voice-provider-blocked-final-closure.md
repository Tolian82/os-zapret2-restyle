# Telegram Voice — owner-authorized closure of direct-provider laboratory testing (20 October 2026)

**Decision:** owner ends all further Telegram Voice tests through this plugin in the present lab because **no working direct-provider media path could be demonstrated** despite repeated bounded experiments. Retain the implemented GUI/Config/STUN and Strategy functionality. **This is a closed negative lab campaign, not a proven universal impossibility of Zapret2, a demonstrated root-cause DPI classification, or a verified successful Telegram voice product claim.** Full release v0.5.6 was explicitly requested after this decision.

## New decisive pfSense read-only evidence

pfSense `192.168.1.140` was previously the only tested successful direct `tgcalls_cli` gateway. New owner-supplied appliance `route -n get 91.108.13.10`:

```text
route to: 91.108.13.10
destination: 91.108.12.0
mask: 255.255.252.0
gateway: 10.1.11.1
interface: ovpnc6
mtu: 1400
flags: <UP,GATEWAY,DONE,STATIC>
```

pfSense `ifconfig -a`: `bridge0 192.168.1.140`, OpenVPN `ovpnc6 10.1.11.2`, default egress `bridge3 192.168.80.100` via `192.168.80.1`. Separate parent proxy destination `185.203.117.88` follows the **default route via bridge3/192.168.80.1**, not the Telegram route to `ovpnc6`. `pfctl -sn` reported `nat on ovpnc6 inet from any to <Telegram> -> 10.1.11.2 port 1024:65535`. Policy-routing precedence and specific PF state for the successful test were not captured, but the **normal FIB route and specific Telegram outbound NAT agree on VPN `ovpnc6`**. The final owner-run:

```text
traceroute to 91.108.13.10, 64 hops max
 1  10.1.11.1 (10.1.11.1)  79.329 ms  78.145 ms  78.166 ms
```

provides corroboration for the VPN next-hop used by pfSense-origin packets. **`traceroute` is not a capture of the TNAS forwarded `tgcalls_cli` flow**, and no simultaneous LAN+VPN packet capture was performed. Consequently one cannot absolutely prove the forwarded lab packets used `ovpnc6` from this alone; but it is strongly supported and invalidates using pfSense's `MEDIA_PASS` as a *same-provider direct UDP Zapret2 bypass* positive control.

## Observed on OPNsense and OpenWrt

- OPNsense `192.168.1.2`, WAN `vtnet1` `192.168.80.251`, default `192.168.80.1`: pinned `tgcalls_cli` two-instance Caller/Callee, reflector `91.108.13.10:596`, repeatedly 15 seconds, `Call established=no`, `BWE non-zero=no`, `TGCALLS_EXIT=1`. **Ordinary Telegram Strategy #4 with 2× zero UDP16 fake per original UDP40:** measured 120 fake + 60 original on WAN, zero incoming reflector datagrams. Selective fake TTL7 vs default TTL established WAN fake TTL control, **but no call**.
- One isolated OPNsense ordinary fake-OFF comparison: `60 original UDP40`, `0 fake UDP16`, WAN RX0, call=no. After this test exact ordinary Strategy #4 restored via GUI to saved Config and effective runtime (`FAKE_RESTORED=YES`, `ACTIVE_FAKE_RESTORED=YES`), `zapret is running`.
- Native Voice profile #1 `--filter-l7=stun --payload=stun` had outgoing synthetic STUN fake/original proof, **no valid incoming STUN response and no successful media**. 40-byte direct `tgcalls_cli` reflector Hello is *non-STUN*, not an exercise of the Voice STUN profile.
- OpenWrt `192.168.1.236` acting as a **direct `/32` gateway** for the same `tgcalls_cli` also failed, `Call established=no`; TNAS route exactly restored to OPNsense `.1.2` (`RESTORE=PASS`). This direct laboratory binary does not use SOCKS5.
- OpenWrt GOST `auto://0.0.0.0:1070?udp=true` enabled SOCKS5 UDP ASSOCIATE (REP00 after previous REP02 denial). One STUN20 sent through actual SOCKS UDP `:1070` resulted in OpenWrt `eth2 Out` exactly **6 UDP64 fake-shaped, one original UDP20**, no STUN response in bounded wait. This is SOCKS outbound transformation proof, **not a real Telegram client voice call**.
- OPNsense Squid 6.14 has `SSL_ports` and `Safe_ports` permitting TCP 563, but no observed `CONNECT` to port 563 and no basis to credit Squid `cache_peer`, persistent connections, `no-delay`, `no-query` or `proxy-only` for the previously successful direct-UDP call.
- Owner tried Podkop `UDP through TCP` and the *direct* reflector remained negative; the generator never exercised GOST/Podkop SOCKS5, so no causal claim about the switch. Its final saved state was not reported; do not change it as part of the release.

## Closure criteria and uncertainty

1. **Installed GUI/config/functionality remain accepted** on `0.5.5_7`: working Strategies Apply, native Voice STUN editor and kernel rule counters. Release `v0.5.6_1` is **packaging/documentation/stage closure**, not a new bypass algorithm or a working Telegram media preset.
2. **Telegram `MEDIA_PASS`/`CALL_PASS`: NOT ACHIEVED on the OPNsense direct-provider path**; no working 2-way voice/audio demonstrated. The ISP-path failure is consistent with blocking/transport limitations; precise upstream cause (DPI, filter, responder behavior, NAT or other network segment) is **not isolated**. Therefore a general theorem “Zapret2 can never bypass Telegram” is unsupported.
3. **pfSense previous MEDIA_PASS is VPN-route-confounded:** route `91.108.12.0/22 via 10.1.11.1 dev ovpnc6`, NAT `<Telegram>` to `10.1.11.2`, first traceroute hop `10.1.11.1`; neither the distant HTTP parent nor its TCP/563 ACL explains direct UDP/596.
4. Owner **explicitly stops new Telegram-related plugin tests** in this campaign. No pfSense LAN/WAN capture, no further synthetic STUN/Reflector/TG-real-call testing, no fake/TTL/fragment sweeps and no route/proxy/VPN changes in this release. Future reopening requires a separately authorized task, new technical basis or proven changed environment; historical testing remains accessible as evidence.
5. This decision **does not delete the existing Voice Transmission GUI or claim other services (Discord/X/SIP/Custom) pass call tests**.

Prior evidence: [GOST SOCKS, direct-route tests](2026-10-20-gost-udp-associate-socks-stun-and-repeated-tgvoice-direct-routes.md), [fake-OFF and restoration](2026-10-20-opnsense-reflector-fake-off-restored-socks-architecture.md), [pfSense MEDIA_PASS](2026-10-20-tgvoice-gateway-140-positive-control.md), [original fake TTL7](2026-10-20-telegram-ttl7-wan-owner-live.md), [OpenWrt STUN](2026-10-20-openwrt-stun-eth2-6x64-wire-proof.md).

**Proof level:** owner-live observations; release publication and Web/pkg repo evidence are separate and are not asserted here before CI/publication.

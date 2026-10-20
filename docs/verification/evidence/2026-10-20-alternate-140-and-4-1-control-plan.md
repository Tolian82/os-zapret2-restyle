# 2026-10-20 — Planned same-endpoint alternate gateway control (NOT YET RUN)

**User-authorized goal:** check both `192.168.1.140` and `192.168.4.1` for current pinned `tgcalls_cli` UDP `91.108.13.10:596` response/media, distinguish direct gateway controls from paths that traverse another gateway.

**Read-only TNAS state observed by owner:**
- TNAS IPv4 `ovs_eth1=192.168.1.100/24`; `ovs_eth0=192.168.192.100/24`; no `192.168.4.0/24` on-link interface.
- Main default via `192.168.1.140 dev ovs_eth1`; exact specific current reflector route `91.108.13.10 via 192.168.1.2 dev ovs_eth1 proto dhcp src 192.168.1.100 metric 1024`.
- `ip -4 route get 192.168.1.140 from 192.168.1.100` selects directly connected `dev ovs_eth1` (no via).
- `ip -4 route get 192.168.4.1 from 192.168.1.100` selects **`via 192.168.1.140 dev ovs_eth1`**. Therefore `192.168.4.1` is NOT a directly reachable L2 next-hop on this TNAS interface and cannot be used in a meaningful single-hop reflector route until the owner identifies its real topology or another suitable source host/interface.

## Ordered controlled tests

1. **First: 192.168.1.140** — from the existing OPNsense→TNAS restricted SSH, preflight exact present reflector route `via 192.168.1.2`, `ovs_eth1` source, link-reachable `.1.140`, host-network `tgvoice-lab`, executable. Route **only** `91.108.13.10/32` temporarily `via 192.168.1.140 dev ovs_eth1 proto static src 192.168.1.100 metric 1024`. Verify `ip -4 route get` selects that gateway. Execute precisely one `timeout -k 5 45 docker exec tgvoice-lab /results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15`, record engine results and exit code. Restore exact original route `via 192.168.1.2 ... proto dhcp ... metric 1024` in remote POSIX-shell EXIT/signal trap plus explicit post-check. This changes no default route and no OPNsense/Squid/sing-box/Zapret2/IPFW. For ~15–20 seconds other TNAS processes using the same reflector destination also take the alternate path. If route, privilege, runtime or restoration validation fails, stop; **do not** silently proceed.
2. **Second: 192.168.4.1** — **HOLD until actual next-hop connectivity is established.** Ask owner whether an alternate host/network interface is directly attached to `192.168.4.0/24` or if `.4.1` is only reachable behind `.1.140`. No speculative `onlink`, IP alias/VLAN, source NAT, bridge, OPNsense gateway changes or `via .4.1` on TNAS `ovs_eth1` without this information.

## Result classification

`Call established=yes`, both peers `Established`, BWE nonzero and CLI exit 0 = positive pinned-reflector media control for the tested network path at the test time. `Call established=no` is a negative call outcome but **not** proof of zero inbound UDP without corresponding capture. One result from either gateway is not automatically comparable if it crosses `.1.140` or uses a different tgcalls version or source. Current engine-13 binary SHA and endpoint must match the 20 October OPNsense tests. Historic 5 September positive control through `.1.140` used a *different* binary and is not current acceptance.

No live alternative-path test has been reported yet. Document owner output before proceeding to `.4.1` or another strategy.

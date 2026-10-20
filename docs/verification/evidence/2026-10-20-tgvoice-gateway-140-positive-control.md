# 2026-10-20 — Owner-live SUCCESS via TNAS gateway 192.168.1.140 (same reflector and binary)

**Status:** **POSITIVE fixed-reflector `MEDIA_PASS` via gateway `192.168.1.140`; OPNsense `192.168.1.2` still unqualified/negative. Route restoration **PASS**. Second requested gateway `192.168.4.1` **NOT YET TESTED**.

Owner executed a single guarded remote POSIX shell from OPNsense (SSH port 9222 to TNAS `192.168.1.100`). First attempt stopped at byte-for-byte route-format comparison **before any mutation**; second corrected attempt normalized whitespace and completed the test and restoration.

## Same-endpoint control and current binary

- TNAS `ovs_eth1 192.168.1.100/24`; Docker `tgvoice-lab` running on **host** networking, actual `/results/tgcalls_cli` hash verified against `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc` in the executed script. Engine log: both peers version `13.0.0`.
- Reflector `91.108.13.10:596`, `--mode reflector`, `--duration 15` seconds, exactly as in failing OPNsense experiments.
- Original TNAS exact route `91.108.13.10 via 192.168.1.2 dev ovs_eth1 proto dhcp src 192.168.1.100 metric 1024`. Successful preflight `ip -4 route get 192.168.1.140 from 192.168.1.100` selected **direct** `dev ovs_eth1`, not via another router.
- Modified **only** destination-specific `91.108.13.10/32` to `via 192.168.1.140 dev ovs_eth1 proto static src 192.168.1.100 metric 1024`. Runtime `ip -4 route get 91.108.13.10 from 192.168.1.100` confirmed **`via 192.168.1.140 dev ovs_eth1`**.

## Actual output

```text
[  1.560] Callee: state -> Established
[  1.763] Caller: state -> Established

=== Call Summary ===
Duration:          15s
Mode:              reflector (91.108.13.10:596)
Caller state:      Established
Callee state:      Established
Call established:  yes (at 1.561s)
Stats log:         caller=15 callee=15 bitrate records
BWE non-zero:      yes
Errors:            none
TGCALLS_EXIT=0
=== TEST FINISHED ===
=== RESTORE ORIGINAL ROUTE ===
RESTORE=PASS
FINAL_EXIT=0
```

This is a **current**, not historical 5 September, same pinned-binary/same-reflector positive control for the alternate `192.168.1.140` route. Positive call establishment and BWE support media health on that route. A successful call suggests there was a working bidirectional network exchange for this test, but **no independent PCAP of this alternate route** was supplied; do not invent on-wire counts, checksum evidence or NAT details.

## A/B scope and remaining task

Current OPNsense `192.168.1.2` route (owner 11:43 local time) with native Voice enabled and ordinary Strategy #4 `fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2` resulted in 120 fake+60 originals at WAN `vtnet1`, 0 captured incoming reflector UDP, both peers Reconnecting, call=no, `TGCALLS_EXIT=1`. In contrast, `192.168.1.140` succeeded at the same endpoint, but route/NAT/egress and injected fakes differ; **this is not a strict one-factor proof of DPI dropping packets**, nor proof specifically of a Zapret2 defect.

**Restoration and blast radius:** `RESTORE=PASS` verified reinstallation of the exact original specific route through OPNsense `192.168.1.2`. TNAS default gateway, its other target `149.154.167.99/32`, OPNsense IPFW/PF/Voice/Strategies, Squid and sing-box were not changed by this experiment.

**Next owner-requested check:** `192.168.4.1` remains untested. TNAS `ip route get 192.168.4.1` chooses `via 192.168.1.140 dev ovs_eth1`; no direct `192.168.4.0/24` interface exists on TNAS. Identify the .4.1 host role, interfaces, upstream routes, and feasible independent traffic origin **read-only** before proposing a route or attempting another same-endpoint test. Never force an `onlink` gateway on `ovs_eth1`, rewrite default routes, or assume going through `.1.140` qualifies `.4.1` as independent.

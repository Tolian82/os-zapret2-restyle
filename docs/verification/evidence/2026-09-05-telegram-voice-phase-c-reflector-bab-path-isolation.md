# Telegram Voice Phase C fixed-reflector B/A/B path isolation

**Date:** 2026-09-05  
**Result:** exact-endpoint direct control `MEDIA_PASS`; repeated OPNsense/provider baseline failed with verified WAN egress and zero ingress  
**Endpoint:** `91.108.13.10:596/udp`  
**Probe host:** TNAS `192.168.1.100`, Docker network mode `host`  
**OPNsense path:** `192.168.1.2` LAN, `192.168.80.251` WAN NAT address  
**Direct control gateway:** `192.168.1.140`  
**Companion:** `tgcalls_cli` SHA-256 `c2bd9e8b55d5542e4471154c832efc4cf0cdd483669dbeb747c706afbe53b11a`

## Purpose

Remove endpoint, harness and stale-route ambiguity before testing reflector desynchronization. The same pinned executable and exact Telegram reflector were tested in this order:

1. B1 — no-desynchronization through OPNsense;
2. A — temporary exact-route override through the ordinary gateway;
3. B2 — no-desynchronization through OPNsense again after removing the override.

Every invocation used a fresh `tgcalls_cli` process and fresh UDP source flows.

## Route evidence

The owner-installed DHCP classless route selected the provider-path tests:

```text
91.108.13.10 via 192.168.1.2 dev ovs_eth1 src 192.168.1.100
```

The direct control temporarily installed a metric-1 exact route through `192.168.1.140`. After the control it was deleted and `ip route get 91.108.13.10` again selected `192.168.1.2`.

This route belongs to the TNAS host namespace. The host-network container has no separate IP address, MAC address or DHCP lease.

## B1 — OPNsense/provider baseline

The first 15-second provider-path run remained `Reconnecting` on both sides, reported no establishment, no non-zero BWE and exited 1.

Capture result:

| Capture | Outbound | Inbound | SHA-256 |
|---|---:|---:|---|
| LAN | 60 | 0 | `81b45cb6d100efb24d5884e61d4b0641d19666f48b550a0fc68f018fec988fc4` |
| WAN | 60 | 0 | `1b934ceaae6cd26158593d43ec871337f1c0902c77b260aad5f3a6cc3fd6139b` |

The WAN capture showed two 40-byte Reflector Hello flows to UDP destination port 596, retransmitted at approximately 500 ms.

## A — exact-endpoint direct control

The route was changed only for `91.108.13.10/32` to gateway `192.168.1.140`. The 15-second run then reached:

- callee `Established` at 1.613 seconds;
- caller `Established` at 1.829 seconds;
- 15 bitrate records per side;
- non-zero BWE;
- no errors;
- exit 0.

Verdict: exact endpoint and pinned harness `MEDIA_PASS`.

## B2 — repeated OPNsense/provider baseline

After restoring the exact endpoint route through OPNsense, the repeated 15-second run again remained `Reconnecting`, reported no establishment, no non-zero BWE, no internal error and exited 1.

Capture result:

| Capture | Outbound | Inbound | SHA-256 |
|---|---:|---:|---|
| LAN | 60 | 0 | `f46dc6f63ae33ff6978884a281a82e4651f2fc4c78a5860708632ce66947517d` |
| WAN | 60 | 0 | `fde9635da6960d1653ddc2379c1d875909829e5a18323caf3b5a63b65c65fb65` |

### Packet-level LAN/WAN comparison

The complete B2 captures were paired packet-for-packet:

| Property | LAN | WAN | Result |
|---|---|---|---|
| direction | `192.168.1.100 -> 91.108.13.10` | `192.168.80.251 -> 91.108.13.10` | expected NAT |
| flows | source ports 39102, 59236 | source ports 37896, 60367 | two stable NAT mappings |
| packets per flow | 30 + 30 | 30 + 30 | all 60 forwarded |
| IPv4 length | 68 | 68 | preserved |
| UDP payload length | 40 | 40 | preserved |
| payload | one constant Hello per peer | byte-identical | preserved for all 60 |
| IPv4 ID | per-packet values | identical to LAN | preserved for all 60 |
| TTL | 64 | 63 | exactly one routed hop |
| flags | DF, unfragmented | DF, unfragmented | no transformation |
| mean retry interval | about 500.2/500.3 ms | about 500.2/500.3 ms | preserved |
| OPNsense processing delta | — | mean 12.815 µs, min 3.815 µs, max 24.796 µs | normal local forwarding |
| inbound | 0 | 0 | no reply reached the WAN interface |

This proves that OPNsense routing, NAT and outbound forwarding were working and that the original Reflector Hello payload reached the WAN capture unchanged. Because no inbound packet existed on the WAN capture, the failure cannot be attributed to a post-WAN inbound firewall drop on OPNsense.

## Zapret runtime state during the baseline

The temporary Telegram Voice PoC marker was `disabled`. The dvtws2 child and supervisor processes were alive, but IPFW rules `19000..19010` were absent, so the service correctly reported `incomplete`.

That lifecycle drift is a separate maintenance issue. Its immediate cause is the missing firewall rule set; the event that removed the rules is not established by this evidence.

It does not contaminate B1/B2:

- the temporary PoC was disabled;
- no Zapret IPFW divert rule existed to feed these packets to dvtws2;
- even the ordinary configured UDP strategy is limited to destination ports `80,443,5222,8888`, not reflector port 596.

The earlier `configctl zapret telegram_voice_disable` `Execute error` was a status consequence of the already-incomplete service after a no-op disable. It is not evidence that the PoC was enabled.

Before candidate testing, perform a controlled `configctl zapret restart` and require the ordinary runtime and IPFW rule set to return to `running`.

## Verdict

The strict sequence is:

| Epoch | Route | Result |
|---|---|---|
| B1 | via OPNsense `192.168.1.2` | provider-path baseline failed; 60 WAN egress, 0 ingress |
| A | via `192.168.1.140` | `MEDIA_PASS` |
| B2 | via OPNsense `192.168.1.2` | provider-path baseline failed again; 60 WAN egress, 0 ingress |

The endpoint is alive and the emulator is valid. The provider path reproducibly blackholes or rejects this Telegram reflector exchange after correct WAN egress. The observation does not by itself distinguish destination-IP policy, reflector/source-policy, DPI classification or another upstream path rule.

This closes the no-desynchronization baseline as a repeatable network failure and justifies live candidate testing.

## Next candidate

The first candidate is reflector-specific ordered IPv4 fragmentation at UDP position 8:

```text
--filter-l3=ipv4
--filter-udp=596
--lua-desync=send:ipfrag:ipfrag_pos_udp=8
--lua-desync=drop
```

It must run as a separate temporary dvtws2 process and exact IPFW rule for only `91.108.13.10:596/udp`. It must not use `--filter-l7=stun` or `--payload=stun`: the 40-byte Reflector Hello is not STUN.

For each original 68-byte IPv4 datagram, the expected WAN replacement is:

| Fragment | IPv4 total length | Offset | MF | Data |
|---|---:|---:|---:|---|
| first | 28 | 0 | 1 | UDP header |
| second | 60 | 1 (8 bytes) | 0 | complete 40-byte Reflector Hello |

Both fragments must share one IPv4 ID, appear in order, and replace rather than accompany the original unfragmented packet. A correct transformation is `WIRE_OK`; only a successful pinned CLI run is `MEDIA_PASS`.

The laboratory remains temporary and console-only. Do not add this runner to the GUI, installed plugin paths, Generic UDP Strategy Lab or permanent service code.

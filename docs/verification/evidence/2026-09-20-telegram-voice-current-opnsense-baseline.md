# Telegram Voice current tgcalls OPNsense/provider baseline

**Date:** 2026-09-20  
**Status:** OWNER-LIVE BASELINE · WIRE PASS · NO REPLY OBSERVED  
**Scope:** current tgcalls `efd330ca04f74706024a5abdfb5b41f4e4dd1065`, fixed reflector `91.108.13.10:596`  
**OPNsense path:** TNAS `192.168.1.100` -> OPNsense gateway `192.168.1.2` -> WAN `vtnet1`

## Runtime result

The owner ran:

```text
/results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15
```

The current binary remained:

```text
Caller state:      Reconnecting
Callee state:      Reconnecting
Call established:  no
Stats log:         caller=15 callee=15 bitrate records
BWE non-zero:      no
Errors:            none
```

The result was repeated and remained stable.

## Route proof

Immediately before the baseline, TNAS resolved the fixed endpoint as:

```text
91.108.13.10 via 192.168.1.2 dev ovs_eth1 src 192.168.1.100
```

This proves the selected reflector traffic used the OPNsense path for this epoch.

## LAN/WAN capture evidence

Capture artifacts:

| Artifact | Size | SHA-256 |
|---|---:|---|
| `tg-current-lan-20260920T185030Z.pcap` | 5,904 B | `6be01570213d19b50f6313b5ebfa71403dcb5fa5cbc44ddad338f22706daaf54` |
| `tg-current-wan-20260920T185030Z.pcap` | 5,904 B | `1ee18497c0858ddf1523e55f39c4e83a4e9ee3642eb69951026cdf1a7a84b909` |

Both tcpdump logs reported 60 packets captured and zero packets dropped by the
kernel.

The LAN capture contains exactly two outbound UDP flows, 30 packets each:

- `192.168.1.100:52188 -> 91.108.13.10:596`
- `192.168.1.100:58791 -> 91.108.13.10:596`

The WAN capture contains the same 60 datagrams after NAT:

- `192.168.80.251:3061 -> 91.108.13.10:596`
- `192.168.80.251:40655 -> 91.108.13.10:596`

Flow mapping by payload/timestamp is one-to-one:

- `52188 -> 3061`
- `58791 -> 40655`

All 60 packets preserve the same IP identification across forwarding, TTL changes
from 64 to 63, and IPv4/UDP checksums validate in both captures. Packet pairing by
timestamp and payload is one-to-one; the largest LAN-to-WAN timestamp delta is
under 0.05 ms. No inbound `91.108.13.10:596` UDP packet appears on WAN or LAN.

## Current Hello framing

Each flow retransmits one stable 40-byte application payload approximately every
500 ms. The two current payloads were:

```text
00578f5df7eb3781f05cabef243fdfa0fffffffffffffffffffffffffeffffff000000000000007b
01578f5df7eb3781f05cabef2a78b9a9fffffffffffffffffffffffffeffffff000000000000007b
```

This is the same 40-byte Telegram Reflector Hello framing family previously
observed: 16-byte peer/session tag, 16-byte marker, and big-endian value 123.
Current Telegram changes therefore did not eliminate the blocked initial reflector
exchange on the tested provider path.

## Verdict and evidence boundary

- **WIRE PASS:** both current tgcalls Hello streams traverse OPNsense/NAT and reach
  WAN intact. OPNsense forwarding/NAT does not drop or corrupt the outbound
  baseline packets.
- **NO REPLY OBSERVED:** the fixed reflector returns zero UDP/596 packets during
  this 15-second epoch; both tgcalls peers remain `Reconnecting`, with zero BWE.
- The failure is not explained by the retired `e3069322...` binary or by a local
  current-tgcalls build/runtime defect: the current `efd330ca...` binary passed
  its local P2P runtime gate immediately before this provider-path experiment.
- The current reflector exchange is **non-STUN**: it is the 40-byte Reflector
  Hello family. Therefore the paused STUN-only `_4` profile cannot directly
  exercise this exact baseline flow.
- This capture alone does **not** prove the provider DPI is the cause. A strict
  `NETWORK_FAIL` classification requires a sufficiently fresh independent
  control for the same endpoint and current oracle. The historical exact-endpoint
  control remains useful context but is not silently treated as a fresh control.
- The next strategy experiment should target only the exact
  `91.108.13.10:596` UDP flow, prove the transformed WAN wire, and retain exact
  cleanup/restoration. A successful candidate would be strong causal evidence;
  another no-reply result remains ambiguous until a fresh independent control is
  available.

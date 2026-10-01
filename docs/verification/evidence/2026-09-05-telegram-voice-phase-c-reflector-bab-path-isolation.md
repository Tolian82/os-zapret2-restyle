# Historical Telegram Voice fixed-reflector B/A/B comparison

**Status:** Historical measurements from superseded [PR #286](https://github.com/Tolian82/os-zapret2-restyle/pull/286), reconciled 2026-10-01. The original private captures were not independently reanalysed in this cleanup.

This is an extended historical continuation of the [September 5 fixed-reflector control](2026-09-05-telegram-voice-fixed-reflector-control-pass.md), not the current test plan.

## Three historical measurement periods

The old pinned laboratory executable had SHA-256 `c2bd9e8b55d5542e4471154c832efc4cf0cdd483669dbeb747c706afbe53b11a`. The same fixed endpoint and fresh test process were used in each period.

| Period | Historical gateway | Recorded result |
|---|---|---|
| B1 | OPNsense `192.168.1.2` | 60 outgoing reflector datagrams on LAN/WAN, no reply; both peers `Reconnecting`, exit 1 |
| A | Former alternate `192.168.1.140` | Both peers `Established` at 1.613/1.829 seconds, 15 bitrate records per side, non-zero BWE, exit 0 |
| B2 | OPNsense `192.168.1.2` | Again 60 outgoing datagrams on LAN/WAN, no reply; both peers `Reconnecting`, exit 1 |

Capture identities reported in the original PR:

| Capture | SHA-256 |
|---|---|
| B1 LAN | `81b45cb6d100efb24d5884e61d19666f48b550a0fc68f018fec988fc4` |
| B1 WAN | `1b934ceaae6cd26158593d43ec871337f1c0902c77b260aad5f3a6cc3fd6139b` |
| B2 LAN | `f46dc6f63ae33ff6978884a281a82e4651f2fc4c78a5860708632ce66947517d` |
| B2 WAN | `fde9635da6960d1653ddc2379c1d875909829e5a18323caf3b5a63b65c65fb65` |

The distinctive value of PR #286 is its packet-level B2 comparison: two flows of 30 packets, original 40-byte Hello payloads preserved in all 60 LAN/WAN pairs, matching IPv4 IDs, expected NAT and single-hop TTL change, no fragmentation, and no response visible on the local WAN capture. The reported local processing interval was 3.815–24.796 microseconds (mean 12.815).

During these old tests the normal Zapret firewall rule set was absent even though related processes were running; the original PR separately classified the service as incomplete. The ordinary configured selector did not target this reflector port, so that incomplete status is not evidence that those unmodified baseline packets were transformed.

## Interpretation and current boundary

The historical A period verifies a successful call through a **different gateway with the old executable** between two unsuccessful OPNsense-gateway runs. It does not isolate provider DPI or establish an independently unblocked provider path. The owner subsequently clarified that the former gateway shared the provider environment and is now non-working. It must not be reintroduced as a current control or rollback route.

The historical B2 measurements support correct observed local forwarding, not a demonstrated explanation for missing packets beyond that WAN capture. Do not inherit PR #286's stronger causal verdict or its now-completed proposed next experiment. For the active binary and later tests use the [current evidence](2026-10-01-telegram-traffic-policy-and-voice-control.md) and [current handoff](../../START_HERE.md).

Only the unique historical measurements were retained; no raw packet captures, session identifiers, running configuration or obsolete operational instructions were added.

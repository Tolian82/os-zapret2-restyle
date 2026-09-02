# Telegram voice / UDP — Phase B STUN baseline live result

**Status:** OWNER-LIVE EVIDENCE · PHASE B NETWORK FAIL · RUNTIME/LIFECYCLE PASS
**Observed:** 2026-09-02
**Appliance:** OPNsense 26.7.3_8
**Package:** `os-zapret2-restyle-0.5.0_3`
**Research authority:** [`TELEGRAM_VOICE_UDP.md`](../../research/TELEGRAM_VOICE_UDP.md)

## Scope and privacy boundary

This record preserves the reproducible, non-sensitive result of the owner's live Phase B comparison. Raw PCAP files are intentionally excluded because they contain private addressing, ephemeral ports and external-proxy metadata. Client/private source addresses, source ports and the external proxy endpoint are redacted here.

The selected comparison used a Windows 11 client, a call participant outside the local network, Telegram Peer-to-Peer disabled on both participants, and the existing TCP/SOCKS proxy unchanged.

| State | Capture | SHA-256 | Size | Frames | Duration |
|---|---|---|---:|---:|---:|
| A — helper OFF | `telegram-voice-phase-b-a2-off-remote-lan-20260902T141315Z.pcap` | `84c912b358a8e72549b819eca9d0897a8bb67cc59a61463a2eb42dbfc2b24ac4` | 65,365 B | 501 | 107.356981 s |
| A — helper OFF | `telegram-voice-phase-b-a2-off-remote-wan-20260902T141327Z.pcap` | `53e62e740ee20ed6330133a9a3681dc4e726b0878381bd13f2df0b2c38609fe3` | 9,618 B | 99 | 44.544896 s |
| B — helper ON | `telegram-voice-phase-b-b2-on-remote-lan-20260902T144329Z.pcap` | `7f846486a76a2538a493782b32aebaadd73c089d4921be1bd22edbe8dd14f6fa` | 70,648 B | 535 | 93.076903 s |
| B — helper ON | `telegram-voice-phase-b-b2-on-remote-wan-20260902T144338Z.pcap` | `6a76d26e81a9560c3db0aacdd0a0bbb0aa484173a1c8c420afce487ba5bb3e46` | 56,117 B | 407 | 89.424269 s |

The owner had already verified the downloaded package SHA-256 as `b88accee3fc7510e3b54ed65bb525be65c79aba8e5e02193435b431a3a4c253f`.

## Runtime/control evidence

Before state A, `telegram_voice_status` reported the helper requested/effective/profile state OFF, no active or staging table, and no helper counter.

State B enable reported:

- requested/effective/profile state ON;
- service running;
- strategy `stun-zero-fake-repeats-2`;
- scope `telegram-ipv4-all-udp-ports`;
- active `zapret2_tgvoice` table with 14 entries;
- no residual staging table;
- helper rule `19000` installed as outbound WAN UDP to the Telegram table;
- initial helper counters `0 packets / 0 bytes`.

The effective first profile was:

```text
--name=telegram-voice-poc
--filter-l3=ipv4
--filter-udp=*
--filter-l7=stun
--ipset=/usr/local/etc/zapret2/runtime-v2/managed/ipset-telegram.txt
--payload=stun
--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2
--new
```

A mid-capture status snapshot reported `70 packets / 4,664 bytes`. This was not the final call count: the final TURN retransmission occurred after that status snapshot and the reflector retry stream continued. The complete LAN/WAN captures contain 99 original Telegram-destination UDP packets.

State C disable completed successfully:

- requested/effective/profile state returned to OFF;
- active and staging helper tables were absent;
- the helper form of rule `19000` disappeared;
- the ordinary TCP rule returned at `19000`;
- the Zapret2 service remained running.

This satisfies the live runtime/lifecycle and cleanup boundary.

## Packet comparison

| State | Destination | Identification | Original outbound | Zero fakes on WAN | Inbound | Result |
|---|---|---|---:|---:|---:|---|
| A — OFF | `91.108.9.118:1400` | TURN Allocate / STUN | 9 | 0 | 0 | all retransmissions exhausted |
| A — OFF | `91.108.9.89:598` | Telegram Reflector Hello | 90 | 0 | 0 | outbound-only |
| B — ON | `91.108.9.105:1400` | TURN Allocate / STUN | 9 | 18 | 0 | all retransmissions exhausted |
| B — ON | `91.108.9.34:596` | Telegram Reflector Hello | 90 | 0 | 0 | outbound-only/pass-through |

All four public destinations are inside the managed Telegram IPv4 scope. Endpoint changes between calls confirm that these addresses/ports are observations rather than a fixed call-port contract.

For every one of the 9 state-B TURN requests, the WAN capture contains this exact same-tuple order:

```text
16 zero bytes -> 16 zero bytes -> original TURN Allocate
```

The two generated datagrams precede each original by approximately 7–44 microseconds. All inspected WAN IPv4 and UDP checksums are valid. No fake was added before any of the 90 non-STUN Reflector Hello packets, proving that the L7/profile plus payload/Lua guards discriminated STUN from pass-through Telegram UDP on the same bounded all-port rule.

The original TURN retry timing remained approximately `0.25, 0.5, 1, 2, 4, 8, 8, 8` seconds. State B produced neither an inbound TURN error/success response nor any sustained bidirectional Telegram UDP flow.

## Acceptance result

Phase B has two separate outcomes:

- **Runtime/lifecycle: PASS.** Exact package, table scope, profile priority, IPFW interception/counters, on-wire fake emission, STUN-only action and disable cleanup all behaved as designed.
- **Provider/network effectiveness: FAIL.** The mandatory inbound TURN/STUN and sustained bidirectional Telegram UDP criteria were both absent. The zero-fake/repeats=2 baseline did not change the observed Telegram UDP path.

The PoC is therefore not product-accepted and must remain default OFF/CLI-only. Working or non-working audio cannot change this packet-based verdict because the existing TCP/SOCKS route can mask UDP failure.

## Interpretation limits

The comparison disproves the effectiveness of this exact upstream zero-fake baseline on the tested provider/path. It does not reveal the provider's internal rule.

The repeated destination-scoped pattern is more consistent with stateless Telegram-IP/direction filtering, relay-policy blocking, or another classifier/path failure that the zero fake does not desynchronize than with the specific stateful STUN behavior this baseline targets. That is an inference, not a packet-level identification of the DPI implementation.

The result does not justify:

- increasing fake repeats blindly;
- widening interception to all Internet UDP;
- adding a global UDP/443 drop;
- adding Telegram Reflector manipulation, because even the separately selected TURN/STUN request received no reply;
- adding a production GUI for the failed candidate.

## Next evidence boundary

Before another package candidate, inspect and document the exact current Zapret2 UDP/IP-fragmentation primitive and its FreeBSD/on-wire behavior. Any next experiment must retain Telegram-destination scope, remain default OFF, expose independent counters, prove the emitted fragments on WAN, and use the same P2P-disabled OFF/ON/OFF call acceptance criteria.

A fragmentation candidate may test whether the provider still parses the original UDP payload statelessly, but it cannot repair a pure destination-IP block. The next result must preserve that distinction rather than claim a universal Telegram Voice strategy.

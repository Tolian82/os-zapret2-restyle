# Telegram voice / UDP — Phase A live observation

**Status:** OWNER-LIVE EVIDENCE · PHASE A COMPLETE
**Observed:** 2026-08-28
**Appliance package:** `os-zapret2-restyle-0.5.0_2`
**Research authority:** [`TELEGRAM_VOICE_UDP.md`](../../research/TELEGRAM_VOICE_UDP.md)

## Scope and privacy boundary

This record preserves the reproducible, non-sensitive conclusions from the owner's live Telegram call capture. The raw PCAP is intentionally not committed: it contains private addressing, ephemeral ports and external-proxy metadata. Private client addresses, local source ports and the proxy endpoint are redacted here.

Capture identity retained for owner-side verification:

- filename: `telegram-voice-phase-a-p2poff-confirmed-20260828T165903Z.pcap`;
- SHA-256: `7f150dca37cf45e40019d57a52ac9c4685ec023f89e9e74168cca61d968216a2`;
- size: 53,403 bytes;
- link type: Ethernet;
- snapshot length: 256 bytes;
- captured packets: 392;
- first packet: `2026-08-28 16:59:06.058253Z`;
- last packet: `2026-08-28 17:00:25.462724Z`;
- duration: 79.404471 seconds.

The confirmed capture was client-scoped on the LAN and included client UDP plus the local SOCKS TCP path, excluding mDNS. Concurrent PF and socket-state snapshots were also collected.

## Test conditions

- client OS: Windows 11;
- both call participants were on the same local network;
- Telegram Peer-to-Peer was disabled on both participants before the confirmed run;
- ordinary Telegram TCP/service traffic remained configured through the existing local SOCKS and external proxy;
- the normal Zapret2 service was running, but no Telegram Voice-specific helper/rule/profile existed;
- no configuration or source change was introduced for Phase A.

## Owner-observed call result

- call established;
- sound worked in both directions;
- no delay was perceived.

These user-visible results are important but are not evidence that UDP succeeded.

## UDP observation

| Destination | Protocol identification | Client → destination | Destination → client | Observation interval |
|---|---|---:|---:|---|
| `91.108.9.100:1400` | TURN Allocate request | 9 packets / 252 UDP payload bytes | 0 packets / 0 bytes | `16:59:13.381499Z`–`16:59:45.131757Z` (31.750258 s) |
| `91.108.9.40:597` | Telegram Reflector Hello | 90 packets / 3,600 UDP payload bytes | 0 packets / 0 bytes | `16:59:13.381553Z`–`16:59:57.925200Z` (44.543647 s) |

Both destinations are within Telegram-managed IPv4 space. A mid-call PF state snapshot independently showed an outbound-only state for each destination. No direct/private-peer UDP candidate appeared in this confirmed P2P-disabled capture.

The repeated 40-byte stream matches Telegram `tgcalls` [`ReflectorPort::SendReflectorHello()`](https://github.com/TelegramMessenger/tgcalls/blob/2faee3b5524f54d56c91c2058c00e11c656a74b3/tgcalls/v2/ReflectorPort.cpp#L309-L360), including the approximately 500 ms hello retry pattern.

## TCP/SOCKS correlation

Several TCP connections between the client and local SOCKS service remained active. Captured SOCKS CONNECT requests targeted Telegram DC addresses:

- `149.154.167.41:443`;
- `149.154.167.51:443`;
- `149.154.167.41:80`;
- `149.154.167.51:80`.

One long-lived bidirectional SOCKS stream overlapped almost the entire call observation:

- client → proxy: 51 packets / 11,023 TCP payload bytes;
- proxy → client: 68 packets / 15,314 TCP payload bytes;
- interval: `16:59:09.979015Z`–`17:00:23.841951Z`.

A new TCP setup burst started at `16:59:13.184237Z`; the first TURN/reflector UDP attempts followed at `16:59:13.381499Z`, approximately 197 ms later. The concurrent socket snapshot also confirmed active outbound proxy TCP connections; the proxy endpoint is deliberately redacted.

## Attribution and limits

The combined evidence supports this bounded conclusion:

1. the client attempted Telegram TURN and reflector UDP with P2P disabled;
2. no packet returned from either observed relay candidate;
3. the call still had stable two-way sound;
4. the only observed bidirectional WAN-capable route for that client was the existing TCP/SOCKS proxy;
5. therefore the working call used a TCP/proxy fallback at route level.

The TCP payload is encrypted and was not decrypted. This record does not claim that one identified TCP connection can be cryptographically proven to contain the audio stream.

The evidence does **not** prove why UDP replies were absent. It cannot distinguish:

- stateful DPI classification triggered by STUN;
- stateless UDP filtering;
- Telegram relay-IP/port filtering;
- endpoint/provider routing loss;
- another upstream blackhole.

It does prove that the failure occurs no later than relay establishment for both observed UDP candidates and that audible call success can hide that failure.

## Zapret2 classification consequence

TURN Allocate is a STUN-framed message and can be selected by Zapret2 `--payload=stun`. The inspected Zapret2 v1.0.4 [`IsStunMessage()`](https://github.com/bol-van/zapret2/blob/2c21faa/nfq2/protocol.c#L1459-L1465) requires the RFC STUN magic cookie and framing checks.

Telegram Reflector Hello is a separate 40-byte protocol message without that cookie. The official zero-fake STUN baseline will therefore target the TURN Allocate request but leave Reflector Hello outside the STUN profile.

This is an explicit first-PoC boundary, not a reason to add a reflector-specific action pre-emptively. Restoring TURN allocation may be sufficient. Reflector handling becomes a separate research branch only if TURN replies return but sustained bidirectional Telegram UDP still does not appear.

## Phase B acceptance gate

Use the same clients with P2P disabled and leave the TCP proxy unchanged. Compare helper OFF/ON/OFF.

A Phase B PASS requires:

- Telegram Voice `ipfw` counter increments;
- dvtws2 reports selection of the STUN helper profile;
- inbound TURN/STUN reply appears;
- sustained bidirectional Telegram UDP follows;
- exact helper rule/table/profile cleanup occurs after disable;
- the B-only UDP behavior disappears in rollback state C.

Call establishment or good sound by itself is not a PASS because Phase A already demonstrated working TCP fallback with completely outbound-only observed relay UDP.

## Repository impact

This evidence record is documentation-only. It adds no raw capture, source change, runtime rule, strategy, GUI, package revision or release artifact.

## Subsequent research boundary

Phase B later proved that the STUN zero-fake helper acted correctly but restored no TURN reply, while the reflector packets remained completely untouched. Official pinned `tgcalls_cli` can exercise a real reflector and bidirectional media without Telegram API signaling or TCP fallback. The current Phase C plan therefore measures reflector strategies independently rather than continuing to assume that reflector work must wait for TURN success. See [`TELEGRAM_VOICE_EMULATION_LAB.md`](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md).

# Telegram Voice reverse position-8 post-reboot repeat

**Status:** LOCAL-WAN WIRE_OK · NO_REPLY_UNKNOWN · RESTORE_OK · NO MEDIA_PASS FOR THIS RUN

**Test date:** 2026-09-22; **recorded:** 2026-09-23

**Scope:** temporary console laboratory; package identity remains `0.5.0_3`

Current task and exact next action: [`START_HERE.md`](../../START_HERE.md). Acceptance: [laboratory architecture](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md). Earlier reported success: [separate observation](2026-09-22-telegram-voice-reverse8-call-observation.md).

## Owner clarification and restored topology

The owner identified the earlier successful display as this command:

```sh
docker exec tgvoice-lab /results/tgcalls_cli \
  --mode reflector --reflector 91.108.13.10:596 --duration 15
echo "tgcalls_exit=$?"
```

The positive summary for that earlier call was not supplied. Preserve the owner's established-call/correct-route observation; this later failed repeat does not disprove it or attribute the earlier success to fragmentation.

After reboot, TNAS restored the endpoint route:

```text
91.108.13.10 via 192.168.1.2 dev ovs_eth1 src 192.168.1.100
status=running network=host
```

OPNsense routes the endpoint through gateway `192.168.80.1`, WAN `vtnet1`, MTU 1500. WAN address is `192.168.80.251`; LAN is `vtnet0`. `192.168.1.140` remains retired as a working lab/control route. Docker has no separate network identity. This runner did not change any route.

## Archive and runtime identities

| Item | Identity |
|---|---|
| Archive | `tgvoice-ipfrag8-reverse-postnat-20260922T210417Z-a6rbyk00.tar.gz` |
| Archive SHA-256 | `e6425bd55476e26028857286e7fcfaa3b687d3626cf1b408bacfa40a3ca27a87` |
| Runner | `tgvoice_ipfrag8_reverse_postnat_v1.py`, `postnat-reverse8-v1` |
| Runner SHA-256 | `3ecb158f246074ce93ac70c87564d4f0b376e61d76b24bcaaa65543c659ab3f2` |
| dvtws2 SHA-256 | `69ac3515d2357f567ca2d12753d71bbc7ff05aa2839d48ebb5667f1651761f7a` |
| zapret-lib.lua SHA-256 | `b67a470f23b00a8d6e732c4e5135a39b224511e0b71809d5f4616adf62674980` |
| zapret-antidpi.lua SHA-256 | `31c9dd75b0bd55e98e5306293f2be81e9d2ecadcbbf9157394ff37dcff7dc85a` |
| tgcalls source | `efd330ca04f74706024a5abdfb5b41f4e4dd1065` |
| `/results/tgcalls_cli` SHA-256 | `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc` |

The installed binary identifies itself as self-built September 20, 2026 16:04:47, Lua compatibility 6; the owner reports Zapret2 `v1.0.5.2`. Both Lua hashes exactly match upstream commit `6b6c63e3385fa73f8af3be4a69171e947f5a319d`. All three runtime hashes match the previous qualified ordered/reverse runner guard.

## Time correlation and CLI result

| Event | UTC |
|---|---|
| Runner READY | `2026-09-22T21:04:17.273273Z` |
| CLI started / finished markers | `21:04:34Z` / `21:04:49Z` |
| LAN packet interval | `21:04:34.905915Z`–`21:04:49.415258Z` |
| WAN packet interval | `21:04:34.906713Z`–`21:04:49.415845Z` |
| Cleanup began, Ctrl+C | `2026-09-22T21:05:00.675204Z` |

The complete 15-second CLI run falls inside the approximately 43.4-second active runner interval. The second-resolution CLI markers and microsecond-resolution PCAP timestamps agree within their respective precision.

The owner retained console output under `tgvoice-reverse8-reboot-<UTC>.txt` and requested RTC output under the same prefix with `.rtc.log`. The supplied console shows:

| CLI field | Result |
|---|---|
| Engine | `13.0.0` on both peers; no custom override |
| Mode / duration | `reflector (91.108.13.10:596)` / 15 seconds |
| Final caller / callee state | `Reconnecting` / `Reconnecting` |
| Call established | `no` |
| Bitrate records | caller 15 / callee 15 |
| BWE non-zero | `no` |
| Errors | `none` |
| Actual CLI exit | `1` |

The RTC log itself has not been supplied. Its absence does not prevent this run's negative media verdict: console, packet timing and zero replies are already correlated. Signaling callbacks, bitrate-record count and `Errors: none` are not proof of media.

## Packet qualification

The temporary rule selects unfragmented outgoing IPv4 UDP from the WAN address to exactly `91.108.13.10:596`, with `frag !mf,!offset`, and diverts to 990. The runner temporarily places outgoing IPv4 IPFW after PF/NAT. This hook ordering affects outgoing IPv4 globally, while the fragmentation rule is endpoint-specific. Captures on both interfaces use `host 91.108.13.10`, including non-initial fragments.

| Evidence | Measured result |
|---|---|
| Rule 18990 | 60 packets / 4080 bytes |
| LAN PCAP | 11,784 bytes; 120 records |
| LAN primary source | 60 datagrams from `192.168.1.100` |
| LAN other/iSCSI source | 60 datagrams from `192.168.192.100`; not emitted as these WAN pairs |
| LAN packet form | IPv4 length 68, UDP payload 40; offset 0, MF=0, DF=1, TTL=64 |
| WAN PCAP | 8,904 bytes; 120 records = 60 complete pairs |
| WAN first emitted fragment | IPv4 length 60, byte offset 8, MF=0, DF=0, TTL=63 |
| WAN second emitted fragment | IPv4 length 28, byte offset 0, MF=1, DF=0, TTL=63 |
| Reverse ordering | 60/60; approximately 26–124 microseconds between paired fragments |
| IPv4 checksums | 120/120 valid on LAN; 120/120 valid on WAN |
| Reassembled UDP | 60/60 lengths correct; 60/60 nonzero checksums valid |
| Payload attribution | 60/60 match primary LAN payloads exactly; zero matches to the other source |
| Unfragmented originals on WAN | zero |
| Packets from reflector | zero on LAN and WAN |
| Capture loss | zero kernel drops on both interfaces |

The profile logged native `send` with `ipfrag_pos_udp="8"` and `ipfrag_disorder`, followed by drop. No packet-processing error was found. The capture proves correct emission on local WAN; it does not prove fragment survival/reassembly beyond the upstream private NAT.

## Restoration

`result.txt` reports `RESTORE_OK`, no error. Before/after IPFW, PFIL and listening-socket snapshots are byte-identical.

- Normal rules 19000/19001 are present before and after, with zero counters in the snapshots. Earlier archives had these rules absent; do not carry that earlier condition forward into this reboot epoch.
- Temporary rule 18990 and listener 990 are gone; existing dvtws2 listener 989 remains.
- IPv4 input remains PF then IPFW. Output begins IPFW then PF, temporarily becomes PF then IPFW, and returns to its original order.
- IPv6 input/output hooks are unchanged. No route is mutated by the runner.

## Interpretation

This specific repeat is **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`**, with **no `MEDIA_PASS`**. Reverse position-8 fragmentation is now live-qualified, but the reflector sent no captured reply and neither peer established. There is no fresh independent working control, so do not isolate provider DPI or classify a universal failure of the strategy/endpoint from this result.

The pinned [CLI source](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tools/cli/main.cpp), [engine 13 implementation](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tgcalls/v2/InstanceV2Impl.cpp) and [native networking](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tgcalls/v2/NativeNetworkingImpl.cpp) support one configured UDP reflector with P2P/TCP disabled for this command; no automatic alternate endpoint/TCP fallback is established. The CLI's `Call established` flag latches if either peer ever establishes. Exit 0 additionally requires stats and nonzero BWE on both sides; the laboratory's `MEDIA_PASS` also requires both final peer states established. The generated-tone/no-op-renderer harness does not prove audible decoded speech.

## Subsequent live result — September 23

The [reverse position-32 archive and CLI](2026-09-23-telegram-voice-reverse32.md) now qualify 60 complete reverse pairs with valid checksums, no replies/media and exact restoration. The preparation record below describes the state before that run; it is retained as history. The current handoff advances to guarded reverse position 16 in [`START_HERE.md`](../../START_HERE.md).

## Prepared next candidate: guarded reverse position 32

Distinct file: **`tgvoice_ipfrag32_reverse_postnat_v1.py`**, revision **`postnat-reverse32-v1`**.

SHA-256: `e2ffde5b84f3e9f7f1b1526cd6f55302b662c86ca7307aa78b195520338b9c76`.

Run on OPNsense:

```sh
/usr/local/bin/python3 -u /tmp/tgvoice_ipfrag32_reverse_postnat_v1.py --after-nat
```

Wait for `READY: REVERSE ipfrag32 AFTER NAT [postnat-reverse32-v1]`, then run the same 15-second CLI from TNAS with a distinct `tgvoice-reverse32-<UTC>` console/RTC prefix. Keep the binary, engine/configuration, endpoint and restored route fixed. Stop the runner with Ctrl+C after the CLI finishes; the runner also has a 120-second bound. Collect its uniquely named `tgvoice-ipfrag32-reverse-postnat-...tar.gz` archive and CLI output together.

For the observed 40-byte Hello, retain reverse order and change only the cut from 8 to 32: expect an IPv4 length-36 final fragment at byte offset 32 before an IPv4 length-52 first fragment at offset 0, MF=1. Validate wire output before interpreting media.

An explicit guard is required for short traffic. Pinned [native fragmentation](https://github.com/bol-van/zapret2/blob/6b6c63e3385fa73f8af3be4a69171e947f5a319d/lua/zapret-lib.lua) cannot split UDP length at or below 32; it falls back to raw-sending the original unfragmented datagram, which can re-enter the same unfragmented rule. The wrapper returns `VERDICT_PASS` without raw-send for UDP payload length at or below 24. Longer datagrams delegate to native [`send`](https://github.com/bol-van/zapret2/blob/6b6c63e3385fa73f8af3be4a69171e947f5a319d/lua/zapret-antidpi.lua) with `ipfrag:ipfrag_pos_udp=32:ipfrag_disorder`, then return `VERDICT_DROP`. This is an additional handling change for short datagrams; do not claim a single-factor comparison for every possible media packet.

The same strict runtime-hash guard, bounded rule/listener ownership, capture scope and restoration contract are retained. Python syntax and `--help` passed. Twenty-seven offline cases ran the pinned native Lua functions with the new wrapper: payload lengths 0/1/8/16/23/24/25/40/200 crossed with IP-option lengths 0/4/40. Short packets passed without raw-send; longer packets emitted two reverse fragments with correct lengths, offsets, ID and payload preservation. Raw socket I/O was stubbed; these checks do not qualify FreeBSD reinjection, remote replies or media. **Position 32 has no live result yet.**

The earlier positive CLI output can be correlated if recovered; waiting for it does not block this bounded experiment. Reach and repeat `MEDIA_PASS`, then complete the real Windows/Android gate. Raw PCAPs, session/peer tags and private logs are not committed. No plugin, package, workflow, Generic UDP or permanent laboratory subsystem changes belong to this record.

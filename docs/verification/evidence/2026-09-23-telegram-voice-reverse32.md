# Telegram Voice reverse position-32 live result

**Status:** LOCAL-WAN WIRE_OK · NO_REPLY_UNKNOWN · RESTORE_OK · NO MEDIA_PASS FOR THIS RUN

**Test / analysis date:** 2026-09-23

**Scope:** temporary console laboratory; package identity remains `0.5.0_3`

Current task: [`START_HERE.md`](../../START_HERE.md). Acceptance: [laboratory architecture](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md). Preceding comparison and exact runtime pins: [reverse position-8 repeat](2026-09-22-telegram-voice-reverse8-postreboot.md). The [earlier owner-reported successful call](2026-09-22-telegram-voice-reverse8-call-observation.md) remains a separate observation.

## Identity and timing

| Evidence | Value |
|---|---|
| Archive | `tgvoice-ipfrag32-reverse-postnat-20260923T070628Z-rwukstn4.tar.gz` |
| Archive SHA-256 | `aeab3aedf2193d2f08a7b81cb2c9b9026ac76e19897757f0149af77349349f5a` |
| Runner revision | `postnat-reverse32-v1` |
| Delivered runner | `tgvoice_ipfrag32_reverse_postnat_v1.py`, SHA-256 `e2ffde5b84f3e9f7f1b1526cd6f55302b662c86ca7307aa78b195520338b9c76` |
| READY | `2026-09-23T07:06:28.360118Z` |
| CLI started / finished | `2026-09-23T07:06:36Z` / `2026-09-23T07:06:51Z` |
| LAN packet interval | `07:06:36.821616Z`–`07:06:51.331042Z` |
| WAN packet interval | `07:06:36.822293Z`–`07:06:51.331559Z` |
| Cleanup began, Ctrl+C | `2026-09-23T07:06:58.601670Z` |

The full CLI run falls within the approximately 30.2-second active runner window. The supplied route is still `91.108.13.10 via 192.168.1.2 dev ovs_eth1 src 192.168.1.100`. The retired `192.168.1.140` is not used as a control or restoration destination. The runner changed no routes.

The supplied CLI hash is unchanged: `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`. Source remains `efd330ca04f74706024a5abdfb5b41f4e4dd1065`, engine `13.0.0` on both peers, same fixed UDP reflector `91.108.13.10:596`, 15 seconds, no custom override. The archive's binary and both Lua hashes exactly match the [preceding runtime identities](2026-09-22-telegram-voice-reverse8-postreboot.md#archive-and-runtime-identities); the runtime guard passed.

## Packet result

The same bounded rule 18990/divert 990 selects only unfragmented outgoing IPv4 UDP from WAN address `192.168.80.251` to the fixed endpoint/port, with `frag !mf,!offset`. PF/NAT runs before IPFW during the test. This temporary hook reordering affects outgoing IPv4 globally; packet transformation remains endpoint-specific. Both PCAP filters are `host 91.108.13.10` and include non-initial fragments.

| Check | Measured result |
|---|---|
| Rule 18990 | 60 packets / 4080 bytes |
| LAN PCAP | 11,784 bytes / 120 records: 60 from primary `192.168.1.100`, 60 from other/iSCSI `192.168.192.100` |
| LAN layout | IP length 68, UDP payload 40, offset 0, MF=0, DF=1, TTL=64 |
| WAN PCAP | 8,904 bytes / 120 records = 60 complete pairs, two flows of 30 datagrams |
| First emitted fragment | IP length 36, byte offset 32, MF=0, DF=0, TTL=63 |
| Second emitted fragment | IP length 52, byte offset 0, MF=1, DF=0, TTL=63 |
| Reverse order | 60/60; paired emission gaps 29–230 microseconds |
| IPv4 checksums | LAN 120/120 valid; WAN 120/120 valid |
| Reassembled UDP | 60/60 lengths correct; 60/60 nonzero checksums valid |
| Payload preservation | 60/60 exact primary-LAN matches; zero matches to the other source |
| Unfragmented originals on WAN | zero |
| Packets from reflector | zero on LAN and WAN |
| Capture loss | zero kernel drops on both interfaces |

The actual inline Lua guard and position-32 profile were accepted. The log contains 60 native `ipfrag2` calls, zero short-packet pass messages and no processing errors. All intercepted payloads were 40 bytes; this live run qualifies fragmentation, while short-packet pass-through retains its earlier offline coverage only.

## Media and restoration

The matching console output reports both final peer states `Reconnecting`, `Call established: no`, 15 bitrate records per side, `BWE non-zero: no`, `Errors: none`, and actual `tgcalls_exit=1`. The requested RTC file was not attached; the negative result is already established by console and correlated packet evidence. Signaling callbacks and record counts are not media success.

`result.txt` reports `RESTORE_OK`, signal 2, no error. IPFW, PFIL and listening-socket snapshots are byte-identical before/after. Normal rules 19000/19001 are retained; the measured TCP rule also carried unrelated traffic during this test. Temporary rule 18990/listener 990 are removed, existing listener 989 remains. Outgoing IPv4 hook order returns from temporary PF→IPFW to original IPFW→PF; inbound and IPv6 hooks are unchanged.

The bounded verdict is **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`**, with **no `MEDIA_PASS` for this run**. The position-32 split was emitted correctly, but no reply returned to the WAN capture. This does not identify the loss point beyond local WAN, upstream-NAT behavior or provider DPI. No fresh independent working control is established. The earlier positive owner observation is not overwritten.

## Next bounded experiment: guarded reverse position 16

File: **`tgvoice_ipfrag16_reverse_postnat_v1.py`**, revision **`postnat-reverse16-v1`**.

SHA-256: `b56c1b8f5db7c4ff6493173646dbabe2db0c12e40afd918035da9e0d24378872`.

```sh
/usr/local/bin/python3 -u /tmp/tgvoice_ipfrag16_reverse_postnat_v1.py --after-nat
```

Wait for `READY: REVERSE ipfrag16 AFTER NAT [postnat-reverse16-v1]`, then run the same fixed-reflector 15-second CLI on TNAS with `tgvoice-reverse16-<UTC>` console/RTC logs. After the CLI ends, Ctrl+C closes the runner and produces the `tgvoice-ipfrag16-reverse-postnat-...tar.gz` archive; it also retains the 120-second automatic bound.

Keep the same binary/runtime, route, engine/configuration and endpoint. For the current 40-byte Hello, change only the cut from 32 to 16 while retaining reverse order. Expected output is IP length 52 at byte offset 16, MF=0, then IP length 36 at offset 0, MF=1.

The guard threshold follows the split: UDP payload length at most 8 passes normally with no raw-send; larger packets call native `send` with `ipfrag:ipfrag_pos_udp=16:ipfrag_disorder`, then return `VERDICT_DROP`. This prevents the pinned native unfragmented fallback from re-entering the same rule. Payloads of 9–24 bytes now fragment instead of pass; that explicit short-traffic difference must not be described as a single-factor comparison across every possible packet. The lifecycle, runtime guard, capture scope and restoration contract are unchanged.

Python syntax and help passed. Twenty-seven offline cases ran the actual pinned [native fragmentation functions](https://github.com/bol-van/zapret2/blob/6b6c63e3385fa73f8af3be4a69171e947f5a319d/lua/zapret-lib.lua) and [`send`](https://github.com/bol-van/zapret2/blob/6b6c63e3385fa73f8af3be4a69171e947f5a319d/lua/zapret-antidpi.lua) with the new guard: payload lengths 0/1/7/8/9/16/24/40/200 crossed with IP-option lengths 0/4/40. Short packets passed without raw-send; longer packets emitted two reverse fragments with expected lengths/offsets/ID and preserved input. Raw socket I/O was stubbed. **Position 16 has no live result yet.**

Qualify wire output and exact restoration before interpreting media. Reach and repeat `MEDIA_PASS`, then complete the real Windows/Android gate. This record commits no raw PCAP, peer/session tags or private logs and makes no plugin/package change.

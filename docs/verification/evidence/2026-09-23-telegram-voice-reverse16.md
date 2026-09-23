# Telegram Voice reverse position-16 live result

**Status:** LOCAL-WAN WIRE_OK · NO_REPLY_UNKNOWN · RESTORE_OK · NO MEDIA_PASS FOR THIS RUN

**Test / analysis date:** 2026-09-23

**Scope:** temporary console laboratory; package identity remains `0.5.0_3`

Current task: [`START_HERE.md`](../../START_HERE.md). Acceptance: [laboratory architecture](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md). Preceding comparison: [reverse position-32](2026-09-23-telegram-voice-reverse32.md).

## Identity and timing

| Evidence | Value |
|---|---|
| Archive | `tgvoice-ipfrag16-reverse-postnat-20260923T072909Z-6i3kgfz9.tar.gz` |
| Archive SHA-256 | `0e1ce28de7065b2d6e9305f5434d98d1dd9126dd09ad694b265a656af6a4da5c` |
| Runner revision | `postnat-reverse16-v1` |
| Delivered runner | `tgvoice_ipfrag16_reverse_postnat_v1.py`, SHA-256 `b56c1b8f5db7c4ff6493173646dbabe2db0c12e40afd918035da9e0d24378872` |
| READY | `2026-09-23T07:29:10.171579Z` |
| CLI started / finished | `2026-09-23T07:29:23Z` / `2026-09-23T07:29:38Z` |
| LAN packet interval | `07:29:23.972424Z`–`07:29:38.482646Z` |
| WAN packet interval | `07:29:23.973155Z`–`07:29:38.483009Z` |
| Cleanup began, Ctrl+C | `2026-09-23T07:29:46.955956Z` |

The complete 15-second CLI run falls inside the active runner window. The supplied route remains `91.108.13.10 via 192.168.1.2 dev ovs_eth1 src 192.168.1.100`. The retired `192.168.1.140` route is not used as a current control or restoration destination. The runner changed no routes.

The supplied CLI hash is unchanged: `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`. Source remains `efd330ca04f74706024a5abdfb5b41f4e4dd1065`, engine `13.0.0` on both peers, fixed UDP reflector `91.108.13.10:596`, 15 seconds, no custom override. The archive runtime guard passed with the same measured `dvtws2` and Lua hashes as the preceding qualified runs.

## Packet result

The bounded temporary rule 18990/divert 990 selected only unfragmented outgoing IPv4 UDP from WAN address `192.168.80.251` to `91.108.13.10:596`, after PF/NAT. The runner temporarily changed outgoing IPv4 hook order from IPFW→PF to PF→IPFW and restored it afterward. LAN/WAN captures used `host 91.108.13.10`, retaining non-initial fragments.

| Check | Measured result |
|---|---|
| Rule 18990 | 60 packets / 4080 bytes |
| LAN PCAP | 120 records: 60 from primary `192.168.1.100`, 60 from other/iSCSI `192.168.192.100` |
| LAN layout | IP length 68, UDP payload 40, offset 0, MF=0, DF=1, TTL=64 |
| WAN PCAP | 120 records = 60 complete fragment pairs |
| First emitted fragment | IP length 52, byte offset 16, MF=0, DF=0, TTL=63 |
| Second emitted fragment | IP length 36, byte offset 0, MF=1, DF=0, TTL=63 |
| Reverse order | 60/60; paired emission gaps approximately 25–102 microseconds |
| IPv4 checksums | LAN 120/120 valid; WAN 120/120 valid |
| Reassembled UDP | 60/60 lengths correct; 60/60 nonzero checksums valid |
| Payload preservation | 60/60 exact primary-LAN application-payload matches; zero matches to the other/iSCSI source |
| Unfragmented originals on WAN | zero |
| Packets from reflector | zero on LAN and WAN |
| Capture loss | zero kernel drops on both interfaces |

The `dvtws2` log contains 60 native `ipfrag2` calls, with fragment 2 emitted before fragment 1 for each intercepted Hello. The short-packet guard was not exercised: all intercepted UDP application payloads were 40 bytes.

## Media and restoration

The correlated console output reports:

```text
Duration:          15s
Mode:              reflector (91.108.13.10:596)
Caller state:      Reconnecting
Callee state:      Reconnecting
Call established:  no
Stats log:         caller=15 callee=15 bitrate records
BWE non-zero:      no
Errors:            none
tgcalls_exit=1
```

This run therefore has no `MEDIA_PASS`.

`result.txt` reports `RESTORE_OK`, signal 2 and no error. IPFW, PFIL and listening-socket state returned to the measured pre-test state. Temporary rule 18990/listener 990 were removed, existing listener 989 remained, and outgoing IPv4 hook order returned to IPFW→PF. No route was modified.

The bounded verdict is **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`**, with **no `MEDIA_PASS` for this run**. Reverse position 16 was emitted exactly as intended, but no reply returned to the local WAN capture. With no fresh independent working control, this does not isolate provider DPI, upstream NAT/fragment behavior, endpoint availability or another path cause. The earlier owner-reported positive call observation remains separate.

## Next bounded experiment: guarded reverse position 24

Prepared file: **`tgvoice_ipfrag24_reverse_postnat_v1.py`**, revision **`postnat-reverse24-v1`**.

SHA-256: `c63ddb5dc097dfcec2759134101a31f1020cf5536d82f26eeab3dd2b30217905`.

The file is derived from the qualified reverse16 runner by changing only the candidate identity, fragmentation position and required short-packet guard. Python syntax passes. Pinned Zapret2 source establishes the guard boundary: `ipfrag2` cancels fragmentation when the split position is at or beyond the complete L3+L4+payload length, and `rawsend_dissect_ipfrag` otherwise falls back to raw-sending the unfragmented packet. For UDP position 24, the wrapper therefore passes application payloads of at most 16 bytes unchanged and delegates longer datagrams to native reverse fragmentation.

Run on OPNsense:

```sh
/usr/local/bin/python3 -u /tmp/tgvoice_ipfrag24_reverse_postnat_v1.py --after-nat
```

Wait for `READY: REVERSE ipfrag24 AFTER NAT [postnat-reverse24-v1]`, then run the same fixed-reflector 15-second CLI on TNAS with a distinct `tgvoice-reverse24-<UTC>` console/RTC prefix.

For the observed 40-byte Hello, the expected WAN order is:

1. IP length 44, byte offset 24, MF=0;
2. IP length 44, byte offset 0, MF=1.

Keep the same endpoint, route, binary, engine/configuration, runtime identities, capture scope and restoration contract. Qualify wire output before interpreting media. If reverse24 also produces correct output with no reply/media, the standalone fragmentation-position family has enough measured coverage to move to the next bounded family rather than widening positions indefinitely.

Raw PCAPs, session/peer tags and private logs are not committed. No plugin/package source change belongs to this evidence.

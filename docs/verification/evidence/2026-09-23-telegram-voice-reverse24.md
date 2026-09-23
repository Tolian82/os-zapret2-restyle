# Telegram Voice reverse position-24 live result

**Status:** LOCAL-WAN WIRE_OK · NO_REPLY_UNKNOWN · RESTORE_OK · NO MEDIA_PASS FOR THIS RUN · STANDALONE FRAGMENT POSITION SWEEP CLOSED

**Test / analysis date:** 2026-09-23

**Scope:** temporary console laboratory; package identity remains `0.5.0_3`

Current task: [`START_HERE.md`](../../START_HERE.md). Acceptance: [laboratory architecture](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md). Preceding comparison: [reverse position-16](2026-09-23-telegram-voice-reverse16.md).

## Identity and timing

| Evidence | Value |
|---|---|
| Archive | `tgvoice-ipfrag24-reverse-postnat-20260923T124534Z-3mlft8uk.tar.gz` |
| Archive SHA-256 | `b7307216b8a186c517c6a41eb36fa7ac0eff451817d4f0bfa4f812ce86e1e03c` |
| Runner revision | `postnat-reverse24-v1` |
| Delivered runner | `tgvoice_ipfrag24_reverse_postnat_v1.py`, SHA-256 `c63ddb5dc097dfcec2759134101a31f1020cf5536d82f26eeab3dd2b30217905` |
| READY | `2026-09-23T12:45:34.971997Z` |
| CLI started / finished | `2026-09-23T12:45:54Z` / `2026-09-23T12:46:09Z` |
| LAN packet interval | `12:45:54.981692Z`–`12:46:09.493217Z` |
| WAN packet interval | `12:45:54.982307Z`–`12:46:09.493765Z` |
| Cleanup began, Ctrl+C | `2026-09-23T12:46:16.865740Z` |

The full CLI run is inside the active runner window. The route remains `91.108.13.10 via 192.168.1.2 dev ovs_eth1 src 192.168.1.100`. The runner changed no routes.

The supplied CLI hash remains `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`; source remains `efd330ca04f74706024a5abdfb5b41f4e4dd1065`, engine `13.0.0` on both peers, fixed UDP reflector `91.108.13.10:596`, 15 seconds and no custom override. Runtime hashes match the preceding qualified v1.0.5.2 epochs.

## Packet result

The same bounded rule 18990/divert 990 selected only unfragmented outgoing IPv4 UDP after PF/NAT from WAN `192.168.80.251` to `91.108.13.10:596`. LAN/WAN captures retained non-initial fragments.

| Check | Measured result |
|---|---|
| Rule 18990 | 60 packets / 4080 bytes |
| LAN PCAP | 120 records: 60 from primary `192.168.1.100`, 60 from other/iSCSI `192.168.192.100` |
| LAN layout | IP length 68, UDP application payload 40, offset 0, MF=0, DF=1, TTL=64 |
| WAN PCAP | 120 records = 60 complete fragment pairs |
| First emitted fragment | IP length 44, byte offset 24, MF=0, DF=0, TTL=63 |
| Second emitted fragment | IP length 44, byte offset 0, MF=1, DF=0, TTL=63 |
| Reverse order | 60/60; paired gaps about 29–136 microseconds, median about 88 microseconds |
| IPv4 checksums | LAN 120/120 valid; WAN 120/120 valid |
| Reassembled UDP | 60/60 lengths correct; 60/60 non-zero checksums valid |
| Payload preservation | 60/60 exact primary-LAN application-payload matches; zero matches to the other/iSCSI source |
| Unfragmented originals on WAN | zero |
| Packets from reflector | zero on LAN and WAN |
| Capture loss | zero kernel drops on both interfaces |

The `dvtws2` log contains 60 native `ipfrag2` calls, zero short-packet guard hits and no processing errors. All intercepted application payloads were 40 bytes, so the <=16-byte guard was not exercised.

## Media and restoration

The correlated console output reports both peers `Reconnecting`, no established call, 15 bitrate records per side, zero BWE, no reported errors and actual `tgcalls_exit=1`. This run has no `MEDIA_PASS`.

`result.txt` reports `RESTORE_OK`, signal 2 and no error. IPFW, PFIL and listening-socket snapshots are byte-identical before/after. Temporary rule 18990/listener 990 were removed, existing listener 989 remained, and outgoing IPv4 hook order returned from temporary PF→IPFW to the original IPFW→PF state.

The bounded verdict is **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`**, with **no `MEDIA_PASS`**.

## Standalone fragmentation conclusion

The corrected current-runtime reflector campaign now has on-wire-qualified standalone fragmentation at:

- ordered position 8;
- reverse position 8;
- reverse position 16;
- reverse position 24;
- reverse position 32.

Every fully correlated current-runtime run emitted the intended valid local-WAN serialization and received zero reflector packets. With no fresh independently working control, this remains `NO_REPLY_UNKNOWN`, not a causal provider `NETWORK_FAIL`. It is nevertheless enough to stop widening fragment positions: another split point would add little diagnostic value while repeating the same silent outcome.

## Next bounded family: fragmented fake plus qualified real fragmentation

Prepared file: **`tgvoice_fakefrag8_reverse24_postnat_v1.py`**, revision **`postnat-fakefrag8-reverse24-v1`**.

SHA-256: `db8d8a9e1e67c2df91a77462d244be37988bbda8cd674bca7c0b77d16d8cc03d`.

The first candidate keeps the just-qualified real reverse24 serialization unchanged and adds one fake before it:

1. fake UDP application payload: 40 zero bytes, matching the observed Hello payload length;
2. fake uses `badsum` so the reconstructed UDP checksum is intentionally invalid;
3. fake uses `ip_id=rnd` so it normally cannot share the real packet's IPv4 reassembly identity; archive analysis must reject/rerun the epoch if an accidental ID collision is observed;
4. fake itself is fragmented **ordered at UDP position 8**. This is required by the post-NAT interception contract: an unfragmented raw-sent fake could re-enter rule 18990, while both position-8 fake fragments fail `frag !mf,!offset` and bypass it;
5. the real Hello then uses the already-qualified guarded **reverse position 24** path and the intercepted original is dropped.

Pinned Zapret2 source supports `fake` with standard `badsum`, `ip_id`, `ipfrag` and raw-send arguments, and its raw-send fragmentation helper sends the fragment array before the original verdict. Sources:

- <https://github.com/bol-van/zapret2/blob/6b6c63e3385fa73f8af3be4a69171e947f5a319d/lua/zapret-antidpi.lua>
- <https://github.com/bol-van/zapret2/blob/6b6c63e3385fa73f8af3be4a69171e947f5a319d/lua/zapret-lib.lua>
- <https://github.com/bol-van/zapret2/blob/6b6c63e3385fa73f8af3be4a69171e947f5a319d/docs/manual.en.md>

Expected WAN output per 40-byte Hello is four fragments:

1. fake: IP length 28, offset 0, MF=1;
2. fake: IP length 60, offset 8, MF=0;
3. real: IP length 44, offset 24, MF=0;
4. real: IP length 44, offset 0, MF=1.

The fake pair must reassemble to a 48-byte UDP datagram with intentionally invalid checksum; the real pair must reassemble with a valid checksum and exact primary-LAN payload. There must be no unfragmented fake or real original and rule 18990 should still count only the 60 intercepted originals.

Python syntax and `--help` passed locally. The runner also performs the existing runtime-hash guard and `dvtws2 --dry-run` before changing PFIL hooks or adding the live rule. **No live fake-plus-fragment result exists yet.**

Raw PCAPs, peer/session tags and private logs are not committed. No plugin/package source change belongs to this evidence.

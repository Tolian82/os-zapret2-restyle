# Telegram Voice — post-NAT ordered position-8 fragmentation

**Status:** LOCAL WIRE QUALIFIED · CALL NOT ESTABLISHED · RESTORE_OK

**Test dates:** 2026-09-20–2026-09-21 UTC

**Recorded / owner correction:** 2026-09-22

**Scope:** temporary laboratory evidence; no plugin/package change

**Package identity:** `VERSION=0.5.0`, `PLUGIN_REVISION=3`

This record consolidates owner-supplied console results and packet/runtime archives. It does not claim a new test was executed while writing the documentation. Raw captures, peer/session tags and complete private logs are not committed.

Current task: [`START_HERE.md`](../../START_HERE.md). Interpretation: [research](../../research/TELEGRAM_VOICE_UDP.md). Runner contract: [laboratory architecture](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md).

## Outcome

The corrected runner produces the intended fragments on the local OPNsense WAN, but the call still fails. The final run emitted 60 complete ordered fragment pairs with valid IPv4 and reassembled UDP checksums. No packet returned from `91.108.13.10`; both peers stayed `Reconnecting`, BWE remained zero and the CLI returned 1.

Classification: **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`; no `MEDIA_PASS`**.

The owner explicitly states that `192.168.1.140` is no longer a working route. It is retired from the active plan and cannot provide a current independent control. The [September 5 success](2026-09-05-telegram-voice-fixed-reflector-control-pass.md) remains historical evidence for its older binary and epoch. No fresh independent working control is established here.

The current task is to obtain a repeatable media call through OPNsense in the rebuilt laboratory. Local wire correctness does not complete that task.

## Laboratory identity

| Item | Recorded value |
|---|---|
| Companion | TNAS, Docker container `tgvoice-lab`, existing Docker `host` network |
| Active executable | `/results/tgcalls_cli` |
| tgcalls source | `efd330ca04f74706024a5abdfb5b41f4e4dd1065` |
| Executable SHA-256 | `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc` |
| Engine/configuration | Caller and Callee `13.0.0`; command supplies no version or custom-parameter override |
| Fixed endpoint | `91.108.13.10:596`, UDP reflector mode |
| Test duration | 15 seconds per CLI run |
| Router | OPNsense; LAN `vtnet0`, WAN `vtnet1`, selected TNAS path via `192.168.1.2` |
| Runtime report | Owner-reported Zapret2 `v1.0.5.2`; executable reports `self-built version Sep 20 2026 16:04:47 lua_compat_ver 6` |
| Corrected runner | `tgvoice_ipfrag8_postnat_v2.py`, marker `postnat-nofrag-v2` |
| Temporary interception | IPFW rule 18990, divert listener 990 |
| Existing listener | Normal `dvtws2` remains listening on 989 |

Measured runtime hashes from the final archive:

| File | SHA-256 |
|---|---|
| `binaries/my/dvtws2` | `69ac3515d2357f567ca2d12753d71bbc7ff05aa2839d48ebb5667f1651761f7a` |
| `lua/zapret-lib.lua` | `b67a470f23b00a8d6e732c4e5135a39b224511e0b71809d5f4616adf62674980` |
| `lua/zapret-antidpi.lua` | `31c9dd75b0bd55e98e5306293f2be81e9d2ecadcbbf9157394ff37dcff7dc85a` |

The executable's build-time version string alone does not prove a Git tag. These hashes identify the measured bytes; `v1.0.5.2` is the owner's runtime-update report.

The [September 20 local P2P qualification](2026-09-20-telegram-voice-current-tgcalls-owner-live-pass.md) passed. That qualifies the rebuilt harness, not reflector reachability. The [unmodified OPNsense baseline](2026-09-20-telegram-voice-current-opnsense-baseline.md) separately showed 60 valid outbound Hello datagrams and zero replies.

## Test sequence and corrected defects

| Attempt | Local evidence | Meaning |
|---|---|---|
| Preparatory invocation / preflight | Owner first reported no `READY`; a later unbuffered invocation printed `ABORTED: Unexpected IPv4 output hooks: ['pf:default-out']; nothing changed` | Not a completed candidate. The reported abort is not a provider or media result. |
| September 20, pre-NAT ordered position 8 | 60 originals intercepted; 120 WAN fragments / 60 complete pairs, but all 60 reconstructed UDP checksums invalid after NAT | Local wire defect. No valid negative conclusion about fragmentation effectiveness. |
| September 21 13:24 UTC, first post-NAT implementation | Rule counted 120 packets / 5760 bytes: 60 originals plus 60 first fragments recaptured. WAN contained only 60 second fragments, offset 8 / MF=0 | Moving after NAT alone was insufficient. First-fragment recapture broke the candidate locally. |
| September 21 13:51 UTC, repeated old runner | Same missing-first-fragment behavior and 120 / 5760 counter; corrected revision marker/filter absent | Reproduced the old implementation, not the corrected v2 candidate. |
| September 21 14:11 UTC, `postnat-nofrag-v2` | Rule counted only 60 originals / 4080 bytes. WAN contained all 60 ordered pairs; every reconstructed UDP checksum validated | Local wire correction passed. No incoming reflector packet; CLI call still failed. |

The download was renamed to `tgvoice_ipfrag8_postnat_v2.py` at the owner's request so it cannot be confused with `tgvoice_ipfrag8.py`. Future changes need an equally distinguishable filename/revision in their evidence.

The final temporary profile selected the exact IPv4 endpoint/UDP port and all payloads, then used:

```text
--lua-desync=send:ipfrag:ipfrag_pos_udp=8
--lua-desync=drop
```

Reflector Hello is non-STUN; the paused STUN-only `_4` profile does not select these packets.

The rule shape was:

```text
18990 divert 990 udp from <wan-ipv4> to 91.108.13.10 596 out not diverted not sockarg xmit vtnet1 frag !mf,!offset
```

The unique ownership comment is omitted here. `frag !mf,!offset` selects only unfragmented originals; the first replacement fragment also needs exclusion even though its offset is zero. Plain `not frag` is insufficient for that purpose; see the [FreeBSD 15 `frag` matching definition](https://github.com/freebsd/freebsd-src/blob/releng/15.0/sbin/ipfw/ipfw.8).

PF translated the intact packet before fragmentation. The temporary output order was PF then IPFW; the original/restored order was IPFW then PF. Changing that hook order affects all outgoing IPv4 for the bounded window, while the divert rule itself remains narrow. Incoming and IPv6 hook order were not changed.

## Final capture findings

Final archive epoch: `20260921T141102Z-uejmp9tw`.

- Runner `READY`: `2026-09-21T14:11:02.880887Z`.
- LAN packet window: `14:11:15.102453–14:11:29.609156Z`.
- WAN packet window: `14:11:15.103336–14:11:29.610452Z`.
- Cleanup began at `14:11:43.218112Z` after signal 2, within the 120-second maximum.

| Measurement | Result |
|---|---|
| LAN observations | 120 packets: 60 from the primary TNAS address and 60 from its other/iSCSI address; only the primary 60 form the measured forwarded pairs |
| Original primary flows | Two flows, 30 datagrams each; 40-byte Hello payload, 48-byte UDP datagram, 68-byte IPv4 packet |
| WAN packet count | 120 fragments forming 60 complete pairs |
| First fragment | IPv4 total length 28, offset 0, MF=1 |
| Second fragment | IPv4 total length 60, offset 8 bytes, MF=0 |
| Fragment order | First then second for all 60 pairs; gaps 26–110 microseconds |
| IPv4 checksums | Valid for all 120 WAN fragments |
| Reassembled UDP checksums | Non-zero and valid for all 60 pairs |
| Reassembled application payload | Byte-identical to the corresponding primary LAN datagram in all 60 pairs |
| Forwarding fields | TTL 64 to 63; translated source address/ports; replacement DF cleared |
| Unfragmented WAN originals | None |
| Incoming packets from fixed reflector | Zero, including any non-UDP packet from that address in the capture |
| LAN/WAN kernel capture drops | Zero |
| Temporary rule counter | 60 packets / 4080 bytes |

These observations establish local OPNsense WAN output. The WAN is behind another private-address hop; this capture does not prove fragment arrival, checksum state or reassembly beyond that upstream device or at Telegram.

## Companion command and media result

Owner command on TNAS (Bash):

```sh
docker exec tgvoice-lab /results/tgcalls_cli \
  --mode reflector \
  --reflector 91.108.13.10:596 \
  --duration 15
echo "tgcalls_exit=$?"
```

The owner supplied repeated failing summaries. The final paired test reports:

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

Signaling messages emitted by this harness are bridged locally between its two instances. Their presence, 15 stats records, and `Errors: none` do not demonstrate a remote reflector response or a working media call.

## Restoration and its limits

The runner reports `RESTORE_OK`, `Error: none`, and no route modification. The saved IPFW rule layout, PFIL hooks and socket-listener state match before/after. The temporary rule was removed, output hook ordering restored, temporary listener 990 stopped, and existing listener 989 retained.

Normal rules 19000/19001 were already absent in these post-NAT pre-test snapshots, which contained only the default 65535 count/allow entries. Restoration therefore means returning to that measured initial state. It does not mean the normal Zapret rules were recreated or normal service forwarding was proven. Earlier session output showing those normal rules belongs to another snapshot.

## Interpretation and next boundary

The initial malformed runs diagnose local implementation defects. The corrected run resolves those defects, but does not restore a call. With no fresh independent working control, silence cannot distinguish provider filtering, fragment policy, upstream NAT/path behavior, endpoint availability or protocol/configuration mismatch. Do not label it proof that the endpoint is dead or that DPI is the identified cause.

Continue toward the current media-call objective using the corrected wire contract: validate installed reverse-order syntax, then isolate reverse position 8 and bounded alternate positions. Any engine/custom-parameter comparison is a separate source-guided epoch. Preserve actual pre-test routing; do not return to retired `192.168.1.140` as a presumed working control. A winner requires repeated `MEDIA_PASS`, followed by the real Windows/Android call gate.

## Private archive identities

These hashes identify the owner-supplied evidence without committing packet/session data.

| Archive | SHA-256 |
|---|---|
| `tgvoice-ipfrag8-20260920T201329Z-7_qoiclk.tar.gz` | `5f89b7a86515c151679cb95a367267a9e653fc5eb9b7645fc9d2f4a4a9e759c7` |
| `tgvoice-ipfrag8-postnat-20260921T132419Z-z9ddnt3i.tar.gz` | `59de3a8b0bbaa3b4f4b888e5f479636075e0d9b0a6ea9c6336092f75cfa3f393` |
| `tgvoice-ipfrag8-postnat-20260921T135152Z-qc2vudy4.tar.gz` | `35839fd803e935f897c36453c363d53e0760843e776ad95500071a4edb4e22aa` |
| `tgvoice-ipfrag8-postnat-20260921T141102Z-uejmp9tw.tar.gz` | `68929978c4c06992a19d348690e13bfdb085df74ef152356b6f37f5c63aa76ef` |

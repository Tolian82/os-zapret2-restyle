# Telegram Voice reverse position-8 run and owner-reported call establishment

**Status:** OWNER REPORTS CALL ESTABLISHED · TRAFFIC ATTRIBUTION OPEN · RESTORE_OK

**Test / owner correction date:** 2026-09-22

**Scope:** temporary console laboratory; no plugin/package change

## Subsequent clarification and separate repeat — recorded September 23

The owner identified the successful display as `docker exec tgvoice-lab /results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15`, followed by `echo "tgcalls_exit=$?"`. Its positive console summary was not supplied. The tool is therefore identified; timing, media qualification and attribution to this first empty archive remain open.

After reboot, a [separate reverse position-8 repeat](2026-09-22-telegram-voice-reverse8-postreboot.md) produced 60 valid fragment pairs during the measured CLI window but no replies or media. This later failed repeat does not disprove the earlier reported success. The historical next-evidence list below records the plan at the time of this first archive; the current handoff has advanced to guarded reverse position 32 in [`START_HERE.md`](../../START_HERE.md).

## Owner observation

After the reverse-run archive was inspected, the owner explicitly reported that **the call established and routing was correct at the time of the call**. Preserve both facts as owner observations. Empty endpoint-filtered captures do not refute that report, and do not justify diagnosing an incorrect route or an absent call.

The supplied archive contains no companion call log. The statement does not yet identify whether this was `tgcalls_cli` or a Windows/Android Telegram call, its actual endpoint/transport, or two-way media evidence. These are attribution questions, not a reason to discard the reported success. Earlier CLI failures belong to their own runs and must not be attached to this observation.

Current handoff: [`START_HERE.md`](../../START_HERE.md). Acceptance definitions: [laboratory architecture](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md).

## Runner and archive identity

- Runner: `tgvoice_ipfrag8_reverse_postnat_v1.py`, revision `postnat-reverse8-v1`.
- Runner SHA-256: `3ecb158f246074ce93ac70c87564d4f0b376e61d76b24bcaaa65543c659ab3f2`.
- Archive: `tgvoice-ipfrag8-reverse-postnat-20260922T201453Z-4pcjss9a.tar.gz`.
- Archive SHA-256: `5a5efba2cc087ee4e2585373d20214ff929b98a33f9efb189b21c6cf5cab35ea`.
- READY: `2026-09-22T20:14:53.344649Z`; cleanup began at `2026-09-22T20:15:24.643717Z` after Ctrl+C, approximately 31.3 seconds later.
- Installed binary and both Lua hashes match the [qualified September 21 ordered run](2026-09-21-telegram-voice-postnat-ipfrag8.md). The runner rejects a runtime mismatch before starting children or changing hooks/rules.

The packet-action change from the qualified ordered runner is:

```text
--lua-desync=send:ipfrag:ipfrag_pos_udp=8:ipfrag_disorder
--lua-desync=drop
```

The pinned [Zapret2 Lua source](https://github.com/bol-van/zapret2/blob/6b6c63e3385fa73f8af3be4a69171e947f5a319d/lua/zapret-lib.lua) implements reverse fragment emission. Source/offline validation passed before delivery, and the installed runtime accepted the profile during this run. Neither establishes that any live datagram was transformed.

## Scope and measured observations

Both tcpdump processes used **`host 91.108.13.10`**, on LAN `vtnet0` and WAN `vtnet1`. This is an endpoint-filtered capture, not a capture of every call or all client traffic. It includes TCP and all ports for that IPv4 address as well as UDP/non-initial fragments; a TCP or port change at that same address alone would not explain a missing capture.

Temporary IPFW rule 18990 selected only unfragmented outgoing IPv4 UDP from WAN address `192.168.80.251` to **`91.108.13.10:596`**, on `vtnet1`, with `frag !mf,!offset`, and diverted it to the owned listener on 990. The runner temporarily placed outgoing IPv4 IPFW after PF/NAT; that hook-order change affects all outgoing IPv4, while the fragmentation rule remains endpoint-specific. No route was changed.

| Evidence | Observation |
|---|---|
| LAN PCAP | 24-byte valid global header; zero packet records |
| WAN PCAP | 24-byte valid global header; zero packet records |
| Temporary rule 18990 | 0 packets / 0 bytes |
| Temporary dvtws2 | Profile loaded, listener started; no packet processing logged |
| Capture loss | Both tcpdump logs report zero packets dropped by kernel |
| Restoration | IPFW, PFIL and listening-socket snapshots identical before/after; `RESTORE_OK`, no recorded error |

The normal dvtws2 listener on 989 remained. Temporary rule/listener 18990/990 were removed. Rules 19000/19001 were absent before and after; restoration does not assert that the normal Zapret interception rules were re-enabled.

The tcpdump `received by filter` statistics are not counts of endpoint packets saved in these files and must not be substituted for PCAP records.

## Interpretation and next evidence

Record **call establishment and correct routing as reported by the owner**, alongside **no observed traffic to the selected reflector in these captures and no hits on the reverse-fragmentation rule**. This is neither a demonstrated reverse-fragmentation success nor a negative media/network result. The archive cannot determine the path that carried the successful call. In particular, `NO_REPLY_UNKNOWN` from an earlier run must not replace this new observation.

The immediate task is to correlate that success before changing strategies:

1. Identify the calling tool/client and obtain the existing output or observation from this same successful call. For the CLI, retain both peer states, BWE/stats, endpoint, duration and exit status; for Telegram, record two-way audio, peer/P2P setting and duration.
2. Match the call's actual flow and timing to the capture scope. A different endpoint/address family or an unmatched capture window is a possibility to investigate, not an established diagnosis. Do not demand another route check as if the owner's correction had not been supplied.
3. If existing evidence is insufficient, repeat the successful conditions with a bounded observation of the selected client's actual flow. Changing capture scope does not authorize wider interception. Keep the current runner/runtime and successful conditions until this attribution is resolved.
4. Once the flow is identified, compare unchanged traffic and reverse fragmentation one factor at a time where applicable, and verify repeatable media. Formal `MEDIA_PASS`/`CALL_PASS` remains pending the corresponding evidence; new split positions are not the immediate next step.

Raw PCAPs, session/peer tags and private logs are not committed. This record adds no live test beyond the supplied archive and owner statement.

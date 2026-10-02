# 2026-10-02: real Telegram Windows → Android call, P2P disabled — good audio, UDP interception observed, UDP media **not** proven

**Status:** owner-live **REAL_CALL_AUDIO_REPORTED_GOOD / VOICE_IPFW_CAPTURE_PASS / UDP_MEDIA_NOT_OBSERVED**; **NOT** verified `CALL_PASS`, `MEDIA_PASS`, verified UDP relay or proof that the experimental STUN fake enabled the call.  
**Source:** owner-reported Windows → Android real call, both peers with P2P disabled and callee in another city; owner-provided OPNsense status/IPFW/PFIL output before/after the call and two original UDP PCAP uploads, read and independently cross-correlated.  
**Date:** 2026-10-02; PCAP timestamps UTC 04:54–04:58 (OPNsense local UTC+3 ≈07:54–07:58).  
**Source privacy:** the original PCAPs were uploaded into the private investigation conversation; **not uploaded to this public GitHub repository** because a real call's packets and identifiers may be sensitive. The tables below give sanitized, reproducible summaries and exact SHA-256 identifiers. The owner should retain the original PCAPs privately for future correlation.

## Outcome and why the distinction matters

The caller used **Telegram Desktop on Windows**, recipient used **Telegram on Android** in **another city**, and **P2P was disabled on both clients**. The owner reported: connection was good; voice was heard clearly without interference. This is a **real successful user-experience observation** and should never be dropped or rewritten as a failed call. The owner did **not explicitly report a directional two-way speech test**, nor establish the actual Android network connection; do not add those as measured facts.

Simultaneously, the UDP-only captures contain **no inbound Telegram-server UDP** and no sustained bidirectional UDP media. The Windows client sent 90 repeated identical non-STUN 40-byte requests to one Telegram endpoint and 9 STUN requests to another; all 99 originals appeared on WAN after source NAT. The STUN-oriented Voice helper apparently produced exactly 18 extra 16-byte zero-payload packets (two per STUN). The IPFW rule `19000` counters increased from **0/0** to **99 packets / 6624 bytes**, which matches the original requests **exactly**: `90 × (20-byte IPv4 + 8-byte UDP + 40-byte payload) + 9 × (20 + 8 + 28) = 6120 + 504 = 6624 bytes`. The fakes are extra output packets; they are not counted as new original matches by the `not diverted` rule.

**Interpretation:** the owner successfully communicated with good reported audio and the selected Voice **UDP interception was definitely exercised**. However, because no Telegram UDP replies or sustained two-way UDP were captured, it is **not demonstrated that the audio traveled through the captured Zapret2 UDP flow**. An alternative, possibly Telegram TCP fallback over the already configured proxy, is plausible but **not observed or proven** here. The captures deliberately selected UDP only and cannot establish which TCP sessions carried any media. Do **not** attribute call success causally to Zapret2/STUN, or conclude UDP is blocked by the provider without an independent working control.

This direct real-call observation is **not interchangeable** with the separate controlled TNAS `tgcalls_cli` fixed-reflector oracle (`91.108.13.10:596`), whose current repeatable `MEDIA_PASS` gate remains open. The real call used *different server addresses/ports*, and an audible call alone does not fulfill the project's planned `CALL_PASS` requirement for sustained **bidirectional UDP**.

## Owner's exact baseline: active Voice and firewall

Before the call, `configctl zapret telegram_voice_status` reported:

```text
telegram_voice_poc.requested=on
telegram_voice_poc.effective=on
telegram_voice_poc.service=running
telegram_voice_poc.active_profile=on
telegram_voice_poc.strategy=stun-zero-fake-repeats-2
telegram_voice_poc.scope=telegram-ipv4-all-udp-ports
telegram_voice_poc.table=zapret2_tgvoice
telegram_voice_poc.table_present=yes
telegram_voice_poc.table_entries=14
telegram_voice_poc.stage_table=zapret2_tgvoice_stage
telegram_voice_poc.stage_table_present=no
telegram_voice_poc.rule=19000
telegram_voice_poc.rule_packets=0
telegram_voice_poc.rule_bytes=0
```

The before/after IPFW state, **with no owner-reported service changes**:

| Rule | Before packets / bytes | After packets / bytes | Meaning |
|---|---:|---:|---|
| `19000` | 0 / 0 | **99 / 6624** | `divert 989 udp from any to table(zapret2_tgvoice) out not diverted not sockarg xmit vtnet1` |
| `19001` | 406 / 444578 | 509 / 461938 | Ordinary TCP ports `80,443,5222,8888` diverted; increase alone **does not prove media over TCP, parent routing, or even Telegram attribution**. |
| `19002` | 0 / 0 | 0 / 0 | Ordinary UDP `80,443,5222,8888` capture unused in this observed interval. |

After the call the full Voice status still reported `requested=on`, `effective=on`, `service=running`, `active_profile=on`, `table_present=yes`, `table_entries=14`, no staging table, `rule=19000`, **`rule_packets=99`**, **`rule_bytes=6624`**. The helper did not crash or silently disable itself. **Do not confuse active helper with a successful UDP call.**

The owner also supplied *current* `pfilctl heads` output (not extrapolated from September). Relevant IPv4 order:

```text
inet In:  pf:default-in  → ipfw:default
inet Out: ipfw:default  → pf:default-out
```

Thus the tested current outbound hook order was **IPFW before PF**. No hook-order changes were performed in this real-call trial. Do not describe GUI versus helper as using separate pre/post-NAT hooks: both existing IPFW rule families occupy the same outbound hook; they differ by match predicate.

## Captures: exact identity, scope and timing

Both original PCAPs were supplied by the owner after the call; the first includes Windows-client UDP and the second broad OPNsense WAN UDP (except DNS/53).

| Property | LAN | WAN |
|---|---|---|
| Owner file name | `tgvoice-real-call1-lan.pcap` | `tgvoice-real-call1-wan.pcap` |
| Interface | `vtnet0` | `vtnet1` |
| Capture expression | `host <Windows-LAN-client> and udp` | `udp and not port 53` |
| Size | **55,770 bytes** | **18,038 bytes** |
| Owner tcpdump packet count | **414 captured**, 0 kernel drops | **156 captured**, 0 kernel drops |
| UTC packet range | 04:54:37.816–04:58:28.331 (230.5 seconds) | 04:54:54.751–04:58:29.721 (215.0 seconds) |
| SHA-256 | `8c60830033d69bddd46d0e9987692745ef139dc185b01079714e366f3068452b` | `7d3552c0c58959a09b8285e331356675036bc066428f1dad0c4557257f69ea70` |

**Scope caution:** these are **UDP-only** captures. LAN also includes unrelated local mDNS, Windows name service and DNS; WAN also includes multicast/local broadcast, NTP and two non-IPv4 Ethernet frames. The total captured packet counts are **not all Telegram**. Both captures covered the observed Telegram UDP window, but the actual audible-media transport is not visible here if it used TCP or an unobserved interface.

### Correlated Telegram UDP flows (original payloads verified byte-identical across LAN/WAN)

| Observed traffic | LAN from Windows | WAN after NAT | Observation |
|---|---|---|---|
| Non-STUN 40-byte datagrams to `91.108.9.88:597` | **90**, Windows ephemeral port `49631`; UTC 04:55:06.362–04:55:51.005 | **90**, WAN source `192.168.80.251:52948` | All 90 WAN payload hashes match the 90 LAN originals; the same 40-byte payload was retransmitted throughout the ~44.6-second interval. **No UDP reply** from this endpoint on either capture. |
| Recognized 28-byte STUN datagrams to `91.108.9.100:1400` | **9**, Windows ephemeral port `49630`; UTC 04:55:06.362–04:55:38.116 | **9** matching originals from `192.168.80.251:64901` | All 9 payload hashes match; **no UDP reply** from this endpoint. |
| Additional 16-byte zero payloads to `91.108.9.100:1400` | **0** | **18**, on the same WAN NAT tuple as STUN originals | Two packets per STUN request, consistent with the current `stun-zero-fake-repeats-2` profile. Not proof of reception or DPI impact at Telegram. |

The 90 non-STUN payloads were **byte-identical on LAN and WAN**: the current STUN-only profile does **not** transform that 40-byte reflector Hello. The 9 STUN payloads also matched as originals; 18 zero-16 extras went out on WAN, preceding/near the corresponding originals. The IPFW counter precisely corresponds to the 99 original destination-matching requests, not to the extra fakes.

Crucially, the WAN capture contains **zero inbound UDP from either Telegram endpoint and no other observed inbound Telegram UDP**, while the owner reports clean audible voice. That combination is the reason the result must be recorded as **real audible call with undetermined media transport**, not `CALL_PASS`.

## Safe follow-up; do not destroy the accepted observation

1. Preserve the **working** Windows/Android P2P-disabled configuration, the owner's existing Squid/sing-box/parent TCP setup and current Zapret2 configuration. Do **not** change NAT hook order, Voice profile or reboot automation based on the audible result alone.
2. Next **bounded** owner-approved real call: capture TCP metadata separately on both LAN/WAN (enough to correlate with the already-working parent proxy) **alongside simultaneous UDP captures**; keep the call private. Avoid public raw PCAPs; redact parent credentials/session identifiers and potentially identifying endpoints in evidence. Record explicit sound direction (Windows→Android, Android→Windows) and call established duration.
3. Compare a deliberate **helper OFF versus ON** case only if required and safe, with identical proxy/routing, preserving the known-good state and full restoration. Current call proves the helper is exercised, **not that it is necessary** for good audio. Do not infer alternative strategy efficacy or particular provider filtering from missing UDP replies alone.
4. Do not mark the distinct current `tgcalls_cli` `MEDIA_PASS` accepted unless its own qualified fixed-reflector evidence independently meets its defined criteria.

The [current oracle and acceptance definitions](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [GUI-vs-helper/NAT source audit](../../architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md), [previous October 1 UDP no-reply evidence](2026-10-01-telegram-traffic-policy-and-voice-control.md) and [live operations](../../architecture/TELEGRAM_LAB_OPERATIONS.md) remain authoritative in their separate domains.

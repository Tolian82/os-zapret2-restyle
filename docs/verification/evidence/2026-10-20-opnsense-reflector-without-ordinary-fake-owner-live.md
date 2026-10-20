# 20 October 2026 — OPNsense non-STUN Reflector without ordinary Strategy #4 fake: no reply, original restored

**Proof level: owner-live, installed `os-zapret2-restyle-0.5.5_7`; one 15-second self-contained pinned `tgcalls_cli` run, one simultaneously bounded WAN capture on OPNsense `vtnet1`, saved/runtime restoration checked.** This is a one-factor **ordinary fake enabled vs disabled** control; no real Telegram SOCKS5 voice user or human counterparty involved.

## Change gate and initial GUI uncertainty

The operator's first edit to remove `--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2` from ordinary Strategy #4 produced GUI `Результат применения неизвестен`. Subsequent read-only checks confirmed that both saved Config `/conf/config.xml` and `runtime-v2/traffic.conf` **still contained** original fake (MATCHING_PROFILES=1, ORIGINAL_FAKE=YES, ANY_LUA_DESYNC=YES, UNKNOWN_PAYLOAD=YES). After a page refresh, a successful Apply with the original unchanged text was reported, then the owner explicitly removed only the fake line again and applied. This time owner-live readback gave:

```text
=== SAVED CONFIG ===
ORIGINAL_FAKE=NO
=== ACTIVE RUNTIME ===
--filter-l3=ipv4
--filter-udp=596-599
--ipset=/usr/local/etc/zapret2/runtime-v2/managed/ipset-telegram.txt
--payload=unknown
--new
=== SERVICE ===
zapret is running
```

This verifies the desired **no-fake configuration on both saved and effective planes**. The earlier generic GUI message's exact backend cause is still **unattributed**; do not infer data corruption or a confirmed Apply product bug from it. The owner did not intentionally alter native Voice STUN #1, routes, NAT, PF/IPFW or proxy settings.

## Same-endpoint no-fake result

The OPNsense-controlled test preflight confirmed `PROFILE_NO_FAKE=PASS`, `zapret is running`, and `ipfw 19000` divert baseline `0 packets / 0 bytes`. TNAS route `91.108.13.10 from 192.168.1.100 via 192.168.1.2 dev ovs_eth1` was verified by SSH, and pinned existing Docker image/binary hash and host mode validated before running two local Caller/Callee instances with `--mode reflector --reflector 91.108.13.10:596 --duration 15`.

```text
=== Call Summary ===
Duration: 15s
Mode: reflector (91.108.13.10:596)
Caller state: Reconnecting
Callee state: Reconnecting
Call established: no
BWE non-zero: no
Errors: none
TGCALLS_EXIT=1
SSH_EXIT=0

=== WAN TRAFFIC SUMMARY ===
SAMPLE=1792508511.122400 IP 192.168.80.251.54136 > 91.108.13.10.596: UDP, length 40
SAMPLE=1792508511.124513 IP 192.168.80.251.9877 > 91.108.13.10.596: UDP, length 40
WAN_TX_TOTAL=60
WAN_TX_ORIGINAL40=60
WAN_TX_FAKE16=0
WAN_TX_OTHER=0
WAN_RX=0

=== IPFW AFTER ===
19000 60 4080 divert 989 udp from any to table(zapret2_voice_telegram) out not diverted not sockarg xmit vtnet1

=== SERVICE AFTER ===
zapret is running

=== CAPTURE STATUS ===
listening on vtnet1, link-type EN10MB, snapshot length 96 bytes
60 packets captured
71 packets received by filter
0 packets dropped by kernel
```

The 60 captured output datagrams had the two shown OPNsense WAN NAT source ports and original UDP 40-byte lengths, not the prior two zero16 fakes per 40-byte Hello. `tcpdump` received-by-filter is capture metadata, **not 11 proven additional lost packets**. Zero incoming packets from this reflector were observed during this run. The absence of a reply on WAN does not identify whether the cause is external router, upstream transport, NAT/return path, PF, IPFW/engine interception, or server handling.

## Same-oracle comparison

| Signal | OPNsense original fake enabled (previous owner-live) | OPNsense fake removed (this run) |
|---|---:|---:|
| Captured original UDP40 egress | 60 | 60 |
| Captured UDP16 fake egress | 120 | **0** |
| WAN reply `91.108.13.10:596` | 0 | 0 |
| Reflector call established | no | no |
| BWE nonzero | no | no |
| IPFW 19000 diverted UDP | 60 / 4080 bytes | 60 / 4080 bytes |

The one-factor hypothesis **“removing Strategy #4 fake suffices to establish the OPNsense path” is rejected by this controlled run**. It does not demonstrate that faking is generally unhelpful for non-STUN traffic or that active shared IPFW/divert/native engine is semantically the same as no plugin interception. Earlier independent alternate-hop control through pfSense `192.168.1.140` using the **same** CLI/binary/reflector delivered both Established, BWE >0 and exit0; however there is no concurrent pfSense WAN PCAP/NAT/egress proof, so it does **not** isolate exactly where the OPNsense loss occurs.

## Restored state

Immediately after this one test, owner restored the exact original Strategy #4 fake line through the **standard GUI Apply**; on-device read-only verification:

```text
=== SAVED ===
FAKE_RESTORED=YES
=== RUNTIME ===
ACTIVE_FAKE_RESTORED=YES
=== SERVICE ===
zapret is running
```

**RESTORE=PASS for Config/runtime Strategy #4 and overall service state**. No further edit or repeat of this known-failed no-fake scenario is justified absent a changed variable. The native Voice STUN profile #1 was not intentionally modified, but the shown post-test readback does not independently attest its entire profile.

## Exactly one next research boundary

**Read-only compare** OPNsense and pfSense **actual route-to-reflector, egress interface/gateway and outbound NAT/PF rule selection** to identify structural differences before any additional 15-second reflector run or shared IPFW bypass. The positive pfSense path is not presumed equivalent to the OPNsense external WAN `192.168.80.251`. Measure only available metadata; avoid dumping proxy credentials, arbitrary firewall rules, changing routes/NAT/Voice/Podkop/youtubeUnblock or disabling all Zapret2. Choose any next active network test based on that comparison, not guesswork.

Version remains `v0.5.5_7`; this repository update is **documentation only**.

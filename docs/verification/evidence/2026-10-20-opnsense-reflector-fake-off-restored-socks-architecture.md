# 2026-10-20 — OPNsense non-STUN Reflector fake-OFF control and correction of comparison scope

**Owner-live result on installed `os-zapret2-restyle-0.5.5_7`, 15 seconds, after a successful ordinary Strategies GUI Apply removing the fake command only from the `UDP 596–599` profile. No real Telegram client call; no SOCKS5 in the reflector generator.**

## Verified one-factor WAN result

```text
=== PREFLIGHT ===
zapret is running
PROFILE_NO_FAKE=PASS
=== IPFW BEFORE ===
19000 0 0 divert 989 udp from any to table(zapret2_voice_telegram) out not diverted not sockarg xmit vtnet1
=== PINNED REFLECTOR TEST ===
TNAS_ROUTE=91.108.13.10 from 192.168.1.100 via 192.168.1.2 dev ovs_eth1 uid 0
TGCALLS_START=YES
Caller state: Reconnecting
Callee state: Reconnecting
Call established: no
BWE non-zero: no
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
60 packets captured
71 packets received by filter
0 packets dropped by kernel
```

Prior same-reflector run with original ordinary Strategy #4 fake enabled had **60 original UDP40 + 120 zero16 UDP fake, WAN RX=0, call=no**. Removing the fake made **WAN fake=0** and kept original UDP40 on WAN; media still failed. This rejects only the sufficiency claim “turning off ordinary fake makes the OPNsense direct reflector succeed”. Does not prove DPI bypass or remote-server receipt. The global IPFW count attests interception, not media success.

## Restored state confirmed by the owner

After the bounded trial, the original exact command was restored using standard GUI Apply:
```text
=== SAVED ===
FAKE_RESTORED=YES
=== RUNTIME ===
ACTIVE_FAKE_RESTORED=YES
=== SERVICE ===
zapret is running
```
**RESTORE PASS** for ordinary Strategy #4 saved Config and live runtime; no persistent test modification remains. Native Voice STUN #1 was not intentionally edited. No further no-fake runs necessary.

Before the successful edited Apply, a GUI attempt reported `Результат применения неизвестен`. The original Strategy #4 remained in both saved Config and active runtime, and a later Apply after page refresh of an unmodified field showed success, but retained fake. The owner then explicitly deleted the fake line, applied successfully, and demonstrated `ORIGINAL_FAKE=NO` in Config and runtime. **No proven general Apply regression** follows from this sequence; the transient UI uncertainty is not root-caused.

## Owner's topology correction — do not turn gateway testing into SOCKS testing

Owner clarified the intended **actual Telegram client** paths:

- pfSense `192.168.1.140` selects Telegram **TCP/TLS** for a remote HTTP parent `185.203.117.88:33128`; this proxy mechanism does **not** forward arbitrary UDP or prove youtubeUnblock receives it.
- OpenWrt `192.168.1.236`, VM on TNAS, provides the **explicit application SOCKS5 service `:1070`**. The user intentionally configures Telegram to use this SOCKS5; only with this application setting does the expected **OpenWrt processing path** become a meaningful test for Telegram. GOST/Podkop handle selected TCP/TLS to the remote parent and youtubeUnblock acts on qualifying UDP. The *actual* Telegram voice UDP transport through GOST SOCKS5 (e.g. UDP ASSOCIATE) is **still not independently traced**. Do not treat the mere setting of SOCKS5 as an observed UDP packet path.
- OPNsense `192.168.1.2`: intended separate paths — Telegram TCP/TLS to the **same remote parent** through its own configured Squid/sing-box chain, and Telegram UDP through **native Zapret2**, including STUN/ordinary profile matching. Actual complete client TCP/TLS and voice UDP wire routes on OPNsense must be qualified independently.

`tgcalls_cli --mode reflector` **always uses direct non-STUN UDP**, independent of the application SOCKS5 setting. Earlier same-binary/same-reflector **pfSense `.1.140` MEDIA_PASS** and **OpenWrt `.1.236` direct gateway FAIL** remain valid empirical **direct-route** observations; **neither represents actual SOCKS5-mediated Telegram audio**, nor proves that youtubeUnblock participated. A change of default/gateway route is not a replacement for setting SOCKS5 in Telegram.

**Follow-up focus (no new experiment executed):** do not repeat `.1.140` gateway control or launch another NAT/PF “pfSense vs OPNsense” gateway comparison as the leading step. Independently determine **which Telegram traffic actually uses SOCKS5 `:1070` on OpenWrt and whether a SOCKS UDP ASSOCIATE/request produces qualifying UDP on its WAN** without needing a human interlocutor. Compare this to the OPNsense native Voice STUN/ordinary-UDP contract only after each path is identified. Do not disable Podkop or modify live network to force a result. The synthetic OpenWrt STUN20 to public Google WAN (6 UDP64 + original UDP20) already proves independent fake egress only, not application-proxy UDP.

Docs-only record; package stays `v0.5.5_7`. No plugin source/runtime changes.

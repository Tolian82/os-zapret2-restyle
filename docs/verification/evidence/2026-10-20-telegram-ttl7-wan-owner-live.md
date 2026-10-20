# 20 October 2026 — Telegram ordinary Strategy #4 fake TTL=7 WAN trial

**Evidence level:** OWNER-LIVE on OPNsense `os-zapret2-restyle-0.5.5_7`, Zapret2 engine `v1.0.5.2`. Owner supplied console output of the live 15-second TNAS Docker `tgcalls_cli --mode reflector` experiment, WAN packet sample, `tcpdump` summary, service status and restoration check. This is a completed **selective fake TTL manipulation** experiment; **not** Telegram media/call success.

## Conditions

- Ordinary Strategy #4 initially matched UDP `596–599`, payload `unknown`, with action `--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2`.
- Owner applied **only** `:ip_ttl=7` to that action via GUI; effective `/usr/local/etc/zapret2/runtime-v2/traffic.conf` displayed the modified line at 31. Native `--name=voice-telegram` remains a separate profile at line 1 (full Voice argument equality was not independently printed).
- Installed engine `v1.0.5.2`; `zapret-antidpi.lua` contains `function fake` and calls `rawsend_payload_segmented`; `zapret-lib.lua` `apply_fooling` uses `fooling_options.ip_ttl` to set the generated packet TTL. Code-path existence was observed, packet behavior was later measured.
- Target `91.108.13.10:596`, SSH TNAS `192.168.1.100:9222`, Docker host `tgvoice-lab`; TNAS route still `via 192.168.1.2 dev ovs_eth1`. Existing common runtime and IPFW rule 19000 were preserved. No upstream gateway, route, STUN Voice profile, PFIL or IPFW rule edits.
- Captured at approximately **05:04:17 appliance local time** on WAN `vtnet1`; PCAP remains private on OPNsense at `/tmp/tgvoice-ttl7.19jgBq/wan.pcap`.

## Owner-observed result

| Property | Observation |
|---|---|
| Fake UDP egress | **120** packets, payload **16 bytes**, **TTL=7** |
| Original UDP egress | **60** packets, payload **40 bytes**, **TTL=63** |
| Packet sample | Repeated fake, fake, original; from `192.168.80.251` to `91.108.13.10:596`; sampled packets report `[udp sum ok]` |
| IPFW 19000 | Before **0/0**, after **60 packets / 4080 bytes** |
| WAN incoming target UDP | **0** packets from `91.108.13.10:596` within capture |
| ICMP sample | Empty; no ICMP decoded in displayed capture |
| Generator | 15 seconds; Caller and Callee `Reconnecting`, `Call established: no`, BWE non-zero `no`, `TGCALLS_EXIT=1`, `SSH_EXIT=0` (SSH script completed, **not** call success) |
| Post-run restoration | Owner used GUI to restore original Strategy #4; `grep -nF` of active traffic.conf prints line 31 **without `:ip_ttl=7`**; `configctl zapret status` = `zapret is running` |

## Conclusions and limits

**PASS — selective fake TTL behavior:** the original payload flows out with TTL 63 while both 16-byte fake packets flow out with TTL 7, on the same ordinary UDP/596 traffic. The restored original action is visible in active runtime after the test.

**NO_REPLY / CALL_FAIL:** no observed inbound UDP, no established call, no media evidence. This does **not** locate the DPI, prove whether the TTL=7 fakes crossed it, establish reachability of UDP/596 from outside the appliance, or demonstrate that the endpoint is a qualified working reflector/responder. ICMP hop 12 from earlier traceroute is not evidence of UDP/596 responder behavior. The 15-second reflector Hello is non-STUN and did not test the native STUN profile; prior A3a tested only STUN outbound toward an unqualified UDP/3478 endpoint.

**Next bounded action:** read-only establish whether the historical `91.108.13.10:596` endpoint and the current `tgcalls_cli` reflector Hello contract can be expected to return UDP on this path (using source/protocol and existing evidence). Only design another live comparator with a qualified responder/endpoint and a clear acceptance observation. Do **not** repeat TTL7 or change TTL values without new evidence; do not repeat A2/A3a, alter native Voice STUN, route, proxy or upstream gateway.

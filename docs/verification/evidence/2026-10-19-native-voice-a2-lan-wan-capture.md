# 2026-10-19 — native Telegram Voice A2: simultaneous LAN/WAN packet capture

**Proof level:** OWNER-LIVE; console output supplied by owner from installed `os-zapret2-restyle-0.5.5_1`. A2 is wire observation, **not** validated Telegram STUN, Telegram reflector reachability, MEDIA_PASS, or CALL_PASS. Existing native common `dvtws2` and IPFW were not changed.

## Conditions and provenance

- Capture time: 19 October 2026, approximately 15:55 local OPNsense time; window approximately 15 seconds plus margins.
- Capture files remain on owner-controlled OPNsense under `/tmp/tgvoice-a2.589zgP/{lan,wan}.pcap`. Raw PCAP contents were **not** uploaded to GitHub or this evidence file.
- Simultaneous passive `tcpdump -i vtnet0` (LAN) and `tcpdump -i vtnet1` (WAN), capture expression `udp and host 91.108.13.10 and port 596`. Snap length 160; independent writers.
- Generator over pre-existing SSH to TNAS: `timeout -k 5 60 docker exec tgvoice-lab /results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15`.
- Before `ipfw -a show 19000`: `0 packets / 0 bytes`; after: `60 packets / 4080 bytes`. Rule `divert 989 udp from any to table(zapret2_voice_telegram) out not diverted not sockarg xmit vtnet1`.
- The previous A0 confirmed plugin `0.5.5_1`, service running, Telegram saved ON, engine/supervisor verified, voice state ready, 14 target IPSET networks including `91.108.13.10`, target route from TNAS through `192.168.1.2 dev ovs_eth1`, Docker true/host and expected `tgcalls_cli` SHA-256. This same-session evidence does not need to be re-run absent drift.

## Observations from owner's command output

| Signal | Direct observation | Supported interpretation |
|---|---|---|
| LAN PCAP | `180` `tcpdump` packet summary lines | Traffic for the selected target observed at `vtnet0` |
| LAN observed sources | `192.168.192.100`, `192.168.1.100`, `100.124.244.1`, each to `91.108.13.10:596`; shown sample payload length 40 | Multiple local source-address candidates were emitted; distribution and acceptance for all 180 require offline PCAP parsing |
| WAN PCAP | `180` packet summary lines; shown examples are **outbound only** from `192.168.80.251` to `91.108.13.10:596` | Actual outbound WAN capture proven, not remote delivery |
| WAN repeated triple | For each shown original UDP length 40, two earlier UDP length 16 packets, same shown NAT source port and IP ID, ttl 63 | Consistent with `fake:...:repeats=2`, but exact bytes/causal attribution need offline PCAP inspection; do not classify all packets by length without counting the saved capture |
| UDP checksum | `tcpdump` reports `[udp sum ok]` for displayed WAN packets | Captured frames have valid observed checksum; not a claim of delivery beyond OPNsense |
| Inbound reply | No inbound packets appear in the displayed WAN first/last samples; total capture lines match an apparent all-outgoing sequence | No observed return in the provided trace excerpt; verify complete WAN PCAP direction count before concluding zero replies |
| Generator summary | Caller/Callee `Reconnecting`; `Call established: no`; BWE non-zero `no`; no local reported errors; `TGCALLS_EXIT=1` | Test failed to establish a call; wrapper `SSH_EXIT=0` only means SSH script returned success |

The 40-byte UDP payload belongs to the historical *Reflector Hello* test, **not** a protocol-qualified STUN request. This matters because saved native Telegram settings were described as `--filter-l7=stun --payload=stun`; WAN presence of 16-byte packets alone does not prove which exact runtime profile matched or that legitimate STUN negotiation succeeded.

## Decision and one next operation

A2 establishes WAN-side egress and a repeated shorter-packet pattern. No further package, SSH, route, container, service or IPFW readiness repetitions are justified absent a change. The immediate next action is **offline, read-only analysis of the already saved A2 PCAPs**, counting all LAN source addresses, WAN direction/UDP lengths, comparing bytes of the two short packets with the expected 16-byte fake and establishing original Hello signature and stream attribution. Cross-check only the effective live process arguments when necessary to attribute the observed manipulation. Do **not** perform another live reflector run merely to reproduce the same 60/4080 result.

After the offline A2 attribution, A3 is a separate validated STUN packet/responder trial. Any controlled strategy change requires its own explicit, evidence-based hypothesis and measurement. A5 actual bidirectional audio call remains open.

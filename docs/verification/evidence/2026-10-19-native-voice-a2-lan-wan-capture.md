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
| LAN observed sources | Six source address:port tuples, **30 original packets each**, all three source IPs `192.168.192.100`, `192.168.1.100`, `100.124.244.1`; UDP payload 40 in printed samples | Three candidate addresses and two source ports per address. Only two translated original UDP streams appear on WAN; which LAN tuples they correspond to is not yet proven |
| WAN PCAP | `180` packet summary lines; shown examples are **outbound only** from `192.168.80.251` to `91.108.13.10:596` | Actual outbound WAN capture proven, not remote delivery |
| WAN repeated triple | **120** outbound UDP packets of 16-byte payload + **60** outbound original 40-byte packets; shown `16,16,40` order, NAT source `192.168.80.251` and two NAT source ports | Both 16-byte payloads in provided hex are **all-zero**, IP TTL 63, UDP checksum valid. Pattern equals configured fake zero16 repeats=2, but the originating dvtws2 profile is still unattributed |
| UDP checksum | `tcpdump` reports `[udp sum ok]` for displayed WAN packets | Captured frames have valid observed checksum; not a claim of delivery beyond OPNsense |
| Inbound reply | Complete PCAP filtering confirmed **0** `src 91.108.13.10:596` packets in WAN and LAN | No remote return was observed at either capture point; not proof of packet fate beyond WAN |
| Generator summary | Caller/Callee `Reconnecting`; `Call established: no`; BWE non-zero `no`; no local reported errors; `TGCALLS_EXIT=1` | Test failed to establish a call; wrapper `SSH_EXIT=0` only means SSH script returned success |

The 40-byte UDP payload belongs to the historical *Reflector Hello* test, **not** a protocol-qualified STUN request. The supplied original packet's UDP payload begins `00 8c 47 3a a0 93 d8 e2`; at offset 4 it has `a0 93 d8 e2` instead of STUN Magic Cookie `21 12 a4 42` (RFC 8489 §5, https://www.rfc-editor.org/rfc/rfc8489.html#section-5). Native Voice requires `--filter-l7=stun --payload=stun`, whereas ordinary Strategy profiles may also match the Hello. The emitted zero16 fake **must not** yet be attributed to Voice without checking the effective merged `traffic.conf` selectors/profile in use. This matters because saved native Telegram settings were described as `--filter-l7=stun --payload=stun`; WAN presence of 16-byte packets alone does not prove which exact runtime profile matched or that legitimate STUN negotiation succeeded.

## Decision and one next operation

A2 establishes WAN-side egress and a repeated shorter-packet pattern. No further package, SSH, route, container, service or IPFW readiness repetitions are justified absent a change. The initial offline packet accounting and hex analysis are complete (LAN six source tuples ×30; WAN 60 original +120 zero16; 0 replies). The immediate next action is **read-only examination of the effective merged `/usr/local/etc/zapret2/runtime-v2/traffic.conf` selectors** to attribute Hello handling to native `voice-telegram` or a separate ordinary profile; if necessary, use saved PCAP for NAT-flow-to-LAN-candidate correlation. No new media experiment is required for this. Cross-check only the effective live process arguments when necessary to attribute the observed manipulation. Do **not** perform another live reflector run merely to reproduce the same 60/4080 result.

After the offline A2 attribution, A3 is a separate validated STUN packet/responder trial. Any controlled strategy change requires its own explicit, evidence-based hypothesis and measurement. A5 actual bidirectional audio call remains open.

## Active merged profile attribution (owner-live inspection, same installed `0.5.5_1`)

The owner read the selectors in `/usr/local/etc/zapret2/runtime-v2/traffic.conf`, without Apply or restarting the service:

- **Profile 1:** `--name=voice-telegram`, `--filter-l3=ipv4`, managed Telegram IPSET, `--filter-udp=*`, `--filter-l7=stun`, `--payload=stun`, `--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2`.
- **Profile 4:** ordinary Strategy, `--filter-l3=ipv4`, `--filter-udp=596-599`, identical managed Telegram IPSET, `--payload=unknown`, `--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2`.
- Other active profiles (2, 3, 5) cover HTTP/TLS and are not candidates for this UDP/596 experiment.

The captured 40-byte Reflector Hello has no standard STUN magic cookie. Its `unknown` type, destination port 596, two matching zero16 fakes and correct target IP identify **ordinary Profile 4 as the packet-processing candidate**. This is stronger than the earlier payload-only inference, although there is no per-packet engine log attributing profile IDs. Native Voice **Profile 1 was not exercised as STUN** by the A2 reflector run. No changes to effective profiles were performed.

**Next single bounded trial:** A3a sends one RFC 8489 valid 20-byte STUN Binding Request from Docker host-mode TNAS bound to `192.168.1.100`, to `91.108.13.10:3478` while passively capturing OPNsense WAN UDP/3478. Port 3478 lies outside Profile 4's `596-599`; it is inside native Voice Profile 1's `--filter-udp=*` and same Telegram IPSET. Expected local wire indication of native STUN processing: one original STUN payload 20 plus two 16-byte zero fakes; no response is promised from this **unverified** port/server. This is an outbound-path profile isolation test only, **not A3 STUN_RX qualification**, which separately requires a known STUN responder. Do not run another reflector A1/A2 or edit routing, IPFW, PFIL, Proxy or Config for A3a.

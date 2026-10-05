# 2026-10-03 — Docker A2 checksum-valid fakes: correct local WAN wire; no reflector reply

**Evidence:** OWNER-LIVE ONE-SHOT A2 fixed-reflector Docker epoch · `CONFIG_PASS / WIRE_OK / NO_REPLY_UNKNOWN` · **NOT** `MEDIA_PASS`.

**Historical-plan clarification, 2026-10-05:** the final "Next evidence gate" paragraph below records the proposal before the owner's October 3 same-ISP correction. Its mandatory independent-path prerequisite is superseded; the measurements remain unchanged. A healthy same-endpoint control is optional causal diagnosis. Current execution follows [START_HERE](../../START_HERE.md) and the [RTC/ICMP plus limited-fake-TTL plan](../../architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#next-experiment--limited-fake-ttl-planned-not-run), which has no new live result yet.

The owner supplied one **private** `a2-20261003T133150Z-5o6Gta.tgz`, verified SHA-256 `f0c7c551bc279278efa6e3914c3ed3c3d7ff5f0de4ef0c5184e788c7818b6bd3`. All archived SHA256SUMS entries passed. No raw PCAP, private runtime XML, keys or proxy credentials are committed. The merged `voice-one-command-v4-a1-a2` runner explicitly recorded `candidate=A2`, pinned fixed `91.108.13.10:596`, 15-second fresh Docker CLI epoch 13:31:53–13:32:08 UTC.

## Configuration and execution

Saved ordinary GUI model was readable and contained exactly the A2 fake (`saved_gui_A2=YES`, `saved_gui_A1_fake=NO`). One matching effective Telegram-IPSET/UDP 596–599/`unknown` profile used exactly `fake:payload=unknown:blob=zero16:repeats=2` with no `:badsum`. Separate STUN-only Voice helper stayed ON/running with 14 destination-table entries. Manual existing TNAS route guard and independent Linux `from` route verification passed for the pinned target and existing separate HTTPS target via OPNsense. Docker `tgvoice-lab` was already running in host mode, pinned `/results/tgcalls_cli` SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc` passed. No user TCP/proxy or route changes were made by this experiment.

## Independent packet checks

Raw full-snaplen Ethernet/IPv4/UDP and post-NAT pseudoheader checksums were recomputed independently from the two complete PCAP files:

| Property | LAN | WAN |
|---|---:|---:|
| Captured pinned-target IPv4 datagrams | 60 | 180 |
| Genuine unmodified 40-byte Hello | 60 | 60 |
| 16-byte zero A2 fake UDP payloads | 0 | 120 |
| Valid IPv4 checksums | 60/60 | 180/180 |
| Genuine valid UDP checksums | 60/60 | 60/60 |
| **A2 fake valid UDP checksums** | — | **120/120** |
| Inbound pinned-target IP/UDP/ICMP packets | 0 | 0 |
| Fragmented datagrams | 0 | 0 |

Two peer streams sent 30 originals each. The LAN genuine payload multiset exactly equalled the post-NAT WAN genuine multiset. All 60 genuine WAN datagrams were immediately preceded by two zero16 A2 fakes on the same NATed tuple and IPv4 ID: 60/60 correct `[fake, fake, genuine]` triplets. First fake to original elapsed **11.9–56.0 μs**; WAN TTL=63, DF on all 180; LAN genuine TTL=64, DF on all 60. Both tcpdump logs recorded zero dropped packets. Destination-scoped Voice IPFW rule19000 increased +60 packets/+4080 bytes; lower-priority common UDP/596–599 rule19002 stayed zero as expected; outgoing IPv4 PFIL hooks were IPFW→PF.

The current engine-13 peer outputs both remained **Reconnecting**, BWE was zero, **call not established**, `tgcalls_exit=1`. Wrapper `ACQUIRED_MEDIA_UNVERIFIED` / wrapper exit 0 means only acquisition success. These WAN captures do **not** prove remote delivery or identify a unique drop site.

Private evidence SHA-256 for owner-side matching only:
- LAN: `9b4e0c59d855aec09f7f7f8cb961253d4b28fa7ba71f40ac184d05172ef9e4f3`
- WAN: `40c3606bc3a2c60f2a700e050ff3f1a329337b9f629173768e13ea3f6c91dd8c`
- CLI: `a722cf857b3a1f86e51e87c64d114d2eb30ce240684c88c77e74484addb55693`

## Comparison and bounded decision

[The matched A1 Docker epoch](2026-10-03-docker-a1-wire-pass-no-reflector-reply.md) also emitted 60 intact originals and 120 preceding zero16 fakes but with **deliberately bad** fake UDP checksums; both candidates received **zero** observed pinned-reflector replies and failed media. The *checksum-validity change alone* was insufficient in these captured epochs. Neither conclusion establishes remote reflector readiness nor proves what a specific provider/DPI discarded.

**Next evidence gate:** qualify a fresh independent **currently working same-`91.108.13.10:596`** fixed-target path for the **same pinned CLI** before choosing a speculative third fake or fragmentation profile. No current alternate path has been qualified, and the historical `192.168.1.140` route is retired; do not reintroduce it. Preserve the working TCP/proxy lab, A2 GUI/helper state, current route and automatic one-archive procedure until a safe independent-control design is established. No live product/package integration or human call per candidate.

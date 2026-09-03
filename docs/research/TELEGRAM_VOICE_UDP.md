# Telegram voice / UDP DPI-bypass research

**Status:** RESEARCH CURRENT · PHASE A/B COMPLETE · ZERO-FAKE NETWORK FAIL · RUNTIME PIN CONFIRMED · PHASE C EMULATION ORACLE SELECTED · `_4` PAUSED
**Opened:** 2026-08-19
**Research conclusion:** 2026-08-19
**Phase A owner-live observation:** 2026-08-28
**Phase B source PoC:** 2026-09-01
**Phase B owner-live result:** 2026-09-02
**Ordered IPv4-fragmentation design:** 2026-09-02
**Installed runtime pin:** Zapret2 `v1.0.4` / `2c21faa80e1acb71ddceb8b49176f266b7d33f05`
**Phase C emulation design:** 2026-09-03
**Updated:** 2026-09-03
**Owner instruction:** Telegram voice/call traffic over UDP is the current selected research task.
**Pinned starting `main`:** `62e9a62e484d7a983b9b3f91ec672bbe96f684f3`
**Research-boundary merge:** `9bc225ea457583ffec696e393c8ba697798369f6`
**Package identity on `main`:** `VERSION=0.5.0`, `PLUGIN_REVISION=3` — bounded Phase B runtime/lifecycle passed; zero-fake provider/network gate failed. Remote `_4` source branch exists but is unpublished and paused.

## Executive conclusion

Telegram voice should **not** be modeled as “Telegram TCP plus one known UDP port.” Current Telegram calls have a Telegram API signaling channel plus a WebRTC-based transport. Telegram explicitly supplies call endpoints with IP address, UDP port and STUN/TURN role, while its call protocol also supports direct UDP P2P and UDP reflector paths. Therefore a call may use dynamically selected UDP destinations/ports that are separate from the ordinary Telegram TCP connection.

Phase A established that **audible call success is not proof that Telegram UDP works**. With P2P disabled on both clients, the test client sent TURN Allocate requests and Telegram Reflector Hello packets to Telegram-managed addresses, received no UDP reply on either candidate, yet the call established with two-way audio and no perceived delay while the existing TCP/SOCKS proxy path remained bidirectional. The bounded inference is TCP/proxy fallback; the encrypted stream was not decrypted, so this record does not attribute media to one specific TCP connection.

Phase B then tested the exact official zero-fake/repeats=2 hypothesis on the same provider path. A clean remote-participant OFF/ON/OFF comparison proved that the plugin intercepted the intended Telegram-destination UDP, selected STUN, and emitted exactly two valid 16-zero-byte datagrams before each of 9 TURN Allocate requests. The ON state still received zero TURN/STUN replies and produced no sustained bidirectional Telegram UDP. Runtime/lifecycle qualification passed, but provider/network effectiveness failed. This directly falsifies the usefulness of the exact zero-fake baseline on the tested path without identifying the provider's internal mechanism.

A separate generic STUN exchange with `141.101.90.1:3478` returned bidirectional responses in the same WAN environment. Thus neither UDP nor STUN framing was universally blocked; the unresolved discriminator is Telegram-specific destination/direction/path policy versus a more selective payload/relay classifier.

The original next candidate was source-designed from Zapret2's UDP fragmentation path: re-send each selected STUN datagram as two ordered IPv4 fragments at UDP position 8, then drop the unfragmented original. The owner then confirmed that the installed Zapret2 `v1.0.4` runtime exposes this primitive. Remote branch `v0.5.0_4-telegram-voice-ipfrag` preserves that implementation, but no PR, CI, merge, package or network result exists and the branch is now paused.

The original **stateful STUN-desynchronization** hypothesis was technically justified but is weakened by the live evidence. Current upstream `bol-van/zapret2` ships `init.d/custom.d.examples.linux/50-stun4all`, which recognizes STUN in the Linux firewall on all addresses/ports and applies native Zapret2:

```text
--payload=stun
--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2
```

The exact strategy was emitted correctly and still received no Telegram TURN reply. Generic public STUN on the same router path had produced bidirectional responses, while both Telegram TURN and reflector endpoints were outbound-only. This raises destination-IP/direction/routing policy, stateless inspection, relay policy or another Telegram-specific blackhole above simple stateful STUN classification. The capture cannot identify which one. No payload-only Zapret2 technique can repair a pure destination-IP block.

The Linux/OpenWrt `50-stun4all` integration cannot be copied literally to OPNsense. Its important property is **kernel-side STUN signature filtering before NFQUEUE**. Zapret2 upstream explicitly documents that FreeBSD `ipfw` lacks raw-payload filtering. Passing all UDP through `dvtws2` merely to discover STUN would create a broad kernel/userspace interception path and is not acceptable as the default production design.

**The project shape remains hybrid and evidence-first, but the next step is now an oracle rather than another package.** Offline replay can predict interception and exact wire transformation only. A standards-correlated TURN probe can prove a returned STUN path but not media. The official pinned `TelegramMessenger/tgcalls` CLI can create caller/callee instances with local signaling and route bidirectional WebRTC media through a real Telegram UDP reflector with TCP disabled. One final real P2P-disabled remote call remains the product gate.

Do **not** make global UDP/443 blocking part of the Telegram Voice default. That is a generic QUIC suppression/fallback measure, can interfere with WebRTC/STUN/TURN using port 443, and current `youtubeUnblock` Telegram-call troubleshooting explicitly found overlapping QUIC-drop/STUN handling to be harmful unless separated.

Do **not** reinterpret the existing Generic UDP result as Telegram-call success. Reuse its lifecycle, fixed-endpoint and restoration components only behind a separate Telegram Voice runner or explicit external-probe mode with protocol-aware results. The current architecture is [`TELEGRAM_VOICE_EMULATION_LAB.md`](../architecture/TELEGRAM_VOICE_EMULATION_LAB.md).

## Owner-provided starting evidence and sources

### `Waujito/youtubeUnblock`

Source: <https://github.com/Waujito/youtubeUnblock/>

Owner observation/comment:

- OpenWRT-oriented DPI-bypass project.
- In the owner's observed configuration, adding Telegram domains is sufficient for Telegram including voice calls to work.

Research result:

- Current `youtubeUnblock` has a dedicated `--udp-stun-filter` specifically described as useful for voice chats.
- Maintainer Waujito added STUN filtering for Telegram calls without binding it to ports in issue #265/#266 and recommended disabling Telegram P2P for reliable testing.
- The same discussion records a conflict where QUIC/“quick drop” overlapped the STUN path; the maintainer recommended a separate UDP/STUN section.
- Therefore the observed working OpenWrt behavior is **not evidence that a Telegram domain list by itself identifies voice traffic**. The project has a separate payload-aware UDP path, and P2P can independently make a call appear fixed.

Relevant issue: <https://github.com/Waujito/youtubeUnblock/issues/265>

### `remittor/zapret-openwrt`

Source: <https://github.com/remittor/zapret-openwrt>

Owner observation/comment:

- OpenWRT GUI/integration around Zapret/Zapret2 deployments.
- Community configurations use custom firewall/daemon hooks for Telegram/Discord voice connectivity.

The repository's currently tracked classic-zapret `zapret/custom.d/50-script.sh` uses the same STUN kernel selector but classic `--dpi-desync=fake --dpi-desync-repeats=2`. The owner supplied the native Zapret2 form from a Zapret2 installation. The equivalent native form is independently confirmed by current primary `bol-van/zapret2` upstream, so the project must continue to use the Zapret2 syntax rather than translate classic `nfqws1` options by analogy.

Observed UDP/443 example:

```sh
zapret_custom_firewall_nft() {
    nft add rule inet fw4 raw_prerouting udp dport 443 drop comment "zapret2-block-quic"
}
```

Conclusion: this is **QUIC suppression**, not a Telegram voice strategy. It may force protocols with a TCP fallback away from QUIC, but Telegram call endpoints have an explicit server-provided port and are not defined as UDP/443-only. A global rule can also discard legitimate STUN/TURN/media that happens to use UDP/443. It must not be bundled into the Telegram Voice default.

Owner-supplied native Zapret2 STUN example:

```sh
# STUN4ALL (Discord audio, Telegram calls)
NFQWS_OPT_DESYNC_STUN="${NFQWS_OPT_DESYNC_STUN:---payload=stun --lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2}"

alloc_dnum DNUM_STUN4ALL
alloc_qnum QNUM_STUN4ALL

zapret_custom_daemons() {
    local opt="--qnum=$QNUM_STUN4ALL $NFQWS_OPT_DESYNC_STUN"
    do_nfqws $1 $DNUM_STUN4ALL "$opt"
}

zapret_custom_firewall() {
    local f='-p udp -m u32 --u32'
    fw_nfqws_post $1 "$f 0>>22&0x3C@4>>16=28:65535&&0>>22&0x3C@12=0x2112A442&&0>>22&0x3C@8&0xC0000003=0" "$f 44>>16=28:65535&&52=0x2112A442&&48&0xC0000003=0" $QNUM_STUN4ALL
}

zapret_custom_firewall_nft() {
    local f="udp length >= 28 @ih,32,32 0x2112A442 @ih,0,2 0 @ih,30,2 0"
    nft_fw_nfqws_post "$f" "$f" $QNUM_STUN4ALL

    # MTProto fix — принудительный перехват Telegram IP (TCP 443)
    nft add rule inet fw4 zapret2_postrouting ip daddr @zapret-ip-user tcp dport 443 counter nft_fw_nfqws_post_hook 200
}
```

Conclusion: the STUN portion is technically justified and native Zapret2. The appended MTProto/TCP interception is a different problem and is outside this voice-only scope because ordinary Telegram TCP already travels through the owner's external proxy.

Community issue #520 is retained only as anecdotal evidence because it mixes broad port ranges, Telegram/WhatsApp IPs and classic-zapret options and explicitly says the strategy was adapted with AI assistance: <https://github.com/remittor/zapret-openwrt/issues/520>

### Primary Zapret2 upstream

Repository: <https://github.com/bol-van/zapret2>

Manual: <https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md>

Discussions: <https://github.com/bol-van/zapret2/discussions>

Official STUN helper: <https://github.com/bol-van/zapret2/blob/master/init.d/custom.d.examples.linux/50-stun4all>

Upstream announcement explaining the helper's design intent: <https://github.com/bol-van/zapret/discussions/1716>

Current upstream facts used by this research:

- `stun` is a native recognized L7/payload class in Zapret2.
- The official `50-stun4all` uses the 16-zero-byte fake with `repeats=2`.
- `fake()` sends a separate generated packet/group and does not suppress the original packet.
- Checksums are normally reconstructed correctly unless an explicit bad-checksum option is requested.
- UDP fake is useful only against stateful DPI; IP fragmentation is another possible UDP technique.
- The author states that kernel signature recognition exists specifically to avoid intercepting whole UDP ports/all ports just to find STUN.
- FreeBSD `ipfw` lacks raw-payload filtering, so the Linux kernel-selector design is unavailable directly on OPNsense.

## Telegram call traffic model

Primary Telegram sources:

- modern call transport: <https://core.telegram.org/api/end-to-end/video-calls>
- WebRTC connection object: <https://core.telegram.org/constructor/phoneConnectionWebrtc>
- call protocol flags: <https://core.telegram.org/constructor/phoneCallProtocol>
- current Telegram network CIDRs: <https://core.telegram.org/resources/cidr.txt>

### Signaling versus media/connectivity

Modern Telegram one-to-one calls have two distinct channels:

1. **Telegram API signaling** — call setup/control data delivered through the Telegram API. In the owner's topology this is already carried through the external TCP proxy path and is not the bypass target.
2. **WebRTC-based transport** — Telegram's current documentation explicitly describes the transport channel as WebRTC-based. `phoneConnectionWebrtc` includes `stun` and `turn` flags plus an IP address and a server-provided `port`.

`phoneCallProtocol` additionally exposes `udp_p2p` and `udp_reflector`, confirming that direct peer UDP and Telegram-reflector UDP are valid call paths.

### What STUN does and what it does not do

STUN is primarily part of NAT traversal/connectivity establishment. RFC 8489 defines a 20-byte STUN header whose first two message-type bits are zero and whose magic cookie is `0x2112A442`.

The Linux `50-stun4all` selector is therefore looking for a standards-shaped STUN UDP datagram rather than a Telegram hostname:

- UDP length at least 28 bytes = 8-byte UDP header + 20-byte minimum STUN header;
- STUN message-type high bits satisfy the STUN framing rule;
- STUN message length is aligned as required;
- magic cookie equals `0x2112A442`.

After connectivity is established, actual encrypted voice/video transport is not simply “more STUN.” This distinction matters: if the provider disrupts STUN classification, fixing STUN may restore the call; if the provider blocks or shapes the later encrypted media/relay path, a STUN-only strategy will not be sufficient.

### Dynamic ports and destinations

There is no protocol basis for treating one fixed UDP port as the universal Telegram-call port. The WebRTC endpoint object carries an explicit `port`, and P2P can use a peer destination that is not part of Telegram infrastructure.

Community ranges such as `590-1400,3478` are useful empirical evidence — including reports for MTS — but they are **not a protocol contract** and must not be hard-coded as the universal Telegram definition.

Current official Telegram CIDRs recorded during this research include:

```text
91.108.56.0/22
91.108.4.0/22
91.108.8.0/22
91.108.16.0/22
91.108.12.0/22
149.154.160.0/20
91.105.192.0/23
91.108.20.0/22
185.76.151.0/24
2001:b28:f23d::/48
2001:b28:f23f::/48
2001:67c:4e8::/48
2001:b28:f23c::/48
2a0a:f280::/32
```

The plugin's current managed `Telegram IPs` target is IPv4-only, so the first proposed PoC is intentionally IPv4-only. IPv6 must be treated as a separate extension if live evidence shows that the test client uses it.

## Why the zero STUN fake can work

The exact internal classifier behavior of a provider DPI is not observable from the public configuration, so the mechanism below is an evidence-based inference rather than a universal guarantee.

Zapret2 `fake()` sends the decoy separately and still permits the real STUN packet to be sent. Without an explicit bad-checksum option the generated packet gets a normal reconstructed checksum. The official helper's 16 zero bytes do not form a valid STUN message and do not contain the STUN magic cookie.

The likely intended effect is therefore:

1. stateful DPI observes a preceding UDP packet with the same flow tuple but payload that does not look like STUN;
2. its flow classification/parser state is moved away from the signature path it would otherwise apply to the following STUN request;
3. the endpoint ignores the meaningless decoy and receives the original standards-valid STUN packet.

This aligns with upstream's explicit statement that UDP fake helps stateful DPI but not stateless DPI. The **16-byte length and repeats=2 should be treated as the upstream baseline, not as mathematically required Telegram values**. Provider-specific tuning may still be necessary.

## Why global UDP/443 drop is the wrong default

Dropping UDP/443 is useful in a different class of problem: disabling QUIC/HTTP/3 so software falls back to TCP. It is not a direct desynchronization attack on Telegram call STUN/media.

Reasons not to use it as the Telegram Voice default:

- Telegram supplies call endpoint ports dynamically.
- A STUN/TURN endpoint may legitimately be reachable on port 443.
- Global UDP/443 drop affects browsers and other QUIC/HTTP/3 applications unrelated to Telegram.
- `youtubeUnblock` Telegram-call troubleshooting records that overlapping QUIC-drop and STUN handling caused failures until the STUN path was separated.

Project decision: **no Telegram-specific UDP/443 drop in the recommended MVP**. If a generic QUIC-block feature is ever added, it belongs to an independent advanced network-control scope, default OFF, with explicit collateral-impact warning.

## OPNsense / FreeBSD constraint

This is the central platform difference from OpenWrt.

Zapret2 upstream documents that FreeBSD `ipfw` cannot filter on raw packet payload. Its normal example therefore diverts traffic by protocol/port. Passing packets between kernel and `dvtws2` userspace has non-trivial cost, and upstream explicitly warns about intercepting entire flows when only a few packets are needed.

Current `os-zapret2-restyle` production code matches that model:

- `backend/ports.sh` extracts only `--filter-tcp=` and `--filter-udp=` port/range artifacts from the unified strategy;
- `backend/firewall.sh` creates `ipfw divert` rules from those port artifacts;
- `backend/generator.sh` then gives the already-intercepted packets to the single generated `dvtws2` strategy;
- the current managed Telegram target is a dvtws IPSET file, not an `ipfw` lookup table.

Consequently, merely adding this to `Traffic Strategy` is insufficient:

```text
--payload=stun
--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2
```

Without an `ipfw` rule that actually diverts the relevant dynamic-port UDP packet, `dvtws2` never sees it.

FreeBSD 15 `ipfw` does support address lookup tables and `lookup dst-ip <table>` matching. That gives the plugin a bounded way to intercept **all UDP destination ports for Telegram-owned IPv4 ranges** without intercepting all Internet UDP.

## Recommended OPNsense architecture

### Decision: hybrid

Use a **protocol-aware automatic oracle plus one final assisted real call**. Preserve the existing Generic UDP contract, but reuse its lifecycle components in a separate Telegram Voice runner or explicit external-probe mode.

Do not add global all-UDP interception, do not make a broad community port list the default, and do not bundle the Linux/WebRTC companion into the OPNsense package.

### Phase A — owner-live observation complete

Phase A was completed on 2026-08-28 on the owner's live OPNsense path. The confirmed run used a Windows 11 client, P2P disabled on both call participants, both participants on the same LAN, the existing Telegram TCP/SOCKS proxy unchanged, and no Telegram Voice-specific helper or source change.

Owner-observed call result:

- the call established;
- audio worked in both directions;
- no delay was perceived.

The client-scoped LAN capture and concurrent PF/socket snapshots showed a different UDP result:

| Destination | Classification | Outbound | Inbound | Observation interval |
|---|---|---:|---:|---|
| `91.108.9.100:1400` | TURN Allocate request | 9 packets / 252 UDP payload bytes | 0 | `16:59:13.381499Z`–`16:59:45.131757Z` |
| `91.108.9.40:597` | Telegram Reflector Hello | 90 packets / 3,600 UDP payload bytes | 0 | `16:59:13.381553Z`–`16:59:57.925200Z` |

Both destinations are inside Telegram-managed IPv4 space. The PF snapshot independently showed outbound-only states for both candidates. No direct/private-peer UDP candidate appeared in this confirmed P2P-disabled capture.

At the same time, several client-to-local-SOCKS TCP flows remained active. Captured SOCKS CONNECT targets included Telegram DC addresses `149.154.167.41` and `149.154.167.51` on ports 80/443. One long-lived bidirectional SOCKS stream overlapped almost the whole call capture and carried 51 client-to-proxy packets / 11,023 TCP payload bytes and 68 proxy-to-client packets / 15,314 TCP payload bytes. A new TCP setup burst began about 197 ms before the first relay UDP attempts.

Therefore Phase A establishes:

1. relay UDP establishment failed no later than the observed TURN/reflector exchange because neither candidate returned a packet;
2. the successful audible call was masked by the already-working TCP/SOCKS fallback path;
3. the test does **not** distinguish stateful STUN DPI classification from stateless UDP filtering, relay-IP policy or another upstream blackhole;
4. the observed destination ports are evidence from one call, not a stable Telegram port contract;
5. Phase B must prove a UDP-path change with packets and counters; sound alone is not an acceptance signal.

Full redacted evidence record: [`2026-08-28-telegram-voice-phase-a-live-observation.md`](../verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md). The raw PCAP is intentionally not committed because it contains private addressing, ephemeral ports and proxy metadata.

#### Zapret2 classification boundary revealed by Phase A

The 40-byte flow to the reflector matches Telegram `tgcalls` [`ReflectorPort::SendReflectorHello()`](https://github.com/TelegramMessenger/tgcalls/blob/2faee3b5524f54d56c91c2058c00e11c656a74b3/tgcalls/v2/ReflectorPort.cpp#L309-L360), including its repeated hello behavior. It is **not STUN**: it has no RFC 8489 magic cookie.

The inspected Zapret2 v1.0.4 detector [`IsStunMessage()`](https://github.com/bol-van/zapret2/blob/2c21faa/nfq2/protocol.c#L1459-L1465) requires the STUN cookie and framing checks. Consequently, the official `--payload=stun` zero-fake baseline can select the 28-byte TURN Allocate requests but will not select the 40-byte Telegram Reflector Hello packets; those remain non-STUN/pass-through traffic in the proposed first PoC.

This does not invalidate the minimal STUN PoC: restoring TURN allocation may be sufficient to establish a native UDP relay path. A Telegram-reflector-specific detector or desync action is a separate hypothesis and must not be added unless the STUN PoC restores TURN replies but still fails the bidirectional UDP-media criterion.

### Phase B — bounded source PoC implemented; zero-fake network gate failed

The `0.5.0_3` source candidate implements a temporary/plugin-owned IPv4 `ipfw` address table populated from the same normalized Telegram CIDRs already used by `<IPSET:telegram>`.

It installs one plugin-owned outbound rule with these semantics:

```text
UDP + WAN out + not diverted + destination IP in Telegram Voice table
    -> divert to the existing dvtws2 divert socket
```

This rule has **no destination-port restriction** but remains bounded by Telegram destination ranges.

It prepends a high-priority dvtws2 profile with these semantics:

```text
filter the selected flow with --filter-l7=stun and guard the Lua instance with --payload=stun
limit target to Telegram IPSET as defense in depth
apply native upstream fake: 16 zero bytes, repeats=2
pass non-STUN Telegram UDP unchanged
```

The PoC uses the existing production `dvtws2` process/divert socket. Its generated profile is first, before the resolved user strategy, so a broad user UDP profile cannot steal a recognized STUN flow. `--filter-l7=stun` and `--payload=stun` are deliberately not treated as aliases: the first participates in profile selection, while the second gates the Lua instance inside that profile.

The helper keeps port extraction separate from effective profile assembly. The ordinary `tcp-ports.txt` / `udp-ports.txt` artifacts are derived from `traffic-user.conf`, while `dvtws.args` receives the helper-prefixed `traffic.conf`. Consequently `--filter-udp=*` widens interception only through the separate Telegram-destination IPFW rule; it does not create a global UDP `1-65535` rule.

Implementation/control details:

- request marker: `/var/run/zapret2-telegram-voice-poc.enabled` (ephemeral, therefore OFF after reboot);
- active/staging tables: `zapret2_tgvoice` and `zapret2_tgvoice_stage`, replaced with an atomic IPFW table swap;
- helper rule: first plugin-owned rule `19000` (`RULE_BASE`); ordinary port rules shift behind it only while ON so an overlapping user UDP port cannot bypass the helper counter;
- enable: `configctl zapret telegram_voice_enable`;
- observe: `configctl zapret telegram_voice_status`;
- disable/rollback: `configctl zapret telegram_voice_disable`;
- status exposes requested/effective/profile/service states, active/staging table presence, active entry count, helper rule number and its packet/byte counters;
- enable/disable use the existing lifecycle lock and transactional reconfigure path; failed rule installation swaps the previous table back, and later rollback restores the prior active tree, table and rule snapshot.

This is intentionally a temporary CLI/configd surface rather than a future product GUI.

Phase B acceptance requires all of the following:

- the Telegram Voice `ipfw` rule counter increments for the captured relay attempt;
- the exact generated STUN profile is active and the WAN capture shows the two separate 16-zero-byte fake datagrams before the original TURN/STUN request;
- at least one inbound TURN/STUN reply returns;
- a sustained bidirectional Telegram UDP flow appears after establishment;
- disable/rollback removes the helper rule, table/profile state and returns counters/traffic to baseline.

A call that remains audible only through TCP fallback while UDP stays outbound-only is **not** a Phase B pass.

#### Phase B owner-live runbook

Use the exact testing package built from this source candidate. Keep both Telegram clients on the same controlled topology, disable P2P on both, leave the existing TCP/SOCKS proxy unchanged, and do not change unrelated zapret2 strategies during the cycle.

1. Confirm the normal service is complete with `configctl zapret status`.
2. Force the PoC OFF with `configctl zapret telegram_voice_disable`, then save `configctl zapret telegram_voice_status`. OFF must report `requested=off` and `effective=off`; the helper form of rule `19000` and `zapret2_tgvoice` must be absent (ordinary port rule `19000` may exist).
3. Start bounded LAN and WAN captures for the test client/call interval. Keep the PCAP private; record only redacted counts, endpoint families and timing in repository evidence.
4. Enable with `configctl zapret telegram_voice_enable`, immediately save `configctl zapret telegram_voice_status`, and record the initial `rule_packets` / `rule_bytes` values.
5. Place a real call with P2P still disabled. Exercise two-way speech long enough to distinguish setup probes from sustained media.
6. Save status again and calculate the helper-rule counter delta. Inspect the WAN capture for the original TURN/STUN request, two separate 16-zero-byte fake datagrams, an inbound TURN/STUN response, and any later sustained bidirectional Telegram UDP flow.
7. Disable with `configctl zapret telegram_voice_disable`; save final status and verify removal of the Telegram-table form of rule `19000`, both helper tables and the helper profile from the effective runtime. The ordinary port rules must return to their default numbering.
8. Repeat the OFF/ON/OFF cycle before product acceptance.

The status command proves requested/runtime/table/rule state and interception counters. On-wire fake packets plus the unchanged exact generated profile prove that the STUN Lua action ran; the IPFW counter by itself proves interception only.

#### Phase B owner-live result

The exact published `v0.5.0_3` package was exercised on OPNsense 26.7.3_8 with a Windows 11 client, a remote participant, P2P disabled on both Telegram clients, and the existing TCP/SOCKS proxy unchanged.

The selected clean comparison was:

| State | TURN Allocate / STUN | Reflector Hello | On-wire fake | Inbound Telegram UDP | Sustained bidirectional UDP |
|---|---:|---:|---:|---:|---:|
| A — helper OFF | 9 outbound | 90 outbound | 0 | 0 | no |
| B — helper ON | 9 outbound | 90 outbound | 18 zero datagrams | 0 | no |
| C — helper OFF | helper state removed | helper state removed | none generated | returned to baseline | no B-only path remained |

For every B-state TURN request, WAN order was exactly `zero16 -> zero16 -> original`; WAN IPv4/UDP checksums were valid. The reflector traffic remained unchanged, demonstrating correct STUN/non-STUN discrimination. The dedicated IPFW counter incremented, and disable removed the active/staging tables and helper profile/rule while preserving the running service.

Result:

- implementation/runtime/lifecycle: **PASS**;
- provider/network effectiveness: **FAIL**.

Full redacted record: [`2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md`](../verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md).

The failure means that increasing fake repeats is not evidence-based. At the Phase B boundary it did not justify adding an unmeasured production reflector action to the same PoC. It also did **not** test or disprove a reflector-specific strategy: `--filter-l7=stun` and `--payload=stun` left every Reflector Hello unchanged. The packet pattern is compatible with stateless destination-IP/direction filtering, relay-policy blocking, payload inspection unaffected by the fake, or another upstream blackhole; the capture cannot distinguish those mechanisms. The later Phase C media oracle makes the reflector path a separate, measurable candidate family.

### Phase B2 — ordered IPv4 fragmentation candidate design

#### Primary-source basis

The installed-runtime line used by this project is release-based: `setup.sh` selects a stable `bol-van/zapret2` tag and builds it on the appliance. The previously pinned Zapret2 v1.0.4 source commit `2c21faa80e1acb71ddceb8b49176f266b7d33f05` and current upstream commit `0b8182d24a887059a628d7266577c4ba8e9b8f2d` expose the same native pattern:

```text
--lua-desync=send:ipfrag:ipfrag_pos_udp=8
--lua-desync=drop
```

Primary references:

- [Zapret2 v1.0.4 manual — standard IP fragmentation](https://github.com/bol-van/zapret2/blob/2c21faa80e1acb71ddceb8b49176f266b7d33f05/docs/manual.en.md#standard-ipfrag);
- [Zapret2 v1.0.4 blockcheck2 QUIC fragmentation candidates](https://github.com/bol-van/zapret2/blob/2c21faa80e1acb71ddceb8b49176f266b7d33f05/blockcheck2.d/standard/90-quic.sh#L24-L35);
- [Zapret2 v1.0.4 `ipfrag2()` implementation](https://github.com/bol-van/zapret2/blob/2c21faa80e1acb71ddceb8b49176f266b7d33f05/lua/zapret-lib.lua#L1473-L1588);
- [Zapret2 v1.0.4 FreeBSD divert raw-send path](https://github.com/bol-van/zapret2/blob/2c21faa80e1acb71ddceb8b49176f266b7d33f05/nfq2/darkmagic.c#L1801-L1997);
- [current pinned upstream manual](https://github.com/bol-van/zapret2/blob/0b8182d24a887059a628d7266577c4ba8e9b8f2d/docs/manual.en.md#standard-ipfrag).

Upstream's own `blockcheck2` tests ordered fragmentation alone before a later fake-plus-fragment combination. The project should preserve that isolation: the first next candidate is fragmentation alone, not a mixture with the already-failed zero fake.

The owner completed this gate on 2026-09-02: the appliance runs Zapret2 `v1.0.4` at exact commit `2c21faa80e1acb71ddceb8b49176f266b7d33f05`, and its installed `90-quic.sh` contains the native standalone `send:ipfrag -> drop` pattern. Evidence is [`2026-09-02-telegram-voice-ipfrag-runtime-pin.md`](../verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md).

#### Exact candidate profile

The smallest next profile is:

```text
--name=telegram-voice-poc
--filter-l3=ipv4
--filter-udp=*
--filter-l7=stun
--ipset=/usr/local/etc/zapret2/runtime-v2/managed/ipset-telegram.txt
--payload=stun
--lua-desync=send:ipfrag:ipfrag_pos_udp=8
--lua-desync=drop
--new
```

Semantics:

1. the existing IPFW rule still diverts all UDP destination ports only toward the managed Telegram IPv4 table;
2. `--filter-l7=stun` selects the first profile and `--payload=stun` guards the Lua actions;
3. `send:ipfrag:ipfrag_pos_udp=8` reconstructs and raw-sends two ordered fragments;
4. `drop` suppresses the intercepted unfragmented original;
5. non-STUN Telegram UDP, including Reflector Hello, falls through unchanged.

No fake action, reverse fragment order, alternate split position, reflector mutation, UDP/443 drop or wider IP/port scope belongs to this first candidate.

#### Why position 8

For IPv4 UDP, Zapret2 counts the fragmentation position from the start of the L4 header and requires an 8-byte multiple. Position 8 is also the upstream default.

For the observed 28-byte TURN Allocate payload, the original IPv4 packet is 56 bytes:

- 20-byte IPv4 header;
- 8-byte UDP header;
- 28-byte STUN payload.

The expected WAN replacement is:

| Fragment | IPv4 length | Offset | MF | Fragment data |
|---|---:|---:|---:|---|
| first | 28 bytes | 0 | 1 | 8-byte UDP header only |
| second | 48 bytes | 8 bytes / offset field 1 | 0 | complete 28-byte STUN payload |

Both fragments use the same non-zero IPv4 ID. Reassembly recreates the original 36-byte UDP datagram and its checksum. A zero source IPv4 ID is replaced by a random non-zero ID by `ipfrag2()`.

Position 16 would leave the first 8 STUN bytes—including the complete `0x2112A442` magic cookie—beside the UDP header. Position 8 is therefore the cleanest minimal test of a stateless payload signature while retaining normal ordered-fragment compatibility.

#### FreeBSD/OPNsense boundary

Zapret2's FreeBSD raw-send implementation uses a divert socket (`PF_DIVERT` on FreeBSD 14+) and sends each reconstructed fragment through that path. The existing Phase B fake packets already proved that generated `dvtws2` traffic reaches the owner's WAN; the fragment candidate uses the same raw-send layer.

No firewall architecture change is required. Keep:

- the `zapret2_tgvoice` active/staging tables;
- the all-destination-port outbound UDP rule bounded by that table;
- `out not diverted not sockarg xmit <WAN>`;
- the existing transactional enable/disable and restoration path.

The `send` plus `drop` pattern intentionally removes the original. If fragment generation/raw-send fails, the original will still be dropped by the next Lua action. The candidate must therefore remain default OFF and an on-wire WAN capture is mandatory; the IPFW counter alone cannot prove successful fragment emission.

#### Minimal packaged-source boundary

The prepared remote `_4` branch applied this minimal source boundary:

- keep `VERSION=0.5.0` and increment `PLUGIN_REVISION: 3 -> 4`;
- replace only the helper action/profile identity from zero fake to ordered `ipfrag_pos_udp=8`;
- keep the existing configd enable/status/disable control, marker, tables, rule and rollback semantics;
- update status to report an unambiguous strategy such as `stun-ipfrag-pos-8-ordered`;
- extend the focused regression contract to require `send:ipfrag` before `drop`, forbid the old zero-fake action in the active helper profile, and preserve first-profile ordering/scope/cleanup tests.

Do not add a second persistent mode selector merely to retain the failed strategy in the same package. The immutable `v0.5.0_3` package already preserves zero-fake reproduction; replacing the temporary candidate is smaller and keeps mutable state single-purpose.

This section records the candidate's design; it no longer authorizes immediate publication. Branch `v0.5.0_4-telegram-voice-ipfrag` at `3ecdd1b3326fe7655e1d7df9edd51808e2a68dc9` is paused with no PR, exact-head CI, merge, package or live result. Phase C must determine whether a STUN-only candidate is relevant, incomplete or ineffective before it is reworked or closed.

#### Capture and acceptance contract

The old WAN BPF expression that looks directly for the STUN cookie cannot observe the replacement fragments: the first fragment has the UDP header but no STUN payload, while the second has the STUN payload but no UDP header.

The WAN capture must select Telegram address ranges at the IPv4 protocol level, for example `ip proto 17` plus the bounded Telegram networks, so both initial and non-initial fragments are retained.

For each client-side TURN request, acceptance requires:

- exactly two ordered WAN fragments matching the expected lengths/offsets/MF flags;
- one shared non-zero IPv4 ID per pair;
- no unfragmented WAN copy;
- byte-exact reassembly to the LAN-side original and a valid reassembled UDP checksum;
- no fake or fragmentation applied to Reflector Hello;
- at least one inbound TURN/STUN response;
- a sustained bidirectional Telegram UDP flow;
- exact disable cleanup and return to the OFF baseline.

Interpretation remains split:

- no correct fragments on WAN: runtime/action failure;
- correct fragments but no inbound TURN: network strategy failure, compatible with fragment dropping or destination-IP/path blocking;
- inbound TURN but no sustained UDP while reflector stays unanswered: separate reflector/post-allocation research boundary;
- inbound TURN plus sustained bidirectional UDP: candidate network success, still requiring a repeat cycle before product acceptance.

### Phase C — automatic traffic emulator/oracle selected

The owner selected automatic Telegram-call-equivalent traffic generation as the next task. Exact architecture: [`TELEGRAM_VOICE_EMULATION_LAB.md`](../architecture/TELEGRAM_VOICE_EMULATION_LAB.md).

The oracle has four evidence layers:

1. offline packet transformation proves only exact interception/profile/action output (`WIRE_OK`);
2. a fresh transaction-correlated 28-byte TURN Allocate probe proves a returned STUN path (`TURN_REPLY`);
3. official pinned `tgcalls_cli` routes in-process caller/callee WebRTC media through a real Telegram UDP reflector with TCP disabled (`REFLECTOR_READY` / `MEDIA_PASS`);
4. one final real remote-participant P2P-disabled Telegram call provides end-to-end product evidence (`CALL_PASS`).

Every negative provider result requires a recent independent unblocked control against the same fixed endpoint. Each candidate receives a fresh process/source-flow state. The temporary OPNsense scope is one selected probe client, one reflector IPv4 address and one port in `596–599`; the reflector profile must not use `--payload=stun` because Reflector Hello is not STUN.

The first reflector matrix is baseline, ordered position 8, reverse position 8, then evidence-driven alternate fragmentation positions. Fake-plus-fragment follows only after standalone families. Any winner is repeated on the same endpoint and at least two additional control-proven reflectors before the final real call.

### Phase D — product GUI only after a strategy passes

No GUI is authorized during Phase C. If a strategy reaches repeated `MEDIA_PASS` and final `CALL_PASS`, the product control belongs under **Settings**, not inside the existing Generic UDP controls. Keep the surface small, explain that it does not replace the TCP proxy path, show active scope/status, and avoid exposing raw repeat/fragment knobs without evidence.

### P2P boundary

The bounded Telegram-IP rule does not capture STUN sent directly to an arbitrary peer IP. That is intentional for the MVP.

For deterministic testing, Telegram P2P should remain disabled. The zero-fake Phase B candidate did not restore a bidirectional UDP relay path; any future candidate must prove that path before the plugin can claim the practical use case without intercepting all Internet UDP.

Future P2P support has only unattractive router-side choices on FreeBSD:

- divert nearly all outbound UDP and let `dvtws2` discover STUN in userspace — broad/high-overhead, reject as default;
- use empirical port ranges — lower cost but incomplete/provider-dependent;
- build another packet-content classifier/kernel integration — invasive and not justified without evidence.

Therefore the project should not claim universal P2P handling in the initial helper.

## Strategy Lab decision

The existing Generic UDP request/reply contract remains unchanged and cannot label a Telegram call strategy as working. It currently:

- generates traffic from OPNsense and installs `from me` IPFW rules;
- accepts any non-empty UDP response rather than parsing/correlating STUN;
- cannot model the per-run peer tags and paired WebRTC state used by Telegram reflectors;
- has no reflector-readiness or bidirectional-media result;
- stops after a synthetic response.

Reuse only its safe machinery: lifecycle ownership, fixed endpoint epochs, candidate profile generation, counters, result storage and exact restoration. Add a separate Telegram Voice runner or explicit external-probe mode for a Linux/WSL2 companion behind OPNsense. Its forwarded-flow IPFW rule must be bounded to one fixed reflector address, one destination port, WAN outbound direction and the verified pre/post-NAT probe tuple where the hook exposes it.

The automatic result vocabulary is intentionally layered: `WIRE_OK`, `TURN_REPLY`, `REFLECTOR_READY`, `MEDIA_PASS`, `CALL_PASS`, `NO_REPLY_UNKNOWN`, `NETWORK_FAIL`, and overriding `RESTORE_FAILED`. This prevents the old false equivalences “any UDP reply = call works” and “audible fallback = UDP works.”

## Universal versus provider-specific answer

There are two different meanings of “universal” here:

**Protocol recognition can be universal:** standards-valid STUN can be recognized by payload signature independently of Telegram and independently of the UDP destination port. That is why upstream calls the helper `stun4all`.

**The DPI bypass cannot be guaranteed universal:** the zero-fake technique depends on how the provider's DPI keeps UDP flow state. Zapret2 itself warns that fake does not defeat stateless DPI. Provider filtering may also move from STUN to relay IPs or the encrypted post-STUN media flow.

Therefore the project should use a small, evidence-ordered and endpoint-controlled strategy matrix rather than a large blind search. A strategy becomes a product default only after repeated media and real-call evidence; no result is universal merely because one provider/reflector passes.

## Live verification matrix for the owner's MTS/MGTS path

The completed comparison kept P2P disabled on both clients and left the existing TCP proxy unchanged:

| State | Telegram Voice helper | Observed UDP evidence | Verdict |
|---|---|---|---|
| A — baseline | OFF | 9 TURN + 90 reflector outbound; 0 inbound | broken Telegram UDP baseline confirmed |
| B — zero-fake PoC | ON, Telegram-IP scoped | helper counter incremented; exact two fakes before each TURN request; 0 inbound; no sustained bidirectional UDP | runtime PASS / network FAIL |
| C — rollback | OFF again | helper table/profile/rule removed; ordinary rule layout and running service restored | cleanup PASS |

The required causal signal—an inbound TURN/STUN response followed by sustained bidirectional Telegram UDP in B—did not appear. Sound remains secondary because TCP fallback can keep a call audible.

The next comparison uses the stricter Phase C hierarchy. First prove one fixed reflector endpoint on an independently unblocked path; then compare the provider baseline and bounded candidates against that exact endpoint with fresh process/flow state. Fragmentation remains diagnostic as well as practical: if the provider blocks by destination IP alone, it will not help. Do not present a fragment candidate as universal before repeated `MEDIA_PASS` and final `CALL_PASS` evidence.

## Collateral-risk assessment

### Telegram-IP scoped STUN helper

Risk: low/bounded relative to global interception. All UDP to Telegram ranges reaches `dvtws2`, but only STUN receives the fake action; non-STUN packets pass unchanged. CPU cost is bounded to Telegram-destination UDP rather than the entire Internet.

### All-STUN / all-UDP interception

Risk: high on FreeBSD. Since `ipfw` cannot inspect payload, discovering STUN globally requires broad userspace diversion. This can affect games, DNS-like UDP applications, WebRTC, VPNs and general router CPU. Not recommended as default.

### Empirical port-range interception

Risk: medium. It can affect unrelated traffic on the same ports and still miss dynamically selected call endpoints. Keep provider-specific/diagnostic only.

### UDP/443 drop

Risk: high and unrelated to the primary mechanism. It can disable QUIC/HTTP/3 and any legitimate UDP/443 STUN/TURN/media. Keep out of Telegram Voice MVP.

## Answers to the original research questions

1. **What carries the call?** Telegram API signaling plus a separately negotiated WebRTC-based transport, with STUN/TURN endpoints and UDP P2P/reflector capabilities.
2. **Is this just MTProto TCP?** No. Working Telegram TCP is necessary for setup but does not imply the UDP media/connectivity path works.
3. **Why can calls fail while generic UDP/STUN works?** The provider can classify Telegram destinations/direction, standardized STUN, reflector signatures or later encrypted flows separately; current packets do not identify which mechanism is active.
4. **Why can the fake work?** Most likely by poisoning/desynchronizing a stateful DPI's UDP flow classification before the genuine STUN packet; this is consistent with upstream's stateful-DPI limitation.
5. **Is the owner's Zapret2 STUN syntax valid?** Yes; it matches the current official Zapret2 `50-stun4all` baseline.
6. **Are zero length/repeats universal?** No. The exact 16-zero/repeats=2 pair is the upstream baseline, not a protocol requirement.
7. **Should UDP/443 be dropped?** Not as a Telegram Voice default. It is a separate QUIC fallback technique with substantial collateral risk.
8. **Can one port list solve Telegram calls?** No protocol-level guarantee exists. Community ranges are empirical/provider-specific evidence only.
9. **Can current Strategy Lab auto-find the voice strategy?** Not with its current arbitrary-reply oracle and `from me` rule. A separate external-probe runner using pinned official tgcalls and a real reflector can provide `MEDIA_PASS` while reusing existing lifecycle machinery.
10. **What was built and measured first?** Phase A completed the traffic observation; `0.5.0_3` implemented the Telegram-IP-scoped native STUN helper. Owner-live testing proved its mechanics and rollback but the zero-fake strategy failed to restore inbound or sustained Telegram UDP.
11. **What about P2P?** The safe MVP does not claim arbitrary-peer P2P interception. Relay-mode verification is the first target.
12. **What is next?** Establish the automatic fixed-endpoint media oracle first, then test reflector fragmentation and the separate TURN family. The prepared STUN-only `_4` branch remains paused until that evidence says whether it is relevant.

## Sources added during research

Primary/protocol sources:

- Telegram modern calls: <https://core.telegram.org/api/end-to-end/video-calls>
- Telegram WebRTC endpoint constructor: <https://core.telegram.org/constructor/phoneConnectionWebrtc>
- Telegram call protocol flags: <https://core.telegram.org/constructor/phoneCallProtocol>
- Telegram CIDRs: <https://core.telegram.org/resources/cidr.txt>
- STUN RFC 8489: <https://www.rfc-editor.org/rfc/rfc8489.html>
- TURN RFC 8656: <https://www.rfc-editor.org/rfc/rfc8656.html>
- FreeBSD 15 `ipfw(8)`: <https://man.freebsd.org/cgi/man.cgi?manpath=FreeBSD+15.0-RELEASE+and+Ports&query=ipfw&sektion=8>
- Zapret2 v1.0.4 manual, pinned source: <https://github.com/bol-van/zapret2/blob/2c21faa/docs/manual.en.md>
- Zapret2 v1.0.4 official `50-stun4all`, pinned source: <https://github.com/bol-van/zapret2/blob/2c21faa/init.d/custom.d.examples.linux/50-stun4all>
- Zapret upstream announcement explaining kernel STUN signature filtering: <https://github.com/bol-van/zapret/discussions/1716>

Project/operator evidence:

- youtubeUnblock repository: <https://github.com/Waujito/youtubeUnblock/>
- youtubeUnblock Telegram-call/STUN issue: <https://github.com/Waujito/youtubeUnblock/issues/265>
- remittor/zapret-openwrt: <https://github.com/remittor/zapret-openwrt>
- remittor Telegram/WhatsApp community recipe: <https://github.com/remittor/zapret-openwrt/issues/520>
- classic zapret Telegram-call discussion with MTS/community reports: <https://github.com/bol-van/zapret/discussions/1668>
- Zapret2 Telegram slowdown discussion: <https://github.com/bol-van/zapret2/discussions/148>
- Zapret2 MTProto/Telegram strategy discussion: <https://github.com/bol-van/zapret2/discussions/77>
- Telegram `tgcalls` reflector hello implementation, pinned source: <https://github.com/TelegramMessenger/tgcalls/blob/2faee3b5524f54d56c91c2058c00e11c656a74b3/tgcalls/v2/ReflectorPort.cpp#L309-L360>
- Telegram `tgcalls_cli` real-reflector harness, current research pin: <https://github.com/TelegramMessenger/tgcalls/blob/78d07f3e46a4bb12b611ccc2816ff59ca63a83fb/CLAUDE.md#L105-L122>
- Telegram `tgcalls_cli` UDP-only server, local signaling and result gate: <https://github.com/TelegramMessenger/tgcalls/blob/78d07f3e46a4bb12b611ccc2816ff59ca63a83fb/tools/cli/main.cpp#L88-L132>
- Telegram `tgcalls_cli` two-party reflector execution and exit contract: <https://github.com/TelegramMessenger/tgcalls/blob/78d07f3e46a4bb12b611ccc2816ff59ca63a83fb/tools/cli/main.cpp#L342-L670>
- Telegram official tgcalls container: <https://github.com/TelegramMessenger/tgcalls/blob/78d07f3e46a4bb12b611ccc2816ff59ca63a83fb/Dockerfile>
- Zapret2 v1.0.4 STUN detector, pinned source: <https://github.com/bol-van/zapret2/blob/2c21faa/nfq2/protocol.c#L1459-L1465>

Community reports are evidence of observed deployments only; they do not override Telegram protocol documentation or current Zapret2 source/manual.

## Recommended next project action

Follow [`TELEGRAM_VOICE_EMULATION_LAB.md`](../architecture/TELEGRAM_VOICE_EMULATION_LAB.md) in this order:

1. pin/build the official tgcalls commit `78d07f3e46a4bb12b611ccc2816ff59ca63a83fb` as a reproducible Linux/WSL2 companion outside the plugin package and record its artifact digest;
2. select one explicit current reflector `IP:596–599`, obtain `MEDIA_PASS` on an independently unblocked path, and capture its wire-equivalence ground truth;
3. run the same endpoint through the blocked provider with no desynchronization;
4. verify the PF/NAT/IPFW source tuple, then add a temporary exact-flow/exact-destination/exact-port IPFW/dvtws2 runner with exact restoration;
5. test reflector position-8 ordered, position-8 reverse and only then evidence-driven alternate fragmentation positions;
6. add the fresh-transaction 28-byte TURN Allocate probe and require a semantically correlated response;
7. repeat any media winner three times on the same reflector and on at least two other control-proven reflectors;
8. perform one final real remote-participant call with P2P disabled and prove sustained bidirectional Telegram UDP plus sound and cleanup;
9. use that evidence to rebase/rework, replace or close the paused `_4` branch before selecting package or GUI scope.

Offline transformed packets are `WIRE_OK`, not a predicted network PASS. Silence without an exact recent control is `NO_REPLY_UNKNOWN`; arbitrary UDP data is not a TURN or media success; restoration failure overrides every candidate result.

Do not publish `_4`, widen to all Internet UDP, globally drop UDP/443, increase fake repeats blindly, or bundle tgcalls/Bazel/Linux into OPNsense before the oracle exists.

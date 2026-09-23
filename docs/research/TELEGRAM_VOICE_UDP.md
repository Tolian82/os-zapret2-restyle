# Telegram voice / UDP DPI-bypass research

**Status:** RESEARCH CURRENT · STANDALONE FRAGMENT SWEEP CLOSED · FAKEFRAG8 + REVERSE24 NEXT · `_4` PAUSED
**Opened:** 2026-08-19
**Research conclusion:** 2026-08-19
**Phase A owner-live observation:** 2026-08-28
**Phase B source PoC:** 2026-09-01
**Phase B owner-live result:** 2026-09-02
**Ordered IPv4-fragmentation design:** 2026-09-02
**Historical Phase B runtime pin:** Zapret2 `v1.0.4` / `2c21faa80e1acb71ddceb8b49176f266b7d33f05`  
**Current owner runtime:** Zapret2 `v1.0.5.2`
**Phase C emulation design:** 2026-09-03
**Phase C companion build/runtime:** 2026-09-04
**Phase C fixed-reflector control:** 2026-09-05
**Updated:** 2026-09-23
**Owner instruction:** Telegram voice/call traffic over UDP is the current selected research task.
**Pinned starting `main`:** `62e9a62e484d7a983b9b3f91ec672bbe96f684f3`
**Research-boundary merge:** `9bc225ea457583ffec696e393c8ba697798369f6`
**Package identity on `main`:** `VERSION=0.5.0`, `PLUGIN_REVISION=3` — bounded Phase B runtime/lifecycle passed; zero-fake provider/network gate failed. Remote `_4` source branch exists but is unpublished and paused.

## 2026-09-22 owner correction and current objective

The owner explicitly states that `192.168.1.140` is no longer a working route. It is retired from current testing and is not a usable independent control or a required restoration destination. The September 5 success is preserved as a historical result with the older binary; it cannot qualify the present endpoint/path.

The owner reports that Telegram changed how voice is transported and that this is why the tgvoice laboratory had to be rebuilt. This is the recorded project motivation. The owner subsequently reported **an established call with correct routing at call time**. The owner identified it as the same fixed-reflector CLI command. Its positive summary remains unavailable, while later fully correlated reverse-fragment runs failed despite valid local-WAN output. Reverse positions 8, 16, 24 and 32 are now wire-qualified without replies/media; the standalone position sweep is closed. The current task remains a repeatable call carrying bidirectional media through OPNsense, with fragmented fake plus qualified real fragmentation as the next bounded family. The failed repeats do not negate the earlier report.

### What official Telegram sources establish

The old and new laboratory pins differ: [source comparison](https://github.com/TelegramMessenger/tgcalls/compare/e3069322a3d1e16ecb11a5e302242e59ddd7f09e...efd330ca04f74706024a5abdfb5b41f4e4dd1065). Relevant changes in that history are:

| Upstream change | Technical effect | Relevance and limit for this laboratory |
|---|---|---|
| [MTProto transport for PeerConnection engines, `bd22b80`](https://github.com/TelegramMessenger/tgcalls/commit/bd22b80ae1a132c348866013203db225a986e27d), 2026-09-01 | With `network_use_mtproto`, engines 11 and 18/19 can encrypt RTP and SCTP using MTProto above ICE, replacing DTLS/SRTP on this path and matching engine 13's transport. It requires the matching WebRTC SCTP support. | The flag is disabled by default for those engines. STUN remains outside that encryption and the reflector/candidate mechanism is unchanged. This is not evidence that the initial Hello changed or that every released client switched transport. Engines 18/19 are not included in this lab build. |
| [Reflector candidate address resolution, `c09fa36`](https://github.com/TelegramMessenger/tgcalls/commit/c09fa36abe4ee8a87f7fe4df3e7edbae90bffa6c), 2026-08-20; [additional engine wiring, `e284539`](https://github.com/TelegramMessenger/tgcalls/commit/e284539c9feddb9b6012a760d5cd9bba56b63d0f), 2026-08-28 | `network_reflector_resolve_remote_candidate_ip` lets UDP connection lookup use a resolved remote address and guards against collisions with existing connections. | Also disabled by default. It can affect ICE Binding-response association after traffic returns; it does not establish why our WAN capture contains no incoming reflector packet at all. |
| [Engine parity fixes, `b174ea9`](https://github.com/TelegramMessenger/tgcalls/commit/b174ea9813c9ca7cc1645f86abaae1d364f3bbeb), 2026-08-20 | Among the changes, `network_disable_stun_when_unconfigured` prevents affected PeerConnection engines from treating an unconfigured UDP reflector as a generic STUN server. | This is another optional, default-off experiment. It does not mean a reflector Hello is a STUN request or that a STUN-only profile covers it. |

The [current CLI](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tools/cli/main.cpp) defaults to engine `13.0.0`, and exposes engine/custom-parameter overrides. The owner's recorded commands supply neither override. Current source plus a passed local P2P smoke test proves a qualified rebuilt harness, not identical negotiated engine/flags/endpoints to every released Windows/Android client. Record those separately if transport parity is investigated; do not blindly enable all experimental flags.

Telegram's [voice/video transport documentation](https://core.telegram.org/api/end-to-end/video-calls) describes WebRTC-based transport with optimized MTProto encryption and API call negotiation. It explicitly covers clients from version 7.0 (2020); it is background architecture, not a dated announcement of a September 2026 migration. The reviewed sources do not establish a global rollout date or a universal STUN-to-reflector switch. Both packet families were already present in earlier project captures. The initial [Reflector Hello implementation](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tgcalls/v2/ReflectorPort.cpp) and our current capture still show the same 40-byte framing family.

### Qualified ordered experiment — September 21

The [September 21 evidence](../verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md) closes the local ordered position-8 wire correction: fragmentation after PF/NAT plus `frag !mf,!offset` avoids both a stale UDP checksum and recapture of the first replacement fragment. The corrected runner emitted 60 complete pairs, all reassembled UDP checksums valid, without duplicate originals. No incoming reflector packet appeared; both peers remained `Reconnecting`, BWE was zero, exit was 1, and cleanup restored the pre-test state.

That run's result is **local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`; its call failed**. No currently working independent control is established. That limits causal attribution but does not prevent continued work. The old gateway is not a prerequisite.

### Qualified reverse position-8 repeat — September 22, recorded September 23

The [earlier archive and owner correction](../verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md) preserve an established-call/correct-route report alongside empty endpoint captures. The owner clarified that the successful display came from the same fixed-reflector CLI command; its positive output is still unavailable.

The [post-reboot repeat](../verification/evidence/2026-09-22-telegram-voice-reverse8-postreboot.md) is fully correlated: the unchanged binary ran from 21:04:34 to 21:04:49 UTC inside the active capture window. Rule 18990 saw 60 packets; WAN contains 60 complete reverse position-8 pairs with correct IPv4/reassembled UDP checksums and exact primary-LAN payload matches. There are no unfragmented originals or replies. Both peers stayed `Reconnecting`, BWE was zero, exit was 1; cleanup restored all snapshots and retained the normal rules. Result: local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`, no `MEDIA_PASS` for this repeat. Neither provider DPI nor behavior beyond local WAN is isolated.

### Latest qualified run — September 23

The [guarded reverse position-32 run](../verification/evidence/2026-09-23-telegram-voice-reverse32.md) overlaps the supplied 07:06:36–07:06:51 UTC CLI log. The same route, CLI hash and runtime produced 60 complete reverse pairs with valid IPv4/UDP checksums and exact primary-LAN payload matches. WAN has no unfragmented originals or reflector replies. Both peers stayed `Reconnecting`, BWE was zero, exit was 1; all snapshots restored exactly. Result: local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`, no `MEDIA_PASS`. The short guard was not exercised by these 40-byte Hellos.

The subsequent [guarded reverse position-16 run](../verification/evidence/2026-09-23-telegram-voice-reverse16.md) is also fully correlated. It emitted 60 complete reverse pairs with the expected offset-16/offset-0 layout, valid IPv4 and reassembled UDP checksums, exact primary-LAN payload matches, no unfragmented originals and no replies. Both peers stayed `Reconnecting`, BWE was zero, exit was 1, and restoration was exact. Result: local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`, no `MEDIA_PASS`. All intercepted payloads were 40 bytes, so the <=8-byte short guard was not exercised.

The subsequent [guarded reverse position-24 run](../verification/evidence/2026-09-23-telegram-voice-reverse24.md) is fully correlated as well. It emitted 60 complete reverse pairs with two equal IP length-44 fragments per Hello, valid IPv4 and reassembled UDP checksums, exact primary-LAN payload matches, no unfragmented originals and no replies. Both peers stayed `Reconnecting`, BWE was zero, exit was 1, and restoration was exact. Result: local-WAN `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`, no `MEDIA_PASS`. This closes standalone fragment-position widening for the current reflector epoch.

The next prepared family adds one fragmented fake before the qualified real reverse24 path. Candidate `postnat-fakefrag8-reverse24-v1` uses a 40-byte zero fake with intentionally bad UDP checksum and random IPv4 ID, fragmented ordered at UDP position 8, followed by the same checksum-valid real reverse24 pair. Fragmenting the fake prevents an unfragmented raw-sent fake from re-entering the post-NAT divert rule. Waiting for the earlier positive CLI log does not block this bounded experiment. No fresh independent control establishes where the silence beyond local WAN originates.

## 2026-09-20 laboratory source update

Owner-client scope is Windows and Android; Telegram-iOS is not used for the live
call tests. The laboratory now uses only public tgcalls
`efd330ca04f74706024a5abdfb5b41f4e4dd1065` as
`/results/tgcalls_cli`. The earlier `e3069322...` binary remains historical
evidence only and is no longer retained as an active lab oracle.

The current oracle intentionally excludes only the new test-only v2wasm 18/19
CLI engines because the public outer Bazel workspace does not expose their build
targets. Current 11/13/14 reflector/networking code is retained. A local P2P
smoke test is mandatory before the current binary is accepted.

Zapret2 on the owner's OPNsense has meanwhile been updated from v1.0.4 to
v1.0.5.2. Earlier v1.0.4 wire evidence remains valid evidence for those exact
epochs, but new candidate runs must record the v1.0.5.2 runtime identity.

## 2026-09-20 current-reflector provider-path baseline

The current `efd330ca04f74706024a5abdfb5b41f4e4dd1065` binary was run for
15 seconds against fixed reflector `91.108.13.10:596` through TNAS route
`via 192.168.1.2`. Both peers remained `Reconnecting`, the call never
established, BWE stayed zero, and the result reproduced on repeated runs.

The paired LAN/WAN captures establish the forwarding truth:

- 60 outbound UDP datagrams on LAN and the same 60 on WAN;
- two flows, 30 packets each;
- each application payload is exactly 40 bytes and repeats at about 500 ms;
- LAN-to-WAN payload pairing is byte-identical;
- NAT maps only address/source port, with TTL 64 -> 63;
- IP identification is preserved and IPv4/UDP checksums validate;
- zero inbound UDP/596 packets from the reflector appear on either capture.

Therefore the current client still uses the same non-STUN 40-byte Reflector
Hello framing family at this stage. The old laboratory binary is no longer
being used; this does not rule out differences in real-client engine negotiation
or custom parameters. Ordinary OPNsense/NAT forwarding is not corrupting or
dropping the outbound baseline packets.

The strict result is `WIRE_OK / NO_REPLY_UNKNOWN`. The capture proves a failed
current reflector exchange on this path but does not, by itself, identify the
provider DPI as the cause. A strict `NETWORK_FAIL` label requires a sufficiently
fresh independent control for the same endpoint/current oracle.

This also changes candidate selection: the paused `_4` STUN-only profile does
not match the observed Reflector Hello flow. New tests must target the exact
`91.108.13.10:596` UDP flow and treat fragmentation/desynchronization as a
non-STUN reflector experiment.

## Executive conclusion

Telegram voice should **not** be modeled as “Telegram TCP plus one known UDP port.” Current Telegram calls have a Telegram API signaling channel plus a WebRTC-based transport. Telegram explicitly supplies call endpoints with IP address, UDP port and STUN/TURN role, while its call protocol also supports direct UDP P2P and UDP reflector paths. Therefore a call may use dynamically selected UDP destinations/ports that are separate from the ordinary Telegram TCP connection.

Phase A established that **audible call success is not proof that Telegram UDP works**. With P2P disabled on both clients, the test client sent TURN Allocate requests and Telegram Reflector Hello packets to Telegram-managed addresses, received no UDP reply on either candidate, yet the call established with two-way audio and no perceived delay while the existing TCP/SOCKS proxy path remained bidirectional. The bounded inference is TCP/proxy fallback; the encrypted stream was not decrypted, so this record does not attribute media to one specific TCP connection.

Phase B then tested the exact official zero-fake/repeats=2 hypothesis on the same provider path. A clean remote-participant OFF/ON/OFF comparison proved that the plugin intercepted the intended Telegram-destination UDP, selected STUN, and emitted exactly two valid 16-zero-byte datagrams before each of 9 TURN Allocate requests. The ON state still received zero TURN/STUN replies and produced no sustained bidirectional Telegram UDP. Runtime/lifecycle qualification passed, but provider/network effectiveness failed. This directly falsifies the usefulness of the exact zero-fake baseline on the tested path without identifying the provider's internal mechanism.

A separate generic STUN exchange with `141.101.90.1:3478` returned bidirectional responses in the same WAN environment. Thus neither UDP nor STUN framing was universally blocked; the unresolved discriminator is Telegram-specific destination/direction/path policy versus a more selective payload/relay classifier.

On 2026-09-05, the historical Phase C binary reached `MEDIA_PASS` at `91.108.13.10:596` through TNAS gateway `192.168.1.140`: both peers established, 15 records per side, non-zero BWE, no errors and exit 0. That did not traverse OPNsense. The owner has since retired this route as non-working; this old success is not a current control for the rebuilt laboratory.

The original next candidate was source-designed from Zapret2's UDP fragmentation path: re-send each selected STUN datagram as two ordered IPv4 fragments at UDP position 8, then drop the unfragmented original. The owner then confirmed that the installed Zapret2 `v1.0.4` runtime exposes this primitive. Remote branch `v0.5.0_4-telegram-voice-ipfrag` preserves that implementation, but no PR, CI, merge, package or network result exists and the branch is now paused.

The original **stateful STUN-desynchronization** hypothesis was technically justified but is weakened by the live evidence. Current upstream `bol-van/zapret2` ships `init.d/custom.d.examples.linux/50-stun4all`, which recognizes STUN in the Linux firewall on all addresses/ports and applies native Zapret2:

```text
--payload=stun
--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2
```

The exact strategy was emitted correctly and still received no Telegram TURN reply. Generic public STUN on the same router path had produced bidirectional responses, while both Telegram TURN and reflector endpoints were outbound-only. This raises destination-IP/direction/routing policy, stateless inspection, relay policy or another Telegram-specific blackhole above simple stateful STUN classification. The capture cannot identify which one. No payload-only Zapret2 technique can repair a pure destination-IP block.

The Linux/OpenWrt `50-stun4all` integration cannot be copied literally to OPNsense. Its important property is **kernel-side STUN signature filtering before NFQUEUE**. Zapret2 upstream explicitly documents that FreeBSD `ipfw` lacks raw-payload filtering. Passing all UDP through `dvtws2` merely to discover STUN would create a broad kernel/userspace interception path and is not acceptable as the default production design.

**The project remains a temporary laboratory campaign: the rebuilt oracle exists, and the next objective is a passing media call.** Offline replay can predict interception and exact wire transformation only. A standards-correlated TURN probe can prove a returned STUN path but not media. The official pinned `TelegramMessenger/tgcalls` CLI can create caller/callee instances with local signaling and route bidirectional WebRTC media through a real Telegram UDP reflector with TCP disabled. One final real P2P-disabled remote call remains the product gate.

The companion build/runtime gate is now complete for the active oracle. The owner built `tgcalls_cli` from current tgcalls `efd330ca04f74706024a5abdfb5b41f4e4dd1065` inside `Telegram-iOS@6ad963e5b62d354da79040f388ae2b9132fb17b8`; the produced binary SHA-256 is `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`. A five-second local P2P self-test reached `Established` on both sides at 0.039 seconds, collected five bitrate records per side, reported non-zero BWE and no errors, and exited 0. This proves the executable/runtime gate only. Historical `e3069322...` evidence remains valid for its old epochs but is no longer the active oracle.

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

The September 2 STUN-only design originally proposed retaining the following firewall arrangement. This is historical design, not an adequate contract for the current reflector experiment: September 21 evidence requires fragmentation after PF/NAT and explicit exclusion of all replacement fragments from the temporary divert rule. The paused packaged `_4` design has not received that qualification. Original arrangement:

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

A causal `NETWORK_FAIL` verdict requires a recent independent working control against the same fixed endpoint. Without one, continue bounded tests and record silence as `NO_REPLY_UNKNOWN`; do not block the campaign waiting for retired `192.168.1.140`. Each candidate receives a fresh process/source-flow state. The temporary OPNsense scope is one selected probe client, one reflector IPv4 address and one port in `596–599`; the reflector profile must not use `--payload=stun` because Reflector Hello is not STUN.

The initial matrix is baseline, ordered position 8, reverse position 8, then evidence-driven alternates. Baseline and both qualified position-8 orders completed without a media pass. The post-reboot reverse repeat has complete wire/CLI attribution; the earlier owner-reported success remains separate. Guarded reverse positions 32 and 16 are now both wire-qualified without replies/media. Position 24 is prepared as the final planned standalone position comparison. If it is also wire-correct and silent, fake-plus-fragment follows rather than further position widening. Repeat a qualified winner with fresh processes, then perform the real-call gate; additional reflector coverage remains a separate epoch.

#### Phase C companion and fixed-reflector result

The active qualified binary is current tgcalls `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; `tgcalls_cli` SHA-256 is `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`.

The local P2P run remains a build/runtime gate. The 2026-09-05 fixed-reflector `MEDIA_PASS` belongs to the older `e3069322...` binary and the now-retired route, not the current qualified binary. The rebuilt oracle has not yet reached reflector `MEDIA_PASS` through OPNsense.

Owner network decision: keep only the existing Docker network named `host`. Host mode has no per-container interface, IP, MAC or DHCP lease. The historical September 5 control inherited TNAS `192.168.1.100` and gateway `192.168.1.140`; that gateway is now retired as non-working.

Therefore a DHCP reservation cannot distinguish this container. pfSense may assign an exact route by the visible TNAS MAC, but that route applies to the TNAS host namespace. Further provider epochs keep host mode and select only the fixed endpoint `/32` through OPNsense `192.168.1.2`, using owner-controlled DHCP policy or a bounded explicit route transaction and proving the original route afterward.

### Phase D — no permanent laboratory integration

The Telegram Voice laboratory is temporary. The existing TNAS/OPNsense consoles run `docker exec` and bounded firewall/runtime experiments. Temporary key-only SSH is optional orchestration; any owned route/firewall/runtime change requires exact cleanup. Do not add a GUI, permanent controller/API/configd surface, daemon or package-owned lab subsystem. Do not change Generic UDP Strategy Lab.

A future working production strategy/helper would require a separate owner decision; the experimental laboratory itself is removed or archived.

### P2P boundary

The bounded Telegram-IP rule does not capture STUN sent directly to an arbitrary peer IP. That is intentional for the MVP.

For deterministic testing, Telegram P2P should remain disabled. The zero-fake Phase B candidate did not restore a bidirectional UDP relay path; any future candidate must prove that path before the plugin can claim the practical use case without intercepting all Internet UDP.

Future P2P support has only unattractive router-side choices on FreeBSD:

- divert nearly all outbound UDP and let `dvtws2` discover STUN in userspace — broad/high-overhead, reject as default;
- use empirical port ranges — lower cost but incomplete/provider-dependent;
- build another packet-content classifier/kernel integration — invasive and not justified without evidence.

Therefore the project should not claim universal P2P handling in the initial helper.

## Strategy Lab decision

The existing Generic UDP request/reply contract remains unchanged and cannot label Telegram reflector media as working.

For this temporary campaign, OPNsense-console scripts may reuse fixed-endpoint, bounded IPFW/divert, fresh-flow and exact-restoration concepts, but they remain outside installed plugin paths. The companion is started with TNAS `docker exec`, directly or through optional temporary key-only SSH.

No GUI, MVC/API/configd addition, background service, permanent external-probe runner or Generic UDP behavior change is authorized.

Result vocabulary remains `WIRE_OK`, `TURN_REPLY`, `REFLECTOR_READY`, `MEDIA_PASS`, `CALL_PASS`, `NO_REPLY_UNKNOWN`, `NETWORK_FAIL`, and overriding `RESTORE_FAILED`.

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

Current comparisons use the stricter Phase C hierarchy and a fixed endpoint with fresh process/flow state. Seek a fresh independent endpoint control when available; none is currently established, and `192.168.1.140` must not be assumed working. Continue the bounded laboratory search meanwhile, preserving `NO_REPLY_UNKNOWN` for silence. Fragmentation remains diagnostic as well as practical: if the provider blocks by destination IP alone, it will not help. Do not present a fragment candidate as universal before repeated `MEDIA_PASS` and final `CALL_PASS` evidence.

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
12. **What is next?** Live-test the first fragmented-fake + qualified reverse24 candidate with the same runtime, binary, engine, endpoint and route. The standalone reflector fragmentation sweep is closed: ordered position 8 and reverse positions 8, 16, 24 and 32 are locally wire-qualified but every fully correlated run remained silent. The new candidate adds one 40-byte zero fake with bad UDP checksum, random IPv4 ID and ordered position-8 fragmentation before the already-qualified real reverse24 pair. Preserve the earlier positive CLI observation separately; later engine comparisons remain isolated. The STUN-only `_4` branch stays paused.

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
- Telegram-iOS outer build workspace, build-validated pin: <https://github.com/TelegramMessenger/Telegram-iOS/tree/6ad963e5b62d354da79040f388ae2b9132fb17b8>
- Historical September 4 `tgcalls_cli` native harness and exit gate: <https://github.com/TelegramMessenger/tgcalls/blob/e3069322a3d1e16ecb11a5e302242e59ddd7f09e/tools/cli/main.cpp>
- Historical September 4 reflector Hello/framing implementation: <https://github.com/TelegramMessenger/tgcalls/blob/e3069322a3d1e16ecb11a5e302242e59ddd7f09e/tgcalls/v2/ReflectorPort.cpp>
- Historical September 4 reflector-list runner: <https://github.com/TelegramMessenger/tgcalls/blob/e3069322a3d1e16ecb11a5e302242e59ddd7f09e/tools/cli/run-test.sh>
- Historical September 3 research delta (superseded by the active `efd330ca...` build): <https://github.com/TelegramMessenger/tgcalls/compare/e3069322a3d1e16ecb11a5e302242e59ddd7f09e...78d07f3e46a4bb12b611ccc2816ff59ca63a83fb>
- Zapret2 v1.0.4 STUN detector, pinned source: <https://github.com/bol-van/zapret2/blob/2c21faa/nfq2/protocol.c#L1459-L1465>

Community reports are evidence of observed deployments only; they do not override Telegram protocol documentation or current Zapret2 source/manual.

## Recommended next project action

The exact current handoff is [`START_HERE.md`](../START_HERE.md); the runner and acceptance contract is in [`TELEGRAM_VOICE_EMULATION_LAB.md`](../architecture/TELEGRAM_VOICE_EMULATION_LAB.md).

1. Run `tgvoice_fakefrag8_reverse24_postnat_v1.py --after-nat`, revision `postnat-fakefrag8-reverse24-v1`, SHA-256 `c4ee47779d778f50b04e48ffe744f5d098d3fb32863133b7d3a8d7ed6c633d24`, then start the same fixed-reflector 15-second CLI after `READY`.
2. Keep endpoint `91.108.13.10:596`, route through `192.168.1.2`, current tgcalls binary/engine and measured Zapret2 runtime identities fixed.
3. Require four WAN fragments per 40-byte Hello: ordered fake len 28 offset 0/MF=1, fake len 60 offset 8/MF=0, then real reverse24 len 44 offset 24/MF=0 and len 44 offset 0/MF=1. The fake pair must have intentionally invalid reassembled UDP checksum and a different IPv4 ID from the real pair; the real pair must remain checksum-valid and payload-exact. Reject/rerun an epoch with a fake/real ID collision.
4. Preserve the earlier positive CLI observation separately. A wire-correct silent result remains `NO_REPLY_UNKNOWN` without a fresh independent control; a media success must be repeated with fresh process/flow state.
5. Reach and repeat `MEDIA_PASS`, then verify one remote P2P-disabled Windows/Android call with two-way audio and sustained bidirectional UDP before a production decision.

Keep the laboratory temporary and package identity `0.5.0_3` unchanged. Do not publish the paused STUN-only `_4` as-is.

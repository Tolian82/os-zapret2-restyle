# Telegram voice / UDP DPI-bypass research

**Status:** CURRENT RESEARCH BOUNDARY · NO IMPLEMENTATION DECISION YET  
**Opened:** 2026-08-19  
**Owner instruction:** Telegram voice/call traffic over UDP is the current selected research task.  
**Pinned starting `main`:** `62e9a62e484d7a983b9b3f91ec672bbe96f684f3`  
**Package identity at opening:** `VERSION=0.5.0`, `PLUGIN_REVISION=2` — documentation/research scope only, no metadata change.

## Purpose

Determine how Telegram voice calls actually use UDP on paths where the provider hard-blocks the main Telegram services, while TCP traffic to Telegram-owned destinations is already routed through an external proxy.

The research must establish whether Telegram voice requires a separate provider-specific Zapret2 strategy, whether a service-oriented UDP/STUN treatment can be sufficiently universal, or whether successful calling depends on a different mechanism such as QUIC suppression/fallback rather than direct Telegram media desynchronization.

This task is specifically about **voice-call media/connectivity**, not ordinary Telegram login, messaging, Web/MTProto TCP reachability, or general TCP bypass.

## Hard boundaries

- Use **bol-van/zapret2** semantics and implementation as the primary DPI-bypass engine authority.
- Do not translate classic `zapret`/`nfqws1` presets into Zapret2 by analogy without verifying equivalent native Zapret2 behavior.
- Existing TCP routing through an external proxy is treated as an external prerequisite, not part of this research scope.
- Provider UDP is not assumed fully open: the task is to determine what Telegram voice packets/protocols are filtered and what manipulation, if any, actually restores calls.
- Do not assume that blocking UDP/443 is automatically correct or desirable. Its purpose, side effects and relation to Telegram call transport/fallback must be established first.
- Do not assume that a generic STUN fake is sufficient merely because community configurations use it. Packet matching, Zapret2 Lua behavior, provider DPI response and collateral impact must be examined.
- Existing Strategy Lab Generic UDP and Enable QUIC paths are architectural inputs, not proof that either is already suitable for Telegram calls.
- No product/source implementation is approved by this document. Research conclusions must precede any architecture or code decision.

## Owner-provided starting evidence and sources

### `Waujito/youtubeUnblock`

Source: <https://github.com/Waujito/youtubeUnblock/>

Owner observation/comment:

- OpenWRT-oriented DPI-bypass project.
- In the owner's observed configuration, adding Telegram domains is sufficient for Telegram including voice calls to work.
- Research question: determine what packet classes/protocol recognizers and firewall paths this project applies to those domains, and whether the apparent domain-only configuration indirectly covers UDP media/STUN/QUIC traffic.

### `remittor/zapret-openwrt`

Source: <https://github.com/remittor/zapret-openwrt>

Owner observation/comment:

- OpenWRT GUI/integration around Zapret2/Zapret.
- Community configurations use custom firewall/daemon hooks for Telegram/Discord voice connectivity.
- These examples are evidence to investigate, not yet project-approved presets.

Observed `custom.d` example that blocks UDP/443:

```sh
zapret_custom_firewall_nft() {
    nft add rule inet fw4 raw_prerouting udp dport 443 drop comment "zapret2-block-quic"
}
```

Research questions:

- Is this intended to force Telegram away from QUIC/UDP-443 to another call transport?
- Is the benefit Telegram-specific, a generic QUIC-fallback workaround, or an unrelated browser/web workaround?
- What breaks when UDP/443 is dropped globally, and can any required behavior be scoped safely?

Observed `/opt/zapret2/init.d/openwrt/custom.d/50-script.sh` STUN example:

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

Research questions:

- Decode exactly what the iptables/u32 and nft expressions identify and whether they match standards-compliant STUN, Telegram-specific variants, both directions, IPv4 fragmentation, and extension/header cases.
- Verify native Zapret2 `--payload=stun` recognition and the semantics of `--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2`.
- Determine whether the all-zero fake is significant, whether repeats/shape are provider-dependent, and what collateral impact exists for unrelated STUN/WebRTC traffic.
- Separate the STUN media-establishment problem from MTProto/TCP interception; the latter is outside the voice-only bypass question except where it is a prerequisite for call setup.

### Primary Zapret2 upstream

Repository: <https://github.com/bol-van/zapret2>

Manual: <https://github.com/bol-van/zapret2/blob/master/docs/manual.en.md>

Discussions: <https://github.com/bol-van/zapret2/discussions>

Required use:

- Treat current Zapret2 source/manual as primary authority for packet classification, payload filters, Lua desync actions, fake generation, UDP handling, flow/range semantics and platform constraints.
- Search upstream discussions for Telegram calls, STUN, VoIP, UDP, QUIC and provider-specific observations, but distinguish anecdotal presets from documented engine behavior.

## Required external research

Search beyond the owner-provided links for current technical material on:

- Telegram voice/video call transport and call establishment;
- Telegram VoIP relay/P2P behavior, STUN/TURN/ICE-like mechanisms where applicable, UDP port selection and fallback behavior;
- Telegram IP ranges/endpoints used for calls versus ordinary MTProto service traffic;
- DPI techniques observed against Telegram calls in Russia/MTS/MGTS and other providers where credible evidence exists;
- Zapret2-native handling of STUN and arbitrary UDP payloads;
- community configurations that restore Telegram/Discord/WebRTC voice and their packet selectors;
- side effects of dropping UDP/443 or applying fake packets to all STUN traffic;
- whether domain/IP classification is sufficient once call media changes destination to relays or peers.

Prefer primary source, upstream code/manual/issues/discussions, protocol documentation, packet captures and reproducible operator reports. Record uncertainty explicitly.

## Questions the research must answer

1. What traffic is actually responsible for Telegram call setup and media after ordinary Telegram TCP connectivity already works through a proxy?
2. Which parts are STUN, Telegram-specific UDP, generic UDP, QUIC/UDP-443, relay traffic, direct peer traffic, or TCP fallback?
3. What does provider DPI need to see or corrupt for a Telegram call to fail while UDP remains nominally routable?
4. Why does the cited STUN fake technique work where reported: classifier evasion, injected decoy state, DPI parser desynchronization, or another effect?
5. Is the proposed STUN technique valid native Zapret2 usage and is the all-zero fake/repeat count essential?
6. Why does globally dropping UDP/443 sometimes improve calls, and is that mechanism rational for this project?
7. Can one safe service-oriented/default Telegram-voice UDP policy work across providers, or must Strategy Lab discover a provider-specific candidate?
8. If discovery is required, what constitutes a reliable machine-testable success signal for a voice strategy? A UDP reply alone is insufficient for many media protocols.
9. How should Telegram call destinations be selected: Telegram IPSET, STUN payload detection globally, destination-port ranges, dynamic learned endpoints, or combinations?
10. How do NAT, P2P/direct calls and Telegram relays affect an OPNsense interception design?
11. What collateral traffic could be affected by a global STUN rule or UDP/443 drop, including WebRTC, games, Discord, browsers and HTTP/3?
12. What is the smallest OPNsense/Zapret2 integration that is explainable, bounded, reversible and testable?

## Project integration alternatives to evaluate

The final research must compare at least these product shapes rather than jumping directly to one implementation:

1. **Static Telegram voice helper** — a predefined Zapret2-native STUN/UDP policy with explicit enable/disable control.
2. **Service-aware Strategy Lab branch** — a Telegram Voice target that can exercise relevant UDP/STUN candidates and return a recommended profile/policy.
3. **Generic UDP extension** — extend the existing arbitrary UDP mechanism with protocol recognizers such as STUN and an appropriate success/evidence model.
4. **Firewall fallback control** — an explicit, narrowly scoped option to suppress UDP/443 only when technically justified.
5. **No separate strategy** — document a universal/native configuration if research demonstrates that a stable provider-independent treatment is sufficient.
6. **Hybrid** — safe default protocol handling plus provider-specific discovery for harder DPI paths.

For every alternative, evaluate correctness, provider dependence, collateral risk, observable success criteria, OPNsense/IPFW feasibility, Zapret2-native semantics, GUI complexity, cleanup/restoration requirements and interaction with the existing TCP proxy route.

## Required deliverable before implementation

Produce a documented research conclusion that includes:

- protocol/traffic model for Telegram calls;
- explanation of every owner-provided workaround and whether it is technically justified;
- current Zapret2-native mechanisms applicable to those packets;
- provider-specific versus universal parts;
- recommended OPNsense plugin architecture and exact proposed GUI/runtime boundary;
- proposed verification method on a live OPNsense/MTS-MGTS path;
- risks/collateral effects and rollback/disable behavior;
- explicit decision whether a new Strategy Lab search branch is needed;
- if search is needed, candidate families, traffic selectors and reliable success evidence;
- if search is not needed, the smallest deterministic configuration and why it is safe enough.

Only after the owner reviews/accepts that conclusion may implementation architecture/source changes be selected.

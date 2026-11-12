# P4c3c — isolated QUIC Initial UDP fake-handler witness

**Feature:** [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936) · **qualified source:** `v0.6.4_33` · **status:** native disposable QUIC fake UDP packet proof **PASS**, [PR #1067](https://github.com/Tolian82/os-zapret2-restyle/pull/1067) merged at `e772418cb45768194e817782eef5247b0c37b1ef`; owner WAN/DPI bypass/A17/P4/P6 remain **OPEN**. Stable published `v0.6.4_1.pkg` unchanged.

## Native evidence contract

Reuse the accepted P4c3a guest-safety gate and FreeBSD `lo0` packet discipline, not a second firewall or runtime. Compile the genuine pinned upstream `bol-van/zapret2` v1.0.7 commit `038c97e5819df10f8e8c22a2f1fffe57f2f7379b` inside a disposable OPNsense 26.7 VM.

Use two **distinguishable upstream captured QUIC Initial binary fixtures**, both 1200 bytes from that exact commit:

- Original client datagram: `files/fake/quic_initial_www_google_com.bin` (Git blob SHA-1 `80a07cc8870c88be6d8ac7f9bf9dc9bb1979468b`).
- Injected fake datagram: `files/fake/quic_initial_rutracker_org.bin` (Git blob SHA-1 `25b3edcd6500ae11e55727995235ff7dd917bd2f`).

They are pinned upstream *test artifacts*, not a claim that their current encrypted TLS/QUIC handshake will complete. Validate paths, sizes, Git blob SHA and QUIC Initial long-header structure; no arbitrary fixtures or external network destinations.

A baseline IPv4 loopback UDP datagram goes to `127.0.0.1:6545` and is delivered intact without divert. After installing one test-only IPFW rule `19351`, with divert socket `19899`, send the same original datagram from a **different local UDP source port**. The actual `dvtws2` profile is:

```text
--blob=quic_probe:@<pinned-upstream-files/fake/quic_initial_rutracker_org.bin>
--filter-udp=6545
--filter-l7=quic
--payload=quic_initial
--lua-desync=fake:blob=quic_probe
```

This deliberately uses a distinctive **explicit test blob**, rather than assuming the production `fake_default_quic` matches an independently named captured file. It exercises the real Lua `fake` handler and outbound injected UDP packet, not repeat-count tuning or a real internet connection.

**PASS requires all independent facts together:** a genuine C-side `payload_type 'quic_initial' satisfy filter` decision; an actual upstream Lua `fake` debug handler marker; a positive IPFW `-a list` counter for rule `19351`; and bounded FreeBSD `lo0` DLT_NULL/LOOP PCAP containing (1) the exact original in the baseline source-port flow, (2) the exact original on the active source-port flow, and (3) the **distinct injected fake bytes** on the active source-port flow. No fake can appear on baseline. Source ports and raw UDP payloads must match independently; observing a handler log alone cannot pass.

**Fail-closed guard:** do not execute on any installed plugin/owner appliance, pre-existing `dvtws2` process, non-default foreign IPFW rules, unexpected upstream version, absent FreeBSD/IPDIVERT, corrupt/truncated PCAP or leaked divert rule. Reuse P4c3a's verified safe cold IPFW startup. Finally remove the exact test rule, stop tcpdump and test engine, compare the pristine IPFW rule list and discard temporary checkout/PCAP. Nothing changes WAN, FD9, Voice, the running user runtime or the stable package.

## Efficient validation and proof limits

`scripts/test-p4c3-native-quic-loopback.py --self-test` is an offline synthetic *negative* parser and evidence fixture (not native PASS). The narrow `.github/workflows/p4c3-native-quic-replay.yml` performs fast Linux source/guest-refusal checks, then one disposable OPNsense 26.7 native VM if preflight succeeds. Do not rerun the P4c3a TLS / P4c3b HTTP VMs or a historical broad test matrix for this feature.

**Exit — SATISFIED for isolated P4c3c only:** real [native #43164894619](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43164894619) shows `P4C3_QUIC_INITIAL_NATIVE_HANDLER=PASS` and `P4C3_QUIC_INITIAL=PASS_NATIVE_QUIC_HANDLER_AND_FORGED_UDP_PCAP_ONLY`. Exact-head [CI #43164894478](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43164894478), FreeBSD [#43164894605](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43164894605), title [#43164894543](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43164894543) and postmerge `main` [CI #43165297388](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43165297388) all PASS.

This deliberately **does not prove** cryptographic QUIC decryption, an end-to-end QUIC handshake, a real provider DPI bypass, default production `fake_default_quic` or repeat-count behavior, STUN/WireGuard/Voice, GUI preset validity, owner-appliance A17, full P4 or P6 acceptance. These remain separate tests.

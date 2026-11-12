# P4c3a — isolated TLS packet-handler witness (source candidate)

**Feature:** [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936), approved P4/A17. **Source revision:** `v0.6.4_29`. **Status:** source-only, **native evidence pending exact-head CI**. The published `v0.6.4_1.pkg` is unchanged.

## Why the previous gate is insufficient

[P4c2](P4C_NATIVE_PROFILE_EXAMPLES.md) proved pinned upstream HTTP/TLS/QUIC command-line parsing and Lua initialization with `--intercept=0`. That cannot prove that a real packet selects a profile or invokes its Lua handler. The new gate uses genuine socket traffic and kernel divert, **only** on a disposable OPNsense 26.7 guest.

## Narrow scenario

- An OpenSSL MemoryBIO TLS 1.2 ClientHello for the synthetic hostname `p4c3.example` is sent over IPv4 loopback `127.0.0.1`, TCP port `6544`. This port is a **test mapping** for the TLS profile; it is not a new installed production filter or WAN port.
- Compile actual pinned `bol-van/zapret2 v1.0.7` at commit `038c97e5819df10f8e8c22a2f1fffe57f2f7379b`. Use its real `dvtws2`, `zapret-lib.lua` and `zapret-antidpi.lua`, with `--filter-l7=tls --payload=tls_client_hello --lua-desync=multisplit:pos=midsld:seqovl=1`.
- Require a baseline un-diverted TCP flow to deliver the original ClientHello intact. Enable **one** disposable IPFW divert rule `19350` (outside the plugin's `19000–19010` and Lab `19100–19131` ranges), with divert socket `19898` and `out not diverted ... xmit lo0`. Do not select or modify the appliance WAN.
- Require **all three independent measurements**: a real IPFW divert rule packet counter greater than zero; the real v1.0.7 Lua `multisplit: sending part 1/2` packet-handler logs with `tls_client_hello` payload-filter evidence and checked split lengths; and a bounded native `lo0` PCAP containing the **intact baseline** ClientHello plus both independently attributed **active split TCP payload segments**. The active full original is not required: genuine `multisplit` replaces it with new packets.
- Fail closed for installed plugin/active `dvtws2`, non-default IPFW owner, absent FreeBSD/IPDIVERT readiness, wrong checkout SHA, invalid TLS fixture, missing native packet capture or leaked rule. A fresh disposable OPNsense guest may have unloaded IPFW: after strict `ipfw list` protocol-unavailable and absent-module proof, reuse the existing FreeBSD native guest's `kenv net.inet.ip.fw.default_to_accept=1` and `kldload ipfw` procedure; attest exactly the default-allow rule before adding any test rule. Never load over foreign rules. Restore the pristine guest IPFW rule **list** (module/kenv state on a disposable guest is not described as restored); stop native engine and tcpdump; discard only private temp checkouts and PCAPs.

## Workload and proof limits

`scripts/test-p4c3-native-tls-loopback.py --self-test` runs without a VM, checking the real TLS fixture, handler marker and safe port/rule policy. The standalone `.github/workflows/p4c3-native-tls-replay.yml` first runs a fast non-FreeBSD refusal, then **one** bounded native OPNsense guest after a runner prerequisite gate. No historical package/RUNNING/Voice/Lab matrix, GitHub push-duplication, installed package or owner's production runtime is involved.

**Exit:** exact-head native workflow must show `P4C3_TLS_MULTISPLIT=PASS_NATIVE_TLS_HANDLER_DISPATCH_AND_PCAP_ONLY`. If the VM lacks appropriate scoped IPFW/loopback support, classify as **NOT TESTED / infrastructure refusal**, not product regression or PASS. The selected handler's dispatch and exact test-only loopback segment payloads **do not** prove reliable end-to-end TCP reconstruction, successful TLS handshake, external ISP DPI bypass, Voice/STUN/WireGuard/QUIC execution, or P4/A17/P6 acceptance. Those remain separate gates.

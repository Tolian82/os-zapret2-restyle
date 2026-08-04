# 2026-08-04 — Strategy Lab Patch 10

Implemented the extended QUIC branch.

The branch is gated exclusively by the stage-30 `quic_ipv4` capability result. A closed or unavailable fixed control produces an explicit skipped result and no candidate runtime. An available control enables a sequential Zapret2-only catalog using `quic_initial`, `fake_default_quic`, and UDP fragmentation candidates.

Temporary dvtws2 arguments use UDP/443 and QUIC filtering. IPFW rules are UDP/443 and target-address scoped. Target requests use OpenSSL QUIC with IPv4, ALPN h3, hostname verification, and command exit status.

Arbitrary UDP, circular validation, GUI activation, and legacy Blockcheck removal remain later patches.

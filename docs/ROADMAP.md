# os-zapret2-restyle — Roadmap

Current candidate: `v0.3.2_12`.

- Patches 1–9: COMPLETE.
- Patch 10 — QUIC strategy branch: IN DELIVERY.
  - [x] Fixed capability gate.
  - [x] Explicit skip when QUIC/IPv4 is closed.
  - [x] UDP/443 target-scoped runtime and firewall.
  - [x] Zapret2 QUIC fake and fragmentation catalog.
  - [x] OpenSSL QUIC target request with ALPN h3.
  - [x] Sequential result persistence.
  - [x] Package candidate `0.3.2_12`.
- Patch 11 — Arbitrary UDP strategy branch: BLOCKED BY PATCH 10 GATE.
- Patch 12 — Temporary circular live validation: BLOCKED.
- Patch 13 — Final synchronous Blockcheck replacement: BLOCKED.

Strict serial delivery and deferred owner-assisted verification remain mandatory.

# os-zapret2-restyle — Roadmap

Current candidate: `v0.3.2_13`.

- Patches 1–10: COMPLETE.
- Patch 11 — Arbitrary UDP strategy branch: IN DELIVERY.
  - [x] Require explicit UDP port and request payload.
  - [x] Safe skip without configuration.
  - [x] Require a non-empty response.
  - [x] Sequential Zapret2 generic UDP fragmentation candidates.
  - [x] Target-scoped UDP runtime and firewall.
  - [x] Structured result persistence.
  - [x] Package candidate `0.3.2_13`.
- Patch 12 — Temporary circular live validation: BLOCKED BY PATCH 11 GATE.
- Patch 13 — Final synchronous Blockcheck replacement: BLOCKED.

Strict serial delivery and deferred owner-assisted verification remain mandatory.

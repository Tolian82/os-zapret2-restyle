# os-zapret2-restyle — Roadmap

Current candidate: `v0.3.2_11`.

Strict serial gate applies to every Strategy Lab patch.

- Patches 1–8: COMPLETE.
- Patch 9 — Extended TLS 1.2 and HTTP: IN DELIVERY.
  - [x] Explicit TLS 1.2 bounded GET.
  - [x] Explicit plain HTTP bounded GET.
  - [x] Protocol-specific port and L7 filtering.
  - [x] Sequential Zapret2 candidate catalogs.
  - [x] Structured protocol result persistence.
  - [x] Extended-mode gating.
  - [x] Package candidate `0.3.2_11`.
- Patch 10 — QUIC strategy branch: BLOCKED BY PATCH 9 GATE.
- Patch 11 — Arbitrary UDP strategy branch: BLOCKED.
- Patch 12 — Temporary circular live validation: BLOCKED.
- Patch 13 — Final synchronous Blockcheck replacement: BLOCKED.

Owner-assisted OPNsense verification follows Patch 13.

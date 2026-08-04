# os-zapret2-restyle — Current state

Project: `os-zapret2-restyle`
Primary branch: `main`
Published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Current package candidate: `os-zapret2-restyle-0.3.2_12.pkg`

- Patches 1–9: complete and merged.
- Patch 9 merged as `8b76c01e0e8f333af93868dd01ccda11fedb8fdb`; task branch removed.
- Patch 10: QUIC capability-gated strategy branch in delivery.
- Patches 11–13: blocked by the serial gate.

Patch 10 tests QUIC only when stage 30 reports `quic_ipv4=available`; otherwise it records an explicit skipped result. It uses Zapret2 QUIC syntax, UDP/443 target-scoped rules, and OpenSSL QUIC target requests. `VERSION=0.3.2`; `PLUGIN_REVISION=12`; no release publication is authorized.

Next action: completely process Patch 10 before Patch 11.
